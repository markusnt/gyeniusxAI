"""Autenticação serviço-a-serviço (BFF -> StudyAI-AI)."""

from fastapi import Header, HTTPException, status

from app.config import get_settings


async def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    """
    Se LLM_API_KEY estiver configurada, exige X-API-Key no header.
    Se vazia, não exige (apenas para dev local).
    """
    settings = get_settings()
    expected = settings.llm_api_key.get_secret_value()
    if not expected or not expected.strip():
        return
    if not x_api_key or x_api_key.strip() != expected.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida ou ausente",
        )
