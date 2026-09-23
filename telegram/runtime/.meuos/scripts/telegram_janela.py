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
        # bug S5 23/09/26: faltava text=True com input em str → TypeError engolido pelo except → foto/áudio sumiam calados
        # --fail: erro HTTP (404/401) não grava o corpo do erro como se fosse a foto; rc != 0 = não baixou
        r = subprocess.run(["curl", "-s", "--fail", "--max-time", "120", "-o", destino, "-K", "-"],
                           input=f'url = "https://api.telegram.org/file/bot{tok}/{caminho}"\n', capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=140)
        if r.returncode == 0 and os.path.isfile(destino) and os.path.getsize(destino) > 0: return destino
        log(f"download falhou: curl {r.returncode}")
        if os.path.isfile(destino): os.remove(destino)
        return None
    except Exception as e: log(f"download falhou: {type(e).__name__}"); return None

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
def pedacos(texto, limite=4000):
    """Corta pelo que o Telegram mede (unidades UTF-16, teto 4096: emoji conta 2); prefere quebra de linha."""
    partes = []
    while texto:
        n = u = 0
        for c in texto:
            u += 2 if ord(c) > 0xFFFF else 1
            if u > limite: break
            n += 1
        if n < len(texto):
            q = texto.rfind("\n", 0, n)
            if q > n // 2: n = q + 1
        partes.append(texto[:n]); texto = texto[n:]
    return partes

def enviar_texto(chat, texto):
    global ENTREGUE, FALHOU
    texto = (texto or "").strip() or "(sem texto)"; ok = True
    for chunk in pedacos(texto):
        r = api("sendMessage", {"chat_id": chat, "text": chunk, "disable_web_page_preview": "true"})
        # Telegram mandou esperar (429) ou caiu do lado dele (5xx) = certeza de que não foi → 1 nova tentativa.
        # Outra recusa (400) falharia igual; sem resposta legível (rede caiu no meio) NÃO repete: pode ter ido, e duplicar é pior.
        if not r.get("ok") and (r.get("error_code") == 429 or (r.get("error_code") or 0) >= 500):
            ra = (r.get("parameters") or {}).get("retry_after"); espera = 2 if ra is None else int(ra)
            log(f"sendMessage recusado ({r.get('error_code')}: {r.get('description')}); tentando de novo em {min(espera, 30)}s")
            time.sleep(min(espera, 30))
            r = api("sendMessage", {"chat_id": chat, "text": chunk, "disable_web_page_preview": "true"})
        mid = (r.get("result") or {}).get("message_id") if r.get("ok") else None
        if mid is None: ok = False; FALHOU = True; log(f"sendMessage sem confirmação ({r.get('error_code', '-')}: {r.get('description')})")
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

AVISO_ANEXO = "[AVISO: o dono mandou um anexo (foto/áudio/arquivo) e eu não consegui baixar. Diga isso com honestidade e peça pra reenviar; não invente o conteúdo.]"

def receber(update):
    msg = update.get("message") or update.get("edited_message")
    if not msg: return
    chat = str(msg.get("chat", {}).get("id", "")); mid = msg.get("message_id"); texto = msg.get("text") or msg.get("caption") or ""
    d = dono()
    if not d: parear(chat, texto); return
    if chat != d: log(f"ignorado chat {chat}"); return
    reagir(chat, mid, "✍" if (msg.get("voice") or msg.get("audio")) else "👀")  # 👂 não existe pra bot no Telegram (REACTION_INVALID)
    imgs, auds, docs = anexos(msg)
    if (msg.get("photo") or msg.get("voice") or msg.get("audio") or msg.get("document")) and not (imgs or auds or docs):
        log(f"anexo {mid}: download falhou"); texto = (texto + "\n\n" if texto else "") + AVISO_ANEXO
    nome = (msg.get("from") or {}).get("first_name") or "dono"
    payload = {"chat": chat, "mid": str(mid), "user": nome, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "texto": texto,
               "imagens": imgs, "audios": auds, "arquivos": docs, "transcricoes": []}
    q = Queue(STATE)
    if q.enqueue(f"{chat}:{mid}", payload): log(f"na fila {mid} ({'áudio ' if auds else ''}{'foto ' if imgs else ''}{len(texto)} chars)")

# ---------- execução (um por vez, em ordem; recibo por envio) ----------
# ---------- porta: junta a rajada e espera o anexo prometido (23/09/26, pedido do dono) ----------
# Antes: áudio "vou te mandar a foto" + foto viravam 2 pedidos e 2 respostas ("vou aguardar a foto", depois outra).
# Agora: texto puro sem promessa sai na hora (expresso); áudio/anexo esperam PORTA_RAJADA por mais mensagens da rajada;
# promessa de anexo sem anexo espera até PORTA_PROMESSA; tudo vira UM pedido ao cérebro. Promessa não cumprida vira nota.
PORTA_RAJADA = float(os.environ.get("MESTREOS_PORTA_RAJADA_S", "2"))
PORTA_PROMESSA = float(os.environ.get("MESTREOS_PORTA_PROMESSA_S", "60"))
# objeto LOGO depois do verbo (só recheio curto e artigo no meio): "vou passar no banco pagar o boleto" NÃO é promessa
RE_PROMESSA = re.compile(r"(?<!\bme\s)(?<!\bnos\s)\b(mandar|mando|mandando|enviar|envio|enviando|encaminhar|encaminho|passar|passo|tirar|tiro|segue|seguem)\b(?:\s+(?:te|lhe|aqui|já|ja|agora|logo|rapidinho|pra|para|você|voce|vc|ti|daqui|a|pouco|em|seguida|também|tambem)){0,3}(?:\s+(?:a|o|as|os|um|uma|uns|umas|essa|esse|essas|esses|esta|este|aquela|aquele|minha|meu|minhas|meus|sua|seu|mais|outra|outro|umas?)){0,2}\s+(fotos?|imagens?|imagem|prints?|screenshots?|captura|arquivos?|pdfs?|documentos?|planilhas?|v[ií]deos?|anexos?|contratos?|comprovantes?|boletos?|notas?)\b", re.I)
ESPERANDO = threading.Event()  # ligado = esperando anexo prometido: o "digitando" pausa (não é hora de fingir que tá escrevendo)
ABSORVIDOS = []

def promessa(p):
    m = RE_PROMESSA.search((p.get("texto") or "") + " " + " ".join(t for t in (p.get("transcricoes") or []) if t))
    return m.group(2).lower() if m else None

def tem_anexo(p):
    return bool(p.get("imagens") or p.get("arquivos"))

def ouvir(p):
    if p.get("audios") and tem_stt() and not p.get("transcricoes"):
        p["transcricoes"] = [transcrever(a) for a in p["audios"]]
    return p

def absorver(chat, ident):
    """Pedidos seguintes do mesmo dono, ainda na fila, entram neste. Ficam 'absorvido' (a fila não os pega de novo) até a resposta;
    queda no meio = a recuperação do pedido principal fecha todos juntos, com UM aviso só (dado continua no SQLite)."""
    novos = []
    with Queue(STATE).connect() as db:
        for r in db.execute("SELECT id, payload FROM jobs WHERE status='queued' AND id LIKE ? AND id != ? ORDER BY seq", (f"{chat}:%", ident)).fetchall():
            if db.execute("UPDATE jobs SET status='absorvido', detail=?, updated=? WHERE id=? AND status='queued'", (f"absorvido em {ident}", time.time(), r["id"])).rowcount:
                ABSORVIDOS.append(r["id"]); novos.append(json.loads(r["payload"]))
    return novos

def porta(ident, payload):
    chat = payload["chat"]; itens = [payload]
    prom = None if tem_anexo(payload) else promessa(payload)
    if not (payload.get("audios") or tem_anexo(payload) or prom): return payload  # expresso
    prom_em = time.time()
    def aguarda(p):
        ESPERANDO.set(); reagir(chat, p.get("mid"), "🫡")
    if prom: aguarda(payload)
    prazo = (prom_em + PORTA_PROMESSA) if prom else time.time() + PORTA_RAJADA
    while time.time() < prazo:
        for p in absorver(chat, ident):
            itens.append(ouvir(p))
            if tem_anexo(p): prom = None; ESPERANDO.clear()
            elif not prom and not any(tem_anexo(i) for i in itens):
                prom = promessa(p)
                if prom: prom_em = time.time(); aguarda(p)
            prazo = (prom_em + PORTA_PROMESSA) if prom else time.time() + PORTA_RAJADA
        time.sleep(0.3)
    ESPERANDO.clear()
    if len(itens) == 1 and not prom: return payload
    linhas = [f"[pacote: {len(itens)} mensagem(ns) que o dono mandou em sequência; responda TUDO numa resposta só]"]
    for p in itens:
        tipo = " (áudio, transcrição abaixo)" if p.get("audios") else " (foto)" if p.get("imagens") else " (arquivo)" if p.get("arquivos") else ""
        linhas.append(f"— msg {p.get('mid')}{tipo}: {p.get('texto') or ''}".rstrip())
    if prom:
        linhas.append(f"[nota da janela: ele disse que ia mandar {prom} e nada chegou em {PORTA_PROMESSA:.0f} s (pode ter esquecido, sido interrompido "
                      f"ou o envio falhou). Responda o resto e avise, curto, que está aguardando o anexo prometido ({prom}).]")
    ult = itens[-1]
    return {**ult, "texto": "\n".join(linhas), "mids": [p.get("mid") for p in itens],
            "imagens": [x for p in itens for x in (p.get("imagens") or [])], "audios": [x for p in itens for x in (p.get("audios") or [])],
            "transcricoes": [x for p in itens for x in (p.get("transcricoes") or [])], "arquivos": [x for p in itens for x in (p.get("arquivos") or [])]}

def executar(ident, payload):
    global JOB, ENTREGUE, FALHOU
    JOB = ident; ENTREGUE = 0; FALHOU = False; chat = payload["chat"]; ABSORVIDOS.clear()
    parar = threading.Event()
    def batimento():
        while not parar.is_set():
            if not ESPERANDO.is_set(): api("sendChatAction", {"chat_id": chat, "action": "typing"}, max_time=10)
            parar.wait(4)
    threading.Thread(target=batimento, daemon=True).start()
    status = "uncertain"
    try:
        if payload.get("audios"):
            if tem_stt():
                ouvir(payload)
                if not any(payload["transcricoes"]): log(f"transcrição vazia {ident}")
            else:
                enviar_texto(chat, "🎧 Recebi seu áudio, mas ainda não consigo ouvir: não tem transcrição configurada neste computador. Manda em texto que eu respondo. (Pra eu ouvir: uma chave gratuita da Groq no arquivo do token, linha GROQ_API_KEY=…)")
                if not (payload.get("texto") or payload.get("imagens")): status = "completed"; return status
        payload = porta(ident, payload)
        if ABSORVIDOS: log(f"porta: {ident} juntou {len(ABSORVIDOS)} mensagem(ns) da rajada")
        acoes = cerebro.responder(payload)
        incerto = False; escolhida = None
        for tipo, valor in acoes:
            if tipo == "texto": enviar_texto(chat, valor)
            elif tipo == "arquivo": enviar_arquivo(chat, valor)
            elif tipo == "reagir": escolhida = valor
            elif tipo == "falha": incerto = True
        # troca GARANTIDA (23/09/26): ✍/👀/🫡 nunca fica parado depois da resposta; sem escolha do cérebro, 👌
        if ENTREGUE and not incerto:
            for m in (payload.get("mids") or [payload.get("mid")]): reagir(chat, m, escolhida or "👌")
        status = "uncertain" if incerto else ("completed" if ENTREGUE and not FALHOU else "uncertain")
        return status
    except Exception as e:
        log(f"execução {ident}: {e!r}")
        if not ENTREGUE: enviar_texto(chat, "⚠️ O motor interrompeu antes de concluir. Seu pedido ficou guardado para conferência; não repeti a ação.")
        return "uncertain"
    finally:
        parar.set(); ESPERANDO.clear(); JOB = None
        for a in ABSORVIDOS: Queue(STATE).finish(a, status, f"absorvido em {ident}")

def recuperado(ident):
    with Queue(STATE).connect() as db:  # mensagens que a porta juntou neste pedido caem junto, sem aviso repetido
        juntas = db.execute("UPDATE jobs SET status='uncertain', detail=?, updated=? WHERE status='absorvido' AND detail=?",
                            (f"interrompido junto com {ident}", time.time(), f"absorvido em {ident}")).rowcount
    extra = f" ({juntas + 1} mensagens suas estavam juntas nesse pedido)" if juntas else ""
    enviar_texto(dono(), f"⚠️ Uma resposta foi interrompida quando a janela fechou{extra}. Guardei o pedido e vou precisar conferir o que foi feito antes de repetir.")

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
    # 15 anexo que não baixa (bug S5 23/09/26): aviso honesto no TEXTO, nunca rotulado como caminho de arquivo
    global api, baixar, JOB
    _baixar = baixar; baixar = lambda fid, dest: None
    receber({"update_id": 13, "message": {"message_id": 21, "chat": {"id": 555}, "photo": [{"file_id": "p9"}], "caption": "olha"}})
    baixar = _baixar
    with q.connect() as db: pl = json.loads(db.execute("SELECT payload FROM jobs WHERE id='555:21'").fetchone()[0])
    chk("15 anexo que não baixa: aviso no texto (legenda preservada), sem caminho falso", pl["texto"].startswith("olha") and "AVISO" in pl["texto"] and not (pl["imagens"] or pl["arquivos"]))
    # 16 corte pelo limite real do Telegram (UTF-16): emoji conta 2
    longo = "😀" * 3000 + "\nlinha\n" + "a" * 5000
    ps = pedacos(longo)
    chk("16 corte UTF-16: nenhum pedaço passa de 4096 e juntar devolve o original", all(len(p.encode("utf-16-le")) // 2 <= 4096 for p in ps) and "".join(ps) == longo and len(ps) >= 3)
    # 17 recusa: 429 tenta de novo 1x; 400 não repete
    _api = api; JOB = None; chamadas = []
    def api_fake(resposta):
        def f(method, fields=None, *a, **k):
            chamadas.append(method)
            return resposta.pop(0) if resposta else {"ok": True, "result": {"message_id": 999}}
        return f
    api = api_fake([{"ok": False, "error_code": 429, "parameters": {"retry_after": 1}}]); ok429 = enviar_texto("555", "oi")
    n429 = len(chamadas); chamadas.clear()
    api = api_fake([{"ok": False, "error_code": 400, "description": "Bad Request"}]); ok400 = enviar_texto("555", "oi")
    api = _api
    chk("17 429 entrega na 2ª tentativa; 400 não repete e fica sem confirmação", ok429 and n429 == 2 and not ok400 and len(chamadas) == 1)
    # ---- porta (23/09/26): rajada, promessa de anexo, reação por tipo e pertinente ----
    global PORTA_RAJADA, PORTA_PROMESSA
    PORTA_RAJADA, PORTA_PROMESSA = 0.4, 1.5
    cerebro.FAKE_CLAUDE = "resposta do claude"; os.environ["MESTREOS_CEREBRO_FAKE_CLAUDE"] = "resposta do claude"
    tem_stt = lambda: True; transcrever = lambda p: "olha só isso aqui"
    def reacoes(mid): return [json.loads(f["reaction"])[0]["emoji"] for m, f, _ in DRY_API if m == "setMessageReaction" and str(f.get("message_id")) == str(mid)]
    def dono_disse(): return [json.loads(l)["texto"] for l in open(cerebro.CONVERSA, encoding="utf-8") if l.strip() and json.loads(l)["quem"] == "Dono"][-1]
    receber({"update_id": 20, "message": {"message_id": 200, "chat": {"id": 555}, "voice": {"file_id": "v200"}}})
    chk("18 reação por tipo: áudio ganha ✍ na chegada (👂 não existe pra bot)", reacoes(200)[:1] == ["✍"])
    q.drain(executar, recuperado)
    receber({"update_id": 21, "message": {"message_id": 210, "chat": {"id": 555}, "photo": [{"file_id": "p210"}], "caption": "olha"}})
    receber({"update_id": 22, "message": {"message_id": 211, "chat": {"id": 555}, "text": "o que acha?"}})
    n0 = len(enviados()); q.drain(executar, recuperado)
    chk("19 rajada foto + texto = UMA resposta, e o 2º pedido fecha como absorvido", len(enviados()) - n0 == 1 and q.status("555:211") == "completed" and "pacote: 2" in dono_disse())
    receber({"update_id": 23, "message": {"message_id": 220, "chat": {"id": 555}, "text": "vou te mandar a foto do contrato"}})
    threading.Timer(0.6, lambda: receber({"update_id": 24, "message": {"message_id": 221, "chat": {"id": 555}, "photo": [{"file_id": "p221"}]}})).start()
    n0 = len(enviados()); q.drain(executar, recuperado)
    chk("20 promessa cumprida: segura, reage 🫡 e responde UMA vez com a foto, sem nota", len(enviados()) - n0 == 1 and "🫡" in reacoes(220) and "nota da janela" not in dono_disse() and q.status("555:221") == "completed")
    t0 = time.time(); receber({"update_id": 25, "message": {"message_id": 230, "chat": {"id": 555}, "text": "vou te enviar o pdf"}}); q.drain(executar, recuperado)
    chk("21 promessa esquecida: espera o prazo e avisa que está aguardando o pdf", time.time() - t0 >= PORTA_PROMESSA and "aguardando o anexo prometido (pdf)" in dono_disse())
    t0 = time.time(); receber({"update_id": 26, "message": {"message_id": 240, "chat": {"id": 555}, "text": "me manda a foto do relatório"}}); q.drain(executar, recuperado)
    chk("22 'me manda a foto' é pedido PRA mim: sai na hora (expresso)", time.time() - t0 < PORTA_RAJADA and "pacote" not in dono_disse())
    cerebro.FAKE_CLAUDE = "[reagir:❤️] valeu demais"
    receber({"update_id": 27, "message": {"message_id": 250, "chat": {"id": 555}, "text": "obrigado, valeu"}}); q.drain(executar, recuperado)
    chk("23 reação pertinente: [reagir:❤️] vira ❤ na mensagem e some do texto", reacoes(250)[-1:] == ["❤"] and enviados()[-1].startswith("valeu demais"))
    sim = ["vou te mandar uma foto", "te mando já já a foto", "segue o print", "vou te enviar o pdf do boleto", "deixa eu tirar uma foto aqui",
           "vou mandar aqui pra você a foto", "já te mando o comprovante", "vou encaminhar o arquivo"]
    nao = ["vou passar no mercado comprar a nota fiscal do gás", "vou passar no banco pagar o boleto", "mandei a foto ontem",
           "manda a foto pra ela", "você pode me mandar a foto?", "me manda o print", "vou tirar férias e mandar notícias"]
    chk("24 promessa: acerta as reais e não cai em 'vou passar no banco pagar o boleto' (achado do juiz)",
        all(promessa({"texto": f}) for f in sim) and not any(promessa({"texto": f}) for f in nao))
    q.enqueue("555:260", {"chat": "555", "mid": "260", "texto": "vou te mandar a foto"}); q.enqueue("555:261", {"chat": "555", "mid": "261", "texto": "(foto)"})
    with q.connect() as db:
        db.execute("UPDATE jobs SET status='running' WHERE id='555:260'")
        db.execute("UPDATE jobs SET status='absorvido', detail='absorvido em 555:260' WHERE id='555:261'")
    n0 = len(enviados()); q.drain(executar, recuperado)
    avisos = [t for t in enviados()[n0:] if "interrompida" in t]
    chk("26 troca garantida: respondeu sem escolher → 👌; pacote foto+texto → as DUAS viram 👌; motor falhou → sem 👌 (não finge que fez)",
        reacoes(13)[-1:] == ["👌"] and reacoes(210)[-1:] == ["👌"] and reacoes(211)[-1:] == ["👌"] and "👌" not in reacoes(20))
    chk("25 queda no meio de um pacote: UM aviso só (com '2 mensagens') e os dois pedidos ficam incertos, sem repetir",
        len(avisos) == 1 and "2 mensagens" in avisos[0] and q.status("555:260") == "uncertain" and q.status("555:261") == "uncertain")
    print(f"----- {ok} ok · {fail} falhas"); return 0 if fail == 0 else 1

if __name__ == "__main__":
    if "--teste" in sys.argv: sys.exit(teste())
    if "--status" in sys.argv: status(); sys.exit(0)
    if "--recover" in sys.argv: sys.exit(recover())
    sys.exit(janela() or 0)
