"""SPK V5-T3i, research-only online policy registry consuming verified T3h A1b credits.

This is deliberately NOT a native neuronal learning primitive. Decisions are
selected by a host-owned registry before constructing the next A1b CaseV0.
No label, C sensor value, future regime or counterfactual is an input to choose().
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
import random
from typing import Mapping
from spk_v5_research.island_c_owned_credit_v5t3h import (ARMS, Measurement, execute,
        verify_custody, CreditAdmissionError, LIGHT_THRESHOLD)

SCHEMA='spk-v5-t3ijk-verified-online-credit/research-v0'


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def digest(value):
    return sha256(canonical(value)).hexdigest()


def context_of(previous_light:float,current_light:float)->str:
    for v in (previous_light,current_light):
        if type(v) not in (int,float) or not __import__('math').isfinite(v) or v<0:
            raise CreditAdmissionError('invalid causal light context')
    return f'{int(previous_light>=LIGHT_THRESHOLD)}{int(current_light>=LIGHT_THRESHOLD)}'


@dataclass(frozen=True)
class CreditPacket:
    episode_id:str
    action:str
    measurement:Measurement
    witness:dict
    decision_step:int
    arrival_step:int
    packet_id:str


def packet_for(episode_id,action,measurement,decision_step,delay=0):
    """Reexecutes the complete A->B->C->B->A native A1b research case."""
    if type(episode_id) is not str or not episode_id or len(episode_id)>128:
        raise CreditAdmissionError('invalid unique episode ID')
    if type(decision_step) is not int or decision_step<0 or type(delay) is not int or not 0<=delay<=6:
        raise CreditAdmissionError('invalid decision step or bounded modeled delay')
    if action not in ARMS:
        raise CreditAdmissionError('unrecognized neural program')
    witness=execute(measurement,action)
    payload={'episode':episode_id,'action':action,'commit':witness['research_measurement_commit_sha256'],
             'decision_step':decision_step,'A_credit':witness['A_consumed_credit'],
             'A1b_proof':witness['A1b_emission_proof']}
    return CreditPacket(episode_id,action,measurement,witness,decision_step,
                        decision_step+1+delay,digest(payload))


class OnlinePolicy:
    """Bounded, deterministic recency-weighted contextual bandit. No native update.

    Non-overlapping epoch steps and reward covariance only for actually admitted
    packets. The account ledger has a hash chain to detect posthoc edits.
    """
    def __init__(self,seed=811,exploration=0.12,step_size=0.20,ttl=7):
        if type(seed) is not int or type(exploration) not in (float,int) or not 0<=exploration<=1:
            raise CreditAdmissionError('invalid selector configuration')
        if type(step_size) not in (float,int) or not 0<step_size<=1 or type(ttl) is not int or ttl<1:
            raise CreditAdmissionError('invalid bounded update or TTL')
        self.rng=random.Random(seed)
        self.exploration=float(exploration)
        self.step_size=float(step_size)
        self.ttl=ttl
        self.q={ctx:{a:0.0 for a in ARMS} for ctx in ('00','01','10','11')}
        self.counts={ctx:{a:0 for a in ARMS} for ctx in self.q}
        self.pending={}
        self.reserved={}
        self.issued=set()
        self.consumed=set()
        self.closed=set()
        self.ledger=[]
        self.head='0'*64
        self.updates=0
        self.forgery_rejections=0

    def _event(self,kind,fields):
        entry={'n':len(self.ledger),'kind':kind,**fields,'previous':self.head}
        self.head=digest(entry)
        self.ledger.append({'entry':entry,'sha256':self.head})

    def choose(self,previous_light,current_light)->str:
        """Only contemporaneously available light. In particular: NO C measurement."""
        ctx=context_of(previous_light,current_light)
        if self.rng.random()<self.exploration:
            return self.rng.choice(ARMS)
        q=self.q[ctx]
        return max(ARMS,key=lambda a:q[a])

    def decide(self,episode_id,previous_light,current_light,decision_step):
        if type(episode_id) is not str or not episode_id or len(episode_id)>128 or episode_id in self.reserved or episode_id in self.closed:
            raise CreditAdmissionError('replayed or invalid episode reservation')
        if type(decision_step) is not int or decision_step<0:
            raise CreditAdmissionError('invalid reservation step')
        ctx=context_of(previous_light,current_light)
        arm=self.choose(previous_light,current_light)
        self.reserved[episode_id]=(arm,ctx,decision_step)
        self._event('A_program_committed_before_C_sensor',{'episode':episode_id,'arm':arm,'ctx':ctx,'step':decision_step})
        return arm

    def register(self,packet:CreditPacket):
        if type(packet) is not CreditPacket or packet.packet_id in self.issued or packet.episode_id in self.closed:
            raise CreditAdmissionError('replayed, wrong-typed or reused decision')
        # Bind the paid A1b execution to the decision recorded BEFORE C was sampled.
        locked=self.reserved.get(packet.episode_id)
        if locked is None or locked!=(packet.action,context_of(packet.measurement.previous_light,
                   packet.measurement.current_light),packet.decision_step):
            raise CreditAdmissionError('uncommitted or swapped selected A program')
        # Verify source custody before *any* mutable state is changed.
        self._verify_packet(packet)
        self.issued.add(packet.packet_id)
        self.closed.add(packet.episode_id)
        self.reserved.pop(packet.episode_id)
        if packet.witness['status']=='C_authored_credit_delivered':
            self.pending[packet.packet_id]=packet
        self._event('decision',{'episode':packet.episode_id,'arm':packet.action,
                 'packet':packet.packet_id,'has_delivered_A_credit':packet.packet_id in self.pending})

    def _verify_packet(self,packet):
        if type(packet) is not CreditPacket or type(packet.decision_step) is not int or packet.decision_step<0:
            raise CreditAdmissionError('invalid packet envelope')
        if type(packet.arrival_step) is not int or not packet.decision_step+1<=packet.arrival_step<=packet.decision_step+7:
            raise CreditAdmissionError('forged or excessively delayed packet')
        if not verify_custody(packet.measurement,packet.action,packet.witness):
            raise CreditAdmissionError('invalid C-authored A1b witness')
        x={'episode':packet.episode_id,'action':packet.action,
           'commit':packet.witness['research_measurement_commit_sha256'],
           'decision_step':packet.decision_step,'A_credit':packet.witness['A_consumed_credit'],
           'A1b_proof':packet.witness['A1b_emission_proof']}
        if packet.packet_id!=digest(x):
            raise CreditAdmissionError('credit packet ownership drift')

    def settle(self,packet_id,current_step):
        if type(packet_id) is not str or type(current_step) is not int or current_step<0:
            raise CreditAdmissionError('invalid settlement identity/time')
        if packet_id not in self.pending or packet_id in self.consumed:
            raise CreditAdmissionError('no pending authentic delivered credit (replay)')
        packet=self.pending[packet_id]
        if current_step<packet.arrival_step or current_step>packet.arrival_step+self.ttl:
            raise CreditAdmissionError('early or expired credit cannot update')
        self._verify_packet(packet)
        reward=packet.witness['A_consumed_credit']
        if type(reward) is not int or reward not in (-1,1):
            raise CreditAdmissionError('credit not physically received at A')
        ctx=context_of(packet.measurement.previous_light,packet.measurement.current_light)
        old=self.q[ctx][packet.action]
        new=round((1-self.step_size)*old+self.step_size*reward,12)
        # Mutation occurs after all checks, exactly once.
        self.q[ctx][packet.action]=new
        self.counts[ctx][packet.action]+=1
        self.updates+=1
        self.pending.pop(packet_id)
        self.consumed.add(packet_id)
        self._event('C_credit_update',{'packet':packet_id,'ctx':ctx,'arm':packet.action,
                'reward':reward,'old':old,'new':new,'step':current_step})
        return reward

    def expire(self,packet_id,current_step,reason):
        if type(packet_id) is not str or packet_id not in self.pending or packet_id in self.consumed:
            raise CreditAdmissionError('invalid expiry or replay')
        if reason not in ('modeled_relay_loss','deadline_exceeded','shutdown_pending'):
            raise CreditAdmissionError('invalid discard reason')
        if type(current_step) is not int or current_step<self.pending[packet_id].decision_step:
            raise CreditAdmissionError('invalid expiry chronology')
        p=self.pending.pop(packet_id)
        self.consumed.add(packet_id)
        self._event('credit_discarded_NO_UPDATE',{'packet':packet_id,'reason':reason,'step':current_step})

    def audit(self):
        head='0'*64
        reconstructed={ctx:{a:0.0 for a in ARMS} for ctx in self.q}
        reconstructed_counts={ctx:{a:0 for a in ARMS} for ctx in self.q}
        for number,rec in enumerate(self.ledger):
            if rec['entry']['n']!=number or rec['entry']['previous']!=head or digest(rec['entry'])!=rec['sha256']:
                raise CreditAdmissionError('hash ledger drift')
            head=rec['sha256']
            ev=rec['entry']
            if ev['kind']=='C_credit_update':
                ctx,arm=ev['ctx'],ev['arm']
                if (ctx not in reconstructed or arm not in ARMS or ev['reward'] not in (-1,1) or
                      ev['old']!=reconstructed[ctx][arm]):
                    raise CreditAdmissionError('learning history is not replayable')
                next_q=round((1-self.step_size)*ev['old']+self.step_size*ev['reward'],12)
                if ev['new']!=next_q:raise CreditAdmissionError('forged learning weight transition')
                reconstructed[ctx][arm]=next_q
                reconstructed_counts[ctx][arm]+=1
        if reconstructed!=self.q or reconstructed_counts!=self.counts:
            raise CreditAdmissionError('mutable learned state differs from verified ledger')
        if head!=self.head or self.updates!=sum(x['entry']['kind']=='C_credit_update' for x in self.ledger):
            raise CreditAdmissionError('update count or ledger head drift')
        if self.updates!=sum(sum(v.values()) for v in self.counts.values()):
            raise CreditAdmissionError('weight counter inconsistency')
        return {'updates':self.updates,'head_sha256':head,'pending':len(self.pending),
                'decisions':len(self.closed),'discarded':sum(x['entry']['kind']=='credit_discarded_NO_UPDATE' for x in self.ledger),
                'weights':self.q,'updates_by_arm_context':self.counts}
