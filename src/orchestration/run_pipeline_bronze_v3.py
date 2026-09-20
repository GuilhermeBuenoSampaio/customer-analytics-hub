import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

INFRASTRUCTURE_DIR = PROJECT_ROOT / "src" / "infrastructure"
if str(INFRASTRUCTURE_DIR) not in sys.path:
    sys.path.insert(0, str(INFRASTRUCTURE_DIR))

from azure_storage import PublicadorAzure, publicar_artefatos_modificados

OUTPUT_LOG_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "logs"
    / "pipeline_bronze_v3"
)

ETAPAS = [
    {
        "numero": 1,
        "nome": "Validação do contrato da fonte",
        "script": (
            PROJECT_ROOT
            / "src"
            / "ingestion"
            / "step_01_validacao_contrato_fonte.py"
        ),
    },
    {
        "numero": 2,
        "nome": "Materialização da Bronze",
        "script": (
            PROJECT_ROOT
            / "src"
            / "ingestion"
            / "step_02_materializacao_bronze.py"
        ),
    },
    {
        "numero": 3,
        "nome": "Profiling estrutural da Bronze",
        "script": (
            PROJECT_ROOT
            / "src"
            / "bronze"
            / "profiling"
            / "step_03_profiling_estrutural.py"
        ),
    },
    {
        "numero": 4,
        "nome": "Análise de granularidade e chaves",
        "script": (
            PROJECT_ROOT
            / "src"
            / "bronze"
            / "profiling"
            / "step_04_analise_granularidade_chaves.py"
        ),
    },
    {
        "numero": 5,
        "nome": "Investigação dos dados ausentes",
        "script": (
            PROJECT_ROOT
            / "src"
            / "bronze"
            / "profiling"
            / "step_05_investigacao_dados_ausentes.py"
        ),
    },
    {
        "numero": 6,
        "nome": "Validação de tipos, domínios e regras",
        "script": (
            PROJECT_ROOT
            / "src"
            / "bronze"
            / "profiling"
            / "step_06_validacao_tipos_dominios_regras.py"
        ),
    },
    {
        "numero": 7,
        "nome": "Investigação contextual das inconsistências",
        "script": (
            PROJECT_ROOT
            / "src"
            / "bronze"
            / "profiling"
            / "step_07_investigacao_contextual_inconsistencias.py"
        ),
    },
    {
        "numero": 8,
        "nome": "Plano de tratamento e normalização da Silver",
        "script": (
            PROJECT_ROOT
            / "src"
            / "bronze"
            / "profiling"
            / "step_08_plano_tratamento_normalizacao_silver.py"
        ),
    },
    {
        "numero": 9,
        "nome": "Materialização e reconciliação da Silver",
        "script": (
            PROJECT_ROOT
            / "src"
            / "silver"
            / "transformation"
            / "step_09_materializacao_silver.py"
        ),
    },
    {
        "numero": 10,
        "nome": "Validação integral da qualidade da Silver",
        "script": (
            PROJECT_ROOT
            / "src"
            / "silver"
            / "quality"
            / "step_10_validacao_qualidade_silver.py"
        ),
    },
    {
        "numero": 11,
        "nome": "Especificação do modelo dimensional Gold",
        "script": (
            PROJECT_ROOT
            / "src"
            / "gold"
            / "modeling"
            / "step_11_especificacao_modelo_dimensional.py"
        ),
    },
    {
        "numero": 12,
        "nome": "Materialização do modelo dimensional Gold",
        "script": (
            PROJECT_ROOT
            / "src"
            / "gold"
            / "transformation"
            / "step_12_materializacao_modelo_dimensional_gold.py"
        ),
    },
    {
        "numero": 13,
        "nome": "Carga Gold no SQL Server",
        "script": PROJECT_ROOT / "src" / "gold" / "loading" / "step_13_carga_gold_sql_server.py",
        "enabled_env": "ENABLE_SQL_SERVER_LOAD",
    },
    {
        "numero": 14,
        "nome": "Execução sequencial das análises SQL",
        "script": PROJECT_ROOT / "src" / "sql" / "execution" / "run_sql_pipeline.py",
        "enabled_env": "ENABLE_SQL_PIPELINE",
    },
]


def flag_ativa(nome: str, padrao: bool = False) -> bool:
    valor = os.getenv(nome)
    if valor is None:
        return padrao
    return valor.strip().casefold() in {"1", "true", "yes", "sim", "on"}


def etapa_habilitada(etapa: dict) -> bool:
    variavel = etapa.get("enabled_env")
    return True if not variavel else flag_ativa(variavel)


def agora_utc():
    return datetime.now(timezone.utc)


def formatar_duracao(segundos):
    if segundos < 60:
        return f"{segundos:.2f} segundos"

    minutos, segundos_restantes = divmod(segundos, 60)

    return (
        f"{int(minutos)} minuto(s) e "
        f"{segundos_restantes:.2f} segundo(s)"
    )


def validar_configuracao():
    if not PROJECT_ROOT.is_dir():
        raise FileNotFoundError(
            f"Raiz do projeto não encontrada: {PROJECT_ROOT}"
        )

    numeros = [etapa["numero"] for etapa in ETAPAS]

    if len(numeros) != len(set(numeros)):
        raise ValueError(
            "Existem números de etapa duplicados no orquestrador."
        )

    if numeros != sorted(numeros):
        raise ValueError(
            "As etapas não estão configuradas em ordem crescente."
        )

    scripts_ausentes = [
        etapa["script"]
        for etapa in ETAPAS
        if not etapa["script"].is_file()
    ]

    if scripts_ausentes:
        raise FileNotFoundError(
            "Scripts obrigatórios ausentes:\n"
            + "\n".join(
                str(script)
                for script in scripts_ausentes
            )
        )

    scripts_fora_projeto = []

    for etapa in ETAPAS:
        try:
            etapa["script"].resolve().relative_to(
                PROJECT_ROOT.resolve()
            )
        except ValueError:
            scripts_fora_projeto.append(etapa["script"])

    if scripts_fora_projeto:
        raise ValueError(
            "Existem scripts configurados fora do projeto:\n"
            + "\n".join(
                str(script)
                for script in scripts_fora_projeto
            )
        )


def criar_registro_pipeline(inicio_pipeline, run_id):
    ambiente_virtual_ativo = (
        getattr(sys, "base_prefix", sys.prefix) != sys.prefix
    )

    return {
        "pipeline": "customer_analytics_bronze_v3",
        "run_id": run_id,
        "status": "running",
        "inicio_utc": inicio_pipeline.isoformat(),
        "fim_utc": None,
        "duracao_segundos": None,
        "project_root": str(PROJECT_ROOT),
        "python_executable": sys.executable,
        "ambiente_virtual_ativo": ambiente_virtual_ativo,
        "total_etapas_configuradas": len(ETAPAS),
        "total_etapas_concluidas": 0,
        "etapa_reprovada": None,
        "erro": None,
        "publicacoes_azure": [],
        "etapas": [],
    }


def executar_etapa(etapa, run_id):
    print("\n" + "=" * 70)
    print(
        f"ETAPA {etapa['numero']:02d}: "
        f"{etapa['nome']}"
    )
    print(f"Script: {etapa['script'].name}")
    print("=" * 70)

    inicio = agora_utc()

    try:
        resultado = subprocess.run(
            [
                sys.executable,
                str(etapa["script"]),
            ],
            cwd=PROJECT_ROOT,
            check=False,
        )
        codigo_saida = resultado.returncode
        erro_execucao = None
        publicacoes_azure = []
        documentacao = None

        if codigo_saida == 0 and flag_ativa("ENABLE_AZURE_PUBLISH"):
            publicacoes_azure = publicar_artefatos_modificados(
                project_root=PROJECT_ROOT,
                inicio_timestamp=inicio.timestamp(),
                run_id=run_id,
                etapa=etapa["numero"],
            )

        if codigo_saida == 0 and flag_ativa("REQUIRE_DOCUMENTATION", True):
            agente_documentacao = (
                PROJECT_ROOT / "src" / "documentation" / "documentation_agent.py"
            )
            resultado_doc = subprocess.run(
                [
                    sys.executable,
                    str(agente_documentacao),
                    "--stage",
                    str(etapa["numero"]),
                    "--run-id",
                    run_id,
                    "--technical-status",
                    "success",
                ],
                cwd=PROJECT_ROOT,
                check=False,
            )
            documentacao = {
                "obrigatoria": True,
                "codigo_saida": resultado_doc.returncode,
                "status": "success" if resultado_doc.returncode == 0 else "failed",
            }
            if resultado_doc.returncode != 0:
                codigo_saida = -3
                erro_execucao = "Falha no gate obrigatório de documentação."

    except OSError as erro:
        codigo_saida = -1
        erro_execucao = (
            f"{type(erro).__name__}: {erro}"
        )
        publicacoes_azure = []
        documentacao = None

    except Exception as erro:
        codigo_saida = -2
        erro_execucao = (
            "Falha na publicação Azure: "
            f"{type(erro).__name__}: {erro}"
        )
        publicacoes_azure = []
        documentacao = None

    fim = agora_utc()
    duracao = (fim - inicio).total_seconds()
    aprovada = codigo_saida == 0

    registro = {
        "numero": etapa["numero"],
        "nome": etapa["nome"],
        "script": str(
            etapa["script"].relative_to(PROJECT_ROOT)
        ),
        "inicio_utc": inicio.isoformat(),
        "fim_utc": fim.isoformat(),
        "duracao_segundos": round(duracao, 4),
        "codigo_saida": codigo_saida,
        "status": "success" if aprovada else "failed",
        "erro_execucao": erro_execucao,
        "publicacoes_azure": publicacoes_azure,
        "documentacao": documentacao,
    }

    if aprovada:
        print(
            f"\nETAPA {etapa['numero']:02d}: APROVADA"
        )
    else:
        print(
            f"\nETAPA {etapa['numero']:02d}: REPROVADA"
        )

        if erro_execucao:
            print(f"Erro de execução: {erro_execucao}")

    print(f"Duração: {formatar_duracao(duracao)}")

    return registro


def salvar_log(registro_pipeline, inicio_pipeline):
    OUTPUT_LOG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    identificador = inicio_pipeline.strftime(
        "%Y%m%dT%H%M%S_%fZ"
    )

    caminho_log = (
        OUTPUT_LOG_DIR
        / f"pipeline_bronze_v3_{identificador}.json"
    )
    caminho_temporario = caminho_log.with_suffix(
        ".tmp.json"
    )

    with caminho_temporario.open(
        mode="w",
        encoding="utf-8",
    ) as arquivo:
        json.dump(
            registro_pipeline,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )

    caminho_temporario.replace(caminho_log)

    return caminho_log


def imprimir_resumo(registro_pipeline):
    print("\n" + "=" * 70)
    print("RESUMO DA PIPELINE")
    print("=" * 70)

    for etapa in registro_pipeline["etapas"]:
        situacao = (
            "APROVADA"
            if etapa["status"] == "success"
            else "REPROVADA"
        )

        print(
            f"Etapa {etapa['numero']:02d} | "
            f"{situacao:<9} | "
            f"{etapa['duracao_segundos']:.2f}s | "
            f"código {etapa['codigo_saida']} | "
            f"{etapa['nome']}"
        )

    etapas_nao_executadas = [
        etapa
        for etapa in ETAPAS
        if etapa["numero"]
        not in {
            executada["numero"]
            for executada in registro_pipeline["etapas"]
        }
    ]

    for etapa in etapas_nao_executadas:
        print(
            f"Etapa {etapa['numero']:02d} | "
            f"NÃO EXECUTADA | {etapa['nome']}"
        )

    print("=" * 70)


def executar_pipeline():
    inicio_pipeline = agora_utc()
    run_id = inicio_pipeline.strftime("%Y%m%dT%H%M%S_%fZ")
    registro_pipeline = criar_registro_pipeline(
        inicio_pipeline,
        run_id,
    )

    print("INICIANDO CUSTOMER ANALYTICS PIPELINE")
    print(
        "Executado em UTC: "
        f"{inicio_pipeline.isoformat()}"
    )
    print(f"Python: {sys.executable}")
    print(f"Raiz do projeto: {PROJECT_ROOT}")

    if not registro_pipeline["ambiente_virtual_ativo"]:
        print(
            "[AVISO] O interpretador atual não parece pertencer "
            "a um ambiente virtual."
        )

    try:
        validar_configuracao()
        print("[OK] Configuração da pipeline validada")

        for etapa in ETAPAS:
            if not etapa_habilitada(etapa):
                print(
                    f"[IGNORADA] Etapa {etapa['numero']:02d}: {etapa['nome']} "
                    f"({etapa['enabled_env']}=false)"
                )
                continue
            registro_etapa = executar_etapa(etapa, run_id)
            registro_pipeline["etapas"].append(
                registro_etapa
            )
            registro_pipeline["publicacoes_azure"].extend(
                registro_etapa["publicacoes_azure"]
            )

            if registro_etapa["status"] != "success":
                registro_pipeline["etapa_reprovada"] = (
                    etapa["numero"]
                )
                raise RuntimeError(
                    "Pipeline interrompida porque uma etapa "
                    "obrigatória foi reprovada."
                )

        registro_pipeline["status"] = "success"

    except KeyboardInterrupt:
        registro_pipeline["status"] = "interrupted"
        registro_pipeline["erro"] = (
            "KeyboardInterrupt: execução interrompida pelo usuário."
        )

    except Exception as erro:
        registro_pipeline["status"] = "failed"
        registro_pipeline["erro"] = (
            f"{type(erro).__name__}: {erro}"
        )

    finally:
        fim_pipeline = agora_utc()
        duracao_pipeline = (
            fim_pipeline - inicio_pipeline
        ).total_seconds()

        registro_pipeline["fim_utc"] = (
            fim_pipeline.isoformat()
        )
        registro_pipeline["duracao_segundos"] = round(
            duracao_pipeline,
            4,
        )
        registro_pipeline["total_etapas_concluidas"] = sum(
            etapa["status"] == "success"
            for etapa in registro_pipeline["etapas"]
        )

        caminho_log = salvar_log(
            registro_pipeline,
            inicio_pipeline,
        )

        if flag_ativa("ENABLE_AZURE_PUBLISH"):
            try:
                PublicadorAzure().publicar_arquivo(
                    caminho=caminho_log,
                    destino=(
                        "metadata/customer_analytics/pipeline_runs/"
                        f"{caminho_log.name}"
                    ),
                    run_id=run_id,
                    etapa="pipeline",
                )
                print("[OK] Log da execução publicado no Azure")
            except Exception as erro_upload_log:
                print(
                    "[AVISO] Log local preservado, mas o envio ao Azure falhou: "
                    f"{type(erro_upload_log).__name__}: {erro_upload_log}"
                )
        else:
            print("[INFO] Publicação Azure desabilitada por configuração.")

        imprimir_resumo(registro_pipeline)

        print(
            "Duração total: "
            f"{formatar_duracao(duracao_pipeline)}"
        )
        print(f"Log da execução: {caminho_log}")

    if registro_pipeline["status"] == "success":
        print("RESULTADO_FINAL_PIPELINE: APROVADO")
        print(
            "Etapas concluídas: "
            f"{registro_pipeline['total_etapas_concluidas']}"
        )
        return True

    print("RESULTADO_FINAL_PIPELINE: REPROVADO")

    if registro_pipeline["erro"]:
        print(f"ERRO: {registro_pipeline['erro']}")

    return False


if __name__ == "__main__":
    sucesso = executar_pipeline()
    sys.exit(0 if sucesso else 1)
