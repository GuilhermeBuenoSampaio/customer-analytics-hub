"""Agente local e gratuito de documentação e rastreabilidade do projeto."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = PROJECT_ROOT / "docs"
STAGES_DIR = DOCS_ROOT / "traceability" / "stages"
INDEX_PATH = DOCS_ROOT / "traceability" / "index.json"
TECHNICAL_REPORT = DOCS_ROOT / "reports" / "technical_report.md"
EXECUTIVE_REPORT = DOCS_ROOT / "reports" / "executive_report.md"
load_dotenv(PROJECT_ROOT / ".env")

STAGES = {
    1: ("Validação do contrato da fonte", "src/ingestion/step_01_validacao_contrato_fonte.py", ["outputs/profiling/bronze_v3/step_01_*"]),
    2: ("Materialização da Bronze", "src/ingestion/step_02_materializacao_bronze.py", ["data/bronze/**/*.parquet", "outputs/manifests/bronze_v3/step_02_*"]),
    3: ("Profiling estrutural da Bronze", "src/bronze/profiling/step_03_profiling_estrutural.py", ["outputs/profiling/bronze_v3/step_03_*"]),
    4: ("Análise de granularidade e chaves", "src/bronze/profiling/step_04_analise_granularidade_chaves.py", ["outputs/profiling/bronze_v3/step_04_*"]),
    5: ("Investigação dos dados ausentes", "src/bronze/profiling/step_05_investigacao_dados_ausentes.py", ["outputs/profiling/bronze_v3/step_05_*"]),
    6: ("Validação de tipos, domínios e regras", "src/bronze/profiling/step_06_validacao_tipos_dominios_regras.py", ["outputs/profiling/bronze_v3/step_06_*"]),
    7: ("Investigação contextual das inconsistências", "src/bronze/profiling/step_07_investigacao_contextual_inconsistencias.py", ["outputs/profiling/bronze_v3/step_07_*"]),
    8: ("Plano de tratamento e normalização", "src/bronze/profiling/step_08_plano_tratamento_normalizacao_silver.py", ["outputs/profiling/bronze_v3/step_08_*"]),
    9: ("Materialização e reconciliação da Silver", "src/silver/transformation/step_09_materializacao_silver.py", ["data/silver/**/*.parquet", "outputs/manifests/silver_v3/step_09_*", "outputs/quality/silver_v3/step_09_*"]),
    10: ("Validação integral da qualidade da Silver", "src/silver/quality/step_10_validacao_qualidade_silver.py", ["outputs/quality/silver_v3/step_10_*.xlsx"]),
    11: ("Especificação do modelo dimensional Gold", "src/gold/modeling/step_11_especificacao_modelo_dimensional.py", ["outputs/modeling/gold_v3/step_11_*", "outputs/manifests/gold_v3/step_11_*"]),
    12: ("Materialização do modelo dimensional Gold", "src/gold/transformation/step_12_materializacao_modelo_dimensional_gold.py", ["data/gold/**/*.parquet", "outputs/quality/gold_v3/step_12_*", "outputs/manifests/gold_v3/step_12_*"]),
    13: ("Carga Gold no SQL Server", "src/gold/loading/step_13_carga_gold_sql_server.py", ["outputs/logs/sql_load/*.json"]),
    14: ("Execução sequencial das análises SQL", "src/sql/execution/run_sql_pipeline.py", ["outputs/logs/sql_pipeline/*.json"]),
}

STAGE_DETAILS = {
    1: ("Compara arquivo, aba, colunas e contrato esperado antes da ingestão.", "Impedir que uma fonte divergente contamine as camadas seguintes."),
    2: ("Extrai a aba canônica e grava a Bronze em Parquet com manifesto.", "Preservar uma representação bruta, reproduzível e rastreável da entrada."),
    3: ("Calcula estrutura, tipos inferidos, cardinalidade e estatísticas iniciais.", "Conhecer a forma real dos dados antes de definir tratamentos."),
    4: ("Investiga granularidade, chaves candidatas, duplicidades e relações pedido-item.", "Evitar contagens duplicadas e definir corretamente fatos e dimensões."),
    5: ("Quantifica nulidade e avalia sua concentração por coluna e unidade de análise.", "Separar ausência legítima de falha de qualidade e evitar imputação sem evidência."),
    6: ("Valida tipos, domínios, limites e coerência entre campos relacionados.", "Transformar regras de negócio em controles verificáveis."),
    7: ("Analisa inconsistências que dependem de contexto e combinações de atributos.", "Nem toda anomalia estatística representa erro; o contexto orienta a decisão."),
    8: ("Consolida problema, tratamento, justificativa e efeito esperado na Silver.", "Separar investigação de correção e tornar cada transformação auditável."),
    9: ("Aplica tratamentos aprovados, grava a Silver e reconcilia entrada e saída.", "Produzir uma base limpa sem perder rastreabilidade quantitativa."),
    10: ("Executa testes de completude, validade, consistência, unicidade e integridade.", "Impedir que uma Silver reprovada alimente o modelo analítico."),
    11: ("Especifica 10 dimensões, 4 fatos, chaves, tipos e granularidades.", "Criar uma camada semântica única para todas as áreas do negócio."),
    12: ("Materializa as 14 tabelas Gold e valida contratos e relacionamentos.", "Disponibilizar estruturas analíticas consistentes e reutilizáveis."),
    13: ("Carrega a Gold no SQL Server, registra auditoria e reconcilia linhas e hashes.", "Garantir que o banco represente fielmente os Parquets aprovados."),
    14: ("Executa os arquivos SQL por pasta e nome, respeitando lotes GO e transações.", "Reproduzir a EDA e análises futuras na mesma ordem, com log de falhas."),
}


def sha256(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def evidencias(padroes: list[str]) -> list[Path]:
    encontrados: set[Path] = set()
    for padrao in padroes:
        encontrados.update(
            p for p in PROJECT_ROOT.glob(padrao)
            if p.is_file() and ".tmp." not in p.name and not p.name.startswith("~$")
        )
    return sorted(encontrados)


def slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = texto.casefold()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")


def carregar_indice() -> dict:
    if not INDEX_PATH.exists():
        return {"project": "customer-analytics-hub", "stages": {}}
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def salvar_indice(indice: dict) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8")


def enriquecimento_ollama(contexto: str) -> str | None:
    if os.getenv("DOCUMENTATION_PROVIDER", "deterministic").casefold() != "ollama":
        return None
    endpoint = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/") + "/api/generate"
    corpo = json.dumps({
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        "stream": False,
        "prompt": (
            "Produza em português um resumo técnico factual, sem inventar métricas, "
            "com no máximo 120 palavras, usando somente este contexto:\n" + contexto
        ),
    }).encode("utf-8")
    try:
        requisicao = urllib.request.Request(endpoint, data=corpo, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(requisicao, timeout=60) as resposta:
            return json.loads(resposta.read().decode("utf-8")).get("response")
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None


def documentar_etapa(numero: int, run_id: str | None, status_tecnico: str) -> Path:
    nome, script_relativo, padroes = STAGES[numero]
    script = PROJECT_ROOT / script_relativo
    if not script.is_file():
        raise FileNotFoundError(f"Script da etapa {numero} não encontrado: {script}")
    arquivos = evidencias(padroes)
    if run_id is None and not arquivos:
        status_tecnico = "unverified"
    agora = datetime.now(timezone.utc).isoformat()
    status = "approved" if status_tecnico == "success" and arquivos else "pending_evidence"
    contexto = f"Etapa {numero}: {nome}. Script: {script_relativo}. Evidências: {len(arquivos)}. Status: {status}."
    resumo_ia = enriquecimento_ollama(contexto)
    metodo, justificativa = STAGE_DETAILS[numero]

    linhas_evidencia = [
        f"- `{arquivo.relative_to(PROJECT_ROOT).as_posix()}` — SHA-256 `{sha256(arquivo)}`"
        for arquivo in arquivos
    ] or ["- Nenhuma evidência material localizada; etapa mantida pendente."]

    conteudo = f"""# Etapa {numero:02d} — {nome}

## Objetivo

Registrar a execução, as evidências e o critério de conclusão da etapa **{nome}**.

## Implementação

- Script: `{script_relativo}`
- SHA-256 do script: `{sha256(script)}`
- Run ID: `{run_id or 'retroactive'}`
- Registro UTC: `{agora}`
- Status técnico informado: `{status_tecnico}`

### Como foi feito

{metodo}

### Por que foi necessário

{justificativa}

## Evidências

{chr(10).join(linhas_evidencia)}

## Validação e critério de aceite

A etapa somente é considerada concluída quando o script termina com código zero, existe ao menos uma evidência material e este documento é gerado com sucesso.

## Decisões e limitações

- A documentação foi produzida a partir de arquivos efetivamente presentes no projeto.
- Ausência de evidência não é convertida automaticamente em aprovação.
- Credenciais, dados sensíveis e conteúdo do arquivo `.env` não são registrados.
"""
    if resumo_ia:
        conteudo += f"\n## Síntese assistida por IA local\n\n{resumo_ia.strip()}\n"

    STAGES_DIR.mkdir(parents=True, exist_ok=True)
    destino = STAGES_DIR / f"step_{numero:02d}_{slug(nome)}.md"
    destino.write_text(conteudo, encoding="utf-8")

    indice = carregar_indice()
    indice["updated_utc"] = agora
    indice["stages"][str(numero)] = {
        "name": nome,
        "status": status,
        "technical_status": status_tecnico,
        "run_id": run_id or "retroactive",
        "document": destino.relative_to(PROJECT_ROOT).as_posix(),
        "evidence_count": len(arquivos),
        "updated_utc": agora,
    }
    salvar_indice(indice)
    atualizar_relatorios(indice)
    return destino


def atualizar_relatorios(indice: dict) -> None:
    DOCS_ROOT.joinpath("reports").mkdir(parents=True, exist_ok=True)
    etapas = sorted(indice["stages"].items(), key=lambda item: int(item[0]))
    linhas = [
        f"| {numero} | {dados['name']} | {dados['status']} | {dados['evidence_count']} |"
        for numero, dados in etapas
    ]
    TECHNICAL_REPORT.write_text(
        "# Relatório técnico progressivo\n\n"
        "Documento atualizado automaticamente a partir da rastreabilidade validada.\n\n"
        "| Etapa | Descrição | Status | Evidências |\n"
        "|---:|---|---|---:|\n" + "\n".join(linhas) +
        "\n\n## Regra de governança\n\n"
        "Nenhuma etapa é concluída sem execução técnica aprovada, evidência material e documentação.\n",
        encoding="utf-8",
    )
    aprovadas = [dados["name"] for _, dados in etapas if dados["status"] == "approved"]
    EXECUTIVE_REPORT.write_text(
        "# Relatório executivo\n\n"
        "## Situação atual\n\n"
        f"O Customer Analytics Hub possui {len(aprovadas)} etapa(s) tecnicamente aprovadas e documentadas.\n\n"
        "## Entregas aprovadas\n\n" +
        ("\n".join(f"- {nome}" for nome in aprovadas) if aprovadas else "- Nenhuma etapa aprovada até o momento.") +
        "\n\n## Observação\n\nSomente resultados aprovados entram neste resumo. Indicadores de negócio serão incluídos após validação analítica.\n",
        encoding="utf-8",
    )


def validar_documentacao(numero: int) -> bool:
    indice = carregar_indice()
    dados = indice.get("stages", {}).get(str(numero))
    if not dados or dados.get("status") != "approved":
        return False
    documento = PROJECT_ROOT / dados["document"]
    if not documento.is_file():
        return False
    texto = documento.read_text(encoding="utf-8")
    secoes = ["## Objetivo", "## Implementação", "## Evidências", "## Validação e critério de aceite"]
    return all(secao in texto for secao in secoes)


def main() -> int:
    parser = argparse.ArgumentParser()
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--stage", type=int, choices=sorted(STAGES))
    grupo.add_argument("--retroactive", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--technical-status", default="success", choices=["success", "failed"])
    args = parser.parse_args()

    numeros = sorted(STAGES) if args.retroactive else [args.stage]
    falhas = []
    for numero in numeros:
        destino = documentar_etapa(numero, args.run_id, args.technical_status)
        aprovado = validar_documentacao(numero)
        print(f"[DOC] Etapa {numero:02d}: {'APROVADA' if aprovado else 'PENDENTE'} - {destino}")
        if not aprovado:
            falhas.append(numero)
    return 1 if falhas and not args.retroactive else 0


if __name__ == "__main__":
    raise SystemExit(main())
