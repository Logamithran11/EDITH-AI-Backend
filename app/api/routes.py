from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.nvidia_service import nvidia_service

router = APIRouter()

@router.get("/")
async def root():
    return {
        "status": "online",
        "service": "PLANORA EDITH AI Backend",
        "version": "1.0.0",
        "health_check": "/health",
        "nvidia_configured": nvidia_service.is_configured(),
    }

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "EDITH AI Backend",
        "version": "1.0.0",
        "nvidia_configured": nvidia_service.is_configured(),
        "default_model": settings.NVIDIA_MODEL,
    }

@router.get("/api/models")
async def get_models():
    return {
        "default_model": settings.NVIDIA_MODEL,
        "available_candidates": settings.CANDIDATE_MODELS,
    }

@router.post("/api/chat", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="At least one message is required in the chat history.")

    reply, actions, model_used = await nvidia_service.generate_chat_response(
        messages=request.messages,
        model=request.model,
        task_context=request.task_context,
        temperature=request.temperature or 0.3,
        max_tokens=request.max_tokens or 1024,
    )

    return ChatResponse(
        reply=reply,
        actions=actions,
        model=model_used,
        is_live_ai=True,
    )
