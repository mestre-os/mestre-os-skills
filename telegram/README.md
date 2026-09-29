# Telegram do MestreOS 4.0

Dupla simétrica (PASSO 7D): a janela do bot não pertence a nenhum motor. Um programa do MestreOS em Python (`telegram_janela.py`) recebe as mensagens, guarda numa fila SQLite, transcreve áudio quando há provedor (whisper local, OpenAI ou Groq) e entrega ao cérebro ligado: Claude Code (modo silencioso, sessão retomada) ou Codex (thread retomada). Troca por frase nos dois sentidos, continuidade por resumo, principal e secundário, entrada do segundo motor sem desinstalar nada. Na 4.0, se o cérebro ligado bater no limite do plano, a janela passa sozinha pro outro motor e volta quando a cota libera (7D.7c). O 7C antigo (Claude dono do bot) foi aposentado e vira redirect.

Também na 4.0: o cérebro acha o Codex no endereço novo do app do ChatGPT (`Resources/codex-cli/bin/codex`, desde setembro de 2026) e ainda aceita o antigo; a linha do Remote Control ("login expired, run /login") não é mais confundida com login perdido; e a pasta da memória do Claude no Windows segue a mesma regra dos robôs.

Atualize pelo [prompt oficial](../prompts/atualizar-telegram.md). Veja [integração](INTEGRACAO.md) e [manifesto](manifest.json). O script `telegram-update.py` consulta novidades; `--stage` baixa uma cópia com hashes para revisão e não instala nada. A consulta periódica é opcional.

Validação: 100 regressões offline executadas em macOS (Python 3.9.6) e Windows 11 ARM (Python 3.12.10), com os mesmos arquivos. Isso não prova login, conta, cota ou conversa real de todos os alunos. Os transportes 7A (plugin) e 7B (cc-connect) continuam exigindo o aceite 7E; a Dupla exige o teste 7D.9 no celular, nos dois sentidos. Nenhuma conta de aluno recebe alterações ou mensagens automaticamente.

Fontes técnicas consultadas: [CLI do Claude Code](https://code.claude.com/docs/en/cli-reference) (`-p`, `--session-id`, `--resume`, `stream-json`), [Groq speech-to-text](https://console.groq.com/docs/speech-to-text) (`whisper-large-v3-turbo`, tier grátis, 25 MB), Codex `exec`/`resume` verificado no help do executável instalado (só imagem como anexo).
