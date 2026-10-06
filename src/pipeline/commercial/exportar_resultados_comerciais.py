"""Exporta os resultados da análise comercial do SQL Server para Parquet."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import pyodbc


NOMES_RESULTADOS = [
    "01_evolucao_mensal",
    "02_shapley_receita",
    "03_decomposicao_ticket",
    "04_novos_recorrentes",
    "05_participacao_novos_recorrentes",
    "06_desempenho_categoria",
    "07_pareto_produtos",
    "08_alerta_crescimento",
    "09_primeiro_ultimo_mes",
]

NOME_BANCO = os.getenv("CUSTOMER_ANALYTICS_DB", "CustomerAnalyticsHub")
SERVIDOR_SQL = os.getenv(
    "CUSTOMER_ANALYTICS_SQL_SERVER", r"DESKTOP-MAMEBQ8\SQLEXPRESS"
)
DRIVER_SQL = os.getenv(
    "CUSTOMER_ANALYTICS_SQL_DRIVER", "ODBC Driver 17 for SQL Server"
)

ARQUIVO_ATUAL = Path(__file__).resolve()
RAIZ_PROJETO = ARQUIVO_ATUAL.parents[3]
ARQUIVO_SQL = (
    RAIZ_PROJETO
    / "sql"
    / "04_business"
    / "commercial"
    / "02_decomposicao_crescimento_comercial.sql"
)
PASTA_EXPORTACAO = RAIZ_PROJETO / "data" / "exports" / "commercial"
PASTA_QUALITY = RAIZ_PROJETO / "quality" / "commercial" / "exportacao_parquet"


def obter_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def criar_conexao() -> pyodbc.Connection:
    string_conexao = (
        f"DRIVER={{{DRIVER_SQL}}};"
        f"SERVER={SERVIDOR_SQL};"
        f"DATABASE={NOME_BANCO};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
        "Encrypt=yes;"
    )
    return pyodbc.connect(string_conexao, autocommit=True, timeout=30)


def ler_arquivo_sql(caminho: Path) -> str:
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo SQL não encontrado: {caminho}")
    return caminho.read_text(encoding="utf-8-sig")


def separar_batches_sql(conteudo_sql: str) -> list[str]:
    batches = re.split(
        r"^\s*GO\s*;?\s*$",
        conteudo_sql,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return [batch.strip() for batch in batches if batch.strip()]


def normalizar_valor_json(valor: Any) -> Any:
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (datetime, pd.Timestamp)):
        return valor.isoformat()
    if hasattr(valor, "item"):
        return valor.item()
    return valor


def executar_sql_com_resultados(
    conexao: pyodbc.Connection, batches: list[str]
) -> list[pd.DataFrame]:
    resultados: list[pd.DataFrame] = []
    cursor = conexao.cursor()
    try:
        for numero_batch, batch in enumerate(batches, start=1):
            print(f"Executando batch SQL {numero_batch}/{len(batches)}...")
            cursor.execute(batch)
            while True:
                if cursor.description is not None:
                    colunas = [coluna[0] for coluna in cursor.description]
                    linhas = cursor.fetchall()
                    dataframe = pd.DataFrame.from_records(linhas, columns=colunas)
                    if len(dataframe.columns) > 0:
                        resultados.append(dataframe)
                if not cursor.nextset():
                    break
    finally:
        cursor.close()
    return resultados


def validar_dataframe(nome_resultado: str, dataframe: pd.DataFrame) -> dict[str, Any]:
    quantidade_linhas = int(len(dataframe))
    quantidade_colunas = int(len(dataframe.columns))
    quantidade_nulos = int(dataframe.isna().sum().sum())
    quantidade_duplicidades = int(dataframe.duplicated().sum())
    status = "APROVADO"
    observacoes: list[str] = []

    if quantidade_linhas == 0:
        status = "REPROVADO"
        observacoes.append("Resultado sem registros.")
    if quantidade_colunas == 0:
        status = "REPROVADO"
        observacoes.append("Resultado sem colunas.")
    if quantidade_duplicidades > 0:
        observacoes.append(
            "Existem linhas integralmente duplicadas; avaliar a granularidade."
        )
    if quantidade_nulos > 0:
        observacoes.append(
            "Existem valores nulos; alguns podem ser esperados no primeiro mês."
        )

    return {
        "resultado": nome_resultado,
        "linhas": quantidade_linhas,
        "colunas": quantidade_colunas,
        "valores_nulos": quantidade_nulos,
        "linhas_duplicadas": quantidade_duplicidades,
        "status_estrutural": status,
        "observacoes": observacoes,
    }


def salvar_parquet(dataframe: pd.DataFrame, caminho_destino: Path) -> None:
    caminho_destino.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_parquet(
        caminho_destino, engine="pyarrow", compression="snappy", index=False
    )


def validar_leitura_parquet(
    dataframe_original: pd.DataFrame, caminho_parquet: Path
) -> dict[str, Any]:
    dataframe_recarregado = pd.read_parquet(caminho_parquet, engine="pyarrow")
    linhas_iguais = len(dataframe_original) == len(dataframe_recarregado)
    colunas_iguais = list(dataframe_original.columns) == list(
        dataframe_recarregado.columns
    )
    return {
        "arquivo": caminho_parquet.name,
        "linhas_origem": int(len(dataframe_original)),
        "linhas_parquet": int(len(dataframe_recarregado)),
        "linhas_iguais": linhas_iguais,
        "colunas_iguais": colunas_iguais,
        "status_releitura": (
            "APROVADO" if linhas_iguais and colunas_iguais else "REPROVADO"
        ),
    }


def salvar_manifesto(manifesto: dict[str, Any], caminho_destino: Path) -> None:
    caminho_destino.parent.mkdir(parents=True, exist_ok=True)
    conteudo = json.dumps(
        manifesto, ensure_ascii=False, indent=2, default=normalizar_valor_json
    )
    caminho_destino.write_text(conteudo, encoding="utf-8")


def executar_exportacao() -> int:
    timestamp = obter_timestamp()
    print("=" * 70)
    print("EXPORTAÇÃO DOS RESULTADOS COMERCIAIS")
    print("=" * 70)
    print(f"Servidor: {SERVIDOR_SQL}")
    print(f"Banco: {NOME_BANCO}")
    print(f"Consulta: {ARQUIVO_SQL}")
    print(f"Destino: {PASTA_EXPORTACAO}")
    print("=" * 70)

    conteudo_sql = ler_arquivo_sql(ARQUIVO_SQL)
    batches = separar_batches_sql(conteudo_sql)
    if not batches:
        raise RuntimeError("Nenhum batch SQL foi identificado no arquivo.")

    PASTA_EXPORTACAO.mkdir(parents=True, exist_ok=True)
    PASTA_QUALITY.mkdir(parents=True, exist_ok=True)

    conexao = criar_conexao()
    try:
        resultados = executar_sql_com_resultados(conexao, batches)
    finally:
        conexao.close()

    quantidade_esperada = len(NOMES_RESULTADOS)
    quantidade_encontrada = len(resultados)
    if quantidade_encontrada != quantidade_esperada:
        raise RuntimeError(
            "Quantidade inesperada de conjuntos de resultados. "
            f"Esperados: {quantidade_esperada}. "
            f"Encontrados: {quantidade_encontrada}. "
            "Verifique se o SQL retorna exatamente os blocos 01 a 09."
        )

    validacoes: list[dict[str, Any]] = []
    arquivos_gerados: list[dict[str, Any]] = []

    for nome_resultado, dataframe in zip(NOMES_RESULTADOS, resultados, strict=True):
        caminho_parquet = PASTA_EXPORTACAO / f"{nome_resultado}.parquet"
        validacao_estrutura = validar_dataframe(nome_resultado, dataframe)
        salvar_parquet(dataframe, caminho_parquet)
        validacao_releitura = validar_leitura_parquet(dataframe, caminho_parquet)
        validacoes.append({**validacao_estrutura, **validacao_releitura})
        arquivos_gerados.append(
            {
                "resultado": nome_resultado,
                "arquivo": str(caminho_parquet.relative_to(RAIZ_PROJETO)),
                "tamanho_bytes": caminho_parquet.stat().st_size,
            }
        )
        print(
            f"[{validacao_releitura['status_releitura']}] "
            f"{caminho_parquet.name}: {len(dataframe)} linhas e "
            f"{len(dataframe.columns)} colunas."
        )

    todos_aprovados = all(
        item["status_estrutural"] == "APROVADO"
        and item["status_releitura"] == "APROVADO"
        for item in validacoes
    )

    manifesto = {
        "processo": "exportacao_resultados_comerciais",
        "timestamp_utc": timestamp,
        "servidor_sql": SERVIDOR_SQL,
        "banco_dados": NOME_BANCO,
        "arquivo_sql": str(ARQUIVO_SQL.relative_to(RAIZ_PROJETO)),
        "pasta_destino": str(PASTA_EXPORTACAO.relative_to(RAIZ_PROJETO)),
        "formato": "parquet",
        "compressao": "snappy",
        "quantidade_resultados_esperada": quantidade_esperada,
        "quantidade_resultados_exportada": quantidade_encontrada,
        "arquivos_gerados": arquivos_gerados,
        "validacoes": validacoes,
        "status_final": "APROVADO" if todos_aprovados else "REPROVADO",
    }

    caminho_manifesto = (
        PASTA_QUALITY / f"{timestamp}_exportacao_resultados_comerciais.json"
    )
    salvar_manifesto(manifesto, caminho_manifesto)
    print("=" * 70)
    print(f"Manifesto: {caminho_manifesto}")
    print(f"Status final: {manifesto['status_final']}")
    print("=" * 70)
    return 0 if todos_aprovados else 1


if __name__ == "__main__":
    try:
        codigo_saida = executar_exportacao()
    except Exception as erro:
        print("=" * 70)
        print("STATUS FINAL: REPROVADO")
        print(f"Erro: {erro}")
        print("=" * 70)
        codigo_saida = 1
    sys.exit(codigo_saida)
