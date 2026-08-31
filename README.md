# Hermes Workflow Kit

Gerador agnóstico de esteiras Hermes com isolamento por organização e os papéis PO, Arquitetura, DEV e QA.

Licenciado sob Apache-2.0. Consulte [LICENSE](LICENSE).

O repositório não contém nomes de empresas reais, contas, caminhos locais, tokens, sessões ou bancos Kanban. Cada instalação parte de um manifesto neutro e produz distribuições Hermes específicas para o ambiente do usuário.

## Fluxo gerado

```text
PO
  -> Arquitetura + grafo de execução
  -> validação do desenho e da decomposição pelo PO
  -> aprovação humana do desenho e do plano
  -> DEV/QA por unidade
  -> QA integrado quando necessário
  -> conformidade arquitetural global
  -> review humano final
```

O arquiteto produz fatias verticais pequenas, verificáveis e empilháveis. Contratos estáveis e mocks liberam implementação em paralelo; QAs upstream continuam bloqueando QA integrado, merge e ativação, não o início seguro do desenvolvimento.

## Requisitos

- Hermes Agent compatível com a versão declarada no manifesto.
- Python 3.10 ou superior, somente com a biblioteca padrão.
- Git, quando as distribuições forem publicadas.
- Credenciais e ferramentas corporativas configuradas localmente em cada máquina.

## Uso rápido

1. Copie o manifesto de exemplo sem versionar a cópia local:

   ```bash
   cp deployment.example.json deployment.json
   ```

2. Edite `deployment.json` com os slugs, nomes dos boards, modelo e organizações. Não coloque valores de credenciais nele.

3. Valide e gere as distribuições:

   ```bash
   python3 scripts/validate.py --config deployment.json
   python3 scripts/render.py --config deployment.json
   ```

4. Examine os comandos sem alterar a máquina:

   ```bash
   python3 scripts/install.py --build build/example-engineering --dry-run --gateway
   ```

5. Instale os perfis e boards:

   ```bash
   python3 scripts/install.py --build build/example-engineering --gateway
   ```

6. Para preencher variáveis locais em todos os perfis de uma organização, copie `deployment.local.example.json` para `deployment.local.json`, preencha os valores e use `--local deployment.local.json`. Esse arquivo é ignorado pelo Git e pode conter somente valores locais; prefira caminhos para cofres/configurações em vez de tokens literais.

7. Autentique o provedor de modelo em cada perfil usando o fluxo oficial do provedor. Por exemplo, para OAuth Codex:

   ```bash
   <nome-do-perfil> auth add openai-codex --type oauth --label personal-codex
   ```

8. Abra o painel quando quiser:

   ```bash
   <nome-do-orquestrador> dashboard
   ```

O gateway é o serviço operacional; o dashboard é apenas a interface. Com `--gateway`, o instalador configura o serviço para iniciar com o login/boot quando a plataforma oferece supervisão compatível.

## Manifesto

`deployment.example.json` descreve:

- nome e versão da implantação;
- provedor/modelo e esforço de raciocínio;
- limite global e limite por perfil;
- rótulo do revisor humano;
- idioma de resposta e dos handoffs dos agentes;
- uma ou mais organizações, cada uma com board e prefixo de perfis próprios;
- variáveis de ambiente adicionais exigidas pelas ferramentas daquela organização.

Cada organização recebe quatro perfis:

- `<prefix>-po`
- `<prefix>-architect`
- `<prefix>-dev`
- `<prefix>-qa`

A implantação recebe um único `<deployment-slug>-orchestrator`. Ele despacha todos os boards, sem executar engenharia e sem revisão automática.

## Variáveis locais obrigatórias

As distribuições de cada organização sempre declaram:

- `HWF_WORKSPACE_ROOTS`: raízes locais permitidas, separadas pelo delimitador apropriado da plataforma.
- `HWF_REPOSITORY_SCOPES`: organizações, grupos ou namespaces Git permitidos.
- `HWF_TOOL_CONTEXT`: caminhos ou instruções para selecionar identidades locais de Git e cloud e validar o provedor do perfil.
- `HWF_DEPLOY_POLICY`: política de deploy e ações reservadas a humanos.
- `HWF_SOURCE_SYSTEM`: sistema externo que originou os cards e como seus links são tratados.
- `HWF_PR_POLICY`: idioma, convenção de títulos e referência canônica para os modelos de PR de documentação, backend, infraestrutura e frontend.

Esses valores ficam no `.env` de cada perfil instalado e não na distribuição Git. Requisitos adicionais podem ser declarados por organização.

Os perfis corporativos gerados usam o `HOME` real do sistema para permitir que ferramentas autenticadas pelo chaveiro local encontrem suas sessões. O orquestrador neutro permanece com `HOME` isolado. `HWF_TOOL_CONTEXT` deve incluir verificações concretas da identidade efetiva; cada agente bloqueia a tarefa diante de falha ou divergência, sem tentar login ou renovação por conta própria. Cada perfil executa diretamente com seu modelo/provider; agentes e CLIs aninhados são proibidos.

O QA é assíncrono: concluir uma unidade libera o DEV. Defeito de código, contrato ou comportamento cria correção e reteste proporcional; metadata do PR é corrigida pelo próprio QA sem handoff. QA de código não aguarda deploy: smoke de ambiente é um gate pós-review/merge separado e autorizado.

## O que pode ser publicado

Pode ir para Git:

- templates;
- scripts;
- esquema JSON;
- exemplos fictícios;
- testes e CI;
- distribuições geradas somente quando seus metadados forem apropriados para o público do repositório.

Nunca publique:

- `.env` ou `auth.json`;
- bancos Kanban, sessões, memórias ou logs;
- tokens, chaves ou credenciais cloud;
- inventários internos de organizações em um repositório público;
- uma implantação combinando empresas sem autorização de todas as partes.

O `.gitignore` é defesa adicional, não substitui a revisão de `git status` antes de cada commit.

## Publicação

Este é um metarrepositório: o usuário clona o kit e instala localmente as distribuições geradas. Se quiser instalação direta por `hermes profile install <git-url>`, publique cada diretório gerado de perfil em um repositório próprio com seu `distribution.yaml` na raiz.

## Atualizações

Atualize o kit, gere novamente e publique novas versões das distribuições. O Hermes preserva autenticação, `.env`, sessões e memórias ao atualizar uma distribuição. `config.yaml` local é preservado por padrão; use atualização forçada apenas quando quiser reaplicar o modelo e os limites do kit.

## Segurança

Leia [SECURITY.md](SECURITY.md). O validador recusa formatos comuns de segredo e caminhos de usuário codificados nos arquivos portáteis, mas nenhum detector é completo.
