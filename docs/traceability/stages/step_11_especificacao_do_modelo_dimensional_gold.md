# Etapa 11 — Especificação do modelo dimensional Gold

## Objetivo

Registrar a execução, as evidências e o critério de conclusão da etapa **Especificação do modelo dimensional Gold**.

## Implementação

- Script: `src/gold/modeling/step_11_especificacao_modelo_dimensional.py`
- SHA-256 do script: `a2eeb4d222e5fbb5e724c6634feb8ea07482b716c34777e474975bce18a41f28`
- Run ID: `retroativo_inicial_001`
- Registro UTC: `2026-09-20T15:45:21.052496+00:00`
- Status técnico informado: `success`

### Como foi feito

Especifica 10 dimensões, 4 fatos, chaves, tipos e granularidades.

### Por que foi necessário

Criar uma camada semântica única para todas as áreas do negócio.

## Evidências

- `outputs/manifests/gold_v3/step_11_especificacao_modelo_dimensional.json` — SHA-256 `bdefcec9b6b85c8ae5fa1eecf57f00cbcef24d08a155906f9a4d52011d787adb`
- `outputs/modeling/gold_v3/step_11_especificacao_modelo_dimensional.xlsx` — SHA-256 `e6c44807594d3d7e28d4e95445f594e8335bda511a279b12821779d264ef6a55`

## Validação e critério de aceite

A etapa somente é considerada concluída quando o script termina com código zero, existe ao menos uma evidência material e este documento é gerado com sucesso.

## Decisões e limitações

- A documentação foi produzida a partir de arquivos efetivamente presentes no projeto.
- Ausência de evidência não é convertida automaticamente em aprovação.
- Credenciais, dados sensíveis e conteúdo do arquivo `.env` não são registrados.
