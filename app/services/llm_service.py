"""Serviço de LLM com suporte a múltiplos provedores e fallback."""

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


def _deduplicate_response(content: str) -> str:
    """
    Remove duplicações comuns que alguns LLMs produzem (ex: mesmo parágrafo repetido).
    """
    if not content or len(content.strip()) < 50:
        return content
    text = content.strip()
    # Se o conteúdo for exatamente a primeira metade repetida, retorna só a primeira metade
    half = len(text) // 2
    if half > 20 and text[:half].strip() == text[half:].strip():
        logger.info("Removida duplicação detectada (conteúdo idêntico em duas metades)")
        return text[:half].strip()
    # Se houver parágrafos duplicados (ex: mesmo texto repetido)
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(parts) >= 2:
        # Dois parágrafos idênticos?
        if len(parts) == 2 and parts[0] == parts[1] and len(parts[0]) > 30:
            logger.info("Removida duplicação detectada (dois parágrafos idênticos)")
            return parts[0]
        # Sequência repetida (ex: A, B, A, B)?
        mid = len(parts) // 2
        if len(parts) % 2 == 0 and parts[:mid] == parts[mid:]:
            logger.info("Removida duplicação detectada (sequência de parágrafos repetida)")
            return "\n\n".join(parts[:mid])
    return content


from app.providers.openai_provider import OpenAIProvider
from app.providers.gemini_provider import GeminiProvider

# Instruções para cada modo de estudo
MODE_INSTRUCTIONS = {
    "padrao": "Responda de forma CLARA e RESUMIDA em 2-4 frases. Foque nos pontos principais. Evite detalhes excessivos.",
    "tecnico": "Responda de forma TÉCNICA e DETALHADA. Use linguagem precisa, cite trechos do documento quando relevante e explique conceitos com profundidade.",
    "amigavel": "Responda de forma CASUAL e AMIGÁVEL, como se estivesse explicando para um amigo. Use linguagem simples, exemplos do dia a dia e um tom acolhedor.",
    "tutor": """Modo TUTOR com fluxo de quiz:
QUANDO o usuário pedir para fazer perguntas (ex: "me faça perguntas", "quero praticar"):
1. Primeiro pergunte: "Quantas perguntas você gostaria de responder?" e ofereça opções: "1) Uma  2) Duas  3) Três  4) Quatro  5) Cinco"
2. Quando o usuário responder com um número (1, 2, 3, 4 ou 5), gere APENAS UMA pergunta por vez.
3. Formato de cada pergunta: múltipla escolha "A) opção B) opção C) opção" ou "Verdadeiro ou falso: afirmação". Referência de página no fim: (Essa informação está na p. X.)
4. Após cada resposta do usuário, envie a PRÓXIMA pergunta (uma só) até completar a quantidade. NÃO dê feedback intermediário.
5. Ao final (após a última resposta), dê o feedback de todas as respostas: indique corretas/incorretas e explique brevemente.
6. Se o usuário quiser sair do quiz e voltar a digitar, ele pode clicar em "Voltar ao chat" - nesse caso apenas confirme que pode continuar digitando normalmente.

OUTROS CASOS (perguntas normais, não pedido de quiz): explique, dê exemplo e faça UMA pergunta com opções. Se o usuário responder, dê feedback e explique.""",
}

# Profundidade: controla o tamanho/detalhe da resposta
DEPTH_INSTRUCTIONS = {
    "rapido": "Resposta MUITO CURTA: 1-2 frases apenas. Apenas o essencial.",
    "normal": "Resposta de tamanho médio: organize em parágrafos curtos (2-4 frases por parágrafo).",
    "aprofundado": "Resposta DETALHADA: organize em parágrafos bem definidos. Cada ideia em um parágrafo.",
}

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

    history_block = ""
    if conversation_history and conversation_history.strip():
        history_block = f"""
HISTÓRICO RECENTE DA CONVERSA (o que já foi discutido - use para não repetir e para dar continuidade):
{conversation_history.strip()}

"""

    anti_hallucination_rules = """REGRAS ANTI-ALUCINAÇÃO (OBRIGATÓRIAS):
1. NÃO afirme nada sem suporte explícito nos trechos do documento acima.
2. Se faltar evidência: admita ("não há informações sobre isso no documento") e sugira reformular ou especificar a pergunta.
3. Cite SEMPRE a página quando responder (ex: "Conforme a p. 5..." ou "Isso aparece na p. 12").
4. Se a pergunta for ambígua, pergunte de volta (ex: "Você quer a parte teórica ou exemplos do texto?").
5. NÃO complete lacunas com achismos ou informações que não estejam nos trechos.
6. Separe claramente: o que vem DO DOCUMENTO (cite a página) vs sua INTERPRETAÇÃO/EXPLICAÇÃO (diga "Em outras palavras..." ou "Isso significa que...").
7. Se usar analogias ou exemplos para ensinar, marque como "Por exemplo," ou "Analogamente," — NUNCA apresente como se fosse trecho do PDF.
8. Se houver conflito ou inconsistência entre trechos do documento, aponte e mostre onde aparece cada versão.
9. Resumo deve ser fiel ao texto, cobrindo os pontos principais, sem "melhorar" ou adicionar o que não está lá."""
    if has_web_context:
        anti_hallucination_rules += """

REGRAS QUANDO HOUVER INFORMAÇÕES DA WEB (OBRIGATÓRIO):
10. A resposta deve ser PRIMARIAMENTE baseada no DOCUMENTO. Use a web APENAS para complementar.
11. Se a pergunta NÃO for sobre o conteúdo do documento/vídeo de estudo, responda: "Sua pergunta não parece estar relacionada ao material de estudo. Por favor, faça perguntas sobre o conteúdo do documento ou vídeo."
12. NUNCA responda apenas com informações da web ignorando o documento. O estudo é o contexto principal."""

    prompt = f"""Você é um assistente de estudos. O usuário está estudando um documento.

TEXTO DO DOCUMENTO (cada trecho tem [p. X] = página, ou [p. X, Seção] quando houver):
{context}

{anti_hallucination_rules}

ESTILO DE RESPOSTA: {mode_instruction}

PROFUNDIDADE: {depth_instruction}
{history_block}
PERGUNTA DO USUÁRIO:
{message}

FORMATAÇÃO: Use quebras de linha para organizar a resposta. Separe ideias em parágrafos (deixe uma linha em branco entre parágrafos). Isso facilita a leitura.

Responda com base nos trechos, citando as páginas e separando fatos do documento de sua explicação."""

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
            return _deduplicate_response(result)
        except Exception as e:
            logger.warning("Provedor %s falhou: %s", name, type(e).__name__)
            last_error = e
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Nenhum provedor de LLM disponível. Configure OPENAI_API_KEY ou GOOGLE_API_KEY.")
