"""Experimental SPK Core transition in a separate, versioned neuron-state image.

This module executes frozen ``run_core_batch`` without calling Network v0's
``run_network_v0``.  It does NOT grant service, reserve OUTPUT, move events,
or confirm any MemoryServiceRequestV0.  All output pairs are *candidates* until
an independent storage controller admits their actual architectural effects.
"""

from dataclasses import dataclass

from spk_network.model_v0 import NetworkV0
# The frozen Network runtime imports this frozen Core entry point, but its
# network-level event loop is deliberately NOT used here.
from spk_network.runtime_v0 import run_core_batch


@dataclass(frozen=True, slots=True)
class NeuronVersionV0:
    node_id: str
    raw: int
    last_timestamp: int
    version: int


@dataclass(frozen=True, slots=True)
class VersionedNeuronImageV0:
    network: NetworkV0
    epoch_id: str
    neurons: tuple[NeuronVersionV0, ...]


@dataclass(frozen=True, slots=True)
class PreparedCoreTransitionV0:
    epoch_id: str
    node_id: str
    event_time: int
    channels: tuple[int, ...]
    base_version: int
    before_raw: int
    before_timestamp: int
    after_raw: int
    after_timestamp: int
    final_guard: bool
    candidate_outputs: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class CoreStateCommitReceiptV0:
    epoch_id: str
    node_id: str
    event_time: int
    old_version: int
    new_version: int
    old_raw: int
    new_raw: int
    old_timestamp: int
    new_timestamp: int
    candidate_outputs: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class CoreStateCommitV0:
    state: VersionedNeuronImageV0
    receipt: CoreStateCommitReceiptV0


def _require_image(network: NetworkV0, image: VersionedNeuronImageV0) -> None:
    if type(network) is not NetworkV0:
        raise TypeError('invalid network')
    if type(image) is not VersionedNeuronImageV0:
        raise TypeError('invalid versioned neuron image')
    if image.network != network:
        raise ValueError('image/network mismatch')
    if type(image.epoch_id) is not str or not image.epoch_id or image.epoch_id.strip() != image.epoch_id:
        raise ValueError('invalid epoch')
    if type(image.neurons) is not tuple:
        raise TypeError('neurons must be a tuple')
    node_by_id = {n.node_id: n for n in network.nodes}
    ids = tuple(n.node_id for n in image.neurons)
    if ids != tuple(sorted(node_by_id)):
        raise ValueError('noncanonical/missing/duplicate neuron entries')
    for item in image.neurons:
        if type(item) is not NeuronVersionV0:
            raise TypeError('invalid neuron entry')
        cfg = node_by_id[item.node_id].config
        if (type(item.raw) is not int or not 0 <= item.raw <= cfg.max_raw
                or type(item.last_timestamp) is not int or item.last_timestamp < 0
                or type(item.version) is not int or item.version < 0):
            raise ValueError('invalid neuron state')
        if item.version == 0 and (item.raw != node_by_id[item.node_id].initial_raw or item.last_timestamp != 0):
            raise ValueError('uncommitted neuron image differs from initial state')


def initialize_neuron_image_v0(
    network: NetworkV0, *, epoch_id: str = 'E0',
) -> VersionedNeuronImageV0:
    if type(network) is not NetworkV0:
        raise TypeError('invalid network')
    if type(epoch_id) is not str or not epoch_id or epoch_id.strip() != epoch_id:
        raise ValueError('invalid epoch_id')
    image = VersionedNeuronImageV0(
        network=network,
        epoch_id=epoch_id,
        neurons=tuple(
            NeuronVersionV0(n.node_id, n.initial_raw, 0, 0)
            for n in sorted(network.nodes, key=lambda n: n.node_id)
        ),
    )
    _require_image(network, image)
    return image


def _check_batch(image: VersionedNeuronImageV0, node_id: str,
                 timestamp: int, channels: tuple[int, ...]) -> NeuronVersionV0:
    if type(node_id) is not str:
        raise TypeError('node_id must be str')
    versions = {n.node_id: n for n in image.neurons}
    if node_id not in versions:
        raise ValueError('unknown node')
    if type(timestamp) is not int or timestamp < 0:
        raise ValueError('invalid EVENT_TIME')
    if (type(channels) is not tuple or not channels
            or any(type(c) is not int or c < 0 for c in channels)
            or channels != tuple(sorted(channels))):
        raise ValueError('batch must be nonempty and canonically sorted, preserving multiplicity')
    prior = versions[node_id]
    if timestamp < prior.last_timestamp or (prior.version and timestamp <= prior.last_timestamp):
        raise ValueError('non-monotone batch EVENT_TIME for neuron')
    return prior


def prepare_core_transition_v0(
    network: NetworkV0, image: VersionedNeuronImageV0,
    *, node_id: str, timestamp: int, channels: tuple[int, ...],
) -> PreparedCoreTransitionV0:
    """Compute frozen Core result, without mutating memory or confirming service."""
    _require_image(network, image)
    prior = _check_batch(image, node_id, timestamp, channels)
    node = next(n for n in network.nodes if n.node_id == node_id)
    result = run_core_batch(
        node.config, node.program,
        timestamp=timestamp, channels=channels,
        initial_raw=prior.raw, previous_timestamp=prior.last_timestamp,
    )
    pairs = tuple(result.output.as_pairs())
    if (type(result.final_raw) is not int or not 0 <= result.final_raw <= node.config.max_raw
            or type(result.last_timestamp) is not int or result.last_timestamp != timestamp
            or type(result.final_guard) is not bool):
        raise ValueError('invalid frozen Core transition result')
    if any(type(t) is not int or type(c) is not int or t != timestamp or c < 0
           for t, c in pairs):
        raise ValueError('invalid frozen Core emission')
    return PreparedCoreTransitionV0(
        image.epoch_id, node_id, timestamp, channels,
        prior.version, prior.raw, prior.last_timestamp,
        result.final_raw, result.last_timestamp, result.final_guard, pairs,
    )


def commit_core_transition_v0(
    network: NetworkV0, image: VersionedNeuronImageV0,
    prepared: PreparedCoreTransitionV0,
) -> CoreStateCommitV0:
    """Commit only a recomputed authentic Core transition against current version.

    WARNING: the returned receipt only proves the *local immutable image* was
    updated under this function's contract. It is not an authenticated service
    request confirmation, and it does not prove OUTPUT was admitted.
    """
    _require_image(network, image)
    if type(prepared) is not PreparedCoreTransitionV0:
        raise TypeError('invalid prepared transition')
    if prepared.epoch_id != image.epoch_id:
        raise ValueError('epoch mismatch')
    prior = _check_batch(image, prepared.node_id, prepared.event_time, prepared.channels)
    if (prepared.base_version != prior.version
            or prepared.before_raw != prior.raw
            or prepared.before_timestamp != prior.last_timestamp):
        raise ValueError('stale or conflicting state version')
    # The caller may fabricate or alter a PreparedCoreTransitionV0. Never trust
    # its result fields; independently recompute from frozen Core v0.
    expected = prepare_core_transition_v0(
        network, image, node_id=prepared.node_id,
        timestamp=prepared.event_time, channels=prepared.channels,
    )
    if expected != prepared:
        raise ValueError('prepared Core result disagrees with frozen Core execution')
    updated = VersionedNeuronImageV0(
        network=network,
        epoch_id=image.epoch_id,
        neurons=tuple(
            NeuronVersionV0(n.node_id, prepared.after_raw,
                            prepared.after_timestamp, n.version + 1)
            if n.node_id == prepared.node_id else n
            for n in image.neurons
        ),
    )
    _require_image(network, updated)
    receipt = CoreStateCommitReceiptV0(
        image.epoch_id, prepared.node_id, prepared.event_time,
        prior.version, prior.version + 1,
        prior.raw, prepared.after_raw,
        prior.last_timestamp, prepared.after_timestamp,
        prepared.candidate_outputs,
    )
    return CoreStateCommitV0(updated, receipt)
