-- =============================================================================
-- 001 — procedência da importação
--
-- Cada CSV da entrega vira uma tabela de espelho (`stg__<caminho>`), com todas
-- as colunas em TEXT, exatamente como veio. O espelho não interpreta nada:
-- datas, centavos e situações são lidos pelas camadas de cima, que declaram a
-- regra que usam. Assim um erro de interpretação se corrige sem reimportar.
--
-- Esta tabela responde "de onde veio esse número" seis meses depois: qual zip,
-- qual arquivo, com que hash, quantas linhas. Sem ela, duas entregas com o
-- mesmo nome de arquivo seriam indistinguíveis.
-- =============================================================================

CREATE TABLE importacao (
  importacao_id INTEGER PRIMARY KEY,
  zip_sha256    TEXT    NOT NULL,
  zip_nome      TEXT    NOT NULL,
  arquivo       TEXT    NOT NULL,   -- caminho dentro do zip
  arquivo_sha256 TEXT   NOT NULL,
  tabela        TEXT,               -- NULL = arquivo não tabular (doc, planilha)
  linhas        INTEGER NOT NULL DEFAULT 0,
  colunas       INTEGER NOT NULL DEFAULT 0,
  -- linhas com número de campos diferente do cabeçalho: completadas/cortadas e contadas
  linhas_irregulares INTEGER NOT NULL DEFAULT 0,
  importado_em  TEXT    NOT NULL,
  UNIQUE (zip_sha256, arquivo),
  CHECK (linhas >= 0),
  CHECK (colunas >= 0),
  CHECK (linhas_irregulares >= 0)
) STRICT;

CREATE INDEX idx_importacao_tabela ON importacao (tabela);
