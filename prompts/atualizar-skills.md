# Prompt oficial de atualização — MestreOS

> Copie tudo abaixo da linha e cole no seu Claude (ou agente equivalente). Ele atualiza suas skills sozinho.

---

Você é o agente do meu OS pessoal (com skills em arquivos markdown — pode estar nomeado MeuOS, SeuOS, MestreOS ou outro nome, é o mesmo sistema, não importa como você chama ele hoje). Quero atualizar minhas skills para a versão mais recente do repositório oficial do MestreOS. Isso NÃO é pra renomear meu sistema nem mexer na marca dele: é só atualizar as skills de conteúdo. Faça assim:

1) LOCALIZE minha pasta de skills (procure por `.meuos/skills/`, `skills/`, ou onde ficam meus arquivos de skill).

2) BAIXE o conteúdo destes links (raw do GitHub) e compare com o que tenho instalado:
- Salvar: https://raw.githubusercontent.com/mestre-os/mestre-os-skills/main/skills/salvar/SKILL.md
- Ligar Loop: https://raw.githubusercontent.com/mestre-os/mestre-os-skills/main/skills/ligar-loop/SKILL.md
- Otimizar OS: https://raw.githubusercontent.com/mestre-os/mestre-os-skills/main/skills/otimizar-os/SKILL.md
- Otimizar Custo: https://raw.githubusercontent.com/mestre-os/mestre-os-skills/main/skills/otimizar-custo/SKILL.md
- Me Faça Perguntas: https://raw.githubusercontent.com/mestre-os/mestre-os-skills/main/skills/me-faca-perguntas/SKILL.md
- Preparar OS Dual: https://raw.githubusercontent.com/mestre-os/mestre-os-skills/main/skills/preparar-os-dual/SKILL.md

3) Para cada skill: se eu não tiver, crie. Se eu tiver versão mais antiga (campo `version:` no frontmatter), substitua preservando qualquer personalização minha que não conflite (me mostre antes o que vai mudar).

4) Se eu ainda tiver as skills antigas "conferir-entrega" e "fim-do-dia" (ou "engenharia-de-loop" e "loop-autonomo") como skills completas: converta em stubs de redirecionamento. O frontmatter e os gatilhos antigos ficam; o corpo passa a dizer só "fundida em salvar.md (ou ligar-loop.md), executar o passo a passo de lá".

5) REAPONTE os gatilhos no meu arquivo de regras raiz (claude.md, e AGENTS.md se existir): as frases antigas (fim do dia, conferir entrega, terminei, liga o loop) caem nas skills novas.

6) DEPOIS de atualizar, rode a limpeza de legado UMA vez: procure no meu documento mestre de cada contexto por linhas de tarefa concluída riscadas (`~~[x] tarefa~~ -> ver changelog`). Elas são resíduo da versão antiga da rotina de fechamento. Colapse todas em um único ponteiro, me mostrando antes e pedindo o meu ok:
> `**Tarefas concluídas não ficam listadas aqui.** Histórico completo, com data, no changelog.`

7) No fim, me mostre um resumo: skill por skill, versão que tinha e versão que ficou, e quantas linhas riscadas saíram de cada mestre. E teste: confirme que falar "fim do dia" cai na salvar.

Não invente caminhos: descubra a estrutura real do meu OS antes de gravar. Não mexa em nada fora das skills e do arquivo de regras. Ambíguo? Pergunta antes.
