# Chatwoot (self-hosted) for Indica Fácil

The inbox Indica Fácil Agents plugs into. The onboarding installs Chatwoot as part of the journey, in one of
**two editions**, chosen by whether you can pull the private Pro image:

| Edition | Image | When | Extra features |
| --- | --- | --- | --- |
| **Pro** | `ghcr.io/indicafacil-ai/chatwoot-pro` (private GHCR) | operator **can pull the private image** | Kanban (+ other Pro-image features) |
| **OSS** | `ghcr.io/indicafacil-ai/chatwoot` (our public fork) | **no** private image | standard Chatwoot + Baileys WhatsApp provider |

**Both editions work with Indica Fácil Agents**: the integration is the standard Chatwoot Agent Bot + API
(see `docs/chatwoot.md`). OSS is **not** a downgrade of compatibility, only of
Pro-exclusive features (Kanban). The Baileys WhatsApp provider ships in **both** editions.

**Edition source (in order).** The onboarding CLI captures the operator's choice up front and writes it to
`~/.indica-facil/onboarding.json` (`{ "chatwootTier": "pro" | "community", "chatwootLicenseId": "<id>" }`).
Read that marker **first**: `"pro"` → deploy the Pro image and license it at step 9b (use
`chatwootLicenseId`); `"community"` → deploy OSS (the operator deliberately chose to skip Pro). Only if the
marker is **absent** (token fallback or a non-CLI entry point) ask the user (there is no hub to query)
`whoami`): a `CHATWOOT` license → Pro; otherwise OSS. The marker wins because "proceed without Pro" is an
intent no registry check can express: an operator may own a license yet still pick OSS for this box.

## Files

| File | Use |
| --- | --- |
| `docker-compose.yml` | **Generic**: Portainer / EasyPanel / Dokploy / plain Docker. ONE file, both editions via env. |
| `docker-compose.coolify.yml` | **Coolify** (magic vars; secrets auto-generated). Pro image by default. |
| `.env.example` | Template for the generic flavor. `cp .env.example .env`, fill every `CHANGE_ME`. |

Topology (both): `chatwoot` (web) + `sidekiq` + `postgres` (pgvector) + `redis` + `baileys-api`
(the Baileys WhatsApp provider, **both editions** — public image).

## Deploy (generic: Portainer / plain Docker)

```sh
cp .env.example .env        # fill every CHANGE_ME (openssl rand -hex 64 / -hex 24)

# OSS (no subscription):
docker compose up -d

# Pro (private image): authenticate to the registry first, then set the Pro image.
docker login ghcr.io          # your GitHub username + a PAT with read:packages
CHATWOOT_IMAGE=ghcr.io/indicafacil-ai/chatwoot-pro:latest \
docker compose up -d
```

**Portainer**: paste `docker-compose.yml` as a Stack and provide the same variables in the Stack env
editor (for Pro, add `CHATWOOT_IMAGE` and register the registry credential under
Registries first, or `Registries:[<id>]` in the API). Front `chatwoot.<domain>` with a TLS proxy: the
Indica Fácil Agents [`docker-compose.portainer.yml`](../docker-compose.portainer.yml) bundled Caddy can do
this (point a Caddy site at the published `CHATWOOT_PORT`); see the `agents-onboarding` skill (`references/deploy-b-portainer.md`).

## Wire into Indica Fácil Agents

After both are up (see `docs/chatwoot.md`): create a Chatwoot admin, mint an
admin token, then from the agents register the deployment (`POST /v1/chatwoot/deployment {baseUrl, adminToken}`),
sync the account inbox, and bind an inbox to an agent (`PATCH /v1/chatwoot/inboxes/:id {agentId}`), which
auto-provisions the Agent Bot. The bind is identical for Pro and OSS.

## First admin

In the real flow the operator creates the first Chatwoot admin **in the browser** at `CHATWOOT_URL/app`.
The agent never creates the account or the admin; it waits for the operator, then reads the admin token
(`scripts/chatwoot-admin.py provision`, Rails runner read-only) to connect the deployment.
