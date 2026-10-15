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
    ("Fase 1", "Base de dados e status", "agora"),
    ("Fase 2", "Frente 1: perfil e preço", ""),
    ("Fase 3", "Frente 2: demanda", ""),
    ("Fase 4", "Frente 3: efeito da live", ""),
    ("Fase 5", "Frente 4 e testes", ""),
]

ABAS = [("status", "Status dos dados"), ("doc", "Documentação"),
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


def aba_doc(doc: dict, rev: int | None) -> str:
    toc = "".join(f'<li><a href="#{a}">{e(t)}</a></li>' for a, t in doc["secoes"])
    return f"""
<section class="panel" id="p-doc">
  <p class="lead">{e(doc['titulo'])}. Gerado a partir do documento do plano{f' (versão {rev})' if rev else ''}; se os dois divergirem, vale o documento.</p>
  <nav class="toc" aria-label="Seções do plano"><span class="eyebrow">Nesta documentação</span><ol>{toc}</ol></nav>
  <div class="doc">{doc['html']}</div>
</section>"""


def montar(st: dict, doc: dict, rev: int | None) -> str:
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
  var abas={{status:1,doc:1,prompt:1,resumo:1}};
  if(abas[h]) {{ var r=document.getElementById('r-'+h); if(r) r.checked=true; }}
  if(h.indexOf('doc-')===0) {{ var d=document.getElementById('r-doc'); if(d) d.checked=true; }}
  document.addEventListener('click',function(ev){{
    var a=ev.target.closest('a[href^="#doc-"]'); if(!a) return;
    var d=document.getElementById('r-doc'); if(d) d.checked=true;
  }});
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
