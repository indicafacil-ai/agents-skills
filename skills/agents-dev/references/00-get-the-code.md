# 00: Obter o código (Free ou Pro)

Bifurca por edição. Pergunte ao desenvolvedor qual ele tem acesso, ou deduza: sem credencial da comunidade = Free.

## Free (repo público)

Clone direto, sem credencial:
```sh
git clone https://github.com/nicolasdasilvaesilva/agents.git indica-facil-agents
```
(O repo Free é `nicolasdasilvaesilva/agents`.)

## Pro (repo privado no GitHub)

O código Pro/Full (`nicolasdasilvaesilva/agents-pro`) é privado. O acesso é por **convite no GitHub** — não há proxy nem credencial intermediária.

1. Peça acesso ao repositório. Autentique com o `gh` CLI (`gh auth login`) ou com um PAT de leitura.
2. Clone:
```sh
git clone https://github.com/nicolasdasilvaesilva/agents-pro.git indica-facil-agents-pro
```
3. **Nunca** logar o token nem commitá-lo. Se usar PAT na URL do remote, ele fica em texto plano no
   `.git/config` do clone — prefira o `gh` CLI ou um credential helper.

## Não-redistribuição (Pro)

Código e imagem Pro são privados e concedidos individualmente. Nunca publique repo, imagem ou trechos exclusivos do Full em local público (gist, fork público, registry público, post, screenshot).
