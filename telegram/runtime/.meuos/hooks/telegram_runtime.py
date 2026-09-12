#!/usr/bin/env python3
"""Runtime Telegram portátil. SQLite durável, execução única e recuperação conservadora.

Não contém token; estado deve ficar em disco local, fora de pastas sincronizadas.
"""
import contextlib
import json
import os
from pathlib import Path
import queue
import sqlite3
import subprocess
import threading
import time


class Busy(Exception):
    pass


@contextlib.contextmanager
def lock(path):
    """Lock do sistema liberado mesmo quando o processo cai (Mac/Windows)."""
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('a+b') as f:
        if p.stat().st_size == 0:
            f.write(b'0'); f.flush()
        f.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            raise Busy() from e
        try:
            yield
        finally:
            f.seek(0)
            if os.name == 'nt':
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class Queue:
    def __init__(self, directory):
        self.path = Path(directory); self.path.mkdir(parents=True, exist_ok=True)
        self.db = self.path / 'telegram.sqlite3'
        with self.connect() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS jobs (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
                payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
                created REAL NOT NULL, updated REAL NOT NULL, detail TEXT);
              CREATE TABLE IF NOT EXISTS receipts (
                job TEXT NOT NULL, message_id TEXT NOT NULL, method TEXT NOT NULL,
                created REAL NOT NULL);
            ''')
        if os.name != 'nt':
            os.chmod(self.path, 0o700); os.chmod(self.db, 0o600)

    @contextlib.contextmanager
    def connect(self):
        c = sqlite3.connect(self.db, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA synchronous=FULL')
        try:
            with c:
                yield c
        finally:
            c.close()

    def enqueue(self, ident, payload):
        with self.connect() as db:
            r = db.execute('INSERT OR IGNORE INTO jobs(id,payload,created,updated) VALUES(?,?,?,?)',
                           (ident, json.dumps(payload, ensure_ascii=False), time.time(), time.time()))
            return bool(r.rowcount)

    def status(self, ident):
        with self.connect() as db:
            r = db.execute('SELECT status FROM jobs WHERE id=?', (ident,)).fetchone()
            return r[0] if r else None

    def finish(self, ident, status, detail=''):
        with self.connect() as db:
            db.execute('UPDATE jobs SET status=?,updated=?,detail=? WHERE id=?',
                       (status, time.time(), detail, ident))

    def receipt(self, ident, mid, method):
        with self.connect() as db:
            db.execute('INSERT INTO receipts VALUES(?,?,?,?)', (ident, str(mid), method, time.time()))

    def drain(self, execute, recovered=lambda ident: None):
        try:
            with lock(self.path / 'executor.lock'):
                with self.connect() as db:
                    lost = db.execute("SELECT id FROM jobs WHERE status='running'").fetchall()
                    db.execute("UPDATE jobs SET status='uncertain',detail='executor interrupted',updated=? WHERE status='running'", (time.time(),))
                for r in lost:
                    recovered(r['id'])
                while True:
                    with self.connect() as db:
                        db.execute('BEGIN IMMEDIATE')
                        r = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY seq LIMIT 1").fetchone()
                        if not r:
                            return True
                        db.execute("UPDATE jobs SET status='running',updated=? WHERE id=?", (time.time(), r['id']))
                    try:
                        status = execute(r['id'], json.loads(r['payload']))
                        if status not in ('completed', 'failed', 'uncertain'):
                            status = 'uncertain'
                        self.finish(r['id'], status)
                    except Exception:
                        # Pode ter havido efeito externo antes da exceção. Nunca repetir.
                        self.finish(r['id'], 'uncertain', 'executor exception')
        except Busy:
            return False


def activity_run(cmd, cwd, timeout, **kwargs):
    """Timeout por inatividade, não por duração total. Pipes funcionam no Windows."""
    events = queue.Queue()
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    def read(stream, kind):
        try:
            for line in iter(stream.readline, b''):
                events.put((kind, line))
        finally:
            stream.close(); events.put((kind, None))
    for stream, kind in ((p.stdout, 'out'), (p.stderr, 'err')):
        threading.Thread(target=read, args=(stream, kind), daemon=True).start()
    data = {'out': [], 'err': []}; ends = 0; last = time.monotonic()
    try:
        while ends < 2:
            remaining = timeout - (time.monotonic() - last)
            if remaining <= 0:
                raise subprocess.TimeoutExpired(cmd[0], timeout)
            try:
                kind, line = events.get(timeout=min(remaining, .2))
            except queue.Empty:
                continue
            if line is None:
                ends += 1
            else:
                # Only stdout JSON activity extends a Codex turn; stderr chatter does not.
                if kind == 'out': last = time.monotonic()
                data[kind].append(line)
        p.wait(timeout=max(.1, timeout - (time.monotonic() - last)))
    except BaseException:
        p.kill(); p.wait(); raise
    return subprocess.CompletedProcess(cmd, p.returncode,
        b''.join(data['out']).decode('utf-8', 'replace'),
        b''.join(data['err']).decode('utf-8', 'replace'))
