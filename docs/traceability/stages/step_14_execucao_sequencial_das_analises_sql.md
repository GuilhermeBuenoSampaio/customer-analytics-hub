# Etapa 14 — Execução sequencial das análises SQL

## Objetivo

Registrar a execução, as evidências e o critério de conclusão da etapa **Execução sequencial das análises SQL**.

## Implementação

- Script: `src/sql/execution/run_sql_pipeline.py`
- SHA-256 do script: `ffec9c81fc27a13e61e4835d5bdeff54eece24209c99c5d1daf81cadbf5ecdae`
- Run ID: `retroactive`
- Registro UTC: `2026-09-20T01:18:12.940393+00:00`
- Status técnico informado: `unverified`

### Como foi feito

Executa os arquivos SQL por pasta e nome, respeitando lotes GO e transações.

### Por que foi necessário

Reproduzir a EDA e análises futuras na mesma ordem, com log de falhas.

## Evidências

- Nenhuma evidência material localizada; etapa mantida pendente.

## Validação e critério de aceite

A etapa somente é considerada concluída quando o script termina com código zero, existe ao menos uma evidência material e este documento é gerado com sucesso.

## Decisões e limitações

- A documentação foi produzida a partir de arquivos efetivamente presentes no projeto.
- Ausência de evidência não é convertida automaticamente em aprovação.
- Credenciais, dados sensíveis e conteúdo do arquivo `.env` não são registrados.
