/*
===============================================================================
PROJETO: Customer Analytics Hub
ETAPA: EDA Geral
ARQUIVO: 12_reconciliacao_metricas_eda_geral.sql
OBJETIVO: Reconciliar as métricas canônicas calculadas no SQL Server com as
          medidas DAX utilizadas no dashboard da EDA geral.
BANCO: CustomerAnalyticsHub
===============================================================================
*/

USE CustomerAnalyticsHub;
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

/*
===============================================================================
1. VALIDAÇÃO DA GRANULARIDADE DAS TABELAS-FATO
===============================================================================
*/

SELECT
    'gold.fato_pedido' AS tabela,
    COUNT(*) AS quantidade_linhas,
    COUNT(DISTINCT Pedido_ID) AS quantidade_chaves_distintas,
    COUNT(*) - COUNT(DISTINCT Pedido_ID) AS duplicidades
FROM gold.fato_pedido

UNION ALL

SELECT
    'gold.fato_item_pedido',
    COUNT(*),
    COUNT(DISTINCT Item_Pedido_SK),
    COUNT(*) - COUNT(DISTINCT Item_Pedido_SK)
FROM gold.fato_item_pedido

UNION ALL

SELECT
    'gold.fato_entrega',
    COUNT(*),
    COUNT(DISTINCT Entrega_SK),
    COUNT(*) - COUNT(DISTINCT Entrega_SK)
FROM gold.fato_entrega;
GO

/*
===============================================================================
2. VALORES OBSERVADOS NO CAMPO DE ATRASO

Esta verificação confirma quais valores textuais serão convertidos pelo
Power Query para verdadeiro, falso ou nulo.
===============================================================================
*/

SELECT
    Atraso_Entrega_Informado,
    COUNT(*) AS quantidade_registros
FROM gold.fato_entrega
GROUP BY Atraso_Entrega_Informado
ORDER BY Atraso_Entrega_Informado;
GO

/*
===============================================================================
3. MÉTRICAS CONSOLIDADAS DA EDA GERAL

Definições equivalentes às medidas DAX:

01. Clientes Analisados
02. Pedidos
03. Itens Vendidos
04. Receita Líquida
05. Ticket Médio
06. Margem Bruta
07. Avaliação Média
08. Taxa de Atraso
===============================================================================
*/

WITH metricas_pedido AS
(
    SELECT
        COUNT(DISTINCT Cliente_SK) AS clientes_analisados,
        COUNT(*) AS pedidos,
        SUM(Valor_Liquido_Pedido) AS receita_liquida,
        SUM(Margem_Bruta_Pedido) AS margem_bruta
    FROM gold.fato_pedido
),
metricas_item AS
(
    SELECT
        SUM(Quantidade) AS itens_vendidos
    FROM gold.fato_item_pedido
),
metricas_entrega AS
(
    SELECT
        AVG(
            CAST(Avaliacao_Cliente AS decimal(19,6))
        ) AS avaliacao_media,

        SUM(
            CASE
                WHEN LOWER(LTRIM(RTRIM(Atraso_Entrega_Informado)))
                     IN ('true', '1', 'sim', 'yes')
                THEN 1
                ELSE 0
            END
        ) AS entregas_atrasadas,

        SUM(
            CASE
                WHEN Atraso_Entrega_Informado IS NOT NULL
                 AND LTRIM(RTRIM(Atraso_Entrega_Informado)) <> ''
                THEN 1
                ELSE 0
            END
        ) AS entregas_com_informacao
    FROM gold.fato_entrega
)
SELECT
    mp.clientes_analisados AS Clientes_Analisados,
    mp.pedidos AS Pedidos,
    mi.itens_vendidos AS Itens_Vendidos,

    CAST(
        mp.receita_liquida
        AS decimal(19,2)
    ) AS Receita_Liquida,

    CAST(
        COALESCE(
            mp.receita_liquida / NULLIF(mp.pedidos, 0),
            0
        )
        AS decimal(19,2)
    ) AS Ticket_Medio,

    CAST(
        mp.margem_bruta
        AS decimal(19,2)
    ) AS Margem_Bruta,

    CAST(
        me.avaliacao_media
        AS decimal(19,2)
    ) AS Avaliacao_Media,

    CAST(
        COALESCE(
            CAST(me.entregas_atrasadas AS decimal(19,6))
            / NULLIF(me.entregas_com_informacao, 0),
            0
        )
        AS decimal(19,6)
    ) AS Taxa_Atraso_Decimal,

    CAST(
        COALESCE(
            CAST(me.entregas_atrasadas AS decimal(19,6))
            / NULLIF(me.entregas_com_informacao, 0),
            0
        ) * 100
        AS decimal(19,2)
    ) AS Taxa_Atraso_Percentual,

    me.entregas_atrasadas AS Entregas_Atrasadas,
    me.entregas_com_informacao AS Entregas_Com_Informacao
FROM metricas_pedido AS mp
CROSS JOIN metricas_item AS mi
CROSS JOIN metricas_entrega AS me;
GO

/*
===============================================================================
4. RESULTADOS MENSAIS

A dimensão gold.dim_data é utilizada como fonte temporal, preservando a mesma
lógica de filtro aplicada pela segmentação do Power BI.
===============================================================================
*/

WITH pedidos_mes AS
(
    SELECT
        d.Ano_Mes,
        COUNT(DISTINCT fp.Cliente_SK) AS clientes_analisados,
        COUNT(*) AS pedidos,
        SUM(fp.Valor_Liquido_Pedido) AS receita_liquida,
        SUM(fp.Margem_Bruta_Pedido) AS margem_bruta
    FROM gold.fato_pedido AS fp
    INNER JOIN gold.dim_data AS d
        ON d.Data_SK = fp.Data_SK
    GROUP BY
        d.Ano_Mes
),
itens_mes AS
(
    SELECT
        d.Ano_Mes,
        SUM(fip.Quantidade) AS itens_vendidos
    FROM gold.fato_item_pedido AS fip
    INNER JOIN gold.dim_data AS d
        ON d.Data_SK = fip.Data_SK
    GROUP BY
        d.Ano_Mes
),
entregas_mes AS
(
    SELECT
        d.Ano_Mes,

        AVG(
            CAST(fe.Avaliacao_Cliente AS decimal(19,6))
        ) AS avaliacao_media,

        SUM(
            CASE
                WHEN LOWER(LTRIM(RTRIM(fe.Atraso_Entrega_Informado)))
                     IN ('true', '1', 'sim', 'yes')
                THEN 1
                ELSE 0
            END
        ) AS entregas_atrasadas,

        SUM(
            CASE
                WHEN fe.Atraso_Entrega_Informado IS NOT NULL
                 AND LTRIM(RTRIM(fe.Atraso_Entrega_Informado)) <> ''
                THEN 1
                ELSE 0
            END
        ) AS entregas_com_informacao
    FROM gold.fato_entrega AS fe
    INNER JOIN gold.dim_data AS d
        ON d.Data_SK = fe.Data_Pedido_SK
    GROUP BY
        d.Ano_Mes
)
SELECT
    pm.Ano_Mes,
    pm.clientes_analisados AS Clientes_Analisados,
    pm.pedidos AS Pedidos,
    im.itens_vendidos AS Itens_Vendidos,

    CAST(
        pm.receita_liquida
        AS decimal(19,2)
    ) AS Receita_Liquida,

    CAST(
        COALESCE(
            pm.receita_liquida / NULLIF(pm.pedidos, 0),
            0
        )
        AS decimal(19,2)
    ) AS Ticket_Medio,

    CAST(
        pm.margem_bruta
        AS decimal(19,2)
    ) AS Margem_Bruta,

    CAST(
        em.avaliacao_media
        AS decimal(19,2)
    ) AS Avaliacao_Media,

    CAST(
        COALESCE(
            CAST(em.entregas_atrasadas AS decimal(19,6))
            / NULLIF(em.entregas_com_informacao, 0),
            0
        ) * 100
        AS decimal(19,2)
    ) AS Taxa_Atraso_Percentual
FROM pedidos_mes AS pm
LEFT JOIN itens_mes AS im
    ON im.Ano_Mes = pm.Ano_Mes
LEFT JOIN entregas_mes AS em
    ON em.Ano_Mes = pm.Ano_Mes
ORDER BY
    pm.Ano_Mes;
GO