"""Conversão do plano: a estrutura do documento sobrevive."""

import unittest

from lives import doc_html

XML = ("<doc node='n' rev='3'>"
       "<paragraph id='a.0' heading='1'><text id='.1'>Plano X</text></paragraph>"
       "<paragraph id='.2'><date id='.3' value='2026-09-23'/><text id='.4'> · </text>"
       "<mention id='.5' user='u' name='ana' self='true'/></paragraph>"
       "<paragraph id='.6' heading='2'><text id='.7'>Seção Ú</text></paragraph>"
       "<paragraph id='.8'><text id='.9'><bold>Forte.</bold></text><text id='.10'> e </text>"
       "<text id='.11'><code>cod</code></text><text id='.12'> &amp; &lt;fim&gt;</text></paragraph>"
       "<list id='.13' kind='check'><listItem id='.14' checked='true'><paragraph id='.15'>"
       "<text id='.16'>feito</text></paragraph></listItem></list>"
       "<table id='.17'><row id='.18'><cell id='.19' header='true'><paragraph id='.20'>"
       "<text id='.21'>Col</text></paragraph></cell></row><row id='.22'><cell id='.23'>"
       "<paragraph id='.24'><text id='.25'>v</text></paragraph></cell></row></table>"
       "<paragraph id='.26'><mention id='.27' ref='project/x' label='Outro doc'/></paragraph>"
       "</doc>")


class TestDocHtml(unittest.TestCase):
    def setUp(self):
        self.r = doc_html.converter(XML)

    def test_titulo_sai_do_corpo(self):
        self.assertEqual(self.r["titulo"], "Plano X")
        self.assertNotIn("Plano X", self.r["html"])

    def test_secao_com_ancora(self):
        self.assertEqual(self.r["secoes"], [("doc-secao-u", "Seção Ú")])

    def test_marcacao_e_escape(self):
        h = self.r["html"]
        self.assertIn("<b>Forte.</b>", h)
        self.assertIn("<code>cod</code>", h)
        self.assertIn("&amp; &lt;fim&gt;", h)
        self.assertIn("23 set 2026 · @ana", h)
        self.assertIn('<li data-feito="1">feito</li>', h)
        self.assertIn("<thead><tr><th>Col</th></tr></thead>", h)
        self.assertIn("Outro doc", h)


if __name__ == "__main__":
    unittest.main()
