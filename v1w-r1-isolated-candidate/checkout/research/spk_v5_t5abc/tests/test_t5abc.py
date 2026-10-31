"""T5ABC offline controls and actual fork-vs-frozen synthetic scheduler parity."""
import copy, importlib.util, json, sys, tempfile, types, unittest
from collections import Counter
from pathlib import Path
from research.spk_v5_t5abc import t5abc

ROOT=Path(__file__).resolve().parents[3]
FORK=ROOT/'research/spk_v5_t5abc/live_semantic_fork_v0.py'
FROZEN=ROOT/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'

def module_import_at(path, name):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s)
    sys.modules[name]=m
    s.loader.exec_module(m)
    return m

class FakeSchedulerEnv:
    def __enter__(self):
        names=('spk_architecture_v1','spk_backvalidation_v0',
         'spk_architecture_v1.pe_execution_v1b','spk_architecture_v1.temporal_transport_v1a',
         'spk_architecture_v1.temporal_service_v1b','spk_architecture_v1.causal_memory_v1c',
         'spk_architecture_v1.causal_transport_v1d','spk_backvalidation_v0.contract_v0')
        self.saved={n:sys.modules.get(n) for n in names}
        for n in names: sys.modules[n]=types.ModuleType(n)
        pe=sys.modules[names[2]]
        def _compute_local(node,state,timestamp,channels):
            raw,prev=state
            if timestamp<prev: raise ValueError('backward')
            counts=Counter(channels); guard=False; outs=[]
            for opcode,arg in node.instructions:
                if opcode=='ACC':raw+=arg[0]*counts[arg[1]]
                elif opcode=='CMP':guard=raw>=arg
                elif opcode=='EMIT' and guard:outs.append(arg)
                elif opcode=='RESET' and guard:raw=arg
                elif opcode=='SHIFT':raw>>=arg*(timestamp-prev)
            return raw,guard,tuple(outs)
        pe._compute_local=_compute_local
        pe._admit=lambda case,fabric: ({n.node_id:n for n in case.nodes},{'A':'pA','B':'pB','C':'pC'})
        sys.modules[names[3]]._admit_plan=lambda x:None
        sys.modules[names[4]]._valid_plan=lambda fabric,p:{p:4 for p in fabric.pe_ids}
        sys.modules[names[5]]._valid_memory=lambda fabric,plan: ({p:256 for p in fabric.pe_ids},{d:256 for d in 'PSEO'})
        sys.modules[names[5]]._reservation=lambda *a:[]
        sys.modules[names[6]]._valid_links=lambda x:None
        sys.modules[names[7]].digest=lambda x:t5abc.digest(x)
        self.fork=module_import_at(FORK,'scratch_t5abc_fork_test')
        self.frozen=module_import_at(FROZEN,'scratch_t5abc_frozen_test')
        return self
    def __exit__(self,*args):
        sys.modules.pop('scratch_t5abc_fork_test',None)
        sys.modules.pop('scratch_t5abc_frozen_test',None)
        for k,v in self.saved.items():
            if v is None: sys.modules.pop(k,None)
            else: sys.modules[k]=v

def workload(sign=1,with_parent=True):
    n=lambda id,in_ch,outs:types.SimpleNamespace(node_id=id,initial_raw=0,
        instructions=(('ACC',(1,in_ch)),('CMP',1)) + tuple(('EMIT',x) for x in outs))
    case=types.SimpleNamespace(nodes=(n('A',0,[1]),n('B',2,[3]),n('C',4,[11 if sign==1 else 12,30] if sign else [])),
        events=(types.SimpleNamespace(timestamp=10,node_id='A',channel=0),),edges=())
    r=lambda a,c,b,d:types.SimpleNamespace(source_node=a,source_channel=c,target_node=b,target_channel=d,
        source_pe='p'+a,target_pe='p'+b,delay_ticks=1)
    fabric=types.SimpleNamespace(pe_ids=('pA','pB','pC'),static_routes=(r('A',1,'B',2),r('B',3,'C',4)))
    args=(case,fabric,types.SimpleNamespace(max_inflight_occurrences=32,cross_pe_extra_ticks=0),
          types.SimpleNamespace(max_service_span_ticks=256,fabric_slots_per_tick=4),
          types.SimpleNamespace(max_service_span_ticks=256,fabric_slots_per_tick=768),
          types.SimpleNamespace(max_link_span_ticks=256,fabric_slots_per_tick=2,
                                link_slots_per_tick=2,max_outbox_per_pe=128))
    return args

class TestT5ABC(unittest.TestCase):
    def test_provenance_sha_literals(self):
        self.assertEqual(t5abc.T4ZABC_SHA,'7de3ccc8c374212748ccedcbd1a4b3d4e99f116b9a6f39e0190695a746cf9d4c')
        self.assertEqual(t5abc.FROZEN_SHA,'2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9')

    def test_reference_immutable(self):
        p=ROOT/'research/spk_v5_t5abc/reference/t4zabc-topology.json'
        j=t5abc.read_pinned(p,t5abc.T4ZABC_SHA,'TEST')
        self.assertEqual(j['BV_PE_C_computes'],312)
        self.assertEqual(j['BV_scheduler_entries'],180)

    def test_reference_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json'; p.write_text('{}')
            with self.assertRaisesRegex(t5abc.GateError,'SHA_DRIFT'):
                t5abc.read_pinned(p,t5abc.T4ZABC_SHA,'TEST')

    def test_fork_custody(self):
        if (ROOT/'spk_architecture_v1/pe_execution_v1b.py').is_file():
            d=t5abc.custodial_fork_check(ROOT)
            self.assertEqual(d['frozen_BV_sha256'],t5abc.FROZEN_SHA)

    def test_frozen_output_parity_and_semantic_hops(self):
        with FakeSchedulerEnv() as env:
            for sign in (1,-1,None):
                args=workload(sign)
                plan=env.fork.LiveBVPlanV0e(enabled=True,assessor='C',terminal_channel=30)
                frozen=env.frozen.execute_live_v0e(*args,bv=env.frozen.LiveBVPlanV0e(enabled=True,assessor='C',terminal_channel=30))
                fork=env.fork.execute_live_v0e(*args,bv=plan)
                self.assertEqual(t5abc.canon(t5abc.strip_experimental(fork)),t5abc.canon(frozen))
                expected=[('C','B'),('B','A')] if sign else []
                a=t5abc.check_port(fork,sign,expected)
                self.assertEqual(a['A_sign_receipts'],int(sign is not None))
                self.assertFalse(a['native_authentication'])

    def test_sign_flip_rejected(self):
        with FakeSchedulerEnv() as env:
            x=env.fork.execute_live_v0e(*workload(1),bv=env.fork.LiveBVPlanV0e(assessor='C',terminal_channel=30))
            x['experimental_semantic_port']['feedback_hops'][0]['sign']=-1
            with self.assertRaises(t5abc.GateError):
                t5abc.check_port(x,1,[('C','B'),('B','A')])

    def test_replayed_receipt_rejected(self):
        with FakeSchedulerEnv() as env:
            x=env.fork.execute_live_v0e(*workload(1),bv=env.fork.LiveBVPlanV0e(assessor='C',terminal_channel=30))
            x['experimental_semantic_port']['receiver_A_sign_receipts'].append(copy.deepcopy(x['experimental_semantic_port']['receiver_A_sign_receipts'][0]))
            with self.assertRaisesRegex(t5abc.GateError,'A_RECEIPT_COUNT_MISMATCH'):
                t5abc.check_port(x,1,[('C','B'),('B','A')])

    def test_missing_issuance_rejected(self):
        with FakeSchedulerEnv() as env:
            x=env.fork.execute_live_v0e(*workload(1),bv=env.fork.LiveBVPlanV0e(assessor='C',terminal_channel=30))
            x['experimental_semantic_port']['issuances']=[]
            with self.assertRaisesRegex(t5abc.GateError,'PE_C_ISSUANCE_COUNT_MISMATCH'):
                t5abc.check_port(x,1,[('C','B'),('B','A')])

    def test_host_auth_claim_rejected(self):
        with FakeSchedulerEnv() as env:
            x=env.fork.execute_live_v0e(*workload(1),bv=env.fork.LiveBVPlanV0e(assessor='C',terminal_channel=30))
            x['experimental_semantic_port']['native_origin_authenticated']=True
            with self.assertRaisesRegex(t5abc.GateError,'NATIVE_PROMOTION_FORBIDDEN'):
                t5abc.check_port(x,1,[('C','B'),('B','A')])

    def test_fork_semantic_executable_not_patched_original(self):
        s=FORK.read_text();o=FROZEN.read_text()
        self.assertIn('inherited_semantic',s)
        self.assertNotIn('inherited_semantic',o)
        self.assertIn("'experimental_semantic_port'",s)
        self.assertNotIn("'experimental_semantic_port'",o)

if __name__=='__main__': unittest.main()
