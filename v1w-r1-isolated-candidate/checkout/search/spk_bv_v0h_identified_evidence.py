"""SPK BV v0h deterministic independent-process re-execution and custody."""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from search.spk_24n_independent_oracle_v0 import EdgeV0
from spk_backvalidation_v0 import n_node_scheduler_v0f as base
from spk_backvalidation_v0 import identified_scheduler_v0h as new
from spk_backvalidation_v0.identified_audit_v0h import audit_identified_v0h,CausalAuditRejected
from spk_backvalidation_v0.context_aggregation_v0h import aggregate_context_v0h
from spk_backvalidation_v0.contract_v0 import canonical,digest,strict_loads
from tests.test_spk_bv_n_node_scheduler_v0f import plans_for

SCHEMA='spk-bv-identified-batch-contextual-evidence/v0h'
FROZEN='5af99cd1f4d603bf0c8e1557a6561c107765fdb5'


def normalize(result):
    r=deepcopy(result)
    r['schema']='baseline'
    for name,keys in [('batches',('batch_id',)),('emissions',('batch_id','emission_id')),
                      ('terminal',('batch_id','emission_id')),
                      ('occurrences',('batch_id','emission_id'))]:
        for row in r['forward'][name]:
            for key in keys:row.pop(key,None)
    for a in r['feedback']['assessments']:
        a.pop('batch_id',None);a.pop('terminal_emission_id',None)
    return r


def trial(name,layers,pe,events=(0,),congested=False,priority='forward-first',parallel=False,cyclic=False):
    case,_=base.layered_case_v0f(layers,events_at=events)
    terminal_channel=7
    if parallel:
        case=replace(case,edges=case.edges+case.edges)
    if cyclic:
        neurons=list(case.nodes)
        neurons[0]=replace(neurons[0],instructions=(('ACC',(1,0)),('SHIFT',1),('CMP',1),('EMIT',7),('RESET',0)))
        neurons[-1]=replace(neurons[-1],instructions=(('ACC',(1,0)),('CMP',1),('EMIT',7),('EMIT',8),('RESET',0)))
        case=replace(case,nodes=tuple(neurons),edges=case.edges+(
            EdgeV0(neurons[-1].node_id,7,neurons[0].node_id,0,1),))
        terminal_channel=8
    f=base.plan_n_v0f(case,pe)
    plans=plans_for(f,link=1 if congested else 8192,pe=2 if congested else 8192,
        fabric_pe=4 if congested else 8192,max_ticks=1024)
    flags=dict(assessors=(case.nodes[-1].node_id,),terminal_channel=terminal_channel,
        priority=priority,max_ticks=1024,max_packets=16384,max_occurrences=16384,
        max_batches=16384,max_events=16384,max_hops=128)
    old=base.execute_n_v0f(case,f,*plans,base.LiveBVPlanV0f(**flags))
    fresh=new.execute_identified_v0h(case,f,*plans,new.LiveBVPlanV0h(**flags))
    if normalize(old)!=normalize(fresh):
        raise CausalAuditRejected('batch ID instrumentation changed old scheduler behavior')
    audit=audit_identified_v0h(case,f,fresh,*plans)
    groups=aggregate_context_v0h(case,f,fresh,*plans)
    if audit['feedback_packets']!=groups['summary']['transport_packets']:
        raise CausalAuditRejected('feedback packet accounting differs')
    repeated=sum(n-1 for n in __import__('collections').Counter(
        (b['node'],b['tick']) for b in fresh['forward']['batches']).values() if n>1)
    return {'name':name,'neurons':len(case.nodes),'pes':pe,
            'same_neuron_tick_additional_batches':repeated,
            'batch_count':audit['batches'],'emission_count':audit['emissions'],
            'feedback_packets':audit['feedback_packets'],
            'unique_receiver_votes':audit['unique_receiver_votes'],
            'duplicate_path_receptions':audit['duplicate_path_receptions'],
            'runtime_sha256':digest(fresh),'context_sha256':groups['sha256']}


def capture():
    rows=[
        trial('diamond-one-pe',(1,2,1),1),
        trial('diamond-two-inlets',(1,2,1),4,events=(0,2)),
        trial('diamond-congested-forward',(1,2,1),4,events=(0,2),congested=True),
        trial('diamond-congested-feedback',(1,2,1),4,events=(0,2),congested=True,priority='feedback-first'),
        trial('resolved-ambiguous-same-tick',(1,2,2,1),1,events=(0,2),congested=True),
        trial('deep-convergence',(1,2,2,1),2,events=(0,2),congested=True,priority='feedback-first'),
        trial('parallel-routes',(1,1),2,parallel=True),
        trial('quiet-visited-cycle',(1,1,1,1),2,cyclic=True),
        trial('layered-24',(8,8,8),4),
        trial('layered-64',(16,16,16,16),8),
    ]
    by_name={x['name']:x for x in rows}
    if (by_name['resolved-ambiguous-same-tick']['same_neuron_tick_additional_batches']<=0 or
        by_name['layered-64']['feedback_packets']!=528 or
        by_name['layered-64']['unique_receiver_votes']!=33 or
        by_name['layered-64']['duplicate_path_receptions']!=495):
        raise CausalAuditRejected('required identity/convergence witnesses not present')
    return {'schema':SCHEMA,'frozen_commit':FROZEN,'witnesses':rows,
        'claims_excluded':['causal-credit attribution','statistical learning',
         'per-PE physical concurrency','automatic program change',
         'feedback-traffic compression','native A3d integration']}


def seal():
    data=capture()
    return canonical({'payload':data,'payload_sha256':digest(data)})


def verify(raw):
    x=strict_loads(raw)
    if (type(x) is not dict or set(x)!={'payload','payload_sha256'} or
        raw!=canonical(x) or digest(x['payload'])!=x['payload_sha256'] or raw!=seal()):
        raise CausalAuditRejected('identified-batch independent replay mismatch')
    rows=x['payload']['witnesses']
    big=next(x for x in rows if x['name']=='layered-64')
    ambiguous=next(x for x in rows if x['name']=='resolved-ambiguous-same-tick')
    return {'status':'IDENTIFIED_BATCH_CONTEXT_REPLAY_PASS',
        'evidence_sha256':digest(x),'witnesses':len(rows),
        'max_neurons':max(r['neurons'] for r in rows),
        'resolved_same_tick_extra_batches':ambiguous['same_neuron_tick_additional_batches'],
        'large_feedback_packets':big['feedback_packets'],
        'large_unique_receiver_votes':big['unique_receiver_votes'],
        'large_duplicate_path_receptions':big['duplicate_path_receptions'],
        'note':'research scheduler+read-only contextual aggregation; no credit or learning'}


def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--write');g.add_argument('--verify')
    args=p.parse_args()
    if args.write:
        path=Path(args.write);path.write_text(seal(),encoding='utf8')
        print(canonical({'status':'WRITTEN','file':path.name}))
    else:
        print(canonical(verify(Path(args.verify).read_text(encoding='utf8'))))

if __name__=='__main__':main()
