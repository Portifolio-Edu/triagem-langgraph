"""Guardrail fora do prompt: corta o que o agente não tem como saber nem cumprir."""

import re

from triagem.texto import limpa, sem_acento

# Os padrões comparam o texto sem acento e em minúsculas.
PROIBIDAS: dict[str, re.Pattern[str]] = {
    "andamento sem base": re.compile(
        r"\b(esta|segue|encontra-se|ja esta)\s+(em\s+)?(analise|andamento|processamento)"
        r"|\besta sendo (analisad|processad|providenciad|feit)"
        r"|\bja (estamos|esta) (trabalhando|providenciando|cuidando)"
    ),
    "promessa de retorno": re.compile(
        r"\b(retornaremos|vamos retornar|daremos (um )?retorno|entraremos em contato"
        r"|(te|lhe) (aviso|avisamos|chamamos|retornamos)|aguarde (o )?(nosso )?(retorno|contato)"
        r"|em breve (voce|vc) (recebe|tera|vai ter)|logo (te|lhe) respond)"
    ),
    "promessa de canal": re.compile(
        r"\b(enviaremos|vamos enviar|mandaremos|vamos mandar|(voce|vc) (vai )?recebera?)\b"
        r".*\b(e-?mail|whats ?app|sms|link|portal)"
    ),
}


def frases(texto: str) -> list[str]:
    return [f for f in re.split(r"(?<=[.!?])\s+", limpa(texto)) if f]


def valida(rascunho: str, protocolo: str | None) -> tuple[str, list[str]]:
    """Devolve a resposta e o motivo de cada corte. Frase com padrão proibido sai inteira."""
    mantidas: list[str] = []
    cortes: list[str] = []
    for frase in frases(rascunho):
        alvo = sem_acento(frase)
        motivo = next((m for m, p in PROIBIDAS.items() if p.search(alvo)), None)
        if motivo:
            cortes.append(motivo)
        else:
            mantidas.append(frase)
    resposta = " ".join(mantidas)
    if protocolo and protocolo not in resposta:
        # Sobrou vazio ou o modelo esqueceu o protocolo: a frase mínima é sempre verdadeira.
        padrao = f"Pedido registrado com o protocolo {protocolo}."
        resposta = f"{resposta} {padrao}".strip()
    return resposta or "Recebemos a sua mensagem.", cortes
