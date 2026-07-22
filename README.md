# MestreOS — Skills oficiais

Skills do **MestreOS**: o sistema operacional pessoal que transforma o seu agente de IA (Claude Code e similares) num parceiro que conhece você, seus projetos e suas regras. Este repositório é a fonte oficial das skills. Cada atualização chega aqui primeiro, versionada.

Por **Paulo Penna** (conceito original de Fernando Lúcio).

## As skills

| Skill | O que faz | Versão |
|---|---|---|
| [salvar](skills/salvar/SKILL.md) | Checkpoint de soberania de contexto: confere a entrega, sintetiza a sessão e grava um checkpoint durável no SEU formato. Rode quando o anel de contexto ficar amarelo (🟡) e sempre antes de fechar uma sessão cheia (🔴). Funde as antigas "conferir entrega" e "fim do dia". | 1.0 |
| [ligar-loop](skills/ligar-loop/SKILL.md) | Engenharia de loop em dois tempos: desenha o Plano de Loop, você aprova, e liga o trabalho autônomo com travas de segurança (critério de parada, teto de iterações, rollback). Funde as antigas "engenharia de loop" e "loop autônomo". | 1.0 |
| [otimizar-os](skills/otimizar-os/SKILL.md) | Organiza e compacta os arquivos do OS. Mostra o custo fixo por sessão em tokens e para quando não há mais nada útil a reduzir. | 1.0 |
| [otimizar-custo](skills/otimizar-custo/SKILL.md) | Higiene da memória persistente do agente. Mede linhas E caracteres, enxuga o índice e funde tópicos irmãos, sempre com aprovação. | 1.0 |
| [me-faca-perguntas](skills/me-faca-perguntas/SKILL.md) | Entrevista implacável antes de construir: a IA faz uma pergunta por vez, não aceita resposta vaga e caça suposições, contradições e casos de borda até a sua ideia virar um plano sólido, com critério de pronto verificável. | 1.0 |

## Como instalar

Você recebeu (ou vai receber) o **instalador do MestreOS** (`instalador-mestre-os.md`): um arquivo único que monta o OS completo na sua máquina, com estas skills já embutidas. O manual em PDF ensina o passo a passo desde a instalação do Claude.

## Como atualizar

Quando sair melhoria, o aviso chega no grupo do MestreOS com um prompt pronto: é colar no seu Claude e ele atualiza sozinho. O prompt oficial de atualização está em [prompts/atualizar-skills.md](prompts/atualizar-skills.md).

Cada skill tem o campo `version:` no frontmatter. Seu agente compara a versão instalada com a deste repositório e só substitui o que estiver desatualizado.

## Histórico

Veja o [CHANGELOG.md](CHANGELOG.md).
