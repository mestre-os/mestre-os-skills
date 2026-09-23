#!/usr/bin/env python3
"""telegram-plugin-remedio.py — remédios pra defeitos do plugin oficial de Telegram do Claude Code (MestreOS, PASSO 7A).

1. "undefined" (visto 09/09/2026): depois de uma compactação automática, a sessão chama a ferramenta `reply` com o campo
   `message` em vez de `text`; o plugin manda "undefined" pro celular. O remédio aceita `message`/`texto` como sinônimo.
2. Emoji partido (provado 23/09/2026): resposta acima de 4096 é cortada por posição; se o corte cai no meio de um emoji,
   o Telegram recusa aquele pedaço inteiro (400 "strings must be encoded in UTF-8") e a resposta chega pela metade.
   O remédio recua o corte 1 posição quando ele partiria o emoji.

Cada remédio só entra se o trecho EXATO for reconhecido; trecho desconhecido não é tocado (✗, exige auditoria).
Idempotente, com backup e reversão. Mac e Windows.
Uso: python3 telegram-plugin-remedio.py [--check | --revert]
"""
import os, sys, glob, shutil
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")

H = os.path.expanduser("~")
BASE = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(H, ".claude")
# (nome, marca, trecho original, trecho remediado, sinal de conserto EQUIVALENTE já presente, ex.: patch do dono)
REMEDIOS = [
    ("undefined", "// MESTREOS-REMEDIO-UNDEFINED",
     "        const text = args.text as string\n",
     "        const text = (args.text ?? (args as Record<string, unknown>).message ?? (args as Record<string, unknown>).texto) as string // MESTREOS-REMEDIO-UNDEFINED\n",
     "(args as Record<string, unknown>).message"),
    ("emoji partido", "// MESTREOS-REMEDIO-EMOJI",
     "    out.push(rest.slice(0, cut))\n",
     "    if (cut > 1 && rest.charCodeAt(cut - 1) >= 0xd800 && rest.charCodeAt(cut - 1) <= 0xdbff) cut-- // MESTREOS-REMEDIO-EMOJI\n"
     "    out.push(rest.slice(0, cut))\n",
     "rest.charCodeAt(cut - 1) >= 0xd800"),
]

def alvos():
    return sorted(glob.glob(os.path.join(BASE, "plugins", "cache", "claude-plugins-official", "telegram", "*", "server.ts")))

def ler(f):
    """Lê SEM traduzir fim de linha: arquivo CRLF (Windows) continua CRLF; só as linhas remediadas mudam."""
    s = open(f, encoding="utf-8", newline="").read()
    return s, ("\r\n" if "\r\n" in s else "\n")

def gravar(f, s):
    open(f, "w", encoding="utf-8", newline="").write(s)

def trechos(nl):
    return [(nome, mark, old.replace("\n", nl), new.replace("\n", nl), equiv) for nome, mark, old, new, equiv in REMEDIOS]

def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "apply"
    files = alvos()
    if not files: print("plugin de Telegram não encontrado em", BASE); return 2
    rc = 0
    for f in files:
        ver = os.path.basename(os.path.dirname(f)); s, nl = ler(f); bak = f + ".pre-remedio"; R = trechos(nl)
        if modo == "--check":
            for nome, mark, old, new, equiv in R:
                tem = mark in s or equiv in s
                print(("✓" if tem else "✗"), ver, nome, ("com remédio" if mark in s else "com conserto equivalente" if tem else "SEM remédio")); rc |= (0 if tem else 1)
            continue
        if modo == "--revert":
            achou = [nome for nome, mark, old, new, equiv in R if new in s]
            for nome, mark, old, new, equiv in R: s = s.replace(new, old)
            if achou: gravar(f, s); print("↩", ver, "revertido:", ", ".join(achou), "(outras mudanças preservadas)")
            else: print("·", ver, "sem remédio aplicado, nada a reverter")
            continue
        mudou = False
        for nome, mark, old, new, equiv in R:
            if mark in s: print("✓", ver, nome, "já com remédio"); continue
            if equiv in s: print("✓", ver, nome, "já tem conserto equivalente; não empilho outro"); continue
            if s.count(old) != 1: print("✗", ver, nome, "trecho esperado não encontrado (plugin mudou?); nada feito nesse ponto"); rc = 1; continue
            s = s.replace(old, new); mudou = True; print("✓", ver, nome, "remédio aplicado")
        if mudou:
            if not os.path.exists(bak): shutil.copy(f, bak)
            gravar(f, s); print("  backup em server.ts.pre-remedio. Carregue na próxima sessão ociosa do bot; não interrompa trabalho ativo.")
    return rc

if __name__ == "__main__": sys.exit(main())
