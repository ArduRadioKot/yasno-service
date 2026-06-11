"""Premium subscription routes"""

from fastapi import APIRouter, Query, HTTPException, status
from typing import Dict, Any
from schemas import (
    PremiumKeyRequest,
    PremiumActivateRequest,
    PremiumEmailRequest,
    PremiumStatusResponse,
)
from services.db import (
    validate_premium_key,
    activate_premium_key,
    get_user_premium_status,
    get_user_by_email,
)

router = APIRouter(prefix="/api", tags=["premium"])


@router.post("/premium/validate")
async def validate_key(request: PremiumKeyRequest) -> Dict[str, Any]:
    """Validate if a premium key exists and is active"""
    return validate_premium_key(request.key.strip())


@router.post("/premium/activate")
async def activate_key(request: PremiumActivateRequest) -> Dict[str, Any]:
    """Activate a premium key for the current user"""
    email = request.email.strip()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email required to activate premium key",
        )

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = activate_premium_key(request.key.strip(), user["id"])

    if not result.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to activate key"),
        )

    return result


@router.get("/premium/status", response_model=PremiumStatusResponse)
async def get_premium_status(email: str = Query(...)) -> PremiumStatusResponse:
    """Get premium subscription status for a user"""
    user = get_user_by_email(email.strip())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    status_data = get_user_premium_status(user["id"])
    expires_at = status_data.get("expires_at")

    return PremiumStatusResponse(
        is_premium=status_data.get("is_premium", False),
        expires_at=str(expires_at) if expires_at else None,
        days_left=status_data.get("days_left", 0),
        message=status_data.get("message", ""),
    )


@router.post("/premium/check", response_model=PremiumStatusResponse)
async def check_premium(request: PremiumEmailRequest) -> PremiumStatusResponse:
    """Check if user has active premium subscription"""
    email = request.email.strip()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required",
        )

    user = get_user_by_email(email)
    if not user:
        return PremiumStatusResponse(
            is_premium=False,
            days_left=0,
            message="User not found",
        )

    status_data = get_user_premium_status(user["id"])
    expires_at = status_data.get("expires_at")

    return PremiumStatusResponse(
        is_premium=status_data.get("is_premium", False),
        expires_at=str(expires_at) if expires_at else None,
        days_left=status_data.get("days_left", 0),
        message=status_data.get("message", ""),
    )
