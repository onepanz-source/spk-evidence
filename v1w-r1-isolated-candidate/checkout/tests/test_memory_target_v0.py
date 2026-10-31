from dataclasses import FrozenInstanceError, replace

import pytest

from spk_architecture.access_v0 import (
    ActivityV0,
    AccessIntentKindV0,
    MemoryAccessIntentV0,
    MemoryDomainV0,
)
from spk_architecture.memory_target_v0 import (
    MemorySpaceV0,
    MemoryTargetV0,
    MemoryTargetCatalogV0,
    MemoryTargetReferenceV0,
    resolve_memory_target_v0,
)


@pytest.fixture
def target():
    return MemoryTargetV0(
        target_id="state-A",
        space=MemorySpaceV0.ACTIVE,
        epoch_id="E0",
        pe_id="PE0",
        domain=MemoryDomainV0.STATE,
        owner_node_id="A",
    )


@pytest.fixture
def intent():
    return MemoryAccessIntentV0(
        request_id=1,
        epoch_id="E0",
        pe_id="PE0",
        activity=ActivityV0.EXECUTE,
        kind=AccessIntentKindV0.STATE_LOAD,
        node_id="A",
        event_time=3,
    )


def test_target_identity(target):
    assert target.owner_node_id == "A"
    assert target.space is MemorySpaceV0.ACTIVE


def test_target_immutable(target):
    with pytest.raises(FrozenInstanceError):
        target.pe_id = "PE1"


@pytest.mark.parametrize("field,value", [
    ("target_id", ""),
    ("epoch_id", " E0"),
    ("pe_id", " "),
    ("owner_node_id", ""),
])
def test_invalid_identifiers(target, field, value):
    with pytest.raises(ValueError):
        replace(target, **{field: value})


def test_state_requires_owner(target):
    with pytest.raises(ValueError):
        replace(target, owner_node_id=None)


def test_shared_event_target(target):
    event_target = replace(
        target,
        target_id="event-buffer",
        domain=MemoryDomainV0.EVENT,
        owner_node_id=None,
    )

    assert event_target.owner_node_id is None


@pytest.mark.parametrize("field,value", [
    ("space", "ACTIVE"),
    ("domain", "S"),
])
def test_invalid_enum_types(target, field, value):
    with pytest.raises(TypeError):
        replace(target, **{field: value})


def test_catalog_lookup(target):
    catalog = MemoryTargetCatalogV0((target,))
    assert catalog.get("state-A") == target


def test_catalog_rejects_duplicate_ids(target):
    with pytest.raises(ValueError):
        MemoryTargetCatalogV0((target, target))


def test_catalog_rejects_empty():
    with pytest.raises(ValueError):
        MemoryTargetCatalogV0(())


def test_catalog_rejects_invalid_member(target):
    with pytest.raises(TypeError):
        MemoryTargetCatalogV0((target, "invalid"))


def test_catalog_requires_tuple(target):
    with pytest.raises(TypeError):
        MemoryTargetCatalogV0([target])


def test_unknown_target(target):
    catalog = MemoryTargetCatalogV0((target,))

    with pytest.raises(KeyError):
        catalog.get("missing")


def test_matching_reference(target, intent):
    catalog = MemoryTargetCatalogV0((target,))

    reference = MemoryTargetReferenceV0(
        intent=intent,
        target_id="state-A",
    )

    assert resolve_memory_target_v0(
        catalog, reference
    ) == target


def test_remote_epoch_reference_is_not_authorization(
    target, intent
):
    remote = replace(
        target,
        pe_id="PE1",
        epoch_id="E1",
        space=MemorySpaceV0.SNAPSHOT,
    )

    catalog = MemoryTargetCatalogV0((remote,))
    reference = MemoryTargetReferenceV0(
        intent=intent,
        target_id="state-A",
    )

    # Identity resolution is permitted.
    # A2 must separately evaluate access rights.
    assert resolve_memory_target_v0(
        catalog, reference
    ) == remote


def test_domain_mismatch_rejected(target, intent):
    catalog = MemoryTargetCatalogV0((target,))

    other_intent = replace(
        intent,
        kind=AccessIntentKindV0.PROGRAM_REFERENCE,
    )

    reference = MemoryTargetReferenceV0(
        intent=other_intent,
        target_id="state-A",
    )

    with pytest.raises(ValueError):
        resolve_memory_target_v0(catalog, reference)


def test_reference_requires_valid_intent():
    with pytest.raises(TypeError):
        MemoryTargetReferenceV0(
            intent="invalid",
            target_id="state-A",
        )
