# Escopo e Perguntas de Negócio — Análise Comercial

## Customer Analytics Hub

| Campo | Informação |
|---|---|
| Módulo | Análise Comercial |
| Ordem no projeto | Primeira análise temática após a EDA Geral |
| Banco de dados | `CustomerAnalyticsHub` |
| Camada analítica | Gold |
| Período analisado | Janeiro a dezembro de 2025 |
| Data de definição | 05/10/2026 |
| Status | Em desenvolvimento — escopo definido |

---

## 1. Contexto

A EDA Geral consolidou uma visão panorâmica do Customer Analytics Hub e validou oito métricas canônicas entre SQL Server e DAX. A Análise Comercial inicia o aprofundamento temático do projeto, reutilizando a mesma camada Gold, as mesmas granularidades e as mesmas definições de cálculo.

O módulo comercial deverá explicar como clientes, produtos, categorias, períodos e incentivos se relacionam com o desempenho das vendas. Seu eixo central será a **rentabilidade sustentável**: identificar quando o crescimento de pedidos, itens e receita também preserva ou amplia a margem bruta.

A análise não deverá considerar aumento de volume como resultado positivo de forma automática. Campanhas, descontos ou frete grátis podem estimular vendas e, ao mesmo tempo, reduzir a contribuição econômica dos pedidos.

---

## 2. Objetivo geral

Identificar os fatores associados ao desempenho comercial, compreender a estrutura e o comportamento da base de clientes e localizar oportunidades de crescimento que conciliem receita, recorrência e margem bruta.

---

## 3. Pergunta central

> Como clientes, produtos, períodos e incentivos comerciais se relacionam com vendas, receita e margem bruta, e quais oportunidades permitem crescer sem deteriorar a contribuição econômica?

---

## 4. Papel da Análise Comercial no projeto

A Análise Comercial funcionará como ponte entre a EDA Geral e os módulos Financeiro, Logístico e de Marketing.

Ela deverá:

- responder às perguntas diretamente relacionadas ao desempenho de vendas;
- identificar padrões e segmentos comercialmente relevantes;
- produzir evidências e hipóteses para os módulos seguintes;
- registrar quais achados exigem aprofundamento especializado;
- preservar a consistência das métricas entre todas as áreas.

| Achado comercial | Encaminhamento principal |
|---|---|
| Receita cresce, mas a margem percentual diminui | Análise Financeira |
| Produtos vendem muito, mas geram pouca margem | Análise Financeira |
| Frete grátis estimula pedidos, mas possui custo relevante | Análises Financeira e Logística |
| Atrasos aparecem em clientes ou regiões de alto valor | Análise Logística |
| Campanhas aumentam vendas apenas durante a promoção | Análise de Marketing |
| Clientes compram somente com descontos | Análises de Marketing e Financeira |
| Canais atraem clientes com recorrências diferentes | Análise de Marketing |

A Análise Comercial indicará esses caminhos, mas não deverá esgotar as investigações específicas das outras áreas.

---

## 5. Perguntas-mãe

### AC01 — Origem do crescimento

**Pergunta:** o crescimento comercial vem de mais clientes, maior frequência, mais itens por pedido, maior ticket, alteração de preços ou mudança no mix de produtos?

Questões complementares:

1. Quais componentes explicam a variação mensal da receita?
2. O crescimento foi sustentado por aquisição de clientes ou por recompra?
3. A quantidade média de itens por pedido aumentou?
4. O ticket médio cresceu por preço, quantidade ou mudança no mix?
5. Quais produtos, categorias, regiões e períodos contribuíram para o crescimento?

### AC02 — Sustentabilidade econômica

**Pergunta:** o aumento de pedidos e receita também amplia a margem bruta ou gera apenas volume com baixa contribuição?

Questões complementares:

1. Receita e margem bruta evoluem na mesma direção?
2. Em quais períodos o volume cresceu enquanto a margem percentual caiu?
3. Quais produtos e categorias combinam receita elevada e margem saudável?
4. Quais itens geram volume, mas pouca contribuição econômica?
5. A composição das vendas favoreceu produtos de maior ou menor margem?

### AC03 — Incentivos comerciais

**Pergunta:** campanhas, descontos e frete grátis estão associados a ganhos suficientes de volume, receita e recorrência para compensar a redução da margem?

Questões complementares:

1. Pedidos com campanha apresentam maior ticket, quantidade e margem do que pedidos sem campanha?
2. Quais campanhas concentram receita e quais concentram margem?
3. Descontos maiores estão associados a crescimento proporcional do volume?
4. Existem faixas de desconto nas quais o ganho de volume deixa de compensar a redução da margem?
5. Pedidos com frete grátis apresentam maior valor e quantidade de itens?
6. O uso simultâneo de campanha, desconto e frete grátis comprime excessivamente a margem?
7. Clientes atraídos por incentivos voltam a comprar sem promoção?

### AC04 — Concentração comercial

**Pergunta:** quais clientes, produtos, categorias, períodos, regiões e canais concentram receita e margem, e qual risco essa dependência representa?

Questões complementares:

1. Qual percentual dos clientes gera 80% da receita?
2. Os clientes que concentram receita também concentram margem?
3. Quais produtos e categorias compõem as faixas A, B e C?
4. A concentração permanece estável ao longo dos meses?
5. O negócio depende excessivamente de poucos clientes, produtos ou campanhas?

### AC05 — Estrutura de clientes

**Pergunta:** quais perfis de clientes existem em termos de recência, frequência, valor, margem, preferências e dependência de incentivos?

Questões complementares:

1. Quais clientes são frequentes e rentáveis?
2. Existem clientes frequentes com baixa contribuição de margem?
3. Quais clientes possuem ticket elevado, mas baixa recorrência?
4. Quais dependem de descontos ou campanhas para comprar?
5. Quais compram sem incentivos e preservam maior margem?
6. Quais categorias e combinações de produtos caracterizam cada perfil?
7. Características demográficas ajudam a interpretar os segmentos comportamentais?

### AC06 — Oportunidades comerciais

**Pergunta:** quais clientes podem comprar mais, quais estão reduzindo atividade e quais combinações de produtos podem ampliar a cesta sem destruir margem?

Questões complementares:

1. Quais clientes apresentam sinais de redução de atividade?
2. Quais possuem potencial de aumentar frequência ou ticket?
3. Quais produtos e categorias costumam ser comprados em conjunto?
4. Quais combinações podem apoiar ações de cross-selling?
5. Quais oportunidades apresentam potencial comercial com margem adequada?
6. Quais ações devem ser priorizadas por segmento de cliente?

---

## 6. Escopo analítico

### 6.1 Incluído

- evolução temporal de clientes, pedidos, itens, receita, ticket e margem;
- decomposição do crescimento por volume, preço, mix e recorrência;
- desempenho por cliente, produto, categoria, região, canal e campanha;
- análise de descontos e frete grátis;
- Pareto e classificação ABC de clientes, produtos e categorias;
- recência, frequência e valor monetário;
- coortes de primeira compra e recompra;
- segmentação comportamental de clientes;
- associações entre incentivos e resultados comerciais;
- oportunidades de cross-selling e ampliação de cesta;
- encaminhamento de achados para Financeiro, Logística e Marketing.

### 6.2 Fora do escopo desta etapa

- cálculo de lucro líquido;
- atribuição causal definitiva a campanhas, descontos ou frete grátis;
- avaliação completa de custos operacionais e despesas administrativas;
- otimização logística de rotas e transportadoras;
- atribuição de marketing multicanal;
- automação de campanhas ou implantação de modelos em produção;
- recomendações comerciais sem evidência quantitativa e validação.

---

## 7. Limites conceituais

### 7.1 Margem bruta não é lucro líquido

A base contém receita, custo dos produtos e margem bruta. Não contém todas as despesas necessárias para calcular lucro líquido, como despesas administrativas, impostos, custos fixos, salários e investimentos em marketing.

Portanto, o módulo utilizará **margem bruta** e **margem percentual**, evitando apresentar esses indicadores como lucro líquido.

### 7.2 Associação não representa causalidade

Os dados são observacionais e não resultam de um experimento aleatorizado. Uma diferença entre pedidos com e sem campanha pode refletir produto, período, perfil do cliente ou outros fatores.

As conclusões deverão utilizar expressões como:

> Pedidos associados à campanha apresentaram maior receita média dentro das condições analisadas.

Não deverá ser utilizada, sem desenho causal defensável, a afirmação:

> A campanha causou o aumento da receita.

### 7.3 Frete grátis possui limitação econômica

Se o valor subsidiado do frete não estiver completamente registrado como custo da empresa, será possível avaliar sua associação com pedidos, receita e margem dos produtos, mas não calcular o retorno econômico integral do benefício.

### 7.4 Técnicas avançadas precisam responder a uma pergunta

Algoritmos de machine learning e conceitos de cálculo somente serão utilizados quando houver dados suficientes, hipótese clara, validação e utilidade para uma decisão comercial.

---

## 8. Base métrica herdada da EDA Geral

| Métrica canônica | Resultado geral validado |
|---|---:|
| Clientes analisados | 330 |
| Pedidos | 2.789 |
| Itens vendidos | 13.375 |
| Receita líquida | R$ 289.904,66 |
| Margem bruta | R$ 151.248,65 |
| Ticket médio | R$ 103,95 |
| Taxa de atraso | 9,90% |
| Avaliação média | 4,27 |

Essas definições não deverão ser alteradas arbitrariamente. Novas métricas comerciais deverão ser derivadas e documentadas a partir dessa base reconciliada.

---

## 9. Métricas comerciais previstas

### 9.1 Desempenho

- clientes ativos;
- novos clientes;
- clientes recorrentes;
- pedidos;
- itens vendidos;
- receita bruta e líquida;
- margem bruta monetária;
- margem percentual;
- ticket médio;
- itens médios por pedido;
- produtos distintos por pedido;
- frequência de compra;
- intervalo médio entre compras.

### 9.2 Incentivos

- desconto monetário;
- desconto percentual ponderado;
- receita e margem por faixa de desconto;
- pedidos com campanha;
- pedidos sem campanha;
- pedidos com frete grátis;
- combinação de campanha, desconto e frete grátis;
- recorrência posterior ao incentivo.

### 9.3 Clientes

- recência;
- frequência;
- valor monetário;
- margem gerada por cliente;
- ticket médio por cliente;
- quantidade média de itens;
- diversidade de produtos e categorias;
- proporção de compras com incentivo;
- primeira e última compra;
- tempo de relacionamento;
- retenção por coorte;
- sinais de redução de atividade.

### 9.4 Concentração

- participação acumulada na receita;
- participação acumulada na margem;
- classificação ABC;
- concentração por cliente;
- concentração por produto;
- concentração por categoria;
- concentração por campanha e canal.

---

## 10. Tabelas Gold principais

| Tabela | Papel na análise |
|---|---|
| `gold.fato_pedido` | Métricas no nível do pedido: receita, desconto, custo, margem, campanha e canal |
| `gold.fato_item_pedido` | Quantidades, produtos, categorias, preços, descontos e margem no nível do item |
| `gold.fato_cliente_mes` | Comportamento mensal, frequência acumulada, recência e status do cliente |
| `gold.fato_entrega` | Frete, frete grátis, prazo, atraso e avaliação como contexto comercial |
| `gold.dim_cliente` | Perfil demográfico e preferências informadas |
| `gold.dim_produto` | Produto, categoria e medida |
| `gold.dim_data` | Análises mensais, trimestrais, sazonais e por datas especiais |
| `gold.dim_campanha` | Identificação das campanhas |
| `gold.dim_canal_marketing` | Comparação entre canais |
| `gold.dim_geografia` | Cidade, estado e região |
| `gold.dim_evento_externo` | Contextualização de eventos externos |

---

## 11. Métodos previstos

| Problema | Método | Finalidade |
|---|---|---|
| Origem do crescimento | Decomposição volume, preço, mix e recorrência | Explicar os componentes da variação comercial |
| Concentração | Pareto e curva ABC | Identificar clientes e produtos relevantes e riscos de dependência |
| Evolução de clientes | RFM e coortes | Medir valor, recorrência, retenção e redução de atividade |
| Comparação entre grupos | Estatística descritiva, testes de hipótese e tamanho de efeito | Comparar campanha, desconto e frete grátis |
| Relação entre variáveis | Pearson, Spearman ou Kendall conforme as condições | Avaliar direção e intensidade das associações |
| Controle de diferenças observáveis | Regressão | Estimar associações ajustadas por período, produto e perfil |
| Segmentação | K-Means e GMM | Identificar grupos comportamentais |
| Validação dos clusters | Elbow, Silhouette, Davies-Bouldin e estabilidade | Avaliar qualidade e consistência dos segmentos |
| Redução de redundância | PCA, somente se necessário | Reduzir colinearidade e dimensionalidade |
| Afinidade de produtos | Regras de associação ou análise de cesta | Identificar oportunidades de cross-selling |
| Probabilidade futura | Modelo de recompra ou inatividade, se defensável | Priorizar oportunidades e riscos comerciais |

Métodos como diferenças em diferenças ou escore de propensão somente serão considerados se a estrutura dos dados permitir grupos, períodos e controles adequados. A utilização não será obrigatória.

---

## 12. Aplicação possível de cálculo

Conceitos de cálculo poderão apoiar a análise da relação entre desconto e margem caso exista variação suficiente nos níveis de desconto.

Uma formulação possível é:

```text
M(d) = R(d) - C(d)
```

Onde:

- `d` representa o desconto;
- `R(d)` representa a receita em função do desconto;
- `C(d)` representa o custo em função do desconto;
- `M(d)` representa a margem resultante.

A derivada `M'(d)` representaria a variação marginal da margem quando o desconto aumenta. Um ponto com `M'(d) = 0` poderia indicar uma faixa candidata de maximização, desde que o modelo seja adequado e os dados sustentem essa interpretação.

Sem observações suficientes, a análise permanecerá em faixas empíricas de desconto, sem alegar a existência de um desconto ótimo.

---

## 13. Variáveis candidatas para segmentação

- recência em dias;
- frequência de pedidos;
- valor monetário acumulado;
- margem bruta acumulada;
- ticket médio;
- quantidade média de itens;
- produtos distintos;
- categorias distintas;
- intervalo médio entre compras;
- desconto médio ponderado;
- proporção de pedidos com campanha;
- proporção de pedidos com frete grátis;
- diversidade de canais;
- avaliação média;
- taxa de atraso.

Variáveis redundantes ou diretamente derivadas umas das outras deverão ser avaliadas antes do clustering. Transformações como `log1p`, padronização por Z-Score ou redução de dimensionalidade somente serão aplicadas após diagnóstico das distribuições e correlações.

---

## 14. Sequência de execução

1. Validar o escopo e as perguntas AC01–AC06.
2. Criar o catálogo de métricas comerciais.
3. Mapear tabelas, colunas, granularidades e chaves.
4. Criar consultas SQL de diagnóstico e bases analíticas.
5. Reconciliar os totais com as métricas canônicas da EDA Geral.
6. Desenvolver análises descritivas e comparativas.
7. Executar Pareto e classificação ABC.
8. Construir RFM, coortes e indicadores de recorrência.
9. Avaliar campanhas, descontos e frete grátis.
10. Construir e validar segmentações de clientes.
11. Avaliar cesta de produtos e oportunidades comerciais.
12. Desenvolver as medidas DAX e as páginas comerciais no Power BI.
13. Reconciliar SQL, Python e DAX.
14. Documentar resultados, limitações e decisões.
15. Produzir resumo executivo e atualizar o GitHub.

---

## 15. Critérios de qualidade

A Análise Comercial será considerada tecnicamente aprovada quando:

- utilizar as mesmas métricas canônicas da EDA Geral;
- preservar as granularidades das tabelas fato;
- apresentar consultas e resultados reproduzíveis;
- separar descrição, associação, previsão e causalidade;
- documentar hipóteses, limitações e critérios de decisão;
- validar modelos e clusters com métricas adequadas;
- evitar recomendações não sustentadas pelos dados;
- reconciliar resultados entre SQL Server, Python e Power BI;
- encaminhar corretamente os achados para as análises posteriores.

---

## 16. Entregas previstas

- escopo e perguntas de negócio;
- catálogo de métricas comerciais;
- dicionário das bases analíticas;
- consultas SQL versionadas;
- notebooks ou scripts Python reproduzíveis;
- resultados de Pareto e classificação ABC;
- análise RFM e coortes;
- segmentação validada de clientes;
- análise de campanhas, descontos e frete grátis;
- análise de cesta e oportunidades comerciais;
- dashboard comercial no Power BI;
- reconciliação SQL × Python × DAX;
- documentação técnica;
- resumo executivo;
- atualização do README e do GitHub.

---

## 17. Próxima atividade

Após a aprovação deste documento, a próxima atividade será criar o catálogo de métricas da Análise Comercial, definindo para cada métrica:

- nome;
- pergunta atendida;
- definição de negócio;
- fórmula;
- tabela e granularidade de origem;
- filtros e exclusões;
- implementação prevista em SQL, Python e DAX;
- critério de reconciliação.

---

## 18. Status inicial

```text
EDA GERAL: CONCLUÍDA
ANÁLISE COMERCIAL: EM DESENVOLVIMENTO
ESCOPO E PERGUNTAS: DEFINIDOS E APROVADOS
CATÁLOGO DE MÉTRICAS COMERCIAIS: PRÓXIMA ATIVIDADE
```
