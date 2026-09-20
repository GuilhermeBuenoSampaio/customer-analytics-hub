USE CustomerAnalyticsHub;
GO

SELECT
    COUNT_BIG(*) AS Total_Clientes,

    SUM(
        CASE WHEN Avaliacao_Media IS NULL
             THEN 1 ELSE 0 END
    ) AS Clientes_Sem_Avaliacao_Media,

    SUM(
        CASE WHEN Categoria_Favorita_Observada IS NULL
             THEN 1 ELSE 0 END
    ) AS Clientes_Sem_Categoria_Favorita,

    SUM(
        CASE
            WHEN Avaliacao_Media IS NULL
              OR Categoria_Favorita_Observada IS NULL
            THEN 1 ELSE 0
        END
    ) AS Clientes_Sem_Uma_Ou_Mais_Informacoes,

    SUM(
        CASE
            WHEN Avaliacao_Media IS NULL
             AND Categoria_Favorita_Observada IS NULL
            THEN 1 ELSE 0
        END
    ) AS Clientes_Sem_Ambas_Informacoes,

    CAST(
        100.0 * SUM(
            CASE
                WHEN Avaliacao_Media IS NULL
                  OR Categoria_Favorita_Observada IS NULL
                THEN 1 ELSE 0
            END
        ) / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Percentual_Sem_Uma_Ou_Mais

FROM eda.vw_perfil_cliente_analytics;