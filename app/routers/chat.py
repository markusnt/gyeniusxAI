"""Rota de chat - recebe context + message, retorna resposta da IA."""

import logging

from fastapi import APIRouter, Depends, Request

from app.config import get_settings
from app.core.auth import verify_api_key
from app.core.limiter import limiter
from app.schemas import ChatRequest, ChatResponse
from app.services.llm_service import chat_with_context

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=ChatResponse,
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(get_settings().rate_limit_chat)
def chat(request: Request, data: ChatRequest) -> ChatResponse:
    """
    Recebe contexto do documento + pergunta do usuário.
    Retorna resposta gerada pelo LLM.
    Exception handlers globais tratam erros sem expor detalhes internos.
    """
    content = chat_with_context(
        context=data.context,
        message=data.message,
        mode=data.mode,
        depth=data.depth,
        conversation_history=data.conversation_history or "",
        has_web_context=data.has_web_context,
    )
    return ChatResponse(content=content)