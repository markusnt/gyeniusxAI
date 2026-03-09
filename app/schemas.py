"""Modelos de request e response para o chat."""

from typing import Literal

from pydantic import BaseModel, Field


# --- Schema do Quiz (modo tutor estruturado) ---
# Usado quando a IA retorna um quiz em JSON. O BFF valida e persiste.


class QuizQuestion(BaseModel):
    """Uma questão do quiz."""

    id: str = Field(..., description="Identificador único da questão, ex: q1")
    question: str = Field(..., description="Enunciado da pergunta")
    options: dict[str, str] = Field(..., description="Alternativas: {'A': 'texto', 'B': 'texto', ...}")
    correctOption: str = Field(..., description="Letra da opção correta: A, B, C ou D")
    explanation: str = Field(
        default="",
        description="Explicação quando o usuário errar (por que a escolhida está errada e por que a correta está certa)",
    )
    pageRef: str | None = Field(
        default=None,
        description="Referência de página no documento, ex: 'p. 10'",
    )


class QuizSchema(BaseModel):
    """Quiz completo retornado pela IA no modo tutor."""

    title: str = Field(..., description="Título do teste")
    topic: str = Field(default="", description="Tema específico baseado no documento")
    difficulty: Literal["facil", "medio", "dificil"] = Field(
        default="medio",
        description="Nível de dificuldade",
    )
    questionCount: int = Field(..., ge=1, le=20, description="Quantidade de questões")
    questions: list[QuizQuestion] = Field(..., description="Lista de questões")

VALID_MODES = ("padrao", "tecnico", "amigavel", "tutor")
MAX_CONTEXT_LEN = 150_000
MAX_MESSAGE_LEN = 5_000
MAX_HISTORY_LEN = 15_000


class ChatRequest(BaseModel):
    """O que o BFF envia ao StudyAI-AI."""

    context: str = Field(
        ...,
        min_length=1,
        max_length=MAX_CONTEXT_LEN,
        description="Texto dos chunks do documento",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MESSAGE_LEN,
        description="Pergunta do usuário",
    )
    mode: Literal["padrao", "tecnico", "amigavel", "tutor"] = Field(
        default="padrao",
        description="padrao | tecnico | amigavel | tutor",
    )
    depth: Literal["rapido", "normal", "aprofundado"] = Field(
        default="normal",
        description="Profundidade: rapido (1-2 frases) | normal | aprofundado",
    )
    conversation_history: str = Field(
        default="",
        max_length=MAX_HISTORY_LEN,
        description="Histórico recente da conversa (para memória da sessão)",
    )
    has_web_context: bool = Field(
        default=False,
        description="Se True, o contexto inclui resultados da web - priorizar o documento",
    )


class ChatResponse(BaseModel):
    """O que o StudyAI-AI retorna ao BFF."""

    content: str = Field(..., description="Resposta da IA (texto ou JSON bruto)")
    quiz: QuizSchema | None = Field(default=None, description="Quiz estruturado quando o modo tutor retorna JSON")