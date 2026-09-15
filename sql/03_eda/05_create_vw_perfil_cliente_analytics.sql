USE [CustomerAnalyticsHub];
GO

/* ============================================================
   VIEW ANALÍTICA DO CLIENTE
   Grão: uma linha por Cliente_SK.
   Período observado: 2025-01-01 a 2025-12-31.
   Agregações são feitas separadamente antes das junções.
   ============================================================ */

CREATE OR ALTER VIEW eda.vw_perfil_cliente_analytics
AS
WITH Pedido_Cliente AS
(
    SELECT
        FP.Cliente_SK,
        COUNT_BIG(*) AS Total_Pedidos_Calculado,
        SUM(FP.Quantidade_Total_Itens) AS Total_Itens_Comprados,
        SUM(FP.Valor_Bruto_Pedido) AS Valor_Bruto_Total,
        SUM(FP.Valor_Desconto_Pedido) AS Valor_Desconto_Total,
        SUM(FP.Valor_Liquido_Pedido) AS Valor_Total_Gasto,
        SUM(FP.Custo_Total_Pedido) AS Custo_Total,
        SUM(FP.Margem_Bruta_Pedido) AS Margem_Bruta_Total,
        AVG(CONVERT(FLOAT, FP.Valor_Liquido_Pedido)) AS Ticket_Medio_Calculado,
        MIN(FP.Data_Hora_Compra) AS Primeira_Compra,
        MAX(FP.Data_Hora_Compra) AS Ultima_Compra,
        DATEDIFF
        (
            DAY,
            CONVERT(DATE, MAX(FP.Data_Hora_Compra)),
            DATEFROMPARTS(2025,12,31)
        ) AS Recencia_Dias_Calculada
    FROM gold.fato_pedido AS FP
    GROUP BY FP.Cliente_SK
),
Item_Cliente AS
(
    SELECT
        FI.Cliente_SK,
        COUNT_BIG(*) AS Total_Linhas_Item,
        COUNT(DISTINCT FI.Produto_SK) AS Produtos_Distintos_Comprados,
        COUNT(DISTINCT P.Categoria_Item) AS Categorias_Distintas_Compradas
    FROM gold.fato_item_pedido AS FI
    INNER JOIN gold.dim_produto AS P
        ON P.Produto_SK = FI.Produto_SK
    GROUP BY FI.Cliente_SK
),
Categoria_Cliente_Base AS
(
    SELECT
        FI.Cliente_SK,
        P.Categoria_Item,
        COUNT(DISTINCT FI.Pedido_ID) AS Pedidos_Categoria,
        SUM(FI.Quantidade) AS Unidades_Categoria,
        SUM(FI.Valor_Compra) AS Receita_Categoria
    FROM gold.fato_item_pedido AS FI
    INNER JOIN gold.dim_produto AS P
        ON P.Produto_SK = FI.Produto_SK
    GROUP BY FI.Cliente_SK, P.Categoria_Item
),
Categoria_Cliente_Ranking AS
(
    SELECT
        B.*,
        ROW_NUMBER() OVER
        (
            PARTITION BY B.Cliente_SK
            ORDER BY
                B.Pedidos_Categoria DESC,
                B.Unidades_Categoria DESC,
                B.Receita_Categoria DESC,
                B.Categoria_Item
        ) AS Posicao
    FROM Categoria_Cliente_Base AS B
),
Categoria_Favorita AS
(
    SELECT
        Cliente_SK,
        Categoria_Item AS Categoria_Favorita_Observada,
        Pedidos_Categoria AS Pedidos_Categoria_Favorita,
        Unidades_Categoria AS Unidades_Categoria_Favorita,
        Receita_Categoria AS Receita_Categoria_Favorita
    FROM Categoria_Cliente_Ranking
    WHERE Posicao = 1
),
Entrega_Cliente AS
(
    SELECT
        FE.Cliente_SK,
        COUNT_BIG(*) AS Total_Entregas,
        SUM(CASE WHEN FE.Status_Entrega_Calculado = 'Atrasada'
                 THEN 1 ELSE 0 END) AS Entregas_Atrasadas,
        AVG(CONVERT(FLOAT, FE.Prazo_Entrega_Real_Dias)) AS Prazo_Real_Medio_Dias,
        AVG(CONVERT(FLOAT, FE.Frete)) AS Frete_Medio,
        AVG(CONVERT(FLOAT, FE.Avaliacao_Cliente)) AS Avaliacao_Media,
        AVG(CASE WHEN FE.Dias_Atraso > 0
                 THEN CONVERT(FLOAT, FE.Dias_Atraso) END) AS Atraso_Medio_Quando_Atrasada,
        SUM(CASE WHEN FE.Frete_Gratis = 1 THEN 1 ELSE 0 END) AS Entregas_Frete_Gratis
    FROM gold.fato_entrega AS FE
    GROUP BY FE.Cliente_SK
),
Ultima_Posicao_Mensal AS
(
    SELECT
        FCM.*,
        ROW_NUMBER() OVER
        (
            PARTITION BY FCM.Cliente_SK
            ORDER BY FCM.Data_Corte_SK DESC
        ) AS Posicao
    FROM gold.fato_cliente_mes AS FCM
)
SELECT
    C.Cliente_SK,
    C.Cliente_ID,

    /* Perfil cadastral e socioeconômico */
    C.Genero,
    C.Idade,
    C.Estado_Civil,
    C.Escolaridade,
    C.Situacao_Profissional,
    C.Profissao,
    C.Tempo_Experiencia_Anos,
    C.Renda_Mensal_Cliente,

    /* Atributos informados pela fonte */
    C.Ciclo_Vida_Informado,
    C.Intervalo_Medio_Informado,
    C.Categoria_Favorita_Informada,
    C.Pagamento_Preferido_Informado,
    C.Dia_Semana_Preferido_Informado,
    C.Ticket_Medio_Informado,

    /* Geografia */
    G.Geografia_SK,
    G.Cidade,
    G.Estado,
    G.Regiao,
    G.Pais,

    /* Métricas transacionais calculadas */
    COALESCE(PC.Total_Pedidos_Calculado, 0) AS Total_Pedidos_Calculado,
    COALESCE(PC.Total_Itens_Comprados, 0) AS Total_Itens_Comprados,
    COALESCE(IC.Total_Linhas_Item, 0) AS Total_Linhas_Item,
    COALESCE(IC.Produtos_Distintos_Comprados, 0) AS Produtos_Distintos_Comprados,
    COALESCE(IC.Categorias_Distintas_Compradas, 0) AS Categorias_Distintas_Compradas,
    COALESCE(PC.Valor_Bruto_Total, 0) AS Valor_Bruto_Total,
    COALESCE(PC.Valor_Desconto_Total, 0) AS Valor_Desconto_Total,
    COALESCE(PC.Valor_Total_Gasto, 0) AS Valor_Total_Gasto,
    COALESCE(PC.Custo_Total, 0) AS Custo_Total,
    COALESCE(PC.Margem_Bruta_Total, 0) AS Margem_Bruta_Total,
    PC.Ticket_Medio_Calculado,
    CASE
        WHEN PC.Valor_Total_Gasto <> 0
            THEN PC.Margem_Bruta_Total / PC.Valor_Total_Gasto
    END AS Margem_Percentual_Ponderada,
    PC.Primeira_Compra,
    PC.Ultima_Compra,
    PC.Recencia_Dias_Calculada,

    /* Preferência observada — maior número de pedidos por categoria */
    CF.Categoria_Favorita_Observada,
    CF.Pedidos_Categoria_Favorita,
    CF.Unidades_Categoria_Favorita,
    CF.Receita_Categoria_Favorita,

    /* Logística e satisfação */
    COALESCE(EC.Total_Entregas, 0) AS Total_Entregas,
    COALESCE(EC.Entregas_Atrasadas, 0) AS Entregas_Atrasadas,
    CASE
        WHEN EC.Total_Entregas > 0
            THEN 100.0 * EC.Entregas_Atrasadas / EC.Total_Entregas
    END AS Percentual_Entregas_Atrasadas,
    EC.Prazo_Real_Medio_Dias,
    EC.Atraso_Medio_Quando_Atrasada,
    EC.Frete_Medio,
    EC.Avaliacao_Media,
    CASE
        WHEN EC.Total_Entregas > 0
            THEN 100.0 * EC.Entregas_Frete_Gratis / EC.Total_Entregas
    END AS Percentual_Entregas_Frete_Gratis,

    /* Última posição mensal disponível */
    UPM.Data_Corte_SK AS Ultima_Data_Corte_SK,
    UPM.Recencia_Dias AS Recencia_Dias_Ultima_Posicao,
    UPM.Frequencia_Acumulada,
    UPM.Intervalo_Medio_Calculado,
    UPM.Pontos_Fidelidade_Ultimo_Observado,
    UPM.Status_Cliente_Calculado,

    DATEFROMPARTS(2025,12,31) AS Data_Referencia_Analise
FROM gold.dim_cliente AS C
INNER JOIN gold.dim_geografia AS G
    ON G.Geografia_SK = C.Geografia_SK
LEFT JOIN Pedido_Cliente AS PC
    ON PC.Cliente_SK = C.Cliente_SK
LEFT JOIN Item_Cliente AS IC
    ON IC.Cliente_SK = C.Cliente_SK
LEFT JOIN Categoria_Favorita AS CF
    ON CF.Cliente_SK = C.Cliente_SK
LEFT JOIN Entrega_Cliente AS EC
    ON EC.Cliente_SK = C.Cliente_SK
LEFT JOIN Ultima_Posicao_Mensal AS UPM
    ON UPM.Cliente_SK = C.Cliente_SK
   AND UPM.Posicao = 1;
GO


/* ============================================================
   VALIDAÇÕES DA VIEW
   Resultados esperados:
   - 330 linhas;
   - 330 clientes distintos;
   - zero Cliente_SK duplicado;
   - 2.789 pedidos;
   - diferença financeira próxima de zero.
   ============================================================ */

SELECT
    COUNT_BIG(*) AS Linhas_View,
    COUNT(DISTINCT Cliente_SK) AS Clientes_Distintos,
    CASE
        WHEN COUNT_BIG(*) = 330
         AND COUNT(DISTINCT Cliente_SK) = 330
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS Status_Granularidade
FROM eda.vw_perfil_cliente_analytics;
GO

SELECT
    COUNT_BIG(*) AS Clientes_SK_Duplicados
FROM
(
    SELECT Cliente_SK
    FROM eda.vw_perfil_cliente_analytics
    GROUP BY Cliente_SK
    HAVING COUNT(*) > 1
) AS D;
GO

SELECT
    SUM(V.Total_Pedidos_Calculado) AS Pedidos_Na_View,
    (SELECT COUNT_BIG(*) FROM gold.fato_pedido) AS Pedidos_Na_Fato,
    CAST
    (
        SUM(V.Valor_Total_Gasto)
        - (SELECT SUM(FP.Valor_Liquido_Pedido) FROM gold.fato_pedido AS FP)
        AS DECIMAL(18,2)
    ) AS Diferenca_Valor_Total,
    CASE
        WHEN SUM(V.Total_Pedidos_Calculado)
             = (SELECT COUNT_BIG(*) FROM gold.fato_pedido)
         AND ABS
             (
                 SUM(V.Valor_Total_Gasto)
                 - (SELECT SUM(FP.Valor_Liquido_Pedido)
                    FROM gold.fato_pedido AS FP)
             ) <= 0.01
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS Status_Reconciliacao
FROM eda.vw_perfil_cliente_analytics AS V;
GO
