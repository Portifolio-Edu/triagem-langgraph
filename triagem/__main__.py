"""CLI: python -m triagem "mensagem" mostra o caminho no grafo e a resposta."""

import argparse
import sqlite3
from datetime import datetime

from langgraph.checkpoint.sqlite import SqliteSaver

from triagem.banco import Banco
from triagem.grafo import monta, parado_em_humano, processa, retoma
from triagem.modelo import ModeloFalso


def main() -> None:
    p = argparse.ArgumentParser(
        prog="triagem", description="Triagem de atendimento (dados fictícios)."
    )
    p.add_argument(
        "mensagem", nargs="?", help="texto do cliente; áudio transcrito começa com [audio]"
    )
    p.add_argument("--conversa", default="demo", help="id da conversa (thread do checkpointer)")
    p.add_argument("--banco", default="triagem.sqlite", help="arquivo SQLite de demandas e estado")
    p.add_argument("--retoma", metavar="NOME", help="pessoa que assume a conversa parada em humano")
    p.add_argument("--mermaid", action="store_true", help="imprime o diagrama do grafo e sai")
    a = p.parse_args()

    con = sqlite3.connect(a.banco, check_same_thread=False)
    app = monta(ModeloFalso(), Banco(a.banco), SqliteSaver(con))
    if a.mermaid:
        print(app.get_graph().draw_mermaid())
        return
    if a.retoma:
        final = retoma(app, a.conversa, a.retoma)
    elif a.mensagem is not None:
        final = processa(app, a.conversa, a.mensagem, datetime.now())
    else:
        p.error("informe a mensagem, --retoma ou --mermaid")

    print("caminho:", " -> ".join(final.get("caminho", [])))
    if parado_em_humano(app, a.conversa):
        print(f"parado em humano, protocolo {final.get('protocolo')}: {final['decisao']['motivo']}")
        print(f'para retomar: python -m triagem --conversa {a.conversa} --retoma "Nome"')
        return
    if final.get("cortes"):
        print("cortes do guardrail:", ", ".join(final["cortes"]))
    print("resposta:", final["resposta"])


if __name__ == "__main__":
    main()
