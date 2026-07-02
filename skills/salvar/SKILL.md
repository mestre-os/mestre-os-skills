---
name: Salvar
description: |
  Checkpoint de soberania de contexto. Roda a QUALQUER hora, quantas vezes
  precisar, quando a janela de contexto aperta (por volta do amarelo / 80%)
  ou quando o trabalho merece ser preservado. Sem saudacao, sem "boa noite",
  sem juizo de horario. Confere o que foi entregue (com evidencia), sintetiza,
  e grava um checkpoint duravel que reconstroi o estado mesmo que o provedor
  compacte a janela sozinho.
  Gatilhos: "salvar", "salva isso", "salva o contexto", "checkpoint",
  "da um checkpoint", e os ANTIGOS (aliases que continuam funcionando):
  "fim do dia", "fechar o dia", "conferir entrega", "verificar entrega",
  "revisao diaria", "terminei", "pronto", "feito", "entregue", "finalizado",
  "ta pronto?".
version: 1.0
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

### PASSO 4 — PERSISTIR no OS (com aprovacao)

Gravar so o que a sintese confirmou, nos arquivos do OS:

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

4. **`index.md`** — atualizar se algum arquivo foi criado ou removido (no contexto e na raiz, se aplicavel).

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
| `aprendizados_do_dia.md` | < 200 linhas | 200 a 250 | > 250 |
| `changelog.md` | < 30 KB | 30 a 50 KB | > 50 KB |

Se algo ficou 🔴, **sugerir** uma limpeza ou reorganizacao. **Nao executar, so sugerir.**

**Trava anti-ruido (REDUTIVEL vs PISO):** antes de sugerir qualquer otimizacao, distinguir de onde vem o tamanho.
- Se o arquivo esta grande por causa de **item redutivel concreto** (registro temporal velho, cemiterio de tarefas ja concluidas, secao densa que da pra extrair, conteudo duplicado): ai sim sugerir a limpeza, apontando o item.
- Se o arquivo esta grande porque e **conteudo perene, necessario e ja curado** (o piso, o minimo que precisa existir): **nao sugerir nada.** Repetir um alarme sem acao possivel e so ruido.

**Caso especifico:** se o `aprendizados_do_dia.md` ficou grande por acumulo de **regra permanente** (muitos "sempre" e "nunca" fixos), e nao por registro temporal, a acao certa NAO e migrar para o changelog. E extrair essas regras para um satelite (`satelites/<topico>.md`, lido so quando o tema surge) e deixar o `aprendizados` como um log curto.

---

### PASSO 7 — Relatorio (neutro, sem saudacao)

```
Checkpoint salvo ✓

Contexto: [caminho]
Checkpoint: .remember/CHECKPOINT.md (ou checkpoints/CHECKPOINT.md)
Conferido: [N itens / "n/a — sessao de conversa"]
Aprendizados: [N entradas]
Migrado pro changelog: [N itens]
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
- **O PASSO 3 (checkpoint) roda sempre:** e a razao de existir da skill.
- **Nunca rodar sozinha:** o gatilho e 100% manual. O agente pode sugerir quando notar o contexto pesado, mas nunca executa por conta propria.

---

## Compatibilidade (skills antigas)

As skills antigas "conferir-entrega" e "fim-do-dia" (ou "revisao diaria") foram **fundidas nesta**. Elas viram redirecionamentos: mantem o frontmatter e os gatilhos antigos, mas o corpo passa a apontar para esta skill.

Os gatilhos antigos continuam funcionando normalmente: falar **"fim do dia"**, **"conferir entrega"**, **"terminei"**, **"pronto"**, **"feito"** ou **"entregue"** cai aqui, na `salvar`, e executa este passo a passo do inicio.
