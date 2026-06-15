"""Configurações do StudyAI-AI."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Ambiente (development | staging | production)
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # CORS - origens permitidas (separadas por vírgula). Em produção, listar apenas o BFF.
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    # API key para autenticação serviço-a-serviço (BFF -> StudyAI-AI).
    # Se vazio, não exige autenticação (apenas para dev local).
    llm_api_key: SecretStr = SecretStr("")

    # OpenAI (pago)
    openai_api_key: SecretStr = SecretStr("")

    # Google Gemini (fallback)
    google_api_key: SecretStr = SecretStr("")

    # Ordem dos provedores: "openai,gemini" = tenta OpenAI primeiro, depois Gemini
    llm_providers: str = "openai,gemini"

    # Rate limiting
    rate_limit_chat: str = "60/minute"

    # Host de bind (produção: 127.0.0.1 ou rede Docker interna)
    bind_host: str = "127.0.0.1"
    bind_port: int = 8001

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_production_settings() -> None:
    s = get_settings()
    if s.environment != "production":
        return
    if not s.llm_api_key.get_secret_value().strip():
        raise RuntimeError("LLM_API_KEY é obrigatória em produção")