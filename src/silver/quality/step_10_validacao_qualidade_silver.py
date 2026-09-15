import hashlib
import json
import sys
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SILVER_PATH = (
    PROJECT_ROOT / "data" / "silver" / "food_commerce"
    / "silver_transactions_v3.parquet"
)
SILVER_MANIFEST_PATH = (
    PROJECT_ROOT / "outputs" / "manifests" / "silver_v3"
    / "step_09_materializacao_silver.json"
)
STEP_04_PATH = (
    PROJECT_ROOT / "outputs" / "profiling" / "bronze_v3"
    / "step_04_analise_granularidade_chaves.xlsx"
)
STEP_09_REPORT_PATH = (
    PROJECT_ROOT / "outputs" / "quality" / "silver_v3"
    / "step_09_materializacao_silver.xlsx"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "quality" / "silver_v3"
OUTPUT_PATH = OUTPUT_DIR / "step_10_validacao_qualidade_silver.xlsx"

TOLERANCIA_MONETARIA = 0.01
UFS_VALIDAS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}
DOMINIOS = {
    "Frete_Gratis": {"sim", "nao"},
    "Cupom_Utilizado": {"sim", "nao"},
    "Atraso_Entrega": {"sim", "nao"},
    "Ciclo_Vida_Cliente": {
        "ativo", "churn", "em risco", "fiel", "novo", "reativado",
    },
}


def calcular_sha256(caminho):
    sha = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            sha.update(bloco)
    return sha.hexdigest().upper()


def normalizar_texto(valor):
    if pd.isna(valor):
        return pd.NA
    texto = " ".join(str(valor).strip().casefold().split())
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )


def carregar_entradas():
    obrigatorios = [
        SILVER_PATH, SILVER_MANIFEST_PATH, STEP_04_PATH, STEP_09_REPORT_PATH,
    ]
    ausentes = [caminho for caminho in obrigatorios if not caminho.is_file()]
    if ausentes:
        raise FileNotFoundError(
            "Arquivos obrigatórios ausentes:\n" + "\n".join(map(str, ausentes))
        )

    with SILVER_MANIFEST_PATH.open("r", encoding="utf-8") as arquivo:
        manifesto = json.load(arquivo)
    if manifesto.get("status") != "success":
        raise ValueError("O manifesto da Silver não possui status success.")
    if calcular_sha256(SILVER_PATH) != manifesto["silver"]["sha256"]:
        raise ValueError("O SHA-256 da Silver difere do manifesto.")

    silver = pd.read_parquet(SILVER_PATH, engine="pyarrow")
    if len(silver) != int(manifesto["silver"]["rows"]):
        raise ValueError("A quantidade de linhas da Silver difere do manifesto.")
    if len(silver.columns) != int(manifesto["silver"]["columns"]):
        raise ValueError("A quantidade de colunas da Silver difere do manifesto.")

    mapa_itens = pd.read_excel(STEP_04_PATH, sheet_name="item_mapa_canonico")
    resumo_09 = pd.read_excel(STEP_09_REPORT_PATH, sheet_name="resumo_execucao")
    auditoria_09 = pd.read_excel(STEP_09_REPORT_PATH, sheet_name="auditoria_alteracoes")
    if resumo_09.empty or resumo_09.iloc[0].get("status") != "success":
        raise ValueError("A Etapa 9 não possui status success.")
    if resumo_09.iloc[0].get("sha256_silver") != manifesto["silver"]["sha256"]:
        raise ValueError("Relatório e manifesto da Etapa 9 apontam Silvers diferentes.")
    return silver, manifesto, mapa_itens, resumo_09.iloc[0], auditoria_09


def criar_controle(nome, observado, esperado, critico, interpretacao):
    conforme = observado == esperado
    return {
        "controle": nome,
        "observado": observado,
        "esperado": esperado,
        "status": "aprovado" if conforme else "reprovado",
        "critico": critico,
        "interpretacao": interpretacao,
    }


def validar_estrutura(silver, manifesto, mapa_itens, auditoria, resumo_09):
    controles = []
    adicionar = controles.append
    adicionar(criar_controle(
        "linhas_silver", len(silver), 6495, True,
        "A Silver deve refletir 6556 linhas menos 58 duplicidades e 3 exclusões logísticas aprovadas.",
    ))
    adicionar(criar_controle(
        "clientes_distintos", silver["Cliente_ID"].nunique(), 330, True,
        "O cliente 5 deixa a Silver transacional porque seu único pedido foi excluído por decisão documentada.",
    ))
    adicionar(criar_controle(
        "pedidos_distintos", silver["Pedido_ID"].nunique(), 2789, True,
        "Somente os três pedidos logísticos aprovados podem ser excluídos.",
    ))
    adicionar(criar_controle(
        "itens_distintos", silver["Id_Item"].nunique(), 36, True,
        "Nenhum item cadastral pode desaparecer durante o tratamento.",
    ))
    adicionar(criar_controle(
        "source_row_number_duplicada",
        int(silver["_bronze_source_row_number"].duplicated().sum()), 0, True,
        "A coluna de linhagem deve identificar uma única linha da Bronze.",
    ))
    adicionar(criar_controle(
        "correcoes_deterministicas_auditadas",
        int((auditoria["acao"] == "corrigir_deterministicamente").sum()),
        int(resumo_09["correcoes_deterministicas_aplicadas"]), True,
        "Todas as correções aprovadas devem estar auditadas.",
    ))
    adicionar(criar_controle(
        "correcoes_deterministicas_aprovadas",
        int(resumo_09["correcoes_deterministicas_aplicadas"]),
        261, True, "A materialização deve aplicar as 261 correções aprovadas.",
    ))
    adicionar(criar_controle(
        "remocoes_auditadas",
        int((auditoria["acao"] == "remover_excedente_duplicado").sum()),
        58, True, "Todas as remoções devem estar auditadas.",
    ))
    adicionar(criar_controle(
        "exclusoes_logisticas_auditadas",
        int((auditoria["acao"] == "excluir_pedido_sem_evidencia_logistica").sum()),
        3, True, "As três exclusões logísticas devem permanecer auditadas.",
    ))
    for campo, esperado in {
        "Cidade": 0,
        "Renda_Mensal_Cliente": 1,
        "Cupom_Utilizado": 5,
        "Transportadora": 0,
        "Prazo_Entrega_Real": 0,
        "Atraso_Entrega": 0,
    }.items():
        adicionar(criar_controle(
            f"nulos_esperados_{campo}", int(silver[campo].isna().sum()),
            esperado, True, "Resultado esperado após as decisões documentadas sobre nulos.",
        ))
    adicionar(criar_controle(
        "colunas_dq_na_silver",
        sum(coluna.startswith("DQ_") for coluna in silver.columns),
        0, True, "Campos de ground truth não podem alimentar a Silver analítica.",
    ))
    adicionar(criar_controle(
        "itens_no_mapa_canonico", mapa_itens["Id_Item"].nunique(),
        silver["Id_Item"].nunique(), True,
        "Todos os itens vendidos devem possuir referência cadastral analisável.",
    ))
    adicionar(criar_controle(
        "sha256_manifesto_confere", calcular_sha256(SILVER_PATH),
        manifesto["silver"]["sha256"], True,
        "O arquivo validado deve ser exatamente o materializado na Etapa 9.",
    ))
    return pd.DataFrame(controles)


def validar_dominios(silver):
    registros = []

    def registrar(regra, campo, mascara, severidade, motivo):
        for indice in silver.index[mascara.fillna(False)]:
            registros.append({
                "_bronze_source_row_number": silver.at[indice, "_bronze_source_row_number"],
                "Pedido_ID": silver.at[indice, "Pedido_ID"],
                "Cliente_ID": silver.at[indice, "Cliente_ID"],
                "Id_Item": silver.at[indice, "Id_Item"],
                "regra": regra, "campo": campo,
                "valor": silver.at[indice, campo],
                "severidade": severidade, "motivo": motivo,
                "pendencia_registrada": pd.notna(silver.at[indice, "_silver_pendencias"]),
            })

    registrar("idade_fora_16_100", "Idade", (silver["Idade"] < 16) | (silver["Idade"] > 100), "alta", "Idade fora do domínio aprovado.")
    registrar("renda_negativa", "Renda_Mensal_Cliente", silver["Renda_Mensal_Cliente"] < 0, "alta", "Renda negativa.")
    registrar("renda_extrema_superior", "Renda_Mensal_Cliente", silver["Renda_Mensal_Cliente"] > 1_000_000, "alta", "Renda acima do limite conservador de validação.")
    registrar("quantidade_nao_positiva", "Quantidade", silver["Quantidade"] <= 0, "alta", "Quantidade deve ser positiva.")
    registrar("quantidade_extrema", "Quantidade", silver["Quantidade"] >= 100, "alta", "Quantidade extrema já deveria ter sido corrigida.")
    registrar("custo_nao_positivo", "Custo_Unitario", silver["Custo_Unitario"] <= 0, "alta", "Custo deve ser positivo.")
    registrar("preco_nao_positivo", "Preco_Unitario_Lista", silver["Preco_Unitario_Lista"] <= 0, "alta", "Preço deve ser positivo.")
    registrar("desconto_fora_0_100", "Desconto_Percentual", (silver["Desconto_Percentual"] < 0) | (silver["Desconto_Percentual"] > 100), "alta", "Desconto fora da escala identificada.")
    registrar("avaliacao_fora_1_5", "Avaliacao_Cliente", (silver["Avaliacao_Cliente"] < 1) | (silver["Avaliacao_Cliente"] > 5), "alta", "Avaliação fora da escala.")
    registrar("pontos_negativos", "Pontos_Fidelidade", silver["Pontos_Fidelidade"] < 0, "alta", "Pontos de fidelidade negativos.")
    registrar("estado_fora_uf", "Estado", silver["Estado"].notna() & ~silver["Estado"].isin(UFS_VALIDAS), "alta", "Estado deve usar sigla UF válida.")
    registrar("mes_ref_incoerente", "Mes_Ref", silver["Mes_Ref"] != (silver["Data_Compra"].dt.year * 100 + silver["Data_Compra"].dt.month), "alta", "Mes_Ref difere de Data_Compra.")
    registrar("data_hora_incoerente", "Data_Hora_Compra", silver["Data_Hora_Compra"].dt.date != silver["Data_Compra"].dt.date, "alta", "Data_Hora_Compra difere da data de compra.")

    for campo, dominio in DOMINIOS.items():
        normalizada = silver[campo].map(normalizar_texto)
        mascara = silver[campo].notna() & ~normalizada.isin(dominio)
        registrar(f"dominio_invalido_{campo}", campo, mascara, "alta", "Valor qualitativo fora do domínio permitido.")

    return pd.DataFrame(registros)


def validar_regras_calculo(silver):
    quantidade = silver["Quantidade"].astype("Float64")
    preco = silver["Preco_Unitario_Lista"].astype("Float64")
    desconto = silver["Desconto_Percentual"].astype("Float64") / 100
    informado = silver["Valor_Compra"].astype("Float64")
    esperado = quantidade * preco * (1 - desconto)
    diferenca = informado - esperado
    divergente = diferenca.abs() > TOLERANCIA_MONETARIA

    quadro = silver.loc[divergente, [
        "_bronze_source_row_number", "Pedido_ID", "Cliente_ID", "Id_Item",
        "Produto", "Categoria_Item", "Quantidade", "Preco_Unitario_Lista",
        "Desconto_Percentual", "Valor_Compra", "Cupom_Utilizado", "Campanha",
        "_silver_pendencias",
    ]].copy()
    quadro["valor_recalculado"] = esperado.loc[divergente]
    quadro["diferenca"] = diferenca.loc[divergente]
    quadro["pendencia_valor_registrada"] = quadro[
        "_silver_pendencias"
    ].astype("string").str.contains("Valor_Compra:TR010", na=False)
    quadro["classificacao"] = np.where(
        quadro["pendencia_valor_registrada"],
        "divergencia_conhecida_e_rastreada",
        "divergencia_nao_rastreada",
    )
    return quadro


def validar_frete(silver):
    gratis = silver["Frete_Gratis"].map(normalizar_texto).eq("sim")
    frete_zero = silver["Frete"].abs() <= TOLERANCIA_MONETARIA
    mascara = gratis.ne(frete_zero)
    quadro = silver.loc[mascara, [
        "_bronze_source_row_number", "Pedido_ID", "Cliente_ID", "Frete",
        "Frete_Gratis", "Transportadora", "_silver_pendencias",
    ]].copy()
    quadro["regra"] = "frete_gratis_difere_frete_zero"
    return quadro


def validar_mapeamento_itens(silver, mapa):
    colunas_mapa = [
        "Id_Item", "produto_canonico_candidato", "categoria_canonica_candidata",
        "medida_canonica_candidata", "produto_percentual_consistencia",
        "categoria_percentual_consistencia", "problemas_detectados",
    ]
    base = silver.merge(mapa[colunas_mapa], on="Id_Item", how="left", validate="many_to_one")
    produto_atual = base["Produto"].map(normalizar_texto).fillna("<nulo>")
    produto_canonico = base["produto_canonico_candidato"].map(
        normalizar_texto
    ).fillna("<nulo>")
    categoria_atual = base["Categoria_Item"].map(normalizar_texto).fillna("<nulo>")
    categoria_canonica = base["categoria_canonica_candidata"].map(
        normalizar_texto
    ).fillna("<nulo>")
    medida_atual = base["Medida"].map(normalizar_texto).fillna("<nulo>")
    medida_canonica = base["medida_canonica_candidata"].map(
        normalizar_texto
    ).fillna("<nulo>")
    produto_diverge = produto_atual.ne(produto_canonico) & base["Produto"].notna()
    categoria_diverge = categoria_atual.ne(categoria_canonica) & base["Categoria_Item"].notna()
    medida_diverge = medida_atual.ne(medida_canonica) & base["Medida"].notna()
    legado = base["Produto"].map(normalizar_texto).astype("string").str.contains(
        "legado descontinuado", na=False
    )
    categoria_nula = base["Categoria_Item"].isna()
    mascara = produto_diverge | categoria_diverge | medida_diverge | legado | categoria_nula
    quadro = base.loc[mascara, [
        "_bronze_source_row_number", "Pedido_ID", "Cliente_ID", "Id_Item",
        "Produto", "produto_canonico_candidato", "Categoria_Item",
        "categoria_canonica_candidata", "Medida", "medida_canonica_candidata",
        "produto_percentual_consistencia", "categoria_percentual_consistencia",
        "problemas_detectados", "_silver_pendencias",
    ]].copy()
    quadro["produto_diverge"] = produto_diverge.loc[mascara].to_numpy()
    quadro["categoria_diverge"] = categoria_diverge.loc[mascara].to_numpy()
    quadro["medida_diverge"] = medida_diverge.loc[mascara].to_numpy()
    quadro["produto_legado"] = legado.loc[mascara].to_numpy()
    quadro["categoria_nula"] = categoria_nula.loc[mascara].to_numpy()
    quadro["pendencia_item_registrada"] = quadro[
        "_silver_pendencias"
    ].astype("string").str.contains("Categoria_Item:TR019", na=False)
    quadro["classificacao"] = np.select(
        [
            quadro["produto_legado"],
            quadro["categoria_nula"] & quadro["pendencia_item_registrada"],
            quadro["categoria_diverge"],
            quadro["produto_diverge"],
            quadro["medida_diverge"],
        ],
        [
            "produto_legado_a_corrigir",
            "categoria_nula_conhecida_e_rastreada",
            "categoria_semantica_divergente",
            "produto_divergente_do_item",
            "medida_divergente_do_item",
        ],
        default="revisar",
    )
    return quadro.sort_values(["classificacao", "Id_Item", "_bronze_source_row_number"])


def validar_constancia(silver):
    registros = []
    cliente = [
        "Gênero", "Estado", "Cidade", "Estado_Civil", "Escolaridade",
        "Situacao_Profissional", "Profissão", "Ciclo_Vida_Cliente",
        "Categoria_Favorita", "Forma_Pagamento_Preferida", "Dia_Semana_Preferido",
    ]
    pedido = [
        "Cliente_ID", "Data_Compra", "Horario_Compra", "Campanha",
        "Evento_Externo", "Canal_Marketing", "Frete", "Frete_Gratis",
        "Transportadora", "Prazo_Entrega_Prometido", "Prazo_Entrega_Real",
        "Atraso_Entrega", "Avaliacao_Cliente",
    ]
    for nivel, chave, colunas in [
        ("cliente", "Cliente_ID", cliente), ("pedido", "Pedido_ID", pedido),
    ]:
        for coluna in colunas:
            distintos = silver.groupby(chave)[coluna].nunique(dropna=True)
            for identificador, quantidade in distintos[distintos > 1].items():
                valores = silver.loc[silver[chave].eq(identificador), coluna]
                registros.append({
                    "nivel": nivel, "chave": chave,
                    "identificador": identificador, "campo": coluna,
                    "valores_distintos": int(quantidade),
                    "valores": " | ".join(map(str, valores.dropna().unique())),
                })
    return pd.DataFrame(registros)


def criar_perfil_nulos(silver, colunas, classificacao):
    """Cria o perfil sem misturar ausência de negócio com metadados técnicos."""
    registros = []
    for coluna in colunas:
        nulos = int(silver[coluna].isna().sum())
        registro = {
            "coluna": coluna,
            "classificacao_coluna": classificacao,
            "dtype": str(silver[coluna].dtype),
            "nulos": nulos,
            "percentual_nulos": round(silver[coluna].isna().mean() * 100, 4),
            "valores_distintos": int(silver[coluna].nunique(dropna=True)),
        }

        if classificacao == "negocio":
            registro["interpretacao_nulo"] = (
                "sem_nulos"
                if nulos == 0
                else "pendencia_de_negocio_documentada"
            )
        else:
            interpretacoes = {
                "_bronze_source_row_number": "nulo_indicaria_quebra_de_linhagem",
                "_silver_regras_aplicadas": "nulo_significa_nenhuma_regra_aplicada",
                "_silver_pendencias": "nulo_significa_nenhuma_pendencia_registrada",
                "_silver_status_qualidade": "nulo_indicaria_status_de_qualidade_ausente",
            }
            registro["interpretacao_nulo"] = interpretacoes.get(
                coluna, "campo_tecnico_sem_interpretacao_cadastrada"
            )
        registros.append(registro)

    return pd.DataFrame(registros)


def criar_linhas_com_nulos_negocio(silver):
    campos = [
        "Cidade", "Renda_Mensal_Cliente", "Cupom_Utilizado",
        "Transportadora", "Prazo_Entrega_Real", "Atraso_Entrega",
    ]
    mascara = silver[campos].isna().any(axis=1)
    detalhe = silver.loc[mascara].copy()
    detalhe.insert(
        0, "campos_nulos",
        detalhe[campos].isna().apply(
            lambda linha: " | ".join(linha.index[linha].tolist()), axis=1
        ),
    )
    detalhe.insert(0, "quantidade_nulos_linha", detalhe[campos].isna().sum(axis=1))
    return detalhe


def criar_resumo_qualidade(estrutura, dominios, calculos, frete, itens, constancia):
    criticos_reprovados = int(
        (estrutura["critico"] & estrutura["status"].eq("reprovado")).sum()
    )
    registros = [
        {"grupo": "estrutura", "metrica": "controles_criticos_reprovados", "quantidade": criticos_reprovados, "status": "conforme" if criticos_reprovados == 0 else "reprovado"},
        {"grupo": "dominios", "metrica": "violacoes_objetivas", "quantidade": len(dominios), "status": "conforme" if dominios.empty else "corrigir"},
        {"grupo": "calculos", "metrica": "divergencias_formula_valor", "quantidade": len(calculos), "status": "conforme" if calculos.empty else "corrigir"},
        {"grupo": "frete", "metrica": "incoerencias_frete_gratis", "quantidade": len(frete), "status": "conforme" if frete.empty else "investigar"},
        {"grupo": "itens", "metrica": "inconsistencias_cadastrais", "quantidade": len(itens), "status": "corrigir" if len(itens) else "conforme"},
        {"grupo": "itens", "metrica": "inconsistencias_sem_pendencia_registrada", "quantidade": int((~itens.get("pendencia_item_registrada", pd.Series(dtype=bool))).sum()), "status": "corrigir" if len(itens) else "conforme"},
        {"grupo": "constancia", "metrica": "conflitos_cliente_ou_pedido", "quantidade": len(constancia), "status": "investigar" if len(constancia) else "conforme"},
    ]
    return pd.DataFrame(registros)


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
            celula.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for coluna in planilha.columns:
            largura = min(max(
                len(str(celula.value)) if celula.value is not None else 0
                for celula in coluna
            ) + 2, 60)
            planilha.column_dimensions[coluna[0].column_letter].width = max(largura, 12)


def salvar_relatorio(planilhas):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporario = OUTPUT_DIR / (
        f".{OUTPUT_PATH.stem}.{uuid.uuid4().hex}.tmp.xlsx"
    )
    try:
        with pd.ExcelWriter(temporario, engine="openpyxl") as writer:
            for nome, quadro in planilhas:
                if quadro.empty and len(quadro.columns) == 0:
                    quadro = pd.DataFrame([{"resultado": "sem_casos"}])
                quadro.to_excel(writer, sheet_name=nome[:31], index=False)
            ajustar_planilhas(writer)
        try:
            temporario.replace(OUTPUT_PATH)
        except PermissionError as erro:
            raise PermissionError(
                "Não foi possível atualizar o relatório da Etapa 10. "
                "Feche step_10_validacao_qualidade_silver.xlsx no Excel, "
                "aguarde a sincronização do OneDrive e execute novamente."
            ) from erro
    finally:
        if temporario.exists():
            try:
                temporario.unlink()
            except PermissionError:
                pass


def executar():
    print("Iniciando validação integral da Silver...")
    silver, manifesto, mapa_itens, resumo_09, auditoria_09 = carregar_entradas()
    estrutura = validar_estrutura(
        silver, manifesto, mapa_itens, auditoria_09, resumo_09
    )
    dominios = validar_dominios(silver)
    calculos = validar_regras_calculo(silver)
    frete = validar_frete(silver)
    itens = validar_mapeamento_itens(silver, mapa_itens)
    constancia = validar_constancia(silver)
    colunas_auditoria = [
        coluna for coluna in silver.columns if coluna.startswith("_")
    ]
    colunas_negocio = [
        coluna for coluna in silver.columns if coluna not in colunas_auditoria
    ]
    perfil_nulos_negocio = criar_perfil_nulos(
        silver, colunas_negocio, "negocio"
    )
    perfil_campos_auditoria = criar_perfil_nulos(
        silver, colunas_auditoria, "auditoria"
    )
    linhas_com_nulos = criar_linhas_com_nulos_negocio(silver)
    resumo_qualidade = criar_resumo_qualidade(
        estrutura, dominios, calculos, frete, itens, constancia
    )

    falha_estrutural = bool(
        (estrutura["critico"] & estrutura["status"].eq("reprovado")).any()
    )
    linhas_com_pendencia = int(silver["_silver_pendencias"].notna().sum())
    resultado_analitico = (
        "reprovado_estruturalmente" if falha_estrutural
        else "aprovado_com_ressalvas_semanticas" if (
            len(dominios) or len(itens) or len(calculos)
            or len(frete) or len(constancia)
        ) else "aprovado_com_pendencias_nao_imputaveis" if linhas_com_pendencia
        else "aprovado"
    )

    resumo_execucao = pd.DataFrame([{
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "etapa": "10_validacao_qualidade_silver",
        "arquivo_silver": SILVER_PATH.name,
        "sha256_silver": calcular_sha256(SILVER_PATH),
        "linhas_silver": len(silver),
        "colunas_silver": len(silver.columns),
        "violacoes_dominio": len(dominios),
        "divergencias_formula_valor": len(calculos),
        "inconsistencias_frete": len(frete),
        "inconsistencias_mapeamento_item": len(itens),
        "conflitos_constancia": len(constancia),
        "linhas_com_pendencia": linhas_com_pendencia,
        "resultado_analitico": resultado_analitico,
        "dados_modificados": False,
        "status_execucao": "success",
    }])

    salvar_relatorio([
        ("resumo_execucao", resumo_execucao),
        ("resumo_qualidade", resumo_qualidade),
        ("controles_estrutura", estrutura),
        ("violacoes_dominio", dominios),
        ("divergencias_calculos", calculos),
        ("inconsistencias_frete", frete),
        ("mapeamento_itens", itens),
        ("conflitos_constancia", constancia),
        ("perfil_nulos_negocio", perfil_nulos_negocio),
        ("perfil_campos_auditoria", perfil_campos_auditoria),
        ("linhas_com_nulos", linhas_com_nulos),
    ])

    if falha_estrutural:
        raise ValueError("A Silver possui falha estrutural crítica.")

    print(f"[OK] Linhas Silver validadas: {len(silver)}")
    print(f"[OK] Violações objetivas de domínio: {len(dominios)}")
    print(f"[OK] Divergências da fórmula de valor: {len(calculos)}")
    print(f"[OK] Inconsistências de mapeamento de item: {len(itens)}")
    print(f"[OK] Resultado analítico: {resultado_analitico}")
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
