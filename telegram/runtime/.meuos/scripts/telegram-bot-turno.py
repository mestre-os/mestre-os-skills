#!/usr/bin/env python3
"""telegram-bot-turno.py — ganchos da janela do bot do Telegram (MestreOS, PASSO 7A). Mac e Windows.

Roda só na janela do bot (os ganchos moram em ~/.mestreos/telegram-bot.settings.json) e grava, na pasta do canal,
os marcadores que os remédios do plugin e a troca de modelo leem:
  sessao      (SessionStart)     → qual conversa e qual processo é a janela; logo depois de uma troca de modelo, a
                                   assinatura já sai com o modelo novo
  inicio      (UserPromptSubmit) → turn-start + assinatura (modelo e esforço) + lembrete curto do Telegram no contexto
  ferramenta  (PostToolUse)      → tool-activity (+ o esforço em uso)
  fim         (Stop)             → turn-end; se o pedido veio do Telegram e terminou sem reply, segura o fim UMA vez
  falha       (StopFailure)      → turn-end (erro de API, limite do plano: o turno acabou sem Stop); se foi a primeira
                                   resposta depois de uma troca de modelo, devolve o modelo de antes, uma vez só
O "digitando" fica aceso do início ao fim do TURNO, não até a 1ª resposta: o agente costuma mandar um "tô nisso" e
continuar trabalhando. Testes reais de aluna (20/10/2026): só a regra escrita não fazia o agente trocar a reação de
chegada (o lembrete a cada mensagem resolveu, como a janela da Dupla faz nas instruções de cada chamada), e uma sessão
escreveu a resposta só na tela, sem reply (a trava do fim pega esse silêncio). Fora esses textos, nunca imprime nada,
e sempre sai 0: gancho que falha não pode travar a conversa do aluno. Entrada e saída em UTF-8 (o Windows lia cp1252).
"""
import json, os, re, subprocess, sys, time, unicodedata

# Esforço pelo nome oficial, sem tradução (21/10/2026): é o id do `claude --effort`, o mesmo que a Anthropic mostra. A chave
# é o que o Claude Code grava; o valor é só o que o aluno lê. "ultracode" é interruptor (xhigh + vários agentes), não nível.
EFF = {nivel: nivel for nivel in ("low", "medium", "high", "xhigh", "max")}
CEREBRO = "🧠"   # emoji único de toda assinatura de modelo, Claude ou OpenAI (pedido do dono, 21/10/2026)
MODELO_ALIAS = {"fable": "Fable", "opus": "Opus", "sonnet": "Sonnet", "haiku": "Haiku"}
EVENTOS = {"sessao": "", "inicio": "turn-start", "ferramenta": "tool-activity", "fim": "turn-end", "falha": "turn-end"}
DO_TELEGRAM = re.compile(r'<channel source="(?:plugin:)?telegram')  # a tag que o plugin põe na mensagem que chega
TROCA = re.compile(r"^MESTREOS_TROCA_(CONCLUIDA|FALHOU)_(-?\d{1,20})$")  # 1ª mensagem da janela reaberta pela troca
# A palavra "resposta" sozinha confundiu uma sessão (escreveu na tela em vez de usar o reply): sempre "pela ferramenta reply".
LEMBRETE = ("[Telegram] Responda SEMPRE pela ferramenta reply: o que fica escrito na tela não chega ao celular. "
            "A reação de chegada (✍ no áudio, 👀 no resto) já foi automática: assim que entender a mensagem (no áudio, "
            "logo depois de ouvir), troque pela pertinente com a ferramenta react: ❤ grato · 🔥 empolga · 🙏 desculpa · "
            "👍 ok · 🤝 fechado · 🤣 graça · 😢 notícia triste · 🫡 ordem recebida. Texto pra ele copiar e mandar a outra pessoa: "
            "o text do reply começa com [[limpo]] e vai sozinho no balão. A assinatura do modelo é só do Telegram: e-mail ou "
            "qualquer outro canal nunca leva.")
FALA_DE_TROCA = re.compile(r"\b(modelo|esforco|sonnet|opus|haiku|fable|padrao)\b")
SEM_REPLY = ("Este pedido veio do Telegram e você ia encerrar sem usar a ferramenta reply: o dono não vê o que ficou na "
             "tela. Se o pedido pedia resposta, mande agora pelo reply (chat_id da tag <channel>), sem repetir o que já "
             "fez. Se era só um agradecimento ou retorno que não pede resposta, pode encerrar.")


def pasta_canal():
    """A mesma pasta que o plugin usa (TELEGRAM_STATE_DIR > CLAUDE_CONFIG_DIR > ~/.claude)."""
    if os.environ.get("TELEGRAM_STATE_DIR"):
        return os.environ["TELEGRAM_STATE_DIR"]
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(base, "channels", "telegram")


def pasta_troca():
    """Onde a troca de modelo (telegram-bot-troca.py) e o atalho meubot guardam as opções da janela."""
    return os.environ.get("MESTREOS_TELEGRAM_BOT_DIR") or os.path.join(os.path.expanduser("~"), ".mestreos", "telegram-bot")


def agora_ms():
    return int(time.time() * 1000)


def grava(pasta, nome, texto):
    """Troca atômica. No Windows o os.replace falha (PermissionError) se o plugin estiver lendo naquele instante:
    tenta de novo algumas vezes e, no fim, escreve direto (marcador velho é pior que marcador escrito sem troca)."""
    os.makedirs(pasta, exist_ok=True)
    alvo = os.path.join(pasta, nome)
    tmp = alvo + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(texto + "\n")
    for _ in range(5):
        try:
            os.replace(tmp, alvo)
            return
        except PermissionError:
            time.sleep(0.05)
    with open(alvo, "w", encoding="utf-8") as f:
        f.write(texto + "\n")
    try:
        os.remove(tmp)
    except OSError:
        pass


def ler_json(caminho):
    try:
        with open(caminho, encoding="utf-8") as f:
            o = json.load(f)
        return o if isinstance(o, dict) else {}
    except (OSError, ValueError):
        return {}


def escreve(texto):
    """O stdout do gancho entra no contexto da conversa. Bytes UTF-8: no Windows o print sairia em cp1252 e o emoji
    derrubaria o texto inteiro, calado."""
    sys.stdout.buffer.write((texto + "\n").encode("utf-8"))
    sys.stdout.flush()


def cauda(transcript, limite=1_000_000):
    """O fim da conversa (o último 1 MB basta pro turno atual e pro modelo da última resposta)."""
    try:
        with open(transcript, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - limite))
            return f.read().decode("utf-8", "ignore")
    except (OSError, TypeError):
        return ""


def linhas(dado):
    for linha in dado.splitlines():
        try:
            o = json.loads(linha)
        except ValueError:
            continue
        if isinstance(o, dict):
            yield o


def instante(iso):
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return 0.0


def nome_modelo(mid):
    """claude-opus-5-5 → Opus 5.5 · claude-sonnet-4-20250514 → Sonnet 4 · sonnet (alias da troca) → Sonnet."""
    m = re.match(r"claude-([a-z]+)-(\d+)(?:-(\d{1,2})(?!\d))?", mid or "")
    if not m:
        return MODELO_ALIAS.get(mid or "", "")
    fam, maj, mnr = m.group(1).capitalize(), m.group(2), m.group(3)
    return f"{fam} {maj}.{mnr}" if mnr else f"{fam} {maj}"


def ultimo_modelo(dado):
    """(modelo, instante) da última resposta registrada. Lê o campo da resposta, nunca o texto: o agente pode estar
    escrevendo código que cita outro modelo."""
    mid, quando = "", 0.0
    for o in linhas(dado):
        m = str((o.get("message") or {}).get("model") or "") if o.get("type") == "assistant" else ""
        if m.startswith("claude-"):
            mid, quando = m, instante(o.get("timestamp"))
    return mid, quando


def assinatura(dado, sessao, esforco_marcado=""):
    """Mesmo formato da janela da Dupla (7D): "🧠 Claude · Opus 5.5 · high". Logo depois de uma troca de modelo, a
    conversa ainda só tem respostas do modelo antigo: vale o modelo que a troca pediu (gravado no SessionStart), até a
    primeira resposta nova. Sem modelo conhecido (1º turno de conversa nova), não assina."""
    mid, quando = ultimo_modelo(dado)
    declarado = sessao.get("declarado")
    if isinstance(declarado, list) and len(declarado) == 2 and quando * 1000 < float(sessao.get("desde") or 0):
        nome, esf = nome_modelo(declarado[0] or ""), declarado[1] or ""
    else:
        nome = nome_modelo(mid)
        achados = re.findall(r'"effort"\s*:\s*"([a-z]+)"', dado)
        esf = achados[-1] if achados else ""
    esf = EFF.get(esforco_marcado or esf, "")
    if not nome:
        return ""
    return f"{CEREBRO} Claude · {nome} · {esf}" if esf else f"{CEREBRO} Claude · {nome}"


def textos_do_usuario(o):
    c = (o.get("message") or {}).get("content")
    if isinstance(c, str):
        return [c]
    return [x.get("text", "") for x in (c or []) if isinstance(x, dict) and x.get("type") == "text"]


def pedido_do_telegram(o):
    """Linha da conversa que é pedido do Telegram: "user" com a tag (janela parada) ou o anexo da fila "queued_command"
    de origem "channel" (mensagem que chegou com a janela trabalhando), ou o aviso da troca de modelo."""
    if o.get("type") == "user" and not o.get("isCompactSummary"):
        return any(DO_TELEGRAM.search(t) or TROCA.match(t.strip()) for t in textos_do_usuario(o))
    a = o.get("attachment") if o.get("type") == "attachment" else None
    if isinstance(a, dict) and a.get("type") == "queued_command" and (a.get("origin") or {}).get("kind") == "channel":
        p = a.get("prompt")
        textos = [p] if isinstance(p, str) else [x.get("text", "") for x in (p or []) if isinstance(x, dict)]
        return any(DO_TELEGRAM.search(t) for t in textos)
    return False


def telegram_sem_reply(dado):
    """True se o último pedido que veio do Telegram não teve reply nem edit_message depois."""
    pendente = False
    for o in linhas(dado):
        if pedido_do_telegram(o):
            pendente = True
        elif o.get("type") == "assistant" and pendente:
            for x in (o.get("message") or {}).get("content") or []:
                nome = str(x.get("name", "")) if isinstance(x, dict) and x.get("type") == "tool_use" else ""
                if "telegram" in nome and nome.endswith(("__reply", "__edit_message")):
                    pendente = False
    return pendente


def processo():
    """O processo do Claude Code desta janela (o Claude Code passa CLAUDE_PID aos ganchos; o pai é ele mesmo)."""
    return os.environ.get("CLAUDE_PID") or str(os.getppid())


def marca_esforco(entrada, pasta):
    """O esforço só aparece no meio do turno (variável CLAUDE_EFFORT ou campo effort do Stop): guarda pro próximo."""
    nivel = (entrada.get("effort") or {}).get("level", "") if isinstance(entrada.get("effort"), dict) else ""
    nivel = os.environ.get("CLAUDE_EFFORT", "") or nivel
    if nivel in EFF:
        grava(pasta, "esforco.json", json.dumps({"nivel": nivel, "pid": processo()}))


def esforco_marcado(pasta, sessao):
    e = ler_json(os.path.join(pasta, "esforco.json"))
    return e.get("nivel", "") if e.get("pid") == sessao.get("pid") else ""


def descreve(par):
    m, e = (list(par) + [None, None])[:2] if isinstance(par, list) else (None, None)
    return "%s · esforço %s" % (MODELO_ALIAS.get(m or "", "modelo padrão da conta"), EFF.get(e or "", "padrão"))


def evento_sessao(entrada, pasta):
    """Registra a janela (conversa, processo, transcript). Se ela acabou de ser reaberta pela troca de modelo, marca a
    troca como entregue e já deixa a assinatura com o modelo pedido."""
    s = {"sid": entrada.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID", ""), "pid": processo(),
         "transcript": entrada.get("transcript_path", ""), "desde": agora_ms()}
    caminho = os.path.join(pasta_troca(), "troca.json")
    t = ler_json(caminho)
    if (t.get("estado") in ("reiniciando", "revertendo") and t.get("sid") == s["sid"]
            and time.time() - float(t.get("t") or 0) < 15 * 60):
        s["declarado"] = t.get("para") if t["estado"] == "reiniciando" else t.get("de")
        t["estado"] = "voltou" if t["estado"] == "reiniciando" else "voltou-antes"
        t["pid"] = s["pid"]
        grava(pasta_troca(), "troca.json", json.dumps(t, ensure_ascii=False))
        grava(pasta, "assinatura", assinatura("", s))
    grava(pasta, "sessao.json", json.dumps(s, ensure_ascii=False))


def aviso_troca(tipo, chat):
    t = ler_json(os.path.join(pasta_troca(), "troca.json"))
    if tipo == "CONCLUIDA":
        para = descreve(t.get("para"))
        return (f"[MestreOS] A janela do bot acabou de reabrir com o modelo novo ({para}), na mesma conversa. Mande agora "
                f"pelo reply, chat_id {chat}, esta linha: \"✅ Pronto, agora estou no {para}.\" Se alguma mensagem do dono "
                f"nesta conversa ficou sem resposta (chegou enquanto a janela fechava), responda também.")
    erro = str(t.get("erro") or "erro do Claude")[:60]
    return (f"[MestreOS] A troca pra {descreve(t.get('para'))} não funcionou: a primeira resposta falhou ({erro}). A janela "
            f"voltou pro {descreve(t.get('de'))}. Mande agora pelo reply, chat_id {chat}, só esta linha: \"⚠️ Não consegui "
            f"trocar pra {descreve(t.get('para'))} ({erro}). Continuo no {descreve(t.get('de'))}.\" e encerre o turno.")


def evento_inicio(entrada, pasta):
    s = ler_json(os.path.join(pasta, "sessao.json"))
    if s.get("pid") != processo():  # janela aberta antes dos ganchos existirem: começa o registro agora
        s = {"pid": processo(), "desde": 0}
    s["sid"] = entrada.get("session_id") or s.get("sid", "")
    s["transcript"] = entrada.get("transcript_path") or s.get("transcript", "")
    grava(pasta, "sessao.json", json.dumps(s, ensure_ascii=False))
    marca_esforco(entrada, pasta)   # hoje o esforço não vem no início do turno; se um dia vier, vale na hora
    grava(pasta, "assinatura", assinatura(cauda(s["transcript"], 400_000), s, esforco_marcado(pasta, s)))
    prompt = str(entrada.get("prompt", ""))
    troca = TROCA.match(prompt.strip())
    if troca:
        escreve(aviso_troca(troca.group(1), troca.group(2)))
    elif DO_TELEGRAM.search(prompt):   # só no pedido que veio do Telegram (o stdout entra no contexto)
        escreve(LEMBRETE + dica_troca(prompt))


def dica_troca(prompt):
    """O comando exato da troca de modelo (o Python e o caminho certos desta máquina), só quando a mensagem fala de
    modelo ou esforço, ou é áudio (o agente ainda vai ouvir)."""
    t = "".join(c for c in unicodedata.normalize("NFKD", prompt.lower()) if not unicodedata.combining(c))
    if not (FALA_DE_TROCA.search(t) or re.search(r'attachment_kind="(?:voice|audio)"', prompt)):
        return ""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram-bot-troca.py")
    return (f' Se for pedido de troca de modelo ou esforço, rode: "{sys.executable}" "{script}" trocar --pedido '
            f'"<a mensagem dele, literal>" (áudio: + --modelo e --esforco com o que você entendeu) e siga a saída.')


def lanca_troca(*args):
    """Roda telegram-bot-troca.py desacoplado (ele fecha esta janela; o gancho não pode esperar por isso)."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram-bot-troca.py")
    if not os.path.exists(script):
        return
    exe = sys.executable
    if os.name == "nt":
        w = os.path.join(os.path.dirname(exe), "pythonw.exe")
        exe = w if os.path.exists(w) else exe
        for fl in (0x01000208 | 0x08000000, 0x00000208 | 0x08000000):  # desacoplado, sem janela; tenta sair do job
            try:
                subprocess.Popen([exe, script] + list(args), creationflags=fl, close_fds=True, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except OSError:
                continue
        return
    subprocess.Popen([exe, script] + list(args), start_new_session=True, close_fds=True, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def marca_fim(entrada, pasta):
    """Fim do turno: antes, quantas tarefas ficaram rodando em segundo plano (o Stop conta), pra troca de modelo não
    fechar a janela em cima delas; depois, o turn-end (mesmo instante nos dois)."""
    agora = agora_ms()
    bt = entrada.get("background_tasks")
    n = len(bt) if isinstance(bt, (list, dict)) else (bt if isinstance(bt, int) else 0)
    grava(pasta, "segundo-plano.json", json.dumps({"n": n, "ts": agora}))
    grava(pasta, "turn-end", str(agora))


def evento_fim(entrada, pasta, falhou):
    marca_esforco(entrada, pasta)
    t = ler_json(os.path.join(pasta_troca(), "troca.json"))
    da_troca = t.get("pid") == processo() and t.get("estado") in ("voltou", "voltou-antes")
    if falhou:
        marca_fim(entrada, pasta)   # erro de API também encerra o turno
        if da_troca:   # o modelo novo falhou na 1ª resposta: volta pro de antes; se nem o de antes respondeu, desiste
            lanca_troca("reverter" if t["estado"] == "voltou" else "desistir", str(entrada.get("error") or "")[:40])
        return
    if not entrada.get("stop_hook_active") and telegram_sem_reply(cauda(entrada.get("transcript_path"))):
        # segura o fim: o turno CONTINUA (o agente vai mandar o reply que faltou), então não é fim de turno ainda
        escreve(json.dumps({"decision": "block", "reason": SEM_REPLY}, ensure_ascii=False))
        return
    if da_troca:
        t["estado"] = "ok" if t["estado"] == "voltou" else "revertido"
        grava(pasta_troca(), "troca.json", json.dumps(t, ensure_ascii=False))
    marca_fim(entrada, pasta)


def main():
    evento = sys.argv[1] if len(sys.argv) > 1 else ""
    if evento not in EVENTOS:
        return 0
    try:
        entrada = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
    except (ValueError, OSError, AttributeError):
        entrada = {}
    if not isinstance(entrada, dict):
        entrada = {}
    pasta = pasta_canal()
    if evento in ("inicio", "ferramenta"):   # o fim (Stop/StopFailure) grava o seu marcador depois de decidir
        grava(pasta, EVENTOS[evento], str(agora_ms()))
    if evento == "sessao":
        evento_sessao(entrada, pasta)
    elif evento == "inicio":
        evento_inicio(entrada, pasta)
    elif evento == "ferramenta":
        marca_esforco(entrada, pasta)
    else:
        evento_fim(entrada, pasta, evento == "falha")
    return 0


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
