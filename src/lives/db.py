"""Conexão e migrações, no mesmo molde do NABOTE (SQLite, tabelas STRICT)."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIN_SQLITE = (3, 37, 0)
PASTA_DADOS = Path("/home/user/dados_lives_confidencial")
BANCO_PADRAO = PASTA_DADOS / "processado" / "lives.db"
MIGRACOES = Path(__file__).resolve().parents[2] / "migrations"
_NOME = re.compile(r"^(\d{3})_(.+)\.sql$")


def agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def conectar(caminho: Path | str = BANCO_PADRAO) -> sqlite3.Connection:
    versao = tuple(int(p) for p in sqlite3.sqlite_version.split("."))
    if versao < MIN_SQLITE:
        raise RuntimeError(f"SQLite {MIN_SQLITE} ou maior é necessário (há {versao}).")
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrar(conn: sqlite3.Connection, pasta: Path = MIGRACOES) -> list[str]:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                 "versao INTEGER PRIMARY KEY, nome TEXT NOT NULL, "
                 "aplicada_em TEXT NOT NULL) STRICT")
    feitas = {r[0] for r in conn.execute("SELECT versao FROM schema_migrations")}
    aplicadas = []
    for arq in sorted(Path(pasta).glob("*.sql")):
        m = _NOME.match(arq.name)
        if not m:
            raise ValueError(f"migração fora do padrão NNN_nome.sql: {arq.name}")
        versao = int(m.group(1))
        if versao in feitas:
            continue
        conn.executescript(arq.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_migrations VALUES (?,?,?)",
                     (versao, m.group(2), agora()))
        aplicadas.append(arq.name)
    return aplicadas
