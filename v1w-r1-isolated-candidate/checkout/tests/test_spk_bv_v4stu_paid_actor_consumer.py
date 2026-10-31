"""v4s-v4u adversarial and causal paid-derived-actor consumer tests."""
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
    CausalProbeRejected, _pinned_executable, execute_paid_consumer_probe,
)
from spk_bv_research.native_ack_paid_consumer_audit_v4stu import (
    conservation, evaluate, null_native_parity,
)
from search.spk_bv_v4stu_paid_actor_consumer import CODE_SHA, main

ROOT = Path(__file__).resolve().parents[1]


class TestV4stuPaidDerivedActorConsumer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        cls.v3 = Path(os.environ.get('SPK_V3TUV_REPORT',
            '/tmp/spk-bv-v3tuv-grant-rank.json'))
        cls.v4 = Path(os.environ.get('SPK_V4PQR_REPORT',
            str(ROOT/'docs/spk-bv-v4pqr-endogenous-actor-ACK-observation.json')))
        cls.raw3 = cls.v3.read_bytes()
        cls.raw4 = cls.v4.read_bytes()

    @staticmethod
    def case(*, ticks=(1,3), policy='consumer-first', feedback=True,
             credit=256, bv=None, pe=None):
        case,fabric,plans=fixture(ticks=ticks)
        p=replace(plans[1],fabric_slots_per_tick=pe) if pe is not None else plans[1]
        b=bv if bv is not None else LiveBVPlanV0e()
        replay=execute_paid_consumer_probe(case,fabric,plans[0],p,plans[2],
                                           plans[3],b,consumer_policy=policy,
                                           feedback=feedback,
                                           max_abs_actor_credit=credit)
        return case,fabric,(plans[0],p,plans[2],plans[3]),b,replay

    def test_signed_matrix_18_and_90_reexecutions(self):
        report=evaluate(json.loads(self.raw3),self.raw3,
                        json.loads(self.raw4),self.raw4)
        t=report['totals']
        self.assertEqual((t['original_native_replays'],t['derived_scenarios'],
                          t['null_native_exact_parity']),(18,90,18))
        self.assertEqual((t['generated_judgments'],
                          t['actual_ACK_transport_deliveries'],
                          t['paid_consumer_services']), (1152,1152,576))
        self.assertFalse(report['native_learning_implemented'])

    def test_actor_delivery_does_not_instantly_mutate_credit_without_paid_service(self):
        c,f,p,b,r=self.case(policy='native-first',pe=1)
        conservation(r,c,f,p[1],p[2])
        services=r['derived_actor']['consumer_service_grants']
        self.assertEqual(len(services),len(r['derived_actor']['applied_receipts']))
        self.assertTrue(any(s['wait']>0 for s in services))
        self.assertTrue(all(s['tick']>=s['delivery_tick'] for s in services))
        self.assertTrue(all(s['PE_units']==s['memory_units']==1 and
                            s['memory_domain']=='S' for s in services))

    def test_consumer_first_and_native_first_have_distinct_causal_service_order(self):
        c,f,p,b,first=self.case(ticks=(1,2,3,4,25,26,27,28),pe=1)
        other=execute_paid_consumer_probe(c,f,*p,b,consumer_policy='native-first')
        conservation(first,c,f,p[1],p[2])
        conservation(other,c,f,p[1],p[2])
        self.assertNotEqual(first['native']['forward'],other['native']['forward'])
        self.assertEqual(first['native']['forward']['states'],
                         other['native']['forward']['states'])
        self.assertEqual(len(first['derived_actor']['applied_receipts']),16)
        self.assertEqual(len(other['derived_actor']['applied_receipts']),16)

    def test_no_feedback_exact_frozen_native_parity(self):
        c,f,p,b,r=self.case(feedback=False)
        native=execute_live_v0e(c,f,*p,b)
        self.assertTrue(null_native_parity(native,r))
        conservation(r,c,f,p[1],p[2])

    def test_no_native_terminal_BV_required_for_semantic_actor_judgment(self):
        c,f,p,b,r=self.case(bv=LiveBVPlanV0e(enabled=False))
        conservation(r,c,f,p[1],p[2])
        self.assertFalse(r['native']['feedback']['deliveries'])
        self.assertEqual(len(r['derived_actor']['applied_receipts']),4)

    def test_consumer_off_still_transports_but_does_not_apply_any_credit(self):
        c,f,p,b,r=self.case(policy='consumer-off')
        conservation(r,c,f,p[1],p[2])
        self.assertEqual(r['derived_actor_ack']['requests'],4)
        self.assertEqual(len(r['derived_actor']['unserved_deliveries']),4)
        self.assertEqual(len(r['derived_actor']['consumer_service_grants']),0)
        self.assertFalse(any(d['actor_credit_applied'] for d in
                             r['derived_actor_ack']['transport_deliveries']))

    def test_zero_credit_denial_is_neither_loss_nor_negative_semantic_judgment(self):
        c,f,p,b,r=self.case(credit=0)
        conservation(r,c,f,p[1],p[2])
        self.assertEqual(len(r['derived_actor_ack']['transport_deliveries']),4)
        self.assertFalse(r['derived_actor']['applied_receipts'])
        self.assertTrue(all(d.get('actor_credit_denied_by_policy') for d in
                            r['derived_actor_ack']['transport_deliveries']))

    def test_negative_actor_feedback_from_real_zero_output_is_charged(self):
        c,f,p=fixture(ticks=(1,3))
        instructions=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        c=replace(c,nodes=tuple(replace(n,instructions=instructions)
            if n.node_id=='B' else n for n in c.nodes))
        b=LiveBVPlanV0e()
        r=execute_paid_consumer_probe(c,f,*p,b)
        conservation(r,c,f,p[1],p[2])
        self.assertEqual([j['response'] for j in r['derived_actor']['judgments']],[-1,-1])
        self.assertEqual(r['derived_actor']['applied_credit_by_actor']['A'],-2)
        self.assertEqual(len(r['derived_actor']['consumer_service_grants']),2)

    def test_paid_consumer_resource_ledger_rejects_PE_and_S_forgery(self):
        c,f,p,b,r=self.case()
        for key in ('pe_service_total','memory_total'):
            tampered=deepcopy(r)
            last=next(x for x in tampered['native']['resources']['timeline']
                if x['derived_actor_consumer_services'])
            last[key]+=1
            with self.subTest(key=key):
                with self.assertRaises(CausalProbeRejected):
                    conservation(tampered,c,f,p[1],p[2])
        tampered=deepcopy(r)
        tampered['derived_actor']['consumer_service_grants'][0]['memory_domain']='O'
        with self.assertRaisesRegex(CausalProbeRejected,'PE/S'):
            conservation(tampered,c,f,p[1],p[2])

    def test_reject_actor_receipt_without_service_and_wrong_owner(self):
        c,f,p,b,r=self.case()
        altered=deepcopy(r)
        altered['derived_actor']['consumer_service_grants'].pop()
        with self.assertRaises(CausalProbeRejected):
            conservation(altered,c,f,p[1],p[2])
        altered=deepcopy(r)
        altered['derived_actor']['applied_receipts'][0]['owner_pe']='PE2'
        with self.assertRaises(CausalProbeRejected):
            conservation(altered,c,f,p[1],p[2])

    def test_reject_time_travel_queued_ACK_consumer(self):
        c,f,p,b,r=self.case()
        altered=deepcopy(r)
        altered['derived_actor']['consumer_service_grants'][0]['tick']-=1
        with self.assertRaises(CausalProbeRejected):
            conservation(altered,c,f,p[1],p[2])

    def test_reject_replayed_or_mutated_hash_receipt(self):
        c,f,p,b,r=self.case()
        altered=deepcopy(r)
        altered['derived_actor']['applied_receipts'][0]['credit_after']+=1
        with self.assertRaises(CausalProbeRejected):
            conservation(altered,c,f,p[1],p[2])
        altered=deepcopy(r)
        altered['derived_actor']['applied_receipts'].append(
            altered['derived_actor']['applied_receipts'][0])
        with self.assertRaises(CausalProbeRejected):
            conservation(altered,c,f,p[1],p[2])

    def test_adversarial_semantic_forgery_rejected(self):
        c,f,p,b,r=self.case()
        altered=deepcopy(r)
        altered['derived_actor']['judgments'][0]['response']*=-1
        with self.assertRaises(CausalProbeRejected):
            conservation(altered,c,f,p[1],p[2])
        altered=deepcopy(r)
        altered['derived_actor_ack']['transport_grants'][0]['source_pe']='PE2'
        with self.assertRaises(CausalProbeRejected):
            conservation(altered,c,f,p[1],p[2])

    def test_policy_and_quota_fail_closed(self):
        c,f,p=fixture()
        b=LiveBVPlanV0e()
        for kw in ({'consumer_policy':'adopt-native'},
                   {'feedback':1},{'max_abs_actor_credit':-1},
                   {'max_abs_actor_credit':513},{'max_judgments':True}):
            with self.subTest(policy=kw):
                with self.assertRaises(CausalProbeRejected):
                    execute_paid_consumer_probe(c,f,*p,b,**kw)
        with self.assertRaisesRegex(CausalProbeRejected,'quota'):
            execute_paid_consumer_probe(c,f,*p,b,max_judgments=1)

    def test_inadequate_owner_S_memory_does_not_borrow_undocumented_resource(self):
        c,f,p=fixture()
        tiny=replace(p[2],domain_slots=tuple((d,1 if d=='S' else v)
                 for d,v in p[2].domain_slots))
        with self.assertRaises(CausalProbeRejected):
            execute_paid_consumer_probe(c,f,p[0],p[1],tiny,p[3],LiveBVPlanV0e())

    def test_signed_predecessor_mutation_rejected(self):
        changed=json.loads(self.raw4)
        changed['totals']['derived_scenarios']=73
        with self.assertRaisesRegex(CausalProbeRejected,'predecessor'):
            evaluate(json.loads(self.raw3),self.raw3,changed,
                     json.dumps(changed,sort_keys=True).encode())

    def test_parent_code_SHA_drift_fails_before_compilation(self):
        parent=ROOT/'spk_bv_research/native_ack_causal_replay_v4mno.py'
        original=Path.read_bytes
        def fake_read(path):
            data=original(path)
            return data+b'\n# injected' if path==parent else data
        with patch.object(Path,'read_bytes',fake_read):
            with self.assertRaisesRegex(CausalProbeRejected,'SHA drift'):
                _pinned_executable()

    def test_source_deterministic_reexecution_same_input(self):
        c,f,p,b,r=self.case(policy='native-first')
        self.assertEqual(r,execute_paid_consumer_probe(
            c,f,*p,b,consumer_policy='native-first'))

    def test_create_only_runner_and_exact_pinned_observation(self):
        with TemporaryDirectory() as temp:
            dest=Path(temp)/'paid.json'
            argv=['--root',str(ROOT),'--v3tuv',str(self.v3),
                  '--v4pqr',str(self.v4),'--out',str(dest)]
            with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
                self.assertEqual(main(argv),0)
                self.assertEqual(main(argv),2)
                argv[-1]=str(ROOT/'docs/unaccepted-v4stu-output.json')
                self.assertEqual(main(argv),2)
            self.assertEqual(dest.read_bytes(),
                (ROOT/'docs/spk-bv-v4stu-paid-actor-consumer-observation.json').read_bytes())

    def test_code_sha_drift_blocks_cli_before_any_output(self):
        with TemporaryDirectory() as temp:
            dest=Path(temp)/'no-output.json'
            argv=['--root',str(ROOT),'--v3tuv',str(self.v3),
                  '--v4pqr',str(self.v4),'--out',str(dest)]
            bad={**CODE_SHA,
                 'spk_bv_research/native_ack_paid_consumer_v4stu.py':'0'*64}
            with patch.dict(CODE_SHA,bad),redirect_stderr(io.StringIO()):
                self.assertEqual(main(argv),2)
            self.assertFalse(dest.exists())

    def test_signed_source_symlink_and_repository_path_rejected(self):
        with TemporaryDirectory() as temp:
            temp=Path(temp)
            v4link=temp/'wrong-link.json'
            v4link.symlink_to(self.v4)
            argv=['--root',str(ROOT),'--v3tuv',str(self.v3),
                  '--v4pqr',str(v4link),'--out',str(temp/'no-output.json')]
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(argv),2)
            self.assertFalse((temp/'no-output.json').exists())


if __name__=='__main__':
    unittest.main()
