"""Chat routes"""

from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional, List, Dict, Any
from schemas import ChatRequest, ChatResponse, ChatSuggestionsResponse, PromptSuggestion
from services.data_service import data_service
from services.ai_client import chat_completion, is_ai_available
from services.db import is_user_premium_by_email

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint for AI assistance"""
    subject_id = request.subjectId or data_service.get_active_subject_id()
    message = (request.message or "").strip()
    email = (request.email or "").strip()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message required"
        )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email required for AI chat",
        )

    if not is_user_premium_by_email(email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "AI-чат доступен только с премиум подпиской. "
                "Активируйте ключ в профиле или получите его через Telegram-бота."
            ),
        )
    
    if not is_ai_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "AI-чат не настроен: добавьте MISTRAL_API_KEY в backend/.env "
                "и перезапустите backend."
            )
        )
    
    try:
        subject = data_service.get_subject(subject_id)
        subject_name = subject["name"] if subject else "предмету"
        topics = ", ".join(data_service.get_plan_topics(subject_id)[:6])
        task_context = (request.taskContext or "").strip()
        user_content = (
            f"Предмет: {subject_name}. Темы плана: {topics or 'не заданы'}.\n"
            f"Вопрос студента: {message}"
        )
        if task_context:
            user_content += f"\n\nКонтекст задачи из теста:\n{task_context}"
        
        reply = chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "Ты AI-репетитор для подготовки к ЕГЭ. Отвечай на русском, "
                        "кратко, понятно и по делу. Если студент просит тест, предложи "
                        "составить диагностику на главной."
                    ),
                },
                {"role": "user", "content": user_content},
            ],
            max_tokens=900,
        )
        return ChatResponse(role="assistant", content=reply)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "AI-чат не смог получить ответ. Проверьте MISTRAL_API_KEY, "
                "MISTRAL_MODEL и доступ backend к Mistral API."
            )
        )


@router.get("/chat/suggestions", response_model=ChatSuggestionsResponse)
async def chat_suggestions(subjectId: Optional[str] = Query(None)):
    """Get chat suggestions"""
    subject_id = subjectId or data_service.get_active_subject_id()
    subject = data_service.get_subject(subject_id)
    name = subject["name"] if subject else "предмету"
    
    return ChatSuggestionsResponse(
        prompts=[
            PromptSuggestion(text="Объясни проще", icon="book"),
            PromptSuggestion(text=f"Разбери задачу по {name}", icon="question"),
            PromptSuggestion(text="Составь мини тест", icon="zap"),
        ]
    )
