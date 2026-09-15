USE [CustomerAnalyticsHub];
GO

-- ==============================================================================
-- 08. MODELO PREDITIVO GERAL: REGRESSÃO MÚLTIPLA PARA PREVISÃO DE LTV
-- ==============================================================================

-- 1. Limpeza de tabelas temporárias e de destino anteriores
DROP TABLE IF EXISTS eda.stg_resultados_preditivos_geral;
DROP TABLE IF EXISTS #temp_coeficientes_ltv;
GO

-- 2. Cálculo de métricas e coeficientes (Betas) em tabela temporária
WITH MetricasEstatisticas AS (
    SELECT 
        AVG(CAST(X_Recencia_Dias AS FLOAT))      AS avg_rec,
        AVG(CAST(X_Freq_Pedidos AS FLOAT))       AS avg_freq,
        AVG(CAST(X_Ticket_Medio AS FLOAT))       AS avg_ticket,
        AVG(CAST(Y_Receita_Futura AS FLOAT))     AS avg_y,
        
        -- Variâncias populacionais
        ISNULL(VARP(CAST(X_Recencia_Dias AS FLOAT)), 0) AS var_rec,
        ISNULL(VARP(CAST(X_Freq_Pedidos AS FLOAT)), 0)  AS var_freq,
        ISNULL(VARP(CAST(X_Ticket_Medio AS FLOAT)), 0)  AS var_ticket
    FROM eda.stg_dataset_preditivo_geral
)
SELECT 
    m.avg_y,
    m.avg_rec,
    m.avg_freq,
    m.avg_ticket,
    
    -- Coeficiente Beta Recência
    CASE 
        WHEN m.var_rec = 0 THEN 0 
        ELSE (AVG(CAST(d.X_Recencia_Dias AS FLOAT) * CAST(d.Y_Receita_Futura AS FLOAT)) - (m.avg_rec * m.avg_y)) / m.var_rec 
    END AS Beta_Recencia,

    -- Coeficiente Beta Frequência
    CASE 
        WHEN m.var_freq = 0 THEN 0 
        ELSE (AVG(CAST(d.X_Freq_Pedidos AS FLOAT) * CAST(d.Y_Receita_Futura AS FLOAT)) - (m.avg_freq * m.avg_y)) / m.var_freq 
    END AS Beta_Frequencia,

    -- Coeficiente Beta Ticket Médio
    CASE 
        WHEN m.var_ticket = 0 THEN 0 
        ELSE (AVG(CAST(d.X_Ticket_Medio AS FLOAT) * CAST(d.Y_Receita_Futura AS FLOAT)) - (m.avg_ticket * m.avg_y)) / m.var_ticket 
    END AS Beta_TicketMedio
INTO #temp_coeficientes_ltv
FROM eda.stg_dataset_preditivo_geral d
CROSS JOIN MetricasEstatisticas m
GROUP BY m.avg_y, m.avg_rec, m.avg_freq, m.avg_ticket, m.var_rec, m.var_freq, m.var_ticket;

-- 3. Aplicação do modelo preditivo e persistência na stg_resultados_preditivos_geral
SELECT 
    d.Cliente_SK,
    d.X_Recencia_Dias,
    d.X_Freq_Pedidos,
    d.X_Ticket_Medio,
    d.Y_Receita_Futura AS Receita_Real_Observada,
    
    -- Cálculo do LTV Preditivo Estimado com trava de piso zero
    ROUND(
        CASE 
            WHEN (c.avg_y 
                  + c.Beta_Recencia * (CAST(d.X_Recencia_Dias AS FLOAT) - c.avg_rec) 
                  + c.Beta_Frequencia * (CAST(d.X_Freq_Pedidos AS FLOAT) - c.avg_freq) 
                  + c.Beta_TicketMedio * (CAST(d.X_Ticket_Medio AS FLOAT) - c.avg_ticket)
                 ) < 0 THEN 0.00
            ELSE (c.avg_y 
                  + c.Beta_Recencia * (CAST(d.X_Recencia_Dias AS FLOAT) - c.avg_rec) 
                  + c.Beta_Frequencia * (CAST(d.X_Freq_Pedidos AS FLOAT) - c.avg_freq) 
                  + c.Beta_TicketMedio * (CAST(d.X_Ticket_Medio AS FLOAT) - c.avg_ticket)
                 )
        END
    , 2) AS LTV_Preditivo_Estimado
INTO eda.stg_resultados_preditivos_geral
FROM eda.stg_dataset_preditivo_geral d
CROSS JOIN #temp_coeficientes_ltv c;
GO

-- 4. Exibição de verificação dos resultados
SELECT TOP 15 
    Cliente_SK,
    X_Recencia_Dias            AS Recencia_Dias,
    X_Freq_Pedidos             AS Total_Pedidos_Historico,
    X_Ticket_Medio             AS Ticket_Medio_Historico,
    Receita_Real_Observada     AS Receita_Real_Futura,
    LTV_Preditivo_Estimado     AS LTV_Preditivo_Calculado
FROM eda.stg_resultados_preditivos_geral
ORDER BY LTV_Preditivo_Estimado DESC;