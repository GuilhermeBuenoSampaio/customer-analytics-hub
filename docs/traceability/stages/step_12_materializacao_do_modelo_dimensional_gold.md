# Etapa 12 — Materialização do modelo dimensional Gold

## Objetivo

Registrar a execução, as evidências e o critério de conclusão da etapa **Materialização do modelo dimensional Gold**.

## Implementação

- Script: `src/gold/transformation/step_12_materializacao_modelo_dimensional_gold.py`
- SHA-256 do script: `09847b6a812d0e863dd991357bda9d3cddcdbe13857335fdaedb2b99b48a2d8c`
- Run ID: `retroactive`
- Registro UTC: `2026-09-20T01:18:12.937157+00:00`
- Status técnico informado: `success`

### Como foi feito

Materializa as 14 tabelas Gold e valida contratos e relacionamentos.

### Por que foi necessário

Disponibilizar estruturas analíticas consistentes e reutilizáveis.

## Evidências

- `data/gold/food_commerce/gold_v3/dim_campanha.parquet` — SHA-256 `41be9d8fec7813b515e4b719231aa50ecbebc38b9a6a2ed661b1d9362f258aa1`
- `data/gold/food_commerce/gold_v3/dim_canal_marketing.parquet` — SHA-256 `2e22b3d70b5fdf5a9ffc1eb9045e027f7e0ad88a76e98eafeed1a3cf4a129511`
- `data/gold/food_commerce/gold_v3/dim_cliente.parquet` — SHA-256 `f1cec5ad96430b2cff331033adfc91b20a97b9a06a5aae7980424866d0da8965`
- `data/gold/food_commerce/gold_v3/dim_data.parquet` — SHA-256 `cff016630495f5ee64a5d396b5c60452b5c91b48970b8825b8c6f6a796ce2696`
- `data/gold/food_commerce/gold_v3/dim_evento_externo.parquet` — SHA-256 `8ce4dc66fe9ee9a07e054425e8bd992260c852c429b31376f72e2b4b19a922b8`
- `data/gold/food_commerce/gold_v3/dim_geografia.parquet` — SHA-256 `851dfe168b311709245832a08595fdd6ab824193604042a6c0ce722f49382158`
- `data/gold/food_commerce/gold_v3/dim_horario.parquet` — SHA-256 `2166429a384a056c56e1d755800c4a695503f0997e09e851e81b1afb685ecebc`
- `data/gold/food_commerce/gold_v3/dim_pagamento.parquet` — SHA-256 `dcff8bb481bb26b16134546ac779542b35b09d0b966a3ddf6ef0686a2dc84111`
- `data/gold/food_commerce/gold_v3/dim_produto.parquet` — SHA-256 `91bfaa0bc233a93dea74ff29ce6bf85a9c042baa08d35521dce3b1624c70933d`
- `data/gold/food_commerce/gold_v3/dim_transportadora.parquet` — SHA-256 `ca9e53cb84794d0b8051e5646dfb068aa00a67f7c3a01296179f20c0d266c344`
- `data/gold/food_commerce/gold_v3/fato_cliente_mes.parquet` — SHA-256 `33baa9fa3ff7bfb2b63feda31c17da96aad444f7641c158c2fa0883e4a01ab4b`
- `data/gold/food_commerce/gold_v3/fato_entrega.parquet` — SHA-256 `5d21a0564d23d7ac3af74741acf0a48a63df9b9252d27260641300f0f9d93bff`
- `data/gold/food_commerce/gold_v3/fato_item_pedido.parquet` — SHA-256 `636cd7c7f5d9ba9adb2578b8c6fa38c8dfe21272ac0d55818161545059bf0b4d`
- `data/gold/food_commerce/gold_v3/fato_pedido.parquet` — SHA-256 `88f7c45e2370c787098d9627104b14c2ec4c34e7ffabec5e8d0093d045046d4f`
- `outputs/manifests/gold_v3/step_12_materializacao_modelo_dimensional_gold.json` — SHA-256 `5da9e46da27f8a7795e6788d5f8c4ed805c54cb5ac0729d66cedc56fb541f40f`
- `outputs/quality/gold_v3/step_12_materializacao_modelo_dimensional_gold.xlsx` — SHA-256 `175a2d9ec71499d69ce0f28ebecbd3f51b2619bf991677eb9da0dc07ae698082`

## Validação e critério de aceite

A etapa somente é considerada concluída quando o script termina com código zero, existe ao menos uma evidência material e este documento é gerado com sucesso.

## Decisões e limitações

- A documentação foi produzida a partir de arquivos efetivamente presentes no projeto.
- Ausência de evidência não é convertida automaticamente em aprovação.
- Credenciais, dados sensíveis e conteúdo do arquivo `.env` não são registrados.
