"""Pydantic models for request/response validation"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    email: str
    firstName: str
    lastName: str
    examType: str
    marketing: bool
    subjects: List[str]
    targets: Dict[str, int]


class RegisterRequest(BaseModel):
    email: str
    password: str
    firstName: str
    lastName: str
    examType: str = "ЕГЭ"
    marketing: bool = False
    subjects: List[str] = []
    targets: Dict[str, int] = {}


class RegisterResponse(BaseModel):
    token: str
    userId: int
    message: str


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str


class UserResponse(BaseModel):
    email: str
    firstName: str
    lastName: str
    examType: str
    marketing: bool
    subjects: List[str]
    targets: Dict[str, int]


class SubjectResponse(BaseModel):
    id: str
    name: str
    targetScore: Optional[int] = None


class SubjectsListResponse(BaseModel):
    subjects: List[Dict[str, Any]]
    activeSubjectId: str
    examType: str


class SetSubjectRequest(BaseModel):
    subjectId: str


class SetSubjectResponse(BaseModel):
    subject: Dict[str, Any]
    activeSubjectId: str


class UpdatePlanTopicRequest(BaseModel):
    email: Optional[str] = None
    subjectId: Optional[str] = None
    status: str
    progress: Optional[int] = None


class TaskCheckRequest(BaseModel):
    answerId: int
    email: Optional[str] = None


class GenerateTaskRequest(BaseModel):
    subjectId: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = "medium"


class ChatRequest(BaseModel):
    message: str
    subjectId: Optional[str] = None
    taskContext: Optional[str] = None
    email: Optional[str] = None


class PremiumKeyRequest(BaseModel):
    key: str


class PremiumActivateRequest(BaseModel):
    key: str
    email: str


class PremiumEmailRequest(BaseModel):
    email: str


class PremiumStatusResponse(BaseModel):
    is_premium: bool
    expires_at: Optional[str] = None
    days_left: int = 0
    message: str = ""


class ChatResponse(BaseModel):
    role: str
    content: str


class PromptSuggestion(BaseModel):
    text: str
    icon: str


class ChatSuggestionsResponse(BaseModel):
    prompts: List[PromptSuggestion]


class AnswerSubmission(BaseModel):
    correct: bool
    topic: Optional[str] = None
    question: Optional[str] = None
    subjectId: Optional[str] = None


class GenerateTestRequest(BaseModel):
    email: Optional[str] = None
    examType: Optional[str] = None
    subjectIds: Optional[List[str]] = None
    subjectId: Optional[str] = None
    topic: Optional[str] = None
    topicName: Optional[str] = None
    count: Optional[int] = 5


class AnalyzeTestRequest(BaseModel):
    email: Optional[str] = None
    examType: Optional[str] = None
    subjectIds: Optional[List[str]] = None
    subjectId: Optional[str] = None
    answers: List[AnswerSubmission] = []


class ErrorResponse(BaseModel):
    error: str


class HealthResponse(BaseModel):
    status: str
