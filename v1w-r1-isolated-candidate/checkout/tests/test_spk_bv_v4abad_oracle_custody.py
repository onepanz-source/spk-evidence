"""v4ab-v4ad signed fixture roles, replay, canary poisoning and custody tests."""
from __future__ import annotations

from contextlib import redirect_stderr,redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from spk_bv_research.native_ack_causal_replay_v4mno import CausalProbeRejected
from spk_bv_research.task_oracle_custody_v4abad import (
    DOMAIN,OracleLedger,ROLES,SCOPE,SCHEMA,assess,lab_mac,
)
from spk_bv_research.task_oracle_fixture_v4abad import (
    TEST_KEYS,VARIANTS,VERDICTS,envelope,run_variant,
)
from spk_bv_research.task_oracle_audit_v4abad import audit_row,evaluate
from search.spk_bv_v4abad_oracle_custody import CODE_SHA,main

ROOT=Path(__file__).resolve().parents[1]
PARENT='a'*64
SOURCE='schedule/mode/1'
CANARY={'0':1,'1':0}


class TestV4abadOracleCustody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v3=Path(os.environ.get('SPK_V3TUV_REPORT',
            '/tmp/spk-bv-v3tuv-grant-rank.json'))
        cls.v4=Path(os.environ.get('SPK_V4YZAA_REPORT',
            str(ROOT/'docs/spk-bv-v4yzaa-task-objective-observation.json')))
        cls.raw3=cls.v3.read_bytes()
        cls.raw4=cls.v4.read_bytes()

    def test_full_18_signed_native_and_216_attestation_scenarios(self):
        report=evaluate(json.loads(self.raw3),self.raw3,
                        json.loads(self.raw4),self.raw4)
        t=report['totals']
        self.assertEqual((t['signed_native_replays'],
                          t['provenance_scenarios'],
                          t['valid_fixture_quorum_MACs']),(18,216,144))
        self.assertEqual(t['verdict_ATTESTED_TEST_WITNESS_NO_EXTERNAL_TRUST'],18)
        self.assertEqual(t['verdict_VETO_SEMANTIC_CANARY_CONFLICT'],18)
        self.assertEqual(report['program_adoptions'],0)
        self.assertFalse(report['native_learning_implemented'])

    def test_valid_fixture_roles_is_not_production_identity(self):
        row=run_variant(SOURCE,PARENT,1,'valid_quorum',CANARY)
        audit_row(row,SOURCE,PARENT,1,CANARY)
        d=row['decision']
        self.assertTrue(d['two_distinct_fixture_mac_roles_valid'])
        self.assertTrue(d['accepted_for_research_evidence_only'])
        self.assertFalse(d['production_identity_authenticated'])
        self.assertFalse(d['candidate_program_adopted'])

    def test_dually_signed_poison_is_mac_valid_but_semantically_quarantined(self):
        row=run_variant(SOURCE,PARENT,1,'dually_signed_poison',CANARY)
        audit_row(row,SOURCE,PARENT,1,CANARY)
        self.assertTrue(row['decision']['two_distinct_fixture_mac_roles_valid'])
        self.assertEqual(row['decision']['verdict'],
                         'VETO_SEMANTIC_CANARY_CONFLICT')
        self.assertFalse(row['decision']['accepted_for_research_evidence_only'])

    def test_without_canary_the_correctly_macced_case_fails_closed(self):
        row=run_variant(SOURCE,PARENT,1,'absent_canary',CANARY)
        self.assertEqual(row['decision']['verdict'],
                         'VETO_NO_PRECOMMITTED_TASK_CANARY')

    def test_missing_reviewer_cannot_be_called_quorum(self):
        r=run_variant(SOURCE,PARENT,1,'missing_reviewer',CANARY)
        self.assertEqual(r['decision']['verdict'],'VETO_QUORUM')

    def test_reviewer_role_cannot_reuse_specifier_mac(self):
        r=run_variant(SOURCE,PARENT,1,'wrong_reviewer_mac',CANARY)
        self.assertEqual(r['decision']['verdict'],'VETO_INVALID_ATTESTATION')

    def test_different_mac_roles_need_different_keys(self):
        r=run_variant(SOURCE,PARENT,1,'single_key_roots',CANARY)
        self.assertEqual(r['decision']['verdict'],'VETO_NO_CONFIGURED_ROLE_ROOT')

    def test_task_payload_tamper_breaks_attestation(self):
        r=run_variant(SOURCE,PARENT,1,'tampered_after_sign',CANARY)
        self.assertEqual(r['decision']['verdict'],'VETO_INVALID_ATTESTATION')

    def test_scope_authorized_by_signer_does_not_authorize_other_neuron(self):
        r=run_variant(SOURCE,PARENT,1,'wrong_scope',CANARY)
        self.assertTrue(r['decision']['two_distinct_fixture_mac_roles_valid'])
        self.assertEqual(r['decision']['verdict'],'VETO_SCOPE')

    def test_expired_attestation_vetoes_even_when_mac_valid(self):
        r=run_variant(SOURCE,PARENT,1,'expired',CANARY)
        self.assertEqual(r['decision']['verdict'],'VETO_EXPIRED_OR_FUTURE')

    def test_transient_replay_ledger_rejects_reuse(self):
        r=run_variant(SOURCE,PARENT,1,'replay',CANARY)
        self.assertEqual(r['decision']['verdict'],'VETO_REPLAY')
        self.assertEqual(r['ledger_before']['nonces'],1)
        self.assertEqual(r['ledger_after']['nonces'],1)

    def test_monotonic_sequence_rejects_stale_revision(self):
        r=run_variant(SOURCE,PARENT,1,'stale_sequence',CANARY)
        self.assertEqual(r['decision']['verdict'],'VETO_STALE_SEQUENCE')
        self.assertEqual(r['ledger_after']['highest'][SOURCE],2)

    def test_report_lineage_must_match_exact_predecessor(self):
        r=run_variant(SOURCE,PARENT,1,'wrong_predecessor',CANARY)
        self.assertEqual(r['decision']['verdict'],'VETO_WRONG_PREDECESSOR')

    def test_every_fixture_variant_has_a_deterministic_auditable_witness(self):
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                first=run_variant(SOURCE,PARENT,1,variant,CANARY)
                second=run_variant(SOURCE,PARENT,1,variant,CANARY)
                self.assertEqual(first,second)
                self.assertEqual(first['decision']['verdict'],VERDICTS[variant])
                audit_row(first,SOURCE,PARENT,1,CANARY)

    def test_independent_report_row_audit_rejects_forged_quorum(self):
        row=run_variant(SOURCE,PARENT,1,'missing_reviewer',CANARY)
        altered=deepcopy(row)
        altered['decision']['two_distinct_fixture_mac_roles_valid']=True
        with self.assertRaises(CausalProbeRejected):
            audit_row(altered,SOURCE,PARENT,1,CANARY)

    def test_independent_report_row_audit_rejects_forged_semantic_verdict(self):
        row=run_variant(SOURCE,PARENT,1,'dually_signed_poison',CANARY)
        row['decision']['verdict']='ATTESTED_TEST_WITNESS_NO_EXTERNAL_TRUST'
        with self.assertRaises(CausalProbeRejected):
            audit_row(row,SOURCE,PARENT,1,CANARY)

    def test_invalid_typed_task_contract_fails_closed(self):
        specimen=envelope(SOURCE,PARENT,1)
        specimen['payload']['sequence']=True
        self.assertEqual(assess(specimen,TEST_KEYS,PARENT,CANARY,2,
                                OracleLedger())['verdict'],
                         'VETO_INVALID_TASK_CONTRACT')

    def test_task_canary_is_precommitted_reference_not_universal_truth(self):
        bad={'0':0,'1':1}
        self.assertEqual(assess(envelope(SOURCE,PARENT,1),TEST_KEYS,
                                PARENT,bad,2,OracleLedger())['verdict'],
                         'VETO_INVALID_CANARY')

    def test_bad_role_key_size_is_rejected(self):
        keyring={**TEST_KEYS,'task_specifier':b'short'}
        self.assertEqual(assess(envelope(SOURCE,PARENT,1),keyring,
                                PARENT,CANARY,2,OracleLedger())['verdict'],
                         'VETO_NO_CONFIGURED_ROLE_ROOT')

    def test_domain_separation_changes_mac(self):
        e=envelope(SOURCE,PARENT,1)
        self.assertNotEqual(e['macs'][ROLES[0]],e['macs'][ROLES[1]])
        self.assertTrue(DOMAIN.startswith(b'SPK/BV/TASK-ORACLE/'))

    def test_signed_predecessor_forgery_rejected_before_native(self):
        prior=json.loads(self.raw4)
        prior['shadow_trial_eligibility_count']=19
        with self.assertRaises(CausalProbeRejected):
            evaluate(json.loads(self.raw3),self.raw3,prior,
                     json.dumps(prior,sort_keys=True).encode())

    def test_create_only_report_exact_reference_and_safe_path(self):
        with TemporaryDirectory() as temp:
            dest=Path(temp)/'oracle.json'
            args=['--root',str(ROOT),'--v3tuv',str(self.v3),
                  '--v4yzaa',str(self.v4),'--out',str(dest)]
            with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
                self.assertEqual(main(args),0)
                self.assertEqual(main(args),2)
                args[-1]=str(ROOT/'docs/illegal-v4abad-output.json')
                self.assertEqual(main(args),2)
            self.assertEqual(dest.read_bytes(),
                (ROOT/'docs/spk-bv-v4abad-oracle-custody-observation.json').read_bytes())

    def test_pinned_source_sha_drift_rejected_without_output(self):
        with TemporaryDirectory() as temp:
            dest=Path(temp)/'no.json'
            modified={**CODE_SHA,
                      'spk_bv_research/task_oracle_custody_v4abad.py':'0'*64}
            with patch.dict(CODE_SHA,modified),redirect_stderr(io.StringIO()):
                status=main(['--root',str(ROOT),'--v3tuv',str(self.v3),
                             '--v4yzaa',str(self.v4),'--out',str(dest)])
            self.assertEqual(status,2)
            self.assertFalse(dest.exists())

    def test_symlink_predecessor_fails_closed(self):
        with TemporaryDirectory() as temp:
            link=Path(temp)/'alias.json'
            link.symlink_to(self.v4)
            dest=Path(temp)/'no.json'
            with redirect_stderr(io.StringIO()):
                status=main(['--root',str(ROOT),'--v3tuv',str(self.v3),
                             '--v4yzaa',str(link),'--out',str(dest)])
            self.assertEqual(status,2)
            self.assertFalse(dest.exists())
