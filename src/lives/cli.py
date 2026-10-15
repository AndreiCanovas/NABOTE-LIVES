"""lives — linha de comando do projeto.

    lives importar <zip>                  zip da entrega -> banco
    lives status                          status das famílias (JSON na pasta de trabalho)
    lives frente1                         agregados da Frente 1 (JSON na pasta de trabalho)
    lives frente3                         agregados da Frente 3 (JSON na pasta de trabalho)
    lives pagina --plano <leitura.json>   página compartilhada, a partir do plano + status

Tudo que sai daqui é gravado na pasta de trabalho, fora do repositório.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import db, doc_html, frente1, frente3, importar, pagina, status

SAIDA = db.PASTA_DADOS / "processado"


def _gravar(caminho: Path, texto: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
    os.chmod(caminho, 0o600)


def cmd_importar(a) -> int:
    conn = db.conectar(a.banco)
    db.migrar(conn)
    r = importar.importar_zip(conn, a.zip)
    if r["ja_importado"]:
        print(f"zip já importado ({r['zip_sha256'][:12]}…): nada a fazer")
    else:
        print(f"importado: {r['tabelas']} tabelas, {r['linhas']:,} linhas".replace(",", "."))
    return 0


def cmd_status(a) -> int:
    st = status.status_geral(db.conectar(a.banco))
    destino = Path(a.saida)
    _gravar(destino, json.dumps(st, ensure_ascii=False, indent=1))
    for c in st["familias"]:
        print(f"{c['status_rotulo']:<15} {c['fonte']} · {c['nome']}: {c['registros']:,} {c['unidade']}"
              .replace(",", "."))
    print(f"\n-> {destino}")
    return 0


def cmd_frente1(a) -> int:
    r = frente1.calcular(db.conectar(a.banco))
    _gravar(Path(a.saida), json.dumps(r, ensure_ascii=False, indent=1, default=str))
    print(f"-> {a.saida}")
    return 0


def cmd_frente3(a) -> int:
    r = frente3.calcular(db.conectar(a.banco))
    _gravar(Path(a.saida), json.dumps(r, ensure_ascii=False, indent=1, default=str))
    print(f"-> {a.saida}")
    return 0


def cmd_pagina(a) -> int:
    st = (json.loads(Path(a.status).read_text(encoding="utf-8")) if a.status
          else status.status_geral(db.conectar(a.banco)))
    xml, rev = doc_html.carregar_xml(a.plano)
    f1 = json.loads(Path(a.frente1).read_text(encoding="utf-8")) if a.frente1 else None
    # os achados são texto escrito a partir dos dados: vivem na pasta de trabalho, não no código
    achados = Path(a.achados).read_text(encoding="utf-8") if a.achados else ""
    f3 = json.loads(Path(a.frente3).read_text(encoding="utf-8")) if a.frente3 else None
    achados3 = Path(a.achados3).read_text(encoding="utf-8") if a.achados3 else ""
    html = pagina.montar(st, doc_html.converter(xml), rev, f1, achados, f3, achados3)
    for destino in a.saida:
        _gravar(Path(destino), html)
        print(f"-> {destino}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lives")
    p.add_argument("--banco", default=str(db.BANCO_PADRAO))
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("importar", help="zip da entrega -> banco")
    i.add_argument("zip")
    s = sub.add_parser("status", help="status das famílias de dados")
    s.add_argument("--saida", default=str(SAIDA / "status.json"))
    g = sub.add_parser("pagina", help="página compartilhada")
    g.add_argument("--plano", required=True, help="leitura completa do documento do plano (JSON)")
    g.add_argument("--status", help="status.json já calculado (padrão: calcula agora)")
    g.add_argument("--frente1", help="frente1.json já calculado")
    g.add_argument("--achados", help="HTML com os achados da Frente 1 (fica na pasta de trabalho)")
    g.add_argument("--frente3", help="frente3.json já calculado")
    g.add_argument("--achados3", help="HTML com os achados da Frente 3 (fica na pasta de trabalho)")
    g.add_argument("--saida", nargs="+", default=[str(SAIDA / "pagina" / "painel.html")])
    f = sub.add_parser("frente1", help="agregados da Frente 1")
    f.add_argument("--saida", default=str(SAIDA / "frente1.json"))
    f3 = sub.add_parser("frente3", help="agregados da Frente 3")
    f3.add_argument("--saida", default=str(SAIDA / "frente3.json"))
    a = p.parse_args(argv)
    return {"importar": cmd_importar, "status": cmd_status, "frente1": cmd_frente1,
            "frente3": cmd_frente3, "pagina": cmd_pagina}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
