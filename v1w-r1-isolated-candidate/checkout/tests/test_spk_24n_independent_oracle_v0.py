"""Independent interpreter tests: work without any installed SPK packages."""
from dataclasses import replace
from itertools import product

import pytest

from search.spk_24n_independent_oracle_v0 import (
    CaseV0, EdgeV0, EventV0, NodeV0, OracleDomainErrorV0,
    OracleLimitV0, execute_v0, relay_path_support_v0,
)

RELAY = (("ACC", (1, 0)), ("CMP", 1), ("EMIT", 7), ("RESET", 0))
T2 = (("ACC", (1, 0)), ("CMP", 2), ("EMIT", 7), ("RESET", 0))


def n(name, ops=RELAY, raw=0):
    return NodeV0(name, 8, 0, raw, ops)


def ref():
    return CaseV0((n('A'), n('B')), (
        EdgeV0('A', 7, 'B', 0, 3), EdgeV0('A', 7, 'B', 0, 2),
        EdgeV0('A', 7, 'B', 0, 2),
    ), (EventV0(2, 'A', 0),))


def events(report):
    return [(x['timestamp'], x['node_id'], x['channel']) for x in report['emissions']]


def test_original_reference_exact_oracle():
    a = execute_v0(ref())
    assert a['processed_batches'] == 3
    assert a['processed_events'] == 4
    assert events(a) == [(2, 'A', 7), (4, 'B', 7), (5, 'B', 7)]
    assert a['terminal_outputs'] == [
        {'timestamp': 4, 'node_id': 'B', 'channel': 7},
        {'timestamp': 5, 'node_id': 'B', 'channel': 7},
    ]
    assert a['states'] == [
        {'node_id': 'A', 'raw': 0, 'last_timestamp': 2},
        {'node_id': 'B', 'raw': 0, 'last_timestamp': 5},
    ]
    assert len(a['observations']['routes']) == 3
    assert [b['channels'] for b in a['observations']['batches']] == [[0], [0, 0], [0]]


def test_duplicate_external_events_are_one_batch():
    x = replace(ref(), events=(EventV0(2, 'A', 0),) * 2)
    a = execute_v0(x)
    assert a['processed_events'] == 5
    assert a['processed_batches'] == 3
    assert len(a['emissions']) == 3
    assert a['observations']['batches'][0]['channels'] == [0, 0]


def test_empty_inputs_keep_initial_state():
    x = CaseV0((n('A', (('ACC', (1, 0)),), 17),), (), ())
    a = execute_v0(x)
    assert a['states'] == [{'node_id': 'A', 'raw': 17, 'last_timestamp': 0}]
    assert a['processed_batches'] == a['processed_events'] == 0


def test_acc_persists_without_reset():
    x = CaseV0((n('A', (('ACC', (3, 0)),)),), (),
               (EventV0(1, 'A', 0), EventV0(2, 'A', 0)))
    a = execute_v0(x)
    assert a['states'][0]['raw'] == 6
    assert a['observations']['batches'][1]['final_guard'] is False


def test_threshold_two_accumulates_across_batches():
    x = CaseV0((n('A', T2),), (),
               (EventV0(1, 'A', 0), EventV0(3, 'A', 0)))
    a = execute_v0(x)
    assert events(a) == [(3, 'A', 7)]
    assert a['states'][0]['raw'] == 0
    assert [b['final_guard'] for b in a['observations']['batches']] == [False, True]


def test_shift_uses_per_node_delta_and_initial_timestamp_zero():
    x = CaseV0((n('A', (('SHIFT', 1),), 8), n('B', (('SHIFT', 1),), 8)),
               (), (EventV0(2, 'A', 0), EventV0(4, 'B', 0)))
    a = execute_v0(x)
    assert [(s['node_id'], s['raw'], s['last_timestamp']) for s in a['states']] == [
        ('A', 2, 2), ('B', 0, 4),
    ]


def test_fractional_scale_and_guard_overwrite():
    x = CaseV0((NodeV0('A', 8, 2, 0, (("ACC", (2, 0)),
        ("CMP", 5), ("CMP", 9), ("EMIT", 7))),), (), (EventV0(0, 'A', 0),))
    a = execute_v0(x)
    assert a['states'][0]['raw'] == 8
    assert a['emissions'] == []


def test_two_emissions_of_same_channel_keep_multiplicity():
    ops = (("ACC", (1, 0)), ("CMP", 1), ("EMIT", 7), ("EMIT", 7))
    x = CaseV0((n('A', ops),), (), (EventV0(1, 'A', 0),))
    assert len(execute_v0(x)['terminal_outputs']) == 2


def test_positive_delay_cycle_hits_declared_budget():
    x = CaseV0((n('A'), n('B')), (
        EdgeV0('A', 7, 'B', 0, 1), EdgeV0('B', 7, 'A', 0, 1),
    ), (EventV0(0, 'A', 0),))
    with pytest.raises(OracleLimitV0, match='max_events'):
        execute_v0(x, max_events=5)


@pytest.mark.parametrize('budget,limit', [('max_batches', 2), ('max_events', 3)])
def test_limits_on_original_reference(budget, limit):
    kwargs = {budget: limit}
    with pytest.raises(OracleLimitV0, match=budget):
        execute_v0(ref(), **kwargs)


@pytest.mark.parametrize('case', [
    CaseV0((n('A'), n('A')), (), ()),
    CaseV0((n('A'),), (EdgeV0('A', 7, 'B', 0, 1),), ()),
    CaseV0((n('A'),), (EdgeV0('A', 7, 'A', 0, 0),), ()),
    CaseV0((n('A'),), (), (EventV0(0, 'B', 0),)),
    CaseV0((n('A', (("MAGIC", 1),)),), (), ()),
    CaseV0((n('A', (("ACC", (1, 0)),), 255),), (), (EventV0(1, 'A', 0),)),
    CaseV0((n('A'),), (), (EventV0(-1, 'A', 0),)),
    CaseV0((NodeV0('A', 8, 9, 0, RELAY),), (), ()),
])
def test_invalid_or_overflow_cases_rejected(case):
    with pytest.raises(OracleDomainErrorV0):
        execute_v0(case)


def test_path_support_separate_from_operational_engine_4_node_dags():
    names = 'ABCD'
    slots = [('A','B'), ('A','C'), ('A','D'),
             ('B','C'), ('B','D'), ('C','D')]
    nodes = tuple(n(x) for x in names)
    inputs = (EventV0(0, 'A', 0), EventV0(2, 'A', 0), EventV0(2, 'A', 0))
    # Exhaustive three choices per edge: 3^6 = 729 networks.
    for delays in product((0, 1, 2), repeat=6):
        edges = tuple(EdgeV0(a, 7, b, 0, d) for (a,b),d in zip(slots,delays) if d)
        case = CaseV0(nodes, edges, inputs)
        algebra = relay_path_support_v0(case)
        runtime = execute_v0(case)
        for name in names:
            assert tuple(sorted(e['timestamp'] for e in runtime['emissions']
                                if e['node_id'] == name)) == algebra[name], (delays, name)


def test_path_support_parallel_routes_merge_only_at_batch():
    x = ref()
    assert relay_path_support_v0(x) == {'A': (2,), 'B': (4,5)}
    assert execute_v0(x)['observations']['batches'][1]['channels'] == [0,0]


def test_algebra_rejects_cycle_and_nonrelay():
    cycle = CaseV0((n('A'),), (EdgeV0('A',7,'A',0,1),), ())
    with pytest.raises(OracleDomainErrorV0, match='DAG'):
        relay_path_support_v0(cycle)
    with pytest.raises(OracleDomainErrorV0, match='relay'):
        relay_path_support_v0(CaseV0((n('A',T2),), (), ()))


def test_differential_projection_with_fake_frozen_shaped_inputs():
    from dataclasses import dataclass
    from search.spk_24n_differential_evidence_v0 import (
        compare_actual_v0, DifferentialMismatchV0,
    )

    @dataclass
    class CoreAcc:
        weight: int
        channel: int

    @dataclass
    class CoreCmp:
        threshold_raw: int

    @dataclass
    class CoreEmit:
        channel_out: int

    @dataclass
    class CoreReset:
        value_raw: int

    @dataclass
    class Config:
        state_bits: int = 8
        fractional_bits: int = 0

    @dataclass
    class Program:
        instructions: tuple = (CoreAcc(1,0), CoreCmp(1), CoreEmit(7), CoreReset(0))

    @dataclass
    class Node:
        node_id: str = 'A'
        config: Config = None
        program: Program = None
        initial_raw: int = 0

    class Network:
        nodes = (Node('A', Config(), Program()),)
        edges = ()

    @dataclass
    class Event:
        timestamp: int
        node_id: str
        channel: int

    events = (Event(2, 'A', 0),)
    full = execute_v0(CaseV0((n('A'),), (), (EventV0(2,'A',0),)))
    trace = full['observations']
    report = compare_actual_v0(Network(), events, full, trace['batches'], trace['routes'])
    assert report['status'] == 'PASS'
    bad = dict(full, processed_events=999)
    with pytest.raises(DifferentialMismatchV0, match='processed_events'):
        compare_actual_v0(Network(), events, bad, trace['batches'], trace['routes'])
