"""SPK BV v0m: read-only, source-bound delivery/link-grant pairing.

This proves a *record* bijection in one captured v0k fixture, not physical
packet identity, v0h large-stress equivalence, compression or causal credit.
Never invents batch/context/link/path/epoch IDs or transport units.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from .native_capture_v0k import _json_bytes, _no_duplicate_keys, _reject_constant
from .native_dossier_v0l import (
    DOSSIER_SCHEMA, GROUPS, DossierError, _field_get, _digest,
    load_capture, native_dossier, typed_path,
)

SCHEMA = 'spk-bv-native-packet-grant-pairing/v0m'
STATUS = 'NATIVE_DELIVERY_GRANT_RECORD_BIJECTION_ONLY'
MAX_DOSSIER_BYTES = 2_000_000
MAX_JOIN_ROWS = 100_000
MAX_TICK = 2**63 - 1


class PairingError(ValueError):
    pass


def _fail(message):
    raise PairingError(message)


def read_dossier(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_DOSSIER_BYTES:
        _fail('dossier must be bounded regular non-symlink file')
    try:
        d = json.loads(path.read_bytes(), object_pairs_hook=_no_duplicate_keys,
                       parse_constant=_reject_constant)
    except (ValueError, UnicodeError) as exc:
        raise PairingError(f'invalid dossier JSON: {exc}') from exc
    if (type(d) is not dict or d.get('schema') != DOSSIER_SCHEMA or
        d.get('status') != 'NATIVE_TYPED_GROUPS_INSPECTED_NOT_PACKET_MAPPING' or
        d.get('native_v0h_verified') is not False or
        type(d.get('groups')) is not dict or set(d['groups']) != set(GROUPS)):
        _fail('dossier schema, observation status or groups mismatch')
    return d


def _validate_bound_dossier(doc: dict, dossier: dict) -> None:
    if (doc['native_fixture_sha256'] != dossier.get('native_fixture_sha256') or
        doc['selected_test'] != dossier.get('selected_test') or
        doc['producer_pins'] != dossier.get('producer_pins')):
        _fail('source pins, selected test or native fixture SHA mismatch')
    fresh = native_dossier(doc, sample_values=3,
                           expected_sha=dossier['native_fixture_sha256'])
    for key, val in fresh.items():
        if key == 'groups':
            continue
        if dossier.get(key) != val:
            _fail(f'dossier envelope mismatch: {key}')
    for group_name in GROUPS:
        supplied = dossier['groups'][group_name]
        new_group = fresh['groups'][group_name]
        if type(supplied) is not dict or type(supplied.get('scalar_samples')) is not list:
            _fail(f'bad dossier samples for {group_name}')
        if len(supplied['scalar_samples']) > 3:
            _fail('dossier contains too many samples')
        for field, expected_value in new_group.items():
            if field == 'scalar_samples':
                if supplied[field] != expected_value[:len(supplied[field])]:
                    _fail('dossier sample contents mismatch')
            elif supplied.get(field) != expected_value:
                _fail(f'dossier group fingerprint mismatch: {group_name}/{field}')
        if set(supplied) != set(new_group):
            _fail('unexpected dossier group fields')


def _rows(doc: dict, group_name: str) -> list:
    result = typed_path(doc['native_fixture'], GROUPS[group_name])
    if type(result) is not dict or result.get('$t') not in ('list', 'tuple'):
        _fail('expected native typed sequence: ' + group_name)
    rows = result['items']
    if not isinstance(rows, list) or len(rows) > MAX_JOIN_ROWS:
        _fail('native row count exceeds bound')
    return rows


def _str(row: object, key: str) -> str:
    x = _field_get(row, key)
    if type(x) is not str or not x or len(x) > 256:
        _fail(f'{key}: required nonempty native string')
    return x


def _int(row: object, key: str) -> int:
    x = _field_get(row, key)
    if type(x) is not int or x < 0 or x > MAX_TICK:
        _fail(f'{key}: invalid nonnegative native integer')
    return x


def _bool(row: object, key: str) -> bool:
    x = _field_get(row, key)
    if type(x) is not bool:
        _fail(f'{key}: required native bool')
    return x


def _common(row: object) -> tuple[str, str, str, str]:
    return tuple(_str(row, k) for k in ('packet_id', 'assessment_id', 'sender', 'receiver'))


def _unique_index(rows: list, label: str) -> dict:
    index = {}
    for row in rows:
        key = _str(row, 'packet_id')
        if key in index:
            _fail(f'{label}: duplicate packet_id; no silent multiplicity collapse')
        index[key] = row
    return index


def native_pairing(doc: dict, dossier: dict) -> dict:
    """Verify exact captured-record pairing, without projecting onto the v0i ledger."""
    _validate_bound_dossier(doc, dossier)
    deliveries = _rows(doc, 'feedback_deliveries')
    grants = _rows(doc, 'feedback_link_grants')
    assessments = _rows(doc, 'feedback_assessments')
    batches = _rows(doc, 'forward_batches')
    if not deliveries or len(deliveries) != len(grants):
        _fail('nonempty delivery/grant cardinality mismatch')
    di = _unique_index(deliveries, 'delivery')
    gi = _unique_index(grants, 'grant')
    if set(di) != set(gi):
        _fail('delivery/grant packet_id sets differ')
    assessment_by_id = {}
    for row in assessments:
        ident = _str(row, 'id')
        if ident in assessment_by_id:
            _fail('duplicate assessment id')
        assessment_by_id[ident] = row
    batch_ids = set()
    for batch in batches:
        bid = _str(batch, 'batch_id')
        if bid in batch_ids:
            _fail('ambiguous forward batch id')
        batch_ids.add(bid)
    for row in assessments:
        if _str(row, 'batch_id') not in batch_ids:
            _fail('assessment references absent forward batch')
        _int(row, 'tick')
    joined = []
    cross_pe = 0
    independent_receiver_flags = 0
    grants_by_dispatch_tick = Counter()
    deliveries_by_tick = Counter()
    sum_reported_wait = 0
    for packet_id in sorted(di):
        d, g = di[packet_id], gi[packet_id]
        if _common(d) != _common(g):
            _fail('matched packet_id carries conflicting assessment/actor provenance')
        assessment_id = _str(d, 'assessment_id')
        if assessment_id not in assessment_by_id:
            _fail('packet references missing assessment')
        dtick = _int(d, 'tick')
        gtick = _int(g, 'tick')
        arrived = _int(g, 'delivered_at')
        wait = _int(g, 'wait')
        src_pe = _str(g, 'source_pe')
        dst_pe = _str(g, 'target_pe')
        is_cross = _bool(g, 'cross_pe')
        independent_receiver_flags += int(_bool(d, 'independent_receiver'))
        if is_cross != (src_pe != dst_pe):
            _fail('cross_pe contradicts source_pe/target_pe')
        if dtick != arrived:
            _fail('delivery tick does not match grant delivered_at')
        if gtick > arrived:
            _fail('grant tick later than delivery')
        # wait is a native reported value, not inferred service/queuing latency.
        if _int(assessment_by_id[assessment_id], 'tick') > dtick:
            _fail('packet delivered before its assessment')
        cross_pe += is_cross
        sum_reported_wait += wait
        grants_by_dispatch_tick[gtick] += 1
        deliveries_by_tick[dtick] += 1
        joined.append({
            'packet_id': packet_id, 'assessment_id': assessment_id,
            'sender': _str(d, 'sender'), 'receiver': _str(d, 'receiver'),
            'grant_tick': gtick, 'delivery_tick': dtick,
            'wait_reported': wait, 'source_pe': src_pe,
            'target_pe': dst_pe, 'cross_pe': is_cross,
            'independent_receiver': _bool(d, 'independent_receiver'),
            'delivery_row_sha256': _digest(d), 'grant_row_sha256': _digest(g),
        })
    return {
        'schema': SCHEMA, 'status': STATUS,
        'native_fixture_sha256': doc['native_fixture_sha256'],
        'bound_dossier_sha256': _digest(dossier),
        'producer_pins': doc['producer_pins'],
        'selected_test': doc['selected_test'],
        'delivery_rows': len(deliveries),
        'grant_rows': len(grants),
        'paired_unique_packet_ids': len(joined),
        'assessment_rows': len(assessments),
        'forward_batch_rows': len(batches),
        'cross_pe_grants': cross_pe,
        'local_pe_grants': len(joined) - cross_pe,
        'native_independent_receiver_true_flags': independent_receiver_flags,
        'sum_native_reported_wait': sum_reported_wait,
        'grants_by_tick': [{'tick': k, 'count': v} for k,v in sorted(grants_by_dispatch_tick.items())],
        'deliveries_by_tick': [{'tick': k, 'count': v} for k,v in sorted(deliveries_by_tick.items())],
        'joined_pair_multiset_sha256': _digest(joined),
        'source_delivery_rows_sha256': dossier['groups']['feedback_deliveries']['native_row_multiset_sha256'],
        'source_grant_rows_sha256': dossier['groups']['feedback_link_grants']['native_row_multiset_sha256'],
        'native_v0h_verified': False,
        'claims_excluded': [
            'physical-packet-or-hardware-identity', '528-packet-stress-equivalence',
            'independent-v0h-source-replay', 'v0i-reception-mapping', 'v0i-vote-deduplication',
            'per-packet-energy-or-latency-model', 'causal-credit', 'learning',
            'compression', 'runtime-scheduling-equivalence',
        ],
    }
