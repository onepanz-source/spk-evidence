"""T8DEF: explicit proposed P admission decision, not SPK Memory Contract v0.

The only available authority is host-controlled research state. A native
Memory Contract grant is ALWAYS DENIED, even when semantic packet checks pass.
"""
from __future__ import annotations
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import check,verify_source
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest
from .semantic_packet_v1_candidate import verify_packet

SCHEMA='spk-bv-P-admission/v1-candidate-research'


def evaluate(source,issue,packet,*,drop_forward=False):
    verify_packet(source,issue,packet,drop_forward=drop_forward)
    feedback=verify_source(source,issue['choice'],issue['goal'],drop_forward=drop_forward)
    candidate=feedback['A_outcome']=='WORSENED'
    request={'schema':SCHEMA,'owner':'C','pe_id':'PE-C-RESEARCH',
        'domain':'P','mode':'execute','intent':'BOUNDED_SWITCH',
        'decision_id':issue['id'],'context_id':issue['cue'],
        'expected_policy_version':issue['version'],
        'expected_choice':issue['choice'],
        'semantic_packet_digest':digest(packet),
        'observed_outcome':feedback['A_outcome'],
        'research_switch_candidate':candidate}
    return {'request':request,
        'research_verdict':'SIMULATOR_ELIGIBLE' if candidate else 'NO_RESEARCH_SWITCH',
        'native_admission':'DENIED_NO_NATIVE_MEMORY_CONTRACT_GRANT',
        'native_grant':None,
        'native_write_performed':False,
        'authority_model':'HOST_CONTROLLED_RESEARCH'}


def settle_research(store,source,issue,packet,decision,*,drop_forward=False):
    expected=evaluate(source,issue,packet,drop_forward=drop_forward)
    check(type(decision) is dict and decision==expected,'ADMISSION_DECISION_DRIFT')
    check(decision['native_grant'] is None and decision['native_write_performed'] is False,
          'FORGED_NATIVE_GRANT')
    # The original T7 host-managed SQLite state remains the *only* mutation.
    feedback=verify_source(source,issue['choice'],issue['goal'],drop_forward=drop_forward)
    completed=store.settle(issue,feedback)
    check(not completed['updated'] or expected['research_verdict']=='SIMULATOR_ELIGIBLE',
          'UNAUTHORIZED_SHADOW_COMMIT')
    return completed
