"""Stage Core-derived MemoryServiceRequestV0 without admitting unbound deliveries."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_architecture.access_v0 import (
    AccessIntentKindV0 as Kind, MemoryDomainV0 as Domain, ActivityV0 as Activity,
)
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0, AccessDependencyV0
from spk_simulator.versioned_core_transition_v0 import (
    prepare_core_transition_v0, commit_core_transition_v0,
)
from spk_simulator.owned_dynamic_service_registration_v0 import (
    DynamicServiceCostsV0 as Costs,
    initialize_owned_dynamic_services_v0 as initialize,
    register_owned_computed_emission_services_v0 as register,
)
from tests.test_computed_topology_routing_v0 import context


def req(rid, kind, node, pe, timestamp):
    prefix, domain = (
        ('program', Domain.PROGRAM) if kind is Kind.PROGRAM_REFERENCE else
        ('state', Domain.STATE) if kind in (Kind.STATE_LOAD, Kind.STATE_COMMIT) else
        ('events', Domain.EVENT)
    )
    return MemoryServiceRequestV0(
        request_id=rid, principal_id=f'static-{rid}',
        activity=Activity.EXECUTE, profile_id='static-cost-v0', epoch_id='E0',
        requester_pe_id=pe, target_pe_id=pe, target_id=f'{prefix}:{node}',
        domain=domain, kind=kind, quantity=1, service_units=1,
        event_time=timestamp,
    )


def scenario(*, nodes=('C',), costs=None, first=None):
    arch, network, placement, image, prepared, _ = context('C', 3)
    source_batches = {'A': ('PE0', 2), 'B': ('PE1', 4), 'C': ('PE0', 3)}
    requests, dependencies = [], []
    for node in nodes:
        pe, t = source_batches[node]
        start = len(requests)
        kinds = (
            Kind.PROGRAM_REFERENCE, Kind.STATE_LOAD,
            Kind.BATCH_CONSUME, Kind.STATE_COMMIT,
        )
        for index, kind in enumerate(kinds):
            rid = start + index
            requests.append(req(rid, kind, node, pe, t))
            dependencies.append(AccessDependencyV0(
                rid, tuple(range(start, start + 3)) if index == 3 else (),
            ))
    requests = tuple(requests)
    graph = AccessDependencyGraphV0(tuple(dependencies))
    policy = Costs('dynamic-cost-v0', 2, 3) if costs is None else costs
    owner = initialize(arch, network, placement, image, requests, graph, policy,
                       first_dynamic_request_id=first)
    return arch, network, placement, image, prepared, owner


def do(c, *, node='C', timestamp=None, prepared=None):
    if timestamp is None:
        timestamp = {'A': 2, 'B': 4, 'C': 3}[node]
    if prepared is None:
        prepared = prepare_core_transition_v0(
            c[1], c[3], node_id=node, timestamp=timestamp, channels=(0,),
        )
    return register(c[5], c[3], prepared)


def records(state):
    return {x.request_id: x for x in state.staged_requests}


def predecessor_map(state):
    return {d.request_id: d.predecessor_ids if hasattr(d, 'predecessor_ids')
            else d.predecessors for d in state.staged_graph.dependencies}


def test_registers_dynamic_emission_and_two_route_requests():
    s = do(scenario())
    assert s.registration.generated_request_ids == (4, 5, 6)
    assert s.registration.unbound_route_request_ids == (5, 6)
    assert len(s.state.staged_requests) == 7


def test_owner_cursor_advances_with_route_count():
    s = do(scenario())
    assert s.state.allocation_ledger.next_request_id == 7


def test_source_batch_is_causally_linked_without_commit_cycle():
    s = do(scenario())
    pred = predecessor_map(s.state)
    assert pred[4] == (0, 1, 2)
    assert pred[5] == (4,) and pred[6] == (4,)
    assert pred[3] == (0, 1, 2)
    assert 3 not in pred[4]


def test_source_emission_request_matches_core_and_PE():
    s = do(scenario())
    r = records(s.state)[4]
    assert (r.kind, r.target_id, r.target_pe_id, r.requester_pe_id, r.event_time) == (
        Kind.EMISSION_RECORD, 'outputs:C', 'PE0', 'PE0', 3,
    )
    assert r.quantity == 1 and r.service_units == 2
    assert r.activity is Activity.EXECUTE


def test_route_request_has_identity_equal_to_occurrence():
    s = do(scenario())
    by_id = records(s.state)
    for route in s.registration.allocation.topology.routes:
        occ = route.occurrence
        r = by_id[occ.event_id]
        assert r.request_id == occ.event_id
        assert (r.kind, r.target_pe_id, r.requester_pe_id) == (
            Kind.ROUTE_ENQUEUE, occ.target_pe_id, occ.source_pe_id,
        )
        assert r.target_id == f'events:{occ.target_node_id}'
        assert r.event_time == occ.emission_event_time and r.service_units == 3
        assert r.activity is Activity.ROUTER


def test_routes_preserve_parallel_edge_multiplicity():
    s = do(scenario())
    occ = [x.occurrence for x in s.registration.allocation.topology.routes]
    assert len(occ) == 2
    assert len({x.event_id for x in occ}) == 2


def test_terminal_emission_has_no_route_requests():
    s = do(scenario(nodes=('B',)), node='B')
    assert s.registration.generated_request_ids == (4,)
    assert s.registration.unbound_route_request_ids == ()
    assert len(s.registration.allocation.topology.terminal_outputs) == 1
    assert records(s.state)[4].target_id == 'outputs:B'


def test_terminal_only_still_consumes_emission_request_identity():
    s = do(scenario(nodes=('B',)), node='B')
    assert s.state.allocation_ledger.next_request_id == 5


def test_emission_after_existing_full_static_namespace():
    s = do(scenario(nodes=('A', 'B', 'C')))
    assert s.registration.generated_request_ids == (12, 13, 14)


def test_custom_owner_first_dynamic_id():
    s = do(scenario(first=200))
    assert s.registration.generated_request_ids == (200, 201, 202)


def test_source_serialized_for_multiple_nodes():
    s = do(scenario(nodes=('A', 'B', 'C')), node='C')
    assert predecessor_map(s.state)[12] == (8, 9, 10)


def test_second_computed_source_cannot_reuse_allocated_identity():
    c = scenario(nodes=('A', 'B', 'C'))
    first = do(c)
    source = prepare_core_transition_v0(c[1], c[3], node_id='A',
                                        timestamp=2, channels=(0,))
    second = register(first.state, c[3], source)
    assert second.registration.generated_request_ids == (15, 16)
    assert second.state.allocation_ledger.next_request_id == 17


def test_second_registration_preserves_original_dynamic_request():
    c = scenario(nodes=('A', 'B', 'C'))
    first = do(c)
    source = prepare_core_transition_v0(c[1], c[3], node_id='A',
                                        timestamp=2, channels=(0,))
    second = register(first.state, c[3], source)
    assert tuple(records(first.state).items()) == tuple(
        (rid, r) for rid, r in records(second.state).items() if rid < 15
    )


def test_second_registration_keeps_both_history_entries():
    c = scenario(nodes=('A', 'B', 'C'))
    first = do(c)
    source = prepare_core_transition_v0(c[1], c[3], node_id='A',
                                        timestamp=2, channels=(0,))
    second = register(first.state, c[3], source)
    assert len(second.state.registrations) == 2
    assert len(second.state.allocation_ledger.allocations) == 2


def test_existing_requests_are_not_mutated():
    c = scenario()
    original = c[5].base_requests
    s = do(c)
    assert c[5].staged_requests == original
    assert s.state.base_requests == original


def test_existing_graph_remains_unchanged():
    c = scenario()
    s = do(c)
    assert c[5].staged_graph == c[5].base_graph
    assert s.state.base_graph == c[5].base_graph


def test_register_snapshot_is_deterministic():
    c = scenario()
    assert do(c) == do(c)


def test_duplicate_same_neuron_version_rejected():
    c = scenario()
    s = do(c)
    with pytest.raises(ValueError, match='already allocated'):
        register(s.state, c[3], c[4])


def test_no_source_batch_rejected():
    c = scenario(nodes=('C',))
    prepared = prepare_core_transition_v0(c[1], c[3],
                                          node_id='A', timestamp=2, channels=(0,))
    with pytest.raises(ValueError, match='no unique'):
        register(c[5], c[3], prepared)


def test_wrong_source_time_rejected():
    c = scenario(nodes=('C',))
    prepared = prepare_core_transition_v0(c[1], c[3],
                                          node_id='C', timestamp=5, channels=(0,))
    with pytest.raises(ValueError, match='no unique'):
        register(c[5], c[3], prepared)


def test_wrong_image_epoch_rejected():
    c = scenario()
    with pytest.raises(ValueError):
        register(c[5], replace(c[3], epoch_id='E2'), c[4])


def test_forged_core_output_rejected():
    c = scenario()
    with pytest.raises(ValueError, match='Core preparation mismatch'):
        register(c[5], c[3], replace(c[4], candidate_outputs=((3, 999),)))


def test_forged_core_version_rejected():
    c = scenario()
    with pytest.raises(ValueError):
        register(c[5], c[3], replace(c[4], base_version=99))


def test_service_cost_must_be_positive():
    with pytest.raises(ValueError, match='service cost'):
        Costs('policy', 0, 3)


@pytest.mark.parametrize('value', (0, -1, True, 1.0, '1'))
def test_invalid_route_unit_cost_rejected(value):
    with pytest.raises(ValueError, match='service cost'):
        Costs('policy', 1, value)


def test_invalid_service_profile_rejected():
    with pytest.raises(ValueError, match='service profile'):
        Costs(' cost ', 1, 2)


def test_staged_state_is_immutable():
    c = scenario()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        c[5].registrations = ()


def test_cost_policy_persists_in_state():
    c = scenario(costs=Costs('test-cost', 4, 7))
    s = do(c)
    assert records(s.state)[4].service_units == 4
    assert records(s.state)[5].service_units == 7


def test_tamper_registered_route_cost_rejected():
    s = do(scenario())
    reqs = tuple(replace(r, service_units=99) if r.request_id == 5 else r
                 for r in s.state.staged_requests)
    with pytest.raises(ValueError, match='invalid staged ROUTE'):
        replace(s.state, staged_requests=reqs)


def test_tamper_registered_route_target_rejected():
    s = do(scenario())
    reqs = tuple(replace(r, target_id='events:wrong') if r.request_id == 5 else r
                 for r in s.state.staged_requests)
    with pytest.raises(ValueError, match='invalid staged ROUTE'):
        replace(s.state, staged_requests=reqs)


def test_tamper_emission_quantity_rejected():
    s = do(scenario())
    reqs = tuple(replace(r, quantity=90) if r.request_id == 4 else r
                 for r in s.state.staged_requests)
    with pytest.raises(ValueError, match='invalid staged EMISSION'):
        replace(s.state, staged_requests=reqs)


def test_tamper_route_dependency_rejected():
    s = do(scenario())
    deps = tuple(AccessDependencyV0(d.request_id, ()) if d.request_id == 5 else d
                 for d in s.state.staged_graph.dependencies)
    with pytest.raises(ValueError, match='invalid staged ROUTE'):
        replace(s.state, staged_graph=AccessDependencyGraphV0(deps))


def test_tamper_emission_dependency_rejected():
    s = do(scenario())
    deps = tuple(AccessDependencyV0(d.request_id, (0,)) if d.request_id == 4 else d
                 for d in s.state.staged_graph.dependencies)
    with pytest.raises(ValueError, match='invalid staged EMISSION'):
        replace(s.state, staged_graph=AccessDependencyGraphV0(deps))


def test_tamper_dynamic_namespace_rejected():
    s = do(scenario())
    with pytest.raises(ValueError):
        replace(s.state, staged_requests=s.state.staged_requests[:-1])


def test_tamper_existing_service_request_rejected():
    s = do(scenario())
    reqs = tuple(replace(r, service_units=999) if r.request_id == 0 else r
                 for r in s.state.staged_requests)
    with pytest.raises(ValueError, match='base service request mutated'):
        replace(s.state, staged_requests=reqs)


def test_broken_existing_service_graph_rejected():
    c = scenario()
    invalid = AccessDependencyGraphV0(tuple(
        AccessDependencyV0(d.request_id, ()) for d in c[5].base_graph.dependencies
    ))
    with pytest.raises(ValueError, match='serialized'):
        initialize(c[0], c[1], c[2], c[3], c[5].base_requests,
                   invalid, Costs('test', 1, 1))


def test_repeated_snapshot_cannot_reallocate_inside_successor():
    c = scenario()
    after = do(c)
    with pytest.raises(ValueError):
        register(after.state, c[3], c[4])


def test_registration_does_not_create_active_controller_state():
    s = do(scenario())
    assert not hasattr(s.state, 'owned')
    assert not hasattr(s.registration, 'publication')


def test_emission_service_does_not_depend_on_unconfirmed_state_commit():
    s = do(scenario())
    assert 3 not in predecessor_map(s.state)[4]


def test_route_service_depends_on_computed_emission_request():
    s = do(scenario())
    assert all(predecessor_map(s.state)[rid] == (4,) for rid in (5, 6))


def test_registration_does_not_claim_destination_consume_owner():
    s = do(scenario())
    assert s.registration.unbound_route_request_ids == (5, 6)
    assert not hasattr(s.registration, 'consume_request_id')


def test_snapshot_with_changed_registration_provenance_rejected():
    s = do(scenario())
    reg = replace(s.registration, source_commit_request_id=900)
    with pytest.raises(ValueError, match='not bound to source'):
        replace(s.state, registrations=(reg,))


def test_registered_route_service_retains_event_time_not_service_boundary():
    s = do(scenario())
    assert all(records(s.state)[rid].event_time == 3 for rid in (5, 6))


def test_image_remains_unchanged_after_registration():
    c = scenario()
    before = c[3]
    do(c)
    assert c[3] == before


def test_bad_initializer_request_coverage_rejected():
    c = scenario()
    with pytest.raises(ValueError, match='coverage'):
        initialize(c[0], c[1], c[2], c[3], c[5].base_requests,
                   AccessDependencyGraphV0(c[5].base_graph.dependencies[:-1]),
                   c[5].cost_policy)


def test_noncanonical_original_requests_rejected():
    c = scenario()
    with pytest.raises(ValueError, match='noncanonical'):
        initialize(c[0], c[1], c[2], c[3], c[5].base_requests[::-1],
                   c[5].base_graph, c[5].cost_policy)


@pytest.mark.parametrize('field,value', (
    ('activity', Activity.ROUTER),
    ('profile_id', 'untrusted-cost-profile'),
    ('principal_id', 'external-pretender'),
))
def test_forged_emission_provenance_rejected(field, value):
    s = do(scenario())
    reqs = tuple(replace(r, **{field: value}) if r.request_id == 4 else r
                 for r in s.state.staged_requests)
    with pytest.raises(ValueError, match='invalid staged EMISSION'):
        replace(s.state, staged_requests=reqs)


@pytest.mark.parametrize('field,value', (
    ('activity', Activity.EXECUTE),
    ('profile_id', 'untrusted-cost-profile'),
    ('principal_id', 'external-pretender'),
))
def test_forged_route_provenance_rejected(field, value):
    s = do(scenario())
    reqs = tuple(replace(r, **{field: value}) if r.request_id == 5 else r
                 for r in s.state.staged_requests)
    with pytest.raises(ValueError, match='invalid staged ROUTE'):
        replace(s.state, staged_requests=reqs)
