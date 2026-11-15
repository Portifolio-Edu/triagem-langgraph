import sqlite3
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from triagem.banco import Banco
from triagem.grafo import monta, parado_em_humano, processa, retoma
from triagem.modelo import ModeloFalso

SEGUNDA_10H = datetime(2026, 11, 16, 10, 0)


def test_fluxo_inteiro_resolve_sozinho() -> None:
    app = monta(ModeloFalso(), Banco(), InMemorySaver())
    final = processa(app, "c1", "Preciso da guia do imposto", SEGUNDA_10H)
    assert final["caminho"] == ["normaliza", "classifica", "decide", "registra", "redige", "valida"]
    assert (
        final["resposta"]
        == "Pedido registrado com o protocolo EX-00001, setor Fiscal. Prazo: 16/11 às 14h00."
    )
    assert final["cortes"] == []


def test_mensagem_nova_na_mesma_conversa_zera_o_estado() -> None:
    app = monta(ModeloFalso(), Banco(), InMemorySaver())
    processa(app, "c1", "Quero cancelar, isso é um absurdo", SEGUNDA_10H)
    retoma(app, "c1", "Ana")
    final = processa(app, "c1", "Preciso da guia do imposto", SEGUNDA_10H)
    assert final["responsavel"] is None
    assert "humano" not in final["caminho"]


def test_interrompe_e_retoma_depois_de_reiniciar(tmp_path: Path) -> None:
    arquivo = str(tmp_path / "triagem.sqlite")

    def app_novo():  # type: ignore[no-untyped-def]
        con = sqlite3.connect(arquivo, check_same_thread=False)
        return monta(ModeloFalso(), Banco(arquivo), SqliteSaver(con))

    primeiro = app_novo()
    parcial = processa(primeiro, "c9", "Quero reclamar do atendimento", SEGUNDA_10H)
    assert parcial["caminho"][-1] == "registra"
    assert parado_em_humano(primeiro, "c9")

    # Outro processo, mesmo arquivo: o checkpointer devolve a conversa parada.
    segundo = app_novo()
    assert parado_em_humano(segundo, "c9")
    final = retoma(segundo, "c9", "Carla")
    assert final["caminho"][-3:] == ["humano", "redige", "valida"]
    assert final["resposta"] == (
        "Pedido registrado com o protocolo EX-00001. "
        "Carla, do setor Atendimento, assumiu o atendimento."
    )
    assert not parado_em_humano(segundo, "c9")


def test_diagrama_mermaid_tem_todos_os_nos() -> None:
    mermaid = monta(ModeloFalso(), Banco()).get_graph().draw_mermaid()
    for no in ("normaliza", "classifica", "decide", "registra", "humano", "redige", "valida"):
        assert no in mermaid
