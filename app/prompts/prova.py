"""Prompts para geração de provas (modo prova)."""

LOCALE_INSTRUCTIONS = {
    "pt-BR": "Use português brasileiro.",
    "en": "Use English.",
    "es": "Use español.",
}

TYPE_LABELS = {
    "multiple_choice": "múltipla escolha",
    "fill_blank": "preencher lacuna",
    "true_false": "verdadeiro ou falso",
}

PROVA_PROMPT_TEMPLATE = """Você é um assistente que cria provas e simulados para estudo. Com base no texto do documento abaixo, gere uma prova com {count} questões.

TEXTO DO DOCUMENTO:
{context}

INSTRUÇÕES:
- Nível de dificuldade: {difficulty} (facil = conceitos básicos, medio = aplicação, dificil = análise e síntese).
- Tipos de questão permitidos nesta prova: {types_description}.
- Distribua as {count} questões entre os tipos selecionados de forma equilibrada.
- Base TODAS as questões no documento. {locale_instruction}
- Inclua explanation (por que a resposta está errada quando errar) e pageRef (página do documento) quando possível.

FORMATOS POR TIPO:
1) multiple_choice: enunciado + 4 alternativas (A, B, C, D), apenas uma correta. options com as 4 opções, correctOption com a letra.
2) fill_blank: enunciado com lacuna (use ___ no texto). options = {{}}. correctOption = resposta exata da lacuna (sem espaços extras).
3) true_false: enunciado afirmativo. options = {{"A": "Verdadeiro", "B": "Falso"}}. correctOption = "A" ou "B".

Retorne APENAS um objeto JSON válido, sem markdown. Formato exato:

{{"title":"Prova: [tema]","topic":"Tema","difficulty":"{difficulty}","questionCount":{count},"questions":[{{"id":"q1","type":"multiple_choice","question":"Enunciado?","options":{{"A":"a","B":"b","C":"c","D":"d"}},"correctOption":"A","explanation":"...","pageRef":"p. 1"}}]}}

Gere exatamente {count} questões. Cada questão deve ter o campo "type" correspondente."""


def build_prova_prompt(
    *,
    context: str,
    count: int = 10,
    difficulty: str = "medio",
    question_types: list[str] | None = None,
    locale: str = "pt-BR",
) -> str:
    """Monta o prompt para geração de prova."""
    types = question_types or ["multiple_choice"]
    labels = [TYPE_LABELS.get(t, t) for t in types]
    types_description = ", ".join(labels)
    locale_instruction = LOCALE_INSTRUCTIONS.get(locale, LOCALE_INSTRUCTIONS["pt-BR"])
    return PROVA_PROMPT_TEMPLATE.format(
        context=context[:80000],
        count=count,
        difficulty=difficulty,
        types_description=types_description,
        locale_instruction=locale_instruction,
    )
