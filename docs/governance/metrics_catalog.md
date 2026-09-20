# Catálogo canônico de métricas

Este documento é a fonte única das métricas compartilhadas por EDA, comercial, financeiro, logística, marketing, SQL e Power BI.

| Métrica | Definição canônica | Granularidade | Fonte Gold | Situação |
|---|---|---|---|---|
| Receita bruta | Soma do valor dos itens antes de descontos e frete, conforme contrato Gold | Período e pedido | `fato_item_pedido` | A validar |
| Receita líquida | Receita bruta menos descontos, seguindo a regra oficial do projeto | Período e pedido | `fato_item_pedido` / `fato_pedido` | A validar |
| Ticket médio | Receita líquida dividida pela quantidade distinta de pedidos válidos | Período | `fato_pedido` | A validar |
| Clientes ativos | Clientes distintos com ao menos um pedido válido no período | Período | `fato_pedido` | A validar |
| Frequência de compra | Quantidade de pedidos válidos dividida pela quantidade de clientes compradores | Período | `fato_pedido` | A validar |
| Prazo médio de entrega | Média do prazo real somente para entregas válidas | Período e transportadora | `fato_entrega` | A validar |
| Taxa de atraso | Entregas atrasadas divididas pelas entregas concluídas e avaliáveis | Período e transportadora | `fato_entrega` | A validar |

Antes de uma métrica mudar para **Aprovada**, devem ser preenchidos: fórmula exata, filtros, tratamento de nulos, unidade, arredondamento, período, versão, responsável e reconciliação entre Python, SQL e DAX.
