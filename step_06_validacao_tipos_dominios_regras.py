# Versão corrigida após auditoria contextual da Etapa 6.
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill


PROJECT_ROOT = Path(__file__).resolve().parents[3]

BRONZE_PATH = (
    PROJECT_ROOT / "data" / "bronze" / "food_commerce"
    / "bronze_transactions_v3.parquet"
)
BRONZE_MANIFEST_PATH = (
    PROJECT_ROOT / "outputs" / "manifests" / "bronze_v3"
    / "step_02_materializacao_bronze.json"
)
CONTRACT_PATH = PROJECT_ROOT / "configs" / "source_contract_v3.json"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "profiling" / "bronze_v3"
OUTPUT_PATH = OUTPUT_DIR / "step_06_validacao_tipos_dominios_regras.xlsx"

DQ_PREFIX = "DQ_"
TECHNICAL_PREFIX = "_"
TOLERANCIA_MONETARIA = 0.01

COLUNAS_NUMERICAS = [
    "Idade", "Tempo_Experiencia_Anos", "Renda_Mensal_Cliente",
    "Intervalo_Medio_Compras_Dias", "Ticket_Medio_Cliente",
    "Quantidade", "Custo_Unitario", "Preco_Unitario_Lista",
    "Desconto_Percentual", "Valor_Compra", "Frete",
    "Prazo_Entrega_Prometido", "Prazo_Entrega_Real",
    "Avaliacao_Cliente", "Pontos_Fidelidade",
]
COLUNAS_INTEIRAS_ESPERADAS = {
    "Idade", "Tempo_Experiencia_Anos", "Quantidade",
    "Prazo_Entrega_Prometido", "Prazo_Entrega_Real",
    "Avaliacao_Cliente", "Pontos_Fidelidade",
}
COLUNAS_DATAS = ["Data_Compra"]
COLUNAS_MES_REFERENCIA = ["Mes_Ref"]
COLUNAS_HORARIOS = ["Horario_Compra"]

DOMINIOS_ESPERADOS = {
    "Ciclo_Vida_Cliente": {
        "ativo", "churn", "em risco", "fiel", "novo", "reativado"
    },
    "Frete_Gratis": {"sim", "nao"},
    "Cupom_Utilizado": {"sim", "nao"},
    "Atraso_Entrega": {"sim", "nao"},
}

NIVEL_VARIAVEL = {
    "Idade": "cliente", "Tempo_Experiencia_Anos": "cliente",
    "Renda_Mensal_Cliente": "cliente",
    "Intervalo_Medio_Compras_Dias": "cliente",
    "Ticket_Medio_Cliente": "cliente", "Pontos_Fidelidade": "cliente",
    "Frete": "pedido", "Prazo_Entrega_Prometido": "pedido",
    "Prazo_Entrega_Real": "pedido", "Custo_Unitario": "item_cadastral",
    "Preco_Unitario_Lista": "item_cadastral", "Quantidade": "item_pedido",
    "Valor_Compra": "item_pedido", "Desconto_Percentual": "dominio_discreto",
    "Avaliacao_Cliente": "dominio_discreto",
}


def calcular_sha256(caminho_arquivo):
    sha256 = hashlib.sha256()
    with caminho_arquivo.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            sha256.update(bloco)
    return sha256.hexdigest().upper()


def percentual(quantidade, total):
    return round(quantidade / total * 100, 4) if total else 0.0


def normalizar_texto(valor):
    if pd.isna(valor):
        return pd.NA
    texto = " ".join(str(valor).strip().casefold().split())
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c)
    )


def ausente(serie):
    texto = serie.astype("string")
    return texto.isna() | texto.str.strip().eq("")


def converter_numero(valor):
    if pd.isna(valor):
        return np.nan
    texto = str(valor).strip()
    if not texto:
        return np.nan
    texto = re.sub(r"(?i)r\$|%", "", texto)
    texto = re.sub(r"\s+", "", texto)
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return np.nan


def converter_serie_numerica(serie):
    return serie.map(converter_numero).astype("float64")


def converter_data(serie):
    texto = serie.astype("string").str.strip()

    resultado = pd.Series(
        pd.NaT,
        index=serie.index,
        dtype="datetime64[ns]",
    )

    mascara_iso = texto.str.match(
        r"^\d{4}-\d{2}-\d{2}(?:\s|$)",
        na=False,
    )

    resultado.loc[mascara_iso] = pd.to_datetime(
        texto.loc[mascara_iso],
        errors="coerce",
        yearfirst=True,
    )

    mascara_dia_primeiro = (
        texto.notna()
        & texto.ne("")
        & ~mascara_iso
    )

    resultado.loc[mascara_dia_primeiro] = pd.to_datetime(
        texto.loc[mascara_dia_primeiro],
        errors="coerce",
        dayfirst=True,
    )

    return resultado


def converter_mes_referencia(serie):
    texto = serie.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    resultado = pd.Series(pd.NaT, index=serie.index, dtype="datetime64[ns]")
    mascara_yyyymm = texto.str.fullmatch(r"\d{6}", na=False)
    resultado.loc[mascara_yyyymm] = pd.to_datetime(
        texto.loc[mascara_yyyymm], format="%Y%m", errors="coerce"
    )
    restantes = ~mascara_yyyymm & texto.notna() & texto.ne("")
    if restantes.any():
        resultado.loc[restantes] = converter_data(texto.loc[restantes])
    return resultado


def horario_valido(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return False
    texto = str(valor).strip()
    if " " in texto:
        texto = texto.split()[-1]
    encontrado = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?", texto)
    if not encontrado:
        return False
    hora, minuto, segundo = encontrado.groups()
    return int(hora) <= 23 and int(minuto) <= 59 and int(segundo or 0) <= 59


def carregar_entradas():
    obrigatorios = [BRONZE_PATH, BRONZE_MANIFEST_PATH, CONTRACT_PATH]
    faltantes = [p for p in obrigatorios if not p.is_file()]
    if faltantes:
        raise FileNotFoundError(
            "Arquivos obrigatórios ausentes:\n" + "\n".join(map(str, faltantes))
        )
    with BRONZE_MANIFEST_PATH.open("r", encoding="utf-8") as arquivo:
        manifesto = json.load(arquivo)
    with CONTRACT_PATH.open("r", encoding="utf-8-sig") as arquivo:
        contrato = json.load(arquivo)
    if manifesto.get("status") != "success":
        raise ValueError("O manifesto da Bronze não possui status success.")
    if calcular_sha256(BRONZE_PATH) != manifesto["bronze"]["sha256"]:
        raise ValueError("O SHA-256 da Bronze difere do manifesto.")
    dados = pd.read_parquet(BRONZE_PATH, engine="pyarrow")
    if len(dados) != manifesto["bronze"]["rows"]:
        raise ValueError("A quantidade de linhas difere do manifesto.")
    if len(dados.columns) != manifesto["bronze"]["total_columns"]:
        raise ValueError("A quantidade de colunas difere do manifesto.")
    exigidas = set(
        COLUNAS_NUMERICAS + COLUNAS_DATAS + COLUNAS_MES_REFERENCIA + COLUNAS_HORARIOS
        + ["Pedido_ID", "Cliente_ID", "Id_Item", "Ciclo_Vida_Cliente",
           "Frete_Gratis", "Cupom_Utilizado"]
    )
    faltantes = sorted(exigidas - set(dados.columns))
    if faltantes:
        raise ValueError("Colunas obrigatórias ausentes: " + ", ".join(faltantes))
    return dados, manifesto, contrato


def classificar_colunas(dados, manifesto):
    dq = [c for c in dados if c.startswith(DQ_PREFIX)]
    tecnicas = [c for c in dados if c.startswith(TECHNICAL_PREFIX)]
    analiticas = [c for c in dados if c not in dq and c not in tecnicas]
    encontrado = {
        "analiticas": len(analiticas), "dq": len(dq), "tecnicas": len(tecnicas)
    }
    esperado = {
        "analiticas": manifesto["bronze"]["analytical_columns"],
        "dq": manifesto["bronze"]["dq_columns"],
        "tecnicas": manifesto["bronze"]["technical_columns"],
    }
    if encontrado != esperado:
        raise ValueError(
            f"Classificação das colunas difere do manifesto. "
            f"Esperado: {esperado}. Encontrado: {encontrado}."
        )
    return {"analiticas": analiticas, "dq": dq, "tecnicas": tecnicas}


def preparar_dados(dados):
    preparado = dados.copy()
    for coluna in COLUNAS_NUMERICAS:
        preparado[f"__num__{coluna}"] = converter_serie_numerica(dados[coluna])
    for coluna in COLUNAS_DATAS:
        preparado[f"__data__{coluna}"] = converter_data(dados[coluna])
    for coluna in COLUNAS_MES_REFERENCIA:
        preparado[f"__data__{coluna}"] = converter_mes_referencia(dados[coluna])
    return preparado


def analisar_tipagem(dados, preparado):
    resumo = []
    erros = []
    for coluna in COLUNAS_NUMERICAS:
        mascara_informado = ~ausente(dados[coluna])
        convertido = preparado[f"__num__{coluna}"]
        mascara_erro = mascara_informado & convertido.isna()
        mascara_fracao = (
            mascara_informado & convertido.notna()
            & ~np.isclose(convertido % 1, 0, atol=1e-9)
        ) if coluna in COLUNAS_INTEIRAS_ESPERADAS else pd.Series(False, index=dados.index)
        resumo.append({
            "coluna": coluna, "tipo_esperado": "inteiro" if coluna in COLUNAS_INTEIRAS_ESPERADAS else "decimal",
            "informados": int(mascara_informado.sum()),
            "convertidos": int((mascara_informado & convertido.notna()).sum()),
            "falhas_conversao": int(mascara_erro.sum()),
            "fracionarios_em_inteiro": int(mascara_fracao.sum()),
            "percentual_convertido": percentual(int((mascara_informado & convertido.notna()).sum()), int(mascara_informado.sum())),
        })
        for indice in dados.index[mascara_erro | mascara_fracao]:
            erros.append({
                "_source_row_number": dados.at[indice, "_source_row_number"],
                "Pedido_ID": dados.at[indice, "Pedido_ID"],
                "coluna": coluna, "valor_original": dados.at[indice, coluna],
                "tipo_erro": "falha_conversao" if mascara_erro.at[indice] else "fracao_em_campo_inteiro",
            })
    for coluna in COLUNAS_DATAS:
        informado = ~ausente(dados[coluna])
        convertido = preparado[f"__data__{coluna}"]
        falha = informado & convertido.isna()
        resumo.append({
            "coluna": coluna, "tipo_esperado": "data",
            "informados": int(informado.sum()), "convertidos": int((informado & convertido.notna()).sum()),
            "falhas_conversao": int(falha.sum()), "fracionarios_em_inteiro": 0,
            "percentual_convertido": percentual(int((informado & convertido.notna()).sum()), int(informado.sum())),
        })
        for indice in dados.index[falha]:
            erros.append({
                "_source_row_number": dados.at[indice, "_source_row_number"], "Pedido_ID": dados.at[indice, "Pedido_ID"],
                "coluna": coluna, "valor_original": dados.at[indice, coluna], "tipo_erro": "data_invalida",
            })
    for coluna in COLUNAS_MES_REFERENCIA:
        informado = ~ausente(dados[coluna])
        convertido = preparado[f"__data__{coluna}"]
        falha = informado & convertido.isna()
        resumo.append({
            "coluna": coluna, "tipo_esperado": "mes_referencia_YYYYMM",
            "informados": int(informado.sum()), "convertidos": int((informado & convertido.notna()).sum()),
            "falhas_conversao": int(falha.sum()), "fracionarios_em_inteiro": 0,
            "percentual_convertido": percentual(int((informado & convertido.notna()).sum()), int(informado.sum())),
        })
        for indice in dados.index[falha]:
            erros.append({
                "_source_row_number": dados.at[indice, "_source_row_number"], "Pedido_ID": dados.at[indice, "Pedido_ID"],
                "coluna": coluna, "valor_original": dados.at[indice, coluna], "tipo_erro": "mes_referencia_invalido",
            })
    for coluna in COLUNAS_HORARIOS:
        informado = ~ausente(dados[coluna])
        valido = dados[coluna].map(horario_valido) & informado
        falha = informado & ~valido
        resumo.append({
            "coluna": coluna, "tipo_esperado": "horario",
            "informados": int(informado.sum()), "convertidos": int(valido.sum()),
            "falhas_conversao": int(falha.sum()), "fracionarios_em_inteiro": 0,
            "percentual_convertido": percentual(int(valido.sum()), int(informado.sum())),
        })
        for indice in dados.index[falha]:
            erros.append({
                "_source_row_number": dados.at[indice, "_source_row_number"], "Pedido_ID": dados.at[indice, "Pedido_ID"],
                "coluna": coluna, "valor_original": dados.at[indice, coluna], "tipo_erro": "horario_invalido",
            })
    return pd.DataFrame(resumo), pd.DataFrame(erros)


def classificar_dominio_quantitativo(coluna, serie, preparado=None):
    if coluna == "Idade":
        return (serie < 16) | (serie > 100), "idade fora do domínio permitido de 16 a 100 anos"
    if coluna == "Tempo_Experiencia_Anos":
        return serie < 0, "tempo de experiência negativo"
    if coluna == "Renda_Mensal_Cliente":
        return serie < 0, "renda negativa; renda zero exige contexto profissional"
    if coluna == "Intervalo_Medio_Compras_Dias":
        return serie < 0, "intervalo negativo"
    if coluna == "Ticket_Medio_Cliente":
        return serie <= 0, "ticket não positivo"
    if coluna == "Quantidade":
        return serie <= 0, "quantidade não positiva"
    if coluna in {"Custo_Unitario", "Preco_Unitario_Lista"}:
        return serie <= 0, "valor unitário não positivo"
    if coluna == "Valor_Compra":
        return serie < 0, "valor de compra negativo"
    if coluna == "Frete":
        return serie < 0, "frete negativo"
    if coluna in {"Prazo_Entrega_Prometido", "Prazo_Entrega_Real"}:
        return serie < 0, "prazo negativo"
    if coluna == "Pontos_Fidelidade":
        return serie < 0, "pontos negativos"
    return pd.Series(False, index=serie.index), "sem violação objetiva identificada"


def criar_base_unidade(dados, preparado, coluna):
    nivel = NIVEL_VARIAVEL[coluna]
    coluna_num = f"__num__{coluna}"
    if nivel == "cliente":
        chaves = ["Cliente_ID", coluna_num]
    elif nivel == "pedido":
        chaves = ["Pedido_ID", coluna_num]
    elif nivel == "item_cadastral":
        chaves = ["Id_Item", "Produto", "Medida", coluna_num]
    else:
        chaves = ["_source_row_number"]
    return preparado.drop_duplicates(subset=chaves, keep="first").copy()


def estatisticas_e_outliers(dados, preparado):
    resumos = []
    detalhes = []
    for coluna in COLUNAS_NUMERICAS:
        nivel = NIVEL_VARIAVEL[coluna]
        base = criar_base_unidade(dados, preparado, coluna)
        serie_com_indice = base[f"__num__{coluna}"]
        serie = serie_com_indice.dropna()
        if serie.empty:
            continue
        violacao, descricao_violacao = classificar_dominio_quantitativo(
            coluna, serie_com_indice, base
        )
        # IQR não é apropriado para escalas ordinais ou variáveis discretas
        # altamente concentradas, como avaliação e percentual de desconto.
        aplicar_iqr = nivel != "dominio_discreto"
        q1, mediana, q3 = serie.quantile([0.25, 0.50, 0.75])
        iqr = q3 - q1
        lim_inf = q1 - 1.5 * iqr
        lim_sup = q3 + 1.5 * iqr
        ext_inf = q1 - 3 * iqr
        ext_sup = q3 + 3 * iqr
        mascara_outlier = ((serie_com_indice < lim_inf) | (serie_com_indice > lim_sup)) if aplicar_iqr and iqr > 0 else pd.Series(False, index=base.index)
        mascara_extremo = ((serie_com_indice < ext_inf) | (serie_com_indice > ext_sup)) if aplicar_iqr and iqr > 0 else pd.Series(False, index=base.index)
        total_violacoes = int(violacao.fillna(False).sum())
        if total_violacoes:
            observacao = f"{total_violacoes} violação(ões) objetiva(s): {descricao_violacao}"
        elif not aplicar_iqr:
            observacao = "IQR não aplicado; validar domínio e distribuição de frequências"
        elif iqr == 0:
            observacao = "IQR não informativo porque a amplitude interquartil é zero"
        else:
            observacao = "Sem violação objetiva; outliers estatísticos exigem validação contextual"
        resumos.append({
            "coluna": coluna, "nivel_analitico": nivel,
            "unidades_analisadas": len(serie), "n_unicos": serie.nunique(),
            "minimo": serie.min(), "p01": serie.quantile(.01), "q1": q1,
            "mediana": mediana, "media": serie.mean(), "q3": q3,
            "p99": serie.quantile(.99), "maximo": serie.max(),
            "desvio_padrao": serie.std(), "iqr": iqr,
            "limite_inferior_iqr": lim_inf, "limite_superior_iqr": lim_sup,
            "outliers_iqr": int(mascara_outlier.sum()),
            "outliers_extremos_3iqr": int(mascara_extremo.sum()),
            "percentual_outliers": percentual(int(mascara_outlier.sum()), len(serie)),
            "violacoes_dominio": total_violacoes,
            "criterio_dominio": descricao_violacao,
            "observacao": observacao,
        })
        mascara_detalhe = mascara_outlier | violacao.fillna(False)
        colunas_contexto = [
            "Profissão", "Escolaridade", "Situacao_Profissional", "Idade",
            "Tempo_Experiencia_Anos", "Renda_Mensal_Cliente", "Estado",
            "Cidade", "Produto", "Categoria_Item", "Medida", "Quantidade",
            "Custo_Unitario", "Preco_Unitario_Lista", "Desconto_Percentual",
            "Valor_Compra", "Campanha", "Cupom_Utilizado", "Frete",
            "Frete_Gratis", "Transportadora", "Prazo_Entrega_Prometido",
            "Prazo_Entrega_Real", "Atraso_Entrega", "Ciclo_Vida_Cliente",
            "Intervalo_Medio_Compras_Dias", "Ticket_Medio_Cliente",
            "Pontos_Fidelidade", "Data_Compra",
        ]
        for indice in base.index[mascara_detalhe]:
            valor = base.at[indice, f"__num__{coluna}"]
            viola = bool(violacao.at[indice])
            if viola:
                classe_final = "violacao_dominio_erro_provavel"
                decisao = "corrigir_ou_nulificar_apos_investigacao"
            elif mascara_extremo.at[indice]:
                classe_final = "outlier_extremo_contextual"
                decisao = "investigar_contexto"
            else:
                classe_final = "outlier_moderado_contextual"
                decisao = "investigar_contexto"
            registro = {
                "_source_row_number": base.at[indice, "_source_row_number"],
                "Pedido_ID": base.at[indice, "Pedido_ID"], "Cliente_ID": base.at[indice, "Cliente_ID"],
                "Id_Item": base.at[indice, "Id_Item"], "coluna": coluna,
                "nivel_analitico": nivel,
                "valor_original": base.at[indice, coluna], "valor_numerico": valor,
                "classificacao_estatistica": "extremo_3iqr" if mascara_extremo.at[indice] else ("moderado_1_5iqr" if mascara_outlier.at[indice] else "nao_outlier_iqr"),
                "violacao_dominio": viola, "motivo_violacao": descricao_violacao if viola else pd.NA,
                "classificacao_final": classe_final,
                "limite_inferior": lim_inf, "limite_superior": lim_sup,
                "decisao_silver": decisao,
            }
            for contexto in colunas_contexto:
                if contexto in base.columns and contexto != coluna:
                    registro[contexto] = base.at[indice, contexto]
            detalhes.append(registro)
    return pd.DataFrame(resumos), pd.DataFrame(detalhes)


def analisar_dominios(dados, preparado):
    registros = []
    for coluna, dominio in DOMINIOS_ESPERADOS.items():
        serie = dados[coluna].map(normalizar_texto)
        frequencias = serie.value_counts(dropna=False)
        for valor, quantidade in frequencias.items():
            informado = not pd.isna(valor) and valor != ""
            registros.append({
                "coluna": coluna, "valor_normalizado": valor,
                "quantidade": int(quantidade), "percentual": percentual(int(quantidade), len(dados)),
                "dominio_valido": bool(valor in dominio) if informado else False,
                "observacao": "ausente" if not informado else ("válido" if valor in dominio else "fora_do_dominio"),
            })
    avaliacao = preparado["__num__Avaliacao_Cliente"]
    for valor, quantidade in avaliacao.value_counts(dropna=False).items():
        registros.append({
            "coluna": "Avaliacao_Cliente", "valor_normalizado": valor,
            "quantidade": int(quantidade), "percentual": percentual(int(quantidade), len(dados)),
            "dominio_valido": bool(pd.notna(valor) and valor in {1, 2, 3, 4, 5}),
            "observacao": "escala_esperada_1_a_5",
        })
    return pd.DataFrame(registros)


def registrar_regra(resumo, detalhes, dados, mascara, regra, nivel, severidade, contexto=None):
    quantidade = int(mascara.fillna(False).sum())
    resumo.append({
        "regra": regra, "nivel_analitico": nivel, "severidade_preliminar": severidade,
        "linhas_avaliadas": len(dados), "divergencias": quantidade,
        "percentual_divergencias": percentual(quantidade, len(dados)),
        "status": "conforme" if quantidade == 0 else "investigar",
    })
    colunas = ["_source_row_number", "Pedido_ID", "Cliente_ID", "Id_Item"]
    for indice in dados.index[mascara.fillna(False)]:
        registro = {c: dados.at[indice, c] for c in colunas}
        registro.update({"regra": regra, "severidade_preliminar": severidade})
        for coluna_contexto in [
            "Profissão", "Escolaridade", "Situacao_Profissional", "Idade",
            "Tempo_Experiencia_Anos", "Renda_Mensal_Cliente", "Estado", "Cidade",
            "Produto", "Categoria_Item", "Medida", "Quantidade", "Custo_Unitario",
            "Preco_Unitario_Lista", "Desconto_Percentual", "Valor_Compra", "Campanha",
            "Cupom_Utilizado", "Frete", "Frete_Gratis", "Transportadora",
            "Prazo_Entrega_Prometido", "Prazo_Entrega_Real", "Atraso_Entrega",
            "Ciclo_Vida_Cliente", "Intervalo_Medio_Compras_Dias",
            "Ticket_Medio_Cliente", "Pontos_Fidelidade", "Data_Compra",
        ]:
            if coluna_contexto in dados.columns:
                registro[coluna_contexto] = dados.at[indice, coluna_contexto]
        if contexto:
            for nome, serie in contexto.items():
                registro[nome] = serie.at[indice]
        detalhes.append(registro)


def analisar_regras(dados, preparado):
    resumo, detalhes = [], []
    n = {c: preparado[f"__num__{c}"] for c in COLUNAS_NUMERICAS}
    regras = [
        ("idade_fora_16_100", (n["Idade"] < 16) | (n["Idade"] > 100), "cliente", "alta", {"Idade": n["Idade"]}),
        ("experiencia_negativa", n["Tempo_Experiencia_Anos"] < 0, "cliente", "alta", {"Tempo_Experiencia_Anos": n["Tempo_Experiencia_Anos"]}),
        ("experiencia_incompativel_idade", n["Tempo_Experiencia_Anos"] > (n["Idade"] - 14), "cliente", "alta", {"Idade": n["Idade"], "Tempo_Experiencia_Anos": n["Tempo_Experiencia_Anos"]}),
        ("renda_negativa", n["Renda_Mensal_Cliente"] < 0, "cliente", "alta", {"Renda": n["Renda_Mensal_Cliente"]}),
        ("renda_zero_requer_contexto", n["Renda_Mensal_Cliente"].abs().le(.001), "cliente", "baixa", {"Renda": n["Renda_Mensal_Cliente"]}),
        ("intervalo_negativo", n["Intervalo_Medio_Compras_Dias"] < 0, "cliente", "alta", {"Intervalo": n["Intervalo_Medio_Compras_Dias"]}),
        ("ticket_nao_positivo", n["Ticket_Medio_Cliente"] <= 0, "cliente", "alta", {"Ticket": n["Ticket_Medio_Cliente"]}),
        ("quantidade_nao_positiva", n["Quantidade"] <= 0, "item_pedido", "alta", {"Quantidade": n["Quantidade"]}),
        ("custo_nao_positivo", n["Custo_Unitario"] <= 0, "item", "alta", {"Custo": n["Custo_Unitario"]}),
        ("preco_nao_positivo", n["Preco_Unitario_Lista"] <= 0, "item", "alta", {"Preco": n["Preco_Unitario_Lista"]}),
        ("custo_superior_preco", n["Custo_Unitario"] > n["Preco_Unitario_Lista"], "item_pedido", "media", {"Custo": n["Custo_Unitario"], "Preco": n["Preco_Unitario_Lista"]}),
        ("valor_compra_negativo", n["Valor_Compra"] < 0, "item_pedido", "alta", {"Valor_Compra": n["Valor_Compra"]}),
        ("frete_negativo", n["Frete"] < 0, "pedido", "alta", {"Frete": n["Frete"]}),
        ("prazo_prometido_negativo", n["Prazo_Entrega_Prometido"] < 0, "pedido", "alta", {"Prazo": n["Prazo_Entrega_Prometido"]}),
        ("prazo_real_negativo", n["Prazo_Entrega_Real"] < 0, "pedido", "alta", {"Prazo": n["Prazo_Entrega_Real"]}),
        ("avaliacao_fora_1_5", n["Avaliacao_Cliente"].notna() & ~n["Avaliacao_Cliente"].isin([1,2,3,4,5]), "pedido", "alta", {"Avaliacao": n["Avaliacao_Cliente"]}),
        ("pontos_negativos", n["Pontos_Fidelidade"] < 0, "cliente", "alta", {"Pontos": n["Pontos_Fidelidade"]}),
    ]
    for regra, mascara, nivel, severidade, contexto in regras:
        registrar_regra(resumo, detalhes, dados, mascara, regra, nivel, severidade, contexto)

    desconto = n["Desconto_Percentual"]
    escala = "0_a_1" if desconto.dropna().max() <= 1 else "0_a_100"
    desconto_decimal = desconto if escala == "0_a_1" else desconto / 100
    registrar_regra(resumo, detalhes, dados, (desconto_decimal < 0) | (desconto_decimal > 1), "desconto_fora_escala", "item_pedido", "alta", {"Desconto": desconto})

    frete_gratis = dados["Frete_Gratis"].map(normalizar_texto)
    mascara_frete = ((frete_gratis == "sim") & ~np.isclose(n["Frete"], 0, atol=.001)) | ((frete_gratis == "nao") & np.isclose(n["Frete"], 0, atol=.001))
    registrar_regra(resumo, detalhes, dados, mascara_frete, "frete_gratis_incoerente_com_frete", "pedido", "media", {"Frete_Gratis": frete_gratis, "Frete": n["Frete"]})

    cupom = dados["Cupom_Utilizado"].map(normalizar_texto)
    mascara_cupom = ((cupom == "nao") & (desconto_decimal > 0)) | ((cupom == "sim") & np.isclose(desconto_decimal, 0, atol=1e-9))
    registrar_regra(resumo, detalhes, dados, mascara_cupom, "cupom_incoerente_com_desconto", "item_pedido", "media", {"Cupom": cupom, "Desconto": desconto})

    data = preparado["__data__Data_Compra"]
    mes = preparado["__data__Mes_Ref"]
    mascara_mes = data.notna() & mes.notna() & ((data.dt.year != mes.dt.year) | (data.dt.month != mes.dt.month))
    registrar_regra(resumo, detalhes, dados, mascara_mes, "mes_ref_difere_data_compra", "pedido", "alta", {"Data_Compra": data, "Mes_Ref": mes})
    data_limite = pd.Timestamp(datetime.now(timezone.utc).date())
    registrar_regra(resumo, detalhes, dados, data > data_limite, "data_compra_futura", "pedido", "alta", {"Data_Compra": data})
    registrar_regra(resumo, detalhes, dados, data.notna() & (data.dt.year != 2025), "data_compra_fora_periodo_2025", "pedido", "media", {"Data_Compra": data})

    atraso_diferenca = n["Prazo_Entrega_Real"] - n["Prazo_Entrega_Prometido"]
    atraso_texto = dados["Atraso_Entrega"].map(normalizar_texto)
    esperado_atraso = pd.Series(pd.NA, index=dados.index, dtype="string")
    # A base considera uma tolerância operacional de um dia.
    # Atraso = Sim somente quando o prazo real supera
    # o prazo prometido em mais de um dia.
    esperado_atraso.loc[
    atraso_diferenca.notna()
    & (atraso_diferenca > 1)
    ] = "sim"

    esperado_atraso.loc[
    atraso_diferenca.notna()
    & (atraso_diferenca <= 1)
    ] = "nao"
    informado = atraso_texto.notna() & esperado_atraso.notna()
    mascara_atraso = informado & atraso_texto.ne(esperado_atraso)
    registrar_regra(
        resumo, detalhes, dados, mascara_atraso,
        "atraso_entrega_coerente_com_prazos", "pedido", "alta",
        {"Atraso_Informado": atraso_texto, "Atraso_Esperado": esperado_atraso,
         "Diferenca_Dias": atraso_diferenca},
    )

    bruto = n["Quantidade"] * n["Preco_Unitario_Lista"]
    com_desconto = bruto * (1 - desconto_decimal)
    informado_valor = n["Valor_Compra"].notna() & bruto.notna()
    conf_bruto = informado_valor & np.isclose(n["Valor_Compra"], bruto, atol=TOLERANCIA_MONETARIA)
    conf_desc = informado_valor & np.isclose(n["Valor_Compra"], com_desconto, atol=TOLERANCIA_MONETARIA)
    for nome, conf in [("valor_compra_igual_quantidade_preco", conf_bruto), ("valor_compra_com_desconto", conf_desc)]:
        resumo.append({
            "regra": nome, "nivel_analitico": "item_pedido", "severidade_preliminar": "diagnostico_formula",
            "linhas_avaliadas": int(informado_valor.sum()), "divergencias": int((informado_valor & ~conf).sum()),
            "percentual_divergencias": percentual(int((informado_valor & ~conf).sum()), int(informado_valor.sum())), "status": "hipotese_formula",
        })
    mascara_sem_formula = informado_valor & ~conf_bruto & ~conf_desc
    causa_valor = pd.Series("formula_ou_campo_origem_a_investigar", index=dados.index, dtype="string")
    causa_valor.loc[n["Quantidade"] <= 0] = "quantidade_nao_positiva"
    causa_valor.loc[n["Quantidade"] >= 100] = "quantidade_extrema_provavel_erro_digitacao"
    registrar_regra(
        resumo, detalhes, dados, mascara_sem_formula,
        "valor_compra_nao_reproduz_formulas_testadas", "item_pedido", "media",
        {"Valor_Informado": n["Valor_Compra"], "Valor_Bruto": bruto,
         "Valor_Com_Desconto": com_desconto, "Causa_Provavel": causa_valor},
    )

    return pd.DataFrame(resumo), pd.DataFrame(detalhes), escala


def base_eventos_sem_duplicidade(dados, preparado, analiticas):
    base = preparado.drop_duplicates(subset=analiticas, keep="first").copy()
    base["__pedido"] = base["Pedido_ID"].astype("string").str.strip()
    base["__cliente"] = base["Cliente_ID"].astype("string").str.strip()
    return base


def analisar_calculos_cliente(dados, preparado, analiticas):
    base = base_eventos_sem_duplicidade(dados, preparado, analiticas)
    valor = "__num__Valor_Compra"
    data = "__data__Data_Compra"
    # Um pedido é contado uma vez; seu valor é a soma das linhas de item.
    pedidos = (
        base.groupby(["__cliente", "__pedido"], dropna=False)
        .agg(Data_Compra=(data, "min"), Valor_Pedido=(valor, "sum"))
        .reset_index()
    )
    referencia = pedidos["Data_Compra"].max()
    registros = []
    for cliente, grupo in pedidos.groupby("__cliente", dropna=False):
        grupo = grupo.sort_values("Data_Compra")
        datas = grupo["Data_Compra"].dropna().drop_duplicates().sort_values()
        intervalos = datas.diff().dt.days.dropna()
        linhas_cliente = base.loc[base["__cliente"] == cliente]
        ciclo_norm = linhas_cliente["Ciclo_Vida_Cliente"].map(normalizar_texto)
        ciclos = ciclo_norm.dropna().value_counts()
        intervalo_informado = base.loc[base["__cliente"] == cliente, "__num__Intervalo_Medio_Compras_Dias"].dropna()
        ticket_informado = base.loc[base["__cliente"] == cliente, "__num__Ticket_Medio_Cliente"].dropna()
        pontos_informados = base.loc[base["__cliente"] == cliente, "__num__Pontos_Fidelidade"].dropna()
        intervalo_calc = intervalos.mean() if not intervalos.empty else np.nan
        ticket_calc = grupo["Valor_Pedido"].mean() if len(grupo) else np.nan
        recencia = (referencia - datas.max()).days if pd.notna(referencia) and len(datas) else np.nan
        registros.append({
            "Cliente_ID": cliente, "Ciclo_Vida_Predominante": ciclos.index[0] if len(ciclos) else pd.NA,
            "ciclos_distintos_cliente": ciclo_norm.nunique(dropna=True),
            "valores_ciclo_cliente": " | ".join(f"{k}: {v}" for k, v in ciclos.items()),
            "pedidos_distintos": grupo["__pedido"].nunique(), "datas_compra_distintas": len(datas),
            "primeira_compra": datas.min() if len(datas) else pd.NaT,
            "ultima_compra": datas.max() if len(datas) else pd.NaT,
            "recencia_dias_na_data_referencia": recencia,
            "intervalo_medio_recalculado": intervalo_calc,
            "intervalo_medio_informado_moda": intervalo_informado.mode().iloc[0] if len(intervalo_informado) else np.nan,
            "diferenca_intervalo": (intervalo_informado.mode().iloc[0] - intervalo_calc) if len(intervalo_informado) and pd.notna(intervalo_calc) else np.nan,
            "ticket_medio_recalculado": ticket_calc,
            "ticket_medio_informado_moda": ticket_informado.mode().iloc[0] if len(ticket_informado) else np.nan,
            "diferenca_ticket": (ticket_informado.mode().iloc[0] - ticket_calc) if len(ticket_informado) else np.nan,
            "valor_total_compras": grupo["Valor_Pedido"].sum(),
            "pontos_fidelidade_moda": pontos_informados.mode().iloc[0] if len(pontos_informados) else np.nan,
            "razao_recencia_intervalo": recencia / intervalo_calc if pd.notna(intervalo_calc) and intervalo_calc > 0 else np.nan,
            "data_referencia": referencia,
        })
    detalhes = pd.DataFrame(registros)
    resumo = (
        detalhes.groupby("Ciclo_Vida_Predominante", dropna=False)
        .agg(
            clientes=("Cliente_ID", "nunique"),
            pedidos_mediana=("pedidos_distintos", "median"),
            pedidos_media=("pedidos_distintos", "mean"),
            recencia_min=("recencia_dias_na_data_referencia", "min"),
            recencia_q1=("recencia_dias_na_data_referencia", lambda s: s.quantile(.25)),
            recencia_mediana=("recencia_dias_na_data_referencia", "median"),
            recencia_q3=("recencia_dias_na_data_referencia", lambda s: s.quantile(.75)),
            recencia_max=("recencia_dias_na_data_referencia", "max"),
            intervalo_mediana=("intervalo_medio_recalculado", "median"),
            ticket_mediana=("ticket_medio_recalculado", "median"),
            valor_total_mediana=("valor_total_compras", "median"),
            razao_recencia_intervalo_mediana=("razao_recencia_intervalo", "median"),
            clientes_com_multiplos_ciclos=("ciclos_distintos_cliente", lambda s: int((s > 1).sum())),
        ).reset_index()
    )
    intervalo_avaliavel = detalhes["diferenca_intervalo"].notna()
    ticket_avaliavel = detalhes["diferenca_ticket"].notna()
    intervalo_divergente = intervalo_avaliavel & detalhes["diferenca_intervalo"].abs().gt(1.0)
    ticket_divergente = ticket_avaliavel & detalhes["diferenca_ticket"].abs().gt(TOLERANCIA_MONETARIA)
    validacao = pd.DataFrame([
        {
            "campo_calculado": "Intervalo_Medio_Compras_Dias",
            "formula_testada": "média dos dias entre datas de pedidos distintos por cliente",
            "clientes_avaliados": int(intervalo_avaliavel.sum()),
            "clientes_divergentes": int(intervalo_divergente.sum()),
            "percentual_divergente": percentual(int(intervalo_divergente.sum()), int(intervalo_avaliavel.sum())),
            "tolerancia": "1 dia",
        },
        {
            "campo_calculado": "Ticket_Medio_Cliente",
            "formula_testada": "média do valor agregado dos pedidos distintos por cliente",
            "clientes_avaliados": int(ticket_avaliavel.sum()),
            "clientes_divergentes": int(ticket_divergente.sum()),
            "percentual_divergente": percentual(int(ticket_divergente.sum()), int(ticket_avaliavel.sum())),
            "tolerancia": TOLERANCIA_MONETARIA,
        },
    ])
    correlacoes = []
    for metrica in ["pedidos_distintos", "valor_total_compras", "ticket_medio_recalculado"]:
        pares = detalhes[["pontos_fidelidade_moda", metrica]].dropna()
        correlacoes.append({
            "campo_calculado": "Pontos_Fidelidade",
            "formula_testada": f"correlação exploratória com {metrica}",
            "clientes_avaliados": len(pares),
            "clientes_divergentes": pd.NA,
            "percentual_divergente": pd.NA,
            "tolerancia": pd.NA,
            "correlacao_pearson": pares.corr().iloc[0, 1] if len(pares) > 1 else np.nan,
        })
    validacao = pd.concat([validacao, pd.DataFrame(correlacoes)], ignore_index=True)
    return resumo, detalhes, validacao


def analisar_constancia(dados, analiticas):
    registros = []
    for coluna in analiticas:
        valores = dados[coluna].astype("string").str.strip()
        informados = valores[~ausente(valores)]
        freq = informados.value_counts(dropna=False)
        maior = int(freq.iloc[0]) if len(freq) else 0
        participacao = percentual(maior, len(informados))
        if len(freq) <= 1:
            classe = "constante"
        elif participacao >= 95:
            classe = "quase_constante_95pct"
        else:
            classe = "variavel"
        registros.append({
            "coluna": coluna, "valores_distintos": int(informados.nunique()),
            "valor_mais_frequente": freq.index[0] if len(freq) else pd.NA,
            "frequencia_maior_valor": maior, "percentual_maior_valor": participacao,
            "classificacao": classe,
        })
    return pd.DataFrame(registros).sort_values(["classificacao", "percentual_maior_valor"], ascending=[True, False])


def criar_colunas_excluidas(grupos):
    registros = []
    for coluna in grupos["dq"]:
        registros.append({"coluna": coluna, "classificacao": "ground_truth_dq", "participou_da_descoberta": False, "motivo": "Isolada para evitar vazamento da resposta."})
    for coluna in grupos["tecnicas"]:
        registros.append({"coluna": coluna, "classificacao": "metadado_tecnico", "participou_da_descoberta": False, "motivo": "Usada somente para rastreabilidade."})
    return pd.DataFrame(registros)


def ajustar_planilhas(writer):
    preenchimento = PatternFill(fill_type="solid", fgColor="1F4E78")
    fonte = Font(color="FFFFFF", bold=True)
    for planilha in writer.book.worksheets:
        planilha.freeze_panes = "A2"
        planilha.auto_filter.ref = planilha.dimensions
        for celula in planilha[1]:
            celula.fill = preenchimento
            celula.font = fonte
            celula.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for coluna in planilha.columns:
            largura = min(max(len(str(c.value)) if c.value is not None else 0 for c in coluna) + 2, 55)
            planilha.column_dimensions[coluna[0].column_letter].width = largura


def salvar_relatorio(planilhas):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporario = OUTPUT_PATH.with_suffix(".tmp.xlsx")
    with pd.ExcelWriter(temporario, engine="openpyxl") as writer:
        for nome, quadro in planilhas:
            quadro.to_excel(writer, sheet_name=nome[:31], index=False)
        ajustar_planilhas(writer)
    temporario.replace(OUTPUT_PATH)


def executar():
    print("Iniciando validação de tipos, domínios e regras...")
    dados, manifesto, _contrato = carregar_entradas()
    grupos = classificar_colunas(dados, manifesto)
    preparado = preparar_dados(dados)
    tipagem_resumo, tipagem_erros = analisar_tipagem(dados, preparado)
    estatisticas, outliers = estatisticas_e_outliers(dados, preparado)
    dominios = analisar_dominios(dados, preparado)
    regras_resumo, regras_detalhes, escala_desconto = analisar_regras(dados, preparado)
    ciclo_resumo, ciclo_detalhes, calculos_cliente = analisar_calculos_cliente(dados, preparado, grupos["analiticas"])
    constantes = analisar_constancia(dados, grupos["analiticas"])
    excluidas = criar_colunas_excluidas(grupos)
    resumo_execucao = pd.DataFrame([{
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "etapa": "06_validacao_tipos_dominios_regras", "arquivo_bronze": BRONZE_PATH.name,
        "sha256_bronze": manifesto["bronze"]["sha256"], "total_linhas": len(dados),
        "colunas_analiticas": len(grupos["analiticas"]), "escala_desconto_identificada": escala_desconto,
        "falhas_tipagem": int(tipagem_resumo["falhas_conversao"].sum()),
        "registros_outliers_iqr": len(outliers), "regras_avaliadas": len(regras_resumo),
        "dados_modificados": False, "dq_usado_na_descoberta": False,
        "data_referencia_ciclo": ciclo_detalhes["data_referencia"].max(), "status": "success",
    }])
    planilhas = [
        ("resumo_execucao", resumo_execucao), ("tipagem_resumo", tipagem_resumo),
        ("tipagem_erros", tipagem_erros), ("estatisticas_quant", estatisticas),
        ("outliers_detalhes", outliers), ("dominios", dominios),
        ("regras_resumo", regras_resumo), ("regras_detalhes", regras_detalhes),
        ("calculos_cliente", calculos_cliente),
        ("ciclo_vida_resumo", ciclo_resumo), ("ciclo_vida_clientes", ciclo_detalhes),
        ("constancia_colunas", constantes), ("colunas_excluidas", excluidas),
    ]
    salvar_relatorio(planilhas)
    print("[OK] Integridade SHA-256: APROVADA")
    print(f"[OK] Escala de desconto identificada: {escala_desconto}")
    print(f"[OK] Falhas de conversão: {int(tipagem_resumo['falhas_conversao'].sum())}")
    print(f"[OK] Registros classificados como outliers: {len(outliers)}")
    print(f"[OK] Relatório gerado: {OUTPUT_PATH}")
    print("RESULTADO_FINAL: APROVADO")
    return True


if __name__ == "__main__":
    try:
        sucesso = executar()
        sys.exit(0 if sucesso else 1)
    except Exception as erro:
        print("RESULTADO_FINAL: REPROVADO")
        print(f"ERRO: {type(erro).__name__}: {erro}")
        sys.exit(1)
