# Telegram do MestreOS 4.0.1

Atualização da integração e dos roteiros para Claude e Codex em Mac e Windows. O runtime da Dupla guarda pedidos em fila, executa um por vez e confirma envio. Pedidos interrompidos ficam preservados para conferência, sem repetição automática de ações.

Atualize pelo [prompt oficial](../prompts/atualizar-telegram.md). Veja [integração](INTEGRACAO.md) e [manifesto](manifest.json). O script `telegram-update.py` consulta novidades; `--stage` baixa uma cópia com hashes para revisão e não instala nada. A consulta periódica é opcional.

Validação: regressões offline executadas em macOS e Windows 11 ARM, com Python. Isso não prova login, conta ou conversa real de todos os alunos. Os transportes Claude e cc-connect continuam exigindo o aceite 7D. Nenhuma conta de aluno recebe alterações ou mensagens automaticamente.

Fontes técnicas consultadas: [configuração por sessão do Claude](https://code.claude.com/docs/en/settings), [canais do Claude](https://code.claude.com/docs/en/channels), [ponte cc-connect](https://github.com/chenhg5/cc-connect). Codex exec/resume verificado no help do executável instalado, mantendo sandbox e saída JSON.
