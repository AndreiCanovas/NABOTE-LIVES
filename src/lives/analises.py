"""Página de análises: as frentes 1, 2 e 3, à parte do painel de dados.

O painel (`pagina.py`) serve a quem acompanha a base: status, plano e pedido
de extração. Esta página serve a quem lê os resultados: abre numa visão geral
e cada frente tem a sua aba. As duas páginas usam a mesma folha de estilo.

É SAÍDA com números tirados dos dados: gravada fora do repositório. Os textos
de achados vêm da pasta de trabalho; aqui só há a montagem.
"""

from __future__ import annotations

import re

from .pagina import CABECA, PAGINA, _css_abas, _data_br, _fmt, e, script_dicas

ABAS = [("geral", "Visão geral"), ("frente1", "Frente 1: perfil e preço"),
        ("frente2", "Frente 2: demanda"), ("frente3", "Frente 3: efeito da live")]

# a pergunta de cada frente, como está no plano
PERGUNTAS = {
    "frente1": "Quem compra o quê, como e por quanto?",
    "frente2": "O que o público pede, e o que disso pode virar produto?",
    "frente3": "Quando há live, as doações mudam?",
}


CORES = {"LivePix": "var(--s1)", "Castcoin": "var(--s2)", "Loja Castcoin": "var(--s2)",
         "Shopify": "var(--s3)", "Hotmart": "var(--s4)"}


def _tabela(cab: list[str], linhas: list[list[str]], resumo: str = "Ver os números", aberta: bool = False) -> str:
    th = "".join(f"<th>{e(c)}</th>" for c in cab)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas)
    return (f'<details class="numeros"{" open" if aberta else ""}><summary>{e(resumo)}</summary><div class="tw">'
            f"<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div></details>")


def _legenda(itens: list[tuple[str, str]]) -> str:
    return '<div class="leg">' + "".join(
        f'<span><i style="background:{cor}"></i>{e(n)}</span>' for n, cor in itens) + "</div>"


def _bloco(titulo: str, subtitulo: str, corpo: str) -> str:
    return (f'<div class="bloco"><h2>{e(titulo)}</h2><p class="lead">{subtitulo}</p>{corpo}</div>')


def _ladrilho(rotulo: str, valor: str, nota: str = "") -> str:
    return (f'<div class="ladrilho"><span class="k">{e(rotulo)}</span><span class="v">{e(valor)}</span>'
            f'{f"<span class=n>{e(nota)}</span>" if nota else ""}</div>')


def aba_frente1(f1: dict, achados_html: str) -> str:
    from . import graficos as G
    d, lj, cmp_ = f1["doacoes"], f1["loja"], f1["comparacao"]
    R, P = G.reais, G.pct
    blocos = []

    # 1. série mensal
    pontos = [{"mes": x["mes"], "serie": x["plataforma"], "valor": x["centavos"], "n": x["n"],
               "parcial": x["parcial"]} for x in d["serie_mensal"]]
    tab = _tabela(["Mês", "Plataforma", "Doações", "Valor"],
                  [[G.mes_legivel(p["mes"]) + (" (parcial)" if p["parcial"] else ""), p["serie"],
                    _fmt(p["n"]), R(p["valor"])] for p in pontos])
    blocos.append(_bloco(
        "Doações ao vivo por mês",
        f"LivePix ({G.mes_legivel(d['livepix']['inicio'][:7])} a {G.mes_legivel(d['livepix']['fim'][:7])}, "
        f"valores observados) e Castcoin ({G.mes_legivel(d['castcoin']['inicio'][:7])} a "
        f"{G.mes_legivel(d['castcoin']['fim'][:7])}, pagamentos confirmados). Colunas claras são meses parciais. "
        "Inclui doação livre, React e Música; vendas da loja ficam de fora.",
        _legenda([("LivePix (valor observado)", CORES["LivePix"]), ("Castcoin (pago)", CORES["Castcoin"])])
        + f'<div class="rolagem">{G.colunas_mensais(pontos, CORES)}</div>' + tab))

    # 2. faixas de valor
    fc = d["faixas_castcoin"]
    graf_n = G.barras_h([(f["faixa"], f["pct_n"], P(f["pct_n"])) for f in fc], maximo=max(
        max(x["pct_n"] for x in fc), max(x["pct_valor"] for x in fc)), largura_rotulo=96, W=380,
        cor="var(--accent)")
    graf_v = G.barras_h([(f["faixa"], f["pct_valor"], P(f["pct_valor"])) for f in fc], maximo=max(
        max(x["pct_n"] for x in fc), max(x["pct_valor"] for x in fc)), largura_rotulo=96, W=380,
        cor="var(--accent)")
    fl = {f["faixa"]: f for f in d["faixas_livepix"]}
    tab = _tabela(["Faixa", "Castcoin: % das doações", "Castcoin: % do valor", "LivePix: % das doações", "LivePix: % do valor"],
                  [[f["faixa"], P(f["pct_n"], 1), P(f["pct_valor"], 1), P(fl[f["faixa"]]["pct_n"], 1),
                    P(fl[f["faixa"]]["pct_valor"], 1)] for f in fc])
    blocos.append(_bloco(
        "Quanto vale cada doação",
        f"Castcoin, {_fmt(d['castcoin']['n'])} doações. À esquerda, quantas doações caem em "
        "cada faixa; à direita, quanto do valor total cada faixa traz. A mesma escala nos dois lados.",
        f'<div class="duplo"><div><h3>% das doações</h3>{graf_n}</div><div><h3>% do valor</h3>{graf_v}</div></div>'
        + tab))

    # 3. React, Música e doação livre contra o mínimo
    tipos = [t for t in d["tipos"] if t.get("mediana") is not None]
    graf = G.faixas_quartis([{"rotulo": t["tipo"], "p25": t["p25"], "mediana": t["mediana"], "p75": t["p75"],
                              "minimo": t["minimo"]} for t in tipos])
    tab = _tabela(["Tipo", "Doações", "% do valor", "Mínimo", "Mediana", "Metade paga entre", "No mínimo exato",
                   "Abaixo de R$ 20"],
                  [[t["tipo"], _fmt(t["n"]), P(t["pct_valor"], 1), R(t["minimo"]),
                    R(t["mediana"]), f"{R(t['p25'])} e {R(t['p75'])}", P(t["pct_no_minimo"], 1),
                    P(t["pct_abaixo_20"], 1)] for t in tipos])
    blocos.append(_bloco(
        "Quanto se paga acima do mínimo",
        "Para cada tipo: a faixa onde fica a metade do meio das doações, o ponto na mediana e o traço no "
        "valor mínimo configurado. A tela da Castcoin só identifica React e Música; os demais tipos de "
        "pedido (Anime, Livro, Jogo…) aparecem como doação livre.",
        _legenda([("metade do meio (do 1º ao 3º quartil)", "color-mix(in srgb, var(--accent) 28%, transparent)"),
                  ("mediana", "var(--accent)"), ("mínimo configurado", "var(--fg)")])
        + f'<div class="rolagem">{graf}</div>' + tab))

    # 4. quando
    blocos.append(_bloco(
        "Quando as doações acontecem",
        "Castcoin, por dia da semana e hora de Brasília. Mais escuro é mais doações; a cor é por faixa "
        "(quintis), para uma hora excepcional não apagar as outras. O número exato aparece ao passar o mouse.",
        f'<div class="rolagem">{G.mapa_calor(d["hora_dia"], d["dias"])}</div>'
        + _tabela(["Dia"] + [f"{h}h" for h in range(24)],
                  [[d["dias"][i]] + [str(n) for n in linha] for i, linha in enumerate(d["hora_dia"])])))

    # 5. loja e cursos
    cl, sh, hm = lj["castcoin_loja"], lj["shopify"], lj["hotmart"]
    ladr = "".join([
        _ladrilho("Loja Castcoin", f"{cl['vendas']} vendas",
                  f"{cl['compradores']} compradores · {P(cl['pct_recompra'])} compraram mais de uma vez"),
        _ladrilho("Compradores da loja Castcoin também na Shopify", P(cl["compradores_tambem_shopify"] / cl["compradores"]),
                  f"{cl['compradores_tambem_shopify']} de {cl['compradores']}, pelo e-mail pseudonimizado"),
        _ladrilho("Shopify", f"{_fmt(sh['pedidos_pagos'])} pedidos pagos",
                  f"{sh['compradores']} compradores · {P(sh['pct_recompra'])} recompraram · mediana {R(sh['mediana'])}"),
        _ladrilho("Assinatura na Hotmart", f"{hm['assinatura_transacoes']} cobranças",
                  f"{P(hm['pct_atrasado'])} em atraso (OVERDUE)"),
    ])
    meses = sorted({m for m, _ in sh["mensal"]} | {m for m, _ in cl["mensal"]}
                   | {x["mes"] for x in hm["mensal_brl"]})
    ultimos = [m for m in meses if m >= max(meses[-17:][0], "0000")][-17:]
    hot = {}
    for x in hm["mensal_brl"]:
        hot[x["mes"]] = hot.get(x["mes"], 0) + x["reais"] * 100
    series = {"Shopify": dict(sh["mensal"]), "Hotmart": hot, "Loja Castcoin": dict(cl["mensal"])}
    graf_l = G.linhas_mensais(series, CORES, ultimos)
    tab_l = _tabela(["Mês", "Shopify", "Hotmart", "Loja Castcoin"],
                    [[G.mes_legivel(m), R(series["Shopify"].get(m, 0)), R(hot.get(m, 0)),
                      R(series["Loja Castcoin"].get(m, 0))] for m in ultimos])
    comp = ""
    if cmp_["meses"]:
        maxi = max(x["media_reais"] for x in cmp_["linhas"])
        comp = (f'<h3>Média mensal por linha de receita, nos meses completos em que todas existem '
                f'({", ".join(G.mes_legivel(m) for m in cmp_["meses"])})</h3>'
                + G.barras_h([(x["linha"], x["media_reais"], R(x["media_reais"], False)) for x in cmp_["linhas"]],
                             maximo=maxi, largura_rotulo=210, W=560, cor="var(--accent)"))
    prods = _tabela(["Produto (loja Castcoin)", "Preço", "Vendas", "Valor", "Pago no preço exato"],
                    [[e(p["produto"]), R(p["preco"]) if p["preco"] else "—", str(p["vendas"]), R(p["centavos"]),
                      P(p["pct_no_preco"]) if p["pct_no_preco"] is not None else "—"] for p in cl["produtos"]],
                    "Ver produtos da loja Castcoin")
    blocos.append(_bloco(
        "Loja, cursos e assinatura",
        f"Vendas a preço fixo, fora das lives: loja da Castcoin, Shopify e a assinatura na Hotmart. O último mês "
        f"({G.mes_legivel(ultimos[-1])}) é parcial. Cada fonte cobre um período diferente; por isso a comparação "
        "entre elas usa só os meses completos em comum.",
        f'<div class="ladrilhos">{ladr}</div>'
        + _legenda([(n, CORES[n]) for n in series])
        + f'<div class="rolagem">{graf_l}</div>' + tab_l + comp + prods))

    return f"""
<section class="panel" id="p-frente1">
  <p class="lead">{e(PERGUNTAS['frente1'])} Doações ao vivo (Castcoin e LivePix, uma depois da outra), loja da Castcoin, Shopify e assinatura na Hotmart.</p>
  {f'<div class="achados"><h2>O que os números dizem</h2>{achados_html}</div>' if achados_html else ''}
  {''.join(blocos)}
</section>"""


def _por_minuto(v: float) -> str:
    """Preço por minuto: inteiro a partir de R$ 10 (a divisão valor ÷ duração tem ruído de centavos)."""
    return f"R$ {v:.0f}" if v >= 10 or abs(v - round(v)) < 0.05 else f"R$ {v:.2f}".replace(".", ",")


def _troca_de_preco(precos: list[dict]) -> dict | None:
    """Última mudança do preço por minuto do React: variação de mais de 10% entre meses seguidos."""
    rs = [p for p in precos if p["tipo"] == "React" and p["reais_por_minuto"]]
    for ant, dep in reversed(list(zip(rs, rs[1:]))):
        if abs(dep["reais_por_minuto"] - ant["reais_por_minuto"]) > 0.1 * ant["reais_por_minuto"]:
            return {"antes": ant, "depois": dep}
    return None


def ladrilhos_frente2(f2: dict) -> list[str]:
    from . import graficos as G
    R, P = G.reais, G.pct
    md, lt = f2["midia"], f2["leitura"]
    comp = {p: {c["intencao"]: c for c in v["composicao"]} for p, v in f2["por_plataforma"].items()}
    pede = {p: c["pedido"]["fracao"] + c["pergunta"]["fracao"] for p, c in comp.items()}
    troca = _troca_de_preco(md["precos"])
    lives_lidas = sum(1 for l in lt["por_live"] if l["testaveis"])
    ladr = [_ladrilho("Pedidos e perguntas", f"{P(pede.get('Castcoin', 0))} das mensagens",
                      f"na Castcoin; na LivePix eram {P(pede.get('LivePix', 0))}")]
    if troca:
        a, d = troca["antes"], troca["depois"]
        ladr.append(_ladrilho("React cobrado por minuto de vídeo",
                              f"{_por_minuto(a['reais_por_minuto'])} → {_por_minuto(d['reais_por_minuto'])}",
                              f"em {G.mes_legivel(d['mes'])}; pedidos de React no mês: {a['n']} em "
                              f"{G.mes_legivel(a['mes'])}, {d['n']} em {G.mes_legivel(d['mes'])}"))
    ladr.append(_ladrilho("Mesmo vídeo, várias pessoas", f"{md['repetidos_itens']} vídeos",
                          f"pedidos 2 vezes ou mais, somando {md['repetidos_pedidos']} pedidos; "
                          f"o mais pedido, {md['repetidos_max']} vezes"))
    if lt["testaveis"]:
        ladr.append(_ladrilho("Lidas em voz alta na live", f"{P(lt['taxa'])} das mensagens",
                              f"em {lives_lidas} lives transcritas; ao acaso daria {P(lt['taxa_controle'])}; "
                              f"atraso mediano de {lt['atraso_mediano']:.0f} min"))
    return ladr


def aba_frente2(f2: dict, achados_html: str) -> str:
    from . import graficos as G
    R, P = G.reais, G.pct
    pp, md, lt, tm = f2["por_plataforma"], f2["midia"], f2["leitura"], f2["temas"]
    comp = {p: {c["intencao"]: c for c in v["composicao"]} for p, v in pp.items()}
    pede = {p: c["pedido"]["fracao"] + c["pergunta"]["fracao"] for p, c in comp.items()}
    per = {p: f"{G.mes_legivel(a)} a {G.mes_legivel(b)}" for p, (a, b) in f2["periodo"].items()}
    troca = _troca_de_preco(md["precos"])

    ladr = ladrilhos_frente2(f2)
    blocos = []

    # 1. intenção
    mx = max(c["fracao"] for v in pp.values() for c in v["composicao"])
    graf = "".join(
        f'<div><h3>{e(p)} · {e(per[p])} · {_fmt(pp[p]["n"])} mensagens</h3><div class="rolagem">'
        + G.barras_h([(c["rotulo"], c["fracao"], P(c["fracao"])) for c in pp[p]["composicao"]],
                     maximo=mx, cor=CORES[p], largura_rotulo=230, W=440) + "</div></div>"
        for p in ("Castcoin", "LivePix") if p in pp)
    plats = [p for p in ("Castcoin", "LivePix") if p in pp]
    tab = _tabela(["Intenção"] + [f"{p}: {c}" for p in plats for c in ("mensagens", "% das mensagens", "% do valor", "mediana")],
                  [[e(ROT)] + [x for p in plats for x in (
                      _fmt(comp[p][k]["n"]), P(comp[p][k]["fracao"]), P(comp[p][k]["fracao_valor"]),
                      R(comp[p][k]["mediana"]))] for k, ROT in ((k, comp[plats[0]][k]["rotulo"]) for k in comp[plats[0]])])
    cm = f2["comentarios"]
    cm_c = {i["intencao"]: i["n"] for i in cm["intencoes"]}
    nota_cm = (f" Nos comentários do canal ({cm['n']} com texto, em {cm['videos']} vídeos), "
               f"{cm_c.get('pedido', 0) + cm_c.get('pergunta', 0)} são pedidos ou perguntas.") if cm["n"] else ""
    blocos.append(_bloco(
        "Para que servem as mensagens pagas",
        "Cada mensagem recebe uma intenção, por regras de texto: mídia (traz link), pedido explícito "
        "(\"fala sobre\", \"joga\", \"pode explicar\", \"vai ter…?\"), pergunta, apoio e comentário. As duas "
        "plataformas vêm em sequência e ficam separadas. A regra erra: os números valem como ordem de grandeza."
        + nota_cm,
        f'<div class="duplo">{graf}</div>' + tab))

    # 2. formato
    fm = [f for f in f2["formatos"] if f["n"]]
    def _prod(f):
        if not f["produtos"]:
            return "nenhum"
        return "; ".join(f"{e(p['nome'])} ({'mín. ' if p['tipo_valor'] == 'minimo' else ''}{R(p['centavos'])})"
                         for p in f["produtos"][:3]) + (f" e mais {len(f['produtos']) - 3}" if len(f["produtos"]) > 3 else "")
    graf = G.barras_h([(f["formato"], f["n"], _fmt(f["n"]) + ("" if f["produtos"] else " · sem produto"))
                       for f in fm], largura_rotulo=230, W=560)
    tab = _tabela(["Formato", "Pedidos", "Castcoin", "Castcoin por doação livre", "LivePix", "Mediana paga",
                   "Produto no catálogo"],
                  [[e(f["formato"]), _fmt(f["n"]), _fmt(f["castcoin_n"]), _fmt(f["castcoin_via_livre"]),
                    _fmt(f["por_plataforma"]["LivePix"]), R(f["mediana"]), _prod(f)] for f in fm])
    blocos.append(_bloco(
        "O que pedem, por formato",
        "Pedidos, perguntas e links, separados pelo tipo de coisa pedida. Uma mensagem pode cair em mais de um "
        "formato. \"Castcoin por doação livre\" conta quem pediu pela doação comum, sem usar o produto. "
        "Formato sem produto no catálogo é candidato a produto novo.",
        f'<div class="rolagem">{graf}</div>' + tab))

    # 3. temas: demanda × oferta
    linhas = [l for l in tm["linhas"] if l["n"] or l["lives"]]
    if linhas and f2.get("lexico_carregado"):
        cores = ("var(--accent)", "var(--eixo)")
        graf = G.halteres([(l["tema"], l["demanda"], l["oferta"]) for l in linhas],
                          ("Pedidos e perguntas", "Lives"), cores)
        tab = _tabela(["Tema", "Pedidos e perguntas", "% da demanda", "Lives", "% das lives", "Diferença"],
                      [[e(l["tema"]), _fmt(l["n"]), P(l["demanda"], 1), _fmt(l["lives"]), P(l["oferta"], 1),
                        f"{100 * l['diferenca']:+.1f} p.p.".replace(".", ",")] for l in linhas])
        blocos.append(_bloco(
            "Temas: o que se pede e o que a live oferece",
            f"Para cada tema, a parte que ele tem nos pedidos e perguntas ({_fmt(tm['com_tema'])} de "
            f"{_fmt(tm['pedidos_perguntas'])} mensagens caíram em algum tema) e a parte que tem nas lives "
            f"({_fmt(tm['lives_com_tema'])} lives com tema identificado pelo título). Ponto à direita do cinza: o "
            "público pede mais do que a live oferece. Leitura indicativa: a mensagem é classificada por palavras, a "
            "live pelo título.",
            _legenda([("Pedidos e perguntas", cores[0]), ("Lives", cores[1])])
            + f'<div class="rolagem">{graf}</div>' + tab))

    # 4. fila de demanda: grupos candidatos
    if f2["grupos"]:
        def _como(g):
            return ", ".join(f"{k} {v}" for k, v in sorted(g["intencoes"].items(), key=lambda kv: -kv[1]))
        tab = _tabela(["Termo", "Mensagens", "Valor", "Meses com menção", "Período", "Como aparece", "Tema"],
                      [[e(g["termo"]), _fmt(g["n"]), R(g["centavos"]), str(g["meses"]),
                        f"{G.mes_legivel(g['de'])} a {G.mes_legivel(g['ate'])}" if g["de"] else "—",
                        e(_como(g)), e(", ".join(g["temas"]) or "—")] for g in f2["grupos"]],
                      resumo="Ver a lista", aberta=True)
        blocos.append(_bloco(
            "Fila de demanda: assuntos que voltam (a confirmar)",
            "Palavras e pares de palavras que mais aparecem em pedidos, perguntas e links, contando cada mensagem "
            "uma vez. É a matéria-prima da fila de demanda: o time confirma quais viram grupo e qual produto "
            "atenderia cada um. As plataformas não identificam quem doou em cada mensagem, então a lista conta "
            "mensagens, não pessoas.",
            tab))

    # 5. React e Música: preço por minuto
    rc = [p for p in md["precos"] if p["tipo"] == "React"]
    if rc:
        pts = [(G.mes_legivel(p["mes"]), p["n"],
                f"{G.mes_legivel(p['mes'])}: {p['n']} pedidos de React, {R(p['centavos'])}"
                + (f", tabela de {_por_minuto(p['reais_por_minuto'])} por minuto" if p["reais_por_minuto"] else ""))
               for p in rc]
        marca = next((i for i, p in enumerate(rc) if troca and p["mes"] == troca["depois"]["mes"]), None)
        rot = (f"{_por_minuto(troca['antes']['reais_por_minuto'])} → "
               f"{_por_minuto(troca['depois']['reais_por_minuto'])} por minuto") if troca else ""
        graf = G.colunas_simples(pts, marca_x=marca, rotulo_marca=rot, rotulos_cada=1, fmt=lambda v: f"{v:.0f}",
                                 inteiros=True)
        tab = _tabela(["Mês", "Tipo", "Pedidos", "Valor", "Minutos pagos", "Preço por minuto (tabela)",
                       "Pedidos no preço da tabela", "Duração mediana"],
                      [[G.mes_legivel(p["mes"]), p["tipo"], _fmt(p["n"]), R(p["centavos"]), _fmt(round(p["minutos"])),
                        _por_minuto(p["reais_por_minuto"]) if p["reais_por_minuto"] else "—", P(p["na_moda"]),
                        f"{p['duracao_mediana_s'] / 60:.1f} min".replace(".", ",") if p["duracao_mediana_s"] else "—"]
                       for p in md["precos"]])
        blocos.append(_bloco(
            "React e Música: preço por minuto de vídeo e volume",
            "Na fila de mídia, o valor pago dividido pela duração paga dá o preço por segundo de cada pedido. Em cada "
            "mês, o preço mais comum é tomado como a tabela vigente; quem paga o mínimo por um vídeo curto ou dá "
            "gorjeta fica fora dela. A tabela é inferida dos dados e precisa da confirmação dos administradores. "
            "Atenção: o volume também depende de quantas lives houve no mês.",
            f'<div class="rolagem">{graf}</div>' + tab))

    # 6. origem dos vídeos e situação da fila
    og = md["origens"]
    graf = G.barras_h([(o["origem"], o["n"], _fmt(o["n"])) for o in og], largura_rotulo=150, W=460)
    tab = _tabela(["Origem do link", "Pedidos", "React", "Música", "Mediana paga"],
                  [[e(o["origem"]), _fmt(o["n"]), _fmt(o["react"]), _fmt(o["musica"]), R(o["mediana"])] for o in og])
    est = _tabela(["Tipo", "Situação na fila", "Pedidos", "Valor"],
                  [[e(x["tipo"]), e(x["estado"]), _fmt(x["n"]), R(x["centavos"])] for x in md["estados"]],
                  resumo="Situação dos pedidos na fila")
    blocos.append(_bloco(
        "De onde vêm os vídeos pedidos",
        f"{_fmt(md['n'])} pedidos de React e Música na fila, de {G.mes_legivel(md['de'])} a "
        f"{G.mes_legivel(md['ate'])}, para {_fmt(md['itens'])} vídeos diferentes. {md['repetidos_itens']} vídeos foram "
        f"pedidos mais de uma vez ({md['repetidos_pedidos']} pedidos), o que é um pedido coletivo feito sem "
        f"ferramenta. {md['proprios']} pedidos apontam para vídeos do próprio canal.",
        f'<div class="rolagem">{graf}</div>' + tab + est))

    # 7. leitura na live e fuso da LivePix
    if lt["testaveis"]:
        fz = f2["fuso_livepix"]
        pts = [(f"UTC{t['utc_mais']:+d}".replace("+0", "±0"), t["lidas"],
                f"Se o horário da LivePix fosse UTC{t['utc_mais']:+d}: {t['lidas']} de {t['na_live']} mensagens "
                "dentro de live casariam com a fala") for t in fz["testes"]]
        graf_fz = G.colunas_simples(pts, rotulos_cada=1, fmt=lambda v: f"{v:.0f}", inteiros=True)
        tab = _tabela(["Live (mês)", "Horas", "Mensagens durante a live", "Testáveis", "Lidas", "Casaram ao acaso"],
                      [[G.mes_legivel(l["mes"]), f"{l['horas']:.1f}".replace(".", ","), str(l["mensagens"]),
                        str(l["testaveis"]), str(l["lidas"]), str(l["controle"])] for l in lt["por_live"]])
        c = lt["criterio"]
        blocos.append(_bloco(
            "A live lê as mensagens pagas?",
            f"Nas {lt['lives']} lives com transcrição e início real, uma mensagem conta como lida quando pelo menos "
            f"{P(c['limiar'])} das suas palavras aparecem na fala entre {c['antes_min']} minutos antes e "
            f"{c['depois_min']} minutos depois dela. Mensagens com menos de {c['min_palavras']} palavras ficam de "
            f"fora. A mesma conta, longe da mensagem, mede o acaso. Lidas: {lt['lidas']} de {lt['testaveis']} "
            f"({P(lt['taxa'])}); ao acaso: {lt['controle']}. Mediana paga: {R(lt['mediana_lidas'])} entre as lidas e "
            f"{R(lt['mediana_nao_lidas'])} entre as não lidas. Amostra pequena: leitura indicativa.",
            tab + "<h3>O fuso da LivePix, testado contra a fala</h3>"
            "<p class=\"lead\">O arquivo da LivePix não diz o fuso. Cada hipótese de fuso põe as mensagens num "
            "minuto diferente; a certa é a que faz mais mensagens casarem com a fala das lives transcritas.</p>"
            + f'<div class="rolagem">{graf_fz}</div>'))

    return f"""
<section class="panel" id="p-frente2">
  <p class="lead">O que o público pede? Leitura das mensagens pagas da Castcoin ({e(per.get('Castcoin', '—'))}) e da LivePix ({e(per.get('LivePix', '—'))}), lado a lado e nunca somadas, mais a fila de React e Música e as transcrições das lives. {_fmt(f2['mensagens'])} mensagens com texto. Tudo agregado: nenhuma mensagem é reproduzida aqui.</p>
  {f'<div class="achados"><h2>O que os números dizem</h2>{achados_html}</div>' if achados_html else ''}
  <div class="ladrilhos">{''.join(ladr)}</div>
  {''.join(blocos)}
</section>"""


CORES_F3 = {"Live registrada": "var(--s3)", "Provável live sem registro": "var(--s4)",
            "Sem sinal de live": "var(--eixo)"}


def ladrilhos_frente3(f3: dict) -> list[str]:
    from . import graficos as G
    R, P = G.reais, G.pct
    x = lambda v: f"{v:.1f}×".replace(".", ",")  # noqa: E731
    el, ec, su = f3["esperado_limpo"], f3["esperado"], f3["suspeitas"]
    total_n = f3["doacoes"]
    meses_sus = sorted(su["por_mes"].items(), key=lambda kv: -kv[1])
    principais = [G.mes_legivel(m) for m, n in meses_sus if n >= max(1, su["noites"] * 0.25)]
    return [
        _ladrilho("Lives registradas", f"{P(f3['dentro']['pct_tempo'])} do tempo",
                  f"concentram {P(f3['dentro']['pct_n'])} das doações e {P(f3['dentro']['pct_valor'])} do valor"),
        _ladrilho("Efeito da live, na mesma hora do dia", f"{x(el['efeito_n'])} doações",
                  f"{x(el['efeito_valor'])} no valor · conservador: {x(ec['efeito_n'])} e {x(ec['efeito_valor'])}"),
        _ladrilho("Ritmo", f"{R(f3['taxa']['live_reais_h'], False)} por hora",
                  f"durante a live; {R(f3['taxa']['fora_reais_h'], False)} por hora nas horas sem sinal de live"),
        _ladrilho("Provável live sem registro", f"{su['noites']} noites",
                  f"{_fmt(su['n'])} doações ({P(su['n'] / total_n)} da janela)"
                  + (f", sobretudo {' e '.join(principais)}" if principais else "")),
    ]


def aba_frente3(f3: dict, achados_html: str) -> str:
    from . import graficos as G
    R, P = G.reais, G.pct
    x = lambda v: f"{v:.1f}×".replace(".", ",")  # noqa: E731
    ja, el, ec, su = f3["janela"], f3["esperado_limpo"], f3["esperado"], f3["suspeitas"]
    total_n = f3["doacoes"]
    meses_sus = sorted(su["por_mes"].items(), key=lambda kv: -kv[1])
    principais = [G.mes_legivel(m) for m, n in meses_sus if n >= max(1, su["noites"] * 0.25)]
    ladr = "".join(ladrilhos_frente3(f3))
    blocos = []

    # 1. ritmo por hora do dia, nas três condições
    ordem = list(range(12, 24)) + list(range(0, 6))   # do meio-dia às 5h: fora disso quase não há doação
    ph = {h["hora"]: h for h in f3["por_hora"]}
    series = {"Live registrada": [ph[h]["live_n_h"] for h in ordem],
              "Provável live sem registro": [ph[h]["suspeita_n_h"] for h in ordem],
              "Sem sinal de live": [ph[h]["fora_n_h"] for h in ordem]}
    xs = [f"{h}h" for h in ordem]
    tab = _tabela(["Hora (Brasília)", "Live registrada", "Provável live sem registro", "Sem sinal de live"],
                  [[f"{h}h"] + [("—" if v is None else f"{v:.2f}".replace(".", ",")) for v in
                                (ph[h]["live_n_h"], ph[h]["suspeita_n_h"], ph[h]["fora_n_h"])] for h in ordem])
    blocos.append(_bloco(
        "Doações por hora, na mesma hora do dia",
        "Quantas doações acontecem por hora em cada condição, hora a hora (Brasília), do meio-dia às 5h. "
        "Comparar na mesma hora tira o efeito de a doação ser noturna. Hora sem exposição suficiente fica sem ponto.",
        _legenda(list(CORES_F3.items())) + f'<div class="rolagem">{G.linhas_categoricas(series, CORES_F3, xs, rotulo_y="doações por hora")}</div>' + tab))

    # 2. perfil desde o início da live
    pts = [(f"{p['min'] // 60:+d}h" if p["min"] % 60 == 0 else "", p["doacoes_por_live"] or 0,
            f"{p['min']:+d} min do início: {str(round(p['doacoes_por_live'] or 0, 2)).replace('.', ',')} doações por live "
            f"({p['lives']} lives ainda no ar)") for p in f3["perfil_inicio"]]
    zero = next(i for i, p in enumerate(f3["perfil_inicio"]) if p["min"] == 0)
    tab = _tabela(["Minutos desde o início", "Doações por live (15 min)", "Lives no ar"],
                  [[f"{p['min']:+d}", f"{(p['doacoes_por_live'] or 0):.2f}".replace(".", ","), str(p["lives"])]
                   for p in f3["perfil_inicio"]])
    blocos.append(_bloco(
        "O que acontece depois que a live começa",
        "Média de doações por live em cada bloco de 15 minutos, contada só entre as lives ainda no ar. "
        "Atenção: as lives começam em horários parecidos, então o crescimento ao longo da live se mistura com a "
        "chegada da noite; este gráfico mostra o ritmo, não separa as duas causas.",
        f'<div class="rolagem">{G.colunas_simples([(r, v, d) for r, v, d in pts], marca_x=zero, rotulo_marca="início da live")}</div>' + tab))

    # 3. temas
    if f3["temas"]:
        mx = max(t["reais_por_hora"] for t in f3["temas"])
        graf = G.barras_h([(f"{t['tema']} ({t['lives']})", t["reais_por_hora"], R(t["reais_por_hora"], False) + "/h")
                           for t in f3["temas"]], maximo=mx, largura_rotulo=300, W=620)
        tab = _tabela(["Tema principal (pelo título)", "Lives", "Horas no ar", "Doações", "Valor", "Valor por hora"],
                      [[e(t["tema"]), str(t["lives"]), f"{t['horas']:.0f}", _fmt(t["n"]), R(t["centavos"]),
                        R(t["reais_por_hora"], False)] for t in f3["temas"]])
        blocos.append(_bloco(
            "Valor por hora de live, por tema",
            f"Tema principal classificado pelo título da live; entre parênteses, quantas lives. Só temas com "
            f"{f3['temas_min_lives']} lives ou mais. Leitura indicativa: poucas lives por tema, e tema se mistura "
            "com dia, horário e convidado.",
            f'<div class="rolagem">{graf}</div>' + tab))

    # 4. lives sem registro, por mês
    if su["por_mes"]:
        mx = max(su["por_mes"].values())
        graf = G.barras_h([(G.mes_legivel(m), n, f"{n} noite" + ("s" if n != 1 else ""))
                           for m, n in su["por_mes"].items()],
                          maximo=mx, largura_rotulo=80, W=420)
        blocos.append(_bloco(
            "Noites com cara de live, sem live registrada",
            f"Noites sem live no catálogo, mas com {su['criterio']['react']} ou mais pedidos de React ou "
            f"{su['criterio']['doacoes']} ou mais doações. Ficaram fora da linha de base e entraram como pedido de "
            "dados: o catálogo de lives desses meses parece incompleto.",
            f'<div class="rolagem">{graf}</div>'))

    return f"""
<section class="panel" id="p-frente3">
  <p class="lead">A live move as doações? Cruzamento do minuto de cada doação da Castcoin com o horário de cada live, de {G.mes_legivel(ja['inicio'][:7])} a {G.mes_legivel(ja['fim'][:7])}: os meses em que toda live conhecida tem início e fim registrados. {f3['lives']} lives, {_fmt(total_n)} doações. Tudo agregado.</p>
  {f'<div class="achados"><h2>O que os números dizem</h2>{achados_html}</div>' if achados_html else ''}
  <div class="ladrilhos">{ladr}</div>
  {''.join(blocos)}
</section>"""


# ---------------------------------------------------------------- visão geral

def ladrilhos_frente1(f1: dict) -> list[str]:
    from . import graficos as G
    R, P = G.reais, G.pct
    d, lj = f1["doacoes"], f1["loja"]
    grandes = [f for f in d["faixas_castcoin"] if _piso(f["faixa"]) >= 10000]
    tipos = {t["tipo"]: t for t in d["tipos"] if t.get("mediana") is not None}
    grade = d["hora_dia"]
    total = sum(sum(l) for l in grade) or 1
    noite = sum(l[h] for l in grade for h in (18, 19, 20, 21, 22, 23, 0)) / total
    saida = []
    if grandes:
        saida.append(_ladrilho("Doações de R$ 100 ou mais", f"{P(sum(f['pct_n'] for f in grandes))} das doações",
                               f"trazem {P(sum(f['pct_valor'] for f in grandes))} do valor (Castcoin)"))
    if "React" in tipos:
        t = tipos["React"]
        nota = f"mínimo de {R(t['minimo'])}"
        if "Música" in tipos:
            nota += f"; na Música, mediana de {R(tipos['Música']['mediana'])}"
        saida.append(_ladrilho("React: mediana paga", R(t["mediana"]), nota))
    saida.append(_ladrilho("Doação à noite", f"{P(noite)} das doações", "entre 18h e 1h (Brasília), na Castcoin"))
    sh, cl = lj["shopify"], lj["castcoin_loja"]
    saida.append(_ladrilho("Compradores que voltam", P(sh["pct_recompra"]),
                           f"na Shopify; {P(cl['pct_recompra'])} na loja da Castcoin"))
    return saida


def _piso(faixa: str) -> int:
    """Primeiro valor em reais do rótulo da faixa ('R$ 100–199' -> 10000 centavos; 'até R$ 9' -> 0)."""
    if faixa.strip().lower().startswith("até"):
        return 0
    m = re.search(r"(\d[\d.]*)", faixa)
    return int(m.group(1).replace(".", "")) * 100 if m else 0


def _manchetes(achados_html: str) -> list[str]:
    """Os títulos em negrito de cada achado ('<li><b>…</b>')."""
    return [re.sub(r"[.:]\s*$", "", t.strip()) for t in re.findall(r"<li>\s*<b>(.*?)</b>", achados_html or "", re.S)]


def _escopo(chave: str, f: dict) -> str:
    from . import graficos as G
    if chave == "frente1":
        d = f["doacoes"]
        return (f"Castcoin de {G.mes_legivel(d['castcoin']['inicio'][:7])} a {G.mes_legivel(d['castcoin']['fim'][:7])}, "
                f"LivePix de {G.mes_legivel(d['livepix']['inicio'][:7])} a {G.mes_legivel(d['livepix']['fim'][:7])}, "
                "mais a loja, a Shopify e a assinatura na Hotmart.")
    if chave == "frente2":
        per = {p: f"{G.mes_legivel(a)} a {G.mes_legivel(b)}" for p, (a, b) in f["periodo"].items()}
        return (f"{_fmt(f['mensagens'])} mensagens pagas com texto (Castcoin {per.get('Castcoin', '—')}, LivePix "
                f"{per.get('LivePix', '—')}), a fila de React e Música e as transcrições das lives.")
    ja = f["janela"]
    return (f"{f['lives']} lives e {_fmt(f['doacoes'])} doações da Castcoin, de {G.mes_legivel(ja['inicio'][:7])} a "
            f"{G.mes_legivel(ja['fim'][:7])}: os meses em que toda live tem horário registrado.")


def aba_geral(frentes: dict[str, tuple[dict | None, str]]) -> str:
    funcoes = {"frente1": ladrilhos_frente1, "frente2": ladrilhos_frente2, "frente3": ladrilhos_frente3}
    partes = []
    for chave, rotulo in ABAS[1:]:
        f, achados = frentes.get(chave, (None, ""))
        if not f:
            continue
        manchetes = _manchetes(achados)
        lista = ("<ul class=\"manchetes\">" + "".join(f"<li>{m}</li>" for m in manchetes) + "</ul>") if manchetes else ""
        partes.append(
            f'<div class="bloco"><h2>{e(rotulo)}</h2>'
            f'<p class="lead"><b>{e(PERGUNTAS[chave])}</b> {e(_escopo(chave, f))}</p>'
            f'<div class="ladrilhos">{"".join(funcoes[chave](f))}</div>{lista}'
            f'<label class="ir" for="r-{chave}">Ver a análise completa</label></div>')
    return f"""
<section class="panel" id="p-geral">
  <p class="lead">Um resumo de cada frente: os números principais e o que eles dizem. Os gráficos, as tabelas e os cuidados de leitura estão na aba de cada frente.</p>
  {''.join(partes)}
</section>"""


def montar(f1: dict | None, achados1: str, f2: dict | None, achados2: str, f3: dict | None, achados3: str,
           gerado_em: str) -> str:
    css = (PAGINA / "estilo.css").read_text(encoding="utf-8") + _css_abas(ABAS)
    radios = "".join(f'<input type="radio" name="aba" id="r-{a}" class="sr"{" checked" if i == 0 else ""}>\n'
                     for i, (a, _) in enumerate(ABAS))
    rotulos = "".join(f'<label class="tab" for="r-{a}">{e(r)}</label>' for a, r in ABAS)
    vazio = lambda a: f'<section class="panel" id="p-{a}"><p class="lead">Em preparação.</p></section>'  # noqa: E731
    return f"""<title>Análises Lives e Doações</title>
{CABECA}
<style>
{css}</style>

<div class="wrap">
{radios}<header>
  <div class="eyebrow">Projeto lives × doações · análises exploratórias</div>
  <h1>Análises de lives e doações</h1>
  <p class="lead">Primeiras leituras das frentes 1, 2 e 3, feitas com o histórico entregue pelos administradores. Tudo agregado: nenhum dado individual. Os gráficos mostram detalhes ao passar o mouse, e cada um tem a tabela com os números logo abaixo.</p>
  <div class="tabs">{rotulos}</div>
</header>
{aba_geral({"frente1": (f1, achados1), "frente2": (f2, achados2), "frente3": (f3, achados3)})}
{aba_frente1(f1, achados1) if f1 else vazio("frente1")}
{aba_frente2(f2, achados2) if f2 else vazio("frente2")}
{aba_frente3(f3, achados3) if f3 else vazio("frente3")}
<footer>Números agregados, sem nenhum dado individual. Os dados ficam na pasta restrita e na pasta de trabalho; nunca em repositório. Gerado em {e(_data_br(gerado_em))}.</footer>
</div>

{script_dicas(ABAS)}"""
