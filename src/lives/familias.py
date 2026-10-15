"""As famílias de dados e o que se sabe sobre cada uma.

Uma família é o que o leitor reconhece ("contribuições da Castcoin",
"transcrições"), não um arquivo. Cada uma declara:

- a tabela principal e a coluna de tempo que definem volume e histórico;
- o status, com a razão dele escrita: status sem justificativa vira opinião;
- as frentes do plano que dependem dela;
- avisos fixos, tirados da documentação da entrega, e avisos calculados.

Este arquivo NÃO contém número tirado dos dados: contagens, períodos e
percentuais são calculados por `status.py` na hora. Aqui ficam só regras e
textos, para que o código possa ir para o git sem levar dado junto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# Status, do mais para o menos aproveitável.
UTILIZAVEL = "utilizavel"
PARCIAL = "parcial"
INSUFICIENTE = "insuficiente"
AUSENTE = "ausente"
FORA = "fora_do_escopo"

ROTULO_STATUS = {
    UTILIZAVEL: "Utilizável",
    PARCIAL: "Parcial",
    INSUFICIENTE: "Insuficiente",
    AUSENTE: "Ausente",
    FORA: "Fora do escopo",
}

# Nível dos avisos.
BLOQUEIA = "bloqueia"   # impede uma análise prevista no plano
ATENCAO = "atencao"     # análise possível, mas com regra de leitura
INFO = "info"           # contexto, sem restrição

ROTULO_NIVEL = {BLOQUEIA: "Bloqueia", ATENCAO: "Atenção", INFO: "Info"}

ALTA, MEDIA, BAIXA = "alta", "media", "baixa"
ROTULO_PRIORIDADE = {ALTA: "Alta", MEDIA: "Média", BAIXA: "Baixa"}

# formatos da coluna de tempo
ISO = "iso"                 # 2026-01-28T17:13:28Z (ou com minutos só)
DATA_BR = "data_br"         # 27/03/2023 21:15, sem fuso


@dataclass
class Familia:
    id: str
    nome: str
    fonte: str
    descricao: str
    tabela: str                 # sufixo da tabela de espelho (stg__...<sufixo>)
    unidade: str                # "contribuições", "lives"...
    status: str
    razao_status: str
    frentes: list[int]
    coluna_tempo: str | None = None
    formato_tempo: str = ISO
    rotulo_tempo: str = ""
    avisos: list[tuple[str, str]] = field(default_factory=list)
    # (rótulo, função(conn, tabela) -> texto) para números extras do cartão
    extras: list[tuple[str, Callable]] = field(default_factory=list)
    # função(conn) -> lista de (nível, texto) calculados na hora
    avisos_calculados: Callable | None = None
    # o aviso genérico "N registros sem data" é desligado quando um aviso
    # calculado já diz o mesmo com mais contexto
    avisar_sem_data: bool = True
    # o que pedir aos administradores: (pedido, prioridade, frentes destravadas)
    pedir: list[tuple[str, str, list[int]]] = field(default_factory=list)


def _tab(conn, sufixo: str) -> str:
    linha = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?",
        ("%" + sufixo,)).fetchone()
    if not linha:
        raise LookupError(f"tabela de espelho não encontrada: *{sufixo}")
    return linha[0]


def _n(conn, sufixo: str, onde: str = "1=1") -> int:
    return conn.execute(f'SELECT COUNT(*) FROM "{_tab(conn, sufixo)}" WHERE {onde}').fetchone()[0]


def _pct(parte: int, todo: int) -> str:
    return f"{(100 * parte / todo):.0f}%".replace(".", ",") if todo else "—"


def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# ---------------------------------------------------------------- calculados

def _avisos_lives(conn):
    total = _n(conn, "01_historico__lives_lives")
    sem = _n(conn, "01_historico__lives_lives", "trim(inicio_real) = ''")
    return [(BLOQUEIA, f"{_fmt(sem)} de {_fmt(total)} lives ({_pct(sem, total)}) sem horário "
                       "real de início: ficam fora do cruzamento com as doações (Frente 3).")]


def _avisos_minimos(conn):
    fixo = _n(conn, "01_historico__doacoes_minimos", "tipo_valor = 'preco_fixo'")
    minimo = _n(conn, "01_historico__doacoes_minimos", "tipo_valor = 'minimo'")
    return [(ATENCAO, f"{_fmt(fixo)} produtos já estão com preço fixo e {_fmt(minimo)} com "
                      "valor mínimo. O plano supunha valor aberto em todos: confirmar com a equipe.")]


def _avisos_compradores(conn):
    pares = _n(conn, "shopify__shopify_castcoin_contatos_correspondentes")
    return [(INFO, f"{_fmt(pares)} compradores da Shopify casam com contatos da Castcoin pelo "
                   "e-mail pseudonimizado. É indício de mesma pessoa, não prova.")]


def _avisos_transcricoes(conn):
    total = _n(conn, "01_historico__lives_lives")
    tab = _tab(conn, "01_historico__lives_transcricao")
    com = conn.execute(f'SELECT COUNT(DISTINCT live_id) FROM "{tab}"').fetchone()[0]
    return [(BLOQUEIA, f"Só {_fmt(com)} de {_fmt(total)} lives ({_pct(com, total)}) têm transcrição: "
                       "tema por minuto não se sustenta em escala.")]


def _avisos_chat(conn):
    t = "youtube_atual__disponibilidade_chat"
    disp = _n(conn, t, "estado_replay = 'replay_disponivel'")
    nao_ver = _n(conn, t, "estado_replay = 'nao_verificada'")
    oficiais = _n(conn, "youtube_atual__metricas_chat_oficiais")
    return [
        (INFO, f"Replay de chat disponível em {_fmt(disp)} lives e não verificado em {_fmt(nao_ver)}: "
               "há chat que ainda pode ser coletado."),
        (INFO, f"{_fmt(oficiais)} registros oficiais de contagem de mensagens por vídeo: "
               "dá para medir volume de chat, não o conteúdo."),
    ]


def _avisos_temas(conn):
    t = "analise_tematica__temas_lives"
    total = _n(conn, t)
    sem = _n(conn, t, "tema_principal = 'Assunto não identificável pelo título'")
    baixa = _n(conn, t, "confianca = 'baixa'")
    return [(ATENCAO, f"{_fmt(sem)} de {_fmt(total)} lives ({_pct(sem, total)}) sem assunto "
                      f"identificável pelo título; confiança baixa em {_fmt(baixa)}.")]


def _extra_lives_inicio(conn, tab):
    total = _n(conn, "01_historico__lives_lives")
    com = _n(conn, "01_historico__lives_lives", "trim(inicio_real) <> ''")
    return f"{_fmt(com)} ({_pct(com, total)})"


def _extra_lives_transcritas(conn, tab):
    return _fmt(conn.execute(f'SELECT COUNT(DISTINCT live_id) FROM "{tab}"').fetchone()[0])


def _extra_aud_lives(conn, tab):
    return _fmt(conn.execute(f'SELECT COUNT(DISTINCT live_id) FROM "{tab}"').fetchone()[0])


def _extra_ui_tipos(conn, tab):
    r = conn.execute(f'SELECT tipo_exibido, COUNT(*) FROM "{tab}" WHERE tipo_exibido <> \'\' '
                     'GROUP BY 1 ORDER BY 2 DESC').fetchall()
    return " · ".join(f"{t} {_fmt(n)}" for t, n in r) or "—"


def _extra_produtos(conn, tab):
    return _fmt(_n(conn, "01_historico__doacoes_produtos"))


def _extra_metas(conn, tab):
    return _fmt(_n(conn, "01_historico__doacoes_metas"))


def _extra_exec(conn, tab):
    r = conn.execute(f'SELECT estado_operacional, COUNT(*) FROM "{tab}" GROUP BY 1 ORDER BY 2 DESC').fetchall()
    return " · ".join(f"{t} {_fmt(n)}" for t, n in r)


def _extra_hotmart_status(conn, tab):
    ok = _n(conn, "hotmart_transacoes__transactions", "status_snapshot IN ('COMPLETE','APPROVED')")
    return f"{_fmt(ok)} concluídas ou aprovadas"


def _extra_moedas_hotmart(conn, tab):
    r = conn.execute(f'SELECT gross_currency, COUNT(*) FROM "{tab}" GROUP BY 1 ORDER BY 2 DESC').fetchall()
    return " · ".join(f"{m} {_fmt(n)}" for m, n in r)


def _extra_shopify_pagos(conn, tab):
    pagos = _n(conn, "shopify__shopify_pedidos", "situacao_financeira = 'PAID'")
    total = _n(conn, "shopify__shopify_pedidos")
    return f"{_fmt(pagos)} ({_pct(pagos, total)})"


def _extra_itens(conn, tab):
    return _fmt(_n(conn, "shopify__shopify_itens"))


def _extra_videos(conn, tab):
    r = conn.execute(f'SELECT tipo, COUNT(*) FROM "{tab}" GROUP BY 1 ORDER BY 2 DESC').fetchall()
    return " · ".join(f"{t} {_fmt(n)}" for t, n in r)


def _extra_temas(conn, tab):
    return _fmt(_n(conn, "analise_tematica__taxonomia"))


def _extra_contas(conn, tab):
    return _fmt(conn.execute(f'SELECT COUNT(DISTINCT account_id) FROM "{tab}"').fetchone()[0])


def _extra_msg_ui(conn, tab):
    com = _n(conn, "castcoin__suplemento_doacoes_ui", "trim(mensagem) <> ''")
    total = _n(conn, "castcoin__suplemento_doacoes_ui")
    return f"{_fmt(com)} ({_pct(com, total)})"


def _extra_msg_livepix(conn, tab):
    com = _n(conn, "livepix__suplemento_livepix_mensagens", "trim(mensagem) <> ''")
    total = _n(conn, "livepix__suplemento_livepix_mensagens")
    return f"{_fmt(com)} ({_pct(com, total)})"


# ------------------------------------------------------------------ famílias

FAMILIAS: list[Familia] = [
    Familia(
        id="castcoin_extrato", nome="Contribuições", fonte="Castcoin",
        descricao="Extrato de pagamentos confirmados: a série principal de doações e compras.",
        tabela="castcoin__suplemento_extrato", unidade="contribuições pagas",
        status=UTILIZAVEL, frentes=[1, 3],
        razao_status="Horário em UTC por contribuição e conciliação mensal com o painel sem diferença.",
        coluna_tempo="data_extrato_utc", rotulo_tempo="data do extrato",
        avisos=[
            (ATENCAO, "Extrato, Doações (tela), Vendas e Execução descrevem os mesmos fatos: nunca somar entre si."),
            (ATENCAO, "A data do extrato não é comprovadamente a do pagamento original."),
            (ATENCAO, "Histórico anterior ao primeiro registro não comprovado; o mês mais recente é parcial."),
            (INFO, "Conciliado mês a mês com o painel da plataforma, com diferença zero."),
        ],
        pedir=[("Extrato anterior ao primeiro registro entregue, se existir", MEDIA, [1, 3])],
    ),
    Familia(
        id="castcoin_tela", nome="Doações na tela", fonte="Castcoin",
        descricao="O que a plataforma mostra de cada doação: tipo (React, Música), mensagem, link e alerta.",
        tabela="castcoin__suplemento_doacoes_ui", unidade="doações exibidas",
        status=UTILIZAVEL, frentes=[1, 2],
        razao_status="Traz o tipo do pedido e a mensagem, que o extrato não tem.",
        coluna_tempo="data_exibida_utc", rotulo_tempo="data exibida",
        avisos=[
            (ATENCAO, "Precisão de minuto; o fuso da tela foi inferido e convertido para UTC."),
            (ATENCAO, "Mesmos fatos do extrato: usar para tipo e mensagem, não para somar valores."),
        ],
        extras=[("Tipos", _extra_ui_tipos), ("Com mensagem", _extra_msg_ui)],
    ),
    Familia(
        id="castcoin_catalogo", nome="Catálogo, preços e metas", fonte="Castcoin",
        descricao="Produtos à venda, valor mínimo ou preço de cada um, e metas configuradas.",
        tabela="01_historico__doacoes_minimos", unidade="produtos com valor configurado",
        status=PARCIAL, frentes=[1],
        razao_status="Só a configuração de hoje: sem histórico de mudanças de preço ou mínimo.",
        avisos=[
            (BLOQUEIA, "Sem histórico de mínimos e preços: não dá para medir o efeito de uma mudança de valor."),
            (ATENCAO, "Categoria e datas de criação dos produtos vieram vazias."),
            (ATENCAO, "Metas só com data de expiração configurada, sem início nem data em que foram batidas."),
        ],
        extras=[("Produtos", _extra_produtos), ("Metas", _extra_metas)],
        avisos_calculados=_avisos_minimos,
        pedir=[("Histórico de alterações de preço e de mínimo por produto, com a data de cada mudança", ALTA, [1]), ("Datas de início das metas e de quando foram batidas", MEDIA, [3]), ("Categoria e data de criação de cada produto", BAIXA, [1])],
    ),
    Familia(
        id="castcoin_execucao", nome="Execução de pedidos", fonte="Castcoin",
        descricao="Filas de React e Música: o que foi aceito, concluído ou rejeitado.",
        tabela="castcoin__suplemento_execucao_midias", unidade="pedidos nas filas",
        status=PARCIAL, frentes=[1, 2],
        razao_status="Mostra o estado do pedido, mas não a hora em que foi atendido.",
        coluna_tempo="data_exibida_utc", rotulo_tempo="data da mídia",
        avisos=[
            (BLOQUEIA, "Hora de atendimento não exposta: tempo de espera não é mensurável."),
            (ATENCAO, "Vínculo entre cada contribuição e o pedido executado não é completo."),
            (ATENCAO, "Período de cobertura diferente do extrato: comparar só na janela comum."),
        ],
        extras=[("Estados", _extra_exec)],
        pedir=[("Hora em que cada pedido foi atendido (exibido ou concluído na live)", ALTA, [1, 3]), ("Vínculo entre cada contribuição e o pedido executado", MEDIA, [1])],
    ),
    Familia(
        id="castcoin_compradores", nome="Compradores", fonte="Castcoin",
        descricao="Cadastro pseudonimizado de quem comprou ou doou.",
        tabela="01_historico__doacoes_compradores", unidade="compradores",
        status=INSUFICIENTE, frentes=[1, 4],
        razao_status="Sem datas e sem campos de perfil: não sustenta segmentação.",
        avisos=[
            (BLOQUEIA, "Sem perfil (cidade, faixa etária etc.) e sem datas de primeira e última compra."),
            (INFO, "Ids são pseudônimos de 16 caracteres; nenhum dado de contato foi entregue."),
        ],
        avisos_calculados=_avisos_compradores,
        pedir=[("Datas de cadastro e de primeira e última compra; campos de perfil disponíveis, sem dado de contato", MEDIA, [1])],
    ),
    Familia(
        id="livepix", nome="Mensagens", fonte="LivePix",
        descricao="Histórico da plataforma anterior, com valor e mensagem de cada doação.",
        tabela="livepix__suplemento_livepix_mensagens", unidade="mensagens",
        status=PARCIAL, frentes=[1, 2],
        razao_status="Série longa, mas sem fuso e sem confirmação de pagamento.",
        coluna_tempo="data_literal_fonte", formato_tempo=DATA_BR, rotulo_tempo="data declarada",
        avisos=[
            (ATENCAO, "Data sem fuso comprovado: serve para mês e dia, não para cruzar com o minuto da live."),
            (ATENCAO, "Valores observados, não pagamentos confirmados; não somar com a Castcoin."),
            (INFO, "Campos omitidos na revisão de privacidade estão registrados em suplemento próprio."),
        ],
        extras=[("Com mensagem", _extra_msg_livepix)],
        pedir=[("Fuso horário das datas do arquivo LivePix", MEDIA, [3])],
    ),
    Familia(
        id="shopify", nome="Loja", fonte="Shopify",
        descricao="Pedidos, itens, transações e reembolsos da loja.",
        tabela="shopify__shopify_pedidos", unidade="pedidos",
        status=UTILIZAVEL, frentes=[1],
        razao_status="Série completa no recorte, com situação financeira e itens.",
        coluna_tempo="criado_em", rotulo_tempo="criação do pedido",
        avisos=[
            (ATENCAO, "Registros de transação não são lucro nem depósito bancário."),
            (INFO, "Análises de coorte, recompra e RFV já vieram prontas na entrega."),
        ],
        extras=[("Pagos", _extra_shopify_pagos), ("Itens", _extra_itens)],
    ),
    Familia(
        id="hotmart", nome="Cursos", fonte="Hotmart",
        descricao="Transações dos cursos, com status, comissões e detalhes de preço.",
        tabela="hotmart_transacoes__transactions", unidade="transações",
        status=PARCIAL, frentes=[1],
        razao_status="Histórico curto, e consultas anteriores vazias não provam ausência de vendas.",
        coluna_tempo="order_date_iso_utc", rotulo_tempo="data do pedido",
        avisos=[
            (ATENCAO, "Moedas diferentes ficam separadas: nunca somar BRL com USD ou EUR."),
            (ATENCAO, "Aprovação não é liquidação; comissão não é caixa recebido."),
            (ATENCAO, "Último dia da série é parcial."),
        ],
        extras=[("Status", _extra_hotmart_status), ("Moedas", _extra_moedas_hotmart)],
        pedir=[("Confirmar se houve vendas antes do primeiro registro entregue", BAIXA, [1])],
    ),
    Familia(
        id="yt_lives", nome="Catálogo de lives", fonte="YouTube",
        descricao="Todas as lives dos dois canais, com título e horário quando disponível.",
        tabela="01_historico__lives_lives", unidade="lives",
        status=PARCIAL, frentes=[2, 3],
        razao_status="Catálogo completo, mas a maioria sem horário real de início.",
        coluna_tempo="inicio_real", rotulo_tempo="início real",
        avisos=[
            (ATENCAO, "Datas do Studio indicam o término, em dia, sem hora: não são início real."),
            (ATENCAO, "Apresentadores e horário agendado vieram vazios."),
        ],
        extras=[("Com início real", _extra_lives_inicio)],
        avisos_calculados=_avisos_lives,
        avisar_sem_data=False,
        pedir=[("Início real (data e hora) das lives que vieram sem esse campo", ALTA, [3])],
    ),
    Familia(
        id="yt_transcricoes", nome="Transcrições", fonte="YouTube",
        descricao="Fala das lives, em trechos com o segundo de início.",
        tabela="01_historico__lives_transcricao", unidade="trechos",
        status=INSUFICIENTE, frentes=[2, 3, 4],
        razao_status="Cobre poucas lives: não sustenta tema por minuto em escala.",
        avisos=[
            (BLOQUEIA, "Sem identificação de quem fala e sem fim do trecho."),
            (ATENCAO, "Alinhamento do segundo zero com o início real da live não verificado."),
            (INFO, "As transcrições das demais lives foram anunciadas para depois."),
        ],
        extras=[("Lives transcritas", _extra_lives_transcritas)],
        avisos_calculados=_avisos_transcricoes,
        pedir=[("Transcrições das demais lives, priorizando as que têm início real", ALTA, [2, 3]), ("Identificação de quem fala, se a ferramenta permitir", BAIXA, [2])],
    ),
    Familia(
        id="yt_chat", nome="Chat das lives", fonte="YouTube",
        descricao="Mensagens do chat ao vivo.",
        tabela="01_historico__lives_chat", unidade="mensagens",
        status=AUSENTE, frentes=[2, 4],
        razao_status="Nenhum texto de chat foi entregue.",
        avisos=[
            (BLOQUEIA, "Sem chat não há demanda gratuita (Frente 2) nem cruzamento doador × espectador (Frente 4)."),
        ],
        avisos_calculados=_avisos_chat,
        pedir=[("Replay do chat das lives com replay disponível ou ainda não verificado", ALTA, [2, 4])],
    ),
    Familia(
        id="yt_audiencia", nome="Audiência", fonte="YouTube",
        descricao="Espectadores simultâneos ao longo da live.",
        tabela="audiencia_15min__audiencia_pontos_observados", unidade="pontos observados",
        status=INSUFICIENTE, frentes=[3],
        razao_status="Poucas lives e eixo relativo, sem horário real.",
        avisos=[
            (BLOQUEIA, "Eixo relativo, sem UTC: não alinha com o minuto das doações."),
            (ATENCAO, "Média de pontos não é média temporal validada."),
        ],
        extras=[("Lives cobertas", _extra_aud_lives)],
        pedir=[("Espectadores simultâneos por minuto com horário real, para as lives com início real", MEDIA, [3])],
    ),
    Familia(
        id="yt_videos", nome="Vídeos e métricas", fonte="YouTube",
        descricao="Catálogo dos dois canais e métricas de cada vídeo.",
        tabela="01_historico__canal_videos", unidade="itens no catálogo",
        status=PARCIAL, frentes=[2, 3],
        razao_status="Métricas são uma foto única, sem série no tempo.",
        coluna_tempo="publicado_em", rotulo_tempo="publicação",
        avisos=[
            (ATENCAO, "Métricas fotografadas num único dia: não mostram evolução."),
            (ATENCAO, "Descrições vieram vazias: sem capítulos para conferir blocos de tema."),
            (ATENCAO, "Parte dos vídeos não tem exportação de analytics."),
        ],
        extras=[("Tipos", _extra_videos)],
        pedir=[("Descrições completas dos vídeos, com a minutagem de capítulos", BAIXA, [2]), ("Métricas em série por data, não só a foto atual", BAIXA, [3])],
    ),
    Familia(
        id="yt_comentarios", nome="Comentários", fonte="YouTube",
        descricao="Comentários nos vídeos.",
        tabela="01_historico__canal_comentarios", unidade="comentários",
        status=INSUFICIENTE, frentes=[2],
        razao_status="Amostra pequena e sem data.",
        avisos=[
            (ATENCAO, "Sem data de publicação: não dá para situar no tempo."),
            (INFO, "Textos com possível dado pessoal foram omitidos na origem."),
        ],
        pedir=[("Comentários com data de publicação", BAIXA, [2])],
    ),
    Familia(
        id="temas", nome="Temas das lives", fonte="Análise temática",
        descricao="Classificação de cada live por assunto, feita a partir do título.",
        tabela="analise_tematica__temas_lives", unidade="lives classificadas",
        status=PARCIAL, frentes=[2, 3],
        razao_status="Cobre todas as lives, mas classifica o título, não a fala.",
        avisos=[
            (ATENCAO, "Indicativa: título não é conteúdo. A transcrição completa permitirá refinar."),
        ],
        extras=[("Temas na taxonomia", _extra_temas)],
        avisos_calculados=_avisos_temas,
    ),
    Familia(
        id="financeiro", nome="Financeiro", fonte="Visor e relatórios",
        descricao="Movimentos de contas e relatórios financeiros anteriores.",
        tabela="06_visor__mensal_por_categoria", unidade="linhas mês × categoria",
        status=FORA, frentes=[],
        razao_status="Não faz parte das quatro frentes; recebido e guardado.",
        avisos=[
            (ATENCAO, "Bancos, cartões, transferências e créditos de plataforma exigem conciliação antes de qualquer soma."),
        ],
        extras=[("Contas", _extra_contas)],
    ),
]
