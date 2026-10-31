from dataclasses import FrozenInstanceError, replace

import pytest

from spk_architecture.access_v0 import (
    ActivityV0,
    AccessIntentKindV0,
    MemoryDomainV0,
    MemoryAccessIntentV0,
)


@pytest.fixture
def intent():
    return MemoryAccessIntentV0(
        request_id=0,
        epoch_id="E0",
        pe_id="PE0",
        activity=ActivityV0.EXECUTE,
        kind=AccessIntentKindV0.STATE_LOAD,
        node_id="N0",
        event_time=3,
    )


@pytest.mark.parametrize("kind,domain", [
    (AccessIntentKindV0.PROGRAM_REFERENCE,
     MemoryDomainV0.PROGRAM),
    (AccessIntentKindV0.STATE_COMMIT,
     MemoryDomainV0.STATE),
    (AccessIntentKindV0.BATCH_CONSUME,
     MemoryDomainV0.EVENT),
    (AccessIntentKindV0.ROUTE_ENQUEUE,
     MemoryDomainV0.EVENT),
    (AccessIntentKindV0.OBSERVATION_RECORD,
     MemoryDomainV0.OBSERVATION),
])
def test_domain_mapping(intent, kind, domain):
    assert replace(intent, kind=kind).domain == domain


def test_intent_is_immutable(intent):
    with pytest.raises(FrozenInstanceError):
        intent.quantity = 2


def test_event_time_is_independent_of_service_time(intent):
    assert intent.event_time == 3
    assert not hasattr(intent, "service_time")


def test_quantity_preserves_multiplicity(intent):
    batch = replace(
        intent,
        kind=AccessIntentKindV0.BATCH_CONSUME,
        quantity=3,
    )
    assert batch.quantity == 3


@pytest.mark.parametrize("field,value", [
    ("request_id", -1),
    ("request_id", True),
    ("epoch_id", ""),
    ("pe_id", " "),
    ("quantity", 0),
    ("quantity", True),
    ("event_time", -1),
])
def test_invalid_fields(intent, field, value):
    with pytest.raises(ValueError):
        replace(intent, **{field: value})


def test_node_is_required_for_active_state_access(intent):
    with pytest.raises(ValueError):
        replace(intent, node_id=None)


def test_invalid_activity_rejected(intent):
    with pytest.raises(TypeError):
        replace(intent, activity="EXECUTE")


def test_invalid_kind_rejected(intent):
    with pytest.raises(TypeError):
        replace(intent, kind="STATE_LOAD")
