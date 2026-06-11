"""Authentication routes"""

from fastapi import APIRouter, HTTPException, status
from schemas import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse
from services.db import (
    get_user_by_email,
    create_user,
    get_user_subjects,
    get_user_targets,
)
from services.exam_utils import normalize_exam_type

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """User login endpoint"""
    if not request.email or not request.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Введите почту и пароль"
        )
    
    user = get_user_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Аккаунт не найден. Создайте аккаунт"
        )
    
    if user.get("password") != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Почта или пароль не совпадают"
        )
    
    subjects = get_user_subjects(user["id"])
    targets = get_user_targets(user["id"])
    exam_type = normalize_exam_type(user.get("exam_type"))
    
    return LoginResponse(
        email=user["email"],
        firstName=user.get("first_name") or "",
        lastName=user.get("last_name") or "",
        examType=exam_type,
        marketing=bool(user.get("marketing")),
        subjects=subjects,
        targets=targets
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """User registration endpoint"""
    # Validate required fields
    if not request.email or not request.password or not request.firstName or not request.lastName:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields"
        )
    
    # Check if user already exists
    existing_user = get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )
    
    try:
        user_id = create_user(
            email=request.email,
            password=request.password,
            first_name=request.firstName,
            last_name=request.lastName,
            exam_type=request.examType,
            marketing=request.marketing,
            subjects=request.subjects,
            targets=request.targets
        )
        return RegisterResponse(userId=user_id, message="User created successfully")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
