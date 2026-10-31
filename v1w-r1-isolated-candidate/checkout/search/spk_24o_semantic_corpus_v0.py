"""24o deterministic, bounded, *primitive* semantic corpus.

No frozen SPK imports. Corpus construction never consults the expected or actual
runtime result. The frozen adapter is in a separate module.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from itertools import product
import json

from search.spk_24n_independent_oracle_v0 import CaseV0, EdgeV0, EventV0, NodeV0

SCHEMA = 'spk-semantic-corpus/v0'
RELAY = (('ACC', (1, 0)), ('CMP', 1), ('EMIT', 7), ('RESET', 0))
THRESHOLD2 = (('ACC', (1, 0)), ('CMP', 2), ('EMIT', 7), ('RESET', 0))
PERSIST = (('ACC', (1, 0)),)
DECAY = (('SHIFT', 1), ('ACC', (1, 0)), ('CMP', 2), ('EMIT', 7), ('RESET', 0))
DUAL_EMIT = (('ACC', (1, 0)), ('CMP', 1), ('EMIT', 7), ('EMIT', 8), ('RESET', 0))
OVERWRITE = (('ACC', (1, 0)), ('CMP', 1), ('CMP', 3), ('EMIT', 7), ('RESET', 0))

# Directed DAGs: some include parallel edges, fanout, fan-in, and delayed paths.
GRAPHS = (
    ('isolated', ()),
    ('single', (('A', 'B', 1),)),
    ('chain', (('A', 'B', 1), ('B', 'C', 2))),
    ('parallel', (('A', 'B', 2), ('A', 'B', 2), ('B', 'C', 3))),
    ('fork', (('A', 'B', 2), ('A', 'C', 3))),
    ('diamond', (('A', 'B', 1), ('B', 'C', 2), ('A', 'C', 4))),
)

# Explicitly bounded, non-random work. Multiple channels and timestamp order.
INPUTS = (
    ('idle', ()),
    ('at_zero', ((0, 'A', 0),)),
    ('duplicate', ((2, 'A', 0), (2, 'A', 0))),
    ('separated', ((1, 'A', 0), (4, 'A', 0), (7, 'A', 0))),
    ('interleaved', ((3, 'C', 0), (2, 'A', 0), (2, 'B', 0))),
    ('channels', ((5, 'A', 1), (5, 'A', 0), (1, 'C', 0))),
)

# Configured so every successful sample remains inside 8-bit Core state.
PROFILES = (
    ('relays', ((RELAY, 0, 0), (RELAY, 0, 0), (RELAY, 0, 0))),
    ('threshold', ((RELAY, 0, 0), (THRESHOLD2, 0, 0), (PERSIST, 0, 0))),
    ('decay', ((RELAY, 0, 0), (DECAY, 8, 0), (RELAY, 0, 0))),
    ('double_emit', ((DUAL_EMIT, 0, 0), (RELAY, 0, 0), (THRESHOLD2, 0, 0))),
    ('guard_overwrite', ((RELAY, 0, 0), (OVERWRITE, 1, 0), (PERSIST, 2, 0))),
    ('fractional', ((RELAY, 0, 0), (THRESHOLD2, 0, 0),
                     ((('ACC', (1, 0)), ('CMP', 4), ('EMIT', 7), ('RESET', 0)), 0, 2))),
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(',', ':'))


def digest(text):
    return sha256(text.encode('utf-8')).hexdigest()


def corpus_v0():
    """216 deterministic cases; 3 nodes / finite DAG / 8-bit Core with fractional variants."""
    for (pname, profiles), (gname, graph), (ename, events) in product(
        PROFILES, GRAPHS, INPUTS,
    ):
        nodes = tuple(NodeV0(nid, 8, fraction, initial, instructions)
                      for nid, (instructions, initial, fraction) in zip('ABC', profiles))
        edges = tuple(EdgeV0(a, 7, b, 0, ticks) for a, b, ticks in graph)
        incoming = tuple(EventV0(t, node, channel) for t, node, channel in events)
        yield f'{pname}/{gname}/{ename}', CaseV0(nodes, edges, incoming)


def catalog_v0():
    return tuple(corpus_v0())


def catalog_fingerprint_v0():
    return digest(canonical({
        'schema': SCHEMA,
        'cases': [(name, asdict(case)) for name, case in catalog_v0()],
    }))


def relay_time_translation_v0(case, delta):
    """Pure fixture transformation; only semantically valid for reset relays."""
    if type(delta) is not int or delta < 0:
        raise ValueError('delta must be a nonnegative integer')
    if any(n.instructions != RELAY or n.initial_raw != 0 or n.fractional_bits != 0
           for n in case.nodes):
        raise ValueError('time translation requires zero-state unit relays')
    return CaseV0(case.nodes, case.edges,
                  tuple(EventV0(e.timestamp + delta, e.node_id, e.channel)
                        for e in case.events))
