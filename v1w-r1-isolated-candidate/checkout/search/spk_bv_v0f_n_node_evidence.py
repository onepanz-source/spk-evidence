"""Deterministic source-backed replay of the variable-neuron BV research executor."""
from __future__ import annotations
import argparse
from dataclasses import replace
from pathlib import Path

from spk_backvalidation_v0.contract_v0 import canonical, digest, strict_loads
from spk_backvalidation_v0.n_node_scheduler_v0f import (
    LiveBVRejected, LiveBVPlanV0f, plan_n_v0f, layered_case_v0f, execute_n_v0f)
from search.spk_24n_independent_oracle_v0 import EdgeV0, execute_v0
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d

SCHEMA='spk-bv-n-node-live-evidence/v0f'
FROZEN='5af99cd1f4d603bf0c8e1557a6561c107765fdb5'


def plans(f, *, constrained=False):
    slots=1 if constrained else 8192
    return (TransportPlanV1a(0,16384),
            uniform_causal_service_plan_v1b(f,pe_slots=2 if constrained else 8192,
                  fabric_slots_per_tick=4 if constrained else 8192),
            uniform_causal_memory_plan_v1c(f,pe_slots=131072,
                  domain_slots=131072,fabric_slots_per_tick=131072),
            CausalLinkPlanV1d(link_slots_per_tick=slots,fabric_slots_per_tick=slots,
                  max_outbox_per_pe=8192))


def witness(name, case, pe_count, *, mapping=None, assessor=None,
            terminal_channel=7, constrained=False, priority='forward-first'):
    f=plan_n_v0f(case,pe_count,mapping=mapping)
    policy=LiveBVPlanV0f(priority=priority,
            assessors=() if assessor is None else (assessor,),
            terminal_channel=terminal_channel,max_ticks=1024,
            max_batches=8192,max_events=16384,max_occurrences=16384,max_packets=16384,
            max_hops=128)
    r=execute_n_v0f(case,f,*plans(f,constrained=constrained),policy)
    disabled=execute_n_v0f(case,f,*plans(f,constrained=constrained),
                           replace(policy,enabled=False))
    if not constrained:
        independent=execute_v0(case,max_batches=8192,max_events=16384)
        if (disabled['forward']['terminal']!=independent['terminal_outputs'] or
            disabled['forward']['emissions']!=independent['emissions'] or
            disabled['forward']['states']!={s['node_id']:s['raw'] for s in independent['states']}):
            raise LiveBVRejected('BV-disabled N-node execution not oracle-equivalent in admitted ideal case')
    if r['population']['neurons']!=len(case.nodes):
        raise LiveBVRejected('invalid N-node population')
    # A valid delivery must have a documented assessment/receiver pair.
    votes={(x['assessment_id'],x['receiver']) for x in r['feedback']['deliveries']}
    if len(votes)!=r['feedback']['unique_receiver_votes']:
        raise LiveBVRejected('feedback multi-path vote amplification')
    return {'name':name,'neurons':len(case.nodes),'pes':pe_count,
            'topology_edges':len(case.edges),'source_digest':digest(r),
            'bv_disabled_digest':digest(disabled),
            'terminal_ticks':[v['timestamp'] for v in r['forward']['terminal']],
            'cross_feedback_grants':r['resources']['bv_link_grants'],
            'local_feedback_grants':r['resources']['bv_local_sends'],
            'unique_receivers':r['feedback']['unique_receiver_votes'],
            'forward_emissions':len(r['forward']['emissions']),
            'scope':'contention-case' if constrained else 'ideal-independent-oracle-checked'}


def capture():
    base,_=layered_case_v0f((1,1,1,1),events_at=(0,))
    mix={'N0':'PE0','N1':'PE0','N2':'PE1','N3':'PE1'}
    wide,_=layered_case_v0f((8,8,8),events_at=(0,))
    large,_=layered_case_v0f((16,16,16,16),events_at=(0,))
    loop_nodes=list(base.nodes)
    loop_nodes[-1]=replace(loop_nodes[-1],instructions=(('ACC',(1,0)),('CMP',1),
            ('EMIT',7),('EMIT',8),('RESET',0)))
    loop=replace(base,nodes=tuple(loop_nodes),edges=base.edges+(EdgeV0('N3',7,'N0',1,1),))
    heavy,_=layered_case_v0f((1,1,1,1),events_at=(1,3))
    w=[witness('local-four',base,1,assessor='N3'),
       witness('mixed-four',base,2,mapping=mix,assessor='N3'),
       witness('spread-four',base,4,assessor='N3'),
       witness('cyclic-four',loop,2,assessor='N3',terminal_channel=8),
       witness('layered-24',wide,4,assessor='N23'),
       witness('layered-64',large,8,assessor='N63'),
       witness('contended-forward',heavy,2,assessor='N3',constrained=True),
       witness('contended-feedback',heavy,2,assessor='N3',constrained=True,
               priority='feedback-first')]
    c={x['name']:x for x in w}
    if not (c['local-four']['local_feedback_grants']==3 and
            c['mixed-four']['local_feedback_grants']==2 and
            c['mixed-four']['cross_feedback_grants']==1 and
            c['spread-four']['cross_feedback_grants']==3 and
            c['cyclic-four']['unique_receivers']==3 and
            c['contended-forward']['terminal_ticks']==[5,7] and
            c['contended-feedback']['terminal_ticks']==[5,10]):
        raise LiveBVRejected('required N-node admission, feedback, or contention witness absent')
    return {'schema':SCHEMA,'frozen_commit':FROZEN,'witnesses':w,
      'claims_excluded':['full A3d N-node equivalence','dynamic learning',
        'global causal credit','distributed physical clock',
        'hardware energy','full ISA conformance','hardware parallelism']}


def seal():
    data=capture()
    return canonical({'payload':data,'payload_sha256':digest(data)})


def verify(raw):
    env=strict_loads(raw)
    if (type(env) is not dict or set(env)!={'payload','payload_sha256'} or
        canonical(env)!=raw or digest(env['payload'])!=env['payload_sha256']):
        raise LiveBVRejected('noncanonical or forged N-node evidence')
    if raw!=seal():
        raise LiveBVRejected('independent source replay mismatch')
    cases=env['payload']['witnesses']
    return {'status':'N_NODE_LIVE_BV_REPLAY_PASS','evidence_sha256':digest(env),
            'witnesses':len(cases),'max_neurons':max(x['neurons'] for x in cases),
            'oracle_checked_uncongested':sum(x['scope'].startswith('ideal') for x in cases),
            'forward_first_terminal':next(x['terminal_ticks'] for x in cases if x['name']=='contended-forward'),
            'feedback_first_terminal':next(x['terminal_ticks'] for x in cases if x['name']=='contended-feedback'),
            'note':'new research engine; not A3d N-node conformance or learning'}


def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--write');g.add_argument('--verify')
    args=p.parse_args()
    if args.write:
        dst=Path(args.write);dst.write_text(seal(),encoding='utf-8')
        print(canonical({'status':'WRITTEN','file':dst.name}))
    else:
        print(canonical(verify(Path(args.verify).read_text(encoding='utf-8'))))

if __name__=='__main__':main()
