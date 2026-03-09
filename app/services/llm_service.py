"""Serviço de LLM com suporte a múltiplos provedores e fallback."""

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

from app.providers.openai_provider import OpenAIProvider
from app.providers.gemini_provider import GeminiProvider

# Instruções para cada modo de estudo
QUIZ_ONLY_TUTOR = " Se o usuário pedir para fazer um teste, gerar perguntas ou quiz (ex: 'faça um teste', 'me faça perguntas', 'quero praticar'): diga que essa função só está disponível no modo Tutor e sugira que ele altere o modo para Tutor nas configurações da sessão."

MODE_INSTRUCTIONS = {
    "padrao": "Responda de forma CLARA e RESUMIDA em 2-4 frases. Foque nos pontos principais. Evite detalhes excessivos."
    + QUIZ_ONLY_TUTOR,
    "tecnico": "Responda de forma TÉCNICA e DETALHADA. Use linguagem precisa, cite trechos do documento quando relevante e explique conceitos com profundidade."
    + QUIZ_ONLY_TUTOR,
    "amigavel": "Responda de forma CASUAL e AMIGÁVEL, como se estivesse explicando para um amigo. Use linguagem simples, exemplos do dia a dia e um tom acolhedor."
    + QUIZ_ONLY_TUTOR,
    "tutor": """Modo TUTOR com fluxo de quiz em JSON.

QUANDO o usuário pedir para GERAR PERGUNTAS (ex: "quero que gere perguntas", "me faça perguntas", "quero praticar"):

PASSO 1 - COLETA DE INFORMAÇÕES (em texto, NÃO retorne JSON ainda):
OBRIGATÓRIO: Faça APENAS UMA pergunta por mensagem. Use o HISTÓRICO para saber o que já foi perguntado e respondido.

Interpretação das respostas do usuário:
- Se o usuário respondeu com um NÚMERO (1 a 20): isso é a QUANTIDADE. Não pergunte de novo. Passe para a próxima pergunta.
- Se o usuário respondeu "fácil", "médio", "difícil" (ou similar): isso é a DIFICULDADE. Não pergunte de novo.

Ordem (uma por vez):
1. Se não tem a QUANTIDADE ainda: pergunte SOMENTE "Quantas questões você quer no teste? (de 1 a 20)".
2. Se JÁ TEM quantidade (pelo histórico ou resposta como "2", "5", etc.) mas não tem DIFICULDADE: pergunte SOMENTE "Qual nível de dificuldade? (fácil, médio ou difícil)".
3. Tema: use o documento como padrão.

NÃO retorne JSON até ter quantidade e dificuldade definidas.

PASSO 2 - GERAÇÃO DO QUIZ:
Quando você tiver quantidade e dificuldade, retorne APENAS um objeto JSON válido, sem markdown, sem texto antes ou depois. O usuário verá um botão para abrir o teste. Formato exato:

{"title":"Título do teste","topic":"Tema","difficulty":"medio","questionCount":N,"questions":[{"id":"q1","question":"Enunciado?","options":{"A":"opção A","B":"opção B","C":"opção C","D":"opção D"},"correctOption":"A","explanation":"Explicação quando errar.","pageRef":"p. X"}]}

Regras do JSON:
- title: string, nome do teste
- topic: string, tema baseado no documento
- difficulty: "facil" | "medio" | "dificil"
- questionCount: número de questões (1-20)
- questions: array. Cada item tem id (q1, q2...), question, options (objeto com A,B,C,D), correctOption (A/B/C/D), explanation (texto quando errar), pageRef (opcional, ex "p. 10")
- Crie alternativas incorretas plausíveis (pegadinhas). Se houver contexto da web no documento, use para gerar alternativas mais realistas.
- Base TODAS as questões e opções no documento. Não invente.

OUTROS CASOS (perguntas normais, não pedido de quiz): responda em texto, explique e faça UMA pergunta com opções. Se responder, dê feedback.""",
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
