# AC01 — Origem e qualidade do crescimento comercial

## Customer Analytics Hub

| Campo | Valor |
|---|---|
| Domínio | Análise Comercial |
| Questão analítica | AC01 — Origem e qualidade do crescimento |
| Banco de dados | `CustomerAnalyticsHub` |
| Camada de dados | Gold |
| Período observado | Janeiro a dezembro de 2025 |
| Data da consolidação | 05/10/2026 |
| Status | Concluído e validado |

---

## 1. Objetivo

Esta etapa investiga de onde veio o crescimento comercial observado em 2025 e se a expansão da receita foi acompanhada por crescimento sustentável da margem.

A análise procura distinguir os efeitos de:

- quantidade de clientes;
- frequência de compra;
- ticket médio;
- quantidade de itens por pedido;
- receita média por item;
- participação de clientes novos e recorrentes;
- categorias e produtos;
- descontos, campanhas, frete grátis e eventos externos;
- composição do mix comercial.

O objetivo não é apenas identificar meses de alta ou queda, mas explicar matematicamente quais componentes contribuíram para cada variação.

---

## 2. Artefatos relacionados

| Artefato | Caminho |
|---|---|
| Diagnóstico da base comercial | `sql/04_business/commercial/01_diagnostico_base_comercial.sql` |
| Decomposição do crescimento | `sql/04_business/commercial/02_decomposicao_crescimento_comercial.sql` |
| Exportação para Parquet | `src/pipeline/commercial/exportar_resultados_comerciais.py` |
| Sincronização com o Azure | `src/pipeline/commercial/sincronizar_resultados_comerciais_azure.py` |
| Resultados locais | `data/exports/commercial/` |
| Manifestos de qualidade | `quality/commercial/exportacao_parquet/` |

Os arquivos Parquet e os manifestos de execução são armazenados no Azure. O GitHub mantém os códigos SQL, Python e a documentação.

---

## 3. Validação da materialização

Foram materializados nove blocos analíticos em formato Parquet.

| Bloco | Linhas | Colunas | Status |
|---|---:|---:|---|
| `01_evolucao_mensal` | 12 | 21 | Aprovado |
| `02_shapley_receita` | 11 | 12 | Aprovado |
| `03_decomposicao_ticket` | 11 | 11 | Aprovado |
| `04_novos_recorrentes` | 23 | 10 | Aprovado |
| `05_participacao_novos_recorrentes` | 23 | 7 | Aprovado |
| `06_desempenho_categoria` | 156 | 9 | Aprovado |
| `07_pareto_produtos` | 419 | 12 | Aprovado |
| `08_alerta_crescimento` | 11 | 12 | Aprovado |
| `09_primeiro_ultimo_mes` | 1 | 20 | Aprovado |

A conexão SQL Server, a escrita, a releitura e a estrutura dos Parquets foram aprovadas. A publicação no Azure também foi validada por SHA-256 e por uma segunda execução idempotente, sem duplicação de conteúdo.

---

## 4. Indicadores canônicos de referência

| Indicador | Resultado anual |
|---|---:|
| Clientes analisados | 330 |
| Pedidos | 2.789 |
| Itens vendidos | 13.375 |
| Receita líquida | R$ 289.904,66 |
| Ticket médio | R$ 103,95 |
| Margem bruta | R$ 151.248,65 |
| Avaliação média | 4,27 |
| Taxa de atraso | 9,90% |

Esses valores foram anteriormente reconciliados entre SQL Server e DAX e constituem a referência canônica da análise.

---

## 5. Bloco 01 — Evolução mensal

### 5.1 Principais resultados

- Abril apresentou o maior desempenho econômico do ano: receita de **R$ 42.106,61**, margem bruta de **R$ 22.888,27** e margem percentual de **54,36%**.
- Maio registrou o maior volume: **403 pedidos** e **1.806 itens**, mas a receita caiu para **R$ 36.936,86**.
- Entre junho e outubro ocorreu uma trajetória predominantemente negativa de receita.
- Agosto apresentou estabilidade de receita, com aumento de margem monetária e percentual.
- Dezembro registrou forte recuperação: receita de **R$ 31.871,14**, margem de **R$ 17.063,40** e ticket médio de **R$ 125,48**.

### 5.2 Interpretação

O maior volume de vendas não garantiu o melhor resultado financeiro. A comparação entre abril e maio mostra que o crescimento de pedidos e itens pode coexistir com queda de receita e margem quando há redução do ticket ou deterioração do mix.

Abril representa o melhor equilíbrio observado entre escala, ticket, receita e margem. Maio demonstra que volume isolado não deve ser utilizado como sinônimo de desempenho comercial.

---

## 6. Bloco 02 — Decomposição Shapley da receita

A receita foi decomposta pela identidade:

```text
Receita = clientes × frequência × ticket médio
```

O método de Shapley distribuiu a variação mensal entre os três componentes, considerando todas as ordens possíveis de alteração. Dessa forma, os efeitos de interação não são atribuídos arbitrariamente a apenas uma variável.

### 6.1 Leituras relevantes

| Transição | Variação da receita | Principal leitura |
|---|---:|---|
| Jan → Fev | +R$ 7.936,29 | Predomínio do aumento de clientes |
| Fev → Mar | +R$ 4.604,63 | Clientes compensaram frequência e ticket negativos |
| Mar → Abr | +R$ 27.822,11 | Clientes e ticket foram os principais motores |
| Abr → Mai | −R$ 5.169,75 | Frequência cresceu, mas a queda do ticket dominou |
| Mai → Jun | −R$ 4.324,56 | Queda de frequência superou clientes e ticket positivos |
| Jun → Jul | −R$ 1.730,42 | Redução de clientes foi o principal efeito negativo |
| Jul → Ago | +R$ 58,53 | Ticket e frequência compensaram a perda de clientes |
| Ago → Set | −R$ 7.876,09 | Frequência e ticket explicaram a maior parte da queda |
| Set → Out | −R$ 5.669,45 | Redução de clientes foi o principal fator |
| Out → Nov | +R$ 993,45 | Entrada de clientes compensou frequência menor |
| Nov → Dez | +R$ 13.482,82 | Frequência e ticket lideraram a recuperação |

Todos os resíduos matemáticos ficaram próximos de zero e as onze decomposições foram aprovadas.

### 6.2 Conclusão

O crescimento não teve uma única origem. Em alguns períodos predominou a expansão da base observada; em outros, frequência ou ticket. Essa diferença é importante porque cada motor exige uma ação comercial distinta.

---

## 7. Bloco 03 — Decomposição do ticket médio

O ticket foi decomposto pela identidade:

```text
Ticket médio = itens por pedido × receita por item
```

### 7.1 Principais resultados

- Janeiro para fevereiro: o aumento de **R$ 12,94** veio quase integralmente de mais itens por pedido.
- Março para abril: o crescimento de **R$ 46,64** foi explicado principalmente pelo aumento de **R$ 45,53** na contribuição da receita por item.
- Abril para maio: a queda de **R$ 34,79** foi explicada principalmente pela redução de **R$ 31,09** na contribuição da receita por item.
- Julho para agosto: a receita por item compensou a redução dos itens por pedido.
- Agosto para setembro: a queda do ticket foi causada pela redução da receita por item.
- Novembro para dezembro: o aumento de **R$ 23,32** foi explicado pela contribuição positiva de **R$ 25,34** da receita por item, apesar da contribuição negativa dos itens por pedido.

### 7.2 Conclusão

As maiores oscilações do ticket foram produzidas principalmente pela receita por item, e não pela quantidade de itens por pedido. Isso direciona o aprofundamento para mix, preço, categoria, desconto, campanha e perfil de cliente.

---

## 8. Blocos 04 e 05 — Clientes novos e recorrentes

### 8.1 Definição operacional

Nesta análise, cliente novo significa **primeira compra observada dentro da janela de janeiro a dezembro de 2025**. A base não contém histórico anterior suficiente para confirmar que se trata da primeira compra real do cliente.

Consequentemente:

- todos os clientes de janeiro são classificados como novos;
- parte dos clientes classificados como novos pode ter comprado antes da janela;
- a classificação mede entrada na amostra observada, não aquisição histórica definitiva.

### 8.2 Principais resultados

- Fevereiro ainda apresentou elevada participação de clientes classificados como novos: **69,72% da receita** e **70,23% da margem**.
- Março marcou uma composição próxima do equilíbrio entre novos e recorrentes.
- A partir de maio, os recorrentes passaram a responder por mais de 92% da receita mensal.
- Entre julho e dezembro, os recorrentes representaram aproximadamente 94% a 97% da receita, com exceções apenas marginais.
- A margem percentual de novos e recorrentes foi geralmente próxima, mas alguns grupos mensais tiveram poucos clientes e elevada instabilidade.

### 8.3 Interpretação

Os resultados indicam crescente dependência comercial dos clientes recorrentes ao longo da janela. Entretanto, não é correto interpretar janeiro e fevereiro como prova de forte aquisição sem uma base histórica anterior.

A análise futura deverá incorporar coortes, tempo até recompra e valor acumulado por cliente para distinguir aquisição, retenção e maturação.

---

## 9. Bloco 06 — Desempenho por categoria

### 9.1 Concentração e rentabilidade

A categoria `Sazonal` apresentou:

- receita anual de **R$ 89.223,51**;
- participação de **30,78%** na receita;
- margem de **R$ 51.601,06**;
- participação de **34,12%** na margem;
- margem percentual de **57,83%**;
- **1.357 unidades**, equivalentes a aproximadamente **10,15%** dos itens vendidos.

Essa combinação mostra alto valor econômico por unidade e participação desproporcional na margem.

### 9.2 Dependência do crescimento

A categoria `Sazonal` explicou aproximadamente:

- **69,95%** do crescimento de receita de março para abril;
- **73,10%** do crescimento de receita de novembro para dezembro.

Isso reforça que parte relevante dos picos de abril e dezembro está associada ao mix de produtos classificados nessa categoria.

### 9.3 Ressalva semântica

O nome `Sazonal` não é evidência suficiente de sazonalidade estatística. Alguns produtos dessa categoria aparecem em vários meses. A sazonalidade deverá ser verificada pelo padrão temporal efetivamente observado, pela concentração em períodos e pelo contexto das campanhas e eventos.

### 9.4 Molhos

A categoria Molhos possui apenas um SKU, `Molho Tomate`, com:

- 373 unidades;
- receita de R$ 2.190,88;
- margem percentual aproximada de 55,8%;
- participação de aproximadamente 0,76% na receita anual.

A margem é elevada, mas a participação é pequena. As hipóteses são:

- produto complementar;
- oportunidade de cross-selling;
- baixa exposição;
- demanda naturalmente limitada;
- potencial de escala restrito.

A análise de cesta será necessária para distinguir essas possibilidades.

---

## 10. Bloco 07 — Pareto e papel dos produtos

### 10.1 Produtos de maior destaque

| Produto | Receita | Participação aproximada | Margem percentual |
|---|---:|---:|---:|
| Kit Presente Gourmet | R$ 44.105,84 | 15,21% | 56,92% |
| Ovo Páscoa | R$ 28.119,75 | 9,70% | 58,73% |
| Café Gourmet | R$ 21.114,06 | 7,28% | 45,45% |
| Panetone | R$ 16.997,92 | 5,86% | 58,71% |

Foram necessários 16 dos 36 produtos para atingir **80,61% da receita**. Portanto, não ocorreu uma concentração estrita do tipo 20/80.

### 10.2 Papéis comerciais sugeridos

Produtos de margem elevada e baixa participação podem atuar como candidatos a complemento, cross-selling ou maior exposição:

- Orégano;
- Pimenta;
- Legumes Congelados;
- Molho Tomate;
- Biscoito Recheado;
- Biscoito Integral;
- Chá Premium.

Produtos de menor margem relativa, mas com receita relevante, podem cumprir função de tráfego, recorrência ou entrada na cesta:

- Arroz;
- Café Tradicional;
- Queijo Minas;
- Café Gourmet;
- Água Mineral.

### 10.3 Diretriz de composição de vendas

A decisão comercial não deve ser simplesmente retirar itens de menor margem. O portfólio pode ser estruturado em três funções:

1. produtos de tráfego ou âncora, que atraem demanda e geram recorrência;
2. produtos de margem, que aumentam a rentabilidade da cesta;
3. produtos complementares, que elevam itens por pedido e receita incremental.

A análise de cesta deverá verificar se produtos de menor margem contribuem indiretamente para a receita e a margem de outros itens.

---

## 11. Bloco 08 — Alertas de crescimento e margem

### 11.1 Classificação mensal

- Fevereiro, abril, agosto e dezembro apresentaram crescimento com aumento da margem monetária.
- Março e novembro apresentaram crescimento de receita com pequena redução da margem percentual.
- Maio, junho, julho, setembro e outubro apresentaram queda de receita.

### 11.2 Critério de materialidade

Variações muito pequenas de margem percentual não devem ser tratadas automaticamente como deterioração relevante.

Foi definido como referência analítica:

```text
Variação entre −0,50 e +0,50 ponto percentual:
estabilidade aproximada da margem percentual.
```

Assim, as quedas de março e novembro devem ser interpretadas com cautela, pois são pequenas em termos econômicos.

### 11.3 Ressalva sobre fevereiro

Fevereiro é o segundo mês da amostra e sucede uma base inicial muito reduzida em janeiro. Seu crescimento percentual é matematicamente elevado, mas não deve ser tratado isoladamente como evidência de expansão estrutural.

---

## 12. Bloco 09 — Primeiro e último mês

Entre janeiro e dezembro, foram observadas as seguintes variações:

| Indicador | Janeiro | Dezembro | Variação absoluta |
|---|---:|---:|---:|
| Clientes | 16 | 154 | +138 |
| Pedidos | 22 | 254 | +232 |
| Itens | 95 | 1.256 | +1.161 |
| Receita | R$ 1.743,58 | R$ 31.871,14 | +R$ 30.127,56 |
| Margem | R$ 795,70 | R$ 17.063,40 | +R$ 16.267,70 |

A comparação mostra grande evolução dentro da janela, mas janeiro não representa uma base madura. Portanto, a diferença entre os extremos não deve ser apresentada como taxa anual orgânica sem ressalvas.

Comparações estruturais deverão utilizar:

- médias móveis;
- trimestres;
- períodos equivalentes;
- análise com e sem janeiro e fevereiro;
- análise com e sem a categoria Sazonal.

---

## 13. Notas consolidadas para aprofundamento

### Nota 1 — Campanhas e períodos

Relacionar cada variação mensal com campanhas, eventos externos, descontos, cupons e frete grátis para verificar quais condições estão associadas às mudanças de clientes, frequência, ticket, receita e margem.

### Nota 2 — Receita por item

Investigar se as mudanças da receita por item foram produzidas por produtos de maior valor, categorias diferentes, menor desconto, campanhas direcionadas, mudança do perfil dos clientes ou combinação desses fatores.

### Nota 3 — Coortes

Criar análise de coortes por primeiro mês observado, tempo até recompra, receita acumulada e margem acumulada.

### Nota 4 — Censura à esquerda

Documentar que a ausência de histórico anterior a janeiro impede separar com certeza novos clientes reais de clientes preexistentes que aparecem pela primeira vez na janela.

### Nota 5 — Dependência de Sazonal

Mensurar o desempenho anual e mensal com e sem a categoria `Sazonal` para identificar a força do portfólio recorrente.

### Nota 6 — Molhos e cross-selling

Usar análise de cesta para verificar se Molho Tomate funciona como complemento, se possui baixa exposição ou se apresenta demanda naturalmente limitada.

### Nota 7 — Composição ótima de vendas

Combinar produtos de tráfego, produtos de margem e complementares para elevar receita e margem conjunta, evitando avaliar cada item apenas por sua margem isolada.

### Nota 8 — Materialidade da margem

Adotar faixa de ±0,50 ponto percentual para distinguir oscilação pequena de mudança economicamente relevante, sem impedir análises mais detalhadas quando necessário.

### Nota 9 — Janeiro e fevereiro

Tratar janeiro como início da observação e fevereiro como transição. Realizar análises de sensibilidade excluindo esses meses.

### Nota 10 — Comparações estruturais

Priorizar trimestres, médias móveis, períodos comparáveis e análises com exclusões controladas em vez de depender apenas da comparação primeiro versus último mês.

### Nota 11 — Validação da sazonalidade

Validar a categoria `Sazonal` pela distribuição real das vendas ao longo do tempo. A classificação cadastral, isoladamente, não comprova comportamento sazonal.

---

## 14. Conclusões da AC01

1. O crescimento comercial de 2025 não foi homogêneo e teve motores diferentes em cada transição mensal.
2. Abril foi o mês de melhor desempenho econômico, enquanto maio demonstrou que maior volume não garante maior receita ou rentabilidade.
3. As maiores oscilações do ticket foram explicadas principalmente pela receita por item, evidenciando a importância do mix.
4. Clientes recorrentes passaram a sustentar a maior parte da receita e da margem a partir de maio.
5. A categoria `Sazonal` teve papel relevante nos picos de abril e dezembro, mas sua classificação ainda precisa de validação temporal.
6. O portfólio apresenta concentração relevante, porém não corresponde a um Pareto estrito de 20/80.
7. Produtos de menor margem podem ter valor indireto como itens de tráfego, entrada ou recorrência.
8. Crescimento de receita deve ser avaliado junto com margem monetária, margem percentual e composição do mix.
9. Janeiro e fevereiro exigem cautela por causa do início da janela e da pequena base inicial.
10. Os resultados são diagnósticos e associativos. Campanhas, descontos e frete grátis ainda não podem ser interpretados causalmente sem controles adicionais.

---

## 15. Próximas etapas

1. Relacionar campanhas, descontos, cupons, frete grátis e eventos externos às variações mensais.
2. Executar análise de sensibilidade com e sem janeiro, fevereiro e categoria Sazonal.
3. Construir coortes de primeira compra observada e recompra.
4. Realizar análise de cesta e cross-selling.
5. Avaliar composição comercial entre produtos de tráfego, margem e complemento.
6. Preparar a base para análises de segmentação de clientes.
7. Manter separação explícita entre associação observada e inferência causal.

---

## 16. Status final

```text
AC01 — ORIGEM E QUALIDADE DO CRESCIMENTO: CONCLUÍDA

DIAGNÓSTICO SQL: APROVADO
EXPORTAÇÃO PARQUET: APROVADA
VALIDAÇÃO DE ESTRUTURA E RELEITURA: APROVADA
SINCRONIZAÇÃO COM AZURE: APROVADA
IDEMPOTÊNCIA: APROVADA
DOCUMENTAÇÃO DOS RESULTADOS: CONCLUÍDA
```
