"""Exact signed-source native replay and persisted SQLite event-root audit."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from hashlib import sha256

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e, execute_live_v0e,
)
from spk_bv_research.grant_rank_integration_v3tuv import (
    ARMS, CAPACITIES, NEW_SCHEDULES,
)
from spk_bv_research.native_ack_causal_replay_v4mno import CausalProbeRejected
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import snapshot
from spk_bv_research.task_disagreement_v4aeag import digest
from spk_bv_research.task_disagreement_fixture_v4aeag import (
    TEST_VIEW_KEYS, VARIANTS as PRIOR_VARIANTS, project_actual_native,
)
from spk_bv_research.task_escrow_fixture_v4ahaj import (
    VARIANTS, EXPECT, run_sequence,
)
from spk_bv_research.task_escrow_store_v4ahaj import (
    STATUS, SCHEMA, DurableEscrow,
)

SIGNED_V3_SHA = 'f783be9952613aa98eafef59d24c19eb64ccc09d29265017eabb675fe0155827'
SIGNED_V4AEAG_SHA = '01211a6cdc2f8efc707514c56934b7c980f001bd22d4ed3df586ace2db5ff152'


def require(condition, message):
    if not condition:
        raise CausalProbeRejected(message)


def evaluate(v3, raw3, previous, raw_previous, *, db_path,
             fixture_fn=fixture, native_executor=execute_live_v0e):
    require(type(v3) is dict and type(previous) is dict and
            type(raw3) is bytes and type(raw_previous) is bytes and
            canon(v3) == raw3 and canon(previous) == raw_previous and
            sha256(raw3).hexdigest() == SIGNED_V3_SHA and
            sha256(raw_previous).hexdigest() == SIGNED_V4AEAG_SHA and
            previous['signed_v3tuv_sha256'] == SIGNED_V3_SHA and
            previous['program_adoptions'] == 0 and
            previous['native_learning_implemented'] is False and
            previous['totals']['signed_native_replays'] == 18 and
            previous['totals']['counterfactual_native_probe_executions'] == 72 and
            previous['totals']['adjudication_scenarios'] == 270 and
            previous['reviewer_conflicts_quarantined'] == 18 and
            previous['reviewer_abstentions_quarantined'] == 18,
            'persistent escrow signed source/parent drift')
    parent = sha256(raw_previous).hexdigest()
    with DurableEscrow.create(db_path, parent, TEST_VIEW_KEYS):
        pass
    rows = []
    totals = Counter()
    evaluated = 0
    for signed, (schedule, ticks) in zip(v3['source_matrix'], NEW_SCHEDULES):
        require(signed['schedule'] == schedule and
                signed['source_external_ticks'] == list(ticks),
                'persistent escrow signed schedule mismatch')
        case, fabric, plans = fixture_fn(ticks=ticks)
        for signed_mode, (mode, enabled, priority) in zip(signed['modes'], ARMS):
            require(signed_mode['mode'] == mode,
                    'persistent escrow signed mode mismatch')
            for signed_capacity, capacity in zip(signed_mode['capacities'], CAPACITIES):
                require(signed_capacity['native_PE_capacity'] == capacity,
                        'persistent escrow fabric capacity mismatch')
                pp = replace(plans[1], fabric_slots_per_tick=capacity)
                active_plans = (plans[0], pp, plans[2], plans[3])
                bv = LiveBVPlanV0e(enabled=enabled, priority=priority)
                original = native_executor(case, fabric, *active_plans, bv)
                source_sha = snapshot(original)
                require(source_sha == signed_capacity['original_native_sha256'],
                        'persistent escrow original native SHA drift')
                projections, completed = project_actual_native(
                    case, fabric, active_plans, bv,
                    native_executor=native_executor)
                prior = previous['scenarios'][evaluated * len(PRIOR_VARIANTS)]
                require(prior['schedule'] == schedule and
                        prior['mode'] == mode and
                        prior['native_global_PE_capacity'] == capacity and
                        prior['witness']['variant'] == 'two_view_consistency' and
                        prior['witness']['decision']['verdict'] ==
                        'CONSISTENT_CORRELATED_TEST_VIEWS_NO_EXTERNAL_TRUST' and
                        prior['witness']['projection_sha256'] == {
                            view: digest(projections[view])
                            for view in ('endpoint', 'emission')},
                        'persistent escrow prior observations mismatch')
                source_key = f'{schedule}/{mode}/{capacity}'
                decisions = run_sequence(db_path, projections, source_key,
                                         source_sha, parent,
                                         case.events[0].timestamp, completed)
                require([r['variant'] for r in decisions] == list(VARIANTS) and
                        [r['verdict'] for r in decisions] ==
                        [EXPECT[variant] for variant in VARIANTS],
                        'persistent escrow adjudication order drift')
                totals['signed_native_replays'] += 1
                totals['counterfactual_native_probes'] += 4
                for decision in decisions:
                    totals['custody_attempts'] += 1
                    totals['verdict_' + decision['verdict']] += 1
                    totals['journaled'] += int(decision['journaled'])
                rows.append({'schedule': schedule, 'mode': mode,
                             'native_global_PE_capacity': capacity,
                             'original_native_sha256': source_sha,
                             'decisions': decisions})
                evaluated += 1
    with DurableEscrow.open(db_path, parent, TEST_VIEW_KEYS) as store:
        proof = store.verify()
    require(len(v3['source_matrix']) == 3 and evaluated == 18 and
            totals['signed_native_replays'] == 18 and
            totals['counterfactual_native_probes'] == 72 and
            totals['custody_attempts'] == 198 and
            totals['journaled'] == 72 and
            proof['entries'] == 72 and
            proof['persisted_unique_nonces'] == 144 and
            all(totals['verdict_' + verdict] >= 18
                for verdict in set(EXPECT.values())),
            'persistent escrow source matrix/custody incomplete')
    # The caller can retain head externally and later demand this exact value.
    with DurableEscrow.open(db_path, parent, TEST_VIEW_KEYS,
                            external_head=proof['head']) as store:
        require(store.verify(external_head=proof['head']) == proof,
                'externally anchored escrow audit mismatch')
    return {
        'schema': SCHEMA, 'status': STATUS,
        'signed_v3tuv_sha256': sha256(raw3).hexdigest(),
        'signed_v4aeag_sha256': parent,
        'database_contract': 'SQLITE_PRIVATE_SINGLE_HOST_TRANSACTIONAL_RESEARCH',
        'replay_scope': 'ON_DISK_RESTART_PERSISTENT_ONE_HOST',
        'durability_coverage': 'ATOMIC_SQLITE_COMMIT_ROLLBACK_AND_REOPEN_TESTS',
        'external_trust_anchor': 'REPORT_HEAD_MUST_BE_STORED_OUTSIDE_MUTABLE_DATABASE',
        'test_key_trust': 'PUBLIC_FIXTURE_KEYS_NOT_PRODUCTION_IDENTITY',
        'semantic_limit': 'PERSISTENCE_DOES_NOT_CORRECT_CORRELATED_TASK_LABELS',
        'tested_variants': list(VARIANTS),
        'totals': dict(sorted(totals.items())),
        'scenario_rows_sha256': digest(rows),
        'scenarios': rows,
        'sqlite_logical_witness': proof,
        'program_adoptions': 0, 'native_learning_implemented': False,
        'native_v0e_modified': False, 'architecture_v1_modified': False,
        'claims_excluded': [
            'no real external reviewer identity or independent task truth',
            'public test-role HMAC keys cannot stop an impersonating adversary',
            'unanchored database hash chains can be rewritten by storage owner',
            'SQLite local durability is not a replicated consensus protocol',
            'injected exceptions do not prove power-loss/fsync hardware behavior',
            'zero candidate adoptions, frozen updates or physical energy claims',
        ],
        'next_gate': 'REAL_INDEPENDENT_HOLDOUT_WITH_PROVISIONED_TRUST_ROOT',
    }
