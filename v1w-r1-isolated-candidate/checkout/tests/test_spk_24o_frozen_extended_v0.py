"""24o integration on the authoritative checkout: true 2-engine / observer corpus."""
from dataclasses import replace
import json

import pytest

from search.spk_24o_semantic_corpus_v0 import (
    OVERWRITE, catalog_v0, catalog_fingerprint_v0,
)
from search.spk_24n_independent_oracle_v0 import (
    CaseV0, EventV0, NodeV0, execute_v0,
)
from search.spk_24o_extended_differential_v0 import (
    SCHEMA, _admitted_instructions_v0, evaluate_case_v0, seal_v0,
    to_frozen_v0, verify_v0,
)
from search.spk_24n_differential_evidence_v0 import (
    canonical, compare_actual_v0, DifferentialMismatchV0, sha,
)
from spk_compiler.network_ir_v0 import dumps_network_ir_v0, loads_network_ir_v0
from spk_network.events_v0 import NetworkEventV0
from spk_network.runtime_v0 import NetworkExecutionLimitV0, run_network_v0

CASES = catalog_v0()



def test_guard_overwrite_admission_keeps_original_primitive_semantics():
    # Deliberately noncanonical source remains in the versioned corpus.
    assert OVERWRITE == (('ACC', (1, 0)), ('CMP', 1), ('CMP', 3),
                         ('EMIT', 7), ('RESET', 0))
    admitted = _admitted_instructions_v0(OVERWRITE)
    assert admitted == (('ACC', (1, 0)), ('CMP', 3), ('EMIT', 7), ('RESET', 0))
    assert _admitted_instructions_v0(admitted) == admitted  # idempotence
    # Exhaust every successful 8-bit pre-state with one channel-0 event.
    # At raw=1 the first comparison is true, but the second is false.
    for raw in range(255):
        original = CaseV0((NodeV0('B', 8, 0, raw, OVERWRITE),), (),
                          (EventV0(0, 'B', 0),))
        normalized = CaseV0((NodeV0('B', 8, 0, raw, admitted),), (),
                            original.events)
        expected = execute_v0(original)
        assert execute_v0(normalized) == expected, raw
        assert len(expected['emissions']) == int(raw >= 2), raw
        assert expected['states'][0]['raw'] == (0 if raw >= 2 else raw + 1), raw


def test_frozen_adapter_only_normalizes_overwritten_guards():
    case = dict(CASES)['guard_overwrite/isolated/idle']
    assert case.nodes[1].instructions == OVERWRITE
    frozen, _ = to_frozen_v0(case)
    # Admission must not mutate the raw independent corpus or other programs.
    assert case.nodes[1].instructions == OVERWRITE
    assert tuple(type(ins).__name__ for ins in frozen.nodes[1].program.instructions) == (
        'CoreAcc', 'CoreCmp', 'CoreEmit', 'CoreReset',
    )
    assert frozen.nodes[1].program.instructions[1].threshold_raw == 3
    for frozen_node, source_node in zip(frozen.nodes, case.nodes):
        if source_node.node_id != 'B':
            assert len(frozen_node.program.instructions) == len(source_node.instructions)

@pytest.mark.parametrize('profile', sorted({name.split('/')[0] for name, _ in CASES}))
def test_full_corpus_differential_and_observer_noninterference(profile):
    tested = []
    for name, case in CASES:
        if name.split('/')[0] != profile:
            continue
        record = evaluate_case_v0(case)
        assert record['observer_noninterference'] is True, name
        assert record['processed_events'] >= len(case.events), name
        assert len(record['result_sha256']) == 64, name
        tested.append(name)
    assert len(tested) == 36


@pytest.mark.parametrize('graph', sorted({name.split('/')[1] for name, _ in CASES}))
def test_frozen_input_order_permutation_on_every_profile(graph):
    count = 0
    for name, case in CASES:
        if name.split('/')[1] != graph:
            continue
        result = evaluate_case_v0(case)
        reverse = evaluate_case_v0(replace(case, events=tuple(reversed(case.events))))
        assert reverse == result, name
        count += 1
    assert count == 36


@pytest.mark.parametrize('profile', sorted({name.split('/')[0] for name, _ in CASES}))
def test_declarative_network_ir_codec_roundtrip_on_expanded_profiles(profile):
    seen = 0
    for name, case in CASES:
        if name.split('/')[0] != profile or not name.endswith('/duplicate'):
            continue
        network, events = to_frozen_v0(case)
        source = dumps_network_ir_v0(network)
        decoded = loads_network_ir_v0(source)
        assert decoded == network, name
        assert run_network_v0(decoded, events) == run_network_v0(network, events), name
        seen += 1
    assert seen == 6


def test_execution_budget_success_boundary_and_fail_closed():
    case = dict(CASES)['relays/parallel/at_zero']
    net, events = to_frozen_v0(case)
    finished = run_network_v0(net, events, max_events=4, max_batches=3)
    assert finished.processed_events == 4
    assert finished.processed_batches == 3
    for name, opts in (
        ('max_events', dict(max_events=3, max_batches=128)),
        ('max_batches', dict(max_events=4096, max_batches=2)),
    ):
        with pytest.raises(NetworkExecutionLimitV0, match=name):
            run_network_v0(net, events, **opts)


def test_observer_route_mutation_rejected_against_independent_oracle():
    case = dict(CASES)['relays/parallel/at_zero']
    net, events = to_frozen_v0(case)
    from search.spk_24o_extended_differential_v0 import Recorder
    recorder = Recorder([], [])
    actual = run_network_v0(net, events, learning_observer=recorder)
    assert len(recorder.routes) == 3
    with pytest.raises(DifferentialMismatchV0, match='routes'):
        compare_actual_v0(net, events, actual, recorder.batches, recorder.routes[:-1])
    with pytest.raises(DifferentialMismatchV0, match='batches'):
        compare_actual_v0(net, events, actual, recorder.batches[:-1], recorder.routes)


def test_full_corpus_artifact_replay():
    doc = seal_v0()
    proof = verify_v0(doc)
    assert proof['status'] == 'PASS'
    assert proof['case_count'] == 216
    assert proof['corpus_sha256'] == catalog_fingerprint_v0()
    obj = json.loads(doc)
    assert len(obj['payload']['rows']) == 216
    assert {item['id'] for item in obj['payload']['rows']} == {name for name, _ in CASES}
    assert obj['payload']['corpus_schema'] == 'spk-semantic-corpus/v0'


def test_resealed_result_forgery_cannot_pass_reexecution():
    obj = json.loads(seal_v0())
    obj['payload']['rows'][0]['result_sha256'] = '0'*64
    obj['payload_sha256'] = sha(SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        verify_v0(canonical(obj))


def test_resealed_corpus_manifest_forgery_cannot_pass_reexecution():
    obj = json.loads(seal_v0())
    obj['payload']['corpus_sha256'] = '0'*64
    obj['payload_sha256'] = sha(SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        verify_v0(canonical(obj))


def test_strict_json_no_duplicate_keys_and_no_invisible_whitespace():
    document = seal_v0()
    with pytest.raises(ValueError, match='invalid or noncanonical'):
        verify_v0(' ' + document)
    with pytest.raises(ValueError, match='duplicate JSON'):
        verify_v0(document[:-1] + ',"schema":"forged"}')


def test_compiler_manifest_bridge_remains_independently_verified():
    from search.spk_24m_compiler_network_evidence_v0 import (
        compile_and_run_v0, reference_scenario_v0,
    )
    from search.spk_24n_differential_evidence_v0 import verify_receipt_differential_v0
    receipt = compile_and_run_v0(**reference_scenario_v0())
    comparison = verify_receipt_differential_v0(receipt)
    assert comparison['status'] == 'PASS'
    assert comparison['oracle']['processed_events'] == 4
