"""Status de cada família de dados, calculado do banco.

Sai um dicionário pronto para virar cartão na página e tabela no plano. Os
números vêm do banco na hora; a regra de leitura vem de `familias.py`.

"Histórico" é a distância entre o primeiro e o último registro com data, e
"meses com dado" quantos meses desse intervalo têm pelo menos um registro. Os
dois juntos denunciam buraco: 20 meses de histórico com 9 meses com dado é uma
série com lacuna, não uma série longa.
"""

from __future__ import annotations

import sqlite3
from collections import Counter

from . import familias as F
from .db import agora

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _data(valor: str, formato: str) -> str | None:
    """Data AAAA-MM-DD a partir do valor da coluna, ou None se não der."""
    v = (valor or "").strip()
    if not v:
        return None
    if formato == F.DATA_BR:
        partes = v[:10].split("/")
        if len(partes) == 3 and len(partes[2]) == 4:
            return f"{partes[2]}-{partes[1]}-{partes[0]}"
        return None
    if len(v) >= 10 and v[4] == "-" and v[7] == "-":
        return v[:10]
    return None


def _mes_legivel(aaaa_mm: str) -> str:
    return f"{MESES[int(aaaa_mm[5:7]) - 1]}/{aaaa_mm[:4]}"


def _meses_entre(ini: str, fim: str) -> int:
    a, b = int(ini[:4]) * 12 + int(ini[5:7]), int(fim[:4]) * 12 + int(fim[5:7])
    return b - a + 1


def status_familia(conn: sqlite3.Connection, fam: F.Familia) -> dict:
    tabela = F._tab(conn, fam.tabela)
    registros = conn.execute(f'SELECT COUNT(*) FROM "{tabela}"').fetchone()[0]
    saida = {
        "id": fam.id, "nome": fam.nome, "fonte": fam.fonte, "descricao": fam.descricao,
        "status": fam.status, "status_rotulo": F.ROTULO_STATUS[fam.status],
        "razao_status": fam.razao_status, "frentes": fam.frentes,
        "registros": registros, "unidade": fam.unidade,
        "periodo": None, "extras": [], "avisos": [],
        "pedir": [{"pedido": p, "prioridade": pr, "prioridade_rotulo": F.ROTULO_PRIORIDADE[pr],
                   "frentes": fr} for p, pr, fr in fam.pedir],
    }
    if registros == 0 and fam.status not in (F.AUSENTE, F.FORA):
        saida["status"], saida["status_rotulo"] = F.AUSENTE, F.ROTULO_STATUS[F.AUSENTE]

    if fam.coluna_tempo and registros:
        datas = [d for (v,) in conn.execute(f'SELECT "{fam.coluna_tempo}" FROM "{tabela}"')
                 if (d := _data(v, fam.formato_tempo))]
        if datas:
            ini, fim = min(datas), max(datas)
            meses_com = len({d[:7] for d in datas})
            saida["periodo"] = {
                "inicio": ini, "fim": fim, "rotulo_tempo": fam.rotulo_tempo,
                "inicio_legivel": _mes_legivel(ini), "fim_legivel": _mes_legivel(fim),
                "meses_historico": _meses_entre(ini, fim), "meses_com_dado": meses_com,
                "registros_com_data": len(datas),
            }
            sem_data = registros - len(datas)
            if sem_data and fam.avisar_sem_data:
                saida["avisos"].append((F.ATENCAO if sem_data / registros > 0.1 else F.INFO,
                                        f"{F._fmt(sem_data)} registros sem {fam.rotulo_tempo}."))
            buracos = saida["periodo"]["meses_historico"] - meses_com
            if buracos > 0:
                saida["avisos"].append((F.ATENCAO, (f"1 mês do período sem nenhum registro com {fam.rotulo_tempo}." if buracos == 1 else f"{buracos} meses do período sem nenhum registro com {fam.rotulo_tempo}.")))

    for rotulo, fn in fam.extras:
        saida["extras"].append((rotulo, fn(conn, tabela)))
    if fam.avisos_calculados:
        saida["avisos"] = fam.avisos_calculados(conn) + saida["avisos"]
    saida["avisos"] = saida["avisos"] + list(fam.avisos)
    # ponto principal: o que bloqueia; senão, a regra de leitura da própria
    # família; senão, o primeiro aviso calculado
    bloqueios = [t for n, t in saida["avisos"] if n == F.BLOQUEIA]
    saida["principal"] = (bloqueios[0] if bloqueios
                          else fam.avisos[0][1] if fam.avisos
                          else saida["avisos"][0][1] if saida["avisos"] else "")
    ordem = {F.BLOQUEIA: 0, F.ATENCAO: 1, F.INFO: 2}
    saida["avisos"] = [{"nivel": n, "nivel_rotulo": F.ROTULO_NIVEL[n], "texto": t}
                       for n, t in sorted(saida["avisos"], key=lambda a: ordem[a[0]])]
    return saida


def status_geral(conn: sqlite3.Connection) -> dict:
    cards = [status_familia(conn, f) for f in F.FAMILIAS]
    imp = conn.execute("SELECT zip_nome, zip_sha256, MAX(importado_em) AS em, COUNT(*) AS arquivos, "
                       "SUM(linhas) AS linhas FROM importacao GROUP BY zip_sha256 "
                       "ORDER BY em DESC LIMIT 1").fetchone()
    contagem = Counter(c["status"] for c in cards)
    return {
        "gerado_em": agora(),
        "entrega": dict(imp) if imp else None,
        "resumo": {s: contagem.get(s, 0) for s in F.ROTULO_STATUS},
        "rotulos": F.ROTULO_STATUS,
        "familias": cards,
    }
