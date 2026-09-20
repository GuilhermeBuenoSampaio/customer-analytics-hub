# Etapa 03 — Profiling estrutural da Bronze

## Objetivo

Registrar a execução, as evidências e o critério de conclusão da etapa **Profiling estrutural da Bronze**.

## Implementação

- Script: `src/bronze/profiling/step_03_profiling_estrutural.py`
- SHA-256 do script: `013e3e955f9447c458ac112c21391f7e244fd9ae13bdf3f8d0f22e3c086fe8dc`
- Run ID: `retroactive`
- Registro UTC: `2026-09-20T01:18:12.927560+00:00`
- Status técnico informado: `success`

### Como foi feito

Calcula estrutura, tipos inferidos, cardinalidade e estatísticas iniciais.

### Por que foi necessário

Conhecer a forma real dos dados antes de definir tratamentos.

## Evidências

- `outputs/profiling/bronze_v3/step_03_profiling_estrutural.xlsx` — SHA-256 `aebd5f8b17666cbfef851098937dec37a15321331ee9e6970bc69319dd0486ef`

## Validação e critério de aceite

A etapa somente é considerada concluída quando o script termina com código zero, existe ao menos uma evidência material e este documento é gerado com sucesso.

## Decisões e limitações

- A documentação foi produzida a partir de arquivos efetivamente presentes no projeto.
- Ausência de evidência não é convertida automaticamente em aprovação.
- Credenciais, dados sensíveis e conteúdo do arquivo `.env` não são registrados.
