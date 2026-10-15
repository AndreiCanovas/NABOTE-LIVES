"""Importação do zip, com dados inventados à mão (nunca linhas reais)."""

import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from lives import db, importar


def _zip(arquivos: dict[str, str]) -> Path:
    pasta = Path(tempfile.mkdtemp())
    caminho = pasta / "entrega_sintetica.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        for nome, texto in arquivos.items():
            z.writestr(nome, texto)
    return caminho


class TestImportar(unittest.TestCase):
    def setUp(self):
        self.conn = db.conectar(":memory:")
        db.migrar(self.conn)

    def test_csv_vira_tabela_com_procedencia(self):
        z = _zip({"01_Historico/doacoes_pedidos.csv": "﻿pedido_id,valor_centavos\np_001,500\np_002,1200\n",
                  "LEIAME.md": "# documentação\n"})
        r = importar.importar_zip(self.conn, z)
        self.assertEqual(r["tabelas"], 1)
        self.assertEqual(r["linhas"], 2)
        linhas = self.conn.execute('SELECT pedido_id, valor_centavos FROM '
                                   '"stg__01_historico__doacoes_pedidos" ORDER BY _linha').fetchall()
        self.assertEqual([tuple(x) for x in linhas], [("p_001", "500"), ("p_002", "1200")])
        docs = self.conn.execute("SELECT tabela FROM importacao WHERE arquivo='LEIAME.md'").fetchone()
        self.assertIsNone(docs[0], "documento entra na procedência, mas não vira tabela")

    def test_mesmo_zip_nao_reimporta(self):
        z = _zip({"a.csv": "x\n1\n"})
        importar.importar_zip(self.conn, z)
        self.assertTrue(importar.importar_zip(self.conn, z)["ja_importado"])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM importacao").fetchone()[0], 1)

    def test_linha_irregular_e_contada_nao_perdida(self):
        z = _zip({"a.csv": "x,y\n1,2\n3\n4,5,6\n"})
        importar.importar_zip(self.conn, z)
        irreg = self.conn.execute("SELECT linhas, linhas_irregulares FROM importacao").fetchone()
        self.assertEqual(tuple(irreg), (3, 2))

    def test_coluna_repetida_ou_sem_nome(self):
        self.assertEqual(importar._colunas(["Valor", "valor", "", "1a"]),
                         ["valor", "valor_2", "col_3", "c_1a"])


if __name__ == "__main__":
    unittest.main()
