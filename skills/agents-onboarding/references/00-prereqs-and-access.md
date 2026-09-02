# 00: Pré-requisitos e acesso

## MCPs (ligar ANTES de começar; reiniciar a sessão cedo)

- **Hostinger** (3 servers via npx, stdio, `HOSTINGER_API_TOKEN`): `hostinger-dns`, `hostinger-vps`, `hostinger-domains`. DNS é o uso central (etapa 1: A-records); VPS/domains pra descoberta/gestão. **Só quando a infra é Hostinger**: em outro provider não há esses MCPs (ver "Outro provider" na `01-vps-dns-ssh.md`). Chame as tools pelo **nome completo** `mcp__hostinger-{dns,vps,domains}__<Tool>` (ex.: `mcp__hostinger-vps__VPS_getVirtualMachinesV1`); o nome cru (`VPS_...`, `domains_...`) devolve *No such tool available*.
- **Não existe hub central.** Nada de OAuth de licença nem proxy de credencial: o registry é o GHCR (credencial = usuário do GitHub + PAT com `read:packages`, ver `03-chatwoot-pro.md`) e o licenciamento do Kanban é resolvido no próprio Chatwoot. Se uma referência antiga mandar você chamar `hub <op>`, ela está obsoleta.
- **agente** (OAuth): conectado **SÓ na etapa 6**, depois do `/setup` (antes disso a instância nem existe). **Não trate a ausência dessas tools como estado inconsistente nem motivo pra parar**: até a etapa 6 ela é o estado esperado da jornada; o gate "sem tools → PARE" de `06-setup-and-mcp.md` só vale **depois** da conexão.
- Depois de adicionar os MCPs, **reinicie a sessão do harness** pra eles ficarem disponíveis na execução.

## Estado do CLI de onboarding (em disco, `~/.indica-facil/`)

O CLI `@indicafacil/agents` roda ANTES do handoff e deixa marcadores que você deve **ler em vez de re-perguntar**:

- **`onboarding.json`**: `{ chatwootSource: "new" | "existing", chatwootTier?: "pro" | "community", edition: "free" | "pro" }`. **Eixos independentes:** a **origem** do Chatwoot (`chatwootSource`: `new` = subir um novo, aí `chatwootTier` diz a edição; `existing` = plugar num Chatwoot que **já existe** / BYO, **sem** tier), a edição do **Chatwoot** quando é novo (`chatwootTier`, etapa 3 / `chatwoot-kanban-enable.md` / `templates/chatwoot/README.md`) e a edição da **Indica Fácil Agents** (`edition`, etapa 4 / `04-agents-image.md`: `pro` = imagem privada no GHCR; `free` = pública). É a escolha **explícita** do operador; respeite-a (inclusive `existing` = não provisionar Chatwoot; `community`/`free` = seguir sem Pro, mesmo que haja acesso à imagem privada).
- **`hostinger.json`**: `{ token }` da API Hostinger (quando o provider é Hostinger); o CLI também já o injeta nos MCPs.
- **`preferences.json`**: defaults de UX do CLI (agente/provider); informativo, não load-bearing.

Marcador ausente (outro ponto de entrada) → **pergunte ao usuário** a origem/edição do Chatwoot e a edição do agents; não há hub a consultar.

## Acesso (fornecido pelo usuário)

> Peça **cada item quando a etapa que o usa chegar**, 1-2 por mensagem; **não** despeje esta lista inteira de uma vez (princípio "Uma pergunta de cada vez" no SKILL.md). Ex.: IP do VPS na 01 (a chave SSH só se a sondagem falhar, ver 01); domínio na 01 (DNS); chave do provedor de modelo só perto do import/E2E; número de WhatsApp só na etapa 10. (O **nome de exibição não é perguntado**: default fixo `Indica Fácil Agents`, ver SKILL.md.)

- **VPS:** `root@<VPS_IP>` (no Hostinger, o id da VM é `<VPS_ID>`). **Qual VPS é escolha do usuário**: se a conta tem mais de uma, liste e **pergunte** (nunca escolha). Acesso SSH como `root` (sonde primeiro; só peça ou gere chave se faltar). Coolify pode já estar instalado (brownfield) ou não. Sondagem + comando SSH na `01-vps-dns-ssh.md`.
- **Sem VPS ainda?** Sugira adquirir uma. Recomendado: [Hostinger](https://www.hostinger.com/br). Em **outro provider**, o usuário cria a VPS lá e fornece IP + chave SSH; o fluxo segue igual (ver `01-vps-dns-ssh.md`).
- **Domínio:** `<seu-dominio>`. **O domínio raiz é escolha do usuário**: liste os domínios da conta e **pergunte qual** (nunca assuma). Os subdomínios de onboarding ficam livres pra apontar (`agents.`, `chatwoot.`, `coolify.`, `langfuse.`).
- **Chave do provedor de modelo** (OpenAI ou outro): o usuário fornece pra preencher o vault do agente (playground/E2E). As demais credenciais entram via deeplink (pending).
- **Número de WhatsApp** que o usuário controle, se for validar o transporte real no E2E (etapa 10).

## Operacional (comandos remotos)

- Chamadas de rede via Bash (ssh/curl) precisam de `dangerouslyDisableSandbox: true`.
- Pra evitar inferno de aspas em SSH/psql/Rails runner: **base64 local → pipe → `base64 -d`** no destino. É o padrão recorrente de todo o fluxo (ex.: `echo <B64> | base64 -d | docker exec -i coolify-db psql ...`).

## Gates de conta

- O **usuário** cria o 1º admin de Coolify/Portainer/Chatwoot/Langfuse/agents no browser; você entrega link + instrução e **espera**, nunca cria por conta própria. Detalhe em `guardrails.md`.
