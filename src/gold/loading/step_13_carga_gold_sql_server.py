from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

import pandas as pd
import pyodbc
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")
GOLD_DIR = PROJECT_ROOT / "data" / "gold" / "food_commerce" / "gold_v3"
SPEC_PATH = (
    PROJECT_ROOT / "outputs" / "modeling" / "gold_v3"
    / "step_11_especificacao_modelo_dimensional.xlsx"
)

DIMENSIONS = [
    "dim_data", "dim_horario", "dim_geografia", "dim_pagamento",
    "dim_campanha", "dim_canal_marketing", "dim_evento_externo",
    "dim_transportadora", "dim_cliente", "dim_produto",
]
FACTS = ["fato_item_pedido", "fato_pedido", "fato_entrega", "fato_cliente_mes"]
TABLES = DIMENSIONS + FACTS

TYPE_MAP = {
    "int8": "SMALLINT", "int16": "SMALLINT", "int32": "INT", "int64": "BIGINT",
    "float64": "DECIMAL(19,6)", "bool": "BIT", "date": "DATE",
    "datetime": "DATETIME2(6)", "time": "TIME(0)", "string": "NVARCHAR(4000)",
}


def env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Variável de ambiente obrigatória ausente: {name}")
    return value


def q(identifier: str) -> str:
    return "[" + str(identifier).replace("]", "]]" ) + "]"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def connection_string() -> str:
    base = (
        f"DRIVER={{{env('CUSTOMER_ANALYTICS_SQL_DRIVER')}}};"
        f"SERVER={env('CUSTOMER_ANALYTICS_SQL_SERVER')};"
        f"DATABASE={env('CUSTOMER_ANALYTICS_SQL_DATABASE')};"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )
    trusted = os.getenv("CUSTOMER_ANALYTICS_SQL_TRUSTED_CONNECTION", "yes")
    if trusted.strip().lower() in {"1", "true", "yes", "sim"}:
        return base + "Trusted_Connection=yes;"
    return (
        base
        + f"UID={env('CUSTOMER_ANALYTICS_SQL_USER')};"
        + f"PWD={env('CUSTOMER_ANALYTICS_SQL_PASSWORD')};"
    )


def load_contract() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not SPEC_PATH.exists():
        raise FileNotFoundError(f"Contrato dimensional não encontrado: {SPEC_PATH}")
    columns = pd.read_excel(SPEC_PATH, sheet_name="colunas_modelo")
    relationships = pd.read_excel(SPEC_PATH, sheet_name="relacionamentos")
    table_spec = pd.read_excel(SPEC_PATH, sheet_name="tabelas_modelo")
    expected = set(TABLES)
    if set(table_spec["tabela"]) != expected:
        raise ValueError("O contrato da Etapa 11 não contém exatamente as 14 tabelas Gold.")
    return columns, relationships, table_spec


def load_parquets(columns: pd.DataFrame) -> dict[str, pd.DataFrame]:
    result = {}
    for table in TABLES:
        path = GOLD_DIR / f"{table}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Parquet Gold não encontrado: {path}")
        frame = pd.read_parquet(path)
        expected_columns = columns.loc[columns["tabela"].eq(table), "coluna_gold"].tolist()
        if frame.columns.tolist() != expected_columns:
            raise ValueError(
                f"Contrato divergente em {table}: esperado={expected_columns}; "
                f"observado={frame.columns.tolist()}"
            )
        result[table] = frame
    return result


def ensure_control_objects(cursor) -> None:
    cursor.execute("""
    IF SCHEMA_ID('gold') IS NULL EXEC('CREATE SCHEMA gold');
    IF SCHEMA_ID('quality') IS NULL EXEC('CREATE SCHEMA quality');
    IF SCHEMA_ID('audit') IS NULL EXEC('CREATE SCHEMA audit');
    IF SCHEMA_ID('eda') IS NULL EXEC('CREATE SCHEMA eda');
    IF OBJECT_ID('audit.execucao_carga_gold', 'U') IS NULL
    CREATE TABLE audit.execucao_carga_gold (
        Execucao_ID UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
        Inicio_UTC DATETIME2(6) NOT NULL,
        Fim_UTC DATETIME2(6) NULL,
        Status VARCHAR(20) NOT NULL,
        Diretorio_Fonte NVARCHAR(1000) NOT NULL,
        Quantidade_Tabelas INT NULL,
        Quantidade_Linhas BIGINT NULL,
        Erro NVARCHAR(4000) NULL
    );
    IF OBJECT_ID('quality.reconciliacao_carga_gold', 'U') IS NULL
    CREATE TABLE quality.reconciliacao_carga_gold (
        Execucao_ID UNIQUEIDENTIFIER NOT NULL,
        Tabela SYSNAME NOT NULL,
        Linhas_Parquet BIGINT NOT NULL,
        Linhas_SQL BIGINT NOT NULL,
        SHA256_Parquet CHAR(64) NOT NULL,
        Status VARCHAR(20) NOT NULL,
        CONSTRAINT PK_reconciliacao_carga_gold PRIMARY KEY (Execucao_ID, Tabela),
        CONSTRAINT FK_reconciliacao_execucao FOREIGN KEY (Execucao_ID)
            REFERENCES audit.execucao_carga_gold(Execucao_ID)
    );
    """)


def create_gold_tables(cursor, columns: pd.DataFrame, table_spec: pd.DataFrame) -> None:
    for table in TABLES:
        if cursor.execute("SELECT OBJECT_ID(?, 'U')", f"gold.{table}").fetchval() is not None:
            continue
        subset = columns.loc[columns["tabela"].eq(table)]
        definitions = []
        for row in subset.itertuples(index=False):
            sql_type = TYPE_MAP.get(str(row.tipo_sugerido))
            if not sql_type:
                raise ValueError(f"Tipo sem mapeamento SQL: {row.tipo_sugerido}")
            nullable = "NULL" if str(row.aceita_nulo).lower() == "sim" else "NOT NULL"
            definitions.append(f"{q(row.coluna_gold)} {sql_type} {nullable}")
        pk = table_spec.loc[table_spec["tabela"].eq(table), "chave_primaria"].iloc[0]
        definitions.append(f"CONSTRAINT {q('PK_' + table)} PRIMARY KEY ({q(pk)})")
        cursor.execute(f"CREATE TABLE {q('gold')}.{q(table)} (" + ",".join(definitions) + ")")


def add_foreign_keys(cursor, relationships: pd.DataFrame) -> None:
    for row in relationships.itertuples(index=False):
        ref_table, ref_column = str(row.referencia).split(".", 1)
        name = f"FK_{row.tabela_origem}_{row.coluna_fk}_{ref_table}"
        exists = cursor.execute(
            "SELECT 1 FROM sys.foreign_keys WHERE name = ?", name
        ).fetchone()
        if not exists:
            cursor.execute(
                f"ALTER TABLE {q('gold')}.{q(row.tabela_origem)} "
                f"ADD CONSTRAINT {q(name)} FOREIGN KEY ({q(row.coluna_fk)}) "
                f"REFERENCES {q('gold')}.{q(ref_table)} ({q(ref_column)})"
            )


def python_value(value, contract_type: str):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if contract_type == "string":
        return str(value)
    if contract_type in {"int8", "int16", "int32", "int64"}:
        return int(value)
    if contract_type == "float64":
        # O contrato SQL usa DECIMAL(19,6). Quantizar antes do ODBC evita
        # perda implícita de precisão e mantém arredondamento determinístico.
        return Decimal(str(float(value))).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_EVEN
        )
    if contract_type == "bool":
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"true", "1", "sim"}:
                return True
            if normalized in {"false", "0", "não", "nao"}:
                return False
            raise ValueError(f"Valor booleano inválido: {value!r}")
        return bool(value)
    if contract_type == "date":
        return pd.Timestamp(value).date()
    if contract_type == "datetime":
        return pd.Timestamp(value).to_pydatetime()
    if contract_type == "time":
        if isinstance(value, time):
            return value.replace(microsecond=0)
        parsed = pd.to_datetime(str(value), format="%H:%M", errors="raise")
        return parsed.time().replace(microsecond=0)
    return str(value)


def replace_data(cursor, frames: dict[str, pd.DataFrame], columns: pd.DataFrame) -> None:
    # DELETE em ordem filho->pai respeita as FKs e torna a recarga idempotente.
    for table in reversed(FACTS):
        cursor.execute(f"DELETE FROM {q('gold')}.{q(table)}")
    for table in reversed(DIMENSIONS):
        cursor.execute(f"DELETE FROM {q('gold')}.{q(table)}")
    for table in TABLES:
        frame = frames[table]
        table_contract = columns.loc[columns["tabela"].eq(table)]
        contract_types = dict(zip(table_contract["coluna_gold"], table_contract["tipo_sugerido"]))
        names = ",".join(q(column) for column in frame.columns)
        marks = ",".join("?" for _ in frame.columns)
        sql = f"INSERT INTO {q('gold')}.{q(table)} ({names}) VALUES ({marks})"
        print(f"[CARGA] {table}: {len(frame)} linhas")
        cursor.fast_executemany = True
        records = [
            tuple(
                python_value(value, str(contract_types[column]))
                for column, value in zip(frame.columns, row)
            )
            for row in frame.itertuples(index=False, name=None)
        ]
        try:
            cursor.executemany(sql, records)
        except Exception as error:
            raise RuntimeError(f"Falha ao carregar gold.{table}: {error}") from error


def reconcile(cursor, execution_id: uuid.UUID, frames: dict[str, pd.DataFrame]) -> None:
    failures = []
    for table in TABLES:
        source_rows = len(frames[table])
        sql_rows = int(cursor.execute(f"SELECT COUNT_BIG(*) FROM {q('gold')}.{q(table)}").fetchval())
        status = "APROVADO" if source_rows == sql_rows else "REPROVADO"
        digest = sha256_file(GOLD_DIR / f"{table}.parquet")
        cursor.execute(
            "INSERT INTO quality.reconciliacao_carga_gold "
            "(Execucao_ID,Tabela,Linhas_Parquet,Linhas_SQL,SHA256_Parquet,Status) "
            "VALUES (?,?,?,?,?,?)",
            execution_id, table, source_rows, sql_rows, digest, status,
        )
        if status == "REPROVADO":
            failures.append((table, source_rows, sql_rows))
    if failures:
        raise ValueError(f"Reconciliação Parquet x SQL reprovada: {failures}")


def main() -> None:
    started = datetime.now(timezone.utc).replace(tzinfo=None)
    execution_id = uuid.uuid4()
    columns, relationships, table_spec = load_contract()
    frames = load_parquets(columns)
    connection = pyodbc.connect(connection_string(), autocommit=False)
    try:
        cursor = connection.cursor()
        ensure_control_objects(cursor)
        connection.commit()
        cursor.execute(
            "INSERT INTO audit.execucao_carga_gold "
            "(Execucao_ID,Inicio_UTC,Status,Diretorio_Fonte) VALUES (?,?,?,?)",
            execution_id, started, "EM_EXECUCAO", str(GOLD_DIR),
        )
        connection.commit()
        try:
            create_gold_tables(cursor, columns, table_spec)
            add_foreign_keys(cursor, relationships)
            replace_data(cursor, frames, columns)
            reconcile(cursor, execution_id, frames)
            total_rows = sum(len(frame) for frame in frames.values())
            cursor.execute(
                "UPDATE audit.execucao_carga_gold SET Fim_UTC=?,Status='APROVADO',"
                "Quantidade_Tabelas=?,Quantidade_Linhas=? WHERE Execucao_ID=?",
                datetime.now(timezone.utc).replace(tzinfo=None), len(TABLES), total_rows, execution_id,
            )
            connection.commit()
        except Exception as error:
            connection.rollback()
            cursor.execute(
                "UPDATE audit.execucao_carga_gold SET Fim_UTC=?,Status='REPROVADO',Erro=? "
                "WHERE Execucao_ID=?",
                datetime.now(timezone.utc).replace(tzinfo=None), str(error)[:4000], execution_id,
            )
            connection.commit()
            raise
    finally:
        connection.close()
    print(f"[OK] {len(TABLES)} tabelas Gold carregadas no SQL Server.")
    print(f"[OK] Execução auditada: {execution_id}")
    log_dir = PROJECT_ROOT / "outputs" / "logs" / "sql_load"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"sql_load_{started.strftime('%Y%m%dT%H%M%S_%fZ')}.json"
    log_path.write_text(
        json.dumps(
            {
                "execution_id": str(execution_id),
                "status": "success",
                "tables": len(TABLES),
                "rows": total_rows,
                "started_utc": started.isoformat(),
                "finished_utc": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[OK] Log local da carga: {log_path}")
    print("RESULTADO_FINAL: APROVADO")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("RESULTADO_FINAL: REPROVADO")
        print(f"ERRO: {type(error).__name__}: {error}")
        sys.exit(1)
