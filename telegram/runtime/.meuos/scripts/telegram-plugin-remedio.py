#!/usr/bin/env python3
"""telegram-plugin-remedio.py — remédio pro "undefined" do plugin oficial de Telegram do Claude Code (MestreOS, PASSO 7A).

Sintoma (visto 09/09/2026): depois de uma compactação automática, a sessão chama a ferramenta `reply` com o campo
`message` em vez de `text`; o plugin manda "undefined" pro celular. Este script deixa o plugin tolerante (aceita
`message`/`texto` como sinônimo de `text`). Idempotente, com backup e reversão. Mac e Windows.
Uso: python3 telegram-plugin-remedio.py [--check | --revert]
"""
import os, sys, glob, shutil
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")

H = os.path.expanduser("~")
BASE = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(H, ".claude")
MARK = "// MESTREOS-REMEDIO-UNDEFINED"
OLD = "        const text = args.text as string\n"
NEW = "        const text = (args.text ?? (args as Record<string, unknown>).message ?? (args as Record<string, unknown>).texto) as string " + MARK + "\n"

def alvos():
    return sorted(glob.glob(os.path.join(BASE, "plugins", "cache", "claude-plugins-official", "telegram", "*", "server.ts")))

def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "apply"
    files = alvos()
    if not files: print("plugin de Telegram não encontrado em", BASE); return 2
    rc = 0
    for f in files:
        ver = os.path.basename(os.path.dirname(f)); s = open(f, encoding="utf-8").read(); bak = f + ".pre-remedio"
        if modo == "--check":
            print(("✓" if MARK in s else "✗"), ver, ("com remédio" if MARK in s else "SEM remédio")); rc |= (0 if MARK in s else 1); continue
        if modo == "--revert":
            if NEW in s:
                open(f, "w", encoding="utf-8", newline="\n").write(s.replace(NEW, OLD)); print("↩", ver, "correção revertida; outras mudanças preservadas")
            else: print("·", ver, "sem backup, nada a reverter")
            continue
        if MARK in s: print("✓", ver, "já com remédio"); continue
        if OLD not in s: print("✗", ver, "trecho esperado não encontrado (plugin mudou?); nada feito"); rc = 1; continue
        if not os.path.exists(bak): shutil.copy(f, bak)
        open(f, "w", encoding="utf-8").write(s.replace(OLD, NEW)); print("✓", ver, "remédio aplicado (backup em server.ts.pre-remedio). Carregue na próxima sessão ociosa do bot; não interrompa trabalho ativo.")
    return rc

if __name__ == "__main__": sys.exit(main())
