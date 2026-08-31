# Changelog

## Unreleased

- QA assíncrono: a conclusão do DEV libera trabalho independente e dependências de QA exigem justificativa técnica.
- Retestes usam novos cards, evitando reexecução presa por histórico de PR.
- Nova política portátil `HWF_PR_POLICY` para idioma e modelos de pull request.
- PRs públicos não expõem ferramentas, perfis, IDs de tarefas, executores ou detalhes da orquestração.
- Modo rápido: execução direta pelo modelo do perfil, fatias verticais menores e implementação antecipada por contratos/mocks.
- Metadata de PR é corrigida no próprio QA; retestes são proporcionais e smoke de ambiente fica após review/merge.

## 0.1.0

- Gerador multi-organização.
- Papéis PO, Arquitetura, DEV e QA.
- Aprovação humana da arquitetura e review final.
- Decomposição condicional em grafo DEV/QA.
- QA integrado opcional e conformidade arquitetural global.
- Instalador idempotente, validação de segurança e CI.
- Licença Apache-2.0.
