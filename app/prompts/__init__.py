"""Prompts centralizados para o LLM."""

from app.prompts.chat import (
    ANTI_HALLUCINATION_BASE,
    ANTI_HALLUCINATION_WEB_EXTRA,
    DEPTH_INSTRUCTIONS,
    MODE_INSTRUCTIONS,
    build_chat_prompt,
)
from app.prompts.flashcards import build_flashcards_prompt
from app.prompts.prova import build_prova_prompt

__all__ = [
    "ANTI_HALLUCINATION_BASE",
    "ANTI_HALLUCINATION_WEB_EXTRA",
    "DEPTH_INSTRUCTIONS",
    "MODE_INSTRUCTIONS",
    "build_chat_prompt",
    "build_flashcards_prompt",
    "build_prova_prompt",
]
