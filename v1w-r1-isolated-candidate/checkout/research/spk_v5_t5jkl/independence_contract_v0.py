"""SPK research-only A judgment independence gate.

Receipt != own observation != authenticated origin != causal credit.
Never issues native credit or learning, even with self-declared independent evidence.
"""
from __future__ import annotations
import re

HEX = re.compile(r'^[0-9a-f]{64}$')
class BoundaryViolation(ValueError): pass

def need(condition, code):
    if not condition: raise BoundaryViolation(code)

def classify(receipt, source, proposed_A_observation=None):
    """Classify pinned source+transport evidence. A's claimed judgment is never trusted.

    No synthetic A evidence is created by this function.
    """
    need(type(receipt) is dict and type(source) is dict,'INPUT_SHAPE')
    idx=receipt.get('index')
    need(type(idx) is int and idx>=0 and source.get('index')==idx,'CASE_ID_DRIFT')
    need(receipt.get('source_sha256')==source.get('source_sha256') and
         isinstance(receipt.get('source_sha256'),str) and HEX.fullmatch(receipt['source_sha256']),
         'SOURCE_HASH_MISMATCH')
    accepted=receipt.get('A_fresh_accept'); issued=receipt.get('C_issued'); guard=receipt.get('guard_only')
    need(type(accepted) is bool and type(issued) is int and issued in (0,1) and
         issued==int(accepted) and type(guard) is bool,'RECEIPT_SHAPE_MISMATCH')
    failure=source.get('failure')
    need(failure in ('none','no_C','no_marker','no_forward','no_reverse'),'UNKNOWN_FAILURE')
    sign=source.get('C_sign_candidate_from_same_source_forward_output')
    need(sign is None or type(sign) is int and sign in (-1,1),'SOURCE_SIGN_INVALID')
    need(accepted==(sign in (-1,1)),'SOURCE_SIGN_RECEIPT_PARITY')
    need(guard==(accepted and failure=='none'),'GUARD_CANDIDATE_DRIFT')
    need(receipt.get('native_credit') is False and source.get('native_learning_proven') is False and
         source.get('signed_C_to_A_native_BV_receipt_proven') is False,'NATIVE_PROMOTION_CLAIM')
    coherent=source.get('C_B_A_emission_candidate_consistent')
    need(type(coherent) is bool,'COHERENCE_SHAPE')
    if coherent: need(accepted,'COHERENT_WITHOUT_RECEIPT')
    # The source observation concerns forward.emissions, not the fork's
    # BV-feedback propagation. They must be labeled as distinct evidence planes.
    status=('NO_SIGN_RECEIVED' if not accepted else
            'FRESH_RECEIPT_GUARD_CANDIDATE' if guard else
            'FRESH_RECEIPT_WITH_SOURCE_FAULT')
    own=assess_A_claim(proposed_A_observation)
    return {'index':idx,'source_sha256':receipt['source_sha256'],
            'experimental_port_sha256':receipt['port_sha256'],
            'failure':failure,'C_sign_seen':accepted,'source_forward_emission_chain':coherent,
            'A_fresh_receipt':accepted,'research_guard_candidate':guard,
            'classification':status,'A_independent_judgment_structural':own['structural_independence'],
            'A_independent_judgment_authenticated':False,
            'native_semantic_BV_credit':False,'native_learning':False}

def assess_A_claim(claim):
    """Check lineage shape ONLY. A declaration never authenticates itself.

    An actual independent A authority would require externally verified sensor
    custody, a PE-bound issuer and receiver-owned state in a separate trust domain.
    The current host-controlled research Python runtime has none of these.
    """
    if claim is None: return {'structural_independence':False,'authenticated':False,'reason':'NO_INDEPENDENT_A_EVIDENCE'}
    need(type(claim) is dict,'A_CLAIM_SHAPE')
    need(set(claim)=={'claimant','assessment','goal_observation_sha256','lineage_roots','attested_by'},'A_CLAIM_FIELDS')
    need(claim['claimant']=='A' and isinstance(claim['assessment'],int) and not isinstance(claim['assessment'],bool)
         and claim['assessment'] in (-1,0,1),'A_CLAIM_INVALID')
    need(type(claim['goal_observation_sha256']) is str and HEX.fullmatch(claim['goal_observation_sha256']),
         'A_GOAL_OBSERVATION_HASH')
    roots=claim['lineage_roots'];need(type(roots) is list and roots and all(type(v) is str for v in roots),
         'A_LINEAGE_INVALID')
    need(len(set(roots))==len(roots),'A_LINEAGE_DUPLICATED')
    # Synthetic 'A' labels or claimed external attestations do not grant authority.
    independent=all(v.startswith('A_SENSOR:') for v in roots)
    need(claim['attested_by'] is None or type(claim['attested_by']) is str,'A_ATTESTATION_TYPE')
    return {'structural_independence':independent,'authenticated':False,
            'reason':'UNVERIFIABLE_HOST_DECLARATION' if independent else 'CIRCULAR_OR_NON_A_LINEAGE'}
