import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill

from step_06_validacao_tipos_dominios_regras import BRONZE_PATH, OUTPUT_DIR
from step_07_investigacao_contextual_inconsistencias import (
    OUTPUT_PATH as STEP_07_PATH,
    STEP_06_PATH,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_PATH = OUTPUT_DIR / "step_08_plano_tratamento_normalizacao_silver.xlsx"
STEP_04_PATH = OUTPUT_DIR / "step_04_analise_granularidade_chaves.xlsx"
STEP_05_PATH = OUTPUT_DIR / "step_05_investigacao_dados_ausentes.xlsx"

ACOES_VALIDAS = {
    "corrigir_deterministicamente",
    "preservar_valor_origem",
    "padronizar_sem_alterar_significado",
    "manter_pendente_regra_negocio",
    "recalcular_validacao_apos_correcao",
    "excluir_pedido_sem_evidencia_logistica",
}


def ler_aba(caminho, aba):
    return pd.read_excel(caminho, sheet_name=aba)


def validar_dependencias():
    for caminho in [STEP_04_PATH, STEP_05_PATH, STEP_06_PATH, STEP_07_PATH]:
        if not caminho.is_file():
            raise FileNotFoundError(f"Relatório obrigatório ausente: {caminho}")

    resumos = {
        numero: ler_aba(caminho, "resumo_execucao")
        for numero, caminho in {
            4: STEP_04_PATH, 5: STEP_05_PATH,
            6: STEP_06_PATH, 7: STEP_07_PATH,
        }.items()
    }

    for numero, resumo in resumos.items():
        if resumo.empty or resumo.iloc[0].get("status") != "success":
            raise ValueError(f"A Etapa {numero} não possui status success.")

    hashes = {
        resumo.iloc[0].get("sha256_bronze")
        for resumo in resumos.values()
    }
    if len(hashes) != 1:
        raise ValueError("As Etapas 4 a 7 não analisaram a mesma Bronze.")

    for numero, resumo in resumos.items():
        if bool(resumo.iloc[0].get("dados_modificados", True)):
            raise ValueError(f"A Etapa {numero} informa modificação dos dados de origem.")

    return {numero: resumo.iloc[0] for numero, resumo in resumos.items()}


def carregar_resultados_etapa_07():
    abas = [
        "idade_investigacao",
        "renda_investigacao",
        "quantidade_investigacao",
        "valor_compra_investigacao",
        "cupom_investigacao",
        "atraso_um_dia",
        "calculos_cliente",
        "ciclo_vida_resumo",
        "colunas_excluidas",
    ]
    return {aba: ler_aba(STEP_07_PATH, aba) for aba in abas}


def carregar_resultados_anteriores():
    return {
        "duplicidade_detalhes": ler_aba(STEP_04_PATH, "duplicidade_detalhes"),
        "duplicidade_resumo": ler_aba(STEP_04_PATH, "duplicidade_resumo"),
        "categoria_item_nulos": ler_aba(STEP_05_PATH, "categoria_item_nulos"),
        "cidade_nulos": ler_aba(STEP_05_PATH, "cidade_nulos"),
        "escolaridade_nulos": ler_aba(STEP_05_PATH, "escolaridade_nulos"),
        "logistica_nulos": ler_aba(STEP_05_PATH, "logistica_nulos"),
        "item_mapeamento_detalhes": ler_aba(
            STEP_04_PATH, "item_mapeamento_detalhes"
        ),
        "item_mapa_canonico": ler_aba(STEP_04_PATH, "item_mapa_canonico"),
    }


def normalizar_chave_textual(valor):
    if pd.isna(valor):
        return pd.NA
    texto = " ".join(str(valor).strip().casefold().split())
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )


def criar_plano_deduplicacao(anteriores):
    detalhes = anteriores["duplicidade_detalhes"].copy()
    detalhes = detalhes.sort_values(
        ["_duplicate_group_id", "_source_row_number"]
    )
    detalhes["ordem_no_grupo"] = detalhes.groupby(
        "_duplicate_group_id"
    ).cumcount() + 1
    detalhes["acao_silver"] = np.where(
        detalhes["ordem_no_grupo"].eq(1),
        "preservar_primeira_ocorrencia",
        "remover_excedente_duplicado",
    )
    detalhes["motivo"] = (
        "Duplicidade exata confirmada nas colunas analíticas da Etapa 4."
    )
    return detalhes[[
        "_duplicate_group_id", "_duplicate_group_size",
        "_source_row_number", "Pedido_ID", "Cliente_ID", "Id_Item",
        "ordem_no_grupo", "acao_silver", "motivo",
    ]]


def linhas_excedentes(plano_deduplicacao):
    return set(
        plano_deduplicacao.loc[
            plano_deduplicacao["acao_silver"].eq(
                "remover_excedente_duplicado"
            ),
            "_source_row_number",
        ].astype(int)
    )


def contar(quadro, coluna=None, valor=None):
    if coluna is None:
        return int(len(quadro))
    return int(quadro[coluna].eq(valor).sum())


def criar_matriz_tratamento(resultados, anteriores, total_linhas):
    idade = resultados["idade_investigacao"]
    renda = resultados["renda_investigacao"]
    quantidade = resultados["quantidade_investigacao"]
    valor = resultados["valor_compra_investigacao"]
    cupom = resultados["cupom_investigacao"]
    atraso = resultados["atraso_um_dia"].drop_duplicates("Pedido_ID")
    categoria = anteriores["categoria_item_nulos"]
    cidade = anteriores["cidade_nulos"]
    escolaridade = anteriores["escolaridade_nulos"]
    logistica = anteriores["logistica_nulos"]
    duplicidades = anteriores["duplicidade_resumo"].iloc[0]

    regras = [
        {
            "regra_id": "TR001", "campo": "Idade", "nivel_analitico": "cliente",
            "situacao": "idade_fora_16_100_com_historico_unico",
            "quantidade_casos": contar(idade, "classificacao", "recuperavel_deterministico"),
            "acao_silver": "corrigir_deterministicamente", "confianca": "alta",
            "regra_tratamento": "Substituir somente a ocorrência inválida pela idade válida única observada no histórico do mesmo Cliente_ID.",
            "evidencia": "Mesmo cliente possui um único valor válido com suporte histórico.",
            "altera_valor": True, "automatizavel": True,
        },
        {
            "regra_id": "TR002", "campo": "Renda_Mensal_Cliente", "nivel_analitico": "cliente",
            "situacao": "renda_negativa_ou_extrema_com_historico_unico",
            "quantidade_casos": int(((renda["classificacao_contextual"] == "erro_provavel") & (renda["recuperabilidade"] == "recuperavel_deterministico")).sum()),
            "acao_silver": "corrigir_deterministicamente", "confianca": "alta",
            "regra_tratamento": "Substituir o valor inválido pela renda válida única observada no histórico do mesmo Cliente_ID.",
            "evidencia": "Valor negativo ou extremo e candidato histórico sem conflito.",
            "altera_valor": True, "automatizavel": True,
        },
        {
            "regra_id": "TR003", "campo": "Renda_Mensal_Cliente", "nivel_analitico": "cliente",
            "situacao": "renda_negativa_ou_extrema_sem_evidencia",
            "quantidade_casos": int(((renda["classificacao_contextual"] == "erro_provavel") & (renda["recuperabilidade"] == "sem_evidencia")).sum()),
            "acao_silver": "corrigir_deterministicamente", "confianca": "alta",
            "regra_tratamento": "Preservar o valor original na auditoria e substituir o valor impossível por nulo, sem imputação estatística.",
            "evidencia": "Valor negativo ou sentinela extrema não representa renda válida; não existe evidência segura para imputar outro valor.",
            "altera_valor": True, "automatizavel": True,
        },
        {
            "regra_id": "TR004", "campo": "Renda_Mensal_Cliente", "nivel_analitico": "cliente",
            "situacao": "renda_zero_contextualmente_plausivel",
            "quantidade_casos": contar(renda, "classificacao_contextual", "zero_contextualmente_plausivel"),
            "acao_silver": "preservar_valor_origem", "confianca": "alta",
            "regra_tratamento": "Manter zero quando profissão ou situação profissional sustentar ausência de renda.",
            "evidencia": "Contexto de estudante, desempregado ou sem ocupação.",
            "altera_valor": False, "automatizavel": True,
        },
        {
            "regra_id": "TR005", "campo": "Quantidade", "nivel_analitico": "item_do_pedido",
            "situacao": "quantidade_zero_ou_extrema_com_candidato_exato",
            "quantidade_casos": int(quantidade["classificacao_contextual"].isin(["quantidade_invalida", "quantidade_extrema_provavel_erro"]).sum()),
            "acao_silver": "corrigir_deterministicamente", "confianca": "alta",
            "regra_tratamento": "Usar a quantidade inteira que reproduz Valor_Compra a partir de preço e desconto, somente quando candidato_reproduz_valor for verdadeiro.",
            "evidencia": "O candidato inteiro recompõe o valor monetário dentro da tolerância da investigação.",
            "altera_valor": True, "automatizavel": True,
        },
        {
            "regra_id": "TR006", "campo": "Quantidade", "nivel_analitico": "item_do_pedido",
            "situacao": "quantidade_7_ou_8_plausivel",
            "quantidade_casos": contar(quantidade, "classificacao_contextual", "quantidade_alta_plausivel"),
            "acao_silver": "preservar_valor_origem", "confianca": "alta",
            "regra_tratamento": "Manter o valor informado; magnitude incomum não constitui erro de domínio.",
            "evidencia": "Quantidade positiva, inteira e compatível com o valor da compra.",
            "altera_valor": False, "automatizavel": True,
        },
        {
            "regra_id": "TR007", "campo": "Cupom_Utilizado", "nivel_analitico": "item_do_pedido",
            "situacao": "desconto_promocional_sem_cupom",
            "quantidade_casos": contar(cupom, "classificacao", "desconto_positivo_com_cupom_nao"),
            "acao_silver": "preservar_valor_origem", "confianca": "alta",
            "regra_tratamento": "Manter Cupom_Utilizado = Não quando o desconto estiver associado à campanha e o valor refletir o desconto.",
            "evidencia": "Os casos observados estão associados à Black Friday; desconto de campanha não exige cupom.",
            "altera_valor": False, "automatizavel": True,
        },
        {
            "regra_id": "TR008", "campo": "Cupom_Utilizado", "nivel_analitico": "item_do_pedido",
            "situacao": "cupom_ausente",
            "quantidade_casos": contar(cupom, "classificacao", "cupom_ausente"),
            "acao_silver": "manter_pendente_regra_negocio", "confianca": "insuficiente",
            "regra_tratamento": "Não converter ausência em Sim ou Não sem regra comercial ou evidência transacional adicional.",
            "evidencia": "Há casos com campanha e sem campanha, e o valor não permite inferência inequívoca.",
            "altera_valor": False, "automatizavel": False,
        },
        {
            "regra_id": "TR009", "campo": "Valor_Compra", "nivel_analitico": "item_do_pedido",
            "situacao": "divergencia_causada_por_quantidade_invalida_ou_extrema",
            "quantidade_casos": int(valor["causa_provavel"].isin(["quantidade_invalida", "quantidade_extrema"]).sum()),
            "acao_silver": "recalcular_validacao_apos_correcao", "confianca": "alta",
            "regra_tratamento": "Corrigir Quantidade primeiro e revalidar a fórmula. Preservar Valor_Compra quando ele passar a ser compatível.",
            "evidencia": "O valor informado permite recuperar a quantidade inteira nos mesmos registros.",
            "altera_valor": False, "automatizavel": True,
        },
        {
            "regra_id": "TR010", "campo": "Valor_Compra", "nivel_analitico": "item_do_pedido",
            "situacao": "formula_ou_origem_a_investigar",
            "quantidade_casos": contar(valor, "causa_provavel", "formula_ou_origem_a_investigar"),
            "acao_silver": "corrigir_deterministicamente", "confianca": "alta",
            "regra_tratamento": "Recalcular o valor líquido como Quantidade × Preço de Lista × (1 - Desconto/100), arredondando para duas casas decimais.",
            "evidencia": "A definição aprovada para Valor_Compra é valor líquido; os casos divergentes coincidem exatamente com o valor bruto.",
            "altera_valor": True, "automatizavel": True,
        },
        {
            "regra_id": "TR011", "campo": "Atraso_Entrega", "nivel_analitico": "pedido",
            "situacao": "fronteira_ambigua_um_dia",
            "quantidade_casos": int(atraso["Pedido_ID"].nunique()),
            "acao_silver": "preservar_valor_origem", "confianca": "alta_para_preservacao",
            "regra_tratamento": "Manter a classificação original e registrar a diferença de um dia para auditoria.",
            "evidencia": "A base apresenta Sim e Não na mesma fronteira; pode existir horário de corte ou regra operacional ausente.",
            "altera_valor": False, "automatizavel": True,
        },
        {
            "regra_id": "TR012", "campo": "Intervalo_Medio_Compras_Dias", "nivel_analitico": "cliente",
            "situacao": "formula_nao_confirmada",
            "quantidade_casos": 211,
            "acao_silver": "preservar_valor_origem", "confianca": "alta_para_preservacao",
            "regra_tratamento": "Manter como atributo histórico; não substituir pela média recalculada apenas com compras de 2025.",
            "evidencia": "74,5583% dos clientes avaliados divergem e o campo possui somente sete valores discretos.",
            "altera_valor": False, "automatizavel": True,
        },
        {
            "regra_id": "TR013", "campo": "Ticket_Medio_Cliente", "nivel_analitico": "cliente",
            "situacao": "formula_nao_confirmada",
            "quantidade_casos": 331,
            "acao_silver": "preservar_valor_origem", "confianca": "alta_para_preservacao",
            "regra_tratamento": "Manter como atributo histórico; não substituir pelo ticket recalculado no recorte de 2025.",
            "evidencia": "Todos os clientes divergiram da fórmula testada.",
            "altera_valor": False, "automatizavel": True,
        },
        {
            "regra_id": "TR014", "campo": "Pontos_Fidelidade", "nivel_analitico": "cliente",
            "situacao": "formula_nao_confirmada",
            "quantidade_casos": 331,
            "acao_silver": "preservar_valor_origem", "confianca": "alta_para_preservacao",
            "regra_tratamento": "Manter o valor informado até que a política de fidelidade seja conhecida.",
            "evidencia": "As correlações exploratórias não identificam uma fórmula determinística.",
            "altera_valor": False, "automatizavel": True,
        },
        {
            "regra_id": "TR015", "campo": "Ciclo_Vida_Cliente", "nivel_analitico": "cliente",
            "situacao": "classificacao_multifatorial_sem_formula_confirmada",
            "quantidade_casos": 331,
            "acao_silver": "preservar_valor_origem", "confianca": "alta_para_preservacao",
            "regra_tratamento": "Manter a categoria original e documentar que sua regra não foi reconstruída.",
            "evidencia": "Recência, frequência, valor e intervalo explicam parte dos grupos, mas não toda a classificação.",
            "altera_valor": False, "automatizavel": True,
        },
        {
            "regra_id": "TR016", "campo": "colunas_tipadas", "nivel_analitico": "conforme_campo",
            "situacao": "tipagem_fisica_da_bronze_em_texto",
            "quantidade_casos": int(total_linhas),
            "acao_silver": "padronizar_sem_alterar_significado", "confianca": "alta",
            "regra_tratamento": "Converter para os tipos definidos na Etapa 6, preservando as colunas originais na Bronze e bloqueando falhas de conversão.",
            "evidencia": "A Etapa 6 obteve 100% de conversão nos campos avaliados.",
            "altera_valor": False, "automatizavel": True,
        },
        {
            "regra_id": "TR017", "campo": "linha_completa", "nivel_analitico": "item_do_pedido",
            "situacao": "duplicidade_exata_excedente",
            "quantidade_casos": int(duplicidades["linhas_excedentes_duplicadas"]),
            "acao_silver": "corrigir_deterministicamente", "confianca": "alta",
            "regra_tratamento": "Preservar a primeira ocorrência pela ordem da fonte e remover somente as ocorrências excedentes do mesmo grupo exato.",
            "evidencia": "A Etapa 4 confirmou igualdade em todas as colunas analíticas.",
            "altera_valor": False, "automatizavel": True,
        },
        {
            "regra_id": "TR018", "campo": "Categoria_Item", "nivel_analitico": "item_do_pedido",
            "situacao": "categoria_ausente_com_candidato_unico",
            "quantidade_casos": contar(categoria, "classificacao_preliminar", "recuperavel_deterministico"),
            "acao_silver": "corrigir_deterministicamente", "confianca": "alta",
            "regra_tratamento": "Preencher pela categoria normalizada única associada ao mesmo Id_Item.",
            "evidencia": "O grupo do item possui uma única categoria após normalização textual.",
            "altera_valor": True, "automatizavel": True,
        },
        {
            "regra_id": "TR019", "campo": "Categoria_Item", "nivel_analitico": "item_do_pedido",
            "situacao": "categoria_ausente_com_conflito_no_item",
            "quantidade_casos": contar(categoria, "classificacao_preliminar", "candidato_com_conflito_no_grupo"),
            "acao_silver": "corrigir_deterministicamente", "confianca": "alta",
            "regra_tratamento": "Preencher pela categoria canônica aprovada para o mesmo Id_Item.",
            "evidencia": "A revisão analítica aprovou o mapa canônico do item como referência cadastral.",
            "altera_valor": True, "automatizavel": True,
        },
        {
            "regra_id": "TR020", "campo": "Cidade", "nivel_analitico": "cliente",
            "situacao": "cidade_ausente_com_historico_unico",
            "quantidade_casos": contar(cidade, "classificacao_preliminar", "recuperavel_deterministico"),
            "acao_silver": "corrigir_deterministicamente", "confianca": "alta",
            "regra_tratamento": "Preencher pela cidade normalizada única observada no histórico do mesmo Cliente_ID.",
            "evidencia": "Histórico interno do cliente sem conflito geográfico.",
            "altera_valor": True, "automatizavel": True,
        },
        {
            "regra_id": "TR021", "campo": "Cidade", "nivel_analitico": "cliente",
            "situacao": "cidade_ausente_sem_evidencia",
            "quantidade_casos": contar(cidade, "classificacao_preliminar", "nao_recuperavel_internamente"),
            "acao_silver": "manter_pendente_regra_negocio", "confianca": "insuficiente",
            "regra_tratamento": "Manter nulo; Estado isoladamente não identifica uma cidade.",
            "evidencia": "Não existe cidade informada para o mesmo Cliente_ID.",
            "altera_valor": False, "automatizavel": False,
        },
        {
            "regra_id": "TR022", "campo": "Escolaridade", "nivel_analitico": "cliente",
            "situacao": "escolaridade_ausente_com_historico_unico",
            "quantidade_casos": contar(escolaridade, "classificacao_preliminar", "recuperavel_deterministico"),
            "acao_silver": "corrigir_deterministicamente", "confianca": "alta",
            "regra_tratamento": "Preencher pela escolaridade normalizada única observada no histórico do mesmo Cliente_ID.",
            "evidencia": "Todos os casos possuem candidato interno sem conflito.",
            "altera_valor": True, "automatizavel": True,
        },
        {
            "regra_id": "TR023", "campo": "logistica", "nivel_analitico": "pedido",
            "situacao": "campos_logisticos_ausentes_recuperaveis_no_pedido",
            "quantidade_casos": contar(logistica, "classificacao_preliminar", "recuperavel_por_mesmo_pedido"),
            "acao_silver": "corrigir_deterministicamente", "confianca": "alta",
            "regra_tratamento": "Preencher Transportadora, Prazo_Entrega_Real e Atraso_Entrega pelos valores únicos das demais linhas do mesmo Pedido_ID.",
            "evidencia": "Os três atributos pertencem ao pedido e possuem candidato único nas outras linhas.",
            "altera_valor": True, "automatizavel": True,
        },
        {
            "regra_id": "TR024", "campo": "logistica", "nivel_analitico": "pedido",
            "situacao": "campos_logisticos_ausentes_sem_evidencia",
            "quantidade_casos": contar(logistica, "classificacao_preliminar", "sem_evidencia_no_mesmo_pedido"),
            "acao_silver": "manter_pendente_regra_negocio", "confianca": "insuficiente",
            "regra_tratamento": "Manter os campos nulos quando todo o pedido não possui evidência logística.",
            "evidencia": "Não há valor informado nas demais linhas do mesmo Pedido_ID.",
            "altera_valor": False, "automatizavel": False,
        },
        {
            "regra_id": "TR025", "campo": "Produto", "nivel_analitico": "item_do_pedido",
            "situacao": "produto_legado_descontinuado",
            "quantidade_casos": int((criar_correcoes_itens(anteriores)["regra_id"] == "TR025").sum()),
            "acao_silver": "corrigir_deterministicamente", "confianca": "alta",
            "regra_tratamento": "Substituir a descrição legada pelo produto canônico aprovado para o mesmo Id_Item.",
            "evidencia": "O Id_Item identifica univocamente o produto vigente no mapa canônico.",
            "altera_valor": True, "automatizavel": True,
        },
        {
            "regra_id": "TR026", "campo": "Categoria_Item", "nivel_analitico": "item_do_pedido",
            "situacao": "categoria_semanticamente_incorreta",
            "quantidade_casos": int((criar_correcoes_itens(anteriores)["regra_id"] == "TR026").sum()),
            "acao_silver": "corrigir_deterministicamente", "confianca": "alta",
            "regra_tratamento": "Substituir a categoria divergente pela categoria canônica aprovada para o Id_Item.",
            "evidencia": "Produto, medida e frequência dominante confirmam a categoria cadastral correta.",
            "altera_valor": True, "automatizavel": True,
        },
    ]
    return pd.DataFrame(regras)


def registro_correcao(quadro, campo, original, proposto, regra_id, evidencia):
    base = pd.DataFrame({
        "regra_id": regra_id,
        "_source_row_number": quadro["_source_row_number"],
        "Pedido_ID": quadro["Pedido_ID"] if "Pedido_ID" in quadro else pd.NA,
        "Cliente_ID": quadro["Cliente_ID"] if "Cliente_ID" in quadro else pd.NA,
        "Id_Item": quadro["Id_Item"] if "Id_Item" in quadro else pd.NA,
        "campo": campo,
        "valor_original": quadro[original],
        "valor_proposto": quadro[proposto],
        "acao_silver": "corrigir_deterministicamente",
        "confianca": "alta",
        "evidencia": evidencia,
        "aplicado_nesta_etapa": False,
    })
    return base


def criar_correcoes_ausencias(anteriores):
    especificacoes = [
        ("TR018", "Categoria_Item", anteriores["categoria_item_nulos"],
         "recuperavel_deterministico", "valor_original", "candidato_recuperacao",
         "categoria única normalizada do mesmo Id_Item"),
        ("TR020", "Cidade", anteriores["cidade_nulos"],
         "recuperavel_deterministico", "valor_original", "candidato_recuperacao",
         "cidade única normalizada do mesmo Cliente_ID"),
        ("TR022", "Escolaridade", anteriores["escolaridade_nulos"],
         "recuperavel_deterministico", "valor_original", "candidato_recuperacao",
         "escolaridade única normalizada do mesmo Cliente_ID"),
    ]
    quadros = []
    for regra, campo, quadro, classe, original, proposto, evidencia in especificacoes:
        selecionado = quadro[quadro["classificacao_preliminar"].eq(classe)].copy()
        quadros.append(registro_correcao(
            selecionado, campo, original, proposto, regra, evidencia
        ))

    logistica = anteriores["logistica_nulos"]
    logistica = logistica[
        logistica["classificacao_preliminar"].eq("recuperavel_por_mesmo_pedido")
    ].copy()
    for campo in ["Transportadora", "Prazo_Entrega_Real", "Atraso_Entrega"]:
        quadros.append(registro_correcao(
            logistica, campo, campo, f"{campo}_candidato", "TR023",
            f"{campo} único nas demais linhas do mesmo Pedido_ID",
        ))
    return pd.concat(quadros, ignore_index=True)


def criar_correcoes_itens(anteriores):
    detalhes = anteriores["item_mapeamento_detalhes"].copy()
    mapa = anteriores["item_mapa_canonico"][[
        "Id_Item", "produto_canonico_candidato", "categoria_canonica_candidata",
    ]]
    base = detalhes.merge(mapa, on="Id_Item", how="left", validate="many_to_one")
    registros = []

    for _, linha in base.iterrows():
        linhas_fonte = [
            int(numero.strip())
            for numero in str(linha["linhas_fonte"]).split("|")
            if numero.strip()
        ]
        produto_atual = normalizar_chave_textual(linha["Produto"])
        produto_canonico = normalizar_chave_textual(
            linha["produto_canonico_candidato"]
        )
        categoria_atual = normalizar_chave_textual(linha["Categoria_Item"])
        categoria_canonica = normalizar_chave_textual(
            linha["categoria_canonica_candidata"]
        )

        correcoes_linha = []
        if pd.notna(produto_atual) and produto_atual != produto_canonico:
            correcoes_linha.append((
                "TR025", "Produto", linha["Produto"],
                linha["produto_canonico_candidato"],
                "produto canônico aprovado para o mesmo Id_Item",
            ))
        if pd.isna(categoria_atual):
            correcoes_linha.append((
                "TR019", "Categoria_Item", linha["Categoria_Item"],
                linha["categoria_canonica_candidata"],
                "categoria canônica aprovada para Id_Item com conflito cadastral",
            ))
        elif categoria_atual != categoria_canonica:
            correcoes_linha.append((
                "TR026", "Categoria_Item", linha["Categoria_Item"],
                linha["categoria_canonica_candidata"],
                "categoria canônica aprovada para o mesmo Id_Item",
            ))

        for numero in linhas_fonte:
            for regra, campo, original, proposto, evidencia in correcoes_linha:
                registros.append({
                    "regra_id": regra,
                    "_source_row_number": numero,
                    "Pedido_ID": pd.NA,
                    "Cliente_ID": pd.NA,
                    "Id_Item": linha["Id_Item"],
                    "campo": campo,
                    "valor_original": original,
                    "valor_proposto": proposto,
                    "acao_silver": "corrigir_deterministicamente",
                    "confianca": "alta",
                    "evidencia": evidencia,
                    "aplicado_nesta_etapa": False,
                })
    return pd.DataFrame(registros)


def criar_correcoes_propostas(resultados, anteriores, excedentes):
    idade = resultados["idade_investigacao"]
    idade = idade[idade["classificacao"] == "recuperavel_deterministico"].copy()

    renda = resultados["renda_investigacao"]
    renda = renda[
        (renda["classificacao_contextual"] == "erro_provavel")
        & (renda["recuperabilidade"] == "recuperavel_deterministico")
    ].copy()

    quantidade = resultados["quantidade_investigacao"]
    quantidade = quantidade[
        quantidade["classificacao_contextual"].isin(
            ["quantidade_invalida", "quantidade_extrema_provavel_erro"]
        )
        & quantidade["candidato_reproduz_valor"].eq(True)
    ].copy()

    renda_sem_evidencia = resultados["renda_investigacao"]
    renda_sem_evidencia = renda_sem_evidencia[
        (renda_sem_evidencia["classificacao_contextual"] == "erro_provavel")
        & (renda_sem_evidencia["recuperabilidade"] == "sem_evidencia")
    ].copy()
    renda_sem_evidencia["valor_proposto_nulo"] = pd.NA

    valor_liquido = resultados["valor_compra_investigacao"]
    valor_liquido = valor_liquido[
        valor_liquido["causa_provavel"] == "formula_ou_origem_a_investigar"
    ].copy()
    valor_liquido["valor_liquido_aprovado"] = valor_liquido[
        "valor_recalculado"
    ].round(2)

    quadros = [
        registro_correcao(
            idade, "Idade", "idade_invalida", "candidato_idade", "TR001",
            "idade válida única no histórico do mesmo cliente",
        ),
        registro_correcao(
            renda, "Renda_Mensal_Cliente", "renda_investigada",
            "candidato_renda_historico", "TR002",
            "renda válida única no histórico do mesmo cliente",
        ),
        registro_correcao(
            quantidade, "Quantidade", "quantidade_informada",
            "candidato_quantidade_inteira", "TR005",
            "quantidade inteira recompõe o valor da compra",
        ),
        registro_correcao(
            renda_sem_evidencia, "Renda_Mensal_Cliente", "renda_investigada",
            "valor_proposto_nulo", "TR003",
            "valor impossível convertido em nulo sem imputação",
        ),
        registro_correcao(
            valor_liquido, "Valor_Compra", "valor_informado",
            "valor_liquido_aprovado", "TR010",
            "valor líquido recalculado pela fórmula aprovada",
        ),
    ]
    quadros.append(criar_correcoes_ausencias(anteriores))
    quadros.append(criar_correcoes_itens(anteriores))
    resultado = pd.concat(quadros, ignore_index=True)
    resultado["chave_auditoria"] = (
        resultado["_source_row_number"].astype("Int64").astype("string")
        + "|" + resultado["campo"].astype("string")
    )
    resultado = resultado.drop_duplicates("chave_auditoria", keep="first")
    resultado["linha_removida_por_deduplicacao"] = resultado[
        "_source_row_number"
    ].astype(int).isin(excedentes)
    resultado["aplicavel_apos_deduplicacao"] = ~resultado[
        "linha_removida_por_deduplicacao"
    ]
    return resultado[
        ["chave_auditoria", "regra_id", "_source_row_number", "Pedido_ID",
         "Cliente_ID", "Id_Item", "campo", "valor_original", "valor_proposto",
         "acao_silver", "confianca", "evidencia",
         "linha_removida_por_deduplicacao", "aplicavel_apos_deduplicacao",
         "aplicado_nesta_etapa"]
    ]


def criar_preservacoes(resultados):
    renda = resultados["renda_investigacao"]
    quantidade = resultados["quantidade_investigacao"]
    cupom = resultados["cupom_investigacao"]
    atraso = resultados["atraso_um_dia"].drop_duplicates("Pedido_ID")

    registros = [
        {
            "regra_id": "TR004", "campo": "Renda_Mensal_Cliente",
            "situacao": "renda_zero_contextualmente_plausivel",
            "registros": contar(renda, "classificacao_contextual", "zero_contextualmente_plausivel"),
            "motivo": "O contexto profissional sustenta renda igual a zero.",
        },
        {
            "regra_id": "TR006", "campo": "Quantidade",
            "situacao": "quantidade_7_ou_8_plausivel",
            "registros": contar(quantidade, "classificacao_contextual", "quantidade_alta_plausivel"),
            "motivo": "Valor positivo, inteiro e monetariamente compatível.",
        },
        {
            "regra_id": "TR007", "campo": "Cupom_Utilizado",
            "situacao": "desconto_promocional_sem_cupom",
            "registros": contar(cupom, "classificacao", "desconto_positivo_com_cupom_nao"),
            "motivo": "Desconto associado à campanha Black Friday.",
        },
        {
            "regra_id": "TR011", "campo": "Atraso_Entrega",
            "situacao": "fronteira_ambigua_um_dia",
            "registros": int(atraso["Pedido_ID"].nunique()),
            "motivo": "Não há regra suficiente para substituir a classificação de origem.",
        },
    ]
    return pd.DataFrame(registros)


def criar_pendencias(resultados, anteriores, excedentes):
    cupom = resultados["cupom_investigacao"]
    cupom_pendente = cupom[cupom["classificacao"] == "cupom_ausente"]

    registros = []
    for regra_id, campo, quadro, original, motivo in [
        ("TR008", "Cupom_Utilizado", cupom_pendente, "Cupom_Utilizado",
         "Ausência não diferencia não utilização de falha de registro."),
    ]:
        for _, linha in quadro.iterrows():
            registros.append({
                "regra_id": regra_id,
                "_source_row_number": linha.get("_source_row_number"),
                "Pedido_ID": linha.get("Pedido_ID"),
                "Cliente_ID": linha.get("Cliente_ID"),
                "Id_Item": linha.get("Id_Item"),
                "campo": campo,
                "valor_original": linha.get(original),
                "acao_silver": "manter_pendente_regra_negocio",
                "motivo_pendencia": motivo,
                "aplicado_nesta_etapa": False,
            })

    cidade = anteriores["cidade_nulos"]
    cidade = cidade[
        cidade["classificacao_preliminar"].eq("nao_recuperavel_internamente")
    ]
    logistica = anteriores["logistica_nulos"]
    logistica = logistica[
        logistica["classificacao_preliminar"].eq("sem_evidencia_no_mesmo_pedido")
    ]

    for regra_id, campo, quadro, original, motivo in [
        ("TR021", "Cidade", cidade, "valor_original",
         "Não existe cidade informada no histórico do cliente."),
    ]:
        for _, linha in quadro.iterrows():
            registros.append({
                "regra_id": regra_id,
                "_source_row_number": linha.get("_source_row_number"),
                "Pedido_ID": linha.get("Pedido_ID"),
                "Cliente_ID": linha.get("Cliente_ID"),
                "Id_Item": linha.get("Id_Item"),
                "campo": campo,
                "valor_original": linha.get(original),
                "acao_silver": "manter_pendente_regra_negocio",
                "motivo_pendencia": motivo,
                "aplicado_nesta_etapa": False,
            })

    for _, linha in logistica.iterrows():
        for campo in ["Transportadora", "Prazo_Entrega_Real", "Atraso_Entrega"]:
            registros.append({
                "regra_id": "TR024",
                "_source_row_number": linha.get("_source_row_number"),
                "Pedido_ID": linha.get("Pedido_ID"),
                "Cliente_ID": linha.get("Cliente_ID"),
                "Id_Item": linha.get("Id_Item"),
                "campo": campo,
                "valor_original": linha.get(campo),
                "acao_silver": "manter_pendente_regra_negocio",
                "motivo_pendencia": "O pedido não possui evidência interna para o campo logístico.",
                "aplicado_nesta_etapa": False,
            })

    resultado = pd.DataFrame(registros)
    resultado["linha_removida_por_deduplicacao"] = resultado[
        "_source_row_number"
    ].astype(int).isin(excedentes)
    resultado["permanece_apos_deduplicacao"] = ~resultado[
        "linha_removida_por_deduplicacao"
    ]
    return resultado


def incorporar_decisoes_residuais(matriz, correcoes, pendencias, anteriores):
    """Incorpora somente as decisões manuais aprovadas após a Etapa 10."""
    fontes_renda_zero = {596, 2089, 2114}
    fonte_renda_estagiario = 3056
    fonte_cidade_df = 5571
    fontes_exclusao_logistica = {52, 152, 202}

    matriz.loc[matriz["regra_id"].eq("TR003"), "quantidade_casos"] = 1
    matriz.loc[matriz["regra_id"].isin(["TR021", "TR024"]), "quantidade_casos"] = 0

    mascara_renda_zero = (
        correcoes["campo"].eq("Renda_Mensal_Cliente")
        & correcoes["_source_row_number"].astype(int).isin(fontes_renda_zero)
    )
    if int(mascara_renda_zero.sum()) != 3:
        raise ValueError("As três ocorrências aprovadas de renda zero não foram localizadas.")
    correcoes.loc[mascara_renda_zero, "regra_id"] = "TR027"
    correcoes.loc[mascara_renda_zero, "valor_proposto"] = 0.0
    correcoes.loc[mascara_renda_zero, "evidencia"] = (
        "Decisão de negócio documentada: desempregado sem ocupação ou "
        "estudante bolsista com renda considerada igual a zero."
    )

    cidade = anteriores["cidade_nulos"].copy()
    cidade = cidade[cidade["_source_row_number"].astype(int).eq(fonte_cidade_df)]
    if len(cidade) != 1:
        raise ValueError("A ocorrência de Cidade nula no DF não foi localizada.")
    cidade["valor_proposto_brasilia"] = "Brasília"
    nova_correcao = registro_correcao(
        cidade, "Cidade", "valor_original", "valor_proposto_brasilia", "TR028",
        "Estado = DF e escopo de atendimento restrito a Brasília.",
    )
    nova_correcao["chave_auditoria"] = (
        nova_correcao["_source_row_number"].astype("Int64").astype("string")
        + "|" + nova_correcao["campo"].astype("string")
    )
    nova_correcao["linha_removida_por_deduplicacao"] = False
    nova_correcao["aplicavel_apos_deduplicacao"] = True
    nova_correcao = nova_correcao[correcoes.columns]
    correcoes = pd.concat([correcoes, nova_correcao], ignore_index=True)

    pendencias = pendencias[
        ~pendencias["_source_row_number"].astype(int).isin(
            fontes_exclusao_logistica | {fonte_cidade_df}
        )
    ].copy()
    renda_estagiario = correcoes[
        correcoes["_source_row_number"].astype(int).eq(fonte_renda_estagiario)
        & correcoes["campo"].eq("Renda_Mensal_Cliente")
    ].iloc[0]
    pendencia_estagiario = pd.DataFrame([{
        "regra_id": "TR029",
        "_source_row_number": fonte_renda_estagiario,
        "Pedido_ID": renda_estagiario["Pedido_ID"],
        "Cliente_ID": renda_estagiario["Cliente_ID"],
        "Id_Item": renda_estagiario["Id_Item"],
        "campo": "Renda_Mensal_Cliente",
        "valor_original": renda_estagiario["valor_original"],
        "acao_silver": "manter_pendente_regra_negocio",
        "motivo_pendencia": "Estagiário pode possuir remuneração; não há evidência segura do valor.",
        "aplicado_nesta_etapa": False,
        "linha_removida_por_deduplicacao": False,
        "permanece_apos_deduplicacao": True,
    }])
    pendencias = pd.concat([pendencias, pendencia_estagiario], ignore_index=True)

    logistica = anteriores["logistica_nulos"].copy()
    exclusoes = logistica[
        logistica["_source_row_number"].astype(int).isin(fontes_exclusao_logistica)
    ].drop_duplicates("_source_row_number").copy()
    if len(exclusoes) != 3:
        raise ValueError("Os três pedidos logísticos aprovados para exclusão não foram localizados.")
    exclusoes["regra_id"] = "TR030"
    exclusoes["acao_silver"] = "excluir_pedido_sem_evidencia_logistica"
    exclusoes["motivo"] = (
        "Ausência conjunta de transportadora, prazo real e atraso; "
        "pedido de linha única e sem evidência contextual."
    )

    novas_regras = pd.DataFrame([
        {"regra_id": "TR027", "campo": "Renda_Mensal_Cliente", "nivel_analitico": "cliente", "situacao": "renda_invalida_com_contexto_zero_aprovado", "quantidade_casos": 3, "acao_silver": "corrigir_deterministicamente", "confianca": "alta_ou_negocial", "regra_tratamento": "Substituir por zero apenas nos três registros aprovados.", "evidencia": "Contexto profissional e decisão de negócio documentada.", "altera_valor": True, "automatizavel": True},
        {"regra_id": "TR028", "campo": "Cidade", "nivel_analitico": "cliente", "situacao": "cidade_nula_estado_df_escopo_brasilia", "quantidade_casos": 1, "acao_silver": "corrigir_deterministicamente", "confianca": "alta", "regra_tratamento": "Preencher Brasília quando Estado = DF e Cidade estiver nula.", "evidencia": "Escopo de atendimento restrito a Brasília.", "altera_valor": True, "automatizavel": True},
        {"regra_id": "TR029", "campo": "Renda_Mensal_Cliente", "nivel_analitico": "cliente", "situacao": "renda_estagiario_sem_evidencia", "quantidade_casos": 1, "acao_silver": "manter_pendente_regra_negocio", "confianca": "insuficiente", "regra_tratamento": "Preservar nulo sem imputação.", "evidencia": "Estágio pode ser remunerado.", "altera_valor": False, "automatizavel": False},
        {"regra_id": "TR030", "campo": "linha_completa", "nivel_analitico": "pedido", "situacao": "logistica_ausente_sem_evidencia", "quantidade_casos": 3, "acao_silver": "excluir_pedido_sem_evidencia_logistica", "confianca": "media", "regra_tratamento": "Excluir os três pedidos de linha única e preservar cópia integral.", "evidencia": "Sem candidato contextual; impacto de 0,0462% das linhas.", "altera_valor": False, "automatizavel": True},
    ])
    matriz = pd.concat([matriz, novas_regras], ignore_index=True)

    catalogo = pd.DataFrame([
        ("DN001", "Cidade ausente no DF", "Preencher Brasília", "regra determinística", "aprovada"),
        ("DN002", "Renda de desempregado", "Definir renda zero", "regra contextual", "aprovada"),
        ("DN003", "Renda de bolsista", "Definir renda zero", "premissa de negócio", "aprovada"),
        ("DN004", "Renda de estagiário", "Preservar nulo", "evidência insuficiente", "aprovada"),
        ("DN005", "Logística sem evidência", "Excluir três pedidos e preservar rejeitados; o cliente 5 deixa a Silver transacional", "exclusão controlada e limitação documentada", "aprovada"),
        ("DN006", "Cupom ausente", "Preservar cinco nulos remanescentes", "evidência insuficiente", "aprovada"),
        ("DN007", "Random Forest", "Não utilizar", "poucos casos e ausência de alvo confiável", "aprovada"),
    ], columns=["decisao_id", "tema", "decisao", "fundamentacao", "status"])
    return matriz, correcoes, pendencias, exclusoes, catalogo


def criar_plano_tipagem():
    tipagem = ler_aba(STEP_06_PATH, "tipagem_resumo").copy()
    tipagem.insert(0, "regra_id", "TR016")
    tipagem["acao_silver"] = "padronizar_sem_alterar_significado"
    tipagem["bloquear_se_falhar"] = True
    tipagem["aplicado_nesta_etapa"] = False
    return tipagem


def criar_controles(matriz, correcoes, pendencias, resumo_07, plano_deduplicacao):
    chaves_duplicadas = int(correcoes["chave_auditoria"].duplicated().sum())
    propostas_nulas_invalidas = int((
        correcoes["valor_proposto"].isna()
        & ~correcoes["regra_id"].eq("TR003")
    ).sum())
    acoes_invalidas = int((~matriz["acao_silver"].isin(ACOES_VALIDAS)).sum())
    regras_sem_casos = int((matriz["quantidade_casos"] < 0).sum())
    controles = [
        ("step_04_status_success", True),
        ("step_05_status_success", True),
        ("step_07_status_success", True),
        ("hash_steps_04_a_07_iguais", True),
        ("bronze_modificada", False),
        ("silver_materializada", False),
        ("chaves_correcao_duplicadas", chaves_duplicadas),
        ("valores_propostos_nulos_invalidos", propostas_nulas_invalidas),
        ("acoes_fora_do_dominio", acoes_invalidas),
        ("quantidades_negativas_na_matriz", regras_sem_casos),
        ("total_linhas_bronze", int(resumo_07["total_linhas"])),
        ("linhas_excedentes_para_remocao", int((plano_deduplicacao["acao_silver"] == "remover_excedente_duplicado").sum())),
        ("correcoes_deterministicas_propostas_bronze", int(len(correcoes))),
        ("correcoes_aplicaveis_apos_deduplicacao", int(correcoes["aplicavel_apos_deduplicacao"].sum())),
        ("casos_pendentes_detalhados_bronze", int(len(pendencias))),
        ("pendencias_apos_deduplicacao", int(pendencias["permanece_apos_deduplicacao"].sum())),
    ]
    quadro = pd.DataFrame(controles, columns=["controle", "resultado"])
    quadro["status"] = np.where(
        quadro["controle"].isin([
            "chaves_correcao_duplicadas", "valores_propostos_nulos_invalidos",
            "acoes_fora_do_dominio", "quantidades_negativas_na_matriz",
        ]),
        np.where(quadro["resultado"].eq(0), "aprovado", "reprovado"),
        "informativo",
    )
    return quadro


def validar_saidas(matriz, correcoes, controles):
    if matriz["regra_id"].duplicated().any():
        raise ValueError("Existem regra_id duplicadas na matriz de tratamento.")
    if not matriz["acao_silver"].isin(ACOES_VALIDAS).all():
        raise ValueError("A matriz contém ação Silver fora do domínio permitido.")
    if correcoes["chave_auditoria"].duplicated().any():
        raise ValueError("Uma mesma linha e campo receberam mais de uma correção.")
    nulos_invalidos = correcoes["valor_proposto"].isna() & ~correcoes[
        "regra_id"
    ].eq("TR003")
    if nulos_invalidos.any():
        raise ValueError("Existem correções sem valor proposto fora da TR003.")
    if (controles["status"] == "reprovado").any():
        raise ValueError("Um ou mais controles de auditoria foram reprovados.")


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
        planilha.row_dimensions[1].height = 32
        for coluna in planilha.columns:
            largura = min(
                max(len(str(celula.value)) if celula.value is not None else 0 for celula in coluna) + 2,
                60,
            )
            planilha.column_dimensions[coluna[0].column_letter].width = max(largura, 12)


def salvar_relatorio(planilhas):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporario = OUTPUT_PATH.with_suffix(".tmp.xlsx")
    with pd.ExcelWriter(temporario, engine="openpyxl") as writer:
        for nome, quadro in planilhas:
            quadro.to_excel(writer, sheet_name=nome[:31], index=False)
        ajustar_planilhas(writer)
    temporario.replace(OUTPUT_PATH)


def executar():
    print("Iniciando plano de tratamento e normalização da Silver...")
    resumos = validar_dependencias()
    resumo_06 = resumos[6]
    resumo_07 = resumos[7]
    resultados = carregar_resultados_etapa_07()
    anteriores = carregar_resultados_anteriores()
    plano_deduplicacao = criar_plano_deduplicacao(anteriores)
    excedentes = linhas_excedentes(plano_deduplicacao)

    matriz = criar_matriz_tratamento(
        resultados, anteriores, resumo_07["total_linhas"]
    )
    correcoes = criar_correcoes_propostas(resultados, anteriores, excedentes)
    preservacoes = criar_preservacoes(resultados)
    pendencias = criar_pendencias(resultados, anteriores, excedentes)
    matriz, correcoes, pendencias, exclusoes_residuais, catalogo_decisoes = (
        incorporar_decisoes_residuais(
            matriz, correcoes, pendencias, anteriores
        )
    )
    tipagem = criar_plano_tipagem()
    controles = criar_controles(
        matriz, correcoes, pendencias, resumo_07, plano_deduplicacao
    )
    validar_saidas(matriz, correcoes, controles)

    resumo_execucao = pd.DataFrame([{
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "etapa": "08_plano_tratamento_normalizacao_silver",
        "arquivo_bronze": BRONZE_PATH.name,
        "sha256_bronze": resumo_07["sha256_bronze"],
        "total_linhas": int(resumo_07["total_linhas"]),
        "total_clientes": int(resumo_07["total_clientes"]),
        "total_pedidos": int(resumo_07["total_pedidos"]),
        "regras_tratamento": int(len(matriz)),
        "linhas_excedentes_para_remocao": int(len(excedentes)),
        "linhas_residuais_para_exclusao": int(len(exclusoes_residuais)),
        "linhas_totais_para_remocao": int(len(excedentes) + len(exclusoes_residuais)),
        "correcoes_deterministicas_propostas_bronze": int(len(correcoes)),
        "correcoes_aplicaveis_apos_deduplicacao": int(correcoes["aplicavel_apos_deduplicacao"].sum()),
        "casos_pendentes_detalhados_bronze": int(len(pendencias)),
        "pendencias_apos_deduplicacao": int(pendencias["permanece_apos_deduplicacao"].sum()),
        "step_06_validado": resumo_06["status"] == "success",
        "step_07_validado": True,
        "dados_modificados": False,
        "silver_materializada": False,
        "status": "success",
    }])

    planilhas = [
        ("resumo_execucao", resumo_execucao),
        ("matriz_tratamento", matriz),
        ("plano_deduplicacao", plano_deduplicacao),
        ("plano_exclusao_residual", exclusoes_residuais),
        ("catalogo_decisoes_nulos", catalogo_decisoes),
        ("correcoes_propostas", correcoes),
        ("preservacoes", preservacoes),
        ("pendencias", pendencias),
        ("plano_tipagem", tipagem),
        ("campos_calculados", resultados["calculos_cliente"]),
        ("ciclo_vida_contexto", resultados["ciclo_vida_resumo"]),
        ("controles_auditoria", controles),
        ("colunas_excluidas", resultados["colunas_excluidas"]),
    ]
    salvar_relatorio(planilhas)

    print("[OK] Etapas 4 a 7 validadas")
    print(f"[OK] Regras de tratamento: {len(matriz)}")
    print(f"[OK] Linhas excedentes para remoção: {len(excedentes)}")
    print(f"[OK] Correções propostas na Bronze: {len(correcoes)}")
    print(f"[OK] Correções aplicáveis após deduplicação: {int(correcoes['aplicavel_apos_deduplicacao'].sum())}")
    print(f"[OK] Pendências após deduplicação: {int(pendencias['permanece_apos_deduplicacao'].sum())}")
    print("[OK] Bronze preservada; Silver ainda não materializada")
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
