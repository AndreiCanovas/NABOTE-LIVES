"""Frente 3 — a live move as doações?

Versão "durante a live × fora dela": cruza o minuto de cada doação da
Castcoin com o intervalo de cada live que tem início e fim reais.

JANELA. Só entram os meses em que TODA live conhecida tem horário. Fora
disso, uma doação "fora de live" pode ter acontecido durante uma live sem
horário registrado, e a linha de base fica contaminada. A janela é calculada
dos dados: começa no primeiro mês completo depois da última live sem horário
e vai até o último registro da Castcoin.

LINHA DE BASE NA MESMA HORA. Doação é noturna e live também; comparar a live
com "o resto do dia" mediria o efeito da hora, não o da live. Para cada hora
do dia (Brasília), calcula-se a taxa de doações fora de live; o "esperado sem
live" é essa taxa aplicada às horas em que houve live. O efeito é observado
dividido por esperado.

LIVE SEM REGISTRO. Uma noite sem live no catálogo, mas com pedido de React
ou com volume de doações típico de live, quase certamente teve live (em
outro canal, apagada, ou fora do inventário). Essas noites saem da linha de
base e são contadas à parte. O efeito é reportado de dois jeitos: com a base
completa (conservador, porque a base inclui essas lives escondidas) e com a
base limpa.

PÓS-LIVE. Alerta e pagamento podem chegar depois do fim. Os 60 minutos depois
do fim são contados à parte, nem dentro nem fora, para não inflar nenhum
dos lados.

Tudo agregado. Nenhuma doação individual sai daqui.
"""

from __future__ import annotations

import bisect
import calendar
import sqlite3
import statistics as S
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from .familias import _tab

BRASILIA = timedelta(hours=-3)
POS_LIVE_MIN = 60
BIN_MIN = 15
PERFIL_ANTES_MIN = 60
PERFIL_DEPOIS_MIN = 6 * 60
TEMA_MIN_LIVES = 4
# noite sem live registrada que parece ter tido live
SUSPEITA_MIN_DOACOES = 15
SUSPEITA_MIN_REACT = 3
# a "noite" vai das 6h de um dia às 6h do seguinte (Brasília): live que passa
# da meia-noite continua na mesma noite
VIRADA_NOITE = timedelta(hours=6)
DESCONHECIDO = "Assunto não identificável pelo título"


def _min(iso: str) -> int:
    """Minuto absoluto (UTC) desde a época, a partir de 'AAAA-MM-DDTHH:MM…Z'."""
    # timegm lê a data como UTC; datetime.timestamp() usaria o fuso da máquina
    return calendar.timegm(datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").timetuple()) // 60


def _noite(minuto: int):
    return (datetime(1970, 1, 1) + timedelta(minutes=minuto) + BRASILIA - VIRADA_NOITE).date()


def _hora_brt(minuto: int) -> int:
    return (datetime(1970, 1, 1) + timedelta(minutes=minuto) + BRASILIA).hour


def _janela(conn) -> tuple[str, str]:
    """Início: 1º dia do mês seguinte à última live sem horário. Fim: último registro da Castcoin."""
    cx = _tab(conn, "analise_tematica__contexto_lives")
    ultima_sem = conn.execute(
        f'SELECT MAX(termino_exibido_studio_data) FROM "{cx}" WHERE inicio_real_utc = \'\' '
        f'AND termino_exibido_studio_data <> \'\'').fetchone()[0]
    ui = _tab(conn, "castcoin__suplemento_doacoes_ui")
    ultimo = conn.execute(f'SELECT MAX(data_exibida_utc) FROM "{ui}"').fetchone()[0]
    a, m = int(ultima_sem[:4]), int(ultima_sem[5:7]) + 1
    if m == 13:
        a, m = a + 1, 1
    return f"{a:04d}-{m:02d}-01T03:00Z", ultimo   # meia-noite de Brasília


def calcular(conn: sqlite3.Connection) -> dict:
    ini_iso, fim_iso = _janela(conn)
    j0, j1 = _min(ini_iso), _min(fim_iso) + 1

    ll = _tab(conn, "01_historico__lives_lives")
    tm = _tab(conn, "analise_tematica__temas_lives")
    temas = {lid: (t, c, tipo) for lid, t, c, tipo in conn.execute(
        f'SELECT live_id, tema_principal, confianca, tipo_de_live FROM "{tm}"')}
    lives = []
    for lid, i, f in conn.execute(f'SELECT live_id, inicio_real, fim_real FROM "{ll}" '
                                  f'WHERE inicio_real <> \'\' AND fim_real <> \'\''):
        a, b = _min(i), _min(f)
        if b > a and a < j1 and b > j0:
            lives.append({"id": lid, "ini": max(a, j0), "fim": min(b, j1), "ini_real": a, "fim_real": b,
                          "tema": temas.get(lid, ("", "", ""))[0], "confianca": temas.get(lid, ("", "", ""))[1],
                          "tipo": temas.get(lid, ("", "", ""))[2]})
    lives.sort(key=lambda x: x["ini"])

    # estado de cada minuto da janela: 1 = live, 2 = pós-live, 0 = fora
    estado = bytearray(j1 - j0)
    for lv in lives:
        for t in range(lv["fim"], min(lv["fim"] + POS_LIVE_MIN, j1)):
            if estado[t - j0] == 0:
                estado[t - j0] = 2
    for lv in lives:
        for t in range(lv["ini"], lv["fim"]):
            estado[t - j0] = 1

    ui = _tab(conn, "castcoin__suplemento_doacoes_ui")
    doacoes = [(_min(d), int(v), t) for d, v, t in conn.execute(
        f'SELECT data_exibida_utc, valor_centavos, tipo_exibido FROM "{ui}" '
        f'WHERE produto_id_correspondente_nome = \'\' AND CAST(valor_centavos AS INT) > 0')]
    doacoes = [x for x in doacoes if j0 <= x[0] < j1]

    # noites sem live registrada que parecem ter tido live -> estado 3
    noites_live = {_noite(lv["ini"]) for lv in lives} | {_noite(lv["fim"] - 1) for lv in lives}
    por_noite = defaultdict(lambda: [0, 0])
    for t, v, tipo in doacoes:
        if estado[t - j0] == 0:
            k = _noite(t)
            por_noite[k][0] += 1
            por_noite[k][1] += tipo == "React"
    suspeitas = {k for k, (n, r) in por_noite.items() if k not in noites_live
                 and (n >= SUSPEITA_MIN_DOACOES or r >= SUSPEITA_MIN_REACT)}
    for k in range(j1 - j0):
        if estado[k] == 0 and _noite(j0 + k) in suspeitas:
            estado[k] = 3

    # minutos e doações por (estado, hora de Brasília)
    min_por = Counter()
    hora_de = [_hora_brt(j0 + k) for k in range(0, j1 - j0)]
    for k, est in enumerate(estado):
        min_por[(est, hora_de[k])] += 1
    n_por, v_por = Counter(), Counter()
    tipos_por = defaultdict(Counter)
    for t, v, tipo in doacoes:
        est, h = estado[t - j0], hora_de[t - j0]
        n_por[(est, h)] += 1
        v_por[(est, h)] += v
        tipos_por[est][tipo or "livre"] += 1

    def soma(c, est):
        return sum(x for (e, _), x in c.items() if e == est)

    horas = {e: soma(min_por, e) / 60 for e in (0, 1, 2, 3)}
    obs_n, obs_v = soma(n_por, 1), soma(v_por, 1)
    def esperado(estados):
        en = ev = 0.0
        for h in range(24):
            base_h = sum(min_por[(e, h)] for e in estados) / 60
            if base_h == 0:
                continue
            horas_live_h = min_por[(1, h)] / 60
            en += horas_live_h * sum(n_por[(e, h)] for e in estados) / base_h
            ev += horas_live_h * sum(v_por[(e, h)] for e in estados) / base_h
        return en, ev
    esp_n, esp_v = esperado((0, 3))          # conservador: base inclui as noites suspeitas
    limpo_n, limpo_v = esperado((0,))        # base limpa
    por_hora = [{"hora": h,
                 "live_n_h": n_por[(1, h)] / (min_por[(1, h)] / 60) if min_por[(1, h)] >= 120 else None,
                 "fora_n_h": n_por[(0, h)] / (min_por[(0, h)] / 60) if min_por[(0, h)] else None,
                 "suspeita_n_h": n_por[(3, h)] / (min_por[(3, h)] / 60) if min_por[(3, h)] >= 120 else None,
                 "horas_live": min_por[(1, h)] / 60}
                for h in range(24)]

    # perfil em torno do início: doações por live por bloco de 15 min
    bins = list(range(-PERFIL_ANTES_MIN, PERFIL_DEPOIS_MIN, BIN_MIN))
    cont, expo = Counter(), Counter()
    tempos = [t for t, _, _ in doacoes]
    tempos.sort()
    for lv in lives:
        for b in bins:
            a = lv["ini_real"] + b
            z = a + BIN_MIN
            if a < j0 or z > j1:
                continue
            if b >= 0 and a >= lv["fim_real"]:
                continue   # a live já tinha acabado: não expõe este bloco
            expo[b] += 1
            cont[b] += bisect.bisect_left(tempos, z) - bisect.bisect_left(tempos, a)
    perfil = [{"min": b, "lives": expo[b], "doacoes_por_live": cont[b] / expo[b] if expo[b] else None}
              for b in bins]

    # por live
    por_live = []
    for lv in lives:
        i0, i1 = bisect.bisect_left(tempos, lv["ini"]), bisect.bisect_left(tempos, lv["fim"])
        vals = [v for t, v, _ in doacoes if lv["ini"] <= t < lv["fim"]]
        h = (lv["fim"] - lv["ini"]) / 60
        por_live.append({"horas": h, "n": i1 - i0, "centavos": sum(vals),
                         "tema": lv["tema"], "confianca": lv["confianca"], "tipo": lv["tipo"]})
    val_lives = sorted((x["centavos"] for x in por_live), reverse=True)
    top = max(1, round(len(val_lives) * 0.1))

    # por tema (só temas com lives suficientes; o desconhecido fica à parte)
    agg = defaultdict(lambda: {"lives": 0, "horas": 0.0, "n": 0, "centavos": 0})
    for x in por_live:
        a = agg[x["tema"] or DESCONHECIDO]
        a["lives"] += 1
        a["horas"] += x["horas"]
        a["n"] += x["n"]
        a["centavos"] += x["centavos"]
    temas_out = sorted(({"tema": t, **a, "reais_por_hora": a["centavos"] / 100 / a["horas"] if a["horas"] else 0}
                        for t, a in agg.items() if a["lives"] >= TEMA_MIN_LIVES),
                       key=lambda x: -x["reais_por_hora"])

    total_n = len(doacoes)
    total_v = sum(v for _, v, _ in doacoes)
    horas_total = (j1 - j0) / 60
    return {
        "janela": {"inicio": ini_iso, "fim": fim_iso, "dias": round(horas_total / 24, 1)},
        "lives": len(lives),
        "horas_live": horas[1], "horas_pos": horas[2], "horas_fora": horas[0], "horas_total": horas_total,
        "doacoes": total_n, "centavos": total_v,
        "dentro": {"n": obs_n, "centavos": obs_v, "pct_n": obs_n / total_n, "pct_valor": obs_v / total_v,
                   "pct_tempo": horas[1] / horas_total},
        "pos": {"n": soma(n_por, 2), "centavos": soma(v_por, 2)},
        "fora": {"n": soma(n_por, 0), "centavos": soma(v_por, 0)},
        "horas_suspeitas": horas[3],
        "taxa": {"live_n_h": obs_n / horas[1], "fora_n_h": soma(n_por, 0) / horas[0],
                 "suspeita_n_h": soma(n_por, 3) / horas[3] if horas[3] else None,
                 "live_reais_h": obs_v / 100 / horas[1], "fora_reais_h": soma(v_por, 0) / 100 / horas[0]},
        "esperado": {"n": esp_n, "centavos": esp_v,
                     "efeito_n": obs_n / esp_n if esp_n else None,
                     "efeito_valor": obs_v / esp_v if esp_v else None},
        "esperado_limpo": {"n": limpo_n, "centavos": limpo_v,
                           "efeito_n": obs_n / limpo_n if limpo_n else None,
                           "efeito_valor": obs_v / limpo_v if limpo_v else None},
        "suspeitas": {"noites": len(suspeitas), "n": soma(n_por, 3), "centavos": soma(v_por, 3),
                      "react": tipos_por[3].get("React", 0),
                      "por_mes": dict(sorted(Counter(k.strftime("%Y-%m") for k in suspeitas).items())),
                      "criterio": {"doacoes": SUSPEITA_MIN_DOACOES, "react": SUSPEITA_MIN_REACT}},
        "noites": {"total": len({_noite(j0 + k) for k in range(0, j1 - j0, 60)}),
                   "com_live": len(noites_live)},
        "por_hora": por_hora,
        "perfil_inicio": perfil,
        "por_live": {"mediana_reais": S.median(val_lives) / 100 if val_lives else 0,
                     "mediana_n": S.median([x["n"] for x in por_live]) if por_live else 0,
                     "top10_pct_valor": sum(val_lives[:top]) / sum(val_lives) if sum(val_lives) else 0,
                     "top10_lives": top,
                     "mediana_horas": S.median([x["horas"] for x in por_live]) if por_live else 0},
        "temas": temas_out,
        "temas_min_lives": TEMA_MIN_LIVES,
        "tipos": {str(e): dict(c) for e, c in tipos_por.items()},
    }
