"""Research-only v4p-v4r endogenous actor semantics / ACK adversarial gate."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVPlanV0e, execute_live_v0e
from spk_bv_research.native_ack_actor_loop_v4pqr import (
    CausalProbeRejected, _pinned_executable, execute_endogenous_probe,
)
from spk_bv_research.native_ack_actor_audit_v4pqr import (
    conservation, evaluate, no_feedback_exact_native_parity,
)
from search.spk_bv_v4pqr_endogenous_actor_ACK import CODE_SHA,main

ROOT = Path(__file__).resolve().parents[1]


class TestV4pqrNativeEndogenousActorACK(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        cls.v3path = Path(os.environ.get('SPK_V3TUV_REPORT',
            '/tmp/spk-bv-v3tuv-grant-rank.json'))
        cls.v4path = Path(os.environ.get('SPK_V4MNO_REPORT',
            str(ROOT / 'docs/spk-bv-v4mno-native-ACK-causal-observation.json')))
        cls.raw3 = cls.v3path.read_bytes()
        cls.raw4 = cls.v4path.read_bytes()

    @staticmethod
    def workload(ticks=(1,3), *, bv=None, feedback=True, credit=256):
        case, fabric, plans = fixture(ticks=ticks)
        plan = bv if bv is not None else LiveBVPlanV0e()
        replay = execute_endogenous_probe(case, fabric, *plans, plan,
            feedback=feedback, max_abs_actor_credit=credit)
        return case, fabric, plans, plan, replay

    def test_source_signed_18_and_derived_72_exact(self):
        report = evaluate(json.loads(self.raw3), self.raw3,
                          json.loads(self.raw4), self.raw4)
        t = report['totals']
        self.assertEqual((t['original_native_replays'],
                          t['derived_scenarios'],t['native_null_exact_parity']),
                         (18,72,18))
        self.assertEqual((t['originated_judgments'],
                          t['PE_link_charged_ACK_deliveries']), (864,864))
        self.assertEqual((t['derived_actor_credit_applied'],
                          t['actor_credit_policy_denials']), (324,540))
        self.assertFalse(report['native_learning_implemented'])

    def test_dynamic_provenance_is_after_actual_receiver_batch(self):
        *_, result = self.workload()
        conservation(result)
        self.assertEqual([j['source_emission'] for j in
                          result['derived_actor']['judgments']],
                         [a['source_emission'] for a in
                          result['derived_actor']['applied_receipts']])
        self.assertEqual(result['derived_actor_ack']['requests'], 4)

    def test_new_transport_reorders_native_without_frozen_modification(self):
        case, fabric, plans, bv, replay = self.workload(ticks=(1,2,3,4,25,26,27,28))
        native = execute_live_v0e(case, fabric, *plans, bv)
        self.assertNotEqual(native['forward'], replay['native']['forward'])
        self.assertEqual(native['forward']['states'], replay['native']['forward']['states'])
        self.assertFalse(replay['native_actor_credit_applied'])
        self.assertFalse(replay['native_learning_implemented'])

    def test_zero_feedback_independent_original_native_bitwise_projection(self):
        case, fabric, plans, bv, replay = self.workload(feedback=False)
        native = execute_live_v0e(case, fabric, *plans, bv)
        self.assertTrue(no_feedback_exact_native_parity(native,replay))
        self.assertFalse(replay['derived_actor']['judgments'])

    def test_semantic_actor_feedback_operates_when_native_terminal_BV_is_off(self):
        *_, replay = self.workload(bv=LiveBVPlanV0e(enabled=False))
        self.assertEqual(len(replay['native']['feedback']['deliveries']), 0)
        self.assertEqual(len(replay['derived_actor']['applied_receipts']), 4)

    def test_negative_receiver_output_yields_real_negative_actor_receipt(self):
        case, fabric, plans = fixture(ticks=(1,3))
        block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        changed=replace(case,nodes=tuple(replace(n,instructions=block)
            if n.node_id=='B' else n for n in case.nodes))
        result=execute_endogenous_probe(changed,fabric,*plans,LiveBVPlanV0e())
        conservation(result)
        self.assertEqual([j['response'] for j in result['derived_actor']['judgments']],
                         [-1,-1])
        self.assertEqual(result['derived_actor']['applied_credit_by_actor']['A'],-2)
        self.assertEqual(result['native']['forward']['states']['A'],0)

    def test_credit_policy_denial_never_relabels_actual_transport_as_loss(self):
        *_, result = self.workload(credit=0)
        conservation(result)
        self.assertEqual(result['derived_actor_ack']['requests'],4)
        self.assertEqual(result['derived_actor_ack']['applied_actor_credits'],0)
        self.assertTrue(all(d['actor_credit_denied_by_policy'] for d in
                            result['derived_actor_ack']['transport_deliveries']))
        self.assertTrue(all(not d['actor_credit_applied'] for d in
                            result['derived_actor_ack']['transport_deliveries']))

    def test_narrow_credit_is_bounded_and_replays_remain_consistent(self):
        *_, result = self.workload(credit=1)
        conservation(result)
        self.assertEqual(result['derived_actor']['applied_credit_by_actor']['A'],1)
        self.assertEqual(result['derived_actor']['applied_credit_by_actor']['B'],1)

    def test_actor_feedback_quota_rejects_unpaid_generation(self):
        case, fabric, plans = fixture(ticks=(1,3))
        with self.assertRaisesRegex(CausalProbeRejected, 'quota'):
            execute_endogenous_probe(case,fabric,*plans,LiveBVPlanV0e(),
                                     max_judgments=1)

    def test_unsupported_policy_types_are_rejected(self):
        case, fabric, plans = fixture()
        for kwargs in ({'feedback':1},{'max_judgments':True},
                       {'max_abs_actor_credit':513},
                       {'max_abs_actor_credit':-1}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(CausalProbeRejected):
                    execute_endogenous_probe(case,fabric,*plans,
                                             LiveBVPlanV0e(),**kwargs)

    def test_independent_resource_ledger_rejects_fabric_PE_forgery(self):
        *_, result=self.workload()
        altered=deepcopy(result)
        altered['native']['resources']['timeline'][0]['pe_service_total']+=1
        with self.assertRaisesRegex(CausalProbeRejected, 'conservation'):
            conservation(altered)

    def test_custody_rejects_forged_semantic_response_and_wrong_owner(self):
        *_, result=self.workload()
        altered=deepcopy(result)
        altered['derived_actor']['judgments'][0]['response']*=-1
        with self.assertRaises(CausalProbeRejected):
            conservation(altered)
        altered=deepcopy(result)
        altered['derived_actor_ack']['transport_grants'][0]['source_pe']='PE2'
        with self.assertRaises(CausalProbeRejected):
            conservation(altered)

    def test_consumer_chain_rejects_receipt_tamper(self):
        *_, result=self.workload()
        altered=deepcopy(result)
        altered['derived_actor']['applied_receipts'][0]['credit_after']=9
        with self.assertRaises(CausalProbeRejected):
            conservation(altered)

    def test_mismatched_signed_v4mno_source_rejected(self):
        changed=json.loads(self.raw4)
        changed['totals']['simulated_ack_deliveries']=0
        with self.assertRaisesRegex(CausalProbeRejected, 'predecessor'):
            evaluate(json.loads(self.raw3),self.raw3,changed,
                     json.dumps(changed,sort_keys=True).encode())

    def test_corrupt_pinned_executor_source_rejected_before_compilation(self):
        source = ROOT / 'spk_bv_research/native_ack_causal_replay_v4mno.py'
        original = Path.read_bytes
        def fake_read(path):
            if path == source:
                return original(path) + b'# malicious change\n'
            return original(path)
        with patch.object(Path,'read_bytes',fake_read):
            with self.assertRaisesRegex(CausalProbeRejected,'SHA drift'):
                _pinned_executable()

    def test_independent_determinism_with_actor_transports(self):
        case, fabric, plans, bv, first = self.workload()
        second=execute_endogenous_probe(case,fabric,*plans,bv)
        self.assertEqual(first,second)

    def test_create_only_runner_rejects_duplicate_and_repository_output(self):
        with TemporaryDirectory() as temp:
            dest=Path(temp)/'created.json'
            args=['--root',str(ROOT),'--v3tuv',str(self.v3path),
                  '--v4mno',str(self.v4path),'--out',str(dest)]
            with redirect_stderr(io.StringIO()),redirect_stdout(io.StringIO()):
                self.assertEqual(main(args),0)
                self.assertEqual(main(args),2)
                args[-1]=str(ROOT/'docs/unaccepted-v4p-output.json')
                self.assertEqual(main(args),2)
            self.assertEqual(dest.read_bytes(),
                (ROOT/'docs/spk-bv-v4pqr-endogenous-actor-ACK-observation.json').read_bytes())

    def test_cli_fails_closed_on_code_SHA_drift(self):
        with TemporaryDirectory() as temp:
            dest=Path(temp)/'never.json'
            args=['--root',str(ROOT),'--v3tuv',str(self.v3path),
                  '--v4mno',str(self.v4path),'--out',str(dest)]
            altered={**CODE_SHA,'spk_bv_research/native_ack_actor_loop_v4pqr.py':'0'*64}
            with patch.dict(CODE_SHA,altered),redirect_stderr(io.StringIO()):
                self.assertEqual(main(args),2)
            self.assertFalse(dest.exists())


if __name__=='__main__':
    unittest.main()
