"""v4v-v4x two-episode ACK-conditioned candidate authority adversarial gate."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVPlanV0e, execute_live_v0e
from spk_bv_research.native_ack_paid_consumer_v4stu import (
    CausalProbeRejected, execute_paid_consumer_probe,
)
from spk_bv_research.native_actor_candidate_boundary_v4vwx import (
    _change_cmp, _challenge, VARIANTS, evaluate_candidate,
)
from spk_bv_research.native_actor_candidate_audit_v4vwx import (
    audit_candidate, evaluate,
)
from search.spk_bv_v4vwx_candidate_authority import CODE_SHA, main

ROOT = Path(__file__).resolve().parents[1]


class TestV4vwxCandidateAuthority(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        cls.v3=Path(os.environ.get('SPK_V3TUV_REPORT',
            '/tmp/spk-bv-v3tuv-grant-rank.json'))
        cls.v4=Path(os.environ.get('SPK_V4STU_REPORT',
            str(ROOT/'docs/spk-bv-v4stu-paid-actor-consumer-observation.json')))
        cls.raw3=cls.v3.read_bytes()
        cls.raw4=cls.v4.read_bytes()

    @staticmethod
    def source(ticks=(1,3),*,bv=None):
        c,f,p=fixture(ticks=ticks)
        b=bv if bv is not None else LiveBVPlanV0e()
        paid=execute_paid_consumer_probe(c,f,*p,b,consumer_policy='consumer-first')
        return c,f,p,b,paid

    def test_signed_18_plus_90_candidate_shadow_episodes(self):
        report=evaluate(json.loads(self.raw3),self.raw3,
                        json.loads(self.raw4),self.raw4)
        totals=report['totals']
        self.assertEqual((totals['native_source_replays'],
                          totals['paid_source_actor_reexecutions'],
                          totals['candidate_shadow_episodes']),(18,18,90))
        self.assertEqual((totals['verdict_VETO_AUTHORITY'],
                          totals['verdict_VETO_SIGNED_SOURCE_SEMANTICS'],
                          totals['verdict_VETO_OFF_MATRIX_COUNTEREXAMPLE'],
                          totals['verdict_VETO_NO_OP_NOT_LEARNING']),
                         (36,18,18,18))
        self.assertEqual(report['applied_native_learning_updates'],0)
        self.assertEqual(report['adopted_derived_algorithm_updates'],0)

    def test_owner_authority_is_not_granted_by_positive_ACK_alone(self):
        c,f,p,b,source=self.source()
        r=evaluate_candidate(c,f,*p,b,source,'owner_denied')
        audit_candidate(r,c,f,p,b,source)
        self.assertEqual(r['verdict'],'VETO_AUTHORITY')
        self.assertFalse(r['authority']['owner_approval'])
        self.assertEqual(r['proposal']['positive_paid_ACK_receipts'],2)

    def test_independent_review_cannot_be_skipped(self):
        c,f,p,b,source=self.source()
        r=evaluate_candidate(c,f,*p,b,source,'reviewer_denied')
        audit_candidate(r,c,f,p,b,source)
        self.assertEqual(r['verdict'],'VETO_AUTHORITY')
        self.assertTrue(r['authority']['owner_approval'])
        self.assertFalse(r['authority']['independent_reviewer_approval'])

    def test_even_dual_authority_rejects_candidate_that_breaks_source(self):
        c,f,p,b,source=self.source()
        r=evaluate_candidate(c,f,*p,b,source,'signed_unsafe')
        self.assertEqual(r['verdict'],'VETO_SIGNED_SOURCE_SEMANTICS')
        self.assertFalse(r['counterfactual']['signed_workload_exact_parity'])
        self.assertEqual(r['proposal']['threshold_proposed'],2)

    def test_signed_parity_is_not_a_global_safety_proof(self):
        c,f,p,b,source=self.source()
        r=evaluate_candidate(c,f,*p,b,source,'holdout_unsafe')
        audit_candidate(r,c,f,p,b,source)
        self.assertTrue(r['counterfactual']['signed_workload_exact_parity'])
        self.assertFalse(r['counterfactual']['off_matrix_channel_challenge_parity'])
        self.assertEqual(r['verdict'],'VETO_OFF_MATRIX_COUNTEREXAMPLE')
        self.assertGreater(r['counterfactual']['candidate_holdout_terminal'],0)
        self.assertGreater(r['counterfactual']['candidate_holdout_terminal'],
                           r['counterfactual']['source_holdout_terminal'])

    def test_no_op_is_not_renamed_learning(self):
        c,f,p,b,source=self.source()
        r=evaluate_candidate(c,f,*p,b,source,'no_op')
        audit_candidate(r,c,f,p,b,source)
        self.assertTrue(r['counterfactual']['signed_workload_exact_parity'])
        self.assertTrue(r['counterfactual']['off_matrix_channel_challenge_parity'])
        self.assertFalse(r['counterfactual']['program_changed'])
        self.assertEqual(r['verdict'],'VETO_NO_OP_NOT_LEARNING')

    def test_cross_episode_source_is_not_mutated_in_place(self):
        c,f,p,b,source=self.source(ticks=(1,2,3,4,25,26,27,28))
        previous=deepcopy(c)
        first=evaluate_candidate(c,f,*p,b,source,'holdout_unsafe')
        self.assertEqual(c,previous)
        self.assertEqual(source,execute_paid_consumer_probe(
            c,f,*p,b,consumer_policy='consumer-first'))
        self.assertFalse(first['frozen_native_program_mutated'])
        self.assertEqual(first['committed_derived_program_version'],0)

    def test_independent_audit_rejects_forged_authority_and_proposal(self):
        c,f,p,b,source=self.source()
        r=evaluate_candidate(c,f,*p,b,source,'holdout_unsafe')
        for path in ('authority','proposal'):
            altered=deepcopy(r)
            if path=='authority':
                altered[path]['owner_approval']=False
            else:
                altered[path]['positive_paid_ACK_receipts']+=1
            with self.subTest(path=path):
                with self.assertRaises(CausalProbeRejected):
                    audit_candidate(altered,c,f,p,b,source)

    def test_independent_audit_rejects_forged_signed_or_holdout_evidence(self):
        c,f,p,b,source=self.source()
        r=evaluate_candidate(c,f,*p,b,source,'holdout_unsafe')
        for key in ('signed_workload_exact_parity',
                    'off_matrix_channel_challenge_parity',
                    'candidate_holdout_terminal'):
            altered=deepcopy(r)
            if type(altered['counterfactual'][key]) is bool:
                altered['counterfactual'][key]=not altered['counterfactual'][key]
            else:
                altered['counterfactual'][key]+=1
            with self.subTest(key=key):
                with self.assertRaises(CausalProbeRejected):
                    audit_candidate(altered,c,f,p,b,source)

    def test_false_claim_of_native_learning_is_rejected(self):
        c,f,p,b,source=self.source()
        r=evaluate_candidate(c,f,*p,b,source,'no_op')
        altered=deepcopy(r)
        altered['native_learning_implemented']=True
        with self.assertRaises(CausalProbeRejected):
            audit_candidate(altered,c,f,p,b,source)
        altered=deepcopy(r)
        altered['committed_derived_program_version']=1
        with self.assertRaises(CausalProbeRejected):
            audit_candidate(altered,c,f,p,b,source)

    def test_negative_feedback_cannot_be_invented_as_positive_proposal(self):
        c,f,p=fixture(ticks=(1,3))
        block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        c=replace(c,nodes=tuple(replace(n,instructions=block)
            if n.node_id=='B' else n for n in c.nodes))
        b=LiveBVPlanV0e()
        source=execute_paid_consumer_probe(c,f,*p,b)
        with self.assertRaisesRegex(CausalProbeRejected,'insufficient'):
            evaluate_candidate(c,f,*p,b,source,'holdout_unsafe')

    def test_unsupported_candidate_threshold_and_mode_fail_closed(self):
        c,f,p,b,source=self.source()
        for value in (-1,True,3,'0'):
            with self.subTest(value=value):
                with self.assertRaises(CausalProbeRejected):
                    _change_cmp(c,value)
        with self.assertRaises(CausalProbeRejected):
            evaluate_candidate(c,f,*p,b,source,'force-adopt')

    def test_off_matrix_channel_challenge_is_independently_reproducible(self):
        c,f,p,b,source=self.source()
        modified=_change_cmp(c,0)
        original_native=execute_live_v0e(_challenge(c),f,*p,b)
        changed_native=execute_live_v0e(_challenge(modified),f,*p,b)
        self.assertNotEqual(original_native['forward']['emissions'],
                            changed_native['forward']['emissions'])
        self.assertGreater(len(changed_native['forward']['terminal']),
                           len(original_native['forward']['terminal']))

    def test_signed_predecessor_tamper_rejected(self):
        corrupted=json.loads(self.raw4)
        corrupted['totals']['paid_consumer_services']+=1
        with self.assertRaisesRegex(CausalProbeRejected,'predecessor'):
            evaluate(json.loads(self.raw3),self.raw3,corrupted,
                     json.dumps(corrupted,sort_keys=True).encode())

    def test_candidate_determinism(self):
        c,f,p,b,source=self.source()
        first=evaluate_candidate(c,f,*p,b,source,'holdout_unsafe')
        second=evaluate_candidate(c,f,*p,b,source,'holdout_unsafe')
        self.assertEqual(first,second)

    def test_create_only_signed_report_and_exact_pinned_observation(self):
        with TemporaryDirectory() as temp:
            dest=Path(temp)/'research.json'
            args=['--root',str(ROOT),'--v3tuv',str(self.v3),
                  '--v4stu',str(self.v4),'--out',str(dest)]
            with redirect_stderr(io.StringIO()),redirect_stdout(io.StringIO()):
                self.assertEqual(main(args),0)
                self.assertEqual(main(args),2)
                args[-1]=str(ROOT/'docs/illegal-v4vwx-output.json')
                self.assertEqual(main(args),2)
            self.assertEqual(dest.read_bytes(),
                (ROOT/'docs/spk-bv-v4vwx-candidate-authority-observation.json').read_bytes())

    def test_pinned_new_code_SHA_drift_fails_closed(self):
        with TemporaryDirectory() as temp:
            dest=Path(temp)/'not-created.json'
            args=['--root',str(ROOT),'--v3tuv',str(self.v3),
                  '--v4stu',str(self.v4),'--out',str(dest)]
            modified={**CODE_SHA,
                      'spk_bv_research/native_actor_candidate_boundary_v4vwx.py':'0'*64}
            with patch.dict(CODE_SHA,modified),redirect_stderr(io.StringIO()):
                self.assertEqual(main(args),2)
            self.assertFalse(dest.exists())

    def test_symlinked_signed_source_is_rejected_before_run(self):
        with TemporaryDirectory() as temp:
            tmp=Path(temp)
            symlink=tmp/'fake-predecessor.json'
            symlink.symlink_to(self.v4)
            dest=tmp/'not-created.json'
            args=['--root',str(ROOT),'--v3tuv',str(self.v3),
                  '--v4stu',str(symlink),'--out',str(dest)]
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(args),2)
            self.assertFalse(dest.exists())


if __name__=='__main__':
    unittest.main()
