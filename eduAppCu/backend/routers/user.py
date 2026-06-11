"""User routes"""

from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional
from schemas import UserResponse
from services.data_service import data_service
from services.db import get_user_by_email, get_user_settings

router = APIRouter(prefix="/api", tags=["user"])


@router.get("/user", response_model=UserResponse)
async def get_user(email: Optional[str] = Query(None)):
    """Get current user information"""
    if email:
        user = get_user_by_email(email)
        if user:
            settings = get_user_settings(user["id"]) or {}
            return UserResponse(
                userName=f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                activeSubjectId=settings.get("active_subject_id") or data_service.get_active_subject_id(),
                completedTaskIds=settings.get("completed_task_ids", [])
            )
    
    return UserResponse(
        userName=data_service.user["userName"],
        activeSubjectId=data_service.get_active_subject_id(),
        completedTaskIds=data_service.user["completedTaskIds"]
    )
