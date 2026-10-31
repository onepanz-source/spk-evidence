"""T8ABC: speculative *candidate* native semantic payload contract.

This emits a research-side proposed v1 packet. BV-v0e continues transporting
ONLY structural assessments. No attestation or native grant is invented.
"""
from __future__ import annotations
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import check
from research.spk_v5_t7jkl_mno_pqr.semantic_custody_v0 import compose
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest

SCHEMA = 'spk-bv-semantic-packet/v1-candidate-research'
ALLOWED_OUTCOMES={'IMPROVED': 1,'WORSENED': -1}


def make_packet(source:dict, issue:dict, *, drop_forward:bool=False)->dict:
    """Construct semantic design candidate from independently verified V0e evidence.

    Source and policy goal are still HOST authored. Message may be replaced by
    privileged host. In particular, this is NOT a native V0e return payload.
    """
    shadow=compose(source,issue,drop_forward=drop_forward)
    check(shadow['C_receipt'] is not None,'NO_CAUSAL_RETURN')
    outcome=shadow['outcome']
    check(outcome in ALLOWED_OUTCOMES,'UNSUPPORTED_OUTCOME')
    a=shadow['A_packet'];b=shadow['B_packet'];c=shadow['C_receipt']
    verdict={'issuer':'A','decision_id':issue['id'],
        'context_id':issue['cue'],'policy_version':issue['version'],
        'choice':issue['choice'],'outcome':outcome,
        'value':ALLOWED_OUTCOMES[outcome],
        'semantic_output_channel':a['semantic_channel'],
        'a_source_sha256':shadow['source_sha256'],
        'a_semantic_emission_sha256':a['semantic_emission_sha256'],
        'a_assessment_sha256':a['assessment_sha256']}
    route={'hops':['A','B','C'], 'intermediary':'B',
        'a_to_b_digest':a['structural_A_B_sha256'],
        'b_to_c_digest':b['structural_B_C_sha256'],
        'input_occurrence_id':a['last_input_id'],
        'shadow_chain_digest':digest(shadow)}
    packet={'schema':SCHEMA,'destination':'C',
        'epoch':issue['id'],'verdict':verdict,'route':route,
        'source_schema':'spk-bv-live-dual-event-scheduler/v0e',
        'carrier':'RESEARCH_OVERLAY_NOT_NATIVE_V0E',
        'provenance':'HOST_VISIBLE_UNATTESTED',
        'source_sha256':shadow['source_sha256']}
    return packet


def verify_packet(source,issue,packet,*,drop_forward=False):
    check(type(packet) is dict,'PACKET_TYPE')
    expected=make_packet(source,issue,drop_forward=drop_forward)
    check(packet==expected,'PACKET_BINDING_OR_SCHEMA_DRIFT')
    # Hash equality/custody is not a signature. Do not let callers claim otherwise.
    check(packet['provenance']=='HOST_VISIBLE_UNATTESTED' and
          packet['carrier']=='RESEARCH_OVERLAY_NOT_NATIVE_V0E', 'FALSE_NATIVE_PROVENANCE')
    return expected
