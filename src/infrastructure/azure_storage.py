"""Publicacao idempotente dos artefatos da pipeline no ADLS Gen2."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from azure.identity import DefaultAzureCredential
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)
from azure.storage.blob import BlobServiceClient, ContentSettings


STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT", "stcustomeranalyticsgb01")
CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER", "customer-analytics")
ACCOUNT_URL = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net"


def calcular_sha256(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest().upper()


def _content_type(caminho: Path) -> str:
    tipos_especificos = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".parquet": "application/vnd.apache.parquet",
        ".py": "text/x-python",
        ".sql": "application/sql",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    return tipos_especificos.get(
        caminho.suffix.lower(),
        mimetypes.guess_type(caminho.name)[0] or "application/octet-stream",
    )


def destino_azure(caminho: Path, project_root: Path) -> str:
    relativo = caminho.resolve().relative_to(project_root.resolve())
    partes = relativo.parts

    if partes[:2] == ("data", "bronze"):
        restante = Path(*partes[2:]).as_posix()
        return f"01_bronze/customer_analytics/bronze_v3/current/{restante}"
    if partes[:2] == ("data", "silver"):
        restante = Path(*partes[2:]).as_posix()
        return f"02_silver/customer_analytics/silver_v3/current/{restante}"
    if partes[:2] == ("data", "gold"):
        restante = Path(*partes[2:]).as_posix()
        return f"03_gold/customer_analytics/gold_v3/current/{restante}"
    if partes and partes[0] == "outputs":
        restante = Path(*partes[1:]).as_posix()
        return f"04_exports/customer_analytics/{restante}"

    raise ValueError(f"Artefato fora das pastas publicaveis: {relativo}")


class PublicadorAzure:
    def __init__(self) -> None:
        self.credential = DefaultAzureCredential(
            exclude_interactive_browser_credential=False
        )
        self.service = BlobServiceClient(
            account_url=ACCOUNT_URL,
            credential=self.credential,
        )
        self.container = self.service.get_container_client(CONTAINER_NAME)

    def testar_conexao(self) -> dict:
        """Valida autenticação, existência do container e permissão de leitura."""
        try:
            propriedades = self.container.get_container_properties()
            return {
                "conectado": True,
                "storage_account": STORAGE_ACCOUNT,
                "container": CONTAINER_NAME,
                "ultima_modificacao_utc": propriedades.last_modified.isoformat(),
            }
        except ClientAuthenticationError as erro:
            raise RuntimeError(
                "Falha de autenticação no Azure. Execute 'az login' e tente novamente."
            ) from erro
        except ResourceNotFoundError as erro:
            raise RuntimeError(
                f"O container '{CONTAINER_NAME}' não foi encontrado na conta "
                f"'{STORAGE_ACCOUNT}'."
            ) from erro
        except HttpResponseError as erro:
            if erro.status_code == 403:
                raise PermissionError(
                    "Acesso negado. Confirme a função 'Storage Blob Data Contributor' "
                    "na conta ou no container."
                ) from erro
            raise RuntimeError(f"Erro ao acessar o Azure: {erro.message}") from erro

    def listar_arquivos(
        self,
        prefixo: str | None = None,
        limite: int | None = None,
    ) -> list[dict]:
        """Lista blobs para diagnóstico sem baixar nem modificar arquivos."""
        arquivos: list[dict] = []
        for item in self.container.list_blobs(name_starts_with=prefixo):
            arquivos.append(
                {
                    "nome": item.name,
                    "tamanho_bytes": item.size,
                    "ultima_modificacao_utc": (
                        item.last_modified.isoformat() if item.last_modified else None
                    ),
                    "content_type": (
                        item.content_settings.content_type
                        if item.content_settings
                        else None
                    ),
                }
            )
            if limite is not None and len(arquivos) >= limite:
                break
        return arquivos

    def publicar_arquivo(
        self,
        caminho: Path,
        destino: str,
        run_id: str,
        etapa: int | str,
    ) -> dict:
        caminho = caminho.resolve()
        sha256 = calcular_sha256(caminho)
        blob = self.container.get_blob_client(destino)

        remoto_igual = False
        try:
            propriedades = blob.get_blob_properties()
            remoto_igual = propriedades.metadata.get("sha256") == sha256
        except ResourceNotFoundError:
            pass

        registro = {
            "arquivo_local": str(caminho),
            "destino_azure": destino,
            "sha256": sha256,
            "tamanho_bytes": caminho.stat().st_size,
            "run_id": run_id,
            "etapa": etapa,
        }

        if remoto_igual:
            registro["acao"] = "ignorado_conteudo_identico"
            return registro

        with caminho.open("rb") as dados:
            blob.upload_blob(
                dados,
                overwrite=True,
                metadata={
                    "sha256": sha256,
                    "run_id": run_id,
                    "etapa": str(etapa),
                    "uploaded_utc": datetime.now(timezone.utc).isoformat(),
                },
                content_settings=ContentSettings(content_type=_content_type(caminho)),
            )

        registro["acao"] = "enviado_substituindo_current"
        return registro


def localizar_artefatos_modificados(
    project_root: Path,
    inicio_timestamp: float,
) -> Iterable[Path]:
    raizes = [project_root / "data", project_root / "outputs"]
    encontrados: set[Path] = set()

    for raiz in raizes:
        if not raiz.is_dir():
            continue
        for extensao in (
            "*.docx",
            "*.json",
            "*.md",
            "*.parquet",
            "*.pdf",
            "*.txt",
            "*.xlsx",
        ):
            for caminho in raiz.rglob(extensao):
                if caminho.name.startswith("~$") or ".tmp." in caminho.name:
                    continue
                if caminho.stat().st_mtime >= inicio_timestamp - 1:
                    encontrados.add(caminho.resolve())

    return sorted(encontrados)


def publicar_artefatos_modificados(
    project_root: Path,
    inicio_timestamp: float,
    run_id: str,
    etapa: int,
) -> list[dict]:
    artefatos = localizar_artefatos_modificados(project_root, inicio_timestamp)
    if not artefatos:
        return []

    publicador = PublicadorAzure()
    return [
        publicador.publicar_arquivo(
            caminho=arquivo,
            destino=destino_azure(arquivo, project_root),
            run_id=run_id,
            etapa=etapa,
        )
        for arquivo in artefatos
    ]


def main() -> None:
    """Teste seguro de acesso quando este módulo for executado diretamente."""
    publicador = PublicadorAzure()
    resultado = {
        "conexao": publicador.testar_conexao(),
        "amostra_arquivos": publicador.listar_arquivos(limite=20),
    }
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()