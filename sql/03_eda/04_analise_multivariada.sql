USE [CustomerAnalyticsHub];
GO
SET NOCOUNT ON;
GO

/* EDA 04 — ANÁLISE MULTIVARIADA
   Combina três ou mais dimensões. Associação não implica causalidade.
   Grupos pequenos são mantidos e sinalizados, nunca ocultados. */

DROP TABLE IF EXISTS #Cliente_360;
DROP TABLE IF EXISTS #Pedido_360;
GO

/* 1. Cliente 360: uma linha por cliente. */
WITH MP AS (
 SELECT Cliente_SK,COUNT_BIG(*) Total_Pedidos,SUM(CONVERT(FLOAT,Quantidade_Total_Itens)) Total_Itens,
  SUM(CONVERT(FLOAT,Valor_Liquido_Pedido)) Receita_Total,
  SUM(CONVERT(FLOAT,Custo_Total_Pedido)) Custo_Total,
  SUM(CONVERT(FLOAT,Margem_Bruta_Pedido)) Margem_Total,
  AVG(CONVERT(FLOAT,Valor_Liquido_Pedido)) Ticket_Medio,
  MIN(Data_Hora_Compra) Primeira_Compra,MAX(Data_Hora_Compra) Ultima_Compra
 FROM gold.fato_pedido GROUP BY Cliente_SK
), UCM AS (
 SELECT *,ROW_NUMBER() OVER(PARTITION BY Cliente_SK ORDER BY Data_Corte_SK DESC) Ordem
 FROM gold.fato_cliente_mes
), Base AS (
 SELECT C.Cliente_SK,C.Cliente_ID,C.Genero,C.Idade,C.Escolaridade,C.Estado_Civil,
  C.Situacao_Profissional,C.Profissao,C.Tempo_Experiencia_Anos,C.Renda_Mensal_Cliente,
  G.Cidade,G.Estado,G.Regiao,COALESCE(MP.Total_Pedidos,0) Total_Pedidos,
  COALESCE(MP.Total_Itens,0) Total_Itens,COALESCE(MP.Receita_Total,0) Receita_Total,
  COALESCE(MP.Custo_Total,0) Custo_Total,COALESCE(MP.Margem_Total,0) Margem_Total,
  MP.Ticket_Medio,MP.Primeira_Compra,MP.Ultima_Compra,UCM.Recencia_Dias,
  UCM.Intervalo_Medio_Calculado,UCM.Pontos_Fidelidade_Ultimo_Observado
 FROM gold.dim_cliente C JOIN gold.dim_geografia G ON G.Geografia_SK=C.Geografia_SK
 LEFT JOIN MP ON MP.Cliente_SK=C.Cliente_SK
 LEFT JOIN UCM ON UCM.Cliente_SK=C.Cliente_SK AND UCM.Ordem=1
)
SELECT *,CASE WHEN Idade BETWEEN 16 AND 24 THEN '16-24' WHEN Idade<=34 THEN '25-34'
 WHEN Idade<=44 THEN '35-44' WHEN Idade<=54 THEN '45-54' WHEN Idade<=64 THEN '55-64'
 WHEN Idade IS NULL THEN '[NULO]' ELSE '65+' END Faixa_Etaria,
 NTILE(4) OVER(ORDER BY Renda_Mensal_Cliente,Cliente_SK) Quartil_Renda
INTO #Cliente_360 FROM Base;
GO
CREATE UNIQUE CLUSTERED INDEX IX_Cliente_360 ON #Cliente_360(Cliente_SK);
GO

/* 2. Pedido 360: uma linha por pedido, incluindo marketing e logística. */
SELECT FP.Pedido_SK,FP.Pedido_ID,FP.Cliente_SK,C.Genero,C.Faixa_Etaria,C.Escolaridade,
 C.Quartil_Renda,C.Cidade,C.Estado,C.Regiao,PG.Forma_Pagamento,CP.Campanha,
 CM.Canal_Marketing,EE.Evento_Externo,FP.Pedido_Com_Campanha,FP.Cupom_Status,
 FP.Quantidade_Total_Itens,FP.Valor_Bruto_Pedido,FP.Valor_Desconto_Pedido,
 FP.Valor_Liquido_Pedido,FP.Custo_Total_Pedido,FP.Margem_Bruta_Pedido,
 FE.Transportadora_SK,T.Transportadora,FE.Frete,FE.Dias_Atraso,
 FE.Status_Entrega_Calculado,FE.Avaliacao_Cliente
INTO #Pedido_360
FROM gold.fato_pedido FP JOIN #Cliente_360 C ON C.Cliente_SK=FP.Cliente_SK
JOIN gold.dim_pagamento PG ON PG.Pagamento_SK=FP.Pagamento_SK
JOIN gold.dim_campanha CP ON CP.Campanha_SK=FP.Campanha_SK
JOIN gold.dim_canal_marketing CM ON CM.Canal_Marketing_SK=FP.Canal_Marketing_SK
JOIN gold.dim_evento_externo EE ON EE.Evento_Externo_SK=FP.Evento_Externo_SK
LEFT JOIN gold.fato_entrega FE ON FE.Pedido_ID=FP.Pedido_ID
LEFT JOIN gold.dim_transportadora T ON T.Transportadora_SK=FE.Transportadora_SK;
GO
CREATE UNIQUE CLUSTERED INDEX IX_Pedido_360 ON #Pedido_360(Pedido_SK);
GO

/* 3. Socioeconomia: gênero x escolaridade x renda x idade. */
SELECT Genero,Escolaridade,Quartil_Renda,Faixa_Etaria,COUNT_BIG(*) Clientes,
 CAST(AVG(CONVERT(FLOAT,Total_Pedidos)) AS DECIMAL(18,2)) Pedidos_Medios_Cliente,
 CAST(AVG(Receita_Total) AS DECIMAL(18,2)) Receita_Media_Cliente,
 CAST(SUM(Receita_Total)/NULLIF(SUM(Total_Pedidos),0) AS DECIMAL(18,2)) Ticket_Medio_Pedido,
 CAST(100.0*SUM(Margem_Total)/NULLIF(SUM(Receita_Total),0) AS DECIMAL(10,2)) Margem_Pct_Ponderada,
 CASE WHEN COUNT_BIG(*)<10 THEN 'AMOSTRA PEQUENA' ELSE 'AMOSTRA SUFICIENTE' END Status_Amostra
FROM #Cliente_360 GROUP BY Genero,Escolaridade,Quartil_Renda,Faixa_Etaria
ORDER BY Clientes DESC,Receita_Media_Cliente DESC;
GO

/* 4. Geografia x renda x gênero x comportamento. */
SELECT Regiao,Estado,Quartil_Renda,Genero,COUNT_BIG(*) Clientes,SUM(Total_Pedidos) Pedidos,
 CAST(AVG(Receita_Total) AS DECIMAL(18,2)) Receita_Media_Cliente,
 CAST(SUM(Receita_Total)/NULLIF(SUM(Total_Pedidos),0) AS DECIMAL(18,2)) Ticket_Medio_Pedido,
 CASE WHEN COUNT_BIG(*)<10 THEN 'AMOSTRA PEQUENA' ELSE 'AMOSTRA SUFICIENTE' END Status_Amostra
FROM #Cliente_360 GROUP BY Regiao,Estado,Quartil_Renda,Genero
ORDER BY Clientes DESC,Receita_Media_Cliente DESC;
GO

/* 5. Marketing: canal x campanha x evento externo. Grão do pedido. */
SELECT Canal_Marketing,Campanha,Evento_Externo,COUNT_BIG(*) Pedidos,
 COUNT(DISTINCT Cliente_SK) Clientes,CAST(SUM(Valor_Liquido_Pedido) AS DECIMAL(18,2)) Receita,
 CAST(AVG(CONVERT(FLOAT,Valor_Liquido_Pedido)) AS DECIMAL(18,2)) Ticket_Medio,
 CAST(100.0*SUM(Valor_Desconto_Pedido)/NULLIF(SUM(Valor_Bruto_Pedido),0) AS DECIMAL(10,2)) Desconto_Pct,
 CAST(100.0*SUM(Margem_Bruta_Pedido)/NULLIF(SUM(Valor_Liquido_Pedido),0) AS DECIMAL(10,2)) Margem_Pct,
 CASE WHEN COUNT_BIG(*)<30 THEN 'AMOSTRA PEQUENA' ELSE 'AMOSTRA SUFICIENTE' END Status_Amostra
FROM #Pedido_360 GROUP BY Canal_Marketing,Campanha,Evento_Externo
ORDER BY Pedidos DESC,Receita DESC;
GO

/* 6. Comercial/financeiro: categoria x pagamento x campanha. Grão do item. */
SELECT DP.Categoria_Item,P.Forma_Pagamento,P.Pedido_Com_Campanha,
 COUNT_BIG(*) Linhas_Item,COUNT(DISTINCT FI.Pedido_ID) Pedidos,COUNT(DISTINCT FI.Cliente_SK) Clientes,
 SUM(FI.Quantidade) Unidades,CAST(SUM(FI.Valor_Compra) AS DECIMAL(18,2)) Receita,
 CAST(100.0*SUM(FI.Margem_Bruta_Item)/NULLIF(SUM(FI.Valor_Compra),0) AS DECIMAL(10,2)) Margem_Pct,
 CASE WHEN COUNT(DISTINCT FI.Pedido_ID)<30 THEN 'AMOSTRA PEQUENA' ELSE 'AMOSTRA SUFICIENTE' END Status_Amostra
FROM gold.fato_item_pedido FI JOIN gold.dim_produto DP ON DP.Produto_SK=FI.Produto_SK
JOIN #Pedido_360 P ON P.Pedido_ID=FI.Pedido_ID
GROUP BY DP.Categoria_Item,P.Forma_Pagamento,P.Pedido_Com_Campanha
ORDER BY Pedidos DESC,Receita DESC;
GO

/* 7. Logística: região x transportadora x status. */
SELECT Regiao,Transportadora,Status_Entrega_Calculado,COUNT_BIG(*) Entregas,
 CAST(AVG(CONVERT(FLOAT,Dias_Atraso)) AS DECIMAL(18,2)) Atraso_Medio,
 CAST(AVG(CONVERT(FLOAT,Frete)) AS DECIMAL(18,2)) Frete_Medio,
 CAST(AVG(CONVERT(FLOAT,Avaliacao_Cliente)) AS DECIMAL(10,2)) Avaliacao_Media,
 CAST(AVG(CONVERT(FLOAT,Valor_Liquido_Pedido)) AS DECIMAL(18,2)) Ticket_Medio,
 CASE WHEN COUNT_BIG(*)<30 THEN 'AMOSTRA PEQUENA' ELSE 'AMOSTRA SUFICIENTE' END Status_Amostra
FROM #Pedido_360 GROUP BY Regiao,Transportadora,Status_Entrega_Calculado
ORDER BY Entregas DESC,Regiao,Transportadora;
GO

/* 8. Diagnóstico de fragmentação causado pelos cruzamentos. */
WITH Segmentos AS (
 SELECT 'Socioeconomico' Analise,Genero+' | '+Escolaridade+' | Q'+CONVERT(VARCHAR(1),Quartil_Renda)+' | '+Faixa_Etaria Segmento
 FROM #Cliente_360
 UNION ALL
 SELECT 'Geografico',Regiao+' | '+Estado+' | Q'+CONVERT(VARCHAR(1),Quartil_Renda)+' | '+Genero FROM #Cliente_360
)
SELECT Analise,SUM(N) Observacoes,COUNT_BIG(*) Segmentos,
 CAST(SUM(N)*1.0/NULLIF(COUNT_BIG(*),0) AS DECIMAL(18,2)) Media_Observacoes_Segmento,
 SUM(CASE WHEN N<10 THEN 1 ELSE 0 END) Segmentos_Com_Amostra_Pequena
FROM (SELECT Analise,Segmento,COUNT_BIG(*) N FROM Segmentos GROUP BY Analise,Segmento) X
GROUP BY Analise;
GO

/* 9. Dataset descritivo preparado para clustering posterior.
   Não constitui clustering e não cria segmentos artificiais. */
WITH E AS (
 SELECT AVG(CONVERT(FLOAT,Idade)) M_Idade,STDEV(CONVERT(FLOAT,Idade)) DP_Idade,
  AVG(CONVERT(FLOAT,Renda_Mensal_Cliente)) M_Renda,STDEV(CONVERT(FLOAT,Renda_Mensal_Cliente)) DP_Renda,
  AVG(CONVERT(FLOAT,Total_Pedidos)) M_Pedidos,STDEV(CONVERT(FLOAT,Total_Pedidos)) DP_Pedidos,
  AVG(Receita_Total) M_Receita,STDEV(Receita_Total) DP_Receita,
  AVG(CONVERT(FLOAT,Recencia_Dias)) M_Recencia,STDEV(CONVERT(FLOAT,Recencia_Dias)) DP_Recencia
 FROM #Cliente_360)
SELECT C.Cliente_SK,C.Idade,C.Renda_Mensal_Cliente,C.Total_Pedidos,C.Receita_Total,C.Ticket_Medio,C.Recencia_Dias,
 CAST((C.Idade-E.M_Idade)/NULLIF(E.DP_Idade,0) AS DECIMAL(18,6)) Z_Idade,
 CAST((C.Renda_Mensal_Cliente-E.M_Renda)/NULLIF(E.DP_Renda,0) AS DECIMAL(18,6)) Z_Renda,
 CAST((C.Total_Pedidos-E.M_Pedidos)/NULLIF(E.DP_Pedidos,0) AS DECIMAL(18,6)) Z_Pedidos,
 CAST((C.Receita_Total-E.M_Receita)/NULLIF(E.DP_Receita,0) AS DECIMAL(18,6)) Z_Receita,
 CAST((C.Recencia_Dias-E.M_Recencia)/NULLIF(E.DP_Recencia,0) AS DECIMAL(18,6)) Z_Recencia
FROM #Cliente_360 C CROSS JOIN E ORDER BY C.Cliente_SK;
GO

DROP TABLE IF EXISTS #Pedido_360;
DROP TABLE IF EXISTS #Cliente_360;
GO
