# Prompt oficial — instalar o Pacote Marketing do MestreOS

> Copie tudo abaixo da linha e cole no seu Claude (ou agente equivalente). Ele instala o pacote sozinho.

---

Você é o agente do meu OS pessoal (MestreOS ou similar, com skills em arquivos markdown). Quero instalar o Pacote Marketing oficial do MestreOS: 34 skills de marketing, growth e SEO. Faça assim:

1) LOCALIZE minha pasta de skills (procure por `.meuos/skills/`, `skills/`, ou onde ficam meus arquivos de skill). Não invente caminho.

2) BAIXE a lista de skills do pacote direto do repositório oficial. Para cada slug da lista abaixo, o arquivo fica em `https://raw.githubusercontent.com/mestre-os/mestre-os-skills/main/skills/{slug}/SKILL.md`:

ab-testing, ads, ad-creative, ai-seo, analytics, churn-prevention, cold-email, competitor-profiling, competitors, content-strategy, copy-editing, copywriting, cro, customer-research, emails, free-tools, launch, lead-magnets, marketing-ideas, marketing-plan, marketing-psychology, offers, onboarding, paywalls, popups, pricing, product-marketing, programmatic-seo, referrals, schema, seo-audit, signup, site-architecture, social

3) Para cada skill: se eu não tiver, crie em `{minha pasta de skills}/{slug}/SKILL.md` (ou `{slug}.md`, seguindo o padrão que eu já uso). Se eu já tiver, compare o campo `version:` do frontmatter e só substitua se a do repositório for mais nova.

4) Ao final, me pergunte qual dos meus contextos é a minha marca/produto principal e crie o arquivo `{contexto}/marketing.md` usando a skill `product-marketing` (é o brief que todas as outras skills do pacote consultam antes de trabalhar). Se eu ainda não quiser, tudo bem: as skills perguntam na hora do uso.

5) Me mostre o resumo: quantas skills instalou, quantas atualizou, quantas já estavam em dia. E um exemplo de uso: "fala 'melhorar meu cadastro' que a skill signup assume".

Não mexa em nada fora da pasta de skills e do arquivo de marketing do contexto que eu escolher. Ambíguo? Pergunta antes.
