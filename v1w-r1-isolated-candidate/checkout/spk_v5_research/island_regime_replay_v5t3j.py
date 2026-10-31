"""SPK V5-T3j. Deterministic engineered distribution shifts and negative controls.

All reward judgments genuinely originate from the frozen A1b C program in T3h;
this harness is *synthetic* and C's proxy itself is planted by the simulator.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from dataclasses import dataclass
from datetime import datetime,timedelta
from hashlib import sha256
import random
from spk_v5_research.island_online_credit_v5t3i import (OnlinePolicy,packet_for,canonical,
         digest,context_of)
from spk_v5_research.island_c_owned_credit_v5t3h import (ARMS,Measurement,execute,
         CreditAdmissionError)

SCHEMA='spk-v5-t3ijk-regime-adversarial-replay/research-v0'
REGIMES=('C_follows_current','C_mostly_quiet','C_follows_persistence')

@dataclass(frozen=True)
class Reading:
    previous_stamp:str
    current_stamp:str
    previous_light:float
    current_light:float
    c_reference:bool
    regime:str
    # Hidden auditor-only reference is deliberately not passed to selector.


def generate(seed:int,per_regime=400,pattern="shift"):
    if type(seed) is not int or type(per_regime) is not int or per_regime<80:
        raise ValueError('invalid controlled replay settings')
    if pattern not in ('shift','stationary_current','uninformative_coin','rapid_switch'):
        raise ValueError('unsupported experimental regime')
    rng=random.Random(seed)
    base=datetime(2026,11,1,0,0,0)
    for idx in range(per_regime*len(REGIMES)):
        stage=idx//per_regime if pattern=='shift' else (idx//7)%3 if pattern=='rapid_switch' else 0
        before=rng.random()<0.55
        now=before if rng.random()<0.63 else not before
        # The proxy rule *changes* on hidden stage boundaries, not revealed to A.
        target=(now if stage==0 else False if stage==1 else before and now)
        if pattern=='uninformative_coin':target=rng.random()<0.5
        elif rng.random()<0.04:target=not target
        gap=(59,60,61)[idx%3]
        t=base+timedelta(minutes=idx)
        yield Reading(t.strftime('%Y-%m-%d %H:%M:%S'),
              (t+timedelta(seconds=gap)).strftime('%Y-%m-%d %H:%M:%S'),
              350.0 if before else 12.0,350.0 if now else 12.0,
              bool(target),('C_uninformative' if pattern=='uninformative_coin' else REGIMES[stage]))


def measurement_of(e:Reading,*,sensor=True,marker=True,forward=True,reverse=True):
    return Measurement(e.previous_stamp,e.current_stamp,e.previous_light,e.current_light,
      850.0 if e.c_reference else 420.0,sensor_visible=sensor,
      send_decision=marker,forward_enabled=forward,reverse_enabled=reverse)


class PlaceboSelector:
    """A matched learning rule trained on unrelated random coins, never T3h credits."""
    def __init__(self,seed):
        self.rng=random.Random(seed)
        self.coin=random.Random(seed+33823)
        self.q={ctx:{a:0.0 for a in ARMS} for ctx in ('00','01','10','11')}
        self.updates=0
    def choose(self,prev,cur):
        ctx=context_of(prev,cur)
        if self.rng.random()<0.12:return self.rng.choice(ARMS)
        return max(ARMS,key=lambda a:self.q[ctx][a])
    def feed_unrelated_coin(self,prev,cur,arm):
        ctx=context_of(prev,cur)
        r=1 if self.coin.random()<0.5 else -1
        old=self.q[ctx][arm]
        self.q[ctx][arm]=round(.8*old+.2*r,12)
        self.updates+=1
        return r


def actual_correct(action,e:Reading):
    current=e.current_light>=200.0
    prev=e.previous_light>=200.0
    emit=(action=='current' and current) or (action=='persist' and prev and current)
    return emit==e.c_reference


def _conditions(seed,idx,stress):
    if not stress:return {'sensor':True,'marker':True,'forward':True,'reverse':True,
                         'delay':0,'registry_loss':False}
    rng=random.Random((seed+19)*100003+idx*67)
    return {'sensor':rng.random()>=0.07,'marker':rng.random()>=0.03,
            'forward':rng.random()>=0.045,'reverse':rng.random()>=0.13,
            'delay':rng.randint(0,3),'registry_loss':rng.random()<0.055}


def _summary(items):
    counts=Counter(x['regime'] for x in items)
    out={}
    for arm in ('learned','placebo','random','current','persist','silent'):
        out[arm]={'correct':sum(x[arm] for x in items),'total':len(items),
                  'accuracy':round(sum(x[arm] for x in items)/len(items),6)}
    out['regimes']={r:{'total':counts[r],'learned_correct':sum(x['learned'] for x in items if x['regime']==r),
                   'fixed_current_correct':sum(x['current'] for x in items if x['regime']==r),
                   'fixed_persist_correct':sum(x['persist'] for x in items if x['regime']==r),
                   'fixed_silent_correct':sum(x['silent'] for x in items if x['regime']==r),
                   'placebo_correct':sum(x['placebo'] for x in items if x['regime']==r)} for r in sorted(counts)}
    return out


def trial(seed=29,per_regime=400,stress=False,simulate_fixed_in_a1b=True,pattern='shift'):
    """Exogenous engineered stream. Source decisions have no access to C's future.
    Delays apply to host research policy registry, NOT native A1b link timing.
    """
    agent=OnlinePolicy(seed=seed+99)
    placebo=PlaceboSelector(seed+99)
    random_arm=random.Random(seed+911)
    episodes=[];outcomes=[];stats=Counter()
    for idx,e in enumerate(generate(seed,per_regime,pattern)):
        # Only credits previously made ready may affect the next policy decision.
        for pid,p in tuple(agent.pending.items()):
            if p.arrival_step<=idx:
                try:agent.settle(pid,idx)
                except CreditAdmissionError:
                    if idx>p.arrival_step+agent.ttl:agent.expire(pid,idx,'deadline_exceeded')
                    else:raise
        arm=agent.decide(f'{seed}:{idx}',e.previous_light,e.current_light,idx)
        placebo_arm=placebo.choose(e.previous_light,e.current_light)
        random_choice=random_arm.choice(ARMS)
        condition=_conditions(seed,idx,stress)
        # C's sensor is materialized ONLY after A's choice was committed.
        m=measurement_of(e,sensor=condition['sensor'],marker=condition['marker'],
                         forward=condition['forward'],reverse=condition['reverse'])
        packet=packet_for(f'{seed}:{idx}',arm,m,idx,condition['delay'])
        agent.register(packet)
        status=packet.witness['status'];stats[status]+=1
        if packet.packet_id in agent.pending and condition['registry_loss']:
            agent.expire(packet.packet_id,idx,'modeled_relay_loss')
            stats['modeled_relay_loss']+=1
        # Placebo comparator is outside the authenticated receipt registry.
        placebo.feed_unrelated_coin(e.previous_light,e.current_light,placebo_arm)
        fixed_result={}
        for a in ARMS:
            if simulate_fixed_in_a1b:
                fixed=execute(measurement_of(e),a)
                if fixed['status']!='C_authored_credit_delivered':
                    raise AssertionError('fixed A1b custody unexpectedly missing')
                fixed_result[a]=fixed['A_consumed_credit']==1
                if fixed_result[a]!=actual_correct(a,e):
                    raise AssertionError('A1b fixed arm disagrees with auditor truth')
            else:fixed_result[a]=actual_correct(a,e)
        if packet.witness['A_light_decision']!=((arm=='current' and e.current_light>=200) or
              (arm=='persist' and e.previous_light>=200 and e.current_light>=200)):
            raise AssertionError('A1b emitted wrong chosen program')
        episodes.append({'idx':idx,'regime':e.regime,'action':arm,'context':context_of(e.previous_light,e.current_light),
                         'status':status,'A_consumed_credit':packet.witness['A_consumed_credit'],
                         'A_authored_conclusion_delivered':status=='C_authored_credit_delivered',
                         'A_effective_feedback_applied_later':packet.packet_id in agent.pending,
                         'packet':packet.packet_id})
        outcomes.append({'regime':e.regime,'learned':actual_correct(arm,e),
          'placebo':actual_correct(placebo_arm,e),'random':actual_correct(random_choice,e),
          **fixed_result})
    # Settle only eligible late credits that were already authored, never future evidence.
    n=len(outcomes)
    for pid,p in tuple(agent.pending.items()):
        if p.arrival_step<=n+agent.ttl:agent.settle(pid,max(n,p.arrival_step))
        else:agent.expire(pid,n,'shutdown_pending')
    audit=agent.audit()
    if audit['pending']!=0 or audit['updates']+audit['discarded']!=stats['C_authored_credit_delivered']:
        raise AssertionError('each delivered signed A credit must settle or expire once')
    summary=_summary(outcomes)
    return {'schema':SCHEMA,'seed':seed,'per_regime':per_regime,'pattern':pattern,'stress':bool(stress),
      'summaries':summary,'source_executions':len(outcomes)*(4 if simulate_fixed_in_a1b else 1),
      'observed_C_origin_statuses':dict(sorted(stats.items())),
      'C_paid_research_A1b_replay_sha256':digest(episodes),
      'policy_registry':audit,
      'episodes':episodes}
