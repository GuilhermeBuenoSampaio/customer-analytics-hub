from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def carregar_agente():
    caminho = PROJECT_ROOT / "src" / "documentation" / "documentation_agent.py"
    spec = importlib.util.spec_from_file_location("documentation_agent", caminho)
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


class AutomationFoundationTests(unittest.TestCase):
    def test_catalogo_compartilha_gold_entre_cinco_dominios(self):
        configuracao = json.loads(
            (PROJECT_ROOT / "configs" / "analysis_domains.json").read_text(encoding="utf-8")
        )
        self.assertEqual(5, len(configuracao["domains"]))
        self.assertEqual(10, len(configuracao["shared_semantic_layer"]["dimensions"]))
        self.assertEqual(4, len(configuracao["shared_semantic_layer"]["facts"]))

    def test_slug_remove_acentos(self):
        agente = carregar_agente()
        self.assertEqual("validacao_e_analise", agente.slug("Validação e análise"))

    def test_etapas_1_a_12_estao_documentadas(self):
        indice = json.loads(
            (PROJECT_ROOT / "docs" / "traceability" / "index.json").read_text(encoding="utf-8")
        )
        for numero in range(1, 13):
            self.assertEqual("approved", indice["stages"][str(numero)]["status"])


if __name__ == "__main__":
    unittest.main()
