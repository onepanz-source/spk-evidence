"""k24d: terminal owner replay, negative mutation gate and closed STATE_COMMIT."""
from dataclasses import FrozenInstanceError, replace

import pytest

from spk_core.isa import CoreCmp, CoreProgram
from spk_simulator.owned_root_single_clock_v0 import (
    initialize_owned_root_single_clock_v0, advance_owned_root_single_clock_v0,
)
from spk_simulator.owned_root_terminal_commit_v0 import (
    handoff_owned_root_terminal_commit_v0 as handoff,
    advance_owned_root_terminal_commit_v0 as advance,
)
from tests import test_owned_root_batch_consumption_v0 as root_fixtures


def prepared_root(monkeypatch, *, quiet=True, commit_units=1, consume_units=1):
    """Use actual service/ingress fixtures; change only Core's output threshold."""
    original = root_fixtures.scenario

    def scenario():
        arch, network, placement, image, prepared, registry = original()
        if quiet:
            nodes = tuple(
                replace(node, program=CoreProgram(tuple(
                    replace(op, threshold_raw=100) if isinstance(op, CoreCmp) else op
                    for op in node.program.instructions
                ))) if node.node_id == 'C' else node
                for node in network.nodes
            )
            network = replace(network, nodes=nodes)
            registry = replace(registry, allocation_ledger=replace(
                registry.allocation_ledger, network=network))
        requests = tuple(replace(r, service_units=commit_units)
                         if r.request_id == 3 else r for r in registry.base_requests)
        registry = replace(registry, base_requests=requests, staged_requests=requests)
        return arch, network, placement, image, prepared, registry

    monkeypatch.setattr(root_fixtures, 'scenario', scenario)
    root = initialize_owned_root_single_clock_v0(
        root_fixtures.seeded(confirmed=(), units=consume_units))
    for _ in range(50):
        if root.prepared:
            return root
        root = advance_owned_root_single_clock_v0(root).state
    pytest.fail('actual root service never prepared Core')


def commit_all(owner, *, limit=30):
    events = []
    for _ in range(limit):
        if owner.committed:
            return owner, tuple(events)
        step = advance(owner)
        events.append(step.quantum)
        owner = step.state
    pytest.fail('terminal STATE_COMMIT never finished')


def neuron(state):
    return next(x for x in state.image.neurons if x.node_id == 'C')


def test_handoff_witnessed_closed_root_and_output_free(monkeypatch):
    root = prepared_root(monkeypatch)
    assert not root.prepared[0].transition.candidate_outputs
    terminal = handoff(root)
    assert terminal.handoff is root
    assert terminal.image == root.image
    assert terminal.service == root.shared.dynamic.transit.service
    assert not terminal.quanta


def test_full_service_commit_and_separate_later_confirmation(monkeypatch):
    root = prepared_root(monkeypatch)
    terminal, trail = commit_all(handoff(root))
    rid = 3
    assert terminal.committed
    assert neuron(root).version == 0
    assert neuron(terminal).version == 1
    assert neuron(terminal).last_timestamp == 3
    assert trail[-1].receipt is not None
    assert trail[-1].receipt.old_version == 0
    assert trail[-1].receipt.new_version == 1
    assert trail[-1].confirmed_request_ids == (rid,)
    assert any(rid in e.work_finished_request_ids for e in trail[:-1])
    assert all(e.receipt is None for e in trail[:-1])
    assert terminal.handoff.shared.dynamic.transit.storage == root.shared.dynamic.transit.storage
    assert terminal.handoff.shared.external_consumed_input_indices == (0,)
    assert all(x.request_id == rid for e in trail for x in e.slices)
    assert [e.service_tick for e in trail] == list(range(
        root.shared.dynamic.transit.service.next_service_tick,
        terminal.service.next_service_tick))
    assert 3 in {x.request_id for x in terminal.service.confirmed}


def test_multiquantum_partial_service(monkeypatch):
    root = prepared_root(monkeypatch, commit_units=7)
    terminal, trail = commit_all(handoff(root))
    assert terminal.committed
    assert sum(s.units for e in trail for s in e.slices) == 7
    assert len(trail) >= 3
    assert neuron(terminal).version == 1


def test_deterministic_replay(monkeypatch):
    initial = handoff(prepared_root(monkeypatch))
    assert advance(initial) == advance(initial)
    terminal, _ = commit_all(initial)
    terminal.__post_init__()
    assert initial.image == initial.handoff.image
    assert neuron(initial).version == 0


def test_cannot_reenter_terminal_owner_after_commit(monkeypatch):
    terminal, _ = commit_all(handoff(prepared_root(monkeypatch)))
    with pytest.raises(ValueError, match='already committed'):
        advance(terminal)
    with pytest.raises(ValueError, match='after committed'):
        replace(terminal, quanta=terminal.quanta + terminal.quanta[-1:])


def test_missing_preparation_rejected(monkeypatch):
    root = prepared_root(monkeypatch)
    with pytest.raises(ValueError, match='unique witnessed'):
        handoff(replace(root, prepared=()))


def test_unconfirmed_root_rejected(monkeypatch):
    root = prepared_root(monkeypatch)
    service = root.shared.dynamic.transit.service
    # Construction may reject sooner at historical consumption coverage.
    with pytest.raises((ValueError, TypeError)):
        replace(root, shared=replace(root.shared, dynamic=replace(
            root.shared.dynamic, transit=replace(
                root.shared.dynamic.transit,
                service=replace(service, confirmed=service.confirmed[:-1])))))


def test_no_handoff_before_core_prepare(monkeypatch):
    root = prepared_root(monkeypatch)
    # The fresh k24b snapshot is a legitimate root but not a terminal one.
    unprepared = initialize_owned_root_single_clock_v0(
        root_fixtures.seeded(confirmed=()))
    with pytest.raises(ValueError, match='handoff requires'):
        handoff(unprepared)


def test_output_bearing_transition_is_rejected(monkeypatch):
    root = prepared_root(monkeypatch, quiet=False)
    assert root.prepared[0].transition.candidate_outputs
    with pytest.raises(ValueError, match='output-bearing'):
        handoff(root)
    assert neuron(root).version == 0


def test_tampered_handoff_witness_rejected(monkeypatch):
    root = prepared_root(monkeypatch)
    bad = replace(root.witnesses[0], channels=(7,))
    with pytest.raises(ValueError):
        handoff(replace(root, witnesses=(bad,)))


def test_tampered_handoff_core_rejected(monkeypatch):
    root = prepared_root(monkeypatch)
    bad = replace(root.prepared[0], transition=replace(
        root.prepared[0].transition, after_raw=999))
    with pytest.raises(ValueError):
        handoff(replace(root, prepared=(bad,)))


def test_mutated_terminal_tick_rejected(monkeypatch):
    owner = handoff(prepared_root(monkeypatch))
    step = advance(owner).state
    wrong = replace(step.quanta[0], service_tick=step.quanta[0].service_tick + 1)
    with pytest.raises(ValueError, match='not reconstructible'):
        replace(step, quanta=(wrong,))


@pytest.mark.parametrize('field', [
    'confirmed_request_ids',
    'work_finished_request_ids',
])
def test_fabricated_terminal_effect_rejected(monkeypatch, field):
    # Multiple units ensure first tick only spends partial work.
    owner = handoff(prepared_root(monkeypatch, commit_units=7))
    step = advance(owner).state
    original = getattr(step.quanta[0], field)
    wrong = replace(step.quanta[0], **{field: (3,) if not original else ()})
    with pytest.raises(ValueError, match='not reconstructible'):
        replace(step, quanta=(wrong,))


def test_mutated_service_slices_rejected(monkeypatch):
    state = advance(handoff(prepared_root(monkeypatch))).state
    evidence = state.quanta[0]
    fake = replace(evidence.slices[0], service_tick=evidence.service_tick + 1)
    with pytest.raises(ValueError, match='not reconstructible'):
        replace(state, quanta=(replace(evidence, slices=(fake,) + evidence.slices[1:]),))


def test_dropped_quantum_rejected(monkeypatch):
    owner = handoff(prepared_root(monkeypatch))
    end, trail = commit_all(owner)
    with pytest.raises(ValueError, match='differs from executed replay'):
        replace(end, quanta=trail[:-1])


def test_reordered_or_duplicated_quantum_rejected(monkeypatch):
    end, trail = commit_all(handoff(prepared_root(monkeypatch, commit_units=7)))
    with pytest.raises(ValueError, match='not reconstructible'):
        replace(end, quanta=tuple(reversed(trail)))
    with pytest.raises(ValueError):
        replace(end, quanta=trail + (trail[0],))


def test_forged_service_clock_rejected(monkeypatch):
    owner = advance(handoff(prepared_root(monkeypatch))).state
    with pytest.raises(ValueError, match='differs from executed replay'):
        replace(owner, service=replace(
            owner.service, next_service_tick=owner.service.next_service_tick + 1))


def test_forged_state_version_rejected(monkeypatch):
    end, _ = commit_all(handoff(prepared_root(monkeypatch)))
    forged_neurons = tuple(replace(n, version=2) if n.node_id == 'C' else n
                           for n in end.image.neurons)
    with pytest.raises(ValueError, match='differs from executed replay'):
        replace(end, image=replace(end.image, neurons=forged_neurons))


def test_forged_receipt_rejected(monkeypatch):
    end, _ = commit_all(handoff(prepared_root(monkeypatch)))
    last = end.quanta[-1]
    fake = replace(last.receipt, new_version=2)
    with pytest.raises(ValueError, match='not reconstructible'):
        replace(end, quanta=end.quanta[:-1] + (replace(last, receipt=fake),))


def test_owner_is_immutable(monkeypatch):
    owner = handoff(prepared_root(monkeypatch))
    with pytest.raises(FrozenInstanceError):
        owner.image = None


def test_input_type_rejected():
    with pytest.raises(TypeError):
        handoff(None)
    with pytest.raises(TypeError):
        advance(None)


def test_two_independent_handoffs_remain_possible_without_external_registry(monkeypatch):
    # This explicitly documents the gap: dataclass immutability is not a
    # globally linear capability. The orchestrator must prevent this fork.
    root = prepared_root(monkeypatch)
    first = handoff(root)
    second = handoff(root)
    assert first == second and first is not second
    assert first.handoff is second.handoff is root
