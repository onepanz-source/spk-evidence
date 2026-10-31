"""V5-T3l: paired-world impossibility witness for C-only feedback.

A and C execute unchanged frozen A1b instructions through T3h; the goal bit is
held by an *auditor* and never supplied to A, C, the selected program or the
research registry. Two worlds with indistinguishable observations/credits and
opposite hidden goals necessarily induce the same learning transcript.

Research-only. Constructed worlds are not fresh data or native SPK learning.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from typing import Literal
from spk_v5_research.island_online_credit_v5t3i import OnlinePolicy, packet_for, digest
from spk_v5_research.island_regime_replay_v5t3j import generate, measurement_of, _conditions
from spk_v5_research.island_c_owned_credit_v5t3h import CreditAdmissionError

SCHEMA='spk-v5-t3l-observationally-indistinguishable-goals/research-v0'


def replay(seed:int, per_regime:int, goal:Literal['C_aligned','C_inverted'], *, stress=False):
    if type(seed) is not int or type(per_regime) is not int or not 80<=per_regime<=500:
        raise ValueError('invalid bounded deterministic scenario')
    if goal not in ('C_aligned','C_inverted') or type(stress) is not bool:
        raise ValueError('unsupported auditor-only goal or stress type')
    agent=OnlinePolicy(seed=seed+99)
    events=[]
    score=Counter()
    for idx,row in enumerate(generate(seed,per_regime,'shift')):
        # Only delivered earlier C judgements influence the present selection.
        for pid,p in tuple(agent.pending.items()):
            if p.arrival_step<=idx:
                try:agent.settle(pid,idx)
                except CreditAdmissionError:
                    if idx>p.arrival_step+agent.ttl:agent.expire(pid,idx,'deadline_exceeded')
                    else:raise
        arm=agent.decide(f'paired:{seed}:{idx}',row.previous_light,row.current_light,idx)
        conditions=_conditions(seed,idx,stress)
        m=measurement_of(row,sensor=conditions['sensor'],marker=conditions['marker'],
                         forward=conditions['forward'],reverse=conditions['reverse'])
        packet=packet_for(f'paired:{seed}:{idx}',arm,m,idx,conditions['delay'])
        agent.register(packet)
        if packet.packet_id in agent.pending and conditions['registry_loss']:
            agent.expire(packet.packet_id,idx,'modeled_relay_loss')
        # Auditor-only, applied AFTER register and A1b execution.
        predicted=packet.witness['A_light_decision']
        external_goal=row.c_reference if goal=='C_aligned' else not row.c_reference
        score['correct']+=predicted==external_goal
        score['total']+=1
        score['delivered']+=packet.witness['status']=='C_authored_credit_delivered'
        score['goal_positive']+=external_goal
        # Deliberately exclude external_goal from evidence digest and registry.
        events.append((idx,row.previous_stamp,row.current_stamp,arm,
                       packet.packet_id,packet.witness['status'],
                       packet.witness['A_consumed_credit'],predicted))
    end=len(events)
    for pid,p in tuple(agent.pending.items()):
        if p.arrival_step<=end+agent.ttl:agent.settle(pid,max(end,p.arrival_step))
        else:agent.expire(pid,end,'shutdown_pending')
    audit=agent.audit()
    assert audit['pending']==0
    return {'schema':SCHEMA,'goal':goal,'stress':stress,'seed':seed,
        'total':score['total'],'correct':score['correct'],'incorrect':score['total']-score['correct'],
        'goal_positive':score['goal_positive'],'C_delivered':score['delivered'],
        'C_credit_updates':audit['updates'],'A_action_and_C_credit_digest':digest(events),
        'A_registry_head_sha256':audit['head_sha256'],
        'A_registry_weights_sha256':digest(audit['weights'])}


def paired_worlds(seed=29,per_regime=120,*,stress=True):
    aligned=replay(seed,per_regime,'C_aligned',stress=stress)
    inverted=replay(seed,per_regime,'C_inverted',stress=stress)
    assert aligned['total']==inverted['total']
    for key in ('A_action_and_C_credit_digest','A_registry_head_sha256',
                'A_registry_weights_sha256','C_credit_updates','C_delivered'):
        assert aligned[key]==inverted[key],key
    assert aligned['correct']+inverted['correct']==aligned['total']
    return {'schema':SCHEMA,'status':'INDISTINGUISHABLE_FEEDBACK_OPPOSITE_OBJECTIVE',
        'seed':seed,'stress':stress,'episodes_per_world':aligned['total'],
        'identical_A_actions_C_credit_and_updates':True,
        'aligned_world':aligned,'inverted_world':inverted,
        'goal_is_auditor_only':True,'no_native_learning':True}
