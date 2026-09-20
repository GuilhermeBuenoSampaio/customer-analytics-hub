# Etapa 14 — Execução sequencial das análises SQL

## Objetivo

Registrar a execução, as evidências e o critério de conclusão da etapa **Execução sequencial das análises SQL**.

## Implementação

- Script: `src/sql/execution/run_sql_pipeline.py`
- SHA-256 do script: `e21911025bbd4a036682de95a4149431a3eee529f59004686a478bf0f2ead211`
- Run ID: `etapa14_sql_aprovada_001`
- Registro UTC: `2026-09-20T18:44:49.306993+00:00`
- Status técnico informado: `success`

### Como foi feito

Executa os arquivos SQL por pasta e nome, respeitando lotes GO e transações.

### Por que foi necessário

Reproduzir a EDA e análises futuras na mesma ordem, com log de falhas.

## Evidências

- `outputs/logs/sql_pipeline/sql_pipeline_20260920T182437_972857Z.json` — SHA-256 `7fd331d9fb6b1bbcaa0b24228b09bb28f226391071ef86ec9850648432f605d0`

## Validação e critério de aceite

A etapa somente é considerada concluída quando o script termina com código zero, existe ao menos uma evidência material e este documento é gerado com sucesso.

## Decisões e limitações

- A documentação foi produzida a partir de arquivos efetivamente presentes no projeto.
- Ausência de evidência não é convertida automaticamente em aprovação.
- Credenciais, dados sensíveis e conteúdo do arquivo `.env` não são registrados.
