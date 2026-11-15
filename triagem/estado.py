from typing import Literal, TypedDict

from pydantic import BaseModel, Field

Setor = Literal["fiscal", "pessoal", "contabil", "societario", "atendimento"]
Origem = Literal["texto", "audio"]


class Classificacao(BaseModel):
    """Saída estruturada do modelo. É o único ponto em que o modelo opina."""

    tipo: str
    setor: Setor
    confianca: float = Field(ge=0, le=1)


class Decisao(TypedDict):
    setor: Setor
    prazo_horas: int | None
    vencimento: str | None
    para_humano: bool
    motivo: str


class Estado(TypedDict):
    conversa_id: str
    mensagem: str
    recebido_em: str
    origem: Origem
    texto: str
    classificacao: dict[str, object] | None
    decisao: Decisao | None
    protocolo: str | None
    evento: str | None
    resumo: list[str]
    responsavel: str | None
    rascunho: str
    resposta: str
    cortes: list[str]
    caminho: list[str]


def entrada(conversa_id: str, mensagem: str, recebido_em: str) -> Estado:
    """Estado inicial completo. Cada mensagem zera os campos, mesmo na mesma conversa."""
    return Estado(
        conversa_id=conversa_id,
        mensagem=mensagem,
        recebido_em=recebido_em,
        origem="texto",
        texto="",
        classificacao=None,
        decisao=None,
        protocolo=None,
        evento=None,
        resumo=[],
        responsavel=None,
        rascunho="",
        resposta="",
        cortes=[],
        caminho=[],
    )
