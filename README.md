# Customer Analytics Hub

Projeto de engenharia, arquitetura e análise de dados desenvolvido para demonstrar a construção completa de uma solução analítica, desde a avaliação técnica da fonte até a produção de análises orientadas às necessidades do negócio.

## Status do projeto

Em desenvolvimento.

Etapa atual: fundação técnica e preparação do ambiente.

Nenhum resultado analítico foi publicado até o momento.

## Objetivo

Construir um pipeline de dados reproduzível e documentado, utilizando apenas os dados-base do dataset Food Commerce Digital Twin.

Dimensões, tabelas-fato, métricas, indicadores e análises serão construídos durante o projeto. As estruturas analíticas existentes no arquivo original não serão utilizadas como entrada do pipeline.

Cada decisão deverá responder:

- o que foi feito;
- por que foi necessário;
- como foi implementado;
- qual evidência sustentou a decisão;
- qual foi o custo técnico e operacional;
- como o resultado foi validado;
- qual é sua interpretação.

## Fonte de dados

A fonte selecionada é a aba `25_bronze_transactions_sujo`, presente no arquivo:

`FOOD_COMMERCE_DIGITAL_TWIN_v3_DADOS_SUJOS_INTENCIONAIS.xlsx`

O arquivo completo será preservado no Azure Data Lake Storage Gen2. Os dados pesados não serão armazenados neste repositório.

## Arquitetura de armazenamento

O projeto utiliza arquitetura em camadas no Azure Data Lake Storage Gen2:

- `00_landing`: recebimento e preservação do arquivo original;
- `01.1_bronze_raw`: dados brutos acompanhados dos metadados de ingestão;
- `02_silver`: dados tipados, padronizados, normalizados e validados em Parquet;
- `03_gold`: estruturas analíticas preparadas para consumo;
- `03_gold_exports`: exportações destinadas às ferramentas consumidoras.

## Estratégia de processamento

Os dados são recebidos em lote. O processamento principal será realizado localmente com Python, Pandas e PyArrow.

Essa decisão considera:

- volumetria compatível com processamento local;
- ausência de necessidade de baixa latência;
- redução de custos recorrentes de computação em nuvem;
- menor complexidade operacional;
- manutenção do Azure como camada de armazenamento.

Apache Spark e Spark SQL poderão ser implementados posteriormente como alternativa de escalabilidade, desde que exista uma justificativa técnica.

## Etapas metodológicas

### 1. Fundação técnica

Preparação do repositório, ambiente de desenvolvimento, segurança, versionamento, dependências e conectividade.

### 2. EDA técnica da Bronze

Investigação da estrutura e da qualidade da fonte antes de qualquer limpeza:

- linhas e colunas;
- tipos inferidos;
- granularidade aparente;
- chaves candidatas;
- nulidade;
- duplicidades;
- cardinalidade;
- domínios categóricos;
- datas e horários;
- valores monetários;
- valores negativos ou impossíveis;
- coerência entre colunas;
- repetição de atributos;
- integridade entre eventos;
- campos básicos e calculados.

### 3. Contrato de dados

Definição de nomes canônicos, tipos esperados, domínios, regras de nulidade, chaves, critérios de validação e tratamentos previstos.

### 4. Normalização e Silver

Padronização dos valores, separação das entidades canônicas, deduplicação, tipagem, rastreabilidade e gravação em Parquet.

### 5. Validação da Silver

Testes de unicidade, completude, validade, consistência, integridade referencial e reconciliação entre Bronze e Silver.

### 6. EDA analítica

As perguntas de negócio serão formuladas somente após a aprovação da Silver. As análises poderão atender áreas como financeiro, comercial, logística, marketing e clientes.

## Governança de métricas

Cada métrica terá uma definição canônica contendo fórmula, granularidade, fontes, filtros, tratamento de nulos, período, unidade, arredondamento e versão.

As diferentes áreas poderão analisar perspectivas distintas, mas utilizarão as mesmas definições para receita, valor bruto, valor líquido, custos, lucro e demais indicadores compartilhados.

## Segurança

Não serão versionados:

- dados brutos ou pesados;
- arquivos Parquet;
- credenciais;
- tokens;
- connection strings;
- arquivos `.env`;
- logs reais;
- ambientes virtuais;
- arquivos temporários;
- resultados intermediários não selecionados para publicação.

O arquivo `.env.example` documentará apenas os nomes das variáveis necessárias, sem valores sensíveis.

## Reprodutibilidade

O projeto documentará:

- versão do Python;
- dependências;
- variáveis de ambiente;
- ordem de execução;
- entradas e saídas;
- contratos de dados;
- testes;
- decisões arquiteturais;
- critérios de aprovação de cada etapa.

## Tecnologias previstas

- Python
- Pandas
- NumPy
- PyArrow
- SQL Server
- T-SQL
- Azure Data Lake Storage Gen2
- Git e GitHub
- Power BI e DAX

Tecnologias adicionais serão incorporadas somente quando resolverem uma necessidade identificada.

## Repositório Snippets

Os códigos específicos e necessários para reproduzir este projeto permanecerão neste repositório.

Versões genéricas e reutilizáveis de funções Python e consultas SQL serão publicadas separadamente no repositório Snippets.