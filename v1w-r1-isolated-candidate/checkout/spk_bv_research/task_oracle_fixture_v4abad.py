"""Deterministic TEST-ONLY oracle fixtures. THESE KEYS ARE PUBLIC TEST DATA.

Never use these embedded keys for authentication, production or deployment.
They are deliberately disclosed to make reproducible attack and custody tests.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.task_oracle_custody_v4abad import (
    SCHEMA,ROLES,SCOPE,OracleLedger,lab_mac,assess,
)

TEST_KEYS = {
    'task_specifier': sha256(b'PUBLIC-RESEARCH-ONLY-TASK-SPECIFIER-v4abad').digest(),
    'independent_reviewer': sha256(b'PUBLIC-RESEARCH-ONLY-REVIEWER-v4abad').digest(),
}
VARIANTS = (
    'valid_quorum',
    'missing_reviewer',
    'wrong_reviewer_mac',
    'tampered_after_sign',
    'expired',
    'wrong_scope',
    'replay',
    'stale_sequence',
    'dually_signed_poison',
    'absent_canary',
    'wrong_predecessor',
    'single_key_roots',
)
VERDICTS = {
    'valid_quorum':'ATTESTED_TEST_WITNESS_NO_EXTERNAL_TRUST',
    'missing_reviewer':'VETO_QUORUM',
    'wrong_reviewer_mac':'VETO_INVALID_ATTESTATION',
    'tampered_after_sign':'VETO_INVALID_ATTESTATION',
    'expired':'VETO_EXPIRED_OR_FUTURE',
    'wrong_scope':'VETO_SCOPE',
    'replay':'VETO_REPLAY',
    'stale_sequence':'VETO_STALE_SEQUENCE',
    'dually_signed_poison':'VETO_SEMANTIC_CANARY_CONFLICT',
    'absent_canary':'VETO_NO_PRECOMMITTED_TASK_CANARY',
    'wrong_predecessor':'VETO_WRONG_PREDECESSOR',
    'single_key_roots':'VETO_NO_CONFIGURED_ROLE_ROOT',
}


def envelope(source_key, parent, tick, *, labels=None, seq=1, nonce=None,
             scope=SCOPE, expires=None):
    if labels is None:
        labels={'0':1,'1':0}
    if nonce is None:
        nonce=sha256(canon([source_key,parent,tick,seq])).hexdigest()
    payload={
        'schema':SCHEMA,'scope':scope,'lineage_sha256':parent,
        'source_key':source_key,'epoch':0,'sequence':seq,
        'nonce':nonce,'created_tick':tick,
        'expires_tick':tick+10 if expires is None else expires,
        'expected_terminal_counts':labels,
    }
    macs={role:lab_mac(TEST_KEYS[role],role,payload) for role in ROLES}
    return {'payload':payload,'macs':macs}


def run_variant(source_key,parent,tick,variant,canary):
    if type(variant) is not str or variant not in VARIANTS:
        raise ValueError('unsupported task oracle provenance test variant')
    ledger=OracleLedger()
    root=TEST_KEYS
    target_parent=parent
    provided_canary=canary
    specimen=envelope(source_key,parent,tick)
    observed=tick+1
    if variant=='missing_reviewer':
        specimen['macs'].pop('independent_reviewer')
    elif variant=='wrong_reviewer_mac':
        specimen['macs']['independent_reviewer']=specimen['macs']['task_specifier']
    elif variant=='tampered_after_sign':
        specimen['payload']['expected_terminal_counts']={'0':0,'1':1}
    elif variant=='expired':
        observed=tick+11
    elif variant=='wrong_scope':
        specimen=envelope(source_key,parent,tick,scope='other_actor/task')
    elif variant=='replay':
        first=assess(deepcopy(specimen),root,target_parent,canary,observed,ledger)
        if first['verdict']!='ATTESTED_TEST_WITNESS_NO_EXTERNAL_TRUST':
            raise ValueError('replay fixture could not establish first custody')
    elif variant=='stale_sequence':
        first=envelope(source_key,parent,tick,seq=2)
        accepted=assess(first,root,target_parent,canary,observed,ledger)
        if accepted['verdict']!='ATTESTED_TEST_WITNESS_NO_EXTERNAL_TRUST':
            raise ValueError('stale sequence fixture could not establish high watermark')
    elif variant=='dually_signed_poison':
        # Both roles validly MAC the *wrong* content. An untrusted MAC cannot
        # resolve this conflict with the earlier precommitted task contract.
        specimen=envelope(source_key,parent,tick,labels={'0':0,'1':1})
    elif variant=='absent_canary':
        provided_canary=None
    elif variant=='wrong_predecessor':
        specimen=envelope(source_key,'0'*64,tick)
    elif variant=='single_key_roots':
        root={role:TEST_KEYS['task_specifier'] for role in ROLES}
    before=(len(ledger.seen),dict(ledger.highest))
    verdict=assess(specimen,root,target_parent,provided_canary,observed,ledger)
    if verdict['verdict']!=VERDICTS[variant]:
        raise ValueError('oracle synthetic failure case diverged: '+variant)
    return {
        'variant':variant,
        'specimen_sha256':sha256(canon(specimen)).hexdigest(),
        'task_payload_sha256':sha256(canon(specimen['payload'])).hexdigest(),
        'source_key':source_key,
        'observed_tick':observed,
        'ledger_before':{'nonces':before[0],'highest':before[1]},
        'ledger_after':{'nonces':len(ledger.seen),'highest':dict(ledger.highest)},
        'decision':verdict,
    }
