#!/usr/bin/env python3
"""Regressões Telegram sem conta, rede, token ou chamada de IA. Mac + Windows.
Cobre a fila (telegram_runtime), o cérebro simétrico (cerebro) e a janela neutra (telegram_janela) do PASSO 7D."""
import importlib.util
import json
import os
from pathlib import Path
import re
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


def _remedio():
    spec = importlib.util.spec_from_file_location('telegram_plugin_remedio', SCRIPTS / 'telegram-plugin-remedio.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def _ancoras():
    """Arquivo mínimo com cada trecho que os remédios reconhecem, 1 vez cada (a ordem real vem no teste do plugin 0.0.7)."""
    vistos = []
    for _nome, _marca, edits, _equiv in _remedio().REMEDIOS:
        for old, _new in edits:
            if old not in vistos: vistos.append(old)
    return ''.join(vistos)


def _bun(root, codigo, **env):
    f = Path(root) / 'harness.ts'; f.write_text(codigo, encoding='utf-8')
    return subprocess.run(['bun', str(f)], capture_output=True, encoding='utf-8', timeout=60,
                          env=dict(os.environ, MESTREOS_TELEGRAM_BATIDA_MS='50', **env))


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
        self.assertEqual(acoes[0][0], 'texto'); self.assertIn('pronto', acoes[0][1]); self.assertIn('🧠 Claude · Opus 5', acoes[0][1])
        self.assertIn('--session-id', seen['cmd']); self.assertNotIn('oi', seen['cmd'])  # prompt vai pelo stdin, nunca pelo argv (item, não texto: a pasta temporária sorteada podia conter "oi")
        self.assertIn('<channel source="mestreos-telegram"', seen['prompt']); self.assertIn('f.jpg', seen['prompt'])
        st = cerebro.load(); self.assertEqual(st['claude']['sessao'], 'sess-1'); self.assertEqual(st['claude']['modelo'], 'claude-opus-5')
        with patch.object(cerebro, '_run_stdin', side_effect=fake_run):
            cerebro.responder(self.msg('de novo'))
        self.assertIn('--resume', seen['cmd']); self.assertIn('sess-1', seen['cmd'])

    def test_signature_is_always_the_brain_emoji(self):
        # 21/10/26 (pedido do dono): toda assinatura de modelo começa com 🧠, Claude ou OpenAI. Sai o roxo do Claude e o
        # emoji de cada modelo da OpenAI; o resto do formato não muda.
        casos = [('claude', 'opus', '🧠 Claude · Opus'), ('claude', 'claude-opus-5-5', '🧠 Claude · Opus 5.5'), ('claude', None, '🧠 Claude'),
                 ('codex', 'gpt-5.6-sol', '🧠 Sol'), ('codex', 'gpt-5.6-terra', '🧠 Terra'), ('codex', 'gpt-5.6-luna', '🧠 Luna'),
                 ('codex', 'gpt-6-astra', '🧠 Astra'), ('codex', None, '🧠 OpenAI')]
        for motor, modelo, esperado in casos:
            self.assertEqual(cerebro.assinatura(motor, modelo), esperado, (motor, modelo))
            for velho in ('🟣', '☀', '🌍', '🌙', '✨', '🟢'): self.assertNotIn(velho, cerebro.assinatura(motor, modelo), (motor, modelo, velho))
        self.assertTrue(cerebro.status_txt(cerebro.load()).startswith('🧠 Cérebro ligado: 🧠 Claude'))   # o status usa a mesma assinatura
        with patch.object(cerebro, 'FAKE_CLAUDE', 'oi do claude'):
            self.assertTrue(cerebro.responder(self.msg('oi'))[-1][1].endswith('\n\n🧠 Claude · Claude'))   # o modelo do dublê não tem nome conhecido
        st = cerebro.load(); st['ativo'] = 'codex'; cerebro.save(st)
        with patch.object(cerebro, 'FAKE_CODEX', 'oi do codex'):
            self.assertEqual(cerebro.responder(self.msg('oi'))[-1][1], 'oi do codex\n\n🧠 Sol')

    def test_clean_marker_sends_the_text_without_marker_or_signature(self):
        # 21/10/26: texto pra ele copiar e mandar a outra pessoa começa com [[limpo]] (a mesma marca do 7A): a marca some e a
        # assinatura do modelo não entra. Qualquer outra resposta continua assinada.
        casos = [('[[limpo]]\nBom dia, síndico.', 'Bom dia, síndico.'), ('  [[limpo]]   Bom dia.', 'Bom dia.'),
                 ('\r\n[[limpo]]\r\nLinha 1\r\nLinha 2\r\n', 'Linha 1\r\nLinha 2'),    # fim de linha do Windows
                 ('[reagir:🤝] [[limpo]]\nCombinado.', 'Combinado.'), ('[[limpo]] [reagir:🤝]\nCombinado.', 'Combinado.')]
        for motor in ('claude', 'codex'):
            st = cerebro.load(); st['ativo'] = motor; cerebro.save(st)
            for resposta, texto in casos:
                with patch.object(cerebro, 'FAKE_CLAUDE' if motor == 'claude' else 'FAKE_CODEX', resposta):
                    acoes = cerebro.responder(self.msg('manda pra ele'))
                self.assertEqual([a[1] for a in acoes if a[0] == 'texto'], [texto], (motor, resposta))
                self.assertEqual(('reagir', '🤝') in acoes, '[reagir:' in resposta, (motor, resposta))
        # sem a marca no começo, nada muda: a assinatura entra e uma "marca" no meio do texto é só texto
        st = cerebro.load(); st['ativo'] = 'claude'; cerebro.save(st)
        with patch.object(cerebro, 'FAKE_CLAUDE', 'Segue o texto. [[limpo]] no meio'):
            texto = [a[1] for a in cerebro.responder(self.msg('oi')) if a[0] == 'texto'][0]
        self.assertTrue(texto.startswith('Segue o texto. [[limpo]] no meio\n\n🧠 Claude'), texto)

    def test_marker_only_sends_nothing_and_does_not_crash(self):
        for resposta in ('[[limpo]]', '  [[limpo]]  ', '[[limpo]]\r\n', '[reagir:👍] [[limpo]]\n'):
            with patch.object(cerebro, 'FAKE_CLAUDE', resposta):
                acoes = cerebro.responder(self.msg('oi'))
            self.assertEqual([a for a in acoes if a[0] == 'texto'], [], resposta)
            self.assertFalse(any(a[0] == 'falha' for a in acoes), resposta)

    def test_clean_marker_survives_the_real_output_paths_with_windows_line_endings(self):
        # o Codex grava a última mensagem num arquivo e o Claude devolve o texto no JSON: o fim de linha do Windows chega
        # nos dois caminhos reais, não só no dublê
        st = cerebro.load(); st['ativo'] = 'codex'; cerebro.save(st)
        def codex(cmd, **kw):
            Path(cmd[cmd.index('-o') + 1]).write_bytes('[[limpo]]\r\nBom dia.\r\nPode confirmar?\r\n'.encode('utf-8'))
            return subprocess.CompletedProcess(cmd, 0, '', '')
        with patch.object(cerebro, 'activity_run', side_effect=codex), patch.object(cerebro, 'codex_command', return_value=['codex']):
            textos = [a[1] for a in cerebro.responder(self.msg('oi')) if a[0] == 'texto']
        self.assertEqual(len(textos), 1); self.assertTrue(textos[0].startswith('Bom dia.')); self.assertNotIn('[[limpo]]', textos[0]); self.assertNotIn('🧠', textos[0])
        st = cerebro.load(); st['ativo'] = 'claude'; cerebro.save(st)
        saida = json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': '[[limpo]]\r\nBom dia.\r\nPode confirmar?', 'session_id': 's', 'modelUsage': {'claude-opus-5-5': {}}})
        with patch.object(cerebro, '_run_stdin', return_value=subprocess.CompletedProcess([], 0, saida, '')):
            textos = [a[1] for a in cerebro.responder(self.msg('oi')) if a[0] == 'texto']
        self.assertEqual(textos, ['Bom dia.\r\nPode confirmar?'])

    def test_agent_instructions_teach_the_clean_marker_and_that_only_telegram_signs(self):
        # as instruções do 7D (as mesmas do 7A, em outras palavras): texto pra copiar e mandar começa com [[limpo]]; a
        # assinatura é só do Telegram, e-mail e qualquer outro canal nunca levam
        for motor in ('claude', 'codex'):
            t = cerebro.instrucoes(motor)
            self.assertIn('[[limpo]]', t); self.assertIn('e-mail', t); self.assertIn('Não assine', t)

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
        import datetime as _dt
        volta = _dt.datetime.now() + _dt.timedelta(days=2)
        quando = volta.strftime('%b ') + str(volta.day) + 'th, ' + volta.strftime('%Y 7:01 AM')
        def quota(cmd, **kw): return subprocess.CompletedProcess(cmd, 1, json.dumps({'type': 'error', 'message': "You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at " + quando + "."}), '')
        with patch.object(cerebro, 'activity_run', side_effect=quota), patch.object(cerebro, 'codex_command', return_value=['codex']):
            acoes = cerebro.responder(self.msg('oi'))
        # 4.3.0: cota estourada = troca SOZINHO pro outro motor, com a hora de volta legível
        self.assertIn('limite do plano', acoes[0][1]); self.assertIn(volta.strftime('%d/%m') + ' 07:01', acoes[0][1]); self.assertIn('Passei pro Claude sozinho', acoes[0][1])
        self.assertEqual(cerebro.load()['ativo'], 'claude'); self.assertEqual(cerebro.load()['auto']['de'], 'codex')
        # sem prova de que nada foi feito (a saída do Codex não mostrou início de turno): NÃO refaz, pede reenvio e marca incerto
        self.assertTrue(any(a[0] == 'falha' for a in acoes)); self.assertIn('me mande de novo', ' '.join(a[1] for a in acoes if a[0] == 'texto'))
        st = cerebro.load(); st['ativo'] = 'codex'; st.pop('auto', None); st.pop('cota', None); cerebro.save(st)
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
        self.assertEqual(Queue(janela.STATE).status('555:2'), 'completed'); self.assertIn('🧠 Claude', self.sent()[-1]); self.assertNotIn('🟣', self.sent()[-1])
        with Queue(janela.STATE).connect() as db: self.assertGreaterEqual(db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0], 1)

    def test_clean_marker_reaches_the_phone_without_marker_or_signature(self):
        # 21/10/26: o mesmo [[limpo]] do 7A, pela janela da Dupla. Só a marca não manda nada (nem "(sem texto)").
        casos = [('[[limpo]]\r\nBom dia, síndico.\r\nPode confirmar?', 'Bom dia, síndico.\r\nPode confirmar?'), ('resposta comum', None)]
        for i, (resposta, enviado) in enumerate(casos):
            janela.receber({'update_id': 10 + i, 'message': {'message_id': 20 + i, 'chat': {'id': 555}, 'text': 'escreve'}})
            with patch.object(cerebro, 'FAKE_CLAUDE', resposta):
                Queue(janela.STATE).drain(janela.executar, janela.recuperado)
            self.assertEqual(Queue(janela.STATE).status(f'555:{20 + i}'), 'completed')
            if enviado: self.assertEqual(self.sent()[-1], enviado)
            else: self.assertTrue(self.sent()[-1].startswith('resposta comum\n\n🧠 Claude'), self.sent()[-1])
        antes = len(self.sent())
        janela.receber({'update_id': 30, 'message': {'message_id': 40, 'chat': {'id': 555}, 'text': 'de novo'}})
        with patch.object(cerebro, 'FAKE_CLAUDE', '[[limpo]]'):
            Queue(janela.STATE).drain(janela.executar, janela.recuperado)
        self.assertEqual(len(self.sent()), antes)   # nada enviado: nem "(sem texto)", nem o aviso de motor interrompido
        self.assertIn(Queue(janela.STATE).status('555:40'), ('completed', 'uncertain'))

    def test_unconfirmed_send_marks_uncertain(self):
        janela.receber({'update_id': 1, 'message': {'message_id': 3, 'chat': {'id': 555}, 'text': 'oi'}})
        def api_sem_id(method, fields=None, files=None, max_time=60, tok=None): return {'ok': True, 'result': {}}
        with patch.object(cerebro, 'FAKE_CLAUDE', 'resposta'), patch.object(janela, 'api', side_effect=api_sem_id):
            Queue(janela.STATE).drain(janela.executar, janela.recuperado)
        self.assertEqual(Queue(janela.STATE).status('555:3'), 'uncertain')

    def test_audio_chain_order_and_honest_fallback(self):
        order = []
        with patch.object(janela, '_stt_mlx', side_effect=lambda p: order.append('mlx') or None), \
             patch.object(janela, '_stt_cpu', side_effect=lambda p: order.append('cpu') or ''), \
             patch.object(janela, 'segredo', side_effect=lambda nome, var: 'k' if var == 'GROQ_API_KEY' else ''), \
             patch.object(janela, '_stt_http', side_effect=lambda p, url, k, m: order.append(m) or 'texto ouvido'):
            f = self.root / 'a.oga'; f.write_bytes(b'x')
            self.assertEqual(janela.transcrever(str(f)), 'texto ouvido'); self.assertEqual(order, ['mlx', 'whisper-large-v3-turbo'])
        # 4.4.2: whisper de CPU (lento, ~1 min por áudio) vira o último recurso, depois das chaves
        order.clear()
        with patch.object(janela, '_stt_mlx', side_effect=lambda p: order.append('mlx') or None), \
             patch.object(janela, '_stt_cpu', side_effect=lambda p: order.append('cpu') or 'ouvido na cpu'), \
             patch.object(janela, 'segredo', side_effect=lambda nome, var: 'k'), \
             patch.object(janela, '_stt_http', side_effect=lambda p, url, k, m: order.append(m) or ''):
            self.assertEqual(janela.transcrever(str(f)), 'ouvido na cpu')
            self.assertEqual(order, ['mlx', 'whisper-1', 'whisper-large-v3-turbo', 'cpu'])
        janela.receber({'update_id': 1, 'message': {'message_id': 4, 'chat': {'id': 555}, 'voice': {'file_id': 'v'}}})
        with patch.object(janela, 'tem_stt', return_value=False), patch.object(cerebro, 'FAKE_CLAUDE', 'nunca'):
            Queue(janela.STATE).drain(janela.executar, janela.recuperado)
        self.assertIn('manda em texto', self.sent()[-1].lower()); self.assertNotIn('nunca', ' '.join(self.sent()))

    def _mlx_fake(self, comportamento, calls):
        """imita o mlx_whisper REAL: volta rc 0 mesmo quando pula o arquivo (medido 28/09); o que vale é a saída e o stderr."""
        def run(cmd, capture_output=True, text=False, encoding=None, errors=None, timeout=None, env=None):
            calls.append((cmd, env, timeout))
            acao = comportamento(cmd, env)
            if isinstance(acao, BaseException): raise acao
            if acao is None or acao.startswith('ERRO:'):
                return subprocess.CompletedProcess(cmd, 0, '', (acao or '')[5:])
            d = cmd[cmd.index('--output-dir') + 1]; Path(d, 'out.txt').write_text(acao, encoding='utf-8')
            return subprocess.CompletedProcess(cmd, 0, '', '')
        return run

    def test_mlx_model_explicit_offline_first(self):
        """4.4.2: sem --model o mlx_whisper usa o tiny. Modelo explícito; sem rede primeiro; rede SÓ com modelo ausente provado."""
        f = self.root / 'a.oga'; f.write_bytes(b'x'); calls = []
        falta = 'ERRO:huggingface_hub.errors.LocalEntryNotFoundError: Cannot find an appropriate cached snapshot folder'
        comp = lambda cmd, env: falta if env.get('HF_HUB_OFFLINE') == '1' else 'ouvido no mlx'
        with patch.object(janela, '_mlx_candidatos', return_value=['/x/mlx_whisper']), patch.object(janela.subprocess, 'run', side_effect=self._mlx_fake(comp, calls)):
            self.assertEqual(janela._stt_mlx(str(f)), 'ouvido no mlx')
        self.assertEqual(len(calls), 2)
        for cmd, env, _ in calls:
            self.assertEqual(cmd[cmd.index('--model') + 1], 'mlx-community/whisper-large-v3-turbo')
            self.assertEqual(env.get('HF_HUB_DISABLE_TELEMETRY'), '1')
        self.assertEqual(calls[0][1].get('HF_HUB_OFFLINE'), '1'); self.assertNotIn('HF_HUB_OFFLINE', calls[1][1])
        self.assertGreaterEqual(calls[0][2], 900)  # a tentativa sem rede É a transcrição: áudio longo legítimo cabe (rodada 2)
        # modelo baixado + áudio em silêncio: resposta vazia É resposta (não sobe o áudio pra API); saída velha não vale
        calls.clear(); (Path(janela.STATE) / 'stt').mkdir(parents=True, exist_ok=True); (Path(janela.STATE) / 'stt' / 'out.txt').write_text('velho', encoding='utf-8')
        with patch.object(janela, '_mlx_candidatos', return_value=['/x/mlx_whisper']), patch.object(janela.subprocess, 'run', side_effect=self._mlx_fake(lambda c, e: '', calls)):
            self.assertEqual(janela._stt_mlx(str(f)), '')
        self.assertEqual(len(calls), 1)

    def test_mlx_inherited_offline_env_still_downloads(self):
        """rodada 2: janela que herda HF_HUB_OFFLINE=1 não pode ficar sem rede na tentativa autorizada a baixar."""
        f = self.root / 'a.oga'; f.write_bytes(b'x'); calls = []
        falta = 'ERRO:LocalEntryNotFoundError: Cannot find an appropriate cached snapshot folder'
        comp = lambda cmd, env: falta if env.get('HF_HUB_OFFLINE') == '1' else 'baixou e ouviu'
        with patch.dict(os.environ, {'HF_HUB_OFFLINE': '1'}), patch.object(janela, '_mlx_candidatos', return_value=['/x/mlx_whisper']), \
             patch.object(janela.subprocess, 'run', side_effect=self._mlx_fake(comp, calls)):
            self.assertEqual(janela._stt_mlx(str(f)), 'baixou e ouviu')
        self.assertEqual(len(calls), 2); self.assertNotIn('HF_HUB_OFFLINE', calls[1][1])

    def test_mlx_candidates_dedup_alias(self):
        """rodada 2: o PATH apontando (symlink) pro mesmo executável do venv não entra duas vezes."""
        exe = self.root / 'mlx_whisper'; exe.write_text('#!/bin/sh\n'); exe.chmod(0o755)
        alias = self.root / 'bin-alias'
        try: alias.symlink_to(exe)
        except (OSError, NotImplementedError): self.skipTest('symlink exige permissão especial neste sistema (Windows)')
        with patch.object(janela, 'STT_VENV', str(exe)), patch.object(janela.shutil, 'which', return_value=str(alias)), patch.object(janela.sys, 'platform', 'darwin'):
            self.assertEqual(janela._mlx_candidatos(), [str(exe)])

    def test_mlx_timeout_never_retries(self):
        f = self.root / 'a.oga'; f.write_bytes(b'x'); calls = []
        trava = lambda cmd, env: subprocess.TimeoutExpired(cmd, 180)
        with patch.object(janela, '_mlx_candidatos', return_value=['/venv/mlx_whisper', '/path/mlx_whisper']), patch.object(janela.subprocess, 'run', side_effect=self._mlx_fake(trava, calls)):
            self.assertIsNone(janela._stt_mlx(str(f)))
        self.assertEqual(len(calls), 1)  # travou uma vez: próximo provedor, sem 2ª espera nem com rede

    def test_mlx_broken_venv_falls_back_to_path(self):
        f = self.root / 'a.oga'; f.write_bytes(b'x'); calls = []
        def comp(cmd, env):
            if cmd[0] == '/venv/mlx_whisper': return FileNotFoundError(2, 'interpretador do venv sumiu')
            return 'ouvido no mlx do PATH'
        with patch.object(janela, '_mlx_candidatos', return_value=['/venv/mlx_whisper', '/path/mlx_whisper']), patch.object(janela.subprocess, 'run', side_effect=self._mlx_fake(comp, calls)):
            self.assertEqual(janela._stt_mlx(str(f)), 'ouvido no mlx do PATH')
        # instalação pela metade (import quebra, sem saída, sem "modelo ausente"): não vai à rede, tenta o próximo
        calls.clear()
        comp2 = lambda cmd, env: 'ERRO:ModuleNotFoundError: No module named torch' if cmd[0] == '/venv/mlx_whisper' else 'ok do PATH'
        with patch.object(janela, '_mlx_candidatos', return_value=['/venv/mlx_whisper', '/path/mlx_whisper']), patch.object(janela.subprocess, 'run', side_effect=self._mlx_fake(comp2, calls)):
            self.assertEqual(janela._stt_mlx(str(f)), 'ok do PATH')
        self.assertEqual([c[0][0] for c in calls], ['/venv/mlx_whisper', '/path/mlx_whisper'])
        # nenhum mlx serve: None (a cadeia segue pras chaves e pro CPU)
        with patch.object(janela, '_mlx_candidatos', return_value=['/venv/mlx_whisper']), patch.object(janela.subprocess, 'run', side_effect=self._mlx_fake(lambda c, e: FileNotFoundError(2, 'x'), [])):
            self.assertIsNone(janela._stt_mlx(str(f)))

    def test_mlx_silence_does_not_upload(self):
        f = self.root / 'a.oga'; f.write_bytes(b'x'); http = []
        with patch.object(janela, '_stt_mlx', return_value=''), patch.object(janela, 'segredo', return_value='k'), \
             patch.object(janela, '_stt_http', side_effect=lambda *a: http.append(a) or 'da api'), patch.object(janela, '_stt_cpu', return_value='cpu'):
            self.assertEqual(janela.transcrever(str(f)), '')
        self.assertEqual(http, [])

    def test_mlx_candidates_venv_first_mac_only(self):
        exe = self.root / 'mlx_whisper'; exe.write_text('#!/bin/sh\n'); exe.chmod(0o755)
        with patch.object(janela, 'STT_VENV', str(exe)), patch.object(janela.shutil, 'which', return_value='/usr/local/bin/mlx_whisper'):
            with patch.object(janela.sys, 'platform', 'darwin'): self.assertEqual(janela._mlx_candidatos(), [str(exe), '/usr/local/bin/mlx_whisper'])
            with patch.object(janela.sys, 'platform', 'win32'): self.assertEqual(janela._mlx_candidatos(), ['/usr/local/bin/mlx_whisper'])
        with patch.object(janela, 'STT_VENV', str(exe)), patch.object(janela.shutil, 'which', return_value=str(exe)), patch.object(janela.sys, 'platform', 'darwin'):
            self.assertEqual(janela._mlx_candidatos(), [str(exe)])  # mesmo executável não entra duas vezes
        with patch.object(janela, 'STT_VENV', str(self.root / 'nao-existe')), patch.object(janela.shutil, 'which', return_value=None), patch.object(janela.sys, 'platform', 'darwin'):
            self.assertEqual(janela._mlx_candidatos(), [])

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
        original = _ancoras()
        server.write_bytes(original.encode('utf-8'))
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root))
        cmd = [sys.executable, str(Path(__file__).parent / 'telegram-plugin-remedio.py')]
        def run(*args):
            return subprocess.run(cmd + list(args), env=env, capture_output=True, encoding='utf-8')
        self.assertEqual(run().returncode, 0)
        first = server.read_bytes(); self.assertEqual(run().returncode, 0)
        self.assertEqual(server.read_bytes(), first); self.assertEqual(run('--check').returncode, 0)
        with server.open('ab') as f: f.write(b'// unrelated upstream fix\n')   # binário: o modo texto do Windows viraria CRLF
        self.assertEqual(run('--revert').returncode, 0)
        self.assertEqual(server.read_bytes(), (original + '// unrelated upstream fix\n').encode('utf-8'))

    def test_stray_crlf_line_does_not_flip_the_whole_file(self):
        # prova no Windows (20/10/26): uma linha CRLF solta num arquivo LF fazia o remédio ler tudo como CRLF; a reversão
        # não achava os trechos e o remédio ficava preso
        server = self.root / 'plugins/cache/claude-plugins-official/telegram/fixture/server.ts'
        server.parent.mkdir(parents=True); original = _ancoras().encode('utf-8'); server.write_bytes(original)
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root))
        cmd = [sys.executable, str(SCRIPTS / 'telegram-plugin-remedio.py')]
        self.assertEqual(subprocess.run(cmd, env=env, capture_output=True).returncode, 0)
        with server.open('ab') as f: f.write(b'// linha de um editor do Windows\r\n')
        r = subprocess.run(cmd + ['--revert'], env=env, capture_output=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(server.read_bytes(), original + b'// linha de um editor do Windows\r\n')

    def test_both_remedies_applied_and_check_needs_both(self):
        server = self.root / 'plugins/cache/claude-plugins-official/telegram/fixture/server.ts'
        server.parent.mkdir(parents=True)
        server.write_bytes(_ancoras().encode('utf-8'))  # LF explícito (write_text vira CRLF no Windows)
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root))
        cmd = [sys.executable, str(Path(__file__).parent / 'telegram-plugin-remedio.py')]
        self.assertEqual(subprocess.run(cmd, env=env, capture_output=True).returncode, 0)
        s = server.read_text(encoding='utf-8')
        self.assertIn('MESTREOS-REMEDIO-UNDEFINED', s); self.assertIn('MESTREOS-REMEDIO-EMOJI', s)
        self.assertIn('rest.charCodeAt(cut - 1) >= 0xd800', s)
        self.assertIn('MESTREOS-REMEDIO-RICH', s)  # 3º remédio (09/10/26): texto formatado
        for marca in ('CONVERSA', 'DIGITANDO', 'ASSINATURA'):  # 4º a 6º (20/10/26): relatório da aluna
            self.assertIn('MESTREOS-REMEDIO-' + marca, s)
        self.assertNotIn(b'\r\n', server.read_bytes())  # arquivo LF continua LF (o de CRLF tem teste próprio)
        self.assertEqual(subprocess.run(cmd + ['--check'], env=env, capture_output=True).returncode, 0)

    def test_new_remedy_is_all_or_nothing(self):
        # 20/10/26: remédio de vários trechos entra inteiro ou não entra; pela metade (chamada sem a função) quebraria o plugin
        server = self.root / 'plugins/cache/claude-plugins-official/telegram/metade/server.ts'
        server.parent.mkdir(parents=True)
        server.write_bytes(_ancoras().replace("      await bot.start({\n        onStart: info => {\n", '').encode('utf-8'))
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root))
        r = subprocess.run([sys.executable, str(SCRIPTS / 'telegram-plugin-remedio.py')], env=env, capture_output=True, encoding='utf-8')
        self.assertNotEqual(r.returncode, 0)
        s = server.read_text(encoding='utf-8')
        self.assertNotIn('MESTREOS-REMEDIO-CONVERSA', s); self.assertNotIn('mestreosArrastada', s)  # nada da conversa entrou
        self.assertIn('MESTREOS-REMEDIO-DIGITANDO', s); self.assertIn('MESTREOS-REMEDIO-ASSINATURA', s)  # os outros entraram
        self.assertNotEqual(subprocess.run([sys.executable, str(SCRIPTS / 'telegram-plugin-remedio.py'), '--check'], env=env, capture_output=True).returncode, 0)

    # sha256 do server.ts 0.0.7 original (LF), o que estes remédios conhecem. Plugin novo na máquina do aluno não pode
    # deixar a suíte vermelha (o 7D.3 exige verde): ali vale o --check, que recusa trecho desconhecido sem mexer.
    REAL_007 = 'd902d7195a527b579b889cfdbf251fc24fd224a68e319ac6b7c3b691515c3458'

    def _plugin_real(self):
        # a cópia da loja de plugins (marketplaces) fica sempre original; a do cache pode ter remédio ou patch do dono
        pedido = os.environ.get('MESTREOS_TELEGRAM_SERVER_TS', '')
        for c in (pedido, str(Path.home() / '.claude/plugins/marketplaces/claude-plugins-official/external_plugins/telegram/server.ts')):
            p = Path(c) if c else None
            if p and p.is_file():
                b = p.read_bytes(); t = b.decode('utf-8', errors='ignore')
                if 'MESTREOS-REMEDIO' in t or 'function startTyping(' in t or 'const bot = new Bot(TOKEN)' not in t: continue
                if c == pedido or __import__('hashlib').sha256(b.replace(b'\r\n', b'\n')).hexdigest() == self.REAL_007: return p
        return None

    def test_revert_is_all_or_nothing_too(self):
        # interrogar 405b: a volta desfazia meio remédio (sobrava a chamada sem a função) e ainda dizia que deu certo
        server = self.root / 'plugins/cache/claude-plugins-official/telegram/fixture/server.ts'
        server.parent.mkdir(parents=True); server.write_bytes(_ancoras().encode('utf-8'))
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root))
        cmd = [sys.executable, str(SCRIPTS / 'telegram-plugin-remedio.py')]
        self.assertEqual(subprocess.run(cmd, env=env, capture_output=True).returncode, 0)
        s = server.read_text(encoding='utf-8')
        mexido = s.replace("        mestreosEscolheu(args.chat_id as string, Number(args.message_id)) // MESTREOS-REMEDIO-CONVERSA: a escolha do agente vale\n", '')
        self.assertNotEqual(mexido, s); server.write_bytes(mexido.encode('utf-8'))
        r = subprocess.run(cmd + ['--revert'], env=env, capture_output=True, encoding='utf-8')
        self.assertNotEqual(r.returncode, 0); self.assertIn('✗', r.stdout)
        depois = server.read_text(encoding='utf-8')
        self.assertIn('function mestreosEscolheu(', depois); self.assertIn("bot.on('message_reaction'", depois)  # a conversa ficou inteira
        self.assertNotIn('MESTREOS-REMEDIO-DIGITANDO', depois); self.assertNotIn('MESTREOS-REMEDIO-ASSINATURA', depois)  # os outros voltaram

    def test_access_rule_comes_before_any_side_effect(self):
        # interrogar 405b (os dois revisores): localização gravava e consultava o mapa antes da régua de acesso do plugin
        server = self.root / 'plugins/cache/claude-plugins-official/telegram/fixture/server.ts'
        server.parent.mkdir(parents=True); server.write_bytes(_ancoras().encode('utf-8'))
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root))
        self.assertEqual(subprocess.run([sys.executable, str(SCRIPTS / 'telegram-plugin-remedio.py')], env=env, capture_output=True).returncode, 0)
        s = server.read_text(encoding='utf-8')
        def antes(guarda, efeito, de):
            i = s.index(de); self.assertLess(s.index(guarda, i), s.index(efeito, i), (guarda, efeito))
        antes('mestreosDoDono(m.chat, m.from)', 'await mestreosLocal(m)', "bot.on('message', async (ctx, next)")
        antes('mestreosDoDono(m.chat, m.from)', 'mestreosLocalSalva(m.location, true)', "bot.on('edited_message'")
        antes('mestreosDoDono(r.chat, user)', 'setMessageReaction', "bot.on('message_reaction'")
        regua = s[s.index('function mestreosDoDono('):s.index('function mestreosArrastada(')]
        for parte in ("chat?.type === 'private'", "a.dmPolicy !== 'disabled'", 'a.allowFrom.includes(String(from.id))'):
            self.assertIn(parte, regua)  # a mesma régua do gate() pro privado
        self.assertIn('chunk(mestreosAssina(text, parseMode), limit, mode)', s)
        self.assertIn('agora - pulso > MESTREOS_MUDO_MS', s)

    def test_unknown_upstream_is_never_taken_as_the_real_plugin(self):
        # rodada 2 (os dois revisores): o filtro por hash existia, mas nenhum teste provava que um plugin novo fica de
        # fora (o aluno com plugin novo não pode ver a suíte vermelha; ali vale o --check)
        casa = self.root / 'casa'
        alvo = casa / '.claude/plugins/marketplaces/claude-plugins-official/external_plugins/telegram/server.ts'
        alvo.parent.mkdir(parents=True); alvo.write_text('const bot = new Bot(TOKEN)\n// 0.0.8 de mentira\n', encoding='utf-8')
        with patch.dict(os.environ, {'HOME': str(casa), 'USERPROFILE': str(casa), 'MESTREOS_TELEGRAM_SERVER_TS': ''}):
            self.assertIsNone(self._plugin_real())
        with patch.dict(os.environ, {'HOME': str(casa), 'USERPROFILE': str(casa), 'MESTREOS_TELEGRAM_SERVER_TS': str(alvo)}):
            self.assertEqual(self._plugin_real(), alvo)   # pedido explícito de quem desenvolve vale

    def test_real_plugin_takes_all_six_and_reverts_identical(self):
        # o teste das âncoras mínimas não pega trecho que mudou no plugin de verdade: este usa o 0.0.7 original, se houver
        real = self._plugin_real()
        if not real: self.skipTest('sem cópia original do plugin 0.0.7 nesta máquina')
        server = self.root / 'plugins/cache/claude-plugins-official/telegram/0.0.7/server.ts'
        server.parent.mkdir(parents=True); original = real.read_bytes(); server.write_bytes(original)
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root))
        cmd = [sys.executable, str(SCRIPTS / 'telegram-plugin-remedio.py')]
        r = subprocess.run(cmd, env=env, capture_output=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stdout); self.assertEqual(r.stdout.count('remédio aplicado'), 6, r.stdout)
        s = server.read_text(encoding='utf-8')
        self.assertLess(s.index("bot.on('message', async (ctx, next)"), s.index('// MESTREOS-REMEDIO-RICH:'))  # localização antes do genérico
        self.assertLess(s.index('const mestreosPendentes'), s.index('await mcp.connect('))  # Map pronto antes de a 1ª ferramenta chegar
        primeira = server.read_bytes()
        self.assertEqual(subprocess.run(cmd, env=env, capture_output=True).returncode, 0); self.assertEqual(server.read_bytes(), primeira)
        self.assertEqual(subprocess.run(cmd + ['--revert'], env=env, capture_output=True).returncode, 0)
        self.assertEqual(server.read_bytes(), original)

    @unittest.skipUnless(__import__('shutil').which('bun'), 'sem bun nesta máquina (o plugin do Claude roda em bun; teste de comportamento pulado)')
    def test_signature_block_behavior_in_bun(self):
        state = self.root / 'state'; state.mkdir()
        r = _bun(self.root, "import { readFileSync, writeFileSync } from 'fs'\nimport { join } from 'path'\n"
                 f"const STATE_DIR = {json.dumps(str(state))}\n" + _remedio().ASSINATURA_BLOCO +
                 "const out: any = { sem: mestreosAssina('oi') }\n"
                 "writeFileSync(join(STATE_DIR, 'assinatura'), '🧠 Claude · Opus 5.5 · high\\n')\n"
                 "out.com = mestreosAssina('oi'); out.limpo = mestreosAssina('  [[limpo]]  Texto pra outra pessoa')\n"
                 "out.md = mestreosAssina('*oi*', 'MarkdownV2')\n"
                 "out.vazio = mestreosAssina(''); console.log(JSON.stringify(out))\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out['sem'], 'oi'); self.assertEqual(out['com'], 'oi\n\n🧠 Claude · Opus 5.5 · high')
        self.assertEqual(out['md'], '*oi*\n\n🧠 Claude · Opus 5\\.5 · high')  # o ponto é reservado no MarkdownV2
        self.assertEqual(out['limpo'], 'Texto pra outra pessoa'); self.assertEqual(out['vazio'], '')

    @unittest.skipUnless(__import__('shutil').which('bun'), 'sem bun nesta máquina (o plugin do Claude roda em bun; teste de comportamento pulado)')
    def test_typing_heartbeat_lasts_until_turn_end_in_bun(self):
        # 20/10/26: o "digitando" bate até o FIM DO TURNO (gancho Stop), não até a 1ª resposta
        state = self.root / 'state'; state.mkdir()
        r = _bun(self.root, "import { readFileSync, statSync, writeFileSync } from 'fs'\nimport { join } from 'path'\n"
                 f"const STATE_DIR = {json.dumps(str(state))}\nlet batidas = 0\n"
                 "const bot = { api: { sendChatAction: async () => { batidas++ } } }\n" + _remedio().DIGITANDO_BLOCO +
                 "const espera = (ms: number) => new Promise(r => setTimeout(r, ms))\nconst out: any = { ganchos: mestreosComGanchos() }\n"
                 "mestreosDigitando('1'); await espera(400); out.sozinho = batidas\n"
                 "writeFileSync(join(STATE_DIR, 'turn-start'), String(Date.now())); await espera(300); out.aberto = batidas\n"
                 "writeFileSync(join(STATE_DIR, 'turn-end'), String(Date.now() + 5)); await espera(200); out.fim = batidas\n"
                 "await espera(300); out.depois = batidas; out.timers = mestreosBatidas.size\nconsole.log(JSON.stringify(out))\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertFalse(out['ganchos'])
        self.assertGreaterEqual(out['sozinho'], 4)              # bate sozinho, sem esperar a 1ª resposta
        self.assertGreaterEqual(out['aberto'] - out['sozinho'], 3)  # turno aberto: continua
        self.assertEqual(out['depois'], out['fim']); self.assertEqual(out['timers'], 0)  # fim do turno: apaga e solta o timer

    @unittest.skipUnless(__import__('shutil').which('bun'), 'sem bun nesta máquina (o plugin do Claude roda em bun; teste de comportamento pulado)')
    def test_typing_stops_when_an_open_turn_goes_silent_in_bun(self):
        # interrogar 405b: Esc na janela não tem gancho; turno aberto sem sinal de vida não pode bater 3 h
        state = self.root / 'state'; state.mkdir()
        r = _bun(self.root, "import { readFileSync, statSync, writeFileSync } from 'fs'\nimport { join } from 'path'\n"
                 f"const STATE_DIR = {json.dumps(str(state))}\nlet batidas = 0\n"
                 "const bot = { api: { sendChatAction: async () => { batidas++ } } }\n" + _remedio().DIGITANDO_BLOCO +
                 "const espera = (ms: number) => new Promise(r => setTimeout(r, ms))\nconst out: any = {}\n"
                 "writeFileSync(join(STATE_DIR, 'turn-end'), String(Date.now() - 9000))\n"
                 "writeFileSync(join(STATE_DIR, 'turn-start'), String(Date.now()))\n"
                 "mestreosDigitando('1'); await espera(150); out.vivo = mestreosBatidas.size\n"
                 "writeFileSync(join(STATE_DIR, 'tool-activity'), String(Date.now())); await espera(250); out.pulso = mestreosBatidas.size\n"
                 "await espera(450); out.mudo = mestreosBatidas.size\nconsole.log(JSON.stringify(out))\n",
                 MESTREOS_TELEGRAM_MUDO_MS='300')
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual((out['vivo'], out['pulso'], out['mudo']), (1, 1, 0))  # ferramenta segura aceso; silêncio apaga

    @unittest.skipUnless(__import__('shutil').which('bun'), 'sem bun nesta máquina (o plugin do Claude roda em bun; teste de comportamento pulado)')
    def test_conversa_block_behavior_in_bun(self):
        # resposta arrastada, localização e a troca da reação de chegada, iguais à janela da Dupla (7D)
        state = self.root / 'state'; state.mkdir()
        r = _bun(self.root, "import { readFileSync, writeFileSync, renameSync } from 'fs'\nimport { join } from 'path'\n"
                 f"const STATE_DIR = {json.dumps(str(state))}\ntype Context = any\ntype ReactionTypeEmoji = any\n"
                 "const reacoes: any[] = []\nconst bot = { api: { setMessageReaction: async (c: string, m: number, r: any) => { reacoes.push([m, r[0].emoji]) } } }\n"
                 "globalThis.fetch = (async () => new Response(JSON.stringify({ display_name: 'Rua da Bahia, 1000' }))) as any\n"
                 "function loadAccess(): any { return acesso }\n"
                 + _remedio().CONVERSA_BLOCO +
                 "const bot_ = { from: { is_bot: true } }\nconst out: any = {}\n"
                 "out.arrastada = mestreosArrastada({ message: { reply_to_message: { ...bot_, text: 'Proposta  A\\n ou B?' } } })\n"
                 "out.propria = mestreosArrastada({ message: { reply_to_message: { from: { is_bot: false }, text: 'minha' } } })\n"
                 "out.nenhuma = mestreosArrastada({ message: {} })\n"
                 "out.local = await mestreosLocal({ location: { latitude: -19.93, longitude: -43.94, horizontal_accuracy: 12 } })\n"
                 "out.lugar = await mestreosLocal({ venue: { location: { latitude: 1, longitude: 2 }, title: 'Padaria', address: 'Rua X' } })\n"
                 "out.vivo = await mestreosLocal({ location: { latitude: 3, longitude: 4, live_period: 600 } })\n"
                 "out.salvo = JSON.parse(readFileSync(join(STATE_DIR, 'ultima-localizacao.json'), 'utf8'))\n"
                 "mestreosPendente('1', 11); mestreosPendente('1', 12); mestreosEscolheu('1', 12); mestreosFinaliza('1'); mestreosFinaliza('1')\n"
                 "let acesso: any = { dmPolicy: 'allowlist', allowFrom: ['42'] }\n"
                 "const regua = () => [mestreosDoDono({ type: 'private' }, { id: 42 }), mestreosDoDono({ type: 'group' }, { id: 42 }),\n"
                 "  mestreosDoDono({ type: 'private' }, { id: 7 }), mestreosDoDono({ type: 'private' }, undefined)]\n"
                 "out.regua = regua(); acesso = { dmPolicy: 'disabled', allowFrom: ['42'] }; out.desligado = regua()\n"
                 "await new Promise(r => setTimeout(r, 50)); out.reacoes = reacoes\nconsole.log(JSON.stringify(out))\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out['arrastada'], '[o dono respondeu arrastando esta sua mensagem: «Proposta A ou B?»]\n')
        self.assertEqual(out['propria'], ''); self.assertEqual(out['nenhuma'], '')  # só mensagem do agente, igual ao 7D
        self.assertEqual(out['local'], '[localização enviada pelo dono: Rua da Bahia, 1000 · -19.930000, -43.940000 (precisão ~12 m) · https://maps.google.com/?q=-19.93,-43.94.]')
        self.assertTrue(out['lugar'].startswith('[localização enviada pelo dono: Padaria · Rua X · 1.000000, 2.000000'))
        self.assertIn('AO VIVO por 10 min', out['vivo']); self.assertEqual(out['salvo']['ao_vivo'], True)
        self.assertEqual(out['reacoes'], [[11, '👌']])  # a escolhida (12) fica; 👌 só uma vez
        self.assertEqual(out['regua'], [True, False, False, False])  # só o dono, só no privado
        self.assertEqual(out['desligado'], [False, False, False, False])  # canal desligado: ninguém

    def test_crlf_file_keeps_crlf_and_revert_is_byte_identical(self):
        server = self.root / 'plugins/cache/claude-plugins-official/telegram/win/server.ts'
        server.parent.mkdir(parents=True)
        original = b'// cabecalho\r\n' + _ancoras().replace('\n', '\r\n').encode('utf-8') + b'// fim\r\n'
        server.write_bytes(original)
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root))
        cmd = [sys.executable, str(Path(__file__).parent / 'telegram-plugin-remedio.py')]
        self.assertEqual(subprocess.run(cmd, env=env, capture_output=True).returncode, 0)
        b = server.read_bytes()
        self.assertIn(b'MESTREOS-REMEDIO-EMOJI', b); self.assertIn(b'MESTREOS-REMEDIO-UNDEFINED', b); self.assertIn(b'MESTREOS-REMEDIO-RICH', b)
        for marca in (b'CONVERSA', b'DIGITANDO', b'ASSINATURA'): self.assertIn(b'MESTREOS-REMEDIO-' + marca, b)
        self.assertEqual(b.count(b'\n'), b.count(b'\r\n'))  # nenhuma linha virou LF
        self.assertTrue(b.startswith(b'// cabecalho\r\n') and b.endswith(b'// fim\r\n'))
        self.assertEqual(subprocess.run(cmd + ['--revert'], env=env, capture_output=True).returncode, 0)
        self.assertEqual(server.read_bytes(), original)

    def test_equivalent_owner_fix_is_not_stacked(self):
        server = self.root / 'plugins/cache/claude-plugins-official/telegram/dono/server.ts'
        server.parent.mkdir(parents=True)
        dono = ('        const text = (args.text ?? (args as Record<string, unknown>).message) as string // PATCH DO DONO\n'
                '    if (cut > 1 && rest.charCodeAt(cut - 1) >= 0xd800 && rest.charCodeAt(cut - 1) <= 0xdbff) cut-- // PATCH DO DONO\n'
                '    out.push(rest.slice(0, cut))\n'
                "bot.on('message', async ctx => { if ((ctx.message as any).rich_message) {} }) // PATCH DO DONO\n"
                "bot.on('message_reaction', async ctx => {}) // PATCH DO DONO\n"
                'function startTyping(chat_id: string): void {} // PATCH DO DONO\n'
                "const s = readFileSync(join(STATE_DIR, 'assinatura'), 'utf8') // PATCH DO DONO\n"
                'type AttachmentMeta = {\n')
        server.write_text(dono, encoding='utf-8')
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root))
        cmd = [sys.executable, str(Path(__file__).parent / 'telegram-plugin-remedio.py')]
        self.assertEqual(subprocess.run(cmd, env=env, capture_output=True).returncode, 0)
        self.assertEqual(server.read_text(encoding='utf-8'), dono)
        self.assertEqual(subprocess.run(cmd + ['--check'], env=env, capture_output=True).returncode, 0)

    def test_partial_plugin_applies_known_and_flags_unknown(self):
        server = self.root / 'plugins/cache/claude-plugins-official/telegram/partial/server.ts'
        server.parent.mkdir(parents=True); server.write_text('        const text = args.text as string\n', encoding='utf-8')
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root))
        cmd = [sys.executable, str(Path(__file__).parent / 'telegram-plugin-remedio.py')]
        r = subprocess.run(cmd, env=env, capture_output=True, encoding='utf-8')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('MESTREOS-REMEDIO-UNDEFINED', server.read_text(encoding='utf-8'))
        self.assertNotEqual(subprocess.run(cmd + ['--check'], env=env, capture_output=True).returncode, 0)

    def _plugin_com_handlers(self, nome):
        server = self.root / f'plugins/cache/claude-plugins-official/telegram/{nome}/server.ts'
        server.parent.mkdir(parents=True)
        server.write_bytes(("bot.on('message:text', async ctx => {\n  await handleInbound(ctx, ctx.message.text, undefined)\n})\n"
                            "bot.on('message:sticker', async ctx => {\n  await handleInbound(ctx, '(sticker)', undefined)\n})\n\n"
                            "type AttachmentMeta = {\n  kind: string\n}\n").encode('utf-8'))
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root))
        r = subprocess.run([sys.executable, str(Path(__file__).parent / 'telegram-plugin-remedio.py')], env=env, capture_output=True, encoding='utf-8')
        return server, r

    def test_rich_remedy_goes_after_every_plugin_handler(self):
        # 09/10/26: o handler genérico só pode ver o que nenhum handler do plugin leu; antes deles ele roubaria texto/foto.
        server, r = self._plugin_com_handlers('ordem')
        self.assertIn('texto formatado remédio aplicado', r.stdout)   # (os outros 2 remédios não têm âncora nesta fixture)
        s = server.read_text(encoding='utf-8')
        self.assertEqual(s.count('MESTREOS-REMEDIO-RICH'), 2)
        self.assertGreater(s.index("bot.on('message', async ctx"), s.index("bot.on('message:sticker'"))
        self.assertLess(s.index("bot.on('message', async ctx"), s.index('type AttachmentMeta = {'))

    @unittest.skipUnless(__import__('shutil').which('bun'), 'sem bun nesta máquina (o plugin do Claude roda em bun; teste de comportamento pulado)')
    def test_rich_remedy_behavior_in_bun(self):
        # comportamento do bloco remediado: rich_message vira texto; texto/foto não duplicam; tipo desconhecido e rich vazio viram nota
        server, r = self._plugin_com_handlers('bun')
        self.assertIn('texto formatado remédio aplicado', r.stdout)   # (os outros 2 remédios não têm âncora nesta fixture)
        s = server.read_text(encoding='utf-8')
        bloco = s[s.index('// MESTREOS-REMEDIO-RICH'):s.index('type AttachmentMeta = {')]
        rich = {'blocks': [{'type': 'paragraph', 'text': 'Oi, segue o plano:'},
                           {'type': 'list', 'items': [{'label': '1.', 'blocks': [{'type': 'paragraph', 'text': 'Primeiro eu mando.'}]},
                                                      {'label': '2.', 'blocks': [{'type': 'paragraph', 'text': 'Depois a empresa publica.'}]}]},
                           {'type': 'paragraph', 'text': 'Um abraço'}]}
        harness = ("const handlers: any[] = []\nconst bot = { on: (ev: string, fn: any) => { handlers.push([ev, fn]) } }\n"
                   "const inbound: string[] = []\nasync function handleInbound(_c: any, t: string, _d: any) { inbound.push(t) }\n"
                   + bloco +
                   "const h = handlers.find(([ev]) => ev === 'message')![1]\n"
                   "const msg = (x: any) => ({ message: { message_id: 1, chat: { id: 1 }, from: { id: 42 }, date: 1, ...x } })\n"
                   "const out: any = {}\n"
                   f"await h(msg({{ rich_message: {json.dumps(rich, ensure_ascii=False)} }})); out.rich = inbound.splice(0)\n"
                   "await h(msg({ text: 'oi' })); out.texto = inbound.splice(0)\n"
                   "await h(msg({ photo: [{}], caption: 'x' })); out.foto = inbound.splice(0)\n"
                   "await h(msg({ tipo_do_futuro: { a: 1 } })); out.desconhecido = inbound.splice(0)\n"
                   "await h(msg({ rich_message: { blocks: [] } })); out.vazio = inbound.splice(0)\n"
                   "console.log(JSON.stringify(out))\n")
        f = self.root / 'harness.ts'; f.write_text(harness, encoding='utf-8')
        r = subprocess.run(['bun', str(f)], capture_output=True, encoding='utf-8', timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(len(out['rich']), 1)
        t = out['rich'][0]
        self.assertTrue(t.startswith('Oi, segue o plano:') and t.endswith('Um abraço'), t)
        self.assertIn('1. Primeiro eu mando.', t); self.assertIn('2. Depois a empresa publica.', t)
        self.assertEqual(out['texto'], []); self.assertEqual(out['foto'], [])   # o handler do plugin cuida; nada duplicado
        self.assertEqual(len(out['desconhecido']), 1); self.assertIn('tipo_do_futuro', out['desconhecido'][0]); self.assertIn('não invente', out['desconhecido'][0])
        self.assertEqual(len(out['vazio']), 1); self.assertIn('rich_message', out['vazio'][0])

    def test_unknown_plugin_version_is_not_modified(self):
        server = self.root / 'plugins/cache/claude-plugins-official/telegram/new/server.ts'
        server.parent.mkdir(parents=True); server.write_text('const totallyDifferent = true;\n')
        original = server.read_bytes()
        r = subprocess.run([sys.executable, str(Path(__file__).parent / 'telegram-plugin-remedio.py')],
                           env=dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root)), capture_output=True)
        self.assertNotEqual(r.returncode, 0); self.assertEqual(server.read_bytes(), original)


SID = '0b9e3c1a-1111-4222-8333-444455556666'


def _quando(seg=0):
    return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(time.time() + seg)) + '.000Z'


def _resposta(modelo, seg=-60, ferramenta=None, entrada=None):
    c = [{'type': 'text', 'text': 'ok'}]
    if ferramenta: c.append({'type': 'tool_use', 'id': 'x', 'name': ferramenta, 'input': entrada or {}})
    return {'type': 'assistant', 'timestamp': _quando(seg), 'message': {'model': modelo, 'content': c}}


def _esforco(nivel):
    return {'type': 'system', 'timestamp': _quando(-90), 'output_config': {'effort': nivel}}  # como a conversa registra


def _do_dono(texto, seg=-30, audio=False, chat='42', user='42'):
    extra = ' attachment_kind="voice" attachment_file_id="f1"' if audio else ''
    return {'type': 'user', 'timestamp': _quando(seg), 'message': {'role': 'user', 'content':
            f'<channel source="plugin:telegram:telegram" chat_id="{chat}" message_id="9" user="aluno" user_id="{user}" ts="x"{extra}>'
            f'{"(voice message)" if audio else texto}</channel>'}}


def _na_fila(texto, seg=-30):
    """Mensagem que chegou com a janela trabalhando: o Claude Code grava como anexo da fila (formato visto no 2.1.30x)."""
    tag = f'<channel source="plugin:telegram:telegram" chat_id="42" message_id="9" user="aluno" user_id="42" ts="x">{texto}</channel>'
    return {'type': 'attachment', 'timestamp': _quando(seg), 'attachment': {
        'type': 'queued_command', 'prompt': tag, 'commandMode': 'prompt', 'isMeta': True, 'timestamp': _quando(seg),
        'origin': {'kind': 'channel', 'server': 'plugin:telegram:telegram'}}}


class TurnoJanelaDoBotTests(unittest.TestCase):
    """Ganchos da janela do bot (7A, 20/10/26): marcam início, ferramenta e fim do turno (Stop e StopFailure), gravam a
    assinatura, lembram o Telegram a cada mensagem e seguram uma vez o fim que ficou sem reply."""
    LIMPA = ('TELEGRAM_STATE_DIR', 'CLAUDE_CONFIG_DIR', 'CLAUDE_EFFORT', 'CLAUDE_PID', 'CLAUDE_CODE_SESSION_ID',
             'MESTREOS_MEUBOT', 'MESTREOS_TELEGRAM_BOT_DIR', 'MESTREOS_TELEGRAM_TROCA_SECO')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.state = self.root / 'state'; self.bot = self.root / 'bot'

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if k not in self.LIMPA}  # o teste roda dentro de uma sessão do Claude
        env.update(TELEGRAM_STATE_DIR=str(self.state), MESTREOS_TELEGRAM_BOT_DIR=str(self.bot), MESTREOS_TELEGRAM_TROCA_SECO='1')
        env.update(extra)
        return env

    def roda(self, evento, entrada='', env=None, **extra):
        r = subprocess.run([sys.executable, str(SCRIPTS / 'telegram-bot-turno.py'), evento], input=entrada.encode('utf-8'),
                           env=env or self.env(**extra), capture_output=True, timeout=30)
        r.stdout, r.stderr = r.stdout.decode('utf-8'), r.stderr.decode('utf-8', 'replace')
        return r

    def conversa(self, linhas, nome='conversa.jsonl', **campos):
        t = self.root / nome
        t.write_text('\n'.join(json.dumps(x, ensure_ascii=False) for x in linhas) + '\n', encoding='utf-8')
        return json.dumps({'transcript_path': str(t), 'session_id': SID, **campos}, ensure_ascii=False)

    def assinatura(self):
        return (self.state / 'assinatura').read_text(encoding='utf-8').strip()

    def test_inicio_marks_turn_and_signs_with_model_and_effort(self):
        antes = int(time.time() * 1000)
        r = self.roda('inicio', self.conversa([_resposta('claude-sonnet-5-5'), _esforco('medium'),
                                                _resposta('claude-opus-5-5', -20), _esforco('high')]))
        self.assertEqual((r.returncode, r.stdout), (0, ''))  # sem a tag do Telegram, nada entra no contexto
        self.assertGreaterEqual(int((self.state / 'turn-start').read_text().strip()), antes)
        self.assertEqual(self.assinatura(), '🧠 Claude · Opus 5.5 · high')  # a última vale

    def test_model_written_in_a_tool_input_does_not_fool_the_signature(self):
        # a assinatura lê o campo da resposta, nunca o texto: o agente pode estar escrevendo código que cita outro modelo
        self.roda('inicio', self.conversa([_resposta('claude-opus-5-5', -10, 'Write', {'content': '"model": "claude-haiku-5-5"'})]))
        self.assertEqual(self.assinatura(), '🧠 Claude · Opus 5.5')

    def test_effort_seen_mid_turn_wins_next_turn(self):
        # o esforço só aparece no meio do turno (CLAUDE_EFFORT na ferramenta, campo effort no Stop): fica pro próximo início
        entrada = self.conversa([_resposta('claude-opus-5-5'), _esforco('medium')])
        self.roda('ferramenta', '{}', CLAUDE_EFFORT='max'); self.roda('inicio', entrada)
        self.assertEqual(self.assinatura(), '🧠 Claude · Opus 5.5 · max')
        self.roda('fim', json.dumps({'effort': {'level': 'low'}})); self.roda('inicio', entrada)
        self.assertEqual(self.assinatura(), '🧠 Claude · Opus 5.5 · low')

    def test_tool_and_end_only_mark(self):
        self.assertEqual(self.roda('ferramenta').returncode, 0); self.assertEqual(self.roda('fim').returncode, 0)
        self.assertTrue((self.state / 'tool-activity').read_text().strip().isdigit())
        self.assertTrue((self.state / 'turn-end').read_text().strip().isdigit())
        self.assertFalse((self.state / 'assinatura').exists())

    def test_stop_failure_ends_the_turn_silently(self):
        # erro de API (limite do plano, sobrecarga) não dispara Stop: sem isso o "digitando" ficaria aceso até o teto
        r = self.roda('falha', json.dumps({'error': 'rate_limit', 'hook_event_name': 'StopFailure'}))
        self.assertEqual((r.returncode, r.stdout), (0, ''))
        self.assertTrue((self.state / 'turn-end').read_text().strip().isdigit())

    def test_bad_input_or_no_conversation_never_fails(self):
        for entrada in ('isto não é json', json.dumps({'transcript_path': str(self.root / 'nao-existe.jsonl')}), ''):
            r = self.roda('inicio', entrada)
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, '', ''))
        self.assertTrue((self.state / 'turn-start').exists()); self.assertEqual(self.assinatura(), '')

    def test_unknown_event_writes_nothing(self):
        self.assertEqual(self.roda('qualquer').returncode, 0); self.assertFalse(self.state.exists())

    def test_names_and_effort_labels(self):
        casos = [('claude-fable-5-1', 'xhigh', '🧠 Claude · Fable 5.1 · xhigh'), ('claude-haiku-5-5', 'low', '🧠 Claude · Haiku 5.5 · low'),
                 ('claude-opus-5', 'max', '🧠 Claude · Opus 5 · max'), ('claude-sonnet-5-5', None, '🧠 Claude · Sonnet 5.5'),
                 ('claude-sonnet-4-20250514', None, '🧠 Claude · Sonnet 4'), ('claude-opus-5-5[1m]', 'high', '🧠 Claude · Opus 5.5 · high')]
        for modelo, esforco, esperado in casos:
            self.roda('inicio', self.conversa([_resposta(modelo)] + ([_esforco(esforco)] if esforco else [])))
            self.assertEqual(self.assinatura(), esperado, modelo)

    def test_signature_carries_the_official_effort_id_never_a_translation(self):
        # 21/10/26: a assinatura dizia "máximo", nome que nenhuma provedora usa. Sai o id do claude --effort, sem
        # tradução (low, medium, high, xhigh, max), venha o esforço da conversa, da ferramenta (CLAUDE_EFFORT) ou do Stop.
        sem = self.conversa([_resposta('claude-opus-5-5')])
        marca = self.state / 'esforco.json'   # o esforço visto no meio do turno vale mais que o da conversa: começa limpo
        for nivel in ('low', 'medium', 'high', 'xhigh', 'max'):
            esperado = f'🧠 Claude · Opus 5.5 · {nivel}'
            marca.unlink(missing_ok=True)
            self.roda('inicio', self.conversa([_resposta('claude-opus-5-5'), _esforco(nivel)]))      # registrado na conversa
            self.assertEqual(self.assinatura(), esperado, nivel)
            outro = 'low' if nivel != 'low' else 'max'
            self.roda('ferramenta', '{}', CLAUDE_EFFORT=outro); self.roda('inicio', sem)
            self.assertEqual(self.assinatura(), f'🧠 Claude · Opus 5.5 · {outro}', outro)             # visto no meio do turno
            self.roda('fim', json.dumps({'effort': {'level': nivel}})); self.roda('inicio', sem)       # campo do Stop
            self.assertEqual(self.assinatura(), esperado, nivel)
            self.assertIsNone(re.search(r'\b(baixo|médio|alto|altíssimo|máximo)\b', self.assinatura()), nivel)
        # id que não é nível (ultracode é interruptor, não nível): a assinatura fica só com o modelo, sem inventar nome
        marca.unlink(missing_ok=True)
        self.roda('ferramenta', '{}', CLAUDE_EFFORT='ultracode'); self.roda('inicio', self.conversa([_resposta('claude-opus-5-5'), _esforco('ultracode')]))
        self.assertEqual(self.assinatura(), '🧠 Claude · Opus 5.5')

    def test_default_folder_follows_claude_config_dir(self):
        cfg = self.root / 'cfg'
        env = {k: v for k, v in self.env(CLAUDE_CONFIG_DIR=str(cfg)).items() if k != 'TELEGRAM_STATE_DIR'}
        self.assertEqual(self.roda('fim', env=env).returncode, 0)
        self.assertTrue((cfg / 'channels' / 'telegram' / 'turn-end').exists())  # mesma pasta que o plugin lê

    def test_reminder_only_for_telegram_and_survives_windows_console(self):
        # 20/10/26: só a regra escrita não fazia o agente trocar a reação; o lembrete vai em toda mensagem do Telegram.
        # PYTHONIOENCODING=cp1252 imita o console do Windows: caminho com acento e emoji não podem derrubar nada
        tag = '<channel source="plugin:telegram:telegram" chat_id="42" message_id="9" user="aluno" ts="x">oi</channel>'
        entrada = self.conversa([_resposta('claude-opus-5-5')], nome='conversa-ação-🧠.jsonl', prompt=tag)
        r = self.roda('inicio', entrada, PYTHONIOENCODING='cp1252')
        self.assertEqual(r.returncode, 0)
        self.assertIn('[Telegram] Responda SEMPRE pela ferramenta reply', r.stdout); self.assertIn('✍', r.stdout)
        self.assertEqual(self.assinatura(), '🧠 Claude · Opus 5.5')
        self.assertNotIn('telegram-bot-troca.py', r.stdout)  # "oi" não fala de modelo: sem a dica da troca
        # 21/10/26: texto pra copiar vai sozinho no balão com [[limpo]]; a assinatura do modelo é só do Telegram
        self.assertIn('[[limpo]]', r.stdout); self.assertIn('sozinho', r.stdout); self.assertIn('e-mail', r.stdout)
        manual = (SCRIPTS / 'telegram-janela-do-bot.md').read_text(encoding='utf-8')
        self.assertIn('[[limpo]]', manual); self.assertIn('e-mail', manual); self.assertNotIn('🟣', manual)
        self.assertEqual(self.roda('inicio', self.conversa([], prompt='pergunta digitada na janela')).stdout, '')

    def test_switch_hint_with_the_exact_command_only_when_it_matters(self):
        # o agente do aluno não sabe qual Python a máquina usa: a dica traz o comando exato, só quando a mensagem pede
        tag = '<channel source="plugin:telegram:telegram" chat_id="42" message_id="9" user="aluno" ts="x"{}>{}</channel>'
        for extra, texto, tem in (('', 'troca pro Sonnet', True), ('', 'muda o esforço pra máximo', True),
                                  (' attachment_kind="voice" attachment_file_id="f"', '(voice message)', True),
                                  ('', 'manda a foto do relatório', False)):
            out = self.roda('inicio', self.conversa([], prompt=tag.format(extra, texto))).stdout
            self.assertEqual('telegram-bot-troca.py" trocar --pedido' in out, tem, texto)
            if tem: self.assertIn(sys.executable, out)

    def test_stop_holds_once_when_a_telegram_request_had_no_reply(self):
        # 20/10/26: uma sessão escreveu a resposta só na tela; a trava do fim pede o reply UMA vez
        sem = self.conversa([_do_dono('qual a previsão?'), _resposta('claude-opus-5-5', -5)])
        r = self.roda('fim', sem)
        self.assertEqual(json.loads(r.stdout)['decision'], 'block'); self.assertIn('ferramenta reply', json.loads(r.stdout)['reason'])
        segunda = json.loads(sem); segunda['stop_hook_active'] = True
        self.assertEqual(self.roda('fim', json.dumps(segunda)).stdout, '')  # já segurou uma vez: deixa encerrar
        com = self.conversa([_do_dono('qual a previsão?'), _resposta('claude-opus-5-5', -5, 'mcp__plugin_telegram_telegram__reply')])
        self.assertEqual(self.roda('fim', com).stdout, '')
        self.assertEqual(self.roda('fim', self.conversa([_resposta('claude-opus-5-5', -5)])).stdout, '')  # pedido da janela

    def test_stop_guard_also_sees_a_message_that_arrived_in_the_queue(self):
        # rodada 2 (revisor A, conferido no transcript real): mensagem que chega com a janela trabalhando vira anexo
        # "queued_command"; a trava do fim não via esse pedido
        r = self.roda('fim', self.conversa([_resposta('claude-opus-5-5', -20), _na_fila('e o relatório?', -10),
                                            _resposta('claude-opus-5-5', -2)]))
        self.assertEqual(json.loads(r.stdout)['decision'], 'block')
        self.assertFalse((self.state / 'turn-end').exists())   # segurou: o turno continua, não é fim
        resumo = {'type': 'user', 'isCompactSummary': True, 'timestamp': _quando(-5), 'message': {'content':
                  'Resumo: <channel source="plugin:telegram:telegram" chat_id="42" user_id="42">antiga</channel>'}}
        self.assertEqual(self.roda('fim', self.conversa([resumo, _resposta('claude-opus-5-5', -2)])).stdout, '')

    def test_session_start_records_the_window(self):
        self.roda('sessao', self.conversa([]), CLAUDE_PID='4242')
        s = json.loads((self.state / 'sessao.json').read_text(encoding='utf-8'))
        self.assertEqual((s['pid'], s['sid']), ('4242', SID)); self.assertTrue(s['transcript'].endswith('conversa.jsonl'))


class TrocaDeModeloTests(unittest.TestCase):
    """Troca de modelo e esforço pelo Telegram (7A, 20/10/26): só a frase do dono troca; áudio confirma; a janela reaberta
    retoma a mesma conversa e avisa assinada com o modelo novo; modelo que falha na 1ª resposta volta pro de antes."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.state = self.root / 'state'; self.bot = self.root / 'bot'; self.t = self.root / 'conversa.jsonl'
        self.linhas = []

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if k not in TurnoJanelaDoBotTests.LIMPA}
        env.update(TELEGRAM_STATE_DIR=str(self.state), MESTREOS_TELEGRAM_BOT_DIR=str(self.bot), CLAUDE_PID='4242',
                   MESTREOS_MEUBOT='1', MESTREOS_TELEGRAM_TROCA_SECO='1')
        env.update(extra)
        return {k: v for k, v in env.items() if v is not None}

    def escreve(self, *linhas):
        self.linhas += list(linhas)
        self.t.write_text('\n'.join(json.dumps(x, ensure_ascii=False) for x in self.linhas) + '\n', encoding='utf-8')

    def gancho(self, evento, pid='4242', **campos):
        entrada = json.dumps({'transcript_path': str(self.t), 'session_id': SID, **campos}, ensure_ascii=False)
        r = subprocess.run([sys.executable, str(SCRIPTS / 'telegram-bot-turno.py'), evento], input=entrada.encode('utf-8'),
                           env=self.env(CLAUDE_PID=pid), capture_output=True, timeout=30)
        return r.stdout.decode('utf-8')

    def troca(self, *args, **extra):
        r = subprocess.run([sys.executable, str(SCRIPTS / 'telegram-bot-troca.py')] + list(args), env=self.env(**extra),
                           capture_output=True, timeout=60)
        return r.returncode, r.stdout.decode('utf-8')

    def janela(self, *linhas, pid='4242'):
        self.state.mkdir(exist_ok=True)   # a lista de acesso do plugin: só o 42 fala com o bot
        (self.state / 'access.json').write_text(json.dumps({'dmPolicy': 'allowlist', 'allowFrom': ['42'], 'groups': {}}))
        self.escreve(*linhas); self.gancho('sessao', pid=pid)

    def arquivo(self, nome):
        p = self.bot / nome
        return p.read_text(encoding='ascii').strip() if p.exists() else None

    def estado(self):
        return json.loads((self.bot / 'troca.json').read_text(encoding='utf-8'))

    def espera_estado(self, valor, teto=15):
        fim = time.time() + teto
        while time.time() < fim:
            try:
                if self.estado().get('estado') == valor: return True
            except (OSError, ValueError): pass
            time.sleep(0.1)
        return False

    def test_clear_phrase_switches_and_the_window_comes_back_signed(self):
        self.janela(_resposta('claude-opus-5-5', -120), _esforco('high'), _do_dono('troca pro sonnet', -5))
        rc, out = self.troca('trocar', '--pedido', 'troca pro sonnet')
        self.assertEqual(rc, 0, out); self.assertIn('OK:', out); self.assertIn('⏳ Trocando pra Sonnet', out)
        self.assertEqual(self.arquivo('opcoes'), '--model sonnet')
        self.assertEqual(self.arquivo('retomar'), f'--resume {SID} MESTREOS_TROCA_CONCLUIDA_42')
        self.assertEqual(self.estado()['estado'], 'pedido')
        # o agente manda o "⏳" e encerra; a derrubada vê o fim do turno e marca o reinício
        self.state.mkdir(exist_ok=True)
        (self.state / 'turn-start').write_text(str(int(time.time() * 1000) - 5000))
        (self.state / 'turn-end').write_text(str(int(time.time() * 1000) + 10))
        self.assertEqual(self.troca('derrubar', '4242', str(int(time.time() * 1000) - 1000))[0], 0)
        self.assertEqual(self.estado()['estado'], 'reiniciando')
        # a janela reabre (processo novo, MESMA conversa): a assinatura já sai com o modelo pedido
        self.gancho('sessao', pid='5151')
        self.assertEqual(self.estado()['estado'], 'voltou')
        self.assertEqual((self.state / 'assinatura').read_text(encoding='utf-8').strip(), '🧠 Claude · Sonnet')
        self.escreve({'type': 'user', 'timestamp': _quando(), 'message': {'role': 'user', 'content': 'MESTREOS_TROCA_CONCLUIDA_42'}})
        aviso = self.gancho('inicio', pid='5151', prompt='MESTREOS_TROCA_CONCLUIDA_42')
        self.assertIn('chat_id 42', aviso); self.assertIn('✅ Pronto, agora estou no Sonnet · esforço padrão.', aviso)
        self.assertEqual((self.state / 'assinatura').read_text(encoding='utf-8').strip(), '🧠 Claude · Sonnet')  # a conversa só tem o Opus
        self.assertEqual(json.loads(self.gancho('fim', pid='5151'))['decision'], 'block')  # voltou sem avisar: segura
        self.assertEqual(self.estado()['estado'], 'voltou')   # o turno continua: ainda não deu certo
        self.escreve(_resposta('claude-sonnet-5-5', 1, 'mcp__plugin_telegram_telegram__reply'), _esforco('medium'))
        self.assertEqual(self.gancho('fim', pid='5151', stop_hook_active=True), '')
        self.assertEqual(self.estado()['estado'], 'ok')
        self.gancho('inicio', pid='5151', prompt='oi')
        self.assertEqual((self.state / 'assinatura').read_text(encoding='utf-8').strip(), '🧠 Claude · Sonnet 5.5 · medium')  # 1ª resposta nova

    def test_every_message_shows_the_official_effort_id(self):
        # 21/10/26: "máximo" não é nome de nível de nenhuma provedora. O que o aluno lê usa o id do claude --effort
        # (low, medium, high, xhigh, max); o que vai pros arquivos e pro `claude --effort` continua sendo o id.
        self.bot.mkdir(); (self.bot / 'opcoes').write_text('--model opus --effort high\n', encoding='ascii')
        self.janela(_resposta('claude-opus-5-5', -120), _esforco('high'), _do_dono('esforço máximo', -5))
        self.assertEqual(self.troca('status')[1].splitlines()[0], 'opções da janela: Opus · esforço high')
        rc, out = self.troca('trocar', '--pedido', 'esforço máximo')   # o aluno fala português: entendido
        self.assertEqual(rc, 0, out)
        self.assertIn('de Opus · esforço high para Opus · esforço max.', out)
        self.assertIn('⏳ Trocando pra Opus · esforço max.', out)
        self.assertEqual(self.arquivo('opcoes'), '--model opus --effort max')   # o arquivo guarda o id, não o nome mostrado
        self.assertEqual(self.troca('status')[1].splitlines()[0], 'opções da janela: Opus · esforço max')
        self.assertIsNone(re.search(r'\b(baixo|médio|alto|altíssimo|máximo)\b', out))
        # a janela fecha, reabre na mesma conversa e o aviso e a assinatura saem com o mesmo nome
        self.state.mkdir(exist_ok=True)
        (self.state / 'turn-start').write_text(str(int(time.time() * 1000) - 5000))
        (self.state / 'turn-end').write_text(str(int(time.time() * 1000) + 10))
        self.assertEqual(self.troca('derrubar', '4242', str(int(time.time() * 1000) - 1000))[0], 0)
        self.gancho('sessao', pid='5151')
        self.escreve({'type': 'user', 'timestamp': _quando(), 'message': {'role': 'user', 'content': 'MESTREOS_TROCA_CONCLUIDA_42'}})
        aviso = self.gancho('inicio', pid='5151', prompt='MESTREOS_TROCA_CONCLUIDA_42')
        self.assertIn('✅ Pronto, agora estou no Opus · esforço max.', aviso)
        self.assertEqual((self.state / 'assinatura').read_text(encoding='utf-8').strip(), '🧠 Claude · Opus · max')
        self.assertIsNone(re.search(r'\b(baixo|médio|alto|altíssimo|máximo)\b', aviso))

    def test_confirmation_and_the_list_of_options_use_official_ids(self):
        self.janela(_do_dono('', -5, audio=True))
        rc, out = self.troca('trocar', '--pedido', 'esforço médio', '--esforco', 'esforço médio')   # áudio: sempre confirma
        self.assertEqual(rc, 3, out)
        self.assertIn('Entendi: trocar pra modelo padrão da conta · esforço medium. Confirma?', out)
        rc, out = self.troca('trocar', '--pedido', 'bom dia')   # nem modelo nem esforço: o agente repete a lista ao dono
        self.assertEqual(rc, 2, out)
        self.assertIn('esforço (low, medium, high, xhigh, max ou padrão)', out)
        self.assertIsNone(re.search(r'\b(baixo|médio|alto|altíssimo|máximo)\b', out))

    def test_portuguese_words_are_still_understood_and_shown_as_official_ids(self):
        for fala, nivel in (('baixo', 'low'), ('médio', 'medium'), ('alto', 'high'), ('altíssimo', 'xhigh'), ('muito alto', 'xhigh'),
                            ('máximo', 'max'), ('low', 'low'), ('medium', 'medium'), ('high', 'high'), ('xhigh', 'xhigh'), ('max', 'max')):
            rc, out = self.troca('entender', 'muda o esforço pra ' + fala)
            self.assertEqual((rc, out.strip()), (0, f'CLARA: modelo padrão da conta · esforço {nivel}'), fala)

    def test_shortcut_never_hands_a_translated_effort_to_claude(self):
        # a troca de nome é só de exibição: o que o meubot passa ao `claude --effort` é o id oficial, e só ele
        self.bot.mkdir()
        for nivel in ('low', 'medium', 'high', 'xhigh', 'max'):
            (self.bot / 'opcoes').write_text(f'--model opus --effort {nivel}\n', encoding='ascii')
            self.assertEqual(self.troca('atalho', '--inicio')[1].strip(), f'--model opus --effort {nivel}', nivel)
        for traduzido in ('baixo', 'medio', 'alto', 'altissimo', 'maximo'):
            (self.bot / 'opcoes').write_text(f'--model opus --effort {traduzido}\n', encoding='ascii')
            self.assertEqual(self.troca('atalho', '--inicio')[1].strip(), '', traduzido)

    def test_one_message_is_worth_one_switch(self):
        self.janela(_do_dono('troca pro sonnet', -5))
        self.assertEqual(self.troca('trocar', '--pedido', 'troca pro sonnet')[0], 0)
        self.concluir()   # a janela reabriu e a troca deu certo
        rc, out = self.troca('trocar', '--pedido', 'troca pro sonnet')  # a janela reaberta relê a conversa: não repete
        self.assertEqual(rc, 2); self.assertIn('mensagem nova', out)

    def test_rewritten_phrase_is_refused(self):
        # a trava de uma aluna (20/10/26): o agente reescreveu um pedido recusado até passar
        self.janela(_do_dono('acho que hoje o sonnet resolve', -5))
        rc, out = self.troca('trocar', '--pedido', 'troca pro haiku')
        self.assertEqual(rc, 2); self.assertIn('literal', out)
        self.assertIsNone(self.arquivo('opcoes')); self.assertIsNone(self.arquivo('retomar'))

    def test_audio_always_confirms_and_typed_yes_switches(self):
        self.janela(_do_dono('', -5, audio=True))
        rc, out = self.troca('trocar', '--pedido', 'troca pro haiku', '--modelo', 'Haiku')
        self.assertEqual(rc, 3); self.assertIn('Entendi: trocar pra Haiku', out); self.assertIsNone(self.arquivo('opcoes'))
        rc, out = self.troca('confirmar', '--pedido', 'sim')
        self.assertEqual(rc, 2); self.assertIn('ainda não respondeu', out)
        self.escreve(_do_dono('sim, pode', 2))
        self.assertEqual(self.troca('confirmar', '--pedido', 'claro')[0], 2)  # o que ele não disse não vale
        rc, out = self.troca('confirmar', '--pedido', 'sim, pode')
        self.assertEqual(rc, 0, out); self.assertEqual(self.arquivo('opcoes'), '--model haiku')
        self.assertFalse((self.bot / 'pendente.json').exists())

    def test_no_cancels_and_loose_phrase_confirms(self):
        self.janela(_do_dono('será que o sonnet não é melhor pra hoje?', -5))
        rc, out = self.troca('trocar', '--pedido', 'será que o sonnet não é melhor pra hoje?')
        self.assertEqual(rc, 3, out)
        self.escreve(_do_dono('não, deixa', 2))
        rc, out = self.troca('confirmar', '--pedido', 'não, deixa')
        self.assertEqual(rc, 0); self.assertIn('CANCELADO', out); self.assertIsNone(self.arquivo('opcoes'))

    def test_effort_only_same_and_back_to_default(self):
        self.bot.mkdir(); (self.bot / 'opcoes').write_text('--model opus --effort high\n', encoding='ascii')
        self.janela(_do_dono('modelo opus', -20))
        rc, out = self.troca('trocar', '--pedido', 'modelo opus')
        self.assertEqual(rc, 0); self.assertIn('IGUAL', out); self.assertIsNone(self.arquivo('retomar'))
        self.escreve(_do_dono('esforço máximo', -10))
        self.assertEqual(self.troca('trocar', '--pedido', 'esforço máximo')[0], 0)
        self.assertEqual(self.arquivo('opcoes'), '--model opus --effort max')
        self.concluir()
        self.escreve(_do_dono('esforço padrão', -5))
        self.assertEqual(self.troca('trocar', '--pedido', 'esforço padrão')[0], 0)
        self.assertEqual(self.arquivo('opcoes'), '--model opus')   # esforço padrão = sem --effort; o modelo fica
        self.concluir()
        # rodada 2 (revisor A, lido no binário do Claude Code): a conversa retomada restaura o modelo dela, então
        # "modelo padrão" não teria efeito e o aviso mentiria: só por nome
        self.escreve(_do_dono('volta tudo pro padrão', -2))
        rc, out = self.troca('trocar', '--pedido', 'volta tudo pro padrão')
        self.assertEqual(rc, 2, out); self.assertIn('só troco por nome', out)
        self.assertEqual(self.arquivo('opcoes'), '--model opus')

    def concluir(self):
        """A janela reabriu e a troca deu certo (o que o SessionStart e o Stop fariam)."""
        t = self.estado(); t['estado'] = 'ok'; (self.bot / 'troca.json').write_text(json.dumps(t))

    def test_one_switch_at_a_time(self):
        # rodada 2 (revisor A, t7): a 2ª troca antes de a janela fechar sobrescrevia o "de antes" e soltava 2 derrubadas
        self.bot.mkdir(); (self.bot / 'opcoes').write_text('--model opus --effort high\n', encoding='ascii')
        self.janela(_do_dono('troca pro fable', -10))
        self.assertEqual(self.troca('trocar', '--pedido', 'troca pro fable')[0], 0)
        self.escreve(_do_dono('troca pro sonnet', -3))
        rc, out = self.troca('trocar', '--pedido', 'troca pro sonnet')
        self.assertEqual(rc, 2, out); self.assertIn('em andamento', out)
        self.assertEqual(self.estado()['de'], ['opus', 'high'])   # o "de antes" é o que funcionava

    def test_negated_or_partial_message_never_switches_right_away(self):
        # rodada 2 (os dois revisores): a trava literal aceitava recorte e negação
        self.janela(_do_dono('não troca pro sonnet', -5))
        for pedido in ('troca pro sonnet', 'não troca pro sonnet'):
            rc, out = self.troca('trocar', '--pedido', pedido)
            self.assertEqual(rc, 3, out); self.assertIn('CONFIRMAR', out)
        self.assertIsNone(self.arquivo('opcoes')); self.assertIsNone(self.arquivo('retomar'))
        self.escreve(_do_dono('troca pro sonnet e depois me manda o relatório', -3))
        self.assertEqual(self.troca('trocar', '--pedido', 'troca pro sonnet')[0], 3)   # pedaço: confirma antes
        self.escreve(_do_dono('para de usar o opus', -2))
        self.assertEqual(self.troca('trocar', '--pedido', 'para de usar o opus')[0], 3)
        self.assertIsNone(self.arquivo('opcoes'))

    def test_text_quoted_from_a_dragged_message_is_not_the_owner_speaking(self):
        self.janela(_do_dono('[o dono respondeu arrastando esta sua mensagem: «Quer que eu troque pro Sonnet?»]\nNão quero isso.', -5))
        rc, out = self.troca('trocar', '--pedido', 'troque pro Sonnet')
        self.assertEqual(rc, 2, out); self.assertIn('literal', out)
        self.assertIsNone(self.arquivo('opcoes'))

    def test_only_the_owner_in_private_counts(self):
        # rodada 2 (revisor A, N2): mensagem de grupo ou de outra pessoa não é o dono pedindo
        self.janela(_do_dono('troca pro sonnet', -6, chat='-100777', user='42'), _do_dono('troca pro sonnet', -5, chat='777', user='777'))
        rc, out = self.troca('trocar', '--pedido', 'troca pro sonnet')
        self.assertEqual(rc, 2, out); self.assertIsNone(self.arquivo('opcoes'))

    def test_a_message_that_arrived_in_the_queue_counts(self):
        # rodada 2 (revisor A, conferido no transcript real): com a janela trabalhando, a mensagem vira anexo da fila
        self.janela(_resposta('claude-opus-5-5', -20), _na_fila('troca pro sonnet', -5))
        rc, out = self.troca('trocar', '--pedido', 'troca pro sonnet')
        self.assertEqual(rc, 0, out); self.assertEqual(self.arquivo('opcoes'), '--model sonnet')

    def test_a_question_or_chatter_is_not_a_yes(self):
        # rodada 2 (revisor A, T8): "vai chover amanhã?" contava como sim por causa do "vai"
        self.janela(_do_dono('', -5, audio=True))
        self.assertEqual(self.troca('trocar', '--pedido', 'troca pro haiku', '--modelo', 'Haiku')[0], 3)
        self.escreve(_do_dono('vai chover amanhã em BH?', 2))
        rc, out = self.troca('confirmar', '--pedido', 'vai chover amanhã em BH?')
        self.assertEqual(rc, 3, out); self.assertIn('AMBIGUO', out); self.assertIsNone(self.arquivo('opcoes'))

    def test_only_inside_the_bot_window_opened_by_meubot(self):
        self.janela(_do_dono('troca pro sonnet', -5))
        rc, out = self.troca('trocar', '--pedido', 'troca pro sonnet', CLAUDE_PID='9999')
        self.assertEqual(rc, 2); self.assertIn('janela do bot', out)
        rc, out = self.troca('trocar', '--pedido', 'troca pro sonnet', MESTREOS_MEUBOT=None)
        self.assertEqual(rc, 2); self.assertIn('meubot', out); self.assertIsNone(self.arquivo('opcoes'))

    def test_new_model_failing_goes_back_once_then_stops(self):
        self.bot.mkdir(); (self.bot / 'opcoes').write_text('--model fable\n', encoding='ascii')
        (self.bot / 'troca.json').write_text(json.dumps({'estado': 'voltou', 'de': ['opus', 'high'], 'para': ['fable', None],
                                                          'sid': SID, 'chat': '42', 't': time.time(), 'pid': '5151'}))
        self.escreve(_resposta('claude-opus-5-5', -60))
        self.gancho('sessao', pid='5151')   # a janela reaberta é a 5151 (o SessionStart registra)
        self.gancho('falha', pid='5151', error='invalid_request')
        self.assertTrue(self.espera_estado('revertendo'), self.estado())
        self.assertEqual(self.arquivo('opcoes'), '--model opus --effort high')
        self.assertEqual(self.arquivo('retomar'), f'--resume {SID} MESTREOS_TROCA_FALHOU_42')
        self.gancho('sessao', pid='6161')
        self.assertEqual(self.estado()['estado'], 'voltou-antes')
        self.assertEqual((self.state / 'assinatura').read_text(encoding='utf-8').strip(), '🧠 Claude · Opus · high')
        aviso = self.gancho('inicio', pid='6161', prompt='MESTREOS_TROCA_FALHOU_42')
        self.assertIn('⚠️ Não consegui trocar pra Fable', aviso); self.assertIn('invalid_request', aviso)
        self.assertIn('Continuo no Opus · esforço high.', aviso)   # 21/10/26: nome oficial do nível, sem tradução
        (self.bot / 'retomar').unlink()   # o meubot já leu
        self.gancho('falha', pid='6161', error='rate_limit')  # nem o de antes respondeu: para de reabrir
        self.assertTrue(self.espera_estado('falhou'), self.estado()); self.assertIsNone(self.arquivo('retomar'))

    def _impostor(self, nome):
        """Um processo que se chama `nome` (o teste não pode fechar o Claude de verdade)."""
        if os.name == 'nt':
            exe = self.root / (nome + '.exe'); __import__('shutil').copy(r'C:\Windows\System32\ping.exe', exe)
            return subprocess.Popen([str(exe), '-n', '60', '127.0.0.1'], stdout=subprocess.DEVNULL)
        exe = self.root / nome; os.symlink('/bin/sleep', exe)   # cópia do sleep o macOS mata; o link vale
        return subprocess.Popen([str(exe), '60'])

    def test_real_switch_closes_the_window_only_after_the_turn_ends(self):
        # de ponta a ponta, sem modo de teste: o pedido desacopla a derrubada, ela espera o fim do turno e fecha a janela
        janela = self._impostor('claude')
        try:
            self.janela(_do_dono('troca pro sonnet', -5), pid=str(janela.pid))
            self.gancho('inicio', pid=str(janela.pid), prompt='troca pro sonnet')
            rc, out = self.troca('trocar', '--pedido', 'troca pro sonnet', CLAUDE_PID=str(janela.pid), MESTREOS_TELEGRAM_TROCA_SECO=None)
            self.assertEqual(rc, 0, out)
            time.sleep(2.5)
            self.assertIsNone(janela.poll())   # o agente ainda está mandando o "⏳": a janela continua aberta
            self.escreve(_resposta('claude-opus-5-5', 0, 'mcp__plugin_telegram_telegram__reply'))   # o "⏳ Trocando…"
            self.gancho('fim', pid=str(janela.pid))   # turno acabou
            fim = time.time() + 15
            while janela.poll() is None and time.time() < fim: time.sleep(0.2)
            self.assertIsNotNone(janela.poll(), 'a janela não fechou depois do fim do turno')
            self.assertEqual(self.estado()['estado'], 'reiniciando')
            self.assertEqual(self.arquivo('retomar'), f'--resume {SID} MESTREOS_TROCA_CONCLUIDA_42')  # o meubot reabre
        finally:
            if janela.poll() is None: janela.kill()
            janela.wait(10)

    def test_closing_only_hits_the_claude_process(self):
        self.state.mkdir(); self.bot.mkdir()
        (self.state / 'turn-start').write_text(str(int(time.time() * 1000) - 5000))
        (self.state / 'turn-end').write_text(str(int(time.time() * 1000)))
        for nome, janela_dele, fecha in (('claude', True, True), ('outro', True, False), ('claude', False, False)):
            p = self._impostor(nome)
            try:
                (self.bot / 'retomar').write_text('--resume x MESTREOS_TROCA_CONCLUIDA_42\n', encoding='ascii')
                (self.bot / 'troca.json').write_text('{"estado": "pedido"}')
                # rodada 2 (revisor A, N1): só fecha se o processo ainda for a janela do bot registrada
                (self.state / 'sessao.json').write_text(json.dumps({'pid': str(p.pid) if janela_dele else '1'}))
                time.sleep(0.3)
                self.assertEqual(self.troca('derrubar', str(p.pid), '0', MESTREOS_TELEGRAM_TROCA_SECO=None)[0], 0)
                time.sleep(0.5)
                self.assertEqual(p.poll() is not None, fecha, (nome, janela_dele))
                self.assertEqual((self.bot / 'retomar').exists(), fecha, (nome, janela_dele))  # não fechou: não reabre
            finally:
                if p.poll() is None: p.kill()
                p.wait(10)
            (self.root / 'claude').unlink(missing_ok=True); (self.root / 'claude.exe').unlink(missing_ok=True)

    # ---- rodada 2 (os dois revisores): nunca fechar a janela com o turno aberto
    def test_a_message_arriving_while_closing_keeps_the_window_open_until_its_turn_ends(self):
        janela = self._impostor('claude')
        try:
            self.state.mkdir(exist_ok=True); self.bot.mkdir(exist_ok=True)
            (self.state / 'sessao.json').write_text(json.dumps({'pid': str(janela.pid)}))
            (self.state / 'turn-start').write_text(str(int(time.time() * 1000) - 5000))
            (self.state / 'turn-end').write_text(str(int(time.time() * 1000)))
            (self.bot / 'troca.json').write_text('{"estado": "pedido"}')
            (self.bot / 'retomar').write_text('--resume x MESTREOS_TROCA_CONCLUIDA_42\n', encoding='ascii')
            p = subprocess.Popen([sys.executable, str(SCRIPTS / 'telegram-bot-troca.py'), 'derrubar', str(janela.pid), '0'],
                                 env=self.env(MESTREOS_TELEGRAM_TROCA_SECO=None), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
            (self.state / 'turn-start').write_text(str(int(time.time() * 1000)))   # chegou mensagem: turno novo
            time.sleep(3)
            self.assertIsNone(janela.poll(), 'fechou a janela no meio do turno novo')
            self.assertEqual(self.estado()['estado'], 'pedido')   # nada marcado como reinício ainda
            (self.state / 'turn-end').write_text(str(int(time.time() * 1000) + 5))   # o turno novo acabou
            fim = time.time() + 15
            while janela.poll() is None and time.time() < fim: time.sleep(0.2)
            self.assertIsNotNone(janela.poll(), 'não fechou depois que o turno novo acabou')
            self.assertEqual(self.estado()['estado'], 'reiniciando')
            p.wait(20)
        finally:
            if janela.poll() is None: janela.kill()
            janela.wait(10)

    def test_window_that_never_quiets_is_not_closed_and_the_switch_is_undone(self):
        # rodada 2 (revisor A, W1-i e tarefas em segundo plano): estourada a espera, cancela em vez de fechar
        self.bot.mkdir(); (self.bot / 'opcoes').write_text('--model sonnet\n', encoding='ascii')
        self.state.mkdir(); agora = int(time.time() * 1000)
        (self.state / 'turn-start').write_text(str(agora - 5000)); (self.state / 'turn-end').write_text(str(agora))
        (self.state / 'segundo-plano.json').write_text(json.dumps({'n': 1, 'ts': agora}))   # build rodando ao fundo
        (self.state / 'sessao.json').write_text(json.dumps({'pid': '4242'}))
        (self.bot / 'troca.json').write_text(json.dumps({'estado': 'pedido', 'de': ['opus', None], 'para': ['sonnet', None], 't': time.time()}))
        (self.bot / 'retomar').write_text('--resume x MESTREOS_TROCA_CONCLUIDA_42\n', encoding='ascii')
        self.assertEqual(self.troca('derrubar', '4242', '0', MESTREOS_TELEGRAM_TROCA_ESPERA='2')[0], 0)
        self.assertEqual(self.estado()['estado'], 'cancelada')
        self.assertEqual(self.arquivo('opcoes'), '--model opus')   # volta pro que estava
        self.assertIsNone(self.arquivo('retomar'))

    def test_stop_that_holds_the_turn_does_not_mark_its_end(self):
        # rodada 2 (os dois revisores): o gancho gravava turn-end antes de segurar o Stop, e a troca fechava a janela
        # no meio do reply que faltava
        self.escreve(_do_dono('qual a previsão?', -5), _resposta('claude-opus-5-5', -2))
        self.state.mkdir(exist_ok=True); (self.state / 'turn-end').write_text('1000000000000')
        self.assertEqual(json.loads(self.gancho('fim'))['decision'], 'block')
        self.assertEqual((self.state / 'turn-end').read_text().strip(), '1000000000000')
        self.assertEqual(self.gancho('fim', stop_hook_active=True, background_tasks=[{'id': 'b1'}]), '')
        self.assertGreater(int((self.state / 'turn-end').read_text().strip()), 1000000000000)
        self.assertEqual(json.loads((self.state / 'segundo-plano.json').read_text())['n'], 1)

    def test_shortcut_only_passes_words_from_the_list(self):
        # rodada 2 (revisor A, W5): o meubot passava o conteúdo cru dos arquivos ao claude (flag qualquer; & no Windows)
        self.bot.mkdir()
        (self.bot / 'opcoes').write_text('--model sonnet --effort high\n', encoding='ascii')
        (self.bot / 'retomar').write_text(f'--resume {SID} MESTREOS_TROCA_CONCLUIDA_42\n', encoding='ascii')
        rc, out = self.troca('atalho')
        self.assertEqual(out.strip(), f'--model sonnet --effort high --resume {SID} MESTREOS_TROCA_CONCLUIDA_42')
        self.assertIsNone(self.arquivo('retomar'))   # vale uma vez
        (self.bot / 'retomar').write_text(f'--resume {SID} MESTREOS_TROCA_CONCLUIDA_42\n', encoding='ascii')
        self.assertEqual(self.troca('atalho', '--inicio')[1].strip(), '--model sonnet --effort high')   # sobra velha: não
        self.assertIsNone(self.arquivo('retomar'))
        for ruim in ('--model sonnet --dangerously-skip-permissions', '--model sonnet & echo x', '--model gpt-9'):
            (self.bot / 'opcoes').write_text(ruim + '\n', encoding='ascii')
            (self.bot / 'retomar').write_text(f'--resume {SID} MESTREOS_TROCA_CONCLUIDA_42 & del x\n', encoding='ascii')
            self.assertEqual(self.troca('atalho')[1].strip(), '', ruim)


class DpapiPowershellTests(unittest.TestCase):
    """4.0.5: o powershell.exe 5.1 que lê o Cofre no Windows não herda o PSModulePath do PowerShell 7.
    Provado na VM (PowerShell 7.6.7): herdando, o ConvertTo-SecureString não carrega e o Cofre "não abre"."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cofre = Path(self.tmp.name) / 'MestreOS' / 'cofre'; cofre.mkdir(parents=True)
        for nome in ('telegram-bot-token', 'groq-api-key'):
            (cofre / f'{nome}.cred').write_text('blob-de-teste', encoding='utf-8')
        self.chamadas = []

    def tearDown(self):
        self.tmp.cleanup()

    def falso(self, rc=0, saida='valor-de-teste'):
        def run(cmd, **kw):
            self.chamadas.append((cmd, kw))
            return subprocess.CompletedProcess(cmd, rc, stdout=saida, stderr='')
        return run

    def ambiente(self, chave='PSModulePath'):
        return {'LOCALAPPDATA': self.tmp.name, 'PATH': os.defpath,
                chave: r'C:\Program Files\PowerShell\7\Modules;C:\WINDOWS\system32\WindowsPowerShell\v1.0\Modules'}

    def confere_env(self, chave):
        cmd, kw = self.chamadas[-1]
        self.assertEqual(cmd[0], 'powershell')
        env = kw.get('env')
        self.assertIsNotNone(env, 'sem env próprio o powershell 5.1 herda o PSModulePath do PowerShell 7')
        self.assertEqual([k for k in env if k.upper() == 'PSMODULEPATH'], [])
        self.assertEqual(env.get('LOCALAPPDATA'), self.tmp.name)   # o resto do ambiente segue igual
        self.assertIn(chave, os.environ)                              # e o ambiente do processo não muda

    def test_send_dpapi_sem_psmodulepath(self):
        import telegram_send
        for chave in ('PSModulePath', 'PSMODULEPATH'):
            with patch.dict(os.environ, self.ambiente(chave), clear=True), patch.object(telegram_send.subprocess, 'run', self.falso()):
                self.assertEqual(telegram_send._token_dpapi(), 'valor-de-teste')
                self.confere_env(chave)

    def test_send_dpapi_que_falha_ainda_avisa(self):
        import contextlib, io
        import telegram_send
        err = io.StringIO()
        with patch.dict(os.environ, self.ambiente(), clear=True), \
             patch.object(telegram_send.subprocess, 'run', self.falso(rc=1, saida='')), contextlib.redirect_stderr(err):
            self.assertEqual(telegram_send._token_dpapi(), '')
        self.assertIn('não abriu', err.getvalue())

    def test_janela_segredo_windows_sem_psmodulepath(self):
        with patch.dict(os.environ, self.ambiente(), clear=True), patch.object(janela, 'SISTEMA', 'Windows'), \
             patch.object(janela, 'PLUGIN_DIR', self.tmp.name), patch.object(janela.subprocess, 'run', self.falso()):
            self.assertEqual(janela.segredo('groq-api-key', 'GROQ_API_KEY'), 'valor-de-teste')
            self.confere_env('PSModulePath')


if __name__ == '__main__': unittest.main()
