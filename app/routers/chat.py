"""Rota de chat - recebe context + message, retorna resposta da IA."""

import json
import logging
import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.core.auth import verify_api_key
from app.core.limiter import limiter
from app.schemas import ChatRequest, ChatResponse, QuizSchema
from app.services.llm_service import chat_with_context, chat_with_context_stream

logger = logging.getLogger(__name__)

router = APIRouter()


def _try_parse_quiz(content: str) -> QuizSchema | None:
    """Tenta extrair e validar quiz JSON da resposta do LLM."""
    text = content.strip()
    if not text:
        return None

    # 1. Tenta bloco markdown ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()

    # 2. Se ainda parece texto antes do JSON, extrai o primeiro objeto { ... }
    if not text.startswith("{"):
        start = text.find("{")
        if start >= 0:
            depth, end = 0, start
            for i, c in enumerate(text[start:], start):
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if depth == 0:
                text = text[start : end + 1]

    try:
        data = json.loads(text)
        return QuizSchema.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None


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
    No modo tutor, quando a IA retorna quiz em JSON, inclui quiz estruturado.
    """
    content = chat_with_context(
        context=data.context,
        message=data.message,
        mode=data.mode,
        depth=data.depth,
        conversation_history=data.conversation_history or "",
        has_web_context=data.has_web_context,
        locale=data.locale,
    )
    quiz = None
    if data.mode == "tutor":
        quiz = _try_parse_quiz(content)
        if quiz:
            logger.info("Quiz estruturado detectado: %s (%d questões)", quiz.title, quiz.questionCount)
    return ChatResponse(content=content, quiz=quiz)


def _stream_chat(data: ChatRequest):
    """Generator: yields SSE events with content chunks."""
    try:
        for chunk in chat_with_context_stream(
            context=data.context,
            message=data.message,
            mode=data.mode,
            depth=data.depth,
            conversation_history=data.conversation_history or "",
            has_web_context=data.has_web_context,
            locale=data.locale,
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    except Exception:
        logger.exception("Erro no stream")
        yield f"data: {json.dumps({'error': 'Erro interno no serviço de IA'})}\n\n"


@router.post(
    "/stream",
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(get_settings().rate_limit_chat)
def chat_stream(request: Request, data: ChatRequest):
    """Retorna resposta em streaming (SSE) para efeito de digitação."""
    return StreamingResponse(
        _stream_chat(data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )