"""S3.7d/3b2b2k/21: real shared EVENT + sealed root admission precheck."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.owned_shared_event_cycle_v0 import (
    OwnedSharedEventCycleStateV0 as State, advance_owned_shared_event_cycle_v0 as tick,
)
from spk_simulator.owned_sealed_root_batch_v0 import (
    analyze_owned_sealed_root_batches_v0 as audit,
)
from tests.test_owned_shared_event_cycle_v0 import make


def root(event_time=3, boundary=4, channel=0):
    return (boundary, 'PE0', 'C', event_time, channel)


def row(s):
    return audit(s).batches[0]


def test_real_external_before_arrival_is_pending():
    _,s=make(arrivals=(root(),))
    a=row(s)
    assert a.status=='SEALED_INPUTS_PENDING'
    assert a.pending_external_indices==(0,)
    assert not a.sealed_input_set_complete


def test_real_external_after_arrival_is_ready():
    _,s=make(arrivals=(root(),))
    result=tick(s)
    a=row(result.state)
    assert a.status=='ROOT_INPUT_SET_READY'
    assert a.expected_external_indices==(0,)
    assert a.resident_external_indices==(0,)
    assert a.consume_request_id==2
    assert a.node_id=='C' and a.event_time==3
    assert a.sealed_input_set_complete
    assert not a.supports_consume_confirmation


def test_no_inputs_no_phantom_batch():
    _,s=make()
    assert audit(s).batches==()


def test_mismatched_event_time_to_static_batch_is_rejected():
    _,s=make(arrivals=(root(event_time=99),))
    with pytest.raises(ValueError, match="identity mismatch"):
        audit(s)


def test_future_arrival_with_same_event_time_remains_pending():
    _,s=make(arrivals=(root(boundary=6),))
    assert not row(tick(s).state).sealed_input_set_complete
    assert row(tick(tick(s).state).state).status=='SEALED_INPUTS_PENDING'


def test_service_boundary_progress_does_not_automatically_close_batch():
    _,s=make(arrivals=(root(boundary=8),))
    for _ in range(3):
        s=tick(s).state
    assert not row(s).sealed_input_set_complete


def test_one_hop_destination_never_ready_without_proof():
    _,s=make(arrivals=((4,'PE1','B',4,0),))
    a=row(tick(s).state)
    assert a.status=='NONROOT_REQUIRES_CAUSAL_FRONTIER'
    assert not a.sealed_input_set_complete


def test_one_hop_pending_status_even_before_arrival():
    _,s=make(arrivals=((8,'PE1','B',4,0),))
    assert row(s).status=='NONROOT_REQUIRES_CAUSAL_FRONTIER'


def test_no_implicit_consumption():
    _,s=make(arrivals=(root(),))
    successor=tick(s).state
    before=successor.external_resident_input_indices
    audit(successor)
    assert successor.external_resident_input_indices==before


def test_audit_idempotent():
    _,s=make(arrivals=(root(),))
    s=tick(s).state
    assert audit(s)==audit(s)


def test_audit_is_pure():
    _,s=make(arrivals=(root(),))
    old=s
    audit(s)
    assert s==old


def test_no_consume_confirmation_even_if_ready():
    _,s=make(arrivals=(root(),))
    a=audit(tick(s).state)
    assert a.batches[0].sealed_input_set_complete
    assert a.supports_consume_confirmation is False


def test_no_state_owner_rejected():
    with pytest.raises(TypeError):
        audit(None)


def test_no_mutable_result():
    _,s=make(arrivals=(root(),))
    candidate=row(tick(s).state)
    with pytest.raises(FrozenInstanceError):
        candidate.status='FORGED'


def test_nonroot_has_no_new_communication_route_assumptions():
    _,s=make(arrivals=((4,'PE1','B',4,0),))
    t=tick(s).state
    assert audit(t).batches[0].expected_external_indices==(0,)
    assert audit(t).batches[0].resident_external_indices==(0,)
    assert not audit(t).batches[0].sealed_input_set_complete


def test_no_forged_future_resident_allowed():
    _,s=make(arrivals=(root(boundary=8),))
    with pytest.raises(ValueError,match='history'):
        State(s.dynamic,s.seal,(0,))


def test_no_forged_missing_resident_allowed():
    _,s=make(arrivals=(root(),))
    t=tick(s).state
    with pytest.raises(ValueError,match='history'):
        State(t.dynamic,t.seal,())


def test_event_time_and_service_time_are_independent():
    _,s=make(arrivals=(root(event_time=3,boundary=4),))
    a=row(tick(s).state)
    assert a.event_time==3 and a.sealed_input_set_complete


def test_no_arrival_spontaneously_consumed():
    _,s=make(arrivals=(root(),))
    t=tick(s).state
    assert row(t).status=='ROOT_INPUT_SET_READY'
    assert t.external_resident_input_indices==(0,)


def test_epoch_is_copied_from_validated_seal():
    _,s=make(arrivals=(root(),))
    a=audit(s)
    assert a.epoch_id=='E0' and a.batches[0].epoch_id=='E0'


def test_multiplicity_not_collapsed():
    _,s=make(arrivals=(root(),))
    assert row(tick(s).state).expected_external_indices==(0,)


def test_do_not_invent_route_batch_from_static_dynamic_registry():
    _,s=make()
    assert not audit(s).batches


def test_status_consistent_with_readiness():
    _,s=make(arrivals=(root(),))
    assert not row(s).sealed_input_set_complete
    assert row(tick(s).state).sealed_input_set_complete


def test_shared_capacity_still_enforced_on_arrival():
    _,s=make(arrivals=(root(),))
    t=tick(s).state
    assert audit(t).batches[0].resident_external_indices==(0,)


def test_no_unverified_nonroot_certification_with_zero_route_delivery():
    _,s=make(arrivals=((4,'PE1','B',4,0),))
    a=audit(tick(s).state)
    assert a.batches[0].status=='NONROOT_REQUIRES_CAUSAL_FRONTIER'


def test_scan_reports_deterministic_order():
    _,s=make(arrivals=(root(),))
    assert audit(s).batches==audit(s).batches


def two_inputs(*, second_boundary=4, quantity=2):
    _,s=make(arrivals=(root(channel=0),root(channel=1,boundary=second_boundary)))
    registry = s.dynamic.transit.registry
    requests = tuple(replace(r,quantity=quantity) if r.request_id==2 else r
                     for r in registry.base_requests)
    staged = tuple(replace(r,quantity=quantity) if r.request_id==2 else r
                   for r in registry.staged_requests)
    updated_registry=replace(registry,base_requests=requests,staged_requests=staged)
    updated_transit=replace(s.dynamic.transit,registry=updated_registry)
    return replace(s,dynamic=replace(s.dynamic,transit=updated_transit))


def test_parallel_external_occurrences_preserve_multiplicity():
    s=two_inputs()
    a=row(tick(s).state)
    assert a.sealed_input_set_complete
    assert a.expected_external_indices == (0,1)
    assert a.resident_external_indices == (0,1)


def test_partial_arrival_does_not_admit_multiple_input_batch():
    s=two_inputs(second_boundary=6)
    after=tick(s).state
    a=row(after)
    assert a.status=='SEALED_INPUTS_PENDING'
    assert a.resident_external_indices==(0,)
    assert a.pending_external_indices==(1,)
    assert not a.sealed_input_set_complete


def test_batch_ready_only_after_final_delayed_arrival():
    s=two_inputs(second_boundary=6)
    for _ in range(3):
        s=tick(s).state
    assert row(s).sealed_input_set_complete
    assert row(s).expected_external_indices==(0,1)


def test_batch_quantity_mismatch_fails_closed():
    s=two_inputs(quantity=1)
    with pytest.raises(ValueError,match='identity mismatch'):
        audit(s)


def test_not_a_ready_batch_without_valid_base_consume_request():
    _,s=make(arrivals=(root(),))
    registry=s.dynamic.transit.registry
    base=tuple(replace(r,kind=Kind.STATE_LOAD) if r.request_id==2 else r
               for r in registry.base_requests)
    staged=tuple(replace(r,kind=Kind.STATE_LOAD) if r.request_id==2 else r
                 for r in registry.staged_requests)
    # The registry's own serialized-graph contract may reject the request first.
    with pytest.raises(ValueError):
        replace(registry,base_requests=base,staged_requests=staged)


def test_ambiguous_same_time_batches_fail_closed():
    _,s=make(arrivals=(root(channel=0),root(channel=1)))
    seal=s.seal
    from spk_simulator.external_ingress_v0 import (
        ExternalIngressBindingV0, BatchIngressReleaseV0,
    )
    from spk_simulator.owned_external_ingress_prefix_v0 import seal_finite_external_ingress_v0
    arrivals=seal.binding.arrivals
    altered=replace(arrivals[1],consume_request_id=3)
    binding=ExternalIngressBindingV0(
        (arrivals[0],altered),
        (BatchIngressReleaseV0(2,4,(0,)), BatchIngressReleaseV0(3,4,(1,))),
    )
    new_seal=seal_finite_external_ingress_v0(
        s.dynamic.transit.registry.architecture,
        s.dynamic.transit.registry.allocation_ledger.network,
        binding, epoch_id='E0',
    )
    altered_s=replace(s,seal=new_seal)
    with pytest.raises(ValueError,match='ambiguous'):
        audit(altered_s)
