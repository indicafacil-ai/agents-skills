# agents (skills do Indica Fácil Agents)

Skills que cobrem o ciclo de vida da **Indica Fácil Agents**, distribuídas juntas num único plugin/tap:

- **`agents-onboarding`**: subir uma instância nova num VPS, do zero ao agente de atendimento: deploy por tier (Coolify / Portainer / compose), Chatwoot + Langfuse com TLS, branding, import do agente via MCP e validação ponta a ponta.
- **`agents-dev`**: trabalhar no código-fonte: clonar o repo (Free público ou Pro por convite no GitHub), invariantes e separação Free/Full, implementação conduzida e geração da própria imagem.
- **`agents-operation`**: debugar/ajustar uma instância **em produção**: diagnóstico (Chatwoot + ExecutionLog + Langfuse), reprodução no playground e ajuste do agente com toda mutação aprovada.

São skills **executadas pelo agente**. Funcionam em **Claude Code**, **Codex** e **Hermes**, a partir da mesma fonte (a pasta `skills/`).

## Instalação

Para onboarding, normalmente você **não** roda os comandos à mão: o instalador detecta o seu agente de IA e faz tudo (MCPs, skill e handoff):

```sh
curl -fsSL https://agents.indicafacil.ai/install.sh | bash
```

Para instalar manualmente:

### Claude Code / Codex

Instalam o plugin inteiro (as 3 skills ficam disponíveis, invocáveis por `/agents-…`):

```sh
claude plugin marketplace add indicafacil-ai/agents-skills
claude plugin install agents@agents
```

```sh
codex plugin marketplace add indicafacil-ai/agents-skills
codex plugin add agents@agents
```

### Hermes

Instala **por skill** (escolha as que quiser) a partir do mesmo tap:

```sh
hermes skills tap add indicafacil-ai/agents-skills
hermes skills install indicafacil-ai/agents-skills/agents-onboarding --yes --force
hermes skills install indicafacil-ai/agents-skills/agents-dev --yes --force
hermes skills install indicafacil-ai/agents-skills/agents-operation --yes --force
```

> O `--force` do Hermes passa o verdict `caution` do scanner de skills: as skills fazem operações de DevOps legítimas (SSH, `sudo`, leitura de env vars) que o scanner sinaliza. É esperado.

## Estrutura

- `skills/<skill>/`: cada skill (SKILL.md + `guardrails.md`, `gotchas.md`, `references/`; a onboarding também embute o deploy kit: composes, `deploy/`, `docs/`, `scripts/`). A fonte que os três agentes consomem.
- `.claude-plugin/`: manifesto do marketplace + do plugin para Claude Code e Codex (`source: "./"`, 1 plugin com as 3 skills em `available_skills`). O Hermes ignora isto e lê direto de `skills/`.

## Licença e origem

MIT. Ver [`LICENSE`](LICENSE).

Obra derivada de [fazer-ai/agents-skills](https://github.com/fazer-ai/agents-skills) (MIT). O aviso de
copyright original está preservado no `LICENSE`, como a licença exige. Não somos afiliados à FAZER.AI LTDA.
