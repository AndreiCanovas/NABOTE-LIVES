# nabote-lives

Análise das lives e das vendas/doações que acontecem em volta delas: o que o
público compra e pede, por quanto, e como a live mexe nos pedidos. Os temas
das lives vêm das pautas do [NABOTE](https://github.com/AndreiCanovas/NABOTE).

**Este repositório só tem código.** Os dados são confidenciais e nunca entram
aqui; leia [`CLAUDE.md`](CLAUDE.md) antes de qualquer commit.

## Uso

```bash
pip install -e .
git config core.hooksPath .githooks       # trava de dados, uma vez por clone

lives importar <zip da entrega>           # zip -> banco, com procedência
lives status                              # status de cada família de dados
lives pagina --plano <leitura do plano>   # página para administradores e analistas
```

Tudo que esses comandos produzem vai para a pasta de trabalho
(`/home/user/dados_lives_confidencial/processado/`), nunca para o repositório.

## Como as peças se ligam

| Peça | Papel |
| --- | --- |
| `importar.py` | cada CSV do zip vira uma tabela de espelho `stg__…`, em TEXT, como veio; `importacao` guarda zip, arquivo, hash e linhas |
| `familias.py` | o que se sabe de cada família de dados: status e razão, frentes, avisos e o que falta pedir. Sem número tirado dos dados |
| `status.py` | volume, histórico (meses cobertos e meses com dado) e avisos calculados do banco |
| `doc_html.py` | converte o plano (documento, fonte da verdade) em HTML |
| `pagina.py` | junta status + plano + pedido de extração na página compartilhada |

## Sincronizar a página com o plano

O plano é editado no documento. Para a página acompanhar:

1. ler o documento inteiro (a leitura completa sai num JSON);
2. `lives pagina --plano <esse JSON>`;
3. republicar a página no mesmo endereço.

## Testes

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Todos com dados sintéticos, ids como `comp_001`.
