USE [CustomerAnalyticsHub];
GO

-- ==============================================================================
-- VALIDAÇÃO DE PERFORMANCE DO MODELO PREDITIVO (MÉTRICAS MATEMÁTICAS)
-- ==============================================================================

WITH AvaliacaoErro AS (
    SELECT 
        Receita_Real_Observada,
        LTV_Preditivo_Estimado,
        -- Erro Residual
        (Receita_Real_Observada - LTV_Preditivo_Estimado)              AS Residuo,
        SQUARE(Receita_Real_Observada - LTV_Preditivo_Estimado)       AS Residuo_Quadrado,
        ABS(Receita_Real_Observada - LTV_Preditivo_Estimado)          AS Erro_Absoluto,
        -- Variância Total em Relação à Média
        SQUARE(Receita_Real_Observada - (SELECT AVG(Receita_Real_Observada) FROM eda.stg_resultados_preditivos_geral)) AS Variancia_Total
    FROM eda.stg_resultados_preditivos_geral
)
SELECT 
    COUNT(*)                                                           AS Total_Amostra,
    -- Erro Médio Absoluto em Reais (MAE)
    ROUND(AVG(Erro_Absoluto), 2)                                       AS MAE_Erro_Medio_Reais,
    -- Raiz do Erro Quadrático Médio (RMSE)
    ROUND(SQRT(AVG(Residuo_Quadrado)), 2)                              AS RMSE_Reais,
    -- Coeficiente de Determinação (R-Quadrado)
    ROUND(1 - (SUM(Residuo_Quadrado) / NULLIF(SUM(Variancia_Total), 0)), 4) AS R_Quadrado_Ajustado
FROM AvaliacaoErro;