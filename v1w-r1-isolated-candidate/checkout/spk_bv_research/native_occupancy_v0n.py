"""SPK BV v0n: bounded, read-only observation of *records* of grant and delivery.

Never interprets native wait as transit duration, energy, CPU work, or causality.
Report-only mode derives exact end-of-tick net occupancy from v0m's aggregated
observations; source-verified mode recomputes v0m against the original v0k fixture.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from .native_capture_v0k import _json_bytes, _no_duplicate_keys, _reject_constant

SCHEMA = 'spk-bv-native-grant-delivery-occupancy/v0n'
STATUS_REPORT = 'BOUND_V0M_REPORT_OBSERVATIONAL_ONLY'
STATUS_NATIVE = 'RECOMPUTED_V0M_NATIVE_OBSERVATIONAL_ONLY'
PAIRING_SCHEMA = 'spk-bv-native-packet-grant-pairing/v0m'
PAIRING_STATUS = 'NATIVE_DELIVERY_GRANT_RECORD_BIJECTION_ONLY'
MAX_INPUT = 2_000_000
MAX_EVENTS = 100_000
MAX_TICK = 2**63-1
SHA = re.compile(r'[0-9a-f]{64}\Z')
CLAIMS_EXCLUDED = [
    'hardware-traffic-or-energy', 'waiting-time-semantics',
    'scheduler-causal-attribution', 'forward-progress-causality',
    'BV-v0h-528-stress-equivalence', 'independent-causal-votes',
    'v0i-contextual-reception-mapping', 'cross-PE-cost-inference',
    'compression-or-learning-benefit', 'architecture-promotion',
]

class OccupancyError(ValueError):
    pass


def reject(s: str):
    raise OccupancyError(s)


def digest(x: object) -> str:
    return sha256(_json_bytes(x)).hexdigest()


def read_pairing(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_INPUT:
        reject('pairing report must be bounded, regular and non-symlink')
    try:
        doc = json.loads(path.read_bytes(), object_pairs_hook=_no_duplicate_keys,
                         parse_constant=_reject_constant)
    except (UnicodeError, ValueError) as e:
        raise OccupancyError(f'bad report JSON: {e}') from e
    return validate_report(doc)


def _uint(value: object, name: str) -> int:
    if type(value) is not int or not (0 <= value <= MAX_EVENTS):
        reject('invalid count: ' + name)
    return value


def _tick(value: object) -> int:
    if type(value) is not int or not (0 <= value <= MAX_TICK):
        reject('invalid tick')
    return value


def _sha(value: object, name: str):
    if type(value) is not str or not SHA.fullmatch(value):
        reject('invalid SHA256: ' + name)


def _series(rows, name):
    if type(rows) is not list or len(rows) > MAX_EVENTS:
        reject('invalid series: ' + name)
    seen = set()
    result = []
    for item in rows:
        if type(item) is not dict or set(item) != {'tick', 'count'}:
            reject('bad per-tick series entry')
        tick, count = _tick(item['tick']), _uint(item['count'], name)
        if count < 1 or tick in seen or (result and tick < result[-1][0]):
            reject('non-positive, repeated or unsorted per-tick rows')
        seen.add(tick)
        result.append((tick, count))
    return result


def validate_report(report: object) -> dict:
    if type(report) is not dict or report.get('schema') != PAIRING_SCHEMA or report.get('status') != PAIRING_STATUS:
        reject('wrong v0m report schema/status')
    if report.get('native_v0h_verified') is not False:
        reject('v0h claim flag invalid')
    if type(report.get('claims_excluded')) is not list or 'physical-packet-or-hardware-identity' not in report['claims_excluded']:
        reject('pairing claims scope invalid')
    for name in ('native_fixture_sha256', 'bound_dossier_sha256', 'joined_pair_multiset_sha256',
                 'source_delivery_rows_sha256', 'source_grant_rows_sha256'):
        _sha(report.get(name), name)
    pins = report.get('producer_pins')
    if type(pins) is not dict or pins.get('status') != 'PINNED_BYTES_ONLY':
        reject('source pins missing/incorrect status')
    _sha(pins.get('probe_sha256'),'probe_sha256')
    if type(pins.get('source_sha256')) is not dict or len(pins['source_sha256']) != 3:
        reject('incomplete producer source hashes')
    for name, value in pins['source_sha256'].items():
        if type(name) is not str: reject('invalid source key')
        _sha(value, name)
    if report.get('selected_test') != 'test_context_aggregation_refuses_unverified_trace':
        reject('not the pinned native fixture test')
    d = _uint(report.get('delivery_rows'), 'delivery_rows')
    g = _uint(report.get('grant_rows'), 'grant_rows')
    n = _uint(report.get('paired_unique_packet_ids'), 'paired_unique_packet_ids')
    local = _uint(report.get('local_pe_grants'), 'local_pe_grants')
    cross = _uint(report.get('cross_pe_grants'), 'cross_pe_grants')
    ind = _uint(report.get('native_independent_receiver_true_flags'), 'independent_flags')
    a = _uint(report.get('assessment_rows'), 'assessment_rows')
    b = _uint(report.get('forward_batch_rows'), 'forward_batch_rows')
    w = report.get('sum_native_reported_wait')
    if type(w) is not int or not (0 <= w <= MAX_TICK):
        reject('invalid reported wait total')
    if not (n == d == g and n > 0 and n == cross + local and ind <= n and a > 0 and b > 0):
        reject('pairing cardinalities inconsistent')
    grants = _series(report.get('grants_by_tick'), 'grants_by_tick')
    deliveries = _series(report.get('deliveries_by_tick'), 'deliveries_by_tick')
    if sum(c for _, c in grants) != g or sum(c for _, c in deliveries) != d:
        reject('tick-series totals inconsistent with report cardinalities')
    # All prefix grant counts must dominate observed delivery counts. The grant
    # tick is a native record timestamp, not a modeled scheduling arrival time.
    events = sorted(set(t for t, _ in grants) | set(t for t, _ in deliveries))
    gr = dict(grants); de = dict(deliveries)
    balance = 0
    for t in events:
        balance += gr.get(t, 0) - de.get(t, 0)
        if balance < 0:
            reject('delivery precedes grant in cumulative native record counts')
    if balance:
        reject('grants not balanced by deliveries')
    return report


def _observe(report: dict, *, verified_native: bool = False) -> dict:
    validate_report(report)
    grants = dict(_series(report['grants_by_tick'], 'grants_by_tick'))
    deliveries = dict(_series(report['deliveries_by_tick'], 'deliveries_by_tick'))
    ticks = sorted(set(grants) | set(deliveries))
    entries = []
    eot = 0
    peak = 0
    co_occurrence = 0
    positive_ticks = 0
    weighted_area = 0
    prev_tick = None
    max_span = 0
    for tick in ticks:
        # Discrete integral of end-of-tick undelivered grant count, over the
        # elapsed tick interval BEFORE events at this tick. Not queueing cost.
        if prev_tick is not None:
            elapsed = tick - prev_tick
            weighted_area += eot * elapsed
            max_span = max(max_span, elapsed)
        issued, received = grants.get(tick, 0), deliveries.get(tick, 0)
        previous = eot
        eot += issued - received
        if eot < 0:
            reject('negative native end-of-tick grant-delivery balance')
        peak = max(peak, eot)
        co_occurrence += int(issued > 0 and received > 0)
        positive_ticks += int(eot > 0)
        entries.append({'tick': tick, 'grants': issued, 'deliveries': received,
                        'end_of_tick_undelivered_grants': eot,
                        'within_tick_peak_upper_bound': previous + issued})
        prev_tick = tick
    if eot != 0:
        reject('unclosed observed ledger')
    n = report['paired_unique_packet_ids']
    if weighted_area > MAX_TICK * MAX_EVENTS:
        reject('area budget exceeded')
    return {
        'schema': SCHEMA,
        'status': STATUS_NATIVE if verified_native else STATUS_REPORT,
        'native_fixture_sha256': report['native_fixture_sha256'],
        'joined_pair_multiset_sha256': report['joined_pair_multiset_sha256'],
        'source_pairing_report_sha256': digest(report),
        'source_verified_by_recomputation': bool(verified_native),
        'delivery_grant_pairs': n,
        'local_pe_grants': report['local_pe_grants'],
        'cross_pe_grants': report['cross_pe_grants'],
        'native_independent_receiver_true_flags': report['native_independent_receiver_true_flags'],
        'native_reported_wait_sum': report['sum_native_reported_wait'],
        'native_reported_wait_mean_fraction': [report['sum_native_reported_wait'], n],
        'tick_min': ticks[0], 'tick_max': ticks[-1],
        'tick_event_rows': entries,
        'end_of_tick_undelivered_grants_peak': peak,
        'within_tick_grant_first_peak_upper_bound': max(r['within_tick_peak_upper_bound'] for r in entries),
        'grant_and_delivery_coactive_tick_count': co_occurrence,
        'end_of_tick_positive_tick_count': positive_ticks,
        'bounded_grant_delivery_tick_area': weighted_area,
        'max_adjacent_observed_tick_span': max_span,
        'final_unmatched_grants': eot,
        'observation_limitations': [
            'grant is a simulator record, not a physical transport packet',
            'reported wait is not grant-to-delivery delay',
            'only end-of-tick count is exact from aggregates; within-tick sequence unknown',
            'area counts elapsed-tick outstanding grants, not scheduler queue work or energy',
            'native independent_receiver flags are not proven distinct causal votes',
        ],
        'claims_excluded': CLAIMS_EXCLUDED,
    }


def verify_against_native(report: dict, capture: Path, dossier: Path) -> None:
    """Recompute full v0m pairing from the authenticated v0k capture & v0l dossier."""
    from .native_dossier_v0l import load_capture
    from .native_packet_pairing_v0m import read_dossier, native_pairing
    doc = load_capture(capture)
    bound = read_dossier(dossier)
    fresh = native_pairing(doc, bound)
    if fresh != report:
        reject('native v0m pairing recomputation differs from supplied report')


def observe(report: dict) -> dict:
    """Report-only observation; cannot claim verified native origin."""
    return _observe(report, verified_native=False)


def observe_native(report: dict, capture: Path, dossier: Path) -> dict:
    """Verified mode only after complete source-record recomputation."""
    verify_against_native(report, capture, dossier)
    return _observe(report, verified_native=True)
