"""Provedor OpenAI - chat com GPT."""

from openai import OpenAI


class OpenAIProvider:
    """Provedor que usa a API da OpenAI para gerar respostas."""

    def __init__(self, api_key: str) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("OPENAI_API_KEY não configurada")
        self._client = OpenAI(api_key=api_key.strip())

    def chat(
        self,
        *,
        prompt: str,
        mode_instruction: str = "",
    ) -> str:
        """Gera resposta usando GPT-4o-mini (ou gpt-4o para mais qualidade)."""
        system_content = (
            "Você é um assistente de estudos. Responda com base no texto do documento fornecido. "
            "Se a pergunta não puder ser respondida com o contexto, diga que não há informações suficientes."
        )

        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        content = response.choices[0].message.content
        return content.strip() if content else "Sem conteúdo na resposta."
