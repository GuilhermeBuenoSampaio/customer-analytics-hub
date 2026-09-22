# Reconciliação de Métricas — EDA Geral

## Customer Analytics Hub

| Campo | Valor |
|---|---|
| Processo | Reconciliação SQL Server × DAX |
| Camada de dados | Gold |
| Banco de dados | `CustomerAnalyticsHub` |
| Dashboard | EDA Geral |
| Data da validação | 21/09/2026 |
| Resultado geral | Aprovado |
| Métricas reconciliadas | 8 |
| Métricas aprovadas | 8 |
| Métricas reprovadas | 0 |

---

## 1. Objetivo

Este documento registra a reconciliação das métricas canônicas utilizadas no dashboard da EDA geral do Customer Analytics Hub.

O objetivo foi verificar se os resultados calculados diretamente no SQL Server são equivalentes aos resultados produzidos pelas medidas DAX no Power BI.

A reconciliação reduz o risco de divergências causadas por:

- diferenças de granularidade;
- duplicação de registros;
- relacionamentos ou filtros incorretos;
- fórmulas diferentes entre SQL e DAX;
- tratamentos distintos de valores nulos;
- arredondamentos;
- utilização inadequada das tabelas-fato.

---

## 2. Escopo da reconciliação

Foram reconciliadas as seguintes métricas:

1. Clientes analisados;
2. Pedidos;
3. Itens vendidos;
4. Receita líquida;
5. Ticket médio;
6. Margem bruta;
7. Avaliação média;
8. Taxa de atraso.

As métricas foram calculadas utilizando:

```text
gold.fato_pedido
gold.fato_item_pedido
gold.fato_entrega
gold.dim_data
```

---

## 3. Arquivos relacionados

| Artefato | Caminho |
|---|---|
| Consulta SQL | `sql/05_eda_geral/12_reconciliacao_metricas_eda_geral.sql` |
| Evidência visual | `docs/images/reconciliacao_metricas_sql_dax.png` |
| Dashboard | `power_bi/eda_geral/Customer_Analytics_Hub_EDA_Geral.pbix` |
| Documentação técnica | `docs/technical/05_eda_geral/eda_geral_documentacao_tecnica.md` |

---

## 4. Validação da granularidade

Antes da comparação, foram verificadas as granularidades das principais tabelas-fato.

| Tabela | Linhas | Chaves distintas | Duplicidades | Status |
|---|---:|---:|---:|---|
| `gold.fato_pedido` | 2.789 | 2.789 | 0 | Aprovado |
| `gold.fato_item_pedido` | 6.495 | 6.495 | 0 | Aprovado |
| `gold.fato_entrega` | 2.789 | 2.789 | 0 | Aprovado |

Os resultados demonstram que:

- cada linha da `gold.fato_pedido` representa um pedido;
- cada linha da `gold.fato_item_pedido` representa um item de pedido;
- cada linha da `gold.fato_entrega` representa uma entrega;
- não foram identificadas duplicidades nas chaves avaliadas.

---

## 5. Validação do campo de atraso

O cálculo utilizou o campo:

```text
gold.fato_entrega[Atraso_Entrega_Informado]
```

| Valor | Quantidade |
|---|---:|
| Não | 2.513 |
| Sim | 276 |
| Total | 2.789 |

Não foram identificados valores nulos ou vazios durante a reconciliação.

```text
Taxa de atraso = entregas atrasadas ÷ entregas com informação
Taxa de atraso = 276 ÷ 2.789
Taxa de atraso = 0,098960
Taxa de atraso = 9,90%
```

---

## 6. Critérios de comparação

| Tipo de métrica | Critério de aprovação |
|---|---|
| Contagens | Diferença igual a zero |
| Valores monetários | Diferença igual a R$ 0,00 após formatação |
| Médias | Diferença igual a zero após duas casas decimais |
| Percentuais | Diferença igual a 0,00 ponto percentual |
| Granularidade | Ausência de duplicidades nas chaves avaliadas |

Foram utilizados os valores exatos do SQL Server e do Power BI, sem unidades automáticas de exibição, como `mil`.

---

## 7. Resultado da reconciliação

| Métrica | Resultado SQL | Resultado DAX | Diferença | Status |
|---|---:|---:|---:|---|
| Clientes analisados | 330 | 330 | 0 | Aprovado |
| Pedidos | 2.789 | 2.789 | 0 | Aprovado |
| Itens vendidos | 13.375 | 13.375 | 0 | Aprovado |
| Receita líquida | R$ 289.904,66 | R$ 289.904,66 | R$ 0,00 | Aprovado |
| Ticket médio | R$ 103,95 | R$ 103,95 | R$ 0,00 | Aprovado |
| Margem bruta | R$ 151.248,65 | R$ 151.248,65 | R$ 0,00 | Aprovado |
| Avaliação média | 4,27 | 4,27 | 0,00 | Aprovado |
| Taxa de atraso | 9,90% | 9,90% | 0,00 p.p. | Aprovado |

---

## 8. Definições reconciliadas

### 8.1 Clientes analisados

Quantidade distinta de clientes presentes na tabela de pedidos.

```text
Origem: gold.fato_pedido[Cliente_SK]
Resultado validado: 330 clientes
```

### 8.2 Pedidos

Quantidade de registros da tabela de pedidos, considerando uma linha por pedido.

```text
Origem: gold.fato_pedido
Resultado validado: 2.789 pedidos
```

### 8.3 Itens vendidos

Soma das unidades vendidas, e não contagem das linhas da tabela de itens.

```text
Origem: gold.fato_item_pedido[Quantidade]
Resultado validado: 13.375 unidades
```

### 8.4 Receita líquida

Soma do valor líquido dos pedidos.

```text
Origem: gold.fato_pedido[Valor_Liquido_Pedido]
Resultado validado: R$ 289.904,66
```

### 8.5 Ticket médio

Receita líquida dividida pela quantidade de pedidos.

```text
Ticket médio = R$ 289.904,66 ÷ 2.789
Ticket médio = R$ 103,95
```

### 8.6 Margem bruta

Soma da margem bruta monetária dos pedidos.

```text
Origem: gold.fato_pedido[Margem_Bruta_Pedido]
Resultado validado: R$ 151.248,65
```

A métrica representa valor monetário de margem, e não margem percentual.

### 8.7 Avaliação média

Média das avaliações registradas pelos clientes.

```text
Origem: gold.fato_entrega[Avaliacao_Cliente]
Resultado validado: 4,27
```

### 8.8 Taxa de atraso

Proporção de entregas classificadas como atrasadas entre as entregas com informação preenchida.

```text
Origem: gold.fato_entrega[Atraso_Entrega_Informado]
Resultado validado: 9,90%
```

---

## 9. Validação temporal

A consulta SQL também calculou as oito métricas por mês utilizando:

```text
gold.dim_data[Ano_Mes]
```

Os resultados foram produzidos para os 12 meses de 2025. A dimensão calendário preserva a mesma lógica temporal aplicada no Power BI pela segmentação de período.

A consulta mensal permite verificar:

- evolução do número de clientes;
- volume de pedidos;
- quantidade de itens vendidos;
- receita líquida;
- ticket médio;
- margem bruta;
- avaliação média;
- taxa de atraso.

---

## 10. Conclusão

A reconciliação foi aprovada para as oito métricas da EDA geral.

Os resultados do SQL Server e do Power BI apresentaram equivalência integral dentro dos critérios definidos. Não foram identificadas diferenças relacionadas a contagens, valores monetários, médias, percentuais, granularidade, duplicidades ou tratamento do campo de atraso.

As métricas reconciliadas passam a ser consideradas definições canônicas do Customer Analytics Hub e poderão ser reutilizadas nas análises:

1. Comercial;
2. Financeira;
3. Logística;
4. Marketing.

As análises específicas poderão aplicar filtros e dimensões diferentes, mas não deverão alterar arbitrariamente as definições aprovadas.

Qualquer modificação futura deverá ser versionada, documentada e submetida a uma nova reconciliação.

---

## 11. Status final

```text
RECONCILIAÇÃO SQL SERVER × DAX: APROVADA
MÉTRICAS AVALIADAS: 8
MÉTRICAS APROVADAS: 8
MÉTRICAS REPROVADAS: 0
DIFERENÇAS IDENTIFICADAS: 0
```
