# Segurança

## Princípios

- Distribuições carregam comportamento, não identidade.
- Cada organização usa board, perfis, `.env`, credenciais, workspaces e memória próprios.
- O orquestrador é neutro e nunca recebe credenciais corporativas.
- Investigações respeitam as raízes e os escopos declarados localmente.
- Merge, aprovação, alteração de infraestrutura e deploy são humanos por padrão.
- Nenhum fallback pode atravessar organizações ou contas corporativas.

## Arquivos proibidos no Git

- `.env`, `auth.json`, bancos SQLite e backups Hermes.
- Chaves privadas, tokens OAuth, API keys e credenciais cloud.
- Logs e sessões que possam conter código ou dados empresariais.
- Configurações locais com caminhos ou identidades reais quando o repositório for público.

## Antes de publicar

1. Execute `python3 scripts/validate.py --source .`.
2. Confira `git status` e `git diff --cached` manualmente.
3. Confirme o público de cada distribuição gerada.
4. Faça os logins novamente em cada máquina; não transporte `auth.json` pelo Git.
5. Prefira arquivos de configuração/credential helpers locais a tokens literais no `.env`.

## Resposta a exposição

Se um segredo for commitado, remova-o do histórico, revogue-o no provedor e emita outro. Apagar apenas o arquivo no commit seguinte não revoga o material exposto.
