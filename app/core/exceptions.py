"""Exception handlers globais - não expõe detalhes internos."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import get_settings

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc):
    """Handler para HTTPException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para erros de validação Pydantic."""
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = first_error.get("msg", "Dados inválidos")
    field = ".".join(str(loc) for loc in first_error.get("loc", []) if loc != "body")
    detail = f"{field}: {msg}" if field else msg
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail},
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handler para exceções não tratadas - não expõe detalhes internos."""
    settings = get_settings()
    logger.exception("Erro não tratado: %s", type(exc).__name__)
    detail = "Erro interno do servidor"
    if settings.debug:
        detail = str(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos os exception handlers."""
    from fastapi import HTTPException

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
