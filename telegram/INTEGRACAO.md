## PASSO 7 — Telegram: o seu agente no bolso (primeira tarefa depois da instalação)

> Só comece este passo depois do PASSO 6 entregue e do usuário ter dito que quer. Explique em 1 frase o que vai acontecer: "Vamos criar um robô no Telegram que é a porta de entrada pra mim pelo celular. Você manda mensagem pra ele, eu leio aqui neste computador e respondo. Funciona enquanto este computador estiver ligado e a minha janela estiver aberta." Analogia: o bot é um interfone; quem atende sou eu, aqui dentro.

**7.0 Regras deste passo (valem pra 7A, 7B e 7D).**
- O token do bot é **segredo**. NUNCA peça pra ele colar o token no chat comigo, NUNCA repita o token, NUNCA grave o token dentro de `{{OS_DIR}}` (é pasta sincronizada). O token vai num arquivo fora do OS, que só o usuário edita (abaixo).
- **Bot próprio de outro programa** (uma ponte feita sob medida, um fluxo do n8n, outro computador já atende o bot): vá pro **7F**, só avisos. Nenhum dos outros ramos se instala nesse caso.
- Uma máquina, **um bot, uma janela**. O Telegram entrega cada mensagem pra UM programa por vez: se duas janelas escutarem o mesmo bot, elas se derrubam. Na dúvida, identifique quem está escutando antes de mexer. Nunca feche um bot com tarefa em andamento; preserve o pedido e confira o resultado antes de repetir.
- Ramo por IA detectada no PASSO 0.0: `{{IA}}` = claude → **7A**. `{{IA}}` = codex → **7B**. Tem os DOIS (`{{OUTRAS_IAS}}` inclui a outra, ou instalou a outra depois) → **7D** (7A e 7B não se instalam nesse caso; a janela do 7D atende os dois). `{{IA}}` = cursor → o Cursor ainda não tem canal de Telegram. <!-- MESTRE:INICIO -->Diga: "O Cursor ainda não conversa pelo Telegram. Fala direto com o Paulo Penna, o Mestre do MestreOS, que ele te orienta: WhatsApp +55 31 99345-3332 · pauloapenna@gmail.com · mestreos.app · LinkedIn: linkedin.com/in/paulo-p-37623171."<!-- MESTRE:FIM --> Se `{{OUTRAS_IAS}}` inclui Claude, ofereça fazer o 7A por lá.

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

**7A.4 Isolar e abrir a janela do bot.** Antes de abrir, faça backup dos settings que serão alterados, sem imprimir seu conteúdo. Desative `telegram@claude-plugins-official` nos settings gerais, de projeto e locais que o habilitem. Preserve todas as demais chaves. Não altere políticas gerenciadas da organização.
- **Cópia duplicada do plugin (Mac e Windows).** A sincronização da conta do claude.ai às vezes instala uma segunda cópia do mesmo plugin (ex.: `telegram@synced`). Com as duas ligadas, a janela do bot sobe duas cópias e o canal pode simplesmente não abrir, sem erro nenhum. Rode `claude plugin list --json` e, pra toda entrada cujo `id` comece com `telegram@` e não seja `telegram@claude-plugins-official`, rode `claude plugin disable <id>` (com `--scope` igual ao `scope` da entrada). Explique: "Tinha uma segunda cópia do plugin do Telegram, que veio da sua conta. Desliguei: duas cópias brigam e o bot fica mudo."
- **Settings da janela do bot.** Crie (ou, se já existir, atualize sem apagar outras chaves) `~/.mestreos/telegram-bot.settings.json` com o plugin ligado e os 5 ganchos da janela: mantêm o "digitando" aceso até o fim de cada tarefa (também quando a tarefa termina em erro, como limite do plano), gravam a assinatura com modelo e esforço, lembram as regras do Telegram a cada mensagem que chega de lá e fazem a troca de modelo do 7A.9 funcionar. O formato `command` + `args` roda o Python direto, sem shell: funciona igual no Mac e no Windows, com ou sem Git Bash. No Windows, use barras normais (`/`) nos caminhos dentro do JSON. Se já houver gancho com `telegram-bot-turno.py`, troque pelos de baixo, sem duplicar:
```
{"enabledPlugins": {"telegram@claude-plugins-official": true},
 "hooks": {
  "SessionStart": [{"hooks": [{"type": "command", "command": "{{PYTHON}}", "args": ["{{OS_DIR}}/.meuos/scripts/telegram-bot-turno.py", "sessao"]}]}],
  "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "{{PYTHON}}", "args": ["{{OS_DIR}}/.meuos/scripts/telegram-bot-turno.py", "inicio"]}]}],
  "PostToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": "{{PYTHON}}", "args": ["{{OS_DIR}}/.meuos/scripts/telegram-bot-turno.py", "ferramenta"]}]}],
  "Stop": [{"hooks": [{"type": "command", "command": "{{PYTHON}}", "args": ["{{OS_DIR}}/.meuos/scripts/telegram-bot-turno.py", "fim"]}]}],
  "StopFailure": [{"hooks": [{"type": "command", "command": "{{PYTHON}}", "args": ["{{OS_DIR}}/.meuos/scripts/telegram-bot-turno.py", "falha"]}]}]}}
```
  O plugin fica ligado somente na janela com `--settings`, evitando que outra conversa inicie um segundo consumidor; os ganchos também só rodam nela. Grave `.meuos/scripts/telegram-bot-turno.py`, `.meuos/scripts/telegram-bot-troca.py` e `.meuos/scripts/telegram-janela-do-bot.md` exatamente como vêm nos blocos 📦. O último é o manual de conduta do Telegram: entra só na janela do bot (`--append-system-prompt-file`), então não ocupa espaço no `claude.md`. Antes de abrir a janela, aplique os remédios do plugin (7A.8): `"{{PYTHON}}" .meuos/scripts/telegram-plugin-remedio.py` e depois `... --check` (✓ nos 6). Assim a primeira janela do bot já abre com eles.
- **Atalho `meubot`** (crie agora, daqui mesmo). É o único jeito de abrir a janela do bot: espera a pasta do OS aparecer (até 2 minutos, porque logo depois de ligar o computador o Google Drive ou o OneDrive ainda pode estar montando a pasta) e é um laço que reabre a janela sozinho quando a troca de modelo do 7A.9 pede, na mesma conversa. As opções de cada abertura vêm do `telegram-bot-troca.py atalho`, que só devolve palavras da lista (modelo, esforço, conversa, aviso): o atalho nunca repassa o conteúdo cru de um arquivo ao `claude`. Ele se recusa a abrir de dentro de uma conversa do Claude Code: a janela do bot herdaria as variáveis da conversa de fora (aconteceu com uma aluna em 20/10/2026), então abre sempre num terminal novo.
  - **Mac:** no `~/.zshrc`, apague a linha antiga `alias meubot=...` ou a função `meubot()` antiga, se existir, e acrescente:
```
unalias meubot 2>/dev/null
meubot() {
  [ -n "$CLAUDECODE" ] && { echo "Abra o meubot num terminal novo, fora do Claude Code."; return 1; }
  local os="{{OS_DIR}}" d="$HOME/.mestreos/telegram-bot" i=0 primeira=--inicio
  while [ ! -d "$os" ] && [ $i -lt 60 ]; do [ $i -eq 0 ] && echo "Esperando a pasta do OS aparecer..."; sleep 2; i=$((i+1)); done
  [ -d "$os" ] || { echo "A pasta do OS não apareceu. Abra o Google Drive e rode meubot de novo."; return 1; }
  cd "$os" || return 1
  while true; do
    local extra=(${=$("{{PYTHON}}" "$os/.meuos/scripts/telegram-bot-troca.py" atalho $primeira)})
    primeira=
    MESTREOS_MEUBOT=1 claude --settings "$HOME/.mestreos/telegram-bot.settings.json" --append-system-prompt-file "$os/.meuos/scripts/telegram-janela-do-bot.md" --channels plugin:telegram@claude-plugins-official "${extra[@]}"
    [ -f "$d/retomar" ] || break
    echo "Reabrindo a janela do bot com o modelo novo..."
  done
}
```
  - **Windows:** o atalho é um arquivo `meubot.cmd` na mesma pasta do `claude` (descubra com `Split-Path (Get-Command claude).Source`), porque `.cmd` funciona igual no PowerShell 7, no Windows PowerShell 5.1 (o que o Windows abre por padrão) e no Prompt, sem depender de perfil nem de política de scripts. Se existir uma função `meubot` antiga no `$PROFILE` de algum dos dois PowerShell, apague (ela passaria na frente do `.cmd`). Grave em UTF-8 sem BOM:
```
@echo off
chcp 65001 >nul
setlocal
if defined CLAUDECODE (echo Abra o meubot num terminal novo, fora do Claude Code. & exit /b 1)
set "PASTA_OS={{OS_DIR}}"
set /a N=0
:espera
if exist "%PASTA_OS%\" goto pronto
if %N%==0 echo Esperando a pasta do OS aparecer...
set /a N+=1
if %N% GEQ 60 (echo A pasta do OS nao apareceu. Abra o Google Drive e rode meubot de novo. & exit /b 1)
ping -n 3 127.0.0.1 >nul
goto espera
:pronto
cd /d "%PASTA_OS%"
set "D=%USERPROFILE%\.mestreos\telegram-bot"
set "MESTREOS_MEUBOT=1"
set "PRIMEIRA=--inicio"
:abrir
set "EXTRA="
for /f "usebackq delims=" %%a in (`call "{{PYTHON}}" "%PASTA_OS%\.meuos\scripts\telegram-bot-troca.py" atalho %PRIMEIRA%`) do set "EXTRA=%%a"
set "PRIMEIRA="
call claude --settings "%USERPROFILE%\.mestreos\telegram-bot.settings.json" --append-system-prompt-file "%PASTA_OS%\.meuos\scripts\telegram-janela-do-bot.md" --channels plugin:telegram@claude-plugins-official %EXTRA%
if not exist "%D%\retomar" goto :eof
echo Reabrindo a janela do bot com o modelo novo...
goto abrir
```
 Explique: "O atalho do bot liga o plugin só naquela janela. Vamos fechar esta conversa e abrir a janela do bot pelo atalho." Peça pra ele sair (`/exit`), abrir **um terminal novo** e digitar `meubot` (Mac e Windows, mesmo nome; no Windows, teste nos dois PowerShell, `powershell` e `pwsh` se tiver, e no Prompt). Essa é **a janela do bot**: enquanto ela estiver aberta, o Telegram funciona. Se fechar, o bot fica mudo até abrir de novo. Confira `/status` na janela do bot e em uma janela comum. Diga: "De agora em diante, `meubot` num terminal novo abre a janela do bot."

**7A.5 Parear e trancar.** Na janela do bot:
1. "Manda um `oi` pro seu bot no Telegram." O bot responde com um código de 6 letras (isso é o pareamento: o bot só obedece a quem você aprovar).
2. Na janela do bot: `/telegram:access pair <código>`.
3. Tranque pra ninguém mais receber código: `/telegram:access policy allowlist`. Explique: "Agora só o seu número fala comigo. Estranho que achar o bot recebe silêncio."
4. Peça o segundo `oi`. Este tem que chegar como mensagem na janela do bot, já com 👀 no celular (o remédio marca a chegada sozinho: ✍ no áudio, 👀 no resto), e você responde pelo Telegram (ferramenta `reply`), trocando a reação pela pertinente com `react`. Não reaja 👀 à mão: reação do agente vale como escolha e a de chegada não vira mais 👌.
5. **Permissões.** Na primeira vez que você usar `reply` ou `react`, o Claude Code pede permissão na janela do bot E manda o mesmo pedido pro Telegram com botões ✅ Permitir / ❌ Negar. Explique: "Quando eu precisar de permissão pra alguma coisa, aparece um botão no Telegram. Você aprova de lá mesmo." Na janela, escolha "Yes, and don't ask again" pra `reply` e `react` desta pasta, senão ele pergunta a cada mensagem. (Testado em 09/09/2026: `oi` → 👀 → pedido de permissão no Telegram → ✅ → resposta no celular em 20 s.)

**7A.6 Dar voz aos robôs.** Agora `telegram-send` funciona: ele lê o token do mesmo `.env` (Mac e Windows) e precisa do número do usuário. Pegue o número do arquivo `~/.claude/channels/telegram/access.json` (campo `allowFrom`, é um número, não é segredo) e grave em `.meuos/scripts/telegram-send.env` como `TELEGRAM_CHAT_ID=<número>` (só o número; o arquivo pode ficar no OS). Grave o arquivo em texto puro sem BOM (no Windows: `Set-Content -Encoding ascii`, não o Bloco de Notas em "UTF-8 com BOM"). Teste, igual nos dois sistemas: `"{{PYTHON}}" ".meuos/scripts/telegram_send.py" "🎉 Robôs com voz. 🤖 Robô de Teste, {{DATA_HOJE}}"`. A mensagem tem que aparecer no celular dele. (No Windows o `telegram_send.py` lê o token do Cofre DPAPI, se você guardou lá no 7A.2, ou do `.env` do plugin; se o Python reclamar de certificado, ele mesmo tenta de novo pelo `curl` do sistema.)

**7A.7 O que dizer no fim.** "Pronto. Você tem 2 jeitos de falar comigo: esta janela e o Telegram. A regra de ouro: **uma janela do bot por vez**. Pode abrir outras conversas do Claude Code normalmente, sem o aviso especial, que elas não atrapalham. Se parar de responder, eu confiro a fila, as permissões e quem está conectado antes de reiniciar. Uma resposta pendente não será anunciada como entregue." Registre no `changelog.md` do OS: "Telegram ligado em {{DATA_HOJE}} (7A, plugin oficial)".

**7A.8 Remédios do plugin (conferir compatibilidade antes).** O plugin oficial tem defeitos e lacunas conhecidos: depois que a conversa é compactada, o bot às vezes responde só a palavra "undefined" (09/09/2026); resposta longa cortada bem no meio de um emoji chega pela metade (23/09/2026); texto longo com lista some calado (06/10/2026); e ele não conta ao agente a mensagem que o usuário arrastou pra responder, ignora reação com emoji e localização, avisa "digitando" uma vez só e não assina as respostas (20/10/2026). O 7A.4 já rodou `"{{PYTHON}}" .meuos/scripts/telegram-plugin-remedio.py` e `... --check` (tem que dar ✓ nos 6) antes da primeira janela; rode de novo sempre que o plugin atualizar. Cada remédio entra inteiro ou não entra, e sai inteiro ou não sai, com backup e `--revert`. Se o plugin atualizar, rode `--check`; só reaplique quando o script reconhecer exatamente o trecho esperado. Trecho desconhecido exige auditoria, não substituição cega. Preserve a versão anterior e não reinicie uma sessão ativa: o plugin remediado vale na próxima vez que a janela do bot abrir. Localização e reação só valem do dono, na conversa privada, com a mesma régua de acesso do plugin. O endereço da localização vem do OpenStreetMap: só as coordenadas saem do computador, sem nome nem número; se a consulta falhar, ficam só as coordenadas. Explique: "Botei uns remendos no plugin: agora eu sei qual mensagem você arrastou pra responder, vejo a sua reação com emoji (e marco 👀 pra você saber que vi), entendo localização (o endereço vem do OpenStreetMap, que só recebe as coordenadas), o 'digitando' fica aceso até eu terminar, e cada resposta mostra no fim o modelo e o esforço que eu usei. Texto que é pra você mandar pra outra pessoa sai limpo, sem essa assinatura."

**7A.9 Trocar modelo e esforço pelo Telegram.** A janela do bot não troca o próprio modelo enquanto roda; quem troca é o `telegram-bot-troca.py`: grava as opções novas, espera o turno acabar, fecha a janela, e o `meubot` (que é um laço) abre de novo na MESMA conversa, com o modelo e o esforço novos. A primeira mensagem depois de reabrir é o aviso "✅ Pronto, agora estou no …", já com a assinatura do modelo novo. Se o modelo novo falhar logo na primeira resposta (a conta não tem aquele modelo, por exemplo), a janela volta sozinha pro de antes e avisa; se nem o de antes responder, ela para de reabrir e o robô avisa pelo `telegram_send.py` (7A.6). Travas: só vale mensagem do dono, na conversa privada (o que o plugin cita da mensagem arrastada não conta), e uma mensagem vale uma troca; troca na hora só quando a mensagem inteira dele é um pedido claro, sem pergunta e sem negação ("não troca", "para de usar"); áudio, recorte ou frase solta sempre pergunta "Confirma? sim ou não" antes; uma troca por vez. A janela só fecha com o turno quieto: se ele mandar outra mensagem no meio, ou se houver tarefa rodando em segundo plano, a troca espera; se não aquietar em 10 minutos, é cancelada e o robô avisa. A escolha fica valendo nas próximas vezes que ele abrir o `meubot`, até ele pedir outra. Modelos: Fable, Opus, Sonnet e Haiku (os que o plano dele tiver), sempre pelo nome: a conversa retomada guarda o modelo dela, então não existe "modelo padrão" por aqui. Esforço: baixo, médio, alto, altíssimo, máximo ou padrão (o da conta). Aviso honesto: raramente, se a conversa estiver muito longa e parada há mais de uma hora, o Claude Code pode abrir uma pergunta na tela ao reabrir; aí o bot fica mudo até alguém responder no computador. Teste real, com ele no celular: 1) "troca pro Sonnet" → "⏳ Trocando…", a janela fecha e abre sozinha, e em até 1 minuto chega "✅ Pronto, agora estou no Sonnet…" com a assinatura nova; 2) um áudio dizendo "muda o esforço pra alto" → a pergunta "Confirma?", ele responde "sim" → troca; 3) "esforço padrão" → volta pro esforço da conta, mantendo o modelo; 4) "não troca pro Opus" → nada troca (no máximo, a pergunta). Explique: "Pelo Telegram você troca o meu modelo e o meu esforço por frase, tipo 'troca pro Sonnet' ou 'esforço máximo'. Eu fecho e abro a janela sozinho, na mesma conversa, e aviso quando voltar. Se vier por áudio, eu confirmo antes. Se eu estiver no meio de uma tarefa, a troca espera eu terminar."

---

### 7B — Codex (Mac e Windows): ponte do Codex

> O Codex não tem canal de Telegram próprio (o controle remoto nativo dele é pelo app ChatGPT do celular, `codex remote-control`, não pelo Telegram). Usamos a ponte **cc-connect** (código aberto, Go, Mac e Windows), auditada em 09/09/2026 no commit `4000b23` com veredito **🟡 instalar com mitigação**. As mitigações estão embutidas abaixo; não pule nenhuma. Explique pro usuário em 1 frase: "Vou instalar um programinha que fica entre o Telegram e o Codex, tipo um porteiro: só deixa passar a SUA mensagem, e leva a resposta de volta."

**7B.1 Codex no caminho.** Rode `codex --version`. Se der "não encontrado" no Mac, o Codex que vem no app ChatGPT mora em `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex` (até setembro de 2026 era `.../Resources/codex`): confira com `"/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex" --version` e use esse caminho completo nos comandos deste passo. O MestreOS acha esse endereço sozinho (cérebro do Telegram e skill de imagem); pra ter o comando `codex` no terminal, instale `npm i -g @openai/codex` (precisa do Node). No Windows: `npm i -g @openai/codex`. Confirme login com `codex login status` (ou o caminho completo + `login status`).

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

**7B.5 Subir a ponte e deixar ligada.** Atalho: Mac `alias meubot='set -a; source ~/.claude/channels/telegram/.env; set +a; ~/.cc-connect/cc-connect --config ~/.cc-connect/config.toml'` no `~/.zshrc`; Windows: o `meubot.cmd` do 7A.4 até a linha `cd /d "%PASTA_OS%"` (espera a pasta do OS, funciona nos dois PowerShell e no Prompt), gravado na pasta do `codex` (`Split-Path (Get-Command codex).Source`), e no lugar do resto só as duas linhas `for /f "usebackq eol=# tokens=1,* delims==" %%a in ("%USERPROFILE%\.claude\channels\telegram\.env") do set "%%a=%%b"` e `"%USERPROFILE%\.cc-connect\cc-connect.exe" --config "%USERPROFILE%\.cc-connect\config.toml"`; apague a função `meubot` antiga do `$PROFILE`, se houver. Pra ligar sozinha com o computador: `cc-connect daemon install --config ~/.cc-connect/config.toml` (cria LaunchAgent no Mac, tarefa agendada no Windows, sem privilégio de administrador). Aviso honesto ao usuário: "Toda vez que abre, a ponte consulta o GitHub pra saber se tem versão nova. Não manda nada seu, mas também não dá pra desligar isso. Atualizar é decisão sua, e só pra versão que eu conferir o hash."

**7B.6 Testar.** `oi` no Telegram → resposta do Codex no celular. (Provado em 09/09/2026 no Mac: ponte conectou em 1 s, "qual é a capital de Minas?" → resposta do Codex em ~10 s; a ponte cria `~/.cc-connect/` com sessões, timers e um socket local `run/api.sock`, tudo só na máquina.) Reaja/edite como a ponte permitir. Robôs: 7A.6 vale igual (mesmo `.env`, mesmo `telegram-send.env`). Registre no `changelog.md`: "Telegram ligado em {{DATA_HOJE}} (7B, cc-connect v1.5.0 pinado, auditoria 🟡 com mitigações)".

---

### 7C — (aposentado em 16/09/2026) → vá para o 7D

> O 7C antigo fazia o Claude ser sempre o dono do bot e o Codex um convidado. Isso não era simétrico: quem começava pelo Codex tinha de desinstalar a ponte pra ganhar a Dupla. Foi substituído pelo **7D**, onde a janela do bot não pertence a nenhum motor. Se você está atualizando um OS que tinha o 7C: siga o 7D e, no 7D.4, remova o gancho antigo do `cerebro.py` do arquivo `~/.mestreos/telegram-bot.settings.json`. O estado da conversa (`cerebro.json`) é migrado sozinho na primeira mensagem.

---

### 7D — Dupla simétrica: Claude Code + Codex no MESMO bot, sem dono (quem tem os dois, em qualquer ordem)

> Entra quando o usuário tem **os dois motores** nesta máquina: o PASSO 0.0 detectou um e ele marcou o outro em `{{OUTRAS_IAS}}` (Claude + ChatGPT/Codex), OU ele já fez o 7A ou o 7B e assinou a outra IA depois. Quem tem uma IA só fica no 7A ou no 7B e nem vê este passo. Cursor: fora (sem canal).
> A regra do 7D: **nenhum motor é dono do bot.** A janela do bot é um programinha nosso, em Python (`telegram_janela.py`), que recebe a mensagem, guarda na fila, transcreve o áudio se houver como, e entrega ao cérebro que estiver ligado: o Claude Code (modo silencioso, sessão retomada) ou o Codex (thread retomada). O usuário tem um motor **principal** (o que ele já usa) e, se assinar o outro, um **secundário**. Começou só com um? Nada muda quando o outro chegar: ele entra como secundário, sem desinstalar nada.
> Explique em 1 frase: "Você vai ter dois cérebros no mesmo bot, {{IA_NOME}} e o outro. Você troca por frase, e eu continuo sendo eu, com a mesma memória e as mesmas regras. Áudio, foto e arquivo funcionam igual nos dois."

**7D.1 Os dois motores no caminho.** `claude --version` e `codex --version` precisam responder (Mac: o Codex do app ChatGPT mora em `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex`; confira com esse caminho completo + `--version`, o MestreOS acha esse endereço sozinho; pra ter o comando `codex` no terminal, `npm i -g @openai/codex`; Windows: `npm i -g @openai/codex` e `npm i -g @anthropic-ai/claude-code`). Confirme login dos dois: `codex login status` e `claude auth status` (ou abra o Claude Code uma vez). Se só um estiver instalado agora, siga o 7D mesmo assim: o `--motores` abaixo recebe `-` no lugar do secundário e o outro entra quando chegar.

**7D.2 Bot e token.** Se ainda não existe bot: faça o 7.1 (BotFather). Guarde o token fora do chat e fora do OS exatamente como no 7A.3 (arquivo `~/.claude/channels/telegram/.env`, linha `TELEGRAM_BOT_TOKEN=...`, o usuário cola, você só confere que a linha existe). Quem veio do 7A ou do 7B já tem isso pronto.

**7D.3 Extrair e validar o motor portátil.** Extraia os blocos `.meuos/hooks/cerebro.py`, `.meuos/hooks/telegram_runtime.py`, `.meuos/scripts/telegram_janela.py`, `.meuos/scripts/telegram_send.py`, `.meuos/scripts/test-telegram-runtime.py` e `.meuos/scripts/telegram-recovery.py`. Rode os três, todos sem token, sem IA e sem mensagem externa: `"{{PYTHON}}" .meuos/hooks/cerebro.py --teste` · `"{{PYTHON}}" .meuos/scripts/telegram_janela.py --teste` · `"{{PYTHON}}" .meuos/scripts/test-telegram-runtime.py`. Os três precisam terminar sem falha. Teste automático não equivale a conversa real aprovada.

**7D.4 Uma janela só (o Telegram entrega pra UM programa por vez).** Antes de abrir a janela nova, feche o que escutava o bot até agora, sem desinstalar nada:
- Veio do **7A** (plugin do Claude): feche a janela do bot (`/exit`). O plugin pode ficar instalado; ele só não pode estar rodando com `--channels`. Se existir `~/.mestreos/telegram-bot.settings.json` com um gancho `UserPromptSubmit` apontando pro `cerebro.py` (7C antigo), remova só esse gancho, preservando o resto do arquivo, com backup.
- Veio do **7B** (ponte cc-connect): pare a ponte (`~/.cc-connect/cc-connect daemon uninstall --config ~/.cc-connect/config.toml`, ou feche a janela dela). O binário e a config ficam no lugar.
- Erro 409 ao abrir a janela nova = ainda tem alguém escutando. Identifique quem antes de mexer; nunca troque o token por causa disso.

**7D.5 Dizer quem é o principal.** Rode `"{{PYTHON}}" .meuos/hooks/cerebro.py --motores {{IA}} <secundario>`, onde `{{IA}}` é `claude` ou `codex` (o app onde você está) e `<secundario>` é o outro (`codex` ou `claude`), ou `-` se o outro ainda não está instalado. Confira com `--status`. O estado mora em `~/.mestreos/telegram/<id-da-pasta>/` (disco local, fora do Drive/OneDrive), nunca dentro de `{{OS_DIR}}`.

**7D.6 Abrir a janela do bot e parear.** No terminal, dentro de `{{OS_DIR}}`: `"{{PYTHON}}" .meuos/scripts/telegram_janela.py` (Mac e Windows, mesmo comando). Ela imprime qual cérebro está ligado e se consegue ouvir áudio. Atalho pra ele não decorar: Mac `alias meubot='cd "{{OS_DIR}}" && "{{PYTHON}}" .meuos/scripts/telegram_janela.py'` no `~/.zshrc` (substitui o atalho antigo do 7A/7B, se houver: apague a linha `alias meubot=` ou a função `meubot()` com o `unalias` antes dela); Windows: o `meubot.cmd` do 7A.4 até a linha `cd /d "%PASTA_OS%"` (espera a pasta do OS, funciona nos dois PowerShell e no Prompt), na pasta do `claude` ou do `codex`, e no lugar do resto só a linha `"{{PYTHON}}" .meuos\scripts\telegram_janela.py`; apague a função `meubot` antiga do `$PROFILE`, se houver. Diga: "`meubot` no terminal abre a janela do bot. Enquanto ela estiver aberta, o Telegram funciona; se fechar, o bot fica mudo e o que chegar depois fica guardado até abrir de novo."
- Quem veio do 7A ou 7B já tem o número do dono em `.meuos/scripts/telegram-send.env` (7A.6) ou no `access.json` do plugin: a janela usa e não pergunta nada.
- Sem dono ainda: peça um `oi` pro bot no celular. A janela imprime **um código de 6 letras no terminal**; o usuário manda esse código pelo Telegram e pronto, pareado (o número dele vai pro `telegram-send.env`; é um número, não é segredo). Estranho que achar o bot recebe silêncio.
- Teste: segundo `oi` → reação 👀 no celular → resposta assinada (`🟣 Claude · Opus 5` ou `☀️ Sol`). A assinatura diz quem respondeu.

**7D.7 Áudio (a transcrição pertence à janela, não ao motor).** Nenhum dos dois motores ouve áudio sozinho; a janela transcreve antes, nesta ordem: `mlx_whisper` local (Mac com chip Apple, ~4 s por áudio) → chave da OpenAI (`OPENAI_API_KEY`) → chave da Groq (`GROQ_API_KEY`, **grátis**, caminho recomendado) → `whisper` de CPU se existir (funciona, mas leva ~1 min por áudio, por isso é o último) → sem nenhum: o bot responde "não consigo ouvir; manda em texto", sem inventar conteúdo.

**7D.7a Transcrição rápida no Mac (opcional, só Mac com chip Apple).** Confira `uname -m` = `arm64`. Procure um Python 3.12 ou mais novo, nesta ordem: `{{PYTHON}}`, `/opt/homebrew/bin/python3`, `/usr/local/bin/python3` (`<python> -c "import sys; print(sys.version_info >= (3,12))"` tem que dizer `True`). Não instale Python novo só pra isso: sem 3.12+, siga com a Groq abaixo. Com 3.12+, ofereça: "Quer que eu deixe a transcrição de áudio local e rápida? O áudio é transcrito no seu próprio Mac, em poucos segundos. São uns 3 GB no total, uma vez só (1,2 GB de programas + 1,5 GB do modelo). Se um dia a transcrição local falhar e você tiver uma chave da Groq ou da OpenAI configurada, aí o áudio vai pra ela, como já acontece hoje." Se sim, rode exatamente (versões fixadas e auditadas; ambiente separado, não mexe no resto do Mac):
```
<python> -m venv ~/.mestreos/stt
~/.mestreos/stt/bin/pip install "mlx-whisper==0.4.3" "mlx==0.32.2" "numpy==2.5.3" "torch==2.14.0" "tqdm==4.70.1" "scipy==1.18.1" "numba==0.67.0" "tiktoken==0.14.0" "huggingface-hub==2.0.0"
rm -f /tmp/mestreos-teste-audio.txt /tmp/mestreos-teste-audio.aiff
say -v Luciana -o /tmp/mestreos-teste-audio.aiff "teste de transcrição"
env -u HF_HUB_OFFLINE HF_HUB_DISABLE_TELEMETRY=1 ~/.mestreos/stt/bin/mlx_whisper /tmp/mestreos-teste-audio.aiff --model mlx-community/whisper-large-v3-turbo --language pt --output-dir /tmp --output-name mestreos-teste-audio -f txt
```
O último comando baixa o modelo (~1,5 GB, alguns minutos; o `env -u HF_HUB_OFFLINE` garante que ele pode usar a internet) e já prova a transcrição: `/tmp/mestreos-teste-audio.txt` tem que conter "teste de transcrição" (o `rm -f` do começo garante que o arquivo é desta tentativa; o `mlx_whisper` sai com sucesso até quando falha, então vale o arquivo, não a mensagem do comando). Se o arquivo não existir ou não tiver essa frase (mesmo com o `pip install` sem erro), a instalação ficou pela metade: apague a pasta `~/.mestreos/stt` que você acabou de criar (mostre ao usuário antes; ela só tem o ditado de áudio) e siga com a Groq. Não deixe um ambiente que não passou no teste. A janela acha o `~/.mestreos/stt` sozinha, pede sempre esse modelo (sem ele o `mlx_whisper` usaria o menor, fraco em português) e roda sem rede depois do primeiro download. Reinicie a janela e mande um áudio de teste. Se o `pip install` falhar, não insista: apague `~/.mestreos/stt` do mesmo jeito e siga com a Groq. Pra ligar a Groq: "Entra em console.groq.com, cria uma conta grátis, vai em API Keys e cria uma chave. Abre o mesmo arquivo do token e acrescenta uma linha `GROQ_API_KEY=` com a chave. Salva." Você NÃO vê a chave; confira só que a linha existe (`grep -c '^GROQ_API_KEY=' ~/.claude/channels/telegram/.env` no Mac; `Select-String` no Windows). Limite do tier grátis: áudio até 25 MB. Comando falado ("troca pro Codex") passa a funcionar porque a janela transcreve antes de decidir.

**7D.7b A porta: rajada, anexo prometido e reações.** A janela junta o que o dono manda em sequência e responde UMA vez: texto digitado sem promessa sai na hora (caminho expresso); áudio, foto ou arquivo esperam 2 segundos por mais mensagens da mesma rajada; se o dono diz que vai mandar um anexo ("vou te mandar a foto", "segue o print"), a janela reage 🫡 e espera até 1 minuto pelo anexo, e aí responde tudo junto. Se o anexo não chegar (esqueceu, foi interrompido, a internet falhou), a resposta sai assim mesmo e avisa que está aguardando. "Me manda a foto" é pedido pro agente, não promessa: sai na hora. Reações: ✍ no áudio (o Telegram não deixa bot usar 👂), 👀 no resto; quando a resposta sai, a reação SEMPRE troca: pela pertinente que o cérebro escolher (❤ agradecimento, 🔥 empolgação, 🙏 desculpa, 👍, 🤝, 😢) ou por 👌 ("entendido, feito"). Bot só usa a lista fixa de 73 reações do Telegram; emoji personalizado do Premium também é recusado. Explique: "Pode mandar áudio e foto em sequência, ou avisar que vai mandar um arquivo: eu espero e respondo tudo de uma vez, sem gastar duas respostas."

**7D.7c Cota estourada: troca sozinha e volta sozinha.** Se o motor que está respondendo bater no limite do plano, o cérebro anota até quando, passa SOZINHO pro outro motor (se o usuário tiver os dois) e avisa em 1 linha ("⏳ O Claude bateu no limite do plano (volta às 23:00). Passei pro Codex sozinho e volto pro Claude quando liberar."). Se a falha foi logo no começo (nada foi feito), o outro motor responde o mesmo pedido na hora; se parou no meio, pede pra reenviar (nunca repete ação às cegas). Na primeira mensagem depois da hora de volta, retorna pro principal com o resumo do que rolou. Os dois sem cota: aviso honesto, sem ficar trocando em laço. Quem tem um motor só continua recebendo o aviso com a hora de volta.

**7D.8 Recuperação.** Rode `"{{PYTHON}}" .meuos/scripts/telegram-recovery.py --plan`, depois `--install` e `--status`. Isso agenda, a cada minuto, uma conferência da fila no launchd (Mac) ou no Agendador (Windows), sob o usuário logado: se a janela estiver aberta, ela cuida e a recuperação não faz nada; se estiver fechada, só pedidos `queued` são atendidos; uma execução interrompida vira `uncertain` e exige conferir efeitos antes de repetir. Uma tarefa já existente divergente exige comparação, não substituição. Registre o rótulo exibido em `--plan`.

Acrescente estas regras ao `claude.md` do usuário, preservando a identidade dele, e depois rode `"{{PYTHON}}" ".meuos/scripts/sync-agents.py"` pra elas chegarem no `AGENTS.md` (nunca edite o `AGENTS.md` à mão):
- Responder à mensagem real do usuário, inclusive se ele mandar outra enquanto eu trabalho; quem entrega é a janela, com recibo; eu não afirmo entrega pela intenção de enviar.
- A troca de cérebro é feita pela janela, por frase; eu não consigo trocar sozinho e não finjo que troquei. Ao assumir, leio o resumo deixado pelo outro cérebro e continuo de onde ele parou, sem comentar o mecanismo.
- Áudio chega transcrito e rotulado pela janela; sem transcrição, peço em texto e não invento o conteúdo.
- Arquivo que eu quiser mandar pro celular vai pra `outputs/imagens/<data>/`; a janela envia o que aparecer lá.

**7D.9 Teste real no celular (obrigatório, nos dois sentidos).**
1. `oi` → resposta do principal, com assinatura.
2. "troca pro Codex" (ou "troca pro Claude") → confirmação de troca; pergunta curta → resposta do outro, com a outra assinatura.
3. Durante uma resposta demorada, mande mais duas perguntas diferentes. Confira as três respostas em ordem, sem repetição.
4. "qual cérebro tá ligado?" → status. "volta pro <principal>" → confirmação; nova mensagem → o principal retoma o assunto (continuidade) e responde de verdade.
5. Mande um áudio dizendo "vou te mandar uma foto" e, logo em seguida, a foto → ✍ no áudio, 🫡 enquanto espera e UMA resposta sobre os dois. Sem transcrição ligada chega o aviso honesto. Depois, um áudio prometendo um print sem mandar nada → em cerca de 1 minuto a resposta avisa que está aguardando o print.
6. `"{{PYTHON}}" .meuos/scripts/telegram_janela.py --status`: todos os pedidos `completed`. Se houver `queued`, `running` ou `uncertain`, não anuncie tudo entregue. O recibo confirma envio, não a qualidade da resposta.

**7D.10 Entrega honesta.** Explique: "Você troca de cérebro por frase, nos dois sentidos. Se mandar outras mensagens enquanto penso, elas ficam na fila e saem em ordem. Se mandar áudio e foto em sequência, ou avisar que vai mandar um anexo, eu espero e respondo tudo junto; se o anexo não chegar em 1 minuto, eu aviso. Áudio funciona igual nos dois, desde que a transcrição esteja ligada. Se um dos cérebros bater no limite do plano, eu passo sozinho pro outro e volto quando liberar. Se algo interromper, eu preservo o pedido e aviso o que ficou pendente; não repito nada sozinho." Anote versão do pacote, sistema, versões dos programas e resultado do teste real no `changelog.md`. Nunca declare compatibilidade completa de uma conta sem testar naquela conta.

> **O que a janela faz e o que não faz.** Faz: receber, reagir 👀, fila em ordem, transcrever, entregar texto e arquivo com recibo, trocar cérebro por frase. Não faz: botão de permissão no celular (o Claude roda em modo silencioso com ferramentas de arquivo; terminal fica desligado por padrão, e o dono pode ampliar com `MESTREOS_CLAUDE_TOOLS`), nem edição de mensagem já enviada. Quem tem uma IA só e prefere o canal nativo continua no 7A ou 7B.

> **Plano B (se a janela falhar numa máquina específica):** ponte cc-connect por motor, um bot por motor, com STT por chave. Não está neste passo; <!-- MESTRE:INICIO -->fale com o Paulo Penna, o Mestre do MestreOS (WhatsApp +55 31 99345-3332 · pauloapenna@gmail.com · mestreos.app · LinkedIn: linkedin.com/in/paulo-p-37623171).<!-- MESTRE:FIM -->

---

## 7E: Aceite e atualização, obrigatório nos três ramos

- Claude/Mac, Claude/Windows, Codex/Mac, Codex/Windows: registrar ramo e testar pergunta simples, mensagens durante trabalho, áudio/foto e falha de entrega. Dupla (7D) exige os testes extras do 7D.9, nos dois sentidos.
- 7A e 7B têm transportes próprios: a fila e a janela do 7D não corrigem internamente o plugin nem o cc-connect. Não chamar os três de homologados só porque os testes Python passaram. Se um transporte perder mensagens durante trabalho, interrompa a instalação naquele ramo, preserve o histórico e encaminhe o diagnóstico ao responsável.
- Nunca execute dois consumidores para o mesmo token (plugin, cc-connect, janela do 7D, webhook, outro computador). Um erro 409 pede auditoria do consumidor; não exige token novo. Não imprimir token nem chamar getUpdates por fora enquanto uma janela estiver aberta.
- Se chegar cobrança de áudio, recupere o anexo e a pergunta original antes de responder sobre outro assunto.
- Atualizações oficiais: chegam junto com o MestreOS inteiro, quando o usuário diz "atualiza o meu MestreOS" (o MODO ATUALIZAR refaz os arquivos do Telegram a partir do instalador novo). Confira versão, hashes e testes; faça backup e aplique só os arquivos técnicos aprovados, preservando personalidade, memória, segredos e permissões. Quem tinha o 7C migra pro 7D pelo mesmo prompt (janela nova, gancho antigo removido, estado preservado).
- Conferir atualização pode ser automático; instalar e reiniciar exige respeitar o trabalho ativo e a autorização do dono da máquina. Nunca disparar mensagem para outros alunos nem implantar silenciosamente em suas máquinas.

---

### 7F — Bot próprio: só avisos (quem já tem um programa seu atendendo o bot)

Quando o token do bot já é usado por um programa que não é do MestreOS (uma ponte feita sob medida, um fluxo do n8n, um serviço, outro computador), o MestreOS **não instala janela, plugin nem ponte**. O Telegram entrega cada mensagem pra um programa só: um segundo programa escutando derrubaria o do aluno (erro 409), e isso iria contra a regra de não derrubar o que funciona. O que entra é só a **voz dos robôs**: o `telegram_send.py` manda os avisos (o bom-dia da saúde, o resumo de domingo, o aviso de compactação) pelo mesmo bot, sem escutar nada. Mandar mensagem não briga com quem escuta.

**7F.1 Token, sem mexer na ponte.** Teste do jeito que o robô roda, sem as variáveis do terminal. Mac: `env -u TELEGRAM_BOT_TOKEN -u TELEGRAM_CHAT_ID "{{PYTHON}}" .meuos/scripts/telegram_send.py "🤖 Teste do MestreOS: os robôs agora falam com você por aqui."`. Windows: o mesmo comando sem o `env -u` (as variáveis de usuário do Windows chegam no Agendador). Se sair `telegram_send: ok`, pule pro 7F.3. Se disser **sem token**: os robôs rodam fora do terminal e não enxergam a variável que a ponte do aluno usa no Mac, então o token precisa estar no Cofre. Rode a skill `cofre` pra guardar o **mesmo token** do bot com o nome `telegram-bot-token` (o aluno cola no popup; o token nunca passa pelo chat; e você nunca abre o arquivo de configuração da ponte, nem o agendamento dela, pra achar o token: o que aparece na conversa fica gravado). Depois de guardar, **rode o teste de novo** e siga pelo que ele disser.

**7F.2 Destino.** Se disser **sem destino**: o robô precisa do número de usuário do aluno no Telegram (é um número, não é segredo). Se a ponte do aluno tem uma lista de quem pode falar com o bot, o número está lá: leia só esse campo, com um comando que imprime só ele (nunca o arquivo inteiro, que costuma ter o token junto). Se não achar, peça: "No Telegram, procura **@userinfobot**, manda `/start` e me diz o número que ele responde em **Id**." Grave em `.meuos/scripts/telegram-send.env` uma linha `TELEGRAM_CHAT_ID=<número>`. Rode o teste do 7F.1 de novo.

**7F.3 Teste no celular.** `telegram_send: ok` prova que o Telegram aceitou, não que o aluno leu. Pergunte: "Chegou no seu celular uma mensagem começando com 🤖 Teste do MestreOS? Os acentos e o emoji vieram certinhos?" Só siga com o sim dele.

**7F.4 O que dizer.** "O seu bot continua do jeito que você montou. O MestreOS só usa ele pra te mandar os avisos dos robôs; ele não responde nem escuta por esse bot. Se um dia você quiser conversar comigo pelo celular, é um segundo bot (eu te ajudo a criar no BotFather) ou desligar o seu programa antes: nunca os dois no mesmo bot." Registre no `changelog.md`: "Telegram: caminho 3 (bot próprio, só avisos) em DD/MM/AAAA".
