"""Frente 2 — o que o público pede?

FONTES. Mensagens pagas (Castcoin e LivePix, uma depois da outra), a fila
de mídia da Castcoin (React e Música, com o link pedido), os
comentários do canal e as transcrições das lives. As plataformas são
sequenciais: aparecem lado a lado, nunca somadas.

INTENÇÃO. Cada mensagem recebe uma só intenção, nesta ordem: mídia (traz
link), pedido (expressão de pedido: "fala sobre", "reage", "pode explicar",
"queria ver", "vai ter"…), pergunta ("?" ou começo interrogativo), apoio
(saudação, agradecimento, meta, em mensagem curta) e comentário (o resto).
Compra de produto que aparece como mensagem fica de fora.

FORMATO E TEMA. Formato é o tipo de coisa pedida (React, jogo, livro…) e sai
das regras genéricas deste arquivo; o produto correspondente é procurado no
catálogo pelo nome. Tema usa um léxico que fica na pasta confidencial, porque
foi montado lendo as mensagens. Os nomes dos temas são os da classificação
das lives, para comparar o que se pede com o que a live oferece.

REGRA ERRA. Os números de cada classe valem como ordem de grandeza. A
precisão é conferida à mão numa amostra e registrada nos achados.

LEITURA NA LIVE. Nas lives com transcrição e início real, uma mensagem conta
como lida quando ao menos 70% das suas palavras informativas aparecem na
fala entre 2 minutos antes e 45 minutos depois dela. A mesma conta numa
janela longe da mensagem dá a taxa de acerto por acaso.

PREÇO POR MINUTO. Na fila de mídia, valor pago ÷ duração paga dá o preço por
segundo de cada pedido. O valor mais comum do mês (com tolerância de 3%) é
tomado como a tabela vigente; quem paga o mínimo por um vídeo curto, ou dá
gorjeta, fica fora dela.

FUSO DA LIVEPIX. O arquivo não diz o fuso. Cada deslocamento de hora é
testado contra as transcrições, e vence o que mais casa mensagem com fala.

Tudo agregado. Nenhuma mensagem individual sai daqui.
"""

from __future__ import annotations

import calendar
import json
import re
import sqlite3
import statistics as S
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from .familias import _tab

DESCONHECIDO = "Assunto não identificável pelo título"
SEM_OFERTA = {DESCONHECIDO, "Operação técnica"}
LIMIAR_LEITURA = 0.7
LEITURA_ANTES_MIN, LEITURA_DEPOIS_MIN = 2, 45
LEITURA_MIN_PALAVRAS = 4
GRUPO_MIN = 8
APOIO_MAX_PALAVRAS = 20
TOLERANCIA_PRECO = 0.03

INTENCOES = ["mídia", "pedido", "pergunta", "apoio", "comentário"]
ROTULO_INTENCAO = {"mídia": "Mídia (link para React ou Música)", "pedido": "Pedido explícito",
                   "pergunta": "Pergunta", "apoio": "Apoio e saudação", "comentário": "Comentário e reação"}

URL = re.compile(r"https?://\S+|www\.\S+")
COMPRA = re.compile(r"^(purchase of product|compra do produto)\b")

# Pedido: verbo de pedido no começo de uma oração (depois de até 2 palavras,
# como o vocativo), verbo modal + infinitivo, desejo ("queria ver") ou
# palavra explícita ("sugestão", "vai ter…?").
_IMPERATIVOS = (
    "fala|fale|falem|comenta|comente|comentem|reage|reaja|reajam|assiste|assista|assistam|joga|jogue|joguem"
    "|toca|toque|toquem|bota|bote|botem|coloca|coloque|coloquem|manda|mande|mandem|grava|grave|gravem"
    "|continua|continue|continuem|abre|abra|abram|lanca|lance|lancem|volta|volte|voltem|traz|traga|tragam"
    "|chama|chame|chamem|posta|poste|postem|le|leia|leiam|responde|responda|respondam|explica|explique"
    "|expliquem|ensina|ensine|ensinem|mostra|mostre|mostrem|cria|crie|criem|vende|venda|vendam|faz|faca"
    "|facam|convida|convide|convidem|aprende|aprenda|analisa|analise|analisem|recomenda|recomende|recomendem"
    "|indica|indique|indiquem|testa|teste|testem|estuda|estude|tenta|tente|tentem|compra|compre|comprem"
    "|aumenta|aumente|estende|estica|retoma|retome|retomem|termina|termine|terminem|zera|zere|baixa|baixe"
    "|instala|instale|ouve|ouca|oucam|canta|cante|cantem|imita|imite|repete|repita|da uma|de uma|deem uma"
    "|chamar|fazer|trazer|convidar|gravar|lancar|criar|abrir|voltar|reagir|jogar|ler"
)
_NAO_PEDIDO_DEPOIS = (r"(sentido|tempo|parte|falta|diferenca|anos|meses|dias|horas|semanas|muito|pix|um pix"
                      r"|o l|questao|mal|bem|isso)")
_BLOQUEIO_ANTES = set("ele ela eles elas que quem nao so se ninguem essa esta esse este a o as os sua seu tua "
                      "teu minha meu uma um nessa nesse dessa desse na no da do quando onde porque pq tambem "
                      "ja ai la eu nos".split())
_IMPERATIVO = re.compile(r"^(?P<antes>(?:\w+ ){0,2}?)(?:" + _IMPERATIVOS + r")\b(?! " + _NAO_PEDIDO_DEPOIS + r"\b)")
_MODAL = (r"(pode|podem|poderia|poderiam|podia|podiam|deveria|deveriam|devia|deviam|consegue|conseguem"
          r"|da pra|tem como|seria (?:possivel|legal|bom|interessante|top|massa)|bem que)")
_MODAL_INICIO = re.compile(r"^(?P<antes>(?:\w+ ){0,2}?)" + _MODAL + r"(?: \w+){0,2} (?P<verbo>\w+(?:ar|er|ir))\b")
_MODAL_VOCE = re.compile(r"\b(voce|voces|vc|vcs|tu|ces|senhores) " + _MODAL + r"(?: \w+){0,2} (?P<verbo>\w+(?:ar|er|ir))\b")
_VERBOS_NEUTROS = {"ser", "estar", "ter", "haver", "acontecer", "existir", "parecer", "ficar"}
_PEDIDO_SOLTO = re.compile(
    r"\b(queria|quero|gostaria|adoraria|queremos|queriamos) (que|de ver|ver|ouvir|saber|um|uma|mais)\b"
    r"|\b(pedido|sugestao|sugiro|recomendo|fica a dica|fica a sugestao)\b"
    r"|\b(quando|qnd) (vai|vao|vem|volta|voltam|sai)\b"
    r"|\bmais (uma hora\w*|um pouco|uma horinha|uma live)\b"
    r"|\bmanda(m)? um salve\b")
_VAI_TER = re.compile(r"\bvai ter\b")


def _oracoes(texto: str) -> list[str]:
    return [o for o in (normalizar(p) for p in re.split(r"[.,!;:\n]+", texto or "")) if o]


def _eh_pedido(texto: str, norm: str) -> bool:
    if _PEDIDO_SOLTO.search(norm) or (_VAI_TER.search(norm) and "?" in norm):
        return True
    for o in _oracoes(texto):
        o = o.replace("?", " ").strip()
        m = _IMPERATIVO.search(o)
        if m and not (set(m.group("antes").split()) & _BLOQUEIO_ANTES):
            return True
        m = _MODAL_INICIO.search(o)
        if m and m.group("verbo") not in _VERBOS_NEUTROS and not (set(m.group("antes").split()) & _BLOQUEIO_ANTES):
            return True
        m = _MODAL_VOCE.search(o)
        if m and m.group("verbo") not in _VERBOS_NEUTROS:
            return True
    return False


PERGUNTA_INICIO = re.compile(r"^(o que|oq|qual|quais|quando|como|por que|porque|pq|quem|onde|sera que"
                             r"|tem como|voces acham|vcs acham|vc acha|voce acha)\b")
PERGUNTA_MEIO = re.compile(r"\b(qual|quais) (a|o|e|sua|seu|vossa)\b"
                           r"|\bo que (voce|voces|vc|vcs) (acha|acham|pensa|pensam)\b")
APOIO = re.compile(r"\b(obrigad|parabens|tmj|tamo junto|salve|boa live|boa noite|bom dia|boa tarde|abraco"
                   r"|valeu|forca|bora|avante|sucesso|deus abencoe|feliz aniversario|feliz natal|contribui"
                   r"|ajudar|meta|vida longa|viva)\w*")

# formato: (rótulo, expressão, palavras para achar o produto no catálogo)
FORMATOS = [
    ("React a vídeo", r"\b(reage|reagir|reajam|react|reacts|assiste|assistir|assistam|da uma olhada"
                      r"|olha esse|olha essa|ve esse|ve essa|veja esse|veja essa)\b", ("react",)),
    ("Música", r"\b(toca|tocar|toque|musica|musicas|cancao|cantar|canta)\b", ("musica",)),
    ("Jogo", r"\b(joga|jogar|joguem|jogo|game|gameplay|zera|zerar)\b", ("jogo",)),
    ("Anime", r"\b(anime|animes|manga|episodio|episodios|otaku)\b", ("anime",)),
    ("Livro e leitura", r"\b(livro|livros|leitura|ler|resenha|bibliografia|ebook|e book|autografad\w*)\b",
     ("livro", "e book")),
    ("Curso e aula", r"\b(curso|cursos|aula|aulas|mentoria|ensinar|formacao|turma)\b",
     ("aula", "curso", "formacao")),
    ("Debate e convidado", r"\b(debate|debater|debatam|convida|convidar|convidem|chama o|chama a|chamem"
                           r"|entrevista|entrevistar|collab)\b", ()),
    ("Encontro presencial", r"\b(presencial|encontro|plateia|evento|meetup|vem pra|vir pra|venham|visitar"
                            r"|autografo)\b", ("presencial", "plateia")),
    ("Mais tempo de live", r"\b(aumenta o tempo|mais uma hora|mais um pouco|mais tempo|estende|estica a live"
                           r"|continua a live|nao para|nao parem|volta a live|voltem)\b", ()),
    ("Quanto custa (preço a combinar)", r"\b(quanto|qto|qnto) (custa|custaria|cobra|cobram|cobraria|cobrariam"
                                        r"|sai|sairia|fica|ficaria|pra|para|seria pra|seria para|voce cobra"
                                        r"|vc cobra|voces cobram|vcs cobram|tem que|preciso|precisa)\b", ()),
    ("Tema ou opinião", r"\b(fala sobre|falar sobre|falem sobre|fala de|falar de|opiniao"
                        r"|o que (voce|voces|vc|vcs) (acha|acham|pensa|pensam)|comenta|comentar|analisa"
                        r"|analisar|analise|explica|explicar|tema|pauta)\b", ("pedido",)),
]
_FORMATOS_RE = [(r, re.compile(e), kw) for r, e, kw in FORMATOS]

# palavras genéricas do português, sem relação com os dados
STOP = set("""
para pela pelo pelas pelos como mais mas que porque quando voce voces isso essa esse esta este estas estes
sobre muito muita muitos muitas ainda entao agora aqui tambem minha minhas meus seus suas sua seu dele dela
deles delas eles elas tudo nada sera seria pode podem fazer cara mano boa noite gente coisa coisas nunca
sempre depois antes onde qual quais quem tava estou estao foram fosse sido sendo tenho temos todo toda
todos todas aquilo aqueles aquelas outra outro outros outras mesmo mesma vcs voces nossa nosso nossos
sendo sim nao isso ate entre cada qualquer algum alguma alguns algumas tipo vou vai vamos vao fazer faz
""".split())

# ---------------------------------------------------------------- texto

def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", (texto or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9?]+", " ", t)).strip()


def _palavras(norm: str) -> list[str]:
    return norm.replace("?", " ").split()


def intencao(texto: str) -> str | None:
    """Intenção principal; None para compra de produto registrada como mensagem."""
    if URL.search(texto or ""):
        return "mídia"
    n = normalizar(texto)
    if COMPRA.search(n):
        return None
    if _eh_pedido(texto, n):
        return "pedido"
    if "?" in n or PERGUNTA_INICIO.search(n) or PERGUNTA_MEIO.search(n):
        return "pergunta"
    if APOIO.search(n) and len(_palavras(n)) <= APOIO_MAX_PALAVRAS:
        return "apoio"
    return "comentário"


def formatos(texto: str, tipo: str = "") -> set[str]:
    n = normalizar(URL.sub(" ", texto or ""))
    achados = {r for r, e, _ in _FORMATOS_RE if e.search(n)}
    if tipo == "React":
        achados.add("React a vídeo")
    elif tipo == "Música":
        achados.add("Música")
    elif URL.search(texto or "") and "Música" not in achados:
        achados.add("React a vídeo")
    return achados


class Lexico:
    """Temas e listas de exclusão; o arquivo fica na pasta confidencial."""

    def __init__(self, dados: dict | None = None):
        dados = dados or {}
        self.temas = {t: self._compilar(ts) for t, ts in dados.get("temas", {}).items()}
        frases = [normalizar(f) for f in dados.get("frases_ignorar", [])]
        self.frases = re.compile(r"\b(" + "|".join(map(re.escape, frases)) + r")\b") if frases else None
        self.ignorar = {normalizar(t) for t in dados.get("termos_ignorar", [])}

    @staticmethod
    def _compilar(termos: list[str]):
        partes = []
        for t in termos:
            t = normalizar(t.rstrip("*")) + ("*" if t.endswith("*") else "")
            partes.append(re.escape(t[:-1]) + r"\w*" if t.endswith("*") else re.escape(t) + r"\b")
        return re.compile(r"\b(" + "|".join(partes) + ")") if partes else None

    @classmethod
    def carregar(cls, caminho: str | Path | None) -> "Lexico":
        if not caminho:
            return cls()
        return cls(json.loads(Path(caminho).read_text(encoding="utf-8")))

    def limpar(self, norm: str) -> str:
        return self.frases.sub(" ", norm) if self.frases else norm

    def temas_de(self, texto: str) -> set[str]:
        n = self.limpar(normalizar(URL.sub(" ", texto or "")))
        return {t for t, e in self.temas.items() if e is not None and e.search(n)}


def _termos(norm: str, lex: Lexico) -> set[str]:
    """Palavras informativas e pares vizinhos depois de tirar as genéricas ("guia de estudo" -> "guia estudo")."""
    ws = [w for w in _palavras(norm) if len(w) >= 4 and not w.isdigit() and w not in STOP and w not in lex.ignorar]
    return set(ws) | {f"{a} {b}" for a, b in zip(ws, ws[1:]) if a != b}


def _informativas(texto: str) -> set[str]:
    n = normalizar(URL.sub(" ", texto or ""))
    return {w for w in _palavras(n) if len(w) >= 4 and w not in STOP and not w.isdigit()}


# ---------------------------------------------------------------- tempo

def _min_iso(iso: str) -> int:
    return calendar.timegm(datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").timetuple()) // 60


def _min_literal(br: str) -> int:
    """'DD/MM/AAAA HH:MM' lido como se fosse UTC; o fuso é somado depois."""
    return calendar.timegm(datetime.strptime(br[:16], "%d/%m/%Y %H:%M").timetuple()) // 60


def _mes_brt(minuto: int) -> str:
    return (datetime(1970, 1, 1) + timedelta(minutes=minuto - 180)).strftime("%Y-%m")


# ---------------------------------------------------------------- corpus

def mensagens(conn: sqlite3.Connection, fuso_livepix_h: int = -3) -> list[dict]:
    """Mensagens pagas com texto. `minuto` em UTC; LivePix convertida pelo fuso dado."""
    ui = _tab(conn, "castcoin__suplemento_doacoes_ui")
    lp = _tab(conn, "livepix__suplemento_livepix_mensagens")
    saida = []
    for tipo, v, d, m, prod in conn.execute(
            f'SELECT tipo_exibido, valor_centavos, data_exibida_utc, mensagem, produto_id_correspondente_nome '
            f'FROM "{ui}" WHERE mensagem <> \'\''):
        if prod:
            continue
        saida.append({"plataforma": "Castcoin", "tipo": tipo or "Doação livre", "centavos": int(v or 0),
                      "minuto": _min_iso(d) if d else None, "texto": m })
    for v, d, m in conn.execute(
            f'SELECT valor_centavos, data_literal_fonte, mensagem FROM "{lp}" WHERE mensagem <> \'\''):
        minuto = _min_literal(d) - fuso_livepix_h * 60 if d else None
        saida.append({"plataforma": "LivePix", "tipo": "Doação livre", "centavos": int(v or 0),
                      "minuto": minuto, "texto": m})
    for s in saida:
        s["intencao"] = intencao(s["texto"])
        s["mes"] = _mes_brt(s["minuto"]) if s["minuto"] is not None else None
    return [s for s in saida if s["intencao"] is not None]


def _mediana(vs: list[int]) -> int:
    return int(S.median(vs)) if vs else 0


def _composicao(msgs: list[dict]) -> list[dict]:
    saida = []
    total = len(msgs)
    total_c = sum(m["centavos"] for m in msgs) or 1
    for k in INTENCOES:
        grupo = [m for m in msgs if m["intencao"] == k]
        vs = [m["centavos"] for m in grupo]
        saida.append({"intencao": k, "rotulo": ROTULO_INTENCAO[k], "n": len(grupo),
                      "fracao": len(grupo) / total if total else 0, "centavos": sum(vs),
                      "fracao_valor": sum(vs) / total_c, "mediana": _mediana(vs)})
    return saida


# ---------------------------------------------------------------- catálogo

def _catalogo(conn: sqlite3.Connection) -> list[dict]:
    prod = _tab(conn, "01_historico__doacoes_produtos")
    mini = _tab(conn, "01_historico__doacoes_minimos")
    return [{"nome": n, "norm": normalizar(n), "tipo_valor": t, "centavos": int(v or 0)}
            for n, t, v in conn.execute(f'SELECT p.nome, m.tipo_valor, m.valor_centavos FROM "{prod}" p '
                                        f'JOIN "{mini}" m USING (produto_id) WHERE p.nome <> \'\'')]


def _produtos_do_formato(catalogo: list[dict], palavras: tuple[str, ...]) -> list[dict]:
    achados = [c for c in catalogo if any(re.search(r"\b" + re.escape(p), c["norm"]) for p in palavras)]
    return [{"nome": c["nome"], "tipo_valor": c["tipo_valor"], "centavos": c["centavos"]}
            for c in sorted(achados, key=lambda c: (c["tipo_valor"] != "minimo", c["centavos"]))]


def _formatos(msgs: list[dict], catalogo: list[dict]) -> list[dict]:
    pede = [m for m in msgs if m["intencao"] in ("mídia", "pedido", "pergunta")]
    por = defaultdict(list)
    for m in pede:
        for f in formatos(m["texto"], m["tipo"] if m["plataforma"] == "Castcoin" else ""):
            por[f].append(m)
    saida = []
    for rotulo, _, kw in FORMATOS:
        grupo = por.get(rotulo, [])
        cast = [m for m in grupo if m["plataforma"] == "Castcoin"]
        saida.append({
            "formato": rotulo, "n": len(grupo), "centavos": sum(m["centavos"] for m in grupo),
            "mediana": _mediana([m["centavos"] for m in grupo]),
            "por_plataforma": {p: sum(1 for m in grupo if m["plataforma"] == p) for p in ("Castcoin", "LivePix")},
            "castcoin_via_livre": sum(1 for m in cast if m["tipo"] == "Doação livre"),
            "castcoin_n": len(cast),
            "produtos": _produtos_do_formato(catalogo, kw) if kw else [],
        })
    saida.sort(key=lambda x: -x["n"])
    return saida


# ---------------------------------------------------------------- temas

def _oferta(conn: sqlite3.Connection) -> dict[str, int]:
    tm = _tab(conn, "analise_tematica__temas_lives")
    return {t: n for t, n in conn.execute(f'SELECT tema_principal, COUNT(*) FROM "{tm}" GROUP BY 1')
            if t not in SEM_OFERTA}


def _temas(msgs: list[dict], lex: Lexico, oferta: dict[str, int]) -> dict:
    pede = [m for m in msgs if m["intencao"] in ("pedido", "pergunta")]
    por = defaultdict(list)
    com_tema = 0
    for m in pede:
        ts = lex.temas_de(m["texto"])
        com_tema += bool(ts)
        for t in ts:
            por[t].append(m)
    atrib = sum(len(v) for v in por.values()) or 1
    total_oferta = sum(oferta.values()) or 1
    linhas = []
    for t in sorted(set(por) | set(oferta)):
        g = por.get(t, [])
        d, o = len(g) / atrib, oferta.get(t, 0) / total_oferta
        linhas.append({"tema": t, "n": len(g), "centavos": sum(m["centavos"] for m in g),
                       "plataformas": {p: sum(1 for m in g if m["plataforma"] == p) for p in ("Castcoin", "LivePix")},
                       "demanda": d, "lives": oferta.get(t, 0), "oferta": o, "diferenca": d - o})
    linhas.sort(key=lambda x: -x["demanda"])
    return {"pedidos_perguntas": len(pede), "com_tema": com_tema, "atribuicoes": atrib if por else 0,
            "lives_com_tema": sum(oferta.values()), "linhas": linhas}


# ---------------------------------------------------------------- grupos candidatos

def _grupos(msgs: list[dict], lex: Lexico, n_min: int = GRUPO_MIN, limite: int = 30) -> list[dict]:
    pede = [m for m in msgs if m["intencao"] in ("pedido", "pergunta", "mídia")]
    por = defaultdict(list)
    for m in pede:
        for t in _termos(lex.limpar(normalizar(URL.sub(" ", m["texto"]))), lex):
            por[t].append(m)
    # plural junta com o singular quando os dois aparecem ("livros" -> "livro")
    for t in [t for t in por if " " not in t and t.endswith("s") and t[:-1] in por]:
        juntos = {id(m): m for m in por[t[:-1]] + por.pop(t)}
        por[t[:-1]] = list(juntos.values())
    cand = {t: g for t, g in por.items() if len(g) >= n_min}
    bigramas = [t for t in cand if " " in t]
    fora = set()
    for t in cand:
        if " " not in t:
            for b in bigramas:
                if t in b.split() and len(cand[b]) >= 0.6 * len(cand[t]):
                    fora.add(t)
    saida = []
    for t, g in sorted(cand.items(), key=lambda x: (-len(x[1]), x[0])):
        if t in fora:
            continue
        meses = sorted({m["mes"] for m in g if m["mes"]})
        saida.append({"termo": t, "n": len(g), "centavos": sum(m["centavos"] for m in g),
                      "mediana": _mediana([m["centavos"] for m in g]),
                      "plataformas": {p: sum(1 for m in g if m["plataforma"] == p) for p in ("Castcoin", "LivePix")},
                      "meses": len(meses), "de": meses[0] if meses else None, "ate": meses[-1] if meses else None,
                      "intencoes": dict(Counter(m["intencao"] for m in g)),
                      "temas": sorted(lex.temas_de(t))})
        if len(saida) >= limite:
            break
    return saida


# ---------------------------------------------------------------- fila de mídia

def _origem(link: str) -> tuple[str, str]:
    """(origem, chave do item) a partir do link pedido."""
    l = (link or "").strip().replace("&amp;", "&")
    host = (re.match(r"https?://([^/?#]+)", l) or [None, ""])[1].lower()
    host = host[4:] if host.startswith("www.") else host
    host = host[2:] if host.startswith("m.") else host
    if host in ("youtube.com", "youtu.be", "music.youtube.com"):
        m = (re.search(r"/shorts/([\w-]{6,})", l))
        if m:
            return "YouTube Shorts", "yt:" + m.group(1)
        m = re.search(r"[?&]v=([\w-]{6,})", l) or re.search(r"youtu\.be/([\w-]{6,})", l) \
            or re.search(r"/(?:live|embed)/([\w-]{6,})", l)
        return "YouTube", "yt:" + (m.group(1) if m else l)
    if host in ("x.com", "twitter.com", "mobile.twitter.com", "vxtwitter.com", "fxtwitter.com"):
        m = re.search(r"/status/(\d+)", l)
        return "X (Twitter)", "x:" + (m.group(1) if m else l)
    if host.endswith("instagram.com"):
        m = re.search(r"/(?:reel|reels|p|tv)/([\w-]+)", l)
        return "Instagram", "ig:" + (m.group(1) if m else l)
    if host.endswith("tiktok.com"):
        m = re.search(r"/video/(\d+)", l)
        return "TikTok", "tt:" + (m.group(1) if m else l)
    if host in ("t.me", "telegram.me"):
        return "Telegram", "tg:" + l.split("?")[0].lower()
    return ("Outro" if host else "Sem link"), "?:" + l.split("?")[0].lower()


def _segundos(duracao: str) -> int | None:
    """'MM:SS' ou 'HH:MM:SS' -> segundos."""
    try:
        partes = [int(x) for x in (duracao or "").split(":")]
    except ValueError:
        return None
    if len(partes) == 2:
        return partes[0] * 60 + partes[1]
    if len(partes) == 3:
        return partes[0] * 3600 + partes[1] * 60 + partes[2]
    return None


def _moda_relativa(valores: list[float], tolerancia: float = TOLERANCIA_PRECO) -> tuple[float | None, int]:
    """Valor com mais vizinhos a ±tolerância (relativa); devolve a mediana desses vizinhos e quantos são.
    Serve para achar o preço por segundo vigente no mês: o pedido típico paga exatamente a tabela;
    quem paga o mínimo por um vídeo curto, ou dá gorjeta, fica fora da moda."""
    if not valores:
        return None, 0
    vs = sorted(valores)
    melhor, viz = None, []
    for v in vs:
        dentro = [x for x in vs if abs(x - v) <= tolerancia * v]
        if len(dentro) > len(viz):
            melhor, viz = v, dentro
    return S.median(viz), len(viz)


ORIGENS = ["YouTube", "YouTube Shorts", "X (Twitter)", "Instagram", "TikTok", "Telegram", "Outro", "Sem link"]


def _fila_midia(conn: sqlite3.Connection) -> dict:
    ex = _tab(conn, "castcoin__suplemento_execucao_midias")
    vids = _tab(conn, "01_historico__canal_videos")
    proprios = {v for (v,) in conn.execute(f'SELECT video_id FROM "{vids}"')}
    linhas = []
    for tipo, estado, d, v, link, dur in conn.execute(
            f'SELECT tipo, estado_operacional, data_exibida_utc, valor_centavos, link_midia, duracao_paga FROM "{ex}"'):
        origem, chave = _origem(link)
        linhas.append({"tipo": "React" if tipo == "REACT" else "Música" if tipo == "MUSIC" else tipo,
                       "estado": estado, "mes": _mes_brt(_min_iso(d)) if d else None,
                       "centavos": int(v or 0), "origem": origem, "chave": chave, "segundos": _segundos(dur)})
    por_chave = Counter(l["chave"] for l in linhas if not l["chave"].endswith(":"))
    repetidos = {k: n for k, n in por_chave.items() if n >= 2}
    origens = []
    for o in ORIGENS:
        g = [l for l in linhas if l["origem"] == o]
        if g:
            origens.append({"origem": o, "n": len(g), "react": sum(1 for l in g if l["tipo"] == "React"),
                            "musica": sum(1 for l in g if l["tipo"] == "Música"),
                            "mediana": _mediana([l["centavos"] for l in g])})
    estados = Counter((l["mes"], l["tipo"], l["estado"]) for l in linhas)
    precos = []
    for tipo in ("React", "Música"):
        for mes in sorted({l["mes"] for l in linhas if l["mes"] and l["tipo"] == tipo}):
            g = [l for l in linhas if l["mes"] == mes and l["tipo"] == tipo]
            taxas = [l["centavos"] / l["segundos"] for l in g if l["segundos"]]
            moda, na_moda = _moda_relativa(taxas)
            precos.append({"tipo": tipo, "mes": mes, "n": len(g), "centavos": sum(l["centavos"] for l in g),
                           "minutos": sum(l["segundos"] or 0 for l in g) / 60,
                           "reais_por_minuto": moda * 60 / 100 if moda else None,
                           "na_moda": na_moda / len(taxas) if taxas else 0,
                           "duracao_mediana_s": S.median([l["segundos"] for l in g if l["segundos"]])
                           if taxas else None})
    meses = sorted({l["mes"] for l in linhas if l["mes"]})
    por_mes = [{"mes": m, "tipo": t, "estado": e, "n": estados[(m, t, e)]}
               for m in meses for t in ("React", "Música") for e in ("aceitos", "concluidos", "rejeitados")
               if estados[(m, t, e)]]
    total_estado = Counter((l["tipo"], l["estado"]) for l in linhas)
    valor_estado = defaultdict(int)
    for l in linhas:
        valor_estado[(l["tipo"], l["estado"])] += l["centavos"]
    return {
        "n": len(linhas), "itens": len(por_chave),
        "repetidos_itens": len(repetidos), "repetidos_pedidos": sum(repetidos.values()),
        "repetidos_max": max(repetidos.values()) if repetidos else 0,
        "proprios": sum(1 for l in linhas if l["chave"].startswith("yt:") and l["chave"][3:] in proprios),
        "origens": origens,
        "estados": [{"tipo": t, "estado": e, "n": n, "centavos": valor_estado[(t, e)]}
                    for (t, e), n in sorted(total_estado.items())],
        "por_mes": por_mes,
        "precos": precos,
        "de": meses[0] if meses else None, "ate": meses[-1] if meses else None,
    }


# ---------------------------------------------------------------- transcrições

def _lives_transcritas(conn: sqlite3.Connection) -> list[dict]:
    tr = _tab(conn, "01_historico__lives_transcricao")
    ll = _tab(conn, "01_historico__lives_lives")
    inicio = {lid: (i, f) for lid, i, f in conn.execute(
        f'SELECT live_id, inicio_real, fim_real FROM "{ll}" WHERE inicio_real <> \'\' AND fim_real <> \'\'')}
    segs = defaultdict(list)
    for lid, s, texto in conn.execute(f'SELECT live_id, inicio_s, texto FROM "{tr}" WHERE inicio_s <> \'\''):
        segs[lid].append((float(s), texto or ""))
    saida = []
    for lid, ss in segs.items():
        ss.sort()
        item = {"id": lid, "segs": ss, "duracao_h": (ss[-1][0] / 3600) if ss else 0, "ini": None, "fim": None}
        if lid in inicio:
            item["ini"], item["fim"] = _min_iso(inicio[lid][0]), _min_iso(inicio[lid][1])
            item["palavras"] = [(item["ini"] + int(s) // 60, _informativas(t)) for s, t in ss]
        saida.append(item)
    return saida


def _casa(msg_palavras: set[str], palavras: list[tuple[int, set[str]]], t: int) -> int | None:
    """Minuto em que a fala cobre o limiar das palavras da mensagem, ou None."""
    precisa = LIMIAR_LEITURA * len(msg_palavras)
    vistas: set[str] = set()
    for minuto, ws in palavras:
        if minuto < t - LEITURA_ANTES_MIN:
            continue
        if minuto > t + LEITURA_DEPOIS_MIN:
            break
        vistas |= msg_palavras & ws
        if len(vistas) >= precisa:
            return minuto
    return None


def _controle(msg_palavras: set[str], palavras: list[tuple[int, set[str]]], t: int, ini: int, fim: int) -> bool:
    """A mesma conta numa janela de mesmo tamanho, longe da mensagem (antes, se couber; senão depois)."""
    largura = LEITURA_ANTES_MIN + LEITURA_DEPOIS_MIN
    t0 = t - 120 if t - 120 - LEITURA_ANTES_MIN >= ini else t + 90
    if t0 + largura > fim and t0 > t:
        return False
    return _casa(msg_palavras, palavras, t0) is not None


def _fuso_livepix(msgs_lp: list[dict], lives: list[dict]) -> list[dict]:
    """Para cada deslocamento (literal = UTC + h), quantas mensagens caem numa live e quantas casam com a fala."""
    saida = []
    datadas = [l for l in lives if l["ini"] is not None]
    for h in range(-6, 5):
        n = lidas = 0
        for m in msgs_lp:
            if m["literal"] is None:
                continue
            t = m["literal"] - h * 60
            ws = _informativas(m["texto"])
            if len(ws) < LEITURA_MIN_PALAVRAS:
                continue
            for lv in datadas:
                if lv["ini"] <= t <= lv["fim"]:
                    n += 1
                    lidas += _casa(ws, lv["palavras"], t) is not None
                    break
        saida.append({"utc_mais": h, "na_live": n, "lidas": lidas})
    return saida


def _leitura(msgs: list[dict], lives: list[dict]) -> dict:
    datadas = [l for l in lives if l["ini"] is not None]
    por_plat: dict[str, dict] = {}
    atrasos, lidas_v, nao_v = [], [], []
    por_live = []
    for lv in datadas:
        dentro = [m for m in msgs if m["minuto"] is not None and lv["ini"] <= m["minuto"] <= lv["fim"]]
        n = lidas = ctrl = curtas = 0
        for m in dentro:
            ws = _informativas(m["texto"])
            if len(ws) < LEITURA_MIN_PALAVRAS:
                curtas += 1
                continue
            n += 1
            quando = _casa(ws, lv["palavras"], m["minuto"])
            acaso = _controle(ws, lv["palavras"], m["minuto"], lv["ini"], lv["fim"])
            ctrl += acaso
            p = por_plat.setdefault(m["plataforma"], {"n": 0, "lidas": 0, "controle": 0})
            p["n"] += 1
            p["controle"] += acaso
            if quando is not None:
                lidas += 1
                p["lidas"] += 1
                atrasos.append(max(0, quando - m["minuto"]))
                lidas_v.append(m["centavos"])
            else:
                nao_v.append(m["centavos"])
        por_live.append({"id": lv["id"], "mes": _mes_brt(lv["ini"]), "horas": (lv["fim"] - lv["ini"]) / 60,
                         "mensagens": len(dentro), "testaveis": n, "lidas": lidas, "controle": ctrl,
                         "curtas": curtas})
    n = sum(p["n"] for p in por_plat.values())
    lidas = sum(p["lidas"] for p in por_plat.values())
    ctrl = sum(p["controle"] for p in por_plat.values())
    return {
        "lives": len(datadas), "testaveis": n, "lidas": lidas, "controle": ctrl,
        "taxa": lidas / n if n else 0, "taxa_controle": ctrl / n if n else 0,
        "atraso_mediano": S.median(atrasos) if atrasos else None,
        "atraso_p75": sorted(atrasos)[int(0.75 * (len(atrasos) - 1))] if atrasos else None,
        "mediana_lidas": _mediana(lidas_v), "mediana_nao_lidas": _mediana(nao_v),
        "por_plataforma": por_plat, "por_live": sorted(por_live, key=lambda x: x["mes"]),
        "criterio": {"limiar": LIMIAR_LEITURA, "antes_min": LEITURA_ANTES_MIN, "depois_min": LEITURA_DEPOIS_MIN,
                     "min_palavras": LEITURA_MIN_PALAVRAS},
    }


# ---------------------------------------------------------------- comentários

def _comentarios(conn: sqlite3.Connection) -> dict:
    cm = _tab(conn, "01_historico__canal_comentarios")
    rows = [(v, t) for v, t in conn.execute(f'SELECT video_id, texto FROM "{cm}" WHERE texto <> \'\'')]
    c = Counter(intencao(t) or "comentário" for _, t in rows)
    return {"n": len(rows), "videos": len({v for v, _ in rows}),
            "intencoes": [{"intencao": k, "rotulo": ROTULO_INTENCAO[k], "n": c[k]} for k in INTENCOES]}


# ---------------------------------------------------------------- total

def avaliar_grupos(msgs: list[dict], definicoes: list[dict], catalogo: list[dict], lex: Lexico) -> list[dict]:
    """Evidência de cada grupo proposto para a fila de demanda.

    Um grupo junta mensagens por formato, por termo, por expressão regular (sobre o
    texto normalizado) ou por tema (basta um) e se
    restringe às intenções dadas. As definições ficam na pasta de trabalho: são
    montadas lendo as mensagens e mudam com a validação do time."""
    saida = []
    for g in definicoes:
        fmts, temas = set(g.get("formatos", [])), set(g.get("temas", []))
        termos = Lexico._compilar(g["termos"]) if g.get("termos") else None
        padrao = re.compile("|".join(g["regex"])) if g.get("regex") else None
        intencoes = set(g.get("intencoes", ["pedido", "pergunta", "mídia"]))
        sel = []
        for m in msgs:
            if m["intencao"] not in intencoes:
                continue
            tipo = m["tipo"] if m["plataforma"] == "Castcoin" else ""
            n = lex.limpar(normalizar(URL.sub(" ", m["texto"])))
            if ((fmts and fmts & formatos(m["texto"], tipo)) or (termos and termos.search(n))
                    or (padrao and padrao.search(n)) or (temas and temas & lex.temas_de(m["texto"]))):
                sel.append(m)
        meses = sorted({m["mes"] for m in sel if m["mes"]})
        cast = [m for m in sel if m["plataforma"] == "Castcoin"]
        saida.append({
            "id": g["id"], "nome": g["nome"], "tipo": g.get("tipo", "produto"),
            "n": len(sel), "centavos": sum(m["centavos"] for m in sel),
            "mediana": _mediana([m["centavos"] for m in sel]),
            "plataformas": {p: sum(1 for m in sel if m["plataforma"] == p) for p in ("Castcoin", "LivePix")},
            "castcoin_livre": sum(1 for m in cast if m["tipo"] == "Doação livre"),
            "intencoes": dict(Counter(m["intencao"] for m in sel)),
            "meses": len(meses), "de": meses[0] if meses else None, "ate": meses[-1] if meses else None,
            "produtos": _produtos_do_formato(catalogo, tuple(g.get("catalogo", []))) if g.get("catalogo") else [],
        })
    return saida


def calcular(conn: sqlite3.Connection, lexico: Lexico | None = None, grupos: list[dict] | None = None) -> dict:
    lex = lexico or Lexico()
    lives = _lives_transcritas(conn)

    lp = _tab(conn, "livepix__suplemento_livepix_mensagens")
    brutas_lp = [{"literal": _min_literal(d) if d else None, "texto": m} for d, m in conn.execute(
        f'SELECT data_literal_fonte, mensagem FROM "{lp}" WHERE mensagem <> \'\'')]
    fuso = _fuso_livepix(brutas_lp, lives)
    melhor = max(fuso, key=lambda x: (x["lidas"], -abs(x["utc_mais"] + 3)))

    msgs = mensagens(conn, melhor["utc_mais"])
    por_plat = {p: [m for m in msgs if m["plataforma"] == p] for p in ("Castcoin", "LivePix")}
    periodo = {p: (min(m["mes"] for m in ms if m["mes"]), max(m["mes"] for m in ms if m["mes"]))
               for p, ms in por_plat.items() if ms}
    catalogo = _catalogo(conn)

    return {
        "mensagens": len(msgs),
        "periodo": periodo,
        "por_plataforma": {p: {"n": len(ms), "composicao": _composicao(ms)} for p, ms in por_plat.items()},
        "formatos": _formatos(msgs, catalogo),
        "temas": _temas(msgs, lex, _oferta(conn)),
        "grupos": _grupos(msgs, lex),
        "midia": _fila_midia(conn),
        "fuso_livepix": {"testes": fuso, "escolhido": melhor["utc_mais"]},
        "leitura": _leitura(msgs, lives),
        "comentarios": _comentarios(conn),
        "lexico_carregado": bool(lex.temas),
        "rascunho_grupos": avaliar_grupos(msgs, grupos, catalogo, lex) if grupos else [],
    }
