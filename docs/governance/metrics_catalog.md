# Catálogo canônico de métricas

Este documento é a fonte única das métricas compartilhadas pela EDA geral e pelas análises Comercial, Financeira, Logística e de Marketing no SQL Server e no Power BI.

## Métricas aprovadas

| ID | Métrica | Definição canônica | Fórmula | Fonte Gold | Unidade | Formato | Situação |
|---|---|---|---|---|---|---|---|
| MET-EDA-001 | Clientes analisados | Clientes distintos com pelo menos um pedido no contexto analisado | `COUNT(DISTINCT Cliente_SK)` | `gold.fato_pedido[Cliente_SK]` | Clientes | Inteiro | Aprovada |
| MET-EDA-002 | Pedidos | Quantidade de pedidos, considerando uma linha por pedido | `COUNT(*)` | `gold.fato_pedido` | Pedidos | Inteiro | Aprovada |
| MET-EDA-003 | Itens vendidos | Soma das unidades vendidas, e não contagem das linhas de itens | `SUM(Quantidade)` | `gold.fato_item_pedido[Quantidade]` | Unidades | Inteiro | Aprovada |
| MET-EDA-004 | Receita líquida | Soma do valor líquido dos pedidos | `SUM(Valor_Liquido_Pedido)` | `gold.fato_pedido[Valor_Liquido_Pedido]` | R$ | Duas casas decimais | Aprovada |
| MET-EDA-005 | Ticket médio | Receita líquida dividida pela quantidade de pedidos | `Receita_Liquida / Pedidos` | Medidas derivadas de `gold.fato_pedido` | R$/pedido | Duas casas decimais | Aprovada |
| MET-EDA-006 | Margem bruta | Soma da margem bruta monetária dos pedidos | `SUM(Margem_Bruta_Pedido)` | `gold.fato_pedido[Margem_Bruta_Pedido]` | R$ | Duas casas decimais | Aprovada |
| MET-EDA-007 | Avaliação média | Média das avaliações registradas pelos clientes | `AVG(Avaliacao_Cliente)` | `gold.fato_entrega[Avaliacao_Cliente]` | Pontos | Duas casas decimais | Aprovada |
| MET-EDA-008 | Taxa de atraso | Entregas informadas como atrasadas divididas pelas entregas com informação preenchida | `Entregas_Atrasadas / Entregas_Com_Informacao` | `gold.fato_entrega[Atraso_Entrega_Informado]` | Percentual | Duas casas decimais | Aprovada |

## Resultados de referência

| Métrica | Resultado validado |
|---|---:|
| Clientes analisados | 330 |
| Pedidos | 2.789 |
| Itens vendidos | 13.375 |
| Receita líquida | R$ 289.904,66 |
| Ticket médio | R$ 103,95 |
| Margem bruta | R$ 151.248,65 |
| Avaliação média | 4,27 |
| Taxa de atraso | 9,90% |

## Regras de governança

- As métricas respeitam o contexto de filtro aplicado pelas dimensões do modelo Gold.
- Contagens devem apresentar diferença igual a zero entre SQL e DAX.
- Valores monetários são comparados com duas casas decimais.
- Médias e percentuais são comparados com duas casas decimais.
- Valores nulos não devem compor denominadores quando não representam observações avaliáveis.
- A margem bruta representa valor monetário e não margem percentual ou lucro líquido.
- Alterações de fórmula, fonte, granularidade ou tratamento de nulos exigem nova versão e nova reconciliação.

## Reconciliação

As oito métricas foram reconciliadas entre SQL Server e DAX em 21/09/2026. Todas foram aprovadas, sem diferenças identificadas.

Documentos de referência:

- `docs/governance/metricas_eda_geral.md`;
- `docs/technical/05_eda_geral/reconciliacao_metricas_eda_geral.md`;
- `sql/05_eda_geral/12_reconciliacao_metricas_eda_geral.sql`;
- `docs/images/reconciliacao_metricas_sql_dax.png`.

## Controle de versão

| Versão | Data | Alteração | Status |
|---|---|---|---|
| 1.0 | 21/09/2026 | Registro das oito definições canônicas e da reconciliação SQL Server × DAX | Aprovada |
