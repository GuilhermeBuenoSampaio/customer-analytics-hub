"""Executa os arquivos T-SQL em ordem e registra rastreabilidade local."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SQL_ROOT = PROJECT_ROOT / "sql"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "logs" / "sql_pipeline"
load_dotenv(PROJECT_ROOT / ".env")

PASTAS_ORDENADAS = ["00_setup", "01_quality", "02_audit", "03_eda", "04_business"]


def env(nome: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(f"Variável de ambiente obrigatória ausente: {nome}")
    return valor


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
    return base + f"UID={env('CUSTOMER_ANALYTICS_SQL_USER')};PWD={env('CUSTOMER_ANALYTICS_SQL_PASSWORD')};"


def descobrir_scripts() -> list[Path]:
    scripts = []
    for pasta in PASTAS_ORDENADAS:
        raiz = SQL_ROOT / pasta
        if raiz.is_dir():
            scripts.extend(
                sorted(
                    raiz.rglob("*.sql"),
                    key=lambda p: p.relative_to(raiz).as_posix().casefold(),
                )
            )
    return scripts


def separar_lotes(conteudo: str) -> list[str]:
    return [
        lote.strip()
        for lote in re.split(r"(?im)^\s*GO\s*(?:--.*)?$", conteudo)
        if lote.strip()
    ]


def ler_sql(caminho: Path) -> str:
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            return caminho.read_text(encoding=codificacao)
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"Codificação SQL não suportada: {caminho}")


def executar_script(cursor, caminho: Path) -> dict:
    inicio = datetime.now(timezone.utc)
    lotes = separar_lotes(ler_sql(caminho))
    conjuntos_resultado = 0
    linhas_resultado = 0
    for lote in lotes:
        cursor.execute(lote)
        while True:
            if cursor.description:
                linhas = cursor.fetchall()
                conjuntos_resultado += 1
                linhas_resultado += len(linhas)
            if not cursor.nextset():
                break
    fim = datetime.now(timezone.utc)
    return {
        "arquivo": str(caminho.relative_to(PROJECT_ROOT)),
        "status": "success",
        "lotes": len(lotes),
        "conjuntos_resultado": conjuntos_resultado,
        "linhas_resultado": linhas_resultado,
        "inicio_utc": inicio.isoformat(),
        "fim_utc": fim.isoformat(),
        "duracao_segundos": round((fim - inicio).total_seconds(), 4),
    }


def main() -> bool:
    scripts = descobrir_scripts()
    if not scripts:
        raise FileNotFoundError(f"Nenhum arquivo SQL encontrado em {SQL_ROOT}")

    inicio = datetime.now(timezone.utc)
    registro = {
        "pipeline": "customer_analytics_sql",
        "inicio_utc": inicio.isoformat(),
        "status": "running",
        "scripts": [],
    }
    conexao = pyodbc.connect(connection_string(), autocommit=False)
    try:
        cursor = conexao.cursor()
        for script in scripts:
            print(f"[SQL] {script.relative_to(PROJECT_ROOT)}")
            try:
                registro["scripts"].append(executar_script(cursor, script))
                conexao.commit()
            except Exception as erro:
                conexao.rollback()
                registro["scripts"].append({
                    "arquivo": str(script.relative_to(PROJECT_ROOT)),
                    "status": "failed",
                    "erro": f"{type(erro).__name__}: {erro}",
                })
                raise
        registro["status"] = "success"
        return True
    except Exception as erro:
        registro["status"] = "failed"
        registro["erro"] = f"{type(erro).__name__}: {erro}"
        return False
    finally:
        conexao.close()
        fim = datetime.now(timezone.utc)
        registro["fim_utc"] = fim.isoformat()
        registro["duracao_segundos"] = round((fim - inicio).total_seconds(), 4)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        destino = OUTPUT_DIR / f"sql_pipeline_{inicio.strftime('%Y%m%dT%H%M%S_%fZ')}.json"
        destino.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Log SQL: {destino}")


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except Exception as erro:
        print(f"RESULTADO_FINAL_SQL: REPROVADO - {type(erro).__name__}: {erro}")
        sys.exit(1)
