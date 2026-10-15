"""Frente 2 sobre mensagens sintéticas: intenção, formato, tema, preço por minuto e leitura na live."""

import unittest

from lives import db, frente2


def _tabela(conn, nome, colunas, linhas):
    defs = ", ".join(f'"{c}" TEXT' for c in colunas)
    conn.execute(f'CREATE TABLE "{nome}" (_linha INTEGER PRIMARY KEY, {defs}) STRICT')
    for i, l in enumerate(linhas):
        conn.execute(f'INSERT INTO "{nome}" VALUES ({",".join("?" * (len(colunas) + 1))})', [i + 1, *l])


LEXICO = frente2.Lexico({
    "temas": {"Tema A": ["planeta*", "estrela"], "Tema B": ["receita*"]},
    "frases_ignorar": ["bom dia"],
    "termos_ignorar": ["apresentador"],
})


class TestRegras(unittest.TestCase):
    def test_intencao(self):
        casos = {
            "Apresentador, fala sobre planetas": "pedido",
            "Joga mais uma hora": "pedido",
            "Você poderia explicar a estrela?": "pedido",
            "Vai ter maratona?": "pedido",
            "Qual a sua opinião?": "pergunta",
            "Bom dia, valeu pela live": "apoio",
            "Essa fala do convidado foi ruim": "comentário",
            "faz sentido isso": "comentário",
            "ele fala sobre isso": "comentário",
            "veja https://exemplo.com/v": "mídia",
            "Compra do produto: Item": None,
        }
        for texto, esperado in casos.items():
            self.assertEqual(frente2.intencao(texto), esperado, texto)

    def test_formatos(self):
        self.assertIn("Jogo", frente2.formatos("joga o jogo novo"))
        self.assertIn("Quanto custa (preço a combinar)", frente2.formatos("quanto pra ler o livro?"))
        self.assertIn("Livro e leitura", frente2.formatos("quanto pra ler o livro?"))
        self.assertEqual(frente2.formatos("https://exemplo.com/v", "Música"), {"Música"})

    def test_lexico_ignora_frases_e_acha_prefixo(self):
        self.assertEqual(LEXICO.temas_de("Bom dia! Fala dos planetas"), {"Tema A"})
        self.assertEqual(LEXICO.temas_de("nada a ver"), set())

    def test_origem_do_link(self):
        self.assertEqual(frente2._origem("https://youtu.be/abcdefgh123?si=x")[0], "YouTube")
        self.assertEqual(frente2._origem("https://www.youtube.com/shorts/abcdefgh123")[0], "YouTube Shorts")
        self.assertEqual(frente2._origem("https://x.com/u/status/123")[1], "x:123")
        self.assertEqual(frente2._origem("https://youtu.be/abcdefgh123")[1],
                         frente2._origem("https://www.youtube.com/watch?v=abcdefgh123&amp;t=0")[1])

    def test_moda_relativa_ignora_quem_paga_acima(self):
        moda, n = frente2._moda_relativa([20.0, 20.1, 19.9, 20.0, 55.0, 90.0])
        self.assertAlmostEqual(moda, 20.0, places=1)
        self.assertEqual(n, 4)


class TestCalcular(unittest.TestCase):
    def setUp(self):
        c = self.conn = db.conectar(":memory:")
        ui = [
            ["React", "2000", "2025-05-05T23:10Z", "https://youtu.be/abcdefgh123", ""],
            ["", "1000", "2025-05-05T23:20Z", "Apresentador, fala sobre planetas e estrelas distantes hoje", ""],
            ["", "500", "2025-05-05T23:30Z", "Qual receita favorita?", ""],
            ["", "4990", "2025-05-05T23:40Z", "Compra do produto: Item", "Item"],
            ["", "500", "2025-05-07T23:10Z", "boa live", ""],
        ]
        _tabela(c, "stg__x__castcoin__suplemento_doacoes_ui",
                ["tipo_exibido", "valor_centavos", "data_exibida_utc", "mensagem", "produto_id_correspondente_nome"],
                ui)
        # LivePix em horário de Brasília: 20h05 local = 23h05 UTC, dentro da live
        _tabela(c, "stg__x__livepix__suplemento_livepix_mensagens",
                ["valor_centavos", "data_literal_fonte", "mensagem"],
                [["2000", "05/05/2025 20:05", "Pergunta sobre cometas brilhantes gigantes amarelos"]])
        _tabela(c, "stg__x__01_historico__lives_lives", ["live_id", "inicio_real", "fim_real"],
                [["lv_1", "2025-05-05T23:00:00Z", "2025-05-06T01:00:00Z"]])
        # a fala lê as duas mensagens poucos minutos depois
        _tabela(c, "stg__x__01_historico__lives_transcricao", ["live_id", "inicio_s", "texto"],
                [["lv_1", "60", "abertura"],
                 ["lv_1", "420", "ele pergunta sobre cometas brilhantes gigantes amarelos"],
                 ["lv_1", "1320", "o apresentador fala sobre planetas e estrelas distantes hoje"]])
        _tabela(c, "stg__x__analise_tematica__temas_lives", ["live_id", "tema_principal"],
                [["lv_1", "Tema A"], ["lv_2", "Tema B"], ["lv_3", frente2.DESCONHECIDO]])
        _tabela(c, "stg__x__01_historico__doacoes_produtos", ["produto_id", "nome"],
                [["p1", "React"], ["p2", "Item"]])
        _tabela(c, "stg__x__01_historico__doacoes_minimos", ["produto_id", "tipo_valor", "valor_centavos"],
                [["p1", "minimo", "1000"], ["p2", "preco_fixo", "4990"]])
        # React: 20 centavos por segundo; um pedido pagou acima da tabela
        _tabela(c, "stg__x__castcoin__suplemento_execucao_midias",
                ["tipo", "estado_operacional", "data_exibida_utc", "valor_centavos", "link_midia", "duracao_paga"],
                [["REACT", "concluidos", "2025-05-05T23:10Z", "2000", "https://youtu.be/abcdefgh123", "01:40"],
                 ["REACT", "aceitos", "2025-05-06T23:10Z", "1200", "https://youtu.be/abcdefgh123", "01:00"],
                 ["REACT", "aceitos", "2025-05-07T23:10Z", "5000", "https://x.com/u/status/9", "00:30"]])
        _tabela(c, "stg__x__01_historico__canal_videos", ["video_id"], [["abcdefgh123"]])
        _tabela(c, "stg__x__01_historico__canal_comentarios", ["video_id", "texto"],
                [["v1", "Qual o próximo tema?"], ["v1", "ótimo"]])
        self.r = frente2.calcular(c, LEXICO)

    def test_compra_sai_e_plataformas_nao_somam(self):
        self.assertEqual(self.r["por_plataforma"]["Castcoin"]["n"], 4)
        self.assertEqual(self.r["por_plataforma"]["LivePix"]["n"], 1)

    def test_fuso_livepix_escolhe_brasilia(self):
        self.assertEqual(self.r["fuso_livepix"]["escolhido"], -3)

    def test_leitura_na_live(self):
        lt = self.r["leitura"]
        self.assertEqual(lt["testaveis"], 2)
        self.assertEqual(lt["lidas"], 2)
        self.assertEqual(lt["controle"], 0)

    def test_tema_demanda_e_oferta(self):
        linhas = {l["tema"]: l for l in self.r["temas"]["linhas"]}
        self.assertEqual(linhas["Tema A"]["n"], 1)
        self.assertEqual(linhas["Tema B"]["n"], 1)
        self.assertAlmostEqual(linhas["Tema A"]["oferta"], 0.5)
        self.assertNotIn(frente2.DESCONHECIDO, linhas)

    def test_midia_preco_e_repeticao(self):
        md = self.r["midia"]
        self.assertEqual(md["repetidos_itens"], 1)
        self.assertEqual(md["repetidos_pedidos"], 2)
        self.assertEqual(md["proprios"], 2)
        precos = [p for p in md["precos"] if p["tipo"] == "React"]
        self.assertEqual(sum(p["n"] for p in precos), 3)
        self.assertAlmostEqual(precos[0]["reais_por_minuto"], 12.0)

    def test_formato_aponta_produto_do_catalogo(self):
        react = next(f for f in self.r["formatos"] if f["formato"] == "React a vídeo")
        self.assertEqual([p["nome"] for p in react["produtos"]], ["React"])

    def test_comentarios(self):
        c = {i["intencao"]: i["n"] for i in self.r["comentarios"]["intencoes"]}
        self.assertEqual(c["pergunta"], 1)

    def test_grupos_por_termo_tema_e_intencao(self):
        grupos = [
            {"id": "astro", "nome": "Astronomia", "termos": ["planeta*"], "intencoes": ["pedido"],
             "catalogo": ["react"]},
            {"id": "culinaria", "nome": "Culinária", "temas": ["Tema B"], "intencoes": ["pedido", "pergunta"]},
            {"id": "so_apoio", "nome": "Só apoio", "regex": [r"\bboa live\b"], "intencoes": ["pedido"]},
        ]
        r = {g["id"]: g for g in frente2.calcular(self.conn, LEXICO, grupos)["rascunho_grupos"]}
        self.assertEqual(r["astro"]["n"], 1)
        self.assertEqual(r["astro"]["castcoin_livre"], 1)
        self.assertEqual([p["nome"] for p in r["astro"]["produtos"]], ["React"])
        self.assertEqual(r["culinaria"]["intencoes"], {"pergunta": 1})
        self.assertEqual(r["so_apoio"]["n"], 0)   # "boa live" é apoio, não pedido


if __name__ == "__main__":
    unittest.main()
