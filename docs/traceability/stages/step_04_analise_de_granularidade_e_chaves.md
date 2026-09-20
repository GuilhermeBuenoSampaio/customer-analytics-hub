# Etapa 04 — Análise de granularidade e chaves

## Objetivo

Registrar a execução, as evidências e o critério de conclusão da etapa **Análise de granularidade e chaves**.

## Implementação

- Script: `src/bronze/profiling/step_04_analise_granularidade_chaves.py`
- SHA-256 do script: `65ef1fea0b1a0e0947c1b48c1fb142111ea3eb0d95826fd3b96d774ac563b02e`
- Run ID: `retroativo_inicial_001`
- Registro UTC: `2026-09-20T15:45:20.623368+00:00`
- Status técnico informado: `success`

### Como foi feito

Investiga granularidade, chaves candidatas, duplicidades e relações pedido-item.

### Por que foi necessário

Evitar contagens duplicadas e definir corretamente fatos e dimensões.

## Evidências

- `outputs/profiling/bronze_v3/step_04_analise_granularidade_chaves.xlsx` — SHA-256 `fc60366f464211e83a131bc594225502cc35cd14bfa560f5a36634bd4cb09ccd`

## Validação e critério de aceite

A etapa somente é considerada concluída quando o script termina com código zero, existe ao menos uma evidência material e este documento é gerado com sucesso.

## Decisões e limitações

- A documentação foi produzida a partir de arquivos efetivamente presentes no projeto.
- Ausência de evidência não é convertida automaticamente em aprovação.
- Credenciais, dados sensíveis e conteúdo do arquivo `.env` não são registrados.
