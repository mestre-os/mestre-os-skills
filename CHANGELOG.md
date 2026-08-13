# Changelog — MestreOS Skills

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
