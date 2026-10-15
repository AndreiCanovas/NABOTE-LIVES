"""Recusa commit que leve dado das plataformas para dentro do repositório.

Os dados deste projeto são confidenciais e nunca entram no git, nem em
repositório privado: repositório se clona, se faz fork, muda de visibilidade
por engano, e o histórico guarda para sempre o que passou por ele. O dado vive
no drive restrito e na pasta de trabalho local; aqui fica só código.

O `.gitignore` já ignora as extensões de dado, mas ele não segura `git add -f`
nem um CSV renomeado para `.txt`. Esta guarda olha o que de fato está no
índice, por quatro critérios:

1. extensão de dado (CSV, ZIP, banco, planilha, legenda, PDF, JSON);
2. caminho que aponta para a pasta de dados;
3. arquivo grande demais para ser código (dado colado num .py também conta);
4. conteúdo com cara de dado pessoal ou de exportação: e-mail, CPF formatado,
   ou vários ids pseudônimos de 16 caracteres hexadecimais no mesmo arquivo.

Não há opção para pular a guarda. Se ela recusar um arquivo legítimo, o
arquivo muda (fixture sintética com ids como `comp_001`), não a regra.
"""

from __future__ import annotations

import re
import subprocess
import sys

EXTENSOES_PROIBIDAS = (
    ".csv", ".tsv", ".vtt", ".srt", ".zip", ".db", ".db-wal", ".db-shm",
    ".sqlite", ".sqlite3", ".parquet", ".xlsx", ".xls", ".pdf", ".json",
)
CAMINHOS_PROIBIDOS = ("dados_lives_confidencial", "dados/", "saida/", "relatorios/")
TAMANHO_MAXIMO = 300_000  # bytes; o maior arquivo de código daqui tem uma fração disso

EMAIL = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CPF = re.compile(rb"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
PSEUDONIMO = re.compile(rb"\b[0-9a-f]{16}\b")
PSEUDONIMOS_TOLERADOS = 3  # um hash de exemplo num teste passa; uma coluna de ids não

# e-mails que podem aparecer em código e documentação sem ser dado de ninguém
EMAILS_PERMITIDOS = (b"noreply@anthropic.com",)


def _staged() -> list[str]:
    saida = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        capture_output=True, check=True).stdout
    return [p for p in saida.decode().split("\0") if p]


def _conteudo(caminho: str) -> bytes:
    return subprocess.run(["git", "show", f":{caminho}"],
                          capture_output=True, check=True).stdout


def problemas(caminho: str, conteudo: bytes) -> list[str]:
    """Motivos para recusar este arquivo. Lista vazia = pode entrar."""
    motivos = []
    baixo = caminho.lower()
    if baixo.endswith(EXTENSOES_PROIBIDAS):
        motivos.append("extensão de arquivo de dados")
    if any(p in baixo for p in CAMINHOS_PROIBIDOS):
        motivos.append("caminho da pasta de dados")
    if len(conteudo) > TAMANHO_MAXIMO:
        motivos.append(f"{len(conteudo):,} bytes: grande demais para ser código")
    emails = [e for e in EMAIL.findall(conteudo) if e not in EMAILS_PERMITIDOS]
    if emails:
        motivos.append(f"{len(emails)} endereço(s) de e-mail")
    if CPF.search(conteudo):
        motivos.append("CPF formatado")
    n_pseud = len(set(PSEUDONIMO.findall(conteudo)))
    if n_pseud > PSEUDONIMOS_TOLERADOS:
        motivos.append(f"{n_pseud} ids pseudônimos de 16 hex: parece exportação")
    return motivos


def main() -> int:
    recusados = []
    for caminho in _staged():
        motivos = problemas(caminho, _conteudo(caminho))
        if motivos:
            recusados.append((caminho, motivos))
    if not recusados:
        return 0
    print("COMMIT RECUSADO: dado confidencial não entra no repositório.\n", file=sys.stderr)
    for caminho, motivos in recusados:
        print(f"  {caminho}: {'; '.join(motivos)}", file=sys.stderr)
    print("\nTire do índice com:  git restore --staged <arquivo>", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
