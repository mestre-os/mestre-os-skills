---
name: Preparar OS Dual
description: |
  Deixa o seu OS pronto para funcionar com mais de um agente de IA ao mesmo tempo:
  Claude (claude.md) e agentes que leem AGENTS.md (ChatGPT/Codex, Cursor e similares).
  Varre a raiz e todos os contextos, garante que cada claude.md tem um AGENTS.md
  espelhado e identico ao lado, e aponta divergencias quando os dois sairam de sincronia.
  Idempotente: pode rodar quantas vezes quiser, so mexe no que estiver faltando ou divergente.
  Gatilhos: "preparar OS dual", "preparar pro ChatGPT", "espelhar AGENTS", "sincronizar AGENTS",
  "meu OS no Cursor", "usar com Codex", "OS dual", "dois agentes".
version: 1.0
user-invocable: true
---

# Preparar OS Dual — um OS, varios agentes

## O problema que esta skill resolve

O seu OS foi montado com o Claude como agente principal: as regras moram em arquivos `claude.md`. So que outros agentes (ChatGPT/Codex, Cursor e a maioria dos novos) nao leem `claude.md` — eles leem um arquivo chamado **`AGENTS.md`**. Se ele nao existir, esses agentes entram no seu OS cegos: sem as suas regras, sem os seus contextos, sem saber o que nunca podem fazer.

A solucao e simples e mecanica: **todo `claude.md` do OS ganha um `AGENTS.md` identico do lado** (clone byte a byte). Um arquivo e a fonte da verdade (`claude.md`); o outro e o espelho. Esta skill garante que o espelho existe e esta em dia — na raiz E em cada contexto.

## Quando rodar

- Depois de instalar o OS, se voce usa (ou pretende usar) ChatGPT, Cursor ou outro agente alem do Claude
- Depois de criar um contexto novo
- De vez em quando como conferencia (a skill e barata: so compara arquivos)
- Quando um agente que nao e o Claude parecer "perdido" no seu OS — sinal classico de AGENTS.md faltando ou velho

## Passo a passo (instrucoes para o agente)

### PASSO 1 — Mapear

Listar todos os `claude.md` do OS: o da raiz + o de cada pasta de contexto (1 nivel de profundidade; incluir subpastas de contexto se o OS tiver 3 niveis). Ignorar `historico/`, `bkp/`, pastas de backup e `.meuos/`.

### PASSO 2 — Diagnosticar

Para cada `claude.md` encontrado, verificar o `AGENTS.md` na MESMA pasta:

| Situacao | Diagnostico |
|---|---|
| `AGENTS.md` nao existe | **Faltando** — criar |
| Existe e e identico ao `claude.md` | **Em dia** — nao tocar |
| Existe mas o conteudo diverge | **Dessincronizado** — atualizar espelho |

Apresentar a tabela do diagnostico antes de mexer em qualquer coisa:

```
| Pasta | claude.md | AGENTS.md | Acao |
|---|---|---|---|
| raiz | ok | identico | nenhuma |
| ClienteA/ | ok | FALTANDO | criar espelho |
| Pessoal/ | ok | divergente (claude.md mais novo) | re-espelhar |
```

### PASSO 3 — Executar (com aprovacao)

- **Criar**: copiar o `claude.md` da pasta para `AGENTS.md`, byte a byte, sem editar nada.
- **Re-espelhar**: sobrescrever o `AGENTS.md` com o conteudo atual do `claude.md`. A direcao e SEMPRE claude.md -> AGENTS.md. Se o `AGENTS.md` estiver mais novo que o `claude.md` (alguem editou o espelho), PARAR e perguntar: o usuario decide qual versao vale, e a vencedora vai para os dois.
- Nunca editar o conteudo durante a copia: espelho e espelho.

### PASSO 4 — Selar a regra

Se o `claude.md` da raiz ainda nao tiver, propor adicionar uma linha na secao de regras:

> `AGENTS.md e um clone byte a byte do claude.md (raiz e contextos). claude.md e a UNICA fonte da verdade; nunca editar AGENTS.md a mao. Ao editar um claude.md, espelhar no AGENTS.md do lado no mesmo momento.`

Assim os proprios agentes passam a manter o espelho em dia no dia a dia, e esta skill vira so uma conferencia periodica.

### PASSO 5 — Relatorio

```
OS dual conferido ✓
claude.md encontrados: N
Espelhos criados: N · re-espelhados: N · ja em dia: N
Pendente de decisao: [pasta com AGENTS.md mais novo, se houver]
```

## Regras de seguranca

- **Nunca editar conteudo** ao espelhar: copia identica, sempre.
- **Nunca resolver divergencia sozinho** quando o espelho estiver mais novo que a fonte: perguntar.
- **Nunca criar AGENTS.md em pasta que nao tem claude.md**: espelho sem fonte e lixo.
- Esta skill nao toca em nenhum outro arquivo do OS.
