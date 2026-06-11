"""Subjects routes"""

from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional
from schemas import SubjectsListResponse, SetSubjectRequest, SetSubjectResponse
from services.data_service import data_service
from services.db import get_user_by_email, get_user_subjects, get_user_targets
from services.exam_utils import normalize_exam_type, normalize_target_score

router = APIRouter(prefix="/api", tags=["subjects"])


@router.get("/subjects", response_model=SubjectsListResponse)
async def list_subjects(email: Optional[str] = Query(None)):
    """Get list of subjects"""
    active = data_service.get_active_subject_id()
    
    # If email provided, filter subjects by user's selection
    if email:
        user = get_user_by_email(email)
        if user:
            user_subjects = get_user_subjects(user["id"])
            user_targets = get_user_targets(user["id"])
            all_subjects = data_service.get_subjects()
            exam_type = normalize_exam_type(user.get("exam_type"))
            filtered_subjects = []
            
            for s in all_subjects:
                if s["id"] not in user_subjects:
                    continue
                subject = dict(s)
                if s["id"] in user_targets:
                    subject["targetScore"] = normalize_target_score(
                        user_targets[s["id"]], exam_type
                    )
                filtered_subjects.append(subject)
            
            return SubjectsListResponse(
                subjects=filtered_subjects,
                activeSubjectId=active,
                examType=exam_type
            )
    
    return SubjectsListResponse(
        subjects=data_service.get_subjects(),
        activeSubjectId=active,
        examType="ЕГЭ"
    )


@router.put("/user/subject", response_model=SetSubjectResponse)
async def set_subject(request: SetSubjectRequest):
    """Set active subject"""
    if not request.subjectId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="subjectId required"
        )
    
    subject = data_service.set_active_subject(request.subjectId)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found"
        )
    
    return SetSubjectResponse(subject=subject, activeSubjectId=request.subjectId)
