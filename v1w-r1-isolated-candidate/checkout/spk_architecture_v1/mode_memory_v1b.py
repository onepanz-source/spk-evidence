"""A4b: trusted mode-bound authority and priorities over A2b/A2c logical memory.

A completed A4a EXECUTE / VERIFY run may authorize post-run A2a logical
memory-demand service. VERIFY requests run in a logically private replay scope,
not against deployed memory; A2c never performs physical reads or writes.
TRAINING and REMODEL stage digests only and receive no A2b memory-service
privilege. No security claim against malicious Python code/forged host objects.
"""
from __future__ import annotations

from dataclasses import dataclass

from search.spk_24n_differential_evidence_v0 import canonical, sha
from spk_architecture_v1.operating_modes_v1a import ModeControllerV1a
from spk_architecture_v1.memory_access_v1b import (
    authorize_requests_v1b, derive_requests_v1b, issue_authority_v1b,
)
from spk_architecture_v1.memory_service_v1c import (
    memory_service_plan_v1c, serve_authorized_v1c,
)

SCHEMA = 'spk-architecture-mode-memory-authority/v1b'
MODE_POLICY = {
    'EXECUTE': {'action': 'RUN', 'scope': 'EXECUTION_LEDGER',
                'priority': ('E', 'S', 'P', 'O')},
    'VERIFY': {'action': 'REPLAY', 'scope': 'ISOLATED_REPLAY_LEDGER',
               'priority': ('P', 'S', 'E', 'O')},
}


class ModeMemoryDeniedV1b(ValueError):
    """Mode, epoch, provenance or priority is insufficient: deny closed."""


@dataclass(frozen=True)
class ModeMemoryPermitV1b:
    mode: str
    epoch: int
    context_sha256: str
    audit_sha256: str
    result_sha256: str
    admission_sha256: str
    projection_sha256: str
    authority_sha256: str
    request_sha256: str
    scope: str
    priority_order: tuple[str, ...]


def _hash(x):
    return sha(canonical(x))


def _issue(controller, admission, projection):
    if type(controller) is not ModeControllerV1a:
        raise ModeMemoryDeniedV1b('expected trusted A4a controller')
    b = controller.boundary()
    policy = MODE_POLICY.get(b.mode)
    if policy is None:
        raise ModeMemoryDeniedV1b('mode may only stage candidates, not serve memory')
    if b.status != 'QUIESCENT' or not controller.audit:
        raise ModeMemoryDeniedV1b('memory service requires completed quiescent A4a run')
    last = controller.audit[-1]
    if (type(last) is not dict or last.get('kind') != policy['action']
            or last.get('mode') != b.mode or last.get('epoch') != b.epoch
            or last.get('context_sha256') != b.context_sha256
            or type(last.get('result_sha256')) is not str):
        raise ModeMemoryDeniedV1b('mode audit does not close the current execution')
    # Admission and projection remain caller-verified A2a references; A2b
    # checks logical intent provenance but does not attest physical activity.
    authority = issue_authority_v1b(admission)
    requests = derive_requests_v1b(admission, projection)
    verdict = authorize_requests_v1b(admission, projection, authority, requests)
    if verdict['status'] != 'AUTHORIZED':
        raise ModeMemoryDeniedV1b('A2b logical access authorization refused')
    grant_sha = _hash({'epoch': authority.epoch_id,
                       'grants': [vars(g) for g in authority.grants]})
    return (ModeMemoryPermitV1b(
        b.mode, b.epoch, b.context_sha256, b.audit_sha256,
        last['result_sha256'], _hash(admission), _hash(projection),
        grant_sha, _hash([vars(r) for r in requests]),
        policy['scope'], policy['priority']), authority, requests)


def issue_mode_memory_permit_v1b(controller, admission, projection):
    """Pin trusted-mode grant to current completed A4a run and A2a ledger."""
    return _issue(controller, admission, projection)[0]


def serve_mode_memory_v1b(controller, permit, admission, projection, *,
                           pe_slots=2, fabric_slots_per_tick=3,
                           domain_slots_per_tick=2, max_service_ticks=65536):
    """Apply mode priority to *aggregate logical* A2c units, not live RAM.

    The caller cannot choose priority or scope. An A4a transition or newer
    completed action revokes the old permit through its audit fingerprint.
    """
    if type(permit) is not ModeMemoryPermitV1b:
        raise ModeMemoryDeniedV1b('missing controller-issued permit')
    expected, authority, requests = _issue(controller, admission, projection)
    if permit != expected:
        raise ModeMemoryDeniedV1b('stale, altered or cross-mode memory permit')
    plan = memory_service_plan_v1c(
        admission, pe_slots=pe_slots,
        fabric_slots_per_tick=fabric_slots_per_tick,
        domain_slots_per_tick=domain_slots_per_tick,
        priority_order=expected.priority_order,
        max_service_ticks=max_service_ticks)
    service = serve_authorized_v1c(admission, projection, authority, requests, plan)
    if (service['status'] != 'SERVED'
            or tuple(service['policy']['priority_order']) != expected.priority_order
            or service['logical_units'] != sum(x.quantity for x in requests)):
        raise AssertionError('mode memory service drift')
    return {'schema': SCHEMA, 'status': 'SERVED',
            'mode': expected.mode, 'epoch': expected.epoch,
            'context_sha256': expected.context_sha256,
            'scope': expected.scope,
            'priority_order': list(expected.priority_order),
            'permit_sha256': _hash(vars(expected)),
            'service': service,
            'limitations': [
                'logical A2a/A2b aggregate ledger after completed A4a epoch',
                'VERIFY scope denotes private logical replay, not isolated physical RAM',
                'no live A3d memory interposition or program writes',
                'no candidate promotion or cryptographic host authentication',
            ]}
