"""Executa os arquivos T-SQL em ordem com validação e rastreabilidade local."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyodbc
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SQL_ROOT = PROJECT_ROOT / "sql"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "logs" / "sql_pipeline"
load_dotenv(PROJECT_ROOT / ".env")

PASTAS_ORDENADAS = ["00_setup", "01_quality", "02_audit", "03_eda", "04_business"]
STATUS_REPROVADOS = {"REPROVADO", "REPROVADA", "FAILED", "FAIL", "FAILURE", "ERROR", "ERRO"}


class ValidacaoSQLReprovada(RuntimeError):
    def __init__(self, mensagem: str, registro: dict[str, Any]) -> None:
        super().__init__(mensagem)
        self.registro = registro


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
    scripts: list[Path] = []
    for pasta in PASTAS_ORDENADAS:
        raiz = SQL_ROOT / pasta
        if raiz.is_dir():
            scripts.extend(sorted(raiz.rglob("*.sql"), key=lambda p: p.relative_to(raiz).as_posix().casefold()))
    return scripts


def separar_lotes(conteudo: str) -> list[str]:
    return [lote.strip() for lote in re.split(r"(?im)^\s*GO\s*(?:--.*)?$", conteudo) if lote.strip()]


def ler_sql(caminho: Path) -> str:
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            return caminho.read_text(encoding=codificacao)
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"Codificação SQL não suportada: {caminho}")


def sql_sem_comentarios_e_textos(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\r\n]*", " ", sql)
    return re.sub(r"N?'(?:''|[^'])*'", "''", sql, flags=re.IGNORECASE)


def validar_seguranca(caminho: Path, conteudo: str) -> None:
    """Bloqueia mutações permanentes fora das exceções auditadas."""
    relativo = caminho.relative_to(PROJECT_ROOT).as_posix()
    sql = sql_sem_comentarios_e_textos(conteudo)
    # Tabelas iniciadas por # são temporárias e existem apenas na sessão SQL.
    # Removemos esses comandos da inspeção antes de procurar DROP permanente.
    sql_inspecao = re.sub(
        r"\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?#{1,2}[A-Za-z0-9_]+\s*;?",
        " ",
        sql,
        flags=re.IGNORECASE,
    )
    proibicoes = [
        (r"\b(?:UPDATE|DELETE|MERGE|TRUNCATE)\b", "DML permanente/destrutivo"),
        (r"\bINSERT\s+INTO\s+(?!#)", "INSERT em objeto permanente"),
        (r"\bSELECT\b[\s\S]*?\bINTO\s+(?!#)", "SELECT INTO permanente"),
        (r"\bDROP\s+(?:TABLE|VIEW|SCHEMA|DATABASE)\b", "DROP permanente"),
        (r"\bALTER\s+(?:TABLE|SCHEMA|DATABASE)\b", "ALTER permanente"),
        (r"\bCREATE\s+TABLE\s+(?!#)", "CREATE TABLE permanente"),
        (r"\bCREATE\s+DATABASE\b", "CREATE DATABASE"),
    ]
    for padrao, descricao in proibicoes:
        if re.search(padrao, sql_inspecao, flags=re.IGNORECASE):
            raise RuntimeError(f"Operação bloqueada em {relativo}: {descricao}")

    setup_autorizado = relativo == "sql/00_setup/01_criacao_schemas.sql"
    if re.search(r"\b(?:CREATE\s+SCHEMA|EXEC(?:UTE)?)\b", sql, re.IGNORECASE) and not setup_autorizado:
        raise RuntimeError(f"CREATE SCHEMA/EXEC não autorizado em {relativo}")

    views = re.findall(r"\bCREATE\s+(?:OR\s+ALTER\s+)?VIEW\s+([^\s(]+)", sql, flags=re.IGNORECASE)
    for view in views:
        nome = view.replace("[", "").replace("]", "").lower()
        if not relativo.startswith("sql/03_eda/") or not nome.startswith("eda."):
            raise RuntimeError(f"CREATE VIEW não autorizado em {relativo}: {view}")


def valor_canonico(valor: Any) -> Any:
    if valor is None or isinstance(valor, (bool, int, str)):
        return valor
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else str(valor)
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, (datetime, date, time)):
        return valor.isoformat()
    if isinstance(valor, bytes):
        return {"bytes_sha256": hashlib.sha256(valor).hexdigest()}
    return str(valor)


def resumo_resultado(cursor, numero: int) -> tuple[dict[str, Any], set[str]]:
    colunas = [str(coluna[0]) for coluna in cursor.description]
    linhas = cursor.fetchall()
    digest = hashlib.sha256()
    statuses_observados: set[str] = set()
    nomes_normalizados = {nome.casefold() for nome in colunas}
    eh_historico_execucao = {
        "execucao_id",
        "inicio_utc",
        "fim_utc",
        "status",
    }.issubset(nomes_normalizados)
    indices_status = [i for i, nome in enumerate(colunas) if "status" in nome.casefold()]
    for linha in linhas:
        canonica = [valor_canonico(valor) for valor in linha]
        digest.update(json.dumps(canonica, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        digest.update(b"\n")
        for indice in indices_status:
            if linha[indice] is not None:
                statuses_observados.add(str(linha[indice]).strip())
    statuses_para_gate = set() if eh_historico_execucao else statuses_observados
    return ({
        "numero": numero,
        "colunas": colunas,
        "linhas": len(linhas),
        "sha256": digest.hexdigest(),
        "status_encontrados": sorted(statuses_observados, key=str.casefold),
        "gate_validacao_aplicado": not eh_historico_execucao,
    }, statuses_para_gate)


def executar_script(cursor, caminho: Path) -> dict[str, Any]:
    inicio = datetime.now(timezone.utc)
    conteudo = ler_sql(caminho)
    validar_seguranca(caminho, conteudo)
    lotes = separar_lotes(conteudo)
    resultados: list[dict[str, Any]] = []
    reprovacoes: set[str] = set()
    registro: dict[str, Any] = {
        "arquivo": caminho.relative_to(PROJECT_ROOT).as_posix(),
        "status": "running",
        "lotes": len(lotes),
        "resultados": resultados,
        "inicio_utc": inicio.isoformat(),
    }
    for lote in lotes:
        cursor.execute(lote)
        while True:
            if cursor.description:
                resumo, statuses = resumo_resultado(cursor, len(resultados) + 1)
                resultados.append(resumo)
                reprovacoes.update(s for s in statuses if s.upper() in STATUS_REPROVADOS)
            if not cursor.nextset():
                break
    fim = datetime.now(timezone.utc)
    registro.update({
        "status": "success" if not reprovacoes else "failed",
        "conjuntos_resultado": len(resultados),
        "linhas_resultado": sum(item["linhas"] for item in resultados),
        "fim_utc": fim.isoformat(),
        "duracao_segundos": round((fim - inicio).total_seconds(), 4),
    })
    if reprovacoes:
        encontrados = ", ".join(sorted(reprovacoes, key=str.casefold))
        registro["erro"] = f"Status lógico reprovado: {encontrados}"
        raise ValidacaoSQLReprovada(registro["erro"], registro)
    return registro


def salvar_registro(registro: dict[str, Any], inicio: datetime) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destino = OUTPUT_DIR / f"sql_pipeline_{inicio.strftime('%Y%m%dT%H%M%S_%fZ')}.json"
    temporario = destino.with_suffix(".json.tmp")
    temporario.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    temporario.replace(destino)
    return destino


def main() -> bool:
    inicio = datetime.now(timezone.utc)
    registro: dict[str, Any] = {
        "pipeline": "customer_analytics_sql",
        "inicio_utc": inicio.isoformat(),
        "status": "running",
        "scripts": [],
    }
    conexao = None
    try:
        scripts = descobrir_scripts()
        if not scripts:
            raise FileNotFoundError(f"Nenhum arquivo SQL encontrado em {SQL_ROOT}")
        registro["quantidade_scripts"] = len(scripts)
        conexao = pyodbc.connect(connection_string(), autocommit=False)
        cursor = conexao.cursor()
        for script in scripts:
            print(f"[SQL] {script.relative_to(PROJECT_ROOT)}")
            try:
                resultado = executar_script(cursor, script)
                registro["scripts"].append(resultado)
                conexao.commit()
            except ValidacaoSQLReprovada as erro:
                conexao.rollback()
                registro["scripts"].append(erro.registro)
                raise
            except Exception as erro:
                conexao.rollback()
                registro["scripts"].append({
                    "arquivo": script.relative_to(PROJECT_ROOT).as_posix(),
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
        if conexao is not None:
            conexao.close()
        fim = datetime.now(timezone.utc)
        registro["fim_utc"] = fim.isoformat()
        registro["duracao_segundos"] = round((fim - inicio).total_seconds(), 4)
        print(f"Log SQL: {salvar_registro(registro, inicio)}")


if __name__ == "__main__":
    aprovado = main()
    print(f"RESULTADO_FINAL_SQL: {'APROVADO' if aprovado else 'REPROVADO'}")
    sys.exit(0 if aprovado else 1)
