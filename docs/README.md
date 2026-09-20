# Documentação do Customer Analytics Hub

Esta pasta é produzida e validada pelo agente local de documentação.

## Estrutura

- `traceability/stages`: um documento por etapa técnica;
- `traceability/index.json`: índice legível por máquina e utilizado pelo gate;
- `governance`: decisões, métricas e critérios compartilhados;
- `reports/technical_report.md`: relatório técnico progressivo;
- `reports/executive_report.md`: resumo curto contendo somente entregas aprovadas.

## Regra de conclusão

Uma etapa somente é concluída quando possui:

1. execução técnica com código de saída zero;
2. ao menos uma evidência material;
3. documento com as seções obrigatórias;
4. registro aprovado no índice de rastreabilidade.

## Modos do agente

O modo `deterministic` é gratuito, reproduzível e não depende de API. O modo `ollama` é opcional e usa um modelo executado localmente para enriquecer a síntese, sem substituir as evidências objetivas.
