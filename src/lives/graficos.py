"""Gráficos em SVG puro para a página, sem biblioteca.

Regras de desenho (as do guia de visualização do projeto):
- uma escala por gráfico, nunca dois eixos;
- barras finas (até 24px) com ponta arredondada e base reta; linhas de 2px;
- grade em linha fina e discreta; texto sempre em cor de texto, nunca na cor
  da série;
- cada marca leva `data-tip` (dica ao passar o mouse) e `<title>` (para quem
  não tem script); cada gráfico tem tabela com os números ao lado.

As cores vêm de variáveis CSS (`--s1`…`--s4`, `--seq-*`), definidas para o
tema claro e o escuro na folha de estilo da página.
"""

from __future__ import annotations

import html
import math

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
e = html.escape


def reais(centavos_ou_reais: float, centavos: bool = True) -> str:
    v = centavos_ou_reais / 100 if centavos else centavos_ou_reais
    if v == 0:
        return "R$ 0"
    if abs(v) >= 1_000_000:
        return f"R$ {v / 1_000_000:.1f} mi".replace(".", ",")
    if abs(v) >= 10_000:
        return f"R$ {v / 1000:.0f} mil"
    if abs(v) >= 1000:
        return f"R$ {v / 1000:.1f} mil".replace(".", ",")
    return f"R$ {v:,.0f}".replace(",", ".") if v >= 100 else f"R$ {v:.2f}".replace(".", ",")


def pct(x: float, casas: int = 0) -> str:
    return f"{100 * x:.{casas}f}%".replace(".", ",")


def mes_legivel(aaaa_mm: str) -> str:
    return f"{MESES[int(aaaa_mm[5:7]) - 1]}/{aaaa_mm[2:4]}"


def _ticks(maximo: float, n: int = 4) -> list[float]:
    if maximo <= 0:
        return [0]
    passo_bruto = maximo / n
    mag = 10 ** math.floor(math.log10(passo_bruto))
    passo = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= passo_bruto)
    return [passo * i for i in range(int(maximo / passo) + 2) if passo * i <= maximo * 1.0001 + passo]


def _barra_v(x: float, y: float, w: float, h: float, cor: str, extra: str = "") -> str:
    """Coluna com topo arredondado (4px) e base reta."""
    if h <= 0:
        return ""
    r = min(4, w / 2, h)
    return (f'<path d="M{x:.1f},{y + h:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} '
            f'H{x + w - r:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} V{y + h:.1f} Z" '
            f'fill="{cor}" {extra}/>')


def _barra_h(x: float, y: float, w: float, h: float, cor: str, extra: str = "") -> str:
    """Barra horizontal com ponta direita arredondada."""
    if w <= 0:
        return ""
    r = min(4, h / 2, w)
    return (f'<path d="M{x:.1f},{y:.1f} H{x + w - r:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} '
            f'V{y + h - r:.1f} Q{x + w:.1f},{y + h:.1f} {x + w - r:.1f},{y + h:.1f} H{x:.1f} Z" '
            f'fill="{cor}" {extra}/>')


def _tip(texto: str) -> str:
    return f'data-tip="{e(texto)}" tabindex="0"'


def colunas_mensais(pontos: list[dict], cores: dict[str, str], altura: int = 260) -> str:
    """pontos: [{'mes','serie','valor'(centavos),'n','parcial'}] — uma coluna por mês."""
    L, R, T, B = 78, 12, 14, 30
    W = max(560, 20 * len(pontos) + L + R)
    ih = altura - T - B
    maximo = max(p["valor"] for p in pontos)
    ticks = _ticks(maximo)
    topo = ticks[-1]
    passo = (W - L - R) / len(pontos)
    bw = min(16, passo - 2)
    out = [f'<svg viewBox="0 0 {W} {altura}" class="graf" style="min-width:{W}px" role="img">']
    for t in ticks:
        y = T + ih - t / topo * ih
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}" class="grade"/>'
                   f'<text x="{L - 8}" y="{y + 4:.1f}" class="eixo" text-anchor="end">{e(reais(t))}</text>')
    ano_ant = None
    for i, p in enumerate(pontos):
        x = L + i * passo + (passo - bw) / 2
        h = p["valor"] / topo * ih
        n = f"{p['n']:,}".replace(",", ".")
        dica = (f"{mes_legivel(p['mes'])} · {p['serie']}: {reais(p['valor'])} em {n} doações"
                + (" (mês parcial)" if p["parcial"] else ""))
        estilo = ' opacity="0.45"' if p["parcial"] else ""
        out.append(_barra_v(x, T + ih - h, bw, h, cores[p["serie"]], f'{_tip(dica)}{estilo}')
                   .replace("/>", f"><title>{e(dica)}</title></path>"))
        ano = p["mes"][:4]
        if ano != ano_ant:
            out.append(f'<text x="{x:.1f}" y="{altura - 8}" class="eixo">{ano}</text>'
                       f'<line x1="{x - 1:.1f}" x2="{x - 1:.1f}" y1="{T + ih}" y2="{T + ih + 6}" class="base"/>')
            ano_ant = ano
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{T + ih}" y2="{T + ih}" class="base"/></svg>')
    return "".join(out)


def barras_h(linhas: list[tuple[str, float, str]], maximo: float | None = None,
             cor: str = "var(--accent)", largura_rotulo: int = 150, W: int = 460) -> str:
    """linhas: (rótulo, valor 0..1 ou absoluto, texto do valor). Uma série, sem legenda."""
    lh, gap, T = 22, 10, 4
    altura = T + len(linhas) * (lh + gap)
    maximo = maximo or max(v for _, v, _ in linhas) or 1
    area = W - largura_rotulo - 70
    out = [f'<svg viewBox="0 0 {W} {altura}" class="graf" style="max-width:{W}px" role="img">']
    for i, (rot, v, txt) in enumerate(linhas):
        y = T + i * (lh + gap)
        w = v / maximo * area
        out.append(f'<text x="{largura_rotulo - 8}" y="{y + 15}" class="rot" text-anchor="end">{e(rot)}</text>')
        out.append(_barra_h(largura_rotulo, y + 3, w, lh - 6, cor, _tip(f"{rot}: {txt}"))
                   .replace("/>", f"><title>{e(rot)}: {e(txt)}</title></path>"))
        out.append(f'<text x="{largura_rotulo + w + 6:.1f}" y="{y + 15}" class="val">{e(txt)}</text>')
    out.append(f'<line x1="{largura_rotulo}" x2="{largura_rotulo}" y1="0" y2="{altura}" class="base"/></svg>')
    return "".join(out)


def faixas_quartis(linhas: list[dict], W: int = 760, cor: str = "var(--accent)") -> str:
    """Por tipo: barra de p25 a p75, ponto na mediana, traço no mínimo configurado.
    linhas: [{'rotulo','p25','mediana','p75','minimo'}] em centavos."""
    L, R, T = 120, 20, 22
    lh = 40
    altura = T + len(linhas) * lh + 26
    topo = max(x["p75"] for x in linhas) * 1.15
    ticks = _ticks(topo / 100, 5)
    escala = lambda c: L + (c / 100) / ticks[-1] * (W - L - R)  # noqa: E731
    out = [f'<svg viewBox="0 0 {W} {altura}" class="graf" style="max-width:{W}px" role="img">']
    for t in ticks:
        x = escala(t * 100)
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{T - 6}" y2="{altura - 22}" class="grade"/>'
                   f'<text x="{x:.1f}" y="{altura - 6}" class="eixo" text-anchor="middle">R$ {t:g}</text>')
    for i, l in enumerate(linhas):
        y = T + i * lh + 12
        x1, x2, xm = escala(l["p25"]), escala(l["p75"]), escala(l["mediana"])
        dica = (f"{l['rotulo']}: metade paga entre {reais(l['p25'])} e {reais(l['p75'])}; "
                f"mediana {reais(l['mediana'])}; mínimo {reais(l['minimo'])}")
        out.append(f'<text x="{L - 10}" y="{y + 5}" class="rot" text-anchor="end">{e(l["rotulo"])}</text>')
        out.append(f'<rect x="{x1:.1f}" y="{y - 5}" width="{max(x2 - x1, 2):.1f}" height="10" rx="5" '
                   f'fill="{cor}" opacity="0.28" {_tip(dica)}><title>{e(dica)}</title></rect>')
        if l.get("minimo"):
            xn = escala(l["minimo"])
            out.append(f'<line x1="{xn:.1f}" x2="{xn:.1f}" y1="{y - 11}" y2="{y + 11}" class="minimo"/>')
        out.append(f'<circle cx="{xm:.1f}" cy="{y}" r="6" fill="{cor}" class="anel" {_tip(dica)}>'
                   f'<title>{e(dica)}</title></circle>')
        out.append(f'<text x="{xm:.1f}" y="{y - 12}" class="val" text-anchor="middle">{e(reais(l["mediana"]))}</text>')
    out.append("</svg>")
    return "".join(out)


def mapa_calor(grade: list[list[int]], dias: list[str]) -> str:
    """7 × 24: dia da semana × hora. Rampa sequencial de um tom (--seq-1 … --seq-6)."""
    L, T, cw, ch = 40, 18, 26, 22
    W, H = L + 24 * cw + 4, T + 7 * ch + 4
    # níveis por percentil dos valores não nulos: uma hora excepcional não apaga
    # a diferença entre todas as outras
    nz = sorted(n for l in grade for n in l if n)
    cortes = [nz[int(q * (len(nz) - 1))] for q in (0.2, 0.4, 0.6, 0.8, 0.95)] if nz else []
    out = [f'<svg viewBox="0 0 {W} {H}" class="graf" style="min-width:{W}px;max-width:{W}px" role="img">']
    for h in range(0, 24, 3):
        out.append(f'<text x="{L + h * cw + cw / 2:.0f}" y="{T - 6}" class="eixo" text-anchor="middle">{h}h</text>')
    for d, linha in enumerate(grade):
        y = T + d * ch
        out.append(f'<text x="{L - 6}" y="{y + 15}" class="rot" text-anchor="end">{e(dias[d])}</text>')
        for h, n in enumerate(linha):
            nivel = 0 if n == 0 else 1 + sum(1 for c in cortes if n > c)
            dica = f"{dias[d]}, {h}h–{h + 1}h (Brasília): " + f"{n:,} doações".replace(",", ".")
            out.append(f'<rect x="{L + h * cw + 1}" y="{y + 1}" width="{cw - 2}" height="{ch - 2}" rx="3" '
                       f'fill="var(--seq-{nivel})" {_tip(dica)}><title>{e(dica)}</title></rect>')
    out.append("</svg>")
    return "".join(out)


def linhas_mensais(series: dict[str, dict[str, float]], cores: dict[str, str], meses: list[str],
                   altura: int = 240) -> str:
    """Várias séries mensais (R$), uma escala. Rótulo direto no fim de cada linha."""
    L, R, T, B = 78, 120, 14, 28
    W = 760
    ih = altura - T - B
    maximo = max(v for s in series.values() for v in s.values()) or 1
    ticks = _ticks(maximo / 100)
    topo = ticks[-1] * 100
    passo = (W - L - R) / max(len(meses) - 1, 1)
    X = {m: L + i * passo for i, m in enumerate(meses)}
    Y = lambda v: T + ih - v / topo * ih  # noqa: E731
    out = [f'<svg viewBox="0 0 {W} {altura}" class="graf" style="min-width:{W}px;max-width:{W}px" role="img">']
    for t in ticks:
        y = Y(t * 100)
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}" class="grade"/>'
                   f'<text x="{L - 8}" y="{y + 4:.1f}" class="eixo" text-anchor="end">{e(reais(t, False))}</text>')
    for i, m in enumerate(meses):
        if i % 2 == 0 or i == len(meses) - 1:
            out.append(f'<text x="{X[m]:.1f}" y="{altura - 8}" class="eixo" text-anchor="middle">{mes_legivel(m)}</text>')
    rotulos = []
    for nome, s in series.items():
        pts = [(X[m], Y(s.get(m, 0))) for m in meses]
        d = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" stroke="{cores[nome]}" stroke-width="2" '
                   f'stroke-linejoin="round" stroke-linecap="round"/>')
        for m, (x, y) in zip(meses, pts):
            dica = f"{mes_legivel(m)} · {nome}: {reais(s.get(m, 0))}"
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="transparent" {_tip(dica)}>'
                       f'<title>{e(dica)}</title></circle>')
        xf, yf = pts[-1]
        out.append(f'<circle cx="{xf:.1f}" cy="{yf:.1f}" r="4" fill="{cores[nome]}" class="anel"/>')
        rotulos.append([yf, nome, xf])
    # rótulos de fim sem sobreposição: afasta na vertical e liga com traço
    rotulos.sort()
    for i in range(1, len(rotulos)):
        if rotulos[i][0] - rotulos[i - 1][0] < 14:
            rotulos[i][0] = rotulos[i - 1][0] + 14
    for yl, nome, xf in rotulos:
        out.append(f'<line x1="{xf + 6:.1f}" x2="{xf + 14:.1f}" y1="{yl:.1f}" y2="{yl:.1f}" stroke="{cores[nome]}" stroke-width="2"/>'
                   f'<text x="{xf + 18:.1f}" y="{yl + 4:.1f}" class="rot">{e(nome)}</text>')
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{T + ih}" y2="{T + ih}" class="base"/></svg>')
    return "".join(out)


def linhas_categoricas(series: dict[str, list[float | None]], cores: dict[str, str], xs: list[str],
                       fmt=lambda v: f"{v:.1f}".replace(".", ","), altura: int = 250, rotulo_y: str = "") -> str:
    """Várias séries sobre o mesmo eixo de categorias (ex.: horas do dia). None = sem dado
    suficiente: a linha é interrompida ali, em vez de desenhar zero."""
    L, R, T, B = 56, 200, 18, 28
    W = 800
    ih = altura - T - B
    vals = [v for s in series.values() for v in s if v is not None]
    ticks = _ticks(max(vals) if vals else 1)
    topo = ticks[-1] or 1
    passo = (W - L - R) / max(len(xs) - 1, 1)
    X = lambda i: L + i * passo  # noqa: E731
    Y = lambda v: T + ih - v / topo * ih  # noqa: E731
    out = [f'<svg viewBox="0 0 {W} {altura}" class="graf" style="min-width:{W}px;max-width:{W}px" role="img">']
    for t in ticks:
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grade"/>'
                   f'<text x="{L - 8}" y="{Y(t) + 4:.1f}" class="eixo" text-anchor="end">{e(fmt(t))}</text>')
    if rotulo_y:
        out.append(f'<text x="{L}" y="{T - 6}" class="eixo">{e(rotulo_y)}</text>')
    for i, x in enumerate(xs):
        if i % 3 == 0 or i == len(xs) - 1:
            out.append(f'<text x="{X(i):.1f}" y="{altura - 8}" class="eixo" text-anchor="middle">{e(x)}</text>')
    fins = []
    for nome, s in series.items():
        trecho, d = [], []
        for i, v in enumerate(s):
            if v is None:
                trecho = []
                continue
            d.append(f"{'L' if trecho else 'M'}{X(i):.1f},{Y(v):.1f}")
            trecho.append(i)
        out.append(f'<path d="{" ".join(d)}" fill="none" stroke="{cores[nome]}" stroke-width="2" '
                   f'stroke-linejoin="round" stroke-linecap="round"/>')
        for i, v in enumerate(s):
            if v is None:
                continue
            dica = f"{xs[i]} · {nome}: {fmt(v)}"
            out.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="9" fill="transparent" {_tip(dica)}>'
                       f'<title>{e(dica)}</title></circle>')
        ult = max((i for i, v in enumerate(s) if v is not None), default=None)
        if ult is not None:
            out.append(f'<circle cx="{X(ult):.1f}" cy="{Y(s[ult]):.1f}" r="4" fill="{cores[nome]}" class="anel"/>')
            fins.append([Y(s[ult]), nome, X(ult)])
    fins.sort()
    for i in range(1, len(fins)):
        if fins[i][0] - fins[i - 1][0] < 14:
            fins[i][0] = fins[i - 1][0] + 14
    for yl, nome, xf in fins:
        out.append(f'<line x1="{xf + 6:.1f}" x2="{xf + 14:.1f}" y1="{yl:.1f}" y2="{yl:.1f}" '
                   f'stroke="{cores[nome]}" stroke-width="2"/>'
                   f'<text x="{xf + 18:.1f}" y="{yl + 4:.1f}" class="rot">{e(nome)}</text>')
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{T + ih}" y2="{T + ih}" class="base"/></svg>')
    return "".join(out)


def colunas_simples(pontos: list[tuple[str, float, str]], marca_x: int | None = None, rotulo_marca: str = "",
                    cor: str = "var(--accent)", altura: int = 220, rotulos_cada: int = 4,
                    fmt=lambda v: f"{v:.1f}".replace(".", ",")) -> str:
    """Colunas sobre categorias em sequência (ex.: blocos de 15 min). `marca_x` desenha uma
    linha vertical antes da coluna de índice dado (ex.: o início da live)."""
    L, R, T, B = 52, 10, 20, 30
    W = max(560, 14 * len(pontos) + L + R)
    ih = altura - T - B
    ticks = _ticks(max(v for _, v, _ in pontos) or 1)
    topo = ticks[-1] or 1
    passo = (W - L - R) / len(pontos)
    bw = min(12, passo - 2)
    out = [f'<svg viewBox="0 0 {W} {altura}" class="graf" style="min-width:{W}px;max-width:{W}px" role="img">']
    for t in ticks:
        y = T + ih - t / topo * ih
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}" class="grade"/>'
                   f'<text x="{L - 8}" y="{y + 4:.1f}" class="eixo" text-anchor="end">{e(fmt(t))}</text>')
    for i, (rot, v, dica) in enumerate(pontos):
        x = L + i * passo + (passo - bw) / 2
        h = v / topo * ih
        out.append(_barra_v(x, T + ih - h, bw, h, cor, _tip(dica)).replace("/>", f"><title>{e(dica)}</title></path>"))
        if i % rotulos_cada == 0:
            out.append(f'<text x="{x + bw / 2:.1f}" y="{altura - 8}" class="eixo" text-anchor="middle">{e(rot)}</text>')
    if marca_x is not None:
        xm = L + marca_x * passo
        out.append(f'<line x1="{xm:.1f}" x2="{xm:.1f}" y1="{T - 8}" y2="{T + ih}" class="minimo"/>'
                   f'<text x="{xm + 5:.1f}" y="{T - 8}" class="rot">{e(rotulo_marca)}</text>')
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{T + ih}" y2="{T + ih}" class="base"/></svg>')
    return "".join(out)
