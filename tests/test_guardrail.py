import pytest

from triagem.guardrail import valida


@pytest.mark.parametrize(
    ("frase", "motivo"),
    [
        # Frases do tipo que saiu em produção antes da correção (dados trocados).
        ("Seu pedido está em análise.", "andamento sem base"),
        ("Seu pedido esta em analise.", "andamento sem base"),
        ("O documento já está em andamento.", "andamento sem base"),
        ("Já estamos providenciando a guia.", "andamento sem base"),
        ("Está sendo processado pela equipe.", "andamento sem base"),
        ("Retornaremos em breve.", "promessa de retorno"),
        ("Assim que ficar pronto te avisamos.", "promessa de retorno"),
        ("Aguarde o nosso retorno.", "promessa de retorno"),
        ("Entraremos em contato amanhã.", "promessa de retorno"),
        ("Vamos enviar a guia por e-mail.", "promessa de canal"),
        ("Você receberá o link no WhatsApp.", "promessa de canal"),
    ],
)
def test_corta_frase_sem_base(frase: str, motivo: str) -> None:
    resposta, cortes = valida(frase, "EX-00001")
    assert cortes == [motivo]
    assert resposta == "Pedido registrado com o protocolo EX-00001."


def test_mantem_frase_verdadeira_e_corta_so_a_ruim() -> None:
    rascunho = "Pedido registrado com o protocolo EX-00007. Retornaremos em breve. Prazo: 16/11."
    resposta, cortes = valida(rascunho, "EX-00007")
    assert resposta == "Pedido registrado com o protocolo EX-00007. Prazo: 16/11."
    assert cortes == ["promessa de retorno"]


def test_frase_neutra_nao_e_cortada() -> None:
    texto = "O setor Fiscal cuida das guias. Pedido registrado com o protocolo EX-00001."
    assert valida(texto, "EX-00001") == (texto, [])


def test_sem_protocolo_e_vazio_tem_resposta_padrao() -> None:
    assert valida("Retornaremos em breve.", None) == (
        "Recebemos a sua mensagem.",
        ["promessa de retorno"],
    )
