SELECT
    name AS schema_criado
FROM sys.schemas
WHERE name IN ('gold', 'quality', 'audit', 'eda')
ORDER BY name;