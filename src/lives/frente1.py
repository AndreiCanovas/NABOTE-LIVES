"""Frente 1 — perfil de compra e preço.

Tudo aqui sai agregado: nenhuma linha individual, nenhum id. As regras de
leitura que mudam o número estão escritas onde são aplicadas:

DOAÇÃO × LOJA NA CASTCOIN. O extrato não diz o que foi comprado, e só uma
parte das vendas da loja tem vínculo com ele: separar as duas coisas dentro do
extrato misturaria venda com doação. A tela de doações identifica o produto e
bate com o extrato em quase todos os pares de mesmo minuto e mensagem. Então:
doação = linha da tela SEM produto; loja = arquivo de vendas.

LIVEPIX E CASTCOIN SÃO EM SEQUÊNCIA. A LivePix termina quando a Castcoin
começa (conferido nos dados, não suposto). As duas
formam uma série só de doações ao vivo, com a troca de plataforma no meio. A
LivePix traz valores observados, não pagamentos confirmados: ela entra no
gráfico com essa legenda, nunca somada à Castcoin num total.

FUSO. Horários da Castcoin vêm em UTC e são convertidos para Brasília (UTC-3;
o Brasil não tem horário de verão desde 2019). A LivePix não tem fuso
comprovado: serve para mês, nunca para hora.

COMPARAR PLATAFORMAS. Cada fonte cobre um período diferente. Total de uma
contra total da outra compara tempo de cobertura, não desempenho. A
comparação entre linhas de receita usa só os meses completos em que TODAS
existem, em média mensal.
"""

from __future__ import annotations

import sqlite3
import statistics as S
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from .familias import _tab

FAIXAS = [(0, 999, "até R$ 9"), (1000, 1999, "R$ 10–19"), (2000, 2999, "R$ 20–29"),
          (3000, 4999, "R$ 30–49"), (5000, 9999, "R$ 50–99"), (10000, 19999, "R$ 100–199"),
          (20000, 49999, "R$ 200–499"), (50000, None, "R$ 500+")]
REDONDOS = [500, 1000, 2000, 5000, 10000]
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
BRASILIA = timedelta(hours=-3)
# tipos de pedido da tela -> nome do produto de valor mínimo no catálogo
TIPO_PRODUTO = {"React": "React", "Música": "Música", "": "Doação simples"}
ROTULO_TIPO = {"React": "React", "Música": "Música", "": "Doação livre"}


def _q(conn, sql, *args):
    return conn.execute(sql, args).fetchall()


def _quartis(vals: list[int]) -> dict:
    if not vals:
        return {}
    v = sorted(vals)
    q = S.quantiles(v, n=20, method="inclusive") if len(v) > 1 else [v[0]] * 19
    return {"p25": q[4], "mediana": S.median(v), "p75": q[14], "p90": q[17]}


def _utc_para_brt(iso: str) -> datetime:
    return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M") + BRASILIA


def _parcial(datas: list[datetime]) -> set[str]:
    """Primeiro e último mês da série, se o dado não cobre o mês inteiro."""
    if not datas:
        return set()
    ini, fim = min(datas), max(datas)
    meses = set()
    if ini.day > 2:
        meses.add(ini.strftime("%Y-%m"))
    prox = (fim.replace(day=28) + timedelta(days=4)).replace(day=1)
    if (prox - fim).days > 2:
        meses.add(fim.strftime("%Y-%m"))
    return meses


def _faixas(vals: list[int]) -> list[dict]:
    total_n, total_v = len(vals), sum(vals)
    saida = []
    for lo, hi, rot in FAIXAS:
        dentro = [v for v in vals if v >= lo and (hi is None or v <= hi)]
        saida.append({"faixa": rot, "n": len(dentro), "pct_n": len(dentro) / total_n if total_n else 0,
                      "pct_valor": sum(dentro) / total_v if total_v else 0})
    return saida


# ---------------------------------------------------------------- doações

def doacoes(conn: sqlite3.Connection) -> dict:
    ui = _tab(conn, "castcoin__suplemento_doacoes_ui")
    lp = _tab(conn, "livepix__suplemento_livepix_mensagens")
    mini = _tab(conn, "01_historico__doacoes_minimos")
    prod = _tab(conn, "01_historico__doacoes_produtos")
    minimo = {n: int(v) for n, v in _q(conn, f'SELECT p.nome, m.valor_centavos FROM "{mini}" m '
                                              f'JOIN "{prod}" p USING (produto_id) WHERE m.tipo_valor = ?', "minimo")}

    cast = [(t, int(v), _utc_para_brt(d), (m or "").strip() != "")
            for t, v, d, m in _q(conn, f'SELECT tipo_exibido, valor_centavos, data_exibida_utc, mensagem '
                                       f'FROM "{ui}" WHERE produto_id_correspondente_nome = \'\'')]
    cast = [c for c in cast if c[1] > 0]
    livep = []
    for v, d in _q(conn, f'SELECT valor_centavos, data_literal_fonte FROM "{lp}" WHERE valor_centavos <> \'\''):
        if int(v) > 0:
            livep.append((int(v), datetime.strptime(d[:10], "%d/%m/%Y")))

    # série mensal
    mensal: dict[tuple[str, str], list[int]] = defaultdict(list)
    for _, v, d, _ in cast:
        mensal[("Castcoin", d.strftime("%Y-%m"))].append(v)
    for v, d in livep:
        mensal[("LivePix", d.strftime("%Y-%m"))].append(v)
    parciais = {"Castcoin": _parcial([c[2] for c in cast]), "LivePix": _parcial([d for _, d in livep])}
    serie = [{"plataforma": p, "mes": m, "n": len(vs), "centavos": sum(vs), "parcial": m in parciais[p]}
             for (p, m), vs in sorted(mensal.items(), key=lambda x: x[0][1])]

    vals_c = [v for _, v, _, _ in cast]
    vals_l = [v for v, _ in livep]

    tipos = []
    for t in ["React", "Música", ""]:
        vs = [v for tt, v, _, _ in cast if tt == t]
        mn = minimo.get(TIPO_PRODUTO[t])
        tipos.append({
            "tipo": ROTULO_TIPO[t], "n": len(vs), "centavos": sum(vs),
            "pct_valor": sum(vs) / sum(vals_c) if vals_c else 0,
            "minimo": mn, **_quartis(vs),
            "pct_no_minimo": (sum(1 for v in vs if v == mn) / len(vs)) if vs and mn else None,
            "pct_abaixo_minimo": (sum(1 for v in vs if v < mn) / len(vs)) if vs and mn else None,
            "pct_abaixo_20": sum(1 for v in vs if v < 2000) / len(vs) if vs else 0,
        })

    grade = Counter((d.weekday(), d.hour) for _, _, d, _ in cast)
    com_msg = [v for _, v, _, m in cast if m]
    sem_msg = [v for _, v, _, m in cast if not m]
    grandes = [v for v in vals_c if v >= 10000]
    return {
        "serie_mensal": serie,
        "castcoin": {"n": len(vals_c), "centavos": sum(vals_c), **_quartis(vals_c),
                     "inicio": min(c[2] for c in cast).date().isoformat(),
                     "fim": max(c[2] for c in cast).date().isoformat()},
        "livepix": {"n": len(vals_l), "centavos": sum(vals_l), **_quartis(vals_l),
                    "inicio": min(d for _, d in livep).date().isoformat(),
                    "fim": max(d for _, d in livep).date().isoformat()},
        "faixas_castcoin": _faixas(vals_c),
        "faixas_livepix": _faixas(vals_l),
        "redondos": [{"valor": r, "pct": sum(1 for v in vals_c if v == r) / len(vals_c)} for r in REDONDOS],
        "tipos": tipos,
        "grandes": {"pct_n": len(grandes) / len(vals_c), "pct_valor": sum(grandes) / sum(vals_c)},
        "mensagem": {"pct_com": len(com_msg) / len(vals_c),
                     "mediana_com": S.median(com_msg) if com_msg else None,
                     "mediana_sem": S.median(sem_msg) if sem_msg else None},
        "hora_dia": [[grade.get((d, h), 0) for h in range(24)] for d in range(7)],
        "dias": DIAS,
    }


# ---------------------------------------------------------------- loja e cursos

def loja(conn: sqlite3.Connection) -> dict:
    v = _tab(conn, "castcoin__suplemento_vendas")
    prod = _tab(conn, "01_historico__doacoes_produtos")
    mini = _tab(conn, "01_historico__doacoes_minimos")
    linhas = _q(conn, f'''SELECT COALESCE(NULLIF(p.nome, ''), '(produto sem nome no catálogo)'),
                                 CAST(m.valor_centavos AS INT), CAST(s.valor_centavos AS INT), s.comprador_id
                          FROM "{v}" s LEFT JOIN "{prod}" p USING (produto_id)
                          LEFT JOIN "{mini}" m USING (produto_id)''')
    por_prod: dict[tuple, list[int]] = defaultdict(list)
    for nome, preco, valor, _ in linhas:
        por_prod[(nome, preco)].append(valor)
    produtos = sorted(({"produto": n, "preco": p, "vendas": len(vs), "centavos": sum(vs),
                        "pct_no_preco": sum(1 for x in vs if x == p) / len(vs) if p else None}
                       for (n, p), vs in por_prod.items()), key=lambda x: -x["centavos"])
    compras = Counter(c for *_, c in linhas if c)
    abaixo = sum(1 for _, p, val, _ in linhas if p and val < p)
    cc = _tab(conn, "shopify__shopify_castcoin_contatos_correspondentes")
    cruzados = _q(conn, f'SELECT COUNT(DISTINCT contato_castcoin_id) FROM "{cc}" '
                        f'WHERE contato_castcoin_id IN (SELECT comprador_id FROM "{v}")')[0][0]
    loja_mes: dict[str, int] = defaultdict(int)
    for dt, val in _q(conn, f'SELECT data_exibida_utc, CAST(valor_centavos AS INT) FROM "{v}"'):
        loja_mes[_utc_para_brt(dt).strftime("%Y-%m")] += val
    castcoin_loja = {
        "mensal": sorted(loja_mes.items()),
        "vendas": len(linhas), "centavos": sum(x[2] for x in linhas), "compradores": len(compras),
        "pct_recompra": sum(1 for n in compras.values() if n >= 2) / len(compras) if compras else 0,
        "abaixo_do_preco": abaixo, "compradores_tambem_shopify": cruzados,
        "produtos": produtos,
    }

    pe = _tab(conn, "shopify__shopify_pedidos")
    it = _tab(conn, "shopify__shopify_itens")
    pagos = _q(conn, f'''SELECT pedido_id, comprador_id, mes_criacao_brasilia,
                                CAST(pagamento_liquido_registrado_loja_centavos AS INT)
                         FROM "{pe}" WHERE situacao_financeira IN ('PAID', 'PARTIALLY_REFUNDED')''')
    ped_por_comp = Counter(c for _, c, _, _ in pagos)
    mensal_s: dict[str, int] = defaultdict(int)
    for _, _, m, val in pagos:
        mensal_s[m] += val
    ids_pagos = {p for p, *_ in pagos}
    tipos_s: dict[str, list[int]] = defaultdict(list)
    for pid, tipo, titulo, val in _q(conn, f'SELECT pedido_id, tipo_produto_origem, titulo, '
                                           f'CAST(total_com_descontos_centavos AS INT) FROM "{it}"'):
        if pid in ids_pagos:
            tipos_s[(tipo or "").strip() or "sem tipo na origem"].append(val)
    shopify = {
        "pedidos_pagos": len(pagos), "centavos": sum(x[3] for x in pagos),
        "compradores": len(ped_por_comp),
        "pct_recompra": sum(1 for n in ped_por_comp.values() if n >= 2) / len(ped_por_comp),
        "distribuicao_pedidos": {k: sum(1 for n in ped_por_comp.values() if (n >= 3 if k == "3+" else n == int(k)))
                                 for k in ["1", "2", "3+"]},
        **_quartis([x[3] for x in pagos]),
        "mensal": sorted(mensal_s.items()),
        "por_tipo": sorted(({"tipo": t, "itens": len(vs), "centavos": sum(vs)} for t, vs in tipos_s.items()),
                           key=lambda x: -x["centavos"]),
        "primeiro_mes": min(mensal_s), "ultimo_mes": max(mensal_s),
    }

    hm = _tab(conn, "hotmart_transacoes__transactions")
    st = _q(conn, f'SELECT status_snapshot, COUNT(*) FROM "{hm}" WHERE is_subscription = \'true\' GROUP BY 1 ORDER BY 2 DESC')
    rec = _q(conn, f'SELECT CAST(recurrency_number AS INT), COUNT(*) FROM "{hm}" '
                   f'WHERE is_subscription = \'true\' GROUP BY 1 ORDER BY 1')
    brl_ok = _q(conn, f'''SELECT substr(order_date_iso_utc, 1, 7), SUM(CAST(gross_value AS REAL)),
                                 is_subscription
                          FROM "{hm}" WHERE gross_currency = 'BRL' AND status_snapshot IN ('COMPLETE', 'APPROVED')
                          GROUP BY 1, 3 ORDER BY 1''')
    total_assin = sum(n for _, n in st)
    hotmart = {
        "assinatura_status": [{"status": s, "n": n} for s, n in st],
        "assinatura_transacoes": total_assin,
        "pct_atrasado": sum(n for s, n in st if s == "OVERDUE") / total_assin if total_assin else 0,
        "renovacoes": [{"parcela": r, "n": n} for r, n in rec],
        "mensal_brl": [{"mes": m, "reais": round(v, 2), "assinatura": a == "true"} for m, v, a in brl_ok],
    }
    return {"castcoin_loja": castcoin_loja, "shopify": shopify, "hotmart": hotmart}


def comparacao_comum(d: dict, lj: dict) -> dict:
    """Média mensal por linha de receita nos meses completos em que todas existem."""
    meses_cast = {s["mes"] for s in d["serie_mensal"] if s["plataforma"] == "Castcoin" and not s["parcial"]}
    meses_shop = {m for m, _ in lj["shopify"]["mensal"]}
    meses_hot = {x["mes"] for x in lj["hotmart"]["mensal_brl"]}
    loja_mes = dict(lj["castcoin_loja"]["mensal"])
    # meses completos: exclui o primeiro mês da Hotmart e o mês corrente
    hot_ord = sorted(meses_hot)
    comuns = sorted((meses_cast & meses_shop & set(hot_ord[1:])) - {max(meses_cast | meses_shop)})
    if not comuns:
        return {"meses": [], "linhas": []}
    doa = {s["mes"]: s["centavos"] for s in d["serie_mensal"] if s["plataforma"] == "Castcoin"}
    shop = dict(lj["shopify"]["mensal"])
    hot = defaultdict(float)
    for x in lj["hotmart"]["mensal_brl"]:
        hot[x["mes"]] += x["reais"]
    k = len(comuns)
    linhas = [
        {"linha": "Doações ao vivo (Castcoin)", "media_reais": sum(doa.get(m, 0) for m in comuns) / 100 / k},
        {"linha": "Loja Shopify", "media_reais": sum(shop.get(m, 0) for m in comuns) / 100 / k},
        {"linha": "Hotmart (assinatura e curso)", "media_reais": sum(hot[m] for m in comuns) / k},
        {"linha": "Loja Castcoin", "media_reais": sum(loja_mes.get(m, 0) for m in comuns) / 100 / k},
    ]
    return {"meses": comuns, "linhas": sorted(linhas, key=lambda x: -x["media_reais"])}


def calcular(conn: sqlite3.Connection) -> dict:
    d = doacoes(conn)
    lj = loja(conn)
    return {"doacoes": d, "loja": lj, "comparacao": comparacao_comum(d, lj)}
