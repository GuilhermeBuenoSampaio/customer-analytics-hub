import json
import sys
import hashlib
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill


PROJECT_ROOT = Path(__file__).resolve().parents[3]

BRONZE_PATH = (
    PROJECT_ROOT
    / "data"
    / "bronze"
    / "food_commerce"
    / "bronze_transactions_v3.parquet"
)

BRONZE_MANIFEST_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "manifests"
    / "bronze_v3"
    / "step_02_materializacao_bronze.json"
)

CONTRACT_PATH = (
    PROJECT_ROOT
    / "configs"
    / "source_contract_v3.json"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "profiling"
    / "bronze_v3"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "step_04_analise_granularidade_chaves.xlsx"
)

DQ_PREFIX = "DQ_"
TECHNICAL_PREFIX = "_"

IDENTIFICADORES_OBRIGATORIOS = [
    "Pedido_ID",
    "Cliente_ID",
    "Id_Item",
]

COLUNAS_DESCRITIVAS_ITEM = [
    "Produto",
    "Categoria_Item",
    "Medida",
]


def calcular_sha256(caminho_arquivo):
    sha256 = hashlib.sha256()

    with caminho_arquivo.open(mode="rb") as arquivo:
        for bloco in iter(
            lambda: arquivo.read(1024 * 1024),
            b"",
        ):
            sha256.update(bloco)

    return sha256.hexdigest().upper()


def calcular_percentual(quantidade, total):
    if total == 0:
        return 0.0

    return round(
        quantidade / total * 100,
        4,
    )


def normalizar_texto_diagnostico(valor):
    if pd.isna(valor):
        return pd.NA

    texto = " ".join(str(valor).strip().casefold().split())
    texto = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )

    return texto


def carregar_entradas():
    caminhos_obrigatorios = [
        BRONZE_PATH,
        BRONZE_MANIFEST_PATH,
        CONTRACT_PATH,
    ]

    ausentes = [
        caminho
        for caminho in caminhos_obrigatorios
        if not caminho.is_file()
    ]

    if ausentes:
        raise FileNotFoundError(
            "Arquivos obrigatórios ausentes:\n"
            + "\n".join(str(caminho) for caminho in ausentes)
        )

    with BRONZE_MANIFEST_PATH.open(
        mode="r",
        encoding="utf-8",
    ) as arquivo:
        manifesto = json.load(arquivo)

    with CONTRACT_PATH.open(
        mode="r",
        encoding="utf-8-sig",
    ) as arquivo:
        contrato = json.load(arquivo)

    if manifesto.get("status") != "success":
        raise ValueError(
            "O manifesto da Bronze não possui status success."
        )

    checksum_encontrado = calcular_sha256(BRONZE_PATH)
    checksum_esperado = manifesto["bronze"]["sha256"]

    if checksum_encontrado != checksum_esperado:
        raise ValueError(
            "O SHA-256 da Bronze difere do manifesto."
        )

    dados = pd.read_parquet(
        BRONZE_PATH,
        engine="pyarrow",
    )

    if len(dados) != manifesto["bronze"]["rows"]:
        raise ValueError(
            "A quantidade de linhas difere do manifesto."
        )

    if len(dados.columns) != manifesto["bronze"]["total_columns"]:
        raise ValueError(
            "A quantidade de colunas difere do manifesto."
        )

    colunas_ausentes = [
        coluna
        for coluna in IDENTIFICADORES_OBRIGATORIOS
        if coluna not in dados.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Identificadores obrigatórios ausentes: "
            + ", ".join(colunas_ausentes)
        )

    if "_source_row_number" not in dados.columns:
        raise ValueError(
            "A coluna técnica _source_row_number está ausente."
        )

    return dados, manifesto, contrato


def classificar_colunas(dados, manifesto):
    colunas_dq = [
        coluna
        for coluna in dados.columns
        if coluna.startswith(DQ_PREFIX)
    ]

    colunas_tecnicas = [
        coluna
        for coluna in dados.columns
        if coluna.startswith(TECHNICAL_PREFIX)
    ]

    colunas_analiticas = [
        coluna
        for coluna in dados.columns
        if coluna not in colunas_dq
        and coluna not in colunas_tecnicas
    ]

    quantidades_esperadas = {
        "analiticas": manifesto["bronze"][
            "analytical_columns"
        ],
        "dq": manifesto["bronze"]["dq_columns"],
        "tecnicas": manifesto["bronze"][
            "technical_columns"
        ],
    }

    quantidades_encontradas = {
        "analiticas": len(colunas_analiticas),
        "dq": len(colunas_dq),
        "tecnicas": len(colunas_tecnicas),
    }

    if quantidades_encontradas != quantidades_esperadas:
        raise ValueError(
            "A classificação das colunas difere do manifesto. "
            f"Esperado: {quantidades_esperadas}. "
            f"Encontrado: {quantidades_encontradas}."
        )

    return {
        "analiticas": colunas_analiticas,
        "dq": colunas_dq,
        "tecnicas": colunas_tecnicas,
    }


def preparar_identificador(serie):
    serie_texto = serie.astype("string")

    return serie_texto.where(
        serie_texto.isna(),
        serie_texto.str.strip(),
    )


def criar_visao_identificadores(dados):
    visao = dados.copy()

    for coluna in IDENTIFICADORES_OBRIGATORIOS:
        visao[coluna] = preparar_identificador(
            visao[coluna]
        )

    return visao


def criar_perfil_identificadores(dados):
    registros = []
    total_linhas = len(dados)

    for coluna in IDENTIFICADORES_OBRIGATORIOS:
        serie_original = dados[coluna].astype("string")
        serie_diagnostica = preparar_identificador(
            dados[coluna]
        )

        mascara_nulos = serie_original.isna()
        mascara_vazios = (
            serie_original.notna()
            & serie_original.str.strip().eq("")
        )
        mascara_espacos = (
            serie_original.notna()
            & serie_original.ne(serie_original.str.strip())
        )

        valores_validos = serie_diagnostica[
            serie_diagnostica.notna()
            & serie_diagnostica.ne("")
        ]

        valores_unicos = int(
            valores_validos.nunique(dropna=True)
        )
        linhas_repetidas = int(
            valores_validos.duplicated(keep=False).sum()
        )
        excedentes = int(
            valores_validos.duplicated(keep="first").sum()
        )

        frequencias = valores_validos.value_counts()

        registros.append(
            {
                "coluna": coluna,
                "total_linhas": total_linhas,
                "nulos": int(mascara_nulos.sum()),
                "vazios_ou_so_espacos": int(
                    mascara_vazios.sum()
                ),
                "espacos_externos": int(
                    mascara_espacos.sum()
                ),
                "valores_validos": len(valores_validos),
                "valores_unicos": valores_unicos,
                "percentual_unicidade": calcular_percentual(
                    valores_unicos,
                    len(valores_validos),
                ),
                "linhas_com_valor_repetido": linhas_repetidas,
                "linhas_excedentes_por_repeticao": excedentes,
                "frequencia_maxima": (
                    int(frequencias.max())
                    if not frequencias.empty
                    else 0
                ),
                "valor_mais_frequente": (
                    str(frequencias.index[0])
                    if not frequencias.empty
                    else None
                ),
            }
        )

    return pd.DataFrame(registros)


def remover_excedentes_exatos(
    dados,
    colunas_analiticas,
):
    mascara_excedente = dados[
        colunas_analiticas
    ].duplicated(keep="first")

    return dados.loc[~mascara_excedente].copy()


def avaliar_chave(
    dados,
    colunas_chave,
    universo,
):
    quadro = dados[colunas_chave].copy()

    for coluna in colunas_chave:
        quadro[coluna] = preparar_identificador(
            quadro[coluna]
        )

    mascara_ausente = quadro.isna().any(axis=1)
    mascara_vazio = quadro.apply(
        lambda serie: serie.astype("string").str.strip().eq("")
    ).any(axis=1)
    mascara_invalida = mascara_ausente | mascara_vazio

    quadro_valido = quadro.loc[~mascara_invalida]

    duplicados_grupo = quadro_valido.duplicated(
        keep=False
    )
    duplicados_excedentes = quadro_valido.duplicated(
        keep="first"
    )

    total_combinacoes = int(
        quadro_valido.drop_duplicates().shape[0]
    )
    total_linhas_validas = len(quadro_valido)

    eh_unica = (
        int(mascara_invalida.sum()) == 0
        and int(duplicados_excedentes.sum()) == 0
    )

    return {
        "universo": universo,
        "colunas_chave": " + ".join(colunas_chave),
        "quantidade_colunas": len(colunas_chave),
        "total_linhas": len(dados),
        "linhas_com_componente_ausente": int(
            mascara_invalida.sum()
        ),
        "combinacoes_distintas": total_combinacoes,
        "percentual_unicidade": calcular_percentual(
            total_combinacoes,
            total_linhas_validas,
        ),
        "linhas_em_grupos_repetidos": int(
            duplicados_grupo.sum()
        ),
        "linhas_excedentes_repetidas": int(
            duplicados_excedentes.sum()
        ),
        "chave_unica_neste_universo": eh_unica,
    }


def testar_chaves_candidatas(
    dados,
    dados_sem_excedentes,
):
    combinacoes = [
        ["Pedido_ID"],
        ["Pedido_ID", "Id_Item"],
        ["Pedido_ID", "Produto"],
        ["Pedido_ID", "Id_Item", "Produto"],
        ["Pedido_ID", "Cliente_ID", "Id_Item"],
    ]

    registros = []

    for colunas_chave in combinacoes:
        colunas_ausentes = [
            coluna
            for coluna in colunas_chave
            if coluna not in dados.columns
        ]

        if colunas_ausentes:
            continue

        registros.append(
            avaliar_chave(
                dados,
                colunas_chave,
                "bronze_integral",
            )
        )
        registros.append(
            avaliar_chave(
                dados_sem_excedentes,
                colunas_chave,
                "visao_sem_excedentes_exatos",
            )
        )

    resultado = pd.DataFrame(registros)

    if resultado.empty:
        return resultado

    status_por_chave = {}

    for nome_chave, grupo in resultado.groupby(
        "colunas_chave",
        sort=False,
    ):
        integral = grupo.loc[
            grupo["universo"].eq("bronze_integral")
        ]
        sem_excedentes = grupo.loc[
            grupo["universo"].eq(
                "visao_sem_excedentes_exatos"
            )
        ]

        unica_integral = bool(
            integral.iloc[0]["chave_unica_neste_universo"]
        )
        unica_sem_excedentes = bool(
            sem_excedentes.iloc[0][
                "chave_unica_neste_universo"
            ]
        )

        if unica_integral:
            status = "chave_candidata_confirmada"
        elif unica_sem_excedentes:
            status = (
                "potencial_apos_investigar_duplicidades_exatas"
            )
        else:
            status = "nao_unica"

        status_por_chave[nome_chave] = status

    resultado["status_interpretativo"] = resultado[
        "colunas_chave"
    ].map(status_por_chave)

    return resultado


def criar_distribuicao_por_pedido(dados):
    visao = criar_visao_identificadores(dados)

    agregacoes = {
        "_source_row_number": [
            ("quantidade_linhas", "size"),
            (
                "primeira_linha_fonte",
                "min",
            ),
            (
                "ultima_linha_fonte",
                "max",
            ),
        ],
        "Cliente_ID": [
            (
                "clientes_distintos",
                lambda serie: serie.nunique(dropna=True),
            )
        ],
        "Id_Item": [
            (
                "itens_distintos",
                lambda serie: serie.nunique(dropna=True),
            )
        ],
    }

    if "Produto" in visao.columns:
        agregacoes["Produto"] = [
            (
                "produtos_distintos",
                lambda serie: serie.nunique(dropna=True),
            )
        ]

    distribuicao = visao.groupby(
        "Pedido_ID",
        dropna=False,
    ).agg(**{
        nome_saida: pd.NamedAgg(
            column=coluna,
            aggfunc=funcao,
        )
        for coluna, definicoes in agregacoes.items()
        for nome_saida, funcao in definicoes
    }).reset_index()

    cliente_representativo = (
        visao.groupby(
            "Pedido_ID",
            dropna=False,
        )["Cliente_ID"]
        .first()
        .rename("Cliente_ID")
        .reset_index()
    )

    distribuicao = distribuicao.merge(
        cliente_representativo,
        on="Pedido_ID",
        how="left",
        validate="one_to_one",
    )

    colunas_inicio = [
        "Pedido_ID",
        "Cliente_ID",
    ]
    demais_colunas = [
        coluna
        for coluna in distribuicao.columns
        if coluna not in colunas_inicio
    ]
    distribuicao = distribuicao[
        colunas_inicio + demais_colunas
    ]

    distribuicao["possui_mais_de_uma_linha"] = (
        distribuicao["quantidade_linhas"] > 1
    )
    distribuicao["conflito_cliente"] = (
        distribuicao["clientes_distintos"] > 1
    )

    return distribuicao.sort_values(
        by=["quantidade_linhas", "Pedido_ID"],
        ascending=[False, True],
    )


def criar_distribuicao_pedidos_cliente(
    distribuicao_pedidos,
):
    base_valida = distribuicao_pedidos.loc[
        ~distribuicao_pedidos["conflito_cliente"]
        & distribuicao_pedidos["Cliente_ID"].notna()
    ].copy()

    distribuicao = (
        base_valida.groupby(
            "Cliente_ID",
            dropna=False,
        )
        .agg(
            quantidade_pedidos=("Pedido_ID", "nunique"),
            quantidade_linhas=("quantidade_linhas", "sum"),
        )
        .reset_index()
        .sort_values(
            by=["quantidade_pedidos", "Cliente_ID"],
            ascending=[False, True],
        )
    )

    distribuicao["possui_recompra_observada"] = (
        distribuicao["quantidade_pedidos"] > 1
    )

    return distribuicao


def criar_resumo_pedidos_cliente(
    distribuicao_clientes,
):
    contagens = distribuicao_clientes[
        "quantidade_pedidos"
    ]
    total_clientes = len(distribuicao_clientes)
    clientes_um_pedido = int(contagens.eq(1).sum())
    clientes_recompra = int(contagens.gt(1).sum())

    return pd.DataFrame(
        [
            {
                "metrica": "clientes_distintos",
                "valor": total_clientes,
                "interpretacao": (
                    "Clientes associados a pedidos sem conflito "
                    "Pedido_ID x Cliente_ID."
                ),
            },
            {
                "metrica": "clientes_com_um_pedido",
                "valor": clientes_um_pedido,
                "interpretacao": (
                    "Clientes sem recompra observada na fonte."
                ),
            },
            {
                "metrica": "clientes_com_recompra_observada",
                "valor": clientes_recompra,
                "interpretacao": (
                    "Clientes associados a dois ou mais pedidos "
                    "distintos."
                ),
            },
            {
                "metrica": "percentual_clientes_com_recompra",
                "valor": calcular_percentual(
                    clientes_recompra,
                    total_clientes,
                ),
                "interpretacao": (
                    "Indicador estrutural; ainda não representa "
                    "taxa de retenção."
                ),
            },
            {
                "metrica": "pedidos_por_cliente_media",
                "valor": round(float(contagens.mean()), 4),
                "interpretacao": (
                    "Média de pedidos distintos por cliente."
                ),
            },
            {
                "metrica": "pedidos_por_cliente_mediana",
                "valor": float(contagens.median()),
                "interpretacao": (
                    "Mediana de pedidos distintos por cliente."
                ),
            },
            {
                "metrica": "pedidos_por_cliente_p95",
                "valor": float(contagens.quantile(0.95)),
                "interpretacao": (
                    "Percentil 95 dos pedidos distintos por cliente."
                ),
            },
            {
                "metrica": "pedidos_por_cliente_maximo",
                "valor": int(contagens.max()),
                "interpretacao": (
                    "Maior quantidade de pedidos associada a um cliente."
                ),
            },
        ]
    )


def resumir_combinacoes_pedido_item(
    dados,
    prefixo,
):
    visao = criar_visao_identificadores(dados)

    colunas_diagnosticas = [
        coluna
        for coluna in [
            "Produto",
            "Categoria_Item",
            "Medida",
            "Quantidade",
            "Custo_Unitario",
            "Preco_Unitario_Lista",
            "Valor_Compra",
        ]
        if coluna in visao.columns
    ]

    grupos = visao.groupby(
        ["Pedido_ID", "Id_Item"],
        dropna=False,
    )

    resumo = grupos.agg(
        **{
            f"linhas_{prefixo}": pd.NamedAgg(
                column="_source_row_number",
                aggfunc="size",
            ),
            f"linhas_fonte_{prefixo}": pd.NamedAgg(
                column="_source_row_number",
                aggfunc=lambda serie: " | ".join(
                    str(valor)
                    for valor in sorted(serie.tolist())
                ),
            ),
            **{
                f"{coluna.lower()}_distintos_{prefixo}": (
                    pd.NamedAgg(
                        column=coluna,
                        aggfunc=lambda serie: serie.nunique(
                            dropna=True
                        ),
                    )
                )
                for coluna in colunas_diagnosticas
            },
        }
    ).reset_index()

    return resumo


def analisar_repeticoes_pedido_item(
    dados,
    dados_sem_excedentes,
):
    integral = resumir_combinacoes_pedido_item(
        dados,
        "bronze",
    )
    sem_excedentes = resumir_combinacoes_pedido_item(
        dados_sem_excedentes,
        "apos_dedup_diagnostica",
    )

    resultado = integral.merge(
        sem_excedentes,
        on=["Pedido_ID", "Id_Item"],
        how="outer",
        validate="one_to_one",
    )

    resultado[
        "excedentes_exatos_removidos_diagnosticamente"
    ] = (
        resultado["linhas_bronze"]
        - resultado["linhas_apos_dedup_diagnostica"]
    )

    resultado[
        "permanece_repetida_apos_dedup_diagnostica"
    ] = resultado[
        "linhas_apos_dedup_diagnostica"
    ].gt(1)

    repeticoes = resultado.loc[
        resultado[
            "permanece_repetida_apos_dedup_diagnostica"
        ]
    ].copy()

    colunas_variacao = [
        coluna
        for coluna in repeticoes.columns
        if coluna.endswith("_distintos_apos_dedup_diagnostica")
    ]

    repeticoes["possui_variacao_entre_linhas"] = (
        repeticoes[colunas_variacao].gt(1).any(axis=1)
        if colunas_variacao
        else False
    )

    repeticoes["classificacao_preliminar"] = repeticoes[
        "possui_variacao_entre_linhas"
    ].map(
        {
            True: "mesmo_item_com_atributos_divergentes",
            False: "repeticao_sem_diferenca_nos_campos_testados",
        }
    )

    repeticoes = repeticoes.sort_values(
        by=[
            "linhas_apos_dedup_diagnostica",
            "Pedido_ID",
            "Id_Item",
        ],
        ascending=[False, True, True],
    )

    total_combinacoes = len(resultado)
    combinacoes_repetidas = len(repeticoes)
    excedentes_restantes = int(
        (
            repeticoes["linhas_apos_dedup_diagnostica"]
            - 1
        ).sum()
    )

    resumo = pd.DataFrame(
        [
            {
                "metrica": "combinacoes_pedido_item_distintas",
                "valor": total_combinacoes,
                "interpretacao": (
                    "Quantidade de combinações distintas de "
                    "Pedido_ID + Id_Item."
                ),
            },
            {
                "metrica": (
                    "combinacoes_repetidas_apos_dedup_diagnostica"
                ),
                "valor": combinacoes_repetidas,
                "interpretacao": (
                    "Combinações que continuam em mais de uma "
                    "linha após desconsiderar excedentes exatos."
                ),
            },
            {
                "metrica": "linhas_excedentes_restantes",
                "valor": excedentes_restantes,
                "interpretacao": (
                    "Ocorrências além da primeira para a mesma "
                    "combinação Pedido_ID + Id_Item."
                ),
            },
            {
                "metrica": "repeticoes_com_atributos_divergentes",
                "valor": int(
                    repeticoes[
                        "possui_variacao_entre_linhas"
                    ].sum()
                ),
                "interpretacao": (
                    "Combinações repetidas com divergência em pelo "
                    "menos um campo de item testado."
                ),
            },
            {
                "metrica": "repeticoes_sem_variacao_detectada",
                "valor": int(
                    (~repeticoes[
                        "possui_variacao_entre_linhas"
                    ]).sum()
                ),
                "interpretacao": (
                    "Repetições que exigem procurar outra coluna "
                    "explicativa ou ausência de chave de linha."
                ),
            },
        ]
    )

    return resumo, repeticoes


def analisar_casos_residuais_diferencas(
    dados_sem_excedentes,
    repeticoes_pedido_item,
    colunas_analiticas,
):
    casos = repeticoes_pedido_item.loc[
        ~repeticoes_pedido_item[
            "possui_variacao_entre_linhas"
        ],
        ["Pedido_ID", "Id_Item"],
    ].drop_duplicates()

    visao = criar_visao_identificadores(
        dados_sem_excedentes
    )
    registros = []

    for _, caso in casos.iterrows():
        pedido_id = caso["Pedido_ID"]
        id_item = caso["Id_Item"]

        linhas = visao.loc[
            visao["Pedido_ID"].eq(pedido_id)
            & visao["Id_Item"].eq(id_item),
            ["_source_row_number"] + colunas_analiticas,
        ].copy()

        for coluna in colunas_analiticas:
            if coluna in {"Pedido_ID", "Id_Item"}:
                continue

            valores_com_nulo = linhas[coluna].astype(
                "string"
            ).fillna("<NULO>")
            valores_distintos = valores_com_nulo.nunique(
                dropna=False
            )

            if valores_distintos <= 1:
                continue

            pares = " | ".join(
                f"{linha['_source_row_number']}="
                f"{('<NULO>' if pd.isna(linha[coluna]) else linha[coluna])}"
                for _, linha in linhas.iterrows()
            )

            registros.append(
                {
                    "Pedido_ID": pedido_id,
                    "Id_Item": id_item,
                    "quantidade_linhas": len(linhas),
                    "linhas_fonte": " | ".join(
                        str(valor)
                        for valor in sorted(
                            linhas[
                                "_source_row_number"
                            ].tolist()
                        )
                    ),
                    "coluna_diferente": coluna,
                    "valores_distintos": int(
                        valores_distintos
                    ),
                    "valores_por_linha": pares,
                    "interpretacao": (
                        "A repetição não é exata; a coluna "
                        "diferencia as ocorrências."
                    ),
                }
            )

    colunas_saida = [
        "Pedido_ID",
        "Id_Item",
        "quantidade_linhas",
        "linhas_fonte",
        "coluna_diferente",
        "valores_distintos",
        "valores_por_linha",
        "interpretacao",
    ]

    detalhes = pd.DataFrame(
        registros,
        columns=colunas_saida,
    )

    resumo = pd.DataFrame(
        [
            {
                "metrica": "casos_residuais_analisados",
                "valor": len(casos),
                "interpretacao": (
                    "Combinações repetidas sem divergência nos "
                    "campos de item inicialmente testados."
                ),
            },
            {
                "metrica": "casos_com_diferenca_encontrada",
                "valor": int(
                    detalhes[
                        ["Pedido_ID", "Id_Item"]
                    ].drop_duplicates().shape[0]
                ) if not detalhes.empty else 0,
                "interpretacao": (
                    "Casos diferenciados por alguma das demais "
                    "colunas analíticas."
                ),
            },
            {
                "metrica": "colunas_divergentes_encontradas",
                "valor": int(
                    detalhes["coluna_diferente"].nunique()
                ) if not detalhes.empty else 0,
                "interpretacao": (
                    "Quantidade de campos que explicam pelo menos "
                    "uma repetição residual."
                ),
            },
        ]
    )

    return resumo, detalhes


def analisar_impacto_duplicidades(
    dados,
    dados_sem_excedentes,
    colunas_analiticas,
):
    mascara_excedente = dados[
        colunas_analiticas
    ].duplicated(keep="first")

    excedentes = dados.loc[mascara_excedente].copy()

    pedidos_afetados = int(
        excedentes["Pedido_ID"].nunique(dropna=True)
    )
    clientes_afetados = int(
        excedentes["Cliente_ID"].nunique(dropna=True)
    )
    itens_afetados = int(
        excedentes["Id_Item"].nunique(dropna=True)
    )

    metricas = [
        (
            "linhas",
            len(dados),
            len(dados_sem_excedentes),
        ),
        (
            "pedidos_distintos",
            int(dados["Pedido_ID"].nunique(dropna=True)),
            int(
                dados_sem_excedentes["Pedido_ID"].nunique(
                    dropna=True
                )
            ),
        ),
        (
            "clientes_distintos",
            int(dados["Cliente_ID"].nunique(dropna=True)),
            int(
                dados_sem_excedentes["Cliente_ID"].nunique(
                    dropna=True
                )
            ),
        ),
        (
            "itens_distintos",
            int(dados["Id_Item"].nunique(dropna=True)),
            int(
                dados_sem_excedentes["Id_Item"].nunique(
                    dropna=True
                )
            ),
        ),
    ]

    registros = []

    for metrica, antes, depois in metricas:
        diferenca = antes - depois
        registros.append(
            {
                "metrica": metrica,
                "antes": antes,
                "depois_visao_diagnostica": depois,
                "diferenca": diferenca,
                "percentual_reducao": calcular_percentual(
                    diferenca,
                    antes,
                ),
                "bronze_modificada": False,
            }
        )

    registros.extend(
        [
            {
                "metrica": "pedidos_afetados",
                "antes": pedidos_afetados,
                "depois_visao_diagnostica": pedidos_afetados,
                "diferenca": 0,
                "percentual_reducao": 0.0,
                "bronze_modificada": False,
            },
            {
                "metrica": "clientes_afetados",
                "antes": clientes_afetados,
                "depois_visao_diagnostica": clientes_afetados,
                "diferenca": 0,
                "percentual_reducao": 0.0,
                "bronze_modificada": False,
            },
            {
                "metrica": "itens_afetados",
                "antes": itens_afetados,
                "depois_visao_diagnostica": itens_afetados,
                "diferenca": 0,
                "percentual_reducao": 0.0,
                "bronze_modificada": False,
            },
        ]
    )

    impacto = pd.DataFrame(registros)

    concentracao = (
        excedentes.groupby(
            ["Pedido_ID", "Cliente_ID", "Id_Item"],
            dropna=False,
        )
        .agg(
            linhas_excedentes=("_source_row_number", "size"),
            linhas_fonte=(
                "_source_row_number",
                lambda serie: " | ".join(
                    str(valor)
                    for valor in sorted(serie.tolist())
                ),
            ),
        )
        .reset_index()
        .sort_values(
            by=["linhas_excedentes", "Pedido_ID", "Id_Item"],
            ascending=[False, True, True],
        )
    )

    return impacto, concentracao


def criar_resumo_granularidade(
    dados,
    distribuicao_pedidos,
):
    contagens = distribuicao_pedidos[
        "quantidade_linhas"
    ]

    pedidos_uma_linha = int(contagens.eq(1).sum())
    pedidos_varias_linhas = int(contagens.gt(1).sum())

    resumo = [
        {
            "metrica": "total_linhas_bronze",
            "valor": len(dados),
            "interpretacao": (
                "Quantidade de registros observados na Bronze."
            ),
        },
        {
            "metrica": "pedidos_distintos",
            "valor": len(distribuicao_pedidos),
            "interpretacao": (
                "Cardinalidade de Pedido_ID após remoção "
                "diagnóstica de espaços externos."
            ),
        },
        {
            "metrica": "pedidos_com_uma_linha",
            "valor": pedidos_uma_linha,
            "interpretacao": (
                "Pedidos representados por apenas uma linha."
            ),
        },
        {
            "metrica": "pedidos_com_varias_linhas",
            "valor": pedidos_varias_linhas,
            "interpretacao": (
                "Pedidos que exigem investigação da "
                "granularidade."
            ),
        },
        {
            "metrica": "percentual_pedidos_varias_linhas",
            "valor": calcular_percentual(
                pedidos_varias_linhas,
                len(distribuicao_pedidos),
            ),
            "interpretacao": (
                "Percentual dos pedidos presentes em mais "
                "de uma linha."
            ),
        },
        {
            "metrica": "linhas_por_pedido_media",
            "valor": round(float(contagens.mean()), 4),
            "interpretacao": (
                "Média descritiva; não define a granularidade."
            ),
        },
        {
            "metrica": "linhas_por_pedido_mediana",
            "valor": float(contagens.median()),
            "interpretacao": (
                "Quantidade mediana de linhas por pedido."
            ),
        },
        {
            "metrica": "linhas_por_pedido_p95",
            "valor": float(contagens.quantile(0.95)),
            "interpretacao": (
                "Percentil 95 da quantidade de linhas por pedido."
            ),
        },
        {
            "metrica": "linhas_por_pedido_maximo",
            "valor": int(contagens.max()),
            "interpretacao": (
                "Maior quantidade de linhas associadas a um pedido."
            ),
        },
        {
            "metrica": "pedidos_com_multiplos_clientes",
            "valor": int(
                distribuicao_pedidos[
                    "conflito_cliente"
                ].sum()
            ),
            "interpretacao": (
                "Esperado: zero. Valores positivos indicam "
                "conflito estrutural."
            ),
        },
    ]

    return pd.DataFrame(resumo)


def criar_frequencia_linhas_por_pedido(
    distribuicao_pedidos,
):
    frequencia = (
        distribuicao_pedidos["quantidade_linhas"]
        .value_counts()
        .rename_axis("quantidade_linhas_no_pedido")
        .reset_index(name="quantidade_pedidos")
        .sort_values("quantidade_linhas_no_pedido")
    )

    frequencia["percentual_pedidos"] = frequencia[
        "quantidade_pedidos"
    ].apply(
        lambda quantidade: calcular_percentual(
            quantidade,
            len(distribuicao_pedidos),
        )
    )

    return frequencia


def analisar_variacao_dentro_pedido(
    dados,
    colunas_analiticas,
):
    visao = dados.copy()
    visao["Pedido_ID"] = preparar_identificador(
        visao["Pedido_ID"]
    )

    total_pedidos = int(
        visao["Pedido_ID"].nunique(dropna=True)
    )
    registros = []

    for coluna in colunas_analiticas:
        if coluna == "Pedido_ID":
            continue

        contagem_distintos = visao.groupby(
            "Pedido_ID",
            dropna=False,
        )[coluna].nunique(dropna=True)

        pedidos_com_variacao = int(
            contagem_distintos.gt(1).sum()
        )
        pedidos_todos_nulos = int(
            contagem_distintos.eq(0).sum()
        )

        if pedidos_com_variacao == 0:
            comportamento = "constante_dentro_do_pedido"
        else:
            comportamento = "varia_dentro_do_pedido"

        registros.append(
            {
                "coluna": coluna,
                "total_pedidos": total_pedidos,
                "pedidos_com_mais_de_um_valor": (
                    pedidos_com_variacao
                ),
                "percentual_pedidos_com_variacao": (
                    calcular_percentual(
                        pedidos_com_variacao,
                        total_pedidos,
                    )
                ),
                "pedidos_sem_valor_informado": (
                    pedidos_todos_nulos
                ),
                "comportamento_observado": comportamento,
                "observacao": (
                    "Resultado descritivo. Constância não prova "
                    "que a coluna pertence ao nível do pedido."
                ),
            }
        )

    return pd.DataFrame(registros).sort_values(
        by=[
            "pedidos_com_mais_de_um_valor",
            "coluna",
        ],
        ascending=[False, True],
    )


def analisar_consistencia_itens(dados):
    visao = criar_visao_identificadores(dados)

    colunas_disponiveis = [
        coluna
        for coluna in COLUNAS_DESCRITIVAS_ITEM
        if coluna in visao.columns
    ]

    agregacoes = {
        "_source_row_number": [
            ("quantidade_linhas", "size"),
            ("primeira_linha_fonte", "min"),
            ("ultima_linha_fonte", "max"),
        ]
    }

    for coluna in colunas_disponiveis:
        agregacoes[coluna] = [
            (
                f"{coluna.lower()}_distintos",
                lambda serie: serie.nunique(dropna=True),
            ),
            (
                f"{coluna.lower()}_nulos",
                lambda serie: int(serie.isna().sum()),
            ),
        ]

    resultado = visao.groupby(
        "Id_Item",
        dropna=False,
    ).agg(**{
        nome_saida: pd.NamedAgg(
            column=coluna,
            aggfunc=funcao,
        )
        for coluna, definicoes in agregacoes.items()
        for nome_saida, funcao in definicoes
    }).reset_index()

    colunas_distintos = [
        coluna
        for coluna in resultado.columns
        if coluna.endswith("_distintos")
    ]

    if colunas_distintos:
        resultado["possui_conflito_descritivo"] = resultado[
            colunas_distintos
        ].gt(1).any(axis=1)
    else:
        resultado["possui_conflito_descritivo"] = False

    return resultado.sort_values(
        by=["possui_conflito_descritivo", "quantidade_linhas"],
        ascending=[False, False],
    )


def criar_detalhes_mapeamento_itens(dados):
    visao = criar_visao_identificadores(dados)

    colunas_mapeamento = [
        "Id_Item",
        "Produto",
        "Categoria_Item",
        "Medida",
    ]

    resultado = (
        visao.groupby(
            colunas_mapeamento,
            dropna=False,
        )
        .agg(
            quantidade_ocorrencias=(
                "_source_row_number",
                "size",
            ),
            primeira_linha_fonte=(
                "_source_row_number",
                "min",
            ),
            ultima_linha_fonte=(
                "_source_row_number",
                "max",
            ),
            linhas_fonte=(
                "_source_row_number",
                lambda serie: " | ".join(
                    str(valor)
                    for valor in sorted(serie.tolist())
                ),
            ),
        )
        .reset_index()
        .sort_values(
            by=[
                "Id_Item",
                "quantidade_ocorrencias",
                "Produto",
                "Categoria_Item",
            ],
            ascending=[True, False, True, True],
        )
    )

    resultado["categoria_item_ausente"] = resultado[
        "Categoria_Item"
    ].isna()

    return resultado


def formatar_frequencias(serie):
    serie_texto = serie.astype("string").fillna("<NULO>")
    frequencias = serie_texto.value_counts(dropna=False)

    return " | ".join(
        f"{valor}: {quantidade}"
        for valor, quantidade in frequencias.items()
    )


def obter_moda_segura(serie):
    valores = serie.dropna()

    if valores.empty:
        return None, 0

    frequencias = valores.value_counts(dropna=True)

    return frequencias.index[0], int(frequencias.iloc[0])


def criar_mapa_canonico_candidato(dados):
    visao = criar_visao_identificadores(dados)
    registros = []

    for id_item, grupo in visao.groupby(
        "Id_Item",
        dropna=False,
        sort=True,
    ):
        produto_candidato, produto_ocorrencias = (
            obter_moda_segura(grupo["Produto"])
        )
        categoria_candidata, categoria_ocorrencias = (
            obter_moda_segura(grupo["Categoria_Item"])
        )
        medida_candidata, medida_ocorrencias = (
            obter_moda_segura(grupo["Medida"])
        )

        total = len(grupo)
        categorias_informadas = int(
            grupo["Categoria_Item"].notna().sum()
        )

        produtos_normalizados = grupo["Produto"].map(
            normalizar_texto_diagnostico
        )
        categorias_normalizadas = grupo[
            "Categoria_Item"
        ].map(normalizar_texto_diagnostico)

        produtos_distintos_raw = int(
            grupo["Produto"].nunique(dropna=True)
        )
        produtos_distintos_normalizados = int(
            produtos_normalizados.nunique(dropna=True)
        )
        categorias_distintas_raw = int(
            grupo["Categoria_Item"].nunique(dropna=True)
        )
        categorias_distintas_normalizadas = int(
            categorias_normalizadas.nunique(dropna=True)
        )

        produto_legado = grupo["Produto"].astype(
            "string"
        ).str.contains(
            "produto legado descontinuado",
            case=False,
            na=False,
        )

        problemas = []

        if produtos_distintos_normalizados > 1:
            problemas.append("conflito_produto")

        if categorias_distintas_normalizadas > 1:
            problemas.append("conflito_semantico_categoria")
        elif categorias_distintas_raw > 1:
            problemas.append("variacao_textual_categoria")

        if grupo["Categoria_Item"].isna().any():
            problemas.append("categoria_ausente")

        if produto_legado.any():
            problemas.append("produto_legado_detectado")

        if not problemas:
            problemas.append("sem_conflito_detectado")

        registros.append(
            {
                "Id_Item": id_item,
                "total_ocorrencias": total,
                "produto_canonico_candidato": produto_candidato,
                "produto_ocorrencias_canonicas": (
                    produto_ocorrencias
                ),
                "produto_percentual_consistencia": (
                    calcular_percentual(
                        produto_ocorrencias,
                        total,
                    )
                ),
                "produto_valores_e_frequencias": (
                    formatar_frequencias(grupo["Produto"])
                ),
                "produto_distintos_brutos": produtos_distintos_raw,
                "produto_distintos_normalizados": (
                    produtos_distintos_normalizados
                ),
                "categoria_canonica_candidata": (
                    categoria_candidata
                ),
                "categoria_ocorrencias_canonicas": (
                    categoria_ocorrencias
                ),
                "categoria_percentual_consistencia": (
                    calcular_percentual(
                        categoria_ocorrencias,
                        categorias_informadas,
                    )
                ),
                "categoria_nulos": int(
                    grupo["Categoria_Item"].isna().sum()
                ),
                "categoria_valores_e_frequencias": (
                    formatar_frequencias(
                        grupo["Categoria_Item"]
                    )
                ),
                "categoria_distintas_brutas": (
                    categorias_distintas_raw
                ),
                "categoria_distintas_normalizadas": (
                    categorias_distintas_normalizadas
                ),
                "medida_canonica_candidata": medida_candidata,
                "medida_percentual_consistencia": (
                    calcular_percentual(
                        medida_ocorrencias,
                        total,
                    )
                ),
                "possui_produto_legado": bool(
                    produto_legado.any()
                ),
                "problemas_detectados": " | ".join(problemas),
                "decisao_silver": "pendente_validacao_analitica",
            }
        )

    return pd.DataFrame(registros).sort_values(
        by=["problemas_detectados", "Id_Item"],
        ascending=[True, True],
    )


def analisar_duplicidades_exatas(
    dados,
    colunas_analiticas,
):
    quadro_analitico = dados[colunas_analiticas]

    mascara_grupo = quadro_analitico.duplicated(
        keep=False
    )
    mascara_excedente = quadro_analitico.duplicated(
        keep="first"
    )

    detalhes = dados.loc[
        mascara_grupo,
        ["_source_row_number"] + colunas_analiticas,
    ].copy()

    if detalhes.empty:
        detalhes.insert(1, "_duplicate_group_id", [])
        detalhes.insert(2, "_duplicate_group_size", [])
        detalhes.insert(3, "_linhas_fonte_do_grupo", [])
    else:
        hashes = pd.util.hash_pandas_object(
            detalhes[colunas_analiticas],
            index=False,
        )

        detalhes.insert(
            1,
            "_duplicate_group_id",
            pd.factorize(hashes)[0] + 1,
        )
        detalhes.insert(
            2,
            "_duplicate_group_size",
            detalhes.groupby(
                "_duplicate_group_id"
            )["_duplicate_group_id"].transform("size"),
        )

        linhas_por_grupo = detalhes.groupby(
            "_duplicate_group_id"
        )["_source_row_number"].transform(
            lambda serie: " | ".join(
                str(valor)
                for valor in sorted(serie.tolist())
            )
        )

        detalhes.insert(
            3,
            "_linhas_fonte_do_grupo",
            linhas_por_grupo,
        )

        detalhes = detalhes.sort_values(
            by=[
                "_duplicate_group_id",
                "_source_row_number",
            ]
        )

    grupos = (
        detalhes.groupby(
            "_duplicate_group_id",
            as_index=False,
        )
        .agg(
            tamanho_grupo=(
                "_duplicate_group_size",
                "first",
            ),
            Pedido_ID=("Pedido_ID", "first"),
            Cliente_ID=("Cliente_ID", "first"),
            Id_Item=("Id_Item", "first"),
            linhas_fonte=(
                "_linhas_fonte_do_grupo",
                "first",
            ),
        )
        if not detalhes.empty
        else pd.DataFrame(
            columns=[
                "_duplicate_group_id",
                "tamanho_grupo",
                "Pedido_ID",
                "Cliente_ID",
                "Id_Item",
                "linhas_fonte",
            ]
        )
    )

    if not grupos.empty:
        grupos["classificacao_atual"] = (
            "duplicidade_exata_confirmada_nas_colunas_analiticas"
        )
        grupos["decisao_silver"] = (
            "pendente_ate_avaliacao_de_impacto"
        )

    resumo = pd.DataFrame(
        [
            {
                "criterio": (
                    "Duplicidade exata nas colunas analíticas"
                ),
                "total_linhas": len(dados),
                "linhas_em_grupos_duplicados": int(
                    mascara_grupo.sum()
                ),
                "linhas_excedentes_duplicadas": int(
                    mascara_excedente.sum()
                ),
                "grupos_duplicados": len(grupos),
                "percentual_excedente": calcular_percentual(
                    int(mascara_excedente.sum()),
                    len(dados),
                ),
                "bronze_modificada": False,
                "decisao_de_exclusao": "não_realizada",
            }
        ]
    )

    return resumo, grupos, detalhes


def criar_conflitos_pedido(
    distribuicao_pedidos,
):
    return distribuicao_pedidos.loc[
        distribuicao_pedidos["conflito_cliente"]
    ].copy()


def inferir_resultado_preliminar(
    chaves_candidatas,
    resumo_granularidade,
):
    status = {
        linha["colunas_chave"]: linha[
            "status_interpretativo"
        ]
        for _, linha in chaves_candidatas.loc[
            chaves_candidatas["universo"].eq(
                "bronze_integral"
            )
        ].iterrows()
    }

    pedidos_multiplos = int(
        resumo_granularidade.loc[
            resumo_granularidade["metrica"].eq(
                "pedidos_com_varias_linhas"
            ),
            "valor",
        ].iloc[0]
    )

    if status.get("Pedido_ID") == "chave_candidata_confirmada":
        hipotese = "uma_linha_por_pedido"
        conclusao = "indicio_forte"
    elif status.get("Pedido_ID + Id_Item") in {
        "chave_candidata_confirmada",
        "potencial_apos_investigar_duplicidades_exatas",
    }:
        hipotese = "uma_linha_por_item_do_pedido"
        conclusao = "indicio_forte"
    elif status.get("Pedido_ID + Id_Item + Produto") in {
        "chave_candidata_confirmada",
        "potencial_apos_investigar_duplicidades_exatas",
    }:
        hipotese = "uma_linha_por_combinacao_pedido_item_produto"
        conclusao = "indicio_moderado"
    else:
        hipotese = "granularidade_nao_confirmada"
        conclusao = "requer_investigacao_adicional"

    return pd.DataFrame(
        [
            {
                "questao": (
                    "O que cada linha parece representar?"
                ),
                "resultado_preliminar": hipotese,
                "nivel_conclusao": conclusao,
                "pedidos_com_varias_linhas": pedidos_multiplos,
                "ressalva": (
                    "A inferência usa unicidade e repetição. "
                    "Ela deve ser confirmada pela leitura das "
                    "colunas que variam dentro do pedido e pela "
                    "análise das duplicidades exatas."
                ),
                "decisao_silver": "não_realizada",
            }
        ]
    )


def criar_colunas_excluidas(grupos_colunas):
    registros = []

    for coluna in grupos_colunas["dq"]:
        registros.append(
            {
                "coluna": coluna,
                "classificacao": "ground_truth_dq",
                "participou_da_descoberta": False,
                "motivo_exclusao": (
                    "Preservada para validação final das regras, "
                    "evitando vazamento da resposta."
                ),
            }
        )

    for coluna in grupos_colunas["tecnicas"]:
        registros.append(
            {
                "coluna": coluna,
                "classificacao": "metadado_tecnico",
                "participou_da_descoberta": False,
                "motivo_exclusao": (
                    "Usada somente para rastreabilidade e "
                    "localização dos registros na fonte."
                ),
            }
        )

    return pd.DataFrame(registros)


def criar_resumo_execucao(
    dados,
    manifesto,
    grupos_colunas,
    resumo_duplicidades,
    conflitos_pedido,
    resumo_repeticoes_pedido_item,
    resumo_clientes,
):
    return pd.DataFrame(
        [
            {
                "executado_em_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "etapa": "04_analise_granularidade_chaves",
                "arquivo_bronze": BRONZE_PATH.name,
                "sha256_bronze": manifesto["bronze"][
                    "sha256"
                ],
                "total_linhas": len(dados),
                "total_colunas": len(dados.columns),
                "colunas_analiticas_analisadas": len(
                    grupos_colunas["analiticas"]
                ),
                "colunas_dq_isoladas": len(
                    grupos_colunas["dq"]
                ),
                "colunas_tecnicas": len(
                    grupos_colunas["tecnicas"]
                ),
                "pedidos_distintos": int(
                    dados["Pedido_ID"].nunique(dropna=True)
                ),
                "conflitos_pedido_cliente": len(
                    conflitos_pedido
                ),
                "linhas_excedentes_duplicadas": int(
                    resumo_duplicidades.iloc[0][
                        "linhas_excedentes_duplicadas"
                    ]
                ),
                "excedentes_pedido_item_apos_dedup": int(
                    resumo_repeticoes_pedido_item.loc[
                        resumo_repeticoes_pedido_item[
                            "metrica"
                        ].eq("linhas_excedentes_restantes"),
                        "valor",
                    ].iloc[0]
                ),
                "clientes_com_recompra_observada": int(
                    resumo_clientes.loc[
                        resumo_clientes["metrica"].eq(
                            "clientes_com_recompra_observada"
                        ),
                        "valor",
                    ].iloc[0]
                ),
                "dados_modificados": False,
                "dq_usado_na_descoberta": False,
                "status": "success",
            }
        ]
    )


def ajustar_planilhas(writer):
    cor_cabecalho = PatternFill(
        fill_type="solid",
        fgColor="1F4E78",
    )
    fonte_cabecalho = Font(
        color="FFFFFF",
        bold=True,
    )

    for planilha in writer.book.worksheets:
        planilha.freeze_panes = "A2"
        planilha.auto_filter.ref = planilha.dimensions

        for celula in planilha[1]:
            celula.fill = cor_cabecalho
            celula.font = fonte_cabecalho
            celula.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True,
            )

        for coluna_celulas in planilha.columns:
            maior_comprimento = max(
                len(str(celula.value))
                if celula.value is not None
                else 0
                for celula in coluna_celulas
            )

            largura = min(
                maior_comprimento + 2,
                60,
            )

            letra_coluna = coluna_celulas[0].column_letter
            planilha.column_dimensions[
                letra_coluna
            ].width = largura


def salvar_relatorio(
    resumo_execucao,
    resultado_preliminar,
    resumo_granularidade,
    perfil_identificadores,
    chaves_candidatas,
    frequencia_linhas_pedido,
    distribuicao_pedidos,
    resumo_clientes,
    distribuicao_clientes,
    conflitos_pedido,
    resumo_repeticoes_pedido_item,
    repeticoes_pedido_item,
    resumo_casos_residuais,
    casos_residuais_diferencas,
    variacao_por_pedido,
    consistencia_itens,
    detalhes_mapeamento_itens,
    mapa_canonico_candidato,
    impacto_duplicidades,
    concentracao_duplicidades,
    resumo_duplicidades,
    grupos_duplicados,
    detalhes_duplicados,
    colunas_excluidas,
):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho_temporario = OUTPUT_PATH.with_suffix(
        ".tmp.xlsx"
    )

    planilhas = [
        ("resumo_execucao", resumo_execucao),
        ("resultado_preliminar", resultado_preliminar),
        ("granularidade_resumo", resumo_granularidade),
        ("perfil_identificadores", perfil_identificadores),
        ("chaves_candidatas", chaves_candidatas),
        ("freq_linhas_pedido", frequencia_linhas_pedido),
        ("distribuicao_pedidos", distribuicao_pedidos),
        ("clientes_resumo", resumo_clientes),
        ("pedidos_por_cliente", distribuicao_clientes),
        ("conflitos_pedido_cliente", conflitos_pedido),
        (
            "pedido_item_rep_resumo",
            resumo_repeticoes_pedido_item,
        ),
        ("pedido_item_repeticoes", repeticoes_pedido_item),
        ("casos_residuais_resumo", resumo_casos_residuais),
        ("casos_residuais_diferencas", casos_residuais_diferencas),
        ("variacao_por_pedido", variacao_por_pedido),
        ("consistencia_itens", consistencia_itens),
        ("item_mapeamento_detalhes", detalhes_mapeamento_itens),
        ("item_mapa_canonico", mapa_canonico_candidato),
        ("duplicidade_impacto", impacto_duplicidades),
        ("duplicidade_concentracao", concentracao_duplicidades),
        ("duplicidade_resumo", resumo_duplicidades),
        ("duplicidade_grupos", grupos_duplicados),
        ("duplicidade_detalhes", detalhes_duplicados),
        ("colunas_excluidas", colunas_excluidas),
    ]

    with pd.ExcelWriter(
        caminho_temporario,
        engine="openpyxl",
    ) as writer:
        for nome_planilha, quadro in planilhas:
            quadro.to_excel(
                writer,
                sheet_name=nome_planilha,
                index=False,
            )

        ajustar_planilhas(writer)

    caminho_temporario.replace(OUTPUT_PATH)


def executar():
    print(
        "Iniciando análise de granularidade, chaves e "
        "duplicidades da Bronze..."
    )

    dados, manifesto, _contrato = carregar_entradas()

    print("[OK] Bronze e controles carregados")
    print("[OK] Integridade SHA-256: APROVADA")

    grupos_colunas = classificar_colunas(
        dados,
        manifesto,
    )

    print(
        "[OK] Colunas analíticas selecionadas: "
        f"{len(grupos_colunas['analiticas'])}"
    )
    print(
        "[OK] Colunas DQ isoladas: "
        f"{len(grupos_colunas['dq'])}"
    )
    print(
        "[OK] Colunas técnicas identificadas: "
        f"{len(grupos_colunas['tecnicas'])}"
    )

    perfil_identificadores = criar_perfil_identificadores(
        dados
    )

    dados_sem_excedentes = remover_excedentes_exatos(
        dados,
        grupos_colunas["analiticas"],
    )

    chaves_candidatas = testar_chaves_candidatas(
        dados,
        dados_sem_excedentes,
    )

    distribuicao_pedidos = criar_distribuicao_por_pedido(
        dados
    )

    distribuicao_clientes = (
        criar_distribuicao_pedidos_cliente(
            distribuicao_pedidos
        )
    )

    resumo_clientes = criar_resumo_pedidos_cliente(
        distribuicao_clientes
    )

    (
        resumo_repeticoes_pedido_item,
        repeticoes_pedido_item,
    ) = analisar_repeticoes_pedido_item(
        dados,
        dados_sem_excedentes,
    )

    (
        resumo_casos_residuais,
        casos_residuais_diferencas,
    ) = analisar_casos_residuais_diferencas(
        dados_sem_excedentes,
        repeticoes_pedido_item,
        grupos_colunas["analiticas"],
    )

    (
        impacto_duplicidades,
        concentracao_duplicidades,
    ) = analisar_impacto_duplicidades(
        dados,
        dados_sem_excedentes,
        grupos_colunas["analiticas"],
    )

    resumo_granularidade = criar_resumo_granularidade(
        dados,
        distribuicao_pedidos,
    )

    frequencia_linhas_pedido = (
        criar_frequencia_linhas_por_pedido(
            distribuicao_pedidos
        )
    )

    variacao_por_pedido = analisar_variacao_dentro_pedido(
        dados,
        grupos_colunas["analiticas"],
    )

    consistencia_itens = analisar_consistencia_itens(
        dados
    )

    detalhes_mapeamento_itens = (
        criar_detalhes_mapeamento_itens(dados)
    )

    mapa_canonico_candidato = (
        criar_mapa_canonico_candidato(dados)
    )

    (
        resumo_duplicidades,
        grupos_duplicados,
        detalhes_duplicados,
    ) = analisar_duplicidades_exatas(
        dados,
        grupos_colunas["analiticas"],
    )

    conflitos_pedido = criar_conflitos_pedido(
        distribuicao_pedidos
    )

    resultado_preliminar = inferir_resultado_preliminar(
        chaves_candidatas,
        resumo_granularidade,
    )

    colunas_excluidas = criar_colunas_excluidas(
        grupos_colunas
    )

    resumo_execucao = criar_resumo_execucao(
        dados,
        manifesto,
        grupos_colunas,
        resumo_duplicidades,
        conflitos_pedido,
        resumo_repeticoes_pedido_item,
        resumo_clientes,
    )

    salvar_relatorio(
        resumo_execucao,
        resultado_preliminar,
        resumo_granularidade,
        perfil_identificadores,
        chaves_candidatas,
        frequencia_linhas_pedido,
        distribuicao_pedidos,
        resumo_clientes,
        distribuicao_clientes,
        conflitos_pedido,
        resumo_repeticoes_pedido_item,
        repeticoes_pedido_item,
        resumo_casos_residuais,
        casos_residuais_diferencas,
        variacao_por_pedido,
        consistencia_itens,
        detalhes_mapeamento_itens,
        mapa_canonico_candidato,
        impacto_duplicidades,
        concentracao_duplicidades,
        resumo_duplicidades,
        grupos_duplicados,
        detalhes_duplicados,
        colunas_excluidas,
    )

    pedidos_distintos = int(
        dados["Pedido_ID"].nunique(dropna=True)
    )
    pedidos_multiplas_linhas = int(
        distribuicao_pedidos[
            "possui_mais_de_uma_linha"
        ].sum()
    )

    print("[OK] Perfil dos identificadores concluído")
    print(
        "[OK] Pedidos distintos: "
        f"{pedidos_distintos}"
    )
    print(
        "[OK] Pedidos com mais de uma linha: "
        f"{pedidos_multiplas_linhas}"
    )
    print(
        "[OK] Conflitos Pedido_ID x Cliente_ID: "
        f"{len(conflitos_pedido)}"
    )
    print(
        "[OK] Linhas excedentes exatamente duplicadas: "
        f"{resumo_duplicidades.iloc[0]['linhas_excedentes_duplicadas']}"
    )
    print(f"[OK] Relatório gerado: {OUTPUT_PATH}")
    print("RESULTADO_FINAL: APROVADO")

    return True


if __name__ == "__main__":
    try:
        sucesso = executar()
        sys.exit(0 if sucesso else 1)

    except Exception as erro:
        print("RESULTADO_FINAL: REPROVADO")
        print(
            f"ERRO: {type(erro).__name__}: {erro}"
        )
        sys.exit(1)
