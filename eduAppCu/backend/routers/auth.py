"""Authentication routes"""

import os
import jwt
import datetime
from fastapi import APIRouter, HTTPException, status, Header
from schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
    ChangePasswordRequest,
)
from services.db import (
    get_user_by_email,
    create_user,
    get_user_subjects,
    get_user_targets,
)
from services.exam_utils import normalize_exam_type

router = APIRouter(prefix="/api", tags=["auth"])

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


def generate_token(user_id: str, email: str) -> str:
    """Generate JWT token for user"""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(authorization: str = None) -> dict | None:
    """Dependency to get current user from JWT token"""
    if not authorization:
        return None
    
    if authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    else:
        token = authorization
    
    payload = verify_token(token)
    if not payload:
        return None
    
    return get_user_by_email(payload.get("email"))


async def require_auth(authorization: str = None) -> dict:
    """Dependency to require authentication for protected routes"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    if authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    else:
        token = authorization
    
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user = get_user_by_email(payload.get("email"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


@router.get("/user/me", response_model=UserResponse)
async def get_current_user_endpoint(authorization: str | None = Header(None)):
    """Get current user from JWT token"""
    user = await require_auth(authorization)
    
    subjects = get_user_subjects(user["id"])
    targets = get_user_targets(user["id"])
    exam_type = normalize_exam_type(user.get("exam_type"))
    
    return UserResponse(
        email=user["email"],
        firstName=user.get("first_name") or "",
        lastName=user.get("last_name") or "",
        examType=exam_type,
        marketing=bool(user.get("marketing")),
        subjects=subjects,
        targets=targets
    )


@router.post("/user/change-password")
async def change_password(request: ChangePasswordRequest, authorization: str | None = Header(None)):
    """Change user password"""
    user = await require_auth(authorization)
    
    # Verify current password
    if user.get("password") != request.currentPassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Текущий пароль неверен"
        )
    
    # Update password
    try:
        update_user_password(user["id"], request.newPassword)
        return {"message": "Пароль успешно изменён"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при смене пароля"
        )


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
    
    # Generate JWT token
    token = generate_token(str(user["id"]), user["email"])
    
    subjects = get_user_subjects(user["id"])
    targets = get_user_targets(user["id"])
    exam_type = normalize_exam_type(user.get("exam_type"))
    
    return LoginResponse(
        token=token,
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
        # Generate JWT token for new user
        token = generate_token(str(user_id), request.email)
        
        return RegisterResponse(
            token=token,
            userId=user_id,
            message="User created successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
