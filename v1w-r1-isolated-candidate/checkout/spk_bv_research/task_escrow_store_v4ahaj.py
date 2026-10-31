"""v4ah-v4aj bounded crash/restart-persistent SQLite research escrow.

The journal gives atomic, replay-resistant custody on one trusted local host.
Neither local SQLite nor an unkeyed hash chain withstand a malicious editor
who can rewrite the entire database AND its head. Such attacks require an
independently retained external anchor and genuinely trusted identities.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import stat

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.task_disagreement_v4aeag import (
    EscrowLedger, VIEWS, adjudicate, digest,
)

SCHEMA = 'spk-bv-persistent-escrow/research-v4ah-v4aj'
STATUS = 'SQLITE_ATOMIC_RESTART_REPLAY_AND_QUARANTINE_CUSTODY_NO_LEARNING'
DOMAIN = b'SPK/BV/ESCROW-V4AHAJ\x00'
GENESIS = '0' * 64
JOURNALABLE = frozenset({
    'CONSISTENT_CORRELATED_TEST_VIEWS_NO_EXTERNAL_TRUST',
    'QUARANTINE_REVIEWER_DISAGREEMENT',
    'QUARANTINE_ABSTENTION',
})


class EscrowRejected(ValueError):
    pass


class SimulatedCrash(RuntimeError):
    pass


def _entry_hash(previous, record):
    return sha256(DOMAIN + bytes.fromhex(previous) + canon(record)).hexdigest()


def _check_path(path, *, new):
    path = Path(path)
    if (not path.is_absolute() or path.name in ('', '.', '..') or
            not path.parent.is_dir() or any(p.is_symlink() for p in
            (path, *path.parents))):
        raise EscrowRejected('unsafe escrow database path or symlink')
    if new and path.exists():
        raise EscrowRejected('escrow must be created exclusively')
    if not new:
        try:
            info = path.stat(follow_symlinks=False)
        except OSError as exc:
            raise EscrowRejected('missing escrow database') from exc
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise EscrowRejected('escrow must be private regular owned file')
    return path


class DurableEscrow:
    def __init__(self, path, connection, keys):
        self.path = path
        self.db = connection
        self.keys = keys

    @staticmethod
    def _connect(path):
        connection = sqlite3.connect(str(path), timeout=5, isolation_level=None)
        connection.execute('PRAGMA busy_timeout=5000')
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA journal_mode=DELETE')
        connection.execute('PRAGMA synchronous=FULL')
        return connection

    @classmethod
    def create(cls, path, parent_sha256, keys):
        p = _check_path(path, new=True)
        if (type(parent_sha256) is not str or len(parent_sha256) != 64 or
                any(c not in '0123456789abcdef' for c in parent_sha256)):
            raise EscrowRejected('invalid signed escrow source parent')
        fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                     0o600)
        os.close(fd)
        conn = cls._connect(p)
        try:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('CREATE TABLE metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL)')
            conn.execute('CREATE TABLE journal (seq INTEGER PRIMARY KEY, record_json TEXT NOT NULL, previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL UNIQUE)')
            conn.execute('CREATE TABLE replay_nonce (nonce TEXT PRIMARY KEY, seq INTEGER NOT NULL, view TEXT NOT NULL, FOREIGN KEY(seq) REFERENCES journal(seq))')
            conn.execute('CREATE TABLE source_clock (source_key TEXT PRIMARY KEY, last_decision_tick INTEGER NOT NULL, seq INTEGER NOT NULL, FOREIGN KEY(seq) REFERENCES journal(seq))')
            conn.executemany('INSERT INTO metadata(name,value) VALUES (?,?)', [
                ('schema', SCHEMA), ('parent_sha256', parent_sha256),
                ('head', GENESIS), ('entries', '0')])
            conn.execute('COMMIT')
            result = cls(p, conn, keys)
            result.verify()
            return result
        except BaseException:
            if conn.in_transaction:
                conn.execute('ROLLBACK')
            conn.close()
            raise

    @classmethod
    def open(cls, path, expected_parent, keys, *, external_head=None):
        p = _check_path(path, new=False)
        conn = cls._connect(p)
        result = cls(p, conn, keys)
        try:
            result.verify(expected_parent=expected_parent,
                          external_head=external_head)
            return result
        except BaseException:
            conn.close()
            raise

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.close()

    def _verify_locked(self, *, expected_parent=None, external_head=None):
        check = self.db.execute('PRAGMA integrity_check').fetchone()
        if check != ('ok',):
            raise EscrowRejected('SQLite page/integrity violation')
        metadata = dict(self.db.execute('SELECT name,value FROM metadata'))
        if (set(metadata) != {'schema', 'parent_sha256', 'head', 'entries'} or
                metadata['schema'] != SCHEMA or
                (expected_parent is not None and
                 metadata['parent_sha256'] != expected_parent)):
            raise EscrowRejected('escrow schema or signed parent changed')
        previous = GENESIS
        count = 0
        replay = {}
        clocks = {}
        for seq, raw, prev, entry_sha in self.db.execute(
                'SELECT seq,record_json,previous_hash,entry_hash FROM journal ORDER BY seq'):
            count += 1
            if (seq != count or type(raw) is not str or
                    prev != previous):
                raise EscrowRejected('escrow sequence or hash ancestry broken')
            try:
                record = json.loads(raw)
            except (TypeError, ValueError) as exc:
                raise EscrowRejected('escrow record JSON is invalid') from exc
            if (type(record) is not dict or canon(record).decode() != raw or
                    set(record) != {'parent_sha256', 'source_key', 'original_sha256',
                                    'decision_tick', 'completed_tick',
                                    'envelope', 'projections', 'source_verdict'} or
                    record['parent_sha256'] != metadata['parent_sha256'] or
                    record['source_verdict'] not in JOURNALABLE or
                    type(record['decision_tick']) is not int or
                    type(record['completed_tick']) is not int or
                    _entry_hash(previous, record) != entry_sha):
                raise EscrowRejected('escrow record hash or semantic structure changed')
            receipt = adjudicate(
                record['envelope'], record['projections'], self.keys,
                expected_parent=metadata['parent_sha256'],
                source_key=record['source_key'],
                original_sha256=record['original_sha256'],
                precommitted_labels={'0': 1, '1': 0},
                completed_tick=record['completed_tick'],
                decision_tick=record['decision_tick'], ledger=EscrowLedger())
            if receipt['verdict'] != record['source_verdict']:
                raise EscrowRejected('escrow signed two-view decision drift')
            previous = entry_sha
            source = record['source_key']
            if source in clocks and clocks[source][0] >= record['decision_tick']:
                raise EscrowRejected('escrow source time order broken')
            clocks[source] = (record['decision_tick'], seq)
            for view in VIEWS:
                nonce = record['envelope']['reviews'][view]['nonce']
                if nonce in replay:
                    raise EscrowRejected('duplicate nonce in escrow event chain')
                replay[nonce] = (seq, view)
        if (metadata['entries'] != str(count) or metadata['head'] != previous or
                (external_head is not None and previous != external_head)):
            raise EscrowRejected('escrow head or external anchor mismatch')
        persisted_replay = {
            nonce: (seq, view)
            for nonce, seq, view in self.db.execute(
                'SELECT nonce,seq,view FROM replay_nonce')
        }
        persisted_clocks = {
            source: (tick, seq)
            for source, tick, seq in self.db.execute(
                'SELECT source_key,last_decision_tick,seq FROM source_clock')
        }
        if persisted_replay != replay or persisted_clocks != clocks:
            raise EscrowRejected('escrow replay or source-clock index divergence')
        return {'entries': count, 'head': previous,
                'persisted_unique_nonces': len(replay),
                'parent_sha256': metadata['parent_sha256']}

    def verify(self, *, expected_parent=None, external_head=None):
        try:
            self.db.execute('BEGIN IMMEDIATE')
            proof = self._verify_locked(expected_parent=expected_parent,
                                        external_head=external_head)
            self.db.execute('COMMIT')
            return proof
        except (sqlite3.Error, EscrowRejected, KeyError, TypeError, ValueError) as exc:
            if self.db.in_transaction:
                self.db.execute('ROLLBACK')
            raise EscrowRejected('escrow verification rejected: ' + str(exc)) from exc

    def append(self, envelope, projections, *, expected_parent,
               source_key, original_sha256, completed_tick,
               decision_tick, fault=None):
        """One SQLite transaction consumes BOTH nonces and journals a verdict."""
        try:
            self.db.execute('BEGIN IMMEDIATE')
            state = self._verify_locked(expected_parent=expected_parent)
            if (type(envelope) is not dict or
                    type(envelope.get('reviews')) is not dict or
                    set(envelope['reviews']) != set(VIEWS) or
                    any(type(review) is not dict or
                        type(review.get('nonce')) is not str
                        for review in envelope['reviews'].values())):
                self.db.execute('ROLLBACK')
                return {'verdict': 'VETO_MALFORMED_ENVELOPE', 'journaled': False}
            for review in envelope['reviews'].values():
                if self.db.execute('SELECT 1 FROM replay_nonce WHERE nonce=?',
                                   (review['nonce'],)).fetchone():
                    self.db.execute('ROLLBACK')
                    return {'verdict': 'VETO_PERSISTENT_REPLAY', 'journaled': False}
            prior = self.db.execute(
                'SELECT last_decision_tick FROM source_clock WHERE source_key=?',
                (source_key,)).fetchone()
            if prior is not None and prior[0] >= decision_tick:
                self.db.execute('ROLLBACK')
                return {'verdict': 'VETO_PERSISTENT_SOURCE_CLOCK', 'journaled': False}
            checked = adjudicate(
                envelope, projections, self.keys,
                expected_parent=expected_parent, source_key=source_key,
                original_sha256=original_sha256,
                precommitted_labels={'0': 1, '1': 0},
                completed_tick=completed_tick,
                decision_tick=decision_tick, ledger=EscrowLedger())
            source_verdict = checked['verdict']
            if source_verdict not in JOURNALABLE:
                self.db.execute('ROLLBACK')
                return {'verdict': source_verdict, 'journaled': False}
            record = {
                'parent_sha256': expected_parent, 'source_key': source_key,
                'original_sha256': original_sha256,
                'decision_tick': decision_tick, 'completed_tick': completed_tick,
                'envelope': envelope, 'projections': projections,
                'source_verdict': source_verdict,
            }
            seq = state['entries'] + 1
            new_hash = _entry_hash(state['head'], record)
            self.db.execute('INSERT INTO journal(seq,record_json,previous_hash,entry_hash) VALUES (?,?,?,?)',
                            (seq, canon(record).decode(), state['head'], new_hash))
            if fault == 'after_record_before_nonce':
                raise SimulatedCrash('injected crash after durable record staging')
            for view in VIEWS:
                self.db.execute('INSERT INTO replay_nonce(nonce,seq,view) VALUES (?,?,?)',
                                (envelope['reviews'][view]['nonce'], seq, view))
            self.db.execute('INSERT INTO source_clock(source_key,last_decision_tick,seq) VALUES (?,?,?) ON CONFLICT(source_key) DO UPDATE SET last_decision_tick=excluded.last_decision_tick, seq=excluded.seq',
                            (source_key, decision_tick, seq))
            if fault == 'after_nonce_before_commit':
                raise SimulatedCrash('injected crash before database commit')
            self.db.execute('UPDATE metadata SET value=? WHERE name="head"', (new_hash,))
            self.db.execute('UPDATE metadata SET value=? WHERE name="entries"', (str(seq),))
            self.db.execute('COMMIT')
            return {'verdict': 'JOURNALED_' + source_verdict,
                    'source_verdict': source_verdict,
                    'journaled': True, 'sequence': seq,
                    'head': new_hash, 'durable_in_local_SQLite': True,
                    'program_adoptions': 0, 'native_learning_updates': 0}
        except BaseException:
            if self.db.in_transaction:
                self.db.execute('ROLLBACK')
            raise
