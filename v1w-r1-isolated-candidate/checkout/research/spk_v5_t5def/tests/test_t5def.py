"""Adversarial PE-scope research issuer tests; no claim of native C authority."""
import copy
from pathlib import Path
import sys
import unittest
from research.spk_v5_t5def import t5def
from research.spk_v5_t5abc import t5abc
from research.spk_v5_t5abc.tests.test_t5abc import FakeSchedulerEnv, workload, module_import_at

ROOT=Path(__file__).resolve().parents[3]
ISSUER=ROOT/'research/spk_v5_t5def/pe_semantic_issuer_v0.py'
FORK=ROOT/'research/spk_v5_t5def/live_pe_issuer_fork_v0.py'


class TestT5DEF(unittest.TestCase):
    def with_env(self):
        class Context:
            def __enter__(self1):
                self1.fake=FakeSchedulerEnv();env=self1.fake.__enter__()
                self1.originals={k:sys.modules.get(k) for k in (
                    'research.spk_v5_t5def.pe_semantic_issuer_v0',)}
                self1.issuer=module_import_at(ISSUER,'research.spk_v5_t5def.pe_semantic_issuer_v0')
                self1.fork=module_import_at(FORK,'scratch_t5def_fork_test')
                return env,self1.issuer,self1.fork
            def __exit__(self1,*args):
                sys.modules.pop('scratch_t5def_fork_test',None)
                for k,v in self1.originals.items():
                    if v is None:sys.modules.pop(k,None)
                    else:sys.modules[k]=v
                self1.fake.__exit__(*args)
        return Context()

    def test_frozen_sha_custody(self):
        x=t5def.check_custody(ROOT)
        self.assertEqual(x['T5ABC_fork_sha256'],t5def.T5ABC_FORK_SHA)
        self.assertEqual(x['frozen_PE_sha256'],t5abc.FROZEN_PE_SHA)

    def test_exact_reference_sha(self):
        p=ROOT/'research/spk_v5_t5def/reference/t5abc-semantic-transit.json'
        d=t5abc.read_pinned(p,t5def.REFERENCE_SHA,'T5ABC')
        self.assertEqual(d['in_scheduler_C_issuances'],72)

    def test_pe_issue_signs(self):
        with self.with_env() as (_,issuer,_fork):
            from types import SimpleNamespace
            for channel,sign in [(11,1),(12,-1)]:
                node=SimpleNamespace(node_id='C',instructions=(('ACC',(1,4)),('CMP',1),('EMIT',channel),('EMIT',30)))
                x=issuer.compute_and_issue(node,[0,0],14,[4],('r1',),3)
                self.assertEqual(x[-1].sign,sign)
                self.assertEqual(x[-1].source_channel,channel)
                self.assertEqual(x[-1].compute_batch,3)
                self.assertEqual(x[-1].to_packet()['causal_parents'],['r1'])

    def test_non_C_never_issues(self):
        with self.with_env() as (_,issuer,_fork):
            from types import SimpleNamespace
            node=SimpleNamespace(node_id='B',instructions=(('ACC',(1,4)),('CMP',1),('EMIT',11),('EMIT',30)))
            self.assertIsNone(issuer.compute_and_issue(node,[0,0],14,[4],('r1',),3)[-1])

    def test_no_semantic_channel_no_issuance(self):
        with self.with_env() as (_,issuer,_fork):
            from types import SimpleNamespace
            node=SimpleNamespace(node_id='C',instructions=(('ACC',(1,4)),('CMP',1),('EMIT',30)))
            self.assertIsNone(issuer.compute_and_issue(node,[0,0],14,[4],('r1',),3)[-1])

    def test_invalid_emission_channels(self):
        with self.with_env() as (_,issuer,_fork):
            from types import SimpleNamespace
            for outs in ([11,12,30],[11],[12]):
                node=SimpleNamespace(node_id='C',instructions=(('ACC',(1,4)),('CMP',1))+tuple(('EMIT',x) for x in outs))
                with self.assertRaises(issuer.PEIssuerRejected):
                    issuer.compute_and_issue(node,[0,0],14,[4],('r1',),3)

    def test_clock_and_parent_validations(self):
        with self.with_env() as (_,issuer,_fork):
            from types import SimpleNamespace
            node=SimpleNamespace(node_id='C',instructions=())
            for timestamp,batch,parents in [(-1,3,()),(0,0,()),(0,3,['r1']),(0,3,('r2','r1')),
                                              (0,3,('r1','r1')),(0,3,(0,)),(True,3,()),(0,False,())]:
                with self.subTest(timestamp=timestamp,batch=batch,parents=parents):
                    with self.assertRaises(issuer.PEIssuerRejected):
                        issuer.compute_and_issue(node,[0,0],timestamp,[],parents,batch)

    def test_synthetic_fork_matches_T5ABC_byte_exact(self):
        with self.with_env() as (env,issuer,fork):
            for sign in [1,-1,None]:
                args=workload(sign)
                plan=fork.LiveBVPlanV0e(enabled=True,assessor='C',terminal_channel=30)
                actual=fork.execute_live_v0e(*args,bv=plan)
                baseline=env.fork.execute_live_v0e(*args,bv=env.fork.LiveBVPlanV0e(enabled=True,assessor='C',terminal_channel=30))
                self.assertEqual(t5abc.canon(actual),t5abc.canon(baseline))
                self.assertEqual(t5abc.canon(t5abc.strip_experimental(actual)),
                                 t5abc.canon(env.frozen.execute_live_v0e(*args,bv=env.frozen.LiveBVPlanV0e(enabled=True,assessor='C',terminal_channel=30))))

    def test_missing_PE_type_rejected(self):
        with self.with_env() as (_,issuer,fork):
            original=fork.compute_and_issue
            def forged(node,*args):
                ret=original(node,*args)
                if node.node_id=='C' and ret[3] is not None:
                    return (*ret[:3],ret[3].to_packet())
                return ret
            fork.compute_and_issue=forged
            try:
                with self.assertRaisesRegex(fork.LiveBVRejected,'PE issuance type mismatch'):
                    fork.execute_live_v0e(*workload(1),bv=fork.LiveBVPlanV0e(assessor='C',terminal_channel=30))
            finally:fork.compute_and_issue=original

    def test_host_can_replay_cached_PE_result_no_C_compute(self):
        with self.with_env() as (_,issuer,fork):
            original=fork.compute_and_issue; cache=[];calls=[]
            def capture(node,*args):
                x=original(node,*args)
                if node.node_id=='C':cache.append(x)
                return x
            fork.compute_and_issue=capture
            try:
                x=fork.execute_live_v0e(*workload(1),bv=fork.LiveBVPlanV0e(assessor='C',terminal_channel=30))
                queue=iter(cache)
                def replay_without_C(node,*args):
                    if node.node_id=='C':
                        calls.append(node.node_id)
                        return next(queue)
                    return original(node,*args)
                fork.compute_and_issue=replay_without_C
                y=fork.execute_live_v0e(*workload(1),bv=fork.LiveBVPlanV0e(assessor='C',terminal_channel=30))
            finally:fork.compute_and_issue=original
            self.assertEqual(t5abc.canon(x),t5abc.canon(y))
            self.assertEqual(len(calls),len(cache))
            self.assertEqual(y['experimental_semantic_port']['receiver_A_sign_receipts'][0]['sign'],1)

    def test_native_promotion_still_rejected(self):
        with self.with_env() as (_,issuer,fork):
            x=fork.execute_live_v0e(*workload(1),bv=fork.LiveBVPlanV0e(assessor='C',terminal_channel=30))
            x['experimental_semantic_port']['native_origin_authenticated']=True
            with self.assertRaises(t5abc.GateError):
                t5abc.check_port(x,1,[('C','B'),('B','A')])

if __name__=='__main__':unittest.main()
