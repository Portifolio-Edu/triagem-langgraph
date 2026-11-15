"""Demandas e eventos em SQLite.

Toda consulta filtra pela conversa: uma conversa só vê o resumo dela.
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass

ESQUEMA = """
CREATE TABLE IF NOT EXISTS demandas (
    id INTEGER PRIMARY KEY,
    conversa_id TEXT NOT NULL,
    setor TEXT NOT NULL,
    tipo TEXT NOT NULL,
    protocolo TEXT UNIQUE,
    resumo TEXT NOT NULL,
    vencimento TEXT,
    status TEXT NOT NULL DEFAULT 'aberta'
);
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY,
    demanda_id INTEGER NOT NULL REFERENCES demandas(id),
    tipo TEXT NOT NULL,
    chave TEXT NOT NULL UNIQUE,
    texto TEXT NOT NULL,
    criado_em TEXT NOT NULL
);
"""


@dataclass
class Registro:
    protocolo: str
    evento: str  # demanda_aberta | novo_pedido | repetido | consulta
    resumo: list[str]
    vencimento: str | None


def chave(conversa_id: str, texto: str) -> str:
    """Chave de idempotência: mesma conversa e mesmo texto geram a mesma chave."""
    return hashlib.sha256(f"{conversa_id}|{texto.strip().lower()}".encode()).hexdigest()


class Banco:
    def __init__(self, caminho: str = ":memory:") -> None:
        self.con = sqlite3.connect(caminho, check_same_thread=False)
        self.con.executescript(ESQUEMA)

    def _demanda(self, demanda_id: int) -> Registro:
        protocolo, resumo, vencimento = self.con.execute(
            "SELECT protocolo, resumo, vencimento FROM demandas WHERE id = ?", (demanda_id,)
        ).fetchone()
        return Registro(protocolo, "", json.loads(resumo), vencimento)

    def registra(
        self,
        conversa_id: str,
        setor: str,
        tipo: str,
        texto: str,
        vencimento: str | None,
        agora: str,
    ) -> Registro:
        k = chave(conversa_id, texto)
        repetido = self.con.execute(
            "SELECT demanda_id FROM eventos WHERE chave = ?", (k,)
        ).fetchone()
        if repetido:
            registro = self._demanda(repetido[0])
            registro.evento = "repetido"
            return registro

        aberta = self.con.execute(
            "SELECT id, resumo FROM demandas WHERE conversa_id = ? AND setor = ? AND tipo = ? "
            "AND status = 'aberta' ORDER BY id DESC LIMIT 1",
            (conversa_id, setor, tipo),
        ).fetchone()
        with self.con:
            if aberta:
                # O pedido novo vai para a frente; o anterior fica atrás, sem se perder.
                demanda_id = aberta[0]
                resumo = [texto, *json.loads(aberta[1])]
                self.con.execute(
                    "UPDATE demandas SET resumo = ?, vencimento = ? WHERE id = ?",
                    (json.dumps(resumo, ensure_ascii=False), vencimento, demanda_id),
                )
                evento = "novo_pedido"
            else:
                cur = self.con.execute(
                    "INSERT INTO demandas (conversa_id, setor, tipo, resumo, vencimento) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (conversa_id, setor, tipo, json.dumps([texto], ensure_ascii=False), vencimento),
                )
                demanda_id = int(cur.lastrowid or 0)
                self.con.execute(
                    "UPDATE demandas SET protocolo = ? WHERE id = ?",
                    (f"EX-{demanda_id:05d}", demanda_id),
                )
                evento = "demanda_aberta"
            self.con.execute(
                "INSERT INTO eventos (demanda_id, tipo, chave, texto, criado_em) "
                "VALUES (?, ?, ?, ?, ?)",
                (demanda_id, evento, k, texto, agora),
            )
        registro = self._demanda(demanda_id)
        registro.evento = evento
        return registro

    def ultima_aberta(self, conversa_id: str, setor: str | None = None) -> Registro | None:
        sql = "SELECT id FROM demandas WHERE conversa_id = ? AND status = 'aberta'"
        args: tuple[str, ...] = (conversa_id,)
        if setor and setor != "atendimento":
            sql += " AND setor = ?"
            args += (setor,)
        linha = self.con.execute(sql + " ORDER BY id DESC LIMIT 1", args).fetchone()
        if not linha:
            return None
        registro = self._demanda(linha[0])
        registro.evento = "consulta"
        return registro

    def conta(self, tabela: str) -> int:
        assert tabela in ("demandas", "eventos")
        return int(self.con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0])

    def eventos(self, protocolo: str) -> list[str]:
        linhas = self.con.execute(
            "SELECT e.tipo FROM eventos e JOIN demandas d ON d.id = e.demanda_id "
            "WHERE d.protocolo = ? ORDER BY e.id",
            (protocolo,),
        ).fetchall()
        return [tipo for (tipo,) in linhas]
