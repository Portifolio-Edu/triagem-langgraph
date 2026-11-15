"""O grafo: cada nó faz uma coisa e devolve só o que mudou no estado."""

from datetime import datetime
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from triagem import regras
from triagem.banco import Banco
from triagem.estado import Classificacao, Estado, entrada
from triagem.guardrail import valida
from triagem.modelo import Modelo
from triagem.texto import limpa

MARCA_AUDIO = "[audio]"


def formata_prazo(vencimento: str | None) -> str:
    if not vencimento:
        return "a definir pela equipe"
    return datetime.fromisoformat(vencimento).strftime("%d/%m às %Hh%M")


def monta(
    modelo: Modelo, banco: Banco, checkpointer: BaseCheckpointSaver[Any] | None = None
) -> CompiledStateGraph[Estado, None, Estado, Estado]:
    def passo(state: Estado, nome: str) -> list[str]:
        return [*state["caminho"], nome]

    def normaliza(state: Estado) -> dict[str, Any]:
        bruto = limpa(state["mensagem"])
        origem = "texto"
        # Áudio chega já transcrito, com a marca de origem na frente.
        if bruto.lower().startswith(MARCA_AUDIO):
            origem, bruto = "audio", limpa(bruto[len(MARCA_AUDIO) :])
        mudou: dict[str, Any] = {
            "texto": bruto,
            "origem": origem,
            "caminho": passo(state, "normaliza"),
        }
        if not bruto:
            mudou["evento"] = "vazia"
        return mudou

    def classifica(state: Estado) -> dict[str, Any]:
        c = modelo.classifica(state["texto"])
        return {"classificacao": c.model_dump(), "caminho": passo(state, "classifica")}

    def decide(state: Estado) -> dict[str, Any]:
        c = Classificacao.model_validate(state["classificacao"])
        recebido = datetime.fromisoformat(state["recebido_em"])
        decisao = regras.decide(c.tipo, c.setor, c.confianca, recebido)
        return {"decisao": decisao, "caminho": passo(state, "decide")}

    def registra(state: Estado) -> dict[str, Any]:
        c = Classificacao.model_validate(state["classificacao"])
        decisao = state["decisao"]
        assert decisao is not None
        if c.tipo == "consulta_status":
            # Pergunta de andamento não abre demanda: responde só com o que está registrado.
            r = banco.ultima_aberta(state["conversa_id"], c.setor)
            if r is None:
                sem_base = {**decisao, "para_humano": True, "motivo": "consulta sem demanda"}
                return {
                    "evento": "consulta_sem_demanda",
                    "decisao": sem_base,
                    "caminho": passo(state, "registra"),
                }
        else:
            r = banco.registra(
                state["conversa_id"],
                c.setor,
                c.tipo,
                state["texto"],
                decisao["vencimento"],
                state["recebido_em"],
            )
        return {
            "protocolo": r.protocolo,
            "evento": r.evento,
            "resumo": r.resumo,
            "decisao": {**decisao, "vencimento": r.vencimento},
            "caminho": passo(state, "registra"),
        }

    def humano(state: Estado) -> dict[str, Any]:
        decisao = state["decisao"]
        assert decisao is not None
        # O grafo para aqui e grava o estado. Volta com Command(resume=...) quando a pessoa assume.
        resposta = interrupt(
            {
                "protocolo": state["protocolo"],
                "setor": decisao["setor"],
                "motivo": decisao["motivo"],
                "texto": state["texto"],
            }
        )
        nome = resposta if isinstance(resposta, str) else resposta.get("responsavel")
        return {"responsavel": nome or "Uma pessoa", "caminho": passo(state, "humano")}

    def redige(state: Estado) -> dict[str, Any]:
        decisao = state["decisao"]
        contexto: dict[str, object] = {
            "protocolo": state["protocolo"],
            "setor": decisao["setor"] if decisao else None,
            "prazo": formata_prazo(decisao["vencimento"] if decisao else None),
            "evento": state["evento"],
            "responsavel": state["responsavel"],
            "resumo": state["resumo"],  # só o resumo desta conversa
        }
        return {"rascunho": modelo.redige(contexto), "caminho": passo(state, "redige")}

    def valida_no(state: Estado) -> dict[str, Any]:
        resposta, cortes = valida(state["rascunho"], state["protocolo"])
        return {"resposta": resposta, "cortes": cortes, "caminho": passo(state, "valida")}

    def depois_de_normaliza(state: Estado) -> str:
        return "redige" if state["evento"] == "vazia" else "classifica"

    def depois_de_registra(state: Estado) -> str:
        if state["evento"] == "repetido":
            return "redige"
        decisao = state["decisao"]
        return "humano" if decisao and decisao["para_humano"] else "redige"

    g = StateGraph(Estado)
    g.add_node("normaliza", normaliza)
    g.add_node("classifica", classifica)
    g.add_node("decide", decide)
    g.add_node("registra", registra)
    g.add_node("humano", humano)
    g.add_node("redige", redige)
    g.add_node("valida", valida_no)
    g.add_edge(START, "normaliza")
    g.add_conditional_edges("normaliza", depois_de_normaliza, ["classifica", "redige"])
    g.add_edge("classifica", "decide")
    g.add_edge("decide", "registra")
    g.add_conditional_edges("registra", depois_de_registra, ["humano", "redige"])
    g.add_edge("humano", "redige")
    g.add_edge("redige", "valida")
    g.add_edge("valida", END)
    return g.compile(checkpointer=checkpointer)


def _config(conversa_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": conversa_id}}


def processa(app: Any, conversa_id: str, mensagem: str, recebido_em: datetime) -> dict[str, Any]:
    """Uma mensagem, uma volta no grafo. A conversa é o thread do checkpointer."""
    estado = entrada(conversa_id, mensagem, recebido_em.isoformat())
    return dict(app.invoke(estado, _config(conversa_id)))


def retoma(app: Any, conversa_id: str, responsavel: str) -> dict[str, Any]:
    return dict(app.invoke(Command(resume={"responsavel": responsavel}), _config(conversa_id)))


def parado_em_humano(app: Any, conversa_id: str) -> bool:
    return "humano" in app.get_state(_config(conversa_id)).next
