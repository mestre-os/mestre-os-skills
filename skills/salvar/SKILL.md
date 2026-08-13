---
name: Salvar
description: |
  Checkpoint de soberania de contexto. Roda a QUALQUER hora, quantas vezes
  precisar, quando a janela de contexto aperta (por volta do amarelo / 80%)
  ou quando o trabalho merece ser preservado. Sem saudacao, sem "boa noite",
  sem juizo de horario. Confere o que foi entregue (com evidencia), sintetiza,
  AVALIA os arquivos antes de escrever (gate anti-duplicacao e anti-verborragia)
  e grava um checkpoint duravel que reconstroi o estado mesmo que o provedor
  compacte a janela sozinho.
  Gatilhos: "salvar", "salva isso", "salva o contexto", "checkpoint",
  "da um checkpoint", e os ANTIGOS (aliases que continuam funcionando):
  "fim do dia", "fechar o dia", "conferir entrega", "verificar entrega",
  "revisao diaria", "terminei", "pronto", "feito", "entregue", "finalizado",
  "ta pronto?".
version: 1.1
user-invocable: true
---

# Salvar — Checkpoint de Soberania de Contexto

## O que esta skill faz

Quando a janela de contexto enche, o provedor (o sistema que roda a IA por baixo) compacta a conversa sozinho, de forma opaca: voce nao controla o que sobra nem em que formato. Esta skill tira esse controle das maos do provedor e poe nas suas. Antes de perder o fio, ela confere o que foi entregue, sintetiza, e grava um checkpoint duravel no SEU formato, de forma que uma sessao nova reconstroi o estado exato mesmo depois de uma compactacao automatica.

Ela une duas rotinas que antes eram separadas:
- **Conferir entrega** (checagem de qualidade com evidencia), agora **adaptativa** (so confere o que de fato aconteceu).
- **Fim do dia** (sintese, aprendizados, organizacao do OS), agora **sem ritual de horario**.

E adiciona o que faltava: **o arquivo de checkpoint**, que sobrevive a compactacao.

> Ideia central: e melhor a gente se compactar do que ser compactado. Voce roda `salvar`, fecha a sessao e abre uma nova. A compactacao vira sua, no seu formato, no seu ritmo.

---

## Quando rodar (o semaforo do anel de contexto) ⭐

Voce pode rodar `salvar` a QUALQUER hora, quantas vezes quiser (tres vezes na mesma sessao longa, se precisar). Mas o gatilho PRINCIPAL e visual.

No Claude Code (e em ferramentas parecidas), a janela de contexto aparece como uma bolinha ou anel que vai enchendo. Use ela como semaforo:

- 🟢 **Verde**: pode seguir trabalhando, contexto tranquilo.
- 🟡 **Amarelo**: rode `salvar` AGORA. Ainda da tempo de gravar um checkpoint limpo antes do sistema mexer.
- 🔴 **Vermelho**: rode `salvar` imediatamente, feche a sessao e abra uma nova. Continue a partir do checkpoint.

**Por que isso importa:** quando o contexto enche, o provedor compacta a conversa por conta propria e de forma opaca. Voce perde o controle do que fica salvo e do que some. Rodar `salvar`, fechar e abrir uma sessao nova significa que VOCE faz a sua propria compactacao, no seu formato, mantendo a soberania do contexto. Melhor se compactar do que ser compactado.

Alem do semaforo, tambem vale rodar:
- Ao terminar uma entrega e querer travar o estado com evidencia.
- Antes de uma pausa, de limpar a conversa, ou de trocar de tarefa.

**O agente pode SUGERIR rodar `salvar`** ao perceber o contexto ficando pesado (sessao longa, muitas acoes), mas **nunca roda sozinho**: espera voce pedir.

---

## Principios inviolaveis

1. **Evidencia, nao opiniao.** "Verifiquei X, deu Y" e evidencia. "Acho que ficou bom" nao e.
2. **Nao forcar conteudo.** Bloco vazio fica vazio. Nunca inventar aprendizado, pendencia ou verificacao so pra preencher.
3. **Aprovacao antes de mover.** Nunca apagar ou migrar arquivo sem mostrar e perguntar.
4. **Tom neutro.** Zero saudacao, zero "boa noite", zero juizo de horario. Fala "checkpoint salvo", "estado preservado".
5. **Escrever e excecao, nao obrigacao.** A rotina AVALIA todos os arquivos, mas so ESCREVE onde sobrou item que passou no gate (PASSO 3.5). Sessao sem material para um arquivo = arquivo INTOCADO. Escrever "pra constar" e exatamente o que incha o OS.

---

## Contrato por arquivo (onde cada coisa mora) ⭐

Metade do inchaco de um OS nao vem de escrever demais: vem de escrever no lugar errado. Antes de gravar qualquer coisa, o agente consulta esta tabela para decidir o destino.

| Arquivo | O que entra | O que NUNCA entra |
|---|---|---|
| `claude.md` (do contexto) | So regra RIGIDA de operacao: limite inviolavel, configuracao fixa. Mexer aqui e a excecao da excecao | Caso do dia, status, decisao de negocio, historico |
| `documento_mestre.md` | O documento VIVO: escopo, status, pendencias, decisoes estrategicas e taticas, planos, ponteiros para os satelites | Especificacao densa (vai pra satelite), historico (vai pro changelog), caso pontual |
| `aprendizados_do_dia.md` | Regra, padrao ou anti-pattern REUTILIZAVEL, em texto curto e objetivo | Narrativa da investigacao, evento datado, caso que nao se repete |
| `changelog.md` | O lar do caso pontual: o que foi feito, incidentes, narrativa com data (so acrescenta, nunca reescreve) | Regra viva, que mora nos arquivos acima |
| `satelites/<topico>.md` | Conteudo denso de UM tema, lido so quando o tema aparece | Coisa consultada em toda sessao (essa vai pro mestre) |
| `index.md` | Catalogo completo dos `.md` do contexto: link + 1 linha de descricao | Conteudo de verdade |
| `soul.md` (raiz) | So carater, tom e papel do agente | Qualquer regra operacional |

Regra pratica: **decisao sobe pro mestre, caso desce pro changelog, regra de tema vai pra gaveta (satelite).** O `claude.md` quase nunca e tocado.

---

## Passo a passo (instrucoes para o agente)

### PASSO 0 — Detectar contexto + classificar a sessao

1. **Identificar o contexto ativo** (qual projeto ou area voce esta salvando):
   - Se ficou obvio na conversa ou o usuario informou, usar esse.
   - Se houver duvida, perguntar: `"Em qual contexto salvo?"` e listar as opcoes que existirem no OS da pessoa.
2. **Mapear a estrutura do OS** ate uns dois niveis (arquivos soltos / pastas / subpastas), adaptando ao que existir. Em geral cada pasta de contexto tem seu documento mestre, `aprendizados_do_dia.md`, `changelog.md` e `index.md`. Nao assumir: descobrir o que realmente existe.
3. **Classificar o que a sessao produziu** (isto comanda o PASSO 1):
   - **(A) Entrega concreta**: codigo, automacao, arquivo, deploy, mudanca real.
   - **(B) Decisao**: uma definicao documentada, uma escolha estrategica.
   - **(C) So conversa, pesquisa ou analise**: sem entrega.
   
   Uma sessao pode ser varios tipos ao mesmo tempo (por exemplo, A + B).

---

### PASSO 1 — CONFERIR (adaptativo)

Rodar a checagem de qualidade **so no que se aplica** ao que a sessao produziu. **Nunca** aplicar um checklist de algo que nao aconteceu.

**Se (A) Entrega concreta**, aplicar o checklist do tipo, sempre com evidencia:

- *Codigo / automacao / fluxo:*
  - [ ] Esta funcionando? (testado com dado real, nao imaginado; citar a evidencia)
  - [ ] Existe tratamento de erro ou aviso quando algo falha?
  - [ ] Nome e descricao claros para "voce daqui a 30 dias"?
  - [ ] Foi salvo / publicado onde devia (commit, deploy, arquivo no lugar)?
- *Documento / arquivo:*
  - [ ] Segue a convencao de nomes do OS?
  - [ ] O `index.md` foi atualizado? Tem ponteiro de volta se o conteudo foi extraido de outro lugar?

**Se (B) Decisao:**
  - [ ] Registrada no documento mestre do contexto? (Data + Decisao + Motivo)
  - [ ] Pendencias relacionadas atualizadas (marcadas como feitas ou criadas novas)?
  - [ ] Se envolve outra pessoa, ela foi alinhada?

**SEGURANCA — aplicar SEMPRE que houve (A) ou (B), sem excecao:**
  - [ ] Nenhuma senha, token ou chave de API em texto claro?
  - [ ] Nenhum dado pessoal (documento, e-mail privado, telefone) escrito direto no codigo ou no arquivo?
  - [ ] Credenciais guardadas em local seguro (gerenciador de senhas do sistema, variavel de ambiente)?
  - [ ] Se vai compartilhar o arquivo com alguem, limpou a informacao sensivel antes?

**Se (C) So conversa ou pesquisa**, **pular este passo em silencio.** Nao ha entrega para verificar, e inventar uma verificacao viola o principio 1. Seguir direto para o PASSO 2.

**Formato de apresentacao do conferir:**
```
Conferido: [o que foi entregue, em 1 linha]
- [x] [item verificado] — [evidencia breve]
- [ ] [item nao aplicavel] — pulado porque [motivo]
```

---

### PASSO 2 — SINTETIZAR (3 blocos, neutro)

Sintetizar a sessao lendo o historico atual mais o `aprendizados_do_dia.md` recente. **O agente sintetiza, o usuario valida.** Qualquer bloco pode ficar vazio.

```
Sintese da sessao [CONTEXTO]:

📌 FIZEMOS:
- [entrega / decisao / correcao]
(ou "Sessao de conversa ou analise, sem entregas concretas")

💡 APRENDEMOS:
- [insight / solucao / o que nao fazer]
(ou "Sem aprendizados novos")

🔜 FICA PRA CONTINUAR:
- [pendencia nova ou antiga em aberto]
(ou "Sem pendencias novas")
```

Apresentar e pedir: `"Confere a sintese? Confirma, ajusta, adiciona ou remove."` Aguardar. Se a resposta for "pula" ou "nao tem nada", nao gravar a sintese e ir para o PASSO 3 (o checkpoint roda sempre).

> "FICA PRA CONTINUAR", nao "pra amanha": a skill roda a qualquer hora.

**Nunca preencher um bloco a forca.** Se nao houve aprendizado, o bloco fica "Sem aprendizados novos". Inventar viola o principio 2.

---

### PASSO 3 — CHECKPOINT duravel (o coracao da skill)

**Este passo roda SEMPRE**, mesmo numa sessao que foi so conversa. E a razao de existir da skill: o arquivo que reconstroi o estado se o provedor compactar a janela.

**Onde gravar:**
1. Se a pasta `.remember/` existir no OS da pessoa, gravar em **`.remember/CHECKPOINT.md`**.
2. Caso contrario, criar e usar **`checkpoints/CHECKPOINT.md`**.

Sempre **sobrescrever** esse arquivo com o ultimo estado completo. Ele e o arquivo de leitura unica para retomar: a foto mais recente, nao um historico.

```markdown
# Checkpoint — [CONTEXTO] — AAAA-MM-DD HH:MM

## Estado atual
[1 paragrafo: onde estamos exatamente, agora.]

## Loops abertos
- [pendencia] — [status]

## Decisoes + porque
- [decisao] : [razao] : [trade-off]   (preserva o RACIONAL, nao so o fato)

## Proxima acao
[1 linha acionavel: a coisa numero 1 a fazer.]

## Arquivos em voo
- [arquivo tocado ou a tocar]

## Estado de verificacao
[o que passou ou falhou: testes verdes? build ok? deploy feito?]

## Como retomar
[o prompt ou comando exato para uma sessao nova continuar do zero.]
```

**Regra de ouro do checkpoint:** uma sessao nova que leia SO o `CHECKPOINT.md` tem que conseguir continuar sem perguntar nada. Se nao consegue, o checkpoint esta incompleto: volte e complete.

Em contexto de projeto, espelhar um resumo de 2 a 3 linhas no topo do documento mestre:
`> Ultimo checkpoint AAAA-MM-DD HH:MM: <estado atual> · proxima: <proxima acao>`.

---

### PASSO 3.5 — GATE DE ESCRITA (obrigatorio antes de gravar) ⭐

Nenhum item confirmado no PASSO 2 vai direto para os arquivos. Cada um passa por este gate antes de qualquer edicao. O motivo e simples: **os arquivos incham na ENTRADA, por escrita repetida e prolixa.** Limpar depois custa muito mais caro do que filtrar na hora, e e por isso que existe uma skill inteira (`otimizar-os`) so pra consertar o estrago.

Para cada item, na ordem:

**1. Ler o arquivo-alvo INTEIRO.** Nao so o comeco, nao so o topo. Sem saber o que ja esta escrito ali, toda escrita nova e uma duplicata em potencial.

**2. Buscar antes de escrever (anti-duplicacao).** Tirar 2 ou 3 palavras-chave do item e procurar no `documento_mestre.md`, no `aprendizados_do_dia.md`, no `claude.md` do contexto e nos satelites.
- Tema **ja coberto** → EDITAR a entrada que existe (incorporar o novo, atualizar a data). Nunca criar uma segunda entrada do mesmo assunto.
- O problema **aconteceu de novo** (reincidencia de uma regra ja escrita) → isso nao e aprendizado novo: 1 linha no changelog e, no maximo, 1 frase de reforco na regra existente.

**3. Teste dos 3 meses (filtra o caso pontual).** Perguntar: *"daqui a 3 meses, isso muda como eu trabalho neste contexto?"*
- **Nao** (bug corrigido, incidente resolvido, evento com data, historia de como voce chegou la) → vai pro **changelog**, 1 ou 2 bullets. Nada nos aprendizados.
- **Sim** → extrair SO a regra generalizavel. A narrativa do caso vai pro changelog, nunca dentro da entrada.

**4. Orcamento de escrita (anti-verborragia).**
- Entrada nova: no maximo **6 linhas e ~700 caracteres**. Insight = a regra. Solucao = o procedimento. Nao fazer = 1 frase.
- Proibido dentro da entrada: historico da investigacao, "caso real: ...", justificativa longa da regra.
- No maximo **3 entradas novas por sessao**. O que passar disso e quase sempre caso pontual, e caso pontual vai pro changelog.

**5. Teto duro (entra um, sai um).** Se o arquivo-alvo JA esta estourado (aprendizados acima de 250 linhas ou 15 KB · `claude.md` acima de 300 linhas · documento mestre acima de 500), a escrita nova so entra se sair volume equivalente na MESMA rodada. Condensar ou migrar primeiro, com aprovacao. Sem isso, o arquivo so cresce.

**6. Destino conferido no contrato.** Bater o item contra a tabela "Contrato por arquivo" (no topo desta skill) antes de gravar. Decisao de negocio, estrategia, tatica ou plano vao pro **documento mestre**. O `claude.md` do contexto so recebe regra rigida de operacao, e isso e raro.

**O que o gate produz:** a lista final do que sera gravado, ja com destino definido. Item que nao passou no gate nao some em silencio: ou virou 1 linha no changelog, ou foi incorporado a uma entrada existente. Reportar em 1 linha quantos itens entraram e quantos foram redirecionados.

---

### PASSO 4 — PERSISTIR no OS (com aprovacao)

Gravar so o que a sintese confirmou **e que passou no gate do PASSO 3.5**, nos arquivos do OS:

1. **`aprendizados_do_dia.md`** — entradas novas no topo:
   ```markdown
   ## [Titulo] (DD/MM)
   **Insight:** ...
   **Solucao:** ...
   **Nao fazer:** ...
   ```
   Ordem sugerida: regra de negocio, depois estrategico, depois tecnico.
   **Destino de uma regra PERMANENTE nao e o changelog.** Se o aprendizado virou regra fixa (um "sempre" ou "nunca" estavel), ele vai para o **documento mestre** (secao de regras) ou para um arquivo satelite (`satelites/<topico>.md`), lido quando o tema surge. Changelog e historico morto; regra viva mora onde e consultada.

2. **`changelog.md`** — entrada no topo com data:
   ```markdown
   ### DD/MM/AAAA — [Titulo]
   - [o que foi feito] · [decisao] · (identificador do commit, se houver)
   ```

3. **Documento mestre** — mover itens concluidos para o changelog (**sempre mostrando antes** de mover), adicionar pendencias novas, atualizar a data de "ultima atualizacao".
   **Antes de adicionar pendencia nova, procurar nas que ja existem:** se o tema ja esta la, atualizar a linha existente em vez de criar uma segunda. Pendencia e 1 ou 2 linhas (o que e + o que ela destrava). Especificacao e historico nao moram aqui.

4. **`index.md`** — atualizar se algum arquivo foi criado ou removido (no contexto e na raiz, se aplicavel).
   **Meta: 100% dos `.md` do contexto listados, sem excecao.** Antes de fechar, cruzar a lista de arquivos da pasta com o que esta no index. Satelite que ficou de fora do index e documento invisivel: daqui a um mes ninguem lembra que ele existe e alguem escreve tudo de novo em outro lugar. Faltou entrada? Adicionar na hora, sem perguntar (index e catalogo, nao e conteudo).

Tudo isso **com aprovacao**: mostrar o que vai gravar e esperar o ok.

---

### PASSO 5 — MEMORIA

- O `CHECKPOINT.md` completo ja foi gravado no PASSO 3.
- **Achado reusavel que vale alem desta sessao** (uma licao geral, um padrao que vai servir de novo)? Registrar na memoria de longo prazo do agente, se o OS tiver esse mecanismo, seguindo as regras de memoria do proprio OS. Uma entrada curta e densa, sem duplicar o que ja esta no checkpoint.
- Se o ambiente ja captura observacoes automaticamente, **nao duplicar**.
- **Nao inventar** memoria: so registrar o que de fato aconteceu.

---

### PASSO 6 — SAUDE (leve, condicional)

Dar uma olhada rapida no tamanho dos arquivos do contexto ativo (so o ativo), como um semaforo:

| Arquivo | 🟢 OK | 🟡 Atencao | 🔴 Grande |
|---------|-------|-----------|----------|
| documento mestre | < 300 linhas | 300 a 500 | > 500 |
| `aprendizados_do_dia.md` | < 200 linhas E < 15 KB | 200 a 250 linhas ou 15 KB | > 250 linhas OU > 15 KB |
| `changelog.md` | < 30 KB | 30 a 50 KB | > 50 KB |
| Por entrada (aprendizados) | ate 6 linhas | 6 a 8 linhas | > 8 linhas ou ~700 caracteres |

**Medir linhas E KB, nunca so linhas.** Um arquivo de paragrafos longos passa folgado no check de linhas e estoura no de tamanho: sao 150 linhas que custam o mesmo que 400. Se as duas medidas discordam, vale a pior.

Se algo ficou 🔴, **sugerir** uma limpeza ou reorganizacao. **Nao executar, so sugerir.**

**Trava anti-ruido (REDUTIVEL vs PISO):** antes de sugerir qualquer otimizacao, distinguir de onde vem o tamanho.
- Se o arquivo esta grande por causa de **item redutivel concreto** (registro temporal velho, cemiterio de tarefas ja concluidas, secao densa que da pra extrair, conteudo duplicado): ai sim sugerir a limpeza, apontando o item.
- Se o arquivo esta grande porque e **conteudo perene, necessario e ja curado** (o piso, o minimo que precisa existir): **nao sugerir nada.** Repetir um alarme sem acao possivel e so ruido.

**Caso especifico:** se o `aprendizados_do_dia.md` ficou grande por acumulo de **regra permanente** (muitos "sempre" e "nunca" fixos), e nao por registro temporal, a acao certa NAO e migrar para o changelog. E extrair essas regras para um satelite (`satelites/<topico>.md`, lido so quando o tema surge) e deixar o `aprendizados` como um log curto.

**Sobre a memoria do agente: observar, nunca cobrar.** Se a memoria persistente estiver visivelmente pesada, registrar no maximo 1 linha no relatorio ("memoria do agente esta grande"). **Nao sugerir a skill `otimizar-custo` aqui.** Esta skill roda todo dia, varias vezes por dia; se ela cobrasse limpeza de memoria toda vez, viraria alarme diario e voce pararia de ler. Quem faz esse lembrete, no maximo 1x por mes, e a `otimizar-os`.

---

### PASSO 7 — Relatorio (neutro, sem saudacao)

```
Checkpoint salvo ✓

Contexto: [caminho]
Checkpoint: .remember/CHECKPOINT.md (ou checkpoints/CHECKPOINT.md)
Conferido: [N itens / "n/a — sessao de conversa"]
Gate de escrita: [N itens entraram · N redirecionados pro changelog · N incorporados a entrada existente]
Aprendizados: [N entradas]
Migrado pro changelog: [N itens]
Index: [completo / N entradas adicionadas]
Saude: [ok / X arquivos 🔴]

Como retomar: [a linha "Como retomar" do checkpoint]
```

**Nunca** fechar com "boa noite", "bom descanso", "ate amanha" ou qualquer juizo de horario. Terminar sempre com a linha **"Como retomar"**.

---

## Regras de seguranca

- **Nunca apagar conteudo:** so mover para o changelog com referencia, e sempre mostrando antes.
- **Nunca migrar sem aprovacao** do usuario.
- **Nunca inventar** aprendizado, pendencia ou verificacao. Bloco vazio fica vazio.
- **Seguranca em toda entrega** (A ou B), sem excecao: nenhuma senha, token ou dado pessoal exposto. Se vazou algo, blindar a arquitetura (guardar o segredo no lugar certo) antes de qualquer outra coisa.
- **Nunca misturar contextos:** `salvar` toca so o contexto ativo.
- **Nunca dar boa-noite nem julgar o horario:** a skill roda a qualquer hora.
- **Nunca escrever no `soul.md` nem promover regra operacional para ele.** O `soul.md` guarda so o carater, o tom e o papel do agente, e deve ficar leve. Regra operacional (uma taxa, um fluxo, um "sempre faca X") vai para o documento mestre ou para um satelite. Se algo parecer de `soul.md`, perguntar antes: nunca escrever por conta propria.
- **Nunca escrever sem passar pelo gate (PASSO 3.5):** ler o arquivo inteiro, buscar duplicata e conferir o destino vem ANTES de qualquer edicao. Gravar direto e o que transforma um OS bom em um OS gordo.
- **Nunca escrever "pra constar":** arquivo sem material novo fica intocado.
- **O PASSO 3 (checkpoint) roda sempre:** e a razao de existir da skill.
- **Nunca rodar sozinha:** o gatilho e 100% manual. O agente pode sugerir quando notar o contexto pesado, mas nunca executa por conta propria.

---

## Compatibilidade (skills antigas)

As skills antigas "conferir-entrega" e "fim-do-dia" (ou "revisao diaria") foram **fundidas nesta**. Elas viram redirecionamentos: mantem o frontmatter e os gatilhos antigos, mas o corpo passa a apontar para esta skill.

Os gatilhos antigos continuam funcionando normalmente: falar **"fim do dia"**, **"conferir entrega"**, **"terminei"**, **"pronto"**, **"feito"** ou **"entregue"** cai aqui, na `salvar`, e executa este passo a passo do inicio.
