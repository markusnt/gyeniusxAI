"""Prompts para geração de flashcards."""

LOCALE_INSTRUCTIONS = {
    "pt-BR": "Use português brasileiro.",
    "en": "Use English.",
    "es": "Use español.",
}

FLASHCARDS_PROMPT_TEMPLATE = """Você é um assistente que cria flashcards para estudo. Com base no texto do documento abaixo, gere {count} flashcards.

TEXTO DO DOCUMENTO:
{context}

INSTRUÇÕES:
- Cada flashcard deve ter uma pergunta (frente) e uma resposta (verso).
- Perguntas claras e diretas. Respostas concisas (1-3 frases).
- Base-se APENAS no texto. Não invente informações.
- Cubra os pontos principais e conceitos importantes.
- {locale_instruction}
- Retorne APENAS um objeto JSON válido, sem markdown, sem texto antes ou depois. Formato exato:

{{"cards":[{{"question":"Pergunta 1?","answer":"Resposta 1."}},{{"question":"Pergunta 2?","answer":"Resposta 2."}}]}}

Gere exatamente {count} cards."""


def build_flashcards_prompt(*, context: str, count: int, locale: str = "pt-BR") -> str:
    """Monta o prompt para geração de flashcards."""
    locale_instruction = LOCALE_INSTRUCTIONS.get(locale, LOCALE_INSTRUCTIONS["pt-BR"])
    return FLASHCARDS_PROMPT_TEMPLATE.format(
        context=context[:50000],
        count=count,
        locale_instruction=locale_instruction,
    )
