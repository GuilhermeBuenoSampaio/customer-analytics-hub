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
    / "step_05_investigacao_dados_ausentes.xlsx"
)

DQ_PREFIX = "DQ_"
TECHNICAL_PREFIX = "_"

COLUNAS_ALVO = [
    "Categoria_Item",
    "Cupom_Utilizado",
    "Transportadora",
    "Cidade",
    "Escolaridade",
    "Prazo_Entrega_Real",
    "Atraso_Entrega",
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

    return round(quantidade / total * 100, 4)


def normalizar_texto_diagnostico(valor):
    if pd.isna(valor):
        return pd.NA

    texto = " ".join(str(valor).strip().casefold().split())

    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )


def preparar_texto(serie):
    serie_texto = serie.astype("string")

    return serie_texto.where(
        serie_texto.isna(),
        serie_texto.str.strip(),
    )


def mascara_ausencia(serie):
    serie_texto = serie.astype("string")

    return serie_texto.isna() | serie_texto.str.strip().eq("")


def formatar_frequencias(serie):
    valores = preparar_texto(serie)
    valores = valores.loc[
        valores.notna() & valores.ne("")
    ]

    if valores.empty:
        return None

    frequencias = valores.value_counts(dropna=False)

    return " | ".join(
        f"{valor}: {quantidade}"
        for valor, quantidade in frequencias.items()
    )


def obter_moda_segura(serie):
    valores = preparar_texto(serie)
    valores = valores.loc[
        valores.notna() & valores.ne("")
    ]

    if valores.empty:
        return None, 0, 0

    frequencias = valores.value_counts(dropna=False)

    return (
        frequencias.index[0],
        int(frequencias.iloc[0]),
        len(valores),
    )


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
        for coluna in COLUNAS_ALVO
        if coluna not in dados.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas obrigatórias ausentes: "
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

    esperadas = {
        "analiticas": manifesto["bronze"][
            "analytical_columns"
        ],
        "dq": manifesto["bronze"]["dq_columns"],
        "tecnicas": manifesto["bronze"][
            "technical_columns"
        ],
    }
    encontradas = {
        "analiticas": len(colunas_analiticas),
        "dq": len(colunas_dq),
        "tecnicas": len(colunas_tecnicas),
    }

    if encontradas != esperadas:
        raise ValueError(
            "A classificação das colunas difere do manifesto. "
            f"Esperado: {esperadas}. Encontrado: {encontradas}."
        )

    return {
        "analiticas": colunas_analiticas,
        "dq": colunas_dq,
        "tecnicas": colunas_tecnicas,
    }


def criar_resumo_nulos(dados, colunas_analiticas):
    registros = []

    for coluna in colunas_analiticas:
        serie = dados[coluna].astype("string")
        nulos = int(serie.isna().sum())
        vazios = int(
            (serie.notna() & serie.str.strip().eq("")).sum()
        )
        total_ausentes = nulos + vazios

        registros.append(
            {
                "coluna": coluna,
                "total_linhas": len(dados),
                "nulos": nulos,
                "vazios_ou_so_espacos": vazios,
                "total_ausentes": total_ausentes,
                "percentual_ausentes": calcular_percentual(
                    total_ausentes,
                    len(dados),
                ),
                "coluna_alvo_etapa_05": coluna in COLUNAS_ALVO,
            }
        )

    return pd.DataFrame(registros).sort_values(
        by=["total_ausentes", "coluna"],
        ascending=[False, True],
    )


def criar_padroes_ausencia(dados):
    quadro = pd.DataFrame(index=dados.index)

    for coluna in COLUNAS_ALVO:
        quadro[coluna] = mascara_ausencia(dados[coluna])

    quadro["padrao_ausencia"] = quadro.apply(
        lambda linha: " | ".join(
            coluna
            for coluna in COLUNAS_ALVO
            if linha[coluna]
        ) or "sem_ausencia_nas_colunas_alvo",
        axis=1,
    )

    resumo = (
        quadro["padrao_ausencia"]
        .value_counts(dropna=False)
        .rename_axis("padrao_ausencia")
        .reset_index(name="quantidade_linhas")
    )
    resumo["percentual_linhas"] = resumo[
        "quantidade_linhas"
    ].apply(
        lambda quantidade: calcular_percentual(
            quantidade,
            len(dados),
        )
    )

    return resumo


def analisar_recuperacao_por_grupo(
    dados,
    coluna_alvo,
    coluna_grupo,
    colunas_contexto,
):
    mascara = mascara_ausencia(dados[coluna_alvo])
    registros = []

    for indice, linha in dados.loc[mascara].iterrows():
        chave = preparar_texto(
            pd.Series([linha[coluna_grupo]])
        ).iloc[0]

        grupo = dados.loc[
            preparar_texto(dados[coluna_grupo]).eq(chave)
        ]
        candidatos = grupo.loc[
            ~mascara_ausencia(grupo[coluna_alvo]),
            coluna_alvo,
        ]

        candidato, suporte, total_informados = (
            obter_moda_segura(candidatos)
        )
        distintos_normalizados = int(
            candidatos.map(
                normalizar_texto_diagnostico
            ).nunique(dropna=True)
        )

        if total_informados == 0:
            classificacao = "nao_recuperavel_internamente"
        elif distintos_normalizados == 1:
            classificacao = "recuperavel_deterministico"
        else:
            classificacao = "candidato_com_conflito_no_grupo"

        registro = {
            "_source_row_number": linha["_source_row_number"],
            coluna_grupo: linha[coluna_grupo],
            "coluna_ausente": coluna_alvo,
            "valor_original": linha[coluna_alvo],
            "candidato_recuperacao": candidato,
            "suporte_candidato": suporte,
            "total_valores_informados_grupo": total_informados,
            "percentual_suporte": calcular_percentual(
                suporte,
                total_informados,
            ),
            "valores_distintos_normalizados": (
                distintos_normalizados
            ),
            "valores_e_frequencias_grupo": (
                formatar_frequencias(candidatos)
            ),
            "classificacao_preliminar": classificacao,
            "decisao_silver": "pendente",
        }

        for coluna in colunas_contexto:
            if coluna in dados.columns:
                registro[coluna] = linha[coluna]

        registros.append(registro)

    return pd.DataFrame(registros)


def analisar_categoria_item(dados):
    return analisar_recuperacao_por_grupo(
        dados=dados,
        coluna_alvo="Categoria_Item",
        coluna_grupo="Id_Item",
        colunas_contexto=[
            "Pedido_ID",
            "Produto",
            "Medida",
        ],
    )


def analisar_atributo_cliente(dados, coluna_alvo):
    return analisar_recuperacao_por_grupo(
        dados=dados,
        coluna_alvo=coluna_alvo,
        coluna_grupo="Cliente_ID",
        colunas_contexto=[
            "Pedido_ID",
            "Cidade",
            "Estado",
            "Escolaridade",
        ],
    )


def analisar_cupom(dados):
    mascara = mascara_ausencia(dados["Cupom_Utilizado"])
    registros = []

    for _, linha in dados.loc[mascara].iterrows():
        pedido = preparar_texto(
            pd.Series([linha["Pedido_ID"]])
        ).iloc[0]
        grupo = dados.loc[
            preparar_texto(dados["Pedido_ID"]).eq(pedido)
        ]
        cupons = grupo.loc[
            ~mascara_ausencia(grupo["Cupom_Utilizado"]),
            "Cupom_Utilizado",
        ]
        candidato, suporte, total = obter_moda_segura(cupons)
        distintos = int(
            cupons.map(
                normalizar_texto_diagnostico
            ).nunique(dropna=True)
        )

        if total > 0 and distintos == 1:
            classificacao = "recuperavel_por_mesmo_pedido"
        elif total > 0:
            classificacao = "conflito_dentro_do_pedido"
        else:
            classificacao = "sem_evidencia_no_mesmo_pedido"

        registros.append(
            {
                "_source_row_number": linha["_source_row_number"],
                "Pedido_ID": linha["Pedido_ID"],
                "Cliente_ID": linha["Cliente_ID"],
                "Id_Item": linha["Id_Item"],
                "Cupom_Utilizado": linha["Cupom_Utilizado"],
                "Desconto_Percentual": linha[
                    "Desconto_Percentual"
                ],
                "Campanha": linha["Campanha"],
                "Valor_Compra": linha["Valor_Compra"],
                "linhas_no_pedido": len(grupo),
                "candidato_cupom_mesmo_pedido": candidato,
                "suporte_candidato": suporte,
                "valores_cupom_no_pedido": (
                    formatar_frequencias(cupons)
                ),
                "valores_desconto_no_pedido": (
                    formatar_frequencias(
                        grupo["Desconto_Percentual"]
                    )
                ),
                "classificacao_preliminar": classificacao,
                "decisao_silver": "pendente_regra_desconto",
            }
        )

    return pd.DataFrame(registros)


def analisar_logistica(dados):
    colunas_logisticas = [
        "Transportadora",
        "Prazo_Entrega_Prometido",
        "Prazo_Entrega_Real",
        "Atraso_Entrega",
        "Frete",
        "Frete_Gratis",
    ]
    mascara_alvo = (
        mascara_ausencia(dados["Transportadora"])
        | mascara_ausencia(dados["Prazo_Entrega_Real"])
        | mascara_ausencia(dados["Atraso_Entrega"])
    )
    registros = []

    for _, linha in dados.loc[mascara_alvo].iterrows():
        pedido = preparar_texto(
            pd.Series([linha["Pedido_ID"]])
        ).iloc[0]
        grupo = dados.loc[
            preparar_texto(dados["Pedido_ID"]).eq(pedido)
        ]

        registro = {
            "_source_row_number": linha["_source_row_number"],
            "Pedido_ID": linha["Pedido_ID"],
            "Cliente_ID": linha["Cliente_ID"],
            "Id_Item": linha["Id_Item"],
            "linhas_no_pedido": len(grupo),
        }

        ausentes_linha = []
        recuperaveis = []

        for coluna in colunas_logisticas:
            registro[coluna] = linha[coluna]

            if mascara_ausencia(
                pd.Series([linha[coluna]])
            ).iloc[0]:
                ausentes_linha.append(coluna)

                candidatos = grupo.loc[
                    ~mascara_ausencia(grupo[coluna]),
                    coluna,
                ]
                candidato, suporte, total = obter_moda_segura(
                    candidatos
                )
                distintos = int(
                    candidatos.map(
                        normalizar_texto_diagnostico
                    ).nunique(dropna=True)
                )

                registro[f"{coluna}_candidato"] = candidato
                registro[f"{coluna}_suporte"] = suporte
                registro[f"{coluna}_distintos_pedido"] = distintos

                if total > 0 and distintos == 1:
                    recuperaveis.append(coluna)

        registro["campos_ausentes_linha"] = " | ".join(
            ausentes_linha
        )
        registro["campos_recuperaveis_mesmo_pedido"] = (
            " | ".join(recuperaveis)
        )

        if len(recuperaveis) == len(ausentes_linha):
            classificacao = "recuperavel_por_mesmo_pedido"
        elif recuperaveis:
            classificacao = "parcialmente_recuperavel"
        else:
            classificacao = "sem_evidencia_no_mesmo_pedido"

        registro["classificacao_preliminar"] = classificacao
        registro["decisao_silver"] = (
            "pendente_contexto_logistico"
        )
        registros.append(registro)

    return pd.DataFrame(registros)


def criar_resumo_recuperabilidade(resultados):
    registros = []

    for nome, quadro in resultados.items():
        if quadro.empty:
            registros.append(
                {
                    "analise": nome,
                    "registros_ausentes": 0,
                    "classificacao": "sem_ausencias",
                    "quantidade": 0,
                    "percentual": 0.0,
                }
            )
            continue

        frequencias = quadro[
            "classificacao_preliminar"
        ].value_counts(dropna=False)

        for classificacao, quantidade in frequencias.items():
            registros.append(
                {
                    "analise": nome,
                    "registros_ausentes": len(quadro),
                    "classificacao": classificacao,
                    "quantidade": int(quantidade),
                    "percentual": calcular_percentual(
                        int(quantidade),
                        len(quadro),
                    ),
                }
            )

    return pd.DataFrame(registros)


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
                    "Usada apenas para localizar os registros "
                    "na fonte."
                ),
            }
        )

    return pd.DataFrame(registros)


def criar_resumo_execucao(
    dados,
    manifesto,
    grupos_colunas,
    resumo_nulos,
):
    total_ausencias = int(
        resumo_nulos["total_ausentes"].sum()
    )

    return pd.DataFrame(
        [
            {
                "executado_em_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "etapa": "05_investigacao_dados_ausentes",
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
                "colunas_com_ausencia": int(
                    resumo_nulos["total_ausentes"].gt(0).sum()
                ),
                "total_celulas_ausentes": total_ausencias,
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
            largura = min(maior_comprimento + 2, 60)
            letra_coluna = coluna_celulas[0].column_letter
            planilha.column_dimensions[
                letra_coluna
            ].width = largura


def salvar_relatorio(planilhas):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporario = OUTPUT_PATH.with_suffix(".tmp.xlsx")

    with pd.ExcelWriter(
        temporario,
        engine="openpyxl",
    ) as writer:
        for nome, quadro in planilhas:
            quadro.to_excel(
                writer,
                sheet_name=nome,
                index=False,
            )

        ajustar_planilhas(writer)

    temporario.replace(OUTPUT_PATH)


def executar():
    print("Iniciando investigação dos dados ausentes...")

    dados, manifesto, _contrato = carregar_entradas()

    print("[OK] Bronze e controles carregados")
    print("[OK] Integridade SHA-256: APROVADA")

    grupos_colunas = classificar_colunas(
        dados,
        manifesto,
    )

    resumo_nulos = criar_resumo_nulos(
        dados,
        grupos_colunas["analiticas"],
    )
    padroes_ausencia = criar_padroes_ausencia(dados)
    categoria_nulos = analisar_categoria_item(dados)
    cupom_nulos = analisar_cupom(dados)
    cidade_nulos = analisar_atributo_cliente(
        dados,
        "Cidade",
    )
    escolaridade_nulos = analisar_atributo_cliente(
        dados,
        "Escolaridade",
    )
    logistica_nulos = analisar_logistica(dados)

    resultados = {
        "Categoria_Item": categoria_nulos,
        "Cupom_Utilizado": cupom_nulos,
        "Cidade": cidade_nulos,
        "Escolaridade": escolaridade_nulos,
        "Logistica": logistica_nulos,
    }

    resumo_recuperabilidade = (
        criar_resumo_recuperabilidade(resultados)
    )
    colunas_excluidas = criar_colunas_excluidas(
        grupos_colunas
    )
    resumo_execucao = criar_resumo_execucao(
        dados,
        manifesto,
        grupos_colunas,
        resumo_nulos,
    )

    planilhas = [
        ("resumo_execucao", resumo_execucao),
        ("nulos_resumo", resumo_nulos),
        ("recuperabilidade_resumo", resumo_recuperabilidade),
        ("padroes_ausencia", padroes_ausencia),
        ("categoria_item_nulos", categoria_nulos),
        ("cupom_nulos", cupom_nulos),
        ("cidade_nulos", cidade_nulos),
        ("escolaridade_nulos", escolaridade_nulos),
        ("logistica_nulos", logistica_nulos),
        ("colunas_excluidas", colunas_excluidas),
    ]

    salvar_relatorio(planilhas)

    print(
        "[OK] Colunas analíticas analisadas: "
        f"{len(grupos_colunas['analiticas'])}"
    )
    print(
        "[OK] Colunas com ausência: "
        f"{resumo_nulos['total_ausentes'].gt(0).sum()}"
    )
    print(
        "[OK] Categoria_Item ausente: "
        f"{len(categoria_nulos)}"
    )
    print(
        "[OK] Cupom_Utilizado ausente: "
        f"{len(cupom_nulos)}"
    )
    print(
        "[OK] Cidade ausente: "
        f"{len(cidade_nulos)}"
    )
    print(
        "[OK] Escolaridade ausente: "
        f"{len(escolaridade_nulos)}"
    )
    print(
        "[OK] Linhas com ausência logística: "
        f"{len(logistica_nulos)}"
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
