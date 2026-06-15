"""Testes de autenticação serviço-a-serviço."""

import secrets

import pytest
from fastapi import HTTPException

from app.core.auth import verify_api_key
from app.config import get_settings


@pytest.mark.asyncio
async def test_compare_digest_rejects_wrong_key(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "super-secret-key")
    get_settings.cache_clear()
    with pytest.raises(HTTPException) as exc:
        await verify_api_key("wrong-key")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_accepts_correct_key(monkeypatch):
    key = "super-secret-key"
    monkeypatch.setenv("LLM_API_KEY", key)
    get_settings.cache_clear()
    await verify_api_key(key)


@pytest.mark.asyncio
async def test_compare_digest_timing_safe():
    a = "a" * 32
    b = "b" * 32
    assert not secrets.compare_digest(a, b)
