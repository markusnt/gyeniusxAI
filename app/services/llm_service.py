"""Serviço de LLM com suporte a múltiplos provedores e fallback."""

import json
import logging
import re

from app.config import get_settings
from app.prompts import (
    DEPTH_INSTRUCTIONS,
    MODE_INSTRUCTIONS,
    build_chat_prompt,
    build_flashcards_prompt,
    build_prova_prompt,
)
from app.providers.openai_provider import OpenAIProvider
from app.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)

PROVIDERS = {
    "openai": lambda: OpenAIProvider(get_settings().openai_api_key.get_secret_value()),
    "gemini": lambda: GeminiProvider(get_settings().google_api_key.get_secret_value()),
}


def chat_with_context(
    *,
    context: str,
    message: str,
    mode: str = "padrao",
    depth: str = "normal",
    conversation_history: str = "",
    has_web_context: bool = False,
) -> str:
    """
    Envia contexto + mensagem ao LLM. Suporta memória da sessão, controle de profundidade e modo tutor.
    """
    settings = get_settings()
    mode_instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["padrao"])
    depth_instruction = DEPTH_INSTRUCTIONS.get(depth, DEPTH_INSTRUCTIONS["normal"])
    prompt = build_chat_prompt(
        context=context,
        message=message,
        mode_instruction=mode_instruction,
        depth_instruction=depth_instruction,
        conversation_history=conversation_history,
        has_web_context=has_web_context,
    )
    provider_names = [p.strip().lower() for p in settings.llm_providers.split(",") if p.strip()]
    if not provider_names:
        provider_names = ["openai", "gemini"]
    last_error: Exception | None = None
    for name in provider_names:
        if name not in PROVIDERS:
            logger.warning("Provedor desconhecido: %s", name)
            continue
        try:
            provider = PROVIDERS[name]()
            result = provider.chat(prompt=prompt, mode_instruction=mode_instruction)
            logger.info("Resposta gerada pelo provedor: %s", name)
            return result
        except Exception as e:
            logger.warning("Provedor %s falhou: %s", name, type(e).__name__)
            last_error = e
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Nenhum provedor de LLM disponível. Configure OPENAI_API_KEY ou GOOGLE_API_KEY.")


def chat_with_context_stream(
    *,
    context: str,
    message: str,
    mode: str = "padrao",
    depth: str = "normal",
    conversation_history: str = "",
    has_web_context: bool = False,
):
    """
    Igual a chat_with_context, mas gera chunks em streaming (generator).
    """
    settings = get_settings()
    mode_instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["padrao"])
    depth_instruction = DEPTH_INSTRUCTIONS.get(depth, DEPTH_INSTRUCTIONS["normal"])
    prompt = build_chat_prompt(
        context=context,
        message=message,
        mode_instruction=mode_instruction,
        depth_instruction=depth_instruction,
        conversation_history=conversation_history,
        has_web_context=has_web_context,
    )
    provider_names = [p.strip().lower() for p in settings.llm_providers.split(",") if p.strip()]
    if not provider_names:
        provider_names = ["openai", "gemini"]

    last_error: Exception | None = None
    for name in provider_names:
        if name not in PROVIDERS:
            logger.warning("Provedor desconhecido: %s", name)
            continue
        try:
            provider = PROVIDERS[name]()
            yield from provider.chat_stream(prompt=prompt, mode_instruction=mode_instruction)
            logger.info("Resposta em streaming pelo provedor: %s", name)
            return
        except Exception as e:
            logger.warning("Provedor %s falhou (stream): %s", name, type(e).__name__)
            last_error = e
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Nenhum provedor de LLM disponível. Configure OPENAI_API_KEY ou GOOGLE_API_KEY.")


def generate_flashcards(*, context: str, count: int = 10) -> list[dict]:
    """
    Gera flashcards a partir do contexto do documento.
    Retorna lista de {"question": str, "answer": str}.
    """
    prompt = build_flashcards_prompt(context=context, count=count)

    provider_names = [p.strip().lower() for p in get_settings().llm_providers.split(",") if p.strip()]
    if not provider_names:
        provider_names = ["openai", "gemini"]

    last_error: Exception | None = None
    for name in provider_names:
        if name not in PROVIDERS:
            continue
        try:
            provider = PROVIDERS[name]()
            result = provider.chat(prompt=prompt, mode_instruction="")
            text = result.strip()
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                text = match.group(1).strip()
            if not text.startswith("{"):
                start = text.find("{")
                if start >= 0:
                    brace_depth, end = 0, start
                    for i, c in enumerate(text[start:], start):
                        if c == "{":
                            brace_depth += 1
                        elif c == "}":
                            brace_depth -= 1
                            if brace_depth == 0:
                                end = i
                                break
                    if brace_depth == 0:
                        text = text[start : end + 1]
            data = json.loads(text)
            cards = data.get("cards", data.get("flashcards", []))
            if not isinstance(cards, list):
                cards = []
            return [{"question": c.get("question", ""), "answer": c.get("answer", "")} for c in cards if c.get("question") and c.get("answer")][:count]
        except Exception as e:
            logger.warning("Provedor %s falhou (flashcards): %s", name, e)
            last_error = e
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Nenhum provedor de LLM disponível.")


def generate_prova(*, context: str, count: int = 10, difficulty: str = "medio") -> dict:
    """
    Gera uma prova (quiz) a partir do contexto do documento.
    Retorna dict no formato QuizSchema: {title, topic, difficulty, questionCount, questions}.
    """
    prompt = build_prova_prompt(context=context, count=count, difficulty=difficulty)

    provider_names = [p.strip().lower() for p in get_settings().llm_providers.split(",") if p.strip()]
    if not provider_names:
        provider_names = ["openai", "gemini"]

    last_error: Exception | None = None
    for name in provider_names:
        if name not in PROVIDERS:
            continue
        try:
            provider = PROVIDERS[name]()
            result = provider.chat(prompt=prompt, mode_instruction="")
            text = result.strip()
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                text = match.group(1).strip()
            if not text.startswith("{"):
                start = text.find("{")
                if start >= 0:
                    brace_depth, end = 0, start
                    for i, c in enumerate(text[start:], start):
                        if c == "{":
                            brace_depth += 1
                        elif c == "}":
                            brace_depth -= 1
                            if brace_depth == 0:
                                end = i
                                break
                    if brace_depth == 0:
                        text = text[start : end + 1]
            data = json.loads(text)
            from app.schemas import QuizSchema
            validated = QuizSchema.model_validate(data)
            return validated.model_dump()
        except Exception as e:
            logger.warning("Provedor %s falhou (prova): %s", name, e)
            last_error = e
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Nenhum provedor de LLM disponível.")
