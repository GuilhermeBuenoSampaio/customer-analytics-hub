/*
===============================================================================
CUSTOMER ANALYTICS HUB
ANÁLISE COMERCIAL — AC01 ORIGEM DO CRESCIMENTO
02 DECOMPOSIÇÃO DO CRESCIMENTO COMERCIAL
===============================================================================

Pergunta principal:
    O crescimento comercial vem de mais clientes, maior frequência de compra,
    mais itens por pedido ou maior valor realizado por item?

Métodos:
    1. Evolução mensal das métricas canônicas;
    2. Decomposição exata da receita pelo método de Shapley;
    3. Decomposição do ticket médio;
    4. Comparação entre clientes novos e recorrentes;
    5. Contribuição mensal de categorias e produtos;
    6. Validação matemática das decomposições.

Observação:
    A análise é descritiva. Os componentes explicam matematicamente a variação
    observada, mas não demonstram causalidade.

Versão:
    1.0 — 05/10/2026
===============================================================================
*/

USE CustomerAnalyticsHub;
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

/*
===============================================================================
1. EVOLUÇÃO MENSAL DOS INDICADORES COMERCIAIS
===============================================================================
*/

WITH mensal AS (
    SELECT
        d.Ano_Mes,
        COUNT(DISTINCT p.Cliente_SK) AS clientes,
        COUNT_BIG(*) AS pedidos,
        SUM(CAST(p.Quantidade_Total_Itens AS bigint)) AS itens_vendidos,
        SUM(CAST(p.Valor_Bruto_Pedido AS decimal(19, 4))) AS receita_bruta,
        SUM(CAST(p.Valor_Desconto_Pedido AS decimal(19, 4))) AS desconto,
        SUM(CAST(p.Valor_Liquido_Pedido AS decimal(19, 4))) AS receita_liquida,
        SUM(CAST(p.Custo_Total_Pedido AS decimal(19, 4))) AS custo_total,
        SUM(CAST(p.Margem_Bruta_Pedido AS decimal(19, 4))) AS margem_bruta
    FROM gold.fato_pedido AS p
    INNER JOIN gold.dim_data AS d ON d.Data_SK = p.Data_SK
    GROUP BY d.Ano_Mes
),
indicadores AS (
    SELECT
        Ano_Mes,
        clientes,
        pedidos,
        itens_vendidos,
        receita_bruta,
        desconto,
        receita_liquida,
        custo_total,
        margem_bruta,
        CAST(receita_liquida / NULLIF(pedidos, 0) AS decimal(19, 4)) AS ticket_medio,
        CAST(1.0 * pedidos / NULLIF(clientes, 0) AS decimal(19, 4)) AS frequencia,
        CAST(1.0 * itens_vendidos / NULLIF(pedidos, 0) AS decimal(19, 4)) AS itens_por_pedido,
        CAST(receita_liquida / NULLIF(itens_vendidos, 0) AS decimal(19, 4)) AS receita_por_item,
        CAST(margem_bruta / NULLIF(receita_liquida, 0) AS decimal(19, 6)) AS margem_percentual,
        CAST(desconto / NULLIF(receita_bruta, 0) AS decimal(19, 6)) AS desconto_percentual
    FROM mensal
),
comparativo AS (
    SELECT
        *,
        LAG(clientes) OVER (ORDER BY Ano_Mes) AS clientes_anterior,
        LAG(pedidos) OVER (ORDER BY Ano_Mes) AS pedidos_anterior,
        LAG(itens_vendidos) OVER (ORDER BY Ano_Mes) AS itens_anterior,
        LAG(receita_liquida) OVER (ORDER BY Ano_Mes) AS receita_anterior,
        LAG(margem_bruta) OVER (ORDER BY Ano_Mes) AS margem_anterior,
        LAG(ticket_medio) OVER (ORDER BY Ano_Mes) AS ticket_anterior
    FROM indicadores
)
SELECT
    '01_evolucao_mensal' AS bloco,
    Ano_Mes,
    clientes,
    pedidos,
    itens_vendidos,
    receita_liquida,
    ticket_medio,
    frequencia,
    itens_por_pedido,
    receita_por_item,
    margem_bruta,
    margem_percentual,
    desconto_percentual,
    receita_liquida - receita_anterior AS variacao_receita,
    CAST(
        (receita_liquida - receita_anterior) / NULLIF(receita_anterior, 0)
        AS decimal(19, 6)
    ) AS variacao_receita_percentual,
    margem_bruta - margem_anterior AS variacao_margem,
    CAST(
        (margem_bruta - margem_anterior) / NULLIF(margem_anterior, 0)
        AS decimal(19, 6)
    ) AS variacao_margem_percentual,
    clientes - clientes_anterior AS variacao_clientes,
    pedidos - pedidos_anterior AS variacao_pedidos,
    itens_vendidos - itens_anterior AS variacao_itens,
    ticket_medio - ticket_anterior AS variacao_ticket
FROM comparativo
ORDER BY Ano_Mes;
GO

/*
===============================================================================
2. DECOMPOSIÇÃO EXATA DA RECEITA: CLIENTES × FREQUÊNCIA × TICKET
===============================================================================

Identidade:
    Receita = Clientes × (Pedidos / Clientes) × (Receita / Pedidos)

O método de Shapley calcula a contribuição média de cada componente em todas
as ordens possíveis de entrada. Assim, a soma das três contribuições é igual
à variação observada da receita, sem atribuir toda a interação a um só fator.
===============================================================================
*/

WITH mensal AS (
    SELECT
        d.Ano_Mes,
        CAST(COUNT(DISTINCT p.Cliente_SK) AS decimal(28, 10)) AS clientes,
        CAST(COUNT_BIG(*) AS decimal(28, 10)) AS pedidos,
        CAST(SUM(p.Valor_Liquido_Pedido) AS decimal(28, 10)) AS receita
    FROM gold.fato_pedido AS p
    INNER JOIN gold.dim_data AS d ON d.Data_SK = p.Data_SK
    GROUP BY d.Ano_Mes
),
componentes AS (
    SELECT
        Ano_Mes,
        clientes,
        pedidos / NULLIF(clientes, 0) AS frequencia,
        receita / NULLIF(pedidos, 0) AS ticket,
        receita
    FROM mensal
),
pares AS (
    SELECT
        Ano_Mes,
        LAG(Ano_Mes) OVER (ORDER BY Ano_Mes) AS mes_anterior,
        LAG(clientes) OVER (ORDER BY Ano_Mes) AS c0,
        clientes AS c1,
        LAG(frequencia) OVER (ORDER BY Ano_Mes) AS f0,
        frequencia AS f1,
        LAG(ticket) OVER (ORDER BY Ano_Mes) AS t0,
        ticket AS t1,
        LAG(receita) OVER (ORDER BY Ano_Mes) AS r0,
        receita AS r1
    FROM componentes
),
shapley AS (
    SELECT
        *,
        (c1 - c0) * (
            (CAST(1 AS decimal(28, 10)) / 3) * f0 * t0
            + (CAST(1 AS decimal(28, 10)) / 6) * f1 * t0
            + (CAST(1 AS decimal(28, 10)) / 6) * f0 * t1
            + (CAST(1 AS decimal(28, 10)) / 3) * f1 * t1
        ) AS contribuicao_clientes,
        (f1 - f0) * (
            (CAST(1 AS decimal(28, 10)) / 3) * c0 * t0
            + (CAST(1 AS decimal(28, 10)) / 6) * c1 * t0
            + (CAST(1 AS decimal(28, 10)) / 6) * c0 * t1
            + (CAST(1 AS decimal(28, 10)) / 3) * c1 * t1
        ) AS contribuicao_frequencia,
        (t1 - t0) * (
            (CAST(1 AS decimal(28, 10)) / 3) * c0 * f0
            + (CAST(1 AS decimal(28, 10)) / 6) * c1 * f0
            + (CAST(1 AS decimal(28, 10)) / 6) * c0 * f1
            + (CAST(1 AS decimal(28, 10)) / 3) * c1 * f1
        ) AS contribuicao_ticket
    FROM pares
    WHERE mes_anterior IS NOT NULL
)
SELECT
    '02_shapley_receita' AS bloco,
    mes_anterior,
    Ano_Mes,
    CAST(r0 AS decimal(19, 2)) AS receita_anterior,
    CAST(r1 AS decimal(19, 2)) AS receita_atual,
    CAST(r1 - r0 AS decimal(19, 2)) AS variacao_receita,
    CAST(contribuicao_clientes AS decimal(19, 2)) AS contribuicao_clientes,
    CAST(contribuicao_frequencia AS decimal(19, 2)) AS contribuicao_frequencia,
    CAST(contribuicao_ticket AS decimal(19, 2)) AS contribuicao_ticket,
    CAST(
        contribuicao_clientes + contribuicao_frequencia + contribuicao_ticket
        AS decimal(19, 2)
    ) AS variacao_explicada,
    CAST(
        (r1 - r0)
        - (contribuicao_clientes + contribuicao_frequencia + contribuicao_ticket)
        AS decimal(19, 4)
    ) AS residuo_matematico,
    CASE
        WHEN ABS(
            (r1 - r0)
            - (contribuicao_clientes + contribuicao_frequencia + contribuicao_ticket)
        ) <= 0.01 THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS status_validacao
FROM shapley
ORDER BY Ano_Mes;
GO

/*
===============================================================================
3. DECOMPOSIÇÃO DO TICKET: ITENS POR PEDIDO × RECEITA POR ITEM
===============================================================================

Identidade:
    Ticket médio = Itens por pedido × Receita líquida por item

Para dois componentes, a interação é dividida igualmente entre eles.
===============================================================================
*/

WITH mensal AS (
    SELECT
        d.Ano_Mes,
        CAST(COUNT_BIG(*) AS decimal(28, 10)) AS pedidos,
        CAST(SUM(p.Quantidade_Total_Itens) AS decimal(28, 10)) AS itens,
        CAST(SUM(p.Valor_Liquido_Pedido) AS decimal(28, 10)) AS receita
    FROM gold.fato_pedido AS p
    INNER JOIN gold.dim_data AS d ON d.Data_SK = p.Data_SK
    GROUP BY d.Ano_Mes
),
componentes AS (
    SELECT
        Ano_Mes,
        itens / NULLIF(pedidos, 0) AS itens_por_pedido,
        receita / NULLIF(itens, 0) AS receita_por_item,
        receita / NULLIF(pedidos, 0) AS ticket
    FROM mensal
),
pares AS (
    SELECT
        Ano_Mes,
        LAG(Ano_Mes) OVER (ORDER BY Ano_Mes) AS mes_anterior,
        LAG(itens_por_pedido) OVER (ORDER BY Ano_Mes) AS q0,
        itens_por_pedido AS q1,
        LAG(receita_por_item) OVER (ORDER BY Ano_Mes) AS p0,
        receita_por_item AS p1,
        LAG(ticket) OVER (ORDER BY Ano_Mes) AS t0,
        ticket AS t1
    FROM componentes
),
decomposicao AS (
    SELECT
        *,
        (q1 - q0) * ((p0 + p1) / 2) AS contribuicao_itens_por_pedido,
        (p1 - p0) * ((q0 + q1) / 2) AS contribuicao_receita_por_item
    FROM pares
    WHERE mes_anterior IS NOT NULL
)
SELECT
    '03_decomposicao_ticket' AS bloco,
    mes_anterior,
    Ano_Mes,
    CAST(t0 AS decimal(19, 2)) AS ticket_anterior,
    CAST(t1 AS decimal(19, 2)) AS ticket_atual,
    CAST(t1 - t0 AS decimal(19, 2)) AS variacao_ticket,
    CAST(contribuicao_itens_por_pedido AS decimal(19, 2)) AS contribuicao_itens_por_pedido,
    CAST(contribuicao_receita_por_item AS decimal(19, 2)) AS contribuicao_receita_por_item,
    CAST(
        contribuicao_itens_por_pedido + contribuicao_receita_por_item
        AS decimal(19, 2)
    ) AS variacao_explicada,
    CAST(
        (t1 - t0)
        - (contribuicao_itens_por_pedido + contribuicao_receita_por_item)
        AS decimal(19, 4)
    ) AS residuo_matematico,
    CASE
        WHEN ABS(
            (t1 - t0)
            - (contribuicao_itens_por_pedido + contribuicao_receita_por_item)
        ) <= 0.01 THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS status_validacao
FROM decomposicao
ORDER BY Ano_Mes;
GO

/*
===============================================================================
4. CLIENTES NOVOS E RECORRENTES POR MÊS
===============================================================================

Regra:
    Novo       = primeira compra histórica no mesmo mês analisado;
    Recorrente = primeira compra histórica anterior ao mês analisado.

Todos os pedidos de um cliente no mês de entrada pertencem ao grupo Novo.
===============================================================================
*/

WITH pedidos_base AS (
    SELECT
        p.Pedido_ID,
        p.Cliente_SK,
        d.Data_Completa,
        d.Ano_Mes,
        p.Quantidade_Total_Itens,
        p.Valor_Liquido_Pedido,
        p.Margem_Bruta_Pedido
    FROM gold.fato_pedido AS p
    INNER JOIN gold.dim_data AS d ON d.Data_SK = p.Data_SK
),
primeira_compra AS (
    SELECT
        Cliente_SK,
        MIN(Data_Completa) AS data_primeira_compra
    FROM pedidos_base
    GROUP BY Cliente_SK
),
classificada AS (
    SELECT
        b.*,
        CASE
            WHEN YEAR(p.data_primeira_compra) * 100 + MONTH(p.data_primeira_compra) = b.Ano_Mes
                THEN 'Novo'
            ELSE 'Recorrente'
        END AS tipo_cliente_mes
    FROM pedidos_base AS b
    INNER JOIN primeira_compra AS p ON p.Cliente_SK = b.Cliente_SK
)
SELECT
    '04_novos_recorrentes' AS bloco,
    Ano_Mes,
    tipo_cliente_mes,
    COUNT(DISTINCT Cliente_SK) AS clientes,
    COUNT_BIG(*) AS pedidos,
    SUM(CAST(Quantidade_Total_Itens AS bigint)) AS itens_vendidos,
    SUM(CAST(Valor_Liquido_Pedido AS decimal(19, 2))) AS receita_liquida,
    SUM(CAST(Margem_Bruta_Pedido AS decimal(19, 2))) AS margem_bruta,
    CAST(
        SUM(Valor_Liquido_Pedido) / NULLIF(COUNT_BIG(*), 0)
        AS decimal(19, 2)
    ) AS ticket_medio,
    CAST(
        SUM(Margem_Bruta_Pedido) / NULLIF(SUM(Valor_Liquido_Pedido), 0)
        AS decimal(19, 6)
    ) AS margem_percentual
FROM classificada
GROUP BY Ano_Mes, tipo_cliente_mes
ORDER BY Ano_Mes, tipo_cliente_mes;
GO

/*
===============================================================================
5. PARTICIPAÇÃO DE NOVOS E RECORRENTES NA RECEITA MENSAL
===============================================================================
*/

WITH pedidos_base AS (
    SELECT
        p.Cliente_SK,
        d.Data_Completa,
        d.Ano_Mes,
        p.Valor_Liquido_Pedido,
        p.Margem_Bruta_Pedido
    FROM gold.fato_pedido AS p
    INNER JOIN gold.dim_data AS d ON d.Data_SK = p.Data_SK
),
primeira_compra AS (
    SELECT Cliente_SK, MIN(Data_Completa) AS data_primeira_compra
    FROM pedidos_base
    GROUP BY Cliente_SK
),
mensal_grupo AS (
    SELECT
        b.Ano_Mes,
        CASE
            WHEN YEAR(p.data_primeira_compra) * 100 + MONTH(p.data_primeira_compra) = b.Ano_Mes
                THEN 'Novo'
            ELSE 'Recorrente'
        END AS tipo_cliente_mes,
        SUM(CAST(b.Valor_Liquido_Pedido AS decimal(19, 4))) AS receita,
        SUM(CAST(b.Margem_Bruta_Pedido AS decimal(19, 4))) AS margem
    FROM pedidos_base AS b
    INNER JOIN primeira_compra AS p ON p.Cliente_SK = b.Cliente_SK
    GROUP BY
        b.Ano_Mes,
        CASE
            WHEN YEAR(p.data_primeira_compra) * 100 + MONTH(p.data_primeira_compra) = b.Ano_Mes
                THEN 'Novo'
            ELSE 'Recorrente'
        END
)
SELECT
    '05_participacao_novos_recorrentes' AS bloco,
    Ano_Mes,
    tipo_cliente_mes,
    receita,
    CAST(
        receita / NULLIF(SUM(receita) OVER (PARTITION BY Ano_Mes), 0)
        AS decimal(19, 6)
    ) AS participacao_receita,
    margem,
    CAST(
        margem / NULLIF(SUM(margem) OVER (PARTITION BY Ano_Mes), 0)
        AS decimal(19, 6)
    ) AS participacao_margem
FROM mensal_grupo
ORDER BY Ano_Mes, tipo_cliente_mes;
GO

/*
===============================================================================
6. CONTRIBUIÇÃO MENSAL DAS CATEGORIAS
===============================================================================
*/

WITH categoria_mensal AS (
    SELECT
        d.Ano_Mes,
        pr.Categoria_Item,
        SUM(CAST(i.Quantidade AS bigint)) AS itens_vendidos,
        SUM(CAST(i.Valor_Compra AS decimal(19, 4))) AS receita_liquida,
        SUM(CAST(i.Margem_Bruta_Item AS decimal(19, 4))) AS margem_bruta
    FROM gold.fato_item_pedido AS i
    INNER JOIN gold.dim_data AS d ON d.Data_SK = i.Data_SK
    INNER JOIN gold.dim_produto AS pr ON pr.Produto_SK = i.Produto_SK
    GROUP BY d.Ano_Mes, pr.Categoria_Item
)
SELECT
    '06_categoria_mensal' AS bloco,
    Ano_Mes,
    Categoria_Item,
    itens_vendidos,
    receita_liquida,
    CAST(
        receita_liquida
        / NULLIF(SUM(receita_liquida) OVER (PARTITION BY Ano_Mes), 0)
        AS decimal(19, 6)
    ) AS participacao_receita,
    margem_bruta,
    CAST(
        margem_bruta
        / NULLIF(SUM(margem_bruta) OVER (PARTITION BY Ano_Mes), 0)
        AS decimal(19, 6)
    ) AS participacao_margem,
    CAST(
        margem_bruta / NULLIF(receita_liquida, 0)
        AS decimal(19, 6)
    ) AS margem_percentual
FROM categoria_mensal
ORDER BY Ano_Mes, receita_liquida DESC;
GO

/*
===============================================================================
7. CONTRIBUIÇÃO MENSAL DOS PRODUTOS E VARIAÇÃO DA RECEITA
===============================================================================
*/

WITH produto_mensal AS (
    SELECT
        d.Ano_Mes,
        pr.Id_Item,
        pr.Produto,
        pr.Categoria_Item,
        SUM(CAST(i.Quantidade AS bigint)) AS quantidade,
        SUM(CAST(i.Valor_Compra AS decimal(19, 4))) AS receita,
        SUM(CAST(i.Margem_Bruta_Item AS decimal(19, 4))) AS margem
    FROM gold.fato_item_pedido AS i
    INNER JOIN gold.dim_data AS d ON d.Data_SK = i.Data_SK
    INNER JOIN gold.dim_produto AS pr ON pr.Produto_SK = i.Produto_SK
    GROUP BY d.Ano_Mes, pr.Id_Item, pr.Produto, pr.Categoria_Item
),
comparativo AS (
    SELECT
        *,
        LAG(quantidade) OVER (PARTITION BY Id_Item ORDER BY Ano_Mes) AS quantidade_anterior,
        LAG(receita) OVER (PARTITION BY Id_Item ORDER BY Ano_Mes) AS receita_anterior,
        LAG(margem) OVER (PARTITION BY Id_Item ORDER BY Ano_Mes) AS margem_anterior
    FROM produto_mensal
)
SELECT
    '07_produto_mensal' AS bloco,
    Ano_Mes,
    Id_Item,
    Produto,
    Categoria_Item,
    quantidade,
    receita,
    margem,
    CAST(margem / NULLIF(receita, 0) AS decimal(19, 6)) AS margem_percentual,
    quantidade - quantidade_anterior AS variacao_quantidade,
    receita - receita_anterior AS variacao_receita,
    margem - margem_anterior AS variacao_margem
FROM comparativo
ORDER BY Ano_Mes, receita DESC;
GO

/*
===============================================================================
8. MESES COM CRESCIMENTO DE RECEITA E QUEDA DE MARGEM PERCENTUAL
===============================================================================
*/

WITH mensal AS (
    SELECT
        d.Ano_Mes,
        SUM(CAST(p.Valor_Liquido_Pedido AS decimal(19, 4))) AS receita,
        SUM(CAST(p.Margem_Bruta_Pedido AS decimal(19, 4))) AS margem
    FROM gold.fato_pedido AS p
    INNER JOIN gold.dim_data AS d ON d.Data_SK = p.Data_SK
    GROUP BY d.Ano_Mes
),
indicadores AS (
    SELECT
        Ano_Mes,
        receita,
        margem,
        margem / NULLIF(receita, 0) AS margem_percentual
    FROM mensal
),
comparativo AS (
    SELECT
        *,
        LAG(receita) OVER (ORDER BY Ano_Mes) AS receita_anterior,
        LAG(margem) OVER (ORDER BY Ano_Mes) AS margem_anterior,
        LAG(margem_percentual) OVER (ORDER BY Ano_Mes) AS margem_percentual_anterior
    FROM indicadores
)
SELECT
    '08_alerta_crescimento' AS bloco,
    Ano_Mes,
    receita_anterior,
    receita,
    receita - receita_anterior AS variacao_receita,
    margem_anterior,
    margem,
    margem - margem_anterior AS variacao_margem,
    margem_percentual_anterior,
    margem_percentual,
    margem_percentual - margem_percentual_anterior AS variacao_margem_percentual,
    CASE
        WHEN receita > receita_anterior
         AND margem_percentual < margem_percentual_anterior
            THEN 'RECEITA_CRESCE_MARGEM_PERCENTUAL_CAI'
        WHEN receita > receita_anterior
         AND margem > margem_anterior
            THEN 'CRESCIMENTO_COM_MARGEM_MONETARIA'
        WHEN receita < receita_anterior
            THEN 'RECEITA_EM_QUEDA'
        ELSE 'ESTAVEL_OU_MISTO'
    END AS classificacao
FROM comparativo
WHERE receita_anterior IS NOT NULL
ORDER BY Ano_Mes;
GO

/*
===============================================================================
9. RESUMO DO PERÍODO E COMPARAÇÃO PRIMEIRO × ÚLTIMO MÊS
===============================================================================
*/

WITH mensal AS (
    SELECT
        d.Ano_Mes,
        COUNT(DISTINCT p.Cliente_SK) AS clientes,
        COUNT_BIG(*) AS pedidos,
        SUM(CAST(p.Quantidade_Total_Itens AS bigint)) AS itens,
        SUM(CAST(p.Valor_Liquido_Pedido AS decimal(19, 4))) AS receita,
        SUM(CAST(p.Margem_Bruta_Pedido AS decimal(19, 4))) AS margem
    FROM gold.fato_pedido AS p
    INNER JOIN gold.dim_data AS d ON d.Data_SK = p.Data_SK
    GROUP BY d.Ano_Mes
),
limites AS (
    SELECT MIN(Ano_Mes) AS primeiro_mes, MAX(Ano_Mes) AS ultimo_mes
    FROM mensal
),
comparacao AS (
    SELECT
        p.Ano_Mes AS primeiro_mes,
        u.Ano_Mes AS ultimo_mes,
        p.clientes AS clientes_inicial,
        u.clientes AS clientes_final,
        p.pedidos AS pedidos_inicial,
        u.pedidos AS pedidos_final,
        p.itens AS itens_inicial,
        u.itens AS itens_final,
        p.receita AS receita_inicial,
        u.receita AS receita_final,
        p.margem AS margem_inicial,
        u.margem AS margem_final
    FROM limites AS l
    INNER JOIN mensal AS p ON p.Ano_Mes = l.primeiro_mes
    INNER JOIN mensal AS u ON u.Ano_Mes = l.ultimo_mes
)
SELECT
    '09_primeiro_ultimo_mes' AS bloco,
    *,
    clientes_final - clientes_inicial AS variacao_clientes,
    pedidos_final - pedidos_inicial AS variacao_pedidos,
    itens_final - itens_inicial AS variacao_itens,
    receita_final - receita_inicial AS variacao_receita,
    margem_final - margem_inicial AS variacao_margem,
    CAST(
        (receita_final - receita_inicial) / NULLIF(receita_inicial, 0)
        AS decimal(19, 6)
    ) AS variacao_receita_percentual,
    CAST(
        (margem_final - margem_inicial) / NULLIF(margem_inicial, 0)
        AS decimal(19, 6)
    ) AS variacao_margem_percentual
FROM comparacao;
GO

/*
===============================================================================
10. CRITÉRIOS DE INTERPRETAÇÃO
===============================================================================

1. Contribuição positiva de clientes:
       aumento da base compradora ajudou a elevar a receita.

2. Contribuição positiva de frequência:
       os clientes realizaram mais pedidos, em média.

3. Contribuição positiva de ticket:
       o valor médio dos pedidos aumentou.

4. Contribuição positiva de itens por pedido:
       houve ampliação da cesta em unidades.

5. Contribuição positiva de receita por item:
       houve maior valor líquido realizado por unidade, podendo envolver
       preço, desconto e mudança de mix. A causa deverá ser aprofundada.

6. Crescimento de receita com queda de margem percentual:
       sinal de atenção, não conclusão automática de perda econômica.

7. Clientes novos e recorrentes:
       crescimento dependente apenas de novos clientes pode ser menos estável;
       crescimento apoiado por recorrência sugere maior retenção comercial.

Próxima consulta prevista:
    sql/04_business/commercial/03_sustentabilidade_receita_margem.sql
===============================================================================
*/
