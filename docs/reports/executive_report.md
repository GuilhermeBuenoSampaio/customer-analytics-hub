# Relatório executivo

## Situação atual

O Customer Analytics Hub possui 14 etapa(s) tecnicamente aprovadas e documentadas.

## Entregas aprovadas

- Validação do contrato da fonte
- Materialização da Bronze
- Profiling estrutural da Bronze
- Análise de granularidade e chaves
- Investigação dos dados ausentes
- Validação de tipos, domínios e regras
- Investigação contextual das inconsistências
- Plano de tratamento e normalização
- Materialização e reconciliação da Silver
- Validação integral da qualidade da Silver
- Especificação do modelo dimensional Gold
- Materialização do modelo dimensional Gold
- Carga Gold no SQL Server
- Execução sequencial das análises SQL

## Observação

Somente resultados aprovados entram neste resumo. A EDA geral foi concluída e suas oito métricas canônicas foram reconciliadas entre SQL Server e DAX, sem diferenças identificadas.

## Indicadores validados da EDA geral

| Indicador | Resultado aprovado |
|---|---:|
| Clientes analisados | 330 |
| Pedidos | 2.789 |
| Itens vendidos | 13.375 |
| Receita líquida | R$ 289.904,66 |
| Ticket médio | R$ 103,95 |
| Margem bruta | R$ 151.248,65 |
| Avaliação média | 4,27 |
| Taxa de atraso | 9,90% |

A próxima etapa do projeto é a Análise Comercial, que reutilizará essas definições canônicas.
