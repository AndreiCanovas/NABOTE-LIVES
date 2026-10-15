"""Status de família, sobre tabela sintética."""

import unittest

from lives import db, familias as F, status


class TestStatus(unittest.TestCase):
    def setUp(self):
        self.conn = db.conectar(":memory:")
        self.conn.execute('CREATE TABLE "stg__x__eventos" (_linha INTEGER PRIMARY KEY, quando TEXT, v TEXT) STRICT')
        for i, q in enumerate(["2026-01-10T10:00Z", "2026-01-20T10:00Z", "2026-04-02T10:00Z", ""]):
            self.conn.execute('INSERT INTO "stg__x__eventos" VALUES (?,?,?)', (i + 1, q, "a"))

    def fam(self, **kw):
        base = dict(id="x", nome="Eventos", fonte="Teste", descricao="d", tabela="x__eventos",
                    unidade="eventos", status=F.UTILIZAVEL, razao_status="r", frentes=[1],
                    coluna_tempo="quando", rotulo_tempo="data",
                    avisos=[(F.INFO, "regra fixa")])
        base.update(kw)
        return F.Familia(**base)

    def test_periodo_e_lacuna(self):
        c = status.status_familia(self.conn, self.fam())
        p = c["periodo"]
        self.assertEqual((p["inicio"], p["fim"]), ("2026-01-10", "2026-04-02"))
        self.assertEqual((p["meses_historico"], p["meses_com_dado"]), (4, 2))
        textos = [a["texto"] for a in c["avisos"]]
        self.assertIn("2 meses do período sem nenhum registro com data.", textos)
        self.assertTrue(any("sem data" in t for t in textos), "linha sem data é avisada")

    def test_ponto_principal_prefere_bloqueio(self):
        c = status.status_familia(self.conn, self.fam(avisos=[(F.ATENCAO, "leitura"), (F.BLOQUEIA, "trava")]))
        self.assertEqual(c["principal"], "trava")
        self.assertEqual(c["avisos"][0]["nivel"], F.BLOQUEIA, "bloqueio vem primeiro")

    def test_tabela_vazia_vira_ausente(self):
        self.conn.execute('DELETE FROM "stg__x__eventos"')
        c = status.status_familia(self.conn, self.fam())
        self.assertEqual(c["status"], F.AUSENTE)

    def test_data_br(self):
        self.assertEqual(status._data("27/03/2023 21:15", F.DATA_BR), "2023-03-27")
        self.assertIsNone(status._data("ontem", F.ISO))

    def test_familias_nao_levam_numero_dos_dados(self):
        """Regra do repositório: textos de família não citam anos nem contagens."""
        import re
        for f in F.FAMILIAS:
            textos = [f.descricao, f.razao_status] + [t for _, t in f.avisos] + [p for p, _, _ in f.pedir]
            for t in textos:
                self.assertIsNone(re.search(r"\b20\d\d\b|\d[\d.]{2,}", t), f"{f.id}: {t}")


if __name__ == "__main__":
    unittest.main()
