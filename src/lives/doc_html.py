"""Plano (Claude Docs) -> HTML, para a página dos administradores.

O plano é a fonte da verdade e é editado no documento. A página não pode ser
uma cópia digitada à mão, ou as duas versões divergem na primeira edição.
Este módulo converte a leitura completa do documento (o XML que a ferramenta
de documentos devolve) em HTML, preservando títulos, listas, tabelas, negrito
e código. Chips viram texto: data, menção a pessoa e referência a documento.

Só a estrutura que o plano usa é tratada. Elemento desconhecido vira o texto
que contém, para nada sumir em silêncio.
"""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def carregar_xml(caminho: Path | str) -> tuple[str, int]:
    """Lê o arquivo salvo pela leitura do documento: JSON com data.xml e rev."""
    bruto = json.loads(Path(caminho).read_text(encoding="utf-8"))
    return bruto["data"]["xml"], bruto.get("rev") or bruto["data"].get("rev")


def _slug(texto: str) -> str:
    import unicodedata
    puro = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", puro).strip("-")


def _inline(el: ET.Element) -> str:
    """Conteúdo de um parágrafo: runs de texto e chips."""
    partes = []
    if el.text:
        partes.append(html.escape(el.text))
    for filho in el:
        partes.append(_run(filho))
        if filho.tail:
            partes.append(html.escape(filho.tail))
    return "".join(partes)


def _run(el: ET.Element) -> str:
    tag = el.tag
    if tag == "text":
        return _inline(el)
    if tag == "bold":
        return f"<b>{_inline(el)}</b>"
    if tag == "italic":
        return f"<i>{_inline(el)}</i>"
    if tag == "code":
        return f"<code>{_inline(el)}</code>"
    if tag == "link":
        href = el.get("href") or el.get("url") or "#"
        return f'<a href="{html.escape(href)}" target="_blank" rel="noopener">{_inline(el)}</a>'
    if tag == "date":
        v = el.get("value", "")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            return f"{int(v[8:10])} {MESES[int(v[5:7]) - 1]} {v[:4]}"
        return html.escape(v)
    if tag == "mention":
        if el.get("label"):
            return f"<span class=\"chip-ref\">{html.escape(el.get('label'))}</span>"
        return "@" + html.escape(el.get("name", "pessoa"))
    return _inline(el)


def _bloco(el: ET.Element, ids: set[str]) -> str:
    tag = el.tag
    if tag == "paragraph":
        conteudo = _inline(el)
        nivel = el.get("heading")
        if nivel:
            texto = re.sub(r"<[^>]+>", "", conteudo)
            ancora = _slug(texto)
            while ancora in ids:
                ancora += "-x"
            ids.add(ancora)
            n = max(2, min(int(nivel), 4))  # o h1 é o título da página; seções ficam em h2
            return f'<h{n} id="doc-{ancora}">{conteudo}</h{n}>'
        return f"<p>{conteudo}</p>" if conteudo.strip() else ""
    if tag == "list":
        tipo = el.get("kind", "bullet")
        tag_html = "ol" if tipo == "ordered" else "ul"
        classe = ' class="checklist"' if tipo == "check" else ""
        itens = []
        for item in el.findall("listItem"):
            dentro = "".join(_bloco(f, ids) for f in item)
            # parágrafo único dentro do item não precisa de <p>
            dentro = re.sub(r"^<p>(.*)</p>$", r"\1", dentro, flags=re.S) if dentro.count("<p>") == 1 else dentro
            marca = ' data-feito="1"' if item.get("checked") == "true" else ""
            itens.append(f"<li{marca}>{dentro}</li>")
        return f"<{tag_html}{classe}>{''.join(itens)}</{tag_html}>"
    if tag == "table":
        linhas = []
        for i, row in enumerate(el.findall("row")):
            celulas = []
            for cell in row.findall("cell"):
                t = "th" if cell.get("header") == "true" else "td"
                dentro = "".join(_bloco(f, ids) for f in cell)
                dentro = re.sub(r"^<p>(.*)</p>$", r"\1", dentro, flags=re.S)
                celulas.append(f"<{t}>{dentro}</{t}>")
            linhas.append(("thead" if i == 0 and row.find("cell[@header='true']") is not None
                           else "tbody", "<tr>" + "".join(celulas) + "</tr>"))
        cab = "".join(r for s, r in linhas if s == "thead")
        corpo = "".join(r for s, r in linhas if s == "tbody")
        return (f'<div class="tw"><table>{"<thead>" + cab + "</thead>" if cab else ""}'
                f"<tbody>{corpo}</tbody></table></div>")
    if tag == "codeBlock":
        return f"<pre class=\"bloco\">{html.escape(''.join(el.itertext()))}</pre>"
    if tag == "pending":
        return ""
    return f"<p>{html.escape(''.join(el.itertext()))}</p>"


def converter(xml: str) -> dict:
    """XML do documento -> {'titulo', 'html', 'secoes': [(ancora, título)]}."""
    raiz = ET.fromstring(xml)
    blocos = list(raiz)
    titulo = ""
    if blocos and blocos[0].tag == "paragraph" and blocos[0].get("heading") == "1":
        titulo = "".join(blocos[0].itertext()).strip()
        blocos = blocos[1:]
    ids: set[str] = set()
    partes = [_bloco(b, ids) for b in blocos]
    corpo = "\n".join(p for p in partes if p)
    secoes = re.findall(r'<h2 id="(doc-[^"]+)">(.*?)</h2>', corpo)
    secoes = [(a, re.sub(r"<[^>]+>", "", t)) for a, t in secoes]
    return {"titulo": titulo, "html": corpo, "secoes": secoes}
