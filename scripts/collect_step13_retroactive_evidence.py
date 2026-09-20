"""Gera evidencia retroativa, somente leitura, da carga Gold no SQL Server."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "scripts" else SCRIPT_DIR
load_dotenv(PROJECT_ROOT / ".env")


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Variavel de ambiente obrigatoria ausente: {name}")
    return value


def connection_string() -> str:
    base = (
        f"DRIVER={{{required('CUSTOMER_ANALYTICS_SQL_DRIVER')}}};"
        f"SERVER={required('CUSTOMER_ANALYTICS_SQL_SERVER')};"
        f"DATABASE={required('CUSTOMER_ANALYTICS_SQL_DATABASE')};"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )
    trusted = os.getenv("CUSTOMER_ANALYTICS_SQL_TRUSTED_CONNECTION", "yes")
    if trusted.strip().lower() in {"1", "true", "yes", "sim"}:
        return base + "Trusted_Connection=yes;"
    return (
        base
        + f"UID={required('CUSTOMER_ANALYTICS_SQL_USER')};"
        + f"PWD={required('CUSTOMER_ANALYTICS_SQL_PASSWORD')};"
    )


def main() -> None:
    connection = pyodbc.connect(connection_string(), autocommit=True)
    try:
        cursor = connection.cursor()
        execution = cursor.execute(
            """
            SELECT TOP (1)
                CONVERT(varchar(36), Execucao_ID),
                CONVERT(varchar(33), Inicio_UTC, 126),
                CONVERT(varchar(33), Fim_UTC, 126),
                Status,
                Quantidade_Tabelas,
                Quantidade_Linhas
            FROM audit.execucao_carga_gold
            WHERE Status = 'APROVADO'
            ORDER BY Fim_UTC DESC;
            """
        ).fetchone()
        if execution is None:
            raise RuntimeError("Nenhuma carga Gold APROVADA foi localizada na auditoria.")

        execution_id = execution[0]
        rows = cursor.execute(
            """
            SELECT
                Tabela,
                Linhas_Parquet,
                Linhas_SQL,
                SHA256_Parquet,
                Status
            FROM quality.reconciliacao_carga_gold
            WHERE Execucao_ID = CONVERT(uniqueidentifier, ?)
            ORDER BY Tabela;
            """,
            execution_id,
        ).fetchall()
    finally:
        connection.close()

    reconciliation = [
        {
            "table": row[0],
            "parquet_rows": int(row[1]),
            "sql_rows": int(row[2]),
            "parquet_sha256": row[3],
            "status": row[4],
        }
        for row in rows
    ]
    valid = (
        execution[3] == "APROVADO"
        and int(execution[4] or 0) == 14
        and len(reconciliation) == 14
        and all(
            item["status"] == "APROVADO"
            and item["parquet_rows"] == item["sql_rows"]
            for item in reconciliation
        )
    )
    if not valid:
        raise RuntimeError("A auditoria existe, mas a reconciliacao integral nao foi aprovada.")

    generated = datetime.now(timezone.utc)
    payload = {
        "evidence_type": "retroactive_read_only_validation",
        "stage": 13,
        "status": "success",
        "source": {
            "execution_table": "audit.execucao_carga_gold",
            "reconciliation_table": "quality.reconciliacao_carga_gold",
        },
        "execution_id": execution_id,
        "started_utc": execution[1],
        "finished_utc": execution[2],
        "tables": int(execution[4]),
        "rows": int(execution[5]),
        "reconciliation": reconciliation,
        "generated_utc": generated.isoformat(),
        "read_only": True,
    }
    output_dir = PROJECT_ROOT / "outputs" / "logs" / "sql_load"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"sql_load_retroactive_{generated:%Y%m%dT%H%M%SZ}.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[OK] Evidencia retroativa criada: {output_path}")
    print("[OK] Consulta somente leitura; nenhuma tabela Gold foi alterada.")
    print("RESULTADO_FINAL: APROVADO")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("RESULTADO_FINAL: REPROVADO")
        print(f"ERRO: {type(error).__name__}: {error}")
        raise SystemExit(1)
