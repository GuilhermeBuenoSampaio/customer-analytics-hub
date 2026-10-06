"""Sincroniza os resultados comerciais aprovados com o Azure Blob Storage."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ARQUIVO_ATUAL = Path(__file__).resolve()
RAIZ_PROJETO = ARQUIVO_ATUAL.parents[3]

if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from src.infrastructure.azure_storage import PublicadorAzure  # noqa: E402


PASTA_PARQUET = RAIZ_PROJETO / "data" / "exports" / "commercial"
PASTA_MANIFESTOS = (
    RAIZ_PROJETO / "quality" / "commercial" / "exportacao_parquet"
)


def localizar_arquivos() -> list[tuple[Path, str, str]]:
    """Localiza Parquets e manifestos e define seus destinos no Azure."""
    arquivos: list[tuple[Path, str, str]] = []

    if not PASTA_PARQUET.is_dir():
        raise FileNotFoundError(f"Pasta de Parquets não encontrada: {PASTA_PARQUET}")

    parquets = sorted(PASTA_PARQUET.glob("*.parquet"))
    if not parquets:
        raise FileNotFoundError(f"Nenhum arquivo Parquet encontrado: {PASTA_PARQUET}")

    for caminho in parquets:
        destino = (
            "04_exports/customer_analytics/commercial/current/"
            f"{caminho.name}"
        )
        arquivos.append((caminho, destino, "resultado_comercial"))

    if not PASTA_MANIFESTOS.is_dir():
        raise FileNotFoundError(
            f"Pasta de manifestos não encontrada: {PASTA_MANIFESTOS}"
        )

    manifestos = sorted(PASTA_MANIFESTOS.glob("*.json"))
    if not manifestos:
        raise FileNotFoundError(
            f"Nenhum manifesto JSON encontrado: {PASTA_MANIFESTOS}"
        )

    for caminho in manifestos:
        destino = (
            "quality/customer_analytics/commercial/exportacao_parquet/"
            f"{caminho.name}"
        )
        arquivos.append((caminho, destino, "manifesto_qualidade"))

    return arquivos


def main() -> int:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    arquivos = localizar_arquivos()
    publicador = PublicadorAzure()

    print("=" * 72)
    print("SINCRONIZAÇÃO DOS RESULTADOS COMERCIAIS COM O AZURE")
    print("=" * 72)
    print(json.dumps(publicador.testar_conexao(), ensure_ascii=False, indent=2))
    print(f"Arquivos identificados: {len(arquivos)}")

    registros: list[dict] = []
    for caminho, destino, tipo in arquivos:
        registro = publicador.publicar_arquivo(
            caminho=caminho,
            destino=destino,
            run_id=run_id,
            etapa="AC01_EXPORTACAO_COMERCIAL",
        )
        registro["tipo_artefato"] = tipo
        registros.append(registro)
        print(f"[{registro['acao']}] {caminho.name} -> {destino}")

    total_enviados = sum(
        item["acao"] == "enviado_substituindo_current" for item in registros
    )
    total_ignorados = sum(
        item["acao"] == "ignorado_conteudo_identico" for item in registros
    )

    resumo = {
        "run_id": run_id,
        "status_final": "APROVADO",
        "arquivos_processados": len(registros),
        "arquivos_enviados": total_enviados,
        "arquivos_ignorados_por_conteudo_identico": total_ignorados,
    }

    print("=" * 72)
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    print("=" * 72)
    return 0


if __name__ == "__main__":
    try:
        codigo_saida = main()
    except Exception as erro:
        print("=" * 72)
        print("STATUS FINAL: REPROVADO")
        print(f"Erro: {erro}")
        print("=" * 72)
        codigo_saida = 1

    raise SystemExit(codigo_saida)
