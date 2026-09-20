USE CustomerAnalyticsHub;
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'gold')
    EXEC('CREATE SCHEMA gold');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'quality')
    EXEC('CREATE SCHEMA quality');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'audit')
    EXEC('CREATE SCHEMA audit');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'eda')
    EXEC('CREATE SCHEMA eda');
GO

SELECT
    DB_NAME() AS banco_atual,
    name AS schema_criado
FROM sys.schemas
WHERE name IN ('gold', 'quality', 'audit', 'eda')
ORDER BY name;