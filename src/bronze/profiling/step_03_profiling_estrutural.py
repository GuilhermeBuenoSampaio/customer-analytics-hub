import json
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from openpyxl.styles import Alignment, Font, PatternFill

import pandas as pd


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
    / "step_03_profiling_estrutural.xlsx"
)

DQ_PREFIX = "DQ_"
TECHNICAL_PREFIX = "_"

def calcular_sha256(caminho_arquivo):
    sha256 = hashlib.sha256()

    with caminho_arquivo.open(mode="rb") as arquivo:
        for bloco in iter(
            lambda: arquivo.read(1024 * 1024),
            b"",
        ):
            sha256.update(bloco)

    return sha256.hexdigest().upper()


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

def calcular_percentual(quantidade, total):
    if total == 0:
        return 0.0

    return round(
        quantidade / total * 100,
        4,
    )


def criar_perfil_colunas(
    dados,
    colunas_analiticas,
):
    total_linhas = len(dados)
    registros_perfil = []

    for posicao, coluna in enumerate(
        colunas_analiticas,
        start=1,
    ):
        serie = dados[coluna].astype("string")

        mascara_nulos = serie.isna()
        mascara_vazios = (
            serie.notna()
            & serie.str.strip().eq("")
        )
        mascara_espacos_externos = (
            serie.notna()
            & serie.ne(serie.str.strip())
        )

        valores_informados = serie[
            ~mascara_nulos
            & ~mascara_vazios
        ]

        valores_unicos = valores_informados.nunique(
            dropna=True
        )

        comprimentos = valores_informados.str.len()

        exemplos = (
            valores_informados
            .drop_duplicates()
            .head(5)
            .str.replace(
                r"[\r\n\t]+",
                " ",
                regex=True,
            )
            .tolist()
        )

        registros_perfil.append(
            {
                "posicao": posicao,
                "coluna": coluna,
                "tipo_fisico_bronze": str(
                    dados[coluna].dtype
                ),
                "total_linhas": total_linhas,
                "nulos": int(mascara_nulos.sum()),
                "percentual_nulos": calcular_percentual(
                    int(mascara_nulos.sum()),
                    total_linhas,
                ),
                "vazios": int(mascara_vazios.sum()),
                "percentual_vazios": calcular_percentual(
                    int(mascara_vazios.sum()),
                    total_linhas,
                ),
                "espacos_externos": int(
                    mascara_espacos_externos.sum()
                ),
                "valores_informados": len(
                    valores_informados
                ),
                "valores_unicos": int(valores_unicos),
                "percentual_cardinalidade": (
                    calcular_percentual(
                        int(valores_unicos),
                        len(valores_informados),
                    )
                ),
                "comprimento_minimo": (
                    int(comprimentos.min())
                    if not comprimentos.empty
                    else None
                ),
                "comprimento_maximo": (
                    int(comprimentos.max())
                    if not comprimentos.empty
                    else None
                ),
                "exemplos": " | ".join(exemplos),
            }
        )

    return pd.DataFrame(registros_perfil)

def criar_perfil_conversibilidade(
    dados,
    colunas_analiticas,
):
    registros_conversibilidade = []

    for coluna in colunas_analiticas:
        serie = dados[coluna].astype("string").str.strip()

        valores = serie[
            serie.notna()
            & serie.ne("")
        ]

        valores_numericos = pd.to_numeric(
            valores.str.replace(
                ",",
                ".",
                regex=False,
            ),
            errors="coerce",
        )

        valores_data = pd.to_datetime(
            valores,
            errors="coerce",
            dayfirst=True,
            format="mixed",
        )

        mascara_formato_horario = valores.str.match(
            r"^\d{1,2}:\d{2}(:\d{2})?(\.\d+)?$",
            na=False,
        )

        valores_horario = pd.to_timedelta(
            valores.where(mascara_formato_horario),
            errors="coerce",
        )

        mascara_horario_valido = (
            valores_horario.notna()
            & (valores_horario >= pd.Timedelta(0))
            & (valores_horario < pd.Timedelta(days=1))
        )

        total_informados = len(valores)

        numericos_validos = int(
            valores_numericos.notna().sum()
        )
        datas_validas = int(
            valores_data.notna().sum()
        )
        horarios_validos = int(
            mascara_horario_valido.sum()
        )

        registros_conversibilidade.append(
            {
                "coluna": coluna,
                "valores_informados": total_informados,
                "numericos_validos": numericos_validos,
                "percentual_numerico": calcular_percentual(
                    numericos_validos,
                    total_informados,
                ),
                "datas_validas": datas_validas,
                "percentual_data": calcular_percentual(
                    datas_validas,
                    total_informados,
                ),
                "horarios_validos": horarios_validos,
                "percentual_horario": calcular_percentual(
                    horarios_validos,
                    total_informados,
                ),
            }
        )

    return pd.DataFrame(
        registros_conversibilidade
    )

def sugerir_tipos(
    perfil_colunas,
    perfil_conversibilidade,
):
    perfil_completo = perfil_colunas.merge(
        perfil_conversibilidade,
        on=[
            "coluna",
            "valores_informados",
        ],
        how="left",
        validate="one_to_one",
    )

    tipos_sugeridos = []
    motivos = []

    for _, linha in perfil_completo.iterrows():
        nome = linha["coluna"].upper()

        eh_identificador = (
            nome.endswith("_ID")
            or nome.startswith("ID_")
        )

        eh_nome_data = (
            "DATA" in nome
            or nome == "MES_REF"
        )

        eh_nome_horario = "HORARIO" in nome

        if eh_identificador:
            tipo = "identificador_textual"
            motivo = (
                "Nome indica identificador; "
                "não deve ser usado em operações matemáticas."
            )

        elif (
            eh_nome_horario
            and linha["percentual_horario"] >= 95
        ):
            tipo = "horario"
            motivo = (
                "Nome indica horário e pelo menos "
                "95% dos valores são compatíveis."
            )

        elif (
            eh_nome_data
            and linha["percentual_data"] >= 95
        ):
            tipo = "data"
            motivo = (
                "Nome indica data e pelo menos "
                "95% dos valores são compatíveis."
            )

        elif linha["percentual_numerico"] >= 95:
            tipo = "numerico"
            motivo = (
                "Pelo menos 95% dos valores informados "
                "podem ser convertidos em número."
            )

        elif linha["valores_unicos"] <= 20:
            tipo = "categorico_textual"
            motivo = (
                "Baixa cardinalidade: até 20 "
                "valores distintos."
            )

        else:
            tipo = "texto"
            motivo = (
                "Não atingiu os critérios preliminares "
                "para número, data, horário ou categoria."
            )

        tipos_sugeridos.append(tipo)
        motivos.append(motivo)

    perfil_completo[
        "tipo_sugerido_preliminar"
    ] = tipos_sugeridos

    perfil_completo[
        "motivo_sugestao"
    ] = motivos

    return perfil_completo

def analisar_duplicidade(
    dados,
    colunas_analiticas,
):
    dados_analiticos = dados[
        colunas_analiticas
    ]

    mascara_grupo_duplicado = (
        dados_analiticos.duplicated(
            keep=False
        )
    )

    mascara_excedente_duplicado = (
        dados_analiticos.duplicated(
            keep="first"
        )
    )

    linhas_em_grupos_duplicados = int(
        mascara_grupo_duplicado.sum()
    )

    linhas_excedentes = int(
        mascara_excedente_duplicado.sum()
    )

    resumo = pd.DataFrame(
        [
            {
                "criterio": (
                    "Duplicidade exata nas "
                    "43 colunas analíticas"
                ),
                "total_linhas": len(dados),
                "linhas_em_grupos_duplicados": (
                    linhas_em_grupos_duplicados
                ),
                "linhas_excedentes_duplicadas": (
                    linhas_excedentes
                ),
                "percentual_excedente": (
                    calcular_percentual(
                        linhas_excedentes,
                        len(dados),
                    )
                ),
                "dq_usado_na_comparacao": False,
                "coluna_tecnica_usada": False,
            }
        ]
    )

    detalhes = dados.loc[
        mascara_grupo_duplicado,
        ["_source_row_number"]
        + colunas_analiticas,
    ].copy()

    if not detalhes.empty:
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

        detalhes = detalhes.sort_values(
            by=[
                "_duplicate_group_id",
                "_source_row_number",
            ]
        )

    return resumo, detalhes

def criar_inventario_colunas_excluidas(
    grupos_colunas,
):
    registros = []

    for coluna in grupos_colunas["dq"]:
        registros.append(
            {
                "coluna": coluna,
                "classificacao": "ground_truth_dq",
                "participou_da_descoberta": False,
                "motivo_exclusao": (
                    "Preservada para validação final das "
                    "regras, evitando vazamento da resposta."
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
                    "Usada somente para rastreabilidade "
                    "até a linha original da fonte."
                ),
            }
        )

    return pd.DataFrame(registros)


def criar_resumo_execucao(
    dados,
    manifesto,
    grupos_colunas,
    resumo_duplicidade,
):
    return pd.DataFrame(
        [
            {
                "executado_em_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "etapa": "03_profiling_estrutural",
                "arquivo_bronze": BRONZE_PATH.name,
                "sha256_bronze": manifesto[
                    "bronze"
                ]["sha256"],
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
                "linhas_excedentes_duplicadas": (
                    resumo_duplicidade.iloc[0][
                        "linhas_excedentes_duplicadas"
                    ]
                ),
                "dados_modificados": False,
                "status": "success",
            }
        ]
    )

def salvar_relatorio(
    resumo_execucao,
    perfil_completo,
    resumo_duplicidade,
    detalhes_duplicidade,
    colunas_excluidas,
):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho_temporario = OUTPUT_PATH.with_suffix(
        ".tmp.xlsx"
    )

    with pd.ExcelWriter(
        caminho_temporario,
        engine="openpyxl",
    ) as writer:
        resumo_execucao.to_excel(
            writer,
            sheet_name="resumo_execucao",
            index=False,
        )

        perfil_completo.to_excel(
            writer,
            sheet_name="perfil_colunas",
            index=False,
        )

        resumo_duplicidade.to_excel(
            writer,
            sheet_name="duplicidade_resumo",
            index=False,
        )

        detalhes_duplicidade.to_excel(
            writer,
            sheet_name="duplicidade_detalhes",
            index=False,
        )

        colunas_excluidas.to_excel(
            writer,
            sheet_name="colunas_excluidas",
            index=False,
        )

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
            planilha.auto_filter.ref = (
                planilha.dimensions
            )

            for celula in planilha[1]:
                celula.fill = cor_cabecalho
                celula.font = fonte_cabecalho
                celula.alignment = Alignment(
                    horizontal="center",
                    vertical="center",
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

                letra_coluna = (
                    coluna_celulas[0].column_letter
                )

                planilha.column_dimensions[
                    letra_coluna
                ].width = largura

    caminho_temporario.replace(OUTPUT_PATH)

def executar():
    print("Iniciando profiling estrutural da Bronze...")

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

    perfil_colunas = criar_perfil_colunas(
        dados,
        grupos_colunas["analiticas"],
    )

    perfil_conversibilidade = (
        criar_perfil_conversibilidade(
            dados,
            grupos_colunas["analiticas"],
        )
    )

    perfil_completo = sugerir_tipos(
        perfil_colunas,
        perfil_conversibilidade,
    )

    (
        resumo_duplicidade,
        detalhes_duplicidade,
    ) = analisar_duplicidade(
        dados,
        grupos_colunas["analiticas"],
    )

    colunas_excluidas = (
        criar_inventario_colunas_excluidas(
            grupos_colunas
        )
    )

    resumo_execucao = criar_resumo_execucao(
        dados,
        manifesto,
        grupos_colunas,
        resumo_duplicidade,
    )

    salvar_relatorio(
        resumo_execucao,
        perfil_completo,
        resumo_duplicidade,
        detalhes_duplicidade,
        colunas_excluidas,
    )

    print("[OK] Perfil estrutural concluído")
    print(
        "[OK] Linhas excedentes duplicadas: "
        f"{resumo_duplicidade.iloc[0]['linhas_excedentes_duplicadas']}"
    )
    print(
        f"[OK] Relatório gerado: {OUTPUT_PATH}"
    )
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