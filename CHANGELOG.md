# Changelog — MestreOS Skills

## 2026-09-23: Telegram 4.1.2 (emoji partido no plugin do ramo Claude)

- **Resposta longa podia chegar pela metade no ramo Claude (7A).** O plugin oficial corta respostas acima de 4096 por posição; se o corte cai no meio de um emoji, o Telegram recusa aquele pedaço inteiro. O `telegram-plugin-remedio.py` ganhou o 2º remédio: recua o corte quando ele partiria o emoji.
- Cada remédio só entra se o trecho exato for reconhecido; conserto equivalente que já exista não é duplicado; arquivo com fim de linha do Windows continua igual fora das linhas remediadas, e reverter devolve o arquivo idêntico.
- **Quem já instalou o ramo Claude:** o prompt de atualização manda rodar o remédio de novo e conferir `--check` (✓ nos dois), com o bot ocioso.
- Provas offline: 72 verificações em macOS e em Windows 11 ARM; remédio testado numa cópia do plugin atual e do mais recente.

## 2026-09-23: Telegram 4.1.1 (correções do teste real no celular)

- **Foto e áudio sumiam sem aviso.** O download do anexo quebrava por dentro e o erro era engolido: a mensagem chegava ao cérebro sem a foto ou sem o áudio. Corrigido, com registro no log. Um erro do servidor não vira mais "arquivo baixado".
- **Anexo que não baixa vira aviso honesto.** O cérebro recebe a instrução de dizer que não conseguiu abrir e pedir o reenvio, nunca de inventar o conteúdo.
- **Resposta longa com muito emoji não some mais.** O corte agora mede como o Telegram mede (emoji conta dobrado, teto 4096) e prefere quebrar na linha.
- **Telegram pedindo pra esperar (429) ou fora do ar (5xx):** uma nova tentativa, respeitando o tempo pedido. Outras recusas não repetem e ficam registradas com o motivo.
- Provas offline: 68 verificações em macOS e em Windows 11 ARM. Conversa real continua sendo aceite por instalação.

## 2026-09-18: Telegram 4.1.0 (Dupla simétrica, PASSO 7D)

- **Janela neutra** `telegram_janela.py`: dona do bot (getUpdates), pareamento por código de 6 letras impresso no terminal, reação 👀, fila SQLite em ordem, download de foto/voz/arquivo, transcrição em cadeia (whisper local, depois OpenAI, depois Groq grátis, senão "manda em texto", sem inventar conteúdo), entrega com recibo, `--recover` pro agendador, `--status`, `--teste`. Recusa segunda janela e para no 409.
- **Cérebro motor-agnóstico** `cerebro.py`: principal e secundário, `--motores`, troca por frase nos dois sentidos ("troca pro Codex", "volta pro Claude", "muda pra Anthropic no modelo sonnet"), continuidade por resumo de quem sai mais as últimas trocas, Claude em `-p` com sessão retomada e ferramentas de arquivo, Codex em sandbox `workspace-write`, estado do 7C migrado sozinho.
- 7C aposentado (redirect pro 7D); aceite renumerado pra 7E. `telegram-recovery.py` passa a chamar a janela em modo `--recover`.
- Falha conhecida vira instrução: Claude ou Codex sem login responde "abra o Terminal e rode `claude auth login`" (ou `codex login`); cota estourada diz quando volta e sugere o outro cérebro. Antes o dono recebia só "código 1".
- Provas offline: 65 verificações em macOS e em Windows 11 ARM. Conversa real continua sendo aceite por instalação.

## v1.4 — 23/08/2026

Atualização de arquitetura documental. O tema desta versão é um só: **parar de pagar, em toda sessão, por informação que já cumpriu o papel dela.**

- **salvar 1.2**: tarefa concluída agora SAI do documento mestre depois de registrada no changelog. Antes ela virava linha riscada e ficava lá pra sempre; como o mestre é lido em toda sessão, cada lápide era custo fixo só pra dizer "isto já foi feito". Se a conclusão derrubar uma regra que o mestre ainda afirma, a skill reescreve a regra no próprio mestre em linguagem afirmativa e registra a virada no changelog, pra próxima sessão não obedecer instrução morta. Entraram também os 2 gatilhos de roteamento e o semáforo do mestre medindo linhas E KB.
- **otimizar-os 1.2**: a faxina das lápides antigas virou migração de uma vez só, com aprovação, e não espera mais juntar quinze delas. Ganhou detector de skill velha: se aparecerem lápides novas depois da limpeza, a rotina de fechamento em uso está desatualizada e você é avisado. E o critério do satélite passou a separar duas coisas que estavam misturadas: onde o conteúdo NASCE (pela natureza do fato, sempre) e quando vale QUEBRAR o que já está grande demais (por tamanho e massa).
- **Regra da mesa e da gaveta**, agora explícita no guia do OS e nas regras invioláveis: o mestre é a mesa (decisão vigente, status, de quem é a bola, próximo passo), o satélite é a gaveta (detalhe durável de um tema). A casa se decide na escrita, nunca na faxina. Contexto novo já nasce com a seção de satélites no mestre e com o index ensinando a listar todos.
- **Checklist final em todas as skills**: cada uma termina com uma lista de conferência que o agente roda antes de dizer que terminou. Item pendente significa corrigir antes, não reportar "pronto".

Skills atualizadas: salvar 1.2, otimizar-os 1.2, otimizar-custo 1.2, ligar-loop 1.1, me-faca-perguntas 1.1, preparar-os-dual 1.1. Cofre e escrita-densa foram para 1.1 dentro do instalador.

## v1.3 — 13/08/2026

Chegou o **Pacote Marketing do MestreOS**: 34 skills de marketing, growth e SEO, adaptadas de material open source consagrado da comunidade (MIT, ver LICENSES.md) com gatilhos em português e integração com a estrutura de contextos do MestreOS. Cobrem fundação (posicionamento, pesquisa de cliente, plano de marketing), conversão (cadastro, onboarding, paywall, preço, testes A/B), aquisição (anúncios, e-mails, social, lançamento, indicação), SEO e IA (auditoria, SEO programático, schema) e conteúdo/análise (copy, concorrentes, analytics). Todas leem o brief da marca em `{contexto}/marketing.md` antes de perguntar qualquer coisa. Instalação opcional pelo prompt em `prompts/instalar-pacote-marketing.md`.

E uma skill nova no núcleo:

- **preparar-os-dual 1.0**: deixa o OS pronto para mais de um agente ao mesmo tempo (Claude + ChatGPT/Codex + Cursor). Varre a raiz e todos os contextos e garante um `AGENTS.md` espelhado, byte a byte, ao lado de cada `claude.md`. Idempotente; quando o espelho diverge da fonte, mostra e pergunta em vez de decidir sozinho.

## v1.2 — 13/08/2026

Esta rodada ataca uma coisa só: **o seu OS engorda na hora de escrever, não na hora de limpar.** Até aqui a gente tinha boas ferramentas pra faxina depois da bagunça. Agora tem filtro na entrada, e o conserto vira exceção.

- **salvar 1.1**: ganha o **gate de escrita**. Antes de gravar qualquer coisa, o agente lê o arquivo de destino inteiro, procura se o assunto já está escrito em algum lugar (se estiver, edita a entrada existente em vez de criar uma segunda), aplica o teste dos 3 meses ("isso muda como eu trabalho daqui a 3 meses?"), respeita um teto de 6 linhas por entrada e no máximo 3 entradas por sessão, e se o arquivo já estourou o limite só grava se algo sair na mesma rodada. Ganha também o **contrato por arquivo**: uma tabela que define o endereço certo de cada tipo de informação, pra decisão parar de cair no changelog e caso pontual parar de virar aprendizado. E passa a exigir o `index.md` 100% completo: satélite fora do índice é documento invisível.
- **otimizar-os 1.1**: a caça de arquivos órfãos vira **checagem completa de integridade**. Agora encontra três defeitos diferentes: link quebrado (renomear um arquivo não conserta quem apontava pra ele, e todos quebram em silêncio), órfão de índice e órfão total (nenhum documento do OS referencia). Ganha o **frontmatter de manutenção**, uma ficha de identificação no topo do arquivo (`updated`, `type`, `status`) adotada aos poucos, arquivo por arquivo, nunca em migração de uma vez só. E a promoção de conteúdo perene passa a ter **três destinos** em vez de dois: decisão de negócio sobe pro documento mestre, regra rígida de operação vai pro claude.md do contexto (raro), regra de um tema só vai pra satélite.
- **otimizar-custo 1.1**: cadência clara. Quem lembra dessa skill é a `otimizar-os`, no máximo uma vez por mês. A `salvar` apenas observa, nunca cobra. Motivo: `salvar` roda várias vezes por dia, e um lembrete diário vira alarme que você aprende a ignorar.

## v1.1 — 22/07/2026

- **me-faca-perguntas 1.0**: skill nova. Antes de construir qualquer coisa (app, feature, decisão, documento), a IA vira um entrevistador rigoroso: uma pergunta por vez, repergunta quando a resposta vem vaga, caça suposições escondidas, contradições e casos de borda, e desafia o escopo ("existe caminho mais simples?"). "Não sei" vale como resposta: ela apresenta 2-3 opções com prós e contras. A entrevista termina numa síntese com decisões tomadas, pontos em aberto, próximo passo e critério de pronto verificável.

## v1.0 — 02/07/2026

Lançamento do repositório oficial, junto com o MestreOS v3.0 (manual + instalador novos).

- **salvar 1.0**: nova skill que funde "conferir entrega" + "fim do dia" num checkpoint que roda a qualquer hora. Orientação principal: siga o semáforo do anel de contexto do Claude Code (🟡 rode a salvar · 🔴 rode, feche a sessão e abra nova). Você faz a sua própria compactação em vez de deixar o provedor compactar às cegas.
- **ligar-loop 1.0**: nova skill que funde "engenharia de loop" + "loop autônomo". Dois tempos: Plano de Loop aprovado por você, depois execução com travas.
- **otimizar-os 1.0**: passa a mostrar o custo fixo por sessão em tokens (o número que você paga em toda mensagem); ganha o gate "no piso, sem ação" (para de reclamar quando não há mais o que limpar); regras permanentes vão pra "gaveta" (satélite lido sob demanda) em vez de inflar os arquivos que carregam sempre; proteção do soul.md.
- **otimizar-custo 1.0**: mede linhas E caracteres da memória (linha gorda também custa); enxuga o índice pra uma linha por item; funde tópicos irmãos com aprovação; relatório mostra o custo fixo da sessão antes e depois.

As skills antigas ("conferir-entrega", "fim-do-dia", "engenharia-de-loop", "loop-autonomo") viram redirects: os comandos antigos continuam funcionando e caem nas skills novas.

## 2026-09-12: Telegram 4.0.1

Fila durável na Dupla, execução serial, confirmação de entrega, recuperação conservadora, timeout por inatividade, UTF-8 e locks Mac/Windows. Isolamento da janela Claude e roteiro de aceite para os três transportes. Pacote, hashes e prompt de atualização. 31 regressões offline em cada sistema; conversa real requer aceite por conta.
