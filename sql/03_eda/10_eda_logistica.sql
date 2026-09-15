USE [CustomerAnalyticsHub];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

/* ============================================================================
   CUSTOMER ANALYTICS HUB
   10 — EDA DE LOGÍSTICA

   OBJETIVO
   Avaliar nível de serviço, cumprimento de prazo, atrasos, antecipações,
   transportadoras, regiões, frete e satisfação do cliente.

   GRÃO PRINCIPAL
   - gold.fato_entrega: uma linha por entrega/pedido.
   - gold.fato_pedido: uma linha por pedido, usada apenas para data, geografia
     e valores comerciais associados à entrega.

   DEFINIÇÕES OPERACIONAIS
   - No prazo: Dias_Atraso <= 0.
   - Atrasada: Dias_Atraso > 0.
   - Antecipada: Dias_Antecipacao > 0.

   LIMITAÇÕES
   - A base não contém distância, rota, peso, volume, custo real do transporte,
     tentativas de entrega ou capacidade operacional.
   - O campo Frete é tratado como valor registrado, não como custo logístico.
   - Associações entre atraso, avaliação e receita não comprovam causalidade.
   ============================================================================ */

DROP TABLE IF EXISTS #Logistica_Entrega;
GO

/* 1. Validação do relacionamento pedido x entrega.
   Antes da EDA, confirma se a junção preservará uma linha por pedido. */
SELECT
    (SELECT COUNT_BIG(*) FROM gold.fato_pedido) AS Pedidos,
    (SELECT COUNT_BIG(*) FROM gold.fato_entrega) AS Entregas,
    SUM(CASE WHEN X.Pedido_ID IS NULL THEN 1 ELSE 0 END)
        AS Pedidos_Sem_Entrega,
    SUM(CASE WHEN X.Quantidade_Entregas > 1 THEN 1 ELSE 0 END)
        AS Pedidos_Com_Mais_De_Uma_Entrega
FROM gold.fato_pedido AS FP
LEFT JOIN
(
    SELECT
        Pedido_ID,
        COUNT_BIG(*) AS Quantidade_Entregas
    FROM gold.fato_entrega
    GROUP BY Pedido_ID
) AS X
    ON X.Pedido_ID = FP.Pedido_ID;
GO

/* 2. Base temporária logística no grão da entrega. */
SELECT
    FE.Pedido_ID,
    FE.Cliente_SK,
    FE.Transportadora_SK,
    T.Transportadora,
    FP.Geografia_SK,
    G.Cidade,
    G.Estado,
    G.Regiao,
    FP.Data_Hora_Compra,
    CONVERT(FLOAT, FE.Frete) AS Frete,
    FE.Frete_Gratis,
    CONVERT(FLOAT, FE.Prazo_Entrega_Prometido_Dias)
        AS Prazo_Prometido_Dias,
    CONVERT(FLOAT, FE.Prazo_Entrega_Real_Dias)
        AS Prazo_Real_Dias,
    CONVERT(FLOAT, FE.Diferenca_Prazo_Dias)
        AS Diferenca_Prazo_Dias,
    CONVERT(FLOAT, FE.Dias_Atraso) AS Dias_Atraso,
    CONVERT(FLOAT, FE.Dias_Antecipacao) AS Dias_Antecipacao,
    FE.Status_Entrega_Calculado,
    CONVERT(FLOAT, FE.Avaliacao_Cliente) AS Avaliacao_Cliente,
    CONVERT(FLOAT, FP.Valor_Liquido_Pedido) AS Receita_Liquida,
    CONVERT(FLOAT, FP.Margem_Bruta_Pedido) AS Margem_Bruta,
    CONVERT(FLOAT, FP.Quantidade_Total_Itens) AS Quantidade_Itens
INTO #Logistica_Entrega
FROM gold.fato_entrega AS FE
INNER JOIN gold.fato_pedido AS FP
    ON FP.Pedido_ID = FE.Pedido_ID
INNER JOIN gold.dim_transportadora AS T
    ON T.Transportadora_SK = FE.Transportadora_SK
INNER JOIN gold.dim_geografia AS G
    ON G.Geografia_SK = FP.Geografia_SK;
GO

CREATE UNIQUE CLUSTERED INDEX IX_Logistica_Entrega
    ON #Logistica_Entrega (Pedido_ID);

CREATE INDEX IX_Logistica_Transportadora
    ON #Logistica_Entrega (Transportadora_SK);

CREATE INDEX IX_Logistica_Geografia
    ON #Logistica_Entrega (Geografia_SK);

CREATE INDEX IX_Logistica_Data
    ON #Logistica_Entrega (Data_Hora_Compra);
GO

/* 3. Resumo operacional geral. */
SELECT
    COUNT_BIG(*) AS Entregas,
    COUNT(DISTINCT Cliente_SK) AS Clientes_Atendidos,
    CAST(AVG(Prazo_Prometido_Dias) AS DECIMAL(18,2))
        AS Prazo_Prometido_Medio_Dias,
    CAST(AVG(Prazo_Real_Dias) AS DECIMAL(18,2))
        AS Prazo_Real_Medio_Dias,
    CAST(AVG(Diferenca_Prazo_Dias) AS DECIMAL(18,2))
        AS Diferenca_Media_Prazo_Dias,
    SUM(CASE WHEN Dias_Atraso > 0 THEN 1 ELSE 0 END)
        AS Entregas_Atrasadas,
    CAST(
        100.0 * SUM(CASE WHEN Dias_Atraso > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Taxa_Atraso_Pct,
    SUM(CASE WHEN Dias_Atraso <= 0 THEN 1 ELSE 0 END)
        AS Entregas_No_Prazo,
    CAST(
        100.0 * SUM(CASE WHEN Dias_Atraso <= 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Nivel_Servico_No_Prazo_Pct,
    CAST(
        AVG(CASE WHEN Dias_Atraso > 0 THEN Dias_Atraso END)
        AS DECIMAL(18,2)
    ) AS Atraso_Medio_Entre_Atrasadas,
    CAST(AVG(Avaliacao_Cliente) AS DECIMAL(10,2)) AS Avaliacao_Media,
    CAST(AVG(Frete) AS DECIMAL(18,2)) AS Frete_Medio_Registrado,
    CAST(
        100.0 * SUM(CASE WHEN Frete_Gratis = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Frete_Gratis_Pct
FROM #Logistica_Entrega;
GO

/* 4. Distribuição por status de entrega. */
SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(Status_Entrega_Calculado)), N''),
             N'Não informado') AS Status_Entrega,
    COUNT_BIG(*) AS Entregas,
    CAST(
        100.0 * COUNT_BIG(*) / SUM(COUNT_BIG(*)) OVER ()
        AS DECIMAL(10,2)
    ) AS Participacao_Entregas_Pct,
    CAST(AVG(Prazo_Real_Dias) AS DECIMAL(18,2)) AS Prazo_Real_Medio_Dias,
    CAST(AVG(Dias_Atraso) AS DECIMAL(18,2)) AS Dias_Atraso_Medio,
    CAST(AVG(Dias_Antecipacao) AS DECIMAL(18,2)) AS Dias_Antecipacao_Medio,
    CAST(AVG(Frete) AS DECIMAL(18,2)) AS Frete_Medio_Registrado,
    CAST(AVG(Avaliacao_Cliente) AS DECIMAL(10,2)) AS Avaliacao_Media,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio
FROM #Logistica_Entrega
GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(Status_Entrega_Calculado)), N''),
                  N'Não informado')
ORDER BY Entregas DESC;
GO

/* 5. Desempenho por transportadora. */
SELECT
    Transportadora,
    COUNT_BIG(*) AS Entregas,
    COUNT(DISTINCT Cliente_SK) AS Clientes_Atendidos,
    CAST(AVG(Prazo_Real_Dias) AS DECIMAL(18,2)) AS Prazo_Real_Medio_Dias,
    CAST(
        100.0 * SUM(CASE WHEN Dias_Atraso > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Taxa_Atraso_Pct,
    CAST(
        AVG(CASE WHEN Dias_Atraso > 0 THEN Dias_Atraso END)
        AS DECIMAL(18,2)
    ) AS Atraso_Medio_Entre_Atrasadas,
    CAST(AVG(Dias_Antecipacao) AS DECIMAL(18,2))
        AS Antecipacao_Media_Dias,
    CAST(AVG(Frete) AS DECIMAL(18,2)) AS Frete_Medio_Registrado,
    CAST(
        100.0 * SUM(CASE WHEN Frete_Gratis = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Frete_Gratis_Pct,
    CAST(AVG(Avaliacao_Cliente) AS DECIMAL(10,2)) AS Avaliacao_Media,
    CASE
        WHEN COUNT_BIG(*) < 30 THEN N'Amostra pequena'
        ELSE N'Amostra suficiente para descrição'
    END AS Status_Amostra
FROM #Logistica_Entrega
GROUP BY Transportadora
ORDER BY Taxa_Atraso_Pct, Entregas DESC;
GO

/* 6. Desempenho por região. */
SELECT
    Regiao,
    COUNT_BIG(*) AS Entregas,
    COUNT(DISTINCT Cliente_SK) AS Clientes_Atendidos,
    CAST(AVG(Prazo_Real_Dias) AS DECIMAL(18,2)) AS Prazo_Real_Medio_Dias,
    CAST(
        100.0 * SUM(CASE WHEN Dias_Atraso > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Taxa_Atraso_Pct,
    CAST(
        AVG(CASE WHEN Dias_Atraso > 0 THEN Dias_Atraso END)
        AS DECIMAL(18,2)
    ) AS Atraso_Medio_Entre_Atrasadas,
    CAST(AVG(Frete) AS DECIMAL(18,2)) AS Frete_Medio_Registrado,
    CAST(AVG(Avaliacao_Cliente) AS DECIMAL(10,2)) AS Avaliacao_Media,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio
FROM #Logistica_Entrega
GROUP BY Regiao
ORDER BY Taxa_Atraso_Pct, Entregas DESC;
GO

/* 7. Cidade x nível de serviço.
   Grupos pequenos são sinalizados para impedir comparações frágeis. */
SELECT
    Regiao,
    Estado,
    Cidade,
    COUNT_BIG(*) AS Entregas,
    COUNT(DISTINCT Cliente_SK) AS Clientes_Atendidos,
    CAST(AVG(Prazo_Real_Dias) AS DECIMAL(18,2)) AS Prazo_Real_Medio_Dias,
    CAST(
        100.0 * SUM(CASE WHEN Dias_Atraso > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Taxa_Atraso_Pct,
    CAST(AVG(Frete) AS DECIMAL(18,2)) AS Frete_Medio_Registrado,
    CAST(AVG(Avaliacao_Cliente) AS DECIMAL(10,2)) AS Avaliacao_Media,
    CASE
        WHEN COUNT_BIG(*) < 30 THEN N'Amostra pequena'
        ELSE N'Amostra suficiente para descrição'
    END AS Status_Amostra
FROM #Logistica_Entrega
GROUP BY Regiao, Estado, Cidade
ORDER BY Entregas DESC, Taxa_Atraso_Pct;
GO

/* 8. Transportadora x região.
   Ajuda a separar efeito de cobertura geográfica de desempenho operacional. */
SELECT
    Regiao,
    Transportadora,
    COUNT_BIG(*) AS Entregas,
    CAST(AVG(Prazo_Real_Dias) AS DECIMAL(18,2)) AS Prazo_Real_Medio_Dias,
    CAST(
        100.0 * SUM(CASE WHEN Dias_Atraso > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Taxa_Atraso_Pct,
    CAST(
        AVG(CASE WHEN Dias_Atraso > 0 THEN Dias_Atraso END)
        AS DECIMAL(18,2)
    ) AS Atraso_Medio_Entre_Atrasadas,
    CAST(AVG(Frete) AS DECIMAL(18,2)) AS Frete_Medio_Registrado,
    CAST(AVG(Avaliacao_Cliente) AS DECIMAL(10,2)) AS Avaliacao_Media,
    CASE
        WHEN COUNT_BIG(*) < 30 THEN N'Amostra pequena'
        ELSE N'Amostra suficiente para descrição'
    END AS Status_Amostra
FROM #Logistica_Entrega
GROUP BY Regiao, Transportadora
ORDER BY Regiao, Entregas DESC;
GO

/* 9. Evolução mensal do nível de serviço. */
SELECT
    DATEFROMPARTS(
        YEAR(Data_Hora_Compra),
        MONTH(Data_Hora_Compra),
        1
    ) AS Mes_Referencia,
    COUNT_BIG(*) AS Entregas,
    CAST(AVG(Prazo_Real_Dias) AS DECIMAL(18,2)) AS Prazo_Real_Medio_Dias,
    CAST(
        100.0 * SUM(CASE WHEN Dias_Atraso > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Taxa_Atraso_Pct,
    CAST(
        AVG(CASE WHEN Dias_Atraso > 0 THEN Dias_Atraso END)
        AS DECIMAL(18,2)
    ) AS Atraso_Medio_Entre_Atrasadas,
    CAST(AVG(Frete) AS DECIMAL(18,2)) AS Frete_Medio_Registrado,
    CAST(AVG(Avaliacao_Cliente) AS DECIMAL(10,2)) AS Avaliacao_Media
FROM #Logistica_Entrega
GROUP BY YEAR(Data_Hora_Compra), MONTH(Data_Hora_Compra)
ORDER BY Mes_Referencia;
GO

/* 10. Severidade dos atrasos. */
WITH Faixas AS
(
    SELECT
        L.*,
        CASE
            WHEN Dias_Atraso IS NULL THEN N'Não informado'
            WHEN Dias_Atraso <= 0 THEN N'No prazo ou antecipada'
            WHEN Dias_Atraso = 1 THEN N'1 dia'
            WHEN Dias_Atraso <= 3 THEN N'2 a 3 dias'
            WHEN Dias_Atraso <= 7 THEN N'4 a 7 dias'
            ELSE N'Acima de 7 dias'
        END AS Faixa_Atraso,
        CASE
            WHEN Dias_Atraso IS NULL THEN 99
            WHEN Dias_Atraso <= 0 THEN 1
            WHEN Dias_Atraso = 1 THEN 2
            WHEN Dias_Atraso <= 3 THEN 3
            WHEN Dias_Atraso <= 7 THEN 4
            ELSE 5
        END AS Ordem_Faixa
    FROM #Logistica_Entrega AS L
)
SELECT
    Faixa_Atraso,
    COUNT_BIG(*) AS Entregas,
    CAST(
        100.0 * COUNT_BIG(*) / SUM(COUNT_BIG(*)) OVER ()
        AS DECIMAL(10,2)
    ) AS Participacao_Entregas_Pct,
    CAST(AVG(Avaliacao_Cliente) AS DECIMAL(10,2)) AS Avaliacao_Media,
    CAST(AVG(Frete) AS DECIMAL(18,2)) AS Frete_Medio_Registrado,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio
FROM Faixas
GROUP BY Faixa_Atraso, Ordem_Faixa
ORDER BY Ordem_Faixa;
GO

/* 11. Atraso x avaliação do cliente.
   A comparação é descritiva e não isola outros fatores da experiência. */
SELECT
    CASE
        WHEN Dias_Atraso > 0 THEN N'Atrasada'
        WHEN Dias_Atraso <= 0 THEN N'No prazo ou antecipada'
        ELSE N'Não informado'
    END AS Condicao_Prazo,
    COUNT_BIG(*) AS Entregas,
    COUNT(Avaliacao_Cliente) AS Avaliacoes_Validas,
    CAST(AVG(Avaliacao_Cliente) AS DECIMAL(10,2)) AS Avaliacao_Media,
    CAST(MIN(Avaliacao_Cliente) AS DECIMAL(10,2)) AS Menor_Avaliacao,
    CAST(MAX(Avaliacao_Cliente) AS DECIMAL(10,2)) AS Maior_Avaliacao,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(AVG(Quantidade_Itens) AS DECIMAL(18,2)) AS Itens_Medios_Pedido
FROM #Logistica_Entrega
GROUP BY
    CASE
        WHEN Dias_Atraso > 0 THEN N'Atrasada'
        WHEN Dias_Atraso <= 0 THEN N'No prazo ou antecipada'
        ELSE N'Não informado'
    END
ORDER BY Entregas DESC;
GO

/* 12. Frete gratuito x prazo, avaliação e valor do pedido.
   Não interpreta Frete como custo da empresa. */
SELECT
    CASE
        WHEN Frete_Gratis = 1 THEN N'Frete grátis'
        WHEN Frete_Gratis = 0 THEN N'Frete cobrado'
        ELSE N'Não informado'
    END AS Condicao_Frete,
    COUNT_BIG(*) AS Entregas,
    CAST(AVG(Frete) AS DECIMAL(18,2)) AS Frete_Medio_Registrado,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(AVG(Quantidade_Itens) AS DECIMAL(18,2)) AS Itens_Medios_Pedido,
    CAST(
        100.0 * SUM(CASE WHEN Dias_Atraso > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Taxa_Atraso_Pct,
    CAST(AVG(Avaliacao_Cliente) AS DECIMAL(10,2)) AS Avaliacao_Media,
    CAST(
        100.0 * SUM(Margem_Bruta) / NULLIF(SUM(Receita_Liquida), 0)
        AS DECIMAL(10,2)
    ) AS Margem_Bruta_Pct_Ponderada
FROM #Logistica_Entrega
GROUP BY Frete_Gratis
ORDER BY Entregas DESC;
GO

/* 13. Faixa de valor do pedido x comportamento logístico. */
WITH Faixas AS
(
    SELECT
        L.*,
        CASE
            WHEN Receita_Liquida < 50 THEN N'Abaixo de R$ 50'
            WHEN Receita_Liquida < 100 THEN N'R$ 50 a R$ 99,99'
            WHEN Receita_Liquida < 200 THEN N'R$ 100 a R$ 199,99'
            ELSE N'R$ 200 ou mais'
        END AS Faixa_Receita,
        CASE
            WHEN Receita_Liquida < 50 THEN 1
            WHEN Receita_Liquida < 100 THEN 2
            WHEN Receita_Liquida < 200 THEN 3
            ELSE 4
        END AS Ordem_Faixa
    FROM #Logistica_Entrega AS L
)
SELECT
    Faixa_Receita,
    COUNT_BIG(*) AS Entregas,
    CAST(AVG(Receita_Liquida) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(AVG(Prazo_Real_Dias) AS DECIMAL(18,2)) AS Prazo_Real_Medio_Dias,
    CAST(
        100.0 * SUM(CASE WHEN Dias_Atraso > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Taxa_Atraso_Pct,
    CAST(AVG(Frete) AS DECIMAL(18,2)) AS Frete_Medio_Registrado,
    CAST(
        100.0 * SUM(CASE WHEN Frete_Gratis = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Frete_Gratis_Pct,
    CAST(AVG(Avaliacao_Cliente) AS DECIMAL(10,2)) AS Avaliacao_Media
FROM Faixas
GROUP BY Faixa_Receita, Ordem_Faixa
ORDER BY Ordem_Faixa;
GO

/* 14. Trinta entregas com maior atraso para investigação operacional.
   O resultado é uma fila de diagnóstico, não uma regra de exclusão. */
SELECT TOP (30)
    Pedido_ID,
    Cliente_SK,
    Data_Hora_Compra,
    Transportadora,
    Cidade,
    Estado,
    Regiao,
    CAST(Prazo_Prometido_Dias AS DECIMAL(18,2)) AS Prazo_Prometido_Dias,
    CAST(Prazo_Real_Dias AS DECIMAL(18,2)) AS Prazo_Real_Dias,
    CAST(Dias_Atraso AS DECIMAL(18,2)) AS Dias_Atraso,
    Status_Entrega_Calculado,
    CAST(Frete AS DECIMAL(18,2)) AS Frete_Registrado,
    Frete_Gratis,
    CAST(Avaliacao_Cliente AS DECIMAL(10,2)) AS Avaliacao_Cliente,
    CAST(Receita_Liquida AS DECIMAL(18,2)) AS Receita_Liquida
FROM #Logistica_Entrega
WHERE Dias_Atraso > 0
ORDER BY Dias_Atraso DESC, Receita_Liquida DESC;
GO

/* 15. Cobertura das principais variáveis logísticas. */
SELECT
    V.Variavel,
    COUNT_BIG(*) AS Entregas,
    SUM(CASE WHEN V.Valor IS NULL THEN 1 ELSE 0 END) AS Valores_Nulos,
    CAST(
        100.0 * SUM(CASE WHEN V.Valor IS NULL THEN 1 ELSE 0 END)
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Nulos_Pct
FROM #Logistica_Entrega AS L
CROSS APPLY
(
    VALUES
        (N'Frete', L.Frete),
        (N'Prazo_Prometido_Dias', L.Prazo_Prometido_Dias),
        (N'Prazo_Real_Dias', L.Prazo_Real_Dias),
        (N'Dias_Atraso', L.Dias_Atraso),
        (N'Dias_Antecipacao', L.Dias_Antecipacao),
        (N'Avaliacao_Cliente', L.Avaliacao_Cliente)
) AS V (Variavel, Valor)
GROUP BY V.Variavel
ORDER BY V.Variavel;
GO

DROP TABLE IF EXISTS #Logistica_Entrega;
GO
