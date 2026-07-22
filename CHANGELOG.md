# Changelog — MestreOS Skills

## v1.1 — 22/07/2026

- **me-faca-perguntas 1.0**: skill nova. Antes de construir qualquer coisa (app, feature, decisão, documento), a IA vira um entrevistador rigoroso: uma pergunta por vez, repergunta quando a resposta vem vaga, caça suposições escondidas, contradições e casos de borda, e desafia o escopo ("existe caminho mais simples?"). "Não sei" vale como resposta: ela apresenta 2-3 opções com prós e contras. A entrevista termina numa síntese com decisões tomadas, pontos em aberto, próximo passo e critério de pronto verificável.

## v1.0 — 02/07/2026

Lançamento do repositório oficial, junto com o MestreOS v3.0 (manual + instalador novos).

- **salvar 1.0**: nova skill que funde "conferir entrega" + "fim do dia" num checkpoint que roda a qualquer hora. Orientação principal: siga o semáforo do anel de contexto do Claude Code (🟡 rode a salvar · 🔴 rode, feche a sessão e abra nova). Você faz a sua própria compactação em vez de deixar o provedor compactar às cegas.
- **ligar-loop 1.0**: nova skill que funde "engenharia de loop" + "loop autônomo". Dois tempos: Plano de Loop aprovado por você, depois execução com travas.
- **otimizar-os 1.0**: passa a mostrar o custo fixo por sessão em tokens (o número que você paga em toda mensagem); ganha o gate "no piso, sem ação" (para de reclamar quando não há mais o que limpar); regras permanentes vão pra "gaveta" (satélite lido sob demanda) em vez de inflar os arquivos que carregam sempre; proteção do soul.md.
- **otimizar-custo 1.0**: mede linhas E caracteres da memória (linha gorda também custa); enxuga o índice pra uma linha por item; funde tópicos irmãos com aprovação; relatório mostra o custo fixo da sessão antes e depois.

As skills antigas ("conferir-entrega", "fim-do-dia", "engenharia-de-loop", "loop-autonomo") viram redirects: os comandos antigos continuam funcionando e caem nas skills novas.
