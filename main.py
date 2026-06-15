"""StudyAI-AI - Serviço de LLM para o StudyIA."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings, validate_production_settings
from app.core.exceptions import register_exception_handlers
from app.core.limiter import limiter
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routers import chat, flashcards, prova

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

settings = get_settings()
validate_production_settings()

app = FastAPI(
    title="StudyAI-AI",
    version="0.1.0",
    description="Serviço de IA para chat com documentos.",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# Exception handlers - não expõem detalhes internos
register_exception_handlers(app)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Middleware - ordem: último adicionado = primeiro executado
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(flashcards.router, prefix="/flashcards", tags=["flashcards"])
app.include_router(prova.router, prefix="/prova", tags=["prova"])


@app.get("/")
def root():
    return {"message": "StudyAI-AI está no ar!"}


@app.get("/health")
def health():
    return {"status": "ok"}