USE [CustomerAnalyticsHub];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

/* ============================================================================
   CUSTOMER ANALYTICS HUB
   09 — EDA DE MARKETING

   OBJETIVO
   Avaliar o comportamento observado de campanhas, canais, cupons e eventos
   externos em relação a pedidos, clientes, receita, descontos e margem bruta.

   GRÃO PRINCIPAL
   - gold.fato_pedido: uma linha por pedido.
   - gold.fato_item_pedido: uma linha por item, apenas no recorte de categoria.

   CUIDADO DE INTERPRETAÇÃO
   Os resultados mostram associações descritivas. Eles não comprovam que uma
   campanha, canal, cupom ou evento causou aumento de vendas. A base não contém
   grupo de controle, exposição individual, impressões, cliques, sessões,
   investimento de mídia ou custo de campanha. Portanto, não é possível
   calcular conversão, CAC, ROI, ROAS ou incremento causal verdadeiro.
   ============================================================================ */

DROP TABLE IF EXISTS #Marketing_Pedido;
GO

/* 1. Base temporária no grão correto: uma linha por pedido. */
SELECT
    FP.Pedido_SK,
    FP.Pedido_ID,
    FP.Cliente_SK,
    FP.Data_Hora_Compra,
    FP.Canal_Marketing_SK,
    FP.Campanha_SK,
    FP.Evento_Externo_SK,
    CM.Canal_Marketing,
    CP.Campanha,
    EE.Evento_Externo,
    FP.Pedido_Com_Campanha,
    FP.Cupom_Status,
    CONVERT(FLOAT, FP.Quantidade_Total_Itens)  AS Quantidade_Itens,
    CONVERT(FLOAT, FP.Valor_Bruto_Pedido)     AS Receita_Bruta,
    CONVERT(FLOAT, FP.Valor_Desconto_Pedido)  AS Desconto,
    CONVERT(FLOAT, FP.Valor_Liquido_Pedido)   AS Receita_Liquida,
    CONVERT(FLOAT, FP.Custo_Total_Pedido)     AS Custo_Produtos,
    CONVERT(FLOAT, FP.Margem_Bruta_Pedido)    AS Margem_Bruta
INTO #Marketing_Pedido
FROM gold.fato_pedido AS FP
INNER JOIN gold.dim_canal_marketing AS CM
    ON CM.Canal_Marketing_SK = FP.Canal_Marketing_SK
INNER JOIN gold.dim_campanha AS CP
    ON CP.Campanha_SK = FP.Campanha_SK
INNER JOIN gold.dim_evento_externo AS EE
    ON EE.Evento_Externo_SK = FP.Evento_Externo_SK;
GO

CREATE UNIQUE CLUSTERED INDEX IX_Marketing_Pedido
    ON #Marketing_Pedido (Pedido_SK);

CREATE INDEX IX_Marketing_Pedido_Data
    ON #Marketing_Pedido (Data_Hora_Compra);

CREATE INDEX IX_Marketing_Pedido_Canal_Campanha
    ON #Marketing_Pedido (Canal_Marketing_SK, Campanha_SK);
GO

/* 2. Visão geral: pedidos associados e não associados a campanha.
   A diferença entre grupos é observada, não causal. */
SELECT
    CASE
        WHEN Pedido_Com_Campanha = 1 THEN N'Com campanha'
        WHEN Pedido_Com_Campanha = 0 THEN N'Sem campanha'
        ELSE N'Não informado'
    END AS Associacao_Campanha,
    COUNT_BIG(*) AS Pedidos,
    COUNT(DISTINCT Cliente_SK) AS Clientes,
    CAST(AVG(Quantidade_Itens) AS DECIMAL(18,2)) AS Itens_Medios_Pedido,
    CAST(SUM(Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(SUM(Desconto) AS DECIMAL(18,2)) AS Descontos,
    CAST(
        100.0 * SUM(Desconto) / NULLIF(SUM(Receita_Bruta), 0)
        AS DECIMAL(10,2)
    ) AS Desconto_Pct_Ponderado,
    CAST(SUM(Margem_Bruta) AS DECIMAL(18,2)) AS Margem_Bruta,
    CAST(
        100.0 * SUM(Margem_Bruta) / NULLIF(SUM(Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada
FROM #Marketing_Pedido
GROUP BY Pedido_Com_Campanha
ORDER BY Associacao_Campanha;
GO

/* 3. Desempenho descritivo por canal de marketing. */
SELECT
    Canal_Marketing,
    COUNT_BIG(*) AS Pedidos,
    COUNT(DISTINCT Cliente_SK) AS Clientes,
    CAST(
        100.0 * COUNT_BIG(*) / SUM(COUNT_BIG(*)) OVER ()
        AS DECIMAL(10,2)
    ) AS Participacao_Pedidos_Pct,
    CAST(SUM(Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(
        100.0 * SUM(Receita_Liquida)
        / NULLIF(SUM(SUM(Receita_Liquida)) OVER (), 0)
        AS DECIMAL(10,2)
    ) AS Participacao_Receita_Pct,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(AVG(Quantidade_Itens) AS DECIMAL(18,2)) AS Itens_Medios_Pedido,
    CAST(
        100.0 * SUM(Desconto) / NULLIF(SUM(Receita_Bruta), 0)
        AS DECIMAL(10,2)
    ) AS Desconto_Pct_Ponderado,
    CAST(
        100.0 * SUM(Margem_Bruta) / NULLIF(SUM(Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada,
    CASE
        WHEN COUNT_BIG(*) < 30 THEN N'Amostra pequena'
        ELSE N'Amostra suficiente para descrição'
    END AS Status_Amostra
FROM #Marketing_Pedido
GROUP BY Canal_Marketing
ORDER BY Receita_Liquida DESC;
GO

/* 4. Desempenho descritivo por campanha cadastrada. */
SELECT
    Campanha,
    COUNT_BIG(*) AS Pedidos,
    COUNT(DISTINCT Cliente_SK) AS Clientes,
    CAST(SUM(Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(AVG(Quantidade_Itens) AS DECIMAL(18,2)) AS Itens_Medios_Pedido,
    CAST(SUM(Desconto) AS DECIMAL(18,2)) AS Descontos,
    CAST(
        100.0 * SUM(Desconto) / NULLIF(SUM(Receita_Bruta), 0)
        AS DECIMAL(10,2)
    ) AS Desconto_Pct_Ponderado,
    CAST(SUM(Margem_Bruta) AS DECIMAL(18,2)) AS Margem_Bruta,
    CAST(
        100.0 * SUM(Margem_Bruta) / NULLIF(SUM(Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada,
    CASE
        WHEN COUNT_BIG(*) < 30 THEN N'Amostra pequena'
        ELSE N'Amostra suficiente para descrição'
    END AS Status_Amostra
FROM #Marketing_Pedido
GROUP BY Campanha
ORDER BY Receita_Liquida DESC;
GO

/* 5. Contexto de eventos externos.
   O evento pode coincidir com a compra, mas a associação não prova influência. */
SELECT
    Evento_Externo,
    COUNT_BIG(*) AS Pedidos,
    COUNT(DISTINCT Cliente_SK) AS Clientes,
    CAST(SUM(Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(AVG(Quantidade_Itens) AS DECIMAL(18,2)) AS Itens_Medios_Pedido,
    CAST(
        100.0 * SUM(Desconto) / NULLIF(SUM(Receita_Bruta), 0)
        AS DECIMAL(10,2)
    ) AS Desconto_Pct_Ponderado,
    CAST(
        100.0 * SUM(Margem_Bruta) / NULLIF(SUM(Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada,
    CASE
        WHEN COUNT_BIG(*) < 30 THEN N'Amostra pequena'
        ELSE N'Amostra suficiente para descrição'
    END AS Status_Amostra
FROM #Marketing_Pedido
GROUP BY Evento_Externo
ORDER BY Receita_Liquida DESC;
GO

/* 6. Uso/status de cupom e comportamento financeiro observado. */
SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(Cupom_Status)), N''), N'Não informado')
        AS Cupom_Status,
    COUNT_BIG(*) AS Pedidos,
    COUNT(DISTINCT Cliente_SK) AS Clientes,
    CAST(AVG(Quantidade_Itens) AS DECIMAL(18,2)) AS Itens_Medios_Pedido,
    CAST(SUM(Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(SUM(Desconto) AS DECIMAL(18,2)) AS Descontos,
    CAST(
        100.0 * SUM(Desconto) / NULLIF(SUM(Receita_Bruta), 0)
        AS DECIMAL(10,2)
    ) AS Desconto_Pct_Ponderado,
    CAST(
        100.0 * SUM(Margem_Bruta) / NULLIF(SUM(Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada
FROM #Marketing_Pedido
GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(Cupom_Status)), N''), N'Não informado')
ORDER BY Pedidos DESC;
GO

/* 7. Cruzamento entre canal e campanha.
   Sinaliza combinações com poucos pedidos para evitar conclusões frágeis. */
SELECT
    Canal_Marketing,
    Campanha,
    COUNT_BIG(*) AS Pedidos,
    COUNT(DISTINCT Cliente_SK) AS Clientes,
    CAST(SUM(Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(
        100.0 * SUM(Desconto) / NULLIF(SUM(Receita_Bruta), 0)
        AS DECIMAL(10,2)
    ) AS Desconto_Pct_Ponderado,
    CAST(
        100.0 * SUM(Margem_Bruta) / NULLIF(SUM(Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada,
    CASE
        WHEN COUNT_BIG(*) < 30 THEN N'Amostra pequena'
        ELSE N'Amostra suficiente para descrição'
    END AS Status_Amostra
FROM #Marketing_Pedido
GROUP BY Canal_Marketing, Campanha
ORDER BY Pedidos DESC, Receita_Liquida DESC;
GO

/* 8. Campanha x evento externo.
   Ajuda a detectar sobreposição entre ação comercial e contexto de calendário. */
SELECT
    Campanha,
    Evento_Externo,
    COUNT_BIG(*) AS Pedidos,
    COUNT(DISTINCT Cliente_SK) AS Clientes,
    CAST(SUM(Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(
        100.0 * SUM(Desconto) / NULLIF(SUM(Receita_Bruta), 0)
        AS DECIMAL(10,2)
    ) AS Desconto_Pct_Ponderado,
    CAST(
        100.0 * SUM(Margem_Bruta) / NULLIF(SUM(Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada,
    CASE
        WHEN COUNT_BIG(*) < 30 THEN N'Amostra pequena'
        ELSE N'Amostra suficiente para descrição'
    END AS Status_Amostra
FROM #Marketing_Pedido
GROUP BY Campanha, Evento_Externo
ORDER BY Pedidos DESC, Receita_Liquida DESC;
GO

/* 9. Evolução mensal por canal.
   Permite verificar estabilidade, sazonalidade e dependência temporal. */
SELECT
    DATEFROMPARTS(
        YEAR(Data_Hora_Compra),
        MONTH(Data_Hora_Compra),
        1
    ) AS Mes_Referencia,
    Canal_Marketing,
    COUNT_BIG(*) AS Pedidos,
    COUNT(DISTINCT Cliente_SK) AS Clientes,
    CAST(SUM(Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(
        100.0 * SUM(Margem_Bruta) / NULLIF(SUM(Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada
FROM #Marketing_Pedido
GROUP BY
    YEAR(Data_Hora_Compra),
    MONTH(Data_Hora_Compra),
    Canal_Marketing
ORDER BY Mes_Referencia, Receita_Liquida DESC;
GO

/* 10. Categoria de produto x associação com campanha.
   O grão muda para item do pedido e não deve ser comparado como número de
   pedidos sem usar COUNT DISTINCT. */
SELECT
    P.Categoria_Item,
    CASE
        WHEN M.Pedido_Com_Campanha = 1 THEN N'Com campanha'
        WHEN M.Pedido_Com_Campanha = 0 THEN N'Sem campanha'
        ELSE N'Não informado'
    END AS Associacao_Campanha,
    COUNT_BIG(*) AS Linhas_Item,
    COUNT(DISTINCT FI.Pedido_ID) AS Pedidos,
    COUNT(DISTINCT FI.Cliente_SK) AS Clientes,
    CAST(SUM(FI.Quantidade) AS DECIMAL(18,0)) AS Unidades,
    CAST(SUM(FI.Valor_Compra) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(SUM(FI.Valor_Desconto_Item) AS DECIMAL(18,2)) AS Descontos,
    CAST(SUM(FI.Margem_Bruta_Item) AS DECIMAL(18,2)) AS Margem_Bruta,
    CAST(
        100.0 * SUM(FI.Margem_Bruta_Item) / NULLIF(SUM(FI.Valor_Compra), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Pct_Ponderada
FROM gold.fato_item_pedido AS FI
INNER JOIN gold.dim_produto AS P
    ON P.Produto_SK = FI.Produto_SK
INNER JOIN #Marketing_Pedido AS M
    ON M.Pedido_ID = FI.Pedido_ID
GROUP BY P.Categoria_Item, M.Pedido_Com_Campanha
ORDER BY P.Categoria_Item, Receita_Liquida DESC;
GO

/* 11. Alcance observado e recorrência de compra por canal.
   Clientes_Multiplos_Pedidos identifica repetição dentro do canal, não retenção
   causada pelo canal. */
WITH Cliente_Canal AS
(
    SELECT
        Canal_Marketing,
        Cliente_SK,
        COUNT_BIG(*) AS Pedidos_Cliente,
        SUM(Receita_Liquida) AS Receita_Cliente
    FROM #Marketing_Pedido
    GROUP BY Canal_Marketing, Cliente_SK
)
SELECT
    Canal_Marketing,
    COUNT_BIG(*) AS Clientes_Alcancados_Com_Compra,
    SUM(CASE WHEN Pedidos_Cliente >= 2 THEN 1 ELSE 0 END)
        AS Clientes_Com_Multiplos_Pedidos,
    CAST(
        100.0 * SUM(CASE WHEN Pedidos_Cliente >= 2 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Clientes_Com_Multiplos_Pedidos_Pct,
    CAST(AVG(CONVERT(FLOAT, Pedidos_Cliente)) AS DECIMAL(18,2))
        AS Pedidos_Medios_Por_Cliente,
    CAST(AVG(Receita_Cliente) AS DECIMAL(18,2))
        AS Receita_Media_Por_Cliente
FROM Cliente_Canal
GROUP BY Canal_Marketing
ORDER BY Clientes_Alcancados_Com_Compra DESC;
GO

/* 12. Diagnóstico de dependência de campanhas por canal.
   Mostra quanto da receita de cada canal está associada a pedidos marcados
   como campanha. */
SELECT
    Canal_Marketing,
    COUNT_BIG(*) AS Pedidos_Totais,
    SUM(CASE WHEN Pedido_Com_Campanha = 1 THEN 1 ELSE 0 END)
        AS Pedidos_Com_Campanha,
    CAST(
        100.0 * SUM(CASE WHEN Pedido_Com_Campanha = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Pedidos_Com_Campanha_Pct,
    CAST(SUM(Receita_Liquida) AS DECIMAL(18,2)) AS Receita_Total,
    CAST(
        SUM(CASE WHEN Pedido_Com_Campanha = 1
                 THEN Receita_Liquida ELSE 0 END)
        AS DECIMAL(18,2)
    ) AS Receita_Associada_Campanha,
    CAST(
        100.0 * SUM(CASE WHEN Pedido_Com_Campanha = 1
                         THEN Receita_Liquida ELSE 0 END)
        / NULLIF(SUM(Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Receita_Associada_Campanha_Pct
FROM #Marketing_Pedido
GROUP BY Canal_Marketing
ORDER BY Receita_Associada_Campanha_Pct DESC;
GO

/* 13. Comparação descritiva entre pedidos com e sem campanha por canal.
   Diferença percentual positiva significa que o grupo com campanha apresentou
   média maior; ainda assim, não representa uplift causal. */
WITH Canal_Grupo AS
(
    SELECT
        Canal_Marketing,
        Pedido_Com_Campanha,
        COUNT_BIG(*) AS Pedidos,
        AVG(Receita_Liquida) AS Ticket_Medio,
        AVG(Quantidade_Itens) AS Itens_Medios,
        SUM(Margem_Bruta) / NULLIF(SUM(Receita_Liquida), 0)
            AS Margem_Pct
    FROM #Marketing_Pedido
    WHERE Pedido_Com_Campanha IN (0, 1)
    GROUP BY Canal_Marketing, Pedido_Com_Campanha
),
Comparacao AS
(
    SELECT
        Canal_Marketing,
        MAX(CASE WHEN Pedido_Com_Campanha = 0 THEN Pedidos END)
            AS Pedidos_Sem_Campanha,
        MAX(CASE WHEN Pedido_Com_Campanha = 1 THEN Pedidos END)
            AS Pedidos_Com_Campanha,
        MAX(CASE WHEN Pedido_Com_Campanha = 0 THEN Ticket_Medio END)
            AS Ticket_Sem_Campanha,
        MAX(CASE WHEN Pedido_Com_Campanha = 1 THEN Ticket_Medio END)
            AS Ticket_Com_Campanha,
        MAX(CASE WHEN Pedido_Com_Campanha = 0 THEN Itens_Medios END)
            AS Itens_Sem_Campanha,
        MAX(CASE WHEN Pedido_Com_Campanha = 1 THEN Itens_Medios END)
            AS Itens_Com_Campanha,
        MAX(CASE WHEN Pedido_Com_Campanha = 0 THEN Margem_Pct END)
            AS Margem_Sem_Campanha,
        MAX(CASE WHEN Pedido_Com_Campanha = 1 THEN Margem_Pct END)
            AS Margem_Com_Campanha
    FROM Canal_Grupo
    GROUP BY Canal_Marketing
)
SELECT
    Canal_Marketing,
    Pedidos_Sem_Campanha,
    Pedidos_Com_Campanha,
    CAST(Ticket_Sem_Campanha AS DECIMAL(18,2)) AS Ticket_Sem_Campanha,
    CAST(Ticket_Com_Campanha AS DECIMAL(18,2)) AS Ticket_Com_Campanha,
    CAST(
        100.0 * (Ticket_Com_Campanha - Ticket_Sem_Campanha)
        / NULLIF(Ticket_Sem_Campanha, 0)
        AS DECIMAL(10,2)
    ) AS Diferenca_Descritiva_Ticket_Pct,
    CAST(Itens_Sem_Campanha AS DECIMAL(18,2)) AS Itens_Sem_Campanha,
    CAST(Itens_Com_Campanha AS DECIMAL(18,2)) AS Itens_Com_Campanha,
    CAST(100.0 * Margem_Sem_Campanha AS DECIMAL(10,2))
        AS Margem_Sem_Campanha_Pct,
    CAST(100.0 * Margem_Com_Campanha AS DECIMAL(10,2))
        AS Margem_Com_Campanha_Pct,
    CASE
        WHEN COALESCE(Pedidos_Sem_Campanha, 0) < 30
          OR COALESCE(Pedidos_Com_Campanha, 0) < 30
            THEN N'Comparação com amostra pequena'
        ELSE N'Amostra suficiente para descrição'
    END AS Status_Comparacao
FROM Comparacao
ORDER BY Canal_Marketing;
GO

/* 14. Cobertura dos atributos de marketing.
   Valores ausentes ou categorias genéricas limitam as comparações. */
SELECT
    V.Atributo,
    COUNT_BIG(*) AS Pedidos,
    SUM(CASE WHEN V.Valor IS NULL OR LTRIM(RTRIM(V.Valor)) = N''
             THEN 1 ELSE 0 END) AS Pedidos_Sem_Informacao,
    CAST(
        100.0 * SUM(
            CASE WHEN V.Valor IS NULL OR LTRIM(RTRIM(V.Valor)) = N''
                 THEN 1 ELSE 0 END
        ) / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Ausencia_Pct,
    COUNT(DISTINCT V.Valor) AS Categorias_Distintas
FROM #Marketing_Pedido AS M
CROSS APPLY
(
    VALUES
        (N'Canal_Marketing', CONVERT(NVARCHAR(255), M.Canal_Marketing)),
        (N'Campanha', CONVERT(NVARCHAR(255), M.Campanha)),
        (N'Evento_Externo', CONVERT(NVARCHAR(255), M.Evento_Externo)),
        (N'Cupom_Status', CONVERT(NVARCHAR(255), M.Cupom_Status))
) AS V (Atributo, Valor)
GROUP BY V.Atributo
ORDER BY V.Atributo;
GO

DROP TABLE IF EXISTS #Marketing_Pedido;
GO
