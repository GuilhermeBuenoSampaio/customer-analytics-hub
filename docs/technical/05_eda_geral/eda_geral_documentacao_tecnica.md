# Documentação Técnica — EDA Geral

## Customer Analytics Hub

| Campo                  | Valor                                                        |
| ---------------------- | ------------------------------------------------------------ |
| Documento              | Documentação técnica da EDA geral                            |
| Projeto                | Customer Analytics Hub                                       |
| Camada analítica       | Gold                                                         |
| Ferramentas principais | Python, SQL Server, Power Query, Power BI e DAX              |
| Estado                 | Em desenvolvimento                                           |
| Versão inicial         | 1.0                                                          |
| Escopo                 | Visão geral dos principais indicadores e sua evolução mensal |

---

## 1. Finalidade do documento

Este documento registra a construção técnica da EDA geral do projeto Customer Analytics Hub.

O objetivo é garantir rastreabilidade sobre:

* origem dos dados;
* arquitetura utilizada;
* preparação e transformação dos dados;
* modelagem dimensional;
* carregamento no SQL Server;
* importação no Power BI;
* relacionamentos do modelo semântico;
* medidas DAX;
* critérios de visualização;
* validações realizadas;
* limitações conhecidas;
* decisões técnicas;
* próximos passos.

A documentação permite que a solução seja compreendida, revisada e reproduzida sem depender exclusivamente do conhecimento de quem a desenvolveu.

---

## 2. Objetivo da EDA geral

A EDA geral foi construída para fornecer uma visão consolidada do desempenho do negócio antes do desenvolvimento das análises específicas dos domínios comercial, financeiro, logístico e de marketing.

O dashboard responde inicialmente às seguintes perguntas:

1. Quantos clientes foram analisados?
2. Quantos pedidos foram registrados?
3. Quantos itens foram vendidos?
4. Qual foi a receita líquida?
5. Qual foi a margem bruta?
6. Qual foi o ticket médio?
7. Qual foi a taxa de atraso?
8. Qual foi a avaliação média dos clientes?
9. Como esses indicadores evoluíram ao longo dos meses?
10. Como os resultados se comportam quando um período específico é selecionado?

A EDA geral não substitui as análises aprofundadas por área. Sua função é estabelecer uma visão panorâmica, validar a estrutura analítica e criar uma base comum para as etapas seguintes.

---

## 3. Escopo analítico

A EDA geral utiliza dados relacionados a:

* clientes;
* pedidos;
* itens dos pedidos;
* valores financeiros;
* custos;
* margens;
* entregas;
* avaliações;
* campanhas;
* canais de marketing;
* produtos;
* pagamentos;
* datas;
* horários;
* geografia;
* eventos externos;
* transportadoras.

Os indicadores são apresentados de forma consolidada e por mês.

O recorte temporal é controlado por uma segmentação de dados baseada na dimensão calendário.

---

## 4. Fonte dos dados

A fonte principal do pipeline é a aba:

```text
25_bronze_transactions_sujo
```

Ela pertence ao arquivo:

```text
FOOD_COMMERCE_DIGITAL_TWIN_v3_DADOS_SUJOS_INTENCIONAIS.xlsx
```

O arquivo de origem contém dados intencionalmente sujos e estruturas analíticas previamente calculadas.

Para preservar a independência metodológica do projeto, somente os dados-base foram utilizados como entrada do pipeline. Dimensões, fatos, métricas e indicadores foram reconstruídos durante o desenvolvimento.

As estruturas analíticas prontas existentes no arquivo original não foram adotadas como fonte oficial das análises.

---

## 5. Arquitetura da solução

A solução utiliza uma arquitetura analítica em camadas.

### 5.1 Landing

Responsável pelo recebimento e pela preservação do arquivo original.

Principais características:

* preservação imutável;
* registro da origem;
* geração de hash;
* manifesto de ingestão;
* ausência de transformações de negócio.

### 5.2 Bronze

Responsável por preservar os dados ingeridos em seu estado bruto.

Nessa camada são executadas principalmente verificações técnicas:

* estrutura do arquivo;
* quantidade de linhas e colunas;
* nomes das colunas;
* tipos inferidos;
* nulidade;
* duplicidades;
* cardinalidade;
* domínios observados;
* granularidade aparente;
* chaves candidatas;
* coerência entre campos.

### 5.3 Silver

Responsável pela padronização e validação dos dados.

Entre os tratamentos realizados estão:

* correção de tipos;
* normalização de nomes;
* tratamento de valores inconsistentes;
* padronização de categorias;
* validação de regras de negócio;
* controle de duplicidades;
* separação de entidades;
* validação de integridade;
* materialização em Parquet;
* geração de evidências de qualidade.

### 5.4 Gold

Responsável por disponibilizar estruturas orientadas ao consumo analítico.

A camada Gold contém:

* dimensões;
* tabelas-fato;
* chaves substitutas;
* métricas compartilhadas;
* estruturas carregadas no SQL Server;
* dados preparados para consumo no Power BI.

### 5.5 Fluxo da informação

```text
Arquivo XLSX
    ↓
Landing
    ↓
Bronze
    ↓
Silver
    ↓
Gold em Parquet
    ↓
SQL Server
    ↓
Power Query
    ↓
Modelo semântico do Power BI
    ↓
Medidas DAX
    ↓
Dashboard da EDA geral
```

---

## 6. Tecnologias utilizadas

| Tecnologia                   | Utilização                                         |
| ---------------------------- | -------------------------------------------------- |
| Python                       | Orquestração, profiling, transformação e validação |
| Pandas                       | Manipulação tabular dos dados                      |
| NumPy                        | Operações numéricas auxiliares                     |
| PyArrow                      | Leitura e gravação em Parquet                      |
| Azure Data Lake Storage Gen2 | Armazenamento em camadas                           |
| SQL Server                   | Persistência e consulta da camada Gold             |
| T-SQL                        | Validação, auditoria e consultas analíticas        |
| Power Query                  | Importação e preparação final para o Power BI      |
| Power BI                     | Modelagem semântica e visualização                 |
| DAX                          | Criação das medidas analíticas                     |
| Git                          | Controle de versão local                           |
| GitHub                       | Versionamento e apresentação do projeto            |

---

## 7. Processamento e validação anteriores ao Power BI

Antes da criação do dashboard, o pipeline executou verificações sobre:

* tipos de dados;
* nulidade;
* cardinalidade;
* granularidade;
* domínios categóricos;
* regras numéricas;
* regras temporais;
* coerência entre colunas;
* integridade referencial;
* reconciliação entre camadas;
* reconciliação entre arquivos Parquet e SQL Server.

A camada Gold foi carregada no banco:

```text
CustomerAnalyticsHub
```

A carga foi acompanhada por estruturas de auditoria e qualidade, incluindo:

```text
audit.execucao_carga_gold
quality.reconciliacao_carga_gold
```

A reconciliação entre os arquivos Gold e as tabelas carregadas no SQL Server foi aprovada antes do consumo no Power BI.

---

## 8. Modelo dimensional Gold

O modelo dimensional contém 10 dimensões e 4 tabelas-fato.

### 8.1 Dimensões

| Tabela                     | Finalidade                                           |
| -------------------------- | ---------------------------------------------------- |
| `gold.dim_campanha`        | Contexto das campanhas associadas aos eventos        |
| `gold.dim_canal_marketing` | Identificação dos canais de aquisição ou comunicação |
| `gold.dim_cliente`         | Atributos cadastrais e comportamentais dos clientes  |
| `gold.dim_data`            | Calendário analítico e atributos temporais           |
| `gold.dim_evento_externo`  | Eventos externos relacionados ao período             |
| `gold.dim_geografia`       | Informações geográficas                              |
| `gold.dim_horario`         | Horários e faixas horárias                           |
| `gold.dim_pagamento`       | Formas e características de pagamento                |
| `gold.dim_produto`         | Informações dos produtos                             |
| `gold.dim_transportadora`  | Informações das transportadoras                      |

### 8.2 Tabelas-fato

| Tabela                  | Granularidade analítica                       |
| ----------------------- | --------------------------------------------- |
| `gold.fato_pedido`      | Uma linha por pedido                          |
| `gold.fato_item_pedido` | Uma linha por item do pedido                  |
| `gold.fato_entrega`     | Uma linha por evento de entrega               |
| `gold.fato_cliente_mes` | Uma linha por cliente e período de referência |

As tabelas-fato registram eventos mensuráveis. As dimensões fornecem o contexto utilizado para filtrar, agrupar e interpretar esses eventos.

---

## 9. Relacionamentos no Power BI

O modelo do Power BI foi estruturado seguindo o conceito de esquema estrela.

As principais características são:

* relacionamentos entre dimensões e fatos;
* cardinalidade de um para muitos;
* lado `1` localizado nas dimensões;
* lado `*` localizado nas tabelas-fato;
* direção de filtro predominantemente única;
* filtro propagado das dimensões para os fatos;
* relacionamentos ativos;
* ausência de relacionamentos diretos entre tabelas-fato.

Essa configuração reduz ambiguidades e evita a propagação indevida de filtros.

### 9.1 Exemplos de relacionamentos

| Tabela-fato             | Chave                | Dimensão                   | Chave                |
| ----------------------- | -------------------- | -------------------------- | -------------------- |
| `gold.fato_pedido`      | `Cliente_SK`         | `gold.dim_cliente`         | `Cliente_SK`         |
| `gold.fato_pedido`      | `Data_SK`            | `gold.dim_data`            | `Data_SK`            |
| `gold.fato_pedido`      | `Horario_SK`         | `gold.dim_horario`         | `Horario_SK`         |
| `gold.fato_pedido`      | `Pagamento_SK`       | `gold.dim_pagamento`       | `Pagamento_SK`       |
| `gold.fato_pedido`      | `Campanha_SK`        | `gold.dim_campanha`        | `Campanha_SK`        |
| `gold.fato_pedido`      | `Canal_Marketing_SK` | `gold.dim_canal_marketing` | `Canal_Marketing_SK` |
| `gold.fato_pedido`      | `Evento_Externo_SK`  | `gold.dim_evento_externo`  | `Evento_Externo_SK`  |
| `gold.fato_pedido`      | `Geografia_SK`       | `gold.dim_geografia`       | `Geografia_SK`       |
| `gold.fato_item_pedido` | `Produto_SK`         | `gold.dim_produto`         | `Produto_SK`         |
| `gold.fato_entrega`     | `Transportadora_SK`  | `gold.dim_transportadora`  | `Transportadora_SK`  |

As demais relações seguem o mesmo princípio dimensional.

---

## 10. Preparação dos dados no Power Query

As tabelas Gold foram importadas do SQL Server para o Power BI.

O Power Query foi utilizado como camada de preparação final, sem substituir as regras estruturais já aplicadas no pipeline Python e no SQL Server.

As principais ações realizadas incluíram:

* conexão com o banco de dados;
* navegação até as tabelas do esquema Gold;
* remoção de colunas não necessárias ao relatório;
* ajuste de tipos de dados;
* substituição de valores quando necessário;
* validação de colunas booleanas;
* identificação e correção de erros de conversão;
* preparação das tabelas para o modelo semântico.

### 10.1 Correção do campo `Cupom_Status`

Durante a preparação, foi identificado um erro de conversão no campo:

```text
Cupom_Status
```

O erro ocorreu porque valores textuais, como `False`, estavam sendo convertidos diretamente para o tipo lógico.

O tratamento foi corrigido antes da aplicação do tipo de dados definitivo.

Depois do ajuste:

* a coluna deixou de apresentar erros;
* os registros passaram a ser interpretados corretamente;
* a consulta foi carregada no modelo.

### 10.2 Validação das consultas

Ao final das transformações:

* não permaneceram erros nas consultas carregadas;
* as tabelas apresentaram tipos compatíveis;
* a atualização do modelo foi concluída;
* os indicadores puderam ser calculados por DAX.

---

## 11. Tabela de medidas

Foi criada uma tabela dedicada chamada:

```text
00_Medidas
```

Sua finalidade é centralizar as medidas DAX do modelo.

A tabela é desconectada das demais tabelas e não participa dos relacionamentos.

Foi criada inicialmente com uma coluna auxiliar, utilizada apenas para permitir a existência da tabela. Essa coluna foi posteriormente ocultada.

A centralização das medidas facilita:

* organização;
* manutenção;
* localização das fórmulas;
* documentação;
* reutilização;
* governança;
* auditoria das definições.

---

## 12. Medidas DAX

### 12.1 Clientes analisados

```DAX
Clientes Analisados =
DISTINCTCOUNT('gold fato_pedido'[Cliente_SK])
```

**Objetivo:** contar clientes distintos com pedidos no contexto de filtro.

**Tabela de origem:** `gold fato_pedido`.

**Granularidade do resultado:** depende do contexto aplicado ao relatório.

**Observação:** a medida contabiliza clientes presentes na tabela de pedidos, e não necessariamente todos os clientes cadastrados na dimensão.

---

### 12.2 Pedidos

```DAX
Pedidos =
COUNTROWS('gold fato_pedido')
```

**Objetivo:** contar a quantidade de registros da tabela de pedidos.

**Tabela de origem:** `gold fato_pedido`.

**Premissa:** cada linha representa um pedido.

**Risco controlado:** se a granularidade da tabela fosse alterada, a medida precisaria ser revisada.

---

### 12.3 Itens vendidos

```DAX
Itens Vendidos =
SUM('gold fato_item_pedido'[Quantidade])
```

**Objetivo:** somar a quantidade de unidades vendidas.

**Tabela de origem:** `gold fato_item_pedido`.

**Observação:** essa medida representa unidades vendidas, não a quantidade de linhas da tabela e nem a quantidade de produtos distintos.

---

### 12.4 Receita líquida

```DAX
Receita Líquida =
SUM('gold fato_pedido'[Valor_Liquido_Pedido])
```

**Objetivo:** calcular o valor líquido total dos pedidos.

**Tabela de origem:** `gold fato_pedido`.

**Unidade:** moeda brasileira.

**Formato:** `R$`, com duas casas decimais.

---

### 12.5 Ticket médio

```DAX
Ticket Médio =
DIVIDE([Receita Líquida], [Pedidos], 0)
```

**Objetivo:** calcular o valor médio líquido por pedido.

**Numerador:** receita líquida.

**Denominador:** quantidade de pedidos.

**Tratamento de divisão por zero:** retorno igual a zero.

**Unidade:** moeda brasileira por pedido.

---

### 12.6 Margem bruta

```DAX
Margem Bruta =
SUM('gold fato_pedido'[Margem_Bruta_Pedido])
```

**Objetivo:** calcular a margem bruta acumulada dos pedidos.

**Tabela de origem:** `gold fato_pedido`.

**Unidade:** moeda brasileira.

**Observação:** esta medida representa valor monetário de margem, e não margem percentual.

---

### 12.7 Avaliação média

```DAX
Avaliação Média =
AVERAGE('gold fato_entrega'[Avaliacao_Cliente])
```

**Objetivo:** calcular a média das avaliações registradas pelos clientes.

**Tabela de origem:** `gold fato_entrega`.

**Unidade:** pontos na escala de avaliação utilizada pelo dataset.

**Tratamento de nulos:** o `AVERAGE` ignora valores em branco.

---

### 12.8 Taxa de atraso

```DAX
Taxa de Atraso =
DIVIDE(
    CALCULATE(
        COUNTROWS('gold fato_entrega'),
        'gold fato_entrega'[Atraso_Entrega_Informado] = TRUE()
    ),
    COUNTROWS(
        FILTER(
            'gold fato_entrega',
            NOT ISBLANK('gold fato_entrega'[Atraso_Entrega_Informado])
        )
    ),
    0
)
```

**Objetivo:** calcular a proporção de entregas marcadas como atrasadas.

**Numerador:** entregas com atraso informado como verdadeiro.

**Denominador:** entregas com informação de atraso preenchida.

**Tratamento de nulos:** registros sem informação de atraso não participam do denominador.

**Formato:** percentual com duas casas decimais.

Essa definição evita classificar valores ausentes como entregas sem atraso.

---

## 13. Dimensão temporal

A dimensão `gold dim_data` contém os atributos utilizados na análise temporal.

O campo original `Ano_Mes` possui formato numérico e não era adequado para leitura direta nos gráficos.

Para melhorar a apresentação, foi criada a coluna calculada:

```DAX
Ano_Mes_Exibicao =
FORMAT(
    DATE(
        INT('gold dim_data'[Ano_Mes] / 100),
        MOD('gold dim_data'[Ano_Mes], 100),
        1
    ),
    "mmm/yyyy",
    "pt-BR"
)
```

O resultado apresenta os períodos no formato:

```text
jan/2025
fev/2025
mar/2025
```

A coluna `Ano_Mes_Exibicao` foi classificada pela coluna `Ano_Mes`, garantindo a ordem cronológica correta.

Essa classificação evita que os meses sejam organizados alfabeticamente.

---

## 14. Segmentação de dados

Foi criada uma segmentação de dados utilizando:

```text
gold dim_data[Ano_Mes_Exibicao]
```

A segmentação foi configurada como lista suspensa e identificada pelo título:

```text
Período
```

O filtro afeta os cartões e os gráficos mensais.

A atualização simultânea dos indicadores confirmou a propagação dos filtros da dimensão de data para as tabelas-fato relacionadas.

---

## 15. Estrutura do dashboard

O dashboard foi organizado em uma única página denominada visão geral.

A estrutura contém:

* título;
* subtítulo;
* segmentação de período;
* oito cartões de indicadores;
* oito gráficos mensais.

### 15.1 Indicadores da primeira linha

* Clientes analisados;
* Pedidos;
* Itens vendidos;
* Receita líquida.

### 15.2 Indicadores da segunda linha

* Margem bruta;
* Ticket médio;
* Taxa de atraso;
* Avaliação média.

Cada indicador possui:

1. um cartão com o valor consolidado;
2. um gráfico com a evolução mensal.

Essa combinação permite visualizar simultaneamente o total e o comportamento temporal.

---

## 16. Tipos de gráficos

| Indicador           | Visual utilizado | Finalidade                            |
| ------------------- | ---------------- | ------------------------------------- |
| Clientes analisados | Linha            | Evidenciar a evolução mensal          |
| Pedidos             | Colunas          | Comparar o volume mensal              |
| Itens vendidos      | Colunas          | Comparar unidades vendidas            |
| Receita líquida     | Linha            | Observar tendência financeira         |
| Margem bruta        | Colunas          | Comparar contribuição mensal          |
| Ticket médio        | Linha            | Avaliar variação do valor médio       |
| Taxa de atraso      | Colunas          | Comparar o percentual mensal          |
| Avaliação média     | Linha            | Identificar oscilações na experiência |

A seleção dos visuais considerou a legibilidade, a comparação entre períodos e a natureza de cada indicador.

---

## 17. Identidade visual

O dashboard utiliza:

* azul escuro nos cabeçalhos;
* azul mais claro nos elementos gráficos;
* fundo branco nas áreas de conteúdo;
* cinza escuro na separação entre os blocos;
* títulos em caixa alta nos cartões;
* organização em grade com quatro colunas.

O tema visual utilizado foi preservado no arquivo:

```text
Tema.json
```

A identidade visual busca:

* consistência;
* legibilidade;
* hierarquia;
* contraste;
* apresentação adequada para portfólio.

---

## 18. Resultados exibidos na versão inicial

Na visão consolidada, sem filtro específico de período, o dashboard apresenta aproximadamente:

| Indicador           | Resultado exibido |
| ------------------- | ----------------: |
| Clientes analisados |               330 |
| Pedidos             |             3 mil |
| Itens vendidos      |            13 mil |
| Receita líquida     |     R$ 289,90 mil |
| Margem bruta        |     R$ 151,25 mil |
| Ticket médio        |         R$ 103,95 |
| Taxa de atraso      |             9,90% |
| Avaliação média     |              4,27 |

Os valores abreviados apresentados nos cartões, como `3 mil` e `13 mil`, são efeitos da unidade automática de exibição do Power BI.

Para reconciliação técnica, devem ser utilizados os valores exatos das medidas, sem abreviação.

Os resultados representam o contexto integral selecionado no relatório e podem mudar quando a segmentação de período for aplicada.

---

## 19. Validações realizadas

### 19.1 Validação de atualização

Foi verificado que as consultas carregam sem erros impeditivos.

### 19.2 Validação dos relacionamentos

Foi confirmado que:

* os relacionamentos estão ativos;
* as dimensões ocupam o lado `1`;
* os fatos ocupam o lado `*`;
* o filtro segue das dimensões para os fatos;
* não existem relacionamentos diretos entre fatos.

### 19.3 Validação temporal

A segmentação de período recalculou os oito indicadores.

Isso demonstra que a dimensão de data filtra adequadamente as tabelas-fato utilizadas pelas medidas.

### 19.4 Validação visual

Foram verificados:

* títulos;
* alinhamento;
* formatação monetária;
* formatação percentual;
* ordem dos meses;
* exibição da segmentação;
* contraste de cores;
* consistência entre cartões e gráficos.

### 19.5 Validação para publicação

Foram preparados para o GitHub:

```text
power_bi/eda_geral/Customer_Analytics_Hub_EDA_Geral.pbix
docs/images/dashboard_eda_geral.png
Tema.json
README.md
```

O arquivo `.pbix` possui tamanho compatível com o limite de arquivos individuais do GitHub.

---

## 20. Reconciliação SQL Server × DAX

A reconciliação das oito métricas canônicas da EDA geral foi concluída em 21/09/2026.

Foram comparados os resultados calculados diretamente no SQL Server com os valores exatos produzidos pelas medidas DAX no Power BI.

### 20.1 Validação da granularidade

| Tabela | Linhas | Chaves distintas | Duplicidades | Status |
|---|---:|---:|---:|---|
| `gold.fato_pedido` | 2.789 | 2.789 | 0 | Aprovado |
| `gold.fato_item_pedido` | 6.495 | 6.495 | 0 | Aprovado |
| `gold.fato_entrega` | 2.789 | 2.789 | 0 | Aprovado |

A ausência de duplicidades confirmou a preservação das granularidades utilizadas pelas métricas.

### 20.2 Resultado da reconciliação

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

As oito métricas foram aprovadas, sem diferenças entre SQL e DAX.

### 20.3 Campo de atraso

A distribuição utilizada no cálculo da taxa de atraso foi:

| Classificação | Quantidade |
|---|---:|
| Não | 2.513 |
| Sim | 276 |
| Total | 2.789 |

O cálculo reconciliado foi:

```text
Taxa de atraso = 276 ÷ 2.789
Taxa de atraso = 9,90%
```

Não foram identificados valores nulos ou vazios no campo `Atraso_Entrega_Informado`.

### 20.4 Evidências

A consulta utilizada está registrada em:

```text
sql/05_eda_geral/12_reconciliacao_metricas_eda_geral.sql
```

O relatório detalhado está registrado em:

```text
docs/technical/05_eda_geral/reconciliacao_metricas_eda_geral.md
```

A evidência visual está armazenada em:

```text
docs/images/reconciliacao_metricas_sql_dax.png
```

### 20.5 Conclusão da reconciliação

A equivalência integral demonstra que:

- SQL e DAX utilizam as mesmas definições;
- as granularidades das tabelas-fato foram preservadas;
- não ocorreram duplicações nos cálculos;
- os relacionamentos do modelo semântico estão funcionando;
- os filtros temporais alcançam adequadamente as tabelas-fato;
- as métricas podem ser reutilizadas nas análises específicas.

As oito métricas passam a ser consideradas definições canônicas do Customer Analytics Hub.

---

## 21. Limitações conhecidas

### 21.1 Dataset de natureza simulada

O projeto utiliza o dataset Food Commerce Digital Twin. Portanto, os resultados demonstram capacidade técnica e analítica, mas não representam uma operação comercial real.

### 21.2 Dados exibidos de forma abreviada

Alguns cartões utilizam unidades automáticas, como `mil`. A abreviação melhora a leitura, mas não deve ser utilizada como evidência de reconciliação.

### 21.3 Credenciais não incorporadas

O arquivo `.pbix` não deve ser considerado autossuficiente para atualização em outros ambientes.

A conexão com o SQL Server depende de:

* servidor disponível;
* banco de dados disponível;
* permissões;
* credenciais;
* configuração local.

Nenhuma senha, token ou connection string sensível deve ser versionada.

### 21.4 Escopo da visão geral

O dashboard apresenta indicadores gerais. Ele não responde, isoladamente, perguntas aprofundadas sobre:

* causas das variações;
* segmentos de clientes;
* rentabilidade por produto;
* eficiência de campanhas;
* desempenho de transportadoras;
* efeito de eventos externos;
* comportamento geográfico;
* causalidade.

Essas análises serão desenvolvidas nos domínios seguintes.

### 21.5 Causalidade

Os gráficos mensais evidenciam variações e associações temporais, mas não demonstram causalidade.

Qualquer afirmação causal exigirá desenho analítico específico, controle de variáveis e evidência estatística adequada.

---

## 22. Decisões técnicas principais

| Decisão                              | Justificativa                                        |
| ------------------------------------ | ---------------------------------------------------- |
| Utilizar a camada Gold no Power BI   | Evitar cálculos baseados diretamente em dados brutos |
| Centralizar medidas em `00_Medidas`  | Melhorar organização e governança                    |
| Usar esquema estrela                 | Reduzir ambiguidades e facilitar filtros             |
| Evitar relacionamentos fato com fato | Prevenir caminhos de filtro complexos                |
| Usar dimensão calendário             | Padronizar análises temporais                        |
| Criar `Ano_Mes_Exibicao`             | Melhorar legibilidade sem perder ordenação           |
| Utilizar filtro de período           | Permitir análise dinâmica dos indicadores            |
| Preservar o `.pbix` no GitHub        | Garantir rastreabilidade do relatório                |
| Publicar imagem no README            | Permitir visualização sem Power BI Desktop           |
| Versionar `Tema.json`                | Preservar a identidade visual                        |
| Separar métricas por domínio         | Manter definições consistentes entre áreas           |

---

## 23. Governança das métricas

As métricas da EDA geral devem ser tratadas como definições canônicas.

As análises comercial, financeira, logística e de marketing poderão utilizar filtros e dimensões diferentes, mas não deverão redefinir arbitrariamente:

* pedidos;
* itens vendidos;
* receita líquida;
* margem bruta;
* ticket médio;
* taxa de atraso;
* avaliação média;
* clientes analisados.

Qualquer alteração em uma definição deverá:

1. receber uma nova versão;
2. registrar a justificativa;
3. indicar a data da mudança;
4. identificar o responsável;
5. avaliar o impacto nos resultados anteriores;
6. atualizar SQL, DAX e documentação;
7. ser submetida novamente à reconciliação.

---

## 24. Evidências do desenvolvimento

As evidências técnicas incluem:

* scripts Python;
* arquivos de configuração;
* logs controlados;
* manifestos;
* contratos de dados;
* relatórios de qualidade;
* consultas SQL;
* tabelas de auditoria;
* reconciliação Parquet versus SQL Server;
* modelo dimensional;
* arquivo Power BI;
* imagem do dashboard;
* medidas DAX;
* documentação Markdown;
* histórico de commits no Git.

Os dados pesados, as credenciais e os logs reais não são publicados no GitHub.

---

customer-analytics-hub/
├── README.md
├── Tema.json
├── docs/
│   ├── images/
│   │   ├── dashboard_eda_geral.png
│   │   └── reconciliacao_metricas_sql_dax.png
│   ├── technical/
│   │   └── 05_eda_geral/
│   │       ├── eda_geral_documentacao_tecnica.md
│   │       └── reconciliacao_metricas_eda_geral.md
│   └── governance/
│       ├── metrics_catalog.md
│       └── metricas_eda_geral.md
├── power_bi/
│   └── eda_geral/
│       └── Customer_Analytics_Hub_EDA_Geral.pbix
├── configs/
│   └── analysis_domains.json
├── sql/
│   └── 05_eda_geral/
│       └── 12_reconciliacao_metricas_eda_geral.sql
└── src/

---

## 26. Próximas etapas

1. Criar o resumo executivo da EDA geral;
2. Revisar as limitações e conclusões da visão geral;
3. Realizar a revisão final da documentação técnica;
4. Versionar a consulta SQL, a reconciliação e as evidências;
5. Atualizar o README com o encerramento da EDA geral;
6. Atualizar o arquivo Power BI com a página de validação;
7. Executar o commit e o push dos novos artefatos;
8. Iniciar a análise do domínio Comercial;
9. Reutilizar as definições canônicas nos demais domínios;
10. Atualizar a documentação conforme o projeto evoluir.


---

## 27. Critérios para conclusão da EDA geral

| Critério | Situação |
|---|---|
| Tabelas Gold carregadas e reconciliadas | Concluído |
| Relacionamentos documentados | Concluído |
| Medidas DAX catalogadas | Concluído |
| Resultados SQL e Power BI equivalentes | Concluído |
| Segmentação temporal validada | Concluído |
| Dashboard construído e salvo | Concluído |
| Imagem do dashboard publicada no README | Concluído |
| Limitações técnicas registradas | Concluído |
| Evidência da reconciliação SQL × DAX criada | Concluído |
| Consulta de reconciliação criada | Concluído |
| Documento técnico revisado | Concluído |
| Resumo executivo concluído | Concluído |
| Novos artefatos versionados no GitHub | Pendente |

A EDA geral será considerada definitivamente concluída após:

1. criação do resumo executivo;
2. revisão final da documentação;
3. versionamento dos novos artefatos;
4. atualização do README com o encerramento da etapa.

---

## 28. Conclusão técnica

A EDA geral estabeleceu a primeira camada de consumo visual do Customer Analytics Hub.

O dashboard demonstra a integração entre:

* arquitetura em camadas;
* preparação de dados;
* controle de qualidade;
* modelagem dimensional;
* SQL Server;
* Power Query;
* modelo semântico;
* medidas DAX;
* visualização de dados;
* documentação;
* versionamento.

A principal contribuição desta etapa não é apenas a criação de gráficos. O resultado consolida uma base governada e reutilizável para análises posteriores.

As próximas análises deverão aprofundar as causas e os padrões observados, preservando as mesmas dimensões, fatos e definições canônicas utilizadas na EDA geral.
