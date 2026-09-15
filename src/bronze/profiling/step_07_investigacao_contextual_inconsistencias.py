import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill

from step_06_validacao_tipos_dominios_regras import (
    BRONZE_PATH,
    OUTPUT_DIR,
    ausente,
    carregar_entradas,
    classificar_colunas,
    normalizar_texto,
    preparar_dados,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STEP_06_PATH = OUTPUT_DIR / "step_06_validacao_tipos_dominios_regras.xlsx"
OUTPUT_PATH = OUTPUT_DIR / "step_07_investigacao_contextual_inconsistencias.xlsx"
TOLERANCIA_MONETARIA = 0.01

CONTEXTO_CLIENTE = [
    "Cliente_ID", "Idade", "Profissão", "Escolaridade",
    "Situacao_Profissional", "Tempo_Experiencia_Anos",
    "Renda_Mensal_Cliente", "Estado", "Cidade",
    "Ciclo_Vida_Cliente", "Intervalo_Medio_Compras_Dias",
    "Ticket_Medio_Cliente", "Pontos_Fidelidade",
]
CONTEXTO_COMPRA = [
    "_source_row_number", "Pedido_ID", "Id_Item", "Produto",
    "Categoria_Item", "Medida", "Quantidade", "Custo_Unitario",
    "Preco_Unitario_Lista", "Desconto_Percentual", "Valor_Compra",
    "Cupom_Utilizado", "Campanha", "Data_Compra",
]


def percentual(quantidade, total):
    return round(quantidade / total * 100, 4) if total else 0.0


def validar_step_06(manifesto):
    if not STEP_06_PATH.is_file():
        raise FileNotFoundError(f"Relatório obrigatório ausente: {STEP_06_PATH}")
    resumo = pd.read_excel(STEP_06_PATH, sheet_name="resumo_execucao")
    if resumo.empty or resumo.iloc[0].get("status") != "success":
        raise ValueError("A Etapa 6 não possui status success.")
    if resumo.iloc[0].get("sha256_bronze") != manifesto["bronze"]["sha256"]:
        raise ValueError("A Etapa 6 não analisou a Bronze atual.")
    if int(resumo.iloc[0].get("falhas_tipagem", -1)) != 0:
        raise ValueError("A Etapa 6 ainda possui falhas de tipagem.")
    regras = pd.read_excel(STEP_06_PATH, sheet_name="regras_resumo")
    controles = regras.set_index("regra")["divergencias"].to_dict()
    if controles.get("mes_ref_difere_data_compra") != 0:
        raise ValueError("A Etapa 6 ainda possui divergências indevidas de Mes_Ref.")
    return resumo, regras


def frequencias_texto(serie):
    valores = serie.astype("string").str.strip().dropna()
    valores = valores[valores.ne("")]
    if valores.empty:
        return None
    return " | ".join(f"{valor}: {qtd}" for valor, qtd in valores.value_counts().items())


def candidato_unico(serie):
    valores = serie.dropna()
    if valores.empty:
        return np.nan, 0, 0, "sem_evidencia"
    freq = valores.value_counts()
    candidato = freq.index[0]
    distintos = valores.nunique()
    classe = "recuperavel_deterministico" if distintos == 1 else "candidato_com_conflito"
    return candidato, int(freq.iloc[0]), int(distintos), classe


def investigar_idade(dados, preparado):
    idade = preparado["__num__Idade"]
    mascara = (idade < 16) | (idade > 100)
    registros = []
    for indice in dados.index[mascara]:
        cliente = dados.at[indice, "Cliente_ID"]
        grupo = preparado[preparado["Cliente_ID"].eq(cliente)]
        idades = grupo["__num__Idade"]
        validas = idades[(idades >= 16) & (idades <= 100)]
        candidato, suporte, distintos, classe = candidato_unico(validas)
        registro = {
            "_source_row_number": dados.at[indice, "_source_row_number"],
            "Pedido_ID": dados.at[indice, "Pedido_ID"], "Cliente_ID": cliente,
            "idade_invalida": idade.at[indice], "candidato_idade": candidato,
            "suporte_candidato": suporte, "idades_validas_distintas": distintos,
            "historico_idades": frequencias_texto(grupo["Idade"]),
            "classificacao": classe,
            "decisao_silver": "preencher_com_historico" if classe == "recuperavel_deterministico" else "revisao_manual",
        }
        for coluna in CONTEXTO_CLIENTE:
            if coluna in dados and coluna not in registro:
                registro[coluna] = dados.at[indice, coluna]
        registros.append(registro)
    return pd.DataFrame(registros)


def investigar_renda(dados, preparado):
    renda = preparado["__num__Renda_Mensal_Cliente"]
    base_cliente_valor = preparado.drop_duplicates(["Cliente_ID", "__num__Renda_Mensal_Cliente"])
    serie = base_cliente_valor["__num__Renda_Mensal_Cliente"].dropna()
    q1, q3 = serie.quantile([.25, .75])
    limite_extremo = q3 + 3 * (q3 - q1)
    mascara = (base_cliente_valor["__num__Renda_Mensal_Cliente"] <= 0) | (base_cliente_valor["__num__Renda_Mensal_Cliente"] > limite_extremo)
    registros = []
    for indice in base_cliente_valor.index[mascara]:
        cliente = dados.at[indice, "Cliente_ID"]
        valor = renda.at[indice]
        grupo = preparado[preparado["Cliente_ID"].eq(cliente)]
        candidatas = grupo["__num__Renda_Mensal_Cliente"]
        candidatas = candidatas[(candidatas > 0) & (candidatas <= limite_extremo)]
        candidato, suporte, distintos, recuperacao = candidato_unico(candidatas)
        situacao = normalizar_texto(dados.at[indice, "Situacao_Profissional"])
        profissao = normalizar_texto(dados.at[indice, "Profissão"])
        if valor < 0 or valor > 1_000_000:
            classe = "erro_provavel"
        elif valor == 0 and (situacao in {"desempregado", "estudante"} or profissao == "sem ocupacao"):
            classe = "zero_contextualmente_plausivel"
        elif valor == 0:
            classe = "zero_incoerente_com_contexto_profissional"
        else:
            classe = "renda_alta_contextual"
        registro = {
            "_source_row_number": dados.at[indice, "_source_row_number"],
            "Cliente_ID": cliente, "renda_investigada": valor,
            "limite_extremo_3iqr": limite_extremo, "classificacao_contextual": classe,
            "candidato_renda_historico": candidato, "suporte_candidato": suporte,
            "rendas_validas_distintas": distintos, "recuperabilidade": recuperacao,
            "historico_rendas": frequencias_texto(grupo["Renda_Mensal_Cliente"]),
            "decisao_silver": "usar_historico" if recuperacao == "recuperavel_deterministico" and classe == "erro_provavel" else "preservar_e_revisar",
        }
        for coluna in CONTEXTO_CLIENTE:
            if coluna in dados and coluna not in registro:
                registro[coluna] = dados.at[indice, coluna]
        registros.append(registro)
    return pd.DataFrame(registros)


def desconto_decimal(preparado):
    return preparado["__num__Desconto_Percentual"] / 100


def investigar_quantidade(dados, preparado):
    quantidade = preparado["__num__Quantidade"]
    mascara = (quantidade <= 0) | (quantidade > 6)
    preco = preparado["__num__Preco_Unitario_Lista"]
    valor = preparado["__num__Valor_Compra"]
    fator = preco * (1 - desconto_decimal(preparado))
    estimada = valor / fator.replace(0, np.nan)
    registros = []
    for indice in dados.index[mascara]:
        qtd = quantidade.at[indice]
        estimativa = estimada.at[indice]
        arredondada = round(estimativa) if pd.notna(estimativa) else np.nan
        reproduz = pd.notna(estimativa) and arredondada > 0 and abs(estimativa - arredondada) <= .01
        if qtd <= 0:
            classe = "quantidade_invalida"
        elif qtd >= 100:
            classe = "quantidade_extrema_provavel_erro"
        else:
            classe = "quantidade_alta_plausivel"
        registro = {
            "_source_row_number": dados.at[indice, "_source_row_number"],
            "Pedido_ID": dados.at[indice, "Pedido_ID"], "Cliente_ID": dados.at[indice, "Cliente_ID"],
            "Id_Item": dados.at[indice, "Id_Item"], "quantidade_informada": qtd,
            "quantidade_estimada_pelo_valor": estimativa,
            "candidato_quantidade_inteira": arredondada if reproduz else np.nan,
            "candidato_reproduz_valor": reproduz, "classificacao_contextual": classe,
            "decisao_silver": "usar_quantidade_estimada" if reproduz and classe != "quantidade_alta_plausivel" else "preservar_e_revisar",
        }
        for coluna in CONTEXTO_COMPRA:
            if coluna in dados and coluna not in registro:
                registro[coluna] = dados.at[indice, coluna]
        registros.append(registro)
    return pd.DataFrame(registros)


def investigar_valor_compra(dados, preparado):
    quantidade = preparado["__num__Quantidade"]
    preco = preparado["__num__Preco_Unitario_Lista"]
    desconto = desconto_decimal(preparado)
    informado = preparado["__num__Valor_Compra"]
    esperado = quantidade * preco * (1 - desconto)
    diferenca = informado - esperado
    mascara = diferenca.abs() > TOLERANCIA_MONETARIA
    registros = []
    for indice in dados.index[mascara]:
        causa = "quantidade_invalida" if quantidade.at[indice] <= 0 else (
            "quantidade_extrema" if quantidade.at[indice] >= 100 else "formula_ou_origem_a_investigar"
        )
        registro = {
            "_source_row_number": dados.at[indice, "_source_row_number"],
            "Pedido_ID": dados.at[indice, "Pedido_ID"], "Cliente_ID": dados.at[indice, "Cliente_ID"],
            "Id_Item": dados.at[indice, "Id_Item"], "valor_informado": informado.at[indice],
            "valor_recalculado": esperado.at[indice], "diferenca": diferenca.at[indice],
            "causa_provavel": causa, "decisao_silver": "pendente_correcao_campo_origem",
        }
        for coluna in CONTEXTO_COMPRA:
            if coluna in dados and coluna not in registro:
                registro[coluna] = dados.at[indice, coluna]
        registros.append(registro)
    return pd.DataFrame(registros)


def investigar_cupom(dados, preparado):
    cupom = dados["Cupom_Utilizado"].map(normalizar_texto)
    desconto = preparado["__num__Desconto_Percentual"]
    mascara = ausente(dados["Cupom_Utilizado"]) | ((cupom == "nao") & (desconto > 0)) | ((cupom == "sim") & (desconto == 0))
    quadro = dados.loc[mascara, CONTEXTO_COMPRA].copy()
    quadro.insert(0, "classificacao", np.select(
        [ausente(quadro["Cupom_Utilizado"]), quadro["Cupom_Utilizado"].map(normalizar_texto).eq("nao")],
        ["cupom_ausente", "desconto_positivo_com_cupom_nao"],
        default="cupom_sim_com_desconto_zero",
    ))
    quadro["decisao_silver"] = "pendente_regra_comercial"
    return quadro


def investigar_atraso(dados, preparado):
    diferenca = preparado["__num__Prazo_Entrega_Real"] - preparado["__num__Prazo_Entrega_Prometido"]
    mascara = diferenca.eq(1)
    colunas = ["Pedido_ID", "Transportadora", "Prazo_Entrega_Prometido", "Prazo_Entrega_Real", "Atraso_Entrega", "Frete", "Frete_Gratis"]
    quadro = dados.loc[mascara, colunas].copy()
    quadro.insert(0, "diferenca_dias", diferenca.loc[mascara])
    quadro = quadro.drop_duplicates().sort_values(["Atraso_Entrega", "Pedido_ID"])
    quadro["classificacao"] = "fronteira_ambigua_um_dia"
    quadro["decisao_silver"] = "preservar_valor_origem"
    return quadro


def criar_resumo(resultados):
    registros = []
    for analise, quadro in resultados.items():
        coluna_classe = next((c for c in ["classificacao", "classificacao_contextual", "causa_provavel"] if c in quadro), None)
        if quadro.empty:
            registros.append({"analise": analise, "classificacao": "sem_casos", "quantidade": 0})
        elif coluna_classe:
            for classe, qtd in quadro[coluna_classe].value_counts(dropna=False).items():
                registros.append({"analise": analise, "classificacao": classe, "quantidade": int(qtd)})
        else:
            registros.append({"analise": analise, "classificacao": "casos_identificados", "quantidade": len(quadro)})
    return pd.DataFrame(registros)


def ajustar_planilhas(writer):
    cor = PatternFill(fill_type="solid", fgColor="1F4E78")
    fonte = Font(color="FFFFFF", bold=True)
    for planilha in writer.book.worksheets:
        planilha.freeze_panes = "A2"
        planilha.auto_filter.ref = planilha.dimensions
        for celula in planilha[1]:
            celula.fill = cor
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
    print("Iniciando investigação contextual das inconsistências...")
    dados, manifesto, _contrato = carregar_entradas()
    grupos = classificar_colunas(dados, manifesto)
    validar_step_06(manifesto)
    preparado = preparar_dados(dados)
    resultados = {
        "idade": investigar_idade(dados, preparado),
        "renda": investigar_renda(dados, preparado),
        "quantidade": investigar_quantidade(dados, preparado),
        "valor_compra": investigar_valor_compra(dados, preparado),
        "cupom": investigar_cupom(dados, preparado),
        "atraso_um_dia": investigar_atraso(dados, preparado),
    }
    resumo_decisoes = criar_resumo(resultados)
    calculos_cliente = pd.read_excel(STEP_06_PATH, sheet_name="calculos_cliente")
    ciclo_vida = pd.read_excel(STEP_06_PATH, sheet_name="ciclo_vida_resumo")
    excluidas = pd.DataFrame([
        {"coluna": c, "classificacao": "ground_truth_dq", "participou_da_descoberta": False}
        for c in grupos["dq"]
    ])
    resumo_execucao = pd.DataFrame([{
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "etapa": "07_investigacao_contextual_inconsistencias",
        "arquivo_bronze": BRONZE_PATH.name,
        "sha256_bronze": manifesto["bronze"]["sha256"],
        "total_linhas": len(dados), "total_clientes": dados["Cliente_ID"].nunique(),
        "total_pedidos": dados["Pedido_ID"].nunique(), "step_06_validado": True,
        "dados_modificados": False, "dq_usado_na_descoberta": False, "status": "success",
    }])
    planilhas = [
        ("resumo_execucao", resumo_execucao), ("decisoes_resumo", resumo_decisoes),
        ("idade_investigacao", resultados["idade"]),
        ("renda_investigacao", resultados["renda"]),
        ("quantidade_investigacao", resultados["quantidade"]),
        ("valor_compra_investigacao", resultados["valor_compra"]),
        ("cupom_investigacao", resultados["cupom"]),
        ("atraso_um_dia", resultados["atraso_um_dia"]),
        ("calculos_cliente", calculos_cliente), ("ciclo_vida_resumo", ciclo_vida),
        ("colunas_excluidas", excluidas),
    ]
    salvar_relatorio(planilhas)
    print("[OK] Etapa 6 validada")
    print(f"[OK] Relatório gerado: {OUTPUT_PATH}")
    print("RESULTADO_FINAL: APROVADO")
    return True


if __name__ == "__main__":
    try:
        sys.exit(0 if executar() else 1)
    except Exception as erro:
        print("RESULTADO_FINAL: REPROVADO")
        print(f"ERRO: {type(erro).__name__}: {erro}")
        sys.exit(1)
