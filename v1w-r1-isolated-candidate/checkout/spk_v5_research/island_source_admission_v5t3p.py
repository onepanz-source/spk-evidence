"""V5-T3p research shadow admission. A host registry can settle only after
independent A1b and source BV-v0e *dual replay* eligibility checks.

This is NOT a native BV authorization contract, signed sensor, or secure enclave.
An attacker controlling Python objects/code can bypass this reference wrapper.
"""
from __future__ import annotations
from dataclasses import dataclass,replace
from spk_v5_research.island_online_credit_v5t3i import (OnlinePolicy,packet_for,
    CreditPacket,digest)
from spk_v5_research.island_c_owned_credit_v5t3h import (Measurement, CreditAdmissionError)
from spk_v5_research.island_source_bv_bridge_v5t3o import evidence,verify_evidence

SCHEMA='spk-v5-t3opq-source-gated-credit-registry/research-v0'

@dataclass(frozen=True)
class SourceReceipt:
    episode_id:str
    packet_id:str
    arm:str
    decision_step:int
    measurement_hash:str
    source_evidence:dict
    commitment_hash:str


def receipt_for(packet:CreditPacket):
    witness=evidence(packet.measurement,packet.action)
    body={'episode':packet.episode_id,'packet':packet.packet_id,'arm':packet.action,
          'step':packet.decision_step,'measurement':digest(__import__('dataclasses').asdict(packet.measurement)),
          'source_evidence_sha256':digest(witness)}
    return SourceReceipt(packet.episode_id,packet.packet_id,packet.action,packet.decision_step,
                         body['measurement'],witness,digest(body))


def verify_receipt(packet,receipt):
    if type(packet) is not CreditPacket or type(receipt) is not SourceReceipt:
        raise CreditAdmissionError('untyped source receipt')
    expected=receipt_for(packet)
    if receipt!=expected:
        raise CreditAdmissionError('source BV custody report forged, reordered, or replaced')
    verify_evidence(packet.measurement,packet.action,receipt.source_evidence)
    return receipt.source_evidence['source_chain_C_to_B_to_A_valid']


class SourceGatedPolicy:
    def __init__(self,seed=811):
        self._policy=OnlinePolicy(seed=seed)
        self._receipts={}
        self._settled=set()
        self._rejects=0
        self._discards=0
    def decide(self,episode_id,previous_light,current_light,step):
        return self._policy.decide(episode_id,previous_light,current_light,step)
    def submit(self,packet,claimed_receipt=None):
        # NO state mutation before complete source replay (both v0e passes).
        receipt=receipt_for(packet) if claimed_receipt is None else claimed_receipt
        allowed=verify_receipt(packet,receipt)
        self._policy.register(packet)
        if allowed:
            if packet.packet_id not in self._policy.pending:
                raise CreditAdmissionError('source pass eligible but original C return absent')
            self._receipts[packet.packet_id]=receipt
        elif packet.packet_id in self._policy.pending:
            # Explicit administrative fail-closed eviction, not a negative reward.
            self._policy.expire(packet.packet_id,packet.decision_step,'shutdown_pending')
            self._discards+=1
        else:self._rejects+=1
        return allowed
    def settle(self,packet_id,current_step):
        if packet_id in self._settled or packet_id not in self._receipts:
            raise CreditAdmissionError('no eligible unconsumed source receipt')
        packet=self._policy.pending.get(packet_id)
        if packet is None or not verify_receipt(packet,self._receipts[packet_id]):
            raise CreditAdmissionError('lost or drifted frozen BV source lineage')
        reward=self._policy.settle(packet_id,current_step)
        self._settled.add(packet_id)
        del self._receipts[packet_id]
        return reward
    def settle_ready(self,current_step):
        for pid,packet in tuple(self._policy.pending.items()):
            if packet.arrival_step<=current_step:
                if current_step>packet.arrival_step+self._policy.ttl:
                    self._policy.expire(pid,current_step,'deadline_exceeded')
                    self._receipts.pop(pid,None);self._discards+=1
                else:self.settle(pid,current_step)
    def audit(self):
        state=self._policy.audit()
        if state['pending']!=len(self._receipts):
            raise CreditAdmissionError('pending credit not backed by source receipts')
        if self._settled & set(self._receipts):
            raise CreditAdmissionError('source receipt paid twice')
        return {'schema':SCHEMA,'registry':state,
                'source_receipts_pending':len(self._receipts),
                'source_receipts_settled':len(self._settled),
                'source_rejected_without_update':self._rejects,
                'source_failclosed_discard':self._discards,
                'receipts_sha256':digest(sorted((pid,r.commitment_hash) for pid,r in self._receipts.items())),
                'native_learning':False,'native_BV_semantic_credit':False}
