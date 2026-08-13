# MestreOS — Skills oficiais

Skills do **MestreOS**: o sistema operacional pessoal que transforma o seu agente de IA (Claude Code e similares) num parceiro que conhece você, seus projetos e suas regras. Este repositório é a fonte oficial das skills. Cada atualização chega aqui primeiro, versionada.

## Núcleo (vem no instalador)

| Skill | O que faz | Versão |
|---|---|---|
| [salvar](skills/salvar/SKILL.md) | Checkpoint de soberania de contexto: confere a entrega, sintetiza a sessão e grava um checkpoint durável no SEU formato. Avalia os arquivos antes de escrever, com gate anti-duplicação e anti-verborragia. Rode no amarelo (🟡) e sempre antes de fechar uma sessão cheia (🔴). | 1.1 |
| [ligar-loop](skills/ligar-loop/SKILL.md) | Engenharia de loop em dois tempos: desenha o Plano de Loop, você aprova, e liga o trabalho autônomo com travas de segurança (critério de parada, teto de iterações, rollback). | 1.0 |
| [otimizar-os](skills/otimizar-os/SKILL.md) | Organiza e compacta os arquivos do OS. Mostra o custo fixo por sessão em tokens, confere a integridade dos links entre documentos (link quebrado, arquivo órfão) e para quando não há mais nada útil a reduzir. | 1.1 |
| [otimizar-custo](skills/otimizar-custo/SKILL.md) | Higiene da memória persistente do agente. Mede linhas E caracteres, enxuga o índice e funde tópicos irmãos, sempre com aprovação. | 1.1 |
| [me-faca-perguntas](skills/me-faca-perguntas/SKILL.md) | Entrevista implacável antes de construir: uma pergunta por vez, sem aceitar resposta vaga, caçando suposições e casos de borda até a ideia virar plano com critério de pronto verificável. | 1.0 |
| [preparar-os-dual](skills/preparar-os-dual/SKILL.md) | Deixa o OS pronto para vários agentes ao mesmo tempo (Claude + ChatGPT/Codex + Cursor): garante um AGENTS.md espelhado ao lado de cada claude.md, na raiz e em todos os contextos. | 1.0 |

## Pacote Marketing (34 skills, opcional)

Adaptado de material open source consagrado da comunidade (MIT, ver [LICENSES.md](LICENSES.md)), com gatilhos em português e integração com a estrutura de contextos do MestreOS: todas as skills leem o brief da marca em `{contexto}/marketing.md` antes de perguntar qualquer coisa.

Instalação: prompt pronto em [prompts/instalar-pacote-marketing.md](prompts/instalar-pacote-marketing.md).

**Fundação** — [product-marketing](skills/product-marketing/SKILL.md) · [customer-research](skills/customer-research/SKILL.md) · [marketing-plan](skills/marketing-plan/SKILL.md) · [marketing-psychology](skills/marketing-psychology/SKILL.md)

**Conversão (CRO)** — [cro](skills/cro/SKILL.md) · [signup](skills/signup/SKILL.md) · [onboarding](skills/onboarding/SKILL.md) · [paywalls](skills/paywalls/SKILL.md) · [popups](skills/popups/SKILL.md) · [pricing](skills/pricing/SKILL.md) · [offers](skills/offers/SKILL.md) · [ab-testing](skills/ab-testing/SKILL.md) · [churn-prevention](skills/churn-prevention/SKILL.md)

**Aquisição** — [ads](skills/ads/SKILL.md) · [ad-creative](skills/ad-creative/SKILL.md) · [cold-email](skills/cold-email/SKILL.md) · [emails](skills/emails/SKILL.md) · [social](skills/social/SKILL.md) · [launch](skills/launch/SKILL.md) · [referrals](skills/referrals/SKILL.md) · [free-tools](skills/free-tools/SKILL.md)

**SEO e IA** — [seo-audit](skills/seo-audit/SKILL.md) · [ai-seo](skills/ai-seo/SKILL.md) · [programmatic-seo](skills/programmatic-seo/SKILL.md) · [schema](skills/schema/SKILL.md) · [site-architecture](skills/site-architecture/SKILL.md) · [lead-magnets](skills/lead-magnets/SKILL.md)

**Conteúdo e análise** — [copywriting](skills/copywriting/SKILL.md) · [copy-editing](skills/copy-editing/SKILL.md) · [content-strategy](skills/content-strategy/SKILL.md) · [competitors](skills/competitors/SKILL.md) · [competitor-profiling](skills/competitor-profiling/SKILL.md) · [analytics](skills/analytics/SKILL.md) · [marketing-ideas](skills/marketing-ideas/SKILL.md)

## Como instalar

Você recebeu (ou vai receber) o **instalador do MestreOS**: um arquivo único que monta o OS completo na sua máquina, com as skills do núcleo já embutidas. O manual em PDF ensina o passo a passo desde a instalação do Claude. O Pacote Marketing é opcional e instala com o prompt em [prompts/instalar-pacote-marketing.md](prompts/instalar-pacote-marketing.md).

## Como atualizar

Quando sair melhoria, o aviso chega no grupo do MestreOS com um prompt pronto: é colar no seu Claude e ele atualiza sozinho. O prompt oficial de atualização está em [prompts/atualizar-skills.md](prompts/atualizar-skills.md).

Cada skill tem o campo `version:` no frontmatter. Seu agente compara a versão instalada com a deste repositório e só substitui o que estiver desatualizado.

## Histórico

Veja o [CHANGELOG.md](CHANGELOG.md).
