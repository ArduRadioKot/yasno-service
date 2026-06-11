"""Tasks routes"""

from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional, List, Dict, Any
from schemas import TaskCheckRequest, GenerateTaskRequest
from services.data_service import data_service
from services.db import get_user_by_email, add_completed_task
from services.ai_client import chat_completion, extract_json, is_ai_available
import json

router = APIRouter(prefix="/api", tags=["tasks"])

# Constants from app.py
SUBJECT_FALLBACK_QUESTIONS = {
    "physics": [
        {
            "topic": "Оптика",
            "question": "Как изменится фокусное расстояние собирающей линзы, если её оптическая сила увеличится в 2 раза?",
            "answers": ["Увеличится в 2 раза", "Уменьшится в 2 раза", "Не изменится", "Станет отрицательным"],
            "correctIndex": 1,
        },
        {
            "topic": "Колебания и волны",
            "question": "Что произойдёт с периодом математического маятника при увеличении длины нити в 4 раза?",
            "answers": ["Увеличится в 2 раза", "Увеличится в 4 раза", "Уменьшится в 2 раза", "Не изменится"],
            "correctIndex": 0,
        },
        {
            "topic": "Электродинамика",
            "question": "При последовательном соединении резисторов какая величина одинакова на всех участках цепи?",
            "answers": ["Напряжение", "Сила тока", "Сопротивление", "Мощность"],
            "correctIndex": 1,
        },
    ],
    "math": [
        {
            "topic": "Производная",
            "question": "Чему равна производная функции f(x)=x^3-4x?",
            "answers": ["3x^2-4", "x^2-4", "3x^2", "x^3-4"],
            "correctIndex": 0,
        },
        {
            "topic": "Стереометрия",
            "question": "Какая формула задаёт объём пирамиды?",
            "answers": ["Sосн*h", "1/2*Sосн*h", "1/3*Sосн*h", "4/3*pi*r^3"],
            "correctIndex": 2,
        },
        {
            "topic": "Тригонометрия",
            "question": "Какое тождество верно для любого x?",
            "answers": ["sin^2 x + cos^2 x = 1", "sin x + cos x = 1", "tg x = cos x / sin x", "cos 2x = 2sin^2 x - 1"],
            "correctIndex": 0,
        },
    ],
    "russian": [
        {
            "topic": "Пунктуация",
            "question": "В каком случае нужна запятая перед союзом «и»?",
            "answers": ["Между однородными членами без повторения союза", "Между частями сложносочинённого предложения", "В устойчивом выражении", "Всегда перед союзом «и»"],
            "correctIndex": 1,
        },
        {
            "topic": "Сочинение",
            "question": "Что обязательно должно быть в комментарии к проблеме исходного текста?",
            "answers": ["Два примера-иллюстрации из текста", "Биография автора", "Пересказ всего текста", "Цитата из любого произведения"],
            "correctIndex": 0,
        },
        {
            "topic": "Синтаксис",
            "question": "Что такое грамматическая основа предложения?",
            "answers": ["Все второстепенные члены", "Подлежащее и сказуемое", "Только сказуемое", "Любые два существительных"],
            "correctIndex": 1,
        },
    ],
}


def normalize_questions(data: dict, subject_id: str, topic: str, count: int = 5):
    questions = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(questions, list):
        raise ValueError("questions must be a list")

    normalized = []
    for item in questions[:count]:
        answers = item.get("answers", [])
        correct_index = item.get("correctIndex", 0)
        if (
            not item.get("question")
            or not isinstance(answers, list)
            or len(answers) < 2
            or not isinstance(correct_index, int)
            or correct_index < 0
            or correct_index >= len(answers)
        ):
            continue
        normalized.append(
            {
                "topic": item.get("topic") or topic,
                "question": item["question"],
                "answers": answers[:4],
                "correctIndex": correct_index,
            }
        )

    if not normalized:
        raise ValueError("AI returned no valid questions")
    return {"topic": topic, "questions": normalized}


def normalize_generated_task(data: dict, subject_id: str, fallback_topic: str):
    task = data.get("task") if isinstance(data.get("task"), dict) else data
    answers = task.get("answers", [])
    correct_index = task.get("correctIndex")

    if correct_index is None:
        correct_index = next(
            (
                i
                for i, answer in enumerate(answers)
                if isinstance(answer, dict) and answer.get("isCorrect")
            ),
            0,
        )

    if not task.get("question") or not isinstance(answers, list) or len(answers) < 2:
        raise ValueError("AI returned invalid task")
    if not isinstance(correct_index, int) or correct_index < 0 or correct_index >= len(answers):
        raise ValueError("AI returned invalid correctIndex")

    normalized_answers = []
    for index, answer in enumerate(answers[:4]):
        text = answer.get("text") if isinstance(answer, dict) else str(answer)
        normalized_answers.append(
            {
                "id": index + 1,
                "text": text,
                "isCorrect": index == correct_index,
            }
        )

    explanation = task.get("explanation") if isinstance(task.get("explanation"), dict) else {}
    steps = explanation.get("steps", [])
    if not isinstance(steps, list) or not steps:
        steps = ["Определи тему вопроса", "Запиши нужное правило или формулу", "Проверь ответ по условию"]

    return {
        "topic": task.get("topic") or fallback_topic,
        "difficulty": task.get("difficulty") or "medium",
        "question": task["question"],
        "given": task.get("given") if isinstance(task.get("given"), list) else [],
        "answers": normalized_answers,
        "explanation": {
            "wrongHint": explanation.get("wrongHint")
            or "Вернись к ключевому правилу темы и проверь, какой ответ ему соответствует.",
            "steps": [str(step) for step in steps[:5]],
            "tip": explanation.get("tip")
            or "После решения обязательно проверь единицы измерения, знаки и смысл ответа.",
        },
    }


def fallback_generated_task(subject_id: str, subject_name: str, topic: str):
    test = fallback_test(subject_id, subject_name, topic)
    question = test["questions"][0]
    return {
        "topic": question.get("topic") or topic,
        "difficulty": "medium",
        "question": question["question"],
        "given": [],
        "answers": [
            {
                "id": index + 1,
                "text": answer,
                "isCorrect": index == question["correctIndex"],
            }
            for index, answer in enumerate(question["answers"])
        ],
        "explanation": {
            "wrongHint": "AI-задание проверяет базовое понимание темы. Сравни ответ с определением или формулой.",
            "steps": [
                "Выдели ключевые величины или понятия в условии",
                "Примени основное правило темы",
                "Сверь ответ с вопросом",
            ],
            "tip": "Если сомневаешься, объясни себе, почему остальные варианты не подходят.",
        },
    }


def fallback_test(subject_id: str, subject_name: str, topic: str, count: int = 5):
    base = SUBJECT_FALLBACK_QUESTIONS.get(subject_id)
    if not base:
        topics = data_service.get_plan_topics(subject_id)[:3] or [topic]
        base = [
            {
                "topic": name,
                "question": f"Какой первый шаг лучше всего помогает проверить понимание темы «{name}»?",
                "answers": [
                    "Дать определение и решить базовый пример",
                    "Сразу перейти к самым сложным задачам",
                    "Запомнить только один ответ",
                    "Не смотреть на ошибки после решения",
                ],
                "correctIndex": 0,
            }
            for name in topics
        ]
    repeats = (base * ((count // len(base)) + 1)) if base else []
    return {"topic": topic or f"диагностика по предмету {subject_name}", "questions": repeats[:count]}


@router.get("/tasks")
async def list_tasks(
    subjectId: Optional[str] = Query(None),
    topic: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get list of tasks"""
    subject_id = subjectId or data_service.get_active_subject_id()
    tasks = data_service.get_tasks(subject_id, topic)
    total = len(tasks)
    
    return {
        "tasks": [
            {
                "id": t["id"],
                "topic": t["topic"],
                "difficulty": t["difficulty"],
                "question": t["question"][:80] + ("…" if len(t["question"]) > 80 else ""),
            }
            for t in tasks
        ],
        "total": total,
    }


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    subjectId: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get specific task"""
    subject_id = subjectId or data_service.get_active_subject_id()
    tasks = data_service.get_tasks(subject_id)
    task = data_service.get_task(task_id)
    
    if not task or task["subjectId"] != subject_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    try:
        index = next(i for i, t in enumerate(tasks) if t["id"] == task_id) + 1
    except StopIteration:
        index = 1
    
    return data_service.task_for_client(task, index, len(tasks))


@router.post("/tasks/{task_id}/check")
async def check_task(
    task_id: str,
    request: TaskCheckRequest,
    email: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Check task answer"""
    email = request.email or email
    answer_id = request.answerId
    
    if answer_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="answerId required"
        )
    
    result = data_service.check_answer(task_id, int(answer_id))
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if result.get("correct") and email:
        user = get_user_by_email(email)
        if user:
            add_completed_task(user["id"], task_id)
    
    return result


@router.get("/tasks/{task_id}/next")
async def next_task(
    task_id: str,
    subjectId: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get next task"""
    subject_id = subjectId or data_service.get_active_subject_id()
    tasks = data_service.get_tasks(subject_id)
    ids = [t["id"] for t in tasks]
    
    if task_id not in ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    idx = ids.index(task_id)
    next_id = ids[(idx + 1) % len(ids)]
    task = data_service.get_task(next_id)
    next_idx = ids.index(next_id)
    
    return data_service.task_for_client(task, next_idx + 1, len(tasks))


@router.post("/tasks/generate")
async def generate_task(request: GenerateTaskRequest) -> Dict[str, Any]:
    """Generate a new task using AI"""
    subject_id = request.subjectId or data_service.get_active_subject_id()
    requested_topic = (request.topic or "").strip()
    requested_difficulty = (request.difficulty or "medium").strip()
    
    subject = data_service.get_subject(subject_id)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found"
        )
    
    subject_name = subject["name"]
    plan_topics = data_service.get_plan_topics(subject_id)
    topic = requested_topic or (plan_topics[0] if plan_topics else "ключевые темы")
    
    if is_ai_available():
        try:
            content = chat_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            "Ты составляешь задания ЕГЭ. Верни только валидный JSON без markdown. "
                            "Варианты ответов должны быть правдоподобными, один правильный. "
                            "Пиши строго на русском языке: тему, условие, дано, ответы и объяснение."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"""Сгенерируй одно новое задание по предмету "{subject_name}".
Тема: "{topic}".
Сложность: "{requested_difficulty}".
Ориентируйся на темы плана: {", ".join(plan_topics[:8])}.
Весь текст должен быть на русском языке, кроме формул и единиц измерения.

Формат:
{{
  "topic": "конкретная тема",
  "difficulty": "easy|medium|hard",
  "question": "условие задания",
  "given": ["дано 1", "дано 2"],
  "answers": ["вариант 1", "вариант 2", "вариант 3", "вариант 4"],
  "correctIndex": 0,
  "explanation": {{
    "wrongHint": "почему типичная ошибка неверна",
    "steps": ["шаг 1", "шаг 2"],
    "tip": "короткий совет"
  }}
}}""",
                    },
                ],
                max_tokens=900,
            )
            task = normalize_generated_task(extract_json(content), subject_id, topic)
        except Exception:
            task = fallback_generated_task(subject_id, subject_name, topic)
    else:
        task = fallback_generated_task(subject_id, subject_name, topic)
    
    generated = data_service.add_generated_task(subject_id, task)
    tasks = data_service.get_tasks(subject_id)
    
    return data_service.task_for_client(generated, 1, len(tasks))
