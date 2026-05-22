import json
from typing import Any

from services.ai_client import chat_json, is_ai_available
from services.data_service import data_service
from services.exam_utils import (
    ai_exam_prompt,
    is_oge,
    normalize_exam_type,
    percent_to_oge_grade,
    predict_exam_result,
)
from services.problem_bank_service import get_problems_for_test


def _fallback_mcq(problem: dict) -> dict:
    answer = problem.get("answer") or "Правильный ответ"
    return {
        "problemId": problem.get("external_id"),
        "topic": problem.get("topic") or "Тема",
        "question": problem.get("condition") or "Вопрос",
        "answers": [
            answer,
            "Ответ не соответствует условию",
            "Нужно другое правило или формула",
            "Недостаточно данных в условии",
        ],
        "correctIndex": 0,
        "solution": problem.get("solution") or "",
    }


def _build_single_mcq_with_ai(
    problem: dict, subject_name: str, exam_type: str = "ЕГЭ"
) -> dict:
    if not is_ai_available():
        return _fallback_mcq(problem)

    exam_label = "ОГЭ" if is_oge(exam_type) else "ЕГЭ"
    try:
        data = chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        f"Ты репетитор {exam_label}. Реши задачу из банка и сформируй тестовый вопрос "
                        "с 4 вариантами ответа (один верный). Только JSON, русский язык."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""Предмет: {subject_name}.
Задача из банка sdamgia:
{json.dumps({
    "id": problem.get("external_id"),
    "topic": problem.get("topic"),
    "condition": problem.get("condition"),
    "solution": problem.get("solution"),
    "answer": problem.get("answer"),
}, ensure_ascii=False)}

Формат:
{{
  "problemId": "id",
  "topic": "тема",
  "question": "вопрос",
  "answers": ["а", "б", "в", "г"],
  "correctIndex": 0,
  "solution": "решение"
}}""",
                },
            ],
            max_tokens=700,
        )
        answers = data.get("answers", [])
        correct_index = data.get("correctIndex", 0)
        if (
            data.get("question")
            and isinstance(answers, list)
            and len(answers) >= 2
            and isinstance(correct_index, int)
            and 0 <= correct_index < len(answers)
        ):
            return {
                "problemId": data.get("problemId") or problem.get("external_id"),
                "topic": data.get("topic") or problem.get("topic"),
                "question": data["question"],
                "answers": [str(a) for a in answers[:4]],
                "correctIndex": correct_index,
                "solution": data.get("solution") or problem.get("solution") or "",
            }
    except Exception:
        pass
    return _fallback_mcq(problem)


def _build_mcq_with_ai(
    problems: list[dict], subject_name: str, exam_type: str = "ЕГЭ"
) -> list[dict]:
    return [
        _build_single_mcq_with_ai(problem, subject_name, exam_type=exam_type)
        for problem in problems
    ]


def _normalize_exam_score_value(value: Any, exam_type: str, subject_id: str, percent: int) -> int:
    if is_oge(exam_type):
        try:
            grade = int(value)
        except (TypeError, ValueError):
            grade = percent_to_oge_grade(percent)
        return max(2, min(5, grade))
    return predict_exam_result(subject_id, percent, exam_type=exam_type)


def generate_test(
    subject_id: str,
    *,
    topic: str = "диагностика",
    count: int = 5,
    topic_name: str | None = None,
    exam_type: str = "ЕГЭ",
) -> dict:
    subject = data_service.get_subject(subject_id)
    subject_name = subject["name"] if subject else subject_id
    exam_type = normalize_exam_type(exam_type)
    count = max(1, min(int(count), 12))
    filter_name = (topic_name or "").strip() or None

    bank_problems = get_problems_for_test(
        subject_id,
        count,
        topic_filter=filter_name,
        exam_type=exam_type,
    )
    questions = _build_mcq_with_ai(bank_problems, subject_name, exam_type=exam_type)

    if filter_name:
        for question in questions:
            question["topic"] = filter_name

    label = topic or (
        f"Тест по теме «{filter_name}» · {subject_name}"
        if filter_name
        else f"Диагностика по предмету {subject_name}"
    )

    return {
        "topic": label,
        "subjectId": subject_id,
        "topicName": filter_name,
        "examType": exam_type,
        "questions": questions,
        "questionCount": len(questions),
    }


def generate_multi_subject_test(
    subject_ids: list[str],
    *,
    topic: str = "комплексная диагностика",
    count_per_subject: int = 3,
    exam_type: str = "ЕГЭ",
) -> dict:
    all_questions = []
    subjects_info = []
    count_per_subject = max(2, min(count_per_subject, 6))

    for subject_id in subject_ids:
        subject = data_service.get_subject(subject_id)
        if not subject:
            continue
        test = generate_test(
            subject_id,
            topic=topic,
            count=count_per_subject,
            exam_type=exam_type,
        )
        for question in test.get("questions", []):
            question["subjectId"] = subject_id
            all_questions.append(question)
        plan_topics = data_service.get_plan_topics(subject_id)[:3]
        subjects_info.append(f"{subject['name']}: {', '.join(plan_topics) or 'ключевые темы'}")

    return {
        "topic": f"Комплексная диагностика по {len(subject_ids)} предметам",
        "questions": all_questions,
        "subjects": subjects_info,
        "subjectIds": subject_ids,
        "examType": normalize_exam_type(exam_type),
    }


def _local_score(answers: list[dict]) -> dict:
    total = len(answers)
    correct_count = sum(1 for a in answers if a.get("correct"))
    percent = round((correct_count / total) * 100) if total else 0
    level = "сильный" if percent >= 80 else "средний" if percent >= 50 else "начальный"
    return {
        "correctCount": correct_count,
        "total": total,
        "percent": percent,
        "level": level,
    }


def analyze_test(
    subject_id: str,
    answers: list[dict],
    *,
    subject_name: str | None = None,
    exam_type: str = "ЕГЭ",
) -> dict:
    subject = data_service.get_subject(subject_id)
    subject_name = subject_name or (subject["name"] if subject else "предмету")
    stats = _local_score(answers)
    wrong = [a for a in answers if not a.get("correct")]
    gaps = list(
        dict.fromkeys(
            str(a.get("topic") or "").strip()
            for a in wrong
            if str(a.get("topic") or "").strip()
        )
    )

    exam_type = normalize_exam_type(exam_type)
    exam_score = predict_exam_result(subject_id, stats["percent"], exam_type=exam_type)
    exam_name = "ОГЭ" if is_oge(exam_type) else "ЕГЭ"
    score_hint = "оценка 2–5" if is_oge(exam_type) else "балл 0–100"
    breakdowns = []

    if is_ai_available():
        try:
            result = chat_json(
                [
                    {
                        "role": "system",
                        "content": (
                            f"{ai_exam_prompt(exam_type)} Проанализируй тест, посчитай прогноз ({score_hint}), "
                            "укажи слабые темы и краткие разборы ошибок. Только JSON, русский язык."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"""Предмет: {subject_name}.
Результаты:
{json.dumps(answers, ensure_ascii=False)}

Формат:
{{
  "analysis": "краткий анализ и рекомендации",
  "gaps": ["тема1", "тема2"],
  "score": 75,
  "examScore": 68,
  "level": "начальный|средний|сильный",
  "breakdowns": [
    {{
      "question": "текст вопроса",
      "topic": "тема",
      "explanation": "почему ошибка и как решать",
      "chatPrompt": "готовый промпт для чата с ИИ по этой задаче"
    }}
  ]
}}""",
                    },
                ],
                max_tokens=1500,
            )
            if isinstance(result.get("gaps"), list):
                ai_gaps = [str(g).strip() for g in result["gaps"] if str(g).strip()]
                gaps = list(dict.fromkeys(ai_gaps + gaps))[:8]
            exam_score = _normalize_exam_score_value(
                result.get("examScore") or result.get("score") or exam_score,
                exam_type,
                subject_id,
                stats["percent"],
            )
            score_percent = int(result.get("score") or stats["percent"])
            level = result.get("level") or stats["level"]
            analysis_text = result.get("analysis") or ""
            raw_breakdowns = result.get("breakdowns", [])
            if isinstance(raw_breakdowns, list):
                breakdowns = raw_breakdowns
            return {
                "analysis": analysis_text
                or (
                    f"Результат: {stats['correctCount']} из {stats['total']} "
                    f"({stats['percent']}%). Прогноз на {exam_name}: {exam_score} "
                    f"{'(оценка)' if is_oge(exam_type) else 'баллов'}."
                ),
                "gaps": gaps[:8],
                "score": score_percent,
                "examScore": exam_score,
                "examType": exam_type,
                "level": level,
                "breakdowns": breakdowns,
            }
        except Exception:
            pass

    for item in wrong:
        breakdowns.append(
            {
                "question": item.get("question"),
                "topic": item.get("topic"),
                "explanation": (
                    f"Правильный ответ: {item.get('correctAnswer')}. "
                    f"Ваш ответ: {item.get('selectedAnswer')}. "
                    "Повторите правило темы и разберите похожий пример."
                ),
                "chatPrompt": (
                    f"Разбери подробно задачу по теме «{item.get('topic')}»: "
                    f"{item.get('question')}. Мой ответ: {item.get('selectedAnswer')}. "
                    f"Правильный: {item.get('correctAnswer')}."
                ),
            }
        )

    return {
        "analysis": (
            f"Результат по «{subject_name}»: {stats['correctCount']} из {stats['total']} "
            f"({stats['percent']}%). Прогноз на {exam_name}: {exam_score} "
            f"{'(оценка)' if is_oge(exam_type) else 'баллов'}. Уровень: {stats['level']}."
        ),
        "gaps": gaps[:8],
        "score": stats["percent"],
        "examScore": exam_score,
        "examType": exam_type,
        "level": stats["level"],
        "breakdowns": breakdowns,
    }


def analyze_multi_subject_test(
    subject_ids: list[str], answers: list[dict], *, exam_type: str = "ЕГЭ"
) -> dict:
    all_gaps = []
    analyses = []
    exam_scores = []
    breakdowns = []

    for subject_id in subject_ids:
        subject = data_service.get_subject(subject_id)
        if not subject:
            continue
        subject_answers = [a for a in answers if a.get("subjectId") == subject_id]
        if not subject_answers and len(subject_ids) == 1:
            subject_answers = answers
        if not subject_answers:
            continue

        result = analyze_test(
            subject_id,
            subject_answers,
            subject_name=subject["name"],
            exam_type=exam_type,
        )
        all_gaps.extend(result.get("gaps", []))
        analyses.append(f"{subject['name']}: {result.get('analysis', '')}")
        exam_scores.append(result.get("examScore", result.get("score", 0)))
        for item in result.get("breakdowns", []):
            item["subjectId"] = subject_id
            breakdowns.append(item)

    exam_type = normalize_exam_type(exam_type)
    avg_score = round(sum(exam_scores) / len(exam_scores)) if exam_scores else 0
    if is_oge(exam_type):
        avg_score = max(2, min(5, avg_score))
    percent = round(sum(a.get("correct", False) for a in answers) / len(answers) * 100) if answers else 0
    if is_oge(exam_type):
        level = (
            "сильный"
            if avg_score >= 5
            else "средний"
            if avg_score >= 4
            else "начальный"
        )
    else:
        level = "сильный" if avg_score >= 80 else "средний" if avg_score >= 50 else "начальный"
    unique_gaps = list(dict.fromkeys(all_gaps))
    forecast_label = "оценка" if is_oge(exam_type) else "баллов"

    return {
        "analysis": (
            f"Комплексный результат по {len(subject_ids)} предметам. "
            f"Средний прогноз: {avg_score} {forecast_label}. " + " ".join(analyses)
        ),
        "gaps": unique_gaps[:10],
        "score": percent,
        "examScore": avg_score,
        "examType": exam_type,
        "level": level,
        "breakdowns": breakdowns,
        "subjects": analyses,
    }
