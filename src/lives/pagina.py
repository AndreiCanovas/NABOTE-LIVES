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
    ("Fase 2", "Frente 1: perfil e preço", "agora"),
    ("Fase 3", "Frente 2: demanda", ""),
    ("Fase 4", "Frente 3: efeito da live", ""),
    ("Fase 5", "Frente 4 e testes", ""),
]

ABAS = [("status", "Status dos dados"), ("frente1", "Frente 1: perfil e preço"), ("doc", "Documentação"),
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


def _tabela(cab: list[str], linhas: list[list[str]], resumo: str = "Ver os números") -> str:
    th = "".join(f"<th>{e(c)}</th>" for c in cab)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas)
    return (f'<details class="numeros"><summary>{e(resumo)}</summary><div class="tw">'
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


def aba_doc(doc: dict, rev: int | None) -> str:
    toc = "".join(f'<li><a href="#{a}">{e(t)}</a></li>' for a, t in doc["secoes"])
    return f"""
<section class="panel" id="p-doc">
  <p class="lead">{e(doc['titulo'])}. Gerado a partir do documento do plano{f' (versão {rev})' if rev else ''}; se os dois divergirem, vale o documento.</p>
  <nav class="toc" aria-label="Seções do plano"><span class="eyebrow">Nesta documentação</span><ol>{toc}</ol></nav>
  <div class="doc">{doc['html']}</div>
</section>"""


def montar(st: dict, doc: dict, rev: int | None, f1: dict | None = None, achados_html: str = "") -> str:
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
  var abas={{status:1,frente1:1,doc:1,prompt:1,resumo:1}};
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
