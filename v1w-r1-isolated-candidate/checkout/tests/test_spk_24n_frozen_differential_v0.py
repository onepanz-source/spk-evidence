"""Actual frozen-Network v0 vs separate SPK 24n Core/event interpreter."""
from dataclasses import replace
from itertools import product
import json

import pytest

from spk_core.isa import CoreAcc, CoreCmp, CoreConfig, CoreEmit, CoreProgram, CoreReset, ShiftDecay
from spk_network.events_v0 import NetworkEventV0
from spk_network.model_v0 import NetworkEdgeV0, NetworkNodeV0, NetworkV0
from spk_network.runtime_v0 import run_network_v0, NetworkExecutionLimitV0
from search.spk_24m_compiler_network_evidence_v0 import (
    compile_and_run_v0, reference_scenario_v0,
)
from search.spk_24n_independent_oracle_v0 import OracleDomainErrorV0, OracleLimitV0
from search.spk_24n_differential_evidence_v0 import (
    DifferentialMismatchV0, adapt_frozen_v0, compare_actual_v0, canonical,
    seal_differential_v0, sha, verify_differential_artifact_v0,
    verify_receipt_differential_v0,
)

CFG = CoreConfig(8, 0)
R = CoreProgram((CoreAcc(1, 0), CoreCmp(1), CoreEmit(7), CoreReset(0)))
T2 = CoreProgram((CoreAcc(1, 0), CoreCmp(2), CoreEmit(7), CoreReset(0)))
ACC = CoreProgram((CoreAcc(1, 0),))


class Recorder:
    def __init__(self):
        self.batches = []
        self.routes = []

    def on_batch(self, obs):
        self.batches.append(obs)

    def on_route(self, obs):
        self.routes.append(obs)


def check(network, events, *, max_batches=128, max_events=4096):
    observer = Recorder()
    actual = run_network_v0(network, events, max_batches=max_batches,
                            max_events=max_events, learning_observer=observer)
    expected = compare_actual_v0(network, events, actual,
                                 observer.batches, observer.routes,
                                 max_batches=max_batches, max_events=max_events)
    assert expected['status'] == 'PASS'
    return actual, observer


def node(name, program=R, raw=0, config=CFG):
    return NetworkNodeV0(name, config, program, initial_raw=raw)


def test_differential_24m_compiler_manifest_reference():
    receipt = compile_and_run_v0(**reference_scenario_v0())
    result = verify_receipt_differential_v0(receipt)
    assert result['status'] == 'PASS'
    assert result['oracle']['processed_events'] == 4
    assert result['oracle']['processed_batches'] == 3


def test_self_verifying_independent_artifact():
    receipt = compile_and_run_v0(**reference_scenario_v0())
    document = seal_differential_v0(receipt)
    report = verify_differential_artifact_v0(document)
    assert report['receipt_sha256'] == sha(receipt)
    assert report['oracle_sha256'] == sha(canonical(report['oracle']))
    assert document == seal_differential_v0(receipt)


def test_forged_comparison_and_recomputed_outer_hash_rejected():
    document = seal_differential_v0(compile_and_run_v0(**reference_scenario_v0()))
    forged = json.loads(document)
    forged['payload']['comparison']['oracle']['processed_events'] += 1
    forged['payload']['comparison']['oracle_sha256'] = sha(
        canonical(forged['payload']['comparison']['oracle']))
    from search.spk_24n_differential_evidence_v0 import SCHEMA
    forged['payload_sha256'] = sha(SCHEMA + '\n' + canonical(forged['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        verify_differential_artifact_v0(canonical(forged))


def test_forged_input_manifest_and_recomputed_hash_rejected():
    document = seal_differential_v0(compile_and_run_v0(**reference_scenario_v0()))
    forged = json.loads(document)
    payload = forged['payload']
    inner = json.loads(payload['receipt'])
    inner['payload']['result']['processed_events'] += 1
    from search.spk_24m_compiler_network_evidence_v0 import SCHEMA as RECEIPT_SCHEMA
    inner['payload_sha256'] = sha(RECEIPT_SCHEMA + '\n' + canonical(inner['payload']))
    payload['receipt'] = canonical(inner)
    payload['comparison']['receipt_sha256'] = sha(payload['receipt'])
    from search.spk_24n_differential_evidence_v0 import SCHEMA
    forged['payload_sha256'] = sha(SCHEMA + '\n' + canonical(payload))
    with pytest.raises(ValueError, match='replay evidence mismatch'):
        verify_differential_artifact_v0(canonical(forged))


def test_duplicate_artifact_json_keys_rejected():
    document = seal_differential_v0(compile_and_run_v0(**reference_scenario_v0()))
    with pytest.raises(ValueError, match='duplicate JSON'):
        verify_differential_artifact_v0(document[:-1] + ',"schema":"again"}')


def test_reference_direct_without_compiler():
    n = NetworkV0((node('A'), node('B')),
                  (NetworkEdgeV0('A',7,'B',0,3),
                   NetworkEdgeV0('A',7,'B',0,2),
                   NetworkEdgeV0('A',7,'B',0,2)))
    result, obs = check(n, (NetworkEventV0(2,'A',0),))
    assert result.processed_events == 4
    assert len(obs.routes) == 3


@pytest.mark.parametrize('seed,program', [(0, R), (1, T2), (2, ACC)])
def test_persistent_state_and_duplicate_initial_inputs(seed, program):
    n = NetworkV0((node('A',program),), ())
    es = (NetworkEventV0(seed,'A',0), NetworkEventV0(seed,'A',0),
          NetworkEventV0(seed+2,'A',0))
    check(n, es)


@pytest.mark.parametrize('initial,delay', [(8,2), (31,1), (5,3), (0,1)])
def test_shift_decay_differential(initial, delay):
    n = NetworkV0((node('A', CoreProgram((ShiftDecay(1),)), raw=initial),), ())
    check(n, (NetworkEventV0(delay,'A',0),))


def test_mixed_decay_acc_and_threshold_guard():
    prog = CoreProgram((ShiftDecay(1), CoreAcc(1,0), CoreCmp(3),
                        CoreEmit(7), CoreReset(0)))
    n = NetworkV0((node('A', prog, raw=16),), ())
    check(n, (NetworkEventV0(1,'A',0), NetworkEventV0(3,'A',0)))


def test_fractional_bits_core_acc():
    cfg = CoreConfig(8, 2)
    n = NetworkV0((node('A', CoreProgram((CoreAcc(2,0),)),config=cfg),), ())
    check(n, (NetworkEventV0(0,'A',0),NetworkEventV0(1,'A',0)))


def test_multiple_emit_instructions_same_time():
    p = CoreProgram((CoreAcc(1,0), CoreCmp(1), CoreEmit(7), CoreEmit(8)))
    n = NetworkV0((node('A',p),), ())
    check(n, (NetworkEventV0(1,'A',0),))


def test_empty_initial_events_state_equality():
    n = NetworkV0((node('A',ACC,raw=17),node('B',R)), ())
    check(n, ())


def test_finite_execution_limit_classification():
    n = NetworkV0((node('A'),node('B')),
                  (NetworkEdgeV0('A',7,'B',0,1),
                   NetworkEdgeV0('B',7,'A',0,1)))
    es = (NetworkEventV0(0,'A',0),)
    for limit in (2,5,10):
        with pytest.raises(NetworkExecutionLimitV0, match='max_events'):
            run_network_v0(n, es, max_events=limit, max_batches=128)
        from search.spk_24n_independent_oracle_v0 import execute_v0
        with pytest.raises(OracleLimitV0, match='max_events'):
            execute_v0(adapt_frozen_v0(n,es), max_events=limit, max_batches=128)


def test_mismatched_processed_events_is_rejected():
    n = NetworkV0((node('A'),), ())
    es = (NetworkEventV0(1,'A',0),)
    actual, obs = check(n, es)
    with pytest.raises(DifferentialMismatchV0, match='processed_events'):
        compare_actual_v0(n,es,replace(actual, processed_events=99),obs.batches,obs.routes)


def test_mismatched_state_is_rejected():
    n = NetworkV0((node('A',ACC),), ())
    es = (NetworkEventV0(1,'A',0),)
    actual, obs = check(n,es)
    from dataclasses import asdict
    wrong = asdict(actual)
    wrong['states'][0]['raw'] += 1
    with pytest.raises(DifferentialMismatchV0, match='states'):
        compare_actual_v0(n,es,wrong,obs.batches,obs.routes)


def test_mismatched_observer_route_is_rejected():
    n = NetworkV0((node('A'),node('B')),(NetworkEdgeV0('A',7,'B',0,1),))
    es = (NetworkEventV0(1,'A',0),)
    actual, obs = check(n,es)
    with pytest.raises(DifferentialMismatchV0, match='routes'):
        compare_actual_v0(n,es,actual,obs.batches,[])


def test_mismatched_batch_observation_is_rejected():
    n = NetworkV0((node('A'),), ())
    es = (NetworkEventV0(1,'A',0),)
    actual, obs = check(n,es)
    with pytest.raises(DifferentialMismatchV0, match='batches'):
        compare_actual_v0(n,es,actual,[],obs.routes)


def test_reject_malformed_supported_subset_without_silent_skip():
    n = NetworkV0((node('A'),), ())
    from search.spk_24n_independent_oracle_v0 import execute_v0
    original = adapt_frozen_v0(n, ())
    corrupted = replace(original, nodes=(replace(original.nodes[0],
                             instructions=(('UNKNOWN', 1),)),))
    with pytest.raises(OracleDomainErrorV0, match='out-of-domain'):
        execute_v0(corrupted)


def test_729_relay_dag_networks_against_frozen_runtime():
    names = 'ABCD'
    slots = [('A','B'),('A','C'),('A','D'),('B','C'),('B','D'),('C','D')]
    nodes = tuple(node(x) for x in names)
    es = (NetworkEventV0(0,'A',0),NetworkEventV0(2,'A',0),NetworkEventV0(2,'A',0))
    for choices in product((0,1,2), repeat=6):
        edges = tuple(NetworkEdgeV0(a,7,b,0,d)
                      for (a,b),d in zip(slots,choices) if d)
        check(NetworkV0(nodes,edges), es, max_batches=128, max_events=1024)


def test_routed_threshold_two_and_parallel_edges():
    n = NetworkV0((node('A'),node('B',T2),node('C',ACC)), (
        NetworkEdgeV0('A',7,'B',0,1),NetworkEdgeV0('A',7,'B',0,1),
        NetworkEdgeV0('B',7,'C',0,2),))
    check(n,(NetworkEventV0(1,'A',0),NetworkEventV0(5,'A',0)))
