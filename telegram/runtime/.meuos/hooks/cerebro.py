#!/usr/bin/env python3
"""cerebro.py — a "Dupla" simétrica do MestreOS (PASSO 7D): Claude Code e Codex no MESMO bot de Telegram,
sem que nenhum motor seja dono da janela.

A janela do bot é a `telegram_janela.py` (neutra, em Python). Ela recebe a mensagem, transcreve o áudio se houver
provedor e chama `responder()` daqui. Este módulo decide QUEM responde (o motor ativo) e devolve as ações (textos,
arquivos) que a janela entrega no celular. Nada aqui fala com o Telegram: quem envia é a janela, com recibo.

Motores: `claude` (Claude Code em modo `-p`, sessão retomada com `--resume`) e `codex` (Codex `exec`, thread retomada).
Cada aluno tem um motor PRINCIPAL (o que ele já usa) e, se assinar o outro, um SECUNDÁRIO. Frases no Telegram, nos
dois sentidos: "troca pro Codex / Sol / Terra / Luna / Astra" · "volta pro Claude / Opus / Sonnet / Haiku" ·
"qual cérebro tá ligado?". Continuidade nos dois sentidos: quem sai deixa um resumo pro que entra.
Mac e Windows (Python 3, sem dependências). Estado em ~/.mestreos/telegram/<id-da-pasta>/ (disco local, fora do Drive).
Self-test (sem Telegram, sem IA): python3 cerebro.py --teste · Status: --status · Motores: --motores claude codex
"""
import json, os, re, sys, subprocess, time, unicodedata, glob, shutil, datetime, hashlib, uuid, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from telegram_runtime import Queue, activity_run
# Windows sem console (Agendador) usa cp1252 e estoura em emoji/acento → força UTF-8 (no Mac não muda nada)
for _s in (sys.stdout, sys.stderr, sys.stdin):
    if hasattr(_s, "reconfigure"):
        try: _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception: pass

H = os.path.expanduser("~")
AQUI = os.path.dirname(os.path.abspath(__file__))
OS_DIR = os.environ.get("MESTREOS_DIR") or os.path.dirname(os.path.dirname(AQUI))          # <OS>/.meuos/hooks → <OS>
STATE = os.environ.get("MESTREOS_CEREBRO_STATE") or os.path.join(H, ".mestreos", "telegram", hashlib.sha256(os.path.normcase(OS_DIR).encode()).hexdigest()[:16])
PROJ_SLUG = "-" + re.sub(r"[^A-Za-z0-9]", "-", OS_DIR.lstrip("/")) if not OS_DIR[1:3] == ":\\" else "-" + re.sub(r"[^A-Za-z0-9]", "-", OS_DIR)
MEMDIR = os.environ.get("MESTREOS_MEMORIA_DIR") or os.path.join(H, ".claude", "projects", PROJ_SLUG, "memory")
CODEX = os.environ.get("MESTREOS_CODEX_BIN") or shutil.which("codex") or shutil.which("codex.cmd") or "/Applications/ChatGPT.app/Contents/Resources/codex"
CLAUDE = os.environ.get("MESTREOS_CLAUDE_BIN") or shutil.which("claude") or shutil.which("claude.cmd") or "claude"
FAKE_CODEX = os.environ.get("MESTREOS_CEREBRO_FAKE_CODEX"); FAKE_CLAUDE = os.environ.get("MESTREOS_CEREBRO_FAKE_CLAUDE")
LOGF = os.path.join(STATE, "cerebro.log"); SF = os.path.join(STATE, "cerebro.json"); CONVERSA = os.path.join(STATE, "conversa.jsonl")
TIMEOUT = int(os.environ.get("MESTREOS_CEREBRO_TIMEOUT", "900"))   # por INATIVIDADE (stdout), não por duração total
IMG = (".png", ".jpg", ".jpeg", ".webp", ".gif"); AUD = (".oga", ".ogg", ".mp3", ".m4a", ".wav", ".opus")
MODELOS_CODEX = {"sol": "gpt-5.6-sol", "terra": "gpt-5.6-terra", "luna": "gpt-5.6-luna", "astra": "gpt-6-astra"}
MODELOS_CLAUDE = {"opus": "opus", "sonnet": "sonnet", "haiku": "haiku", "fable": "fable"}
EMOJI = {"sol": "☀️", "terra": "🌍", "luna": "🌙", "astra": "✨", "claude": "🟣"}
# ferramentas que o Claude pode usar sozinho pelo Telegram (mesmo espírito do sandbox do Codex: ler e escrever no OS e na memória,
# sem terminal). O dono pode ampliar com MESTREOS_CLAUDE_TOOLS="Read,Edit,Write,Glob,Grep,WebFetch,WebSearch,Bash(python3 *)".
TOOLS_CLAUDE = [t.strip() for t in os.environ.get("MESTREOS_CLAUDE_TOOLS", "Read,Edit,Write,Glob,Grep,WebFetch,WebSearch").split(",") if t.strip()]

def log(m):
    try:
        os.makedirs(STATE, exist_ok=True)
        with open(LOGF, "a", encoding="utf-8") as f: f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {m}\n")
    except Exception: pass

def norm(s):
    s = unicodedata.normalize("NFD", s or "").lower(); return "".join(c for c in s if unicodedata.category(c) != "Mn")

def tem(motor):
    """o motor está instalado nesta máquina? (só o binário; login/cota é assunto do próprio motor)"""
    p = CODEX if motor == "codex" else CLAUDE
    return os.path.isfile(p) or bool(shutil.which(p))

# ---------- estado ----------
def novo_estado(principal=None, secundario=None):
    if not principal:
        principal = "claude" if tem("claude") else "codex"
        secundario = ("codex" if tem("codex") else None) if principal == "claude" else ("claude" if tem("claude") else None)
    return {"versao": 2, "principal": principal, "secundario": secundario, "ativo": principal,
            "claude": {"sessao": None, "modelo": None}, "codex": {"thread": None, "modelo": MODELOS_CODEX["sol"]},
            "desde": time.strftime("%d/%m %H:%M"), "resumo_pendente": None}

def load():
    try:
        with open(SF, encoding="utf-8") as f: st = json.load(f)
    except Exception: return novo_estado()
    if st.get("versao") != 2:  # estado do 7C (Claude dono do bot): migra sem perder a conversa do Codex
        novo = novo_estado("claude", "codex" if tem("codex") else None)
        if st.get("empresa") == "openai":
            novo["ativo"] = "codex"; novo["codex"] = {"thread": st.get("thread"), "modelo": st.get("modelo") or MODELOS_CODEX["sol"]}
        return novo
    return st

def save(st):
    os.makedirs(STATE, exist_ok=True); tmp = SF + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, SF)

def nome_modelo(motor, modelo):
    if motor == "codex":
        m = re.search(r"-(sol|terra|luna|astra)\b", modelo or ""); return m.group(1).capitalize() if m else (modelo or "OpenAI")
    m = re.search(r"(opus|sonnet|haiku|fable)[-\s]?(\d+)?(?:[-.](\d+))?", modelo or "")
    if not m: return "Claude"
    v = (m.group(2) or "") + (("." + m.group(3)) if m.group(3) else "")
    return f"{m.group(1).capitalize()}{(' ' + v) if v else ''}"

def assinatura(motor, modelo=None):
    if motor == "codex":
        m = re.search(r"-(sol|terra|luna|astra)\b", modelo or ""); return f"{EMOJI.get(m.group(1), '🟢') if m else '🟢'} {nome_modelo('codex', modelo)}"
    return f"🟣 Claude · {nome_modelo('claude', modelo)}" if modelo else "🟣 Claude"

def status_txt(st):
    outro = st.get("secundario")
    ativo = st["ativo"]; modelo = st[ativo].get("modelo")
    base = f"🧠 Cérebro ligado: {assinatura(ativo, modelo)} desde {st.get('desde', '?')} (principal: {st['principal'].capitalize()})."
    if not outro: return base + " Você tem só este motor; se um dia assinar o outro, ele entra como secundário sem desinstalar nada."
    dica = '"troca pro Codex" (Sol; ou Terra, Luna, Astra)' if outro == "codex" else '"troca pro Claude" (ou Opus, Sonnet, Haiku)'
    return base + f" Pra trocar: {dica}."

# ---------- continuidade (a janela grava a conversa; quem sai deixa um resumo) ----------
def registrar(quem, texto):
    try:
        os.makedirs(STATE, exist_ok=True)
        with open(CONVERSA, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "quem": quem, "texto": (texto or "")[:600]}, ensure_ascii=False) + "\n")
    except Exception: pass

def ultimas_trocas(n=16):
    try:
        linhas = open(CONVERSA, "rb").read()[-200_000:].decode("utf-8", "ignore").splitlines()
        out = []
        for ln in linhas:
            try: d = json.loads(ln)
            except Exception: continue
            out.append(f"- {d.get('quem')}: {(d.get('texto') or '').replace(chr(10), ' ')[:400]}")
        return "\n".join(out[-n:])
    except Exception: return ""

# ---------- motores ----------
def instrucoes(motor):
    hoje = datetime.date.today().isoformat(); out_dir = os.path.join(OS_DIR, "outputs", "imagens", hoje)
    return (f"[Modo Telegram · janela do MestreOS. Você é o agente do dono deste OS (mesma personalidade, regras e skills de sempre; "
            f"{'leia AGENTS.md desta pasta' if motor == 'codex' else 'seu claude.md e soul.md já estão carregados'}). "
            f"A mensagem abaixo chegou pelo Telegram dele. Responda em português, curto, texto puro (sem markdown pesado): o que você "
            f"escrever como resposta final é o que ele vai receber no celular. Não assine. Memória do agente: {MEMDIR} (leia MEMORY.md e só os "
            f"arquivos que a pergunta pedir; grave feedback/decisão lá também). Arquivo que você quiser mandar pro celular: salve em {out_dir}/ "
            f"(tudo que aparecer lá eu envio). Skill `salvar` e os outros ritos do OS valem aqui igual. Você NÃO consegue trocar de cérebro: "
            f"se ele pedir, responda só: 'pra trocar, manda: troca pro Codex' (ou 'volta pro Claude'). Seja rápido: não varra pastas nem skills "
            f"sem necessidade. Reação: a janela já pôs ✍ (áudio) ou 👀 na mensagem dele; se couber uma reação pertinente, comece a resposta com "
            f"[reagir:EMOJI] usando um destes: ❤ agradecimento, 🔥 empolgação, 🙏 desculpa, 👍 ok, 🤝 combinado, 😁 graça, 🎉 comemoração, 😢 notícia ruim, 🫡 ordem dada "
            f"(sem essa marca, a janela põe 👌 quando a resposta sai). "
            f"Pacote de várias mensagens = uma resposta só.]")

def prefixo_continuidade(st, motor):
    p = ""
    rp = st.get("resumo_pendente")
    if rp and rp.get("para") == motor and rp.get("texto"):
        p += f"\n[Continuidade: você acabou de assumir a conversa. Resumo deixado pelo outro cérebro ({rp.get('de', '?')}):\n{rp['texto']}\n]\n"
    tr = ultimas_trocas()
    if tr and (rp or not st[motor].get("thread" if motor == "codex" else "sessao")):
        p += f"\n[Últimas trocas pelo Telegram (\"Agente\" é o cérebro que respondia antes):\n{tr}\n]\n"
    return p

def novos_arquivos(antes):
    hoje = datetime.date.today().isoformat(); out_dir = os.path.join(OS_DIR, "outputs", "imagens", hoje)
    return [n for n in sorted(set(glob.glob(os.path.join(out_dir, "*"))) - antes, key=os.path.getmtime) if os.path.isfile(n)]

def _out_dir_antes():
    hoje = datetime.date.today().isoformat(); out_dir = os.path.join(OS_DIR, "outputs", "imagens", hoje)
    try: os.makedirs(out_dir, exist_ok=True)
    except OSError as e: log(f"pasta de saída indisponível ({e.__class__.__name__}); sigo sem envio de arquivos")
    return set(glob.glob(os.path.join(out_dir, "*")))

def codex_command():
    if str(CODEX).lower().endswith((".cmd", ".bat")):
        # Não passar prompt do Telegram por cmd.exe (metacaracteres virariam comandos).
        js = os.path.join(os.path.dirname(CODEX), "node_modules", "@openai", "codex", "bin", "codex.js")
        node = shutil.which("node")
        if not node or not os.path.isfile(js):
            raise RuntimeError("Instalação Codex/npm não reconhecida; conferir executável nativo")
        return [node, js]
    return [CODEX]

def motor_codex(st, prompt, imagens, batimento=None):
    """Roda o Codex (sandbox workspace-write, thread retomada). Devolve (ok, resposta, arquivos_novos, erro)."""
    c = st["codex"]; outf = os.path.join(STATE, "ultima-codex.txt"); antes = _out_dir_antes()
    try: os.remove(outf)
    except FileNotFoundError: pass
    ULTIMA.update(lida=False, ferramentas=0)
    if FAKE_CODEX:
        if FAKE_CODEX.startswith("ERRO:"): ULTIMA.update(lida=True); return False, "", [], FAKE_CODEX[5:]
        if FAKE_CODEX.startswith("ERRO_DEPOIS:"): ULTIMA.update(lida=True, ferramentas=1); return False, "", [], FAKE_CODEX[12:]
        c["thread"] = c.get("thread") or "fake-thread"; return True, FAKE_CODEX, [], ""
    roots = 'sandbox_workspace_write.writable_roots=["' + MEMDIR.replace("\\", "/") + '","' + os.path.join(OS_DIR, "outputs").replace("\\", "/") + '"]'
    comum = ["--skip-git-repo-check", "-m", c["modelo"], "-c", roots, "-c", "sandbox_workspace_write.network_access=true", "-o", outf]
    if c.get("thread"):
        cmd = codex_command() + ["exec", "resume", "--json", "-c", 'sandbox_mode="workspace-write"'] + comum
        for i in imagens: cmd += ["-i", i]
        cmd += [c["thread"], prompt]
    else:
        cmd = codex_command() + ["exec", "--json", "-C", OS_DIR, "-s", "workspace-write"] + comum
        for i in imagens: cmd += ["-i", i]
        cmd += [prompt]
    try: r = activity_run(cmd, cwd=OS_DIR, timeout=TIMEOUT)
    except subprocess.TimeoutExpired: return False, "", [], f"ficou sem atividade por {TIMEOUT // 60} min; resultado precisa de conferência"
    for ln in (r.stdout or "").splitlines():
        try: d = json.loads(ln)
        except Exception: continue
        if isinstance(d, dict) and d.get("type") == "thread.started" and d.get("thread_id"): c["thread"] = d["thread_id"]
        if isinstance(d, dict) and d.get("type") in ("thread.started", "turn.started"): ULTIMA["lida"] = True
        it = d.get("item") if isinstance(d, dict) else None
        if isinstance(it, dict) and it.get("type") not in (None, "agent_message", "reasoning", "todo_list", "error"): ULTIMA["ferramentas"] += 1
    resp = ""
    try:
        with open(outf, encoding="utf-8") as f: resp = f.read().strip()
    except Exception: pass
    if r.returncode != 0 or not resp:
        erro = ""
        for ln in (r.stderr or "").splitlines() + (r.stdout or "").splitlines():
            m = re.search(r'"message":"([^"]{0,160})"', ln)
            if m and "chronicle" not in m.group(1): erro = m.group(1); break
        bruto = (r.stderr or "") + "\n" + (r.stdout or "")
        if causa_conhecida(bruto) and not causa_conhecida(erro): erro = bruto[-600:]
        return False, "", [], erro or f"código {r.returncode}"
    return True, resp, novos_arquivos(antes), ""

def motor_claude(st, prompt, imagens, batimento=None):
    """Roda o Claude Code em modo -p (sessão retomada). Devolve (ok, resposta, arquivos_novos, erro)."""
    c = st["claude"]; antes = _out_dir_antes()
    ULTIMA.update(lida=False, ferramentas=0)
    if FAKE_CLAUDE:
        if FAKE_CLAUDE.startswith("ERRO:"): ULTIMA.update(lida=True); return False, "", [], FAKE_CLAUDE[5:]
        if FAKE_CLAUDE.startswith("ERRO_DEPOIS:"): ULTIMA.update(lida=True, ferramentas=1); return False, "", [], FAKE_CLAUDE[12:]
        c["sessao"] = c.get("sessao") or "fake-sessao"; c["modelo"] = c.get("modelo") or "claude-fake-1"; return True, FAKE_CLAUDE, [], ""
    if imagens: prompt += "\n[Fotos anexas (abra com a ferramenta Read): " + ", ".join(imagens) + "]"
    cmd = [CLAUDE, "-p", "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits",
           "--append-system-prompt", instrucoes("claude"), "--add-dir", MEMDIR]
    if TOOLS_CLAUDE: cmd += ["--allowedTools"] + TOOLS_CLAUDE
    if c.get("modelo_pedido"): cmd += ["--model", c["modelo_pedido"]]
    if c.get("sessao"): cmd += ["--resume", c["sessao"]]
    else: c["sessao"] = str(uuid.uuid4()); cmd += ["--session-id", c["sessao"]]
    try: r = _run_stdin(cmd, prompt)
    except subprocess.TimeoutExpired: return False, "", [], f"ficou sem atividade por {TIMEOUT // 60} min; resultado precisa de conferência"
    resp, ok, erro = "", False, ""
    for ln in (r.stdout or "").splitlines():
        try: d = json.loads(ln)
        except Exception: continue
        if isinstance(d, dict) and d.get("type") == "system": ULTIMA["lida"] = True
        if isinstance(d, dict) and d.get("type") == "assistant":
            ULTIMA["ferramentas"] += sum(1 for b in ((d.get("message") or {}).get("content") or []) if isinstance(b, dict) and b.get("type") == "tool_use")
        if isinstance(d, dict) and d.get("type") == "result":
            resp = (d.get("result") or "").strip(); ok = not d.get("is_error") and d.get("subtype") == "success"
            if d.get("session_id"): c["sessao"] = d["session_id"]
            usados = list((d.get("modelUsage") or {}).keys())
            if usados: c["modelo"] = usados[-1]
            if not ok: erro = d.get("subtype") or "erro"
    if r.returncode != 0 and not resp:
        m = re.search(r"(?i)(error|erro)[^\n]{0,160}", r.stderr or ""); erro = erro or (m.group(0) if m else f"código {r.returncode}")
        # sessão que não existe mais (apagada/limpa) → recomeça na próxima
        if c.get("sessao") and re.search(r"(?i)no conversation|not found|session", r.stderr or ""): c["sessao"] = None
    bruto = resp + "\n" + (r.stderr or "")
    if (not ok or not resp or r.returncode != 0) and causa_conhecida(bruto): return False, "", [], bruto[-600:]
    if not ok or not resp: return False, "", [], erro or "sem resposta"
    return True, resp, novos_arquivos(antes), ""

def _run_stdin(cmd, prompt):
    """activity_run com o prompt pelo stdin (nunca no argv: no Windows o claude.cmd passa por cmd.exe)."""
    import queue as _q
    p = subprocess.Popen(cmd, cwd=OS_DIR, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    def escrever():
        try: p.stdin.write(prompt.encode("utf-8")); p.stdin.close()
        except Exception: pass
    threading.Thread(target=escrever, daemon=True).start()
    events = _q.Queue()
    def read(stream, kind):
        try:
            for line in iter(stream.readline, b""): events.put((kind, line))
        finally: stream.close(); events.put((kind, None))
    for stream, kind in ((p.stdout, "out"), (p.stderr, "err")): threading.Thread(target=read, args=(stream, kind), daemon=True).start()
    data = {"out": [], "err": []}; ends = 0; last = time.monotonic()
    try:
        while ends < 2:
            remaining = TIMEOUT - (time.monotonic() - last)
            if remaining <= 0: raise subprocess.TimeoutExpired(cmd[0], TIMEOUT)
            try: kind, line = events.get(timeout=min(remaining, .2))
            except _q.Empty: continue
            if line is None: ends += 1
            else:
                if kind == "out": last = time.monotonic()
                data[kind].append(line)
        p.wait(timeout=max(.1, TIMEOUT - (time.monotonic() - last)))
    except BaseException:
        p.kill(); p.wait(); raise
    return subprocess.CompletedProcess(cmd, p.returncode, b"".join(data["out"]).decode("utf-8", "replace"), b"".join(data["err"]).decode("utf-8", "replace"))

RE_LOGIN = re.compile(r"(?i)not logged in|login expired|please run /login|invalid api key|oauth token[^\n]{0,30}expired|authentication_error|401 unauthorized|please log ?in|run `?codex login")
RE_COTA = re.compile(r"(?i)usage limit|hit your (usage )?limit|limit reached|quota|credit balance is too low|rate limit")
RE_VOLTA_COTA = re.compile(r"(?i)(?:try again (?:at|in)|resets(?: at| in)?) ([^.\n\"]{2,60})")
COTA_PADRAO = 5 * 3600  # sem hora legível na mensagem: tenta de novo em 5 h (se ainda estiver preso, troca de novo)

def volta_em(texto, agora=None):
    """'3:05 PM' · '6am (America/Sao_Paulo)' · 'in 2 hours' · '14:30' → epoch da próxima vez que isso acontece."""
    agora = agora or time.time(); t = (texto or "").lower()
    tz = None  # juiz 23/09: hora escrita num fuso ("6am (America/Sao_Paulo)", "UTC") é lida nesse fuso
    try:
        from zoneinfo import ZoneInfo
        mz = re.search(r"\(([A-Za-z_]+/[A-Za-z_]+(?:/[A-Za-z_]+)?)\)", texto or "")
        tz = ZoneInfo(mz.group(1)) if mz else (datetime.timezone.utc if re.search(r"\butc\b", t) else None)
    except Exception: tz = datetime.timezone.utc if re.search(r"\butc\b", t) else None
    MESES = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
    m = re.search(r"\b([a-z]{3})[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4}),?\s+(\d{1,2}):(\d{2})\s*(am|pm)?", t)
    if m and m.group(1) in MESES:  # data completa do Codex: "Sep 19th, 2026 7:01 AM"
        h = int(m.group(4)) % 12 + (12 if m.group(6) == "pm" else 0) if m.group(6) else int(m.group(4))
        try:
            d = datetime.datetime(int(m.group(3)), MESES[m.group(1)], int(m.group(2)), h, int(m.group(5)), tzinfo=tz).timestamp()
            return d if d > agora else agora + COTA_PADRAO
        except ValueError: pass
    m = re.search(r"in (\d+)\s*(hour|hr|h\b|minute|min)", t)
    if m: return agora + int(m.group(1)) * (3600 if m.group(2).startswith("h") else 60)
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", t) or re.search(r"\b(\d{1,2}):(\d{2})\b()", t)
    if m:
        h, mi = int(m.group(1)) % 24, int(m.group(2) or 0)
        if m.group(3) == "pm" and h < 12: h += 12
        if m.group(3) == "am" and h == 12: h = 0
        d = datetime.datetime.fromtimestamp(agora, tz).replace(hour=h, minute=mi, second=0, microsecond=0)
        if d.timestamp() <= agora: d += datetime.timedelta(days=1)
        return d.timestamp()
    return agora + COTA_PADRAO

def quando_txt(ts):
    d = datetime.datetime.fromtimestamp(ts)
    return d.strftime("%H:%M") if d.date() == datetime.date.today() else d.strftime("%d/%m %H:%M")

def causa_conhecida(texto):
    """stderr/resultado do motor → ("login", "") | ("cota", "quando volta") | None. Sem isso o dono recebia só 'código 1'."""
    t = texto or ""
    if RE_LOGIN.search(t): return ("login", "")
    if RE_COTA.search(t):
        m = RE_VOLTA_COTA.search(t); return ("cota", m.group(1).strip() if m else "")
    return None

def aviso_falha(st, motor, erro):
    quem = "Claude" if motor == "claude" else "Codex"
    outro = st.get("secundario") if st["ativo"] == st["principal"] else st["principal"]
    troca = f" Enquanto isso, \"troca pro {'Codex' if outro == 'codex' else 'Claude'}\" que eu sigo com o outro." if outro else ""
    causa = causa_conhecida(erro)
    if causa and causa[0] == "login":
        cmd = "claude auth login" if motor == "claude" else "codex login"
        return f"🔑 O {quem} perdeu o login neste computador. Abra o Terminal, rode `{cmd}`, entre na sua conta e me mande a mensagem de novo. Não fiz nada do seu pedido.{troca}"
    if causa and causa[0] == "cota":
        volta = f" Volta em: {causa[1]}." if causa[1] else ""
        return f"⏳ O {quem} bateu no limite do plano.{volta} Não fiz nada do seu pedido; quando o limite voltar, é só mandar de novo.{troca}"
    quem_modelo = "Claude" if motor == "claude" else nome_modelo("codex", st["codex"].get("modelo"))
    return (f"⚠️ O cérebro {quem_modelo} parou antes de concluir ({(erro or 'sem detalhe')[:120]}). Guardei seu pedido; não repeti nada sozinho."
            + (f" Se quiser, \"troca pro {'Codex' if outro == 'codex' else 'Claude'}\" pra seguir com o outro." if outro else ""))

MOTORES = {"codex": motor_codex, "claude": motor_claude}
ULTIMA = {"lida": False, "ferramentas": 0}  # lida = a saída do motor foi lida; ferramentas = quantas ele usou antes de parar

def resumir(st, motor):
    """pede ao motor que está saindo um resumo da conversa (continuidade pro outro). Sem conversa = sem resumo."""
    houve = bool(st["codex"].get("thread")) if motor == "codex" else bool(st["claude"].get("sessao"))
    if not houve: return ""
    if (motor == "codex" and FAKE_CODEX) or (motor == "claude" and FAKE_CLAUDE): return "(resumo fake)"
    p = "[O dono vai trocar de cérebro] Resuma em até 12 linhas o que rolou nesta conversa pelo Telegram: assuntos, decisões, pendências, arquivos, o que ele esperava. Texto puro, sem ferramentas."
    try:
        ok, resp, _, _ = MOTORES[motor](st, p, [])
        return resp[:3000] if ok else "(não consegui resumir)"
    except Exception as e: log(f"resumo {motor}: {e!r}"); return "(não consegui resumir)"

# ---------- comandos (ditado erra nome próprio: "Claudio", "cloud", "codecs", "códex"… → aceitar as variações) ----------
VERBOS = r"(troca|trocar|muda|mudar|liga|ligar|ativa|ativar|usa|usar|passa|passar|bota|botar|coloca|colocar|volta|voltar|volte|retorna|retornar|devolve|devolver)"
RE_CMD = re.compile(r"\b" + VERBOS + r"\b(?:\s+(?:pro|pra|para|o|a|no|na|de|do|pelo|pela|modelo|cerebro|ai|com|ao))*\s+([a-z][a-z0-9.-]*)\b")
RE_STATUS = re.compile(r"\b(qual|que|quem)\b.*\b(cerebro|modelo|respondendo|ligado|ativo)\b")

def alvo(palavra):
    """palavra ditada → (motor, modelo) ou None."""
    p = palavra.lower()
    if p.startswith(("claud", "cloud", "clode", "anthropic", "antropic")): return ("claude", None)
    for k in MODELOS_CLAUDE:
        if p.startswith(k[:4]): return ("claude", k)
    if p.startswith(("codex", "codec", "codes", "code", "openai", "chatgpt", "gpt")): return ("codex", "sol")  # "codigo" fica de fora
    if p.startswith("astra"): return ("codex", "astra")
    if p.startswith("terra"): return ("codex", "terra")
    if p.startswith("luna") or p == "lua": return ("codex", "luna")
    if p == "sol": return ("codex", "sol")
    return None

def comando(n):
    """texto normalizado → ('status',) | ('troca', motor, modelo) | None"""
    if len(n) >= 120: return None
    if RE_STATUS.search(n) and ("cerebro" in n or "respondendo" in n or ("modelo" in n and "ligado" in n)): return ("status",)
    for m in RE_CMD.finditer(n):
        a = alvo(m.group(2))
        if not a: continue
        motor, modelo = a
        if not modelo:  # "muda pra Anthropic no modelo sonnet" → o modelo pode vir depois do alvo
            for w in n[m.end():].split():
                b = alvo(w)
                if b and b[0] == motor and b[1]: modelo = b[1]; break
        return ("troca", motor, modelo)
    return None

def trocar(st, motor, modelo, resumo=True):
    """executa a troca (nos dois sentidos) e devolve o texto pro celular. resumo=False: o motor que sai está sem cota."""
    if motor not in (st["principal"], st.get("secundario")):
        if not tem(motor):
            return (f"🤔 Você só tem o {st['principal'].capitalize()} nesta máquina. Quando assinar o "
                    f"{'Codex' if motor == 'codex' else 'Claude Code'}, é só rodar o PASSO 7D do instalador que ele entra como secundário, sem desinstalar nada.")
        st["secundario"] = motor  # instalou depois: entra como secundário na hora
    if motor == "codex":
        novo_modelo = MODELOS_CODEX.get(modelo or "sol", MODELOS_CODEX["sol"])
        mudou_modelo = st["codex"].get("modelo") != novo_modelo
        st["codex"]["modelo"] = novo_modelo
        if mudou_modelo: st["codex"]["thread"] = None  # modelo novo = conversa nova (o resumo abaixo mantém o fio)
    else:
        pedido = MODELOS_CLAUDE.get(modelo) if modelo else None
        mudou_modelo = bool(pedido) and st["claude"].get("modelo_pedido") != pedido
        if pedido: st["claude"]["modelo_pedido"] = pedido
    if st["ativo"] == motor and not mudou_modelo:
        return f"{assinatura(motor, st[motor].get('modelo'))} já está ligado. Pode mandar."
    de = st["ativo"]
    if de != motor:
        resumo = resumir(st, de) if resumo else ""
        st["resumo_pendente"] = {"de": assinatura(de, st[de].get("modelo")), "para": motor, "texto": resumo} if resumo else None
    st["ativo"] = motor; st["desde"] = time.strftime("%d/%m %H:%M"); save(st)
    log(f"troca {de} → {motor} ({st[motor].get('modelo')})")
    nome = "OpenAI" if motor == "codex" else "Anthropic"
    return f"{assinatura(motor, st[motor].get('modelo') or (MODELOS_CLAUDE.get(modelo) if motor == 'claude' else None))} ligado. Sou eu mesmo, só que pensando com a {nome}. Pode continuar de onde parou."

# ---------- entrada da janela ----------
REACOES_OK = {"❤", "🔥", "🙏", "👍", "🤝", "😁", "🎉", "👌", "💯", "🫡", "🤔", "😢", "🤣", "😍", "👏"}
RE_REAGIR = re.compile(r"^\s*\[reagir:\s*([^\]\s]{1,4})\s*\]\s*")

def responder(msg, batimento=None):
    """msg = {"chat","mid","user","ts","texto","imagens":[...],"audios":[...],"transcricoes":[...],"arquivos":[...]}
    → lista de ações pra janela entregar: [("texto", str), ("arquivo", caminho), ...]. Nunca fala com o Telegram."""
    st = load(); texto = (msg.get("texto") or "").strip(); transc = [t for t in (msg.get("transcricoes") or []) if t]
    falado = " ".join(transc).strip()
    n = norm(texto or falado)
    cmd = comando(n)
    if cmd:
        registrar("Dono", texto or falado)
        if cmd[0] == "status": out = status_txt(st)
        else:
            if st.pop("auto", None): save(st); log("troca manual: volta automática cancelada")
            out = trocar(st, cmd[1], cmd[2])
        registrar("Agente", out); return [("texto", out)]
    antes_acoes = []
    auto = st.get("auto") or {}
    if auto.get("de") and time.time() >= auto.get("volta_em", 0) and st["ativo"] != auto["de"] and auto["de"] in (st["principal"], st.get("secundario")):
        # 4.3.0: a cota do motor que tinha estourado já voltou → volta sozinho pra ele (com o resumo do que rolou no outro)
        quem = "Claude" if auto["de"] == "claude" else "Codex"
        trocar(st, auto["de"], None); st = load(); st.pop("auto", None); save(st)
        antes_acoes.append(("texto", f"🔙 A cota do {quem} voltou. Voltei pra ele."))
        log(f"volta automática → {auto['de']}")
    motor = st["ativo"]
    envelope = (f'<channel source="mestreos-telegram" chat_id="{msg.get("chat")}" message_id="{msg.get("mid")}" user="{msg.get("user", "")}" '
                f'ts="{msg.get("ts", "")}">{texto}</channel>')
    if transc: envelope += "\n" + "\n".join(f"[áudio do dono, transcrito: {t}]" for t in transc)
    if msg.get("audios") and not transc: envelope += "\n[o dono mandou um áudio e a janela não conseguiu transcrever; peça em texto, sem inventar o conteúdo]"
    if msg.get("arquivos"): envelope += "\n[arquivos anexos (caminhos locais): " + ", ".join(msg["arquivos"]) + "]"
    prompt = (instrucoes("codex") + "\n" if motor == "codex" else "") + prefixo_continuidade(st, motor) + envelope
    registrar("Dono", texto + ((" [áudio: " + falado + "]") if falado else "") + (" [foto]" if msg.get("imagens") else ""))
    t0 = time.time()
    try: ok, resp, novos, erro = MOTORES[motor](st, prompt, msg.get("imagens") or [], batimento)
    except Exception as e:
        ok, resp, novos, erro = False, "", [], f"{type(e).__name__}"
    save(st)  # thread/sessão preservadas mesmo depois de falha
    if not ok:
        log(f"{motor} falhou ({time.time() - t0:.0f}s): {erro}")
        causa = causa_conhecida(erro)
        outro = st.get("secundario") if motor == st["principal"] else st["principal"]
        preso = (st.get("cota") or {}).get(outro, 0) > time.time() if outro else True
        if causa and causa[0] == "cota" and outro and not preso and not msg.get("_retentativa"):
            # 4.3.0 anti-mudo: cota estourada → troca SOZINHO pro outro motor e volta quando liberar
            volta = volta_em(causa[1]); st.setdefault("cota", {})[motor] = volta
            trocar(st, outro, None, resumo=False); st = load()
            st.setdefault("cota", {})[motor] = volta; st["auto"] = {"de": motor, "volta_em": volta}; save(st)
            quem, qo = ("Claude" if motor == "claude" else "Codex"), ("Codex" if outro == "codex" else "Claude")
            aviso = f"⏳ O {quem} bateu no limite do plano (volta às {quando_txt(volta)}). Passei pro {qo} sozinho e volto pro {quem} quando liberar."
            log(f"troca automática {motor} → {outro} por cota (volta {quando_txt(volta)})")
            if ULTIMA["lida"] and ULTIMA["ferramentas"] == 0 and not novos:  # PROVA de que nada foi feito: o outro responde já
                return antes_acoes + [("texto", aviso)] + responder(dict(msg, _retentativa=True), batimento)
            return antes_acoes + [("texto", aviso + " Seu pedido parou no meio; me mande de novo que eu sigo daqui."), ("falha", (erro or "")[:200])]
        return antes_acoes + [("texto", aviso_falha(st, motor, erro)), ("falha", (erro or "")[:200])]  # "falha" = a janela marca o pedido como incerto, nunca repete
    st["resumo_pendente"] = None; save(st)
    registrar("Agente", resp)
    log(f"respondido por {motor} ({st[motor].get('modelo')}) em {time.time() - t0:.0f}s ({len(msg.get('imagens') or [])} img, {len(transc)} áudio, {len(novos)} arquivos)")
    reacao = RE_REAGIR.match(resp or "")
    if reacao: resp = resp[reacao.end():].lstrip()
    emoji = reacao.group(1).replace("\ufe0f", "") if reacao else ""  # "❤️" do modelo → "❤" que o Telegram aceita
    acoes = antes_acoes + ([("reagir", emoji)] if emoji in REACOES_OK else [])
    acoes += [("texto", resp + "\n\n" + assinatura(motor, st[motor].get("modelo")))]
    acoes += [("arquivo", a) for a in novos]
    return acoes

# ---------- self-test (sem Telegram, sem IA): python3 cerebro.py --teste ----------
def teste():
    import tempfile
    T = tempfile.mkdtemp(); os.environ["MESTREOS_CEREBRO_STATE"] = os.path.join(T, "s")
    me = os.path.abspath(__file__); ok = fail = 0
    def run(texto, fake_codex=None, fake_claude=None, principal="claude", secundario="codex", audios=None, transc=None):
        env = dict(os.environ); env.pop("MESTREOS_CEREBRO_FAKE_CODEX", None); env.pop("MESTREOS_CEREBRO_FAKE_CLAUDE", None)
        env["MESTREOS_CLAUDE_BIN"] = os.path.join(T, "nao-existe-claude"); env["MESTREOS_CODEX_BIN"] = os.path.join(T, "nao-existe-codex")  # nunca chama IA de verdade
        if fake_codex is not None: env["MESTREOS_CEREBRO_FAKE_CODEX"] = fake_codex
        if fake_claude is not None: env["MESTREOS_CEREBRO_FAKE_CLAUDE"] = fake_claude
        msg = {"chat": "111", "mid": str(int(time.time() * 1000) % 100000), "user": "x", "ts": "t", "texto": texto, "imagens": [], "audios": audios or [], "transcricoes": transc or []}
        r = subprocess.run([sys.executable, me, "--responder", principal, secundario or "-"], input=json.dumps(msg), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        try: return json.loads(r.stdout.strip().splitlines()[-1])
        except Exception: return {"erro": r.stderr[-300:]}
    def st():  # encoding explícito: no Windows o open() sem encoding lê em cp1252 e quebra no emoji da assinatura
        p = os.path.join(T, "s", "cerebro.json")
        if not os.path.exists(p): return {}
        with open(p, encoding="utf-8") as f: return json.load(f)
    def chk(nome, cond):
        nonlocal ok, fail
        if cond: ok += 1; print("✅", nome)
        else: fail += 1; print("❌", nome)
    def txt(r): return "".join(a[1] for a in r.get("acoes", []) if a[0] == "texto")
    subprocess.run([sys.executable, me, "--motores", "claude", "codex"], capture_output=True, env=dict(os.environ))
    r = run("oi tudo bem", fake_claude="tudo ótimo");                          chk("1 principal Claude responde e assina 🟣", "tudo ótimo" in txt(r) and "🟣" in txt(r) and st()["ativo"] == "claude")
    if "tudo ótimo" not in txt(r): print("   detalhe:", json.dumps(r, ensure_ascii=False)[:600])
    r = run("qual cérebro tá ligado?");                                          chk("2 status sem chamar motor", "Cérebro ligado" in txt(r) and "Claude" in txt(r))
    r = run("troca pro codex", fake_claude="resumo do claude");                  chk("3 'troca pro codex' = Sol; resumo do Claude fica pendente", st()["ativo"] == "codex" and st()["codex"]["modelo"] == "gpt-5.6-sol" and (st().get("resumo_pendente") or {}).get("para") == "codex")
    r = run("qual é a capital de Minas?", fake_codex="BH");                      chk("4 Codex responde com assinatura ☀️ e limpa o resumo pendente", "BH" in txt(r) and "Sol" in txt(r) and not st().get("resumo_pendente"))
    r = run("salvar", fake_codex="salvo");                                       chk("5 'salvar' vai pro cérebro ativo (Codex)", "salvo" in txt(r))
    r = run("liga o astra", fake_codex="x");                                     chk("6 Sol → Astra (thread nova, mesmo motor)", st()["codex"]["modelo"] == "gpt-6-astra" and st()["ativo"] == "codex" and st()["codex"]["thread"] is None)
    r = run("e agora?", fake_codex="astra na área");                             chk("6b Astra responde e abre thread", "astra na área" in txt(r) and st()["codex"]["thread"])
    r = run("Volta para o Claudio", fake_codex="resumo do astra");               chk("7 ditado 'Claudio' → volta pro Claude com resumo do Codex", st()["ativo"] == "claude" and (st().get("resumo_pendente") or {}).get("para") == "claude")
    r = run("e aí", fake_claude="segui");                                        chk("8 Claude retoma a sessão (mesma sessão) e responde", "segui" in txt(r) and st()["claude"]["sessao"] == "fake-sessao")
    r = run("Muda pra Anthropic no modelo sonnet 5 alto", fake_claude="ok");    chk("9 'muda pra Anthropic … sonnet' já no Claude = troca de modelo, não cai no Codex", st()["ativo"] == "claude" and st()["claude"].get("modelo_pedido") == "sonnet")
    r = run("Troca pro Codecs.", fake_claude="r");                               chk("10 ditado 'Codecs' → Codex/Sol", st()["ativo"] == "codex" and st()["codex"]["modelo"] == "gpt-5.6-sol")
    r = run("troca pro plutao", fake_codex="?");                                 chk("11 alvo desconhecido = mensagem normal (vai pro motor ativo)", "?" in txt(r) and st()["ativo"] == "codex")
    r = run("liga o carro da garagem", fake_codex="carro");                      chk("12 'liga o carro' não é troca", "carro" in txt(r) and st()["ativo"] == "codex")
    r = run("", fake_codex="ouvi", audios=["/x/a.oga"], transc=["troca pro claude"]); chk("13 comando FALADO (transcrito pela janela) troca de cérebro", st()["ativo"] == "claude")
    r = run("", fake_claude="não ouvi", audios=["/x/a.oga"]);                    chk("14 áudio sem transcrição avisa o motor, não inventa conteúdo", "não ouvi" in txt(r))
    r = run("usa o codigo que te mandei", fake_claude="usei");                   chk("14b 'usa o codigo' não é troca pro Codex", "usei" in txt(r) and st()["ativo"] == "claude")
    r = run("oi", fake_claude=None, principal="claude", secundario="codex");     chk("14c motor que falha: aviso honesto + ação 'falha' (pedido vira incerto)", any(a[0] == "falha" for a in r.get("acoes", [])) and "parou antes de concluir" in txt(r))
    # 4.3.0: cota estourada no principal → troca sozinho pro secundário, refaz o pedido, e volta quando liberar
    subprocess.run([sys.executable, me, "--motores", "claude", "codex"], capture_output=True, env=dict(os.environ))
    r = run("me ajuda com a planilha", fake_claude="ERRO:You've hit your usage limit · resets 11pm", fake_codex="feito pelo codex")
    chk("17 cota no principal → troca sozinho, avisa com hora e o Codex responde o mesmo pedido",
        st()["ativo"] == "codex" and "bateu no limite" in txt(r) and "feito pelo codex" in txt(r) and (st().get("auto") or {}).get("de") == "claude" and not any(a[0] == "falha" for a in r.get("acoes", [])))
    r = run("e agora?", fake_claude="não devia", fake_codex="ainda eu");          chk("18 antes da hora de volta, segue no Codex", "ainda eu" in txt(r) and st()["ativo"] == "codex")
    s_ = st(); s_["auto"]["volta_em"] = 0
    with open(os.path.join(T, "s", "cerebro.json"), "w", encoding="utf-8") as f: json.dump(s_, f)
    r = run("voltou?", fake_claude="de volta", fake_codex="resumo do codex")
    chk("19 passou a hora → volta sozinho pro Claude, avisa e responde", st()["ativo"] == "claude" and "cota do Claude voltou" in txt(r) and "de volta" in txt(r) and not st().get("auto"))
    r = run("oi", fake_claude="ERRO:usage limit reached", fake_codex="ERRO:You've hit your usage limit. Try again at 3:05 PM")
    chk("20 os dois sem cota → aviso honesto, sem laço", "bateu no limite" in txt(r) and any(a[0] == "falha" for a in r.get("acoes", [])))
    chk("21 hora de volta: '6am', '3:05 PM', 'in 2 hours', 'Sep 19th, 2099 7:01 AM'", abs(volta_em("in 2 hours", 1000) - 8200) < 1 and datetime.datetime.fromtimestamp(volta_em("resets 6am")).hour == 6
        and datetime.datetime.fromtimestamp(volta_em("try again at 3:05 PM")).strftime("%H:%M") == "15:05"
        and datetime.datetime.fromtimestamp(volta_em("try again at Sep 19th, 2099 7:01 AM")).strftime("%d/%m/%Y %H:%M") == "19/09/2099 07:01"
        and datetime.datetime.fromtimestamp(volta_em("try again at Sep 19th, 2099 7:01 PM")).strftime("%H:%M") == "19:01")
    # juiz 23/09: só refaz com prova de que nada foi feito; troca manual cancela a volta automática; fuso da mensagem
    subprocess.run([sys.executable, me, "--motores", "claude", "codex"], capture_output=True, env=dict(os.environ))
    r = run("apaga o rascunho velho", fake_claude="ERRO_DEPOIS:You've hit your usage limit · resets 11pm", fake_codex="NÃO PODIA RODAR")
    chk("22 cota DEPOIS de usar ferramenta → troca, mas NÃO refaz (pede reenvio, marca incerto)",
        st()["ativo"] == "codex" and "NÃO PODIA RODAR" not in txt(r) and "me mande de novo" in txt(r) and any(a[0] == "falha" for a in r.get("acoes", [])))
    r = run("troca pro codex terra", fake_codex="x")
    chk("23 troca manual durante a reserva cancela a volta automática", not st().get("auto") and st()["ativo"] == "codex")
    s_ = st(); s_["auto"] = {"de": "claude", "volta_em": 0}; s_["ativo"] = "codex"
    with open(os.path.join(T, "s", "cerebro.json"), "w", encoding="utf-8") as f: json.dump(s_, f)
    r = run("troca pro codex sol", fake_codex="y"); r = run("oi", fake_claude="não devia", fake_codex="fiquei no codex")
    chk("23b depois da troca manual, a hora de volta não arrasta de volta pro Claude", "fiquei no codex" in txt(r) and st()["ativo"] == "codex")
    agora_ = datetime.datetime(2030, 1, 1, 12, 0, tzinfo=datetime.timezone.utc).timestamp()
    try:
        from zoneinfo import ZoneInfo; ZoneInfo("America/Sao_Paulo"); tem_tz = True
    except Exception: tem_tz = False  # Windows sem o pacote tzdata: cai na hora local (a UTC continua certa)
    chk("24 fuso da mensagem: '6am (America/Sao_Paulo)' = 09:00 UTC; '14:00 UTC' = 14:00 UTC",
        (not tem_tz or datetime.datetime.fromtimestamp(volta_em("resets 6am (America/Sao_Paulo)", agora_), datetime.timezone.utc).strftime("%H:%M") == "09:00")
        and datetime.datetime.fromtimestamp(volta_em("try again at 14:00 UTC", agora_), datetime.timezone.utc).strftime("%H:%M") == "14:00")
    # aluno só-Codex: principal codex, sem secundário
    subprocess.run([sys.executable, me, "--motores", "codex", "-"], capture_output=True, env=dict(os.environ))
    r = run("oi", fake_codex="opa", principal="codex", secundario=None);          chk("15 aluno só-Codex: Codex é o principal e responde", "opa" in txt(r) and st()["ativo"] == "codex")
    r = run("volta pro claude", principal="codex", secundario=None);            chk("16 só-Codex pede Claude: avisa que não tem, sem quebrar", "só tem o Codex" in txt(r) and st()["ativo"] == "codex")
    print(f"----- {ok} ok · {fail} falhas"); return 0 if fail == 0 else 1

if __name__ == "__main__":
    if "--status" in sys.argv:
        st = load()
        with Queue(STATE).connect() as db: counts = dict(db.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall())
        print(json.dumps({"state_dir": STATE, "ativo": st["ativo"], "principal": st["principal"], "secundario": st.get("secundario"), "jobs": counts}, ensure_ascii=False)); sys.exit(0)
    if "--motores" in sys.argv:  # cerebro.py --motores <principal> <secundario|->  (o instalador chama no 7D)
        i = sys.argv.index("--motores"); principal = sys.argv[i + 1]; sec = sys.argv[i + 2] if len(sys.argv) > i + 2 else "-"
        st = load(); st["principal"] = principal; st["secundario"] = None if sec == "-" else sec
        st["ativo"] = principal  # comando de instalação: liga o principal (o aluno troca por frase depois)
        save(st); print(f"principal={principal} secundario={st['secundario']} ativo={st['ativo']}"); sys.exit(0)
    if "--responder" in sys.argv:  # usado pelo --teste (processo separado, estado isolado): stdin = msg JSON
        i = sys.argv.index("--responder")
        if len(sys.argv) > i + 2 and not os.path.exists(SF):
            st = novo_estado(sys.argv[i + 1], None if sys.argv[i + 2] == "-" else sys.argv[i + 2]); save(st)
        msg = json.load(sys.stdin); out = responder(msg)
        print(json.dumps({"acoes": out}, ensure_ascii=False)); sys.exit(0)
    if "--teste" in sys.argv: sys.exit(teste())
    print("uso: cerebro.py --teste | --status | --motores <principal> <secundario|->   (a janela do bot é telegram_janela.py)"); sys.exit(2)
