"""Bateria de replay: casos de borda em JSONL, rodando o grafo inteiro sem chamar modelo."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from triagem.banco import Banco
from triagem.grafo import monta, parado_em_humano, processa, retoma
from triagem.modelo import ModeloGravado

CASOS = [
    json.loads(linha) for linha in (Path(__file__).parent / "casos.jsonl").open(encoding="utf-8")
]
SEGUNDA_10H = "2026-11-16T10:00:00"


def test_bateria_tem_casos_suficientes() -> None:
    assert len(CASOS) >= 18


@pytest.mark.parametrize("caso", CASOS, ids=[c["id"] for c in CASOS])
def test_caso(caso: dict[str, Any]) -> None:
    banco = Banco()
    modelo = ModeloGravado(None)
    app = monta(modelo, banco, InMemorySaver())
    recebido = datetime.fromisoformat(caso.get("recebido_em", SEGUNDA_10H))

    final: dict[str, Any] = {}
    conversa = "c1"
    for i, msg in enumerate(caso["mensagens"]):
        conversa, texto = (msg["conversa"], msg["texto"]) if isinstance(msg, dict) else ("c1", msg)
        # O rascunho gravado vale só para a última mensagem do caso.
        modelo.rascunho = caso.get("rascunho") if i == len(caso["mensagens"]) - 1 else None
        final = processa(app, conversa, texto, recebido)

    e = caso["espera"]
    parado = parado_em_humano(app, conversa)
    if "humano" in e:
        assert parado is e["humano"]
    if "motivo" in e:
        assert final["decisao"]["motivo"] == e["motivo"]
    if parado:
        final = retoma(app, conversa, "Bia")
        assert "Bia" in final["resposta"]

    if "evento" in e:
        assert final["evento"] == e["evento"]
    if "setor" in e:
        assert final["classificacao"]["setor"] == e["setor"]
    if "tipo" in e:
        assert final["classificacao"]["tipo"] == e["tipo"]
    if "origem" in e:
        assert final["origem"] == e["origem"]
    if "caminho" in e:
        assert final["caminho"] == e["caminho"]
    if "demandas" in e:
        assert banco.conta("demandas") == e["demandas"]
    if "eventos" in e:
        assert banco.conta("eventos") == e["eventos"]
    if "resumo_primeiro" in e:
        assert final["resumo"][0] == e["resumo_primeiro"]
    if "cortes" in e:
        assert final["cortes"] == e["cortes"]
    if "resposta_igual" in e:
        assert final["resposta"] == e["resposta_igual"]
    for trecho in e.get("resposta_contem", []):
        assert trecho in final["resposta"]
    for trecho in e.get("resposta_nao_contem", []):
        assert trecho not in final["resposta"]
