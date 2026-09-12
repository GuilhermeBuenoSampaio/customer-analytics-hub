import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_PATH = PROJECT_ROOT / ".env"
CONTRACT_PATH = PROJECT_ROOT / "configs" / "source_contract_v3.json"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "profiling" / "bronze_v3"
OUTPUT_PATH = OUTPUT_DIR / "step_01_validacao_contrato_fonte.xlsx"

def carregar_configuracoes():
    if not ENV_PATH.exists():
        raise FileNotFoundError(f"Arquivo .env não encontrado: {ENV_PATH}")

    load_dotenv(ENV_PATH)

    nomes_obrigatorios = [
        "SOURCE_FILE_NAME",
        "SOURCE_SHEET_NAME",
        "LOCAL_DATA_DIR",
    ]

    configuracoes = {
        nome: os.getenv(nome)
        for nome in nomes_obrigatorios
    }

    ausentes = [
        nome
        for nome, valor in configuracoes.items()
        if valor is None or not valor.strip()
    ]

    if ausentes:
        raise ValueError(
            "Variáveis ausentes ou vazias no .env: "
            + ", ".join(ausentes)
        )

    return configuracoes


def carregar_contrato():
    if not CONTRACT_PATH.exists():
        raise FileNotFoundError(
            f"Contrato da fonte não encontrado: {CONTRACT_PATH}"
        )

    with CONTRACT_PATH.open(
        mode="r",
        encoding="utf-8-sig",
    ) as arquivo:
        return json.load(arquivo)


def calcular_sha256(caminho_arquivo):
    calculador = hashlib.sha256()

    with caminho_arquivo.open(mode="rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            calculador.update(bloco)

    return calculador.hexdigest().upper()


def registrar_resultado(
    resultados,
    controle,
    esperado,
    encontrado,
    aprovado,
    critico=True,
):
    status = "APROVADO" if aprovado else "REPROVADO"

    resultados.append(
        {
            "controle": controle,
            "esperado": esperado,
            "encontrado": encontrado,
            "status": status,
            "critico": critico,
        }
    )

    marcador = "OK" if aprovado else "ERRO"
    print(f"[{marcador}] {controle}: {status}")


def salvar_relatorio(resultados, colunas_encontradas, contrato):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tabela_resultados = pd.DataFrame(resultados)

    colunas_analiticas = set(contrato["analytical_columns"])
    colunas_dq = set(contrato["dq_columns"])

    registros_colunas = []

    for ordem, coluna in enumerate(colunas_encontradas, start=1):
        if coluna in colunas_analiticas:
            grupo = "analitica"
        elif coluna in colunas_dq:
            grupo = "dq_validacao"
        else:
            grupo = "nao_prevista"

        registros_colunas.append(
            {
                "ordem": ordem,
                "coluna": coluna,
                "grupo": grupo,
            }
        )

    tabela_colunas = pd.DataFrame(registros_colunas)

    with pd.ExcelWriter(
        OUTPUT_PATH,
        engine="openpyxl",
    ) as escritor:
        tabela_resultados.to_excel(
            escritor,
            sheet_name="validacoes",
            index=False,
        )

        tabela_colunas.to_excel(
            escritor,
            sheet_name="colunas_encontradas",
            index=False,
        )

    print(f"Relatório gerado: {OUTPUT_PATH}")



def executar():
    print("Iniciando validação do contrato da fonte...")

    resultados = []
    colunas_encontradas = []

    configuracoes = carregar_configuracoes()
    contrato = carregar_contrato()

    fonte_contratada = contrato["source"]
    estrutura_esperada = contrato["expected_structure"]

    diretorio_dados = Path(configuracoes["LOCAL_DATA_DIR"])

    if not diretorio_dados.is_absolute():
        diretorio_dados = PROJECT_ROOT / diretorio_dados

    caminho_fonte = (
        diretorio_dados
        / "landing"
        / configuracoes["SOURCE_FILE_NAME"]
    )

    registrar_resultado(
        resultados,
        controle="Nome do arquivo configurado",
        esperado=fonte_contratada["file_name"],
        encontrado=configuracoes["SOURCE_FILE_NAME"],
        aprovado=(
            configuracoes["SOURCE_FILE_NAME"]
            == fonte_contratada["file_name"]
        ),
    )

    registrar_resultado(
        resultados,
        controle="Aba canônica configurada",
        esperado=fonte_contratada["sheet_name"],
        encontrado=configuracoes["SOURCE_SHEET_NAME"],
        aprovado=(
            configuracoes["SOURCE_SHEET_NAME"]
            == fonte_contratada["sheet_name"]
        ),
    )

    arquivo_existe = caminho_fonte.exists()

    registrar_resultado(
        resultados,
        controle="Arquivo local encontrado",
        esperado=True,
        encontrado=arquivo_existe,
        aprovado=arquivo_existe,
    )

    if not arquivo_existe:
        salvar_relatorio(
            resultados,
            colunas_encontradas,
            contrato,
        )
        return False

    hash_encontrado = calcular_sha256(caminho_fonte)
    hash_esperado = fonte_contratada["sha256"].upper()

    registrar_resultado(
        resultados,
        controle="Integridade SHA-256",
        esperado=hash_esperado,
        encontrado=hash_encontrado,
        aprovado=(hash_encontrado == hash_esperado),
    )

    planilha = pd.ExcelFile(
        caminho_fonte,
        engine="openpyxl",
    )

    aba_esperada = configuracoes["SOURCE_SHEET_NAME"]
    aba_existe = aba_esperada in planilha.sheet_names

    registrar_resultado(
        resultados,
        controle="Aba canônica encontrada",
        esperado=True,
        encontrado=aba_existe,
        aprovado=aba_existe,
    )

    if not aba_existe:
        salvar_relatorio(
            resultados,
            colunas_encontradas,
            contrato,
        )
        return False

    dados = pd.read_excel(
        caminho_fonte,
        sheet_name=aba_esperada,
        engine="openpyxl",
    )

    colunas_encontradas = [
        str(coluna)
        for coluna in dados.columns
    ]

    colunas_esperadas = (
        contrato["analytical_columns"]
        + contrato["dq_columns"]
    )

    registrar_resultado(
        resultados,
        controle="Quantidade de linhas",
        esperado=estrutura_esperada["data_rows"],
        encontrado=len(dados),
        aprovado=(
            len(dados)
            == estrutura_esperada["data_rows"]
        ),
    )

    registrar_resultado(
        resultados,
        controle="Quantidade de colunas",
        esperado=estrutura_esperada["columns"],
        encontrado=len(dados.columns),
        aprovado=(
            len(dados.columns)
            == estrutura_esperada["columns"]
        ),
    )

    registrar_resultado(
        resultados,
        controle="Ordem e nomes das colunas",
        esperado=" | ".join(colunas_esperadas),
        encontrado=" | ".join(colunas_encontradas),
        aprovado=(
            colunas_encontradas
            == colunas_esperadas
        ),
    )

    cabecalhos_duplicados = (
        len(colunas_encontradas)
        - len(set(colunas_encontradas))
    )

    registrar_resultado(
        resultados,
        controle="Cabeçalhos duplicados",
        esperado=0,
        encontrado=cabecalhos_duplicados,
        aprovado=(cabecalhos_duplicados == 0),
    )

    cabecalhos_vazios = [
        coluna
        for coluna in colunas_encontradas
        if not coluna.strip()
        or coluna.startswith("Unnamed:")
    ]

    registrar_resultado(
        resultados,
        controle="Cabeçalhos vazios",
        esperado=0,
        encontrado=len(cabecalhos_vazios),
        aprovado=(len(cabecalhos_vazios) == 0),
    )

    dq_ausentes = [
        coluna
        for coluna in contrato["dq_columns"]
        if coluna not in colunas_encontradas
    ]

    registrar_resultado(
        resultados,
        controle="Colunas DQ obrigatórias",
        esperado=4,
        encontrado=(
            len(contrato["dq_columns"])
            - len(dq_ausentes)
        ),
        aprovado=(len(dq_ausentes) == 0),
    )

    salvar_relatorio(
        resultados,
        colunas_encontradas,
        contrato,
    )

    falhas_criticas = [
        resultado
        for resultado in resultados
        if resultado["critico"]
        and resultado["status"] == "REPROVADO"
    ]

    if falhas_criticas:
        print(
            "RESULTADO_FINAL: REPROVADO "
            f"({len(falhas_criticas)} falha(s) crítica(s))"
        )
        return False

    print("RESULTADO_FINAL: APROVADO")
    return True



if __name__ == "__main__":
    try:
        sucesso = executar()
        sys.exit(0 if sucesso else 1)

    except Exception as erro:
        print(
            f"ERRO NÃO TRATADO: "
            f"{type(erro).__name__}: {erro}"
        )
        sys.exit(1)