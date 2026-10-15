"""Zip da entrega -> tabelas de espelho no SQLite, com procedência.

Lê direto do zip, sem extrair: o zip é a fonte da verdade e o hash dele vai
para cada linha de `importacao`. Cada CSV vira `stg__<caminho>` com todas as
colunas em TEXT, como vieram. Interpretar (data, centavos, situação) é trabalho
das camadas de cima, que declaram a regra que usam.

Reimportar o mesmo zip não faz nada. Importar um zip novo recria as tabelas de
espelho com o conteúdo novo e mantém o histórico de importações.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import sqlite3
import unicodedata
import zipfile
from pathlib import Path

from .db import agora

csv.field_size_limit(10**9)
PREFIXO = "stg__"


def nome_tabela(caminho: str) -> str:
    """'01_Historico/suplementos/castcoin/suplemento_extrato.csv' ->
    'stg__01_historico__suplementos__castcoin__suplemento_extrato'."""
    sem_ext = caminho.rsplit(".", 1)[0]
    partes = [_slug(p) for p in sem_ext.split("/") if p]
    return PREFIXO + "__".join(partes)


def _slug(texto: str) -> str:
    puro = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", puro.lower()).strip("_") or "x"


def _colunas(cabecalho: list[str]) -> list[str]:
    """Nomes de coluna seguros e únicos. Coluna sem nome vira col_N."""
    vistos: dict[str, int] = {}
    saida = []
    for i, c in enumerate(cabecalho):
        base = _slug(c) if c.strip() else f"col_{i + 1}"
        if base[0].isdigit():
            base = "c_" + base
        n = vistos.get(base, 0)
        vistos[base] = n + 1
        saida.append(base if n == 0 else f"{base}_{n + 1}")
    return saida


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def importar_zip(conn: sqlite3.Connection, zip_path: Path | str) -> dict:
    zip_path = Path(zip_path)
    zip_sha = sha256_arquivo(zip_path)
    ja = conn.execute("SELECT COUNT(*) FROM importacao WHERE zip_sha256 = ?",
                      (zip_sha,)).fetchone()[0]
    if ja:
        return {"zip_sha256": zip_sha, "ja_importado": True, "tabelas": 0, "linhas": 0}

    quando = agora()
    total_tab = total_lin = 0
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            dados = z.read(info)
            sha = hashlib.sha256(dados).hexdigest()
            if not info.filename.lower().endswith(".csv"):
                conn.execute(
                    "INSERT INTO importacao (zip_sha256, zip_nome, arquivo, arquivo_sha256, "
                    "tabela, linhas, colunas, importado_em) VALUES (?,?,?,?,NULL,0,0,?)",
                    (zip_sha, zip_path.name, info.filename, sha, quando))
                continue
            tabela, linhas, colunas, irregulares = _carregar_csv(conn, info.filename, dados)
            conn.execute(
                "INSERT INTO importacao (zip_sha256, zip_nome, arquivo, arquivo_sha256, tabela, "
                "linhas, colunas, linhas_irregulares, importado_em) VALUES (?,?,?,?,?,?,?,?,?)",
                (zip_sha, zip_path.name, info.filename, sha, tabela, linhas, colunas,
                 irregulares, quando))
            total_tab += 1
            total_lin += linhas
    return {"zip_sha256": zip_sha, "ja_importado": False,
            "tabelas": total_tab, "linhas": total_lin}


def _carregar_csv(conn: sqlite3.Connection, caminho: str, dados: bytes):
    texto = dados.decode("utf-8-sig")
    leitor = csv.reader(io.StringIO(texto, newline=""))
    try:
        cabecalho = next(leitor)
    except StopIteration:
        cabecalho = []
    colunas = _colunas(cabecalho) or ["col_1"]
    tabela = nome_tabela(caminho)
    defs = ", ".join(f'"{c}" TEXT' for c in colunas)
    conn.execute(f'DROP TABLE IF EXISTS "{tabela}"')
    conn.execute(f'CREATE TABLE "{tabela}" (_linha INTEGER PRIMARY KEY, {defs}) STRICT')
    marcadores = ", ".join("?" * (len(colunas) + 1))
    n = irregulares = 0
    conn.execute("BEGIN")
    for registro in leitor:
        if not registro:
            continue
        if len(registro) != len(colunas):
            irregulares += 1
            registro = (registro + [""] * len(colunas))[: len(colunas)]
        n += 1
        conn.execute(f'INSERT INTO "{tabela}" VALUES ({marcadores})', [n, *registro])
    conn.execute("COMMIT")
    return tabela, n, len(cabecalho), irregulares
