#!/usr/bin/env python3
"""Regressões Telegram sem conta, rede, token ou chamada de IA. Mac + Windows.
Cobre a fila (telegram_runtime), o cérebro simétrico (cerebro) e a janela neutra (telegram_janela) do PASSO 7D."""
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
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS)); sys.path.insert(0, str(SCRIPTS))
from telegram_runtime import Queue, activity_run
import cerebro
import telegram_janela as janela


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


class CerebroTests(unittest.TestCase):
    """o cérebro decide quem responde; nunca fala com o Telegram."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.patches = [patch.object(cerebro, 'STATE', str(self.root / 's')), patch.object(cerebro, 'SF', str(self.root / 's' / 'cerebro.json')),
                        patch.object(cerebro, 'CONVERSA', str(self.root / 's' / 'conversa.jsonl')), patch.object(cerebro, 'LOGF', str(self.root / 's' / 'log')),
                        patch.object(cerebro, 'OS_DIR', str(self.root)), patch.object(cerebro, 'MEMDIR', str(self.root / 'mem')),
                        patch.object(cerebro, 'CLAUDE', str(self.root / 'nao-claude')), patch.object(cerebro, 'CODEX', str(self.root / 'nao-codex'))]
        for p in self.patches: p.start()
        cerebro.save(cerebro.novo_estado('claude', 'codex'))

    def tearDown(self):
        for p in self.patches: p.stop()
        self.tmp.cleanup()

    def msg(self, texto, **kw):
        d = {'chat': '1', 'mid': '1', 'user': 'x', 'ts': 't', 'texto': texto, 'imagens': [], 'audios': [], 'transcricoes': []}; d.update(kw); return d

    def test_claude_motor_parses_stream_json_and_keeps_session(self):
        seen = {}
        def fake_run(cmd, prompt):
            seen['cmd'] = cmd; seen['prompt'] = prompt
            out = '\n'.join([json.dumps({'type': 'system', 'subtype': 'init'}),
                             json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'pronto', 'session_id': 'sess-1', 'modelUsage': {'claude-opus-5': {}}})])
            return subprocess.CompletedProcess(cmd, 0, out, '')
        with patch.object(cerebro, '_run_stdin', side_effect=fake_run):
            acoes = cerebro.responder(self.msg('oi', imagens=[str(self.root / 'f.jpg')]))
        self.assertEqual(acoes[0][0], 'texto'); self.assertIn('pronto', acoes[0][1]); self.assertIn('🟣 Claude · Opus 5', acoes[0][1])
        self.assertIn('--session-id', seen['cmd']); self.assertNotIn('oi', ' '.join(seen['cmd']))  # prompt vai pelo stdin, nunca pelo argv
        self.assertIn('<channel source="mestreos-telegram"', seen['prompt']); self.assertIn('f.jpg', seen['prompt'])
        st = cerebro.load(); self.assertEqual(st['claude']['sessao'], 'sess-1'); self.assertEqual(st['claude']['modelo'], 'claude-opus-5')
        with patch.object(cerebro, '_run_stdin', side_effect=fake_run):
            cerebro.responder(self.msg('de novo'))
        self.assertIn('--resume', seen['cmd']); self.assertIn('sess-1', seen['cmd'])

    def test_claude_motor_error_result_is_failure(self):
        def fake_run(cmd, prompt):
            return subprocess.CompletedProcess(cmd, 1, json.dumps({'type': 'result', 'subtype': 'error_during_execution', 'is_error': True, 'result': 'partial'}), 'boom')
        with patch.object(cerebro, '_run_stdin', side_effect=fake_run):
            acoes = cerebro.responder(self.msg('oi'))
        self.assertTrue(any(a[0] == 'falha' for a in acoes)); self.assertIn('parou antes de concluir', acoes[0][1])

    def test_claude_login_lost_gives_actionable_message(self):
        for saida in (subprocess.CompletedProcess([], 1, json.dumps({'type': 'result', 'subtype': 'success', 'is_error': True, 'result': 'Login expired · Please run /login'}), ''),
                      subprocess.CompletedProcess([], 1, '', 'Error: Not logged in. Please run /login')):
            with patch.object(cerebro, '_run_stdin', return_value=saida):
                acoes = cerebro.responder(self.msg('oi'))
            self.assertIn('claude auth login', acoes[0][1]); self.assertIn('perdeu o login', acoes[0][1]); self.assertNotIn('código 1', acoes[0][1])
            self.assertTrue(any(a[0] == 'falha' for a in acoes)); self.assertIn('troca pro Codex', acoes[0][1])

    def test_codex_quota_and_login_give_actionable_message(self):
        st = cerebro.load(); st['ativo'] = 'codex'; cerebro.save(st)
        def quota(cmd, **kw): return subprocess.CompletedProcess(cmd, 1, json.dumps({'type': 'error', 'message': "You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at Sep 19th, 2026 7:01 AM."}), '')
        with patch.object(cerebro, 'activity_run', side_effect=quota), patch.object(cerebro, 'codex_command', return_value=['codex']):
            acoes = cerebro.responder(self.msg('oi'))
        self.assertIn('limite do plano', acoes[0][1]); self.assertIn('Sep 19th, 2026 7:01 AM', acoes[0][1]); self.assertIn('troca pro Claude', acoes[0][1])
        def login(cmd, **kw): return subprocess.CompletedProcess(cmd, 1, '', 'ERROR: Not logged in. Run `codex login`.')
        with patch.object(cerebro, 'activity_run', side_effect=login), patch.object(cerebro, 'codex_command', return_value=['codex']):
            acoes = cerebro.responder(self.msg('oi'))
        self.assertIn('codex login', acoes[0][1]); self.assertIn('perdeu o login', acoes[0][1])

    def test_unknown_failure_keeps_generic_message(self):
        with patch.object(cerebro, '_run_stdin', return_value=subprocess.CompletedProcess([], 2, '', 'segfault qualquer')):
            acoes = cerebro.responder(self.msg('oi'))
        self.assertIn('parou antes de concluir', acoes[0][1]); self.assertNotIn('login', acoes[0][1].lower())

    def test_codex_motor_resume_json_and_partial_output_is_failure(self):
        st = cerebro.load(); st['ativo'] = 'codex'; st['codex']['thread'] = 'existing'; cerebro.save(st)
        def run(cmd, **kw):
            self.assertIn('--json', cmd); self.assertIn('sandbox_mode="workspace-write"', cmd); self.assertIn('existing', cmd)
            Path(cmd[cmd.index('-o')+1]).write_text('partial', encoding='utf-8')
            return subprocess.CompletedProcess(cmd, 1, '', '')
        with patch.object(cerebro, 'activity_run', side_effect=run), patch.object(cerebro, 'codex_command', return_value=['codex']):
            ok, resp, novos, erro = cerebro.motor_codex(cerebro.load(), 'hello', [])
        self.assertFalse(ok)

    def test_switch_both_directions_with_summary(self):
        with patch.object(cerebro, 'FAKE_CLAUDE', 'oi do claude'):
            cerebro.responder(self.msg('oi'))
            acoes = cerebro.responder(self.msg('troca pro Sol'))
        st = cerebro.load(); self.assertEqual(st['ativo'], 'codex'); self.assertEqual(st['resumo_pendente']['para'], 'codex'); self.assertIn('ligado', acoes[0][1])
        with patch.object(cerebro, 'FAKE_CODEX', 'oi do codex'):
            seen = {}
            real = cerebro.motor_codex
            def spy(st, prompt, imagens, batimento=None): seen['prompt'] = prompt; return real(st, prompt, imagens)
            with patch.object(cerebro, 'MOTORES', {'codex': spy, 'claude': cerebro.motor_claude}):
                cerebro.responder(self.msg('e aí'))
            self.assertIn('Continuidade', seen['prompt']); self.assertIn('Últimas trocas', seen['prompt'])
            acoes = cerebro.responder(self.msg('volta pro Claude'))
        st = cerebro.load(); self.assertEqual(st['ativo'], 'claude'); self.assertEqual(st['resumo_pendente']['para'], 'claude')

    def test_only_one_engine_refuses_switch_without_breaking(self):
        cerebro.save(cerebro.novo_estado('codex', None))
        acoes = cerebro.responder(self.msg('volta pro claude'))
        self.assertIn('só tem o Codex', acoes[0][1]); self.assertEqual(cerebro.load()['ativo'], 'codex')

    def test_dictation_variants_and_false_positives(self):
        self.assertEqual(cerebro.comando(cerebro.norm('Volta para o Claudio')), ('troca', 'claude', None))
        self.assertEqual(cerebro.comando(cerebro.norm('Troca pro Codecs.')), ('troca', 'codex', 'sol'))
        self.assertEqual(cerebro.comando(cerebro.norm('Muda pra Anthropic no modelo sonnet 5 alto')), ('troca', 'claude', 'sonnet'))
        self.assertEqual(cerebro.comando(cerebro.norm('qual cérebro tá ligado?')), ('status',))
        self.assertIsNone(cerebro.comando(cerebro.norm('liga o carro da garagem')))
        self.assertIsNone(cerebro.comando(cerebro.norm('usa o código que te mandei ontem')))
        self.assertIsNone(cerebro.comando(cerebro.norm('x' * 130 + ' troca pro codex')))

    def test_v1_state_migrates_without_losing_codex_thread(self):
        Path(cerebro.SF).write_text(json.dumps({'empresa': 'openai', 'modelo': 'gpt-6-astra', 'thread': 'th-1'}), encoding='utf-8')
        st = cerebro.load()
        self.assertEqual(st['versao'], 2); self.assertEqual(st['ativo'], 'codex'); self.assertEqual(st['codex']['thread'], 'th-1'); self.assertEqual(st['codex']['modelo'], 'gpt-6-astra')

    def test_windows_cmd_uses_node_without_shell(self):
        with patch.object(cerebro, 'CODEX', str(self.root / 'codex.cmd')), patch.object(cerebro.shutil, 'which', return_value='node.exe'), patch.object(cerebro.os.path, 'isfile', return_value=True):
            cmd = cerebro.codex_command()
            self.assertEqual(cmd[0], 'node.exe'); self.assertTrue(cmd[1].endswith('codex.js'))

    def test_unknown_windows_wrapper_fails_closed(self):
        with patch.object(cerebro, 'CODEX', str(self.root / 'codex.cmd')), patch.object(cerebro.shutil, 'which', return_value=None):
            with self.assertRaises(RuntimeError): cerebro.codex_command()


class JanelaTests(unittest.TestCase):
    """a janela é dona do bot: recebe, enfileira antes do ACK, transcreve, entrega com recibo."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name); s = str(self.root / 's')
        self.patches = [patch.object(janela, 'STATE', s), patch.object(janela, 'INBOX', s + '/inbox'), patch.object(janela, 'OFFSET', s + '/offset'), patch.object(janela, 'LOGF', s + '/log'),
                        patch.object(cerebro, 'STATE', s), patch.object(cerebro, 'SF', s + '/cerebro.json'), patch.object(cerebro, 'CONVERSA', s + '/conversa.jsonl'), patch.object(cerebro, 'LOGF', s + '/clog'),
                        patch.object(cerebro, 'CLAUDE', str(self.root / 'nao')), patch.object(cerebro, 'CODEX', str(self.root / 'nao')), patch.object(cerebro, 'OS_DIR', str(self.root)),
                        patch.object(janela, 'dono', return_value='555')]
        for p in self.patches: p.start()
        cerebro.save(cerebro.novo_estado('claude', 'codex'))
        self.calls = []
        def fake_api(method, fields=None, files=None, max_time=60, tok=None):
            self.calls.append((method, dict(fields or {})))
            return {'ok': True, 'result': {'message_id': len(self.calls), 'file_path': 'voice/x.oga'}}
        self.patches.append(patch.object(janela, 'api', side_effect=fake_api)); self.patches[-1].start()
        self.patches.append(patch.object(janela, 'baixar', side_effect=lambda fid, dest: (Path(dest).parent.mkdir(parents=True, exist_ok=True), Path(dest).write_bytes(b'x'), dest)[2])); self.patches[-1].start()

    def tearDown(self):
        for p in self.patches: p.stop()
        self.tmp.cleanup()

    def sent(self): return [f.get('text', '') for m, f in self.calls if m == 'sendMessage']

    def test_enqueue_happens_before_offset_and_reply(self):
        janela.receber({'update_id': 7, 'message': {'message_id': 13, 'chat': {'id': 555}, 'text': 'oi'}})
        q = Queue(janela.STATE); self.assertEqual(q.status('555:13'), 'queued')
        self.assertIn('setMessageReaction', [m for m, _ in self.calls]); self.assertEqual(self.sent(), [])

    def test_missing_owner_fails_closed_into_pairing(self):
        with patch.object(janela, 'dono', return_value=''), patch.object(janela, 'gravar_dono', return_value=True):
            janela.CODIGO['valor'] = None
            janela.receber({'update_id': 1, 'message': {'message_id': 1, 'chat': {'id': 999}, 'text': 'troca pro codex'}})
            self.assertIsNone(Queue(janela.STATE).status('999:1')); self.assertIn('código', self.sent()[-1])

    def test_other_chat_ignored(self):
        janela.receber({'update_id': 1, 'message': {'message_id': 1, 'chat': {'id': 666}, 'text': 'oi'}})
        self.assertIsNone(Queue(janela.STATE).status('666:1')); self.assertEqual(self.sent(), [])

    def test_delivery_with_receipt_and_signature(self):
        janela.receber({'update_id': 1, 'message': {'message_id': 2, 'chat': {'id': 555}, 'text': 'oi'}})
        with patch.object(cerebro, 'FAKE_CLAUDE', 'resposta'):
            Queue(janela.STATE).drain(janela.executar, janela.recuperado)
        self.assertEqual(Queue(janela.STATE).status('555:2'), 'completed'); self.assertIn('🟣', self.sent()[-1])
        with Queue(janela.STATE).connect() as db: self.assertGreaterEqual(db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0], 1)

    def test_unconfirmed_send_marks_uncertain(self):
        janela.receber({'update_id': 1, 'message': {'message_id': 3, 'chat': {'id': 555}, 'text': 'oi'}})
        def api_sem_id(method, fields=None, files=None, max_time=60, tok=None): return {'ok': True, 'result': {}}
        with patch.object(cerebro, 'FAKE_CLAUDE', 'resposta'), patch.object(janela, 'api', side_effect=api_sem_id):
            Queue(janela.STATE).drain(janela.executar, janela.recuperado)
        self.assertEqual(Queue(janela.STATE).status('555:3'), 'uncertain')

    def test_audio_chain_order_and_honest_fallback(self):
        order = []
        with patch.object(janela, '_stt_local', side_effect=lambda p: order.append('local') or ''), \
             patch.object(janela, 'segredo', side_effect=lambda nome, var: 'k' if var == 'GROQ_API_KEY' else ''), \
             patch.object(janela, '_stt_http', side_effect=lambda p, url, k, m: order.append(m) or 'texto ouvido'):
            f = self.root / 'a.oga'; f.write_bytes(b'x')
            self.assertEqual(janela.transcrever(str(f)), 'texto ouvido'); self.assertEqual(order, ['local', 'whisper-large-v3-turbo'])
        janela.receber({'update_id': 1, 'message': {'message_id': 4, 'chat': {'id': 555}, 'voice': {'file_id': 'v'}}})
        with patch.object(janela, 'tem_stt', return_value=False), patch.object(cerebro, 'FAKE_CLAUDE', 'nunca'):
            Queue(janela.STATE).drain(janela.executar, janela.recuperado)
        self.assertIn('manda em texto', self.sent()[-1].lower()); self.assertNotIn('nunca', ' '.join(self.sent()))

    def test_spoken_command_switches_engine(self):
        janela.receber({'update_id': 1, 'message': {'message_id': 5, 'chat': {'id': 555}, 'voice': {'file_id': 'v'}}})
        with patch.object(janela, 'tem_stt', return_value=True), patch.object(janela, 'transcrever', return_value='troca pro codex'), patch.object(cerebro, 'FAKE_CLAUDE', 'resumo'):
            Queue(janela.STATE).drain(janela.executar, janela.recuperado)
        self.assertEqual(cerebro.load()['ativo'], 'codex')

    def test_engine_failure_is_uncertain_and_never_replayed(self):
        janela.receber({'update_id': 1, 'message': {'message_id': 6, 'chat': {'id': 555}, 'text': 'faz'}})
        Queue(janela.STATE).drain(janela.executar, janela.recuperado)
        self.assertEqual(Queue(janela.STATE).status('555:6'), 'uncertain'); n = len(self.sent())
        Queue(janela.STATE).drain(janela.executar, janela.recuperado); self.assertEqual(len(self.sent()), n)

    def test_second_window_is_refused(self):
        from telegram_runtime import lock, Busy
        Path(janela.STATE).mkdir(parents=True, exist_ok=True)
        with lock(str(Path(janela.STATE) / 'janela.lock')):
            with patch.object(janela, 'ler_token', return_value='t'):
                self.assertEqual(janela.janela(), 3)

    def test_conflict_409_stops_window(self):
        def api409(method, fields=None, files=None, max_time=60, tok=None): return {'ok': False, 'error_code': 409, 'description': 'Conflict: terminated by other getUpdates request'}
        with patch.object(janela, 'api', side_effect=api409), patch.object(janela, 'ler_token', return_value='t'), patch.object(janela.time, 'sleep'), patch.object(janela, 'executor_loop', lambda parar: None):
            self.assertEqual(janela.janela(), 2)


class PluginRemedioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

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
