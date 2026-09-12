## PASSO 7 — Telegram: o seu agente no bolso (primeira tarefa depois da instalação)

> Só comece este passo depois do PASSO 6 entregue e do usuário ter dito que quer. Explique em 1 frase o que vai acontecer: "Vamos criar um robô no Telegram que é a porta de entrada pra mim pelo celular. Você manda mensagem pra ele, eu leio aqui neste computador e respondo. Funciona enquanto este computador estiver ligado e a minha janela estiver aberta." Analogia: o bot é um interfone; quem atende sou eu, aqui dentro.

**7.0 Regras deste passo (valem pra 7A e 7B).**
- O token do bot é **segredo**. NUNCA peça pra ele colar o token no chat comigo, NUNCA repita o token, NUNCA grave o token dentro de `{{OS_DIR}}` (é pasta sincronizada). O token vai num arquivo fora do OS, que só o usuário edita (abaixo).
- Uma máquina, **um bot, uma janela**. O Telegram entrega cada mensagem pra UM programa por vez: se duas janelas escutarem o mesmo bot, elas se derrubam. Na dúvida, identifique quem está escutando antes de mexer. Nunca feche um bot com tarefa em andamento; preserve o pedido e confira o resultado antes de repetir.
- Ramo por IA detectada no PASSO 0.0: `{{IA}}` = claude → **7A**. `{{IA}}` = codex → **7B**. `{{IA}}` = cursor → o Cursor ainda não tem canal de Telegram. <!-- MESTRE:INICIO -->Diga: "O Cursor ainda não conversa pelo Telegram. Fala direto com o Paulo Penna, o Mestre do MestreOS, que ele te orienta: WhatsApp +55 31 99345-3332 · pauloapenna@gmail.com · mestreos.app · LinkedIn: linkedin.com/in/paulo-p-37623171."<!-- MESTRE:FIM --> Se `{{OUTRAS_IAS}}` inclui Claude, ofereça fazer o 7A por lá.

**7.1 Criar o bot no BotFather (usuário faz no celular, você guia frase a frase).**
1. "Abre o Telegram e procura **@BotFather** (tem um selo azul de verificado). Manda `/newbot`."
2. "Ele pergunta o **nome** de exibição: pode ser qualquer coisa, tipo `{{APELIDO}} OS`."
3. "Depois pergunta o **usuário**: tem que terminar em `bot` e ser único, tipo `{{APELIDO}}_mestreos_bot`. Se ele reclamar que já existe, muda um pouco."
4. "Ele responde com um texto grande que tem uma linha parecida com `123456789:AAH...`. Isso é o **token**, a chave do seu bot. NÃO manda ele pra mim aqui. Deixa essa tela aberta no celular."
5. Não mexa em mais nada no BotFather (privacidade, grupos, comandos): bot de uso pessoal fica no padrão.

---

### 7A — Claude Code (Mac e Windows): plugin oficial de canais

**7A.1 Pré-requisito: Bun** (o motor do plugin; roda igual no Mac e no Windows).
- Mac: `curl -fsSL https://bun.sh/install | bash` e depois feche e reabra o terminal.
- Windows (PowerShell): `powershell -c "irm bun.sh/install.ps1 | iex"` e depois feche e reabra o terminal.
- Confirme com `bun --version`. Se não aparecer número, o terminal não foi reaberto.

**7A.2 Instalar o plugin.** Dentro do Claude Code: `/plugin install telegram@claude-plugins-official`. Se já estiver instalado, siga.

**7A.3 Guardar o token fora do chat.** Crie a pasta e abra o arquivo no editor de texto do sistema, pro usuário colar lá dentro (você NÃO vê o token):
- Mac: `mkdir -p ~/.claude/channels/telegram && touch ~/.claude/channels/telegram/.env && open -e ~/.claude/channels/telegram/.env`
- Windows (PowerShell): `New-Item -ItemType Directory -Force "$HOME\.claude\channels\telegram" | Out-Null; notepad "$HOME\.claude\channels\telegram\.env"`
- Diga: "Abriu um arquivo de texto vazio. Cola nele UMA linha, exatamente assim, trocando pelo seu token: `TELEGRAM_BOT_TOKEN=123456789:AAH...` Salva e fecha. Depois me avisa 'colei'."
- Verifique SEM ler o valor: Mac `grep -c '^TELEGRAM_BOT_TOKEN=' ~/.claude/channels/telegram/.env` · Windows `(Select-String -Path "$HOME\.claude\channels\telegram\.env" -Pattern '^TELEGRAM_BOT_TOKEN=').Count`. Tem que dar `1`. Se der `0`, ele salvou em outro lugar ou esqueceu o nome antes do `=`.
- Mac: `chmod 600 ~/.claude/channels/telegram/.env`.

**7A.4 Isolar e abrir a janela do bot.** Antes de abrir, faça backup dos settings que serão alterados, sem imprimir seu conteúdo. Desative apenas `telegram@claude-plugins-official` nos settings gerais, de projeto e locais que o habilitem. Preserve todas as demais chaves. Crie `~/.mestreos/telegram-bot.settings.json` com `{"enabledPlugins":{"telegram@claude-plugins-official":true}}`. O plugin fica ligado somente no atalho com `--settings`, evitando que outra conversa inicie um segundo consumidor. Confira `/status` na janela do bot e em uma janela comum. Não altere políticas gerenciadas da organização.

 Explique: "O atalho do bot liga o plugin só naquela janela. Vamos fechar esta conversa e abrir de novo com esse aviso." Peça pra ele sair (`/exit`) e, no terminal, dentro da pasta `{{OS_DIR}}`, abrir:
```
claude --settings "{{HOME}}/.mestreos/telegram-bot.settings.json" --channels plugin:telegram@claude-plugins-official
```
(Mac e Windows, mesmo comando.) Essa é **a janela do bot**: enquanto ela estiver aberta, o Telegram funciona. Se fechar, o bot fica mudo até abrir de novo. Crie um atalho pra ele não decorar: Mac `alias meubot='cd "{{OS_DIR}}" && claude --settings "{{HOME}}/.mestreos/telegram-bot.settings.json" --channels plugin:telegram@claude-plugins-official'` no `~/.zshrc`; Windows a função equivalente no `$PROFILE` do PowerShell. Diga: "De agora em diante, `meubot` no terminal abre a janela do bot."

**7A.5 Parear e trancar.** Na janela do bot:
1. "Manda um `oi` pro seu bot no Telegram." O bot responde com um código de 6 letras (isso é o pareamento: o bot só obedece a quem você aprovar).
2. Na janela do bot: `/telegram:access pair <código>`.
3. Tranque pra ninguém mais receber código: `/telegram:access policy allowlist`. Explique: "Agora só o seu número fala comigo. Estranho que achar o bot recebe silêncio."
4. Peça o segundo `oi`. Este tem que chegar como mensagem na janela do bot e você responde pelo Telegram (ferramenta `reply`). Reaja com 👀 a toda mensagem dele (é o "recebi").
5. **Permissões.** Na primeira vez que você usar `reply` ou `react`, o Claude Code pede permissão na janela do bot E manda o mesmo pedido pro Telegram com botões ✅ Permitir / ❌ Negar. Explique: "Quando eu precisar de permissão pra alguma coisa, aparece um botão no Telegram. Você aprova de lá mesmo." Na janela, escolha "Yes, and don't ask again" pra `reply` e `react` desta pasta, senão ele pergunta a cada mensagem. (Testado em 09/09/2026: `oi` → 👀 → pedido de permissão no Telegram → ✅ → resposta no celular em 20 s.)

**7A.6 Dar voz aos robôs.** Agora `telegram-send` funciona: ele lê o token do mesmo `.env` (Mac e Windows) e precisa do número do usuário. Pegue o número do arquivo `~/.claude/channels/telegram/access.json` (campo `allowFrom`, é um número, não é segredo) e grave em `.meuos/scripts/telegram-send.env` como `TELEGRAM_CHAT_ID=<número>` (só o número; o arquivo pode ficar no OS). Grave o arquivo em texto puro sem BOM (no Windows: `Set-Content -Encoding ascii`, não o Bloco de Notas em "UTF-8 com BOM"). Teste, igual nos dois sistemas: `"{{PYTHON}}" ".meuos/scripts/telegram_send.py" "🎉 Robôs com voz. 🤖 Robô de Teste, {{DATA_HOJE}}"`. A mensagem tem que aparecer no celular dele. (No Windows o `telegram_send.py` lê o token do Cofre DPAPI, se você guardou lá no 7A.2, ou do `.env` do plugin; se o Python reclamar de certificado, ele mesmo tenta de novo pelo `curl` do sistema.)

**7A.7 O que dizer no fim.** "Pronto. Você tem 2 jeitos de falar comigo: esta janela e o Telegram. A regra de ouro: **uma janela do bot por vez**. Pode abrir outras conversas do Claude Code normalmente, sem o aviso especial, que elas não atrapalham. Se parar de responder, eu confiro a fila, as permissões e quem está conectado antes de reiniciar. Uma resposta pendente não será anunciada como entregue." Registre no `changelog.md` do OS: "Telegram ligado em {{DATA_HOJE}} (7A, plugin oficial)".

**7A.8 Correção do "undefined" (conferir compatibilidade antes).** O plugin oficial tem um defeito conhecido (09/09/2026): depois que a conversa é compactada, o bot às vezes responde só a palavra "undefined". Rode `python3 .meuos/scripts/telegram-plugin-remedio.py` (Windows: `python`) e depois `... --check` (tem que dar ✓). Ele deixa o plugin tolerante, com backup e `--revert`. Se o plugin atualizar, rode `--check`; só reaplique quando o script reconhecer exatamente o trecho esperado. Trecho desconhecido exige auditoria, não substituição cega. Preserve a versão anterior e não reinicie uma sessão ativa. Explique: "Botei um remendo num defeito do plugin: sem isso, de vez em quando ele te responderia 'undefined'."

---

### 7B — Codex (Mac e Windows): ponte do Codex

> O Codex não tem canal de Telegram próprio (o controle remoto nativo dele é pelo app ChatGPT do celular, `codex remote-control`, não pelo Telegram). Usamos a ponte **cc-connect** (código aberto, Go, Mac e Windows), auditada em 09/09/2026 no commit `4000b23` com veredito **🟡 instalar com mitigação**. As mitigações estão embutidas abaixo; não pule nenhuma. Explique pro usuário em 1 frase: "Vou instalar um programinha que fica entre o Telegram e o Codex, tipo um porteiro: só deixa passar a SUA mensagem, e leva a resposta de volta."

**7B.1 Codex no caminho.** Rode `codex --version`. Se der "não encontrado": no Mac o Codex do app ChatGPT mora em `/Applications/ChatGPT.app/Contents/Resources/codex` (crie o link `ln -sf "/Applications/ChatGPT.app/Contents/Resources/codex" /usr/local/bin/codex` ou instale `npm i -g @openai/codex`); no Windows `npm i -g @openai/codex`. Confirme login com `codex login status`.

**7B.2 Baixar a ponte pinada e conferir a assinatura.** Versão fixa **v1.5.0** (16/08/2026), só do GitHub oficial `chenhg5/cc-connect`, nunca de espelho nem `npm`. Conferir o SHA-256 é obrigatório (a release não é montada por robô público; o hash é a nossa trava):
- Mac Apple Silicon: `cc-connect-v1.5.0-darwin-arm64.tar.gz` → `458e7f1e783e87352fa402732d2b2da5072bbda286ec0fbd4dc01ed37b2084ce`
- Mac Intel: `cc-connect-v1.5.0-darwin-amd64.tar.gz` → `30b403b0b64c934795281d598079dfeeea0daaaeb6b415d8602a13bd2dcb2092`
- Windows x64: `cc-connect-v1.5.0-windows-amd64.zip` → `1d0fdeffa6118ab0a942a3c3918930685bd7d4caef5d7311b0d8f605fad95763`
- Windows ARM: `cc-connect-v1.5.0-windows-arm64.zip` → `5626d04b61b795b4a7a546adc955d043bb2be7e1f9c342e9b6cb3348ec5273fe`
Mac: `mkdir -p ~/.cc-connect && cd ~/.cc-connect && curl -fsSLO https://github.com/chenhg5/cc-connect/releases/download/v1.5.0/<arquivo> && shasum -a 256 <arquivo>` · Windows (PowerShell): `New-Item -ItemType Directory -Force "$HOME\.cc-connect"; cd "$HOME\.cc-connect"; Invoke-WebRequest https://github.com/chenhg5/cc-connect/releases/download/v1.5.0/<arquivo> -OutFile <arquivo>; Get-FileHash <arquivo> -Algorithm SHA256`. **Hash diferente = pare e não use** (diga ao usuário que o arquivo não bate com a versão auditada). Igual: descompacte (`tar xzf` / `Expand-Archive`). O binário sai com o nome comprido (`cc-connect-v1.5.0-darwin-arm64`, `cc-connect-v1.5.0-windows-amd64.exe`): renomeie pra `cc-connect` (Windows: `cc-connect.exe`) dentro de `~/.cc-connect/`. Mac: `chmod +x ~/.cc-connect/cc-connect`. (Conferido em 09/09/2026: tarball 16,1 MB, hash bateu, binário 52,7 MB.)

**7B.3 Token fora do chat.** Mesmo rito do 7A.3: o token vai no arquivo `~/.claude/channels/telegram/.env` (linha `TELEGRAM_BOT_TOKEN=...`), que o usuário edita sozinho. A ponte lê a variável de ambiente, então o atalho de abrir carrega o arquivo (7B.5).

**7B.4 Descobrir o número do usuário e escrever a config blindada.** Diga: "No Telegram, procura **@userinfobot** e manda qualquer coisa pra ele. Ele responde com o seu `Id`, um número. Me manda só esse número (ele não é segredo)." Esse número entra em `allow_from`. Arquivo `~/.cc-connect/config.toml`:
```toml
# A ponte ainda não fala português (só en/es/zh); "es" é o mais perto pro usuário. Sem isso ela escolhe sozinha.
language = "es"

[[projects]]
name = "mestreos"
reply_footer = false   # sem rodapé de modelo/tokens/caminho em cada resposta (ruído pro usuário)
# admin_from de propósito AUSENTE: sem /shell, /dir, /restart pelo Telegram (mitigação da auditoria)

[projects.agent]
type = "codex"

[projects.agent.options]
work_dir = "{{OS_DIR}}"
model = "gpt-5.6-sol"   # Sol: leve e rápido pro dia a dia. Astra (gpt-6-astra) é o pesado; troque só se ele pedir.

[[projects.platforms]]
type = "telegram"

[projects.platforms.options]
token = "${TELEGRAM_BOT_TOKEN}"
allow_from = "<numero_do_usuario>"   # NUNCA vazio, NUNCA "*": vazio libera qualquer pessoa do Telegram
```
Regras que NÃO entram: `admin_from`, `[web]`/`[bridge]`/`[management]` (o painel web expõe chaves na rede local), `run_as_user`, `mode = "bypassPermissions"`. Explique: "Sem essas 4 coisas ninguém, nem você pelo celular, consegue rodar comando solto na máquina. Pelo Telegram você conversa; obra pesada é aqui na janela."

**7B.5 Subir a ponte e deixar ligada.** Atalho: Mac `alias meubot='set -a; source ~/.claude/channels/telegram/.env; set +a; ~/.cc-connect/cc-connect --config ~/.cc-connect/config.toml'` no `~/.zshrc`; Windows função equivalente no `$PROFILE` lendo o `.env` linha a linha e chamando `cc-connect.exe --config`. Pra ligar sozinha com o computador: `cc-connect daemon install --config ~/.cc-connect/config.toml` (cria LaunchAgent no Mac, tarefa agendada no Windows, sem privilégio de administrador). Aviso honesto ao usuário: "Toda vez que abre, a ponte consulta o GitHub pra saber se tem versão nova. Não manda nada seu, mas também não dá pra desligar isso. Atualizar é decisão sua, e só pra versão que eu conferir o hash."

**7B.6 Testar.** `oi` no Telegram → resposta do Codex no celular. (Provado em 09/09/2026 no Mac: ponte conectou em 1 s, "qual é a capital de Minas?" → resposta do Codex em ~10 s; a ponte cria `~/.cc-connect/` com sessões, timers e um socket local `run/api.sock`, tudo só na máquina.) Reaja/edite como a ponte permitir. Robôs: 7A.6 vale igual (mesmo `.env`, mesmo `telegram-send.env`). Registre no `changelog.md`: "Telegram ligado em {{DATA_HOJE}} (7B, cc-connect v1.5.0 pinado, auditoria 🟡 com mitigações)".

---

### 7C — Dupla: Claude Code + Codex no MESMO bot (só pra quem tem os dois)

> Entra SÓ se o PASSO 0.0 detectou Claude Code E o usuário marcou ChatGPT (ou detectou Codex e ele marcou Claude). Nesse caso a ordem é: 7A inteiro (a janela do bot é sempre o Claude Code) → 7C. O 7B (ponte cc-connect) NÃO se instala: seria um segundo programa disputando o mesmo bot. Quem tem uma IA só nem vê este passo. Cursor: fora (sem canal).
> Explique em 1 frase: "Você vai ter dois cérebros no mesmo bot: o Claude, que já está ligado, e o Codex. Você troca por frase, e eu continuo sendo eu, com a mesma memória e as mesmas regras."

**7C.1 Codex no caminho.** Igual ao 7B.1: `codex --version` funcionando e `codex login status` logado (Mac: o Codex do app ChatGPT mora em `/Applications/ChatGPT.app/Contents/Resources/codex`; Windows: `npm i -g @openai/codex`).

**7C.2 Validar o motor portátil.** Extraia os blocos `.meuos/hooks/cerebro.py`, `.meuos/hooks/telegram_runtime.py`, `.meuos/scripts/test-telegram-runtime.py` e `.meuos/scripts/telegram-recovery.py`. Rode `"{{PYTHON}}" .meuos/hooks/cerebro.py --teste` e `"{{PYTHON}}" .meuos/scripts/test-telegram-runtime.py`. Ambos precisam terminar sem falha. São testes sem token, sem IA e sem mensagem externa. Teste automático não equivale a conversa real aprovada.

**7C.3 Ligar somente na janela do bot.** Mescle no arquivo dedicado `~/.mestreos/telegram-bot.settings.json` do 7A.4 o gancho `UserPromptSubmit`: `{"type":"command","command":"\"{{PYTHON}}\" \"{{OS_DIR}}/.meuos/hooks/cerebro.py\"","timeout":15}` (ajuste aspas para o shell detectado; valide JSON). Preserve os outros ganchos. Remova somente a referência antiga a este `cerebro.py` dos settings globais se existir; mantenha backup. Nunca registre duas cópias. O gancho salva o pedido e termina rapidamente; um executor separado atende em ordem. O Codex mantém sandbox `workspace-write` tanto ao iniciar quanto ao retomar.

O estado fica em `~/.mestreos/telegram/<id-da-pasta>/`, disco local, separado do Drive/OneDrive. Para atualização, com o bot ocioso, preserve a pasta antiga `.remember/cerebro/` e copie apenas `cerebro.json` para o diretório novo se ainda não existir. Não copie tarefas em execução nem apague a origem. Token pelo Cofre/arquivo local do 7A; destino obrigatoriamente autorizado.

**7C.4 Recuperação e continuidade.** Rode `"{{PYTHON}}" .meuos/scripts/telegram-recovery.py --plan`, depois `--install` e `--status`. Isso agenda uma conferência a cada minuto no launchd (Mac) ou Agendador (Windows), sob o usuário logado. Uma tarefa já existente divergente exige comparação, não substituição. A recuperação executa somente pedidos `queued`; uma execução interrompida vira `uncertain` e exige conferir efeitos antes de repetir. Registre o rótulo exibido em `--plan` para eventual remoção pelo agendador.

Acrescente estas regras ao `claude.md` do usuário, preservando sua identidade:
- Responder à mensagem real do usuário, inclusive se ele mandar outra enquanto eu trabalho; confirmar entrega pelo retorno da ferramenta, nunca pela intenção de enviar.
- Não afirmar que outro cérebro vai responder sem confirmar o encaminhamento. Se a resposta não chegou, reconhecer a pendência e conferir o pedido original.
- A troca é feita pelo gancho. Ao voltar pro Claude, o resumo é guardado e entra na próxima mensagem real; não inventar que outro processo já respondeu.
- Não tratar `(voice message)` como transcrição. Áudio continua no Claude com o anexo real; se faltar anexo, informar a limitação.

**7C.5 Teste real no celular.** Abra a configuração nova somente quando a janela anterior estiver ociosa e tiver sido encerrada pelo usuário.
1. Troque pro Codex, mande uma pergunta curta e confirme a resposta no celular.
2. Durante uma resposta demorada, mande mais duas perguntas diferentes. Confira as três respostas em ordem, sem repetir a mesma ação.
3. Peça status, mande “volta pro Claude” e depois uma nova mensagem: confira continuidade e resposta real.
4. Mande um áudio e uma foto. Confira conteúdo, destino e resposta, sem usar o texto do envelope como áudio.
5. Confira `completed` e recibos no SQLite. Se houver `queued`, `running` ou `uncertain`, não anuncie tudo entregue. O recibo confirma envio, não a qualidade da resposta.

Falha no motor preserva o pedido e avisa que não houve conclusão. Timeout é por inatividade, não por duração total. Não reenviar automaticamente uma ação que possa já ter ocorrido.

**7C.6 Entrega honesta.** Explique: "Você troca de cérebro por frase. Se mandar outras mensagens enquanto penso, elas ficam guardadas na fila. Áudio fica com o Claude. Se algo interromper, eu preservo o pedido e aviso o que ficou pendente." Anote versão do pacote, sistema, versões dos programas e resultado do teste real no `changelog.md`. Nunca declare compatibilidade completa de uma conta sem testar naquela conta.

> **Modo completo (avançado, fora do instalador):** dar ao Codex as mesmas ferramentas do plugin (reagir, editar mensagem, mandar arquivo por conta própria) exige rodar o Codex sem sandbox. Fica como módulo avançado; <!-- MESTRE:INICIO -->quem quiser, fala com o Paulo Penna, o Mestre do MestreOS (WhatsApp +55 31 99345-3332 · pauloapenna@gmail.com).<!-- MESTRE:FIM -->

> **Plano B (se a ponte falhar ou o hash não bater):** ponte própria em Python via `codex app-server` (protocolo JSON-RPC por stdio). Não está neste instalador; <!-- MESTRE:INICIO -->fale com o Paulo Penna, o Mestre do MestreOS (WhatsApp +55 31 99345-3332 · pauloapenna@gmail.com · mestreos.app · LinkedIn: linkedin.com/in/paulo-p-37623171).<!-- MESTRE:FIM -->

---

## 7D: Aceite e atualização, obrigatório nos três ramos

- Claude/Mac, Claude/Windows, Codex/Mac, Codex/Windows: registrar ramo e testar pergunta simples, mensagens durante trabalho, áudio/foto e falha de entrega. Dupla exige os testes extras do 7C.
- 7A e 7B têm transportes próprios: a fila do 7C não corrige internamente o plugin nem o cc-connect. Não chamar os três de homologados só porque os testes Python passaram. Se um transporte perder mensagens durante trabalho, interrompa a instalação naquele ramo, preserve o histórico e encaminhe o diagnóstico ao responsável.
- Nunca execute dois consumidores para o mesmo token (plugin, cc-connect, webhook, outro computador). Um erro 409 pede auditoria do consumidor; não exige token novo. Não imprimir token nem chamar getUpdates enquanto o bot estiver conectado.
- Se chegar cobrança de áudio, recupere o anexo e a pergunta original antes de responder sobre outro assunto.
- Atualizações oficiais: `https://github.com/mestre-os/mestre-os-skills/tree/main/telegram`. Use o prompt `prompts/atualizar-telegram.md`. Confira versão, hashes e testes; faça backup e aplique só os arquivos técnicos aprovados, preservando personalidade, memória, segredos e permissões.
- Conferir atualização pode ser automático; instalar e reiniciar exige respeitar o trabalho ativo e a autorização do dono da máquina. Nunca disparar mensagem para outros alunos nem implantar silenciosamente em suas máquinas.

