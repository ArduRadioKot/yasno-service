from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json
import re
from dotenv import load_dotenv

from services.ai_client import chat_completion, extract_json, is_ai_available
from services.data_service import data_service
from services.problem_bank_service import ProblemBankError, ensure_problem_bank
from services.test_service import (
    analyze_multi_subject_test as run_multi_analysis,
    analyze_test as run_test_analysis,
    generate_multi_subject_test,
    generate_test as run_generate_test,
)
from services.db import (
    init_db,
    create_user,
    get_user_by_email,
    get_user_subjects,
    get_user_settings,
    update_user_settings,
    get_user_progress,
    upsert_user_progress,
    get_topic_progress,
    get_user_plan_topics,
    set_topic_progress,
    add_completed_task,
    update_plan_topic_entry,
    get_subject_task_progress,
    record_test_task_progress,
)
import datetime

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

init_db()


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


def save_progress_after_test(user_id: int, subject_id: str, exam_score: int, score_delta_base: int | None = None):
    prev = get_user_progress(user_id, subject_id) or {"score": 0, "chart": []}
    prev_score = prev.get("score", 0)
    chart = list(prev.get("chart", []) or [])
    chart.append(exam_score)
    if len(chart) > 14:
        chart = chart[-14:]
    score_delta = exam_score - prev_score if score_delta_base is None else score_delta_base
    upsert_user_progress(
        user_id,
        subject_id,
        score=exam_score,
        score_delta=score_delta,
        chart=chart,
    )


def update_streak(user_id: int):
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
    level = "сильный" if score >= 80 else "средний" if score >= 50 else "начальный"
    analysis = (
        f"Результат по предмету «{subject_name}»: {correct_count} из {total} "
        f"({score}%). Уровень: {level}. "
    )
    if gaps:
        analysis += "В план добавлены темы, которые стоит подтянуть в первую очередь."
    else:
        analysis += "Явных пробелов не видно, можно переходить к задачам повышенной сложности."
    return {
        "analysis": analysis,
        "gaps": gaps,
        "score": score,
        "examScore": round(score * 0.9),
        "level": level,
        "breakdowns": [],
    }


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
    topic_overrides = None
    stored_topics = None
    user_id = None
    if email:
        user = get_user_by_email(email)
        if user:
            user_id = user["id"]
            topic_overrides = get_topic_progress(user_id, subject_id)
            stored_topics = get_user_plan_topics(user_id, subject_id)

    completed_task_ids = None
    subject_task_stats = None
    if email and user_id:
        settings = get_user_settings(user_id) or {}
        completed_task_ids = settings.get("completed_task_ids") or []
        subject_task_stats = get_subject_task_progress(user_id, subject_id)

    data = data_service.get_dashboard(
        subject_id,
        topic_overrides=topic_overrides,
        stored_topics=stored_topics,
        completed_task_ids=completed_task_ids,
        subject_task_stats=subject_task_stats,
    )
    if not data:
        return jsonify({"error": "Subject not found"}), 404

    if email and user_id:
        progress = get_user_progress(user_id, subject_id)
        if not progress:
            progress = {"score": 0, "score_delta": 0, "chart": []}
        settings = get_user_settings(user_id) or {}
        data["score"] = progress.get("score", 0)
        data["scoreDelta"] = progress.get("score_delta", 0)
        chart_data = progress.get("chart", []) or []
        data["chart"] = [
            {"day": i + 1, "score": int(v) if v is not None else 0}
            for i, v in enumerate(chart_data)
        ]
        data["streak"] = settings.get("streak", 0)
        data["achievements"] = settings.get("achievements", 0)
    return jsonify(data)


@app.get("/api/plan")
def plan():
    subject_id = request.args.get("subjectId") or data_service.get_active_subject_id()
    email = request.args.get("email")
    topic_overrides = None
    stored_topics = None
    if email:
        user = get_user_by_email(email)
        if user:
            topic_overrides = get_topic_progress(user["id"], subject_id)
            stored_topics = get_user_plan_topics(user["id"], subject_id)
    data = data_service.get_plan(
        subject_id,
        topic_overrides=topic_overrides,
        stored_topics=stored_topics,
    )
    if not data:
        return jsonify({"error": "Plan not found"}), 404
    return jsonify(data)


@app.patch("/api/plan/topics/<topic_id>")
def update_plan_topic(topic_id: str):
    body = request.get_json(silent=True) or {}
    email = body.get("email") or request.args.get("email")
    subject_id = body.get("subjectId") or request.args.get("subjectId") or data_service.get_active_subject_id()
    status = (body.get("status") or "").strip()
    progress = body.get("progress")

    if not email:
        return jsonify({"error": "email required"}), 400
    if status not in ("completed", "in-progress", "pending"):
        return jsonify({"error": "status must be completed, in-progress or pending"}), 400

    user = get_user_by_email(email)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        progress_value = int(progress) if progress is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "progress must be a number"}), 400

    set_topic_progress(
        user["id"],
        subject_id,
        topic_id,
        status=status,
        progress=progress_value,
    )
    update_plan_topic_entry(
        user["id"],
        subject_id,
        topic_id,
        status=status,
        progress=progress_value,
    )
    data_service.update_topic_status(
        subject_id,
        topic_id,
        status,
        progress=progress_value,
    )
    plan = data_service.get_plan(
        subject_id,
        topic_overrides=get_topic_progress(user["id"], subject_id),
        stored_topics=get_user_plan_topics(user["id"], subject_id),
    )
    if not plan:
        return jsonify({"error": "Plan not found"}), 404
    return jsonify(plan)


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
    email = body.get("email") or request.args.get("email")
    if answer_id is None:
        return jsonify({"error": "answerId required"}), 400
    result = data_service.check_answer(task_id, int(answer_id))
    if not result:
        return jsonify({"error": "Task not found"}), 404
    if result.get("correct") and email:
        user = get_user_by_email(email)
        if user:
            add_completed_task(user["id"], task_id)
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
    return jsonify(data_service.task_for_client(generated, 1, len(tasks)))


@app.post("/api/chat")
def chat():
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    subject_id = body.get("subjectId") or data_service.get_active_subject_id()
    if not message:
        return jsonify({"error": "message required"}), 400
    
    if not is_ai_available():
        return jsonify(
            {
                "error": (
                    "AI-чат не настроен: добавьте MISTRAL_API_KEY в backend/.env "
                    "и перезапустите backend."
                )
            }
        ), 503

    try:
        subject = data_service.get_subject(subject_id)
        subject_name = subject["name"] if subject else "предмету"
        topics = ", ".join(data_service.get_plan_topics(subject_id)[:6])
        task_context = (body.get("taskContext") or "").strip()
        user_content = (
            f"Предмет: {subject_name}. Темы плана: {topics or 'не заданы'}.\n"
            f"Вопрос студента: {message}"
        )
        if task_context:
            user_content += f"\n\nКонтекст задачи из теста:\n{task_context}"

        reply = chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "Ты AI-репетитор для подготовки к ЕГЭ. Отвечай на русском, "
                        "кратко, понятно и по делу. Если студент просит тест, предложи "
                        "составить диагностику на главной."
                    ),
                },
                {"role": "user", "content": user_content},
            ],
            max_tokens=900,
        )
        return jsonify({"role": "assistant", "content": reply})
    except Exception:
        return jsonify(
            {
                "error": (
                    "AI-чат не смог получить ответ. Проверьте MISTRAL_API_KEY, "
                    "MISTRAL_MODEL и доступ backend к Mistral API."
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

    try:
        if subject_ids and isinstance(subject_ids, list):
            topic = body.get("topic") or "комплексная диагностика"
            count_per_subject = int(body.get("count") or 3)
            for sid in subject_ids:
                ensure_problem_bank(sid)
            return jsonify(
                generate_multi_subject_test(
                    subject_ids,
                    topic=topic,
                    count_per_subject=count_per_subject,
                )
            )

        topic = body.get("topic") or request.args.get("topic") or "диагностика по предмету"
        topic_name = (body.get("topicName") or request.args.get("topicName") or "").strip() or None
        count = int(body.get("count") or request.args.get("count") or 5)
        count = max(1, min(count, 12))
        return jsonify(
            run_generate_test(
                subject_id,
                topic=topic,
                count=count,
                topic_name=topic_name,
            )
        )
    except ProblemBankError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        return jsonify({"error": f"Не удалось составить тест: {exc}"}), 500


@app.post("/api/analyze-test")
def analyze_test():
    body = request.get_json(silent=True) or {}
    email = body.get("email") or request.args.get("email")
    subject_ids = body.get("subjectIds")
    subject_id = body.get("subjectId") or request.args.get("subjectId") or data_service.get_active_subject_id()
    answers = body.get("answers", [])

    if subject_ids and isinstance(subject_ids, list):
        analysis_data = run_multi_analysis(subject_ids, answers)
        user = get_user_by_email(email) if email else None
        if user:
            user_id = user["id"]
            try:
                for sid in subject_ids:
                    subject_answers = [a for a in answers if a.get("subjectId") == sid]
                    if not subject_answers:
                        continue
                    sub_result = run_test_analysis(sid, subject_answers)
                    data_service.update_plan_from_gaps(
                        sid,
                        sub_result.get("gaps", []),
                        sub_result.get("analysis", ""),
                        user_id=user_id,
                    )
                    save_progress_after_test(
                        user_id,
                        sid,
                        int(sub_result.get("examScore") or sub_result.get("score") or 0),
                    )
                    record_test_task_progress(
                        user_id,
                        sid,
                        correct_count=sum(1 for a in subject_answers if a.get("correct")),
                        total_count=len(subject_answers),
                        plan_topic_count=len(get_user_plan_topics(user_id, sid)),
                    )
                update_streak(user_id)
            except Exception:
                pass
        else:
            for sid in subject_ids:
                subject_answers = [a for a in answers if a.get("subjectId") == sid]
                if not subject_answers:
                    continue
                sub_result = run_test_analysis(sid, subject_answers)
                data_service.update_plan_from_gaps(
                    sid,
                    sub_result.get("gaps", []),
                    sub_result.get("analysis", ""),
                )
                data_service.record_test_task_progress(
                    sid,
                    correct_count=sum(1 for a in subject_answers if a.get("correct")),
                    total_count=len(subject_answers),
                    plan_topic_count=0,
                )
        return jsonify(analysis_data)

    subject = data_service.get_subject(subject_id)
    subject_name = subject["name"] if subject else "предмету"

    try:
        analysis_data = run_test_analysis(subject_id, answers, subject_name=subject_name)
    except Exception:
        analysis_data = fallback_analysis(subject_id, subject_name, answers)
        analysis_data["examScore"] = analysis_data.get("score", 0)
        analysis_data["breakdowns"] = []

    user = get_user_by_email(email) if email else None
    data_service.update_plan_from_gaps(
        subject_id,
        analysis_data.get("gaps", []),
        analysis_data.get("analysis", ""),
        user_id=user["id"] if user else None,
    )

    correct_count = sum(1 for a in answers if a.get("correct"))
    total_count = len(answers)
    plan_topic_count = 0
    if user:
        user_id = user["id"]
        plan_topic_count = len(get_user_plan_topics(user_id, subject_id))
        try:
            exam_score = int(analysis_data.get("examScore") or analysis_data.get("score") or 0)
            save_progress_after_test(user_id, subject_id, exam_score)
            update_streak(user_id)
            record_test_task_progress(
                user_id,
                subject_id,
                correct_count=correct_count,
                total_count=total_count,
                plan_topic_count=plan_topic_count,
            )
        except Exception:
            pass
    else:
        data_service.record_test_task_progress(
            subject_id,
            correct_count=correct_count,
            total_count=total_count,
            plan_topic_count=plan_topic_count,
        )

    return jsonify(analysis_data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
