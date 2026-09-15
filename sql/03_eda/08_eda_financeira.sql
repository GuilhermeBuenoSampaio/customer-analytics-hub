USE [CustomerAnalyticsHub];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

/* ============================================================================
   CUSTOMER ANALYTICS HUB
   08 — EDA FINANCEIRA

   OBJETIVO
   Examinar receita, descontos, custos dos produtos e margem bruta sob os
   principais recortes financeiros do negócio.

   GRÃOS UTILIZADOS
   - gold.fato_pedido: uma linha por pedido.
   - gold.fato_item_pedido: uma linha por item do pedido.
   - gold.fato_entrega: uma linha por entrega/pedido.

   DEFINIÇÕES
   - Receita bruta: valor antes dos descontos.
   - Receita líquida: receita bruta menos descontos comerciais.
   - Margem bruta: receita líquida menos custo dos produtos.
   - Margem percentual ponderada: soma das margens / soma da receita líquida.

   LIMITAÇÃO
   A margem bruta não representa lucro líquido. A base não disponibiliza
   impostos, taxas financeiras, despesas administrativas, custo logístico
   efetivo nem investimento de marketing. O campo Frete representa o valor
   registrado na entrega e é analisado separadamente.
   ============================================================================ */

DROP TABLE IF EXISTS #Financeiro_Pedido;
DROP TABLE IF EXISTS #Financeiro_Item;
GO

/* 1. Bases temporárias enxutas para melhorar o desempenho das consultas. */
SELECT
    FP.Pedido_SK,
    FP.Pedido_ID,
    FP.Cliente_SK,
    FP.Pagamento_SK,
    FP.Data_Hora_Compra,
    FP.Quantidade_Total_Itens,
    CONVERT(FLOAT, FP.Valor_Bruto_Pedido)       AS Receita_Bruta,
    CONVERT(FLOAT, FP.Valor_Desconto_Pedido)    AS Desconto,
    CONVERT(FLOAT, FP.Valor_Liquido_Pedido)     AS Receita_Liquida,
    CONVERT(FLOAT, FP.Custo_Total_Pedido)       AS Custo_Produtos,
    CONVERT(FLOAT, FP.Margem_Bruta_Pedido)      AS Margem_Bruta,
    CONVERT(FLOAT, FP.Margem_Percentual_Pedido) AS Margem_Percentual,
    CONVERT(FLOAT, FP.Desconto_Medio_Ponderado) AS Desconto_Percentual,
    FP.Pedido_Com_Campanha,
    FP.Cupom_Status
INTO #Financeiro_Pedido
FROM gold.fato_pedido AS FP;
GO

CREATE UNIQUE CLUSTERED INDEX IX_Financeiro_Pedido
    ON #Financeiro_Pedido (Pedido_SK);

CREATE INDEX IX_Financeiro_Pedido_Data
    ON #Financeiro_Pedido (Data_Hora_Compra);

CREATE INDEX IX_Financeiro_Pedido_Cliente
    ON #Financeiro_Pedido (Cliente_SK);
GO

SELECT
    FI.Item_Pedido_SK,
    FI.Pedido_ID,
    FI.Cliente_SK,
    FI.Produto_SK,
    CONVERT(FLOAT, FI.Quantidade)               AS Quantidade,
    CONVERT(FLOAT, FI.Valor_Bruto_Item)         AS Receita_Bruta,
    CONVERT(FLOAT, FI.Valor_Desconto_Item)      AS Desconto,
    CONVERT(FLOAT, FI.Valor_Compra)             AS Receita_Liquida,
    CONVERT(FLOAT, FI.Custo_Total_Item)         AS Custo_Produtos,
    CONVERT(FLOAT, FI.Margem_Bruta_Item)        AS Margem_Bruta,
    CONVERT(FLOAT, FI.Margem_Percentual_Item)   AS Margem_Percentual,
    CONVERT(FLOAT, FI.Desconto_Percentual)      AS Desconto_Percentual
INTO #Financeiro_Item
FROM gold.fato_item_pedido AS FI;
GO

CREATE UNIQUE CLUSTERED INDEX IX_Financeiro_Item
    ON #Financeiro_Item (Item_Pedido_SK);

CREATE INDEX IX_Financeiro_Item_Produto
    ON #Financeiro_Item (Produto_SK);

CREATE INDEX IX_Financeiro_Item_Pedido
    ON #Financeiro_Item (Pedido_ID);
GO

/* 2. Resumo financeiro geral.
   Os indicadores percentuais são ponderados pelas bases monetárias. */
SELECT
    COUNT_BIG(*) AS Pedidos,
    COUNT(DISTINCT Cliente_SK) AS Clientes_Com_Compra,
    CAST(SUM(Receita_Bruta) AS DECIMAL(18,2)) AS Receita_Bruta,
    CAST(SUM(Desconto) AS DECIMAL(18,2)) AS Descontos_Concedidos,
    CAST(SUM(Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(SUM(Custo_Produtos) AS DECIMAL(18,2)) AS Custo_Dos_Produtos,
    CAST(SUM(Margem_Bruta) AS DECIMAL(18,2)) AS Margem_Bruta,
    CAST(
        100.0 * SUM(Desconto) / NULLIF(SUM(Receita_Bruta), 0)
        AS DECIMAL(10,2)
    ) AS Desconto_Pct_Ponderado,
    CAST(
        100.0 * SUM(Margem_Bruta) / NULLIF(SUM(Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(AVG(Custo_Produtos) AS DECIMAL(18,2)) AS Custo_Medio_Pedido,
    CAST(AVG(Margem_Bruta) AS DECIMAL(18,2)) AS Margem_Media_Pedido
FROM #Financeiro_Pedido;
GO

/* 3. Evolução financeira mensal e variação da receita líquida.
   LAG compara cada mês com o mês imediatamente anterior. */
WITH Mensal AS
(
    SELECT
        DATEFROMPARTS(
            YEAR(Data_Hora_Compra),
            MONTH(Data_Hora_Compra),
            1
        ) AS Mes_Referencia,
        COUNT_BIG(*) AS Pedidos,
        COUNT(DISTINCT Cliente_SK) AS Clientes,
        SUM(Receita_Bruta) AS Receita_Bruta,
        SUM(Desconto) AS Desconto,
        SUM(Receita_Liquida) AS Receita_Liquida,
        SUM(Custo_Produtos) AS Custo_Produtos,
        SUM(Margem_Bruta) AS Margem_Bruta
    FROM #Financeiro_Pedido
    GROUP BY
        YEAR(Data_Hora_Compra),
        MONTH(Data_Hora_Compra)
),
Comparacao AS
(
    SELECT
        M.*,
        LAG(M.Receita_Liquida) OVER
            (ORDER BY M.Mes_Referencia) AS Receita_Mes_Anterior
    FROM Mensal AS M
)
SELECT
    Mes_Referencia,
    Pedidos,
    Clientes,
    CAST(Receita_Bruta AS DECIMAL(18,2)) AS Receita_Bruta,
    CAST(Desconto AS DECIMAL(18,2)) AS Descontos,
    CAST(Receita_Liquida AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(Custo_Produtos AS DECIMAL(18,2)) AS Custo_Dos_Produtos,
    CAST(Margem_Bruta AS DECIMAL(18,2)) AS Margem_Bruta,
    CAST(Receita_Liquida / NULLIF(Pedidos, 0) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(
        100.0 * Desconto / NULLIF(Receita_Bruta, 0)
        AS DECIMAL(10,2)
    ) AS Desconto_Pct_Ponderado,
    CAST(
        100.0 * Margem_Bruta / NULLIF(Receita_Liquida, 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada,
    CAST(
        100.0 * (Receita_Liquida - Receita_Mes_Anterior)
        / NULLIF(Receita_Mes_Anterior, 0)
        AS DECIMAL(10,2)
    ) AS Variacao_Receita_Mes_Anterior_Pct
FROM Comparacao
ORDER BY Mes_Referencia;
GO

/* 4. Desempenho por forma de pagamento. */
SELECT
    PG.Forma_Pagamento,
    COUNT_BIG(*) AS Pedidos,
    COUNT(DISTINCT F.Cliente_SK) AS Clientes,
    CAST(SUM(F.Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(AVG(F.Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(SUM(F.Desconto) AS DECIMAL(18,2)) AS Descontos,
    CAST(
        100.0 * SUM(F.Desconto) / NULLIF(SUM(F.Receita_Bruta), 0)
        AS DECIMAL(10,2)
    ) AS Desconto_Pct_Ponderado,
    CAST(SUM(F.Margem_Bruta) AS DECIMAL(18,2)) AS Margem_Bruta,
    CAST(
        100.0 * SUM(F.Margem_Bruta) / NULLIF(SUM(F.Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada
FROM #Financeiro_Pedido AS F
INNER JOIN gold.dim_pagamento AS PG
    ON PG.Pagamento_SK = F.Pagamento_SK
GROUP BY PG.Forma_Pagamento
ORDER BY Receita_Liquida DESC;
GO

/* 5. Efeito observado do desconto nos pedidos.
   A comparação é descritiva: não prova que o desconto causou o resultado. */
WITH Faixas AS
(
    SELECT
        F.*,
        CASE
            WHEN Desconto_Percentual IS NULL THEN N'Não informado'
            WHEN Desconto_Percentual = 0 THEN N'0%'
            WHEN Desconto_Percentual <= 0.05 THEN N'> 0% a 5%'
            WHEN Desconto_Percentual <= 0.10 THEN N'> 5% a 10%'
            WHEN Desconto_Percentual <= 0.20 THEN N'> 10% a 20%'
            ELSE N'Acima de 20%'
        END AS Faixa_Desconto,
        CASE
            WHEN Desconto_Percentual IS NULL THEN 99
            WHEN Desconto_Percentual = 0 THEN 1
            WHEN Desconto_Percentual <= 0.05 THEN 2
            WHEN Desconto_Percentual <= 0.10 THEN 3
            WHEN Desconto_Percentual <= 0.20 THEN 4
            ELSE 5
        END AS Ordem_Faixa
    FROM #Financeiro_Pedido AS F
)
SELECT
    Faixa_Desconto,
    COUNT_BIG(*) AS Pedidos,
    COUNT(DISTINCT Cliente_SK) AS Clientes,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(SUM(Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(SUM(Desconto) AS DECIMAL(18,2)) AS Descontos,
    CAST(SUM(Margem_Bruta) AS DECIMAL(18,2)) AS Margem_Bruta,
    CAST(
        100.0 * SUM(Margem_Bruta) / NULLIF(SUM(Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada
FROM Faixas
GROUP BY Faixa_Desconto, Ordem_Faixa
ORDER BY Ordem_Faixa;
GO

/* 6. Rentabilidade por categoria de produto. */
SELECT
    P.Categoria_Item,
    COUNT(DISTINCT I.Produto_SK) AS Produtos_Vendidos,
    COUNT(DISTINCT I.Pedido_ID) AS Pedidos,
    COUNT(DISTINCT I.Cliente_SK) AS Clientes,
    CAST(SUM(I.Quantidade) AS DECIMAL(18,0)) AS Unidades,
    CAST(SUM(I.Receita_Bruta) AS DECIMAL(18,2)) AS Receita_Bruta,
    CAST(SUM(I.Desconto) AS DECIMAL(18,2)) AS Descontos,
    CAST(SUM(I.Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(SUM(I.Custo_Produtos) AS DECIMAL(18,2)) AS Custo_Dos_Produtos,
    CAST(SUM(I.Margem_Bruta) AS DECIMAL(18,2)) AS Margem_Bruta,
    CAST(
        100.0 * SUM(I.Desconto) / NULLIF(SUM(I.Receita_Bruta), 0)
        AS DECIMAL(10,2)
    ) AS Desconto_Pct_Ponderado,
    CAST(
        100.0 * SUM(I.Margem_Bruta) / NULLIF(SUM(I.Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada
FROM #Financeiro_Item AS I
INNER JOIN gold.dim_produto AS P
    ON P.Produto_SK = I.Produto_SK
GROUP BY P.Categoria_Item
ORDER BY Receita_Liquida DESC;
GO

/* 7. Rentabilidade por produto.
   A ordenação destaca os produtos que mais geraram margem absoluta. */
SELECT
    P.Produto_SK,
    P.Produto,
    P.Categoria_Item,
    COUNT(DISTINCT I.Pedido_ID) AS Pedidos,
    COUNT(DISTINCT I.Cliente_SK) AS Clientes,
    CAST(SUM(I.Quantidade) AS DECIMAL(18,0)) AS Unidades,
    CAST(SUM(I.Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(SUM(I.Custo_Produtos) AS DECIMAL(18,2)) AS Custo_Dos_Produtos,
    CAST(SUM(I.Margem_Bruta) AS DECIMAL(18,2)) AS Margem_Bruta,
    CAST(
        100.0 * SUM(I.Margem_Bruta) / NULLIF(SUM(I.Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada,
    CAST(
        100.0 * SUM(I.Desconto) / NULLIF(SUM(I.Receita_Bruta), 0)
        AS DECIMAL(10,2)
    ) AS Desconto_Pct_Ponderado
FROM #Financeiro_Item AS I
INNER JOIN gold.dim_produto AS P
    ON P.Produto_SK = I.Produto_SK
GROUP BY
    P.Produto_SK,
    P.Produto,
    P.Categoria_Item
ORDER BY Margem_Bruta DESC, Receita_Liquida DESC;
GO

/* 8. Pedidos com margem negativa, nula ou baixa.
   O limite de 10% é diagnóstico e pode ser ajustado à política do negócio. */
WITH Classificacao AS
(
    SELECT
        F.*,
        CASE
            WHEN Margem_Bruta < 0 THEN N'Negativa'
            WHEN Margem_Bruta = 0 THEN N'Nula'
            WHEN Margem_Bruta / NULLIF(Receita_Liquida, 0) < 0.10
                THEN N'Positiva abaixo de 10%'
            ELSE N'Igual ou acima de 10%'
        END AS Faixa_Margem,
        CASE
            WHEN Margem_Bruta < 0 THEN 1
            WHEN Margem_Bruta = 0 THEN 2
            WHEN Margem_Bruta / NULLIF(Receita_Liquida, 0) < 0.10 THEN 3
            ELSE 4
        END AS Ordem_Faixa
    FROM #Financeiro_Pedido AS F
)
SELECT
    Faixa_Margem,
    COUNT_BIG(*) AS Pedidos,
    CAST(
        100.0 * COUNT_BIG(*) / SUM(COUNT_BIG(*)) OVER ()
        AS DECIMAL(10,2)
    ) AS Pedidos_Pct,
    CAST(SUM(Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(SUM(Margem_Bruta) AS DECIMAL(18,2)) AS Margem_Bruta,
    CAST(AVG(Desconto_Percentual) * 100.0 AS DECIMAL(10,2))
        AS Desconto_Medio_Simples_Pct
FROM Classificacao
GROUP BY Faixa_Margem, Ordem_Faixa
ORDER BY Ordem_Faixa;
GO

/* 9. Detalhamento dos 30 pedidos de menor margem.
   Serve para investigação; não significa exclusão automática. */
SELECT TOP (30)
    F.Pedido_ID,
    F.Cliente_SK,
    F.Data_Hora_Compra,
    F.Quantidade_Total_Itens,
    CAST(F.Receita_Bruta AS DECIMAL(18,2)) AS Receita_Bruta,
    CAST(F.Desconto AS DECIMAL(18,2)) AS Desconto,
    CAST(F.Receita_Liquida AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(F.Custo_Produtos AS DECIMAL(18,2)) AS Custo_Dos_Produtos,
    CAST(F.Margem_Bruta AS DECIMAL(18,2)) AS Margem_Bruta,
    CAST(
        100.0 * F.Margem_Bruta / NULLIF(F.Receita_Liquida, 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct,
    CAST(F.Desconto_Percentual * 100.0 AS DECIMAL(10,2)) AS Desconto_Pct,
    F.Pedido_Com_Campanha,
    F.Cupom_Status
FROM #Financeiro_Pedido AS F
ORDER BY F.Margem_Bruta, F.Receita_Liquida DESC;
GO

/* 10. Rentabilidade por cliente.
   Receita alta não garante margem alta; ambas são exibidas separadamente. */
SELECT
    C.Cliente_SK,
    C.Cliente_ID,
    C.Genero,
    C.Idade,
    COUNT_BIG(*) AS Pedidos,
    CAST(SUM(F.Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(AVG(F.Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(SUM(F.Desconto) AS DECIMAL(18,2)) AS Descontos,
    CAST(SUM(F.Custo_Produtos) AS DECIMAL(18,2)) AS Custo_Dos_Produtos,
    CAST(SUM(F.Margem_Bruta) AS DECIMAL(18,2)) AS Margem_Bruta,
    CAST(
        100.0 * SUM(F.Margem_Bruta) / NULLIF(SUM(F.Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada
FROM #Financeiro_Pedido AS F
INNER JOIN gold.dim_cliente AS C
    ON C.Cliente_SK = F.Cliente_SK
GROUP BY
    C.Cliente_SK,
    C.Cliente_ID,
    C.Genero,
    C.Idade
ORDER BY Margem_Bruta DESC, Receita_Liquida DESC;
GO

/* 11. Concentração da receita por cliente — curva acumulada tipo Pareto. */
WITH Cliente AS
(
    SELECT
        Cliente_SK,
        SUM(Receita_Liquida) AS Receita_Liquida
    FROM #Financeiro_Pedido
    GROUP BY Cliente_SK
),
Ranking AS
(
    SELECT
        Cliente_SK,
        Receita_Liquida,
        ROW_NUMBER() OVER
            (ORDER BY Receita_Liquida DESC, Cliente_SK) AS Posicao,
        COUNT_BIG(*) OVER () AS Total_Clientes,
        SUM(Receita_Liquida) OVER
            (ORDER BY Receita_Liquida DESC, Cliente_SK
             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
            AS Receita_Acumulada,
        SUM(Receita_Liquida) OVER () AS Receita_Total
    FROM Cliente
),
Faixas AS
(
    SELECT
        CASE
            WHEN 1.0 * Posicao / NULLIF(Total_Clientes, 0) <= 0.10
                THEN N'Top 10%'
            WHEN 1.0 * Posicao / NULLIF(Total_Clientes, 0) <= 0.20
                THEN N'Entre 10% e 20%'
            ELSE N'Demais 80%'
        END AS Faixa_Clientes,
        CASE
            WHEN 1.0 * Posicao / NULLIF(Total_Clientes, 0) <= 0.10 THEN 1
            WHEN 1.0 * Posicao / NULLIF(Total_Clientes, 0) <= 0.20 THEN 2
            ELSE 3
        END AS Ordem_Faixa,
        Cliente_SK,
        Receita_Liquida,
        Receita_Total
    FROM Ranking
)
SELECT
    Faixa_Clientes,
    COUNT_BIG(*) AS Clientes,
    CAST(SUM(Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(
        100.0 * SUM(Receita_Liquida) / NULLIF(MAX(Receita_Total), 0)
        AS DECIMAL(10,2)
    ) AS Participacao_Na_Receita_Pct
FROM Faixas
GROUP BY Faixa_Clientes, Ordem_Faixa
ORDER BY Ordem_Faixa;
GO

/* 12. Frete registrado e gratuidade por faixa financeira do pedido.
   Frete não é subtraído da margem bruta porque não há confirmação de que
   represente custo logístico da empresa. */
WITH Pedido_Entrega AS
(
    SELECT
        F.Pedido_ID,
        F.Receita_Liquida,
        F.Margem_Bruta,
        CONVERT(FLOAT, FE.Frete) AS Frete,
        FE.Frete_Gratis,
        CASE
            WHEN F.Receita_Liquida < 50 THEN N'Abaixo de R$ 50'
            WHEN F.Receita_Liquida < 100 THEN N'R$ 50 a R$ 99,99'
            WHEN F.Receita_Liquida < 200 THEN N'R$ 100 a R$ 199,99'
            ELSE N'R$ 200 ou mais'
        END AS Faixa_Receita,
        CASE
            WHEN F.Receita_Liquida < 50 THEN 1
            WHEN F.Receita_Liquida < 100 THEN 2
            WHEN F.Receita_Liquida < 200 THEN 3
            ELSE 4
        END AS Ordem_Faixa
    FROM #Financeiro_Pedido AS F
    INNER JOIN gold.fato_entrega AS FE
        ON FE.Pedido_ID = F.Pedido_ID
)
SELECT
    Faixa_Receita,
    COUNT_BIG(*) AS Entregas,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(AVG(Frete) AS DECIMAL(18,2)) AS Frete_Medio_Registrado,
    CAST(
        100.0 * SUM(CASE WHEN Frete_Gratis = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Entregas_Com_Frete_Gratis_Pct,
    CAST(
        100.0 * SUM(Margem_Bruta) / NULLIF(SUM(Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada
FROM Pedido_Entrega
GROUP BY Faixa_Receita, Ordem_Faixa
ORDER BY Ordem_Faixa;
GO

/* 13. Reconciliação final entre o grão do pedido e o grão do item.
   As diferenças esperadas são zero ou apenas resíduos mínimos de arredondamento. */
SELECT
    CAST(SUM(P.Receita_Bruta) AS DECIMAL(18,2)) AS Bruta_Pedidos,
    CAST(MAX(I.Receita_Bruta) AS DECIMAL(18,2)) AS Bruta_Itens,
    CAST(SUM(P.Receita_Bruta) - MAX(I.Receita_Bruta) AS DECIMAL(18,2))
        AS Diferenca_Bruta,
    CAST(SUM(P.Desconto) AS DECIMAL(18,2)) AS Desconto_Pedidos,
    CAST(MAX(I.Desconto) AS DECIMAL(18,2)) AS Desconto_Itens,
    CAST(SUM(P.Desconto) - MAX(I.Desconto) AS DECIMAL(18,2))
        AS Diferenca_Desconto,
    CAST(SUM(P.Receita_Liquida) AS DECIMAL(18,2)) AS Liquida_Pedidos,
    CAST(MAX(I.Receita_Liquida) AS DECIMAL(18,2)) AS Liquida_Itens,
    CAST(SUM(P.Receita_Liquida) - MAX(I.Receita_Liquida) AS DECIMAL(18,2))
        AS Diferenca_Liquida,
    CAST(SUM(P.Custo_Produtos) AS DECIMAL(18,2)) AS Custo_Pedidos,
    CAST(MAX(I.Custo_Produtos) AS DECIMAL(18,2)) AS Custo_Itens,
    CAST(SUM(P.Custo_Produtos) - MAX(I.Custo_Produtos) AS DECIMAL(18,2))
        AS Diferenca_Custo,
    CAST(SUM(P.Margem_Bruta) AS DECIMAL(18,2)) AS Margem_Pedidos,
    CAST(MAX(I.Margem_Bruta) AS DECIMAL(18,2)) AS Margem_Itens,
    CAST(SUM(P.Margem_Bruta) - MAX(I.Margem_Bruta) AS DECIMAL(18,2))
        AS Diferenca_Margem
FROM #Financeiro_Pedido AS P
CROSS JOIN
(
    SELECT
        SUM(Receita_Bruta) AS Receita_Bruta,
        SUM(Desconto) AS Desconto,
        SUM(Receita_Liquida) AS Receita_Liquida,
        SUM(Custo_Produtos) AS Custo_Produtos,
        SUM(Margem_Bruta) AS Margem_Bruta
    FROM #Financeiro_Item
) AS I;
GO

DROP TABLE IF EXISTS #Financeiro_Item;
DROP TABLE IF EXISTS #Financeiro_Pedido;
GO
