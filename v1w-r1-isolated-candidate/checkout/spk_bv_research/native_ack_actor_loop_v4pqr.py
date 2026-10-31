"""v4p-v4r: source-derived actor judgment, causal transport and actor receipt.

This is an isolated research fork of the SHA-pinned v4m-v4o causal executor.
Its hooks observe *reexecuted* native ingress and actor-local output; unlike
v4m, request timestamps do not come from a frozen shadow grant ledger.
The credit register is a DERIVED actor, not a frozen neuron's learner.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path

from spk_bv_research.native_ack_causal_replay_v4mno import (
    CausalProbeRejected, SyntheticACKRequest,
)

SCHEMA = 'spk-bv-endogenous-actor-ACK-causal-execution/research-v4p-v4r'
STATUS = 'REEXECUTED_ACTOR_JUDGMENT_TRANSPORT_AND_DERIVED_CREDIT_NO_NATIVE_LEARNING'
PINNED_PARENT_SHA = 'b256c82f6452eb39789481d265d6e79bbcb5527e4c8155b66524a0e8d8680261'
ZERO_ROOT = '0' * 64


@dataclass(frozen=True)
class ActorJudgment:
    identity: str
    source_emission: str
    issuer: str
    recipient: str
    response: int
    emitted_tick: int
    ingress_tick: int
    created_tick: int
    ready_tick: int
    source_pe: str
    target_pe: str


def _canon(item):
    return json.dumps(item, sort_keys=True, ensure_ascii=True,
                      separators=(',', ':')).encode('utf-8') + b'\n'


def _sha_receipt(event):
    return sha256(_canon(event)).hexdigest()


def _pinned_executable():
    parent = Path(__file__).with_name('native_ack_causal_replay_v4mno.py')
    raw = parent.read_bytes()
    if sha256(raw).hexdigest() != PINNED_PARENT_SHA:
        raise CausalProbeRejected('v4p native causal parent source SHA drift')
    source = raw.decode('utf-8')
    # Reuse, don't redeclare, the pinned exception/request dataclass. This
    # prevents dynamic-module dataclass resolution and preserves exact types.
    begin = source.index('class CausalProbeRejected(ValueError):')
    end = source.index('def _validate_requests(requests, fabric, start, bv):')
    if source[begin:end].count('class SyntheticACKRequest:') != 1:
        raise CausalProbeRejected('v4p pinned request dataclass anchor drift')
    source = source[:begin] + source[end:]

    # Every anchor must be exact and unique. The parent is never changed.
    modifications = (
        ("    ready_acks = []\n", """    ready_acks = []
    _v4p_requests, _v4p_judgments, _v4p_applied = [], [], []
    _v4p_seen = set()
    _v4p_balances = {nid: 0 for nid in nodes}
    _v4p_roots = {nid: '0' * 64 for nid in nodes}
"""),
        ("                for ch in outs:\n", """                _v4p_generate(now, nid, parents, outs, occurrences, owners,
                              _v4p_requests, _v4p_judgments, _v4p_seen, ready_acks)
                for ch in outs:
"""),
        ("                                       'actor_credit_applied': False})\n", """                                       'actor_credit_applied': False})
                _v4p_deliver(item, now, ack_grants, _v4p_requests,
                             _v4p_judgments, _v4p_applied, _v4p_balances,
                             _v4p_roots, ack_deliveries)
"""),
        ("len(ack_deliveries) != len(requests)",
         "len(ack_deliveries) != len(_v4p_requests)"),
        ("'requests': len(requests)", "'requests': len(_v4p_requests)"),
        ("'applied_actor_credits': 0", "'applied_actor_credits': len(_v4p_applied)"),
        ("'owner_ACK_FIFOs_decremented': 0", "'owner_ACK_FIFOs_decremented': len(_v4p_applied)"),
        ("'real_actor_ACK_evidence': False", "'real_actor_ACK_evidence': True"),
        ("'synthetic_ack': {'requests'", "'derived_actor_ack': {'requests'"),
        ("'synthetic_ack_sends'", "'actor_ack_sends'"),
        ("'synthetic_ack_transport_blocked'", "'actor_ack_transport_blocked'"),
        ("        'native_source_timeline_frozen': False,", """        'derived_actor': {
            'judgments': [asdict(j) for j in _v4p_judgments],
            'applied_receipts': _v4p_applied,
            'applied_credit_by_actor': dict(sorted(_v4p_balances.items())),
            'receipt_roots': dict(sorted(_v4p_roots.items())),
            'native_learner_mutations': 0,
            'policy_denials_are_negative_judgments': False,
        },
        'native_source_timeline_frozen': False,"""),
    )
    for anchor, substitution in modifications:
        if source.count(anchor) != 1:
            raise CausalProbeRejected('v4p native parent hook missing or ambiguous: ' + anchor[:60])
        source = source.replace(anchor, substitution, 1)
    # Compile only after all SHA and exact source-anchor checks.
    return compile(source, '<v4pqr-pinned-native-causal-fork>', 'exec')


_EXECUTABLE = _pinned_executable()


def execute_endogenous_probe(case, fabric, tplan, pplan, mplan, lplan, bv,
                             *, feedback=True, max_judgments=128,
                             max_abs_actor_credit=256):
    """Reexecute forward/BV and earn each actor ACK from a real receiver batch.

    Actor source computations have semantic sign 1 if their newly computed
    output is nonempty, else -1 (v2h research convention). No external request
    sequence, invented silence judgment, or frozen-native learning occurs.
    """
    if (type(feedback) is not bool or type(max_judgments) is not int or
            not 0 <= max_judgments <= 128 or
            type(max_abs_actor_credit) is not int or
            not 0 <= max_abs_actor_credit <= 512):
        raise CausalProbeRejected('invalid bounded actor feedback policy')
    if not feedback:
        max_judgments = 0
    granted = set()
    received = set()

    def generate(now, nid, parents, outs, occurrences, owners,
                 requests, judgments, seen, ready):
        for oid in parents:
            if oid in seen or oid not in occurrences:
                raise CausalProbeRejected('actor judgment parent forged or duplicated')
            occ = occurrences[oid]
            if (occ['target'] != nid or occ['delivered_at'] is None or
                    occ['delivered_at'] > now or occ['emitted_at'] >= now or
                    owners.get(nid) != occ['target_pe'] or
                    owners.get(occ['source']) != occ['source_pe']):
                raise CausalProbeRejected('actor judgment lacks causal native ingress')
            seen.add(oid)
            if not feedback:
                continue
            if len(judgments) >= max_judgments:
                raise CausalProbeRejected('actor judgment quota exhausted')
            if occ['source_pe'] == occ['target_pe']:
                raise CausalProbeRejected('local actor ACK service is not modeled')
            identity = f'j{len(judgments) + 1}'
            request = SyntheticACKRequest(identity, now + 1,
                                          occ['target_pe'], occ['source_pe'])
            judgment = ActorJudgment(
                identity, oid, nid, occ['source'], 1 if outs else -1,
                occ['emitted_at'], occ['delivered_at'], now, now + 1,
                request.source_pe, request.target_pe)
            judgments.append(judgment)
            requests.append(request)
            ready.append(request)

    def deliver(request, now, grants, requests, judgments, applied,
                balances, roots, delivery_rows):
        if (request.identity in received or len(requests) != len(judgments)):
            raise CausalProbeRejected('actor ACK replay or request/semantic drift')
        index = next((i for i, r in enumerate(requests)
                      if r.identity == request.identity), None)
        if index is None:
            raise CausalProbeRejected('delivered ACK has no native receiver judgment')
        j = judgments[index]
        matched = [g for g in grants if g['identity'] == request.identity]
        if (len(matched) != 1 or matched[0]['delivered_at'] != now or
                matched[0]['tick'] < j.ready_tick or
                matched[0]['source_pe'] != j.source_pe or
                matched[0]['target_pe'] != j.target_pe or
                now <= j.created_tick or j.response not in (-1, 1) or
                j.identity in received):
            raise CausalProbeRejected('actor ACK transport/resource custody invalid')
        received.add(j.identity)
        before = balances[j.recipient]
        after = before + j.response
        if abs(after) > max_abs_actor_credit:
            # A real transport delivery may be denied by policy. This is NOT
            # negative evidence, an ACK loss or a successful actor credit.
            delivery_rows[-1]['actor_credit_denied_by_policy'] = True
            return
        seq = 1 + sum(x['actor'] == j.recipient for x in applied)
        event = {
            'actor': j.recipient, 'owner_pe': j.target_pe,
            'issuer': j.issuer, 'source_emission': j.source_emission,
            'judgment_id': j.identity, 'response': j.response,
            'seq': seq, 'created_tick': j.created_tick,
            'grant_tick': matched[0]['tick'], 'delivery_tick': now,
            'credit_before': before, 'credit_after': after,
            'chain_prev': roots[j.recipient],
        }
        event['chain_digest'] = _sha_receipt(event)
        applied.append(event)
        balances[j.recipient] = after
        roots[j.recipient] = event['chain_digest']
        delivery_rows[-1]['actor_credit_applied'] = True

    namespace = {
        '__name__': 'spk_bv_research.v4pqr_fork',
        '_v4p_generate': generate, '_v4p_deliver': deliver,
        'asdict': asdict, 'CausalProbeRejected': CausalProbeRejected,
        'SyntheticACKRequest': SyntheticACKRequest,
    }
    exec(_EXECUTABLE, namespace)
    result = namespace['execute_causal_probe'](
        case, fabric, tplan, pplan, mplan, lplan, bv, ())
    if (result['derived_actor_ack']['requests'] !=
            len(result['derived_actor']['judgments']) or
            len(result['derived_actor_ack']['transport_grants']) !=
            len(result['derived_actor_ack']['transport_deliveries']) or
            len(received) != len(result['derived_actor']['judgments'])):
        raise CausalProbeRejected('endogenous actor execution not causally closed')
    result['schema'] = SCHEMA
    result['status'] = STATUS
    result['native_v0e_modified'] = False
    result['derived_actor']['feedback_enabled'] = feedback
    result['derived_actor']['max_abs_actor_credit'] = max_abs_actor_credit
    result['native_actor_credit_applied'] = False
    result['native_learning_implemented'] = False
    return result
