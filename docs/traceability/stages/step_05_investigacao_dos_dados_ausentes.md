# Etapa 05 — Investigação dos dados ausentes

## Objetivo

Registrar a execução, as evidências e o critério de conclusão da etapa **Investigação dos dados ausentes**.

## Implementação

- Script: `src/bronze/profiling/step_05_investigacao_dados_ausentes.py`
- SHA-256 do script: `f9fcf0718b711533be3236043ad2694c620c47e7340bf857c39d5b42b98957f7`
- Run ID: `retroativo_inicial_001`
- Registro UTC: `2026-09-20T15:45:20.680686+00:00`
- Status técnico informado: `success`

### Como foi feito

Quantifica nulidade e avalia sua concentração por coluna e unidade de análise.

### Por que foi necessário

Separar ausência legítima de falha de qualidade e evitar imputação sem evidência.

## Evidências

- `outputs/profiling/bronze_v3/step_05_investigacao_dados_ausentes.xlsx` — SHA-256 `6860760d2c975e58955438faccfc5ba73495387221c33b5d319a76cee3cda088`

## Validação e critério de aceite

A etapa somente é considerada concluída quando o script termina com código zero, existe ao menos uma evidência material e este documento é gerado com sucesso.

## Decisões e limitações

- A documentação foi produzida a partir de arquivos efetivamente presentes no projeto.
- Ausência de evidência não é convertida automaticamente em aprovação.
- Credenciais, dados sensíveis e conteúdo do arquivo `.env` não são registrados.
