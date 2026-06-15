"""Autenticação serviço-a-serviço (BFF -> StudyAI-AI)."""

import secrets

from fastapi import Header, HTTPException, status

from app.config import get_settings


async def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    """
    Se LLM_API_KEY estiver configurada, exige X-API-Key no header.
    Em produção, LLM_API_KEY é obrigatória (validada no startup).
    """
    settings = get_settings()
    expected = settings.llm_api_key.get_secret_value()
    if not expected or not expected.strip():
        if settings.environment == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Serviço de IA não configurado",
            )
        return
    if not x_api_key or not secrets.compare_digest(x_api_key.strip(), expected.strip()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida ou ausente",
        )
