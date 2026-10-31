"""Deterministic independent-process BV v0g causal closure, pressure & replay."""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from search.spk_24n_independent_oracle_v0 import EdgeV0, execute_v0
from spk_backvalidation_v0.contract_v0 import canonical, digest, strict_loads
from spk_backvalidation_v0.n_node_scheduler_v0f import (
    LiveBVPlanV0f, layered_case_v0f, plan_n_v0f, execute_n_v0f,
)
from spk_backvalidation_v0.causal_audit_v0g import (
    CausalAuditRejected, audit_closed_v0g,
)
from tests.test_spk_bv_n_node_scheduler_v0f import plans_for

SCHEMA='spk-bv-causal-closure-stress-evidence/v0g'
FROZEN='5af99cd1f4d603bf0c8e1557a6561c107765fdb5'


def scenario(name,layers,*,pe,events=(0,),constrained=False,
             priority='forward-first',cyclic=False,parallel=False):
    case,_=layered_case_v0f(layers,events_at=events)
    terminal_channel=7
    if parallel:
        case=replace(case,edges=case.edges+case.edges)
    if cyclic:
        nodes=list(case.nodes)
        nodes[0]=replace(nodes[0],instructions=(('ACC',(1,0)),('SHIFT',1),
                    ('CMP',1),('EMIT',7),('RESET',0)))
        nodes[-1]=replace(nodes[-1],instructions=(('ACC',(1,0)),('CMP',1),
                    ('EMIT',7),('EMIT',8),('RESET',0)))
        case=replace(case,nodes=tuple(nodes),edges=case.edges+(
            EdgeV0(nodes[-1].node_id,7,nodes[0].node_id,0,1),))
        terminal_channel=8
    f=plan_n_v0f(case,pe)
    plans=plans_for(f,link=1 if constrained else 8192,
                    pe=2 if constrained else 8192,
                    fabric_pe=4 if constrained else 8192,max_ticks=1024)
    bv=LiveBVPlanV0f(assessors=(case.nodes[-1].node_id,),
          terminal_channel=terminal_channel,priority=priority,
          max_ticks=1024,max_packets=16384,max_occurrences=16384,
          max_batches=16384,max_events=16384,max_hops=128)
    r=execute_n_v0f(case,f,*plans,bv)
    audit=audit_closed_v0g(case,f,r,*plans)
    if not constrained:
        disabled=execute_n_v0f(case,f,*plans,replace(bv,enabled=False))
        oracle=execute_v0(case,max_batches=16384,max_events=16384)
        if (disabled['forward']['terminal']!=oracle['terminal_outputs'] or
            disabled['forward']['emissions']!=oracle['emissions']):
            raise CausalAuditRejected('uncongested forward execution not independent-oracle equal')
    return {'name':name,'neurons':len(case.nodes),'pes':pe,
            'edges':len(case.edges),'priority':priority,
            'constrained':constrained,'audit':audit,
            'forward_terminal_ticks':[x['timestamp'] for x in r['forward']['terminal']],
            'runtime_sha256':digest(r)}


def capture():
    rows = [
      scenario('diamond-one-pe',(1,2,1),pe=1),
      scenario('diamond-four-pe',(1,2,1),pe=4),
      scenario('diamond-contended-forward',(1,2,1),pe=4,constrained=True),
      scenario('diamond-contended-feedback',(1,2,1),pe=4,constrained=True,priority='feedback-first'),
      scenario('deep-convergence-forward',(1,2,2,1),pe=2,events=(0,2),constrained=True),
      scenario('deep-convergence-feedback',(1,2,2,1),pe=2,events=(0,2),constrained=True,priority='feedback-first'),
      scenario('quiet-visited-cycle',(1,1,1,1),pe=2,cyclic=True),
      scenario('parallel-route',(1,1),pe=2,parallel=True),
      scenario('layered-24',(8,8,8),pe=4),
      scenario('layered-64',(16,16,16,16),pe=8),
    ]
    by_name={r['name']:r for r in rows}
    d=by_name['diamond-four-pe']['audit']
    large=by_name['layered-64']['audit']
    if (d['duplicate_path_receptions']!=1 or
        d['unique_receiver_votes']!=3 or
        large['duplicate_path_receptions']<=0 or
        large['feedback_packets']<=large['unique_receiver_votes'] or
        by_name['diamond-contended-feedback']['forward_terminal_ticks']==
        by_name['diamond-contended-forward']['forward_terminal_ticks']):
        raise CausalAuditRejected('required convergent/control cost witness missing')
    # Explicitly capture the open provenance boundary rather than counting it
    # as CLOSED. Two source batches in one tick cannot be disambiguated by ID.
    case,_=layered_case_v0f((1,2,2,1),events_at=(0,2))
    f=plan_n_v0f(case,1)
    plans=plans_for(f,link=1,pe=2,fabric_pe=4,max_ticks=1024)
    run=execute_n_v0f(case,f,*plans,LiveBVPlanV0f(
          assessors=('N5',),max_ticks=1024,max_packets=16384,
          max_occurrences=16384,max_batches=16384,max_events=16384))
    try:
        audit_closed_v0g(case,f,run,*plans)
    except CausalAuditRejected as e:
        if 'batch identity ambiguity' not in str(e):
            raise
        denied='BATCH_IDENTITY_AMBIGUITY'
    else:
        raise CausalAuditRejected('ambiguous same-neuron tick accidentally certified')
    return {'schema':SCHEMA,'frozen_commit':FROZEN,'witnesses':rows,
            'provenance_boundary':denied,
            'claims_excluded':['counterfactual causal credit','global value truth',
              'statistical learning','automatic program rewrite','native A3d integration',
              'physical parallelism','complete N-neuron ISA conformance']}


def seal():
    payload=capture()
    return canonical({'payload':payload,'payload_sha256':digest(payload)})


def verify(raw):
    env=strict_loads(raw)
    if (type(env) is not dict or set(env)!={'payload','payload_sha256'} or
        canonical(env)!=raw or digest(env['payload'])!=env['payload_sha256'] or
        raw!=seal()):
        raise CausalAuditRejected('canonical source-backed evidence replay mismatch')
    rows=env['payload']['witnesses']
    big=next(x for x in rows if x['name']=='layered-64')['audit']
    return {'status':'CAUSAL_STRESS_REPLAY_PASS',
      'evidence_sha256':digest(env),'witnesses':len(rows),
      'max_neurons':max(x['neurons'] for x in rows),
      'large_feedback_packets':big['feedback_packets'],
      'large_unique_receiver_votes':big['unique_receiver_votes'],
      'large_duplicate_path_receptions':big['duplicate_path_receptions'],
      'provenance_boundary':env['payload']['provenance_boundary'],
      'note':'read-only checker over live research engine, NOT causal credit or learning'}


def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--write'); g.add_argument('--verify')
    a=p.parse_args()
    if a.write:
        path=Path(a.write)
        path.write_text(seal(),encoding='utf8')
        print(canonical({'status':'WRITTEN','file':path.name}))
    else:
        print(canonical(verify(Path(a.verify).read_text(encoding='utf8'))))


if __name__=='__main__':
    main()
