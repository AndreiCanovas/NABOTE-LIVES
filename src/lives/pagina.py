"""A página compartilhada com administradores e analistas.

Junta três coisas que mudam em ritmos diferentes:

- o status dos dados, calculado do banco (`status.py`);
- o plano, convertido do documento (`doc_html.py`), que é a fonte da verdade;
- o prompt e o resumo do pedido de extração, que são texto fixo (`pagina/`).

A página é SAÍDA: traz contagens tiradas dos dados, então é gravada fora do
repositório. As abas funcionam sem JavaScript (rádio + rótulo), porque alguns
visualizadores de arquivo não executam script; o único script é o botão de
copiar o prompt, que tem alternativa manual.
"""

from __future__ import annotations

import html
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PAGINA = RAIZ / "pagina"

FRENTES = {1: "Perfil e preço", 2: "Demanda", 3: "Efeito da live", 4: "Proxy"}
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

# Estado do projeto, não dos dados: atualizar aqui quando uma fase muda.
ANDAMENTO = [
    ("Fase 0", "Inventário dos dados", "feito"),
    ("Fase 1", "Base de dados e status", "feito"),
    ("Fase 2", "Frente 1: perfil e preço", "feito"),
    ("Fase 3", "Frente 2: demanda", "agora"),
    ("Fase 4", "Frente 3: efeito da live", "feito"),
    ("Fase 5", "Frente 4 e testes", ""),
]

ABAS = [("status", "Status dos dados"), ("frente1", "Frente 1: perfil e preço"),
        ("frente2", "Frente 2: demanda"), ("frente3", "Frente 3: efeito da live"), ("doc", "Documentação"),
        ("prompt", "Prompt para os administradores"), ("resumo", "Resumo para analistas")]

e = html.escape


def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _data_br(iso: str) -> str:
    return f"{int(iso[8:10])} {MESES[int(iso[5:7]) - 1]} {iso[:4]}"


def _meses(aaaa_mm_dd: str) -> int:
    return int(aaaa_mm_dd[:4]) * 12 + int(aaaa_mm_dd[5:7])


def _css_abas() -> str:
    ativo = ",".join(f'#r-{a}:checked ~ header label[for="r-{a}"]' for a, _ in ABAS)
    foco = ",".join(f'#r-{a}:focus-visible ~ header label[for="r-{a}"]' for a, _ in ABAS)
    painel = ",".join(f"#r-{a}:checked ~ #p-{a}" for a, _ in ABAS)
    return (f"{ativo}{{color:var(--accent);border-bottom-color:var(--accent)}}\n"
            f"{foco}{{outline:2px solid var(--accent);outline-offset:2px}}\n"
            f"{painel}{{display:flex}}\n")


def _cartao(c: dict, escala: tuple[int, int] | None) -> str:
    p = c["periodo"]
    if p and escala:
        ini, fim = escala
        total = max(fim - ini + 1, 1)
        esq = (_meses(p["inicio"]) - ini) / total * 100
        larg = max((_meses(p["fim"]) - _meses(p["inicio"]) + 1) / total * 100, 1.5)
        lacuna = (f" · {p['meses_com_dado']} com dado"
                  if p["meses_com_dado"] < p["meses_historico"] else "")
        hist = (f'<div class="hist"><div class="linha"><span>{e(p["inicio_legivel"])} → '
                f'{e(p["fim_legivel"])}</span><span>{p["meses_historico"]} meses{lacuna}</span></div>'
                f'<div class="trilha" role="img" aria-label="Histórico de {e(p["inicio_legivel"])} '
                f'a {e(p["fim_legivel"])}"><i style="left:{esq:.1f}%;width:{larg:.1f}%"></i></div>'
                f'<div class="linha"><span>por {e(p["rotulo_tempo"])}</span></div></div>')
    else:
        hist = '<div class="semdata">Sem data utilizável para medir histórico.</div>'
    extras = "".join(f"<dt>{e(r)}</dt><dd>{e(v)}</dd>" for r, v in c["extras"])
    frentes = "".join(f'<span class="tag-f" title="{e(FRENTES[f])}">F{f} {e(FRENTES[f])}</span>'
                      for f in c["frentes"]) or '<span class="tag-f">nenhuma</span>'
    avisos = "".join(f'<li><span class="pill n-{a["nivel"]}">{e(a["nivel_rotulo"])}</span>'
                     f'<span>{e(a["texto"])}</span></li>' for a in c["avisos"])
    return f"""
<article class="card" data-status="{e(c['status'])}">
  <div class="topo"><span class="fonte">{e(c['fonte'])}</span><span class="pill s-{e(c['status'])}">{e(c['status_rotulo'])}</span></div>
  <h3>{e(c['nome'])}</h3>
  <p class="desc">{e(c['descricao'])}</p>
  <div class="num"><b>{_fmt(c['registros'])}</b><span>{e(c['unidade'])}</span></div>
  {hist}
  {f'<dl>{extras}</dl>' if extras else ''}
  <p class="razao">{e(c['razao_status'])}</p>
  <div class="frentes-tags">Usada em: {frentes}</div>
  {f'<ul class="avisos">{avisos}</ul>' if avisos else ''}
</article>"""


def aba_status(st: dict) -> str:
    fams = st["familias"]
    periodos = [c["periodo"] for c in fams if c["periodo"]]
    escala = ((min(_meses(p["inicio"]) for p in periodos), max(_meses(p["fim"]) for p in periodos))
              if periodos else None)
    ent = st.get("entrega") or {}
    fases = "".join(
        f'<div class="fase {cls}"><span class="n">{e(n)}{" · concluída" if cls == "feito" else " · em andamento" if cls == "agora" else ""}</span>'
        f'<span class="t">{e(t)}</span></div>' for n, t, cls in ANDAMENTO)
    filtros_radios = "".join(
        f'<input type="radio" name="filtro" id="f-{s}" class="sr"{" checked" if s == "todos" else ""}>'
        for s in ["todos", *st["rotulos"].keys()])
    opcoes = [("todos", "Todas", "")] + [(s, r, f" ({st['resumo'][s]})")
                                         for s, r in st["rotulos"].items() if st["resumo"].get(s)]
    filtros_rot = "".join(f'<label for="f-{s}">{e(r)}{n}</label>' for s, r, n in opcoes)
    cards = "".join(_cartao(c, escala) for c in fams)

    ordem = {"alta": 0, "media": 1, "baixa": 2}
    pedidos = sorted(((ordem[p["prioridade"]], p, c) for c in fams for p in c["pedir"]),
                     key=lambda x: (x[0], x[2]["fonte"], x[1]["pedido"]))
    linhas = "".join(
        f'<tr><td><span class="pill p-{p["prioridade"]}">{e(p["prioridade_rotulo"])}</span></td>'
        f'<td>{e(p["pedido"])}</td><td>{e(c["fonte"])} · {e(c["nome"])}</td>'
        f'<td>{" ".join(f"<span class=tag-f>F{f}</span>" for f in p["frentes"])}</td></tr>'
        for _, p, c in pedidos)
    altas = sum(1 for o, _, _ in pedidos if o == 0)

    return f"""
<section class="panel" id="p-status">
  <div class="faixa">
    <span>Entrega: <b>{e(ent.get('zip_nome', '—'))}</b></span>
    <span>Arquivos: <b>{_fmt(ent.get('arquivos', 0))}</b></span>
    <span>Linhas importadas: <b>{_fmt(ent.get('linhas') or 0)}</b></span>
    <span>Status calculado em <b>{e(_data_br(st['gerado_em']))}</b></span>
  </div>
  <div>
    <h2>Andamento</h2>
    <div class="andamento" style="margin-top:10px">{fases}</div>
  </div>
  <div>
    <h2>Famílias de dados</h2>
    <p class="lead" style="margin-top:6px">Cada cartão é uma família: o volume, quanto histórico ela cobre, em que frentes do plano entra e o que limita o uso. A barra mostra o período de cada família na mesma escala de tempo.</p>
  </div>
  <div>
    {filtros_radios}
    <div class="filtros" role="group" aria-label="Filtrar por status">{filtros_rot}</div>
    <div class="legenda" style="margin-top:10px">
      <span><span class="pill n-bloqueia">Bloqueia</span> impede uma análise prevista</span>
      <span><span class="pill n-atencao">Atenção</span> análise possível, com regra de leitura</span>
      <span><span class="pill n-info">Info</span> contexto</span>
    </div>
    <div class="cards">{cards}</div>
  </div>
  <div>
    <h2>O que falta pedir</h2>
    <p class="lead" style="margin-top:6px">{len(pedidos)} pedidos, {altas} de prioridade alta. Os de prioridade alta bloqueiam análises já previstas no plano; F1 a F4 são as frentes que cada um destrava.</p>
    <div class="tw" style="margin-top:12px"><table>
      <thead><tr><th>Prioridade</th><th>Pedido</th><th>Família</th><th>Destrava</th></tr></thead>
      <tbody>{linhas}</tbody>
    </table></div>
  </div>
</section>"""


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
  <p class="lead">Primeira leitura da Frente 1 com o histórico entregue pelos administradores. Tudo agregado: nenhum dado individual. Os gráficos mostram detalhes ao passar o mouse, e cada um tem a tabela com os números logo abaixo.</p>
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


def aba_frente2(f2: dict, achados_html: str) -> str:
    from . import graficos as G
    R, P = G.reais, G.pct
    pp, md, lt, tm = f2["por_plataforma"], f2["midia"], f2["leitura"], f2["temas"]
    comp = {p: {c["intencao"]: c for c in v["composicao"]} for p, v in pp.items()}
    pede = {p: c["pedido"]["fracao"] + c["pergunta"]["fracao"] for p, c in comp.items()}
    per = {p: f"{G.mes_legivel(a)} a {G.mes_legivel(b)}" for p, (a, b) in f2["periodo"].items()}
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


def aba_frente3(f3: dict, achados_html: str) -> str:
    from . import graficos as G
    R, P = G.reais, G.pct
    x = lambda v: f"{v:.1f}×".replace(".", ",")  # noqa: E731
    ja, el, ec, su = f3["janela"], f3["esperado_limpo"], f3["esperado"], f3["suspeitas"]
    total_n = f3["doacoes"]
    meses_sus = sorted(su["por_mes"].items(), key=lambda kv: -kv[1])
    principais = [G.mes_legivel(m) for m, n in meses_sus if n >= max(1, su["noites"] * 0.25)]
    ladr = "".join([
        _ladrilho("Lives registradas", f"{P(f3['dentro']['pct_tempo'])} do tempo",
                  f"concentram {P(f3['dentro']['pct_n'])} das doações e {P(f3['dentro']['pct_valor'])} do valor"),
        _ladrilho("Efeito da live, na mesma hora do dia", f"{x(el['efeito_n'])} doações",
                  f"{x(el['efeito_valor'])} no valor · conservador: {x(ec['efeito_n'])} e {x(ec['efeito_valor'])}"),
        _ladrilho("Ritmo", f"{R(f3['taxa']['live_reais_h'], False)} por hora",
                  f"durante a live; {R(f3['taxa']['fora_reais_h'], False)} por hora nas horas sem sinal de live"),
        _ladrilho("Provável live sem registro", f"{su['noites']} noites",
                  f"{_fmt(su['n'])} doações ({P(su['n'] / total_n)} da janela)"
                  + (f", sobretudo {' e '.join(principais)}" if principais else "")),
    ])
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


def aba_doc(doc: dict, rev: int | None) -> str:
    toc = "".join(f'<li><a href="#{a}">{e(t)}</a></li>' for a, t in doc["secoes"])
    return f"""
<section class="panel" id="p-doc">
  <p class="lead">{e(doc['titulo'])}. Gerado a partir do documento do plano{f' (versão {rev})' if rev else ''}; se os dois divergirem, vale o documento.</p>
  <nav class="toc" aria-label="Seções do plano"><span class="eyebrow">Nesta documentação</span><ol>{toc}</ol></nav>
  <div class="doc">{doc['html']}</div>
</section>"""


def montar(st: dict, doc: dict, rev: int | None, f1: dict | None = None, achados_html: str = "",
           f3: dict | None = None, achados3_html: str = "", f2: dict | None = None, achados2_html: str = "") -> str:
    css = (PAGINA / "estilo.css").read_text(encoding="utf-8") + _css_abas()
    prompt = (PAGINA / "prompt.html").read_text(encoding="utf-8")
    resumo = (PAGINA / "resumo_analistas.html").read_text(encoding="utf-8")
    radios = "".join(f'<input type="radio" name="aba" id="r-{a}" class="sr"{" checked" if i == 0 else ""}>\n'
                     for i, (a, _) in enumerate(ABAS))
    rotulos = "".join(f'<label class="tab" for="r-{a}">{e(r)}</label>' for a, r in ABAS)
    return f"""<title>Painel Lives e Doações</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
{css}</style>

<div class="wrap">
{radios}<header>
  <div class="eyebrow">Projeto lives × doações · painel compartilhado com administradores e analistas</div>
  <h1>Painel de dados</h1>
  <p class="lead">Status de cada família de dados recebida, o plano do projeto e o pedido de extração, num lugar só. O plano é a fonte da verdade; esta página é gerada a partir dele.</p>
  <div class="tabs">{rotulos}</div>
</header>
{aba_status(st)}
{aba_frente1(f1, achados_html) if f1 else '<section class="panel" id="p-frente1"><p class="lead">Em preparação.</p></section>'}
{aba_frente2(f2, achados2_html) if f2 else '<section class="panel" id="p-frente2"><p class="lead">Em preparação.</p></section>'}
{aba_frente3(f3, achados3_html) if f3 else '<section class="panel" id="p-frente3"><p class="lead">Em preparação.</p></section>'}
{aba_doc(doc, rev)}
<section class="panel" id="p-prompt">
{prompt}</section>
<section class="panel" id="p-resumo">
{resumo}</section>
<footer>Números agregados, sem nenhum dado individual. Os dados ficam na pasta restrita do Drive e na pasta de trabalho; nunca em repositório. Status calculado em {e(_data_br(st['gerado_em']))}.</footer>
</div>

<script>
(function(){{
  var h=location.hash.replace('#','');
  var abas={{status:1,frente1:1,frente2:1,frente3:1,doc:1,prompt:1,resumo:1}};
  if(abas[h]) {{ var r=document.getElementById('r-'+h); if(r) r.checked=true; }}
  if(h.indexOf('doc-')===0) {{ var d=document.getElementById('r-doc'); if(d) d.checked=true; }}
  document.addEventListener('click',function(ev){{
    var a=ev.target.closest('a[href^="#doc-"]'); if(!a) return;
    var d=document.getElementById('r-doc'); if(d) d.checked=true;
  }});
  var tip=document.createElement('div'); tip.className='tip'; document.body.appendChild(tip);
  function mostra(el,x,y){{ tip.textContent=el.getAttribute('data-tip'); tip.classList.add('on');
    var w=tip.offsetWidth,h=tip.offsetHeight; var nx=Math.min(x+12,innerWidth-w-8), ny=y-h-10<4?y+16:y-h-10;
    tip.style.left=Math.max(4,nx)+'px'; tip.style.top=ny+'px'; }}
  document.addEventListener('mousemove',function(ev){{ var el=ev.target.closest&&ev.target.closest('[data-tip]');
    if(el) mostra(el,ev.clientX,ev.clientY); else tip.classList.remove('on'); }});
  document.addEventListener('focusin',function(ev){{ var el=ev.target.closest&&ev.target.closest('[data-tip]');
    if(el){{ var r=el.getBoundingClientRect(); mostra(el,r.left+r.width/2,r.top); }} }});
  document.addEventListener('focusout',function(){{ tip.classList.remove('on'); }});
  var btn=document.getElementById('copy'),pre=document.getElementById('prompt');
  if(!btn||!pre) return;
  function sel(){{var r=document.createRange();r.selectNodeContents(pre);var s=getSelection();s.removeAllRanges();s.addRange(r);}}
  btn.addEventListener('click',function(){{
    try{{navigator.clipboard.writeText(pre.textContent).then(function(){{btn.textContent='Copiado';setTimeout(function(){{btn.textContent='Copiar prompt';}},2000);}},function(){{sel();btn.textContent='Texto selecionado: Ctrl+C';}});}}
    catch(e){{sel();btn.textContent='Texto selecionado: Ctrl+C';}}
  }});
}})();
</script>
"""
