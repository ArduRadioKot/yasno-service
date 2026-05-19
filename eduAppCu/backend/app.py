from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

from services.data_service import data_service
from services.db import (
    init_db,
    create_user,
    get_user_by_email,
    get_user_subjects,
    get_user_settings,
    update_user_settings,
    get_user_progress,
    update_user_progress,
    upsert_user_progress,
)
import datetime

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize SQLite database
init_db()

# Initialize OpenAI client for Gemma 4b
openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_api_key,
    timeout=25,
) if openrouter_api_key else None
AI_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")


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


def extract_json(content: str):
    match = re.search(r"\{[\s\S]*\}", content or "")
    if not match:
        raise ValueError("AI response does not contain JSON")
    return json.loads(match.group())


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


def fallback_analysis(subject_id: str, subject_name: str, answers: list[dict]):
    total = len(answers)
    correct_count = sum(1 for a in answers if a.get("correct"))
    score = round((correct_count / total) * 100) if total else 0
    wrong_topics = [
        a.get("topic") or a.get("question", "Тема вопроса")
        for a in answers
        if not a.get("correct")
    ]
    gaps = list(dict.fromkeys([str(t).strip() for t in wrong_topics if str(t).strip()]))
    if not gaps and score < 90:
        gaps = data_service.get_plan_topics(subject_id)[:2]
    level = "сильный" if score >= 80 else "средний" if score >= 50 else "начальный"
    analysis = (
        f"Результат по предмету «{subject_name}»: {correct_count} из {total} "
        f"({score}%). Уровень: {level}. "
    )
    if gaps:
        analysis += "В план добавлены темы, которые стоит подтянуть в первую очередь."
    else:
        analysis += "Явных пробелов не видно, можно переходить к задачам повышенной сложности."
    return {"analysis": analysis, "gaps": gaps, "score": score, "level": level}


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/register")
def register():
    body = request.get_json(silent=True) or {}
    email = body.get("email")
    password = body.get("password")
    first_name = body.get("firstName")
    last_name = body.get("lastName")
    exam_type = body.get("examType", "ЕГЭ")
    marketing = body.get("marketing", False)
    subjects = body.get("subjects", [])
    targets = body.get("targets", {})
    
    if not email or not password or not first_name or not last_name:
        return jsonify({"error": "Missing required fields"}), 400
    
    # Check if user already exists
    existing_user = get_user_by_email(email)
    if existing_user:
        return jsonify({"error": "User already exists"}), 400
    
    try:
        user_id = create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            exam_type=exam_type,
            marketing=marketing,
            subjects=subjects,
            targets=targets
        )
        return jsonify({"userId": user_id, "message": "User created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/subjects")
def list_subjects():
    email = request.args.get("email")
    active = data_service.get_active_subject_id()
    
    # If email provided, filter subjects by user's selection
    if email:
        user = get_user_by_email(email)
        if user:
            user_subjects = get_user_subjects(user["id"])
            all_subjects = data_service.get_subjects()
            filtered_subjects = [s for s in all_subjects if s["id"] in user_subjects]
            return jsonify(
                {
                    "subjects": filtered_subjects,
                    "activeSubjectId": active,
                }
            )
    
    return jsonify(
        {
            "subjects": data_service.get_subjects(),
            "activeSubjectId": active,
        }
    )


@app.put("/api/user/subject")
def set_subject():
    body = request.get_json(silent=True) or {}
    subject_id = body.get("subjectId")
    if not subject_id:
        return jsonify({"error": "subjectId required"}), 400
    subject = data_service.set_active_subject(subject_id)
    if not subject:
        return jsonify({"error": "Subject not found"}), 404
    return jsonify({"subject": subject, "activeSubjectId": subject_id})


@app.get("/api/user")
def get_user():
    email = request.args.get("email")
    if email:
        user = get_user_by_email(email)
        if user:
            settings = get_user_settings(user["id"]) or {}
            return jsonify(
                {
                    "userName": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                    "activeSubjectId": settings.get("active_subject_id") or data_service.get_active_subject_id(),
                    "completedTaskIds": settings.get("completed_task_ids", []),
                }
            )

    return jsonify(
        {
            "userName": data_service.user["userName"],
            "activeSubjectId": data_service.get_active_subject_id(),
            "completedTaskIds": data_service.user["completedTaskIds"],
        }
    )


@app.get("/api/dashboard")
def dashboard():
    subject_id = request.args.get("subjectId") or data_service.get_active_subject_id()
    email = request.args.get("email")
    data = data_service.get_dashboard(subject_id)
    if not data:
        return jsonify({"error": "Subject not found"}), 404

    # If user email provided, overlay DB-stored progress and settings
    if email:
        user = get_user_by_email(email)
        if user:
            user_id = user["id"]
            progress = get_user_progress(user_id, subject_id) or {"score": 0, "score_delta": 0, "chart": []}
            settings = get_user_settings(user_id) or {}
            data["score"] = progress.get("score", 0)
            data["scoreDelta"] = progress.get("score_delta", 0)
            data["chart"] = [{"day": i + 1, "score": v} for i, v in enumerate(progress.get("chart", []))]
            data["streak"] = settings.get("streak", 0)
            data["achievements"] = settings.get("achievements", 0)
    return jsonify(data)


@app.get("/api/plan")
def plan():
    subject_id = request.args.get("subjectId") or data_service.get_active_subject_id()
    data = data_service.get_plan(subject_id)
    if not data:
        return jsonify({"error": "Plan not found"}), 404
    return jsonify(data)


@app.get("/api/tasks")
def list_tasks():
    subject_id = request.args.get("subjectId") or data_service.get_active_subject_id()
    topic = request.args.get("topic")
    tasks = data_service.get_tasks(subject_id, topic)
    total = len(tasks)
    return jsonify(
        {
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
    )


@app.get("/api/tasks/<task_id>")
def get_task(task_id):
    subject_id = request.args.get("subjectId") or data_service.get_active_subject_id()
    tasks = data_service.get_tasks(subject_id)
    task = data_service.get_task(task_id)
    if not task or task["subjectId"] != subject_id:
        return jsonify({"error": "Task not found"}), 404
    try:
        index = next(i for i, t in enumerate(tasks) if t["id"] == task_id) + 1
    except StopIteration:
        index = 1
    return jsonify(data_service.task_for_client(task, index, len(tasks)))


@app.post("/api/tasks/<task_id>/check")
def check_task(task_id):
    body = request.get_json(silent=True) or {}
    answer_id = body.get("answerId")
    if answer_id is None:
        return jsonify({"error": "answerId required"}), 400
    result = data_service.check_answer(task_id, int(answer_id))
    if not result:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(result)


@app.get("/api/tasks/<task_id>/next")
def next_task(task_id):
    subject_id = request.args.get("subjectId") or data_service.get_active_subject_id()
    tasks = data_service.get_tasks(subject_id)
    ids = [t["id"] for t in tasks]
    if task_id not in ids:
        return jsonify({"error": "Task not found"}), 404
    idx = ids.index(task_id)
    next_id = ids[(idx + 1) % len(ids)]
    task = data_service.get_task(next_id)
    next_idx = ids.index(next_id)
    return jsonify(data_service.task_for_client(task, next_idx + 1, len(tasks)))


@app.post("/api/tasks/generate")
def generate_task():
    body = request.get_json(silent=True) or {}
    subject_id = body.get("subjectId") or data_service.get_active_subject_id()
    requested_topic = (body.get("topic") or "").strip()
    requested_difficulty = (body.get("difficulty") or "medium").strip()

    subject = data_service.get_subject(subject_id)
    if not subject:
        return jsonify({"error": "Subject not found"}), 404

    subject_name = subject["name"]
    plan_topics = data_service.get_plan_topics(subject_id)
    topic = requested_topic or (plan_topics[0] if plan_topics else "ключевые темы")

    if client:
        try:
            response = client.chat.completions.create(
                model=AI_MODEL,
                max_tokens=900,
                messages=[
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
            )
            content = response.choices[0].message.content or ""
            task = normalize_generated_task(extract_json(content), subject_id, topic)
        except Exception:
            task = fallback_generated_task(subject_id, subject_name, topic)
    else:
        task = fallback_generated_task(subject_id, subject_name, topic)

    generated = data_service.add_generated_task(subject_id, task)
    tasks = data_service.get_tasks(subject_id)
    return jsonify(data_service.task_for_client(generated, 1, len(tasks)))


@app.post("/api/chat")
def chat():
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    subject_id = body.get("subjectId") or data_service.get_active_subject_id()
    if not message:
        return jsonify({"error": "message required"}), 400
    
    if not client:
        return jsonify(
            {
                "error": (
                    "AI-чат не настроен: добавьте OPENROUTER_API_KEY в backend/.env "
                    "и перезапустите backend."
                )
            }
        ), 503

    if client:
        try:
            subject = data_service.get_subject(subject_id)
            subject_name = subject["name"] if subject else "предмету"
            
            topics = ", ".join(data_service.get_plan_topics(subject_id)[:6])
            response = client.chat.completions.create(
                model=AI_MODEL,
                max_tokens=900,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты AI-репетитор для подготовки к ЕГЭ. Отвечай на русском, "
                            "кратко, понятно и по делу. Если студент просит тест, предложи "
                            "нажать «Начать занятие» на главной для диагностики и плана."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Предмет: {subject_name}. Темы плана: {topics or 'не заданы'}.\n"
                            f"Вопрос студента: {message}"
                        ),
                    }
                ]
            )
            
            reply = (response.choices[0].message.content or "").strip()
            if not reply:
                raise ValueError("empty AI response")
            return jsonify({"role": "assistant", "content": reply})
            
        except Exception:
            return jsonify(
                {
                    "error": (
                        "AI-чат сейчас не смог получить ответ от модели. "
                        "Проверьте OPENROUTER_API_KEY, модель OPENROUTER_MODEL и доступ backend к OpenRouter."
                    )
                }
            ), 502


@app.get("/api/chat/suggestions")
def chat_suggestions():
    subject_id = request.args.get("subjectId") or data_service.get_active_subject_id()
    subject = data_service.get_subject(subject_id)
    name = subject["name"] if subject else "предмету"
    return jsonify(
        {
            "prompts": [
                {"text": "Объясни проще", "icon": "book"},
                {"text": f"Разбери задачу по {name}", "icon": "question"},
                {"text": "Составь мини тест", "icon": "zap"},
            ]
        }
    )


@app.post("/api/generate-test")
def generate_test():
    body = request.get_json(silent=True) or {}
    subject_ids = body.get("subjectIds")
    subject_id = (
        body.get("subjectId")
        or request.args.get("subjectId")
        or data_service.get_active_subject_id()
    )
    
    # If multiple subjects provided, generate combined test
    if subject_ids and isinstance(subject_ids, list):
        return generate_multi_subject_test(subject_ids, body)
    
    topic = body.get("topic") or request.args.get("topic") or "диагностика по предмету"
    count = int(body.get("count") or request.args.get("count") or 5)
    count = max(3, min(count, 12))
    subject = data_service.get_subject(subject_id)
    subject_name = subject["name"] if subject else "предмету"
    plan_topics = data_service.get_plan_topics(subject_id)[:8]
    
    if not client:
        return jsonify(fallback_test(subject_id, subject_name, topic, count))
    
    try:
        prompt = f"""Сгенерируй диагностический тест по предмету "{subject_name}" для подготовки к ЕГЭ.
Тест должен показать, насколько ученик разбирается в предмете, и найти темы, которые нужно подтянуть.
Охвати разные темы из списка: {", ".join(plan_topics) or topic}.
Сделай ровно {count} вопросов разной сложности.
Весь текст вопросов, тем и ответов должен быть на русском языке, кроме формул.
        
Формат ответа (строго в JSON):
{{
  "questions": [
    {{
      "topic": "тема вопроса",
      "question": "текст вопроса",
      "answers": ["ответ1", "ответ2", "ответ3", "ответ4"],
      "correctIndex": 0
    }}
  ]
}}

Не добавляй пояснения вне JSON."""

        response = client.chat.completions.create(
            model=AI_MODEL,
            max_tokens=1200,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        content = response.choices[0].message.content or ""
        return jsonify(normalize_questions(extract_json(content), subject_id, topic, count))
        
    except Exception as e:
        return jsonify(fallback_test(subject_id, subject_name, topic, count))


def generate_multi_subject_test(subject_ids: list, body: dict):
    """Generate a diagnostic test covering multiple subjects."""
    topic = body.get("topic") or "комплексная диагностика"
    count_per_subject = int(body.get("count") or 3)
    count_per_subject = max(2, min(count_per_subject, 5))
    
    all_questions = []
    subjects_info = []
    
    for subject_id in subject_ids:
        subject = data_service.get_subject(subject_id)
        if not subject:
            continue
        subject_name = subject["name"]
        plan_topics = data_service.get_plan_topics(subject_id)[:4]
        subjects_info.append(f"{subject_name}: {', '.join(plan_topics[:3])}")
        
        if not client:
            test = fallback_test(subject_id, subject_name, topic, count_per_subject)
            all_questions.extend(test.get("questions", []))
        else:
            try:
                prompt = f"""Сгенерируй {count_per_subject} диагностических вопросов по предмету "{subject_name}" для подготовки к ЕГЭ.
Охвати темы: {", ".join(plan_topics) or topic}.
Весь текст вопросов, тем и ответов должен быть на русском языке, кроме формул.
                
Формат ответа (строго в JSON):
{{
  "questions": [
    {{
      "topic": "тема вопроса",
      "question": "текст вопроса",
      "answers": ["ответ1", "ответ2", "ответ3", "ответ4"],
      "correctIndex": 0
    }}
  ]
}}

Не добавляй пояснения вне JSON."""

                response = client.chat.completions.create(
                    model=AI_MODEL,
                    max_tokens=800,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                content = response.choices[0].message.content or ""
                test_data = normalize_questions(extract_json(content), subject_id, topic, count_per_subject)
                all_questions.extend(test_data.get("questions", []))
                
            except Exception:
                test = fallback_test(subject_id, subject_name, topic, count_per_subject)
                all_questions.extend(test.get("questions", []))
    
    return jsonify({
        "topic": f"Комплексная диагностика по {len(subject_ids)} предметам",
        "questions": all_questions,
        "subjects": subjects_info
    })


def analyze_multi_subject_test(subject_ids: list, answers: list, email: str = None):
    """Analyze test results for multiple subjects."""
    all_gaps = []
    all_scores = []
    analyses = []
    
    subject_scores = {}
    for subject_id in subject_ids:
        subject = data_service.get_subject(subject_id)
        if not subject:
            continue
        subject_name = subject["name"]
        
        # Filter answers for this subject (by topic matching)
        subject_answers = [
            a for a in answers
            if a.get('topic') or any(topic in a.get('question', '') for topic in data_service.get_plan_topics(subject_id)[:5])
        ]
        
        if not subject_answers:
            continue
        
        if not client:
            analysis_data = fallback_analysis(subject_id, subject_name, subject_answers)
            subject_scores[subject_id] = analysis_data.get("score", 0)
            all_gaps.extend(analysis_data.get("gaps", []))
            all_scores.append(analysis_data.get("score", 0))
            analyses.append(f"{subject_name}: {analysis_data.get('analysis', '')}")
            data_service.update_plan_from_gaps(
                subject_id, analysis_data["gaps"], analysis_data["analysis"]
            )
        else:
            try:
                answers_text = "\n".join([
                    (
                        f"- Тема: {a.get('topic', 'не указана')}; "
                        f"вопрос: {a.get('question', 'Вопрос')}; "
                        f"ответ ученика: {a.get('selectedAnswer', 'не указан')}; "
                        f"правильный ответ: {a.get('correctAnswer', 'не указан')}; "
                        f"результат: {'Правильно' if a.get('correct') else 'Неправильно'}"
                    )
                    for a in subject_answers
                ])
                
                prompt = f"""Проанализируй результаты теста по предмету "{subject_name}".

Результаты:
{answers_text}

Формат ответа (строго в JSON):
{{
  "analysis": "краткий анализ результатов и рекомендации",
  "gaps": ["список конкретных тем с пробелами в знаниях"],
  "score": 0,
  "level": "начальный|средний|сильный"
}}

Верни только темы, которые действительно стоит подтянуть. Не добавляй пояснения вне JSON."""

                response = client.chat.completions.create(
                    model=AI_MODEL,
                    max_tokens=700,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                content = response.choices[0].message.content or ""
                analysis_data = extract_json(content)
                if not isinstance(analysis_data.get("gaps"), list):
                    analysis_data["gaps"] = []
                if "score" not in analysis_data or "level" not in analysis_data:
                    fallback = fallback_analysis(subject_id, subject_name, subject_answers)
                    analysis_data.setdefault("score", fallback["score"])
                    analysis_data.setdefault("level", fallback["level"])
                
                subject_scores[subject_id] = analysis_data.get("score", 0)
                all_gaps.extend(analysis_data.get("gaps", []))
                all_scores.append(analysis_data.get("score", 0))
                analyses.append(f"{subject_name}: {analysis_data.get('analysis', '')}")
                data_service.update_plan_from_gaps(
                    subject_id, analysis_data.get("gaps", []), analysis_data.get("analysis", "")
                )
                
            except Exception:
                analysis_data = fallback_analysis(subject_id, subject_name, subject_answers)
                subject_scores[subject_id] = analysis_data.get("score", 0)
                all_gaps.extend(analysis_data.get("gaps", []))
                all_scores.append(analysis_data.get("score", 0))
                analyses.append(f"{subject_name}: {analysis_data.get('analysis', '')}")
                data_service.update_plan_from_gaps(
                    subject_id, analysis_data["gaps"], analysis_data["analysis"]
                )
    
    # Calculate overall score and level
    avg_score = round(sum(all_scores) / len(all_scores)) if all_scores else 0
    level = "сильный" if avg_score >= 80 else "средний" if avg_score >= 50 else "начальный"
    
    # Remove duplicate gaps
    unique_gaps = list(dict.fromkeys([str(g).strip() for g in all_gaps if str(g).strip()]))
    
    combined_analysis = (
        f"Комплексный результат по {len(subject_ids)} предметам: средний балл {avg_score}%. "
        f"Уровень: {level}. " + ". ".join(analyses)
    )
    
    # Persist per-user progress if email provided
    if email:
        user = get_user_by_email(email)
        if user:
            user_id = user["id"]
            try:
                for sid, score in subject_scores.items():
                    prev = get_user_progress(user_id, sid) or {"score": 0, "chart": []}
                    prev_score = prev.get("score", 0)
                    chart = prev.get("chart", []) or []
                    chart.append(score)
                    score_delta = score - prev_score
                    upsert_user_progress(user_id, sid, score=score, score_delta=score_delta, chart=chart)

                # Update streak and last active
                settings = get_user_settings(user_id) or {}
                last_active = settings.get("last_active_date")
                today = datetime.date.today()
                try:
                    last_date = datetime.date.fromisoformat(last_active) if last_active else None
                except Exception:
                    last_date = None
                if last_date and (today - last_date).days == 1:
                    streak = (settings.get("streak") or 0) + 1
                else:
                    streak = 1
                update_user_settings(user_id, streak=streak, last_active_date=today.isoformat())
            except Exception:
                pass

    return jsonify({
        "analysis": combined_analysis,
        "gaps": unique_gaps[:10],  # Limit to top 10 gaps
        "score": avg_score,
        "level": level,
        "subjects": analyses
    })


@app.post("/api/analyze-test")
def analyze_test():
    body = request.get_json(silent=True) or {}
    email = body.get("email") or request.args.get("email")
    subject_ids = body.get("subjectIds")
    subject_id = request.args.get("subjectId") or data_service.get_active_subject_id()
    answers = body.get("answers", [])
    
    # If multiple subjects provided, analyze for each subject separately
    if subject_ids and isinstance(subject_ids, list):
        return analyze_multi_subject_test(subject_ids, answers, email)
    
    subject = data_service.get_subject(subject_id)
    subject_name = subject["name"] if subject else "предмету"
    
    if not client:
        analysis_data = fallback_analysis(subject_id, subject_name, answers)
        data_service.update_plan_from_gaps(
            subject_id, analysis_data["gaps"], analysis_data["analysis"]
        )

        # Persist to DB if user email provided
        if email:
            user = get_user_by_email(email)
            if user:
                user_id = user["id"]
                try:
                    prev = get_user_progress(user_id, subject_id) or {"score": 0, "chart": []}
                    prev_score = prev.get("score", 0)
                    chart = prev.get("chart", []) or []
                    chart.append(analysis_data.get("score", 0))
                    score_delta = analysis_data.get("score", 0) - prev_score
                    upsert_user_progress(user_id, subject_id, score=analysis_data.get("score", 0), score_delta=score_delta, chart=chart)

                    settings = get_user_settings(user_id) or {}
                    last_active = settings.get("last_active_date")
                    today = datetime.date.today()
                    try:
                        last_date = datetime.date.fromisoformat(last_active) if last_active else None
                    except Exception:
                        last_date = None
                    if last_date and (today - last_date).days == 1:
                        streak = (settings.get("streak") or 0) + 1
                    else:
                        streak = 1
                    update_user_settings(user_id, streak=streak, last_active_date=today.isoformat())
                except Exception:
                    pass

        return jsonify(analysis_data)
    
    try:
        # Analyze test results using AI
        answers_text = "\n".join([
            (
                f"- Тема: {a.get('topic', 'не указана')}; "
                f"вопрос: {a.get('question', 'Вопрос')}; "
                f"ответ ученика: {a.get('selectedAnswer', 'не указан')}; "
                f"правильный ответ: {a.get('correctAnswer', 'не указан')}; "
                f"результат: {'Правильно' if a.get('correct') else 'Неправильно'}"
            )
            for a in answers
        ])
        
        prompt = f"""Проанализируй результаты теста по предмету "{subject_name}".

Результаты:
{answers_text}

Формат ответа (строго в JSON):
{{
  "analysis": "краткий анализ результатов и рекомендации",
  "gaps": ["список конкретных тем с пробелами в знаниях"],
  "score": 0,
  "level": "начальный|средний|сильный"
}}

Верни только темы, которые действительно стоит подтянуть. Не добавляй пояснения вне JSON."""

        response = client.chat.completions.create(
            model=AI_MODEL,
            max_tokens=700,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        content = response.choices[0].message.content or ""
        analysis_data = extract_json(content)
        if not isinstance(analysis_data.get("gaps"), list):
            analysis_data["gaps"] = []
        if "score" not in analysis_data or "level" not in analysis_data:
            fallback = fallback_analysis(subject_id, subject_name, answers)
            analysis_data.setdefault("score", fallback["score"])
            analysis_data.setdefault("level", fallback["level"])
        data_service.update_plan_from_gaps(
            subject_id, analysis_data.get("gaps", []), analysis_data.get("analysis", "")
        )

        # Persist to DB if user email provided
        if email:
            user = get_user_by_email(email)
            if user:
                user_id = user["id"]
                try:
                    prev = get_user_progress(user_id, subject_id) or {"score": 0, "chart": []}
                    prev_score = prev.get("score", 0)
                    chart = prev.get("chart", []) or []
                    chart.append(analysis_data.get("score", 0))
                    score_delta = analysis_data.get("score", 0) - prev_score
                    upsert_user_progress(user_id, subject_id, score=analysis_data.get("score", 0), score_delta=score_delta, chart=chart)

                    settings = get_user_settings(user_id) or {}
                    last_active = settings.get("last_active_date")
                    today = datetime.date.today()
                    try:
                        last_date = datetime.date.fromisoformat(last_active) if last_active else None
                    except Exception:
                        last_date = None
                    if last_date and (today - last_date).days == 1:
                        streak = (settings.get("streak") or 0) + 1
                    else:
                        streak = 1
                    update_user_settings(user_id, streak=streak, last_active_date=today.isoformat())
                except Exception:
                    pass

        return jsonify(analysis_data)
        
    except Exception as e:
        analysis_data = fallback_analysis(subject_id, subject_name, answers)
        data_service.update_plan_from_gaps(
            subject_id, analysis_data["gaps"], analysis_data["analysis"]
        )
        return jsonify(analysis_data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
