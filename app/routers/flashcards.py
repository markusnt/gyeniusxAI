"""Rota para gerar flashcards via LLM."""

from fastapi import APIRouter, Depends, Request

from app.config import get_settings
from app.core.auth import verify_api_key
from app.core.limiter import limiter
from app.schemas import FlashcardsRequest, FlashcardsResponse, FlashcardItem
from app.services.llm_service import generate_flashcards

router = APIRouter()


@router.post("/generate", response_model=FlashcardsResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit(get_settings().rate_limit_chat)
def generate(request: Request, data: FlashcardsRequest) -> FlashcardsResponse:
    """Gera flashcards a partir do contexto do documento."""
    cards = generate_flashcards(context=data.context, count=data.count, locale=data.locale)
    return FlashcardsResponse(
        cards=[FlashcardItem(question=c["question"], answer=c["answer"]) for c in cards]
    )
