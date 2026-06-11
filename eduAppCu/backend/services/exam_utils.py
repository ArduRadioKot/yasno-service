"""Утилиты для ЕГЭ (баллы) и ОГЭ (оценка 2–5)."""

EXAM_EGE = "ЕГЭ"
EXAM_OGE = "ОГЭ"


def normalize_exam_type(value: str | None) -> str:
    if not value:
        return EXAM_EGE
    normalized = str(value).strip().upper()
    if normalized in ("ОГЭ", "OGE"):
        return EXAM_OGE
    return EXAM_EGE


def is_oge(exam_type: str | None) -> bool:
    return normalize_exam_type(exam_type) == EXAM_OGE


def percent_to_oge_grade(percent: int) -> int:
    """Прогноз оценки ОГЭ (2–5) по доле правильных ответов."""
    percent = max(0, min(100, int(percent)))
    if percent < 25:
        return 2
    if percent < 50:
        return 3
    if percent < 75:
        return 4
    return 5


def predict_exam_result(
    subject_id: str,
    percent: int,
    *,
    exam_type: str = EXAM_EGE,
) -> int:
    if is_oge(exam_type):
        return percent_to_oge_grade(percent)
    base = round(percent * 0.9)
    from services.data_service import data_service

    subject = data_service.get_subject(subject_id)
    max_score = subject.get("targetScore", 100) if subject else 100
    return max(0, min(int(base), int(max_score)))


def exam_score_label(exam_type: str | None) -> str:
    return "оценка" if is_oge(exam_type) else "баллов"


def exam_forecast_title(exam_type: str | None) -> str:
    return "Прогноз ОГЭ" if is_oge(exam_type) else "Прогноз ЕГЭ"


def normalize_target_score(score: int | float | None, exam_type: str | None) -> int:
    """Цель пользователя: оценка 2–5 для ОГЭ, баллы 0–100 для ЕГЭ."""
    if score is None:
        return 4 if is_oge(exam_type) else 80
    value = int(round(float(score)))
    if is_oge(exam_type):
        if 2 <= value <= 5:
            return value
        return percent_to_oge_grade(value)
    return max(0, min(100, value))


def score_to_progress_percent(current: int, target: int, exam_type: str | None) -> int:
    """Convert exam score/grade to 0–100 progress toward target."""
    current = int(current or 0)
    target = int(target or 0)
    if is_oge(exam_type):
        if target <= 2:
            return 0
        return max(0, min(100, round((current - 2) / (target - 2) * 100)))
    if target <= 0:
        return 0
    return max(0, min(100, round(current / target * 100)))


def ai_exam_prompt(exam_type: str | None) -> str:
    if is_oge(exam_type):
        return (
            "Ты репетитор ОГЭ. Оценка только по шкале 2, 3, 4 или 5. "
            "В JSON укажи examScore числом от 2 до 5."
        )
    return "Ты репетитор ЕГЭ. Прогноз балла на экзамен от 0 до 100."
