# Resumo Executivo — EDA Geral

## Customer Analytics Hub

| Campo | Informação |
|---|---|
| Projeto | Customer Analytics Hub |
| Etapa | Análise Exploratória Geral |
| Período analisado | Janeiro a dezembro de 2025 |
| Camada analítica | Gold |
| Status | Concluída e reconciliada |
| Data de conclusão | 21/09/2026 |

---

## 1. Visão executiva

A EDA geral foi desenvolvida para apresentar uma visão consolidada do desempenho do negócio antes do aprofundamento das análises Comercial, Financeira, Logística e de Marketing.

A solução integra dados preparados em arquitetura de camadas, tabelas dimensionais no SQL Server e indicadores calculados no Power BI.

O resultado fornece uma base analítica comum, governada e reutilizável para as próximas etapas do Customer Analytics Hub.

---

## 2. Principais resultados

| Indicador | Resultado |
|---|---:|
| Clientes analisados | 330 |
| Pedidos | 2.789 |
| Itens vendidos | 13.375 |
| Receita líquida | R$ 289.904,66 |
| Margem bruta | R$ 151.248,65 |
| Ticket médio | R$ 103,95 |
| Taxa de atraso | 9,90% |
| Avaliação média | 4,27 |

Os resultados representam o período integral analisado, sem aplicação de filtro mensal.

---

## 3. Leitura dos indicadores

### Clientes e pedidos

Foram identificados 330 clientes com pedidos no período, responsáveis por 2.789 pedidos.

A relação entre pedidos e clientes indica recorrência de compra, pois a quantidade de pedidos é significativamente superior ao número de clientes analisados.

Essa característica deverá ser aprofundada na análise Comercial por meio de frequência, recência, retenção e comportamento de recompra.

### Volume de itens

Foram vendidas 13.375 unidades.

O indicador representa a soma das quantidades comercializadas, e não apenas a quantidade de linhas existentes na tabela de itens.

A relação entre unidades vendidas e pedidos demonstra que os pedidos normalmente contêm múltiplas unidades.

### Receita e ticket médio

A operação registrou receita líquida de R$ 289.904,66 e ticket médio de R$ 103,95 por pedido.

O ticket médio fornece uma referência geral do valor transacionado, mas não explica isoladamente as diferenças entre produtos, categorias, clientes, campanhas ou regiões.

Essas variações serão investigadas nas análises específicas.

### Margem bruta

A margem bruta acumulada foi de R$ 151.248,65.

Esse valor representa margem monetária, e não percentual.

A análise Financeira deverá aprofundar:

- margem por produto;
- margem por categoria;
- impacto dos descontos;
- relação entre receita e custo;
- concentração da rentabilidade;
- pedidos com baixa contribuição financeira.

### Entregas

A taxa de atraso foi de 9,90%.

Entre 2.789 entregas avaliadas:

- 276 foram classificadas como atrasadas;
- 2.513 foram classificadas como não atrasadas.

O indicador representa aproximadamente uma entrega atrasada a cada dez entregas realizadas.

A análise Logística deverá identificar onde os atrasos estão concentrados, considerando período, região, transportadora, prazo prometido e características dos pedidos.

### Avaliação dos clientes

A avaliação média foi de 4,27.

O resultado indica percepção geral positiva, mas a média isolada pode ocultar diferenças entre entregas pontuais e atrasadas, transportadoras, regiões e perfis de clientes.

A etapa logística deverá avaliar a associação entre atraso, prazo real e avaliação do cliente, sem interpretar associação como causalidade.

---

## 4. Comportamento temporal

A evolução mensal demonstrou variação dos indicadores ao longo de 2025.

Os resultados indicam:

- crescimento do volume de pedidos nos primeiros meses;
- maior intensidade operacional entre abril e julho;
- redução do volume durante parte do segundo semestre;
- recuperação dos pedidos e da receita em dezembro;
- oscilação da taxa de atraso entre os meses;
- relativa estabilidade da avaliação média dos clientes.

Essas variações justificam análises posteriores sobre:

- sazonalidade;
- campanhas;
- eventos externos;
- composição do portfólio;
- comportamento dos clientes;
- desempenho logístico.

A EDA geral identifica os padrões iniciais, mas não atribui causalidade às variações observadas.

---

## 5. Confiabilidade dos resultados

As oito métricas foram calculadas independentemente no SQL Server e no Power BI.

A reconciliação apresentou equivalência integral:

```text
Métricas avaliadas: 8
Métricas aprovadas: 8
Métricas reprovadas: 0
Diferenças identificadas: 0
```

Também foi confirmada a ausência de duplicidades nas chaves avaliadas das principais tabelas-fato.

Com isso, as métricas da EDA geral passam a ser consideradas definições canônicas do projeto.

---

## 6. Entregas realizadas

A etapa produziu:

- modelo dimensional com 10 dimensões e 4 tabelas-fato;
- camada Gold carregada no SQL Server;
- dashboard da EDA geral no Power BI;
- oito medidas DAX documentadas;
- segmentação temporal;
- gráficos mensais;
- catálogo de métricas;
- consulta SQL de reconciliação;
- evidência da comparação SQL × DAX;
- documentação técnica detalhada;
- arquivos preparados para versionamento.

---

## 7. Limitações

Os resultados devem ser interpretados considerando que:

- o dataset possui natureza simulada;
- a EDA geral apresenta uma visão panorâmica;
- os indicadores consolidados não explicam sozinhos as causas das variações;
- associações observadas não representam causalidade;
- análises por produto, cliente, região, campanha e transportadora exigem aprofundamento;
- a atualização do Power BI depende da disponibilidade do SQL Server e das permissões de acesso.

Essas limitações não invalidam a solução. Elas delimitam o alcance das conclusões e orientam as próximas análises.

---

## 8. Recomendações analíticas

Com base na visão geral, recomenda-se:

1. aprofundar a recorrência e o comportamento de compra dos clientes;
2. identificar os principais geradores de receita e margem;
3. investigar produtos e categorias com alta receita e baixa contribuição;
4. avaliar o impacto de descontos sobre margem e ticket médio;
5. localizar períodos e segmentos com maior taxa de atraso;
6. comparar desempenho entre transportadoras e regiões;
7. relacionar atraso, prazo real e avaliação do cliente;
8. avaliar o papel de campanhas, canais e eventos externos;
9. preservar as mesmas definições de métricas em todas as áreas;
10. manter a reconciliação entre SQL e DAX nas etapas futuras.

---

## 9. Próxima etapa

A próxima etapa do Customer Analytics Hub será a análise Comercial.

Ela utilizará as mesmas dimensões, tabelas-fato e métricas canônicas da EDA geral, aprofundando questões relacionadas a:

- comportamento de compra;
- recorrência;
- ticket médio;
- clientes;
- produtos;
- categorias;
- campanhas;
- canais;
- sazonalidade;
- oportunidades de crescimento.

---

## 10. Conclusão executiva

A EDA geral consolidou uma visão confiável do desempenho do negócio e validou a integração entre arquitetura de dados, SQL Server, Power BI e DAX.

O principal resultado não é apenas o dashboard, mas a criação de uma base analítica consistente, reconciliada e reutilizável.

A etapa estabelece um ponto de partida seguro para análises mais profundas e para a produção de recomendações orientadas às necessidades específicas das áreas Comercial, Financeira, Logística e de Marketing.