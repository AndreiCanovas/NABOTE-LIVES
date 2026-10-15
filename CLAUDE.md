# nabote-lives — regras para quem trabalha neste repositório

Este repositório guarda SÓ CÓDIGO, e pode ser público. Os dados das plataformas (Castcoin, LivePix,
Shopify, Hotmart, YouTube) são confidenciais e nunca entram aqui.

## Regras de confidencialidade (inegociáveis)

1. Nunca commitar dado, nem em repositório privado: CSV, ZIP, banco SQLite,
   planilha, PDF, JSON de saída, transcrição, ou qualquer amostra de linha real.
2. Nunca colocar dados dentro da pasta do repositório NABOTE: ele é PÚBLICO.
3. Nunca enviar dados a serviço externo, API ou site.
4. Saídas compartilhadas (páginas, documentos) só com números agregados, privadas
   e por convite. Nunca link aberto, nunca linha individual, nunca id pseudônimo.
5. O CÓDIGO pode ser público; os DADOS nunca. Por isso nada que venha dos dados
   entra aqui, nem agregado: contagens, totais e páginas geradas ficam na pasta
   de trabalho. Código e textos de regra (como `familias.py`) não levam número
   tirado dos dados.
6. Testes usam dados sintéticos, com ids como `comp_001`. Nunca copiar linha real
   para fixture.

As travas técnicas: `.gitignore`, `tools/guarda_dados.py` (pre-commit, ativar com
`git config core.hooksPath .githooks`) e o bloqueio global de extensões no git do
ambiente de trabalho.

## Onde ficam os dados

| Camada | Onde |
| --- | --- |
| Bruto | pasta restrita "nabote" no Google Drive (zip entregue pelos administradores) |
| Trabalho | `/home/user/dados_lives_confidencial/` (fora de qualquer repositório, modo 700) |
| Banco | `/home/user/dados_lives_confidencial/processado/lives.db`, reproduzível com `lives importar` |

O banco não tem backup próprio: ele se reconstrói em segundos a partir do zip
bruto. Uma cópia só existe se puder ser refeita.

## Documentação

- Plano (fonte da verdade): documento "Lives × NABOTE: plano prévio" no Claude Docs.
- Página para administradores e analistas: artefato HTML gerado por
  `lives pagina`, a partir do plano + status dos dados. A página é saída: fica na
  pasta de trabalho, nunca no git, porque traz contagens dos dados.
