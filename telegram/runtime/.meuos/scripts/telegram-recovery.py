#!/usr/bin/env python3
"""Recuperação da Dupla. --install agenda; padrão recupera; --status só consulta.
Só queued é executado. Running órfão vira uncertain e nunca é repetido sozinho.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / '.meuos/hooks/cerebro.py'
LABEL = 'com.mestreos.telegram.' + hashlib.sha256(os.path.normcase(str(ROOT)).encode()).hexdigest()[:16]


def plan():
    if sys.platform == 'darwin':
        return {'Label': LABEL, 'ProgramArguments': [sys.executable, str(HOOK), '--recover'],
                'WorkingDirectory': str(ROOT), 'StartInterval': 60, 'RunAtLoad': True,
                'EnvironmentVariables': {'PATH': os.environ.get('PATH', '/usr/bin:/bin')}}
    return {'name': LABEL, 'python': sys.executable, 'script': str(HOOK), 'arguments': '--recover', 'interval_seconds': 60}


def main():
    if '--plan' in sys.argv:
        print(json.dumps(plan(), ensure_ascii=False)); return 0
    if '--status' in sys.argv:
        cmd = ['launchctl', 'print', f'gui/{os.getuid()}/{LABEL}'] if sys.platform == 'darwin' else ['schtasks', '/Query', '/TN', LABEL]
        r = subprocess.run(cmd, capture_output=True)
        print('Agendado' if r.returncode == 0 else 'Não agendado'); return r.returncode
    if '--install' not in sys.argv:
        return subprocess.call([sys.executable, str(HOOK), '--recover'], cwd=ROOT)
    if sys.platform == 'darwin':
        p = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist'); p.parent.mkdir(parents=True, exist_ok=True)
        body = plistlib.dumps(plan())
        if p.exists():
            if p.read_bytes() == body:
                r = subprocess.run(['launchctl','print',f'gui/{os.getuid()}/{LABEL}'], capture_output=True)
                if r.returncode == 0: print('Já agendado'); return 0
            else:
                print('Agendamento diferente já existe; conferir e preservar antes de substituir.'); return 2
        p.write_bytes(body)
        return subprocess.call(['launchctl', 'bootstrap', f'gui/{os.getuid()}', str(p)])
    if os.name == 'nt':
        def quote(x): return "'" + str(x).replace("'", "''") + "'"
        # Não substitui tarefa existente nem encerra executor ativo.
        ps = f'''$ErrorActionPreference='Stop'
$old=Get-ScheduledTask -TaskName {quote(LABEL)} -ErrorAction SilentlyContinue
if($old){{Write-Output 'Tarefa já existe; conferir configuração com --status'; exit 2}}
$a=New-ScheduledTaskAction -Execute {quote(sys.executable)} -Argument {quote('"' + str(HOOK) + '" --recover')} -WorkingDirectory {quote(ROOT)}
$t=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)
$s=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName {quote(LABEL)} -Action $a -Trigger $t -Settings $s | Out-Null
'''
        encoded = base64.b64encode(ps.encode('utf-16-le')).decode()
        return subprocess.call(['powershell','-NoProfile','-NonInteractive','-EncodedCommand',encoded])
    print('Agendador automático: Mac ou Windows. Use --recover pelo seu agendador.'); return 2


if __name__ == '__main__': sys.exit(main())
