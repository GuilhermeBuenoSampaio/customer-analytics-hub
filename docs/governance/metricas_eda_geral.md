# Catálogo de Métricas — EDA Geral

## Customer Analytics Hub

| Campo                   | Valor                                      |
| ----------------------- | ------------------------------------------ |
| Documento               | Catálogo de métricas da EDA geral          |
| Versão                  | 1.0                                        |
| Camada de origem        | Gold                                       |
| Banco                   | CustomerAnalyticsHub                       |
| Ferramentas             | SQL Server e Power BI                      |
| Quantidade de métricas  | 8                                          |
| Status da reconciliação | Pendente de validação final SQL versus DAX |

---

## 1. Objetivo

Este documento registra as definições canônicas das métricas utilizadas no dashboard da EDA geral.

O catálogo tem como objetivos:

* evitar definições diferentes para um mesmo indicador;
* garantir consistência entre SQL Server e Power BI;
* documentar fórmulas, fontes e granularidades;
* registrar o tratamento de valores nulos;
* facilitar a reutilização das métricas;
* apoiar auditorias e reconciliações;
* manter os indicadores consistentes entre os domínios comercial, financeiro, logístico e de marketing.

Uma métrica somente deverá ser considerada aprovada depois que sua definição, cálculo e resultado forem validados.

---

## 2. Regras gerais de governança

Cada métrica deve possuir:

* identificador único;
* nome canônico;
* definição de negócio;
* fórmula;
* tabela de origem;
* coluna de origem;
* granularidade;
* contexto de filtro;
* tratamento de nulos;
* unidade;
* formato;
* regra de validação;
* limitações;
* versão;
* status.

Alterações posteriores devem gerar uma nova versão da definição quando modificarem o significado ou o resultado do indicador.

---

## 3. Resumo das métricas

| ID          | Métrica             | Tipo              | Tabela principal        | Unidade    |
| ----------- | ------------------- | ----------------- | ----------------------- | ---------- |
| MET-EDA-001 | Clientes analisados | Contagem distinta | `gold.fato_pedido`      | Clientes   |
| MET-EDA-002 | Pedidos             | Contagem          | `gold.fato_pedido`      | Pedidos    |
| MET-EDA-003 | Itens vendidos      | Soma              | `gold.fato_item_pedido` | Unidades   |
| MET-EDA-004 | Receita líquida     | Soma monetária    | `gold.fato_pedido`      | R$         |
| MET-EDA-005 | Ticket médio        | Razão             | Medidas derivadas       | R$/pedido  |
| MET-EDA-006 | Margem bruta        | Soma monetária    | `gold.fato_pedido`      | R$         |
| MET-EDA-007 | Avaliação média     | Média aritmética  | `gold.fato_entrega`     | Pontos     |
| MET-EDA-008 | Taxa de atraso      | Proporção         | `gold.fato_entrega`     | Percentual |

---

# 4. MET-EDA-001 — Clientes analisados

## 4.1 Identificação

| Campo                 | Definição                                               |
| --------------------- | ------------------------------------------------------- |
| ID                    | MET-EDA-001                                             |
| Nome canônico         | Clientes analisados                                     |
| Nome no Power BI      | `Clientes Analisados`                                   |
| Tipo                  | Contagem distinta                                       |
| Domínios consumidores | EDA geral, comercial, financeiro, logística e marketing |
| Versão                | 1.0                                                     |
| Status                | Implementada; reconciliação final pendente              |

## 4.2 Definição de negócio

Quantidade de clientes distintos que possuem pelo menos um pedido no contexto de filtro analisado.

A métrica não representa necessariamente todos os clientes cadastrados na dimensão de clientes. Ela considera somente os clientes presentes na tabela de pedidos.

## 4.3 Fonte

| Campo                   | Origem               |
| ----------------------- | -------------------- |
| Tabela SQL              | `gold.fato_pedido`   |
| Tabela no Power BI      | `gold fato_pedido`   |
| Coluna                  | `Cliente_SK`         |
| Granularidade da origem | Uma linha por pedido |

## 4.4 Fórmula DAX

```DAX
Clientes Analisados =
DISTINCTCOUNT('gold fato_pedido'[Cliente_SK])
```

## 4.5 Validação em SQL

```sql
SELECT
    COUNT(DISTINCT Cliente_SK) AS Clientes_Analisados
FROM gold.fato_pedido;
```

## 4.6 Regras

* Contar cada `Cliente_SK` apenas uma vez no contexto selecionado;
* Respeitar os filtros propagados pelas dimensões;
* Não utilizar `COUNTROWS` na dimensão de clientes;
* Não somar clientes mensais para obter o total geral;
* Valores nulos de `Cliente_SK` não devem representar clientes válidos.

## 4.7 Unidade e formato

| Campo               | Valor              |
| ------------------- | ------------------ |
| Unidade             | Clientes           |
| Casas decimais      | 0                  |
| Separador de milhar | Sim                |
| Unidade automática  | Opcional no visual |

## 4.8 Interpretação

A métrica informa o alcance da operação entre clientes que efetivamente realizaram pedidos.

Uma redução mensal pode indicar menor atividade, sazonalidade, perda de clientes ou mudança no período selecionado. A métrica isolada não explica a causa da variação.

## 4.9 Limitações

* Não mede clientes cadastrados sem pedido;
* Não distingue clientes novos de recorrentes;
* Não representa retenção;
* Não deve ser somada entre meses, pois um mesmo cliente pode aparecer em vários períodos.

---

# 5. MET-EDA-002 — Pedidos

## 5.1 Identificação

| Campo                 | Definição                                  |
| --------------------- | ------------------------------------------ |
| ID                    | MET-EDA-002                                |
| Nome canônico         | Pedidos                                    |
| Nome no Power BI      | `Pedidos`                                  |
| Tipo                  | Contagem de linhas                         |
| Domínios consumidores | Todos                                      |
| Versão                | 1.0                                        |
| Status                | Implementada; reconciliação final pendente |

## 5.2 Definição de negócio

Quantidade de pedidos registrados no contexto de filtro analisado.

A métrica depende da premissa de que cada linha da tabela `gold.fato_pedido` representa exatamente um pedido.

## 5.3 Fonte

| Campo               | Origem                                   |
| ------------------- | ---------------------------------------- |
| Tabela SQL          | `gold.fato_pedido`                       |
| Tabela no Power BI  | `gold fato_pedido`                       |
| Granularidade       | Uma linha por pedido                     |
| Chave de referência | `Pedido_SK` ou identificador equivalente |

## 5.4 Fórmula DAX

```DAX
Pedidos =
COUNTROWS('gold fato_pedido')
```

## 5.5 Validação em SQL

```sql
SELECT
    COUNT(*) AS Pedidos
FROM gold.fato_pedido;
```

### Validação complementar de granularidade

```sql
SELECT
    COUNT(*) AS Total_Linhas,
    COUNT(DISTINCT Pedido_SK) AS Pedidos_Distintos
FROM gold.fato_pedido;
```

O total de linhas deve ser igual ao total de chaves de pedido distintas.

## 5.6 Regras

* Cada linha deve representar um pedido;
* A chave do pedido não pode estar duplicada;
* A medida deve respeitar filtros temporais e dimensionais;
* Pedidos não devem ser contados na tabela de itens;
* O valor exibido como `3 mil` no cartão é uma abreviação visual.

## 5.7 Unidade e formato

| Campo                            | Valor               |
| -------------------------------- | ------------------- |
| Unidade                          | Pedidos             |
| Casas decimais                   | 0                   |
| Unidade automática               | Ativada no cartão   |
| Valor técnico para reconciliação | Valor inteiro exato |

## 5.8 Interpretação

A métrica mede o volume de transações comerciais.

Deve ser analisada junto de clientes, itens vendidos, receita e ticket médio para distinguir crescimento em quantidade de pedidos de crescimento em valor.

## 5.9 Limitações

* Não mede quantidade de itens;
* Não mede quantidade de produtos distintos;
* Não demonstra rentabilidade;
* Depende da integridade da granularidade da tabela.

---

# 6. MET-EDA-003 — Itens vendidos

## 6.1 Identificação

| Campo                 | Definição                                    |
| --------------------- | -------------------------------------------- |
| ID                    | MET-EDA-003                                  |
| Nome canônico         | Itens vendidos                               |
| Nome no Power BI      | `Itens Vendidos`                             |
| Tipo                  | Soma                                         |
| Domínios consumidores | EDA geral, comercial, financeiro e marketing |
| Versão                | 1.0                                          |
| Status                | Implementada; reconciliação final pendente   |

## 6.2 Definição de negócio

Quantidade total de unidades de produtos vendidas no contexto analisado.

A métrica soma a coluna `Quantidade`. Ela não conta apenas as linhas da tabela.

## 6.3 Fonte

| Campo              | Origem                       |
| ------------------ | ---------------------------- |
| Tabela SQL         | `gold.fato_item_pedido`      |
| Tabela no Power BI | `gold fato_item_pedido`      |
| Coluna             | `Quantidade`                 |
| Granularidade      | Uma linha por item do pedido |

## 6.4 Fórmula DAX

```DAX
Itens Vendidos =
SUM('gold fato_item_pedido'[Quantidade])
```

## 6.5 Validação em SQL

```sql
SELECT
    SUM(Quantidade) AS Itens_Vendidos
FROM gold.fato_item_pedido;
```

## 6.6 Regras

* Somar unidades vendidas;
* Não substituir a soma por contagem de linhas;
* Quantidades devem ser maiores ou iguais a 1;
* Valores nulos devem ser investigados;
* A medida deve respeitar os filtros das dimensões relacionadas.

## 6.7 Unidade e formato

| Campo                            | Valor                |
| -------------------------------- | -------------------- |
| Unidade                          | Unidades vendidas    |
| Casas decimais                   | 0                    |
| Unidade automática               | Ativada no cartão    |
| Valor técnico para reconciliação | Número inteiro exato |

## 6.8 Interpretação

A métrica informa o volume físico vendido.

Quando comparada aos pedidos, permite estimar a quantidade média de itens por pedido. Quando comparada à receita, ajuda a avaliar se o crescimento financeiro ocorreu por aumento de volume ou de valor.

## 6.9 Limitações

* Não representa produtos distintos;
* Não representa número de linhas;
* Não indica receita;
* Pode crescer sem aumento proporcional da margem.

---

# 7. MET-EDA-004 — Receita líquida

## 7.1 Identificação

| Campo                 | Definição                                    |
| --------------------- | -------------------------------------------- |
| ID                    | MET-EDA-004                                  |
| Nome canônico         | Receita líquida                              |
| Nome no Power BI      | `Receita Líquida`                            |
| Tipo                  | Soma monetária                               |
| Domínios consumidores | EDA geral, comercial, financeiro e marketing |
| Versão                | 1.0                                          |
| Status                | Implementada; reconciliação final pendente   |

## 7.2 Definição de negócio

Somatório do valor líquido dos pedidos no contexto de filtro analisado.

Representa o valor dos pedidos após os descontos considerados na construção do campo `Valor_Liquido_Pedido`.

## 7.3 Fonte

| Campo              | Origem                 |
| ------------------ | ---------------------- |
| Tabela SQL         | `gold.fato_pedido`     |
| Tabela no Power BI | `gold fato_pedido`     |
| Coluna             | `Valor_Liquido_Pedido` |
| Granularidade      | Uma linha por pedido   |

## 7.4 Fórmula DAX

```DAX
Receita Líquida =
SUM('gold fato_pedido'[Valor_Liquido_Pedido])
```

## 7.5 Validação em SQL

```sql
SELECT
    SUM(Valor_Liquido_Pedido) AS Receita_Liquida
FROM gold.fato_pedido;
```

## 7.6 Regras

* Somar o valor líquido uma vez por pedido;
* Não calcular a medida pela tabela de itens sem reconciliação;
* Respeitar filtros temporais e dimensionais;
* Valores nulos precisam ser analisados;
* Diferenças causadas apenas por arredondamento devem ser documentadas.

## 7.7 Unidade e formato

| Campo                        | Valor                 |
| ---------------------------- | --------------------- |
| Unidade                      | Real brasileiro       |
| Símbolo                      | R$                    |
| Casas decimais               | 2                     |
| Unidade automática no cartão | Mil                   |
| Formato técnico              | Valor monetário exato |

## 7.8 Interpretação

A receita líquida mede o valor efetivamente reconhecido nos pedidos depois dos descontos considerados.

Seu crescimento deve ser comparado com custos, margem, pedidos e itens vendidos.

## 7.9 Limitações

* Receita não equivale a lucro;
* Não incorpora interpretação causal;
* Depende da regra de construção do valor líquido;
* O valor abreviado no cartão não deve ser usado na reconciliação.

---

# 8. MET-EDA-005 — Ticket médio

## 8.1 Identificação

| Campo                 | Definição                                    |
| --------------------- | -------------------------------------------- |
| ID                    | MET-EDA-005                                  |
| Nome canônico         | Ticket médio                                 |
| Nome no Power BI      | `Ticket Médio`                               |
| Tipo                  | Razão                                        |
| Domínios consumidores | EDA geral, comercial, financeiro e marketing |
| Versão                | 1.0                                          |
| Status                | Implementada; reconciliação final pendente   |

## 8.2 Definição de negócio

Valor líquido médio por pedido no contexto analisado.

## 8.3 Componentes

| Componente                                      | Métrica         |
| ----------------------------------------------- | --------------- |
| Numerador                                       | Receita líquida |
| Denominador                                     | Pedidos         |
| Resultado alternativo quando não houver pedidos | 0               |

## 8.4 Fórmula matemática

$$
\text{Ticket Médio} =
\frac{\text{Receita Líquida}}{\text{Quantidade de Pedidos}}
$$

## 8.5 Fórmula DAX

```DAX
Ticket Médio =
DIVIDE([Receita Líquida], [Pedidos], 0)
```

## 8.6 Validação em SQL

```sql
SELECT
    CAST(
        SUM(Valor_Liquido_Pedido) /
        NULLIF(COUNT(*), 0)
        AS DECIMAL(18, 2)
    ) AS Ticket_Medio
FROM gold.fato_pedido;
```

## 8.7 Regras

* Utilizar receita líquida como numerador;
* Utilizar pedidos como denominador;
* Proteger a divisão contra zero;
* Calcular o indicador no contexto de filtro;
* Não calcular pela média simples de tickets mensais.

## 8.8 Unidade e formato

| Campo             | Valor           |
| ----------------- | --------------- |
| Unidade           | R$ por pedido   |
| Símbolo           | R$              |
| Casas decimais    | 2               |
| Tipo de agregação | Medida derivada |

## 8.9 Interpretação

O ticket médio informa quanto, em média, cada pedido representa em receita líquida.

O aumento pode ocorrer por:

* maior quantidade de itens por pedido;
* produtos mais caros;
* menor desconto;
* mudança na composição das vendas;
* mudança no perfil de clientes.

A métrica isolada não identifica qual desses fatores provocou a alteração.

## 8.10 Limitações

* A média pode ser influenciada por pedidos muito altos;
* Não representa mediana;
* Não mostra dispersão;
* Não mede rentabilidade;
* Não deve ser calculada como média dos tickets de grupos.

---

# 9. MET-EDA-006 — Margem bruta

## 9.1 Identificação

| Campo                 | Definição                                  |
| --------------------- | ------------------------------------------ |
| ID                    | MET-EDA-006                                |
| Nome canônico         | Margem bruta                               |
| Nome no Power BI      | `Margem Bruta`                             |
| Tipo                  | Soma monetária                             |
| Domínios consumidores | EDA geral, comercial e financeiro          |
| Versão                | 1.0                                        |
| Status                | Implementada; reconciliação final pendente |

## 9.2 Definição de negócio

Somatório da margem bruta monetária dos pedidos no contexto analisado.

A medida representa valor monetário, não percentual de margem.

## 9.3 Fonte

| Campo              | Origem                |
| ------------------ | --------------------- |
| Tabela SQL         | `gold.fato_pedido`    |
| Tabela no Power BI | `gold fato_pedido`    |
| Coluna             | `Margem_Bruta_Pedido` |
| Granularidade      | Uma linha por pedido  |

## 9.4 Fórmula DAX

```DAX
Margem Bruta =
SUM('gold fato_pedido'[Margem_Bruta_Pedido])
```

## 9.5 Validação em SQL

```sql
SELECT
    SUM(Margem_Bruta_Pedido) AS Margem_Bruta
FROM gold.fato_pedido;
```

## 9.6 Regras

* Somar o valor de margem uma vez por pedido;
* Não aplicar formato percentual;
* Respeitar o contexto de filtro;
* Validar a regra de formação da margem na camada Gold;
* Comparar o resultado com receita líquida e custo total.

## 9.7 Unidade e formato

| Campo                        | Valor           |
| ---------------------------- | --------------- |
| Unidade                      | Real brasileiro |
| Símbolo                      | R$              |
| Casas decimais               | 2               |
| Unidade automática no cartão | Mil             |

## 9.8 Interpretação

A margem bruta representa o valor financeiro restante depois da dedução dos custos considerados na definição do dataset.

O crescimento da receita sem crescimento proporcional da margem pode indicar mudança no mix, aumento de custos ou concessão de descontos.

## 9.9 Limitações

* Não representa margem percentual;
* Não equivale ao lucro líquido;
* Não inclui necessariamente todas as despesas operacionais;
* Depende da definição de custo utilizada na camada Gold.

---

# 10. MET-EDA-007 — Avaliação média

## 10.1 Identificação

| Campo                 | Definição                                  |
| --------------------- | ------------------------------------------ |
| ID                    | MET-EDA-007                                |
| Nome canônico         | Avaliação média                            |
| Nome no Power BI      | `Avaliação Média`                          |
| Tipo                  | Média aritmética                           |
| Domínios consumidores | EDA geral, logística e clientes            |
| Versão                | 1.0                                        |
| Status                | Implementada; reconciliação final pendente |

## 10.2 Definição de negócio

Média aritmética das avaliações de clientes registradas nas entregas dentro do contexto analisado.

## 10.3 Fonte

| Campo              | Origem                          |
| ------------------ | ------------------------------- |
| Tabela SQL         | `gold.fato_entrega`             |
| Tabela no Power BI | `gold fato_entrega`             |
| Coluna             | `Avaliacao_Cliente`             |
| Granularidade      | Uma linha por evento de entrega |

## 10.4 Fórmula DAX

```DAX
Avaliação Média =
AVERAGE('gold fato_entrega'[Avaliacao_Cliente])
```

## 10.5 Validação em SQL

```sql
SELECT
    AVG(CAST(Avaliacao_Cliente AS DECIMAL(18, 4))) AS Avaliacao_Media
FROM gold.fato_entrega
WHERE Avaliacao_Cliente IS NOT NULL;
```

## 10.6 Regras

* Utilizar apenas avaliações preenchidas;
* Não transformar nulos em zero;
* Respeitar filtros temporais e dimensionais;
* Preservar a escala original da avaliação;
* Arredondar somente na apresentação.

## 10.7 Unidade e formato

| Campo               | Valor                         |
| ------------------- | ----------------------------- |
| Unidade             | Pontos                        |
| Casas decimais      | 2                             |
| Escala              | Conforme definição do dataset |
| Tratamento de nulos | Ignorados                     |

## 10.8 Interpretação

A métrica resume a percepção média dos clientes sobre as entregas.

Deve ser analisada com:

* atraso;
* prazo prometido;
* prazo realizado;
* transportadora;
* região;
* período.

## 10.9 Limitações

* A média pode esconder avaliações extremas;
* Nem todas as entregas podem possuir avaliação;
* Ausência de avaliação não significa avaliação zero;
* Não demonstra a distribuição das notas;
* Não permite inferir causalidade sem análise adicional.

---

# 11. MET-EDA-008 — Taxa de atraso

## 11.1 Identificação

| Campo                 | Definição                                  |
| --------------------- | ------------------------------------------ |
| ID                    | MET-EDA-008                                |
| Nome canônico         | Taxa de atraso                             |
| Nome no Power BI      | `Taxa de Atraso`                           |
| Tipo                  | Proporção                                  |
| Domínios consumidores | EDA geral e logística                      |
| Versão                | 1.0                                        |
| Status                | Implementada; reconciliação final pendente |

## 11.2 Definição de negócio

Proporção de entregas com atraso informado como verdadeiro em relação ao total de entregas que possuem informação válida de atraso.

Registros sem informação não são classificados automaticamente como entregas no prazo.

## 11.3 Fonte

| Campo              | Origem                          |
| ------------------ | ------------------------------- |
| Tabela SQL         | `gold.fato_entrega`             |
| Tabela no Power BI | `gold fato_entrega`             |
| Coluna             | `Atraso_Entrega_Informado`      |
| Granularidade      | Uma linha por evento de entrega |

## 11.4 Fórmula matemática

$$
\text{Taxa de Atraso} =
\frac{\text{Entregas com atraso}}
{\text{Entregas com informação de atraso válida}}
$$

## 11.5 Fórmula DAX

```DAX
Taxa de Atraso =
DIVIDE(
    CALCULATE(
        COUNTROWS('gold fato_entrega'),
        'gold fato_entrega'[Atraso_Entrega_Informado] = TRUE()
    ),
    COUNTROWS(
        FILTER(
            'gold fato_entrega',
            NOT ISBLANK('gold fato_entrega'[Atraso_Entrega_Informado])
        )
    ),
    0
)
```

## 11.6 Validação em SQL

```sql
SELECT
    CAST(
        SUM(
            CASE
                WHEN Atraso_Entrega_Informado = 1 THEN 1
                ELSE 0
            END
        ) * 1.0
        /
        NULLIF(
            SUM(
                CASE
                    WHEN Atraso_Entrega_Informado IS NOT NULL THEN 1
                    ELSE 0
                END
            ),
            0
        )
        AS DECIMAL(18, 6)
    ) AS Taxa_Atraso
FROM gold.fato_entrega;
```

## 11.7 Regras

* Numerador: entregas com valor verdadeiro;
* Denominador: entregas com informação preenchida;
* Nulos não devem ser classificados como falso;
* A divisão por zero deve retornar zero;
* O resultado deve ser armazenado como proporção e exibido como percentual.

## 11.8 Unidade e formato

| Campo               | Valor                         |
| ------------------- | ----------------------------- |
| Unidade técnica     | Proporção entre 0 e 1         |
| Unidade de exibição | Percentual                    |
| Casas decimais      | 2                             |
| Exemplo             | `0,0990` exibido como `9,90%` |

## 11.9 Interpretação

A taxa de atraso mede a participação das entregas atrasadas entre as entregas com informação válida.

O aumento do indicador pode estar associado a:

* transportadora;
* região;
* sazonalidade;
* eventos externos;
* prazo prometido;
* volume de pedidos;
* capacidade operacional.

Essas hipóteses devem ser investigadas na análise logística.

## 11.10 Limitações

* Não mede quantidade de dias de atraso;
* Não identifica a causa;
* Depende da completude do campo;
* Pode ser afetada por diferentes volumes mensais;
* Não deve ser interpretada isoladamente como avaliação integral da logística.

---

# 12. Regras de reconciliação SQL versus DAX

## 12.1 Procedimento

Para cada métrica:

1. Remover filtros do relatório;
2. Registrar o valor exato apresentado pelo Power BI;
3. Executar a consulta SQL correspondente;
4. Comparar os resultados;
5. Registrar diferença absoluta;
6. Registrar diferença percentual;
7. Investigar divergências;
8. Salvar evidência;
9. Classificar a métrica como aprovada ou reprovada.

## 12.2 Critérios de aceitação

| Tipo de métrica   | Critério                                                                        |
| ----------------- | ------------------------------------------------------------------------------- |
| Contagem          | Diferença igual a zero                                                          |
| Contagem distinta | Diferença igual a zero                                                          |
| Soma de unidades  | Diferença igual a zero                                                          |
| Valor monetário   | Igualdade antes da formatação ou diferença apenas de arredondamento documentado |
| Média             | Igualdade dentro da precisão decimal definida                                   |
| Percentual        | Igualdade dentro da precisão decimal definida                                   |
| Razão             | Igualdade dentro da precisão decimal definida                                   |

## 12.3 Modelo de registro

| ID          | Resultado SQL | Resultado DAX | Diferença | Status   | Evidência |
| ----------- | ------------: | ------------: | --------: | -------- | --------- |
| MET-EDA-001 |      Pendente |      Pendente |  Pendente | Pendente | Pendente  |
| MET-EDA-002 |      Pendente |      Pendente |  Pendente | Pendente | Pendente  |
| MET-EDA-003 |      Pendente |      Pendente |  Pendente | Pendente | Pendente  |
| MET-EDA-004 |      Pendente |      Pendente |  Pendente | Pendente | Pendente  |
| MET-EDA-005 |      Pendente |      Pendente |  Pendente | Pendente | Pendente  |
| MET-EDA-006 |      Pendente |      Pendente |  Pendente | Pendente | Pendente  |
| MET-EDA-007 |      Pendente |      Pendente |  Pendente | Pendente | Pendente  |
| MET-EDA-008 |      Pendente |      Pendente |  Pendente | Pendente | Pendente  |

---

# 13. Contexto temporal

As métricas utilizam a dimensão:

```text
gold.dim_data
```

A segmentação e os eixos temporais utilizam:

```text
Ano_Mes_Exibicao
```

A coluna de exibição é ordenada pela coluna:

```text
Ano_Mes
```

Essa configuração preserva a ordem cronológica.

As medidas devem apresentar o mesmo resultado quando o mesmo período for aplicado no SQL Server e no Power BI.

---

# 14. Controle de alterações

| Versão | Alteração                                | Status       |
| ------ | ---------------------------------------- | ------------ |
| 1.0    | Criação das oito definições da EDA geral | Em validação |

Alterações futuras devem registrar:

* data;
* versão;
* métrica afetada;
* definição anterior;
* nova definição;
* justificativa;
* impacto;
* responsável;
* resultado da nova reconciliação.

---

# 15. Critério de aprovação do catálogo

O catálogo será considerado aprovado quando:

* as oito definições estiverem revisadas;
* as fórmulas DAX estiverem iguais às implementadas;
* as colunas SQL estiverem confirmadas;
* as consultas SQL forem executadas;
* os resultados SQL e Power BI forem reconciliados;
* as evidências estiverem armazenadas;
* todas as métricas estiverem classificadas como aprovadas;
* eventuais diferenças estiverem justificadas;
* o documento estiver versionado no GitHub.

---

# 16. Conclusão

As oito métricas da EDA geral formam a base compartilhada das análises futuras.

A formalização das definições evita que diferentes áreas calculem o mesmo indicador de maneiras incompatíveis.

O catálogo também cria uma ponte verificável entre:

* regra de negócio;
* estrutura dimensional;
* cálculo SQL;
* medida DAX;
* visualização;
* interpretação analítica.

As próximas análises poderão aprofundar diferentes perspectivas do negócio, mas deverão preservar estas definições enquanto não houver uma alteração formalmente versionada.
