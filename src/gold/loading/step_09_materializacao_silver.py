import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BRONZE_PROFILING_DIR = PROJECT_ROOT / "src" / "bronze" / "profiling"
if str(BRONZE_PROFILING_DIR) not in sys.path:
    sys.path.insert(0, str(BRONZE_PROFILING_DIR))

from step_06_validacao_tipos_dominios_regras import (
    BRONZE_PATH,
    COLUNAS_DATAS,
    COLUNAS_HORARIOS,
    COLUNAS_INTEIRAS_ESPERADAS,
    COLUNAS_MES_REFERENCIA,
    COLUNAS_NUMERICAS,
    calcular_sha256,
    carregar_entradas,
    converter_data,
    converter_mes_referencia,
    converter_serie_numerica,
    normalizar_texto,
)


STEP_08_PATH = (
    PROJECT_ROOT / "outputs" / "profiling" / "bronze_v3"
    / "step_08_plano_tratamento_normalizacao_silver.xlsx"
)
SILVER_DIR = PROJECT_ROOT / "data" / "silver" / "food_commerce"
SILVER_PATH = SILVER_DIR / "silver_transactions_v3.parquet"
REPORT_DIR = PROJECT_ROOT / "outputs" / "quality" / "silver_v3"
REPORT_PATH = REPORT_DIR / "step_09_materializacao_silver.xlsx"
MANIFEST_DIR = PROJECT_ROOT / "outputs" / "manifests" / "silver_v3"
MANIFEST_PATH = MANIFEST_DIR / "step_09_materializacao_silver.json"

COLUNAS_BOOLEANAS = ["Frete_Gratis", "Cupom_Utilizado", "Atraso_Entrega"]
MAPA_BOOLEANO = {"sim": "Sim", "nao": "Não"}
MAPA_ESTADOS_UF = {
    "acre": "AC", "alagoas": "AL", "amapa": "AP", "amazonas": "AM",
    "bahia": "BA", "ceara": "CE", "distrito federal": "DF",
    "espirito santo": "ES", "goias": "GO", "maranhao": "MA",
    "mato grosso": "MT", "mato grosso do sul": "MS",
    "minas gerais": "MG", "para": "PA", "paraiba": "PB",
    "parana": "PR", "pernambuco": "PE", "piaui": "PI",
    "rio de janeiro": "RJ", "rio grande do norte": "RN",
    "rio grande do sul": "RS", "rondonia": "RO", "roraima": "RR",
    "santa catarina": "SC", "sao paulo": "SP", "sergipe": "SE",
    "tocantins": "TO",
}
UFS_VALIDAS = set(MAPA_ESTADOS_UF.values())
DQ_PREFIX = "DQ_"
TOLERANCIA_NUMERICA = 1e-9


def sha256_arquivo(caminho):
    sha = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            sha.update(bloco)
    return sha.hexdigest().upper()


def ler_aba(aba):
    return pd.read_excel(STEP_08_PATH, sheet_name=aba)


def validar_plano(manifesto):
    if not STEP_08_PATH.is_file():
        raise FileNotFoundError(f"Plano obrigatório ausente: {STEP_08_PATH}")

    resumo = ler_aba("resumo_execucao")
    if resumo.empty or resumo.iloc[0].get("status") != "success":
        raise ValueError("A Etapa 8 não possui status success.")
    linha = resumo.iloc[0]

    if linha.get("sha256_bronze") != manifesto["bronze"]["sha256"]:
        raise ValueError("A Etapa 8 não corresponde à Bronze atual.")
    if int(linha.get("regras_tratamento", -1)) != 30:
        raise ValueError("A Etapa 8 não contém as 30 regras aprovadas.")
    if int(linha.get("linhas_excedentes_para_remocao", -1)) != 58:
        raise ValueError("A Etapa 8 não contém as 58 remoções aprovadas.")
    correcoes_esperadas = int(
        linha.get("correcoes_aplicaveis_apos_deduplicacao", -1)
    )
    if correcoes_esperadas != 261:
        raise ValueError("A Etapa 8 não contém as 261 correções aprovadas.")
    if int(linha.get("linhas_residuais_para_exclusao", -1)) != 3:
        raise ValueError("A Etapa 8 não contém as 3 exclusões residuais aprovadas.")
    if bool(linha.get("silver_materializada", True)):
        raise ValueError("O plano informa que a Silver já foi materializada.")

    controles = ler_aba("controles_auditoria")
    if controles["status"].eq("reprovado").any():
        raise ValueError("A Etapa 8 possui controle de auditoria reprovado.")

    correcoes = ler_aba("correcoes_propostas")
    if int(correcoes["aplicavel_apos_deduplicacao"].sum()) != correcoes_esperadas:
        raise ValueError("O detalhe de correções diverge do resumo da Etapa 8.")

    return {
        "resumo": linha,
        "deduplicacao": ler_aba("plano_deduplicacao"),
        "correcoes": correcoes,
        "pendencias": ler_aba("pendencias"),
        "tipagem": ler_aba("plano_tipagem"),
        "exclusoes_residuais": ler_aba("plano_exclusao_residual"),
        "catalogo_decisoes": ler_aba("catalogo_decisoes_nulos"),
    }


def limpar_texto_basico(serie):
    resultado = serie.astype("string").str.strip()
    return resultado.mask(resultado.eq(""), pd.NA)


def padronizar_variantes_textuais(serie):
    limpa = limpar_texto_basico(serie)
    base = pd.DataFrame({"valor": limpa})
    base["normalizado"] = base["valor"].map(normalizar_texto)
    informada = base.dropna(subset=["valor", "normalizado"])
    if informada.empty:
        return limpa

    frequencias = (
        informada.groupby(["normalizado", "valor"], dropna=False)
        .size().rename("frequencia").reset_index()
        .sort_values(["normalizado", "frequencia", "valor"], ascending=[True, False, True])
    )
    canonicos = frequencias.drop_duplicates("normalizado").set_index(
        "normalizado"
    )["valor"]
    return base["normalizado"].map(canonicos).astype("string")


def registrar_auditoria(registros, linha, campo, antes, depois, regra, acao):
    registros.append({
        "_source_row_number": int(linha),
        "campo": campo,
        "valor_antes": antes,
        "valor_depois": depois,
        "regra_id": regra,
        "acao": acao,
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
    })


def remover_duplicidades(dados, plano, auditoria):
    remover = plano.loc[
        plano["acao_silver"].eq("remover_excedente_duplicado"),
        "_source_row_number",
    ].astype(int)
    if remover.duplicated().any() or len(remover) != 58:
        raise ValueError("Plano de deduplicação inválido.")

    existentes = set(dados["_source_row_number"].astype(int))
    ausentes = sorted(set(remover) - existentes)
    if ausentes:
        raise ValueError(f"Linhas de deduplicação ausentes na Bronze: {ausentes}")

    for linha in remover:
        registrar_auditoria(
            auditoria, linha, "linha_completa", "presente", "removida",
            "TR017", "remover_excedente_duplicado",
        )
    return dados.loc[~dados["_source_row_number"].astype(int).isin(remover)].copy()


def excluir_pedidos_sem_evidencia_logistica(dados, plano, auditoria):
    fontes = plano["_source_row_number"].astype(int)
    if len(fontes) != 3 or fontes.duplicated().any():
        raise ValueError("Plano de exclusão logística deve conter três linhas únicas.")
    selecionados = dados[dados["_source_row_number"].astype(int).isin(fontes)].copy()
    if len(selecionados) != 3 or selecionados["Pedido_ID"].nunique() != 3:
        raise ValueError("As três linhas logísticas aprovadas não foram localizadas.")
    tamanhos = dados.groupby("Pedido_ID").size()
    if not selecionados["Pedido_ID"].map(tamanhos).eq(1).all():
        raise ValueError("Uma exclusão logística fragmentaria pedido com múltiplos itens.")
    for _, registro in selecionados.iterrows():
        registrar_auditoria(
            auditoria, registro["_source_row_number"], "linha_completa",
            "presente", "removida", "TR030",
            "excluir_pedido_sem_evidencia_logistica",
        )
    restante = dados.loc[
        ~dados["_source_row_number"].astype(int).isin(fontes)
    ].copy()
    return restante, selecionados


def aplicar_correcoes(dados, correcoes, auditoria):
    elegiveis = correcoes[correcoes["aplicavel_apos_deduplicacao"].eq(True)].copy()
    if len(elegiveis) != 261:
        raise ValueError("Quantidade de correções elegíveis diferente de 261.")
    if elegiveis["chave_auditoria"].duplicated().any():
        raise ValueError("Existem correções duplicadas por linha e campo.")

    # A Bronze possui colunas físicas do tipo string, enquanto algumas
    # correções são numéricas. O dtype object permite a atribuição temporária.
    # A tipagem definitiva é aplicada logo depois por aplicar_tipagem().
    for campo in elegiveis["campo"].dropna().unique():
        if campo in dados.columns:
            dados[campo] = dados[campo].astype("object")

    indice_linha = dados.reset_index().set_index("_source_row_number")["index"]
    for _, correcao in elegiveis.iterrows():
        linha = int(correcao["_source_row_number"])
        campo = correcao["campo"]
        if linha not in indice_linha.index:
            raise ValueError(f"Linha elegível não localizada após deduplicação: {linha}")
        if campo not in dados.columns:
            raise ValueError(f"Campo da correção não localizado: {campo}")
        indice = indice_linha.loc[linha]
        antes = dados.at[indice, campo]
        depois = correcao["valor_proposto"]
        dados.at[indice, campo] = depois
        registrar_auditoria(
            auditoria, linha, campo, antes, depois,
            correcao["regra_id"], "corrigir_deterministicamente",
        )
    return dados, elegiveis


def aplicar_tipagem(dados):
    falhas = []
    for coluna in COLUNAS_NUMERICAS:
        original_informado = limpar_texto_basico(dados[coluna]).notna()
        convertido = converter_serie_numerica(dados[coluna])
        falha = original_informado & convertido.isna()
        if falha.any():
            falhas.append({"coluna": coluna, "falhas": int(falha.sum())})
        if coluna in COLUNAS_INTEIRAS_ESPERADAS:
            fracionarios = convertido.dropna().mod(1).abs() > TOLERANCIA_NUMERICA
            if fracionarios.any():
                raise ValueError(f"Valores fracionários encontrados em {coluna}.")
            dados[coluna] = convertido.round().astype("Int64")
        else:
            dados[coluna] = convertido.astype("Float64")

    for coluna in COLUNAS_DATAS:
        informado = limpar_texto_basico(dados[coluna]).notna()
        convertido = converter_data(dados[coluna])
        if (informado & convertido.isna()).any():
            falhas.append({"coluna": coluna, "falhas": int((informado & convertido.isna()).sum())})
        dados[coluna] = convertido

    for coluna in COLUNAS_MES_REFERENCIA:
        informado = limpar_texto_basico(dados[coluna]).notna()
        convertido = converter_mes_referencia(dados[coluna])
        if (informado & convertido.isna()).any():
            falhas.append({"coluna": coluna, "falhas": int((informado & convertido.isna()).sum())})
        dados[coluna] = (convertido.dt.year * 100 + convertido.dt.month).astype("Int32")

    for coluna in COLUNAS_HORARIOS:
        texto = limpar_texto_basico(dados[coluna])
        convertido = pd.to_datetime(texto, format="%H:%M:%S", errors="coerce")
        falha = texto.notna() & convertido.isna()
        if falha.any():
            falhas.append({"coluna": coluna, "falhas": int(falha.sum())})
        dados[coluna] = convertido.dt.strftime("%H:%M:%S").astype("string")

    if falhas:
        raise ValueError(f"Falhas de tipagem na Silver: {falhas}")

    dados["Data_Hora_Compra"] = pd.to_datetime(
        dados["Data_Compra"].dt.strftime("%Y-%m-%d")
        + " " + dados["Horario_Compra"],
        errors="coerce",
    )
    if dados["Data_Hora_Compra"].isna().any():
        raise ValueError("Falha ao construir Data_Hora_Compra.")
    return dados


def aplicar_normalizacao_textual(dados, auditoria):
    excluidas = set(COLUNAS_NUMERICAS + COLUNAS_DATAS + COLUNAS_MES_REFERENCIA)
    excluidas.update(["_source_row_number", "Data_Hora_Compra"])
    colunas_texto = [
        coluna for coluna in dados.columns
        if coluna not in excluidas
        and not coluna.startswith(DQ_PREFIX)
        and (pd.api.types.is_object_dtype(dados[coluna])
             or pd.api.types.is_string_dtype(dados[coluna]))
    ]

    for coluna in colunas_texto:
        antes = dados[coluna].copy()
        if coluna in COLUNAS_BOOLEANAS:
            depois = limpar_texto_basico(antes).map(
                lambda valor: MAPA_BOOLEANO.get(normalizar_texto(valor), valor)
                if pd.notna(valor) else pd.NA
            ).astype("string")
        elif coluna == "Estado":
            limpa = limpar_texto_basico(antes)
            depois = limpa.map(
                lambda valor: MAPA_ESTADOS_UF.get(
                    normalizar_texto(valor), str(valor).strip().upper()
                ) if pd.notna(valor) else pd.NA
            ).astype("string")
        elif coluna in {"Pedido_ID", "Id_Item"}:
            depois = limpar_texto_basico(antes).str.upper()
        else:
            depois = padronizar_variantes_textuais(antes)

        alterada = antes.astype("string").fillna("<NULO>").ne(
            depois.astype("string").fillna("<NULO>")
        )
        for indice in dados.index[alterada]:
            registrar_auditoria(
                auditoria, dados.at[indice, "_source_row_number"], coluna,
                antes.at[indice], depois.at[indice], "TR016",
                "padronizar_sem_alterar_significado",
            )
        dados[coluna] = depois
    return dados


def adicionar_rastreabilidade(dados, auditoria, pendencias):
    regras_por_linha = {}
    for registro in auditoria:
        if registro["campo"] == "linha_completa":
            continue
        regras_por_linha.setdefault(registro["_source_row_number"], set()).add(
            registro["regra_id"]
        )

    pendentes = pendencias[pendencias["permanece_apos_deduplicacao"].eq(True)]
    pendencias_por_linha = {}
    for _, linha in pendentes.iterrows():
        numero = int(linha["_source_row_number"])
        pendencias_por_linha.setdefault(numero, []).append(
            f"{linha['campo']}:{linha['regra_id']}"
        )

    fonte = dados["_source_row_number"].astype(int)
    dados["_silver_regras_aplicadas"] = fonte.map(
        lambda numero: " | ".join(sorted(regras_por_linha.get(numero, set())))
        or pd.NA
    ).astype("string")
    dados["_silver_pendencias"] = fonte.map(
        lambda numero: " | ".join(sorted(pendencias_por_linha.get(numero, [])))
        or pd.NA
    ).astype("string")
    dados["_silver_status_qualidade"] = np.select(
        [dados["_silver_pendencias"].notna(), dados["_silver_regras_aplicadas"].notna()],
        ["pendente", "tratado"], default="sem_alteracao",
    )
    dados = dados.rename(columns={"_source_row_number": "_bronze_source_row_number"})
    return dados


def excluir_colunas_dq(dados):
    dq = [coluna for coluna in dados.columns if coluna.startswith(DQ_PREFIX)]
    return dados.drop(columns=dq), dq


def valores_equivalentes(observado, esperado):
    if pd.isna(observado) and pd.isna(esperado):
        return True
    try:
        return abs(float(observado) - float(esperado)) <= TOLERANCIA_NUMERICA
    except (TypeError, ValueError):
        return str(observado) == str(esperado)


def validar_resultado(bronze, silver, correcoes, dq_excluidas):
    controles = []
    def adicionar(nome, observado, esperado, critico=True):
        conforme = valores_equivalentes(observado, esperado)
        controles.append({
            "controle": nome, "observado": observado, "esperado": esperado,
            "status": "aprovado" if conforme else "reprovado",
            "critico": critico,
        })

    adicionar("linhas_bronze", len(bronze), 6556)
    adicionar("linhas_silver", len(silver), 6495)
    adicionar("linhas_removidas", len(bronze) - len(silver), 61)
    adicionar("clientes_apos_exclusoes_aprovadas", silver["Cliente_ID"].nunique(), 330)
    adicionar("pedidos_apos_exclusoes_aprovadas", silver["Pedido_ID"].nunique(), 2789)
    adicionar("itens_preservados", silver["Id_Item"].nunique(), bronze["Id_Item"].nunique())
    adicionar("correcoes_aplicadas", len(correcoes), 261)
    adicionar("colunas_dq_excluidas", len(dq_excluidas), 4)
    adicionar("data_hora_nula", silver["Data_Hora_Compra"].isna().sum(), 0)
    adicionar("source_row_duplicada", silver["_bronze_source_row_number"].duplicated().sum(), 0)
    estados_invalidos = int(
        (~silver["Estado"].isin(UFS_VALIDAS) & silver["Estado"].notna()).sum()
    )
    adicionar("estados_fora_dominio_uf", estados_invalidos, 0)

    quadro = pd.DataFrame(controles)
    if quadro.loc[quadro["critico"], "status"].eq("reprovado").any():
        erros = quadro[quadro["status"].eq("reprovado")].to_dict("records")
        raise ValueError(f"Reconciliação Silver reprovada: {erros}")
    return quadro


def criar_resumo_alteracoes(auditoria):
    quadro = pd.DataFrame(auditoria)
    return (
        quadro.groupby(["acao", "regra_id", "campo"], dropna=False)
        .size().rename("quantidade").reset_index()
        .sort_values(["acao", "regra_id", "campo"])
    )


def ajustar_planilhas(writer):
    preenchimento = PatternFill(fill_type="solid", fgColor="1F4E78")
    fonte = Font(color="FFFFFF", bold=True)
    for planilha in writer.book.worksheets:
        planilha.freeze_panes = "A2"
        planilha.auto_filter.ref = planilha.dimensions
        planilha.sheet_view.showGridLines = False
        for celula in planilha[1]:
            celula.fill = preenchimento
            celula.font = fonte
            celula.alignment = Alignment(
                horizontal="center", vertical="center", wrap_text=True
            )
        for coluna in planilha.columns:
            largura = min(max(
                len(str(celula.value)) if celula.value is not None else 0
                for celula in coluna
            ) + 2, 60)
            planilha.column_dimensions[coluna[0].column_letter].width = max(largura, 12)


def salvar_relatorio(planilhas):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    temporario = REPORT_PATH.with_suffix(".tmp.xlsx")
    with pd.ExcelWriter(temporario, engine="openpyxl") as writer:
        for nome, quadro in planilhas:
            quadro.to_excel(writer, sheet_name=nome[:31], index=False)
        ajustar_planilhas(writer)
    temporario.replace(REPORT_PATH)


def salvar_manifesto(manifesto):
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    temporario = MANIFEST_PATH.with_suffix(".tmp.json")
    with temporario.open("w", encoding="utf-8") as arquivo:
        json.dump(manifesto, arquivo, ensure_ascii=False, indent=2, default=str)
    temporario.replace(MANIFEST_PATH)


def executar():
    print("Iniciando materialização da Silver...")
    bronze, manifesto_bronze, _contrato = carregar_entradas()
    plano = validar_plano(manifesto_bronze)
    auditoria = []

    silver = remover_duplicidades(bronze, plano["deduplicacao"], auditoria)
    silver, correcoes = aplicar_correcoes(silver, plano["correcoes"], auditoria)
    silver = aplicar_tipagem(silver)
    silver = aplicar_normalizacao_textual(silver, auditoria)
    silver, dq_excluidas = excluir_colunas_dq(silver)
    silver, registros_excluidos = excluir_pedidos_sem_evidencia_logistica(
        silver, plano["exclusoes_residuais"], auditoria
    )
    silver = adicionar_rastreabilidade(silver, auditoria, plano["pendencias"])
    silver = silver.sort_values("_bronze_source_row_number").reset_index(drop=True)

    controles = validar_resultado(bronze, silver, correcoes, dq_excluidas)
    auditoria_df = pd.DataFrame(auditoria)
    resumo_alteracoes = criar_resumo_alteracoes(auditoria)

    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    silver_temporaria = SILVER_PATH.with_suffix(".tmp.parquet")
    silver.to_parquet(silver_temporaria, index=False, engine="pyarrow")
    silver_temporaria.replace(SILVER_PATH)

    resumo_execucao = pd.DataFrame([{
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "etapa": "09_materializacao_silver",
        "arquivo_bronze": BRONZE_PATH.name,
        "sha256_bronze": calcular_sha256(BRONZE_PATH),
        "arquivo_silver": SILVER_PATH.name,
        "sha256_silver": sha256_arquivo(SILVER_PATH),
        "linhas_bronze": len(bronze),
        "linhas_silver": len(silver),
        "linhas_removidas": len(bronze) - len(silver),
        "duplicidades_removidas": 58,
        "pedidos_logisticos_excluidos": len(registros_excluidos),
        "correcoes_deterministicas_aplicadas": len(correcoes),
        "pendencias_preservadas": int(plano["pendencias"]["permanece_apos_deduplicacao"].sum()),
        "colunas_dq_excluidas": len(dq_excluidas),
        "step_08_validado": True,
        "bronze_modificada": False,
        "status": "success",
    }])

    perfil_nulos = pd.DataFrame({
        "coluna": silver.columns,
        "nulos": [int(silver[coluna].isna().sum()) for coluna in silver.columns],
        "percentual_nulos": [round(silver[coluna].isna().mean() * 100, 4) for coluna in silver.columns],
        "dtype_silver": [str(silver[coluna].dtype) for coluna in silver.columns],
    })
    pendencias_ativas = plano["pendencias"][
        plano["pendencias"]["permanece_apos_deduplicacao"].eq(True)
    ].copy()

    salvar_relatorio([
        ("resumo_execucao", resumo_execucao),
        ("controles_reconciliacao", controles),
        ("resumo_alteracoes", resumo_alteracoes),
        ("auditoria_alteracoes", auditoria_df),
        ("catalogo_decisoes_nulos", plano["catalogo_decisoes"]),
        ("registros_excluidos", registros_excluidos),
        ("pendencias_preservadas", pendencias_ativas),
        ("perfil_nulos_silver", perfil_nulos),
        ("amostra_silver", silver.head(200)),
    ])

    manifesto = {
        "status": "success",
        "executado_em_utc": resumo_execucao.iloc[0]["executado_em_utc"],
        "pipeline_step": "09_materializacao_silver",
        "source": {
            "path": str(BRONZE_PATH.relative_to(PROJECT_ROOT)),
            "sha256": calcular_sha256(BRONZE_PATH),
            "rows": len(bronze),
        },
        "silver": {
            "path": str(SILVER_PATH.relative_to(PROJECT_ROOT)),
            "sha256": sha256_arquivo(SILVER_PATH),
            "rows": len(silver),
            "columns": len(silver.columns),
            "schema": {coluna: str(tipo) for coluna, tipo in silver.dtypes.items()},
        },
        "quality": {
            "rows_removed_total": len(bronze) - len(silver),
            "exact_duplicate_rows_removed": 58,
            "logistics_orders_removed": len(registros_excluidos),
            "deterministic_corrections_applied": len(correcoes),
            "pending_field_occurrences_preserved": int(
                plano["pendencias"]["permanece_apos_deduplicacao"].sum()
            ),
            "dq_columns_excluded": dq_excluidas,
        },
    }
    salvar_manifesto(manifesto)

    print(f"[OK] Linhas Bronze: {len(bronze)}")
    print(f"[OK] Linhas Silver: {len(silver)}")
    print(f"[OK] Duplicidades removidas: {len(bronze) - len(silver)}")
    print(f"[OK] Correções determinísticas aplicadas: {len(correcoes)}")
    print(f"[OK] Parquet Silver: {SILVER_PATH}")
    print(f"[OK] Relatório: {REPORT_PATH}")
    print(f"[OK] Manifesto: {MANIFEST_PATH}")
    print("RESULTADO_FINAL: APROVADO")
    return True


if __name__ == "__main__":
    try:
        sys.exit(0 if executar() else 1)
    except Exception as erro:
        print("RESULTADO_FINAL: REPROVADO")
        print(f"ERRO: {type(erro).__name__}: {erro}")
        sys.exit(1)
