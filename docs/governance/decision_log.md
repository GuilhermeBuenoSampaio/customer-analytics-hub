# Registro de decisões

| ID | Decisão | Justificativa | Impacto | Status |
|---|---|---|---|---|
| DEC-001 | Utilizar Pandas e PyArrow no processamento principal | A volumetria é compatível com processamento local e não justifica Spark nesta fase | Menor custo e complexidade | Aprovada |
| DEC-002 | Preservar a fonte e construir Bronze, Silver e Gold | Garante rastreabilidade e separação entre dado recebido, tratado e analítico | Aumenta auditabilidade | Aprovada |
| DEC-003 | Compartilhar fatos, dimensões e métricas entre as áreas | Evita divergências entre comercial, financeiro, logística e marketing | Cria camada semântica comum | Aprovada |
| DEC-004 | Tornar a publicação Azure configurável | Falha de autenticação externa não deve invalidar processamento local aprovado | Melhora resiliência | Aprovada |
| DEC-005 | Exigir documentação para concluir uma etapa | O portfólio precisa demonstrar como e por que cada decisão foi tomada | Aumenta governança e explicabilidade | Aprovada |
| DEC-006 | Roteamento por tipo de artefato | Código e documentação pública pertencem ao GitHub; dados e evidências pesadas permanecem localmente e no Azure | Reduz exposição e duplicação inadequada | Aprovada |
