USE [CustomerAnalyticsHub];
GO
SET NOCOUNT ON;
GO

/* ============================================================
   EDA 07 — ANÁLISE COMERCIAL
   Escopo: vendas, clientes, produtos, cesta, frequência e tempo.
   Período: 2025-01-01 a 2025-12-31.
   ============================================================ */

/* 1. KPIs comerciais gerais — grão do pedido. */
SELECT
    COUNT_BIG(*) AS Total_Pedidos,
    COUNT(DISTINCT Cliente_SK) AS Clientes_Com_Compra,
    SUM(Quantidade_Total_Itens) AS Unidades_Vendidas,
    SUM(Quantidade_Produtos_Distintos) AS Soma_Produtos_Distintos_Por_Pedido,
    CAST(SUM(Valor_Liquido_Pedido) AS DECIMAL(18,2)) AS Receita_Liquida,
    CAST(AVG(CONVERT(FLOAT,Valor_Liquido_Pedido)) AS DECIMAL(18,2)) AS Ticket_Medio,
    CAST(AVG(CONVERT(FLOAT,Quantidade_Total_Itens)) AS DECIMAL(18,2)) AS Itens_Medios_Por_Pedido,
    CAST(AVG(CONVERT(FLOAT,Quantidade_Produtos_Distintos)) AS DECIMAL(18,2)) AS Produtos_Distintos_Medios_Por_Pedido
FROM gold.fato_pedido;
GO

/* 2. Evolução mensal e variação em relação ao mês anterior. */
WITH Mensal AS
(
    SELECT
        D.Ano_Mes,
        D.Nome_Mes,
        COUNT_BIG(*) AS Pedidos,
        COUNT(DISTINCT FP.Cliente_SK) AS Clientes,
        SUM(FP.Quantidade_Total_Itens) AS Unidades,
        SUM(FP.Valor_Liquido_Pedido) AS Receita
    FROM gold.fato_pedido FP
    INNER JOIN gold.dim_data D ON D.Data_SK=FP.Data_SK
    GROUP BY D.Ano_Mes,D.Nome_Mes
), Comparacao AS
(
    SELECT *,LAG(Receita) OVER(ORDER BY Ano_Mes) AS Receita_Mes_Anterior,
             LAG(Pedidos) OVER(ORDER BY Ano_Mes) AS Pedidos_Mes_Anterior
    FROM Mensal
)
SELECT Ano_Mes,Nome_Mes,Pedidos,Clientes,Unidades,
       CAST(Receita AS DECIMAL(18,2)) AS Receita,
       CAST(Receita/NULLIF(Pedidos,0) AS DECIMAL(18,2)) AS Ticket_Medio,
       CAST(100.0*(Receita-Receita_Mes_Anterior)/NULLIF(Receita_Mes_Anterior,0) AS DECIMAL(10,2)) AS Variacao_Receita_Pct,
       CAST(100.0*(Pedidos-Pedidos_Mes_Anterior)/NULLIF(Pedidos_Mes_Anterior,0) AS DECIMAL(10,2)) AS Variacao_Pedidos_Pct
FROM Comparacao ORDER BY Ano_Mes;
GO

/* 3. Clientes novos e recorrentes por mês.
   Novo = primeira compra observada ocorreu naquele mês. */
WITH Primeira AS
(
    SELECT Cliente_SK,MIN(Data_SK) AS Primeira_Data_SK
    FROM gold.fato_pedido GROUP BY Cliente_SK
)
SELECT D.Ano_Mes,D.Nome_Mes,COUNT(DISTINCT FP.Cliente_SK) AS Clientes_Ativos,
       COUNT(DISTINCT CASE WHEN D.Data_SK=P.Primeira_Data_SK THEN FP.Cliente_SK END) AS Clientes_Novos,
       COUNT(DISTINCT FP.Cliente_SK)
       -COUNT(DISTINCT CASE WHEN D.Data_SK=P.Primeira_Data_SK THEN FP.Cliente_SK END) AS Clientes_Recorrentes
FROM gold.fato_pedido FP
JOIN gold.dim_data D ON D.Data_SK=FP.Data_SK
JOIN Primeira P ON P.Cliente_SK=FP.Cliente_SK
GROUP BY D.Ano_Mes,D.Nome_Mes ORDER BY D.Ano_Mes;
GO

/* 4. Frequência de compra por cliente. */
WITH F AS
(
    SELECT Cliente_SK,Total_Pedidos_Calculado,Valor_Total_Gasto,Ticket_Medio_Calculado,
           CASE WHEN Total_Pedidos_Calculado=1 THEN '1 pedido'
                WHEN Total_Pedidos_Calculado BETWEEN 2 AND 3 THEN '2-3 pedidos'
                WHEN Total_Pedidos_Calculado BETWEEN 4 AND 6 THEN '4-6 pedidos'
                WHEN Total_Pedidos_Calculado BETWEEN 7 AND 12 THEN '7-12 pedidos'
                ELSE '13+ pedidos' END AS Faixa_Frequencia
    FROM eda.vw_perfil_cliente_analytics
)
SELECT Faixa_Frequencia,COUNT_BIG(*) AS Clientes,SUM(Total_Pedidos_Calculado) AS Pedidos,
       CAST(SUM(Valor_Total_Gasto) AS DECIMAL(18,2)) AS Receita,
       CAST(AVG(Valor_Total_Gasto) AS DECIMAL(18,2)) AS Receita_Media_Cliente,
       CAST(SUM(Valor_Total_Gasto)/NULLIF(SUM(Total_Pedidos_Calculado),0) AS DECIMAL(18,2)) AS Ticket_Medio_Pedido
FROM F GROUP BY Faixa_Frequencia
ORDER BY MIN(CASE Faixa_Frequencia WHEN '1 pedido' THEN 1 WHEN '2-3 pedidos' THEN 2
 WHEN '4-6 pedidos' THEN 3 WHEN '7-12 pedidos' THEN 4 ELSE 5 END);
GO

/* 5. Concentração da receita por cliente — curva de Pareto. */
WITH B AS
(
    SELECT Cliente_SK,Cliente_ID,Total_Pedidos_Calculado,Valor_Total_Gasto,
           ROW_NUMBER() OVER(ORDER BY Valor_Total_Gasto DESC,Cliente_SK) AS Posicao,
           SUM(Valor_Total_Gasto) OVER(ORDER BY Valor_Total_Gasto DESC,Cliente_SK ROWS UNBOUNDED PRECEDING) AS Receita_Acumulada,
           SUM(Valor_Total_Gasto) OVER() AS Receita_Geral
    FROM eda.vw_perfil_cliente_analytics
)
SELECT Posicao,Cliente_SK,Cliente_ID,Total_Pedidos_Calculado,
       CAST(Valor_Total_Gasto AS DECIMAL(18,2)) AS Valor_Total_Gasto,
       CAST(100.0*Valor_Total_Gasto/NULLIF(Receita_Geral,0) AS DECIMAL(10,4)) AS Participacao_Individual_Pct,
       CAST(100.0*Receita_Acumulada/NULLIF(Receita_Geral,0) AS DECIMAL(10,2)) AS Receita_Acumulada_Pct
FROM B ORDER BY Posicao;
GO

/* 6. Desempenho comercial por categoria. */
SELECT P.Categoria_Item,COUNT(DISTINCT P.Produto_SK) AS Produtos_Vendidos,
       COUNT(DISTINCT FI.Pedido_ID) AS Pedidos,COUNT(DISTINCT FI.Cliente_SK) AS Clientes,
       SUM(FI.Quantidade) AS Unidades,CAST(SUM(FI.Valor_Compra) AS DECIMAL(18,2)) AS Receita,
       CAST(SUM(FI.Valor_Compra)/NULLIF(SUM(FI.Quantidade),0) AS DECIMAL(18,2)) AS Receita_Media_Unidade,
       CAST(100.0*COUNT(DISTINCT FI.Cliente_SK)/(SELECT COUNT(DISTINCT Cliente_SK) FROM gold.fato_pedido) AS DECIMAL(10,2)) AS Penetracao_Clientes_Pct
FROM gold.fato_item_pedido FI JOIN gold.dim_produto P ON P.Produto_SK=FI.Produto_SK
GROUP BY P.Categoria_Item ORDER BY Receita DESC;
GO

/* 7. Ranking dos 20 produtos por receita. */
SELECT TOP (20) P.Produto_SK,P.Produto,P.Categoria_Item,
       COUNT(DISTINCT FI.Pedido_ID) AS Pedidos,COUNT(DISTINCT FI.Cliente_SK) AS Clientes,
       SUM(FI.Quantidade) AS Unidades,CAST(SUM(FI.Valor_Compra) AS DECIMAL(18,2)) AS Receita,
       CAST(SUM(FI.Valor_Compra)/NULLIF(SUM(FI.Quantidade),0) AS DECIMAL(18,2)) AS Receita_Media_Unidade
FROM gold.fato_item_pedido FI JOIN gold.dim_produto P ON P.Produto_SK=FI.Produto_SK
GROUP BY P.Produto_SK,P.Produto,P.Categoria_Item
ORDER BY Receita DESC,Unidades DESC,P.Produto;
GO

/* 8. Tamanho da cesta x resultado comercial. */
WITH C AS
(
    SELECT *,CASE WHEN Quantidade_Total_Itens=1 THEN '1 item'
      WHEN Quantidade_Total_Itens BETWEEN 2 AND 3 THEN '2-3 itens'
      WHEN Quantidade_Total_Itens BETWEEN 4 AND 6 THEN '4-6 itens'
      WHEN Quantidade_Total_Itens BETWEEN 7 AND 10 THEN '7-10 itens'
      ELSE '11+ itens' END AS Faixa_Cesta
    FROM gold.fato_pedido
)
SELECT Faixa_Cesta,COUNT_BIG(*) AS Pedidos,COUNT(DISTINCT Cliente_SK) AS Clientes,
       SUM(Quantidade_Total_Itens) AS Unidades,
       CAST(SUM(Valor_Liquido_Pedido) AS DECIMAL(18,2)) AS Receita,
       CAST(AVG(CONVERT(FLOAT,Valor_Liquido_Pedido)) AS DECIMAL(18,2)) AS Ticket_Medio
FROM C GROUP BY Faixa_Cesta
ORDER BY MIN(CASE Faixa_Cesta WHEN '1 item' THEN 1 WHEN '2-3 itens' THEN 2
 WHEN '4-6 itens' THEN 3 WHEN '7-10 itens' THEN 4 ELSE 5 END);
GO

/* 9. Dia da semana e faixa horária x vendas. */
SELECT D.Numero_Dia_Semana,D.Nome_Dia_Semana,H.Faixa_Horaria,
       COUNT_BIG(*) AS Pedidos,COUNT(DISTINCT FP.Cliente_SK) AS Clientes,
       CAST(SUM(FP.Valor_Liquido_Pedido) AS DECIMAL(18,2)) AS Receita,
       CAST(AVG(CONVERT(FLOAT,FP.Valor_Liquido_Pedido)) AS DECIMAL(18,2)) AS Ticket_Medio
FROM gold.fato_pedido FP JOIN gold.dim_data D ON D.Data_SK=FP.Data_SK
JOIN gold.dim_horario H ON H.Horario_SK=FP.Horario_SK
GROUP BY D.Numero_Dia_Semana,D.Nome_Dia_Semana,H.Faixa_Horaria
ORDER BY D.Numero_Dia_Semana,MIN(H.Hora);
GO

/* 10. Pares de categorias comprados no mesmo pedido. */
WITH Categorias_Pedido AS
(
    SELECT DISTINCT FI.Pedido_ID,FI.Cliente_SK,P.Categoria_Item
    FROM gold.fato_item_pedido FI JOIN gold.dim_produto P ON P.Produto_SK=FI.Produto_SK
), Pares AS
(
    SELECT A.Categoria_Item AS Categoria_A,B.Categoria_Item AS Categoria_B,
           COUNT(DISTINCT A.Pedido_ID) AS Pedidos_Conjuntos,
           COUNT(DISTINCT A.Cliente_SK) AS Clientes
    FROM Categorias_Pedido A JOIN Categorias_Pedido B
      ON B.Pedido_ID=A.Pedido_ID AND B.Categoria_Item>A.Categoria_Item
    GROUP BY A.Categoria_Item,B.Categoria_Item
)
SELECT TOP (20) Categoria_A,Categoria_B,Pedidos_Conjuntos,Clientes
FROM Pares ORDER BY Pedidos_Conjuntos DESC,Clientes DESC,Categoria_A,Categoria_B;
GO

/* 11. Reconciliação final. */
SELECT
 (SELECT COUNT_BIG(*) FROM gold.fato_pedido) AS Pedidos_Gold,
 (SELECT SUM(Total_Pedidos_Calculado) FROM eda.vw_perfil_cliente_analytics) AS Pedidos_View,
 CAST((SELECT SUM(Valor_Liquido_Pedido) FROM gold.fato_pedido)
      -(SELECT SUM(Valor_Total_Gasto) FROM eda.vw_perfil_cliente_analytics) AS DECIMAL(18,2)) AS Diferenca_Receita,
 CASE WHEN (SELECT COUNT_BIG(*) FROM gold.fato_pedido)
           =(SELECT SUM(Total_Pedidos_Calculado) FROM eda.vw_perfil_cliente_analytics)
       AND ABS((SELECT SUM(Valor_Liquido_Pedido) FROM gold.fato_pedido)
              -(SELECT SUM(Valor_Total_Gasto) FROM eda.vw_perfil_cliente_analytics))<=0.01
      THEN 'APROVADO' ELSE 'REPROVADO' END AS Status_Reconciliacao;
GO
