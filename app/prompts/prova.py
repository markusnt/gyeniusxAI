"""Prompts para geração de provas (modo prova)."""

PROVA_PROMPT_TEMPLATE = """Você é um assistente que cria provas e simulados para estudo. Com base no texto do documento abaixo, gere uma prova com {count} questões de múltipla escolha.

TEXTO DO DOCUMENTO:
{context}

INSTRUÇÕES:
- Nível de dificuldade: {difficulty} (facil = conceitos básicos, medio = aplicação, dificil = análise e síntese).
- Cada questão deve ter enunciado claro, 4 alternativas (A, B, C, D), apenas uma correta.
- Crie alternativas incorretas plausíveis (pegadinhas). Base TODAS as questões e opções no documento.
- Inclua explanation (por que a resposta está errada quando errar) e pageRef (página do documento) quando possível.
- Use português.
- Retorne APENAS um objeto JSON válido, sem markdown, sem texto antes ou depois. Formato exato:

{{"title":"Prova: [tema do documento]","topic":"Tema baseado no documento","difficulty":"{difficulty}","questionCount":{count},"questions":[{{"id":"q1","question":"Enunciado da questão 1?","options":{{"A":"opção A","B":"opção B","C":"opção C","D":"opção D"}},"correctOption":"A","explanation":"Explicação quando errar.","pageRef":"p. X"}}]}}

Gere exatamente {count} questões."""


def build_prova_prompt(*, context: str, count: int = 10, difficulty: str = "medio") -> str:
    """Monta o prompt para geração de prova."""
    return PROVA_PROMPT_TEMPLATE.format(
        context=context[:80000],
        count=count,
        difficulty=difficulty,
    )
