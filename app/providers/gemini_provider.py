"""Provedor Google Gemini - chat com modelo generativo."""

from collections.abc import Iterator

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold


SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}


class GeminiProvider:
    """Provedor que usa a API do Google Gemini para gerar respostas."""

    def __init__(self, api_key: str) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("GOOGLE_API_KEY não configurada")
        genai.configure(api_key=api_key.strip())

    def chat(
        self,
        *,
        prompt: str,
        mode_instruction: str = "",
    ) -> str:
        """Gera resposta usando Gemini. Usa o prompt completo (já montado)."""
        # gemini-1.5-flash foi descontinuado; usar modelos atuais
        model_names = ["gemini-2.5-flash", "gemini-2.0-flash"]
        response = None
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(
                    model_name,
                    safety_settings=SAFETY_SETTINGS,
                )
                response = model.generate_content(prompt)
                break
            except Exception as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    continue
                raise
        if response is None:
            raise RuntimeError(
                f"Nenhum modelo Gemini disponível. Tentados: {model_names}"
            )

        if not response.candidates:
            return "Não foi possível gerar uma resposta. Tente reformular a pergunta."
        try:
            return response.text or "Sem conteúdo na resposta."
        except ValueError:
            return "A resposta foi bloqueada pelos filtros de segurança. Tente reformular a pergunta."

    def chat_stream(
        self,
        *,
        prompt: str,
        mode_instruction: str = "",
    ) -> Iterator[str]:
        """Gera resposta em streaming, token a token."""
        model_names = ["gemini-2.5-flash", "gemini-2.0-flash"]
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(
                    model_name,
                    safety_settings=SAFETY_SETTINGS,
                )
                stream = model.generate_content(prompt, stream=True)
                for chunk in stream:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    continue
                raise
        raise RuntimeError(f"Nenhum modelo Gemini disponível. Tentados: {model_names}")
