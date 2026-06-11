"""Test routes"""

from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional, List, Dict, Any
from schemas import GenerateTestRequest, AnalyzeTestRequest, AnswerSubmission
from services.data_service import data_service
from services.db import (
    get_user_by_email,
    get_user_progress,
    upsert_user_progress,
    update_user_settings,
    get_user_settings,
    get_subject_task_progress,
    record_test_task_progress,
    get_user_plan_topics,
)
from services.problem_bank_service import ProblemBankError, ensure_problem_bank
from services.test_service import (
    _answer_field,
    _serialize_answers,
    analyze_multi_subject_test as run_multi_analysis,
    analyze_test as run_test_analysis,
    generate_multi_subject_test,
    generate_test as run_generate_test,
)
from services.exam_utils import (
    normalize_exam_type,
    predict_exam_result,
    is_oge,
)
import datetime

router = APIRouter(prefix="/api", tags=["tests"])


def resolve_exam_type(body: dict | None = None, email: str | None = None) -> str:
    """Resolve exam type from body or user settings"""
    body = body or {}
    if body.get("examType"):
        return normalize_exam_type(body.get("examType"))
    if email:
        user = get_user_by_email(email)
        if user and user.get("exam_type"):
            return normalize_exam_type(user["exam_type"])
    return "ЕГЭ"


def fallback_analysis(
    subject_id: str,
    subject_name: str,
    answers: list,
    exam_type: str = "ЕГЭ",
):
    """Fallback analysis when AI service is not available"""
    exam_type = normalize_exam_type(exam_type)
    total = len(answers)
    answers = _serialize_answers(answers)
    correct_count = sum(1 for a in answers if _answer_field(a, "correct", False))
    score = round((correct_count / total) * 100) if total else 0
    wrong_topics = [
        _answer_field(a, "topic", "") or _answer_field(a, "question", "Тема вопроса")
        for a in answers
        if not _answer_field(a, "correct", False)
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
    exam_score = predict_exam_result(subject_id, score, exam_type=exam_type)
    return {
        "analysis": analysis,
        "gaps": gaps,
        "score": score,
        "examScore": exam_score,
        "examType": exam_type,
        "level": level,
        "breakdowns": [],
    }


def save_progress_after_test(user_id: int, subject_id: str, exam_score: int, score_delta_base: int | None = None):
    """Save progress after test completion"""
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
    """Update user streak"""
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


@router.post("/generate-test")
async def generate_test(request: GenerateTestRequest) -> Dict[str, Any]:
    """Generate a test"""
    email = request.email
    exam_type = resolve_exam_type({"examType": request.examType}, email)
    subject_ids = request.subjectIds
    subject_id = (
        request.subjectId
        or data_service.get_active_subject_id()
    )
    
    try:
        if subject_ids and isinstance(subject_ids, list):
            topic = request.topic or "комплексная диагностика"
            count_per_subject = int(request.count or 3)
            for sid in subject_ids:
                ensure_problem_bank(sid, exam_type=exam_type)
            return generate_multi_subject_test(
                subject_ids,
                topic=topic,
                count_per_subject=count_per_subject,
                exam_type=exam_type,
            )
        
        topic = request.topic or "диагностика по предмету"
        topic_name = (request.topicName or "").strip() or None
        count = int(request.count or 5)
        count = max(1, min(count, 12))
        ensure_problem_bank(subject_id, exam_type=exam_type)
        return run_generate_test(
            subject_id,
            topic=topic,
            count=count,
            topic_name=topic_name,
            exam_type=exam_type,
        )
    except ProblemBankError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось составить тест: {exc}"
        )


@router.post("/analyze-test")
async def analyze_test(request: AnalyzeTestRequest) -> Dict[str, Any]:
    """Analyze test results"""
    email = request.email
    subject_ids = request.subjectIds
    subject_id = request.subjectId or data_service.get_active_subject_id()
    answers = _serialize_answers(request.answers)

    exam_type = resolve_exam_type({"examType": request.examType}, email)
    
    if subject_ids and isinstance(subject_ids, list):
        analysis_data = run_multi_analysis(subject_ids, answers, exam_type=exam_type)
        user = get_user_by_email(email) if email else None
        if user:
            user_id = user["id"]
            try:
                for sid in subject_ids:
                    subject_answers = [a for a in answers if _answer_field(a, "subjectId", "") == sid]
                    if not subject_answers:
                        continue
                    sub_result = run_test_analysis(
                        sid, subject_answers, exam_type=exam_type
                    )
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
                        correct_count=sum(1 for a in subject_answers if _answer_field(a, "correct", False)),
                        total_count=len(subject_answers),
                        plan_topic_count=len(get_user_plan_topics(user_id, sid)),
                    )
                update_streak(user_id)
            except Exception:
                pass
        else:
            for sid in subject_ids:
                subject_answers = [a for a in answers if _answer_field(a, "subjectId", "") == sid]
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
                    correct_count=sum(1 for a in subject_answers if getattr(a, "correct", False)),
                    total_count=len(subject_answers),
                    plan_topic_count=0,
                )
        return analysis_data
    
    subject = data_service.get_subject(subject_id)
    subject_name = subject["name"] if subject else "предмету"
    
    try:
        analysis_data = run_test_analysis(
            subject_id, answers, subject_name=subject_name, exam_type=exam_type
        )
    except Exception:
        analysis_data = fallback_analysis(
            subject_id, subject_name, answers, exam_type=exam_type
        )
        analysis_data["examScore"] = analysis_data.get("score", 0)
        analysis_data["breakdowns"] = []
    
    user = get_user_by_email(email) if email else None
    data_service.update_plan_from_gaps(
        subject_id,
        analysis_data.get("gaps", []),
        analysis_data.get("analysis", ""),
        user_id=user["id"] if user else None,
    )
    
    correct_count = sum(1 for a in answers if _answer_field(a, "correct", False))
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
    
    return analysis_data
