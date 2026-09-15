USE [CustomerAnalyticsHub];
GO
SET NOCOUNT ON;
GO

/* EDA 03 — ANÁLISE BIVARIADA
   Associação não implica causalidade. Cada bloco preserva o grão. */

DROP TABLE IF EXISTS #Perfil_Cliente;
GO

/* Base com uma linha por cliente: evita super-representação de clientes frequentes. */
WITH M AS (
 SELECT Cliente_SK,COUNT_BIG(*) Total_Pedidos,
  SUM(CONVERT(FLOAT,Quantidade_Total_Itens)) Total_Itens,
  SUM(CONVERT(FLOAT,Valor_Liquido_Pedido)) Receita_Total,
  SUM(CONVERT(FLOAT,Margem_Bruta_Pedido)) Margem_Total,
  AVG(CONVERT(FLOAT,Valor_Liquido_Pedido)) Ticket_Calculado
 FROM gold.fato_pedido GROUP BY Cliente_SK
)
SELECT C.Cliente_SK,C.Cliente_ID,C.Genero,C.Idade,C.Estado_Civil,C.Escolaridade,
 C.Situacao_Profissional,C.Profissao,C.Tempo_Experiencia_Anos,C.Renda_Mensal_Cliente,
 C.Ciclo_Vida_Informado,C.Ticket_Medio_Informado,G.Cidade,G.Estado,G.Regiao,
 COALESCE(M.Total_Pedidos,0) Total_Pedidos,COALESCE(M.Total_Itens,0) Total_Itens,
 COALESCE(M.Receita_Total,0) Receita_Total,COALESCE(M.Margem_Total,0) Margem_Total,
 M.Ticket_Calculado
INTO #Perfil_Cliente
FROM gold.dim_cliente C JOIN gold.dim_geografia G ON G.Geografia_SK=C.Geografia_SK
LEFT JOIN M ON M.Cliente_SK=C.Cliente_SK;
GO
CREATE UNIQUE CLUSTERED INDEX IX_Perfil_Cliente ON #Perfil_Cliente(Cliente_SK);
GO

/* 1. Completude socioeconômica. Variáveis 100% nulas ficam indisponíveis. */
SELECT V.Variavel,COUNT_BIG(*) Total_Clientes,
 SUM(CASE WHEN V.Valor IS NULL OR LTRIM(RTRIM(V.Valor))='' THEN 1 ELSE 0 END) Ausentes,
 CAST(100.0*SUM(CASE WHEN V.Valor IS NULL OR LTRIM(RTRIM(V.Valor))='' THEN 1 ELSE 0 END)
 /NULLIF(COUNT_BIG(*),0) AS DECIMAL(10,2)) Percentual_Ausente,
 CASE WHEN SUM(CASE WHEN V.Valor IS NULL OR LTRIM(RTRIM(V.Valor))='' THEN 1 ELSE 0 END)=COUNT_BIG(*)
 THEN 'INDISPONIVEL' ELSE 'DISPONIVEL' END Status_Uso
FROM #Perfil_Cliente P CROSS APPLY (VALUES
 ('Genero',CONVERT(NVARCHAR(255),P.Genero)),('Idade',CONVERT(NVARCHAR(255),P.Idade)),
 ('Escolaridade',CONVERT(NVARCHAR(255),P.Escolaridade)),
 ('Situacao_Profissional',CONVERT(NVARCHAR(255),P.Situacao_Profissional)),
 ('Renda_Mensal_Cliente',CONVERT(NVARCHAR(255),P.Renda_Mensal_Cliente)),
 ('Ciclo_Vida_Informado',CONVERT(NVARCHAR(255),P.Ciclo_Vida_Informado))) V(Variavel,Valor)
GROUP BY V.Variavel ORDER BY V.Variavel;
GO

/* 2. Perfil categórico do cliente x comportamento de compra. */
WITH S AS (
 SELECT X.Dimensao,COALESCE(NULLIF(LTRIM(RTRIM(X.Segmento)),''),N'[NULO]') Segmento,
  P.Total_Pedidos,P.Receita_Total,P.Margem_Total
 FROM #Perfil_Cliente P CROSS APPLY (VALUES
  ('Genero',CONVERT(NVARCHAR(255),P.Genero)),
  ('Escolaridade',CONVERT(NVARCHAR(255),P.Escolaridade)),
  ('Estado_Civil',CONVERT(NVARCHAR(255),P.Estado_Civil)),
  ('Situacao_Profissional',CONVERT(NVARCHAR(255),P.Situacao_Profissional))) X(Dimensao,Segmento)
)
SELECT Dimensao,Segmento,COUNT_BIG(*) Clientes,SUM(Total_Pedidos) Pedidos,
 CAST(AVG(CONVERT(FLOAT,Total_Pedidos)) AS DECIMAL(18,2)) Pedidos_Medios_Cliente,
 CAST(SUM(Receita_Total) AS DECIMAL(18,2)) Receita_Total,
 CAST(AVG(Receita_Total) AS DECIMAL(18,2)) Receita_Media_Cliente,
 CAST(SUM(Receita_Total)/NULLIF(SUM(Total_Pedidos),0) AS DECIMAL(18,2)) Ticket_Medio_Pedido,
 CAST(100.0*SUM(Margem_Total)/NULLIF(SUM(Receita_Total),0) AS DECIMAL(10,2)) Margem_Pct_Ponderada
FROM S GROUP BY Dimensao,Segmento ORDER BY Dimensao,Receita_Total DESC;
GO

/* 3. Faixa etária x comportamento, no grão do cliente. */
WITH F AS (
 SELECT P.*,CASE WHEN Idade BETWEEN 16 AND 24 THEN '16-24' WHEN Idade<=34 THEN '25-34'
 WHEN Idade<=44 THEN '35-44' WHEN Idade<=54 THEN '45-54' WHEN Idade<=64 THEN '55-64'
 WHEN Idade IS NULL THEN '[NULO]' ELSE '65+' END Faixa FROM #Perfil_Cliente P)
SELECT Faixa,COUNT_BIG(*) Clientes,SUM(Total_Pedidos) Pedidos,
 CAST(AVG(Receita_Total) AS DECIMAL(18,2)) Receita_Media_Cliente,
 CAST(SUM(Receita_Total)/NULLIF(SUM(Total_Pedidos),0) AS DECIMAL(18,2)) Ticket_Medio_Pedido
FROM F GROUP BY Faixa ORDER BY MIN(COALESCE(Idade,999));
GO

/* 4. Quartil de renda x comportamento. Quartis são posicionais. */
WITH R AS (SELECT P.*,NTILE(4) OVER(ORDER BY Renda_Mensal_Cliente,Cliente_SK) Quartil_Renda
 FROM #Perfil_Cliente P WHERE Renda_Mensal_Cliente IS NOT NULL)
SELECT Quartil_Renda,COUNT_BIG(*) Clientes,
 CAST(MIN(Renda_Mensal_Cliente) AS DECIMAL(18,2)) Renda_Min,
 CAST(MAX(Renda_Mensal_Cliente) AS DECIMAL(18,2)) Renda_Max,
 CAST(AVG(Receita_Total) AS DECIMAL(18,2)) Receita_Media_Cliente,
 CAST(AVG(CONVERT(FLOAT,Total_Pedidos)) AS DECIMAL(18,2)) Pedidos_Medios_Cliente,
 CAST(SUM(Receita_Total)/NULLIF(SUM(Total_Pedidos),0) AS DECIMAL(18,2)) Ticket_Medio_Pedido
FROM R GROUP BY Quartil_Renda ORDER BY Quartil_Renda;
GO

/* 5. Geografia x comportamento, uma linha de origem por cliente. */
SELECT Regiao,Estado,Cidade,COUNT_BIG(*) Clientes,SUM(Total_Pedidos) Pedidos,
 CAST(SUM(Receita_Total) AS DECIMAL(18,2)) Receita_Total,
 CAST(AVG(Receita_Total) AS DECIMAL(18,2)) Receita_Media_Cliente,
 CAST(SUM(Receita_Total)/NULLIF(SUM(Total_Pedidos),0) AS DECIMAL(18,2)) Ticket_Medio_Pedido
FROM #Perfil_Cliente GROUP BY Regiao,Estado,Cidade ORDER BY Receita_Total DESC;
GO

/* 6. Categoria x desempenho, no grão do item vendido. */
SELECT P.Categoria_Item,COUNT(DISTINCT P.Produto_SK) Produtos_Vendidos,
 COUNT_BIG(*) Linhas_Item,SUM(FI.Quantidade) Unidades,COUNT(DISTINCT FI.Pedido_ID) Pedidos,
 COUNT(DISTINCT FI.Cliente_SK) Clientes,CAST(SUM(FI.Valor_Compra) AS DECIMAL(18,2)) Receita_Total,
 CAST(SUM(FI.Margem_Bruta_Item) AS DECIMAL(18,2)) Margem_Total,
 CAST(100.0*SUM(FI.Margem_Bruta_Item)/NULLIF(SUM(FI.Valor_Compra),0) AS DECIMAL(10,2)) Margem_Pct_Ponderada
FROM gold.fato_item_pedido FI JOIN gold.dim_produto P ON P.Produto_SK=FI.Produto_SK
GROUP BY P.Categoria_Item ORDER BY Receita_Total DESC;
GO

/* 7. Pagamento, campanha, canal, evento e cupom x resultado do pedido. */
WITH C AS (
 SELECT FP.Cliente_SK,X.Dimensao,X.Categoria,FP.Quantidade_Total_Itens,FP.Valor_Bruto_Pedido,
  FP.Valor_Desconto_Pedido,FP.Valor_Liquido_Pedido,FP.Margem_Bruta_Pedido
 FROM gold.fato_pedido FP JOIN gold.dim_pagamento PG ON PG.Pagamento_SK=FP.Pagamento_SK
 JOIN gold.dim_campanha CP ON CP.Campanha_SK=FP.Campanha_SK
 JOIN gold.dim_canal_marketing CM ON CM.Canal_Marketing_SK=FP.Canal_Marketing_SK
 JOIN gold.dim_evento_externo EE ON EE.Evento_Externo_SK=FP.Evento_Externo_SK
 CROSS APPLY (VALUES ('Forma_Pagamento',CONVERT(NVARCHAR(255),PG.Forma_Pagamento)),
 ('Campanha',CONVERT(NVARCHAR(255),CP.Campanha)),('Canal_Marketing',CONVERT(NVARCHAR(255),CM.Canal_Marketing)),
 ('Evento_Externo',CONVERT(NVARCHAR(255),EE.Evento_Externo)),('Cupom_Status',CONVERT(NVARCHAR(255),FP.Cupom_Status))) X(Dimensao,Categoria))
SELECT Dimensao,Categoria,COUNT_BIG(*) Pedidos,COUNT(DISTINCT Cliente_SK) Clientes,
 CAST(AVG(CONVERT(FLOAT,Quantidade_Total_Itens)) AS DECIMAL(18,2)) Itens_Medios,
 CAST(SUM(Valor_Liquido_Pedido) AS DECIMAL(18,2)) Receita_Total,
 CAST(AVG(CONVERT(FLOAT,Valor_Liquido_Pedido)) AS DECIMAL(18,2)) Ticket_Medio,
 CAST(100.0*SUM(Valor_Desconto_Pedido)/NULLIF(SUM(Valor_Bruto_Pedido),0) AS DECIMAL(10,2)) Desconto_Pct_Ponderado,
 CAST(100.0*SUM(Margem_Bruta_Pedido)/NULLIF(SUM(Valor_Liquido_Pedido),0) AS DECIMAL(10,2)) Margem_Pct_Ponderada
FROM C GROUP BY Dimensao,Categoria ORDER BY Dimensao,Receita_Total DESC;
GO

/* 8. Status da entrega e transportadora x experiência logística. */
SELECT 'Status_Entrega' Dimensao,FE.Status_Entrega_Calculado Categoria,COUNT_BIG(*) Entregas,
 CAST(AVG(CONVERT(FLOAT,FE.Dias_Atraso)) AS DECIMAL(18,2)) Atraso_Medio,
 CAST(AVG(CONVERT(FLOAT,FE.Frete)) AS DECIMAL(18,2)) Frete_Medio,
 CAST(AVG(CONVERT(FLOAT,FE.Avaliacao_Cliente)) AS DECIMAL(10,2)) Avaliacao_Media
FROM gold.fato_entrega FE GROUP BY FE.Status_Entrega_Calculado
UNION ALL
SELECT 'Transportadora',T.Transportadora,COUNT_BIG(*),
 CAST(AVG(CONVERT(FLOAT,FE.Dias_Atraso)) AS DECIMAL(18,2)),
 CAST(AVG(CONVERT(FLOAT,FE.Frete)) AS DECIMAL(18,2)),
 CAST(AVG(CONVERT(FLOAT,FE.Avaliacao_Cliente)) AS DECIMAL(10,2))
FROM gold.fato_entrega FE JOIN gold.dim_transportadora T ON T.Transportadora_SK=FE.Transportadora_SK
GROUP BY T.Transportadora ORDER BY Dimensao,Entregas DESC;
GO

/* 9. Correlação de Pearson, no grão do cliente. */
WITH P AS (
 SELECT V.Relacao,CONVERT(FLOAT,V.X) X,CONVERT(FLOAT,V.Y) Y FROM #Perfil_Cliente C
 CROSS APPLY (VALUES ('Idade x Receita',C.Idade,C.Receita_Total),
 ('Idade x Pedidos',C.Idade,CONVERT(FLOAT,C.Total_Pedidos)),
 ('Renda x Receita',C.Renda_Mensal_Cliente,C.Receita_Total),
 ('Renda x Pedidos',C.Renda_Mensal_Cliente,CONVERT(FLOAT,C.Total_Pedidos)),
 ('Renda x Ticket',C.Renda_Mensal_Cliente,C.Ticket_Calculado),
 ('Ticket informado x calculado',C.Ticket_Medio_Informado,C.Ticket_Calculado)) V(Relacao,X,Y)
 WHERE V.X IS NOT NULL AND V.Y IS NOT NULL),
A AS (SELECT Relacao,COUNT_BIG(*) N,SUM(X) SX,SUM(Y) SY,SUM(X*Y) SXY,SUM(X*X) SX2,SUM(Y*Y) SY2 FROM P GROUP BY Relacao),
R AS (SELECT Relacao,N,(N*SXY-SX*SY)/NULLIF(SQRT((N*SX2-SX*SX)*(N*SY2-SY*SY)),0) Pearson FROM A)
SELECT Relacao,N Observacoes,CAST(Pearson AS DECIMAL(10,6)) Correlacao_Pearson,
 CASE WHEN Pearson IS NULL THEN 'NAO CALCULAVEL' WHEN ABS(Pearson)<0.10 THEN 'DESPREZIVEL'
 WHEN ABS(Pearson)<0.30 THEN 'FRACA' WHEN ABS(Pearson)<0.50 THEN 'MODERADA' ELSE 'FORTE' END Magnitude,
 CASE WHEN Pearson>0 THEN 'POSITIVA' WHEN Pearson<0 THEN 'NEGATIVA' WHEN Pearson=0 THEN 'NULA' ELSE 'NAO CALCULAVEL' END Direcao
FROM R ORDER BY ABS(Pearson) DESC;
GO

DROP TABLE IF EXISTS #Perfil_Cliente;
GO
