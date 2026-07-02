---
name: Ligar Loop
description: |
  Porta única da engenharia de loop no seu OS: desenha o loop de agente certo pra uma
  tarefa E liga ele, num fluxo só. Primeiro DESENHA o Plano de Loop (qual padrão, os 4
  pilares, critério de pronto verificável), você aprova, e só então LIGA o loop com
  guardrails (baseline verde, ambiente isolado, caminho de volta, verificação automática,
  teto de iterações). Funde e substitui as antigas `engenharia-de-loop` e `loop-autonomo`.
  Executa quando o usuário diz: "liga o loop", "roda o loop", "rodar loop", "loop autônomo",
  "deixa rodando", "loop overnight", "põe em loop sozinho", "loop infinito", "engenharia de
  loop", "montar um loop", "desenhar um loop", "qual loop usar", "loop pra X", "como faço
  isso em loop".
  Se o usuário só PERGUNTA qual loop usar (não manda ligar), pare no Plano: ele é a resposta.
version: 1.0
user-invocable: true
argument-hint: "[objetivo do loop] (opcional)"
---

# Ligar o Loop — Desenhar o Loop Certo e Ligar com Segurança

## O que esta skill faz

Loop engineering é parar de "promptar" tarefa por tarefa e passar a projetar o loop que prompta o agente. Um agente, na definição da Anthropic, é um modelo de linguagem usando ferramentas dentro de um loop. Esta skill é a porta única: pega um objetivo, desenha a estrutura do loop (qual padrão, como verificar, quando parar), te mostra o Plano de Loop pra aprovação, e, com seu OK, liga o loop com os guardrails que o tornam seguro (baseline verde, ambiente isolado, verificação automática, teto de iterações e caminho de volta).

> Skill avançada e opcional. Dá pra usar o seu OS por meses sem ela. Ela só importa quando a tarefa exige muitas iterações: construir uma feature inteira, varrer muitos arquivos, gerar variações, ou rodar algo longo.

> Honestidade técnica: "Loop Engineering" é um termo de comunidade, não um nome oficial da Anthropic. A Anthropic chama o ciclo de agentic loop e o ambiente ao redor dele de agentic harness. Não atribuir "Loop Engineering" à Anthropic como termo oficial.

## O mecanismo, em uma frase

Você não precisa de nenhuma infraestrutura avançada pra rodar um loop. O "loop" é simplesmente pedir pro agente trabalhar de forma repetida, com um critério de parada que ele mesmo consegue checar e checkpoints ao longo do caminho. As ferramentas nativas do Claude Code já dão conta: o plan mode (planejar antes de executar), os subagentes (investigação pesada que devolve só o resumo), o comando `/goal` (se existir na sua versão, re-checa o critério a cada turno) e o Git (ramos e histórico pra isolar e desfazer).

---

## O fluxo único (dois tempos, um portão)

```
VOCÊ: "liga o loop pra X" / "roda o loop" / "qual loop usar pra X?"
   |
   v
TEMPO 1 — DESENHAR ......... PASSO 0 a 4, produz o PLANO DE LOOP
   |
   PORTÃO .................. você aprova o Plano
   |                         (pergunta-only? para aqui: o Plano é a resposta)
   v
TEMPO 2 — LIGAR ........... PASSO 5 a 9, pré-checks, andaime, guardrails,
   |                         LIGA, observabilidade, recuperação
   v
FECHAR ................... confere a entrega antes de declarar "pronto"
```

O loop só para quando o agente responde sem mais nenhuma ação a tomar. Logo: sem um critério de parada que o próprio agente consiga checar, sobra só o "parece pronto", e você vira o loop de verificação. Engenharia de loop boa elimina isso.

Regra de ouro do TEMPO 2: loop autônomo não é fire and forget. O que o torna seguro é a soma de quatro coisas: baseline verde, ambiente isolado, verificação automática e caminho de volta. Sem os quatro, não liga.

---

## Quando usar e quando não usar

Usar:
- Antes de uma tarefa que vai exigir várias iterações (feature, refatoração, varredura, build longo)
- Quando você diz "monta um loop" ou "qual o melhor jeito de fazer isso em loop"
- Quando uma tarefa "simples" já falhou duas vezes no improviso: falta estrutura

Não usar:
- Tarefa de um passo que você descreve em uma frase: só faça, depois confira a entrega
- Resposta a pergunta ou pesquisa (não é execução)
- Código delicado sem testes: primeiro crie a rede de testes, depois ligue o loop

---

# TEMPO 1 — DESENHAR (instruções para o agente)

### PASSO 0 — objetivo e critério de pronto verificável

Trave duas coisas com o usuário (ou infira e confirme) antes de escolher qualquer padrão:

1. Objetivo em uma frase. O que tem que existir no fim que não existe agora.
2. Critério de pronto VERIFICÁVEL. Como uma máquina, não você, decide que terminou? Exemplos: "os testes passam", "o build fecha com sucesso", "o lint está limpo", "o resultado bate com o esperado".

> Se não dá pra escrever o critério de pronto, PARE aqui. Loop sem critério verificável é loop que não fecha. Defina o critério primeiro (ou um teste que reproduz o bug).

### PASSO 1 — escolher o padrão (árvore de decisão)

Comece sempre pelo mais simples. Só suba a complexidade se ela melhorar o resultado de forma comprovada.

| Se o objetivo é... | Padrão |
|---|---|
| 1 passo, descritível em 1 frase | Sem loop, só faça |
| Passos fixos e previsíveis (A, B, C) | Passos fixos em sequência |
| Gerar N variações e escolher a melhor | Gerar variações e filtrar |
| Explorar e decidir o caminho na hora | Agente autônomo (plan mode) |
| Qualidade crítica antes de entregar | Verificação de qualidade (quem faz diferente de quem julga) |

### PASSO 2 — montar o setup (os 4 pilares)

Todo loop de agente tem o mesmo coração. Os 4 pilares:

1. Contexto (reunir): o que o agente tem à mão. Estado durável mora em arquivos e no histórico do Git, não na conversa. Um arquivo de progresso (`progress.txt`) que diz o que já foi feito e o que falta. Investigação pesada vai pra um subagente, que devolve só o resumo e mantém o contexto limpo.
2. Ação (agir): as ferramentas certas disponíveis e com permissões claras.
3. Verificação (verificar): o pilar que mais falha. Precisa existir um check que o agente roda sozinho (teste, build, lint). E quem faz o trabalho tem que ser diferente de quem julga: o avaliador é um subagente em contexto novo, instruído a tentar refutar, senão o agente elogia o próprio trabalho. O critério é passa/falha, não "ficou bom".
4. Parada e budget (repetir até quando): o critério do PASSO 0 amarrado, mais um teto de iterações e um teto de gasto. Se mexe em algo real (produção, dado que importa), backup e caminho de volta documentados antes.

### PASSO 3 — escolher o mecanismo (só ferramentas nativas)

- Plan mode (Shift+Tab duas vezes): o agente planeja antes de executar. Melhor pra tarefa exploratória, onde o caminho se decide na hora.
- `/goal <critério>` (se existir na sua versão): jeito nativo mais limpo numa sessão. Um avaliador re-checa o critério a cada turno até ele valer.
- Subagentes: pra investigação pesada ou pra separar quem faz de quem julga.
- Git (ramo ou worktree): pra isolar o trabalho e ter caminho de volta.

Não invente infraestrutura. O loop é o agente trabalhando de forma repetida com critério de parada e checkpoints, montado com essas peças nativas.

### PASSO 4 — apresentar o Plano de Loop e aguardar OK (o PORTÃO)

Mostre o plano mastigado:

```
PLANO DE LOOP

Objetivo: [1 frase]
Critério de pronto (verificável): [como a máquina decide que acabou]

Padrão escolhido: [nome], porque [1 linha]

Os 4 pilares:
  Contexto:    [o que vai no contexto, arquivo de progresso, subagentes]
  Ação:        [ferramentas e permissões]
  Verificação: [o check que roda sozinho e quem julga]
  Parada:      [critério, teto de iterações, teto de gasto]

Mecanismo: [plan mode / goal / subagentes / Git]
Risco e custo estimado: verde / amarelo / vermelho, [1 linha]

Confirma que ligo?
```

Se o usuário só PERGUNTOU qual loop usar, pare aqui: o Plano é a resposta.
Se mandou ligar, siga pro TEMPO 2 após o OK. Se mexe em produção, tem custo alto ou é destrutivo (vermelho), a confirmação explícita é obrigatória mesmo com o plano aprovado.

---

# TEMPO 2 — LIGAR (só após o OK do PASSO 4)

### PASSO 5 — pré-checks obrigatórios (não pular nenhum; se um falha, não liga)

- [ ] Critério de parada verificável existe (veio do PASSO 0)
- [ ] Os testes passam agora (uma base verde antes de começar)
- [ ] Ambiente isolado (ramo ou worktree dedicado no Git; nunca direto no que importa)
- [ ] Caminho de volta existe (sei como desfazer, pelo Git ou por backup)
- [ ] Teto de iterações e de gasto definidos

### PASSO 6 — montar o andaime

1. Prepare o terreno: um arquivo de progresso (`progress.txt`) com o que fazer e o que já foi feito, e um commit inicial.
2. A cada ciclo, o agente lê o histórico do Git e o arquivo de progresso pra se situar, avança em uma coisa por vez, e deixa o progresso atualizado antes de sair.

> O estado mora em arquivos e no histórico de versões, não na conversa, que é finita e degrada quando enche. O arquivo de progresso é o que dá continuidade entre uma iteração e a próxima.

### PASSO 7 — definir os guardrails

| Guardrail | Como setar |
|---|---|
| Teto de iterações | Um contador claro no loop, com limite |
| Teto de gasto | Um orçamento explícito no plano; pare ao atingir |
| Ambiente isolado | Um ramo ou worktree do Git por unidade de trabalho |
| Verificação | Check automático a cada iteração (teste, lint, build), com quem faz diferente de quem julga |
| Persistência | Arquivo de progresso e commits descritivos a cada passo |

### PASSO 8 — ligar o loop

Ligue com o mecanismo escolhido no PASSO 3:
- Plan mode pra tarefa exploratória.
- `/goal <critério>` (se existir na sua versão) pra fechar numa sessão com avaliador a cada turno.
- Subagentes pra separar quem faz de quem julga, ou pra investigação pesada.
- Git isolando cada unidade de trabalho.

### PASSO 9 — observabilidade e recuperação

A cada checkpoint, observe: avançou de verdade ou está girando em falso? O gasto acumulado está dentro do budget? O mesmo erro está voltando?

Gatilhos de parada automática:

| Sintoma | Ação |
|---|---|
| Sem progresso em dois checkpoints seguidos | Pausa, reduz o escopo, re-roda com critério explícito |
| Mesmo erro ou stack trace repetindo | Pausa, captura o contexto, escala pra você |
| Gasto saindo do budget | Pausa imediata |
| Build quebrado ou trabalho travado | Pausa, captura o contexto, recuperação informada |

Princípio: degradar com segurança (pausar e avisar) é sempre melhor que continuar gerando lixo caro.

---

## FECHAR — conferir a entrega

Todo loop termina conferindo a entrega antes de declarar "pronto". O loop não se declara concluído sem passar pelo check de qualidade. E fecha tudo: varra e execute todo item acionável antes de declarar pronto; deixe pra pedir confirmação só o que é produção, custo alto ou destrutivo. Terminar com "pontos em aberto" que dava pra fechar é falha.

---

## Anti-padrões (não cometer)

- Loop sem critério de parada verificável: o erro número um. Sempre comece pelo PASSO 0.
- Complexidade sem ganho: não use orquestração pesada numa tarefa de dois arquivos. Comece simples.
- Gerador julgando a si mesmo: sempre separe quem faz de quem verifica.
- Misturar tarefas não relacionadas no mesmo loop: limpe o contexto entre elas.
- Caçar todo achado de um avaliador adversarial leva a over-engineering: corrija o que importa.
- Encerrar cedo achando que vai estourar o contexto.

---

## Regras de segurança (invioláveis)

- Nunca ligar um loop que mexe em produção sem backup e caminho de volta documentados.
- Nunca ligar um loop sem teto de iterações e teto de gasto.
- Nunca misturar contextos diferentes no mesmo loop.
- Ambiente isolado pra qualquer ação que possa quebrar algo.
- Pensar custo primeiro: sinalizar o custo estimado com semáforo verde, amarelo ou vermelho.

---

Esta skill funde e substitui as antigas `engenharia-de-loop` (desenhar o loop) e `loop-autonomo` (deixar rodando com segurança), que ficam mantidas apenas como redirect pra cá.
