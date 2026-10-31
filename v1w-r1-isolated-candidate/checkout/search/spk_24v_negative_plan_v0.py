"""SPK 24v: source-pinned negative admission and observer fault plan.

Pure plan: does not import or execute frozen Compiler/Network. All mutations
are intentional INVALID requests, not new admitted network semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_v0, catalog_fingerprint_v0

SCHEMA = 'spk-cross-layer-negative-plan/v0'
EXPECTED_CORPUS = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
MUTATIONS = (
    'wrong_pin',
    'malformed_pin',
    'zero_batches',
    'boolean_events',
    'truncated_manifest',
    'wrong_root_shape',
    'nontext_manifest',
)
OBSERVER_FAULTS = ('throw_batch', 'drop_batch')
ROUTE_FAULTS = ('throw_route', 'drop_route')


@dataclass(frozen=True)
class NegativeCaseV0:
    case_id: str
    mutation: str


def checked_catalog_v0():
    cases = catalog_v0()
    if len(cases) != 216 or catalog_fingerprint_v0() != EXPECTED_CORPUS:
        raise AssertionError('24v refuses changed 24o source corpus')
    if len({cid for cid, _ in cases}) != 216:
        raise AssertionError('24v duplicate source id')
    return cases


def negative_plan_v0():
    return tuple(NegativeCaseV0(cid, m)
                 for cid, _ in checked_catalog_v0() for m in MUTATIONS)


def observer_plan_v0():
    # Exactly one ingress per profile x topology. Ensures a real on_batch call.
    return tuple(cid for cid, _ in checked_catalog_v0()
                 if cid.endswith('/at_zero'))


def route_plan_v0():
    # A unit relay at A emits and routes on each nonempty topology.
    return tuple(cid for cid in observer_plan_v0()
                 if cid.startswith('relays/') and '/isolated/' not in cid)


def budget_observer_plan_v0():
    # Two simultaneous ingress events guarantee max_events=1 is insufficient.
    return tuple(cid for cid, _ in checked_catalog_v0()
                 if cid.endswith('/duplicate'))


def summary_v0():
    return {
        'schema': SCHEMA, 'corpus_sha256': EXPECTED_CORPUS,
        'cases': len(checked_catalog_v0()),
        'negative_admissions': len(negative_plan_v0()),
        'mutations_per_case': len(MUTATIONS),
        'observer_batch_cases': len(observer_plan_v0()),
        'observer_route_cases': len(route_plan_v0()),
        'observer_budget_cases': len(budget_observer_plan_v0()),
        'compiler_invalid_ir_cases': len(budget_observer_plan_v0()),
    }


def identity_v0():
    return sha(canonical({
        'summary': summary_v0(),
        'mutations': MUTATIONS,
        'negative_cases': [(e.case_id, e.mutation) for e in negative_plan_v0()],
        'observer_cases': observer_plan_v0(),
        'route_cases': route_plan_v0(),
        'budget_cases': budget_observer_plan_v0(),
    }))
