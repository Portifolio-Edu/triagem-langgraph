from datetime import datetime

import pytest

from triagem.regras import LIMIAR_CONFIANCA, decide, soma_horas_uteis

SEGUNDA_10H = datetime(2026, 11, 16, 10, 0)


@pytest.mark.parametrize(
    ("inicio", "horas", "esperado"),
    [
        (datetime(2026, 11, 16, 10, 0), 4, datetime(2026, 11, 16, 14, 0)),  # dentro do dia
        (datetime(2026, 11, 16, 10, 0), 8, datetime(2026, 11, 16, 18, 0)),  # fecha exato às 18h
        (datetime(2026, 11, 16, 16, 0), 4, datetime(2026, 11, 17, 10, 0)),  # vira o dia
        (datetime(2026, 11, 20, 17, 0), 4, datetime(2026, 11, 23, 11, 0)),  # sexta para segunda
        (datetime(2026, 11, 21, 9, 0), 2, datetime(2026, 11, 23, 10, 0)),  # sábado começa segunda
        (datetime(2026, 11, 16, 6, 30), 1, datetime(2026, 11, 16, 9, 0)),  # antes de abrir
        (datetime(2026, 11, 16, 19, 0), 24, datetime(2026, 11, 19, 12, 0)),  # depois de fechar
    ],
)
def test_soma_horas_uteis(inicio: datetime, horas: int, esperado: datetime) -> None:
    assert soma_horas_uteis(inicio, horas) == esperado


def test_regra_do_setor_define_prazo() -> None:
    d = decide("guia_imposto", "fiscal", 0.92, SEGUNDA_10H)
    assert d["para_humano"] is False
    assert d["prazo_horas"] == 4
    assert d["vencimento"] == "2026-11-16T14:00:00"


def test_confianca_baixa_vai_para_pessoa() -> None:
    d = decide("guia_imposto", "fiscal", LIMIAR_CONFIANCA - 0.01, SEGUNDA_10H)
    assert d["para_humano"] is True
    assert d["motivo"] == "confiança baixa"


def test_confianca_no_limiar_resolve_sozinho() -> None:
    assert decide("folha", "pessoal", LIMIAR_CONFIANCA, SEGUNDA_10H)["para_humano"] is False


def test_reclamacao_vai_para_pessoa_mesmo_com_confianca_alta() -> None:
    d = decide("reclamacao", "fiscal", 0.99, SEGUNDA_10H)
    assert d["para_humano"] is True
    assert d["prazo_horas"] == 2


def test_consulta_nao_cria_prazo() -> None:
    d = decide("consulta_status", "fiscal", 0.9, SEGUNDA_10H)
    assert d["prazo_horas"] is None
    assert d["para_humano"] is False
