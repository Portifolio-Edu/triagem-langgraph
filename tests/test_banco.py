from triagem.banco import Banco

AGORA = "2026-11-16T10:00:00"


def test_repetir_o_mesmo_pedido_nao_duplica() -> None:
    b = Banco()
    r1 = b.registra("c1", "fiscal", "guia_imposto", "Preciso da guia", None, AGORA)
    r2 = b.registra("c1", "fiscal", "guia_imposto", "Preciso da guia", None, AGORA)
    assert (r1.evento, r2.evento) == ("demanda_aberta", "repetido")
    assert r1.protocolo == r2.protocolo
    assert (b.conta("demandas"), b.conta("eventos")) == (1, 1)


def test_pedido_novo_vai_para_a_frente_e_gera_evento() -> None:
    b = Banco()
    b.registra("c1", "fiscal", "guia_imposto", "guia de outubro", None, AGORA)
    r = b.registra("c1", "fiscal", "guia_imposto", "guia de novembro", None, AGORA)
    assert r.evento == "novo_pedido"
    assert r.resumo == ["guia de novembro", "guia de outubro"]
    assert b.eventos(r.protocolo) == ["demanda_aberta", "novo_pedido"]


def test_mesmo_texto_em_outra_conversa_e_outra_demanda() -> None:
    b = Banco()
    a = b.registra("a", "fiscal", "guia_imposto", "Preciso da guia", None, AGORA)
    c = b.registra("b", "fiscal", "guia_imposto", "Preciso da guia", None, AGORA)
    assert a.protocolo != c.protocolo


def test_conversa_so_ve_a_propria_demanda() -> None:
    b = Banco()
    b.registra("a", "fiscal", "guia_imposto", "Preciso da guia", None, AGORA)
    assert b.ultima_aberta("b") is None
    achada = b.ultima_aberta("a", "fiscal")
    assert achada is not None
    assert achada.resumo == ["Preciso da guia"]
