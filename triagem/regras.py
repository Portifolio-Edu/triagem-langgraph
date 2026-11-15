"""Regras de negócio em Python puro. Nada aqui chama modelo."""

from datetime import datetime, timedelta

from triagem.estado import Decisao, Setor

LIMIAR_CONFIANCA = 0.7
PRAZO_HORAS: dict[str, int] = {"fiscal": 4, "pessoal": 8, "contabil": 16, "societario": 24}
PRAZO_HUMANO = 2  # primeiro contato de uma pessoa, em horas úteis
ABRE, FECHA = 8, 18  # expediente de segunda a sexta


def _hora(t: datetime, hora: int) -> datetime:
    return t.replace(hour=hora, minute=0, second=0, microsecond=0)


def _proxima_abertura(t: datetime) -> datetime:
    if t.weekday() < 5 and ABRE <= t.hour < FECHA:
        return t
    if t.weekday() < 5 and t.hour < ABRE:
        return _hora(t, ABRE)
    t = _hora(t + timedelta(days=1), ABRE)
    while t.weekday() >= 5:
        t += timedelta(days=1)
    return t


def soma_horas_uteis(inicio: datetime, horas: int) -> datetime:
    """Conta só o expediente: pedido de sexta às 17h com prazo de 4h vence segunda às 11h."""
    t = _proxima_abertura(inicio)
    restante = timedelta(hours=horas)
    while restante > _hora(t, FECHA) - t:
        restante -= _hora(t, FECHA) - t
        t = _proxima_abertura(_hora(t, FECHA))
    return t + restante


def decide(tipo: str, setor: Setor, confianca: float, recebido_em: datetime) -> Decisao:
    def humano(motivo: str) -> Decisao:
        vencimento = soma_horas_uteis(recebido_em, PRAZO_HUMANO).isoformat()
        return Decisao(
            setor=setor,
            prazo_horas=PRAZO_HUMANO,
            vencimento=vencimento,
            para_humano=True,
            motivo=motivo,
        )

    if tipo == "reclamacao":
        return humano("reclamação ou cancelamento")
    if confianca < LIMIAR_CONFIANCA:
        return humano("confiança baixa")
    if tipo == "consulta_status":
        return Decisao(
            setor=setor,
            prazo_horas=None,
            vencimento=None,
            para_humano=False,
            motivo="consulta: responde só com o que está registrado",
        )
    horas = PRAZO_HORAS[setor]
    return Decisao(
        setor=setor,
        prazo_horas=horas,
        vencimento=soma_horas_uteis(recebido_em, horas).isoformat(),
        para_humano=False,
        motivo="regra do setor",
    )
