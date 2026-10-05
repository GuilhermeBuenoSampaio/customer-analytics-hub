# Catálogo de Métricas — Análise Comercial

## Customer Analytics Hub

| Campo | Informação |
|---|---|
| Módulo | Análise Comercial |
| Banco de dados | `CustomerAnalyticsHub` |
| Camada analítica | Gold |
| Período inicial | Janeiro a dezembro de 2025 |
| Versão | 1.0 |
| Data de definição | 05/10/2026 |
| Status | Em desenvolvimento |

---

## 1. Objetivo

Este documento define as métricas que serão utilizadas para responder às perguntas AC01–AC06 da Análise Comercial.

O catálogo tem como objetivos:

- preservar as oito definições canônicas aprovadas na EDA Geral;
- impedir cálculos diferentes para um mesmo conceito;
- documentar fórmula, fonte, granularidade e tratamento de nulos;
- orientar as implementações em SQL Server, Python, DAX e Power BI;
- estabelecer critérios de reconciliação;
- separar métricas já aprovadas de métricas ainda em desenvolvimento.

---

## 2. Classificação dos status

| Status | Significado |
|---|---|
| Aprovada | Definição e resultado reconciliados entre as ferramentas |
| Definida | Regra de negócio documentada, mas cálculo ainda não reconciliado |
| Em validação | Implementação executada e aguardando conferência final |
| Reprovada | Resultado divergente ou regra inadequada |

Uma métrica nova somente passará para **Aprovada** depois da reconciliação entre SQL Server, Python e DAX, quando aplicável.

---

## 3. Métricas canônicas herdadas da EDA Geral

| ID | Métrica | Definição resumida | Fonte principal | Resultado geral | Status |
|---|---|---|---|---:|---|
| MET-EDA-001 | Clientes analisados | Clientes distintos com pelo menos um pedido | `gold.fato_pedido` | 330 | Aprovada |
| MET-EDA-002 | Pedidos | Quantidade de pedidos, uma linha por pedido | `gold.fato_pedido` | 2.789 | Aprovada |
| MET-EDA-003 | Itens vendidos | Soma das unidades vendidas | `gold.fato_item_pedido` | 13.375 | Aprovada |
| MET-EDA-004 | Receita líquida | Soma do valor líquido dos pedidos | `gold.fato_pedido` | R$ 289.904,66 | Aprovada |
| MET-EDA-005 | Ticket médio | Receita líquida dividida pelos pedidos | `gold.fato_pedido` | R$ 103,95 | Aprovada |
| MET-EDA-006 | Margem bruta | Soma da margem bruta monetária | `gold.fato_pedido` | R$ 151.248,65 | Aprovada |
| MET-EDA-007 | Avaliação média | Média das avaliações preenchidas | `gold.fato_entrega` | 4,27 | Aprovada |
| MET-EDA-008 | Taxa de atraso | Entregas atrasadas divididas pelas entregas informadas | `gold.fato_entrega` | 9,90% | Aprovada |

Essas métricas não deverão ter fórmula, fonte ou granularidade alteradas sem nova versão e nova reconciliação.

---

## 4. Métricas comerciais de desempenho

| ID | Métrica | Definição | Fórmula conceitual | Fonte | Status |
|---|---|---|---|---|---|
| MET-COM-001 | Receita bruta | Valor total dos pedidos antes dos descontos | `SUM(Valor_Bruto_Pedido)` | `gold.fato_pedido` | Definida |
| MET-COM-002 | Desconto concedido | Valor monetário total dos descontos | `SUM(Valor_Desconto_Pedido)` | `gold.fato_pedido` | Definida |
| MET-COM-003 | Desconto percentual ponderado | Desconto total dividido pela receita bruta | `Desconto_Concedido / Receita_Bruta` | `gold.fato_pedido` | Definida |
| MET-COM-004 | Custo total | Soma dos custos dos pedidos | `SUM(Custo_Total_Pedido)` | `gold.fato_pedido` | Definida |
| MET-COM-005 | Margem percentual | Margem bruta dividida pela receita líquida | `Margem_Bruta / Receita_Liquida` | `gold.fato_pedido` | Definida |
| MET-COM-006 | Itens médios por pedido | Quantidade de itens dividida pelos pedidos | `Itens_Vendidos / Pedidos` | `gold.fato_pedido` | Definida |
| MET-COM-007 | Produtos distintos por pedido | Média da quantidade de produtos distintos de cada pedido | `AVG(Quantidade_Produtos_Distintos)` | `gold.fato_pedido` | Definida |
| MET-COM-008 | Frequência média de compra | Pedidos divididos pelos clientes compradores | `Pedidos / Clientes_Analisados` | `gold.fato_pedido` | Definida |
| MET-COM-009 | Receita média por cliente | Receita líquida dividida pelos clientes compradores | `Receita_Liquida / Clientes_Analisados` | `gold.fato_pedido` | Definida |
| MET-COM-010 | Margem média por cliente | Margem bruta dividida pelos clientes compradores | `Margem_Bruta / Clientes_Analisados` | `gold.fato_pedido` | Definida |

### Regras

- A margem percentual utilizará receita líquida como denominador.
- Divisões deverão retornar nulo quando o denominador for zero.
- Receita bruta, desconto, custo e margem serão apresentados em reais com duas casas decimais.
- A soma das quantidades, e não a contagem de linhas, representa itens vendidos.

---

## 5. Métricas de clientes e recorrência

| ID | Métrica | Definição | Regra conceitual | Fonte | Status |
|---|---|---|---|---|---|
| MET-COM-011 | Novos clientes | Clientes cuja primeira compra ocorreu no período analisado | `MIN(Data_Compra)` por cliente dentro da história disponível | `gold.fato_pedido` + `gold.dim_data` | Definida |
| MET-COM-012 | Clientes recorrentes | Clientes com compra anterior ao período ou mais de um pedido acumulado | Existência de compra anterior ou frequência acumulada maior que 1 | `gold.fato_pedido` / `gold.fato_cliente_mes` | Definida |
| MET-COM-013 | Taxa de recompra | Clientes com pelo menos uma recompra divididos pelos clientes compradores | `Clientes_Com_Recompra / Clientes_Analisados` | `gold.fato_pedido` | Definida |
| MET-COM-014 | Recência | Dias entre a última compra do cliente e a data de corte | `Data_Corte - MAX(Data_Compra)` | `gold.fato_cliente_mes` | Definida |
| MET-COM-015 | Intervalo médio entre compras | Média de dias entre compras consecutivas do cliente | Média das diferenças entre datas consecutivas | `gold.fato_cliente_mes` ou base derivada | Definida |
| MET-COM-016 | Retenção por coorte | Clientes da coorte que voltaram a comprar em período posterior | `Clientes_Retidos / Clientes_Iniciais_Coorte` | Base derivada de `gold.fato_pedido` | Definida |
| MET-COM-017 | Taxa de inatividade | Clientes acima do limite de recência definido | `Clientes_Inativos / Clientes_Elegiveis` | `gold.fato_cliente_mes` | Definida |

### Regras

- A primeira compra deve ser calculada usando todo o histórico disponível, não apenas o mês filtrado.
- A data de corte deverá ser explícita e igual entre SQL, Python e DAX.
- O limite de inatividade será definido após analisar a distribuição dos intervalos entre compras.
- Retenção deverá ser apresentada por coorte e tempo decorrido, evitando somar percentuais de períodos diferentes.

---

## 6. Métricas de campanhas e incentivos

| ID | Métrica | Definição | Fórmula conceitual | Fonte | Status |
|---|---|---|---|---|---|
| MET-COM-018 | Pedidos com campanha | Pedidos identificados com campanha válida | `COUNT` onde `Pedido_Com_Campanha = 1` | `gold.fato_pedido` | Definida |
| MET-COM-019 | Participação de pedidos com campanha | Proporção dos pedidos vinculados a campanhas | `Pedidos_Com_Campanha / Pedidos` | `gold.fato_pedido` | Definida |
| MET-COM-020 | Receita com campanha | Receita líquida dos pedidos com campanha | `SUM(Valor_Liquido_Pedido)` com campanha | `gold.fato_pedido` | Definida |
| MET-COM-021 | Margem com campanha | Margem bruta dos pedidos com campanha | `SUM(Margem_Bruta_Pedido)` com campanha | `gold.fato_pedido` | Definida |
| MET-COM-022 | Pedidos com frete grátis | Pedidos cuja entrega possui frete grátis | `COUNT` onde `Frete_Gratis = 1` | `gold.fato_entrega` | Definida |
| MET-COM-023 | Participação de frete grátis | Proporção dos pedidos com frete grátis | `Pedidos_Com_Frete_Gratis / Pedidos_Com_Entrega` | `gold.fato_entrega` | Definida |
| MET-COM-024 | Ticket por condição comercial | Ticket médio por combinação de campanha, desconto e frete grátis | `Receita_Liquida_Grupo / Pedidos_Grupo` | `gold.fato_pedido` + `gold.fato_entrega` | Definida |
| MET-COM-025 | Margem percentual por condição | Margem percentual por combinação de incentivos | `Margem_Bruta_Grupo / Receita_Liquida_Grupo` | `gold.fato_pedido` + `gold.fato_entrega` | Definida |
| MET-COM-026 | Recompra após incentivo | Clientes que voltaram a comprar após pedido incentivado | `Clientes_Que_Recompraram / Clientes_Expostos` | Base derivada de pedidos | Definida |

### Regras

- Comparações deverão usar grupos equivalentes sempre que possível.
- Campanha, desconto e frete grátis serão avaliados isoladamente e em combinação.
- Resultados observacionais serão descritos como associação, não como efeito causal.
- A análise de frete grátis não será tratada como retorno integral enquanto o custo subsidiado não estiver completamente identificado.
- Médias de grupos deverão ser acompanhadas por tamanho da amostra, dispersão e tamanho de efeito.

---

## 7. Métricas de concentração e Pareto

| ID | Métrica | Definição | Regra conceitual | Status |
|---|---|---|---|---|
| MET-COM-027 | Participação acumulada na receita | Percentual acumulado da receita após ordenar entidades da maior para a menor | `Receita_Acumulada / Receita_Total` | Definida |
| MET-COM-028 | Participação acumulada na margem | Percentual acumulado da margem após ordenar entidades da maior para a menor | `Margem_Acumulada / Margem_Total` | Definida |
| MET-COM-029 | Quantidade no grupo Pareto | Número de entidades necessárias para atingir 80% do indicador | Primeira posição cuja participação acumulada seja maior ou igual a 80% | Definida |
| MET-COM-030 | Classificação ABC | Classificação por participação acumulada | A: até 80%; B: acima de 80% até 95%; C: acima de 95% | Definida |
| MET-COM-031 | Índice de concentração do maior grupo | Participação dos principais clientes, produtos ou categorias | Receita ou margem do grupo dividida pelo total | Definida |

### Regras

- O Pareto será calculado separadamente para clientes, produtos, categorias, campanhas e canais.
- Receita e margem terão classificações independentes.
- A entidade que ultrapassar o limite será incluída na faixa que completa o percentual acumulado.
- A regra 80/15/5 é critério de classificação, não resultado garantido dos dados.

---

## 8. Métricas de segmentação de clientes

| ID | Variável | Definição | Uso previsto | Status |
|---|---|---|---|---|
| VAR-COM-001 | Recência em dias | Dias desde a última compra até a data de corte | RFM e clustering | Definida |
| VAR-COM-002 | Frequência | Quantidade de pedidos do cliente | RFM e clustering | Definida |
| VAR-COM-003 | Valor monetário | Receita líquida acumulada do cliente | RFM e clustering | Definida |
| VAR-COM-004 | Margem acumulada | Margem bruta total gerada pelo cliente | Clustering e priorização | Definida |
| VAR-COM-005 | Ticket médio do cliente | Receita líquida dividida pelos pedidos do cliente | Clustering | Definida |
| VAR-COM-006 | Itens médios | Itens comprados divididos pelos pedidos do cliente | Clustering | Definida |
| VAR-COM-007 | Diversidade de produtos | Quantidade distinta de produtos comprados | Clustering | Definida |
| VAR-COM-008 | Diversidade de categorias | Quantidade distinta de categorias compradas | Clustering | Definida |
| VAR-COM-009 | Dependência de campanha | Proporção dos pedidos do cliente com campanha | Clustering e interpretação | Definida |
| VAR-COM-010 | Dependência de desconto | Desconto total dividido pela receita bruta do cliente | Clustering e interpretação | Definida |
| VAR-COM-011 | Dependência de frete grátis | Proporção dos pedidos do cliente com frete grátis | Clustering e interpretação | Definida |

As variáveis serão avaliadas quanto a assimetria, escala, valores extremos, redundância e correlação antes da modelagem. Transformações como `log1p` e padronização por Z-Score serão documentadas quando aplicadas.

---

## 9. Granularidades e regras de junção

| Objeto | Granularidade | Chave principal de análise |
|---|---|---|
| `gold.fato_pedido` | Uma linha por pedido | `Pedido_ID` |
| `gold.fato_item_pedido` | Uma linha por item de pedido | `Item_Pedido_SK` |
| `gold.fato_entrega` | Uma linha por entrega/pedido | `Pedido_ID` |
| `gold.fato_cliente_mes` | Uma linha por cliente e mês | `Cliente_SK` + `Data_Corte_SK` |

Regras obrigatórias:

- métricas de pedido serão calculadas antes de qualquer expansão para o nível de item;
- pedidos não poderão ser multiplicados por junções com itens;
- a junção entre pedido e entrega deverá permanecer um para um;
- totais derivados de itens deverão ser reconciliados com os totais correspondentes de pedidos;
- chaves substitutas serão utilizadas para relacionar dimensões e fatos;
- o contexto temporal será controlado por `gold.dim_data`.

---

## 10. Tratamento de nulos e denominadores

- Valores monetários nulos não serão convertidos automaticamente em zero sem confirmação da regra de negócio.
- Avaliações nulas não participarão da avaliação média.
- Entregas sem informação de atraso não participarão do denominador da taxa de atraso.
- Divisões por zero retornarão nulo.
- Clientes sem histórico suficiente para intervalo entre compras permanecerão sem valor nessa métrica.
- Métricas de recompra deverão considerar apenas clientes com janela temporal suficiente para observação.

---

## 11. Critérios de reconciliação

| Tipo | Critério de aprovação |
|---|---|
| Contagem | Diferença igual a zero |
| Soma de unidades | Diferença igual a zero |
| Valor monetário | Diferença igual a R$ 0,00 após duas casas decimais |
| Média ou razão | Diferença igual a zero após a precisão definida |
| Percentual | Diferença igual a 0,00 ponto percentual |
| Segmentação | Mesma população, variáveis, data de corte e transformação |
| Pareto/ABC | Mesma ordenação, regra de acumulado e limites de classe |

Toda reconciliação deverá registrar:

- período e filtros;
- quantidade de registros de entrada;
- resultado SQL;
- resultado Python;
- resultado DAX, quando aplicável;
- diferença encontrada;
- status;
- evidência da execução.

---

## 12. Relação com as perguntas de negócio

| Eixo | Principais métricas |
|---|---|
| AC01 — Origem do crescimento | Clientes, pedidos, itens, receita, ticket, frequência, novos e recorrentes |
| AC02 — Sustentabilidade econômica | Receita bruta e líquida, custo, margem bruta e margem percentual |
| AC03 — Incentivos comerciais | Desconto, campanha, frete grátis, ticket, margem e recompra por condição |
| AC04 — Concentração comercial | Participação acumulada, Pareto, ABC e índices de concentração |
| AC05 — Estrutura de clientes | RFM, margem, ticket, diversidade e dependência de incentivos |
| AC06 — Oportunidades comerciais | Retenção, inatividade, cesta, potencial de recompra e priorização |

---

## 13. Limitações

- Margem bruta não representa lucro líquido.
- Os dados observacionais não sustentam causalidade definitiva.
- O retorno integral do frete grátis depende da identificação completa do custo subsidiado.
- A data de corte influencia recência, inatividade e retenção.
- Segmentos estatísticos somente terão validade após avaliação de estabilidade e utilidade comercial.
- Métricas preditivas dependerão de volume, horizonte temporal e capacidade de validação fora da amostra.

---

## 14. Controle de alterações

| Versão | Data | Alteração | Status |
|---|---|---|---|
| 1.0 | 05/10/2026 | Definição inicial das métricas e variáveis comerciais | Em desenvolvimento |

---

## 15. Próxima atividade

Mapear as colunas Gold utilizadas pelas métricas comerciais e criar a primeira consulta de diagnóstico em:

```text
sql/04_business/commercial/01_diagnostico_base_comercial.sql
```

Essa consulta deverá validar a granularidade, a cobertura das chaves, os totais canônicos e a disponibilidade das variáveis necessárias antes das análises aprofundadas.
