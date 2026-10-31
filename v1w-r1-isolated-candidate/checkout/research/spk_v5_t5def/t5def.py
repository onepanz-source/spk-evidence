"""T5DEF: PE-scope semantics in additive fork; strict T5ABC parity and host-forgery witness."""
import argparse
from collections import Counter
import difflib
import json
from pathlib import Path
from hashlib import sha256

from research.spk_v5_t5abc import t5abc

SCHEMA='spk-v5-t5def-pe-scope-issuer/research-v0'
STATUS='PE_SCOPE_ISSUER_TRANSPORT_PARITY_HOST_REBINDABLE_NOT_NATIVE'
REFERENCE_SHA='17416abffffd0c959eb79df32e4fc397eda014a0ba9986ef20f38fb1a9798872'
T5ABC_FORK_SHA='3b75d21cd14ecf4262234646a1247ac568e2c26be9d67fd640e4d7eb169201c1'

class GateError(ValueError):pass

def need(cond,code):
    if not cond:raise GateError(code)

def file_hash(p):return sha256(Path(p).read_bytes()).hexdigest()

def check_custody(root):
    root=Path(root)
    old=root/'research/spk_v5_t5abc/live_semantic_fork_v0.py'
    new=root/'research/spk_v5_t5def/live_pe_issuer_fork_v0.py'
    patch=root/'research/spk_v5_t5def/FORK_DIFF.patch'
    emitter=root/'research/spk_v5_t5def/pe_semantic_issuer_v0.py'
    need(file_hash(old)==T5ABC_FORK_SHA,'ORIGINAL_T5ABC_FORK_SHA_DRIFT')
    need(file_hash(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==t5abc.FROZEN_SHA,
         'FROZEN_BV_SHA_DRIFT')
    need(file_hash(root/'spk_architecture_v1/pe_execution_v1b.py')==t5abc.FROZEN_PE_SHA,
         'FROZEN_PE_SHA_DRIFT')
    diff=''.join(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),
       fromfile='research/spk_v5_t5abc/live_semantic_fork_v0.py',
       tofile='research/spk_v5_t5def/live_pe_issuer_fork_v0.py'))
    need(diff==patch.read_text(),'EXPERIMENTAL_FORK_DIFF_SHA_DRIFT')
    for forbidden in ('native_origin_authenticated\':True','native_receiver_semantic_credit\':True'):
        need(forbidden not in new.read_text(),'FORBIDDEN_NATIVE_PROMOTION')
    need('from spk_architecture_v1.pe_execution_v1b import _compute_local' in emitter.read_text(),
         'PE_SCOPE_COMPUTE_BINDING_MISSING')
    return {'T5ABC_fork_sha256':T5ABC_FORK_SHA,'experimental_fork_sha256':file_hash(new),
       'PE_issuer_sha256':file_hash(emitter),'fork_diff_sha256':file_hash(patch),
       'frozen_PE_sha256':t5abc.FROZEN_PE_SHA,'frozen_BV_sha256':t5abc.FROZEN_SHA}


def run_fork_source(m,arm):
    from research.spk_v5_t4def import t4def
    from spk_v5_research.island_c_owned_credit_v5t3h import build_case
    from spk_architecture_v1.pe_fabric_v1a import plan_v1a
    from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
    from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
    from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
    from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
    from research.spk_v5_t5def.live_pe_issuer_fork_v0 import execute_live_v0e, LiveBVPlanV0e
    case=t4def.fixed_terminal_case(m,arm,build_case)
    fabric=plan_v1a(case,'spread')
    return execute_live_v0e(case,fabric,TransportPlanV1a(0,16),
        uniform_causal_service_plan_v1b(fabric,pe_slots=3,fabric_slots_per_tick=4),
        uniform_causal_memory_plan_v1c(fabric,pe_slots=256,domain_slots=256,fabric_slots_per_tick=768),
        CausalLinkPlanV1d(link_slots_per_tick=2,fabric_slots_per_tick=2,max_outbox_per_pe=128,max_link_span_ticks=256),
        LiveBVPlanV0e(enabled=True,priority='forward-first',assessor='C',terminal_channel=30,max_ticks=256))


def host_rebind_witness(m, arm, expected_row):
    """Constructive attack: same source-looking BV result without running C on replay.

    This models a host empowered to rebind Python imports; it is not a remote attacker.
    """
    from research.spk_v5_t5def import live_pe_issuer_fork_v0 as fork
    original=fork.compute_and_issue
    cache=[]; calls=Counter()
    def capture(node,*args):
        result=original(node,*args)
        if node.node_id=='C':cache.append(result)
        return result
    try:
        fork.compute_and_issue=capture
        first=run_fork_source(m,arm)
        need(len(cache)>=1,'HOST_WITNESS_NO_C_COMPUTE')
        seq=iter(cache)
        def cached_without_C(node,*args):
            if node.node_id=='C':
                calls['C_cache_substitutions']+=1
                return next(seq)
            return original(node,*args)
        fork.compute_and_issue=cached_without_C
        second=run_fork_source(m,arm)
    finally:
        fork.compute_and_issue=original
    need(calls['C_cache_substitutions']==len(cache),'HOST_WITNESS_C_SUBSTITUTION_COUNT_DRIFT')
    need(t5abc.canon(first)==t5abc.canon(second),'HOST_WITNESS_REPLAY_DIVERGED')
    need(t5abc.digest(t5abc.strip_experimental(second))==expected_row['source_sha256'],
         'HOST_WITNESS_FROZEN_PARITY_DRIFT')
    need(t5abc.digest(second['experimental_semantic_port'])==expected_row['experimental_port_sha256'],
         'HOST_WITNESS_PORT_PARITY_DRIFT')
    return {'C_PE_compute_calls_in_replay':0,'C_cached_substitutions':len(cache),
       'same_scheduler_and_semantic_result_bytes':True,'native_origin_authentication_falsified':True}


def run(root):
    from research.spk_v5_t4def import t4def
    from research.spk_v5_t5def import live_pe_issuer_fork_v0 as fork
    root=Path(root); pins=check_custody(root)
    ref=t5abc.read_pinned(root/'research/spk_v5_t5def/reference/t5abc-semantic-transit.json',
                           REFERENCE_SHA,'T5ABC_REFERENCE')
    need(ref['fork_BV_calls']==180 and len(ref['rows'])==180 and
         ref['in_scheduler_C_issuances']==72 and ref['A_received_sign_messages']==72 and
         ref['host_can_forge_runtime'] is True,'T5ABC_RESEARCH_REFERENCE_INVALID')
    # Reuse T5ABC source custody and report oracle, without running frozen BV.
    basepins=t5abc.custodial_fork_check(root)
    need(basepins['experimental_fork_sha256']==T5ABC_FORK_SHA,'T5ABC_CUSTODY_INVALID')
    originals=fork.compute_and_issue
    counts=Counter()
    def instrumented(node,*args):
        result=originals(node,*args)
        counts['all_PE_steps']+=1
        if node.node_id=='C':counts['C_PE_steps']+=1
        if result[3] is not None:counts['C_PE_scope_issuances']+=1
        return result
    rows=[]
    try:
        fork.compute_and_issue=instrumented
        for idx,((meta,m,arm),old) in enumerate(zip(t4def.table_cases(),ref['rows'])):
            need(idx==old['index'],'CASE_INDEX_DRIFT_'+str(idx))
            res=run_fork_source(m,arm)
            need(t5abc.digest(t5abc.strip_experimental(res))==old['source_sha256'],
                 'ORIGINAL_OUTPUT_PARITY_FAIL_'+str(idx))
            # T5ABC's entire semantic port must be byte-equivalent as well.
            need(t5abc.digest(res['experimental_semantic_port'])==old['experimental_port_sha256'],
                 'SEMANTIC_PORT_PARITY_FAIL_'+str(idx))
            port=res['experimental_semantic_port']
            need(len(port['issuances'])==old['C_issuance_count'] and
                 len(port['feedback_hops'])==old['semantic_hops'] and
                 len(port['receiver_A_sign_receipts'])==old['A_receipt_count'],
                 'SEMANTIC_REPORT_COUNTS_DRIFT_'+str(idx))
            need(port['host_can_forge'] is True and port['native_origin_authenticated'] is False and
                 port['native_receiver_semantic_credit'] is False and port['native_learning'] is False,
                 'NATIVE_PROMOTION_FORBIDDEN')
            rows.append({'index':idx,'source_sha256':old['source_sha256'],
                         'port_sha256':old['experimental_port_sha256'],
                         'C_PE_issued':len(port['issuances']),
                         'A_received':len(port['receiver_A_sign_receipts']),
                         'guard_only':old['guard_only_not_native_credit'],
                         'native_credit':False})
    finally:
        fork.compute_and_issue=originals
    need(len(rows)==180 and counts['all_PE_steps']==1002 and counts['C_PE_steps']==312 and
         counts['C_PE_scope_issuances']==72 and sum(x['A_received'] for x in rows)==72 and
         sum(x['guard_only'] for x in rows)==24,'PE_COMPUTATION_TOPOLOGY_DRIFT')
    cases=list(t4def.table_cases())
    witness=host_rebind_witness(cases[0][1],cases[0][2],ref['rows'][0])
    need(check_custody(root)==pins,'CUSTODY_CHANGED_DURING_RUN')
    return {'schema':SCHEMA,'status':STATUS,'T5ABC_reference_sha256':REFERENCE_SHA,
       'pins':pins,'frozen_source_calls':0,'experimental_fork_cases':180,
       'PE_scope_compute_steps':counts['all_PE_steps'],
       'C_PE_compute_steps':counts['C_PE_steps'],
       'PE_scope_sign_issuances':counts['C_PE_scope_issuances'],
       'A_sign_receipts':sum(x['A_received'] for x in rows),
       'semantic_hops':sum(x['C_PE_issued']*2 for x in rows),
       'research_guard_only_cases':sum(x['guard_only'] for x in rows),
       'all_180_frozen_and_T5ABC_port_sha_parity':True,
       'host_rebind_forgery_witness':witness,
       'rows_sha256':t5abc.digest(rows),'rows':rows,
       'host_can_forge_runtime':True,'native_neuron_origin_authenticated':False,
       'native_semantic_BV_proven':False,'native_learning_proven':False,
       'promotion_allowed':False,
       'limits':['C descriptors originate in a PE-scope Python research wrapper, not frozen PE v1b itself',
         'The wrapper invokes frozen _compute_local but Python host can substitute cached result',
         'PE wrapper is imported by COPIED scheduler fork; not silicon-bound or independently authenticated',
         'Equivalent scheduler and semantic output can be forged by privileged host on cached PE C result',
         'One simulated single clock; no independently authenticated sensor, native BV credit or learning']}


def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    args=a.parse_args()
    try:
        t5abc.need(not args.out.exists(),'OUTPUT_ALREADY_EXISTS')
        d=run(args.root)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_bytes(json.dumps(d,indent=2,sort_keys=True,allow_nan=False).encode()+b'\n')
        print('T5DEF',d['status'],'PE steps',d['PE_scope_compute_steps'],
              'C steps',d['C_PE_compute_steps'],'A receipts',d['A_sign_receipts'],
              'HOST REBIND STILL POSSIBLE')
        print('sha256',file_hash(args.out))
    except (GateError,t5abc.GateError,ValueError,KeyError,TypeError,ImportError,OSError,AssertionError,StopIteration) as e:
        raise SystemExit('T5DEF FAIL CLOSED: '+str(e))

if __name__=='__main__':main()
