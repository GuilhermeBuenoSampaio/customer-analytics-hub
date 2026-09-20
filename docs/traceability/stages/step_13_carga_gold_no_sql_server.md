# Etapa 13 — Carga Gold no SQL Server

## Objetivo

Registrar a execução, as evidências e o critério de conclusão da etapa **Carga Gold no SQL Server**.

## Implementação

- Script: `src/gold/loading/step_13_carga_gold_sql_server.py`
- SHA-256 do script: `b16229f87bf7758dbc67affa20bae2dbdce5aa9964d6ecc8867f7e3e67dcd844`
- Run ID: `retroativo_etapa_13_001`
- Registro UTC: `2026-09-20T16:17:25.479128+00:00`
- Status técnico informado: `success`

### Como foi feito

Carrega a Gold no SQL Server, registra auditoria e reconcilia linhas e hashes.

### Por que foi necessário

Garantir que o banco represente fielmente os Parquets aprovados.

## Evidências

- `outputs/logs/sql_load/sql_load_retroactive_20260920T161633Z.json` — SHA-256 `812d7f8c1d433f290b8727132b91988c78a48fa598f7f8960e7a56873d253682`

## Validação e critério de aceite

A etapa somente é considerada concluída quando o script termina com código zero, existe ao menos uma evidência material e este documento é gerado com sucesso.

## Decisões e limitações

- A documentação foi produzida a partir de arquivos efetivamente presentes no projeto.
- Ausência de evidência não é convertida automaticamente em aprovação.
- Credenciais, dados sensíveis e conteúdo do arquivo `.env` não são registrados.
