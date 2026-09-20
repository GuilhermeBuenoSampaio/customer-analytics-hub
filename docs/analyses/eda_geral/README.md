# EDA Geral — Customer Analytics Hub

## Objetivo

Esta pasta reúne a documentação da Análise Exploratória de Dados geral do Customer Analytics Hub.

A EDA foi realizada sobre o modelo dimensional Gold carregado no SQL Server, com o objetivo de investigar estrutura, qualidade, distribuições, anomalias e relações existentes nos dados.

## Escopo da análise

A EDA contempla:

- volumetria e integridade;
- granularidade das tabelas;
- cobertura das variáveis;
- valores ausentes;
- estatísticas descritivas;
- média, mediana e moda;
- mínimo e máximo;
- quartis e percentis;
- variância e desvio-padrão;
- coeficiente de variação;
- intervalo interquartil;
- possíveis outliers pelo método do IQR;
- distribuições categóricas;
- perfil socioeconômico dos clientes;
- distribuição geográfica;
- comportamento de compra;
- produtos e categorias;
- pedidos, descontos, custos e margens;
- entregas e desempenho logístico;
- relações bivariadas e multivariadas;
- correlações e limitações analíticas.

## Documento principal

- `PERGUNTAS_RESPONDIDAS_EDA_GERAL_v1.0.docx`: relatório técnico com as respostas, tabelas, interpretações e limitações das 60 perguntas da EDA geral.

## Fontes analíticas

A análise utiliza as tabelas dimensionais e fatos do schema `gold` no banco de dados `CustomerAnalyticsHub`.

Principais tabelas:

- `gold.dim_cliente`;
- `gold.dim_produto`;
- `gold.dim_data`;
- `gold.dim_horario`;
- `gold.dim_geografia`;
- `gold.dim_pagamento`;
- `gold.dim_campanha`;
- `gold.dim_canal_marketing`;
- `gold.dim_evento_externo`;
- `gold.dim_transportadora`;
- `gold.fato_item_pedido`;
- `gold.fato_pedido`;
- `gold.fato_entrega`;
- `gold.fato_cliente_mes`.

Também são utilizados objetos auxiliares dos schemas:

- `eda`;
- `quality`;
- `audit`.

## Tecnologias utilizadas

- Python;
- Pandas;
- Azure Data Lake Storage Gen2;
- Parquet;
- SQL Server;
- SQL;
- Git e GitHub;
- Microsoft Word.

## Volumetria principal

| Unidade de análise | Quantidade |
|---|---:|
| Clientes | 330 |
| Produtos | 36 |
| Itens de pedidos | 6.495 |
| Pedidos | 2.789 |
| Entregas | 2.789 |
| Registros cliente-mês | 2.804 |

## Metodologia

A análise foi organizada em quatro blocos:

1. visão geral, integridade e cobertura;
2. análise univariada;
3. análise bivariada;
4. análise multivariada.

As conclusões diferenciam:

- resultado observado;
- indício analítico;
- possível anomalia;
- limitação dos dados;
- hipótese que necessita de análise posterior.

Correlação não foi interpretada como causalidade. Possíveis outliers não foram automaticamente classificados como erros.

## Situação atual

- modelo Gold: concluído;
- carga no SQL Server: concluída;
- reconciliação Parquet × SQL: aprovada;
- pipeline Python: aprovada;
- pipeline SQL: aprovada;
- EDA geral: concluída;
- 60 perguntas: respondidas;
- relatório técnico: publicado;
- dashboard Power BI: próxima etapa.

## Próximos artefatos

- dicionário de métricas;
- matriz de rastreabilidade das perguntas;
- dashboard da EDA geral no Power BI;
- apresentação executiva;
- análises específicas das áreas comercial, financeira, logística e marketing.