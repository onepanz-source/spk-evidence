"""SPK 24w: purely structural, independent, source-pinned metamorphic plan.

No frozen SPK import and no execution of the frozen runtime. Transformations
are bijective renamings and/or tuple re-orderings, never lossy graph rewrites.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from collections import Counter
from search.spk_24n_differential_evidence_v0 import canonical, sha, project_v0
from search.spk_24n_independent_oracle_v0 import CaseV0, execute_v0
from search.spk_24o_semantic_corpus_v0 import catalog_v0, catalog_fingerprint_v0

SCHEMA = 'spk-structural-metamorphic-plan/v0'
SOURCE_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
VARIANTS = ('cycle_and_reverse', 'swap_ac', 'reverse_order')
NAMES = ('A', 'B', 'C')
_MAPS = {
    'cycle_and_reverse': {'A': 'B', 'B': 'C', 'C': 'A'},
    'swap_ac': {'A': 'C', 'B': 'B', 'C': 'A'},
    'reverse_order': {'A': 'A', 'B': 'B', 'C': 'C'},
}


def checked_catalog_v0():
    cases = catalog_v0()
    if len(cases) != 216 or catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('24w source corpus drift')
    if len(set(k for k, _ in cases)) != 216:
        raise AssertionError('24w duplicate case ids')
    return cases


def renaming_v0(variant):
    if variant not in _MAPS:
        raise ValueError('unknown metamorphic variant: ' + str(variant))
    mapping = dict(_MAPS[variant])
    if set(mapping) != set(NAMES) or set(mapping.values()) != set(NAMES):
        raise AssertionError('metamorphic renaming is not bijective')
    return mapping


def transform_v0(case, variant):
    """Bijection of names, preserving all edge and event *multiplicities*."""
    if type(case) is not CaseV0:
        raise TypeError('case must be a primitive CaseV0')
    m = renaming_v0(variant)
    if {n.node_id for n in case.nodes} != set(NAMES):
        raise ValueError('24w transform domain: three A/B/C neurons')
    nodes = tuple(replace(n, node_id=m[n.node_id]) for n in case.nodes)
    edges = tuple(replace(e, source_node=m[e.source_node],
                          target_node=m[e.target_node]) for e in case.edges)
    events = tuple(replace(e, node_id=m[e.node_id]) for e in case.events)
    if variant in ('cycle_and_reverse', 'reverse_order'):
        nodes, edges, events = nodes[::-1], edges[::-1], events[::-1]
    transformed = CaseV0(nodes, edges, events)
    # Non-lossy structural contract: no dropped/duplicated inputs or wires.
    if (len(transformed.nodes), len(transformed.edges), len(transformed.events)) != (
            len(case.nodes), len(case.edges), len(case.events)):
        raise AssertionError('metamorphic transformation lost graph elements')
    return transformed


def _rewrite_record(record, inverse):
    if type(record) is not dict:
        raise TypeError('projection record must be an object')
    out = dict(record)
    for key in ('node_id', 'source_node', 'target_node'):
        if key in out:
            if out[key] not in inverse:
                raise ValueError('unexpected neuron identifier: ' + str(out[key]))
            out[key] = inverse[out[key]]
    return out


def inverse_projection_v0(projection, variant):
    """Normalize a projected transformed execution to original identifiers.

    Node names occur only at three documented primitive observation positions;
    all counts, timestamps, raw states and multiplicities remain untouched.
    """
    from search.spk_24n_differential_evidence_v0 import strict_json
    mapping = renaming_v0(variant)
    inverse = {b: a for a, b in mapping.items()}
    expected = {'emissions', 'terminal_outputs', 'states', 'processed_batches',
                'processed_events', 'observations'}
    if type(projection) is not dict or set(projection) != expected:
        raise ValueError('unexpected projection structure')
    obs = projection['observations']
    if type(obs) is not dict or set(obs) != {'batches', 'routes'}:
        raise ValueError('unexpected observation structure')
    def inv_rows(rows):
        return sorted(canonical(_rewrite_record(strict_json(x), inverse)) for x in rows)
    return {
        'emissions': inv_rows(projection['emissions']),
        'terminal_outputs': inv_rows(projection['terminal_outputs']),
        'states': sorted([inverse[node], raw, timestamp] for node, raw, timestamp
                         in projection['states']),
        'processed_batches': projection['processed_batches'],
        'processed_events': projection['processed_events'],
        'observations': {
            'batches': inv_rows(obs['batches']),
            'routes': inv_rows(obs['routes']),
        },
    }


def oracle_projection_v0(case):
    result = execute_v0(case, max_batches=128, max_events=4096)
    return project_v0(result, result['observations']['batches'],
                      result['observations']['routes'])


def assert_pure_equivalence_v0(case, variant):
    original = oracle_projection_v0(case)
    mutated = transform_v0(case, variant)
    actual = inverse_projection_v0(oracle_projection_v0(mutated), variant)
    if actual != original:
        raise AssertionError('independent oracle violates structural equivalence: ' + variant)
    return sha(canonical(actual))


def plan_v0():
    cases = checked_catalog_v0()
    return tuple((cid, variant) for cid, _ in cases for variant in VARIANTS)


def summary_v0():
    return {'schema': SCHEMA, 'source_sha256': SOURCE_SHA256,
            'source_cases': len(checked_catalog_v0()),
            'variants': len(VARIANTS), 'metamorphic_cases': len(plan_v0())}


def identity_v0():
    return sha(canonical({
        'summary': summary_v0(),
        'mappings': {name: renaming_v0(name) for name in VARIANTS},
        'entries': plan_v0(),
    }))
