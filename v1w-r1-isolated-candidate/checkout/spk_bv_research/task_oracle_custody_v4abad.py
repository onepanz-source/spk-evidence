"""v4ab-v4ad: typed task-oracle custody, strict fail-closed evaluation.

HMAC is used for *test-only* role separation with externally supplied keys.
No key in this verifier and no cryptographic trust root is installed. A valid
MAC authenticates a laboratory fixture only; it cannot establish task truth.
"""
from __future__ import annotations

from dataclasses import dataclass,field
import hashlib
import hmac

from spk_bv_research.native_allocation_boundary_v1r import canon

SCHEMA='spk-bv-task-oracle-custody/research-v4ab-v4ad'
STATUS='TASK_LABEL_PROVENANCE_QUORUM_AND_SEMANTIC_CANARY_NO_NATIVE_LEARNING'
DOMAIN=b'SPK/BV/TASK-ORACLE/V4ABAD\x00'
ROLES=('task_specifier','independent_reviewer')
SCOPE='A/channel_event_to_C/terminal_channel_7'
PAYLOAD_FIELDS=frozenset({
    'schema','scope','lineage_sha256','source_key','epoch',
    'sequence','nonce','created_tick','expires_tick','expected_terminal_counts',
})


@dataclass
class OracleLedger:
    """Transient within-run experiment custody, NOT durable replay security."""
    seen: set[str]=field(default_factory=set)
    highest: dict[str,int]=field(default_factory=dict)


def signing_input(role,payload):
    if type(role) is not str or role not in ROLES or type(payload) is not dict:
        raise ValueError('unsupported task attestation role or payload')
    return DOMAIN+role.encode('ascii')+b'\x00'+canon(payload)


def lab_mac(key,role,payload):
    if type(key) is not bytes or len(key)<32:
        raise ValueError('task test key must be at least 32 bytes')
    return hmac.new(key,signing_input(role,payload),hashlib.sha256).hexdigest()


def assess(envelope, trusted_keys, expected_parent, canary_labels,
           current_tick, ledger):
    """Return a typed gate witness; never apply a program or native update."""
    if type(envelope) is not dict or set(envelope)!={'payload','macs'}:
        return _result('VETO_MALFORMED_ENVELOPE',False,False,False)
    payload=envelope['payload']
    if (type(payload) is not dict or set(payload)!=PAYLOAD_FIELDS or
            type(envelope['macs']) is not dict or
            type(trusted_keys) is not dict or type(ledger) is not OracleLedger):
        return _result('VETO_MALFORMED_ENVELOPE',False,False,False)
    if (payload['schema'] != SCHEMA or type(payload['scope']) is not str or
            type(payload['lineage_sha256']) is not str or
            type(payload['source_key']) is not str or
            type(payload['nonce']) is not str or not payload['nonce'] or
            any(type(payload[k]) is not int for k in
                ('epoch','sequence','created_tick','expires_tick')) or
            payload['epoch'] != 0 or payload['sequence']<1 or
            payload['created_tick']<0 or
            payload['expires_tick']<=payload['created_tick'] or
            type(payload['expected_terminal_counts']) is not dict or
            set(payload['expected_terminal_counts'])!={'0','1'} or
            any(type(v) is not int or v not in (0,1) for v in
                payload['expected_terminal_counts'].values())):
        return _result('VETO_INVALID_TASK_CONTRACT',False,False,False)
    if (set(trusted_keys)!=set(ROLES) or
            any(type(trusted_keys[r]) is not bytes or
                len(trusted_keys[r])<32 for r in ROLES) or
            trusted_keys[ROLES[0]] == trusted_keys[ROLES[1]]):
        return _result('VETO_NO_CONFIGURED_ROLE_ROOT',False,False,False)
    if set(envelope['macs'])!=set(ROLES):
        return _result('VETO_QUORUM',False,False,False)
    for role in ROLES:
        mac=envelope['macs'][role]
        if type(mac) is not str or len(mac)!=64:
            return _result('VETO_INVALID_ATTESTATION',False,False,False)
        if not hmac.compare_digest(mac,lab_mac(trusted_keys[role],role,payload)):
            return _result('VETO_INVALID_ATTESTATION',False,False,False)
    # Important: MAC validity is independent of authorization, freshness and
    # semantic consistency. Neither proves the oracle's label is correct.
    if type(expected_parent) is not str or payload['lineage_sha256']!=expected_parent:
        return _result('VETO_WRONG_PREDECESSOR',True,False,False)
    if payload['scope']!=SCOPE:
        return _result('VETO_SCOPE',True,False,False)
    if (type(current_tick) is not int or
            current_tick<payload['created_tick'] or
            current_tick>payload['expires_tick']):
        return _result('VETO_EXPIRED_OR_FUTURE',True,False,False)
    if payload['nonce'] in ledger.seen:
        return _result('VETO_REPLAY',True,False,False)
    if payload['sequence']<=ledger.highest.get(payload['source_key'],0):
        return _result('VETO_STALE_SEQUENCE',True,False,False)
    if canary_labels is None:
        return _result('VETO_NO_PRECOMMITTED_TASK_CANARY',True,False,False)
    if (type(canary_labels) is not dict or
            canary_labels!={'0':1,'1':0}):
        return _result('VETO_INVALID_CANARY',True,False,False)
    if payload['expected_terminal_counts']!=canary_labels:
        return _result('VETO_SEMANTIC_CANARY_CONFLICT',True,True,False)
    ledger.seen.add(payload['nonce'])
    ledger.highest[payload['source_key']]=payload['sequence']
    return _result('ATTESTED_TEST_WITNESS_NO_EXTERNAL_TRUST',True,True,True)


def _result(verdict,valid_mac,canary_checked,accepted):
    return {
        'schema':SCHEMA,'status':STATUS,'verdict':verdict,
        'two_distinct_fixture_mac_roles_valid':valid_mac,
        'previously_pinned_semantic_canary_checked':canary_checked,
        'accepted_for_research_evidence_only':accepted,
        'production_identity_authenticated':False,
        'durable_replay_protection_implemented':False,
        'candidate_program_adopted':False,
        'native_learning_implemented':False,
    }
