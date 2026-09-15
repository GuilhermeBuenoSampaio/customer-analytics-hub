USE [CustomerAnalyticsHub];
GO

SET NOCOUNT ON;
GO

/* ============================================================
   CUSTOMER ANALYTICS HUB
   EDA GERAL — ETAPA 01
   VISÃO GERAL E INTEGRIDADE DO MODELO GOLD

   Objetivos:
   1. Validar a volumetria das 14 tabelas Gold.
   2. Verificar PKs e FKs criadas no SQL Server.
   3. Verificar FKs nulas nas tabelas fato.
   4. Verificar duplicidades no grão de cada tabela.
   ============================================================ */


/* ============================================================
   1. VOLUMETRIA DAS 14 TABELAS GOLD
   ============================================================ */

SELECT
    Resultado.Tabela,
    Resultado.Tipo_Tabela,
    Resultado.Total_Linhas,
    Resultado.Total_Esperado,
    CASE
        WHEN Resultado.Total_Esperado IS NULL
            THEN 'INFORMATIVO'
        WHEN Resultado.Total_Linhas = Resultado.Total_Esperado
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS Status_Validacao
FROM
(
    SELECT
        'gold.dim_cliente' AS Tabela,
        'DIMENSAO' AS Tipo_Tabela,
        COUNT_BIG(*) AS Total_Linhas,
        CAST(330 AS BIGINT) AS Total_Esperado
    FROM gold.dim_cliente

    UNION ALL

    SELECT
        'gold.dim_produto',
        'DIMENSAO',
        COUNT_BIG(*),
        CAST(36 AS BIGINT)
    FROM gold.dim_produto

    UNION ALL

    SELECT
        'gold.dim_geografia',
        'DIMENSAO',
        COUNT_BIG(*),
        CAST(15 AS BIGINT)
    FROM gold.dim_geografia

    UNION ALL

    SELECT
        'gold.dim_data',
        'DIMENSAO',
        COUNT_BIG(*),
        CAST(365 AS BIGINT)
    FROM gold.dim_data

    UNION ALL

    SELECT
        'gold.dim_horario',
        'DIMENSAO',
        COUNT_BIG(*),
        CAST(1440 AS BIGINT)
    FROM gold.dim_horario

    UNION ALL

    SELECT
        'gold.dim_pagamento',
        'DIMENSAO',
        COUNT_BIG(*),
        CAST(5 AS BIGINT)
    FROM gold.dim_pagamento

    UNION ALL

    SELECT
        'gold.dim_campanha',
        'DIMENSAO',
        COUNT_BIG(*),
        CAST(6 AS BIGINT)
    FROM gold.dim_campanha

    UNION ALL

    SELECT
        'gold.dim_canal_marketing',
        'DIMENSAO',
        COUNT_BIG(*),
        CAST(9 AS BIGINT)
    FROM gold.dim_canal_marketing

    UNION ALL

    SELECT
        'gold.dim_evento_externo',
        'DIMENSAO',
        COUNT_BIG(*),
        CAST(4 AS BIGINT)
    FROM gold.dim_evento_externo

    UNION ALL

    SELECT
        'gold.dim_transportadora',
        'DIMENSAO',
        COUNT_BIG(*),
        CAST(5 AS BIGINT)
    FROM gold.dim_transportadora

    UNION ALL

    SELECT
        'gold.fato_item_pedido',
        'FATO',
        COUNT_BIG(*),
        CAST(6495 AS BIGINT)
    FROM gold.fato_item_pedido

    UNION ALL

    SELECT
        'gold.fato_pedido',
        'FATO',
        COUNT_BIG(*),
        CAST(2789 AS BIGINT)
    FROM gold.fato_pedido

    UNION ALL

    SELECT
        'gold.fato_entrega',
        'FATO',
        COUNT_BIG(*),
        CAST(2789 AS BIGINT)
    FROM gold.fato_entrega

    UNION ALL

    SELECT
        'gold.fato_cliente_mes',
        'FATO',
        COUNT_BIG(*),
        CAST(NULL AS BIGINT)
    FROM gold.fato_cliente_mes
) AS Resultado
ORDER BY
    Resultado.Tipo_Tabela,
    Resultado.Tabela;
GO


/* ============================================================
   2. VALIDAÇÃO DAS CHAVES PRIMÁRIAS — PKs

   Resultado esperado:
   - 14 tabelas Gold;
   - 14 tabelas com PK;
   - 0 tabelas sem PK.
   ============================================================ */

SELECT
    COUNT(DISTINCT T.object_id) AS Total_Tabelas_Gold,

    COUNT(
        DISTINCT CASE
            WHEN PK.object_id IS NOT NULL
            THEN T.object_id
        END
    ) AS Tabelas_Com_PK,

    COUNT(DISTINCT T.object_id)
    -
    COUNT(
        DISTINCT CASE
            WHEN PK.object_id IS NOT NULL
            THEN T.object_id
        END
    ) AS Tabelas_Sem_PK,

    CASE
        WHEN COUNT(DISTINCT T.object_id) = 14
         AND COUNT(
                DISTINCT CASE
                    WHEN PK.object_id IS NOT NULL
                    THEN T.object_id
                END
             ) = 14
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS Status_Validacao
FROM sys.tables AS T
INNER JOIN sys.schemas AS S
    ON S.schema_id = T.schema_id
LEFT JOIN sys.key_constraints AS PK
    ON PK.parent_object_id = T.object_id
   AND PK.type = 'PK'
WHERE S.name = 'gold';
GO


/* ============================================================
   3. DETALHAMENTO DAS CHAVES PRIMÁRIAS
   ============================================================ */

SELECT
    S.name AS Schema_Nome,
    T.name AS Tabela,
    PK.name AS Nome_PK,
    C.name AS Coluna_PK,
    IC.key_ordinal AS Ordem_Coluna
FROM sys.key_constraints AS PK
INNER JOIN sys.tables AS T
    ON T.object_id = PK.parent_object_id
INNER JOIN sys.schemas AS S
    ON S.schema_id = T.schema_id
INNER JOIN sys.index_columns AS IC
    ON IC.object_id = T.object_id
   AND IC.index_id = PK.unique_index_id
INNER JOIN sys.columns AS C
    ON C.object_id = IC.object_id
   AND C.column_id = IC.column_id
WHERE
    S.name = 'gold'
    AND PK.type = 'PK'
ORDER BY
    T.name,
    IC.key_ordinal;
GO


/* ============================================================
   4. VALIDAÇÃO DAS CHAVES ESTRANGEIRAS — FKs

   Resultado esperado:
   - 22 relacionamentos;
   - 0 FKs desabilitadas;
   - 0 FKs não confiáveis.
   ============================================================ */

SELECT
    COUNT(*) AS Total_Chaves_Estrangeiras,

    SUM(
        CASE
            WHEN FK.is_disabled = 1 THEN 1
            ELSE 0
        END
    ) AS FKs_Desabilitadas,

    SUM(
        CASE
            WHEN FK.is_not_trusted = 1 THEN 1
            ELSE 0
        END
    ) AS FKs_Nao_Confiaveis,

    CASE
        WHEN COUNT(*) = 22
         AND SUM(CASE WHEN FK.is_disabled = 1 THEN 1 ELSE 0 END) = 0
         AND SUM(CASE WHEN FK.is_not_trusted = 1 THEN 1 ELSE 0 END) = 0
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS Status_Validacao
FROM sys.foreign_keys AS FK
INNER JOIN sys.tables AS T
    ON T.object_id = FK.parent_object_id
INNER JOIN sys.schemas AS S
    ON S.schema_id = T.schema_id
WHERE S.name = 'gold';
GO


/* ============================================================
   5. DETALHAMENTO DOS RELACIONAMENTOS ENTRE FATOS E DIMENSÕES
   ============================================================ */

SELECT
    SF.name + '.' + TF.name AS Tabela_Fato,
    CF.name AS Coluna_FK,
    SD.name + '.' + TD.name AS Tabela_Dimensao,
    CD.name AS Coluna_Referenciada,
    FK.name AS Nome_FK,

    CASE
        WHEN FK.is_disabled = 0
         AND FK.is_not_trusted = 0
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS Status_Relacionamento
FROM sys.foreign_keys AS FK
INNER JOIN sys.foreign_key_columns AS FKC
    ON FKC.constraint_object_id = FK.object_id
INNER JOIN sys.tables AS TF
    ON TF.object_id = FK.parent_object_id
INNER JOIN sys.schemas AS SF
    ON SF.schema_id = TF.schema_id
INNER JOIN sys.columns AS CF
    ON CF.object_id = TF.object_id
   AND CF.column_id = FKC.parent_column_id
INNER JOIN sys.tables AS TD
    ON TD.object_id = FK.referenced_object_id
INNER JOIN sys.schemas AS SD
    ON SD.schema_id = TD.schema_id
INNER JOIN sys.columns AS CD
    ON CD.object_id = TD.object_id
   AND CD.column_id = FKC.referenced_column_id
WHERE SF.name = 'gold'
ORDER BY
    TF.name,
    CF.name;
GO


/* ============================================================
   6. NULOS NAS CHAVES ESTRANGEIRAS DAS TABELAS FATO

   Como os relacionamentos são obrigatórios, o resultado esperado
   é zero em Total_FKs_Nulas para todas as tabelas.
   ============================================================ */

SELECT
    Resultado.Tabela,
    Resultado.Total_Linhas,
    Resultado.Quantidade_FKs,
    Resultado.Total_FKs_Nulas,

    CASE
        WHEN Resultado.Total_FKs_Nulas = 0
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS Status_Validacao
FROM
(
    SELECT
        'gold.fato_item_pedido' AS Tabela,
        COUNT_BIG(*) AS Total_Linhas,
        8 AS Quantidade_FKs,

        COALESCE(
            SUM(
                CASE WHEN Cliente_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Produto_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Data_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Horario_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Pagamento_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Campanha_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Canal_Marketing_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Evento_Externo_SK IS NULL THEN 1 ELSE 0 END
            ),
            0
        ) AS Total_FKs_Nulas
    FROM gold.fato_item_pedido

    UNION ALL

    SELECT
        'gold.fato_pedido',
        COUNT_BIG(*),
        8,

        COALESCE(
            SUM(
                CASE WHEN Cliente_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Data_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Horario_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Geografia_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Pagamento_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Campanha_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Canal_Marketing_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Evento_Externo_SK IS NULL THEN 1 ELSE 0 END
            ),
            0
        )
    FROM gold.fato_pedido

    UNION ALL

    SELECT
        'gold.fato_entrega',
        COUNT_BIG(*),
        4,

        COALESCE(
            SUM(
                CASE WHEN Cliente_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Data_Pedido_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Geografia_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Transportadora_SK IS NULL THEN 1 ELSE 0 END
            ),
            0
        )
    FROM gold.fato_entrega

    UNION ALL

    SELECT
        'gold.fato_cliente_mes',
        COUNT_BIG(*),
        2,

        COALESCE(
            SUM(
                CASE WHEN Cliente_SK IS NULL THEN 1 ELSE 0 END
              + CASE WHEN Data_Corte_SK IS NULL THEN 1 ELSE 0 END
            ),
            0
        )
    FROM gold.fato_cliente_mes
) AS Resultado
ORDER BY Resultado.Tabela;
GO


/* ============================================================
   7. DUPLICIDADES NO GRÃO DAS DIMENSÕES

   Resultado esperado:
   - zero grupos duplicados em todas as dimensões.
   ============================================================ */

SELECT
    Resultado.Tabela,
    Resultado.Grao_Validado,
    Resultado.Grupos_Duplicados,

    CASE
        WHEN Resultado.Grupos_Duplicados = 0
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS Status_Validacao
FROM
(
    SELECT
        'gold.dim_cliente' AS Tabela,
        'Cliente_ID' AS Grao_Validado,
        COUNT_BIG(*) AS Grupos_Duplicados
    FROM
    (
        SELECT Cliente_ID
        FROM gold.dim_cliente
        GROUP BY Cliente_ID
        HAVING COUNT(*) > 1
    ) AS D

    UNION ALL

    SELECT
        'gold.dim_produto',
        'Id_Item',
        COUNT_BIG(*)
    FROM
    (
        SELECT Id_Item
        FROM gold.dim_produto
        GROUP BY Id_Item
        HAVING COUNT(*) > 1
    ) AS D

    UNION ALL

    SELECT
        'gold.dim_geografia',
        'Cidade + Estado',
        COUNT_BIG(*)
    FROM
    (
        SELECT Cidade, Estado
        FROM gold.dim_geografia
        GROUP BY Cidade, Estado
        HAVING COUNT(*) > 1
    ) AS D

    UNION ALL

    SELECT
        'gold.dim_data',
        'Data_Completa',
        COUNT_BIG(*)
    FROM
    (
        SELECT Data_Completa
        FROM gold.dim_data
        GROUP BY Data_Completa
        HAVING COUNT(*) > 1
    ) AS D

    UNION ALL

    SELECT
        'gold.dim_horario',
        'Horario',
        COUNT_BIG(*)
    FROM
    (
        SELECT Horario
        FROM gold.dim_horario
        GROUP BY Horario
        HAVING COUNT(*) > 1
    ) AS D

    UNION ALL

    SELECT
        'gold.dim_pagamento',
        'Forma_Pagamento',
        COUNT_BIG(*)
    FROM
    (
        SELECT Forma_Pagamento
        FROM gold.dim_pagamento
        GROUP BY Forma_Pagamento
        HAVING COUNT(*) > 1
    ) AS D

    UNION ALL

    SELECT
        'gold.dim_campanha',
        'Campanha',
        COUNT_BIG(*)
    FROM
    (
        SELECT Campanha
        FROM gold.dim_campanha
        GROUP BY Campanha
        HAVING COUNT(*) > 1
    ) AS D

    UNION ALL

    SELECT
        'gold.dim_canal_marketing',
        'Canal_Marketing',
        COUNT_BIG(*)
    FROM
    (
        SELECT Canal_Marketing
        FROM gold.dim_canal_marketing
        GROUP BY Canal_Marketing
        HAVING COUNT(*) > 1
    ) AS D

    UNION ALL

    SELECT
        'gold.dim_evento_externo',
        'Evento_Externo',
        COUNT_BIG(*)
    FROM
    (
        SELECT Evento_Externo
        FROM gold.dim_evento_externo
        GROUP BY Evento_Externo
        HAVING COUNT(*) > 1
    ) AS D

    UNION ALL

    SELECT
        'gold.dim_transportadora',
        'Transportadora',
        COUNT_BIG(*)
    FROM
    (
        SELECT Transportadora
        FROM gold.dim_transportadora
        GROUP BY Transportadora
        HAVING COUNT(*) > 1
    ) AS D
) AS Resultado
ORDER BY Resultado.Tabela;
GO


/* ============================================================
   8. DUPLICIDADES NO GRÃO DAS TABELAS FATO

   Resultado esperado:
   - zero grupos duplicados nas quatro tabelas fato.
   ============================================================ */

SELECT
    Resultado.Tabela,
    Resultado.Grao_Validado,
    Resultado.Grupos_Duplicados,

    CASE
        WHEN Resultado.Grupos_Duplicados = 0
            THEN 'APROVADO'
        ELSE 'REPROVADO'
    END AS Status_Validacao
FROM
(
    SELECT
        'gold.fato_item_pedido' AS Tabela,
        'Pedido_ID + Bronze_Source_Row_Number' AS Grao_Validado,
        COUNT_BIG(*) AS Grupos_Duplicados
    FROM
    (
        SELECT
            Pedido_ID,
            Bronze_Source_Row_Number
        FROM gold.fato_item_pedido
        GROUP BY
            Pedido_ID,
            Bronze_Source_Row_Number
        HAVING COUNT(*) > 1
    ) AS D

    UNION ALL

    SELECT
        'gold.fato_pedido',
        'Pedido_ID',
        COUNT_BIG(*)
    FROM
    (
        SELECT Pedido_ID
        FROM gold.fato_pedido
        GROUP BY Pedido_ID
        HAVING COUNT(*) > 1
    ) AS D

    UNION ALL

    SELECT
        'gold.fato_entrega',
        'Pedido_ID',
        COUNT_BIG(*)
    FROM
    (
        SELECT Pedido_ID
        FROM gold.fato_entrega
        GROUP BY Pedido_ID
        HAVING COUNT(*) > 1
    ) AS D

    UNION ALL

    SELECT
        'gold.fato_cliente_mes',
        'Cliente_SK + Data_Corte_SK',
        COUNT_BIG(*)
    FROM
    (
        SELECT
            Cliente_SK,
            Data_Corte_SK
        FROM gold.fato_cliente_mes
        GROUP BY
            Cliente_SK,
            Data_Corte_SK
        HAVING COUNT(*) > 1
    ) AS D
) AS Resultado
ORDER BY Resultado.Tabela;
GO