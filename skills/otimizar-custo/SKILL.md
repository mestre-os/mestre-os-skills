---
name: Otimizar Custo
description: |
  Reduz o custo de tokens das suas sessoes com Claude Code higienizando a memoria
  persistente do agente. Voce paga os tokens dessa memoria em toda conversa: cada linha
  e cobrada. Uma memoria de 263 linhas pode virar 95 (-64%) depois da higiene. Esta skill
  transforma essa reducao em economia direta todo dia. Escaneia a memoria persistente e os
  arquivos de topico, classifica entradas em OK, velhas, duplicadas ou que deveriam estar no
  seu OS, alerta se o CLAUDE.md tambem esta gordo (ele tambem entra em toda sessao) e propoe
  um plano de limpeza (sempre com aprovacao antes de executar). Calcula economia estimada em
  R$/mes no relatorio final. Executa quando o usuario diz "otimizar custo", "reduzir custo",
  "economizar tokens", "otimizar memoria", "limpar memoria", "memoria ta cara", "higienizar
  memoria", "memoria do claude", "revisar memoria", "auditar memoria".
version: 1.1
user-invocable: true
argument-hint: "(sem argumentos: roda na pasta do seu Claude Code atual)"
---

# Otimizar Custo — Reduzir o Custo de Tokens das Sessoes

## O que esta skill faz

Seu agente de IA (Claude Code) guarda uma "memoria persistente" das suas preferencias,
contexto e decisoes: ela vive numa pasta especial do seu computador (ex: o `MEMORY.md`
do Claude Code em `~/.claude/projects/<seu-projeto>/memory/`). Com o tempo essa memoria
cresce e fica com coisas velhas, duplicadas ou que deveriam estar no seu OS, e nao na
memoria do agente. Isso aumenta o custo por conversa (mais tokens carregados) e deixa o
agente mais lento ou confuso. Esta skill foca em **reduzir esse custo** higienizando a
memoria, alem de alertar quando o CLAUDE.md tambem esta crescendo demais.

Esta skill escaneia essa memoria, mostra o que pode ser limpo e executa a higiene com sua
aprovacao. Reducao tipica: 60% a 80% do tamanho.

> **Importante:** Esta skill so faz sentido se voce usa **Claude Code**. Se voce usa Cursor,
> Claude CoWork ou outra ferramenta, a "memoria" dela fica em outro lugar e funciona
> diferente: esta skill nao se aplica.

---

## Por que isso reduz seu custo

Cada conversa com o Claude Code carrega o conteudo da memoria persistente (o `MEMORY.md`)
como contexto inicial. Se ele tem 300 linhas, voce paga tokens dessas 300 linhas **em toda
mensagem**. Mantendo enxuto (sub-100 linhas), voce economiza todo dia.

Exemplo: um `MEMORY.md` de 263 linhas vira ~95 linhas apos higiene, uma reducao de **~64%**
no custo fixo de cada sessao.

---

## Quando usar

- **Quando a `otimizar-os` sugerir ao terminar uma execucao.** Esse e o canal unico do lembrete, no maximo 1x por mes. A `salvar` roda todo dia e por isso apenas observa: ela nunca sugere esta skill, senao viraria alarme diario
- Cadencia na pratica: o lembrete e mensal, mas quem decide se ha trabalho e o gate de "nada a fazer" logo no inicio. Memoria saudavel = a proxima execucao de verdade fica pra uns 90 dias
- Quando sentir que o Claude Code esta lento ou confuso com coisas antigas
- Quando o usuario disser "otimizar memoria", "limpar memoria do claude", "memoria ta cara", "auditar memoria"

---

## Passo a passo (instrucoes para o agente de IA)

### PASSO 0 — Confirmar o working directory

Antes de escanear, mostrar ao usuario o diretorio atual e pedir confirmacao:

> `"Vou escanear a memoria do Claude Code para este diretorio: [caminho]. Confirma?"`

A memoria vive em `~/.claude/projects/{working-dir-encoded}/memory/`, onde
`{working-dir-encoded}` e o caminho do diretorio atual com `/` e `\` trocados por `-` e
`:` removido. Exemplo:
- Diretorio: `C:\Users\fulano\MeuOs`
- Encoded: `C--Users-fulano-MeuOs`
- Path final: `~/.claude/projects/C--Users-fulano-MeuOs/memory/`

Se a pasta `memory/` nao existir: avisar o usuario que **ainda nao ha memoria para
higienizar** nesse diretorio (pode ser que nunca usou Claude Code aqui, ou e uma pasta
nova). Encerrar.

---

### PASSO 1 — Escanear a memoria

Listar `MEMORY.md` + todos os arquivos `.md` na pasta `memory/`.

Para cada arquivo coletar:
- Nome do arquivo
- Numero de linhas
- Tamanho em KB
- Data da ultima modificacao

Apresentar tabela com semaforo:

```
Memoria do Claude Code — [caminho]

| Arquivo | Linhas | Tamanho | Modificado | Status |
|---------|--------|---------|------------|--------|
| MEMORY.md | 263 | 26KB | hoje | 🔴 muito grande |
| feedback_email_pattern.md | 45 | 2KB | 02-MAR | 🟡 velho |
| stack-config.md | 28 | 1KB | 15-ABR | 🟢 ok |
| project_old.md | 120 | 5KB | 10-JAN | 🔴 muito velho |

Total: 8 arquivos, 54KB, ultima otimizacao: nunca
```

**Regras de semaforo:**

| Metrica | 🟢 OK | 🟡 Atencao | 🔴 Acao |
|---------|-------|-----------|---------|
| `MEMORY.md` linhas | menos de 100 | 100 a 150 | mais de 150 |
| MEMORY.md **chars** (pega linha gorda) | menos de 6KB | 6 a 10KB | mais de 10KB |
| Numero de arquivos de topico | menos de 15 | 15 a 20 | mais de 20 |
| Idade sem modificar | menos de 60 dias | 60 a 90 dias | mais de 90 dias |
| Tamanho arquivo de topico | menos de 5KB | 5 a 10KB | mais de 10KB |

> **Medir os DOIS (linhas E chars).** Uma memoria de 34 linhas com 7,7KB (cada linha virou
> paragrafo) passa no teste de linhas mas reprova no de chars: e cara do mesmo jeito. O custo
> e cobrado por token (≈ char), nao por linha.

### Verificacao extra: CLAUDE.md tambem entra no custo

Alem do MEMORY.md, **o CLAUDE.md raiz do seu OS e o CLAUDE.md do contexto ativo** tambem sao
carregados em toda mensagem (project instructions). Se eles estiverem grandes, somam tokens
em toda sessao.

Verificar e **alertar** (sem atuar, so apontar):

| Arquivo | 🟢 OK | 🟡 Atencao | 🔴 Considerar slim |
|---|---|---|---|
| `claude.md` raiz | menos de 200 linhas | 200 a 300 | mais de 300 |
| `claude.md` de contexto | menos de 150 linhas | 150 a 250 | mais de 250 |

Se algum estiver 🟡 ou 🔴, sugerir ao usuario:
> `"Detectei que claude.md [raiz/contexto X] tem N linhas: tambem entra em toda sessao.
> Considerar rodar a skill 'Otimizar OS' para slim depois desta higiene de memoria. Esta
> skill aqui foca so na memoria do agente."`

**So alertar, nao tocar no CLAUDE.md aqui.** Esta skill foca exclusivamente na memoria do
agente; o claude.md e responsabilidade da skill `otimizar-os`.

---

### PASSO 2 — Classificar cada entrada

Para cada arquivo (e para as linhas do `MEMORY.md` que apontam para topicos), classificar em
3 categorias:

| Categoria | Criterio | O que fazer |
|-----------|----------|-------------|
| **Manter** | Preferencia pessoal ativa, regra de estilo, convencao do agente (usada nas ultimas semanas) | Deixar como esta |
| **Arquivar** | Mais de 90 dias sem modificacao, conteudo sobre projeto/decisao que ja passou | Mover para `memory/historico/` |
| **Promover** | Informacao que deveria estar no seu OS (regra de negocio, decisao de produto, credencial, stack ativa) | Copiar para o OS e remover daqui |

**Como identificar:**

**Manter:** "prefiro respostas curtas", "NUNCA usar DALL-E", "sempre perguntar o contexto
antes". Sao preferencias pessoais ou de estilo: fazem sentido so aqui.

**Arquivar:** Menciona projeto concluido, bug corrigido, decisao ja implementada, ou
simplesmente nao foi tocada em 90+ dias.

**Promover:** Regra de negocio do seu cliente/produto, configuracao de stack (URL de API,
modelo usado), decisao estrategica, credencial: tudo isso cabe melhor no seu OS (nos arquivos
CLAUDE.md / DOCUMENTO_MESTRE / aprendizados) porque outros agentes que voce usar no futuro
tambem vao precisar dessa info.

---

### PASSO 3 — Plano de acao (sempre mostrar antes de executar)

Apresentar ao usuario uma lista NUMERADA agrupada por categoria:

```
Plano de Higiene — Memoria do Claude Code

ARQUIVAR (mover para historico — X acoes)
1. [project_old.md] 120d sem mod, projeto ja concluido → memory/historico/
2. [feedback_old_thing.md] 100d sem mod, feature descontinuada → memory/historico/

PROMOVER PARA O SEU OS (X acoes)
3. [meu-produto-config.md] regra de produto → copiar para sua pasta do OS
   (sugerido: CLAUDE.md do contexto relevante ou aprendizados_do_dia.md)
4. [stack-config.md] configuracao de stack ativa → copiar para o OS e depois excluir daqui

LIMPAR MEMORY.md (X linhas a remover)
5. Linha 42 ("padrao visual da minha-marca") — DUPLICADA do seu OS → remover linha
6. Linha 87 ("projeto X concluido") — evento pontual antigo → remover linha

MANTER (sem acao — X arquivos)
- feedback_prompt_format.md (preferencia pessoal, fica aqui mesmo)
- feedback_git_push.md (feedback de estilo, OK)

Reducao esperada:
- MEMORY.md: 263 → ~95 linhas (-64%)
- Arquivos de topico: 8 → 3 ativos + 2 arquivados
```

Perguntar:
> `"Posso executar o plano completo, ou prefere aprovar item por item?"`

**NUNCA executar sem resposta do usuario.** Aceitar respostas como "tudo sim", "so 1, 3 e 5",
"nao quero promover nada, so arquivar".

---

### PASSO 4 — Execucao (somente com aprovacao)

Para cada acao aprovada:

**4a. Arquivar arquivo velho**
1. Criar pasta `memory/historico/` se nao existir
2. Mover o arquivo para la
3. Remover a linha correspondente no `MEMORY.md` (se apontava para ele)

**4b. Promover para o OS**
1. Ler o arquivo de topico original
2. Identificar o destino certo no OS (perguntar ao usuario se nao for obvio):
   - Regra de negocio → `CLAUDE.md` ou `*MESTRE.md` do contexto
   - Aprendizado tecnico → `aprendizados_do_dia.md` do contexto
   - Configuracao de stack → secao de stack no `*MESTRE.md`
3. Copiar o conteudo para o destino, adaptando o formato
4. Adicionar uma nota no destino: "Promovido da memoria em DD/MM pelo usuario"
5. Excluir o arquivo original da memoria do Claude Code
6. Remover a linha correspondente no `MEMORY.md`

**4c. Limpar e enxugar o MEMORY.md**
1. Ler o `MEMORY.md` inteiro antes de alterar (nao perder nada)
2. Remover apenas as linhas aprovadas, mantendo a estrutura do indice
3. **Reescrever cada item do indice para UMA linha** (gancho curto + link). Se um item virou
   paragrafo, condensar para um gancho de uma linha: o detalhe mora no arquivo de topico, nao
   no indice. (Esta e a maior fonte de chars inflados.)
4. **Fundir arquivos de topico irmaos** sobre o mesmo assunto, com aprovacao (ex: varios
   `feedback_*` do mesmo tema viram um so): reduz o numero de arquivos e o tamanho do indice.
5. Atualizar o cabecalho: "> Ultima otimizacao: DD/MM (skill Otimizar Custo)"
6. Salvar

**Antes de qualquer alteracao, mostrar antes/depois de cada arquivo tocado:** o usuario
confirma antes de salvar.

---

### PASSO 4.5 — Verificar se ha mesmo o que otimizar (gate de "nada a fazer")

**Antes de propor qualquer plano**, verificar se o estado atual realmente justifica higiene:

| Sinal | O que fazer |
|---|---|
| MEMORY.md ja abaixo de 100 linhas + zero arquivos >90d sem mod + zero duplicatas | **Avisar que nao ha higiene a fazer** e encerrar (sem propor plano vazio) |
| Ultima execucao foi ha menos de 30 dias E metricas pioraram menos de 10% | Avisar que ainda e cedo (rodar antes de 30d so forca compactacao artificial) |
| Nao detectou nenhum item PROMOVER nem ARQUIVAR nem duplicata | Avisar que a memoria esta saudavel |

**Mensagem padrao quando nao ha nada a otimizar:**

> `"Sua memoria ja esta enxuta: MEMORY.md com X linhas (limite seria 100), Y arquivos de
> topico (limite 15), nenhum >90d sem modificacao, zero duplicatas detectadas. Nao ha higiene
> util a fazer agora. **Rodar a skill com frequencia demais deteriora arquivos** (compactacao
> excessiva remove contexto necessario). Proxima execucao recomendada: ~90 dias."`

**REGRA: nunca forcar plano de higiene quando nao ha ganho real.** Higiene excessiva remove
conteudo util: o oposto do que a skill pretende.

---

### PASSO 5 — Relatorio final com estimativa de economia em R$

Apresentar ao usuario:

**Calculo de economia em R$ (parametros simples):**
- 1 linha do MEMORY.md = ~15 tokens em media
- Custo Claude Sonnet (input): ~$3 / 1M tokens (~R$ 15 / 1M com USD a 5)
- Custo Claude Opus (input): ~$15 / 1M tokens (~R$ 75 / 1M)
- Sessoes por dia × 30 dias × tokens economizados por mensagem = economia mensal

**Formula simples:**
```
linhas_reduzidas × 15 tokens × N_mensagens_dia × 30_dias / 1_000_000 × custo_modelo_USD × 5_BRL
```

**Exemplo (reducao 263 → 94 = -169 linhas, 50 msgs/dia):**
- 169 × 15 = ~2.535 tokens/mensagem economizados
- 50 msgs/dia × 30 = 1.500 msgs/mes
- 2.535 × 1.500 = ~3,8M tokens/mes
- Sonnet: ~R$ 55/mes | Opus: ~R$ 285/mes
- Em 1 ano: R$ 660–3.420 (depende do modelo + uso)

**Formato do relatorio:**

```
Higiene de custo concluida ✓

| Metrica | Antes | Depois | Reducao |
|---------|-------|--------|---------|
| MEMORY.md | 263 linhas | 94 linhas | -64% |
| Arquivos de topico | 8 | 3 ativos + 2 arquivados | -38% |
| Tamanho total | 54KB | 19KB | -65% |

💰 Custo fixo da sessao (o que carrega em TODA mensagem):
- MEMORY.md + claude.md raiz + claude.md contexto: antes ~Xk → depois ~Yk tokens

💰 Economia estimada (input tokens cobrados em toda mensagem):
- ~2.535 tokens/mensagem economizados
- Em Sonnet (50 msgs/dia): ~R$ 55/mes
- Em Opus (50 msgs/dia): ~R$ 285/mes

Arquivados: X (em memory/historico/)
Promovidos para o OS: X (com destinos)
Linhas removidas do MEMORY.md: X

⚠️ Alerta CLAUDE.md (se aplicavel):
- claude.md raiz: N linhas (🟡 atencao / 🔴 considerar otimizar-os)
- claude.md contexto X: N linhas

Proxima higiene recomendada: DD/MM/AAAA (daqui a 90 dias)
⚠️ Rodar antes de 90d so faz sentido se houve aumento abrupto da memoria: caso contrario,
deteriora arquivos por compactacao excessiva.
```

Se houver arquivos ou linhas nao aprovados nesta rodada, listar como pendencia:
> `"Ficaram X itens que voce preferiu nao mexer agora. Posso revisar numa proxima vez."`

---

## Regras de seguranca

- **Sempre confirmar o diretorio** antes de escanear: evita mexer na memoria errada
- **Nunca executar sem aprovacao explicita:** plano primeiro, acao depois
- **Nunca deletar arquivo sem arquivar antes** (arquivar em `memory/historico/`, nao apagar definitivo)
- **Nunca promover para o OS sem identificar o destino exato:** se houver duvida, perguntar
- **Nunca modificar arquivos do OS** sem deixar uma nota de onde veio (rastreabilidade)
- **Nunca rodar em loop:** uma execucao por chamada
- **Se a pasta memory/ nao existir**, nao cria: apenas informa que nao ha o que higienizar
- **Nao auto-dispara:** o usuario precisa pedir explicitamente

---

## Formato de saida

**`MEMORY.md`** — apos a higiene:
- Cabecalho atualizado com data da otimizacao
- Indice limpo, com links apenas para arquivos de topico que existem
- Sem linhas duplicadas ou apontando para arquivos removidos

**Arquivos em `memory/historico/`** — preservados, so movidos de lugar

**Destinos no OS (quando houve promocao)** — cada entrada promovida carrega uma nota curta
indicando a origem: "Promovido da memoria em DD/MM"

---

## Integracao com outras skills (a corrente: salvar → otimizar-os → esta skill)

As tres tem ritmos diferentes de proposito, e cada uma so cobra a seguinte. Assim voce recebe um lembrete quando ele importa, em vez de tres avisos por dia que voce aprende a ignorar.

| Skill | Ritmo | Papel | Sobre a memoria |
|---|---|---|---|
| **`salvar`** | a qualquer hora, varias vezes ao dia | checkpoint, captura com gate de escrita e higiene leve | apenas OBSERVA (1 linha se estiver pesada). Nunca sugere esta skill |
| **`otimizar-os`** | semanal, quando o volume pedir | organiza os arquivos do seu OS | e QUEM lembra desta skill, no maximo 1x por mes |
| **`otimizar-custo`** (esta) | mensal sob lembrete, ~90 dias se estiver saudavel | exclusivamente a memoria do agente | e o destino do lembrete |

Rodar cada uma no seu momento mantem o sistema enxuto e barato de operar, sem transformar manutencao em ocupacao.
