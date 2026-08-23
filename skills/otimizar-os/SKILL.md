---
name: Otimizar OS
description: |
  Organiza e compacta os arquivos do contexto ativo quando estao crescendo demais.
  Executa quando o usuario diz "otimizar OS", "organizar OS", "limpar OS", "OS ta pesado",
  "organizar arquivos", "arquivos grandes", "compactar docs", "higienizar", "limpar documentos",
  "reduzir arquivos", "arquivos crescendo", "limpar terreno", "organizar contexto".
  Analisa, propoe um plano e executa somente com aprovacao do usuario.
  Tambem confere a integridade dos links entre documentos (link quebrado, arquivo orfao).
version: 1.2
user-invocable: true
---

# Otimizar OS — Organizacao e Compactacao de Documentos

## O que esta skill faz

Esta skill analisa os arquivos de documentacao de um contexto do seu OS (a raiz, ou uma pasta de contexto e suas subpastas), identifica quais estao crescendo demais e propoe um plano de organizacao. Ela pode resumir secoes antigas, mover conteudo concluido para o historico e sugerir a criacao de arquivos secundarios quando o documento principal estiver sobrecarregado. Tudo com sua aprovacao antes de qualquer mudanca.

---

## Estrutura de arquivos do OS (o que o instalador cria)

Este e o layout padrao que o instalador MestreOS monta. A skill trabalha em cima dele:

- **Raiz do OS:** `claude.md` (regras globais), `soul.md` (personalidade e tom do agente), `index.md` (catalogo geral que aponta para os contextos)
- **Cada contexto** (pasta): `claude.md` (regras do contexto), `documento_mestre.md` (escopo, status e pendencias), `aprendizados_do_dia.md`, `changelog.md`, `index.md` (catalogo do contexto)
- **Satelites** (info densa lida sob demanda): `<contexto>/satelites/<topico>.md`
- **Historico:** `<contexto>/historico/` (conteudo arquivado)

Termos usados aqui: "mestre" = `documento_mestre.md` (o documento principal do contexto). O OS pode estar em 1, 2 ou 3 niveis (ver PASSO 0.5).

---

## Quando usar

- Quando o agente alertar que arquivos estao com semaforo 🔴 na revisao de saude
- Antes de uma sessao longa em um contexto (para "limpar o terreno")
- Quando sentir que os arquivos estao pesados e dificeis de navegar
- Uma vez por mes como higiene preventiva
- Quando o usuario diz "otimizar OS", "organizar OS", "limpar OS", "OS ta pesado"

---

## Passo a passo (instrucoes para o agente de IA)

### PASSO 0 — Backup da memoria do Claude Code (sempre primeiro)

**Antes de qualquer scan/edicao**, copiar a memoria do Claude Code para uma pasta versionada dentro do OS do usuario. Isso protege contra perda de maquina, renomeacao da pasta de trabalho ou troca de equipamento (a memoria do Claude vive em `~/.claude/`, fora do Drive/OneDrive).

**Origem:** `~/.claude/projects/{working-dir-encoded}/memory/`
**Destino:** `auto-memory-backup/{YYYY-MM-DD}/` (na raiz do OS)

```bash
DATA=$(date +%Y-%m-%d)
WORKING_DIR_ENCODED=$(pwd | sed 's|:||;s|/|-|g;s|\\|-|g')
ORIGEM=~/.claude/projects/${WORKING_DIR_ENCODED}/memory
DESTINO="auto-memory-backup/${DATA}"

# Se a memoria existe, copiar
if [ -d "$ORIGEM" ]; then
  mkdir -p "$DESTINO"
  cp -r "$ORIGEM"/* "$DESTINO/" 2>/dev/null
  echo "OK — memoria copiada para $DESTINO"
else
  echo "Sem memoria do Claude Code para este diretorio (pular)"
fi
```

**Rotacao automatica — manter os 10 backups mais recentes:**

```bash
cd auto-memory-backup 2>/dev/null && \
  ls -t | tail -n +11 | xargs -I {} rm -rf "{}" 2>/dev/null
```

**Se a pasta `auto-memory-backup/` nao existir**: criar automaticamente. **Se a pasta `~/.claude/projects/.../memory/` nao existir**: pular silenciosamente (o usuario pode nao usar Claude Code, ou e diretorio novo).

**Reportar ao usuario:** `"Backup da memoria do Claude: [N arquivos copiados para auto-memory-backup/{data}/] (10 mais recentes mantidos)"` ou `"Sem memoria pra fazer backup neste diretorio."`

---

### PASSO 0.5 — Identificar o contexto a otimizar (escopo obrigatorio)

**Esta skill SEMPRE roda em UM contexto por vez.** Antes de qualquer scan ou edicao, identificar exatamente qual pasta sera otimizada:

- Se o usuario informou na chamada: usar esse
- Se ficou obvio pela conversa: usar esse
- Se houver duvida ou nao foi informado: **PERGUNTAR**:

```
"Em qual contexto vou rodar a organizacao? Exemplos:
- Pessoal
- ClienteA
- Produtos/meu-projeto
- Raiz (apenas arquivos da raiz, sem entrar em pastas)

Qual?"
```

**NUNCA escanear o OS inteiro de uma vez.** Esta skill organiza UM contexto. Se o usuario quiser organizar varios, rodar a skill multiplas vezes (uma por contexto).

**Nota sobre profundidade do OS:** O usuario pode ter um OS em qualquer uma destas configuracoes — adaptar ao que existir:
- **Flat (1 nivel):** arquivos diretamente na raiz do OS
- **Com pastas (2 niveis):** raiz + pastas de contexto (ex: `ClienteA/`)
- **Com subpastas (3 niveis):** raiz + pastas + subpastas (ex: `ClienteA/meu-projeto/`)

O scan de diagnostico (Passo 1) cobre todos os niveis existentes. Pastas excluidas automaticamente: `.meuos/`, `historico/`, `auto-memory-backup/` e pastas de backup.

---

### PASSO 1 — Scan e relatorio de saude (APENAS DO CONTEXTO ESCOLHIDO)

**Importante:** esta skill roda em **UM contexto por vez**. Se o usuario nao informou qual, **perguntar no PASSO 0.5** antes de prosseguir. Nunca escanear o OS inteiro de uma vez — isso vira plano impossivel de aprovar item-a-item.

Escolha valida do contexto:
- "Pessoal" → escaneia raiz + apenas a pasta `Pessoal/` e suas subpastas
- "ClienteA/meu-projeto" → escaneia apenas `ClienteA/meu-projeto/` (e subpastas dela, se houver)
- "Raiz" → escaneia apenas os arquivos diretamente na raiz (sem entrar em pastas)

Para cada nivel **dentro do contexto escolhido**:
- Listar todos os arquivos `.md`
- Coletar: nome, numero de linhas, tamanho em KB
- Identificar o `documento_mestre.md` de cada contexto

Apresentar uma tabela com semaforo de saude, agrupada por contexto com path completo:

```
Relatorio de Saude — OS
Data: [DATA]

RAIZ
| Arquivo | Linhas | Tamanho | Status |
|---------|--------|---------|--------|
| claude.md | 95 | 6KB | 🟢 ok |
| soul.md | 42 | 3KB | 🟢 ok |
| index.md | 60 | 4KB | 🟢 ok |

CLIENTEA/MEU-PROJETO
| Arquivo | Linhas | Tamanho | Status |
|---------|--------|---------|--------|
| documento_mestre.md | 487 | 28KB | 🔴 muito grande |
| aprendizados_do_dia.md | 220 | 14KB | 🟡 atencao |
| changelog.md | 150 | 10KB | 🟢 ok |

CLIENTEA/OUTRO-PROJETO
| Arquivo | Linhas | Tamanho | Status |
|---------|--------|---------|--------|
| documento_mestre.md | 180 | 12KB | 🟢 ok |
| aprendizados_do_dia.md | 95 | 6KB | 🟢 ok |
```

**Regras de semaforo:**

| Arquivo | 🟢 OK | 🟡 Atencao | 🔴 Precisa de acao |
|---------|-------|-----------|-------------------|
| `documento_mestre.md` (qualquer nivel) | menos de 300 linhas E menos de 25KB | 300 a 500 linhas ou 25 a 40KB | mais de 500 linhas OU mais de 40KB |
| `claude.md` | menos de 200 linhas | 200 a 300 | mais de 300 |
| Arquivos secundarios (ex: satelites) | menos de 25KB | 25 a 40KB | mais de 40KB |
| `changelog.md` | menos de 30KB | 30 a 50KB | mais de 50KB |
| `aprendizados_do_dia.md` | menos de 200 linhas E de 15KB | 200 a 250 linhas ou 15KB | mais de 250 linhas OU mais de 15KB |
| `index.md` | menos de 100 linhas | 100 a 150 | mais de 150 |
| Outros arquivos `.md` | menos de 20KB | 20 a 35KB | mais de 35KB |

**Custo fixo da sessao (numero unico):** alem do tamanho por arquivo, somar os arquivos que carregam em TODA sessao — `claude.md` raiz + `soul.md` + `claude.md` do contexto + `documento_mestre.md` + `aprendizados_do_dia.md` + a memoria do Claude Code. Reportar o total estimado em tokens (~1 linha = 15 tokens) e a meta:
> `Custo fixo atual: ~Xk tokens/sessao. Meta apos organizacao: ~Yk.`
Esse e o numero que importa — e o que se paga em TODA mensagem, nao o tamanho de um arquivo isolado.

---

### PASSO 1.5 — Gate no piso, sem acao

Antes de montar qualquer plano, verificar se ha mesmo o que reduzir. Se todos os arquivos estao 🟢, OU o que esta acima do limite e majoritariamente conteudo perene ja curado (sem temporal velho >60d, sem duplicata, sem cemiterio de tarefas, sem secao densa extraivel), parar aqui com a mensagem: `Este contexto ja esta no piso — o que carrega e conteudo perene necessario, nao ha compactacao util a fazer. Sem acao.` **Nunca inventar plano quando nao ha ganho real.** Compactar conteudo perene irredutivel piora o OS — e o oposto do objetivo da skill.

---

### PASSO 2 — Analise profunda

Para cada arquivo com status 🔴 ou 🟡 (em qualquer nivel), analisar o conteudo e identificar:

**2a. Separar o que e permanente do que e temporario (criterio primario)**

Antes de olhar a idade do conteudo, o agente classifica cada bloco pelo seu TIPO:

| Tipo | Exemplos | O que acontece |
|------|----------|----------------|
| **Permanente** | Regras do seu negocio, padroes de trabalho, convencoes, "nunca fazer X", configuracoes ativas | **Fica onde esta** — nao importa a idade |
| **Promovivel** | Conteudo perene que merece subir de lugar: decisao de negocio, regra rigida de operacao ou regra tecnica de um tema | **Promover para o destino certo** (sao 3 destinos diferentes, ver 2d) |
| **Temporario** | Entregas concluidas, bugs corrigidos, decisoes pontuais, status updates datados | Compacta conforme a idade (ver abaixo) |
| **Ultrapassado** | Status que nao vale mais, pesquisa ja usada, decisao substituida por outra mais recente | **Vai para o historico** ou changelog |

**Como o agente identifica o tipo:**
- Contem "nunca", "sempre", "regra", "padrao", "obrigatorio" → provavelmente **permanente**
- Contem data especifica + resultado pontual ("Bug X corrigido em DD/MM") → **temporario**
- Referencia a estado passado ("aguardando X" quando X ja aconteceu) → **ultrapassado**
- Usado em toda sessao do contexto (o agente consulta frequentemente) → **promovivel**

**2a.1 Para conteudo temporario, aplicar criterio de idade:**

| Idade | O que fazer |
|-------|-------------|
| Menos de 30 dias | Nao mexer — conteudo ativo |
| 30 a 60 dias | Propor condensacao (3 paragrafos viram 3 linhas) |
| 60 a 90 dias | Condensar obrigatoriamente + mover detalhes para o changelog |
| Mais de 90 dias | Manter apenas 1 linha resumo + referencia ao changelog |

**2b. Secoes densas que podem virar arquivos separados**

Quando um `documento_mestre.md` (em qualquer nivel do OS) tiver uma secao com mais de 50 linhas sobre um unico tema, ela e candidata a virar um arquivo separado referenciado no mestre. Criar o arquivo separado na mesma pasta do mestre (ou em `satelites/`, ver 2d).

Exemplos de bons candidatos para arquivo separado:
- Historico de decisoes tecnicas de um sistema especifico
- Especificacoes detalhadas de um modulo ou produto
- Mapeamentos de APIs e integracoes
- Documentacao de fluxos comerciais detalhados

**2c. Conteudo obsoleto**

Identificar:
- Arquivos de pesquisa ou analise pontuais que ja cumpriram seu papel
- Secoes sobre decisoes que foram substituidas por decisoes mais recentes
- Status desatualizados (ex: "aguardando X" sendo que X ja aconteceu)

**2d. Conteudo que merece promocao — TRES destinos, por natureza e frequencia**

Algumas entradas nos seus aprendizados nao sao aprendizados datados: sao regras ou decisoes perenes. Elas nao deveriam ficar num arquivo rolante. Mas "sair dos aprendizados" nao significa "ir todo mundo pro mesmo lugar": o destino depende do QUE o item e e de COM QUE FREQUENCIA ele e consultado.

| O item e... | Destino | Por que |
|---|---|---|
| **Decisao de negocio, estrategia ou plano** consultado sempre (modelo de preco, posicionamento, escopo) | `documento_mestre.md` | o mestre ja carrega em toda sessao e e onde decisao mora; e o documento vivo |
| **Regra RIGIDA de operacao** do contexto (limite inviolavel, tipo "nunca cruzar dados deste cliente") | `claude.md` do contexto | e a lei de COMO se trabalha ali. Mexer no claude.md e a excecao da excecao, quase nunca acontece |
| **Regra de UM tema especifico** (tabela de taxas, regra de um modulo, detalhe de integracao) | satelite em `<contexto>/satelites/<topico>.md` + ponteiro de 1 linha no mestre | tira o peso da sessao; o agente abre o satelite so quando o assunto aparece |

**Analogia mesa/gaveta:** o mestre e a mesa (tudo ali carrega em toda sessao — promover regra de tema pra mesa nao reduz o imposto fixo, so muda de bolso); o satelite e a gaveta (lido so quando o tema surge — mover pra gaveta reduz de verdade).

**Satelite nasce por dois criterios DIFERENTES. Nao confundir os dois.**

- **Na ESCRITA (vale sempre, mesmo com o mestre pequeno):** a casa do conteudo se decide pela NATUREZA do fato, nunca pelo tamanho do arquivo. Medicao, inventario, especificacao e evidencia **nascem** no satelite do tema, com data; o mestre fica so com o ponteiro de uma linha. Estado atual, com quem esta a bola e proximo passo **nascem** no mestre. E isso que impede o mestre de engordar.
- **No SPLIT RETROATIVO (a faxina do que JA esta dentro do mestre), as DUAS condicoes precisam ser verdade:** (1) o mestre ja esta 🟡 (mais de 300 linhas ou 25KB; prioridade se 🔴) e (2) ha ~40+ linhas sobre UM mesmo tema. Mestre pequeno nao justifica split, e splittar 10 linhas fragmenta sem ganho.

O agente identifica essas regras e pergunta:
> `"Encontrei X regras nos aprendizados que parecem permanentes. Quer que eu promova para o documento mestre?"`

**Fluxo:** regra vai pro destino certo → removida dos aprendizados → registrada no changelog. Sempre com aprovacao.

> ⚠️ **NUNCA promover regra operacional para o soul.md.** O soul trata so de carater, comportamento e perfil do agente — deve ser leve. Regrinhas operacionais vao para claude.md / documento_mestre / satelite, nunca para o soul.

**2e. Cemiterio de tarefas concluidas no mestre**

Versoes antigas da rotina de fechamento deixavam uma lapide no mestre a cada tarefa migrada (`~~[x] tarefa~~ → ver changelog [data]`). Da versao atual da `salvar` em diante, **o item concluido sai do mestre** — o changelog ja e o registro. Entao este bloco vira **migracao de legado, rodada uma vez**: se o scan achar linhas riscadas (qualquer quantidade, nao espere juntar 15), propor colapsar TODAS em UM unico ponteiro, com preview e aprovacao como qualquer acao desta fase:

> `**Tarefas concluidas nao ficam listadas aqui.** Historico completo, com data, no changelog.`

**Detector de skill velha:** se, depois dessa limpeza, aparecerem lapides NOVAS no mestre, a rotina de fechamento em uso esta desatualizada. Avisar o usuario e sugerir que ele reinstale a versao atual da `salvar` pelo canal de atualizacao do OS dele.

**2f. Frontmatter de manutencao (a ficha de identificacao do arquivo)** ⭐

Frontmatter e um bloco curto de metadados no TOPO do arquivo, entre duas linhas `---`. Ele faz pelo documento o que uma ficha de identificacao faz por uma pasta num arquivo fisico: o agente le a ficha e ja sabe o que e aquilo, de quando e, e se ainda vale, sem precisar ler o documento inteiro pra descobrir.

Padrao minimo para os documentos vivos do contexto:

```yaml
---
updated: AAAA-MM-DD    # data da ultima edicao relevante
context: NomeDoContexto
type: mestre | claude | satelite | changelog | aprendizados | index
status: vivo | congelado | arquivado
---
```

**Como esta skill usa o frontmatter:**
- **Lendo:** quando ele existe, a manutencao deixa de ser adivinhacao. O scan usa `updated` pra saber a idade de verdade (e nao chutar pela data escrita no meio do texto), a classificacao do PASSO 2 usa `type` e `status` em vez de deduzir pelo conteudo, e a caca de orfaos pula quem esta com `status: arquivado`.
- **Escrevendo (regra do escoteiro):** ao editar um documento por qualquer motivo, propor colocar ou atualizar o frontmatter DELE no mesmo lote de aprovacao. **Nunca fazer migracao em massa** so pra carimbar frontmatter em tudo: e mexida enorme por um ganho que so aparece depois. A cobertura cresce sozinha, arquivo por arquivo.
- **Onde vale mais:** nos satelites e nos documentos lidos sob demanda. Nos arquivos que carregam em TODA sessao (`claude.md`, mestre, aprendizados), so vale se o ganho compensar as ~5 linhas a mais de custo fixo.
- **Sem duplicata:** `updated` passa a ser o unico carimbo de edicao. Se o arquivo ganhou frontmatter, apagar a linha solta "Ultima atualizacao: ..." do corpo do texto, senao viram duas datas que discordam entre si.

---

### PASSO 3 — Plano de acao (sempre mostrar antes de executar)

Apresentar ao usuario uma lista numerada das acoes propostas, agrupadas por tipo e indicando o path completo de cada arquivo:

```
Plano de Organizacao — OS

RESUMIR CONTEUDO ANTIGO (X acoes)
1. [ClienteA/meu-projeto/documento_mestre.md] Secao "Decisoes de Marco" (mais de 60 dias): condensar de 45 → ~8 linhas
2. [ClienteA/meu-projeto/changelog.md] Entradas antes de Janeiro/2026: arquivar em historico/

CRIAR ARQUIVO SEPARADO (X acoes)
3. [ClienteA/meu-projeto/documento_mestre.md] Secao "Integracao com API X" (55 linhas): criar ClienteA/meu-projeto/satelites/tech_api_x.md
4. [ClienteA/meu-projeto/documento_mestre.md] Secao "Historico de Contratos" (70 linhas): criar ClienteA/meu-projeto/satelites/comercial_contratos.md

ARQUIVAR OBSOLETOS (X acoes)
5. [ClienteA/meu-projeto/pesquisa_plataformas_2025.md] Analise pontual ja concluida → mover para ClienteA/meu-projeto/historico/

MANTER (sem acao)
- [claude.md] Conteudo evergreen — nao alterar
- [ClienteA/outro-projeto/documento_mestre.md] Tamanho adequado — nao alterar
```

Perguntar ao usuario:
> `"Posso executar o plano completo? Ou prefere aprovar item por item?"`

**NUNCA executar sem resposta do usuario.**

---

### PASSO 4 — Execucao (somente com aprovacao)

Executar apenas os itens aprovados, nesta ordem:

**4a. Resumir conteudo antigo**
1. Ler a secao original antes de alterar (nao perder nada)
2. Reescrever em formato compacto:
   - Decisoes: `**[DATA] Decisao:** [resultado em 1 frase]. Detalhes no changelog [DATA].`
   - Processos concluidos: `**[TEMA]:** [resultado final]. Ver changelog para detalhes.`
   - Status desatualizados: remover (ja estao no changelog)
3. Verificar que nenhuma referencia a outros arquivos quebrou

**4b. Criar arquivo separado (split)**
1. Criar novo arquivo com nome descritivo em `<contexto>/satelites/`: `<area>_<tema>.md`
2. Adicionar no topo do novo arquivo uma linha apontando de onde veio:
   ```
   > Documento pai: [path/documento_mestre.md]
   ```
3. Mover o conteudo (cortar do mestre, colar no novo arquivo)
4. No `documento_mestre.md`, substituir o conteudo removido por um ponteiro (gancho inline):
   ```
   > **[TEMA]:** [resumo de 1 a 2 linhas]. Documento completo: `[path/nome_do_arquivo.md]`
   ```
5. Atualizar a tabela de arquivos do contexto no documento mestre (se houver)

**Atualizar index.md apos cada criacao:**
- Se `index.md` existir na pasta do contexto: adicionar entrada para o novo arquivo com link e descricao
- Se o arquivo original foi arquivado: remover a entrada do index.md do contexto
- Se houve mudanca na raiz: atualizar tambem o index.md da raiz
- Atualizar data e contadores no cabecalho de cada index tocado
- O index.md e atualizado JUNTO com cada acao — nao esperar o final

> Cada contexto tem seu proprio index.md. A raiz tem o index geral que aponta para os contextos.

**Limite:** no maximo 3 arquivos novos por execucao para nao fragmentar demais.

**Como a arvore de arquivos fica organizada depois da execucao:**

```
documento_mestre.md (documento principal — ponteiros para tudo, max 300 linhas)
|
+-- satelites/tech_decisoes.md (tema principal)
|   |
|   +-- satelites/tech_decisoes_sub.md (sub-tema, se o principal crescer muito)
|
+-- satelites/comercial_contratos.md (outro tema)
|
+-- changelog.md (historico de entregas e decisoes)
    |
    +-- historico/changelog_2026_Q1.md (arquivado quando o changelog passa de 50KB)
```

**Regra do ponteiro dos dois lados:**
- Arquivo pai (mestre) aponta para baixo: `ver satelites/tema.md`
- Arquivo filho (separado) tem cabecalho apontando para cima: `> Documento pai: documento_mestre.md`

Isso mantem a navegacao clara nos dois sentidos.

**4c. Arquivar conteudo obsoleto**
1. Criar pasta `historico/` dentro do mesmo contexto se nao existir
2. Mover arquivo para `[path]/historico/nome_original.md`
3. Se for o changelog: quando passar do limite (50KB), **quebrar por data** — mover as entradas antigas para arquivos datados em `historico/` (ex: `historico/changelog_2026_Q1.md` por trimestre, ou `historico/changelog_2026-06.md` por mes se muito ativo), mantendo no changelog vivo so as entradas recentes + o cabecalho. Cada arquivo datado e um pedaco fechado daquele periodo.

**4d. Integridade referencial: links quebrados e arquivos orfaos (SEMPRE executar)** ⭐

Um OS nao se degrada so por inchar. Ele se degrada por **perder as ligacoes entre os documentos**: o arquivo continua la, mas ninguem mais chega nele. Esta checagem cobre TODOS os `.md` do contexto, porque qualquer documento pode apontar para qualquer outro, nao so o `index.md` e o mestre.

Sao tres defeitos diferentes:

| Defeito | O que e | Por que acontece |
|---|---|---|
| **Link quebrado** | Um link `[texto](arquivo.md)` ou `[[wikilink]]` cujo alvo nao existe mais no disco | Renomear ou mover um arquivo NAO atualiza quem apontava pra ele. Todos os links quebram em silencio e ninguem descobre ate um agente seguir o ponteiro morto |
| **Orfao de indice** | O `.md` existe no disco (normalmente escondido numa subpasta) mas nao e citado no `index.md`, nem no mestre, nem no `claude.md` do contexto | Arquivo criado no meio de uma sessao e nunca catalogado. O agente futuro nao sabe que ele existe e o conhecimento se perde |
| **Orfao total** | NENHUM outro documento do contexto referencia esse arquivo (zero links de entrada) | E o sinal mais forte de sobra de sessao antiga. Principal candidato a `historico/` |

**Procedimento:**

1. Listar TODOS os `.md` do contexto escolhido (recursivo, ignorando `historico/`, `tmp/`, `node_modules/`, `.git/`).

2. **Varrer os links de saida:** em cada `.md`, extrair os links markdown `[texto](alvo.md)` e os wikilinks `[[nome]]`, resolver cada alvo no disco e anotar os que nao existem. Esses sao os links quebrados.

3. **Contar os links de entrada:** para cada arquivo, contar quantos documentos do contexto apontam pra ele. Zero referencias em qualquer lugar = orfao total. Sem referencia no `index.md` / mestre / `claude.md`, mas citado por outro documento = orfao de indice.

4. Apresentar a tabela unica ao usuario:

```
| # | Achado | Arquivo | Detalhe | Sugestao |
|---|--------|---------|---------|----------|
| L1 | Link quebrado | ClienteA/meu-projeto/documento_mestre.md | aponta pra satelites/tech_api.md (nao existe) | Apontar pro nome novo: satelites/tech_api_v2.md |
| L2 | Link quebrado | ClienteA/meu-projeto/index.md | [[pesquisa_antiga]] sem alvo | Remover a entrada (arquivo foi arquivado) |
| O1 | Orfao de indice | ClienteA/meu-projeto/docs/analise_concorrentes.md | citado no mestre, fora do index | Adicionar ponteiro no index.md |
| O2 | Orfao total | ClienteA/meu-projeto/tmp_old/rascunho_velho.md | zero links de entrada | Mover para historico/ |
```

5. Aguardar aprovacao item-a-item ou em lote ("todos os links sim, O2 arquivar").

6. Executar os aprovados:
   - **Consertar o link:** se o alvo foi renomeado, apontar pro nome novo. Se foi arquivado de verdade, remover a entrada.
   - **Adicionar entrada no `index.md`** da pasta correspondente: `- [NOME](caminho) — descricao em uma linha`
   - **Mencionar no mestre** com ponteiro, se for satelite relevante pro contexto
   - **Mover para `historico/`**, se for obsoleto

**Re-check obrigatorio no fim da execucao.** Se ESTA skill renomeou, moveu, dividiu ou arquivou algum arquivo (passos 4b e 4c), ela mesma acabou de criar links quebrados. Antes de encerrar, rodar de novo a varredura de links nos arquivos que apontavam pros arquivos tocados e consertar. O conserto nao acontece sozinho, e uma otimizacao que quebra a navegacao do OS deixou o sistema pior do que achou.

**REGRA — nunca decidir sozinho:** o agente conserta link quebrado sem perguntar (e correcao mecanica, o alvo certo e obvio), mas **nunca** decide sozinho se um arquivo orfao e relevante ou lixo. Orfao sempre vai pra tabela e espera resposta.

**4e. Confirmar cada alteracao**
Antes de salvar qualquer mudanca em arquivo existente, mostrar o antes e depois:
```
ANTES:
[trecho original — primeiras linhas]

DEPOIS:
[trecho resumido — como ficara]

Confirmar? (sim / nao / ajustar)
```

---

### PASSO 5 — Relatorio final

Apresentar o resultado da organizacao com paths completos:

```
Organizacao concluida ✓

| Arquivo | Antes | Depois | Reducao |
|---------|-------|--------|---------|
| ClienteA/meu-projeto/documento_mestre.md | 487 linhas | 220 linhas | -55% |
| ClienteA/meu-projeto/changelog.md | 210 linhas | 140 linhas | -33% |

Novos arquivos criados:
- ClienteA/meu-projeto/satelites/tech_api_x.md (detalhes da integracao)
- ClienteA/meu-projeto/satelites/comercial_contratos.md (historico de contratos)

Arquivados:
- ClienteA/meu-projeto/historico/pesquisa_plataformas_2025.md

Status atual:
- ClienteA/meu-projeto/documento_mestre.md: 🟢 ok
- ClienteA/meu-projeto/changelog.md: 🟢 ok
- ClienteA/meu-projeto/aprendizados_do_dia.md: 🟢 ok

Integridade: [N links quebrados corrigidos · N orfaos catalogados · N arquivados]
Frontmatter: [N arquivos ganharam ficha nesta rodada]

Custo fixo da sessao: ~Xk → ~Yk tokens.
```

Se ainda houver arquivos 🟡 ou 🔴 restantes (itens nao aprovados), indicar claramente:
> `"Ainda ha X arquivos acima do limite ideal. Posso organiza-los numa proxima execucao quando quiser."`

**Lembrete da higiene de memoria (no maximo 1x por mes).** Esta skill cuida dos ARQUIVOS do seu OS; a memoria do agente e outra coisa e tem skill propria (`otimizar-custo`). Ao concluir, se fizer mais de um mes desde a ultima passada na memoria, fechar com uma linha:
> `"De olho tambem na memoria do agente: faz mais de um mes desde a ultima limpeza. Quando quiser, e so falar 'otimizar custo'."`

**Esta skill e o unico canal desse lembrete.** A `salvar` roda todo dia e, se ela tambem cobrasse, viraria alarme diario e voce ia parar de ler. A `salvar` no maximo observa, sem sugerir.

---

## Formato de saida

**`documento_mestre.md`** — apos a organizacao:
- Deve ser legivel em menos de 5 minutos
- Contem: escopo do contexto, status atual, pendencias abertas, ponteiros para arquivos de detalhe
- NAO contem: historico detalhado, logs de decisoes antigas, especificacoes extensas

**Arquivo separado criado:**
```markdown
> Documento pai: [path/documento_mestre.md]

# [Titulo do Tema]
> Criado em: [DATA] | Extraido de: documento_mestre.md

[Conteudo completo do tema]
```

**changelog.md** — estrutura mantida, apenas entradas antigas arquivadas (por data em `historico/`) se aprovado.

---

## Regras de seguranca

- **Nunca executar sem aprovacao** — sempre mostrar o plano primeiro
- **Nunca apagar conteudo** — apenas mover (changelog, historico/ ou arquivo separado)
- **Nunca resumir regras de negocio fundamentais** — independente da idade
- **Nunca promover regra operacional para o soul.md** — o soul e so carater e perfil do agente
- **Nunca criar mais de 3 arquivos novos por execucao** — evita fragmentacao excessiva
- **Nunca quebrar links entre arquivos** — todo arquivo separado tem ponteiro bidirecional
- **Nunca modificar arquivos de outro contexto** (quando o escopo for um subcontexto especifico)
- **Sempre ler o arquivo antes de alterar** — nada de editar sem entender o conteudo primeiro
- **Sempre mostrar antes/depois** para alteracoes em arquivos existentes
- **Nunca assumir que o OS e flat** — sempre escanear raiz + pastas + subpastas antes de declarar o relatorio completo

---

## Checklist final: a execucao foi bem feita? (conferir ANTES de dizer que terminou)

- [ ] Rodou SO no contexto aprovado; nenhum arquivo de outro contexto foi tocado
- [ ] Todo ajuste executado tinha OK explicito do usuario (nenhuma acao por conta propria)
- [ ] Nada foi apagado, so movido (changelog ou `historico/`), com antes/depois mostrado
- [ ] Todo split deixou ponteiro dos DOIS lados e entrou no `index.md` na mesma rodada
- [ ] Nenhum link quebrou: os links que APONTAM para cada arquivo movido foram re-checados
- [ ] Estado atual e "com quem esta a bola" continuam no mestre; nenhum satelite virou dono de status
- [ ] Lapides de tarefa concluida foram colapsadas em um unico ponteiro (migracao de legado)
- [ ] Tabela final `arquivo | antes | depois | reducao` apresentada ao usuario

Se algum item falhou, corrigir ANTES de declarar concluido. Nunca reportar "pronto" com item pendente.
