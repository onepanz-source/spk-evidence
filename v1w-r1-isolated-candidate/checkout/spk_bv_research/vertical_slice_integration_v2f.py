"""v2f integrated release: finite tick-batch bridge + research BV feedback loop.

Reads v2e historical native attestation. Executes NEW micro-runtime only.
A match is an empirical projection, never frozen CMP/state/native mailbox proof.
"""
from __future__ import annotations
from hashlib import sha256

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import require
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES, SCHEMA as V2E_SCHEMA, STATUS as V2E_STATUS,
)
from spk_backvalidation_v2.batched_feedback_executor_v2f import (
    BatchCaseV2f, MailboxV2f, execute_batch_v2f, forward_projection,
)
from spk_backvalidation_v2.observed_scheduler_v2a import ObserverV2a

SCHEMA='spk-bv-batched-source-owned-feedback-vertical-slice/v2f'
STATUS='RESEARCH_TICK_BATCH_AND_ACTOR_LOCAL_FEEDBACK_NATIVE_INTEGRATION_BLOCKED'
CODE_VERSION='spk-bv-batched-feedback-executor/research-v2f'
NEGATIVE_CLAIMS=(
 'native-v2e-counts-and-batches-match-research-model-in-finite-matrix-only',
 'per-tick-batch-policy-is-hypothesis-not-proven-native-CMP-semantics',
 'template-source-identities-are-not-independent-or-distinguishable-in-v2e',
 'research-actor-local-judgment-is-not-frozen-native-B-endogenous-feedback',
 'research-delivery-via-same-process-queue-is-not-cryptographic-authentication',
 'local-judgment-criterion-was-chosen-for-research-not-derived-from-SPK-algebra',
 'lost-control-or-queue-overflow-is-not-evidence-of-sender-silence',
 'no-native-source-callback-absence-certificate-or-frozen-operator-update',
 'source-owned-forward-parity-is-bounded-not-real-time-noninterference',
 'no-alteration-to-frozen-core-network-compiler-architecture-scheduler',
)


def validate_evidence(v2e: dict, data: bytes, *, v2d_data: bytes | None = None):
    require(type(v2e) is dict and type(data) is bytes and canon(v2e)==data,
            'v2e must be canonical and byte-identical')
    require(v2e.get('schema')==V2E_SCHEMA and v2e.get('status')==V2E_STATUS and
            v2e.get('source_kind')=='READONLY_FROZEN_V0E_NEW_PREDECLARED_NATIVE_ADMISSION_INTERVENTIONS' and
            v2e.get('frozen_native_source_pins_rechecked_in_this_run') is True and
            v2e.get('native_semantic_probe_executed') is True and
            v2e.get('new_frozen_scheduler_executions')==45 and
            v2e.get('full_native_v0w_anchor_replay_count')==12 and
            v2e.get('native_source_template_variants_distinguishable') is False and
            v2e.get('native_CMP_semantics_or_scheduler_coalescence_identified') is False and
            v2e.get('native_B_control_messages')==0 and
            v2e.get('native_learning_proven') is False and
            v2e.get('reference_v0w_sha256')=='3d383897163e32e46a062575bf8b9fa4713800e68d36316ee3dba4db7f0a5f59',
            'v2e native provenance invalid')
    if v2d_data is not None:
        require(type(v2d_data) is bytes and
                sha256(v2d_data).hexdigest()==v2e.get('reference_v2d_sha256'),
                'v2d predecessor SHA mismatch')
    rows=v2e.get('native_matrix')
    require(type(rows) is list and len(rows)==len(RECIPES) and
            [r.get('label') for r in rows]==[name for name,_ in RECIPES],
            'native workload roster invalid')
    for row, (name, recipe) in zip(rows,RECIPES):
        require(row.get('recipe_template_index_and_tick')==[list(x) for x in recipe] and
                row.get('external_input_ticks')==[t for _,t in recipe] and
                row.get('event_count')==len(recipe) and
                row.get('native_mechanism_identified') is False and
                row.get('runs') is not None and
                set(row['runs'])=={'off','on_forward_first','on_feedback_first'},
                'native attested matrix entry or mode tampered')
        counts=[];term=[]
        for mode in ('off','on_forward_first','on_feedback_first'):
            run=row['runs'][mode];m=run.get('metrics')
            require(type(m) is dict and type(run.get('whole_result_sha256')) is str and
                    len(run['whole_result_sha256'])==64 and
                    m.get('forward_emissions')==3*len(set(t for _,t in recipe)) and
                    m.get('forward_terminal')==len(set(t for _,t in recipe)) and
                    m.get('processed_batches')==3*len(set(t for _,t in recipe)) and
                    m.get('processed_events')==len(recipe)+2*len(set(t for _,t in recipe)) and
                    m.get('forward_occurrences')==2*len(set(t for _,t in recipe)) and
                    m.get('forward_batches')==m.get('processed_batches'),
                    'native evidence contradicts required finite batch projection')
            counts.append(m['forward_emissions']);term.append(m['forward_terminal'])
        require(row.get('observed_total_emissions_per_control')==counts and
                row.get('observed_terminal_per_control')==term and
                row.get('candidate_matches_per_control',{}).get('one_three_emission_chain_per_tick')==[True]*3,
                'empirical predictions or counts altered')
    return True


def _micro_case(label,recipe,operators=('relay','relay','relay')):
    return BatchCaseV2f('v2f.'+label,tuple(recipe),operators)


def run_integrated(v2e, data, *, v2d_data=None, custody=False):
    validate_evidence(v2e,data,v2d_data=v2d_data)
    require(type(custody) is bool, 'invalid custody flag')
    cells=[]
    for row,(name,recipe) in zip(v2e['native_matrix'],RECIPES):
        case=_micro_case(name,recipe)
        r_off=execute_batch_v2f(case)
        observer=ObserverV2a()
        r_observed=execute_batch_v2f(case,observe=observer)
        box=MailboxV2f()
        r_feedback=execute_batch_v2f(case,feedback=True,mailbox=box)
        both_observer=ObserverV2a()
        both_box=MailboxV2f()
        r_both=execute_batch_v2f(case,observe=both_observer,
                                  feedback=True,mailbox=both_box)
        forward=forward_projection(r_off)
        require(forward==forward_projection(r_observed)==
                forward_projection(r_feedback)==forward_projection(r_both),
                'observer or receiver feedback modified forward result')
        require(r_off['observer_records_offered']==len(observer.events)==
                len(both_observer.events) and observer.summary()['complete'] and
                both_observer.summary()['complete'],
                'source-owned record gap or observer overflow')
        native=row['runs']['off']['metrics']
        groups=len(set(t for _,t in recipe))
        require(r_off['processed_batches']==native['processed_batches'] and
                r_off['processed_forward_events']==native['processed_events'] and
                sum(r_off['forward_emissions'].values())==native['forward_emissions'] and
                r_off['forward_terminal_count']==native['forward_terminal'] and
                r_off['forward_routes']=={'A->B':native['forward_occurrences']//2,
                                          'B->C':native['forward_occurrences']//2} and
                r_feedback['research_receiver_local_judgments']==2*groups and
                r_both['research_feedback_delivered']['research_delivered_total']==2*groups and
                r_both['research_score_by_sender']=={'A':groups,'B':groups,'C':0},
                'micro forward counts, actor-local judgment or delivery divergence')
        cells.append({
            'label':name,'input_ticks':[t for _,t in recipe],
            'events_admitted':len(recipe),'distinct_tick_batches':groups,
            'native_metrics_reference':{key:native[key] for key in
                    ('forward_emissions','forward_terminal','forward_occurrences',
                     'processed_batches','processed_events')},
            'research_micro_metrics':{
                'forward_emissions':sum(r_off['forward_emissions'].values()),
                'forward_terminal':r_off['forward_terminal_count'],
                'forward_occurrences':sum(r_off['forward_routes'].values()),
                'processed_batches':r_off['processed_batches'],
                'processed_events':r_off['processed_forward_events']},
            'five_projection_metrics_equal':True,
            'observer_off_on_forward_equal':True,
            'control_off_on_forward_equal':True,
            'source_owned_observer_records':len(observer.events),
            'research_judgments_generated':r_feedback['research_receiver_local_judgments'],
            'research_control_packets_delivered':box.summary()['research_delivered_total'],
            'research_recipient_score':r_feedback['research_score_by_sender'],
            'forward_projection_sha256':sha256(canon(forward)).hexdigest(),
            'cross_runtime_state_or_event_identity_equal':None,
        })
    # Negative controls are new running experiments, not claims based on v2e.
    negative_case=_micro_case('negative_block',((0,1),(1,3)),('relay','block','relay'))
    negative_box=MailboxV2f()
    neg=execute_batch_v2f(negative_case,feedback=True,mailbox=negative_box)
    require(neg['research_score_by_sender']['A']==-2 and
            neg['research_feedback_delivered']['research_delivered_total']==2 and
            neg['forward_emissions']=={'A':2,'B':0,'C':0},
            'negative local receiver judgment broken')
    loss_case=_micro_case('lost_feedback',((0,1),(1,3)))
    lost_box=MailboxV2f(accept=lambda _: False)
    loss=execute_batch_v2f(loss_case,feedback=True,mailbox=lost_box)
    require(loss['research_receiver_local_judgments']==4 and
            loss['research_feedback_delivered']['research_lost']==4 and
            loss['research_feedback_delivered']['research_delivered_total']==0,
            'receiver loss control failure')
    overflow_box=MailboxV2f(capacity=1)
    over=execute_batch_v2f(loss_case,feedback=True,mailbox=overflow_box)
    require(over['research_feedback_delivered']['research_overflow'] and
            over['research_feedback_delivered']['research_delivered_total']==1,
            'receiver capacity control failure')
    def raising(_):raise RuntimeError('telemetry offline')
    broken_observer=ObserverV2a(sink=raising)
    unaffected=execute_batch_v2f(loss_case,observe=broken_observer)
    control=execute_batch_v2f(loss_case)
    require(broken_observer.sink_fault and
            forward_projection(unaffected)==forward_projection(control),
            'observer-fault noninterference broken')
    return {
       'schema':SCHEMA,'status':STATUS,
       'source_kind':'ATTESTED_NATIVE_V2E_REPORT_PLUS_NEW_VERSIONED_RESEARCH_VERTICAL_SLICE',
       'reference_v2e_sha256':sha256(data).hexdigest(),
       'reference_v2d_sha256':v2e['reference_v2d_sha256'],
       'frozen_native_source_pins_rechecked_in_this_run':custody,
       'inherited_native_v2e_reexecution_in_this_module':False,
       'native_runs_new':0,'native_runs_inherited_v2e':45,
       'source_owned_research_micro_executions':len(cells)*4+5,
       'native_projection_cells_checked':len(cells)*3,
       'finite_native_forward_projection_fields_matched':5,
       'research_receiver_local_judgment_implemented':True,
       'research_control_messages_delivered_in_new_executor':sum(
           c['research_control_packets_delivered'] for c in cells),
       'research_bounded_loss_and_overflow_checked':True,
       'negative_research_receiver_judgment_tested':True,
       'research_observer_and_control_off_on_forward_parity':True,
       'native_receiver_B_control_messages':0,
       'native_B_endogenous_judgment_proven':False,
       'native_CMP_or_scheduler_semantics_equivalence_proven':False,
       'native_independent_absence_certificates':0,
       'native_operator_updates':0,'native_learning_proven':False,
       'native_integration_gate':'BLOCKED_NATIVE_VERSIONED_EXECUTOR_AND_RECEIVER_PORT_ABSENT',
       'finite_cells':cells,
       'claims_excluded':list(NEGATIVE_CLAIMS),
    }
