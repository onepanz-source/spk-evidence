"""SPK 24u: independent traceability and sample plan across S3-S5.

This planning module has NO frozen SPK dependencies and makes no assertion
about compiler acceptance, which must be measured on fwork.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from search.spk_24o_semantic_corpus_v0 import catalog_v0, catalog_fingerprint_v0
from search.spk_24q_limit_probe_plan_v0 import probes_for_case_v0
from search.spk_24s_budget_triads_v0 import plan_v0 as causal_plan_v0

SCHEMA = 'spk-cross-layer-conformance-plan/v0'
EXPECTED_CORPUS_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'


@dataclass(frozen=True)
class PlannedCaseV0:
    case_id: str
    profile: str
    graph: str
    input_kind: str
    boundary_kinds: tuple[str, ...]
    dual_controls: tuple[str, ...]


def entries_v0():
    cases = catalog_v0()
    if catalog_fingerprint_v0() != EXPECTED_CORPUS_SHA256 or len(cases) != 216:
        raise AssertionError('24o corpus identity changed; refuse silent drift')
    causal = {cid: controls for cid, _, controls in causal_plan_v0()}
    result = []
    for cid, case in cases:
        profile, graph, input_kind = cid.split('/')
        limits = probes_for_case_v0(cid, case)
        # A small, spread-out subset additionally exercises the versioned
        # manifest host with boundary budgets and causal diagnostics.
        boundary = tuple(p.kind for p in limits) if input_kind == 'duplicate' else ()
        dual = tuple(c.condition for c in causal[cid]) if (
            input_kind == 'duplicate' and cid in causal
        ) else ()
        result.append(PlannedCaseV0(cid, profile, graph, input_kind,
                                    boundary, dual))
    return tuple(result)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def sha(value):
    return sha256(value.encode('utf-8')).hexdigest()


def summary_v0():
    entries = entries_v0()
    return {'schema': SCHEMA, 'corpus_sha256': EXPECTED_CORPUS_SHA256,
            'source_cases': len(entries),
            'profiles': sorted({e.profile for e in entries}),
            'topologies': sorted({e.graph for e in entries}),
            'input_kinds': sorted({e.input_kind for e in entries}),
            'selected_budget_cases': sum(bool(e.boundary_kinds) for e in entries),
            'selected_budget_probes': sum(len(e.boundary_kinds) for e in entries),
            'selected_causal_cases': sum(bool(e.dual_controls) for e in entries),
            'selected_causal_probes': sum(len(e.dual_controls) for e in entries)}


def identity_v0():
    from dataclasses import asdict
    return sha(canonical({'summary': summary_v0(),
                          'plan': [asdict(e) for e in entries_v0()]}))
