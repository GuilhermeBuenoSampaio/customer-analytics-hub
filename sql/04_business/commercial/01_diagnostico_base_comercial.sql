/*
===============================================================================
CUSTOMER ANALYTICS HUB
ANÁLISE COMERCIAL — 01 DIAGNÓSTICO DA BASE COMERCIAL
===============================================================================

Objetivo:
    Validar estrutura, granularidade, relacionamentos, cobertura temporal,
    campos comerciais e métricas canônicas antes das análises AC01–AC06.

Características:
    - Somente leitura;
    - Não altera objetos permanentes;
    - Pode ser executado no SQL Server Management Studio;
    - Resultados REPROVADO devem ser investigados antes da próxima etapa.

Banco esperado:
    CustomerAnalyticsHub

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
1. EXISTÊNCIA DOS OBJETOS OBRIGATÓRIOS
===============================================================================
*/

WITH objetos_esperados AS (
    SELECT 'gold' AS schema_name, 'fato_pedido' AS object_name UNION ALL
    SELECT 'gold', 'fato_item_pedido' UNION ALL
    SELECT 'gold', 'fato_entrega' UNION ALL
    SELECT 'gold', 'fato_cliente_mes' UNION ALL
    SELECT 'gold', 'dim_cliente' UNION ALL
    SELECT 'gold', 'dim_produto' UNION ALL
    SELECT 'gold', 'dim_data' UNION ALL
    SELECT 'gold', 'dim_campanha' UNION ALL
    SELECT 'gold', 'dim_canal_marketing' UNION ALL
    SELECT 'gold', 'dim_geografia' UNION ALL
    SELECT 'gold', 'dim_evento_externo'
)
SELECT
    '01_objetos_obrigatorios' AS controle,
    CONCAT(o.schema_name, '.', o.object_name) AS objeto,
    CASE
        WHEN OBJECT_ID(CONCAT(o.schema_name, '.', o.object_name), 'U') IS NOT NULL
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS status_validacao
FROM objetos_esperados AS o
ORDER BY objeto;
GO

/*
===============================================================================
2. GRANULARIDADE E DUPLICIDADES DAS TABELAS-FATO
===============================================================================
*/

WITH validacoes AS (
    SELECT
        'gold.fato_pedido' AS tabela,
        COUNT_BIG(*) AS quantidade_linhas,
        CAST((SELECT COUNT_BIG(*)
              FROM (SELECT Pedido_ID FROM gold.fato_pedido GROUP BY Pedido_ID) AS d)
             AS bigint) AS quantidade_chaves_distintas
    FROM gold.fato_pedido

    UNION ALL

    SELECT
        'gold.fato_item_pedido',
        COUNT_BIG(*),
        CAST((SELECT COUNT_BIG(*)
              FROM (SELECT Item_Pedido_SK FROM gold.fato_item_pedido GROUP BY Item_Pedido_SK) AS d)
             AS bigint)
    FROM gold.fato_item_pedido

    UNION ALL

    SELECT
        'gold.fato_entrega',
        COUNT_BIG(*),
        CAST((SELECT COUNT_BIG(*)
              FROM (SELECT Pedido_ID FROM gold.fato_entrega GROUP BY Pedido_ID) AS d)
             AS bigint)
    FROM gold.fato_entrega

    UNION ALL

    SELECT
        'gold.fato_cliente_mes',
        COUNT_BIG(*),
        CAST((SELECT COUNT_BIG(*)
              FROM (
                  SELECT Cliente_SK, Data_Corte_SK
                  FROM gold.fato_cliente_mes
                  GROUP BY Cliente_SK, Data_Corte_SK
              ) AS d)
             AS bigint)
    FROM gold.fato_cliente_mes
)
SELECT
    '02_granularidade' AS controle,
    tabela,
    quantidade_linhas,
    quantidade_chaves_distintas,
    quantidade_linhas - quantidade_chaves_distintas AS duplicidades,
    CASE
        WHEN quantidade_linhas = quantidade_chaves_distintas THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS status_validacao
FROM validacoes
ORDER BY tabela;
GO

/*
===============================================================================
3. CONSISTÊNCIA ENTRE PEDIDO, ITEM E ENTREGA
===============================================================================
*/

WITH controles AS (
    SELECT
        'Pedidos sem itens' AS validacao,
        COUNT_BIG(*) AS quantidade_inconsistencias
    FROM gold.fato_pedido AS p
    WHERE NOT EXISTS (
        SELECT 1
        FROM gold.fato_item_pedido AS i
        WHERE i.Pedido_ID = p.Pedido_ID
    )

    UNION ALL

    SELECT
        'Itens sem pedido',
        COUNT_BIG(*)
    FROM gold.fato_item_pedido AS i
    WHERE NOT EXISTS (
        SELECT 1
        FROM gold.fato_pedido AS p
        WHERE p.Pedido_ID = i.Pedido_ID
    )

    UNION ALL

    SELECT
        'Pedidos sem entrega',
        COUNT_BIG(*)
    FROM gold.fato_pedido AS p
    WHERE NOT EXISTS (
        SELECT 1
        FROM gold.fato_entrega AS e
        WHERE e.Pedido_ID = p.Pedido_ID
    )

    UNION ALL

    SELECT
        'Entregas sem pedido',
        COUNT_BIG(*)
    FROM gold.fato_entrega AS e
    WHERE NOT EXISTS (
        SELECT 1
        FROM gold.fato_pedido AS p
        WHERE p.Pedido_ID = e.Pedido_ID
    )
)
SELECT
    '03_integridade_entre_fatos' AS controle,
    validacao,
    quantidade_inconsistencias,
    CASE
        WHEN quantidade_inconsistencias = 0 THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS status_validacao
FROM controles
ORDER BY validacao;
GO

/*
===============================================================================
4. COBERTURA DAS CHAVES DIMENSIONAIS
===============================================================================
*/

WITH controles AS (
    SELECT 'Pedido → cliente' AS relacionamento, COUNT_BIG(*) AS orfaos
    FROM gold.fato_pedido AS f
    LEFT JOIN gold.dim_cliente AS d ON d.Cliente_SK = f.Cliente_SK
    WHERE d.Cliente_SK IS NULL

    UNION ALL

    SELECT 'Pedido → data', COUNT_BIG(*)
    FROM gold.fato_pedido AS f
    LEFT JOIN gold.dim_data AS d ON d.Data_SK = f.Data_SK
    WHERE d.Data_SK IS NULL

    UNION ALL

    SELECT 'Pedido → campanha', COUNT_BIG(*)
    FROM gold.fato_pedido AS f
    LEFT JOIN gold.dim_campanha AS d ON d.Campanha_SK = f.Campanha_SK
    WHERE d.Campanha_SK IS NULL

    UNION ALL

    SELECT 'Pedido → canal', COUNT_BIG(*)
    FROM gold.fato_pedido AS f
    LEFT JOIN gold.dim_canal_marketing AS d
        ON d.Canal_Marketing_SK = f.Canal_Marketing_SK
    WHERE d.Canal_Marketing_SK IS NULL

    UNION ALL

    SELECT 'Item → produto', COUNT_BIG(*)
    FROM gold.fato_item_pedido AS f
    LEFT JOIN gold.dim_produto AS d ON d.Produto_SK = f.Produto_SK
    WHERE d.Produto_SK IS NULL

    UNION ALL

    SELECT 'Entrega → cliente', COUNT_BIG(*)
    FROM gold.fato_entrega AS f
    LEFT JOIN gold.dim_cliente AS d ON d.Cliente_SK = f.Cliente_SK
    WHERE d.Cliente_SK IS NULL
)
SELECT
    '04_chaves_dimensionais' AS controle,
    relacionamento,
    orfaos,
    CASE WHEN orfaos = 0 THEN 'APROVADO' ELSE 'REPROVADO' END AS status_validacao
FROM controles
ORDER BY relacionamento;
GO

/*
===============================================================================
5. COBERTURA TEMPORAL
===============================================================================
*/

SELECT
    '05_cobertura_temporal' AS controle,
    MIN(d.Data_Completa) AS primeira_data,
    MAX(d.Data_Completa) AS ultima_data,
    COUNT(DISTINCT d.Ano_Mes) AS meses_distintos,
    CASE
        WHEN MIN(d.Data_Completa) = CAST('2025-01-01' AS date)
         AND MAX(d.Data_Completa) = CAST('2025-12-31' AS date)
         AND COUNT(DISTINCT d.Ano_Mes) = 12
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS status_validacao
FROM gold.fato_pedido AS p
INNER JOIN gold.dim_data AS d ON d.Data_SK = p.Data_SK;
GO

/*
===============================================================================
6. NULOS EM CAMPOS COMERCIAIS OBRIGATÓRIOS
===============================================================================
*/

WITH controles AS (
    SELECT 'fato_pedido.Cliente_SK' AS campo, COUNT_BIG(*) AS nulos
    FROM gold.fato_pedido WHERE Cliente_SK IS NULL

    UNION ALL SELECT 'fato_pedido.Data_SK', COUNT_BIG(*)
    FROM gold.fato_pedido WHERE Data_SK IS NULL

    UNION ALL SELECT 'fato_pedido.Valor_Bruto_Pedido', COUNT_BIG(*)
    FROM gold.fato_pedido WHERE Valor_Bruto_Pedido IS NULL

    UNION ALL SELECT 'fato_pedido.Valor_Desconto_Pedido', COUNT_BIG(*)
    FROM gold.fato_pedido WHERE Valor_Desconto_Pedido IS NULL

    UNION ALL SELECT 'fato_pedido.Valor_Liquido_Pedido', COUNT_BIG(*)
    FROM gold.fato_pedido WHERE Valor_Liquido_Pedido IS NULL

    UNION ALL SELECT 'fato_pedido.Custo_Total_Pedido', COUNT_BIG(*)
    FROM gold.fato_pedido WHERE Custo_Total_Pedido IS NULL

    UNION ALL SELECT 'fato_pedido.Margem_Bruta_Pedido', COUNT_BIG(*)
    FROM gold.fato_pedido WHERE Margem_Bruta_Pedido IS NULL

    UNION ALL SELECT 'fato_item_pedido.Quantidade', COUNT_BIG(*)
    FROM gold.fato_item_pedido WHERE Quantidade IS NULL

    UNION ALL SELECT 'fato_item_pedido.Produto_SK', COUNT_BIG(*)
    FROM gold.fato_item_pedido WHERE Produto_SK IS NULL
)
SELECT
    '06_nulos_campos_comerciais' AS controle,
    campo,
    nulos,
    CASE WHEN nulos = 0 THEN 'APROVADO' ELSE 'REPROVADO' END AS status_validacao
FROM controles
ORDER BY campo;
GO

/*
===============================================================================
7. DOMÍNIOS DOS INCENTIVOS COMERCIAIS
===============================================================================
*/

SELECT
    '07a_pedido_com_campanha' AS controle,
    CAST(Pedido_Com_Campanha AS varchar(10)) AS valor,
    COUNT_BIG(*) AS quantidade
FROM gold.fato_pedido
GROUP BY Pedido_Com_Campanha
ORDER BY Pedido_Com_Campanha;

SELECT
    '07b_frete_gratis' AS controle,
    CAST(Frete_Gratis AS varchar(10)) AS valor,
    COUNT_BIG(*) AS quantidade
FROM gold.fato_entrega
GROUP BY Frete_Gratis
ORDER BY Frete_Gratis;

SELECT
    '07c_atraso_entrega_informado' AS controle,
    COALESCE(NULLIF(LTRIM(RTRIM(Atraso_Entrega_Informado)), ''), '<NULO_OU_VAZIO>') AS valor,
    COUNT_BIG(*) AS quantidade
FROM gold.fato_entrega
GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(Atraso_Entrega_Informado)), ''), '<NULO_OU_VAZIO>')
ORDER BY valor;
GO

/*
===============================================================================
8. CONSISTÊNCIA ARITMÉTICA DOS PEDIDOS
===============================================================================
*/

WITH controles AS (
    SELECT
        'Bruto - desconto = líquido' AS validacao,
        COUNT_BIG(*) AS divergencias
    FROM gold.fato_pedido
    WHERE ABS(
        CAST(Valor_Bruto_Pedido AS decimal(19, 4))
        - CAST(Valor_Desconto_Pedido AS decimal(19, 4))
        - CAST(Valor_Liquido_Pedido AS decimal(19, 4))
    ) > 0.01

    UNION ALL

    SELECT
        'Líquido - custo = margem bruta',
        COUNT_BIG(*)
    FROM gold.fato_pedido
    WHERE ABS(
        CAST(Valor_Liquido_Pedido AS decimal(19, 4))
        - CAST(Custo_Total_Pedido AS decimal(19, 4))
        - CAST(Margem_Bruta_Pedido AS decimal(19, 4))
    ) > 0.01
)
SELECT
    '08_consistencia_aritmetica' AS controle,
    validacao,
    divergencias,
    CASE WHEN divergencias = 0 THEN 'APROVADO' ELSE 'REPROVADO' END AS status_validacao
FROM controles
ORDER BY validacao;
GO

/*
===============================================================================
9. RECONCILIAÇÃO DOS TOTAIS ENTRE PEDIDOS E ITENS
===============================================================================
*/

WITH pedidos AS (
    SELECT
        SUM(CAST(Quantidade_Total_Itens AS bigint)) AS itens_pedidos,
        SUM(CAST(Valor_Bruto_Pedido AS decimal(19, 4))) AS bruto_pedidos,
        SUM(CAST(Valor_Desconto_Pedido AS decimal(19, 4))) AS desconto_pedidos,
        SUM(CAST(Valor_Liquido_Pedido AS decimal(19, 4))) AS liquido_pedidos,
        SUM(CAST(Custo_Total_Pedido AS decimal(19, 4))) AS custo_pedidos,
        SUM(CAST(Margem_Bruta_Pedido AS decimal(19, 4))) AS margem_pedidos
    FROM gold.fato_pedido
),
itens AS (
    SELECT
        SUM(CAST(Quantidade AS bigint)) AS itens_itens,
        SUM(CAST(Valor_Bruto_Item AS decimal(19, 4))) AS bruto_itens,
        SUM(CAST(Valor_Desconto_Item AS decimal(19, 4))) AS desconto_itens,
        SUM(CAST(Valor_Compra AS decimal(19, 4))) AS liquido_itens,
        SUM(CAST(Custo_Total_Item AS decimal(19, 4))) AS custo_itens,
        SUM(CAST(Margem_Bruta_Item AS decimal(19, 4))) AS margem_itens
    FROM gold.fato_item_pedido
),
comparacoes AS (
    SELECT 'Itens vendidos' AS metrica,
           CAST(p.itens_pedidos AS decimal(19, 4)) AS valor_pedido,
           CAST(i.itens_itens AS decimal(19, 4)) AS valor_item,
           CAST(0.0000 AS decimal(19, 4)) AS tolerancia
    FROM pedidos AS p CROSS JOIN itens AS i

    UNION ALL SELECT 'Receita bruta', p.bruto_pedidos, i.bruto_itens, 0.0100
    FROM pedidos AS p CROSS JOIN itens AS i

    UNION ALL SELECT 'Desconto', p.desconto_pedidos, i.desconto_itens, 0.0100
    FROM pedidos AS p CROSS JOIN itens AS i

    UNION ALL SELECT 'Receita líquida', p.liquido_pedidos, i.liquido_itens, 0.0100
    FROM pedidos AS p CROSS JOIN itens AS i

    UNION ALL SELECT 'Custo total', p.custo_pedidos, i.custo_itens, 0.0100
    FROM pedidos AS p CROSS JOIN itens AS i

    UNION ALL SELECT 'Margem bruta', p.margem_pedidos, i.margem_itens, 0.0100
    FROM pedidos AS p CROSS JOIN itens AS i
)
SELECT
    '09_pedidos_versus_itens' AS controle,
    metrica,
    valor_pedido,
    valor_item,
    valor_pedido - valor_item AS diferenca,
    CASE
        WHEN ABS(valor_pedido - valor_item) <= tolerancia THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS status_validacao
FROM comparacoes
ORDER BY metrica;
GO

/*
===============================================================================
10. RECONCILIAÇÃO DAS OITO MÉTRICAS CANÔNICAS
===============================================================================
*/

WITH metricas AS (
    SELECT
        'MET-EDA-001' AS id,
        'Clientes analisados' AS metrica,
        CAST(COUNT(DISTINCT Cliente_SK) AS decimal(19, 4)) AS observado,
        CAST(330 AS decimal(19, 4)) AS esperado,
        CAST(0 AS decimal(19, 4)) AS tolerancia
    FROM gold.fato_pedido

    UNION ALL

    SELECT 'MET-EDA-002', 'Pedidos',
           CAST(COUNT_BIG(*) AS decimal(19, 4)), 2789, 0
    FROM gold.fato_pedido

    UNION ALL

    SELECT 'MET-EDA-003', 'Itens vendidos',
           CAST(SUM(Quantidade) AS decimal(19, 4)), 13375, 0
    FROM gold.fato_item_pedido

    UNION ALL

    SELECT 'MET-EDA-004', 'Receita líquida',
           CAST(SUM(Valor_Liquido_Pedido) AS decimal(19, 4)), 289904.66, 0.01
    FROM gold.fato_pedido

    UNION ALL

    SELECT 'MET-EDA-005', 'Ticket médio',
           CAST(SUM(Valor_Liquido_Pedido) / NULLIF(COUNT_BIG(*), 0) AS decimal(19, 4)),
           103.95, 0.01
    FROM gold.fato_pedido

    UNION ALL

    SELECT 'MET-EDA-006', 'Margem bruta',
           CAST(SUM(Margem_Bruta_Pedido) AS decimal(19, 4)), 151248.65, 0.01
    FROM gold.fato_pedido

    UNION ALL

    SELECT 'MET-EDA-007', 'Avaliação média',
           CAST(AVG(CAST(Avaliacao_Cliente AS decimal(19, 4))) AS decimal(19, 4)),
           4.27, 0.01
    FROM gold.fato_entrega
    WHERE Avaliacao_Cliente IS NOT NULL

    UNION ALL

    SELECT 'MET-EDA-008', 'Taxa de atraso percentual',
           CAST(
               100.0 * SUM(CASE WHEN Atraso_Entrega_Informado = N'Sim' THEN 1 ELSE 0 END)
               / NULLIF(SUM(CASE
                   WHEN NULLIF(LTRIM(RTRIM(Atraso_Entrega_Informado)), '') IS NOT NULL
                   THEN 1 ELSE 0 END), 0)
               AS decimal(19, 4)
           ),
           9.90, 0.01
    FROM gold.fato_entrega
)
SELECT
    '10_metricas_canonicas' AS controle,
    id,
    metrica,
    observado,
    esperado,
    observado - esperado AS diferenca,
    CASE
        WHEN ABS(observado - esperado) <= tolerancia THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS status_validacao
FROM metricas
ORDER BY id;
GO

/*
===============================================================================
11. COBERTURA DAS VARIÁVEIS COMERCIAIS
===============================================================================
*/

SELECT
    '11_cobertura_comercial' AS controle,
    COUNT_BIG(*) AS pedidos,
    COUNT(DISTINCT Cliente_SK) AS clientes,
    COUNT(DISTINCT Campanha_SK) AS campanhas_distintas,
    COUNT(DISTINCT Canal_Marketing_SK) AS canais_distintos,
    SUM(CASE WHEN Pedido_Com_Campanha = 1 THEN 1 ELSE 0 END) AS pedidos_com_campanha,
    SUM(CASE WHEN Valor_Desconto_Pedido > 0 THEN 1 ELSE 0 END) AS pedidos_com_desconto,
    MIN(Desconto_Medio_Ponderado) AS desconto_minimo,
    MAX(Desconto_Medio_Ponderado) AS desconto_maximo,
    AVG(CAST(Desconto_Medio_Ponderado AS decimal(19, 4))) AS desconto_medio,
    MIN(Margem_Percentual_Pedido) AS margem_percentual_minima,
    MAX(Margem_Percentual_Pedido) AS margem_percentual_maxima,
    AVG(CAST(Margem_Percentual_Pedido AS decimal(19, 4))) AS margem_percentual_media
FROM gold.fato_pedido;

SELECT
    '11b_cobertura_frete' AS controle,
    COUNT_BIG(*) AS entregas,
    SUM(CASE WHEN Frete_Gratis = 1 THEN 1 ELSE 0 END) AS entregas_com_frete_gratis,
    MIN(Frete) AS frete_minimo,
    MAX(Frete) AS frete_maximo,
    AVG(CAST(Frete AS decimal(19, 4))) AS frete_medio
FROM gold.fato_entrega;
GO

/*
===============================================================================
12. RESUMO FINAL DO DIAGNÓSTICO
===============================================================================

Critério de continuidade:
    - Todos os controles estruturais devem estar APROVADOS;
    - As métricas canônicas devem permanecer reconciliadas;
    - Domínios e coberturas devem ser revisados antes das comparações;
    - Qualquer REPROVADO deverá ser documentado e corrigido.

Próxima consulta prevista:
    sql/04_business/commercial/02_decomposicao_crescimento_comercial.sql
===============================================================================
*/
