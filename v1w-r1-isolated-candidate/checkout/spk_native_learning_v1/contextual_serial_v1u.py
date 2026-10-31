"""Cooperative v1u context memory and original PE causal ledger ownership."""
from __future__ import annotations
from spk_native_learning_v1 import contextual_durable_v1u as d
from spk_native_learning_v1.generalized_serial_v1t import serialized_ownership
SCHEMA='spk-native-learning-contextual-serialized/v1u'
class SerialReject(RuntimeError):pass

def run_epoch(path,epoch,context,choice,goal,*,second_tick=30,pause_after=None,root='.',wait_seconds=5.0):
    with serialized_ownership(path,wait_seconds=wait_seconds) as p:
        result=d.run_epoch(p,epoch,context,choice,goal,second_tick=second_tick,pause_after=pause_after,root=root)
        chain=d.audit(p,root=root)
        if len(chain['epochs'])!=epoch+1 or chain['bank']!=result['bank']:raise SerialReject('POST_COMMIT_BANK_AUDIT_FAILED')
        return {'schema':SCHEMA,'episode':result['episode'],'bank':result['bank'],'chain_sha256':chain['chain_sha256']}

def audit(path,*,root='.',wait_seconds=5.0):
    with serialized_ownership(path,wait_seconds=wait_seconds) as p:return d.audit(p,root=root)

def run_sequence(path,cases,*,root='.',wait_seconds=5.0,stop_after=None):
    if type(cases) not in (tuple,list) or not cases:raise SerialReject('INVALID_SEQUENCE')
    with serialized_ownership(path,wait_seconds=wait_seconds) as p:
        reports=[]
        for i,case in enumerate(cases):
            if type(case) not in (tuple,list) or len(case)!=3:raise SerialReject('INVALID_CASE_SHAPE')
            result=d.run_epoch(p,i,*case,root=root);reports.append(result['episode'])
            if stop_after==i:raise d.SimulatedPowerLoss('AFTER_CLOSED_EPOCH:'+str(i))
        chain=d.audit(p,root=root)
        if len(chain['epochs'])!=len(cases):raise SerialReject('CHAIN_INCOMPLETE')
        return {'schema':SCHEMA,'chain':chain,'new_tick_rows':sum(x['new_tick_rows'] for x in reports),
                'P_grants_by_epoch':[len(x['P_grants']) for x in reports],
                'C_PE_reads_by_epoch':[x['C_PE_reads'] for x in reports]}
