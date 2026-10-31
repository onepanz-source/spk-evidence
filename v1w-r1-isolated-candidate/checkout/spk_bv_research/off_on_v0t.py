"""SPK BV v0t: source-bound three-arm native feedback intervention (research only).

OFF vs ON forward-first changes only enabled; ON forward-first vs ON
feedback-first changes only priority. Shared fixture is hashed before and after
EVERY run. None of this is hardware, learning, or global causal credit.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import fields, is_dataclass
from hashlib import sha256
import json
from pathlib import Path

from spk_bv_research.native_capture_v0k import _sha, canonical_fixture

SCHEMA = 'spk-bv-native-three-arm-feedback/v0t'
STATUS = 'SOURCE_BOUND_THREE_ARM_MODEL_INTERVENTION_ONLY'
PINNED = {
    'spk_backvalidation_v0/live_dual_scheduler_v0e.py': '2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9',
    'search/spk_bv_v0e_live_evidence.py': '1e93f1a71c1099a3ce3c5e14d2cb9cfa47b8bfa9027832785d9f09af0c2bbc70',
    'tests/test_spk_bv_live_dual_scheduler_v0e.py': '6de34cd1ff6c85c96faad3dc047066406cf49d9675ac87fc77b260814f18dfa8',
}
EXCLUSIONS = [
    'no-learning-or-global-causal-credit', 'no-hardware-latency-energy',
    'bounded-three-node-v0e-not-N-node', 'no-v0h-528-stress-equivalence',
    'identical-fixture-not-identical-effective-dynamic-workload',
    'no-proof-of-BV-informational-benefit', 'no-architecture-promotion',
]

class InterventionError(ValueError):
    pass


def require(cond: bool, explanation: str):
    if not cond:
        raise InterventionError(explanation)


def source_pins(root: Path) -> dict:
    root = root.resolve(strict=True)
    actual = {}
    for relative, expected in PINNED.items():
        source = root / relative
        require(source.is_file() and not source.is_symlink() and source.resolve() == source,
                f'absent or unsafe source: {relative}')
        require(source.stat().st_size <= 600_000, f'oversized source: {relative}')
        digest = sha256(source.read_bytes()).hexdigest()
        require(digest == expected, f'source SHA256 drift: {relative}')
        actual[relative] = digest
    return actual


def runtime_modules_bound(root: Path, executor, fixture_function, plan_type):
    """Supplement static SHA-256 pins with actual imported implementation locations."""
    import sys
    expected = {
        executor.__module__: 'spk_backvalidation_v0/live_dual_scheduler_v0e.py',
        fixture_function.__module__: 'search/spk_bv_v0e_live_evidence.py',
        plan_type.__module__: 'spk_backvalidation_v0/live_dual_scheduler_v0e.py',
    }
    for module_name, rel in expected.items():
        mod = sys.modules.get(module_name)
        require(mod is not None and getattr(mod, '__file__', None) is not None,
                f'runtime module has no on-disk source: {module_name}')
        p = Path(mod.__file__)
        require(p.is_file() and not p.is_symlink() and p.resolve() == root / rel,
                f'runtime module not loaded from pinned path: {module_name}')
    require(executor.__name__ == 'execute_live_v0e', 'unexpected scheduler entrypoint')
    require(fixture_function.__name__ == 'fixture', 'unexpected fixture entrypoint')
    require(plan_type.__name__ == 'LiveBVPlanV0e', 'unexpected plan type')


def snapshot(value) -> str:
    return _sha(canonical_fixture(value))


def integer(v, name):
    require(type(v) is int and v >= 0, 'expected nonnegative int: ' + name)
    return v


def rows(section, name):
    result = section.get(name)
    require(type(result) is list and len(result) <= 200_000, f'bad list: {name}')
    return result


def hist_payload(records: list, omit: tuple[str, ...]):
    """Compare multiset of payloads; do not invent identity for duplicates."""
    canon = []
    for row in records:
        require(type(row) is dict, 'bad output row')
        payload = {k:v for k,v in row.items() if k not in omit}
        canon.append(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                ensure_ascii=True, allow_nan=False))
    return dict(sorted(Counter(canon).items()))


def nonempty_forward(forward):
    require(type(forward) is dict, 'bad forward section')
    for key in ('batches', 'emissions', 'terminal', 'link_grants', 'occurrences'):
        rows(forward, key)
    require(type(forward.get('states')) is dict, 'bad neuron states')
    integer(forward.get('processed_events'), 'processed_events')
    integer(forward.get('processed_batches'), 'processed_batches')


def summarize(result, *, enabled: bool, priority: str):
    require(type(result) is dict and result.get('schema') == 'spk-bv-live-dual-event-scheduler/v0e',
            'unexpected live scheduler result schema')
    require(type(result.get('enabled')) is bool and result['enabled'] is enabled and
            result.get('policy') == priority, 'scheduler did not honor control plan')
    fw = result.get('forward'); bv = result.get('feedback'); res = result.get('resources')
    nonempty_forward(fw)
    require(type(bv) is dict and type(res) is dict, 'missing feedback/resources')
    for key in ('assessments','deliveries','link_grants'):
        rows(bv, key)
    tim = rows(res, 'timeline')
    require(all(type(x) is dict and type(x.get('tick')) is int for x in tim), 'bad timeline')
    require(len({x['tick'] for x in tim}) == len(tim), 'duplicated timeline tick')
    require([x['tick'] for x in tim] == sorted(x['tick'] for x in tim), 'unsorted timeline')
    contention = res.get('contention')
    require(type(contention) is dict, 'bad contention')
    for k,v in contention.items(): integer(v, 'contention.'+str(k))
    counts = {
        'processed_batches': integer(fw['processed_batches'], 'processed_batches'),
        'processed_events': integer(fw['processed_events'], 'processed_events'),
        'forward_batches': len(fw['batches']),
        'forward_emissions': len(fw['emissions']),
        'forward_terminal': len(fw['terminal']),
        'forward_occurrences': len(fw['occurrences']),
        'forward_link_grants': len(fw['link_grants']),
        'feedback_assessments': len(bv['assessments']),
        'feedback_deliveries': len(bv['deliveries']),
        'feedback_link_grants': len(bv['link_grants']),
        'feedback_unique_receiver_votes': integer(bv.get('unique_receiver_votes'), 'unique_receiver_votes'),
        'bv_link_grants': integer(res.get('bv_link_grants'), 'bv_link_grants'),
        'bv_service_units': integer(res.get('bv_service_units'), 'bv_service_units'),
        'bv_memory_units': integer(res.get('bv_memory_units'), 'bv_memory_units'),
        'forward_reserved_memory_units': integer(res.get('forward_reserved_memory_units'), 'forward_reserved_memory_units'),
        'peak_cross_inflight': integer(res.get('peak_cross_inflight'), 'peak_cross_inflight'),
        'fabric_link_contention': integer(contention.get('fabric_link', 0), 'fabric_link'),
        'forward_grant_wait_sum': sum(integer(g.get('wait'), 'forward wait') for g in fw['link_grants']),
        'feedback_grant_wait_sum': sum(integer(g.get('wait'), 'feedback wait') for g in bv['link_grants']),
        'timeline_sample_count': len(tim),
        'timeline_service_unit_sum': sum(integer(x.get('pe_service_total'), 'pe_service_total') for x in tim),
        'timeline_memory_unit_sum': sum(integer(x.get('memory_total'), 'memory_total') for x in tim),
        'timeline_link_unit_sum': sum(integer(x.get('link_total'), 'link_total') for x in tim),
    }
    require(counts['forward_batches'] == counts['processed_batches'], 'forward batch accounting mismatch')
    require(counts['bv_link_grants'] == counts['feedback_link_grants'] == counts['bv_service_units'],
            'feedback grant/service accounting mismatch')
    require(counts['bv_memory_units'] == 2 * counts['feedback_link_grants'], 'feedback memory accounting mismatch')
    require(counts['forward_link_grants'] == len(fw['link_grants']), 'forward link accounting mismatch')
    if not enabled:
        require(all(counts[x] == 0 for x in ('feedback_assessments','feedback_deliveries',
            'feedback_link_grants','feedback_unique_receiver_votes','bv_link_grants',
            'bv_service_units','bv_memory_units','feedback_grant_wait_sum')),
            'OFF control produced feedback')
        require(all(integer(x.get('feedback_sends'), 'feedback_sends') == 0 for x in tim),
                'OFF control contains feedback sends')
    require(counts['processed_batches'] > 0, 'fixture produced no forward work')
    for key in ('emissions','terminal'):
        for event in fw[key]:
            require(type(event) is dict and type(event.get('timestamp')) is int,
                    'missing forward event timestamp')
    return {
        'enabled': enabled,'priority':priority,'metrics':counts,
        'last_forward_terminal_tick': max((x['timestamp'] for x in fw['terminal']),default=None),
        'last_forward_emission_tick': max((x['timestamp'] for x in fw['emissions']),default=None),
        'forward_states_sha256': _sha(canonical_fixture(fw['states'])),
        'forward_emission_payload_multiset_sha256':_sha(hist_payload(fw['emissions'],('timestamp',))),
        'forward_terminal_payload_multiset_sha256':_sha(hist_payload(fw['terminal'],('timestamp',))),
        'whole_result_sha256':snapshot(result),
    }


def _deltas(a, b):
    keys = sorted(set(a['metrics']) & set(b['metrics']))
    delta={k:b['metrics'][k]-a['metrics'][k] for k in keys}
    tm_a = a['last_forward_terminal_tick'];tm_b=b['last_forward_terminal_tick']
    end_delta = None if tm_a is None or tm_b is None else tm_b-tm_a
    return {'metric_deltas':delta,'last_terminal_tick_delta':end_delta,
            'state_hash_equal':a['forward_states_sha256']==b['forward_states_sha256'],
            'emission_payload_multiset_equal':a['forward_emission_payload_multiset_sha256']==b['forward_emission_payload_multiset_sha256'],
            'terminal_payload_multiset_equal':a['forward_terminal_payload_multiset_sha256']==b['forward_terminal_payload_multiset_sha256']}


def execute_three(fixture_function, executor, plan_type, *, root:Path, pin_sources=True):
    root=root.resolve(strict=True)
    before_pins=source_pins(root) if pin_sources else None
    if pin_sources:runtime_modules_bound(root, executor, fixture_function, plan_type)
    require(is_dataclass(plan_type) and {f.name for f in fields(plan_type)} >= {'enabled','priority'},
            'unexpected BV plan dataclass')
    # Native fixture is generated ONCE, never per policy.
    native=fixture_function()
    require(type(native) is tuple and len(native)==3 and type(native[2]) is tuple and len(native[2])==4,
            'unexpected fixture() contract')
    case,fabric,plans=native
    input_hash=snapshot(native)
    controls=(('off',False,'forward-first'),
              ('on_forward_first',True,'forward-first'),
              ('on_feedback_first',True,'feedback-first'))
    reports={}
    for name,on,policy in controls:
        plan=plan_type(enabled=on, priority=policy)
        require(type(plan.enabled) is bool and plan.enabled is on and plan.priority==policy,
                'BV plan did not preserve explicit toggles')
        require(snapshot(native)==input_hash, 'input/plan mutated before '+name)
        observation=executor(case,fabric,*plans,plan)
        require(snapshot(native)==input_hash, 'input/plan mutated by '+name)
        reports[name]=summarize(observation,enabled=on,priority=policy)
    require(reports['on_forward_first']['metrics']['feedback_link_grants']>0 and
            reports['on_feedback_first']['metrics']['feedback_link_grants']>0,
            'ON intervention produced no feedback; comparison uninformative')
    if pin_sources:
        require(source_pins(root)==before_pins,'native source drift after interventions')
        runtime_modules_bound(root, executor, fixture_function, plan_type)
    return {'schema':SCHEMA,'status':STATUS,'shared_fixture_input_sha256':input_hash,
            'input_rechecked_before_after_every_arm':True,
            'producer_source_sha256':before_pins,
            'controls':{'off':{'enabled':False,'priority':'forward-first'},
                        'on_forward_first':{'enabled':True,'priority':'forward-first'},
                        'on_feedback_first':{'enabled':True,'priority':'feedback-first'}},
            'runs':reports,
            'interventions':{
                'toggle_enabled_only':_deltas(reports['off'],reports['on_forward_first']),
                'change_priority_only':_deltas(reports['on_forward_first'],reports['on_feedback_first']),
                'off_to_feedback_first_combined':_deltas(reports['off'],reports['on_feedback_first'])},
            'claims_excluded':EXCLUSIONS}


EXPECTED_V0O_FIXTURE_SHA256 = '887ad94cc89d91083950d9a99fff10007edc160df370c6bdef5b1d9048167fb4'

def compare_reference_v0o(report: dict, encoded: object) -> dict:
    """Pin 3-arm input and both ON outputs to the v0o typed native tuple.

    v0o's independently captured runs are ON/ON; no OFF run is inferred from it.
    """
    require(type(report) is dict and report.get('schema')==SCHEMA, 'bad three-arm report')
    require(type(encoded) is dict and encoded.get('$t') == 'tuple' and
            type(encoded.get('items')) is list and len(encoded['items']) == 5,
            'unexpected v0o native fixture tuple')
    things = encoded['items']
    shared = {'$t':'tuple', 'items':things[:3]}
    require(_sha(shared)==report['shared_fixture_input_sha256'],
            'v0o reference input != v0t shared input')
    for idx,key in ((3,'on_forward_first'),(4,'on_feedback_first')):
        require(_sha(things[idx])==report['runs'][key]['whole_result_sha256'],
                f'v0o reference run differs from three-arm {key}')
    return {'reference_shared_input_equal':True,'reference_on_forward_first_equal':True,
            'reference_on_feedback_first_equal':True,
            'status':'PINNED_V0O_ON_RUNS_REPLAYED_IN_THREE_ARM'}


def verify_reference_v0o(report: dict, reference_path: Path) -> dict:
    from spk_bv_research.paired_runs_v0o import load_capture
    reference = load_capture(reference_path)
    require(reference['native_fixture_sha256']==EXPECTED_V0O_FIXTURE_SHA256,
            'v0o reference hash not the observed pinned fixture')
    source_hashes=reference['producer_pins']['source_sha256']
    require(all(source_hashes.get(k)==v for k,v in PINNED.items()),
            'v0o source pins do not agree with v0t')
    return compare_reference_v0o(report,reference['native_fixture'])
