USE [CustomerAnalyticsHub];
GO

SET NOCOUNT ON;
GO

/* ============================================================
   CUSTOMER ANALYTICS HUB
   EDA GERAL — ETAPA 02
   ANÁLISE UNIVARIADA

   Objetivos:
   1. Analisar cada variável individualmente.
   2. Preservar a granularidade de cliente, item, pedido e entrega.
   3. Calcular medidas de posição e dispersão.
   4. Identificar possíveis outliers pelo método do IQR.
   5. Analisar frequências das variáveis categóricas.

   Observação:
   - A identificação pelo IQR indica valores extremos.
   - Um valor extremo não deve ser automaticamente excluído.
   ============================================================ */


/* ============================================================
   1. BASE TEMPORÁRIA DAS VARIÁVEIS NUMÉRICAS

   Cada variável recebe explicitamente sua unidade de análise:
   - CLIENTE
   - ITEM_PEDIDO
   - PEDIDO
   - ENTREGA
   - CLIENTE_MES
   ============================================================ */

DROP TABLE IF EXISTS #Base_Numerica;
GO

CREATE TABLE #Base_Numerica
(
    Unidade_Analise VARCHAR(30)  NOT NULL,
    Variavel       VARCHAR(80)  NOT NULL,
    Valor          FLOAT        NULL
);
GO


/* ============================================================
   1.1 VARIÁVEIS NUMÉRICAS DO CLIENTE
   Granularidade: uma linha por cliente
   ============================================================ */

INSERT INTO #Base_Numerica
(
    Unidade_Analise,
    Variavel,
    Valor
)
SELECT
    'CLIENTE',
    V.Variavel,
    V.Valor
FROM gold.dim_cliente AS C
CROSS APPLY
(
    VALUES
        ('Idade',
            TRY_CONVERT(FLOAT, C.Idade)),

        ('Tempo_Experiencia_Anos',
            TRY_CONVERT(FLOAT, C.Tempo_Experiencia_Anos)),

        ('Renda_Mensal_Cliente',
            TRY_CONVERT(FLOAT, C.Renda_Mensal_Cliente)),

        ('Ciclo_Vida_Informado',
            TRY_CONVERT(FLOAT, C.Ciclo_Vida_Informado)),

        ('Intervalo_Medio_Informado',
            TRY_CONVERT(FLOAT, C.Intervalo_Medio_Informado)),

        ('Ticket_Medio_Informado',
            TRY_CONVERT(FLOAT, C.Ticket_Medio_Informado))
) AS V (Variavel, Valor);
GO


/* ============================================================
   1.2 VARIÁVEIS NUMÉRICAS DOS ITENS

   Granularidade: uma linha por item dentro de um pedido
   ============================================================ */

INSERT INTO #Base_Numerica
(
    Unidade_Analise,
    Variavel,
    Valor
)
SELECT
    'ITEM_PEDIDO',
    V.Variavel,
    V.Valor
FROM gold.fato_item_pedido AS FI
CROSS APPLY
(
    VALUES
        ('Quantidade',
            TRY_CONVERT(FLOAT, FI.Quantidade)),

        ('Custo_Unitario',
            TRY_CONVERT(FLOAT, FI.Custo_Unitario)),

        ('Preco_Unitario_Lista',
            TRY_CONVERT(FLOAT, FI.Preco_Unitario_Lista)),

        ('Desconto_Percentual',
            TRY_CONVERT(FLOAT, FI.Desconto_Percentual)),

        ('Valor_Compra',
            TRY_CONVERT(FLOAT, FI.Valor_Compra)),

        ('Valor_Bruto_Item',
            TRY_CONVERT(FLOAT, FI.Valor_Bruto_Item)),

        ('Custo_Total_Item',
            TRY_CONVERT(FLOAT, FI.Custo_Total_Item)),

        ('Valor_Desconto_Item',
            TRY_CONVERT(FLOAT, FI.Valor_Desconto_Item)),

        ('Margem_Bruta_Item',
            TRY_CONVERT(FLOAT, FI.Margem_Bruta_Item)),

        ('Margem_Percentual_Item',
            TRY_CONVERT(FLOAT, FI.Margem_Percentual_Item))
) AS V (Variavel, Valor);
GO


/* ============================================================
   1.3 VARIÁVEIS NUMÉRICAS DOS PEDIDOS

   Granularidade: uma linha por pedido
   ============================================================ */

INSERT INTO #Base_Numerica
(
    Unidade_Analise,
    Variavel,
    Valor
)
SELECT
    'PEDIDO',
    V.Variavel,
    V.Valor
FROM gold.fato_pedido AS FP
CROSS APPLY
(
    VALUES
        ('Quantidade_Linhas_Pedido',
            TRY_CONVERT(FLOAT, FP.Quantidade_Linhas_Pedido)),

        ('Quantidade_Total_Itens',
            TRY_CONVERT(FLOAT, FP.Quantidade_Total_Itens)),

        ('Quantidade_Produtos_Distintos',
            TRY_CONVERT(FLOAT, FP.Quantidade_Produtos_Distintos)),

        ('Valor_Bruto_Pedido',
            TRY_CONVERT(FLOAT, FP.Valor_Bruto_Pedido)),

        ('Valor_Desconto_Pedido',
            TRY_CONVERT(FLOAT, FP.Valor_Desconto_Pedido)),

        ('Valor_Liquido_Pedido',
            TRY_CONVERT(FLOAT, FP.Valor_Liquido_Pedido)),

        ('Custo_Total_Pedido',
            TRY_CONVERT(FLOAT, FP.Custo_Total_Pedido)),

        ('Margem_Bruta_Pedido',
            TRY_CONVERT(FLOAT, FP.Margem_Bruta_Pedido)),

        ('Margem_Percentual_Pedido',
            TRY_CONVERT(FLOAT, FP.Margem_Percentual_Pedido)),

        ('Desconto_Medio_Ponderado',
            TRY_CONVERT(FLOAT, FP.Desconto_Medio_Ponderado)),

        ('Pontos_Fidelidade_Observados',
            TRY_CONVERT(FLOAT, FP.Pontos_Fidelidade_Observados))
) AS V (Variavel, Valor);
GO


/* ============================================================
   1.4 VARIÁVEIS NUMÉRICAS DAS ENTREGAS

   Granularidade: uma linha por entrega/pedido
   ============================================================ */

INSERT INTO #Base_Numerica
(
    Unidade_Analise,
    Variavel,
    Valor
)
SELECT
    'ENTREGA',
    V.Variavel,
    V.Valor
FROM gold.fato_entrega AS FE
CROSS APPLY
(
    VALUES
        ('Frete',
            TRY_CONVERT(FLOAT, FE.Frete)),

        ('Prazo_Entrega_Prometido_Dias',
            TRY_CONVERT(FLOAT, FE.Prazo_Entrega_Prometido_Dias)),

        ('Prazo_Entrega_Real_Dias',
            TRY_CONVERT(FLOAT, FE.Prazo_Entrega_Real_Dias)),

        ('Diferenca_Prazo_Dias',
            TRY_CONVERT(FLOAT, FE.Diferenca_Prazo_Dias)),

        ('Dias_Atraso',
            TRY_CONVERT(FLOAT, FE.Dias_Atraso)),

        ('Dias_Antecipacao',
            TRY_CONVERT(FLOAT, FE.Dias_Antecipacao)),

        ('Avaliacao_Cliente',
            TRY_CONVERT(FLOAT, FE.Avaliacao_Cliente))
) AS V (Variavel, Valor);
GO


/* ============================================================
   1.5 VARIÁVEIS NUMÉRICAS DO CLIENTE POR MÊS

   Granularidade: uma linha por cliente e mês de referência

   Atenção:
   - Inclui meses sem compra.
   - Valores iguais a zero podem representar inatividade real.
   ============================================================ */

INSERT INTO #Base_Numerica
(
    Unidade_Analise,
    Variavel,
    Valor
)
SELECT
    'CLIENTE_MES',
    V.Variavel,
    V.Valor
FROM gold.fato_cliente_mes AS FCM
CROSS APPLY
(
    VALUES
        ('Pedidos_Mes',
            TRY_CONVERT(FLOAT, FCM.Pedidos_Mes)),

        ('Itens_Mes',
            TRY_CONVERT(FLOAT, FCM.Itens_Mes)),

        ('Produtos_Distintos_Mes',
            TRY_CONVERT(FLOAT, FCM.Produtos_Distintos_Mes)),

        ('Categorias_Distintas_Mes',
            TRY_CONVERT(FLOAT, FCM.Categorias_Distintas_Mes)),

        ('Receita_Liquida_Mes',
            TRY_CONVERT(FLOAT, FCM.Receita_Liquida_Mes)),

        ('Custo_Total_Mes',
            TRY_CONVERT(FLOAT, FCM.Custo_Total_Mes)),

        ('Margem_Bruta_Mes',
            TRY_CONVERT(FLOAT, FCM.Margem_Bruta_Mes)),

        ('Ticket_Medio_Calculado',
            TRY_CONVERT(FLOAT, FCM.Ticket_Medio_Calculado)),

        ('Recencia_Dias',
            TRY_CONVERT(FLOAT, FCM.Recencia_Dias)),

        ('Frequencia_Acumulada',
            TRY_CONVERT(FLOAT, FCM.Frequencia_Acumulada)),

        ('Intervalo_Medio_Calculado',
            TRY_CONVERT(FLOAT, FCM.Intervalo_Medio_Calculado)),

        ('Pontos_Fidelidade_Ultimo_Observado',
            TRY_CONVERT(FLOAT, FCM.Pontos_Fidelidade_Ultimo_Observado))
) AS V (Variavel, Valor);
GO


/* Índice para acelerar percentis, moda e detecção de outliers. */

CREATE CLUSTERED INDEX IX_Base_Numerica
ON #Base_Numerica
(
    Unidade_Analise,
    Variavel,
    Valor
);
GO


/* ============================================================
   2. ESTATÍSTICAS DESCRITIVAS

   Medidas calculadas:
   - total de observações;
   - valores válidos e nulos;
   - média;
   - moda;
   - mínimo e máximo;
   - amplitude;
   - desvio-padrão;
   - coeficiente de variação;
   - percentis;
   - quartis;
   - intervalo interquartil;
   - limites do boxplot;
   - quantidade e percentual de possíveis outliers.
   ============================================================ */

WITH Estatisticas_Basicas AS
(
    SELECT
        Unidade_Analise,
        Variavel,
        COUNT_BIG(*) AS Total_Observacoes,
        COUNT(Valor) AS Valores_Validos,
        SUM(CASE WHEN Valor IS NULL THEN 1 ELSE 0 END) AS Valores_Nulos,
        AVG(Valor) AS Media,
        STDEV(Valor) AS Desvio_Padrao,
        MIN(Valor) AS Minimo,
        MAX(Valor) AS Maximo
    FROM #Base_Numerica
    GROUP BY
        Unidade_Analise,
        Variavel
),
Percentis AS
(
    /*
       SQL Server 2022: percentis aproximados por grupo.
       Esta implementação evita nove funções de janela completas e é
       mais apropriada para exploração interativa no SQL Server Express.
    */
    SELECT
        Unidade_Analise,
        Variavel,

        APPROX_PERCENTILE_CONT(0.01)
            WITHIN GROUP (ORDER BY Valor) AS P01,

        APPROX_PERCENTILE_CONT(0.05)
            WITHIN GROUP (ORDER BY Valor) AS P05,

        APPROX_PERCENTILE_CONT(0.10)
            WITHIN GROUP (ORDER BY Valor) AS P10,

        APPROX_PERCENTILE_CONT(0.25)
            WITHIN GROUP (ORDER BY Valor) AS Q1_P25,

        APPROX_PERCENTILE_CONT(0.50)
            WITHIN GROUP (ORDER BY Valor) AS Mediana_P50,

        APPROX_PERCENTILE_CONT(0.75)
            WITHIN GROUP (ORDER BY Valor) AS Q3_P75,

        APPROX_PERCENTILE_CONT(0.90)
            WITHIN GROUP (ORDER BY Valor) AS P90,

        APPROX_PERCENTILE_CONT(0.95)
            WITHIN GROUP (ORDER BY Valor) AS P95,

        APPROX_PERCENTILE_CONT(0.99)
            WITHIN GROUP (ORDER BY Valor) AS P99
    FROM #Base_Numerica
    WHERE Valor IS NOT NULL
    GROUP BY
        Unidade_Analise,
        Variavel
),
Frequencias_Numericas AS
(
    SELECT
        Unidade_Analise,
        Variavel,
        Valor,
        COUNT_BIG(*) AS Frequencia
    FROM #Base_Numerica
    WHERE Valor IS NOT NULL
    GROUP BY
        Unidade_Analise,
        Variavel,
        Valor
),
Ranking_Moda AS
(
    SELECT
        Unidade_Analise,
        Variavel,
        Valor AS Moda,
        Frequencia AS Frequencia_Moda,

        ROW_NUMBER() OVER
        (
            PARTITION BY Unidade_Analise, Variavel
            ORDER BY Frequencia DESC, Valor
        ) AS Ordem_Moda
    FROM Frequencias_Numericas
),
Limites_Boxplot AS
(
    SELECT
        Unidade_Analise,
        Variavel,
        Q1_P25,
        Q3_P75,
        Q3_P75 - Q1_P25 AS IQR,
        Q1_P25 - (1.5 * (Q3_P75 - Q1_P25)) AS Limite_Inferior_IQR,
        Q3_P75 + (1.5 * (Q3_P75 - Q1_P25)) AS Limite_Superior_IQR
    FROM Percentis
),
Outliers AS
(
    SELECT
        B.Unidade_Analise,
        B.Variavel,

        CASE
            /*
               Quando IQR = 0, a distribuição normalmente é discreta ou
               concentrada em um único valor, como descontos com muitos
               zeros. Nesse cenário, o método de Tukey não é informativo.
            */
            WHEN MAX(L.IQR) = 0 THEN NULL
            ELSE
                SUM
                (
                    CASE
                        WHEN B.Valor < L.Limite_Inferior_IQR
                          OR B.Valor > L.Limite_Superior_IQR
                            THEN 1
                        ELSE 0
                    END
                )
        END AS Possiveis_Outliers
    FROM #Base_Numerica AS B
    INNER JOIN Limites_Boxplot AS L
        ON L.Unidade_Analise = B.Unidade_Analise
       AND L.Variavel = B.Variavel
    WHERE B.Valor IS NOT NULL
    GROUP BY
        B.Unidade_Analise,
        B.Variavel
)
SELECT
    E.Unidade_Analise,
    E.Variavel,
    E.Total_Observacoes,
    E.Valores_Validos,
    E.Valores_Nulos,

    CAST(
        100.0 * E.Valores_Nulos /
        NULLIF(E.Total_Observacoes, 0)
        AS DECIMAL(10,2)
    ) AS Percentual_Nulos,

    CAST(E.Media AS DECIMAL(18,4)) AS Media,
    CAST(P.Mediana_P50 AS DECIMAL(18,4)) AS Mediana,
    CAST(M.Moda AS DECIMAL(18,4)) AS Moda,
    M.Frequencia_Moda,

    CAST(E.Minimo AS DECIMAL(18,4)) AS Minimo,
    CAST(E.Maximo AS DECIMAL(18,4)) AS Maximo,
    CAST(E.Maximo - E.Minimo AS DECIMAL(18,4)) AS Amplitude,

    CAST(E.Desvio_Padrao AS DECIMAL(18,4)) AS Desvio_Padrao,

    CAST(
        100.0 * E.Desvio_Padrao /
        NULLIF(ABS(E.Media), 0)
        AS DECIMAL(18,4)
    ) AS Coeficiente_Variacao_Percentual,

    CAST(P.P01 AS DECIMAL(18,4)) AS P01,
    CAST(P.P05 AS DECIMAL(18,4)) AS P05,
    CAST(P.P10 AS DECIMAL(18,4)) AS P10,
    CAST(P.Q1_P25 AS DECIMAL(18,4)) AS Q1_P25,
    CAST(P.Mediana_P50 AS DECIMAL(18,4)) AS P50_Mediana,
    CAST(P.Q3_P75 AS DECIMAL(18,4)) AS Q3_P75,
    CAST(P.P90 AS DECIMAL(18,4)) AS P90,
    CAST(P.P95 AS DECIMAL(18,4)) AS P95,
    CAST(P.P99 AS DECIMAL(18,4)) AS P99,

    CAST(L.IQR AS DECIMAL(18,4)) AS IQR,
    CAST(L.Limite_Inferior_IQR AS DECIMAL(18,4)) AS Limite_Inferior_Boxplot,
    CAST(L.Limite_Superior_IQR AS DECIMAL(18,4)) AS Limite_Superior_Boxplot,

    CASE
        WHEN L.IQR IS NULL THEN 'SEM DADOS SUFICIENTES'
        WHEN L.IQR = 0 THEN 'NAO APLICAVEL - IQR ZERO'
        ELSE 'APLICAVEL'
    END AS Aplicabilidade_Metodo_IQR,

    O.Possiveis_Outliers,

    CAST(
        100.0 * O.Possiveis_Outliers /
        NULLIF(E.Valores_Validos, 0)
        AS DECIMAL(10,2)
    ) AS Percentual_Possiveis_Outliers
FROM Estatisticas_Basicas AS E
LEFT JOIN Percentis AS P
    ON P.Unidade_Analise = E.Unidade_Analise
   AND P.Variavel = E.Variavel
LEFT JOIN Ranking_Moda AS M
    ON M.Unidade_Analise = E.Unidade_Analise
   AND M.Variavel = E.Variavel
   AND M.Ordem_Moda = 1
LEFT JOIN Limites_Boxplot AS L
    ON L.Unidade_Analise = E.Unidade_Analise
   AND L.Variavel = E.Variavel
LEFT JOIN Outliers AS O
    ON O.Unidade_Analise = E.Unidade_Analise
   AND O.Variavel = E.Variavel
ORDER BY
    E.Unidade_Analise,
    E.Variavel;
GO


/* ============================================================
   3. BASE TEMPORÁRIA DAS VARIÁVEIS CATEGÓRICAS
   ============================================================ */

DROP TABLE IF EXISTS #Base_Categorica;
GO

CREATE TABLE #Base_Categorica
(
    Unidade_Analise VARCHAR(30)   NOT NULL,
    Variavel       VARCHAR(80)   NOT NULL,
    Categoria      NVARCHAR(255) NOT NULL
);
GO


/* ============================================================
   3.1 CARACTERÍSTICAS DOS CLIENTES
   ============================================================ */

INSERT INTO #Base_Categorica
(
    Unidade_Analise,
    Variavel,
    Categoria
)
SELECT
    'CLIENTE',
    V.Variavel,
    COALESCE(NULLIF(LTRIM(RTRIM(V.Categoria)), ''), N'[NULO]')
FROM gold.dim_cliente AS C
CROSS APPLY
(
    VALUES
        ('Genero',
            CONVERT(NVARCHAR(255), C.Genero)),

        ('Estado_Civil',
            CONVERT(NVARCHAR(255), C.Estado_Civil)),

        ('Escolaridade',
            CONVERT(NVARCHAR(255), C.Escolaridade)),

        ('Situacao_Profissional',
            CONVERT(NVARCHAR(255), C.Situacao_Profissional)),

        ('Profissao',
            CONVERT(NVARCHAR(255), C.Profissao)),

        ('Categoria_Favorita_Informada',
            CONVERT(NVARCHAR(255), C.Categoria_Favorita_Informada)),

        ('Pagamento_Preferido_Informado',
            CONVERT(NVARCHAR(255), C.Pagamento_Preferido_Informado)),

        ('Dia_Semana_Preferido_Informado',
            CONVERT(NVARCHAR(255), C.Dia_Semana_Preferido_Informado))
) AS V (Variavel, Categoria);
GO


/* ============================================================
   3.2 CADASTRO DE PRODUTOS

   Esta distribuição representa o catálogo, não as vendas.
   ============================================================ */

INSERT INTO #Base_Categorica
(
    Unidade_Analise,
    Variavel,
    Categoria
)
SELECT
    'PRODUTO_CADASTRADO',
    V.Variavel,
    COALESCE(NULLIF(LTRIM(RTRIM(V.Categoria)), ''), N'[NULO]')
FROM gold.dim_produto AS P
CROSS APPLY
(
    VALUES
        ('Produto',
            CONVERT(NVARCHAR(255), P.Produto)),

        ('Categoria_Item',
            CONVERT(NVARCHAR(255), P.Categoria_Item)),

        ('Medida',
            CONVERT(NVARCHAR(255), P.Medida))
) AS V (Variavel, Categoria);
GO


/* ============================================================
   3.3 PRODUTOS EFETIVAMENTE VENDIDOS

   Granularidade: item do pedido.
   Produtos repetem conforme a quantidade de linhas vendidas.
   ============================================================ */

INSERT INTO #Base_Categorica
(
    Unidade_Analise,
    Variavel,
    Categoria
)
SELECT
    'ITEM_VENDIDO',
    V.Variavel,
    COALESCE(NULLIF(LTRIM(RTRIM(V.Categoria)), ''), N'[NULO]')
FROM gold.fato_item_pedido AS FI
INNER JOIN gold.dim_produto AS P
    ON P.Produto_SK = FI.Produto_SK
CROSS APPLY
(
    VALUES
        ('Produto',
            CONVERT(NVARCHAR(255), P.Produto)),

        ('Categoria_Item',
            CONVERT(NVARCHAR(255), P.Categoria_Item))
) AS V (Variavel, Categoria);
GO


/* ============================================================
   3.4 CARACTERÍSTICAS DOS PEDIDOS
   ============================================================ */

INSERT INTO #Base_Categorica
(
    Unidade_Analise,
    Variavel,
    Categoria
)
SELECT
    'PEDIDO',
    V.Variavel,
    COALESCE(NULLIF(LTRIM(RTRIM(V.Categoria)), ''), N'[NULO]')
FROM gold.fato_pedido AS FP
INNER JOIN gold.dim_pagamento AS PG
    ON PG.Pagamento_SK = FP.Pagamento_SK
INNER JOIN gold.dim_campanha AS CP
    ON CP.Campanha_SK = FP.Campanha_SK
INNER JOIN gold.dim_canal_marketing AS CM
    ON CM.Canal_Marketing_SK = FP.Canal_Marketing_SK
INNER JOIN gold.dim_evento_externo AS EE
    ON EE.Evento_Externo_SK = FP.Evento_Externo_SK
CROSS APPLY
(
    VALUES
        ('Forma_Pagamento',
            CONVERT(NVARCHAR(255), PG.Forma_Pagamento)),

        ('Campanha',
            CONVERT(NVARCHAR(255), CP.Campanha)),

        ('Canal_Marketing',
            CONVERT(NVARCHAR(255), CM.Canal_Marketing)),

        ('Evento_Externo',
            CONVERT(NVARCHAR(255), EE.Evento_Externo)),

        ('Cupom_Status',
            CONVERT(NVARCHAR(255), FP.Cupom_Status)),

        ('Pedido_Com_Campanha',
            CASE
                WHEN FP.Pedido_Com_Campanha = 1 THEN N'Sim'
                WHEN FP.Pedido_Com_Campanha = 0 THEN N'Não'
                ELSE N'[NULO]'
            END)
) AS V (Variavel, Categoria);
GO


/* ============================================================
   3.5 CARACTERÍSTICAS DAS ENTREGAS
   ============================================================ */

INSERT INTO #Base_Categorica
(
    Unidade_Analise,
    Variavel,
    Categoria
)
SELECT
    'ENTREGA',
    V.Variavel,
    COALESCE(NULLIF(LTRIM(RTRIM(V.Categoria)), ''), N'[NULO]')
FROM gold.fato_entrega AS FE
INNER JOIN gold.dim_transportadora AS T
    ON T.Transportadora_SK = FE.Transportadora_SK
CROSS APPLY
(
    VALUES
        ('Transportadora',
            CONVERT(NVARCHAR(255), T.Transportadora)),

        ('Status_Entrega_Calculado',
            CONVERT(NVARCHAR(255), FE.Status_Entrega_Calculado)),

        ('Atraso_Entrega_Informado',
            CONVERT(NVARCHAR(255), FE.Atraso_Entrega_Informado)),

        ('Frete_Gratis',
            CASE
                WHEN FE.Frete_Gratis = 1 THEN N'Sim'
                WHEN FE.Frete_Gratis = 0 THEN N'Não'
                ELSE N'[NULO]'
            END)
) AS V (Variavel, Categoria);
GO


/* ============================================================
   3.6 GEOGRAFIA DOS CLIENTES

   A contagem representa clientes, não pedidos.
   ============================================================ */

INSERT INTO #Base_Categorica
(
    Unidade_Analise,
    Variavel,
    Categoria
)
SELECT
    'CLIENTE',
    V.Variavel,
    COALESCE(NULLIF(LTRIM(RTRIM(V.Categoria)), ''), N'[NULO]')
FROM gold.dim_cliente AS C
INNER JOIN gold.dim_geografia AS G
    ON G.Geografia_SK = C.Geografia_SK
CROSS APPLY
(
    VALUES
        ('Cidade',
            CONVERT(NVARCHAR(255), G.Cidade)),

        ('Estado',
            CONVERT(NVARCHAR(255), G.Estado)),

        ('Regiao',
            CONVERT(NVARCHAR(255), G.Regiao))
) AS V (Variavel, Categoria);
GO


/* Índice para acelerar frequências e modas categóricas. */

CREATE CLUSTERED INDEX IX_Base_Categorica
ON #Base_Categorica
(
    Unidade_Analise,
    Variavel,
    Categoria
);
GO


/* ============================================================
   4. DISTRIBUIÇÃO DE FREQUÊNCIA DAS VARIÁVEIS CATEGÓRICAS
   ============================================================ */

WITH Frequencias AS
(
    SELECT
        Unidade_Analise,
        Variavel,
        Categoria,
        COUNT_BIG(*) AS Frequencia_Absoluta
    FROM #Base_Categorica
    GROUP BY
        Unidade_Analise,
        Variavel,
        Categoria
),
Distribuicao AS
(
    SELECT
        Unidade_Analise,
        Variavel,
        Categoria,
        Frequencia_Absoluta,

        SUM(Frequencia_Absoluta) OVER
        (
            PARTITION BY Unidade_Analise, Variavel
        ) AS Total_Observacoes,

        DENSE_RANK() OVER
        (
            PARTITION BY Unidade_Analise, Variavel
            ORDER BY Frequencia_Absoluta DESC
        ) AS Posicao_Frequencia
    FROM Frequencias
)
SELECT
    Unidade_Analise,
    Variavel,
    Categoria,
    Frequencia_Absoluta,
    Total_Observacoes,

    CAST(
        100.0 * Frequencia_Absoluta /
        NULLIF(Total_Observacoes, 0)
        AS DECIMAL(10,2)
    ) AS Frequencia_Percentual,

    Posicao_Frequencia,

    CASE
        WHEN Categoria = N'[NULO]' THEN 'AUSENTE'
        ELSE 'PREENCHIDO'
    END AS Status_Preenchimento
FROM Distribuicao
ORDER BY
    Unidade_Analise,
    Variavel,
    Frequencia_Absoluta DESC,
    Categoria;
GO


/* ============================================================
   5. MODA DAS VARIÁVEIS CATEGÓRICAS

   DENSE_RANK preserva empates:
   se duas categorias tiverem a mesma maior frequência,
   ambas serão apresentadas como moda.
   ============================================================ */

WITH Frequencias AS
(
    SELECT
        Unidade_Analise,
        Variavel,
        Categoria,
        COUNT_BIG(*) AS Frequencia_Absoluta
    FROM #Base_Categorica
    GROUP BY
        Unidade_Analise,
        Variavel,
        Categoria
),
Ranking_Moda AS
(
    SELECT
        Unidade_Analise,
        Variavel,
        Categoria AS Moda,
        Frequencia_Absoluta,

        SUM(Frequencia_Absoluta) OVER
        (
            PARTITION BY Unidade_Analise, Variavel
        ) AS Total_Observacoes,

        DENSE_RANK() OVER
        (
            PARTITION BY Unidade_Analise, Variavel
            ORDER BY Frequencia_Absoluta DESC
        ) AS Posicao_Moda
    FROM Frequencias
)
SELECT
    Unidade_Analise,
    Variavel,
    Moda,
    Frequencia_Absoluta AS Frequencia_Moda,

    CAST(
        100.0 * Frequencia_Absoluta /
        NULLIF(Total_Observacoes, 0)
        AS DECIMAL(10,2)
    ) AS Percentual_Moda
FROM Ranking_Moda
WHERE Posicao_Moda = 1
ORDER BY
    Unidade_Analise,
    Variavel,
    Moda;
GO


/* ============================================================
   6. LIMPEZA DAS TABELAS TEMPORÁRIAS
   ============================================================ */

DROP TABLE IF EXISTS #Base_Numerica;
DROP TABLE IF EXISTS #Base_Categorica;
GO
