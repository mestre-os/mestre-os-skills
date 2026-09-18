#!/usr/bin/env python3
"""telegram_janela.py — a janela do bot do MestreOS (PASSO 7D): neutra, em Python, dona do Telegram.
Nenhum motor (Claude Code ou Codex) é dono do bot: esta janela recebe, guarda na fila, transcreve áudio se houver
provedor e entrega ao cérebro ativo (`.meuos/hooks/cerebro.py`), que decide quem responde. A resposta volta por aqui,
com recibo. Roda igual no Mac e no Windows (Python 3 + curl do sistema, sem dependências).

Uso:  python3 telegram_janela.py            abre a janela (fica escutando; Ctrl+C fecha)
      python3 telegram_janela.py --recover  atende só o que ficou na fila e sai (usado pelo agendador; se a janela estiver aberta, não faz nada)
      python3 telegram_janela.py --status   estado da fila e do cérebro
      python3 telegram_janela.py --teste    self-test sem Telegram, sem IA
Token: o mesmo Cofre dos robôs (variável TELEGRAM_BOT_TOKEN · Keychain · DPAPI · ~/.claude/channels/telegram/.env). Nunca impresso.
Dono: TELEGRAM_CHAT_ID · .meuos/scripts/telegram-send.env · access.json do plugin. Sem dono, a janela pareia com um código.
Transcrição de áudio, em cadeia: whisper local (mlx_whisper ou whisper no PATH) → OpenAI (OPENAI_API_KEY) → Groq (GROQ_API_KEY,
grátis) → sem nenhum: responde honesto "manda em texto". Chaves: variável · Keychain (openai-api-key / groq-api-key) · DPAPI ·
linhas OPENAI_API_KEY= / GROQ_API_KEY= no mesmo ~/.claude/channels/telegram/.env do token.
"""
import json, os, re, sys, subprocess, time, threading, random, string, shutil, platform
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI); sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "hooks"))
for _s in (sys.stdout, sys.stderr, sys.stdin):
    if hasattr(_s, "reconfigure"):
        try: _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception: pass
import cerebro
from telegram_runtime import Queue, lock, Busy
from telegram_send import token as ler_token, chat_id as ler_chat_id, _token_keychain, _token_dpapi, PLUGIN_DIR

STATE = cerebro.STATE; OS_DIR = cerebro.OS_DIR
INBOX = os.path.join(STATE, "inbox"); LOGF = os.path.join(STATE, "janela.log"); OFFSET = os.path.join(STATE, "offset")
DRY = bool(os.environ.get("MESTREOS_JANELA_DRYRUN")); DRY_API = []   # em teste, tudo que iria pro Telegram cai aqui
POLL = int(os.environ.get("MESTREOS_JANELA_POLL", "25"))
MAX_AUDIO = 25 * 1024 * 1024   # teto do tier grátis da Groq
SISTEMA = platform.system()

def log(m):
    try:
        os.makedirs(STATE, exist_ok=True)
        with open(LOGF, "a", encoding="utf-8") as f: f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {m}\n")
    except Exception: pass

def diga(m):
    print(time.strftime("%H:%M ") + m, flush=True)

# ---------- segredos (mesmo Cofre dos robôs; nada impresso) ----------
def segredo(nome, var):
    v = (os.environ.get(var) or "").strip()
    if v: return v
    if SISTEMA == "Darwin":
        try:
            r = subprocess.run(["security", "find-generic-password", "-s", nome, "-w"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout.strip(): return r.stdout.strip()
        except Exception: pass
    elif SISTEMA == "Windows":
        f = os.path.join(os.environ.get("LOCALAPPDATA", ""), "MestreOS", "cofre", nome + ".cred")
        if os.path.isfile(f):
            ps = ("$e = (Get-Content -Raw -LiteralPath '" + f.replace("'", "''") + "').Trim(); $s = ConvertTo-SecureString $e; "
                  "$b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s); [Runtime.InteropServices.Marshal]::PtrToStringAuto($b)")
            try:
                r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps], capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
                if r.returncode == 0 and r.stdout.strip(): return r.stdout.strip()
            except Exception: pass
    try:
        for l in open(os.path.join(PLUGIN_DIR, ".env"), encoding="utf-8-sig", errors="ignore"):
            if l.startswith(var + "="): return l.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception: pass
    return ""

# ---------- Bot API (curl com o token pelo stdin: nunca no argv nem no log) ----------
def api(method, fields=None, files=None, max_time=60, tok=None):
    if DRY:
        DRY_API.append((method, dict(fields or {}), list((files or {}).values())))
        if method == "getUpdates": return {"ok": True, "result": []}
        return {"ok": True, "result": {"message_id": len(DRY_API), "file_path": "voice/x.oga"}}
    tok = tok or ler_token()
    if not tok: return {"ok": False, "description": "sem token do bot"}
    cmd = ["curl", "-s", "--max-time", str(max_time), "-K", "-"]
    for k, v in (fields or {}).items(): cmd += (["-F", f"{k}={v}"] if files else ["--data-urlencode", f"{k}={v}"])
    for k, p in (files or {}).items(): cmd += ["-F", f"{k}=@{p}"]
    try:
        r = subprocess.run(cmd, input=f'url = "https://api.telegram.org/bot{tok}/{method}"\n', capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=max_time + 15)
        return json.loads(r.stdout)
    except Exception as e:
        return {"ok": False, "description": type(e).__name__}

def baixar(file_id, destino):
    r = api("getFile", {"file_id": file_id})
    if not r.get("ok"): return None
    caminho = (r.get("result") or {}).get("file_path")
    if not caminho: return None
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    if DRY:
        open(destino, "wb").write(b"fake"); return destino
    tok = ler_token()
    try:
        subprocess.run(["curl", "-s", "--max-time", "120", "-K", "-", "-o", destino], input=f'url = "https://api.telegram.org/file/bot{tok}/{caminho}"\n', capture_output=True, timeout=140)
        return destino if os.path.isfile(destino) and os.path.getsize(destino) > 0 else None
    except Exception: return None

# ---------- transcrição em cadeia ----------
def _stt_local(path):
    """whisper local, se o dono tiver: mlx_whisper (Mac, Metal) ou whisper (CPU). Sem nada instalado, pula."""
    mlx = shutil.which("mlx_whisper")
    if mlx:
        td = os.path.join(STATE, "stt"); os.makedirs(td, exist_ok=True)
        try:
            r = subprocess.run([mlx, path, "--language", "pt", "--output-dir", td, "--output-name", "out", "-f", "txt"], capture_output=True, timeout=900)
            t = open(os.path.join(td, "out.txt"), encoding="utf-8").read().strip() if r.returncode == 0 else ""
            if t: return t
        except Exception: pass
    w = shutil.which("whisper")
    if w:
        td = os.path.join(STATE, "stt"); os.makedirs(td, exist_ok=True)
        try:
            subprocess.run([w, path, "--model", "turbo", "--language", "Portuguese", "--task", "transcribe", "--output_format", "txt", "--output_dir", td, "--fp16", "False", "--verbose", "False"], capture_output=True, timeout=1800)
            base = os.path.splitext(os.path.basename(path))[0]
            t = open(os.path.join(td, base + ".txt"), encoding="utf-8").read().strip()
            if t: return t
        except Exception: pass
    return ""

def _stt_http(path, url, chave, modelo):
    """POST multipart compatível com a API da OpenAI (a Groq usa o mesmo formato). Chave pelo stdin do curl."""
    if DRY: return f"(transcrição fake via {modelo})"
    cfg = f'url = "{url}"\nheader = "Authorization: Bearer {chave}"\n'
    cmd = ["curl", "-s", "--max-time", "180", "-K", "-", "-F", f"file=@{path}", "-F", f"model={modelo}", "-F", "language=pt", "-F", "response_format=json"]
    try:
        r = subprocess.run(cmd, input=cfg, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)
        d = json.loads(r.stdout); return (d.get("text") or "").strip()
    except Exception: return ""

def transcrever(path):
    """áudio → texto pela primeira cadeia disponível; "" se nenhuma. Nunca inventa."""
    try:
        if os.path.getsize(path) > MAX_AUDIO: return ""
    except OSError: return ""
    t = _stt_local(path)
    if t: return t
    k = segredo("openai-api-key", "OPENAI_API_KEY")
    if k: t = _stt_http(path, "https://api.openai.com/v1/audio/transcriptions", k, "whisper-1")
    if t: return t
    k = segredo("groq-api-key", "GROQ_API_KEY")
    if k: t = _stt_http(path, "https://api.groq.com/openai/v1/audio/transcriptions", k, "whisper-large-v3-turbo")
    return t or ""

def tem_stt():
    return bool(shutil.which("mlx_whisper") or shutil.which("whisper") or segredo("openai-api-key", "OPENAI_API_KEY") or segredo("groq-api-key", "GROQ_API_KEY"))

# ---------- entrega (com recibo na fila) ----------
JOB = None; ENTREGUE = 0; FALHOU = False
def enviar_texto(chat, texto):
    global ENTREGUE, FALHOU
    texto = (texto or "").strip() or "(sem texto)"; ok = True
    while texto:
        chunk, texto = texto[:3900], texto[3900:]
        r = api("sendMessage", {"chat_id": chat, "text": chunk, "disable_web_page_preview": "true"})
        mid = (r.get("result") or {}).get("message_id") if r.get("ok") else None
        if mid is None: ok = False; FALHOU = True; log("sendMessage sem confirmação")
        else:
            ENTREGUE += 1
            if JOB: Queue(STATE).receipt(JOB, mid, "sendMessage")
    return ok

def enviar_arquivo(chat, path):
    global ENTREGUE, FALHOU
    if path.lower().endswith(cerebro.IMG) and os.path.getsize(path) < 10 * 1024 * 1024: r = api("sendPhoto", {"chat_id": chat}, {"photo": path}, max_time=120)
    else: r = api("sendDocument", {"chat_id": chat}, {"document": path}, max_time=300)
    mid = (r.get("result") or {}).get("message_id") if r.get("ok") else None
    if mid is None: FALHOU = True; log(f"arquivo não confirmado: {os.path.basename(path)}"); return False
    ENTREGUE += 1
    if JOB: Queue(STATE).receipt(JOB, mid, "sendDocument")
    return True

def reagir(chat, mid, emoji="👀"):
    api("setMessageReaction", {"chat_id": chat, "message_id": mid, "reaction": json.dumps([{"type": "emoji", "emoji": emoji}])}, max_time=15)

# ---------- pareamento (sem dono configurado, o primeiro que mandar o código vira o dono) ----------
CODIGO = {"valor": None}
def dono():
    return ler_chat_id()

def gravar_dono(chat):
    f = os.path.join(AQUI, "telegram-send.env")
    try:
        with open(f, "w", encoding="utf-8") as fh: fh.write(f"TELEGRAM_CHAT_ID={chat}\n")
        return True
    except Exception as e: log(f"não gravei o dono: {e!r}"); return False

def parear(chat, texto):
    if not CODIGO["valor"]:
        CODIGO["valor"] = "".join(random.choices(string.ascii_uppercase, k=6))
        diga(f"🔐 Alguém falou com o bot. Se for você, manda este código pelo Telegram: {CODIGO['valor']}")
        enviar_texto(chat, "🔐 Oi! Ainda não sei quem é o dono. Olha no computador: apareceu um código de 6 letras na janela do bot. Manda ele aqui.")
        return
    if (texto or "").strip().upper() == CODIGO["valor"]:
        if gravar_dono(chat):
            diga(f"✅ Pareado com o chat {chat}."); enviar_texto(chat, "✅ Pareado. Agora só você fala comigo por aqui. Manda um oi.")
    else:
        enviar_texto(chat, "🤔 Não é esse. O código tem 6 letras e está na janela do bot, no computador.")

# ---------- recepção ----------
def anexos(msg):
    """baixa foto (maior tamanho), voz/áudio e documento pra inbox local. Devolve (imagens, audios, arquivos)."""
    mid = msg.get("message_id"); imgs, auds, docs = [], [], []
    if msg.get("photo"):
        p = msg["photo"][-1]; d = baixar(p["file_id"], os.path.join(INBOX, f"{mid}_foto.jpg"))
        if d: imgs.append(d)
    for k in ("voice", "audio"):
        if msg.get(k):
            ext = ".oga" if k == "voice" else os.path.splitext(msg[k].get("file_name") or ".mp3")[1] or ".mp3"
            d = baixar(msg[k]["file_id"], os.path.join(INBOX, f"{mid}_{k}{ext}"))
            if d: auds.append(d)
    if msg.get("document"):
        nome = re.sub(r"[^A-Za-z0-9._-]", "_", msg["document"].get("file_name") or "arquivo")
        d = baixar(msg["document"]["file_id"], os.path.join(INBOX, f"{mid}_{nome}"))
        if d: (imgs if d.lower().endswith(cerebro.IMG) else docs).append(d)
    return imgs, auds, docs

def receber(update):
    msg = update.get("message") or update.get("edited_message")
    if not msg: return
    chat = str(msg.get("chat", {}).get("id", "")); mid = msg.get("message_id"); texto = msg.get("text") or msg.get("caption") or ""
    d = dono()
    if not d: parear(chat, texto); return
    if chat != d: log(f"ignorado chat {chat}"); return
    reagir(chat, mid)
    imgs, auds, docs = anexos(msg)
    nome = (msg.get("from") or {}).get("first_name") or "dono"
    payload = {"chat": chat, "mid": str(mid), "user": nome, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "texto": texto,
               "imagens": imgs, "audios": auds, "arquivos": docs, "transcricoes": []}
    q = Queue(STATE)
    if q.enqueue(f"{chat}:{mid}", payload): log(f"na fila {mid} ({'áudio ' if auds else ''}{'foto ' if imgs else ''}{len(texto)} chars)")

# ---------- execução (um por vez, em ordem; recibo por envio) ----------
def executar(ident, payload):
    global JOB, ENTREGUE, FALHOU
    JOB = ident; ENTREGUE = 0; FALHOU = False; chat = payload["chat"]
    parar = threading.Event()
    def batimento():
        while not parar.is_set():
            api("sendChatAction", {"chat_id": chat, "action": "typing"}, max_time=10); parar.wait(4)
    threading.Thread(target=batimento, daemon=True).start()
    try:
        if payload.get("audios"):
            if tem_stt():
                payload["transcricoes"] = [transcrever(a) for a in payload["audios"]]
                if not any(payload["transcricoes"]): log(f"transcrição vazia {ident}")
            else:
                enviar_texto(chat, "🎧 Recebi seu áudio, mas ainda não consigo ouvir: não tem transcrição configurada neste computador. Manda em texto que eu respondo. (Pra eu ouvir: uma chave gratuita da Groq no arquivo do token, linha GROQ_API_KEY=…)")
                if not (payload.get("texto") or payload.get("imagens")): return "completed"
        acoes = cerebro.responder(payload)
        incerto = False
        for tipo, valor in acoes:
            if tipo == "texto": enviar_texto(chat, valor)
            elif tipo == "arquivo": enviar_arquivo(chat, valor)
            elif tipo == "falha": incerto = True
        if incerto: return "uncertain"
        return "completed" if ENTREGUE and not FALHOU else "uncertain"
    except Exception as e:
        log(f"execução {ident}: {e!r}")
        if not ENTREGUE: enviar_texto(chat, "⚠️ O motor interrompeu antes de concluir. Seu pedido ficou guardado para conferência; não repeti a ação.")
        return "uncertain"
    finally:
        parar.set(); JOB = None

def recuperado(ident):
    enviar_texto(dono(), "⚠️ Uma resposta foi interrompida quando a janela fechou. Guardei o pedido e vou precisar conferir o que foi feito antes de repetir.")

def executor_loop(parar):
    q = Queue(STATE)
    while not parar.is_set():
        try: q.drain(executar, recuperado)
        except Exception as e: log(f"executor: {e!r}")
        parar.wait(1)

# ---------- janela ----------
def ler_offset():
    try: return int(open(OFFSET).read().strip())
    except Exception: return 0

def gravar_offset(v):
    try:
        os.makedirs(STATE, exist_ok=True); open(OFFSET + ".tmp", "w").write(str(v)); os.replace(OFFSET + ".tmp", OFFSET)
    except Exception: pass

def janela():
    os.makedirs(STATE, exist_ok=True)
    if not ler_token():
        diga("❌ Sem token do bot. Grave a linha TELEGRAM_BOT_TOKEN= no arquivo do token (PASSO 7A.3 / 7B.3) e abra de novo."); return 1
    try:
        with lock(os.path.join(STATE, "janela.lock")):
            st = cerebro.load()
            diga(f"🤖 Janela do bot aberta · cérebro: {cerebro.assinatura(st['ativo'], st[st['ativo']].get('modelo'))} · principal {st['principal']}"
                 + (f", secundário {st['secundario']}" if st.get("secundario") else "") + f" · áudio: {'sim' if tem_stt() else 'sem transcrição (manda em texto)'}")
            if not dono(): diga("🔐 Sem dono ainda: manda qualquer mensagem pro bot no celular pra parear.")
            parar = threading.Event(); threading.Thread(target=executor_loop, args=(parar,), daemon=True).start()
            offset = ler_offset(); erros409 = 0
            try:
                while True:
                    r = api("getUpdates", {"offset": offset, "timeout": POLL, "allowed_updates": json.dumps(["message"])}, max_time=POLL + 15)
                    if not r.get("ok"):
                        if r.get("error_code") == 409 or "409" in str(r.get("description", "")) or "Conflict" in str(r.get("description", "")):
                            erros409 += 1
                            diga("⚠️ Outro programa está escutando este bot (o plugin do Claude, a ponte do Codex ou outra janela). Feche-o: o Telegram só entrega pra um por vez.")
                            if erros409 >= 3: return 2
                        else: log(f"getUpdates: {r.get('description')}")
                        time.sleep(3); continue
                    erros409 = 0
                    for u in r.get("result") or []:
                        offset = max(offset, int(u.get("update_id", 0)) + 1)
                        try: receber(u)
                        except Exception as e: log(f"receber: {e!r}")
                        gravar_offset(offset)  # depois de guardar na fila: mensagem nunca some entre o ACK e o disco
                    if DRY: return 0
            except KeyboardInterrupt:
                diga("👋 Janela fechada. O que estava na fila fica guardado; abre de novo quando quiser."); return 0
            finally: parar.set()
    except Busy:
        diga("⚠️ Já existe uma janela deste bot aberta neste computador. Use aquela (ou feche-a) antes de abrir outra."); return 3

def recover():
    q = Queue(STATE)
    if not q.drain(executar, recuperado): return 0  # janela aberta = ela cuida
    return 0

def status():
    st = cerebro.load()
    with Queue(STATE).connect() as db: counts = dict(db.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall())
    print(json.dumps({"state_dir": STATE, "dono": bool(dono()), "cerebro": cerebro.assinatura(st["ativo"], st[st["ativo"]].get("modelo")), "principal": st["principal"],
                      "secundario": st.get("secundario"), "audio": tem_stt(), "jobs": counts}, ensure_ascii=False))

# ---------- self-test: sem Telegram, sem IA ----------
def teste():
    import tempfile
    global DRY, STATE, INBOX, OFFSET, LOGF
    T = tempfile.mkdtemp(); DRY = True
    STATE = cerebro.STATE = os.path.join(T, "s"); cerebro.SF = os.path.join(STATE, "cerebro.json"); cerebro.CONVERSA = os.path.join(STATE, "conversa.jsonl"); cerebro.LOGF = os.path.join(STATE, "cerebro.log")
    INBOX = os.path.join(STATE, "inbox"); OFFSET = os.path.join(STATE, "offset"); LOGF = os.path.join(STATE, "janela.log")
    os.environ["MESTREOS_CEREBRO_FAKE_CLAUDE"] = "resposta do claude"; os.environ["MESTREOS_CEREBRO_FAKE_CODEX"] = "resposta do codex"
    os.environ["MESTREOS_CLAUDE_BIN"] = os.path.join(T, "nao"); os.environ["MESTREOS_CODEX_BIN"] = os.path.join(T, "nao")
    cerebro.FAKE_CLAUDE = "resposta do claude"; cerebro.FAKE_CODEX = "resposta do codex"
    cerebro.CLAUDE = os.path.join(T, "nao"); cerebro.CODEX = os.path.join(T, "nao")  # nunca chama IA de verdade
    ok = fail = 0
    def chk(nome, cond):
        nonlocal ok, fail
        if cond: ok += 1; print("✅", nome)
        else: fail += 1; print("❌", nome)
    def enviados(): return [f.get("text", "") for m, f, _ in DRY_API if m == "sendMessage"]
    global dono, gravar_dono, tem_stt, transcrever
    _dono = {"v": ""}
    dono = lambda: _dono["v"]; gravar_dono = lambda chat: _dono.update(v=chat) or True
    tem_stt = lambda: False
    q = Queue(STATE); st = cerebro.novo_estado("claude", "codex"); cerebro.save(st)
    # 1 pareamento
    receber({"update_id": 1, "message": {"message_id": 10, "chat": {"id": 555}, "text": "oi"}})
    chk("1 sem dono: pede o código e não enfileira", CODIGO["valor"] and "código" in enviados()[-1] and q.status("555:10") is None)
    receber({"update_id": 2, "message": {"message_id": 11, "chat": {"id": 555}, "text": CODIGO["valor"].lower()}})
    chk("2 código certo pareia e grava o dono", _dono["v"] == "555" and "Pareado" in enviados()[-1])
    receber({"update_id": 3, "message": {"message_id": 12, "chat": {"id": 666}, "text": "oi sou estranho"}})
    chk("3 outro chat é ignorado em silêncio", q.status("666:12") is None and "estranho" not in " ".join(enviados()))
    # 4 mensagem do dono: reação 👀 + fila
    receber({"update_id": 4, "message": {"message_id": 13, "chat": {"id": 555}, "from": {"first_name": "Ana"}, "text": "oi tudo bem"}})
    chk("4 dono: reage 👀 e guarda na fila antes de responder", q.status("555:13") == "queued" and any(m == "setMessageReaction" for m, _, _ in DRY_API))
    receber({"update_id": 4, "message": {"message_id": 13, "chat": {"id": 555}, "text": "oi tudo bem"}})
    with q.connect() as db: n = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    chk("5 update repetido não duplica o pedido", n == 1)
    q.drain(executar, recuperado)
    chk("6 executor entrega a resposta do Claude com assinatura e recibo", q.status("555:13") == "completed" and "resposta do claude" in enviados()[-1] and "🟣" in enviados()[-1])
    with q.connect() as db: rec = db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
    chk("6b recibo gravado com o message_id do Telegram", rec >= 1)
    # 7 troca de cérebro pela janela
    receber({"update_id": 5, "message": {"message_id": 14, "chat": {"id": 555}, "text": "troca pro codex"}}); q.drain(executar, recuperado)
    receber({"update_id": 6, "message": {"message_id": 15, "chat": {"id": 555}, "text": "e aí"}}); q.drain(executar, recuperado)
    chk("7 'troca pro codex' pela janela: Codex responde a próxima com ☀️", "resposta do codex" in enviados()[-1] and "Sol" in enviados()[-1])
    # 8 áudio sem transcrição
    receber({"update_id": 7, "message": {"message_id": 16, "chat": {"id": 555}, "voice": {"file_id": "abc"}}}); q.drain(executar, recuperado)
    chk("8 áudio sem provedor: aviso honesto 'manda em texto', pedido fechado sem chamar motor", "manda em texto" in enviados()[-1].lower() and q.status("555:16") == "completed")
    # 9 áudio com transcrição (fake) vira comando falado
    tem_stt = lambda: True; transcrever = lambda p: "volta pro claude"
    receber({"update_id": 8, "message": {"message_id": 17, "chat": {"id": 555}, "voice": {"file_id": "abc"}}}); q.drain(executar, recuperado)
    chk("9 comando FALADO transcrito pela janela troca o cérebro", cerebro.load()["ativo"] == "claude" and "ligado" in enviados()[-1])
    transcrever = lambda p: "qual a capital de minas"
    receber({"update_id": 9, "message": {"message_id": 18, "chat": {"id": 555}, "voice": {"file_id": "abc"}, "caption": ""}}); q.drain(executar, recuperado)
    chk("10 áudio transcrito vai pro motor ativo como texto rotulado", "resposta do claude" in enviados()[-1])
    # 11 foto
    receber({"update_id": 10, "message": {"message_id": 19, "chat": {"id": 555}, "photo": [{"file_id": "p1"}, {"file_id": "p2"}], "caption": "o que é isso"}})
    with q.connect() as db: pl = json.loads(db.execute("SELECT payload FROM jobs WHERE id='555:19'").fetchone()[0])
    chk("11 foto: baixa o maior tamanho pra inbox local e entra na fila com a legenda", pl["imagens"] and os.path.isfile(pl["imagens"][0]) and pl["texto"] == "o que é isso")
    q.drain(executar, recuperado)
    # 12 motor falha → incerto, aviso, sem repetição
    cerebro.FAKE_CLAUDE = None; os.environ.pop("MESTREOS_CEREBRO_FAKE_CLAUDE", None)
    receber({"update_id": 11, "message": {"message_id": 20, "chat": {"id": 555}, "text": "faz algo"}}); q.drain(executar, recuperado)
    chk("12 motor indisponível: pedido fica 'uncertain', aviso honesto, sem repetir", q.status("555:20") == "uncertain" and "parou antes de concluir" in enviados()[-1])
    q.drain(executar, recuperado)
    chk("13 segunda passada não repete o pedido incerto", enviados().count(enviados()[-1]) == 1)
    # 14 offset persistido e janela em DRY encerra
    gravar_offset(12); chk("14 offset persistido em disco", ler_offset() == 12)
    print(f"----- {ok} ok · {fail} falhas"); return 0 if fail == 0 else 1

if __name__ == "__main__":
    if "--teste" in sys.argv: sys.exit(teste())
    if "--status" in sys.argv: status(); sys.exit(0)
    if "--recover" in sys.argv: sys.exit(recover())
    sys.exit(janela() or 0)
