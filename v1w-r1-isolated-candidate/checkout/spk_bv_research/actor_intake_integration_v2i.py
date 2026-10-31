"""BV v2i: original-vs-derived actor-batch control intake admission matrix."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, read_pinned_source,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_intake_v2i import (
    ActorIntakeV2i, derive_actor_intake_executor,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import (
    require, snapshot, source_pins, runtime_modules_bound,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES, build_workload,
)
from spk_bv_research.link_pressure_v0u import ARMS, _arm
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources

SCHEMA = 'spk-bv-derived-native-actor-batch-control-intake/v2i'
STATUS = 'DERIVED_COMMITTED_ACTOR_BATCH_INTAKE_NO_FROZEN_ACTOR_CONTRACT'
CONTRACT_STATUS = 'V2I_CONTRACT_ONLY_NATIVE_EXECUTION_PENDING'
V2H_SHA = '8407d93d78ca1aba76b1b01e65bafc9692aa35715261b53833366823f37138cd'

EXCLUSIONS = (
    'actor-intake-executes-in-pinned-derived-batch-proxy-not-frozen-neuron',
    'in-process-admission-identity-is-not-cryptographic-origin-authentication',
    'credit-receipts-are-separate-read-only-research-ledger-not-learning',
    'receipt-service-does-not-consume-modelled-PE-memory-link-grants',
    'unconsumed-control-and-lost-control-never-imply-negative-or-absence',
    'post-native-control-drain-is-not-native-actor-service',
    'finite-native-parity-does-not-prove-N-node-or-all-input-equivalence',
    'no-frozen-source-modification-or-contract-promotion',
)


def validate_v2h(previous, raw):
    require(type(previous) is dict and type(raw) is bytes and
            raw == canon(previous) and sha256(raw).hexdigest() == V2H_SHA,
            'v2i predecessor must be exact signed-off canonical v2h')
    require(previous.get('schema') ==
            'spk-bv-derived-native-actor-semantic-receiver-port/v2h' and
            previous.get('status') ==
            'DERIVED_ACTOR_CAUSAL_FEEDBACK_DELIVERED_NO_FROZEN_ACTOR_INTAKE' and
            previous.get('full_native_result_parity_cells') == 45 and
            previous.get('actor_semantic_totals', {}).get('control_delivered') == 156 and
            previous.get('negative_real_actor_judgments') == 2 and
            previous.get('frozen_native_actor_receives_research_control') is False and
            previous.get('native_learning_proven') is False and
            previous.get('next_gate') ==
            'BLOCKED_FROZEN_ACTOR_INTAKE_AND_LEARNING_CONTRACT',
            'v2h predecessor not native-backed or falsely promoted')
    rows = previous.get('paired_native_matrix')
    require(type(rows) is list and len(rows) == len(RECIPES),
            'v2h paired predecessor roster mismatch')
    for (label, recipe), entry in zip(RECIPES, rows):
        require(entry.get('label') == label and
                entry.get('recipe') == [list(x) for x in recipe] and
                [x.get('mode') for x in entry.get('modes', [])] ==
                [x[0] for x in ARMS] and
                all(x.get('full_native_parity') is True and
                    type(x.get('whole_result_sha256')) is str and
                    len(x['whole_result_sha256']) == 64
                    for x in entry['modes']),
                'v2h historical matrix mutated')
    return True


def _derived_arm(source, native, plan_type, changed, fabric, plans,
                 enabled, priority, digest, data, *, policy='normal'):
    require(policy in ('normal', 'loss', 'pressure'),
            'unsupported v2i feedback intervention')
    if policy == 'loss':
        port = ReceiverPortV2h(accept=lambda _j: False)
    else:
        port = ReceiverPortV2h()
    if policy == 'pressure':
        intake = ActorIntakeV2i(port, per_batch=1, max_receipts=1)
    else:
        intake = ActorIntakeV2i(port)
    observer = CallsiteObserver()
    derived, _, anchors = derive_actor_intake_executor(
        source, native, port, intake, observer)
    result = _arm(derived, plan_type, changed, fabric, plans,
                  f'v2i-{policy}', enabled, priority, digest, data)
    port.close()
    summary = intake.summary()
    transport = port.summary()
    require(anchors == (('batch', 194), ('clock', 125),
                        ('emission', 217), ('ingress', 136)) and
            not observer.overflow and not observer.sink_failed and
            summary['delivered_controls'] == transport['control_delivered'] and
            summary['derived_actor_batch_receipts'] +
            summary['unconsumed_delivered_controls'] ==
            summary['delivered_controls'] and
            not summary['frozen_actor_receives_control'] and
            summary['frozen_state_updates_from_control'] == 0 and
            summary['operator_learning_updates'] == 0,
            'v2i actor custody/parity accounting inconsistent')
    if policy == 'normal':
        require(summary['admitted_actors'] == ['A', 'B', 'C'] and
                transport['source_owned_emissions'] ==
                transport['receiver_local_judgments'] ==
                transport['control_delivered'] ==
                result['metrics']['forward_occurrences'] and
                not summary['receipt_pressure'] and
                not summary['per_batch_pressure'],
                'v2i normal live actor semantics inconsistent')
    if policy == 'loss':
        require(transport['lost'] == transport['receiver_local_judgments'] and
                summary['delivered_controls'] == 0 and
                summary['derived_actor_batch_receipts'] == 0,
                'v2i loss fabricated actor receipt')
    return result, summary, transport, observer.counts()


def experiment(previous, raw, *, root:Path, fixture_fn, native_executor,
               plan_type):
    validate_v2h(previous, raw)
    root = root.resolve(strict=True)
    pins_before = source_pins(root)
    architecture_before = read_pinned_sources(root)
    runtime_modules_bound(root, native_executor, fixture_fn, plan_type)
    source = read_pinned_source(root)
    original = fixture_fn()
    case, fabric, plans = original
    unchanged = snapshot(original)
    totals = {'committed_actor_batch_visits':0,
              'derived_actor_batch_receipts':0,
              'unconsumed_delivered_controls':0,
              'delivered_controls':0,
              'post_native_deliveries_not_native_intake':0,
              'delivered_during_native_unconsumed':0}
    rows = []
    for (label, recipe), prior in zip(RECIPES, previous['paired_native_matrix']):
        changed = build_workload(case, recipe)
        data = (changed, fabric, tuple(plans))
        digest = snapshot(data)
        modes = []
        for (mode, enabled, priority), historic in zip(ARMS, prior['modes']):
            baseline = _arm(native_executor, plan_type, changed, fabric, plans,
                            f'v2i-native/{label}/{mode}', enabled, priority,
                            digest, data)
            require(baseline['whole_result_sha256'] ==
                    historic['whole_result_sha256'],
                    'v2i pinned-native historical drift')
            derived, s, transport, callsites = _derived_arm(
                source, native_executor, plan_type, changed, fabric, plans,
                enabled, priority, digest, data)
            require(derived == baseline and
                    callsites == historic['callsite_counts'] and
                    s['delivered_controls'] ==
                    historic['actor_port']['control_delivered'],
                    'v2i native report, callsite or predecessor delivery drift')
            for key in totals:
                totals[key] += s[key]
            interventions = {}
            for policy in ('loss', 'pressure'):
                stress, stressed, control, _ = _derived_arm(
                    source, native_executor, plan_type, changed, fabric,
                    plans, enabled, priority, digest, data, policy=policy)
                require(stress == baseline,
                        'v2i receipt loss/bounded pressure altered frozen forward')
                interventions[policy] = {
                    'actor_receipts':stressed['derived_actor_batch_receipts'],
                    'unconsumed':stressed['unconsumed_delivered_controls'],
                    'lost_controls':control['lost'],
                    'receipt_pressure':stressed['receipt_pressure'],
                    'per_batch_pressure':stressed['per_batch_pressure'],
                }
            modes.append({'mode':mode, 'native_result_parity':True,
                          'whole_result_sha256':baseline['whole_result_sha256'],
                          'actor_intake':s, 'interventions':interventions})
        rows.append({'label':label,'recipe':[list(x) for x in recipe],
                     'modes':modes})
        require(snapshot(original) == unchanged,
                'v2i altered original native fixture')
    block = (('ACC',(1,0)), ('CMP',100), ('EMIT',7), ('RESET',0))
    negative = replace(case, nodes=tuple(
        replace(node, instructions=block) if node.node_id == 'B' else node
        for node in case.nodes))
    negative_data = (negative, fabric, tuple(plans))
    negative_digest = snapshot(negative_data)
    native_negative = _arm(native_executor, plan_type, negative, fabric, plans,
                           'v2i-negative-original', True, 'forward-first',
                           negative_digest, negative_data)
    derived_negative, negative_intake, negative_port, _ = _derived_arm(
        source, native_executor, plan_type, negative, fabric, plans,
        True, 'forward-first', negative_digest, negative_data)
    require(native_negative == derived_negative and
            negative_port['negative_judgments'] == 2 and
            negative_port['credit_by_sender'] == {'A':-2} and
            negative_intake['delivered_controls'] == 2 and
            negative_intake['credit_by_actor']['A'] <= 0 and
            negative_intake['absence_certificates'] == 0,
            'v2i negative receiver provenance or parity failed')
    require(source_pins(root) == pins_before and
            read_pinned_sources(root) == architecture_before and
            read_pinned_source(root) == source and
            snapshot(original) == unchanged,
            'v2i source custody drift')
    return {'matrix':rows, 'totals':totals,
            'negative_fixture':{
                'delivered_negative_judgments':2,
                'derived_actor_receipts':negative_intake['derived_actor_batch_receipts'],
                'unconsumed_delivered':negative_intake['unconsumed_delivered_controls'],
                'actor_credit':negative_intake['credit_by_actor'],
            },
            'original_runs':46, 'derived_normal_runs':46,
            'derived_loss_runs':45, 'derived_pressure_runs':45,
            'full_native_parity_cells':45,
            'native_source_custody':True}


def build_report(previous, raw, result=None):
    validate_v2h(previous, raw)
    require(result is None or
            (result['native_source_custody'] and
             result['full_native_parity_cells'] == 45 and
             result['original_runs'] == 46 and
             result['derived_normal_runs'] == 46 and
             result['derived_loss_runs'] == 45 and
             result['derived_pressure_runs'] == 45),
            'v2i derived native execution not admissible')
    return {
        'schema':SCHEMA,
        'status':STATUS if result else CONTRACT_STATUS,
        'source_kind':'PINNED_DERIVED_COMMITTED_ACTOR_BATCH' if result else
                      'PREDECESSOR_ONLY_CONTRACT',
        'reference_v2h_sha256':sha256(raw).hexdigest(),
        'frozen_native_source_pins_rechecked_in_this_run':bool(result),
        'new_original_native_runs':result['original_runs'] if result else 0,
        'new_derived_normal_runs':result['derived_normal_runs'] if result else 0,
        'new_derived_loss_runs':result['derived_loss_runs'] if result else 0,
        'new_derived_receipt_pressure_runs':result['derived_pressure_runs'] if result else 0,
        'full_native_result_parity_cells':result['full_native_parity_cells'] if result else 0,
        'actor_intake_totals':result['totals'] if result else None,
        'paired_native_matrix':result['matrix'] if result else None,
        'negative_native_fixture':result['negative_fixture'] if result else None,
        'committed_derived_actor_batch_receipt_observed':bool(result and
            result['totals']['derived_actor_batch_receipts'] > 0),
        'frozen_native_actor_intake_observed':False,
        'native_actor_service_resources_accounted':False,
        'native_learner_updates':0,
        'native_learning_proven':False,
        'next_gate':'BLOCKED_FROZEN_ACTOR_INTAKE_CONTRACT_AND_RESOURCE_SERVICE',
        'claims_excluded':list(EXCLUSIONS),
    }
