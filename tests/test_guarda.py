"""A guarda de pre-commit recusa o que tem cara de dado."""

import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "guarda", Path(__file__).resolve().parents[1] / "tools" / "guarda_dados.py")
guarda = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guarda)


class TestGuarda(unittest.TestCase):
    def test_extensao_de_dado(self):
        for nome in ["x.csv", "a/b.zip", "lives.db", "p.xlsx", "status.json", "t.vtt"]:
            self.assertTrue(guarda.problemas(nome, b"conteudo"), nome)

    def test_caminho_da_pasta_de_dados(self):
        self.assertTrue(guarda.problemas("dados_lives_confidencial/x.txt", b"a"))

    def test_conteudo_pessoal(self):
        # montados em tempo de execução para o próprio teste não carregar o padrão
        email = ("fulana" + "@" + "exemplo.com.br").encode()
        cpf = ".".join(["123", "456", "789"]).encode() + b"-09"
        self.assertTrue(guarda.problemas("n.py", b"contato = '" + email + b"'"))
        self.assertTrue(guarda.problemas("n.py", b"cpf = '" + cpf + b"'"))
        ids = b"\n".join(f"{i:016x}".encode() for i in range(10))
        self.assertTrue(guarda.problemas("n.py", ids), "coluna de pseudônimos colada em código")

    def test_codigo_normal_passa(self):
        self.assertEqual(guarda.problemas("src/x.py", b"def f():\n    return 1\n"), [])
        self.assertEqual(guarda.problemas("t.py", b"id = 'comp_001'"), [])


if __name__ == "__main__":
    unittest.main()
