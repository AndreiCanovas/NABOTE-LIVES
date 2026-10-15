"""Frente 3 sobre um calendário sintético: janela, noite suspeita e efeito na mesma hora."""

import unittest

from lives import db, frente3


def _tabela(conn, nome, colunas, linhas):
    defs = ", ".join(f'"{c}" TEXT' for c in colunas)
    conn.execute(f'CREATE TABLE "{nome}" (_linha INTEGER PRIMARY KEY, {defs}) STRICT')
    for i, l in enumerate(linhas):
        conn.execute(f'INSERT INTO "{nome}" VALUES ({",".join("?" * (len(colunas) + 1))})', [i + 1, *l])


def _doacao(iso, valor="1000", tipo=""):
    return [tipo, valor, iso, ""]


class TestFrente3(unittest.TestCase):
    def setUp(self):
        c = self.conn = db.conectar(":memory:")
        # última live sem horário em abril -> janela começa em maio
        _tabela(c, "stg__x__analise_tematica__contexto_lives",
                ["live_id", "inicio_real_utc", "termino_exibido_studio_data"],
                [["lv_antiga", "", "2025-04-20"], ["lv_1", "2025-05-05T22:00:00Z", ""]])
        # live registrada: 5/mai, 19h às 22h de Brasília (22h–01h UTC)
        _tabela(c, "stg__x__01_historico__lives_lives", ["live_id", "inicio_real", "fim_real"],
                [["lv_1", "2025-05-05T22:00:00Z", "2025-05-06T01:00:00Z"]])
        _tabela(c, "stg__x__analise_tematica__temas_lives",
                ["live_id", "tema_principal", "confianca", "tipo_de_live"], [["lv_1", "Tema A", "alta", "x"]])
        doacoes = []
        # 6 doações durante a live, às 20h de Brasília
        doacoes += [_doacao(f"2025-05-05T23:{m:02d}Z") for m in range(0, 60, 10)]
        # noite comum (sem live): 1 doação às 20h de Brasília
        doacoes += [_doacao("2025-05-07T23:10Z")]
        # noite suspeita: 3 Reacts sem live registrada
        doacoes += [_doacao(f"2025-05-09T23:{m:02d}Z", tipo="React") for m in (0, 5, 10)]
        doacoes += [_doacao("2025-05-20T23:00Z")]   # fixa o fim da janela
        _tabela(c, "stg__x__castcoin__suplemento_doacoes_ui",
                ["tipo_exibido", "valor_centavos", "data_exibida_utc", "produto_id_correspondente_nome"],
                doacoes)

    def test_janela_comeca_depois_da_ultima_live_sem_horario(self):
        self.assertEqual(frente3._janela(self.conn)[0], "2025-05-01T03:00Z")

    def test_noite_suspeita_sai_da_base(self):
        r = frente3.calcular(self.conn)
        self.assertEqual(r["suspeitas"]["noites"], 1)
        self.assertEqual(r["suspeitas"]["react"], 3)
        self.assertEqual(r["dentro"]["n"], 6)
        self.assertEqual(r["fora"]["n"], 2)

    def test_efeito_limpo_maior_que_conservador(self):
        r = frente3.calcular(self.conn)
        self.assertGreater(r["esperado_limpo"]["efeito_n"], r["esperado"]["efeito_n"])

    def test_perfil_conta_so_lives_no_ar(self):
        r = frente3.calcular(self.conn)
        depois_do_fim = [p for p in r["perfil_inicio"] if p["min"] >= 180]
        self.assertTrue(all(p["lives"] == 0 for p in depois_do_fim))


if __name__ == "__main__":
    unittest.main()
