#!/usr/bin/env python3
"""cerebro.py — "Dupla" do MestreOS: Claude Code + Codex no MESMO bot de Telegram (PASSO 7C do instalador).

Gancho UserPromptSubmit do Claude Code. O bot é um só (o plugin oficial, na "janela do bot"); quem responde é o
cérebro: anthropic (a sessão Claude) ou openai:<modelo> (Codex rodando escondido nesta mesma pasta do OS).
Frases no Telegram: "troca pro Codex" (= Sol) · "troca pro Sol / Terra / Luna / Astra" · "qual cérebro tá ligado?" ·
"volta pro Claude". MODO SEGURO (padrão pra todo mundo): o Codex roda dentro do sandbox e quem entrega a resposta
e os arquivos novos é este gancho; áudio vai sempre pro Claude. Continuidade nos dois sentidos (últimas trocas ao ir,
resumo ao voltar) e vigia da janela do Codex (renova a conversa com resumo perto do limite).
Mac e Windows (Python 3, sem dependências). Token do bot: TELEGRAM_BOT_TOKEN ou ~/.claude/channels/telegram/.env.
Destino: TELEGRAM_CHAT_ID ou .meuos/scripts/telegram-send.env. Self-test: python3 cerebro.py --teste
"""
import json, os, re, sys, subprocess, time, unicodedata, glob, shutil, datetime, hashlib
from telegram_runtime import Queue, activity_run
# Windows sem console (hook/Agendador) usa cp1252 e estoura em emoji/acento → força UTF-8 (no Mac não muda nada)
for _s in (sys.stdout, sys.stderr, sys.stdin):
    if hasattr(_s, "reconfigure"):
        try: _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception: pass

H = os.path.expanduser("~")
AQUI = os.path.dirname(os.path.abspath(__file__))
OS_DIR = os.environ.get("MESTREOS_DIR") or os.path.dirname(os.path.dirname(AQUI))          # <OS>/.meuos/hooks → <OS>
STATE = os.environ.get("MESTREOS_CEREBRO_STATE") or os.path.join(H, ".mestreos", "telegram", hashlib.sha256(os.path.normcase(OS_DIR).encode()).hexdigest()[:16])
TGDIR = os.environ.get("TELEGRAM_STATE_DIR") or os.path.join(H, ".claude", "channels", "telegram")
PROJ_SLUG = "-" + re.sub(r"[^A-Za-z0-9]", "-", OS_DIR.lstrip("/")) if not OS_DIR[1:3] == ":\\" else "-" + re.sub(r"[^A-Za-z0-9]", "-", OS_DIR)
MEMDIR = os.environ.get("MESTREOS_MEMORIA_DIR") or os.path.join(H, ".claude", "projects", PROJ_SLUG, "memory")
CODEX = os.environ.get("MESTREOS_CODEX_BIN") or shutil.which("codex") or shutil.which("codex.cmd") or "/Applications/ChatGPT.app/Contents/Resources/codex"
DRY = bool(os.environ.get("MESTREOS_CEREBRO_DRYRUN")); FAKE = os.environ.get("MESTREOS_CEREBRO_FAKE_CODEX")
JOB = None; DELIVERED = 0; DELIVERY_FAILED = False
LOGF = os.path.join(STATE, "cerebro.log"); SF = os.path.join(STATE, "cerebro.json")
TIMEOUT = int(os.environ.get("MESTREOS_CEREBRO_TIMEOUT", "900"))
# Renovação da conversa por tokens fica DESLIGADA (0): o `input_tokens` do turn.completed soma todas as chamadas do turno
# (deu 437k num turno só, 10/09 00:21) e disparava renovação à toa. O Codex compacta sozinho; o hook PreCompact dele grava o checkpoint.
ROLLOVER = int(os.environ.get("MESTREOS_CEREBRO_ROLLOVER", "0"))
IMG = (".png", ".jpg", ".jpeg", ".webp", ".gif"); AUD = (".oga", ".ogg", ".mp3", ".m4a", ".wav", ".opus")
MODELOS = {"sol": "gpt-5.6-sol", "terra": "gpt-5.6-terra", "luna": "gpt-5.6-luna", "lua": "gpt-5.6-luna", "astra": "gpt-6-astra",
           "codex": "gpt-5.6-sol", "openai": "gpt-5.6-sol", "chatgpt": "gpt-5.6-sol", "gpt": "gpt-5.6-sol"}
EMOJI = {"sol": "☀️", "terra": "🌍", "luna": "🌙", "astra": "✨"}

def log(m):
    try:
        os.makedirs(STATE, exist_ok=True)
        with open(LOGF, "a", encoding="utf-8") as f: f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {m}\n")
    except Exception: pass

def norm(s):
    s = unicodedata.normalize("NFD", s or "").lower(); return "".join(c for c in s if unicodedata.category(c) != "Mn")

def nome(modelo):
    m = re.search(r"-(sol|terra|luna|astra)\b", modelo or ""); return m.group(1).capitalize() if m else (modelo or "OpenAI")
def assinatura(modelo):
    m = re.search(r"-(sol|terra|luna|astra)\b", modelo or ""); return f"{EMOJI.get(m.group(1), '🟢') if m else '🟢'} {nome(modelo)}"

def load():
    try: return json.load(open(SF, encoding="utf-8"))
    except Exception: return {"empresa": "anthropic", "modelo": None, "thread": None, "desde": None, "tokens": 0}
def save(st):
    os.makedirs(STATE, exist_ok=True); tmp = SF + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmp, SF)

# ---------- Telegram (Bot API direta) ----------
def token():
    # Mesmo Cofre dos robôs: Keychain no Mac, DPAPI no Windows; sem leitura no chat.
    sys.path.insert(0, os.path.join(OS_DIR, ".meuos", "scripts"))
    try:
        from telegram_send import token as read_token
        return read_token()
    except ImportError:
        return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


def chat_id_dono():
    c = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if c: return c
    try:
        for ln in open(os.path.join(OS_DIR, ".meuos", "scripts", "telegram-send.env"), encoding="utf-8"):
            if ln.startswith("TELEGRAM_CHAT_ID="): return ln.split("=", 1)[1].strip()
    except Exception: pass
    try:
        a = json.load(open(os.path.join(TGDIR, "access.json"))); return str((a.get("allowFrom") or [""])[0])
    except Exception: return ""

def tg(method, fields=None, files=None):
    if DRY:
        global DELIVERED, DELIVERY_FAILED
        if method != "sendChatAction": DELIVERED += 1
        print(f"DRY tg {method} {json.dumps(fields or {}, ensure_ascii=False)[:200]} files={list((files or {}).values())}", file=sys.stderr); return True
    tok = token()
    if not tok: log("sem token do bot"); return False
    cmd = ["curl", "-s", "--max-time", "60", "-K", "-"]
    for k, v in (fields or {}).items(): cmd += (["-F", f"{k}={v}"] if files else ["--data-urlencode", f"{k}={v}"])
    for k, p in (files or {}).items(): cmd += ["-F", f"{k}=@{p}"]
    try:
        r = subprocess.run(cmd, input=f'url = "https://api.telegram.org/bot{tok}/{method}"\n', capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
        result = json.loads(r.stdout)
        ok = result.get("ok") is True
        if method in ("sendMessage", "sendPhoto", "sendDocument"):
            mid = (result.get("result") or {}).get("message_id")
            ok = ok and mid is not None
            if ok:
                if JOB: Queue(STATE).receipt(JOB, mid, method)
                DELIVERED += 1
            else: DELIVERY_FAILED = True
        if not ok: log(f"tg {method} falhou: HTTP/API sem confirmação")
        return ok
    except Exception:
        DELIVERY_FAILED = True; log(f"tg {method}: entrega não confirmada"); return False

def send_text(chat, text):
    text = (text or "").strip() or "(sem texto)"; ok = True
    while text:
        chunk, text = text[:3900], text[3900:]
        ok = tg("sendMessage", {"chat_id": chat, "text": chunk, "disable_web_page_preview": "true"}) and ok
    return ok

def send_file(chat, path):
    if path.lower().endswith(IMG) and os.path.getsize(path) < 10 * 1024 * 1024: return tg("sendPhoto", {"chat_id": chat}, {"photo": path})
    return tg("sendDocument", {"chat_id": chat}, {"document": path})

def block(reason):
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False)); sys.exit(0)
def add_context(text):
    if JOB:
        handoff = os.path.join(STATE, "claude-handoff.json")
        with open(handoff, "w", encoding="utf-8") as f: json.dump(text, f, ensure_ascii=False)
        send_text(chat_id_dono(), "🟣 Voltei pro Claude. Seu contexto ficou guardado; pode mandar a próxima mensagem.")
        block("[contexto preservado para a próxima mensagem do Claude]")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}}, ensure_ascii=False)); sys.exit(0)

# ---------- continuidade ----------
def ultimas_trocas(n=16):
    try:
        proj = os.path.dirname(MEMDIR)
        cands = sorted(glob.glob(os.path.join(proj, "*.jsonl")), key=os.path.getmtime)[-3:]
        out = []
        for c in cands:
            for ln in open(c, "rb").read()[-1_000_000:].decode("utf-8", "ignore").splitlines():
                if '"queue-operation"' in ln and '"enqueue"' in ln:
                    m = re.search(r'message_id="(\d+)"[^>]*>(.*?)</channel>', ln, re.S)
                    if m: out.append(("Dono", m.group(2).replace("\\n", " ").strip()[:400]))
                elif "telegram__reply" in ln:
                    m = re.search(r'\\"text\\":\\"(.*?)\\"(?:,|})', ln)
                    if m: out.append(("Agente", m.group(1).replace("\\\\n", " ").replace('\\\\"', '"').strip()[:400]))
        return "\n".join(f"- {q}: {t}" for q, t in out[-n:])
    except Exception as e: log(f"ultimas_trocas: {e!r}"); return ""

# ---------- Codex (modo seguro: sandbox, gancho entrega) ----------
def prefixo(st, primeira):
    hoje = datetime.date.today().isoformat(); out_dir = os.path.join(OS_DIR, "outputs", "imagens", hoje)
    p = (f"[Modo Telegram · cérebro OpenAI. Você é o agente do dono deste OS (leia AGENTS.md desta pasta: mesma personalidade, regras e skills). "
         f"A mensagem abaixo chegou pelo Telegram dele. Responda em português, curto, texto puro (sem markdown pesado): o que você escrever como "
         f"resposta final é o que ele vai receber no celular. Não assine. Memória do agente: {MEMDIR} (leia MEMORY.md e os arquivos relevantes; "
         f"grave feedback/decisão lá também). Fotos que chegam ficam em {TGDIR}/inbox/. Imagem gerada/restaurada: use a ferramenta de imagem "
         f"(gpt-image-2) e salve em {out_dir}/ — o que aparecer lá eu envio pro celular dele. Skill `salvar` e os outros ritos do OS valem aqui igual. "
         f"Você NÃO consegue trocar de cérebro: se ele pedir pra voltar pro Claude, responda só: 'pra voltar, manda exatamente: volta pro Claude'. "
         f"Seja rápido: leia MEMORY.md e só os arquivos que a pergunta pedir; não varra pastas nem skills sem necessidade.]\n")
    if primeira:
        tr = ultimas_trocas()
        if tr: p += f"\n[Contexto: você acabou de assumir a conversa; últimas trocas pelo Telegram (\"Agente\" era a sessão Claude):\n{tr}\n]\n"
        if st.get("resumo_anterior"): p += f"\n[Resumo da sua conversa anterior (janela renovada): {st['resumo_anterior']}]\n"
    return p + "\n"

def codex_command():
    if str(CODEX).lower().endswith((".cmd", ".bat")):
        # Não passar prompt do Telegram por cmd.exe (metacaracteres virariam comandos).
        js = os.path.join(os.path.dirname(CODEX), "node_modules", "@openai", "codex", "bin", "codex.js")
        node = shutil.which("node")
        if not node or not os.path.isfile(js):
            raise RuntimeError("Instalação Codex/npm não reconhecida; conferir executável nativo")
        return [node, js]
    return [CODEX]

def run_codex(st, prompt, imagens):
    outf = os.path.join(STATE, "ultima.txt"); hoje = datetime.date.today().isoformat()
    out_dir = os.path.join(OS_DIR, "outputs", "imagens", hoje); os.makedirs(out_dir, exist_ok=True)
    antes = set(glob.glob(os.path.join(out_dir, "*")))
    try: os.remove(outf)
    except FileNotFoundError: pass
    t0 = time.time()
    if FAKE: return True, FAKE, st.get("thread") or "fake-thread", 1234, round(time.time() - t0, 1), []
    roots = 'sandbox_workspace_write.writable_roots=["' + MEMDIR.replace("\\", "/") + '","' + os.path.join(OS_DIR, "outputs").replace("\\", "/") + '"]'
    comum = ["--skip-git-repo-check", "-m", st["modelo"], "-c", roots, "-c", "sandbox_workspace_write.network_access=true", "-o", outf]
    if st.get("thread"):
        cmd = codex_command() + ["exec", "resume", "--json", "-c", 'sandbox_mode="workspace-write"'] + comum
        for i in imagens: cmd += ["-i", i]
        cmd += [st["thread"], prompt]
    else:
        cmd = codex_command() + ["exec", "--json", "-C", OS_DIR, "-s", "workspace-write"] + comum
        for i in imagens: cmd += ["-i", i]
        cmd += [prompt]
    # "digitando…" no celular enquanto o Codex pensa (o Telegram apaga em 5 s; repetir a cada 4 s)
    import threading
    parar = threading.Event()
    def batimento():
        while not parar.is_set():
            tg("sendChatAction", {"chat_id": chat_id_dono(), "action": "typing"}); parar.wait(4)
    th = threading.Thread(target=batimento, daemon=True); th.start()
    try: r = activity_run(cmd, cwd=OS_DIR, timeout=TIMEOUT)
    except subprocess.TimeoutExpired: parar.set(); return False, f"ficou sem atividade por {TIMEOUT // 60} min; resultado precisa de conferência", st.get("thread"), 0, round(time.time() - t0, 1), []
    finally: parar.set()
    thread, tokens = st.get("thread"), 0
    for ln in (r.stdout or "").splitlines():
        try: d = json.loads(ln)
        except Exception: continue
        if isinstance(d, dict) and d.get("type") == "thread.started" and d.get("thread_id"): thread = d["thread_id"]
        if isinstance(d, dict) and d.get("type") == "turn.completed": tokens = int((d.get("usage") or {}).get("input_tokens") or 0)
    resp = ""
    try:
        with open(outf, encoding="utf-8") as f: resp = f.read().strip()
    except Exception: pass
    if r.returncode != 0 or not resp:
        erro = ""
        for ln in (r.stderr or "").splitlines() + (r.stdout or "").splitlines():
            m = re.search(r'"message":"([^"]{0,160})"', ln)
            if m and "chronicle" not in m.group(1): erro = m.group(1); break
        return False, erro or f"código {r.returncode}", thread, tokens, round(time.time() - t0, 1), []
    novos = [n for n in sorted(set(glob.glob(os.path.join(out_dir, "*"))) - antes, key=os.path.getmtime) if os.path.isfile(n)]
    return True, resp, thread, tokens, round(time.time() - t0, 1), novos

def resumo_thread(st, motivo):
    if FAKE or not st.get("thread"): return st.get("resumo_anterior") or "(sem conversa registrada)"
    outf = os.path.join(STATE, "resumo.txt")
    p = f"[{motivo}] Resuma em até 12 linhas o que rolou nesta conversa pelo Telegram: assuntos, decisões, pendências, arquivos, o que o dono esperava. Texto puro."
    try:
        subprocess.run(codex_command() + ["exec", "resume", "--json", "-c", 'sandbox_mode="workspace-write"', "--skip-git-repo-check", "-m", st["modelo"], "-o", outf, st["thread"], p], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, cwd=OS_DIR)
        return open(outf, encoding="utf-8").read().strip()[:3000]
    except Exception as e: log(f"resumo: {e!r}"); return "(não consegui resumir)"

# ---------- comandos ----------
# Ditado (Voice Ink) erra nome próprio: "Claudio", "cloud", "clode", "códex", "codecs"… → aceitar as variações.
RE_TROCA = re.compile(r"\b(troca|trocar|muda|mudar|liga|ligar|ativa|ativar|usa|usar|passa|passar|bota|botar|coloca|colocar|volta|voltar|volte)\b(?:\s+(?:pro|pra|para|o|a|no|na|de|do|pelo|pela|modelo|cerebro|ai))*\s+([a-z][a-z0-9.-]*)\b")  # "volta pro Codex" também é troca
RE_VOLTA = re.compile(r"\b(volta|voltar|volte|retorna|retornar|devolve|devolver)\b.*?\b(claud\w*|cloud\w*|clode|anthropic|antropic|opus|fable|sonnet|haiku)\b")
def alvo_modelo(palavra):
    """normaliza o que o ditado escreveu: codecs/códex/codes → codex; claud* fica fora (é volta)."""
    p = palavra.lower()
    if p in MODELOS: return p
    if p.startswith("cod"): return "codex"
    if p.startswith("astr"): return "astra"
    if p.startswith("terr"): return "terra"
    if p.startswith("lun") or p == "lua": return "luna"
    if p.startswith("sol"): return "sol"
    if p.startswith("open") or p.startswith("chat") or p.startswith("gpt"): return "openai"
    return p
RE_STATUS = re.compile(r"\b(qual|que|quem)\b.*\b(cerebro|modelo|respondendo|ligado|ativo)\b")

def status_txt(st):
    if st.get("empresa") == "openai":
        return f"🧠 Cérebro: OpenAI · {nome(st['modelo'])} ({st['modelo']}) desde {st.get('desde', '?')} · janela ~{int(st.get('tokens') or 0)//1000}k/272k. \"volta pro Claude\" quando quiser."
    return "🧠 Cérebro: Anthropic (a janela do bot, Claude). \"troca pro Codex\" (Sol) ou Terra, Luna, Astra pra falar com a OpenAI."

def main(d=None):
    if d is None:
        try: d = json.load(sys.stdin)
        except Exception: return 0
    prompt = d.get("prompt") or ""
    m = re.search(r'<channel source="(?:plugin:)?telegram[^>]*chat_id="(\d+)"[^>]*message_id="(\d+)"[^>]*>(.*?)</channel>', prompt, re.S)
    if not m: return 0
    chat, mid, corpo = m.group(1), m.group(2), m.group(3).strip()
    dono = chat_id_dono()
    if not dono or chat != dono: return 0
    anexos = [p for p in re.findall(r"(/[^\s\"'<>]+/channels/telegram/inbox/[^\s\"'<>]+|[A-Za-z]:\\[^\s\"'<>]+channels\\telegram\\inbox\\[^\s\"'<>]+)", prompt) if os.path.exists(p)]
    imagens = [p for p in anexos if p.lower().endswith(IMG)]; audios = [p for p in anexos if p.lower().endswith(AUD)]
    texto = re.sub(r"\[(photo|imagem|foto|document|arquivo|voice|audio|áudio)[^\]]*\]", "", corpo).strip()
    n = norm(texto); st = load()
    if len(n) < 120 and not audios:
        mt = RE_TROCA.search(n)
        if mt and not RE_VOLTA.search(n) and (alvo_modelo(mt.group(2)) in MODELOS or mt.group(2) in MODELOS.values() or (mt.group(1) in ("troca", "trocar", "muda", "mudar") and len(n.split()) <= 6)):
            alvo = alvo_modelo(mt.group(2)); modelo = MODELOS.get(alvo) or (mt.group(2) if mt.group(2) in MODELOS.values() else None)
            if not modelo:
                send_text(chat, f"🤔 Não achei o modelo \"{alvo}\". Cérebros OpenAI: Sol, Terra, Luna, Astra. Ex.: \"troca pro Sol\"."); block("[cérebro: modelo desconhecido, já avisei]")
            resumo = resumo_thread(st, "Troca de modelo") if st.get("empresa") == "openai" and st.get("modelo") != modelo else None
            save({"empresa": "openai", "modelo": modelo, "thread": None, "desde": time.strftime("%d/%m %H:%M"), "tokens": 0, "resumo_anterior": resumo})
            send_text(chat, f"{assinatura(modelo)} ligado. Sou eu mesmo, só que pensando com a OpenAI. \"volta pro Claude\" quando quiser.")
            log(f"troca → openai:{modelo}"); block("[cérebro: troquei pra OpenAI e já avisei no Telegram]")
        if RE_VOLTA.search(n):
            if st.get("empresa") == "openai":
                houve = bool(st.get("thread"))
                resumo = resumo_thread(st, "O dono pediu pra voltar pro Claude") if houve else ""
                save({"empresa": "anthropic", "modelo": None, "thread": None, "desde": time.strftime("%d/%m %H:%M"), "tokens": 0}); log("volta → anthropic")
                if houve:
                    add_context(f"[cérebro: o dono acabou de voltar pra você (Anthropic) depois de conversar com o cérebro OpenAI ({nome(st['modelo'])}). Resumo do que rolou lá:\n{resumo}\n\nResponda pelo reply, curto, confirmando que voltou e retomando de onde ele parou. Não comente o mecanismo da troca.]")
                add_context(f"[cérebro: o dono ligou o cérebro OpenAI ({nome(st['modelo'])}) e voltou pra você sem conversar lá. Responda pelo reply, em 1 linha, que você está de volta. Não comente o mecanismo da troca nem diga que faltou resumo.]")
            return 0
        if RE_STATUS.search(n) and ("cerebro" in n or "respondendo" in n or ("modelo" in n and "ligado" in n)):
            send_text(chat, status_txt(st)); block("[cérebro: status já enviado]")
    if st.get("empresa") != "openai":
        if JOB:
            send_text(chat, "🟣 A troca pro Claude já terminou. Esta mensagem ficou na fila anterior; envie de novo para ele responder.")
            raise RuntimeError("Claude requires a real channel turn")
        return 0
    if audios:
        add_context("[cérebro: o dono está no cérebro OpenAI, mas áudio só o Claude ouve. Responda você esta mensagem normalmente e, se fizer sentido, diga que áudio fica com você.]")
    primeira = not st.get("thread")
    if ROLLOVER and (st.get("tokens") or 0) > ROLLOVER and st.get("thread"):
        st["resumo_anterior"] = resumo_thread(st, "Janela cheia: renovando a conversa"); st["thread"] = None; st["tokens"] = 0; save(st); primeira = True; log("rollover")
    envelope = m.group(0) + ("\n[arquivos anexos (caminhos locais): " + ", ".join(anexos) + "]" if anexos and not imagens else "")
    ok, resp, thread, tokens, dur, novos = run_codex(st, prefixo(st, primeira) + envelope, imagens)
    if thread:
        st["thread"] = thread; save(st)  # preservar continuidade também depois de falha
    if not ok:
        log(f"codex falhou ({dur}s)")
        send_text(chat, "⚠️ O cérebro OpenAI parou antes de concluir. Guardei seu pedido; não encaminhei nem repeti ações automaticamente. Vou precisar conferir o resultado antes de tentar de novo.")
        raise RuntimeError("Codex turn not confirmed")
    if thread and thread != st.get("thread"): st["thread"] = thread
    if tokens: st["tokens"] = tokens
    st["resumo_anterior"] = None; save(st)
    send_text(chat, resp + "\n\n" + assinatura(st["modelo"]))
    for a in novos: send_file(chat, a)
    log(f"respondido por {st['modelo']} em {dur}s (tokens={tokens}, {len(imagens)} img, {len(novos)} arquivos)")
    block(f"[cérebro OpenAI ({nome(st['modelo'])}) já respondeu esta mensagem no Telegram em {dur:.0f}s]")

# ---------- fila durável (o hook termina imediatamente) ----------
def worker():
    q = Queue(STATE)
    def execute(ident, payload):
        global JOB, DELIVERED, DELIVERY_FAILED
        JOB = ident; DELIVERED = 0; DELIVERY_FAILED = False
        try:
            main(payload)
        except SystemExit:
            pass
        except Exception:
            if not DELIVERED:
                send_text(chat_id_dono(), "⚠️ O motor interrompeu antes de concluir. Seu pedido ficou guardado para conferência; não repeti a ação.")
            return "uncertain"
        finally:
            JOB = None
        return "completed" if DELIVERED and not DELIVERY_FAILED else "uncertain"
    def recovered(ident):
        send_text(chat_id_dono(), "⚠️ Uma resposta foi interrompida quando o computador parou. Guardei o pedido e vou precisar conferir o que foi feito antes de repetir.")
    q.drain(execute, recovered)


def dispatch():
    try: d = json.load(sys.stdin)
    except Exception: return 0
    prompt = d.get("prompt") or ""
    m = re.search(r'<channel source="(?:plugin:)?telegram[^>]*chat_id="(\d+)"[^>]*message_id="(\d+)"[^>]*>(.*?)</channel>', prompt, re.S)
    if not m or not chat_id_dono() or m.group(1) != chat_id_dono(): return 0
    if DRY: return main(d)  # testes antigos; fila possui suíte própria com subprocessos reais
    if re.search(r'attachment_kind="(?:voice|audio)"|\(voice message\)', m.group(0)) or any(x in prompt.lower() for x in AUD):
        add_context("[Áudio: responda pelo Claude usando o anexo real. Não trate '(voice message)' como conteúdo nem prometa encaminhamento.]")
    q = Queue(STATE)
    n = norm(m.group(3)); mt = RE_TROCA.search(n)
    switch = mt and (alvo_modelo(mt.group(2)) in MODELOS or mt.group(2) in MODELOS.values() or mt.group(1) in ("troca", "trocar", "muda", "mudar"))
    command = len(n) < 120 and (switch or RE_VOLTA.search(n) or RE_STATUS.search(n))
    with q.connect() as db:
        pending = db.execute("SELECT 1 FROM jobs WHERE status IN ('queued','running') LIMIT 1").fetchone()
    if load().get("empresa") != "openai" and not command and not pending:
        handoff = os.path.join(STATE, "claude-handoff.json")
        if os.path.exists(handoff):
            text = json.load(open(handoff, encoding="utf-8")); os.remove(handoff); add_context(text)
        return main(d)
    ident = m.group(1) + ":" + m.group(2)
    fresh = q.enqueue(ident, d)  # commit em disco ANTES do ACK do hook
    try:
        opts = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS} if os.name == "nt" else {"start_new_session": True}
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "--worker"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         cwd=OS_DIR, close_fds=True, **opts)
    except Exception:
        log("worker não iniciou; pedido permanece queued para recuperação")
        send_text(m.group(1), "⚠️ Guardei seu pedido, mas o motor não iniciou. Ele ficou pendente para recuperação.")
    block("[pedido salvo na fila; resposta ainda pendente]" if fresh else "[mensagem duplicada; pedido original preservado]")

# ---------- self-test (sem Telegram, sem Codex): python3 cerebro.py --teste ----------
def teste():
    import tempfile
    T = tempfile.mkdtemp(); os.environ["MESTREOS_CEREBRO_DRYRUN"] = "1"; os.environ["MESTREOS_CEREBRO_STATE"] = os.path.join(T, "s"); os.environ["TELEGRAM_CHAT_ID"] = "111"
    me = os.path.abspath(__file__); ok = 0; fail = 0
    def ch(c, mid, t): return json.dumps({"prompt": f'<channel source="plugin:telegram@claude-plugins-official" chat_id="{c}" message_id="{mid}" user="x" ts="t">{t}</channel>'})
    def run(inp, fake=None):
        env = dict(os.environ); env.pop("MESTREOS_CEREBRO_FAKE_CODEX", None)
        if fake is not None: env["MESTREOS_CEREBRO_FAKE_CODEX"] = fake
        r = subprocess.run([sys.executable, me], input=inp, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env); return r.stdout, r.stderr
    def st(): return json.load(open(os.path.join(T, "s", "cerebro.json"))) if os.path.exists(os.path.join(T, "s", "cerebro.json")) else {}
    def chk(nome, cond):
        nonlocal ok, fail
        if cond: ok += 1; print("✅", nome)
        else: fail += 1; print("❌", nome)
    o, e = run('{"prompt":"oi digitado"}');                        chk("1 prompt sem canal passa direto", not o)
    o, e = run(ch(999, 1, "troca pro sol"));                        chk("2 outro chat passa direto", not o)
    o, e = run(ch(111, 2, "oi tudo bem"));                          chk("3 modo Claude: mensagem normal passa", not o)
    o, e = run(ch(111, 3, "troca pro codex"));                      chk("4 'troca pro codex' = Sol, bloqueia e avisa", '"block"' in o and "sendMessage" in e and st().get("modelo") == "gpt-5.6-sol")
    o, e = run(ch(111, 4, "qual é a capital de Minas?"), "BH");     chk("5 modo OpenAI: resposta (fake) entregue com assinatura e bloqueio", '"block"' in o and "BH" in e and "Sol" in e)
    o, e = run(ch(111, 5, "salvar"), "salvo");                      chk("6 'salvar' vai pro cérebro ativo", '"block"' in o and "salvo" in e)
    o, e = run(ch(111, 6, "qual cérebro tá ligado?"));              chk("7 status responde", '"block"' in o and "OpenAI" in e)
    o, e = run(ch(111, 7, "troca pro plutao"));                     chk("8 modelo desconhecido avisa e mantém", '"block"' in o and "Não achei" in e and st().get("modelo") == "gpt-5.6-sol")
    o, e = run(ch(111, 8, "liga o astra"), "x");                    chk("9 Sol → Astra", st().get("modelo") == "gpt-6-astra")
    o, e = run(ch(111, 9, "volta pro claude"));                     chk("10 volta: não bloqueia, injeta resumo, estado anthropic", "additionalContext" in o and '"block"' not in o and st().get("empresa") == "anthropic")
    o, e = run(ch(111, 10, "e aí"));                                chk("11 de volta ao Claude: passa", not o)
    o, e = run(ch(111, 11, "Troca pro Codecs."));                    chk("12 ditado 'Codecs' → Codex/Sol", st().get("modelo") == "gpt-5.6-sol")
    o, e = run(ch(111, 12, "Volta para o Claudio"));                 chk("13 ditado 'Claudio' → volta pro Claude", "additionalContext" in o and st().get("empresa") == "anthropic")
    o, e = run(ch(111, 13, "volta pro codex"));                      chk("14 'volta pro codex' = troca pro Sol", '"block"' in o and st().get("modelo") == "gpt-5.6-sol")
    o, e = run(ch(111, 14, "volta pro claude"));                     chk("15 volta sem conversa lá: contexto curto, sem resumo", "additionalContext" in o and "sem conversar" in o and st().get("empresa") == "anthropic")
    print(f"----- {ok} ok · {fail} falhas"); return 0 if fail == 0 else 1

if __name__ == "__main__":
    if "--status" in sys.argv:
        with Queue(STATE).connect() as db:
            counts = dict(db.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall())
        print(json.dumps({"state_dir": STATE, "jobs": counts}, ensure_ascii=False)); sys.exit(0)
    if "--teste" in sys.argv: sys.exit(teste())
    try: sys.exit((worker() if "--worker" in sys.argv or "--recover" in sys.argv else dispatch()) or 0)
    except SystemExit: raise
    except Exception as e: log(f"exceção: {e!r}"); sys.exit(0)
