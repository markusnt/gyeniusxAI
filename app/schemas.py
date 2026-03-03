"""Modelos de request e response para o chat."""

from typing import Literal

from pydantic import BaseModel, Field

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

    content: str = Field(..., description="Resposta da IA")