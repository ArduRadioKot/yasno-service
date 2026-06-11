"""Plan routes"""

from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional, Dict, Any
from schemas import UpdatePlanTopicRequest
from services.data_service import data_service
from services.exam_utils import normalize_exam_type
from services.db import (
    get_user_by_email,
    get_user_settings,
    get_topic_progress,
    get_user_plan_topics,
    get_user_plan_meta,
    get_user_targets,
    set_topic_progress,
    update_plan_topic_entry,
    get_user_progress,
)

router = APIRouter(prefix="/api", tags=["plan"])


@router.get("/dashboard")
async def dashboard(
    subjectId: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    examType: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Get dashboard data for a subject"""
    subject_id = subjectId or data_service.get_active_subject_id()
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
        from services.db import get_subject_task_progress
        subject_task_stats = get_subject_task_progress(user_id, subject_id)
    
    from services.exam_utils import (
        normalize_exam_type,
        exam_score_label,
        exam_forecast_title,
        is_oge,
    )
    
    exam_type = "ЕГЭ"
    if examType:
        exam_type = normalize_exam_type(examType)
    elif email:
        user = get_user_by_email(email)
        if user and user.get("exam_type"):
            exam_type = normalize_exam_type(user["exam_type"])
    
    data = data_service.get_dashboard(
        subject_id,
        topic_overrides=topic_overrides,
        stored_topics=stored_topics,
        completed_task_ids=completed_task_ids,
        subject_task_stats=subject_task_stats,
        exam_type=exam_type,
    )
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found"
        )
    
    data["examType"] = exam_type
    data["scoreLabel"] = exam_score_label(exam_type)
    data["forecastTitle"] = exam_forecast_title(exam_type)
    
    if is_oge(exam_type):
        data["score"] = max(2, min(5, int(data.get("score", 0))))
        data["scoreDelta"] = max(-3, min(3, int(data.get("scoreDelta", 0))))
    
    if email and user_id:
        progress = get_user_progress(user_id, subject_id)
        if not progress:
            progress = {"score": 0, "score_delta": 0, "chart": []}
        settings = get_user_settings(user_id) or {}
        data["score"] = progress.get("score", 0)
        data["scoreDelta"] = progress.get("score_delta", 0)
        chart_data = progress.get("chart", []) or []
        if not chart_data and progress.get("score"):
            chart_data = [progress.get("score")]
        data["chart"] = [
            {"day": i + 1, "score": int(v) if v is not None else 0}
            for i, v in enumerate(chart_data)
        ]
        data["streak"] = settings.get("streak", 0)
        data["achievements"] = settings.get("achievements", 0)
    
    return data


@router.get("/plan")
async def plan(
    subjectId: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    examType: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Get plan for a subject"""
    subject_id = subjectId or data_service.get_active_subject_id()
    topic_overrides = None
    stored_topics = None
    plan_meta = None
    current_score = None
    target_score = None
    exam_type = "ЕГЭ"

    if email:
        user = get_user_by_email(email)
        if user:
            user_id = user["id"]
            topic_overrides = get_topic_progress(user_id, subject_id)
            stored_topics = get_user_plan_topics(user_id, subject_id)
            plan_meta = get_user_plan_meta(user_id, subject_id)
            progress = get_user_progress(user_id, subject_id)
            if progress:
                current_score = progress.get("score", 0)
            user_targets = get_user_targets(user_id)
            if subject_id in user_targets:
                target_score = user_targets[subject_id]
            if examType:
                exam_type = normalize_exam_type(examType)
            elif user.get("exam_type"):
                exam_type = normalize_exam_type(user["exam_type"])

    data = data_service.get_plan(
        subject_id,
        topic_overrides=topic_overrides,
        stored_topics=stored_topics,
        plan_meta=plan_meta,
        current_score=current_score,
        target_score=target_score,
        exam_type=exam_type,
    )
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )

    from services.exam_utils import is_oge

    if is_oge(exam_type):
        data["currentScore"] = max(2, min(5, int(data.get("currentScore", 0))))
    
    return data


@router.patch("/plan/topics/{topic_id}")
async def update_plan_topic(
    topic_id: str,
    request: UpdatePlanTopicRequest,
    email: Optional[str] = Query(None),
    subjectId: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Update plan topic status"""
    email = request.email or email
    subject_id = request.subjectId or subjectId or data_service.get_active_subject_id()
    status = (request.status or "").strip()
    progress = request.progress
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email required"
        )
    
    if status not in ("completed", "in-progress", "pending"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be completed, in-progress or pending"
        )
    
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        progress_value = int(progress) if progress is not None else None
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="progress must be a number"
        )
    
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
    
    user_id = user["id"]
    plan_meta = get_user_plan_meta(user_id, subject_id)
    progress_row = get_user_progress(user_id, subject_id)
    current_score = progress_row.get("score", 0) if progress_row else None
    user_targets = get_user_targets(user_id)
    target_score = user_targets.get(subject_id)
    exam_type = normalize_exam_type(user.get("exam_type") or "ЕГЭ")

    plan_data = data_service.get_plan(
        subject_id,
        topic_overrides=get_topic_progress(user_id, subject_id),
        stored_topics=get_user_plan_topics(user_id, subject_id),
        plan_meta=plan_meta,
        current_score=current_score,
        target_score=target_score,
        exam_type=exam_type,
    )
    
    if not plan_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    return plan_data
