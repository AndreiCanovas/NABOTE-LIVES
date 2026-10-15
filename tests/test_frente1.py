"""Frente 1 sobre tabelas sintéticas: regras de leitura que mudam o número."""

import unittest
from datetime import datetime

from lives import db, frente1


def _tabela(conn, nome, colunas, linhas):
    defs = ", ".join(f'"{c}" TEXT' for c in colunas)
    conn.execute(f'CREATE TABLE "{nome}" (_linha INTEGER PRIMARY KEY, {defs}) STRICT')
    for i, l in enumerate(linhas):
        conn.execute(f'INSERT INTO "{nome}" VALUES ({",".join("?" * (len(colunas) + 1))})', [i + 1, *l])


class TestRegras(unittest.TestCase):
    def test_fuso_de_brasilia(self):
        self.assertEqual(frente1._utc_para_brt("2025-06-01T02:30Z"), datetime(2025, 5, 31, 23, 30))

    def test_faixas_somam_um(self):
        f = frente1._faixas([500, 2000, 2000, 60000])
        self.assertAlmostEqual(sum(x["pct_n"] for x in f), 1)
        self.assertAlmostEqual(sum(x["pct_valor"] for x in f), 1)
        self.assertEqual([x["n"] for x in f if x["faixa"] == "R$ 500+"], [1])

    def test_mes_parcial(self):
        datas = [datetime(2025, 3, 20), datetime(2025, 4, 15), datetime(2025, 5, 31)]
        self.assertEqual(frente1._parcial(datas), {"2025-03"})


class TestDoacoes(unittest.TestCase):
    def setUp(self):
        c = self.conn = db.conectar(":memory:")
        _tabela(c, "stg__01_historico__doacoes_produtos", ["produto_id", "nome"],
                [["p_r", "React"], ["p_d", "Doação simples"], ["p_l", "Livro X"]])
        _tabela(c, "stg__01_historico__doacoes_minimos", ["produto_id", "tipo_valor", "valor_centavos"],
                [["p_r", "minimo", "1000"], ["p_d", "minimo", "500"], ["p_l", "preco_fixo", "2000"]])
        _tabela(c, "stg__x__castcoin__suplemento_doacoes_ui",
                ["tipo_exibido", "valor_centavos", "data_exibida_utc", "mensagem", "produto_id_correspondente_nome"],
                [["React", "1000", "2025-06-01T23:00Z", "oi", ""],
                 ["React", "3000", "2025-06-02T23:00Z", "", ""],
                 ["", "500", "2025-06-03T23:00Z", "valeu", ""],
                 ["", "2000", "2025-06-04T23:00Z", "", "p_l"]])          # venda da loja: fica de fora
        _tabela(c, "stg__x__livepix__suplemento_livepix_mensagens", ["valor_centavos", "data_literal_fonte"],
                [["2500", "10/05/2025 20:00"]])

    def test_loja_nao_entra_nas_doacoes(self):
        d = frente1.doacoes(self.conn)
        self.assertEqual(d["castcoin"]["n"], 3)
        self.assertEqual(d["castcoin"]["centavos"], 4500)

    def test_minimo_por_tipo(self):
        react = next(t for t in frente1.doacoes(self.conn)["tipos"] if t["tipo"] == "React")
        self.assertEqual(react["minimo"], 1000)
        self.assertEqual(react["pct_no_minimo"], 0.5)

    def test_livepix_e_castcoin_nao_se_somam(self):
        serie = frente1.doacoes(self.conn)["serie_mensal"]
        self.assertEqual({(s["plataforma"], s["mes"]) for s in serie},
                         {("LivePix", "2025-05"), ("Castcoin", "2025-06")})


if __name__ == "__main__":
    unittest.main()
