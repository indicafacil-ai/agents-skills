# 04: Deploy do Indica Fácil Agents

> **Avise o usuário onde você está:** o Indica Fácil Agents vem **depois do painel e do Chatwoot**; em seguida só falta o Langfuse. Diga que vai subir o Indica Fácil Agents agora e que leva alguns minutos; dê sinal de vida durante a espera longa e confirme ao terminar. Ver o princípio de narração (com a contagem que se ajusta ao caso real) em `SKILL.md`.

## Edição: Free ou Pro (lê o marcador PRIMEIRO)

Leia `~/.indica-facil/onboarding.json` → `edition` (`free` | `pro`; ausente = `free`). É a escolha **explícita** do CLI; respeite-a. Eixo **independente** do `chatwootTier` (etapa 3).

- **`free`** → imagem **pública** `ghcr.io/nicolasdasilvaesilva/agents:latest` (default do compose, multi-arch amd64/arm64). **Sem** `docker login`, não seta `AGENTS_IMAGE`.
- **`pro`** → imagem **privada** no GHCR: `ghcr.io/nicolasdasilvaesilva/agents-pro:latest`. A credencial é o seu usuário do GitHub + um **PAT** com o escopo `read:packages`, gravado num arquivo `0600` (`ghcr.secret`). Logue com `scripts/registry-login.py login` (token via `--secret-file ghcr.secret`, fora do argv) e sete `AGENTS_IMAGE` pra esse path. **Nunca** logar o token.
  - **Reuso:** se o Chatwoot também for Pro (etapa 3), é o **mesmo** `docker login`, não logar duas vezes.
  - **Tier A (Coolify):** setar a env `AGENTS_IMAGE` no serviço + registrar a registry credential no Coolify (igual ao Chatwoot Pro).
  - **Tier B/C (compose):** `export AGENTS_IMAGE=<imagem>` (ou no `.env`) antes do `docker compose up`.

## Compose

Use o `templates/docker-compose.coolify.yml` do repo via `scripts/coolify.py create-service` (lê o compose, base64-encoda, POSTa em `/api/v1/services`). Topologia: `agents` (imagem conforme a **edição** acima; o compose default é a Free) + `postgres` (`ghcr.io/nicolasdasilvaesilva/postgres-17-pgvector:latest`: NÃO postgres puro: o schema precisa de `CREATE EXTENSION vector`). Volume `storage:/app/storage`. Healthcheck `wget -qO- http://localhost:3000/api/health`.

## Magic vars (Coolify gera; NÃO setar à mão)

- `SERVICE_URL_AGENTS` → `PUBLIC_URL` e `CDN_URL`.
- `SERVICE_USER_DBUSER` / `SERVICE_PASSWORD_64_DBPASSWORD` → **superuser** (dono do Postgres) → `MIGRATION_DATABASE_URL`.
- `SERVICE_USER_APPDBUSER` / `SERVICE_PASSWORD_64_APPDBPASSWORD` → **app role** (não-superuser) → `DATABASE_URL` + `LANGGRAPH_DATABASE_URL`.
- `SERVICE_PASSWORD_64_JWTSECRET` → `JWT_SECRET`; `SERVICE_PASSWORD_64_ENCRYPTIONKEY` → `ENCRYPTION_KEY`.

## Persistência de branding/quotes (fix: já no compose)

```
BRANDING_STORAGE_DIR=/app/storage/branding
QUOTES_STORAGE_DIR=/app/storage/quotes
```
Sem isso caem em `./data/*` (FS efêmero do container) e logo/favicon (+ PDFs de quote) somem no redeploy. Já corrigido no `templates/docker-compose.coolify.yml`; **confira que está lá** (branding é refino manual opcional depois, em `/admin/branding`, mas a persistência precisa já estar no lugar).

## Boot = CMD da imagem (NÃO sobrescrever `command`)

A sequência `bootstrap → migrate deploy → serve` é o CMD do Dockerfile. **Não** declare `command:` no compose (sobrescrever crash-loopa). Detalhe em `gotchas.md`.

## FQDN + 503 + verificação

O `SERVICE_FQDN_*` não dirige o Traefik; quem roteia é a linha em `service_applications` (ver `gotchas.md`). Ache o id e seta o FQDN:
```sh
python3 scripts/coolify.py list-apps --ssh root@<VPS_IP>            # ache o id do agents
python3 scripts/coolify.py set-fqdn  --ssh root@<VPS_IP> --app-id <id> --fqdn https://agents.<seu-dominio>
python3 scripts/coolify.py api-post  --base-url http://<VPS_IP>:8000 --token-file coolify.token --path /services/<uuid>/restart
```
Antes do DNS resolver, verifique o routing por sslip.io: `curl http://agents-<service-uuid>.<VPS_IP>.sslip.io/api/health`. Depois do `/setup` (etapa 6) o app responde em `https://agents.<seu-dominio>`.
