USE CustomerAnalyticsHub;
GO

SELECT
    COUNT_BIG(*) AS Clientes_Sem_Intervalo_Calculavel,
    CAST(
        100.0 * COUNT_BIG(*) /
        NULLIF((SELECT COUNT_BIG(*)
                FROM eda.vw_perfil_cliente_analytics), 0)
        AS DECIMAL(10,2)
    ) AS Percentual_Dos_Clientes
FROM eda.vw_perfil_cliente_analytics
WHERE Intervalo_Medio_Calculado IS NULL;