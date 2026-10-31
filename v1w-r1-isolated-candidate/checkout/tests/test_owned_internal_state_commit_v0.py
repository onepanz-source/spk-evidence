"""Output-free owned STATE_COMMIT: real service + owned Core, historical audit."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_core.isa import CoreCmp, CoreProgram
from spk_simulator.owned_internal_reads_v0 import (
    OwnedInternalCommitEvidenceV0, audit_committed_internal_history_v0,
    advance_owned_internal_reads_v0,
)
from spk_simulator.owned_internal_state_commit_v0 import commit_owned_internal_state_v0
from spk_simulator.serialized_internal_graph_v0 import serialize_internal_access_graph_v0
from spk_simulator.versioned_core_transition_v0 import initialize_neuron_image_v0
from tests.test_serialized_internal_graph_v0 import fixture


def context(*, quiet=True, ingress_tick=None):
    c, reqs, graph = fixture()
    if quiet:
        nodes = tuple(replace(node, program=CoreProgram(tuple(
            replace(op, threshold_raw=100) if isinstance(op, CoreCmp) else op
            for op in node.program.instructions
        ))) if node.node_id == 'B' else node for node in c[1].nodes)
        network = replace(c[1], nodes=nodes)
    else:
        network = c[1]
    graph = serialize_internal_access_graph_v0(reqs, graph).graph
    state = replace(c[6], image=initialize_neuron_image_v0(network))
    return (c[0], network, c[2], c[3], reqs, graph, state, c[7])


def tick(c):
    state = advance_owned_internal_reads_v0(
        c[0], c[1], c[2], c[3], c[4], c[5], c[6], ingress=c[7]
    ).state
    return (*c[:6], state, c[7])


def commit(c, rid=80):
    return commit_owned_internal_state_v0(c[1], c[2], c[4], c[5], c[6], commit_request_id=rid)


def ready(c, rid=80, limit=20):
    for _ in range(limit):
        if rid in {x.request_id for x in c[6].owned.boundary.service.awaiting_confirmation}:
            return c
        c = tick(c)
    raise AssertionError('STATE_COMMIT did not finish its requested service')


def one():
    c = ready(context())
    step = commit(c)
    return c, step


def all_three():
    c = context()
    records = []
    for rid in (80, 81, 82):
        c = ready(c, rid)
        step = commit(c, rid)
        records.append(step)
        c = (*c[:6], step.state, c[7])
    return c, tuple(records)


def neuron(c):
    return next(n for n in c[6].image.neurons if n.node_id == 'B')


def confirmed(c):
    return {x.request_id for x in c[6].owned.boundary.service.confirmed}


def test_commits_first_batch_from_actual_service_and_core():
    before, result = one()
    assert result.request_id == 80
    assert neuron(before).version == 0
    assert next(n for n in result.state.image.neurons if n.node_id == 'B').version == 1


def test_first_commit_is_a_real_state_write():
    c, step = one()
    assert step.evidence.receipt.old_raw == 0
    assert step.evidence.receipt.new_raw == 1
    assert step.evidence.receipt.old_timestamp == 0
    assert step.evidence.receipt.new_timestamp == 4


def test_real_service_confirmation_is_added_only_after_commit():
    c, step = one()
    assert 80 not in confirmed(c)
    assert 80 in {x.request_id for x in step.state.owned.boundary.service.confirmed}
    assert 80 not in {x.request_id for x in step.state.owned.boundary.service.awaiting_confirmation}


def test_first_state_commit_has_no_candidate_outputs():
    _, step = one()
    assert step.evidence.receipt.candidate_outputs == ()


def test_prepared_core_is_retired_after_commit():
    _, step = one()
    assert not step.state.prepared
    assert step.state.commits[0].preparation.consume_request_id == 50


def test_commit_preserves_event_tombstones():
    c, step = one()
    assert step.state.owned.boundary.driver == c[6].owned.boundary.driver


def test_commit_does_not_advance_service_time():
    c, step = one()
    assert step.state.owned.boundary.service.next_service_tick == c[6].owned.boundary.service.next_service_tick


def test_three_ordered_commits_advance_versions():
    c, records = all_three()
    assert [r.evidence.receipt.new_version for r in records] == [1, 2, 3]
    assert (neuron(c).raw, neuron(c).last_timestamp, neuron(c).version) == (3, 6, 3)


def test_each_later_state_load_is_new_version():
    c, _ = all_three()
    versions = {r.request_id: r.state_version for r in c[6].reads if r.kind.name == 'STATE_LOAD'}
    assert versions == {71: 0, 73: 1, 75: 2}


def test_all_historical_reads_can_be_replayed():
    c, _ = all_three()
    snapshots = audit_committed_internal_history_v0(c[1], c[6], c[4], c[5])
    assert [(snapshots[('B',i)].raw, snapshots[('B',i)].last_timestamp) for i in range(4)] == [
        (0,0), (1,4), (2,5), (3,6)
    ]


def test_three_completed_batches_have_distinct_events():
    c, _ = all_three()
    assert [rec.preparation.consume_request_id for rec in c[6].commits] == [50,51,52]
    assert len(c[6].pending_batches) == 3


def test_resume_from_middle_snapshot_matches_continuous_execution():
    c, _ = all_three()
    d, first = one()
    d = (*d[:6], first.state, d[7])
    for rid in (81, 82):
        d = ready(d, rid)
        result = commit(d, rid)
        d = (*d[:6], result.state, d[7])
    assert c[6] == d[6]


def test_committed_snapshot_is_frozen():
    _, step = one()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        step.state.image = None


def test_first_commit_cannot_happen_before_service_finishes():
    with pytest.raises(ValueError, match='not finished'):
        commit(context())


def test_cannot_replay_same_commit_request():
    c, step = one()
    with pytest.raises(ValueError, match='not finished'):
        commit((*c[:6], step.state, c[7]))


def test_cannot_commit_later_batch_early():
    c = ready(context())
    with pytest.raises(ValueError, match='not finished'):
        commit(c, 81)


def test_cannot_commit_without_serialized_graph():
    c = ready(context())
    deps = fixture()[2]
    with pytest.raises(ValueError, match='serialized dependencies'):
        commit((*c[:5], deps, c[6], c[7]))


def test_wrong_commit_request_rejected():
    c = ready(context())
    with pytest.raises(ValueError, match='no serialized'):
        commit(c, 71)


def test_cannot_commit_with_output_candidate():
    c = ready(context(quiet=False))
    assert c[6].prepared[0].transition.candidate_outputs
    with pytest.raises(ValueError, match='OUTPUT'):
        commit(c)


def test_wrong_routing_manifest_epoch_rejected():
    c = ready(context())

    altered_routes = tuple(
        replace(
            route,
            occurrence=replace(route.occurrence, epoch_id='DIFFERENT'),
        )
        for route in c[2].routes
    )

    altered = replace(
        c[2],
        epoch_id='DIFFERENT',
        routes=altered_routes,
    )

    with pytest.raises(ValueError, match='routing/neuronal epoch mismatch'):
        commit((*c[:2], altered, *c[3:]))


def test_wrong_commit_id_type_rejected():
    c = ready(context())
    with pytest.raises(ValueError, match='commit request ID'):
        commit(c, '80')


def test_forged_pending_witness_channels_rejected():
    c = ready(context())
    state = replace(c[6],pending_batches=(replace(c[6].pending_batches[0],channels=(99,)),)+c[6].pending_batches[1:])
    with pytest.raises(ValueError, match='channels|consumed batch'):
        commit((*c[:6], state, c[7]))


def test_forged_consumed_identity_rejected():
    c = ready(context())
    state = replace(c[6],pending_batches=(replace(c[6].pending_batches[0],route_request_ids=(999,)),)+c[6].pending_batches[1:])
    with pytest.raises(ValueError, match='EVENT|route'):
        commit((*c[:6],state,c[7]))


def test_forged_core_result_rejected():
    c = ready(context())
    bad = replace(c[6].prepared[0],transition=replace(c[6].prepared[0].transition, after_raw=77))
    state = replace(c[6],prepared=(bad,))
    with pytest.raises(ValueError, match='prepared Core result|Core'):
        commit((*c[:6],state,c[7]))


def test_missing_read_evidence_rejected():
    c = ready(context())
    state = replace(c[6], reads=tuple(r for r in c[6].reads if r.request_id != 71))
    with pytest.raises(ValueError, match='missing confirmed P/S'):
        commit((*c[:6],state,c[7]))


def test_forged_current_neuron_image_rejected():
    c = ready(context())
    versions=tuple(replace(n,raw=5,version=1,last_timestamp=3) if n.node_id=='B' else n for n in c[6].image.neurons)
    state=replace(c[6],image=replace(c[6].image, neurons=versions))
    with pytest.raises(ValueError, match='history'):
        commit((*c[:6],state,c[7]))


def test_tampered_historical_commit_receipt_detected_on_resume():
    c, _ = all_three()
    evidence = c[6].commits[0]
    bad = replace(evidence,receipt=replace(evidence.receipt,new_raw=199))
    state = replace(c[6],commits=(bad,)+c[6].commits[1:])
    with pytest.raises(ValueError, match='receipt mismatch'):
        audit_committed_internal_history_v0(c[1],state,c[4],c[5])


def test_tampered_historical_state_read_detected_on_resume():
    c, _ = all_three()
    bad = replace(c[6].reads[3],raw=99)
    state = replace(c[6],reads=c[6].reads[:3]+(bad,)+c[6].reads[4:])
    with pytest.raises(ValueError, match='historical STATE_LOAD'):
        audit_committed_internal_history_v0(c[1],state,c[4],c[5])


def test_missing_committed_history_is_rejected():
    c, _ = all_three()
    with pytest.raises(ValueError, match='commit history'):
        audit_committed_internal_history_v0(c[1],replace(c[6],commits=()),c[4],c[5])


def test_reordering_committed_history_is_rejected():
    c, _ = all_three()
    with pytest.raises(ValueError, match='commit history'):
        audit_committed_internal_history_v0(c[1],replace(c[6],commits=c[6].commits[::-1]),c[4],c[5])


def test_committed_history_cannot_claim_future_boundary():
    c, _ = all_three()
    bad=replace(c[6].commits[0],confirmation_boundary=999)
    with pytest.raises(ValueError, match='history|binding'):
        audit_committed_internal_history_v0(c[1],replace(c[6],commits=(bad,)+c[6].commits[1:]),c[4],c[5])


def test_commits_do_not_mutate_original_state():
    c, step = one()
    assert c[6].image.neurons[1].version == 0
    assert step.state.image.neurons[1].version == 1


def test_output_free_core_state_matches_independent_network_reference():
    from spk_network.events_v0 import NetworkEventV0
    from spk_network.runtime_v0 import run_network_v0
    c, _ = all_three()
    events = tuple(NetworkEventV0(ts, 'B', 0) for ts in (4, 5, 6))
    functional = run_network_v0(c[1], events)
    expected = next(n for n in functional.states if n.node_id == 'B')
    assert (neuron(c).raw, neuron(c).last_timestamp) == (expected.raw, expected.last_timestamp)
    assert not functional.emissions
