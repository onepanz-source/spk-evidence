"""V5-T3q bundled source-v0e causal credit and fail-closed research audit."""
from __future__ import annotations
from collections import Counter
from dataclasses import asdict
from functools import lru_cache
from spk_v5_research.island_c_owned_credit_v5t3h import ARMS,Measurement
from spk_v5_research.island_online_credit_v5t3i import packet_for,digest
from spk_v5_research.island_source_bv_bridge_v5t3o import evidence
from spk_v5_research.island_source_admission_v5t3p import SourceGatedPolicy
from spk_v5_research.island_regime_replay_v5t3j import generate,measurement_of,_conditions,actual_correct

SCHEMA='spk-v5-t3opq-source-custody-and-shared-resource-dual-replay/research-v0'
STAMPS=('2026-10-22 12:00:00','2026-10-22 12:01:00')


@lru_cache(maxsize=1)
def table():
    rows=[];status=Counter()
    for prev in (12,350):
      for now in (12,350):
       for co2 in (420,850,None):
        for arm in ARMS:
         for failure in ('none','no_C','no_marker','no_forward','no_reverse'):
          m=Measurement(*STAMPS,prev,now,co2 if failure!='no_C' else None,
                    sensor_visible=(co2 is not None and failure!='no_C'),
                    send_decision=failure!='no_marker',forward_enabled=failure!='no_forward',
                    reverse_enabled=failure!='no_reverse')
          r=evidence(m,arm)
          status[r['research_admission']]+=1
          a=r['dual_frozen_BV_v0e_source_passes']
          charged=sum(x['grant_count'] for x in a.values())
          rows.append({'context':f'{int(prev>=200)}{int(now>=200)}',
           'C_sensor':None if co2 is None else co2>=600,'arm':arm,'failure':failure,
           'T3h_status':r['A1b_T3h_status'],'BV_channel':r['mirrored_C_terminal'],
           'source_grants_charged':charged,'eligible':r['source_chain_C_to_B_to_A_valid'],
           'source_replay_digest':digest(r)})
    return rows,dict(sorted(status.items()))


@lru_cache(maxsize=32)
def cohort(seed=11,steps=120,stress=False):
    gated=SourceGatedPolicy(seed=seed+99)
    metrics=Counter();records=[]
    for idx,r in enumerate(generate(seed,per_regime=max(80,steps//3),pattern='shift')):
        if idx>=steps:break
        gated.settle_ready(idx)
        arm=gated.decide(f'{seed}:{idx}',r.previous_light,r.current_light,idx)
        conditions=_conditions(seed,idx,stress)
        m=measurement_of(r,sensor=conditions['sensor'],marker=conditions['marker'],
             forward=conditions['forward'],reverse=conditions['reverse'])
        p=packet_for(f'{seed}:{idx}',arm,m,idx,conditions['delay'])
        admitted=gated.submit(p)
        if p.packet_id in gated._policy.pending and conditions['registry_loss']:
            gated._policy.expire(p.packet_id,idx,'modeled_relay_loss')
            gated._receipts.pop(p.packet_id,None)
            gated._discards+=1
            admitted=False
        metrics['decisions']+=1
        metrics['source_admitted']+=int(admitted)
        metrics['C_proxy_correct']+=int(actual_correct(arm,r))
        records.append((idx,arm,p.witness['status'],admitted))
    gated.settle_ready(steps+7)
    # Pending packets may have arrived much earlier and expire; reject rather
    # than forcing an update at an arbitrary late evaluation time.
    state=gated.audit()
    return {'seed':seed,'stress':stress,'steps':steps,
       'observations':dict(sorted(metrics.items())),
       'registry':{'updates':state['registry']['updates'],
                   'discards':state['registry']['discarded'],
                   'head':state['registry']['head_sha256'],
                   'weights_sha256':digest(state['registry']['weights']),
                   'source_rejected':state['source_rejected_without_update'],
                   'pending':state['registry']['pending']},
       'episode_digest':digest(records)}


@lru_cache(maxsize=1)
def report():
    rows,counts=table()
    runs=[cohort(seed,120,stress) for seed in (11,29,47) for stress in (False,True)]
    assert all(r['registry']['updates']<=r['observations']['source_admitted'] for r in runs)
    assert all(r['registry']['pending']==0 for r in runs)
    return {'schema':SCHEMA,'status':'SOURCE_BV_V0E_DUAL_VERDICT_LINEAGE_WITH_SHADOW_LEARNING',
      'C_verdict_table':{'cases':len(rows),'counts':counts,
          'positive_verdicts':sum(x['BV_channel']==30 for x in rows),
          'negative_verdicts':sum(x['BV_channel']==31 for x in rows),
          'total_charged_native_source_grants':sum(x['source_grants_charged'] for x in rows),
          'rows_sha256':digest(rows)},
      'online_replay_runs':runs,
      'total_online_episodes':sum(r['steps'] for r in runs),
      'total_source_admitted':sum(r['observations']['source_admitted'] for r in runs),
      'total_credited_updates':sum(r['registry']['updates'] for r in runs),
      'claims_excluded':['dual BV-v0e source invocations per episode, not single native BV semantic channel',
        'source v0e ancestry follows C terminal mirror; original T3h routed verdict is a separate A1b channel',
        'terminal mirror/close-tick alignment are research program changes, not frozen Architecture changes',
        'host selects terminal observer after reading both passes: no native dynamic sign routing',
        'A1b source PE link timing is not the T3i host inter-episode delay',
        'C CO2 sensor threshold is host-prepared, not authenticated',
        'hash chain is not a signature, no hardware attestation',
        'registry is mutable Python and not a secure native learning primitive',
        'no blind independent goal-label evidence or independent policy usefulness claim']}
