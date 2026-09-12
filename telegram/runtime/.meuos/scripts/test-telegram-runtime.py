#!/usr/bin/env python3
"""Regressões Telegram sem conta, rede, token ou chamada de IA. Mac + Windows."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HOOKS = Path(__file__).resolve().parent.parent / 'hooks'
sys.path.insert(0, str(HOOKS))
from telegram_runtime import Queue, activity_run
import cerebro


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.q = Queue(self.root / 'queue')

    def tearDown(self):
        self.tmp.cleanup()

    def test_fifo_dedup_multi_process(self):
        for i in range(5): self.assertTrue(self.q.enqueue(str(i), {'n': i}))
        self.assertFalse(self.q.enqueue('2', {'n': 999}))
        code = '''import sys,time
sys.path.insert(0,sys.argv[1])
from telegram_runtime import Queue
q=Queue(sys.argv[2])
def execute(i,p):
 with open(sys.argv[3],'a') as f: f.write(i+' start\\n'); f.flush()
 time.sleep(.05)
 with open(sys.argv[3],'a') as f: f.write(i+' end\\n'); f.flush()
 return 'completed'
q.drain(execute)
'''
        out = self.root / 'order'
        children = [subprocess.Popen([sys.executable, '-c', code, str(HOOKS), str(self.q.path), str(out)]) for _ in range(3)]
        for c in children: self.assertEqual(c.wait(timeout=15), 0)
        self.assertEqual(out.read_text().splitlines(), [f'{i} {phase}' for i in range(5) for phase in ('start', 'end')])
        self.assertTrue(all(self.q.status(str(i)) == 'completed' for i in range(5)))

    def test_queued_survives_process_restart(self):
        self.q.enqueue('a', {'body': 'retomar'})
        other = Queue(self.q.path); seen = []
        other.drain(lambda ident, p: seen.append(p['body']) or 'completed')
        self.assertEqual(seen, ['retomar'])

    def test_interrupted_running_not_replayed(self):
        self.q.enqueue('old', {}); self.q.finish('old', 'running')
        self.q.enqueue('next', {}); seen = []; alerted = []
        self.q.drain(lambda i, p: seen.append(i) or 'completed', alerted.append)
        self.assertEqual(seen, ['next']); self.assertEqual(alerted, ['old'])
        self.assertEqual(self.q.status('old'), 'uncertain')

    def test_exception_preserves_payload_without_retry(self):
        self.q.enqueue('a', {'question': 'original'})
        def explode(i, p): raise RuntimeError('after external action')
        self.q.drain(explode)
        self.q.drain(lambda i, p: self.fail('replayed'))
        self.assertEqual(self.q.status('a'), 'uncertain')
        with self.q.connect() as db:
            self.assertIn('original', db.execute('SELECT payload FROM jobs').fetchone()[0])

    def test_receipt_requires_telegram_message_id(self):
        with patch.object(cerebro, 'STATE', str(self.q.path)), patch.object(cerebro, 'JOB', 'a'), patch.object(cerebro, 'DRY', False), patch.object(cerebro, 'token', return_value='mock'), patch.object(cerebro.subprocess, 'run') as run:
            run.return_value.stdout = '{"ok":true,"result":{"message_id":42}}'
            self.assertTrue(cerebro.tg('sendMessage', {'text': 'ok'}))
            run.return_value.stdout = '{"ok":true,"result":{}}'
            self.assertFalse(cerebro.tg('sendMessage', {'text': 'not confirmed'}))
            with self.q.connect() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0], 1)

    def test_active_process_outlives_total_timeout(self):
        t = time.monotonic()
        r = activity_run([sys.executable, '-u', '-c', 'import time\nfor i in range(6):\n print(i,flush=True);time.sleep(.15)'], str(self.root), .5)
        self.assertEqual(r.returncode, 0); self.assertGreater(time.monotonic()-t, .5)

    def test_silent_process_times_out(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            activity_run([sys.executable, '-c', 'import time;time.sleep(5)'], str(self.root), .4)

    def test_stderr_noise_does_not_hide_stall(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            activity_run([sys.executable, '-u', '-c', 'import time,sys\nfor i in range(20):\n print(i,file=sys.stderr,flush=True);time.sleep(.05)'], str(self.root), .4)

    def test_nonzero_partial_answer_and_resume_json(self):
        def run(cmd, **kw):
            self.assertIn('--json', cmd)
            self.assertIn('sandbox_mode="workspace-write"', cmd)
            Path(cmd[cmd.index('-o')+1]).write_text('partial', encoding='utf-8')
            return subprocess.CompletedProcess(cmd, 1, '', '')
        with patch.object(cerebro, 'STATE', str(self.root)), patch.object(cerebro, 'OS_DIR', str(self.root)), patch.object(cerebro, 'FAKE', None), patch.object(cerebro, 'tg', return_value=True), patch.object(cerebro, 'activity_run', side_effect=run):
            ok, *_ = cerebro.run_codex({'modelo':'model', 'thread':'existing'}, 'hello', [])
            self.assertFalse(ok)

    def test_hook_enqueues_before_ack_and_launch_failure(self):
        import io
        d = {'prompt':'<channel source="plugin:telegram" chat_id="123" message_id="456">oi</channel>'}
        with patch.object(cerebro, 'STATE', str(self.q.path)), patch.object(cerebro, 'DRY', False), patch.object(cerebro, 'chat_id_dono', return_value='123'), patch.object(cerebro, 'load', return_value={'empresa':'openai'}), patch.object(cerebro.sys, 'stdin', io.StringIO(json.dumps(d))), patch.object(cerebro.subprocess, 'Popen', side_effect=OSError('cannot start')), patch.object(cerebro, 'send_text', return_value=True), patch.object(cerebro, 'block', side_effect=SystemExit):
            with self.assertRaises(SystemExit): cerebro.dispatch()
        self.assertEqual(self.q.status('123:456'), 'queued')

    def test_audio_envelope_goes_to_claude_without_codex(self):
        import io
        d = {'prompt':'<channel source="plugin:telegram" chat_id="123" message_id="456" attachment_kind="voice">(voice message)</channel>'}
        with patch.object(cerebro, 'DRY', False), patch.object(cerebro, 'chat_id_dono', return_value='123'), patch.object(cerebro.sys, 'stdin', io.StringIO(json.dumps(d))), patch.object(cerebro, 'add_context', side_effect=SystemExit) as context, patch.object(cerebro, 'run_codex') as run:
            with self.assertRaises(SystemExit): cerebro.dispatch()
            context.assert_called_once(); run.assert_not_called()

    def test_missing_owner_fails_closed(self):
        import io
        d = {'prompt':'<channel source="plugin:telegram" chat_id="123" message_id="456">troca pro codex</channel>'}
        with patch.object(cerebro, 'chat_id_dono', return_value=''), patch.object(cerebro.sys, 'stdin', io.StringIO(json.dumps(d))), patch.object(cerebro, 'main') as main:
            cerebro.dispatch(); main.assert_not_called()

    def test_windows_cmd_uses_node_without_shell(self):
        with patch.object(cerebro, 'CODEX', str(self.root / 'codex.cmd')), patch.object(cerebro.shutil, 'which', return_value='node.exe'), patch.object(cerebro.os.path, 'isfile', return_value=True):
            cmd = cerebro.codex_command()
            self.assertEqual(cmd[0], 'node.exe')
            self.assertTrue(cmd[1].endswith('codex.js'))

    def test_unknown_windows_wrapper_fails_closed(self):
        with patch.object(cerebro, 'CODEX', str(self.root / 'codex.cmd')), patch.object(cerebro.shutil, 'which', return_value=None):
            with self.assertRaises(RuntimeError): cerebro.codex_command()

    def test_plugin_patch_idempotent_and_revert_preserves_new_code(self):
        server = self.root / 'plugins/cache/claude-plugins-official/telegram/fixture/server.ts'
        server.parent.mkdir(parents=True)
        original = '        const text = args.text as string\n'
        server.write_text(original, encoding='utf-8')
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root))
        cmd = [sys.executable, str(Path(__file__).parent / 'telegram-plugin-remedio.py')]
        def run(*args):
            return subprocess.run(cmd + list(args), env=env, capture_output=True, encoding='utf-8')
        self.assertEqual(run().returncode, 0)
        first = server.read_bytes(); self.assertEqual(run().returncode, 0)
        self.assertEqual(server.read_bytes(), first); self.assertEqual(run('--check').returncode, 0)
        with server.open('a', encoding='utf-8') as f: f.write('// unrelated upstream fix\n')
        self.assertEqual(run('--revert').returncode, 0)
        self.assertEqual(server.read_text(), original + '// unrelated upstream fix\n')

    def test_unknown_plugin_version_is_not_modified(self):
        server = self.root / 'plugins/cache/claude-plugins-official/telegram/new/server.ts'
        server.parent.mkdir(parents=True); server.write_text('const totallyDifferent = true;\n')
        original = server.read_bytes()
        r = subprocess.run([sys.executable, str(Path(__file__).parent / 'telegram-plugin-remedio.py')],
                           env=dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root)), capture_output=True)
        self.assertNotEqual(r.returncode, 0); self.assertEqual(server.read_bytes(), original)


if __name__ == '__main__': unittest.main()
