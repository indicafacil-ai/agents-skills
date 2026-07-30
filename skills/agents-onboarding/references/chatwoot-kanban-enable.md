# Habilitar o Kanban numa instância Chatwoot Pro

Habilita as features **Pro** (Kanban) numa instância Chatwoot **Pro já deployada**. Duas coisas são
necessárias e **distintas**:

- A **imagem Pro** (`ghcr.io/nicolasdasilvaesilva/chatwoot-pro`) traz o **código** do Kanban. (O Baileys
  já vem no fork OSS público, então não é o que distingue o Pro.) Sem a imagem Pro, não há Kanban. A
  edição é escolhida no deploy (ver [`03-chatwoot-pro.md`](03-chatwoot-pro.md)).
- A **feature ligada na conta**, no super admin: imagem Pro com a feature desligada = Kanban invisível.
  É a pegadinha nº 1 — a imagem sozinha não basta.

## Quando

A edição é decidida **no deploy**, pelo marcador do CLI `~/.indica-facil/onboarding.json`
(`chatwootTier`):

- **`chatwootTier: "pro"`** → deploy da **imagem Pro**, e estes passos são **happy-path**: ligar a
  feature na conta e confirmar que o board aparece. Não pule.
- **`chatwootTier: "community"`** → deploy da imagem **OSS** (sem Kanban); nada a fazer aqui.
- **`chatwootSource: "existing"`** (Chatwoot BYO) → detecte Pro/OSS pela **imagem** (etapa 1b); não
  assuma Pro. Um Pro existente sem Kanban pode ser habilitado por estes passos, mas **não é forçado**
  (só se o usuário quiser). OSS não tem Kanban.

> Marcador ausente → **pergunte ao usuário** qual edição ele quer. Não há hub a consultar.

## Passos

> **Ao pedir o OK do usuário**, fale em linguagem de usuário: "vou ligar o Kanban no seu Chatwoot".
> **Não** cite "habilitar a feature na conta", "idempotente" nem os comandos: são o seu mecanismo.
> Frases boas × ruins em `guardrails.md`.

1. **Ligar o Kanban na conta**, via `scripts/chatwoot-admin.py` (Rails runner dentro do container):
   ```sh
   python3 scripts/chatwoot-admin.py enable-kanban --ssh root@<VPS_IP> --container <chatwoot-rails-container>
   ```
   Liga o flag da feature na conta do onboarding (a primeira conta; use `--account-id` só num brownfield
   multi-conta). Idempotente (no-op se já ligado).

   **Só dê o passo por concluído com `kanban_feature_enabled: true`.** O script sai com erro (exit 1) se
   não conseguir ligar; leia o `enable_error`:
   - `kanban_feature_not_available` → a imagem no ar **não** é a Pro (ou o build não traz o Kanban).
     Confirme a imagem (etapa 1b) antes de insistir.
   - `kanban_account_limit_reached` → limite de contas atingido; num onboarding novo não deve acontecer.

2. **Confirmação visual:** o board de Kanban aparece no menu da conta no Chatwoot. Um estado que o
   script reporta como ligado mas que não aparece na UI é sinal de imagem errada, não de configuração.

Estado das configs de assinatura/feature, quando você precisar provar sem depender da UI:
```sh
python3 scripts/chatwoot-admin.py refresh-subscription --ssh root@<VPS_IP> --container <chatwoot-rails-container>
```

## ⚠️ Licenciamento: pendente

O mecanismo de **licença** do Kanban — quem pode ligar a feature, e por quanto tempo — **ainda não está
implementado** no nosso fork. O upstream resolvia isso com um hub central que cada instância consultava
por ping (registro da instância por UUID, licença atachada, job de refresh gravando um token); nada disso
existe aqui, e as referências a `hub …` que sobrarem em qualquer doc estão obsoletas.

O nosso caminho é o **Keygen** (`keygen-portal-indicafacil`), e é a **Fase 3 do projeto do Kanban**.

Enquanto isso, o controle de acesso efetivo é o acesso à **imagem privada** no GHCR: quem não tem o PAT
não puxa a imagem, logo não tem o código do Kanban. A feature é ligada manualmente pelo passo 1.

**Não invente um fluxo de licença que não existe.** Se o usuário perguntar, explique este estado.

## Erros comuns

- **Kanban não aparece com a imagem Pro:** faltou o passo 1 (ligar a feature na conta). A imagem traz o
  código; o flag por-conta é separado.
- **`kanban_feature_not_available`:** a imagem no ar não é a Pro. Confira com a etapa 1b —
  `ghcr.io/nicolasdasilvaesilva/chatwoot-pro` = Pro; `.../chatwoot` = OSS.
- **`FRONTEND_URL` vazio:** não afeta o Kanban em si, mas quebra outros caminhos do Chatwoot que montam
  URL absoluta. Sete de todo modo.

OSS não tem nada disso (sem Kanban). Migrar OSS → Pro = re-deploy com a imagem Pro + o passo 1.
