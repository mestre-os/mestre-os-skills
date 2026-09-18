# Atualizar a integração Telegram do meu MestreOS

Quero atualizar somente a integração Telegram nesta pasta. Preserve minha identidade, memória, arquivos, credenciais e permissões.

1. Leia minhas regras e identifique Mac/Windows e o ramo: Claude, Codex com cc-connect ou Dupla. Consulte https://raw.githubusercontent.com/mestre-os/mestre-os-skills/main/telegram/manifest.json e https://github.com/mestre-os/mestre-os-skills/tree/main/telegram. Não presuma que todos usam a mesma ponte.
2. Mostre versão atual, versão disponível e arquivos a alterar. Se houver trabalho ativo no bot, guarde o plano e espere a janela ficar ociosa, sem encerrar processos. Não crie outro consumidor do mesmo token.
3. Confira hashes. Leia os arquivos técnicos antes de aplicar. Faça backup com manifesto e instrução de restauração. Substitua apenas arquivos deste pacote que pertençam à integração escolhida; mescle configuração dedicada sem apagar minhas demais chaves. Não reinstale meu OS.
4. Siga INTEGRACAO.md do pacote. Rode testes offline no meu sistema. Para Dupla (7D), com o bot ocioso: feche a janela antiga (plugin ou ponte, sem desinstalar), remova só o gancho antigo do cerebro.py de `~/.mestreos/telegram-bot.settings.json` se existir, rode `cerebro.py --motores <principal> <secundario>`, agende a recuperação e abra a janela nova (`telegram_janela.py`). O estado de conversa é migrado sozinho; preserve a origem. Não execute pedidos incertos sem conferir o que já ocorreu.
5. Abra o bot só com a configuração conferida e valide pelo meu celular: pergunta simples, duas mensagens durante trabalho, áudio/foto, troca de cérebro se aplicável. Confirme cada resposta real. Sem conta ou permissão, diga o que falta, sem afirmar sucesso.
6. Registre versão, arquivos, backup, resultado e limitações no changelog. Ofereça consulta periódica de novas versões; não ligue broadcast nem instalação automática silenciosa.
