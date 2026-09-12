#!/usr/bin/env python3
"""telegram_send.py — manda 1 mensagem pro dono do OS no Telegram. Roda igual no Mac, no Windows e no Linux.
Uso:   python3 telegram_send.py "texto"      ou      echo "texto" | python3 telegram_send.py
       de outro script: from telegram_send import enviar; enviar("texto")
Token (nesta ordem): variável TELEGRAM_BOT_TOKEN · Cofre do sistema (Keychain 'telegram-bot-token' no Mac;
       %LOCALAPPDATA%\\MestreOS\\cofre\\telegram-bot-token.cred no Windows, DPAPI) · ~/.claude/channels/telegram/.env (plugin oficial).
Destino (nesta ordem): variável TELEGRAM_CHAT_ID · telegram-send.env ao lado deste arquivo (TELEGRAM_CHAT_ID=...) ·
       ~/.claude/channels/telegram/access.json (o primeiro número autorizado no plugin).
O token NUNCA é impresso. Sem token ou sem destino, avisa no stderr e sai com código 1 (os robôs continuam)."""
import os, sys, json, platform, subprocess, urllib.request, urllib.parse
# Windows sem console (hook/Agendador) usa cp1252 e estoura em emoji/acento → força UTF-8 (no Mac não muda nada)
for _s in (sys.stdout, sys.stderr, sys.stdin):
    if hasattr(_s, "reconfigure"):
        try: _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception: pass

AQUI = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
SISTEMA = platform.system()          # Darwin · Windows · Linux
PLUGIN_DIR = os.path.join(HOME, ".claude", "channels", "telegram")

def _limpo(s):
    return (s or "").strip().strip('"').strip("'")

def _token_keychain():
    try:
        r = subprocess.run(["security", "find-generic-password", "-s", "telegram-bot-token", "-w"],
                           capture_output=True, text=True, timeout=10)
        return _limpo(r.stdout) if r.returncode == 0 else ""
    except Exception:
        return ""

def _token_dpapi():
    f = os.path.join(os.environ.get("LOCALAPPDATA", ""), "MestreOS", "cofre", "telegram-bot-token.cred")
    if not os.path.isfile(f): return ""
    ps = ("$e = (Get-Content -Raw -LiteralPath '" + f.replace("'", "''") + "').Trim(); "
          "$s = ConvertTo-SecureString $e; "
          "$b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s); "
          "[Runtime.InteropServices.Marshal]::PtrToStringAuto($b)")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps],
                           capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not _limpo(r.stdout):
            print("telegram_send: o Cofre DPAPI existe mas não abriu (é de outro usuário do Windows? regrave pelo Cofre).", file=sys.stderr)
            return ""
        return _limpo(r.stdout)
    except Exception:
        return ""

def _token_env_plugin():
    f = os.path.join(PLUGIN_DIR, ".env")
    try:
        for l in open(f, encoding="utf-8-sig", errors="ignore"):
            if l.startswith("TELEGRAM_BOT_TOKEN="): return _limpo(l.split("=", 1)[1])
    except Exception:
        pass
    return ""

def token():
    t = _limpo(os.environ.get("TELEGRAM_BOT_TOKEN"))
    if t: return t
    if SISTEMA == "Darwin": t = _token_keychain()
    elif SISTEMA == "Windows": t = _token_dpapi()
    return t or _token_env_plugin()

def chat_id():
    c = _limpo(os.environ.get("TELEGRAM_CHAT_ID"))
    if c: return c
    try:
        for l in open(os.path.join(AQUI, "telegram-send.env"), encoding="utf-8-sig"):
            if l.startswith("TELEGRAM_CHAT_ID="): return _limpo(l.split("=", 1)[1])
    except Exception:
        pass
    try:
        a = json.load(open(os.path.join(PLUGIN_DIR, "access.json"), encoding="utf-8")).get("allowFrom") or []
        if a: return str(a[0])
    except Exception:
        pass
    return ""

def enviar(texto, destino=None, timeout=10):
    """Manda o texto. Devolve True/False. Nunca levanta exceção (robô não pode morrer por causa do aviso)."""
    tok, chat = token(), destino or chat_id()
    if not tok:
        print("telegram_send: sem token (variável, Cofre ou plugin). Mensagem não enviada.", file=sys.stderr); return False
    if not chat:
        print("telegram_send: sem destino (TELEGRAM_CHAT_ID, telegram-send.env ou access.json).", file=sys.stderr); return False
    dados = urllib.parse.urlencode({"chat_id": chat, "text": texto, "disable_web_page_preview": "true"}).encode()
    url = f"https://api.telegram.org/bot{tok}/sendMessage"
    try:
        req = urllib.request.Request(url, data=dados)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r).get("ok", False)
    except Exception as e:
        erro = type(e).__name__
    # Plano B: curl (vem no Mac e no Windows 10+; usa os certificados do sistema — resolve o
    # CERTIFICATE_VERIFY_FAILED do Python em rede com proxy/antivírus). URL e dados vão pelo stdin
    # como arquivo de config do curl (-K -): o token nunca aparece no argv nem em `ps`.
    try:
        campos = urllib.parse.urlencode({"chat_id": chat, "text": texto, "disable_web_page_preview": "true"})
        cfg = f'url = "{url}"\ndata = "{campos}"\n'
        r = subprocess.run(["curl", "-s", "--max-time", str(timeout), "-K", "-"], input=cfg, capture_output=True, text=True, timeout=timeout + 5, encoding="utf-8", errors="replace")
        if r.returncode == 0 and '"ok":true' in r.stdout.replace(" ", ""):
            return True
    except Exception:
        pass
    # a URL contém o token: nunca imprimir o erro inteiro
    print(f"telegram_send: falhou ({erro}; curl também não conseguiu)", file=sys.stderr); return False

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    if not msg.strip():
        print("uso: telegram_send.py \"texto\"  (ou texto pelo stdin)", file=sys.stderr); sys.exit(2)
    ok = enviar(msg)
    print("telegram_send: ok" if ok else "telegram_send: falhou")
    sys.exit(0 if ok else 1)
