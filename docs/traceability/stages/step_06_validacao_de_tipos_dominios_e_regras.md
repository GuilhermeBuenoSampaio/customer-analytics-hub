# Etapa 06 — Validação de tipos, domínios e regras

## Objetivo

Registrar a execução, as evidências e o critério de conclusão da etapa **Validação de tipos, domínios e regras**.

## Implementação

- Script: `src/bronze/profiling/step_06_validacao_tipos_dominios_regras.py`
- SHA-256 do script: `96c889eaf426430a2d19541652c84d8bd757b6b53bff15268f7f6703a01d5603`
- Run ID: `retroactive`
- Registro UTC: `2026-09-20T01:18:12.930534+00:00`
- Status técnico informado: `success`

### Como foi feito

Valida tipos, domínios, limites e coerência entre campos relacionados.

### Por que foi necessário

Transformar regras de negócio em controles verificáveis.

## Evidências

- `outputs/profiling/bronze_v3/step_06_validacao_tipos_dominios_regras.xlsx` — SHA-256 `14690a4ad5225e85e20db9ecb801808630a2123f522b2c3a8846888449a48f71`

## Validação e critério de aceite

A etapa somente é considerada concluída quando o script termina com código zero, existe ao menos uma evidência material e este documento é gerado com sucesso.

## Decisões e limitações

- A documentação foi produzida a partir de arquivos efetivamente presentes no projeto.
- Ausência de evidência não é convertida automaticamente em aprovação.
- Credenciais, dados sensíveis e conteúdo do arquivo `.env` não são registrados.
