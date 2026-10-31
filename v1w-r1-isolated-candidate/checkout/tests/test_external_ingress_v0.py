from dataclasses import replace

import pytest

from spk_architecture.access_v0 import (
    ActivityV0, AccessIntentKindV0, MemoryAccessIntentV0, MemoryDomainV0,
)
from spk_architecture.memory_target_v0 import (
    MemorySpaceV0, MemoryTargetV0, MemoryTargetCatalogV0,
    MemoryTargetReferenceV0,
)
from spk_network.events_v0 import NetworkEventV0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0
from spk_simulator.event_provenance_v0 import (
    BatchInputProvenanceV0, EventProvenanceV0,
)
from spk_simulator.external_ingress_v0 import (
    ExternalArrivalV0, ExternalIngressPlanV0, bind_external_ingress_v0,
)


def scenario(*, duplicate=False):
    events = (
        NetworkEventV0(2, "A", 0),
        NetworkEventV0(4, "B", 0),
    )
    batches = (
        BatchInputProvenanceV0(0, 2, "A", (0,), 1, ()),
        BatchInputProvenanceV0(1, 4, "B", (0,), 1, ()),
    )
    if duplicate:
        events = (events[0], events[0], events[1])
        batches = (
            BatchInputProvenanceV0(0, 2, "A", (0, 0), 2, ()),
            batches[1],
        )
    targets = MemoryTargetCatalogV0((
        MemoryTargetV0("events:A", MemorySpaceV0.ACTIVE, "E0", "PE0", MemoryDomainV0.EVENT, "A"),
        MemoryTargetV0("events:B", MemorySpaceV0.ACTIVE, "E0", "PE1", MemoryDomainV0.EVENT, "B"),
    ))
    refs = tuple(
        MemoryTargetReferenceV0(
            MemoryAccessIntentV0(
                request_id=req_id, epoch_id="E0", pe_id=pe_id,
                activity=ActivityV0.EXECUTE,
                kind=AccessIntentKindV0.BATCH_CONSUME,
                node_id=node, event_time=timestamp, quantity=qty,
            ), f"events:{node}",
        )
        for req_id, pe_id, node, timestamp, qty in (
            (3, "PE0", "A", 2, 2 if duplicate else 1),
            (7, "PE1", "B", 4, 1),
        )
    )
    return (
        LogicalAccessPlanV0("E0", targets, refs),
        EventProvenanceV0(batches, len(events), 0, len(events)),
        events,
    )


def bind(data, boundaries):
    ingress = ExternalIngressPlanV0(tuple(
        ExternalArrivalV0(index, boundary)
        for index, boundary in enumerate(boundaries)
    ))
    return bind_external_ingress_v0(*data, ingress)


def test_explicit_arrival_boundaries():
    result = bind(scenario(), (5, 1))
    assert [(a.input_index, a.event_time, a.arrival_boundary)
            for a in result.arrivals] == [(0, 2, 5), (1, 4, 1)]


def test_batch_release_and_pe_binding():
    result = bind(scenario(), (5, 1))
    assert [(b.consume_request_id, b.ready_boundary)
            for b in result.batch_releases] == [(3, 5), (7, 1)]
    assert [a.target_pe_id for a in result.arrivals] == ["PE0", "PE1"]


def test_duplicate_spikes_are_distinct_occurrences():
    result = bind(scenario(duplicate=True), (2, 8, 3))
    assert [(b.consume_request_id, b.ready_boundary, b.input_indices)
            for b in result.batch_releases] == [
                (3, 8, (0, 1)), (7, 3, (2,))
            ]


def test_event_time_does_not_define_arrival_time():
    result = bind(scenario(), (100, 0))
    assert result.arrivals[0].event_time == 2
    assert result.arrivals[0].arrival_boundary == 100
    assert result.arrivals[1].event_time == 4
    assert result.arrivals[1].arrival_boundary == 0


def test_missing_event_binding_rejected():
    with pytest.raises(ValueError, match="every initial occurrence"):
        bind(scenario(), (0,))


def test_extra_event_binding_rejected():
    with pytest.raises(ValueError, match="every initial occurrence"):
        bind(scenario(), (0, 1, 2))


def test_duplicate_input_index_rejected():
    with pytest.raises(ValueError, match="noncanonical"):
        ExternalIngressPlanV0((ExternalArrivalV0(0, 0), ExternalArrivalV0(0, 1)))


def test_out_of_order_input_indices_rejected():
    with pytest.raises(ValueError, match="noncanonical"):
        ExternalIngressPlanV0((ExternalArrivalV0(1, 0), ExternalArrivalV0(0, 1)))


@pytest.mark.parametrize("index,boundary", [(-1, 0), (True, 0), (0, -1), (0, True)])
def test_invalid_arrival_values(index, boundary):
    with pytest.raises(ValueError):
        ExternalArrivalV0(index, boundary)


def test_bad_provenance_count_rejected():
    plan, provenance, events = scenario()
    with pytest.raises(ValueError, match="initial event/provenance count"):
        bind_external_ingress_v0(
            plan, replace(provenance, initial_count=10), events,
            ExternalIngressPlanV0((ExternalArrivalV0(0, 0), ExternalArrivalV0(1, 0))),
        )


def test_corrupted_batch_count_rejected():
    plan, provenance, events = scenario()
    corrupted = replace(provenance.batches[0], initial_count=0, channels=())
    changed = replace(provenance, batches=(corrupted, provenance.batches[1]))
    with pytest.raises(ValueError, match="batch external multiplicity"):
        bind_external_ingress_v0(
            plan, changed, events,
            ExternalIngressPlanV0((ExternalArrivalV0(0, 0), ExternalArrivalV0(1, 0))),
        )


def test_empty_initials_and_empty_batches():
    plan, _, _ = scenario()
    result = bind_external_ingress_v0(
        replace(plan, references=()),
        EventProvenanceV0((), 0, 0, 0),
        (), ExternalIngressPlanV0(()),
    )
    assert result.arrivals == ()
    assert result.batch_releases == ()


def test_deterministic_bind():
    data = scenario(duplicate=True)
    assert bind(data, (0, 2, 1)) == bind(data, (0, 2, 1))
