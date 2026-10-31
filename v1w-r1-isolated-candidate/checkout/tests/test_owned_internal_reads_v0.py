"""Owned internal P/S read tests using the existing SPK storage fixtures."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind, MemoryDomainV0 as Domain
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0, AccessDependencyV0
from spk_simulator.versioned_core_transition_v0 import initialize_neuron_image_v0
from spk_simulator.owned_internal_reads_v0 import (
    InternalReadEvidenceV0, OwnedInternalReadStateV0,
    advance_owned_internal_reads_v0 as advance,
)
from tests.test_witnessed_core_input_v0 import scenario


def context(*, ingress_tick=None):
    a, n, manifest, admission, requests, deps, owned, ingress = scenario(ingress_tick=ingress_tick)
    extra = []
    for i, req in enumerate(r for r in requests if r.kind is Kind.BATCH_CONSUME):
        extra.append(replace(req, request_id=70 + 2*i, kind=Kind.PROGRAM_REFERENCE,
                            target_id='program:B', domain=Domain.PROGRAM, quantity=1))
        extra.append(replace(req, request_id=71 + 2*i, kind=Kind.STATE_LOAD,
                            target_id='state:B', domain=Domain.STATE, quantity=1))
    all_reqs = tuple(sorted(requests + tuple(extra), key=lambda r: r.request_id))
    new_deps = AccessDependencyGraphV0(tuple(sorted(
        deps.dependencies + tuple(AccessDependencyV0(r.request_id, ()) for r in extra),
        key=lambda item: item.request_id,
    )))
    state = OwnedInternalReadStateV0(owned, initialize_neuron_image_v0(n))
    return a, n, manifest, admission, all_reqs, new_deps, state, ingress


def tick(c):
    return advance(*c[:6], c[6], ingress=c[7])


def trace(c, limit=8):
    states = []
    for i in range(limit):
        result = tick(c)
        states.append(result)
        c = (*c[:6], result.state, c[7])
    return tuple(states)


def read_ids(steps):
    return tuple(e.request_id for s in steps for e in s.new_reads)


def prep_ids(steps):
    return tuple(e.consume_request_id for s in steps for e in s.new_preparations)


def test_initial_owner_is_immutable():
    c = context()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        c[6].image = None


def test_first_service_tick_respects_finite_p_s_bandwidth():
    s = tick(context())
    assert tuple(e.request_id for e in s.new_reads) == (70, 71)
    assert all(e.service_boundary == 1 for e in s.new_reads)
    assert sum(x.units for x in s.witnessed_tick.owned_tick.result.quantum.slices
               if x.pe_id == 'PE1') <= 2


def test_read_receipts_come_from_real_program_and_state():
    s = tick(context())
    prog = s.new_reads[0]
    load = s.new_reads[1]
    node = next(n for n in s.state.image.network.nodes if n.node_id == 'B')
    assert prog.program == node.program
    assert prog.config == node.config
    assert prog.raw is None and prog.state_version is None
    assert load.raw == 0 and load.last_timestamp == 0 and load.state_version == 0
    assert load.program is None and load.config is None


def test_p_s_confirmations_propagate_to_owner_quantum():
    s = trace(context(), 4)[-1]
    actual = {e.request_id for e in s.state.owned.boundary.service.confirmed}
    assert set(range(70, 76)) <= actual
    pending = {e.request_id for e in s.state.owned.boundary.service.awaiting_confirmation}
    assert not set(range(70, 76)) & pending


def test_no_p_s_read_pretended_before_service_finishes():
    c = context()
    more = tuple(replace(r, service_units=4) if r.request_id in (70, 71) else r for r in c[4])
    c = (*c[:4], more, *c[5:])
    s = tick(c)
    assert not {70, 71} & {e.request_id for e in s.new_reads}
    assert 70 not in {e.request_id for e in s.state.owned.boundary.service.confirmed}


def test_batch_inputs_are_from_actual_event_consumption():
    result = trace(context())
    assert prep_ids(result) == (50,)
    prep = result[-1].state.prepared[0]
    assert prep.transition.node_id == 'B'
    assert prep.transition.event_time == 4
    assert prep.transition.channels == (0,)


def test_preparation_never_commits_neuronal_state():
    result = trace(context())
    assert result[-1].state.image == context()[6].image
    assert all(n.version == 0 for n in result[-1].state.image.neurons)


def test_preparation_records_matching_read_request_ids():
    result = trace(context())
    prep = result[-1].state.prepared[0]
    assert prep.program_read_request_id == 70
    assert prep.state_read_request_id == 71
    assert prep.consume_request_id == 50


def test_no_second_same_neuron_preparation_without_commit():
    result = trace(context(), 20)
    assert prep_ids(result) == (50,)
    assert len(result[-1].state.prepared) == 1


def test_read_receipts_are_not_duplicated_on_later_ticks():
    result = trace(context(), 6)
    assert read_ids(result) == tuple(range(70,76))
    assert len(result[-1].state.reads) == 6


def test_determinism_from_same_snapshot():
    c = context()
    assert tick(c) == tick(c)


def test_resume_reproduces_continuous_execution():
    c = context()
    full = trace(c, 8)[-1].state
    part = trace(c, 3)[-1].state
    replay = trace((*c[:6], part, c[7]), 5)[-1].state
    assert full == replay


def test_duplicate_internal_read_for_same_batch_rejected():
    c = context()
    duplicate = replace(next(r for r in c[4] if r.request_id == 70), request_id=100)
    requests = tuple(sorted(c[4] + (duplicate,), key=lambda r:r.request_id))
    deps = AccessDependencyGraphV0(tuple(sorted(c[5].dependencies +
            (AccessDependencyV0(100,()),), key=lambda d:d.request_id)))
    with pytest.raises(ValueError, match='duplicate P/S read'):
        tick((*c[:4], requests, deps, *c[6:]))


def test_missing_p_read_rejected():
    c=context()
    requests=tuple(r for r in c[4] if r.request_id!=70)
    deps=AccessDependencyGraphV0(tuple(d for d in c[5].dependencies if d.request_id!=70))
    with pytest.raises(ValueError,match='lacks P/S read'):
        tick((*c[:4],requests,deps,*c[6:]))


def test_orphan_program_read_rejected():
    c=context()
    extra=replace(next(r for r in c[4] if r.request_id==70),request_id=99,event_time=100)
    requests=tuple(sorted(c[4]+(extra,),key=lambda r:r.request_id))
    deps=AccessDependencyGraphV0(tuple(sorted(c[5].dependencies+
                  (AccessDependencyV0(99,()),),key=lambda d:d.request_id)))
    with pytest.raises(ValueError,match='orphan'):
        tick((*c[:4], requests,deps,*c[6:]))


@pytest.mark.parametrize('field,value',[
    ('target_pe_id','PE0'),
    ('epoch_id','WRONG'),
    ('quantity',2),
    ('domain',Domain.EVENT),
])
def test_bad_internal_program_read_binding_rejected(field,value):
    c=context()
    requests=tuple(replace(r,**{field:value}) if r.request_id==70 else r for r in c[4])
    with pytest.raises(ValueError,match='internal read/batch'):
        tick((*c[:4],requests,*c[5:]))


def test_wrong_image_epoch_rejected():
    c=context()
    state=replace(c[6],image=replace(c[6].image,epoch_id='E9'))
    with pytest.raises(ValueError,match='epoch mismatch'):
        tick((*c[:6],state,c[7]))


def test_wrong_image_network_rejected():
    c=context()
    other=replace(c[6].image,network=replace(c[1],nodes=c[1].nodes[:-1]))
    state=replace(c[6],image=other)
    with pytest.raises(ValueError,match='network/image'):
        tick((*c[:6],state,c[7]))


def test_replay_claim_without_read_evidence_rejected():
    c=context()
    step=tick(c)
    forged=replace(step.state,reads=())
    with pytest.raises(ValueError,match='lacks matching owner evidence'):
        tick((*c[:6],forged,c[7]))


def test_forged_read_evidence_without_confirmation_rejected():
    c=context()
    step=tick(c)
    forged=replace(c[6],reads=step.state.reads)
    with pytest.raises(ValueError,match='lacks matching owner evidence'):
        tick((*c[:6],forged,c[7]))


def test_no_caller_confirmations_can_be_supplied():
    c=context()
    with pytest.raises(TypeError):
        advance(*c[:6],c[6],ingress=c[7],confirmed_request_ids=(70,))


def test_historical_channels_cannot_be_forged():
    c=context()
    s=trace(c,6)[-1].state
    batch=s.pending_batches[0]
    forged=replace(s,pending_batches=(replace(batch,channels=(999,)),)+s.pending_batches[1:])
    with pytest.raises(ValueError,match='historical consumed channels'):
        tick((*c[:6],forged,c[7]))


def test_historical_consumed_route_cannot_be_forged():
    c=context()
    s=trace(c,6)[-1].state
    batch=s.pending_batches[0]
    forged=replace(s,pending_batches=(replace(batch,route_request_ids=(12,)),)+s.pending_batches[1:])
    with pytest.raises(ValueError,match='historical batch lacks retained EVENT consumption|historical route not bound'):
        tick((*c[:6],forged,c[7]))


def test_saved_program_read_alteration_rejected():
    c=context()
    s=tick(c).state
    forged=replace(s,reads=(replace(s.reads[0],config=None),)+s.reads[1:])
    with pytest.raises(ValueError,match='saved program read'):
        tick((*c[:6],forged,c[7]))


def test_saved_state_read_alteration_rejected():
    c=context()
    s=tick(c).state
    forged=replace(s,reads=(s.reads[0],replace(s.reads[1],raw=999)))
    with pytest.raises(ValueError,match='saved state read'):
        tick((*c[:6],forged,c[7]))


def test_prepared_result_tampering_rejected():
    c=context()
    s=trace(c,8)[-1].state
    record=s.prepared[0]
    corrupt=replace(record,transition=replace(record.transition,after_raw=7))
    forged=replace(s,prepared=(corrupt,))
    with pytest.raises(ValueError,match='prepared transition disagrees'):
        tick((*c[:6],forged,c[7]))


def test_historical_batch_requires_retained_consumption_tombstone():
    c=context()
    s=trace(c,7)[-1].state
    boundary=s.owned.boundary
    driver=boundary.driver
    storage=driver.boundary.storage
    stripped=replace(storage,consumed_ids=())
    new_owned=replace(s.owned,boundary=replace(boundary,driver=replace(driver,
                    boundary=replace(driver.boundary,storage=stripped))))
    forged=replace(s,owned=new_owned)
    with pytest.raises(ValueError,match='historical batch lacks retained EVENT consumption'):
        tick((*c[:6],forged,c[7]))


def test_event_time_is_not_service_boundary():
    steps=trace(context(ingress_tick=12),20)
    late = next(b for b in steps[-1].state.pending_batches
                if b.consume_request_id == 50)
    assert late.event_time == 4
    assert late.service_boundary >= 12
    assert late.event_time != late.service_boundary


def test_multiple_later_batches_remain_uncommitted():
    s=trace(context(),20)[-1].state
    assert len(s.pending_batches)==3
    assert len(s.prepared)==1
    assert {n.version for n in s.image.neurons}=={0}
