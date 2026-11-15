"""Modelos plugáveis.

O padrão é falso e determinístico: teste e demonstração sem chave e sem custo.
"""

from typing import Protocol

from triagem.estado import Classificacao, Setor
from triagem.texto import sem_acento

NOME_SETOR: dict[str, str] = {
    "fiscal": "Fiscal",
    "pessoal": "Pessoal",
    "contabil": "Contábil",
    "societario": "Societário",
    "atendimento": "Atendimento",
}

# (palavras-chave, tipo, setor). A ordem da lista decide o empate.
PALAVRAS: list[tuple[tuple[str, ...], str, Setor]] = [
    (("guia", "imposto", "das ", "darf"), "guia_imposto", "fiscal"),
    (("nota fiscal", "nfse", "nf-e", "nfe"), "nota_fiscal", "fiscal"),
    (("admissao", "admitir", "novo funcionario", "contratei"), "admissao", "pessoal"),
    (("ferias",), "ferias", "pessoal"),
    (("rescisao", "demissao", "desligamento"), "rescisao", "pessoal"),
    (("folha", "holerite", "pro-labore", "pro labore"), "folha", "pessoal"),
    (("balancete", "balanco", "dre "), "balancete", "contabil"),
    (
        ("contrato social", "alteracao contratual", "endereco da empresa", "abrir empresa"),
        "alteracao_contratual",
        "societario",
    ),
]
SENSIVEIS = ("cancelar", "cancelamento", "reclamacao", "reclamar", "absurdo", "procon")
STATUS = ("andamento", "como esta", "como ta", "novidade", "ja ficou pronto", "status")


class Modelo(Protocol):
    def classifica(self, texto: str) -> Classificacao: ...

    def redige(self, contexto: dict[str, object]) -> str: ...


class ModeloFalso:
    """Classifica por palavra-chave e redige por modelo de frase. Mesma entrada, mesma saída."""

    def classifica(self, texto: str) -> Classificacao:
        alvo = sem_acento(texto) + " "
        achados = [
            (tipo, setor) for palavras, tipo, setor in PALAVRAS if any(p in alvo for p in palavras)
        ]
        setor: Setor = achados[0][1] if achados else "atendimento"
        if any(p in alvo for p in SENSIVEIS):
            return Classificacao(tipo="reclamacao", setor=setor, confianca=0.9)
        if any(p in alvo for p in STATUS):
            return Classificacao(tipo="consulta_status", setor=setor, confianca=0.9)
        if not achados:
            return Classificacao(tipo="outro", setor="atendimento", confianca=0.2)
        um_setor = len({s for _, s in achados}) == 1
        return Classificacao(tipo=achados[0][0], setor=setor, confianca=0.92 if um_setor else 0.55)

    def redige(self, contexto: dict[str, object]) -> str:
        p = contexto.get("protocolo")
        setor = NOME_SETOR.get(str(contexto.get("setor")), "Atendimento")
        prazo = contexto.get("prazo")
        evento = contexto.get("evento")
        if evento == "vazia":
            return "Não recebi o texto do pedido. Pode escrever o que você precisa?"
        if evento == "repetido":
            return f"Esse pedido já está registrado com o protocolo {p}."
        if contexto.get("responsavel"):
            assumiu = f"{contexto['responsavel']}, do setor {setor}, assumiu o atendimento."
            return f"Pedido registrado com o protocolo {p}. {assumiu}" if p else assumiu
        if evento == "consulta":
            return f"Seu pedido está registrado com o protocolo {p}, setor {setor}. Prazo: {prazo}."
        if evento == "novo_pedido":
            return f"Novo pedido incluído no protocolo {p}, setor {setor}. Prazo: {prazo}."
        return f"Pedido registrado com o protocolo {p}, setor {setor}. Prazo: {prazo}."


class ModeloGravado(ModeloFalso):
    """Replay: devolve o rascunho gravado de um modelo no lugar do modelo de frase."""

    def __init__(self, rascunho: str | None) -> None:
        self.rascunho = rascunho

    def redige(self, contexto: dict[str, object]) -> str:
        if self.rascunho is None:
            return super().redige(contexto)
        return self.rascunho.replace("{protocolo}", str(contexto.get("protocolo")))
