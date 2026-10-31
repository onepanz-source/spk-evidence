"""Source-pinned cumulative task-oracle provenance/poison quarantine gate."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from hashlib import sha256

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVPlanV0e,execute_live_v0e
from spk_bv_research.grant_rank_integration_v3tuv import ARMS,CAPACITIES,NEW_SCHEDULES
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_ack_causal_replay_v4mno import CausalProbeRejected
from spk_bv_research.native_actor_objective_v4yzaa import OBJECTIVE
from spk_bv_research.off_on_v0t import snapshot
from spk_bv_research.task_oracle_custody_v4abad import SCHEMA,STATUS
from spk_bv_research.task_oracle_fixture_v4abad import (
    VARIANTS,VERDICTS,run_variant,
)

SIGNED_V3_SHA='f783be9952613aa98eafef59d24c19eb64ccc09d29265017eabb675fe0155827'
SIGNED_V4YZAA_SHA='049e2c555ca42f7a0b029b6ac112801233df5794ebcffc26a63554ce534149a3'


def require(condition, message):
    if not condition:
        raise CausalProbeRejected(message)


def audit_row(row,source_key,parent,tick,canary):
    """Deterministic independent recomputation of custody verdict from inputs.

    Not an independent test of the real-world correctness of task labels.
    """
    expected=run_variant(source_key,parent,tick,row['variant'],canary)
    require(row==expected,'oracle provenance audit report forged')


def evaluate(v3,raw3,prev,raw_prev,*,fixture_fn=fixture,
             native_executor=execute_live_v0e):
    require(type(v3) is dict and type(prev) is dict and
            type(raw3) is bytes and type(raw_prev) is bytes and
            canon(v3)==raw3 and canon(prev)==raw_prev and
            sha256(raw3).hexdigest()==SIGNED_V3_SHA and
            sha256(raw_prev).hexdigest()==SIGNED_V4YZAA_SHA and
            prev['signed_v3tuv_sha256']==SIGNED_V3_SHA and
            prev['external_objective']==OBJECTIVE and
            prev['totals']['signed_native_replays']==18 and
            prev['totals']['counterfactual_objective_trials']==126 and
            prev['shadow_trial_eligibility_count']==18 and
            prev['actual_shadow_adoptions']==0 and
            prev['native_learning_implemented'] is False,
            'oracle signed predecessor/objective drift')
    parent=sha256(raw_prev).hexdigest()
    canary=OBJECTIVE['expected_terminal_counts']
    totals=Counter()
    rows=[]
    evaluated=0
    for signed,(schedule,ticks) in zip(v3['source_matrix'],NEW_SCHEDULES):
        require(signed['schedule']==schedule and
                signed['source_external_ticks']==list(ticks),
                'oracle signed schedule mismatch')
        case,fabric,plans=fixture_fn(ticks=ticks)
        for entry,(mode,enabled,priority) in zip(signed['modes'],ARMS):
            require(entry['mode']==mode,'oracle signed mode mismatch')
            for capacity,cap in zip(entry['capacities'],CAPACITIES):
                require(capacity['native_PE_capacity']==cap,
                        'oracle signed capacity mismatch')
                pp=replace(plans[1],fabric_slots_per_tick=cap)
                native=native_executor(case,fabric,plans[0],pp,plans[2],plans[3],
                                       LiveBVPlanV0e(enabled=enabled,priority=priority))
                require(snapshot(native)==capacity['original_native_sha256'],
                        'oracle signed native executor drift')
                reference=prev['scenarios'][evaluated*7+3]
                require(reference['schedule']==schedule and reference['mode']==mode and
                        reference['native_global_PE_capacity']==cap and
                        reference['result']['variant']=='degraded_repair' and
                        reference['result']['objective_cost_improvement']==4 and
                        reference['result']['committed_derived_program_version']==0,
                        'oracle preceding corrective positive control drift')
                totals['signed_native_replays']+=1
                source_key=f'{schedule}/{mode}/{cap}'
                for variant in VARIANTS:
                    witness=run_variant(source_key,parent,case.events[0].timestamp,
                                        variant,canary)
                    audit_row(witness,source_key,parent,case.events[0].timestamp,canary)
                    decision=witness['decision']
                    require(decision['verdict']==VERDICTS[variant] and
                            decision['native_learning_implemented'] is False and
                            decision['candidate_program_adopted'] is False and
                            decision['production_identity_authenticated'] is False,
                            'oracle witness unsupported success or adoption')
                    totals['provenance_scenarios']+=1
                    totals['verdict_'+decision['verdict']]+=1
                    totals['valid_fixture_quorum_MACs']+=int(
                        decision['two_distinct_fixture_mac_roles_valid'])
                    rows.append({'schedule':schedule,'mode':mode,
                                 'native_global_PE_capacity':cap,
                                 'witness':witness})
                evaluated+=1
    require(len(v3['source_matrix'])==3 and evaluated==18 and
            totals['signed_native_replays']==18 and
            totals['provenance_scenarios']==216 and
            totals['verdict_ATTESTED_TEST_WITNESS_NO_EXTERNAL_TRUST']==18 and
            totals['verdict_VETO_SEMANTIC_CANARY_CONFLICT']==18 and
            totals['valid_fixture_quorum_MACs']==144,
            'oracle full source research matrix incomplete')
    return {
        'schema':SCHEMA,'status':STATUS,
        'signed_v3tuv_sha256':sha256(raw3).hexdigest(),
        'signed_v4yzaa_sha256':parent,
        'precommitted_task_canary_labels':canary,
        'trust_root':'PUBLIC_TEST_KEYS_EMBEDDED_IN_FIXTURE_NOT_PRODUCTION_IDENTITY',
        'attestation':'TWO_DISTINCT_HMAC_TEST_ROLES_WITH_DOMAIN_SEPARATION',
        'replay_scope':'ONE_IN_MEMORY_GATE_INVOCATION_NOT_DURABLE_CUSTODY',
        'semantic_limit':'PRECOMMITTED_REFERENCE_CONSISTENCY_NOT_INDEPENDENT_TASK_TRUTH',
        'tested_variants':list(VARIANTS),
        'totals':dict(sorted(totals.items())),
        'scenarios':rows,
        'program_adoptions':0,
        'native_learning_implemented':False,
        'native_v0e_modified':False,
        'architecture_v1_modified':False,
        'claims_excluded':[
            'test HMACs and embedded fixture keys are not production authentication',
            'two agreeing authorized label providers can still both be wrong',
            'a pinned previous task declaration is not an independent real-world oracle',
            'transient replay guard does not protect across restarts or peers',
            'no program learning, promotion, native algorithm update or physical cost validation',
        ],
        'next_gate':'EXTERNAL_VERIFIER_KEY_PROVISIONING_AND_INDEPENDENT_TASK_GROUND_TRUTH',
    }
