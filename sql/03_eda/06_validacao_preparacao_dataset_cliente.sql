USE [CustomerAnalyticsHub];
GO
SET NOCOUNT ON;
GO

/* ============================================================
   EDA 06 — VALIDAÇÃO E PREPARAÇÃO DO DATASET DE CLIENTES

   Fontes:
   - eda.vw_perfil_cliente_analytics: uma linha por cliente;
   - tabelas Gold: reconciliação independente.

   Este arquivo não cria clusters, não imputa valores e não inventa
   status. Ele apenas valida a visão e disponibiliza variáveis brutas
   com indicadores transparentes de elegibilidade.
   ============================================================ */

/* 1. Dataset reutilizável para segmentação e análises posteriores. */
CREATE OR ALTER VIEW eda.vw_dataset_segmentacao_cliente
AS
SELECT
    V.Cliente_SK,
    V.Cliente_ID,
    V.Genero,
    V.Idade,
    V.Estado_Civil,
    V.Escolaridade,
    V.Situacao_Profissional,
    V.Profissao,
    V.Tempo_Experiencia_Anos,
    V.Renda_Mensal_Cliente,
    V.Cidade,
    V.Estado,
    V.Regiao,
    V.Total_Pedidos_Calculado,
    V.Total_Itens_Comprados,
    V.Produtos_Distintos_Comprados,
    V.Categorias_Distintas_Compradas,
    V.Valor_Total_Gasto,
    V.Custo_Total,
    V.Margem_Bruta_Total,
    V.Margem_Percentual_Ponderada,
    V.Ticket_Medio_Calculado,
    V.Recencia_Dias_Calculada,
    V.Intervalo_Medio_Calculado,
    V.Pontos_Fidelidade_Ultimo_Observado,
    V.Categoria_Favorita_Observada,
    V.Percentual_Entregas_Atrasadas,
    V.Avaliacao_Media,
    V.Data_Referencia_Analise,

    CASE WHEN V.Renda_Mensal_Cliente = 0 THEN 1 ELSE 0 END
        AS Flag_Renda_Zero,

    CASE WHEN V.Intervalo_Medio_Calculado IS NULL THEN 1 ELSE 0 END
        AS Flag_Intervalo_Indisponivel,

    CASE
        WHEN V.Idade IS NOT NULL
         AND V.Renda_Mensal_Cliente IS NOT NULL
         AND V.Total_Pedidos_Calculado > 0
         AND V.Valor_Total_Gasto IS NOT NULL
         AND V.Ticket_Medio_Calculado IS NOT NULL
         AND V.Recencia_Dias_Calculada IS NOT NULL
            THEN 1
        ELSE 0
    END AS Elegivel_Segmentacao_Base
FROM eda.vw_perfil_cliente_analytics AS V;
GO


/* 2. Existência das duas views. */
SELECT
    OBJECT_ID('eda.vw_perfil_cliente_analytics', 'V') AS ID_View_Perfil,
    OBJECT_ID('eda.vw_dataset_segmentacao_cliente', 'V') AS ID_View_Dataset,
    CASE
        WHEN OBJECT_ID('eda.vw_perfil_cliente_analytics', 'V') IS NOT NULL
         AND OBJECT_ID('eda.vw_dataset_segmentacao_cliente', 'V') IS NOT NULL
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS Status_Existencia;
GO


/* 3. Granularidade: exatamente uma linha por cliente. */
SELECT
    COUNT_BIG(*) AS Linhas_Dataset,
    COUNT(DISTINCT Cliente_SK) AS Clientes_Distintos,
    COUNT_BIG(*) - COUNT(DISTINCT Cliente_SK) AS Linhas_Excedentes,
    CASE
        WHEN COUNT_BIG(*) = 330
         AND COUNT(DISTINCT Cliente_SK) = 330
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS Status_Granularidade
FROM eda.vw_dataset_segmentacao_cliente;
GO


/* 4. Reconciliação do dataset com as fatos Gold. */
SELECT
    SUM(D.Total_Pedidos_Calculado) AS Pedidos_Dataset,
    (SELECT COUNT_BIG(*) FROM gold.fato_pedido) AS Pedidos_Gold,
    SUM(D.Total_Itens_Comprados) AS Itens_Dataset,
    (SELECT SUM(F.Quantidade_Total_Itens) FROM gold.fato_pedido AS F) AS Itens_Gold,
    CAST
    (
        SUM(D.Valor_Total_Gasto)
        - (SELECT SUM(F.Valor_Liquido_Pedido) FROM gold.fato_pedido AS F)
        AS DECIMAL(18,2)
    ) AS Diferenca_Receita,
    CAST
    (
        SUM(D.Margem_Bruta_Total)
        - (SELECT SUM(F.Margem_Bruta_Pedido) FROM gold.fato_pedido AS F)
        AS DECIMAL(18,2)
    ) AS Diferenca_Margem,
    CASE
        WHEN SUM(D.Total_Pedidos_Calculado)
             = (SELECT COUNT_BIG(*) FROM gold.fato_pedido)
         AND SUM(D.Total_Itens_Comprados)
             = (SELECT SUM(F.Quantidade_Total_Itens) FROM gold.fato_pedido AS F)
         AND ABS
             (
                 SUM(D.Valor_Total_Gasto)
                 - (SELECT SUM(F.Valor_Liquido_Pedido)
                    FROM gold.fato_pedido AS F)
             ) <= 0.01
         AND ABS
             (
                 SUM(D.Margem_Bruta_Total)
                 - (SELECT SUM(F.Margem_Bruta_Pedido)
                    FROM gold.fato_pedido AS F)
             ) <= 0.01
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS Status_Reconciliacao
FROM eda.vw_dataset_segmentacao_cliente AS D;
GO


/* 5. Coerência matemática por cliente. */
SELECT
    SUM(CASE WHEN Total_Pedidos_Calculado < 0 THEN 1 ELSE 0 END)
        AS Clientes_Pedidos_Negativos,
    SUM(CASE WHEN Total_Itens_Comprados < 0 THEN 1 ELSE 0 END)
        AS Clientes_Itens_Negativos,
    SUM(CASE WHEN Valor_Total_Gasto < 0 THEN 1 ELSE 0 END)
        AS Clientes_Receita_Negativa,
    SUM(CASE WHEN Recencia_Dias_Calculada < 0 THEN 1 ELSE 0 END)
        AS Clientes_Recencia_Negativa,
    SUM
    (
        CASE
            WHEN ABS
                 (
                     Margem_Bruta_Total
                     - (Valor_Total_Gasto - Custo_Total)
                 ) > 0.01
                THEN 1
            ELSE 0
        END
    ) AS Clientes_Margem_Incoerente,
    CASE
        WHEN SUM(CASE WHEN Total_Pedidos_Calculado < 0 THEN 1 ELSE 0 END) = 0
         AND SUM(CASE WHEN Total_Itens_Comprados < 0 THEN 1 ELSE 0 END) = 0
         AND SUM(CASE WHEN Valor_Total_Gasto < 0 THEN 1 ELSE 0 END) = 0
         AND SUM(CASE WHEN Recencia_Dias_Calculada < 0 THEN 1 ELSE 0 END) = 0
         AND SUM
             (
                 CASE
                     WHEN ABS
                          (
                              Margem_Bruta_Total
                              - (Valor_Total_Gasto - Custo_Total)
                          ) > 0.01
                         THEN 1
                     ELSE 0
                 END
             ) = 0
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS Status_Coerencia
FROM eda.vw_dataset_segmentacao_cliente;
GO


/* 6. Cobertura das variáveis candidatas à segmentação. */
WITH Base_Long AS
(
    SELECT
        D.Cliente_SK,
        V.Variavel,
        V.Valor
    FROM eda.vw_dataset_segmentacao_cliente AS D
    CROSS APPLY
    (
        VALUES
            ('Idade', CONVERT(FLOAT, D.Idade)),
            ('Renda_Mensal_Cliente', CONVERT(FLOAT, D.Renda_Mensal_Cliente)),
            ('Tempo_Experiencia_Anos', CONVERT(FLOAT, D.Tempo_Experiencia_Anos)),
            ('Total_Pedidos_Calculado', CONVERT(FLOAT, D.Total_Pedidos_Calculado)),
            ('Total_Itens_Comprados', CONVERT(FLOAT, D.Total_Itens_Comprados)),
            ('Produtos_Distintos_Comprados', CONVERT(FLOAT, D.Produtos_Distintos_Comprados)),
            ('Valor_Total_Gasto', CONVERT(FLOAT, D.Valor_Total_Gasto)),
            ('Ticket_Medio_Calculado', CONVERT(FLOAT, D.Ticket_Medio_Calculado)),
            ('Recencia_Dias_Calculada', CONVERT(FLOAT, D.Recencia_Dias_Calculada)),
            ('Intervalo_Medio_Calculado', CONVERT(FLOAT, D.Intervalo_Medio_Calculado)),
            ('Percentual_Entregas_Atrasadas', CONVERT(FLOAT, D.Percentual_Entregas_Atrasadas)),
            ('Avaliacao_Media', CONVERT(FLOAT, D.Avaliacao_Media))
    ) AS V (Variavel, Valor)
)
SELECT
    Variavel,
    COUNT_BIG(*) AS Total_Clientes,
    COUNT(Valor) AS Valores_Validos,
    SUM(CASE WHEN Valor IS NULL THEN 1 ELSE 0 END) AS Valores_Ausentes,
    CAST
    (
        100.0 * COUNT(Valor) / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(10,2)
    ) AS Percentual_Cobertura,
    CASE
        WHEN 100.0 * COUNT(Valor) / NULLIF(COUNT_BIG(*), 0) >= 95
            THEN 'COBERTURA ALTA'
        WHEN 100.0 * COUNT(Valor) / NULLIF(COUNT_BIG(*), 0) >= 80
            THEN 'COBERTURA MODERADA'
        ELSE 'COBERTURA BAIXA'
    END AS Classificacao_Cobertura
FROM Base_Long
GROUP BY Variavel
ORDER BY Percentual_Cobertura DESC, Variavel;
GO


/* 7. Elegibilidade sem imputação artificial. */
SELECT
    Elegivel_Segmentacao_Base,
    CASE
        WHEN Elegivel_Segmentacao_Base = 1 THEN 'ELEGIVEL'
        ELSE 'NAO ELEGIVEL'
    END AS Classificacao,
    COUNT_BIG(*) AS Clientes,
    CAST
    (
        100.0 * COUNT_BIG(*) / SUM(COUNT_BIG(*)) OVER ()
        AS DECIMAL(10,2)
    ) AS Percentual_Clientes
FROM eda.vw_dataset_segmentacao_cliente
GROUP BY Elegivel_Segmentacao_Base
ORDER BY Elegivel_Segmentacao_Base DESC;
GO


/* 8. Limitações conhecidas preservadas. */
SELECT
    SUM(Flag_Renda_Zero) AS Clientes_Renda_Zero,
    SUM(Flag_Intervalo_Indisponivel) AS Clientes_Sem_Intervalo_Calculavel,
    SUM(CASE WHEN Avaliacao_Media IS NULL THEN 1 ELSE 0 END)
        AS Clientes_Sem_Avaliacao,
    SUM(CASE WHEN Categoria_Favorita_Observada IS NULL THEN 1 ELSE 0 END)
        AS Clientes_Sem_Categoria_Observada,
    'Ciclo_Vida_Informado excluido: cobertura igual a zero' AS Observacao_Ciclo_Vida
FROM eda.vw_dataset_segmentacao_cliente;
GO
