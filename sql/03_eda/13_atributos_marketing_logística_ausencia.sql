USE CustomerAnalyticsHub;
GO

WITH Marketing AS
(
    SELECT
        N'Marketing' AS Area,
        V.Atributo,
        COUNT_BIG(*) AS Total_Registros,
        SUM(
            CASE
                WHEN V.Valor IS NULL
                  OR LTRIM(RTRIM(V.Valor)) = N''
                THEN 1 ELSE 0
            END
        ) AS Valores_Ausentes
    FROM gold.fato_pedido AS FP
    INNER JOIN gold.dim_canal_marketing AS CM
        ON CM.Canal_Marketing_SK = FP.Canal_Marketing_SK
    INNER JOIN gold.dim_campanha AS CP
        ON CP.Campanha_SK = FP.Campanha_SK
    INNER JOIN gold.dim_evento_externo AS EE
        ON EE.Evento_Externo_SK = FP.Evento_Externo_SK
    CROSS APPLY
    (
        VALUES
            (N'Canal_Marketing',
             CONVERT(NVARCHAR(255), CM.Canal_Marketing)),

            (N'Campanha',
             CONVERT(NVARCHAR(255), CP.Campanha)),

            (N'Evento_Externo',
             CONVERT(NVARCHAR(255), EE.Evento_Externo)),

            (N'Cupom_Status',
             CONVERT(NVARCHAR(255), FP.Cupom_Status))
    ) AS V (Atributo, Valor)
    GROUP BY V.Atributo
),
Logistica AS
(
    SELECT
        N'Logística' AS Area,
        V.Atributo,
        COUNT_BIG(*) AS Total_Registros,
        SUM(
            CASE WHEN V.Valor IS NULL
                 THEN 1 ELSE 0 END
        ) AS Valores_Ausentes
    FROM gold.fato_entrega AS FE
    CROSS APPLY
    (
        VALUES
            (N'Frete',
             CONVERT(FLOAT, FE.Frete)),

            (N'Prazo_Entrega_Prometido',
             CONVERT(FLOAT, FE.Prazo_Entrega_Prometido_Dias)),

            (N'Prazo_Entrega_Real',
             CONVERT(FLOAT, FE.Prazo_Entrega_Real_Dias)),

            (N'Dias_Atraso',
             CONVERT(FLOAT, FE.Dias_Atraso)),

            (N'Dias_Antecipacao',
             CONVERT(FLOAT, FE.Dias_Antecipacao)),

            (N'Avaliacao_Cliente',
             CONVERT(FLOAT, FE.Avaliacao_Cliente))
    ) AS V (Atributo, Valor)
    GROUP BY V.Atributo
),
Resultado AS
(
    SELECT * FROM Marketing

    UNION ALL

    SELECT * FROM Logistica
)
SELECT
    Area,
    Atributo,
    Total_Registros,
    Valores_Ausentes,
    CAST(
        100.0 * Valores_Ausentes /
        NULLIF(Total_Registros, 0)
        AS DECIMAL(10,2)
    ) AS Ausencia_Pct
FROM Resultado
ORDER BY
    Ausencia_Pct DESC,
    Area,
    Atributo;