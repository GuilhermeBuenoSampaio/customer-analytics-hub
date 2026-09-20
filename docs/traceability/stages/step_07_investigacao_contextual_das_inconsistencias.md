# Etapa 07 — Investigação contextual das inconsistências

## Objetivo

Registrar a execução, as evidências e o critério de conclusão da etapa **Investigação contextual das inconsistências**.

## Implementação

- Script: `src/bronze/profiling/step_07_investigacao_contextual_inconsistencias.py`
- SHA-256 do script: `bf6800602a85437c53cc8f375f8d4aead731740d2f31122b8c90ec53d2b477c3`
- Run ID: `retroativo_inicial_001`
- Registro UTC: `2026-09-20T15:45:20.809467+00:00`
- Status técnico informado: `success`

### Como foi feito

Analisa inconsistências que dependem de contexto e combinações de atributos.

### Por que foi necessário

Nem toda anomalia estatística representa erro; o contexto orienta a decisão.

## Evidências

- `outputs/profiling/bronze_v3/step_07_investigacao_contextual_inconsistencias.xlsx` — SHA-256 `9a26da6b71078e0649fb031041bd693fcd1db36d6f9c8cbd828927e0b886e54e`

## Validação e critério de aceite

A etapa somente é considerada concluída quando o script termina com código zero, existe ao menos uma evidência material e este documento é gerado com sucesso.

## Decisões e limitações

- A documentação foi produzida a partir de arquivos efetivamente presentes no projeto.
- Ausência de evidência não é convertida automaticamente em aprovação.
- Credenciais, dados sensíveis e conteúdo do arquivo `.env` não são registrados.
