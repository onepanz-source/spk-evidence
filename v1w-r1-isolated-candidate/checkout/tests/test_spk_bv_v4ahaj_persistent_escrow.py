"""v4ah-v4aj durable SQLite custody, restart, crash and tamper tests."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from search.spk_bv_v0e_live_evidence import fixture
from search.spk_bv_v4ahaj_persistent_escrow import CODE_SHA, main
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e, execute_live_v0e,
)
from spk_bv_research.native_ack_causal_replay_v4mno import CausalProbeRejected
from spk_bv_research.off_on_v0t import snapshot
from spk_bv_research.task_disagreement_fixture_v4aeag import (
    TEST_VIEW_KEYS, project_actual_native, reseal,
)
from spk_bv_research.task_escrow_audit_v4ahaj import evaluate
from spk_bv_research.task_escrow_fixture_v4ahaj import (
    EXPECT, VARIANTS, round_message, run_sequence,
)
from spk_bv_research.task_escrow_store_v4ahaj import (
    DurableEscrow, EscrowRejected, SimulatedCrash, SCHEMA,
)

ROOT = Path(__file__).resolve().parents[1]
PARENT = 'a' * 64
SOURCE = 'independent/schedule/1'


class TestV4ahajPersistentEscrow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v3 = Path(os.environ.get('SPK_V3TUV_REPORT',
                                  '/tmp/spk-bv-v3tuv-grant-rank.json'))
        cls.v4 = Path(os.environ.get('SPK_V4AEAG_REPORT',
            str(ROOT / 'docs/spk-bv-v4aeag-two-view-observation.json')))
        cls.raw3 = cls.v3.read_bytes()
        cls.raw4 = cls.v4.read_bytes()

    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db_path = Path(temp.name) / 'escrow.sqlite'
        case, fabric, plans = fixture(ticks=(1, 2))
        bv = LiveBVPlanV0e(enabled=False, priority='forward-first')
        self.source_sha = snapshot(execute_live_v0e(case, fabric, *plans, bv))
        self.projections, self.completed = project_actual_native(
            case, fabric, plans, bv, native_executor=execute_live_v0e)
        self.issued = case.events[0].timestamp

    def create(self):
        with DurableEscrow.create(self.db_path, PARENT, TEST_VIEW_KEYS):
            pass

    def message(self, round_no=0, *, nonce_suffix=''):
        return round_message(self.projections, SOURCE, self.source_sha,
                             PARENT, self.issued, self.completed, round_no,
                             nonce_suffix=nonce_suffix)

    def append(self, msg, tick, *, fault=None):
        with DurableEscrow.open(self.db_path, PARENT, TEST_VIEW_KEYS) as store:
            return store.append(msg, self.projections, expected_parent=PARENT,
                                source_key=SOURCE,
                                original_sha256=self.source_sha,
                                completed_tick=self.completed,
                                decision_tick=tick, fault=fault)

    def state(self, *, anchor=None):
        with DurableEscrow.open(self.db_path, PARENT, TEST_VIEW_KEYS,
                                external_head=anchor) as store:
            return store.verify(external_head=anchor)

    def test_18_signed_native_72_probes_198_attempts_72_commits(self):
        database = self.db_path
        report = evaluate(json.loads(self.raw3), self.raw3,
                          json.loads(self.raw4), self.raw4, db_path=database)
        totals = report['totals']
        self.assertEqual((totals['signed_native_replays'],
                          totals['counterfactual_native_probes'],
                          totals['custody_attempts'],
                          totals['journaled']), (18, 72, 198, 72))
        self.assertEqual((report['sqlite_logical_witness']['entries'],
                          report['sqlite_logical_witness']['persisted_unique_nonces']),
                         (72, 144))
        self.assertEqual(report['program_adoptions'], 0)
        self.assertFalse(report['native_learning_implemented'])
        with DurableEscrow.open(database, sha256(self.raw4).hexdigest(),
                                TEST_VIEW_KEYS) as store:
            self.assertEqual(report['sqlite_logical_witness'], store.verify())

    def test_create_only_private_mode(self):
        self.create()
        self.assertEqual(self.db_path.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(EscrowRejected):
            DurableEscrow.create(self.db_path, PARENT, TEST_VIEW_KEYS)

    def test_empty_escrow_root_and_reopen(self):
        self.create()
        self.assertEqual(self.state()['entries'],0)
        self.assertEqual(self.state()['head'],'0'*64)

    def test_consensus_after_restart_is_logged_but_never_adopted(self):
        self.create()
        message, tick = self.message()
        receipt = self.append(message, tick)
        self.assertTrue(receipt['journaled'])
        self.assertEqual(receipt['sequence'], 1)
        self.assertEqual(receipt['program_adoptions'],0)
        self.assertEqual(receipt['native_learning_updates'],0)
        self.assertEqual(self.state()['entries'],1)

    def test_replay_blocked_after_reopen(self):
        self.create()
        message, tick = self.message()
        self.append(message, tick)
        denial = self.append(message, tick)
        self.assertEqual(denial['verdict'],'VETO_PERSISTENT_REPLAY')
        self.assertFalse(denial['journaled'])
        self.assertEqual(self.state()['persisted_unique_nonces'],2)

    def test_explicit_disagreement_is_durably_quarantined(self):
        self.create()
        message, tick = self.message()
        message['reviews']['emission']['vote'] = 'REGRESSES'
        reseal(message)
        r = self.append(message, tick)
        self.assertEqual(r['verdict'],'JOURNALED_QUARANTINE_REVIEWER_DISAGREEMENT')
        self.assertEqual(self.state()['entries'],1)
        self.assertEqual(self.append(message,tick)['verdict'],'VETO_PERSISTENT_REPLAY')

    def test_explicit_abstention_is_durably_quarantined(self):
        self.create()
        message, tick = self.message()
        message['reviews']['emission']['vote'] = 'ABSTAIN'
        reseal(message)
        r = self.append(message,tick)
        self.assertEqual(r['verdict'],'JOURNALED_QUARANTINE_ABSTENTION')
        self.assertEqual(self.state()['entries'],1)

    def test_invalid_signature_is_not_recorded_and_does_not_consume_nonce(self):
        self.create()
        message, tick = self.message()
        tampered = deepcopy(message)
        tampered['reviews']['endpoint']['vote'] = 'REGRESSES'
        self.assertEqual(self.append(tampered,tick)['verdict'],
                         'VETO_INVALID_ATTESTATION')
        self.assertEqual(self.state()['entries'],0)
        self.assertTrue(self.append(message,tick)['journaled'])

    def test_mac_valid_task_poison_still_fails_closed(self):
        self.create()
        message, tick = self.message()
        message['task_labels'] = {'0':0,'1':1}
        reseal(message)
        self.assertEqual(self.append(message,tick)['verdict'],
                         'VETO_TASK_CANARY_CONFLICT')
        self.assertEqual(self.state()['entries'],0)

    def test_wrong_source_parent_never_writes(self):
        self.create()
        message, tick = self.message()
        message['parent_sha256'] = '0'*64
        reseal(message)
        self.assertEqual(self.append(message,tick)['verdict'],'VETO_SOURCE_BINDING')
        self.assertEqual(self.state()['entries'],0)

    def test_cross_view_nonce_collision_cannot_bypass_persisted_set(self):
        self.create()
        message, tick = self.message()
        self.append(message,tick)
        second, tick2 = self.message(1)
        second['reviews']['emission']['nonce'] = message['reviews']['endpoint']['nonce']
        reseal(second)
        self.assertEqual(self.append(second,tick2)['verdict'],'VETO_PERSISTENT_REPLAY')
        self.assertEqual(self.state()['entries'],1)

    def test_signed_nonce_new_but_source_tick_stale_vetoes(self):
        self.create()
        message, tick = self.message(2)
        self.append(message,tick)
        stale, t0 = self.message(0,nonce_suffix='unique-but-stale')
        self.assertEqual(self.append(stale,t0)['verdict'],
                         'VETO_PERSISTENT_SOURCE_CLOCK')
        self.assertEqual(self.state()['entries'],1)

    def test_crash_after_record_insert_atomic_rollback(self):
        self.create()
        message, tick = self.message()
        with self.assertRaises(SimulatedCrash):
            self.append(message,tick,fault='after_record_before_nonce')
        self.assertEqual(self.state()['entries'],0)
        self.assertEqual(self.state()['persisted_unique_nonces'],0)
        self.assertTrue(self.append(message,tick)['journaled'])

    def test_crash_after_nonce_insert_atomic_rollback(self):
        self.create()
        message, tick = self.message()
        with self.assertRaises(SimulatedCrash):
            self.append(message,tick,fault='after_nonce_before_commit')
        self.assertEqual(self.state()['entries'],0)
        self.assertTrue(self.append(message,tick)['journaled'])

    def test_abrupt_child_process_death_rolls_back_uncommitted_transaction(self):
        self.create()
        child = (
            'import os,sqlite3,sys;'
            'c=sqlite3.connect(sys.argv[1],isolation_level=None);'
            'c.execute("BEGIN IMMEDIATE");'
            'c.execute("INSERT INTO journal(seq,record_json,previous_hash,entry_hash) VALUES (1,\'{}\',\'0\',\'x\')");'
            'os._exit(77)'
        )
        process = subprocess.run([sys.executable,'-c',child,str(self.db_path)],
                                 check=False,capture_output=True)
        self.assertEqual(process.returncode,77)
        self.assertEqual(self.state()['entries'],0)

    def test_concurrent_duplicate_review_only_one_commits(self):
        self.create()
        message, tick = self.message()
        with ThreadPoolExecutor(max_workers=2) as executor:
            a = executor.submit(self.append,message,tick)
            b = executor.submit(self.append,message,tick)
            results = [a.result(),b.result()]
        self.assertEqual(sum(bool(r['journaled']) for r in results),1)
        self.assertEqual({r['verdict'] for r in results},
            {'JOURNALED_CONSISTENT_CORRELATED_TEST_VIEWS_NO_EXTERNAL_TRUST',
             'VETO_PERSISTENT_REPLAY'})
        self.assertEqual(self.state()['entries'],1)

    def test_tampered_database_row_is_rejected(self):
        self.create()
        message, tick = self.message()
        self.append(message,tick)
        with sqlite3.connect(self.db_path) as raw:
            raw.execute('UPDATE journal SET entry_hash=? WHERE seq=1',('f'*64,))
        with self.assertRaises(EscrowRejected):
            self.state()

    def test_external_anchor_rejects_incorrect_head(self):
        self.create()
        message, tick = self.message()
        self.append(message,tick)
        head = self.state()['head']
        self.assertEqual(self.state(anchor=head)['head'],head)
        with self.assertRaises(EscrowRejected):
            self.state(anchor='f'*64)

    def test_external_old_anchor_rejects_valid_new_commits(self):
        self.create()
        message, tick = self.message()
        self.append(message,tick)
        original_head = self.state()['head']
        second,tick2 = self.message(1)
        self.append(second,tick2)
        with self.assertRaises(EscrowRejected):
            self.state(anchor=original_head)

    def test_nonprivate_permissions_rejected(self):
        self.create()
        self.db_path.chmod(0o644)
        with self.assertRaises(EscrowRejected):
            self.state()

    def test_symlinked_escrow_path_rejected(self):
        self.create()
        alias = self.db_path.parent / 'alias.sqlite'
        alias.symlink_to(self.db_path)
        with self.assertRaises(EscrowRejected):
            DurableEscrow.open(alias,PARENT,TEST_VIEW_KEYS)

    def test_wrong_signed_parent_cannot_open_escrow(self):
        self.create()
        with self.assertRaises(EscrowRejected):
            DurableEscrow.open(self.db_path,'b'*64,TEST_VIEW_KEYS)

    def test_malformed_review_does_not_crash_partial_transaction(self):
        self.create()
        self.assertEqual(self.append({'no_reviews':True},self.completed+3)['verdict'],
                         'VETO_MALFORMED_ENVELOPE')
        self.assertEqual(self.state()['entries'],0)

    def test_all_eleven_variants_restart_and_deterministic_journal(self):
        self.create()
        decisions = run_sequence(self.db_path,self.projections,SOURCE,
                                 self.source_sha,PARENT,self.issued,self.completed)
        self.assertEqual([r['variant'] for r in decisions],list(VARIANTS))
        self.assertEqual([r['verdict'] for r in decisions],
                         [EXPECT[v] for v in VARIANTS])
        self.assertEqual(self.state()['entries'],4)
        self.assertEqual(self.state()['persisted_unique_nonces'],8)

    def test_signed_predecessor_tamper_prevents_escrow_creation(self):
        bad = json.loads(self.raw4)
        bad['program_adoptions'] = 1
        with self.assertRaises(CausalProbeRejected):
            evaluate(json.loads(self.raw3),self.raw3,bad,
                     json.dumps(bad,sort_keys=True).encode(),
                     db_path=self.db_path)
        self.assertFalse(self.db_path.exists())

    def test_create_only_cli_byte_exact_and_database_reopen(self):
        dest = self.db_path.parent / 'report.json'
        args = ['--root',str(ROOT),'--v3tuv',str(self.v3),
                '--v4aeag',str(self.v4),'--db',str(self.db_path),
                '--out',str(dest)]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(args),0)
            self.assertEqual(main(args),2)
            args[-1] = str(ROOT/'docs/v4ahaj-forbidden-output.json')
            self.assertEqual(main(args),2)
        self.assertEqual(dest.read_bytes(),
            (ROOT/'docs/spk-bv-v4ahaj-persistent-escrow-observation.json').read_bytes())
        with DurableEscrow.open(self.db_path, sha256(self.raw4).hexdigest(),
                                TEST_VIEW_KEYS) as store:
            self.assertEqual(store.verify()['entries'],72)

    def test_cli_rejects_invalid_sha_without_db_or_report(self):
        dest = self.db_path.parent / 'report.json'
        changed = {**CODE_SHA,
                   'spk_bv_research/task_escrow_store_v4ahaj.py':'0'*64}
        with patch.dict(CODE_SHA,changed),redirect_stderr(io.StringIO()):
            status = main(['--root',str(ROOT),'--v3tuv',str(self.v3),
                           '--v4aeag',str(self.v4),'--db',str(self.db_path),
                           '--out',str(dest)])
        self.assertEqual(status,2)
        self.assertFalse(self.db_path.exists())
        self.assertFalse(dest.exists())

    def test_cli_rejects_symlinked_report(self):
        link = self.db_path.parent / 'predecessor.json'
        link.symlink_to(self.v4)
        dest = self.db_path.parent / 'report.json'
        with redirect_stderr(io.StringIO()):
            status = main(['--root',str(ROOT),'--v3tuv',str(self.v3),
                           '--v4aeag',str(link),'--db',str(self.db_path),
                           '--out',str(dest)])
        self.assertEqual(status,2)
        self.assertFalse(self.db_path.exists())

    def test_program_adoption_not_authorized_by_persistent_consensus(self):
        self.create()
        message,tick = self.message()
        response = self.append(message,tick)
        self.assertFalse('adopted' in response)
        self.assertEqual(response['program_adoptions'],0)
        self.assertEqual(response['native_learning_updates'],0)
