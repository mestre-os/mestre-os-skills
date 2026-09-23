#!/usr/bin/env python3
"""Consulta atualização oficial. Não instala, não reinicia e não manda mensagens.
--stage baixa cópia verificada para revisão; nunca executa arquivos baixados.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import urllib.request

BASE = 'https://raw.githubusercontent.com/mestre-os/mestre-os-skills/main/telegram/'
VERSION = '4.1.1'


def fetch(url, limit):
    with urllib.request.urlopen(url, timeout=20) as response:
        data = response.read(limit + 1)
    if len(data) > limit: raise ValueError('arquivo acima do limite')
    return data


def main():
    manifest = json.loads(fetch(BASE + 'manifest.json', 100000))
    version = manifest['version']
    parts = version.split('.')
    if len(parts) != 3 or not all(p.isdigit() and len(p) <= 5 for p in parts): raise ValueError('versão inválida')
    newer = tuple(map(int, parts)) > tuple(map(int, VERSION.split('.')))
    print('Atualização disponível: ' + version if newer else 'Pacote instalado: ' + VERSION + '; publicado: ' + version)
    if '--stage' not in sys.argv: return 0
    dest = Path.home() / '.mestreos/updates' / ('telegram-' + version)
    for name, expected in manifest['files'].items():
        p = PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name or not name.startswith('.meuos/'):
            raise ValueError('caminho fora do pacote')
        data = fetch(BASE + 'runtime/' + name, 2000000)
        if hashlib.sha256(data).hexdigest() != expected: raise ValueError('hash divergente')
        target = dest.joinpath(*p.parts)
        if target.is_symlink() or any(x.is_symlink() for x in target.parents): raise ValueError('destino é link')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print('Cópia para revisão: ' + str(dest) + '. Nada instalado.'); return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except Exception as e:
        print('Consulta interrompida: ' + type(e).__name__ + '. Instalação preservada.'); sys.exit(1)
