#BLOCO 1

import hashlib
import json
import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_PATH = PROJECT_ROOT / ".env"
CONTRACT_PATH = PROJECT_ROOT / "configs" / "source_contract_v3.json"

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze" / "food_commerce"
BRONZE_PATH = BRONZE_DIR / "bronze_transactions_v3.parquet"

MANIFEST_DIR = PROJECT_ROOT / "outputs" / "manifests" / "bronze_v3"
MANIFEST_PATH = MANIFEST_DIR / "step_02_materializacao_bronze.json"

#BLOCO 2

def carregar_configuracoes():
    load_dotenv(ENV_PATH)

    nomes_obrigatorios = [
        "SOURCE_FILE_NAME",
        "SOURCE_SHEET_NAME",
        "LOCAL_DATA_DIR",
    ]

    configuracoes = {
        nome: os.getenv(nome, "").strip()
        for nome in nomes_obrigatorios
    }

    ausentes = [
        nome
        for nome, valor in configuracoes.items()
        if not valor
    ]

    if ausentes:
        raise ValueError(
            "Configurações ausentes no .env: "
            + ", ".join(ausentes)
        )

    return configuracoes


def carregar_contrato():
    with CONTRACT_PATH.open(
        mode="r",
        encoding="utf-8-sig",
    ) as arquivo:
        return json.load(arquivo)


def calcular_sha256(caminho_arquivo):
    sha256 = hashlib.sha256()

    with caminho_arquivo.open(mode="rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            sha256.update(bloco)

    return sha256.hexdigest().upper()

#BLOCO 3

def localizar_arquivo_fonte(configuracoes):
    diretorio_configurado = Path(
        configuracoes["LOCAL_DATA_DIR"]
    )

    if diretorio_configurado.is_absolute():
        diretorio_dados = diretorio_configurado
    else:
        diretorio_dados = PROJECT_ROOT / diretorio_configurado

    nome_arquivo = configuracoes["SOURCE_FILE_NAME"]

    caminhos_candidatos = [
        diretorio_dados / nome_arquivo,
        diretorio_dados / "landing" / nome_arquivo,
    ]

    arquivos_encontrados = [
        caminho
        for caminho in caminhos_candidatos
        if caminho.is_file()
    ]

    if not arquivos_encontrados:
        caminhos_testados = "\n".join(
            str(caminho)
            for caminho in caminhos_candidatos
        )

        raise FileNotFoundError(
            "Arquivo de origem não encontrado. "
            "Caminhos testados:\n"
            f"{caminhos_testados}"
        )

    if len(arquivos_encontrados) > 1:
        raise RuntimeError(
            "Mais de um arquivo de origem foi encontrado. "
            "A localização está ambígua."
        )

    return arquivos_encontrados[0]

#BLOCO 4

def executar_validacao_previa():
    script_validacao = (
        PROJECT_ROOT
        / "src"
        / "ingestion"
        / "step_01_validacao_contrato_fonte.py"
    )

    resultado = subprocess.run(
        [sys.executable, str(script_validacao)],
        cwd=PROJECT_ROOT,
        check=False,
    )

    if resultado.returncode != 0:
        raise RuntimeError(
            "A Etapa 1 foi reprovada. "
            "A materialização da Bronze foi interrompida."
        )

#BLOCO 5

def ler_aba_canonica(caminho_fonte, configuracoes):
    nome_aba = configuracoes["SOURCE_SHEET_NAME"]

    dados = pd.read_excel(
        caminho_fonte,
        sheet_name=nome_aba,
        dtype=str,
        engine="openpyxl",
    )

    for coluna in dados.columns:
        dados[coluna] = dados[coluna].astype("string")

    dados["_source_row_number"] = range(
        2,
        len(dados) + 2,
    )

    return dados

#BLOCO 6

def gravar_bronze_parquet(dados):
    BRONZE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho_temporario = BRONZE_PATH.with_suffix(
        ".tmp.parquet"
    )

    dados.to_parquet(
        caminho_temporario,
        engine="pyarrow",
        compression="snappy",
        index=False,
    )

    caminho_temporario.replace(BRONZE_PATH)

    return BRONZE_PATH

#BLOCO 7

def validar_parquet_gravado(dados_originais):
    dados_recarregados = pd.read_parquet(
        BRONZE_PATH,
        engine="pyarrow",
    )

    if list(dados_originais.columns) != list(
        dados_recarregados.columns
    ):
        raise ValueError(
            "As colunas do Parquet diferem das colunas materializadas."
        )

    if len(dados_originais) != len(dados_recarregados):
        raise ValueError(
            "A quantidade de linhas mudou durante a gravação."
        )

    pd.testing.assert_frame_equal(
        dados_originais,
        dados_recarregados,
        check_dtype=False,
        check_exact=True,
    )

    return {
        "rows": len(dados_recarregados),
        "columns": len(dados_recarregados.columns),
        "parquet_size_bytes": BRONZE_PATH.stat().st_size,
        "parquet_sha256": calcular_sha256(BRONZE_PATH),
    }

#BLOCO 8

def gerar_manifesto_bronze(
    caminho_fonte,
    configuracoes,
    dados,
    validacao,
):
    MANIFEST_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    colunas_fonte = [
        coluna
        for coluna in dados.columns
        if not coluna.startswith("_")
    ]

    colunas_dq = [
        coluna
        for coluna in colunas_fonte
        if coluna.startswith("DQ_")
    ]

    colunas_analiticas = [
        coluna
        for coluna in colunas_fonte
        if not coluna.startswith("DQ_")
    ]

    manifesto = {
        "schema_version": "1.0",
        "pipeline_step": "02_materializacao_bronze",
        "status": "success",
        "materialized_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source": {
            "file_name": caminho_fonte.name,
            "sheet_name": configuracoes[
                "SOURCE_SHEET_NAME"
            ],
            "size_bytes": caminho_fonte.stat().st_size,
            "sha256": calcular_sha256(caminho_fonte),
        },
        "contract": {
            "path": str(
                CONTRACT_PATH.relative_to(PROJECT_ROOT)
            ),
            "sha256": calcular_sha256(CONTRACT_PATH),
            "step_01_approved": True,
        },
        "bronze": {
            "path": str(
                BRONZE_PATH.relative_to(PROJECT_ROOT)
            ),
            "format": "parquet",
            "compression": "snappy",
            "rows": validacao["rows"],
            "source_columns": len(colunas_fonte),
            "analytical_columns": len(
                colunas_analiticas
            ),
            "dq_columns": len(colunas_dq),
            "technical_columns": 1,
            "total_columns": validacao["columns"],
            "size_bytes": validacao[
                "parquet_size_bytes"
            ],
            "sha256": validacao["parquet_sha256"],
        },
        "lineage": {
            "canonical_sheet_only": True,
            "source_row_number_added": True,
            "source_values_cleaned": False,
            "source_values_normalized": False,
            "source_rows_removed": False,
            "dq_columns_preserved": True,
            "dq_columns_used_for_discovery": False,
        },
    }

    caminho_temporario = MANIFEST_PATH.with_suffix(
        ".tmp.json"
    )

    with caminho_temporario.open(
        mode="w",
        encoding="utf-8",
    ) as arquivo:
        json.dump(
            manifesto,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )

    caminho_temporario.replace(MANIFEST_PATH)

    return manifesto

#BLOCO 9

def executar():
    print("Iniciando materialização da Bronze...")

    configuracoes = carregar_configuracoes()

    # Confirma que o contrato existe e possui JSON válido.
    carregar_contrato()

    caminho_fonte = localizar_arquivo_fonte(
        configuracoes
    )

    print(
        f"Fonte encontrada: {caminho_fonte.name}"
    )
    print(
        "Executando validação obrigatória da Etapa 1..."
    )

    executar_validacao_previa()

    print("[OK] Contrato da fonte: APROVADO")
    print(
        "Lendo exclusivamente a aba canônica: "
        f"{configuracoes['SOURCE_SHEET_NAME']}"
    )

    dados = ler_aba_canonica(
        caminho_fonte,
        configuracoes,
    )

    print(
        f"[OK] Linhas lidas: {len(dados)}"
    )
    print(
        f"[OK] Colunas da fonte: {len(dados.columns) - 1}"
    )
    print(
        "[OK] Coluna técnica adicionada: "
        "_source_row_number"
    )

    gravar_bronze_parquet(dados)

    print(
        f"[OK] Bronze gravada: {BRONZE_PATH}"
    )

    validacao = validar_parquet_gravado(dados)

    print(
        "[OK] Validação de ida e volta: APROVADA"
    )
    print(
        f"[OK] SHA-256 do Parquet: "
        f"{validacao['parquet_sha256']}"
    )

    gerar_manifesto_bronze(
        caminho_fonte,
        configuracoes,
        dados,
        validacao,
    )

    print(
        f"[OK] Manifesto gerado: {MANIFEST_PATH}"
    )
    print("RESULTADO_FINAL: APROVADO")

    return True

#BLOCO 10

if __name__ == "__main__":
    try:
        sucesso = executar()
        sys.exit(0 if sucesso else 1)

    except Exception as erro:
        print(
            f"RESULTADO_FINAL: REPROVADO"
        )
        print(
            f"ERRO: {type(erro).__name__}: {erro}"
        )
        sys.exit(1)