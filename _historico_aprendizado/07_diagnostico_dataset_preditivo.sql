USE [CustomerAnalyticsHub];
GO

-- ==============================================================================
-- DIAGNÓSTICO E DISTRIBUIÇÃO DAS VARIÁVEIS DO MODELO PREDITIVO GERAL
-- ==============================================================================

SELECT 
    COUNT(*)                                            AS N_Clientes,
    
    -- Diagnóstico da Variável Alvo Contínua (LTV Futuro)
    ROUND(AVG(Y_Receita_Futura), 2)                     AS Y_LTV_Medio_Futuro,
    ROUND(STDEV(Y_Receita_Futura), 2)                   AS Y_LTV_DesvioPadrao,
    ROUND(MIN(Y_Receita_Futura), 2)                     AS Y_LTV_Min,
    ROUND(MAX(Y_Receita_Futura), 2)                     AS Y_LTV_Max,
    
    -- Diagnóstico da Variável Alvo Categórica (Taxa de Churn 6M)
    SUM(Y_Churn_Binario)                                AS Total_Churns,
    ROUND(AVG(CAST(Y_Churn_Binario AS DECIMAL(5,4))) * 100, 2) AS Taxa_Churn_Percentual,
    
    -- Comportamento dos Previsores Principais (X)
    ROUND(AVG(X_Recencia_Dias), 1)                      AS X_Recencia_Media_Dias,
    ROUND(AVG(X_Freq_Pedidos), 1)                       AS X_Frequencia_Media_Pedidos,
    ROUND(AVG(X_Ticket_Medio), 2)                       AS X_Ticket_Medio_Historico
FROM eda.stg_dataset_preditivo_geral;