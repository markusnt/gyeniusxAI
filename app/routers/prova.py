"""Rota para gerar prova (modo prova) via LLM."""

from fastapi import APIRouter, Depends, Request

from app.config import get_settings
from app.core.auth import verify_api_key
from app.core.limiter import limiter
from app.schemas import ProvaRequest, QuizSchema
from app.services.llm_service import generate_prova

router = APIRouter()


@router.post("/generate", response_model=QuizSchema, dependencies=[Depends(verify_api_key)])
@limiter.limit(get_settings().rate_limit_chat)
def generate(request: Request, data: ProvaRequest) -> QuizSchema:
    """Gera uma prova a partir do contexto do documento."""
    result = generate_prova(
        context=data.context,
        count=data.count,
        difficulty=data.difficulty,
        question_types=data.question_types,
        locale=data.locale,
    )
    return QuizSchema.model_validate(result)
