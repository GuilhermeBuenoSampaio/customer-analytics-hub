# Etapa 01 — Validação do contrato da fonte

## Objetivo

Registrar a execução, as evidências e o critério de conclusão da etapa **Validação do contrato da fonte**.

## Implementação

- Script: `src/ingestion/step_01_validacao_contrato_fonte.py`
- SHA-256 do script: `10e7385315d5eced926179aa93a804fff7fdc7e0d3d4313ce33ca0d2e3535035`
- Run ID: `retroativo_inicial_001`
- Registro UTC: `2026-09-20T15:45:20.438283+00:00`
- Status técnico informado: `success`

### Como foi feito

Compara arquivo, aba, colunas e contrato esperado antes da ingestão.

### Por que foi necessário

Impedir que uma fonte divergente contamine as camadas seguintes.

## Evidências

- `outputs/profiling/bronze_v3/step_01_validacao_contrato_fonte.xlsx` — SHA-256 `8a35b3fa6e8152bdbd637eed6f4fc3b2d19fffe8aee4c253f56f6a9d215b4c64`

## Validação e critério de aceite

A etapa somente é considerada concluída quando o script termina com código zero, existe ao menos uma evidência material e este documento é gerado com sucesso.

## Decisões e limitações

- A documentação foi produzida a partir de arquivos efetivamente presentes no projeto.
- Ausência de evidência não é convertida automaticamente em aprovação.
- Credenciais, dados sensíveis e conteúdo do arquivo `.env` não são registrados.
