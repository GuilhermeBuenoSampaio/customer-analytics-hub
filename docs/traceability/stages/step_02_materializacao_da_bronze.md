# Etapa 02 — Materialização da Bronze

## Objetivo

Registrar a execução, as evidências e o critério de conclusão da etapa **Materialização da Bronze**.

## Implementação

- Script: `src/ingestion/step_02_materializacao_bronze.py`
- SHA-256 do script: `6d83bf8582d33b57dcb752626def4cdd7d7254e9ae190b4570feaee2583bc54b`
- Run ID: `retroativo_inicial_001`
- Registro UTC: `2026-09-20T15:45:20.500782+00:00`
- Status técnico informado: `success`

### Como foi feito

Extrai a aba canônica e grava a Bronze em Parquet com manifesto.

### Por que foi necessário

Preservar uma representação bruta, reproduzível e rastreável da entrada.

## Evidências

- `data/bronze/food_commerce/bronze_transactions_v3.parquet` — SHA-256 `f3c358311134f20b3928e9ff63a4ee922cb7f8dde0d37e732cbf8c90f33a7e9b`
- `outputs/manifests/bronze_v3/step_02_materializacao_bronze.json` — SHA-256 `dfb40985c5fe848e0f831366dfb9f9c5c278f71c9e5637a48c0611d6082320de`

## Validação e critério de aceite

A etapa somente é considerada concluída quando o script termina com código zero, existe ao menos uma evidência material e este documento é gerado com sucesso.

## Decisões e limitações

- A documentação foi produzida a partir de arquivos efetivamente presentes no projeto.
- Ausência de evidência não é convertida automaticamente em aprovação.
- Credenciais, dados sensíveis e conteúdo do arquivo `.env` não são registrados.
