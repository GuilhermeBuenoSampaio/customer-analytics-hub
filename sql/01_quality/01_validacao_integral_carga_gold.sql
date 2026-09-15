USE CustomerAnalyticsHub;
GO

/* ============================================================
   1. CONTAGEM DE LINHAS DAS 14 TABELAS GOLD
   ============================================================ */

SELECT
    s.name AS schema_nome,
    t.name AS tabela,
    SUM(p.rows) AS quantidade_linhas
FROM sys.tables AS t
INNER JOIN sys.schemas AS s
    ON s.schema_id = t.schema_id
INNER JOIN sys.partitions AS p
    ON p.object_id = t.object_id
WHERE
    s.name = 'gold'
    AND p.index_id IN (0, 1)
GROUP BY
    s.name,
    t.name
ORDER BY
    t.name;


/* ============================================================
   2. HISTÓRICO DAS EXECUÇÕES DA CARGA GOLD
   ============================================================ */

SELECT TOP (10) *
FROM audit.execucao_carga_gold
ORDER BY Inicio_UTC DESC;


/* ============================================================
   3. RECONCILIAÇÃO PARQUET × SQL DA ÚLTIMA CARGA APROVADA
   ============================================================ */

SELECT *
FROM quality.reconciliacao_carga_gold
WHERE Execucao_ID = (
    SELECT TOP (1) Execucao_ID
    FROM audit.execucao_carga_gold
    WHERE Status = 'APROVADO'
    ORDER BY Inicio_UTC DESC
)
ORDER BY Tabela;


/* ============================================================
   4. QUANTIDADE DE CHAVES ESTRANGEIRAS DA GOLD
   ============================================================ */

SELECT
    COUNT(*) AS quantidade_chaves_estrangeiras
FROM sys.foreign_keys AS fk
INNER JOIN sys.tables AS t
    ON t.object_id = fk.parent_object_id
INNER JOIN sys.schemas AS s
    ON s.schema_id = t.schema_id
WHERE s.name = 'gold';