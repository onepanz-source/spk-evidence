"""A2b: versioned, deterministic authorization of A2a *logical* accesses.

This is a simulator policy boundary, NOT authentication, a memory bank, or
arbitration.  The trusted controller generates authority from admitted PEs;
request payloads cannot confer activity, epoch, or permission to themselves.
Caller-created Python objects are not cryptographically authenticated.
"""
from __future__ import annotations

from dataclasses import dataclass

from spk_architecture_v1.memory_projection_v1a import SCHEMA as A2A_SCHEMA

SCHEMA = 'spk-architecture-memory-authorization/v1b'
# (domain, executing activity); this table encodes the preliminary v0
# access-intent vocabulary and never derives privileges from request fields.
INTENT_POLICY = {
    'PROGRAM_REFERENCE': ('P', 'EXECUTE'),
    'STATE_LOAD': ('S', 'EXECUTE'),
    'STATE_COMMIT': ('S', 'EXECUTE'),
    'BATCH_CONSUME': ('E', 'EXECUTE'),
    'EMISSION_RECORD': ('E', 'EXECUTE'),
    'ROUTE_ENQUEUE': ('E', 'ROUTER'),
    'OBSERVATION_RECORD': ('O', 'OBSERVER'),
}
ACTIVITIES = ('EXECUTE', 'ROUTER', 'OBSERVER')


class MemoryAccessDeniedV1b(ValueError):
    """Fail closed: unauthorized or unverifiable request/authority."""


@dataclass(frozen=True)
class AccessGrantV1b:
    principal_id: str
    activity: str
    epoch_id: str
    pe_id: str
    domain: str
    allowed_intents: tuple[str, ...]


@dataclass(frozen=True)
class AccessRequestV1b:
    request_id: str
    principal_id: str
    activity: str
    epoch_id: str
    pe_id: str
    domain: str
    intent: str
    quantity: int


@dataclass(frozen=True)
class AccessAuthorityV1b:
    epoch_id: str
    grants: tuple[AccessGrantV1b, ...]


def _fail(message):
    raise MemoryAccessDeniedV1b(message)


def _principal(activity, pe_id):
    return f'spk/{activity.lower()}/{pe_id}'


def _admission(admission):
    if type(admission) is not dict or admission.get('schema') != A2A_SCHEMA:
        _fail('unrecognized A2a admission')
    pe_ids, epoch = admission.get('pe_ids'), admission.get('epoch_id')
    if (type(pe_ids) is not list or not pe_ids
            or any(type(p) is not str or not p for p in pe_ids)
            or len(set(pe_ids)) != len(pe_ids)
            or type(epoch) is not str or not epoch
            or type(admission.get('reservations')) is not dict
            or set(admission['reservations']) != set(pe_ids)):
        _fail('invalid PE ownership or execution epoch')
    return pe_ids, epoch


def issue_authority_v1b(admission):
    """Trusted controller policy template, derived ONLY from A2a admission.

    No user-provided priority, activity claim, or request fields are inputs.
    Controller provenance is procedural (trusted simulator), not secure.
    """
    pe_ids, epoch = _admission(admission)
    grants = []
    for pe in sorted(pe_ids):
        for activity in ACTIVITIES:
            for domain in ('P', 'S', 'E', 'O'):
                intents = tuple(sorted(k for k, pair in INTENT_POLICY.items()
                                       if pair == (domain, activity)))
                if intents:
                    grants.append(AccessGrantV1b(_principal(activity, pe), activity,
                                                 epoch, pe, domain, intents))
    return AccessAuthorityV1b(epoch, tuple(grants))


def _check_authority(admission, authority):
    expected = issue_authority_v1b(admission)
    if type(authority) is not AccessAuthorityV1b or authority != expected:
        _fail('authority not issued for this admitted PE/epoch policy')
    return expected


def derive_requests_v1b(admission, projection):
    """Map A2a verified logical aggregates to activity-bound requests.

    This projection is *not* a second independent authentication source;
    callers must validate A2a traces before they reach this layer.
    """
    pe_ids, epoch = _admission(admission)
    if (type(projection) is not dict or projection.get('schema') != A2A_SCHEMA
            or projection.get('epoch_id') != epoch
            or projection.get('status') not in ('CLOSED', 'PE_FAULT')
            or type(projection.get('logical_accesses')) is not list):
        _fail('invalid A2a logical access projection')
    accesses = projection['logical_accesses']
    grants = issue_authority_v1b(admission).grants
    seen = set()
    requests = []
    for i, item in enumerate(accesses):
        if type(item) is not dict or set(item) != {'pe_id', 'domain', 'intent', 'quantity'}:
            _fail('unexpected logical access record')
        pe, domain, intent, quantity = (
            item['pe_id'], item['domain'], item['intent'], item['quantity'])
        if (type(pe) is not str or pe not in pe_ids
                or type(domain) is not str or type(intent) is not str
                or type(quantity) is not int or quantity < 0
                or (quantity == 0 and intent != 'EMISSION_RECORD')
                or intent not in INTENT_POLICY
                or INTENT_POLICY[intent][0] != domain
                or (pe, domain, intent) in seen):
            _fail('invalid or duplicate access occurrence')
        seen.add((pe, domain, intent))
        if quantity == 0:
            # A2a records zero emissions for a completed guarded batch.
            # A zero occurrence is not a resource access request.
            continue
        # Activity provenance is taken from the trusted controller's grant,
        # never from a caller-supplied activity or scheduling priority.
        eligible = [g for g in grants if g.pe_id == pe and g.domain == domain
                    and intent in g.allowed_intents]
        if len(eligible) != 1:
            _fail('no unique controller grant for logical access')
        grant = eligible[0]
        requests.append(AccessRequestV1b(f'access-{i:06d}',
                                          grant.principal_id, grant.activity,
                                          epoch, pe, domain, intent, quantity))
    # Canonical sorted A2a ledger, independent of caller list ordering.
    if [(x['pe_id'], x['domain'], x['intent']) for x in accesses] != sorted(seen):
        _fail('noncanonical A2a access ordering')
    return tuple(requests)


def authorize_requests_v1b(admission, projection, authority, requests):
    """Reject re-labeled, omitted, inserted and cross-epoch accesses.

    The request sequence must match the *trusted A2a projection* exactly.
    A request's self-asserted activity or principal is never sufficient.
    """
    _check_authority(admission, authority)
    expected = derive_requests_v1b(admission, projection)
    if type(requests) is not tuple or requests != expected or any(
            type(req) is not AccessRequestV1b for req in requests):
        _fail('request list does not match verified logical access provenance')
    grant_map = {(g.principal_id, g.activity, g.epoch_id, g.pe_id, g.domain):
                 g for g in authority.grants}
    for req in requests:
        grant = grant_map.get((req.principal_id, req.activity, req.epoch_id,
                               req.pe_id, req.domain))
        if grant is None or req.intent not in grant.allowed_intents:
            _fail('access denied by PE/domain/epoch/activity grant')
    total = sum(x.quantity for x in requests)
    count_by_activity = {a: sum(x.quantity for x in requests if x.activity == a)
                         for a in ACTIVITIES}
    count_by_domain = {d: sum(x.quantity for x in requests if x.domain == d)
                       for d in ('P', 'S', 'E', 'O')}
    return {'schema': SCHEMA, 'status': 'AUTHORIZED', 'epoch_id': admission['epoch_id'],
            'request_count': len(requests), 'logical_units': total,
            'units_by_activity': count_by_activity,
            'units_by_domain': count_by_domain,
            'limitations': ['trusted in-process policy, not principal authentication',
                            'authorization of verified logical ledger, not live RAM access',
                            'no priority, memory bandwidth or service-time arbitration']}


def authorize_projection_v1b(admission, projection):
    authority = issue_authority_v1b(admission)
    requests = derive_requests_v1b(admission, projection)
    return authorize_requests_v1b(admission, projection, authority, requests)
