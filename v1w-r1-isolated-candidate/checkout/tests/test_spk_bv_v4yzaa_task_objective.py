"""v4y-v4aa signed external task objective and adversarial controls."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVPlanV0e, execute_live_v0e
from spk_bv_research.native_ack_causal_replay_v4mno import CausalProbeRejected
from spk_bv_research.native_actor_objective_v4yzaa import (
    OBJECTIVE, VARIANTS, _set_cmp, _probe_case, _score, evaluate_objective,
)
from spk_bv_research.native_actor_objective_audit_v4yzaa import (
    audit_objective,evaluate,
)
from spk_bv_research.native_ack_paid_consumer_v4stu import execute_paid_consumer_probe
from search.spk_bv_v4yzaa_task_objective import CODE_SHA, main

ROOT=Path(__file__).resolve().parents[1]


class TestV4yzaaExternalTaskObjective(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v3=Path(os.environ.get('SPK_V3TUV_REPORT',
            '/tmp/spk-bv-v3tuv-grant-rank.json'))
        cls.v4=Path(os.environ.get('SPK_V4VWX_REPORT',
            str(ROOT/'docs/spk-bv-v4vwx-candidate-authority-observation.json')))
        cls.raw3=cls.v3.read_bytes()
        cls.raw4=cls.v4.read_bytes()

    @staticmethod
    def context(ticks=(1,3), bv=None):
        case,fabric,plans=fixture(ticks=ticks)
        return case,fabric,plans,bv or LiveBVPlanV0e(enabled=False)

    def test_full_signed_18_native_and_126_counterfactuals(self):
        report=evaluate(json.loads(self.raw3),self.raw3,
                        json.loads(self.raw4),self.raw4)
        t=report['totals']
        self.assertEqual((t['signed_native_replays'],
                          t['counterfactual_objective_trials'],
                          t['positive_misleading_ACKs']),(18,126,72))
        self.assertEqual(t['verdict_ELIGIBLE_SHADOW_TRIAL_NOT_ADOPTED'],18)
        self.assertEqual(t['verdict_VETO_UNAUTHENTICATED_RESEARCH_AUTHORITY'],36)
        self.assertEqual(t['verdict_VETO_NO_OBJECTIVE_IMPROVEMENT'],54)
        self.assertEqual(t['verdict_VETO_NO_OP'],18)
        self.assertEqual(report['actual_shadow_adoptions'],0)
        self.assertFalse(report['native_learning_implemented'])

    def test_receiver_positive_ACK_can_reward_wrong_task_response(self):
        c,f,p,b=self.context()
        bad=_set_cmp(c,1,0)
        distractor=_probe_case(bad,1)
        executed=execute_paid_consumer_probe(distractor,f,*p,b)
        self.assertEqual(len(executed['native']['forward']['terminal']),1)
        receipt=[r for r in executed['derived_actor']['applied_receipts']
                 if r['actor']=='A']
        self.assertEqual(len(receipt),1)
        self.assertEqual(receipt[0]['response'],1)
        self.assertEqual(OBJECTIVE['expected_terminal_counts']['1'],0)

    def test_signed_source_is_objective_optimal_on_declared_two_channels(self):
        c,f,p,b=self.context()
        base=_score(c,f,p,b)
        self.assertEqual((base['false_negative'],base['false_positive'],
                          base['declared_cost']),(0,0,0))
        for variant in ('source_overfire','source_underfire'):
            row=evaluate_objective(c,f,p,b,variant)
            audit_objective(row,c,f,p,b)
            self.assertLess(row['objective_cost_improvement'],0)
            self.assertEqual(row['verdict'],'VETO_NO_OBJECTIVE_IMPROVEMENT')

    def test_injected_degraded_program_has_falsifiable_positive_control(self):
        c,f,p,b=self.context()
        row=evaluate_objective(c,f,p,b,'degraded_repair')
        audit_objective(row,c,f,p,b)
        self.assertEqual(row['old_task_score']['declared_cost'],4)
        self.assertEqual(row['new_task_score']['declared_cost'],0)
        self.assertEqual(row['objective_cost_improvement'],4)
        self.assertEqual(row['verdict'],'ELIGIBLE_SHADOW_TRIAL_NOT_ADOPTED')
        self.assertEqual(row['committed_derived_program_version'],0)
        self.assertFalse(row['native_learning_implemented'])

    def test_correcting_false_positive_by_creating_false_negative_is_not_improvement(self):
        c,f,p,b=self.context()
        row=evaluate_objective(c,f,p,b,'degraded_tradeoff')
        audit_objective(row,c,f,p,b)
        self.assertEqual(row['old_task_score']['declared_cost'],4)
        self.assertEqual(row['new_task_score']['declared_cost'],5)
        self.assertFalse(row['no_component_regression'])
        self.assertEqual(row['verdict'],'VETO_NO_OBJECTIVE_IMPROVEMENT')

    def test_authority_flags_do_not_spring_from_objective_improvement(self):
        c,f,p,b=self.context()
        for variant in ('degraded_owner_denied','degraded_reviewer_denied'):
            row=evaluate_objective(c,f,p,b,variant)
            audit_objective(row,c,f,p,b)
            self.assertEqual(row['objective_cost_improvement'],4)
            self.assertEqual(row['verdict'],
                             'VETO_UNAUTHENTICATED_RESEARCH_AUTHORITY')

    def test_signed_native_program_and_fixture_are_never_mutated(self):
        c,f,p,b=self.context()
        original=deepcopy(c)
        live=execute_live_v0e(c,f,*p,b)
        evaluate_objective(c,f,p,b,'degraded_repair')
        self.assertEqual(c,original)
        self.assertEqual(execute_live_v0e(c,f,*p,b),live)

    def test_task_contract_is_not_disguised_as_empirical_truth(self):
        self.assertEqual(OBJECTIVE['source'],
                         'HYPOTHESIS_TEST_TWO_CHANNEL_EVENT_CLASSIFICATION')
        self.assertFalse(OBJECTIVE['blind_external_ground_truth_available'])
        self.assertFalse(OBJECTIVE['physical_energy_model_available'])

    def test_all_evidence_is_deterministic_and_temporally_challenged(self):
        c,f,p,b=self.context()
        first=evaluate_objective(c,f,p,b,'degraded_repair')
        second=evaluate_objective(c,f,p,b,'degraded_repair')
        self.assertEqual(first,second)
        self.assertTrue(first['temporal_challenge_consistent'])
        self.assertEqual(first['new_temporal_challenge']['declared_cost'],0)

    def test_independent_audit_rejects_score_forgery(self):
        c,f,p,b=self.context()
        row=evaluate_objective(c,f,p,b,'degraded_repair')
        forged=deepcopy(row)
        forged['new_task_score']['declared_cost']=1
        with self.assertRaises(CausalProbeRejected):
            audit_objective(forged,c,f,p,b)

    def test_independent_audit_rejects_false_program_version_commit(self):
        c,f,p,b=self.context()
        row=evaluate_objective(c,f,p,b,'degraded_repair')
        row['committed_derived_program_version']=1
        with self.assertRaises(CausalProbeRejected):
            audit_objective(row,c,f,p,b)

    def test_independent_audit_rejects_forged_receiver_ACK(self):
        c,f,p,b=self.context()
        row=evaluate_objective(c,f,p,b,'degraded_repair')
        row['negative_task_label_positive_paid_ACKs']=0
        with self.assertRaises(CausalProbeRejected):
            audit_objective(row,c,f,p,b)

    def test_independent_audit_rejects_forged_task_spec_hash(self):
        c,f,p,b=self.context()
        row=evaluate_objective(c,f,p,b,'degraded_repair')
        row['task_contract_sha256']='0'*64
        with self.assertRaises(CausalProbeRejected):
            audit_objective(row,c,f,p,b)

    def test_invalid_program_input_and_variant_fail_closed(self):
        c,f,p,b=self.context()
        for bad in (-1,3,True,'2'):
            with self.subTest(bad=bad):
                with self.assertRaises(CausalProbeRejected):
                    _set_cmp(c,1,bad)
        with self.assertRaises(CausalProbeRejected):
            _set_cmp(c,0,1)
        with self.assertRaises(CausalProbeRejected):
            evaluate_objective(c,f,p,b,'adopt')

    def test_invalid_probe_and_mismatched_source_fail_closed(self):
        c,f,p,b=self.context()
        for channel in (True,2,'1'):
            with self.assertRaises(CausalProbeRejected):
                _probe_case(c,channel)
        changed=replace(c,nodes=tuple(replace(n,instructions=(('CMP',0),))
            if n.node_id=='A' else n for n in c.nodes))
        with self.assertRaises(CausalProbeRejected):
            evaluate_objective(changed,f,p,b,'degraded_repair')

    def test_forged_signed_predecessor_rejected(self):
        changed=json.loads(self.raw4)
        changed['totals']['candidate_shadow_episodes']+=1
        altered=json.dumps(changed,sort_keys=True).encode()
        with self.assertRaises(CausalProbeRejected):
            evaluate(json.loads(self.raw3),self.raw3,changed,altered)

    def test_create_only_report_and_exact_pinned_observation(self):
        with TemporaryDirectory() as temp:
            target=Path(temp)/'objective.json'
            args=['--root',str(ROOT),'--v3tuv',str(self.v3),
                  '--v4vwx',str(self.v4),'--out',str(target)]
            with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
                self.assertEqual(main(args),0)
                self.assertEqual(main(args),2)
                args[-1]=str(ROOT/'docs/illegal-v4yzaa-output.json')
                self.assertEqual(main(args),2)
            self.assertEqual(target.read_bytes(),
                (ROOT/'docs/spk-bv-v4yzaa-task-objective-observation.json').read_bytes())

    def test_code_SHA_drift_fails_closed_before_output(self):
        with TemporaryDirectory() as temp:
            target=Path(temp)/'objective.json'
            changed={**CODE_SHA,
                'spk_bv_research/native_actor_objective_v4yzaa.py':'0'*64}
            with patch.dict(CODE_SHA,changed),redirect_stderr(io.StringIO()):
                status=main(['--root',str(ROOT),'--v3tuv',str(self.v3),
                             '--v4vwx',str(self.v4),'--out',str(target)])
            self.assertEqual(status,2)
            self.assertFalse(target.exists())

    def test_symlinked_signed_source_is_rejected(self):
        with TemporaryDirectory() as temp:
            source=Path(temp)/'alias.json'
            source.symlink_to(self.v4)
            dest=Path(temp)/'out.json'
            with redirect_stderr(io.StringIO()):
                status=main(['--root',str(ROOT),'--v3tuv',str(self.v3),
                             '--v4vwx',str(source),'--out',str(dest)])
            self.assertEqual(status,2)
            self.assertFalse(dest.exists())
