USE [CustomerAnalyticsHub];
GO

SET NOCOUNT ON;

/* ============================================================================
   EDA GERAL DA CAMADA GOLD
   ARQUIVO 00 — PARÂMETROS, ESCOPO TEMPORAL E INDICADORES MACRO

   Tabela principal: gold.fato_pedido
   Granularidade: um registro por pedido
   ============================================================================ */


/* ============================================================================
   1. DEFINIÇÃO DOS PARÂMETROS TEMPORAIS
   ============================================================================ */

DECLARE @Data_Inicio DATE;
DECLARE @Data_Fim DATE;
DECLARE @Data_Corte DATE;
DECLARE @Quantidade_Produtos_Vendidos BIGINT;

SELECT
    @Data_Inicio = MIN(CAST(Data_Hora_Compra AS DATE)),
    @Data_Fim = MAX(CAST(Data_Hora_Compra AS DATE))
FROM gold.fato_pedido;

SET @Data_Corte = @Data_Fim;

SELECT
    @Quantidade_Produtos_Vendidos =
        COUNT(DISTINCT Produto_SK)
FROM gold.fato_item_pedido;


/* ============================================================================
   2. ESCOPO DA EDA
   ============================================================================ */

SELECT
    DB_NAME() AS banco_analisado,
    @Data_Inicio AS data_inicio_observada,
    @Data_Fim AS data_fim_observada,
    @Data_Corte AS data_corte_eda,

    DATEDIFF(
        DAY,
        @Data_Inicio,
        @Data_Fim
    ) + 1 AS quantidade_dias_calendario,

    YEAR(@Data_Inicio) AS ano_inicial,
    YEAR(@Data_Fim) AS ano_final;


/* ============================================================================
   3. INDICADORES MACRO DA GOLD
   ============================================================================ */

SELECT
    COUNT(*) AS quantidade_registros_fato_pedido,

    COUNT(DISTINCT fp.Pedido_ID)
        AS quantidade_pedidos_unicos,

    COUNT(DISTINCT fp.Cliente_SK)
        AS quantidade_clientes_com_compra,

    @Quantidade_Produtos_Vendidos
        AS quantidade_produtos_vendidos,

    SUM(fp.Quantidade_Total_Itens)
        AS quantidade_total_itens,

    ROUND(
        SUM(fp.Valor_Bruto_Pedido),
        2
    ) AS receita_bruta_total,

    ROUND(
        SUM(fp.Valor_Desconto_Pedido),
        2
    ) AS descontos_concedidos_total,

    ROUND(
        SUM(fp.Valor_Liquido_Pedido),
        2
    ) AS receita_liquida_total,

    ROUND(
        SUM(fp.Custo_Total_Pedido),
        2
    ) AS custo_total,

    ROUND(
        SUM(fp.Margem_Bruta_Pedido),
        2
    ) AS margem_bruta_total,

    ROUND(
        AVG(fp.Valor_Liquido_Pedido),
        2
    ) AS ticket_medio_por_pedido,

    ROUND(
        AVG(
            CAST(
                fp.Quantidade_Total_Itens
                AS DECIMAL(19, 6)
            )
        ),
        2
    ) AS quantidade_media_itens_por_pedido,

    ROUND(
        100.0 * SUM(fp.Valor_Desconto_Pedido)
        / NULLIF(SUM(fp.Valor_Bruto_Pedido), 0),
        2
    ) AS taxa_desconto_global_percentual,

    ROUND(
        100.0 * SUM(fp.Margem_Bruta_Pedido)
        / NULLIF(SUM(fp.Valor_Liquido_Pedido), 0),
        2
    ) AS margem_bruta_global_percentual

FROM gold.fato_pedido AS fp;