USE [CustomerAnalyticsHub];
GO

-- ==============================================================================
-- 10. ANÁLISE COMERCIAL INTEGRADAS AO LTV PREDITIVO
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- PARTE 1: CURVA ABC DE CATEGORIAS POR SEGMENTO PREDITIVO (TOP VS BOTTOM LTV)
-- ------------------------------------------------------------------------------
WITH SegmentosLTV AS (
    SELECT 
        Cliente_SK,
        LTV_Preditivo_Estimado,
        NTILE(4) OVER (ORDER BY LTV_Preditivo_Estimado DESC) AS Quartil_LTV -- 1 = Top LTV, 4 = Baixo LTV
    FROM eda.stg_resultados_preditivos_geral
)
SELECT 
    CASE WHEN s.Quartil_LTV = 1 THEN 'Top 25% Preditivo (Alta Valia)'
         WHEN s.Quartil_LTV = 4 THEN 'Bottom 25% Preditivo (Baixa Valia)'
         ELSE 'Medio LTV' END                             AS Segmento_Cliente,
    p.Categoria_Item,
    COUNT(DISTINCT fp.Pedido_ID)                        AS Total_Pedidos,
    SUM(fip.Quantidade)                                 AS Itens_Vendidos,
    ROUND(SUM(fip.Valor_Compra), 2)                     AS Receita_Total_Categoria,
    ROUND(AVG(fip.Preco_Unitario_Lista), 2)             AS Preco_Medio_Item
FROM eda.stg_resultados_preditivos_geral g
INNER JOIN SegmentosLTV s              ON g.Cliente_SK = s.Cliente_SK
INNER JOIN gold.fato_pedido fp         ON g.Cliente_SK = fp.Cliente_SK
INNER JOIN gold.fato_item_pedido fip    ON fp.Pedido_ID = fip.Pedido_ID
INNER JOIN gold.dim_produto p          ON fip.Produto_SK = p.Produto_SK
WHERE s.Quartil_LTV IN (1, 4) -- Compara apenas os extremos
GROUP BY 
    CASE WHEN s.Quartil_LTV = 1 THEN 'Top 25% Preditivo (Alta Valia)'
         WHEN s.Quartil_LTV = 4 THEN 'Bottom 25% Preditivo (Baixa Valia)'
         ELSE 'Medio LTV' END,
    p.Categoria_Item
ORDER BY Segmento_Cliente, Receita_Total_Categoria DESC;

-- ------------------------------------------------------------------------------
-- PARTE 2: ANÁLISE DE MIX E PENETRAÇÃO DE PRODUTOS
-- ------------------------------------------------------------------------------
SELECT 
    p.Categoria_Item,
    COUNT(DISTINCT fip.Produto_SK)                       AS SKUs_Ativos_Vendidos,
    SUM(fip.Quantidade)                                 AS Total_Unidades_Vendidas,
    ROUND(SUM(fip.Valor_Compra), 2)                     AS Faturamento_Liquido,
    ROUND(SUM(fip.Valor_Desconto_Item), 2)              AS Total_Descontos_Concedidos,
    ROUND(AVG(fip.Desconto_Percentual) * 100, 2)        AS Desconto_Medio_Pct,
    ROUND(SUM(fip.Margem_Bruta_Item), 2)                AS Margem_Bruta_Total,
    ROUND(AVG(fip.Margem_Percentual_Item) * 100, 2)     AS Margem_Percentual_Media
FROM gold.fato_item_pedido fip
INNER JOIN gold.dim_produto p ON fip.Produto_SK = p.Produto_SK
GROUP BY p.Categoria_Item
ORDER BY Faturamento_Liquido DESC;