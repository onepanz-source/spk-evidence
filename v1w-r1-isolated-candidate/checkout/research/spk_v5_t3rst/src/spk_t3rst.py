#!/usr/bin/env python3
"""SPK V5 T3RST research-only causal boundary audit.

NOT a SPK native source verifier unless fed actual, independently extracted source traces.
No signature, sensor authentication, native BV or learning is established here.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = 'spk-v5-t3rst-single-pass-trace/research-v0'
REF_SCHEMA = 'spk-v5-t3opq-source-custody-and-shared-resource-dual-replay/research-v0'
REF_SHA_USER = '813753afd706eabff52653cf0a7674e1a44755981df61c6760fcbd4652c790d2'

class AuditError(ValueError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)

def stable_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()

def audit_reference(report: dict[str, Any]) -> dict[str, Any]:
    """Verify internal arithmetical consistency; does NOT prove source lineage."""
    require(report.get('schema') == REF_SCHEMA, 'wrong T3OPQ report schema')
    require(report.get('status') == 'SOURCE_BV_V0E_DUAL_VERDICT_LINEAGE_WITH_SHADOW_LEARNING', 'wrong T3OPQ status')
    table = report['C_verdict_table']
    counts = table['counts']
    require(table['cases'] == 180, 'unexpected case count')
    require(counts['REJECT_NO_UPDATE'] + counts['SHADOW_SOURCE_REPLAY_ELIGIBLE'] == table['cases'], 'table partition inconsistent')
    require(table['positive_verdicts'] == table['negative_verdicts'] == 36, 'verdict sign accounting differs')
    runs = report['online_replay_runs']
    require(len(runs) == 6, 'six runs expected')
    require({(r['seed'], r['stress']) for r in runs} == {(s, b) for s in (11, 29, 47) for b in (False, True)}, 'seed/stress matrix incomplete')
    total_decisions = total_admitted = total_updates = 0
    for r in runs:
        o, reg = r['observations'], r['registry']
        d, a = o['decisions'], o['source_admitted']
        require(d == 120, 'unexpected episodes/run')
        require(a == reg['updates'], 'source-admitted/updates mismatch')
        require(reg['updates'] + reg['source_rejected'] + reg['discards'] == d, 'conservation accounting fails')
        require(reg['pending'] == 0, 'nonzero pending ledger')
        require(len(r['episode_digest']) == 64 and len(reg['head']) == 64 and len(reg['weights_sha256']) == 64, 'digest shape invalid')
        total_decisions += d
        total_admitted += a
        total_updates += reg['updates']
    require(total_decisions == report['total_online_episodes'] == 720, 'total decisions differ')
    require(total_admitted == report['total_source_admitted'] == 617, 'total admitted differ')
    require(total_updates == report['total_credited_updates'] == 617, 'total updates differ')
    excluded = set(report.get('claims_excluded', []))
    require(any('not authenticated' in e for e in excluded), 'sensor nonauthentication disclaimer missing')
    require(any('not a signature' in e for e in excluded), 'hash/signature disclaimer missing')
    require(any('not single native BV semantic channel' in e for e in excluded), 'dual replay disclaimer missing')
    return {'outcome': 'REPORT_INTERNAL_CONSISTENCY_PASS', 'case_count': table['cases'],
            'eligible': counts['SHADOW_SOURCE_REPLAY_ELIGIBLE'],
            'rejected': counts['REJECT_NO_UPDATE'], 'episodes': total_decisions,
            'shadow_updates': total_updates, 'source_sha_verified': False,
            'reference_report_sha256_claim_unverified': REF_SHA_USER}

def audit_trace(doc: dict[str, Any]) -> dict[str, Any]:
    """Structural causal-order/lineage validation, NEVER a semantic oracle.

    Events are observational claims, not physically authenticated source records.
    Credit is admitted only after source decision, emitted event, receiver
    ingress, C sensor and C verdict all exist in the same single-pass episode.
    """
    require(doc.get('schema') == SCHEMA, 'wrong trace schema')
    require(doc.get('mode') == 'single_pass', 'dual replay / retrospective mode forbidden')
    require(doc.get('environment') == 'research_shadow', 'must remain research shadow')
    require(doc.get('selection_after_replay') is False, 'posthoc host-selected observer forbidden')
    require(doc.get('authenticated_C_sensor') is False, 'sensor authentication is unsupported')
    require(doc.get('native_learning') is False, 'native learning is unsupported')
    require(doc.get('native_semantic_BV') is False, 'native semantic BV is unsupported')
    episodes = doc.get('episodes')
    require(isinstance(episodes, list) and bool(episodes), 'no episodes')
    ids: set[str] = set()
    global_event_ids: set[str] = set()
    global_decision_ids: set[str] = set()
    global_grant_ids: set[str] = set()
    credits = 0
    verdicts = Counter()
    for ep in episodes:
        eid = ep.get('episode_id')
        require(isinstance(eid, str) and eid and eid not in ids, 'episode id absent/duplicate')
        ids.add(eid)
        events = ep.get('events', [])
        require(isinstance(events, list) and bool(events), 'missing episode events')
        seen: dict[str, dict] = {}
        buckets: dict[str, list[dict]] = {}
        last_tick = -1
        for e in events:
            key, kind, tick = e.get('event_id'), e.get('kind'), e.get('tick')
            require(isinstance(key, str) and key and key not in seen and key not in global_event_ids, 'event id absent/duplicate')
            global_event_ids.add(key)
            require(type(tick) is int and tick >= last_tick, 'event ticks nonmonotonic')
            last_tick = tick
            require(e.get('episode_id') == eid, 'event episode mismatch')
            require(e.get('pass_id') == 'observed', 'counterfactual or second pass entered online trace')
            require(kind in {'source_decision', 'source_emission', 'receiver_ingress', 'c_sensor', 'c_verdict', 'credit_admission'}, 'unknown kind')
            parent = e.get('parent')
            if parent is not None:
                require(parent in seen, 'parent absent or from future')
                require(seen[parent]['tick'] <= tick, 'parent lies in future')
            seen[key] = e
            buckets.setdefault(kind, []).append(e)
        def single(kind):
            require(len(buckets.get(kind, [])) == 1, f'{kind} cardinality not one')
            return buckets[kind][0]
        decision = single('source_decision')
        require(decision.get('author') == 'A', 'decision not source-authored')
        require(decision.get('action') in ('emit', 'silent'), 'bad decision action')
        did = decision.get('decision_id')
        require(isinstance(did, str) and bool(did) and did not in global_decision_ids, 'decision id missing/replayed')
        global_decision_ids.add(did)
        sensor = single('c_sensor')
        require(sensor.get('author') == 'host_adapter', 'C sensor is host-derived in this research gate')
        require(sensor.get('authenticated') is False, 'sensor must be marked unauthenticated')
        require(type(sensor.get('sensor_value')) is bool, 'host sensor bit absent/invalid')
        require(sensor['tick'] > decision['tick'], 'sensor available before source decision: future leakage risk')
        emits = buckets.get('source_emission', [])
        receives = buckets.get('receiver_ingress', [])
        c_verdicts = buckets.get('c_verdict', [])
        admissions = buckets.get('credit_admission', [])
        require(len(emits) <= 1 and len(receives) <= 1 and len(c_verdicts) <= 1 and len(admissions) <= 1, 'duplicate causal records')
        if decision['action'] == 'silent':
            require(not emits and not receives and not c_verdicts and not admissions, 'unwitnessed silence received credit')
        else:
            em = single('source_emission')
            require(em.get('author') == 'A' and em.get('parent') == decision['event_id'], 'emission lineage broken')
            if not receives:
                # Source emission is not proof that C saw anything. Lost/unknown
                # delivery cannot be silently reclassified as a negative verdict.
                require(ep.get('receiver_coverage') == 'unknown', 'missing ingress lacks explicit unknown coverage')
                require(not c_verdicts and not admissions, 'credit from missing receiver ingress')
            else:
                recv = single('receiver_ingress')
                require(recv.get('author') == 'C' and recv.get('parent') == em['event_id'], 'receiver ingress lineage broken')
                if not c_verdicts:
                    require(ep.get('receiver_coverage') == 'verdict_unknown', 'unobserved C verdict not labeled unknown')
                    require(not admissions, 'credit with no C verdict')
                else:
                    v = single('c_verdict')
                    require(v.get('author') == 'C' and v.get('parent') == recv['event_id'], 'C authored verdict lineage broken')
                    require(v.get('sensor_event_id') == sensor['event_id'], 'verdict missing sensor lineage')
                    require(v['tick'] >= sensor['tick'] and v['tick'] >= recv['tick'], 'verdict depends on future evidence')
                    require(v.get('policy_id') == 'C_SENSOR_BOOL_SIGN_V0', 'no known C policy semantics')
                    require(v.get('verdict') == ('positive' if sensor['sensor_value'] else 'negative'), 'C declared sign mismatches policy and sensor')
                    verdicts[v['verdict']] += 1
                    if admissions:
                        a = admissions[0]
                        require(a.get('author') == 'shadow_registry' and a.get('parent') == v['event_id'], 'credit must depend on C verdict')
                        require(a['tick'] > v['tick'], 'credit committed before judgment')
                        require(a.get('verdict') == v['verdict'], 'host/registry verdict sign differs from C')
                        credits += 1
        for kind in ('source_emission', 'receiver_ingress', 'c_verdict', 'credit_admission'):
            for event in buckets.get(kind, []):
                require(event.get('decision_id') == did, 'decision identity mismatch')
        resources = ep.get('resources')
        require(isinstance(resources, dict), 'resource envelope absent')
        capacity = resources.get('per_tick_capacity')
        require(type(capacity) is int and capacity > 0, 'invalid capacity')
        used: dict[int,int] = {}
        grant_ids: set[str] = set()
        for grant in resources.get('grants', []):
            gt, units, gid = grant.get('tick'), grant.get('units'), grant.get('grant_id')
            require(type(gt) is int and type(units) is int and units > 0, 'bad resource grant')
            require(isinstance(gid, str) and gid and gid not in grant_ids and gid not in global_grant_ids, 'duplicate/absent grant id')
            grant_ids.add(gid)
            global_grant_ids.add(gid)
            require(any(ev['tick'] == gt for ev in events), 'grant unlinked to source event clock')
            used[gt] = used.get(gt, 0) + units
            require(used[gt] <= capacity, 'resource overadmission')
    return {'outcome':'SHADOW_CAUSAL_ORDER_PASS', 'episodes':len(episodes),
            'source_structural_credit_events': credits, 'verdict_counts':dict(verdicts),
            'authenticated_C_sensor': False, 'native_semantic_BV': False,
            'native_learning': False, 'goal_identifiability': 'NOT_ESTABLISHED',
            'source_origin_authenticated': False}

def audit_pair(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Compare identical source-visible past with perturbed future.

    Asserts invariance of source decision only. C verdict is allowed to react to
    later legitimate evidence; this is NOT a semantic correctness oracle.
    """
    audit_trace(a); audit_trace(b)
    require(len(a['episodes']) == len(b['episodes']), 'paired population mismatch')
    distinct_future = 0
    for left, right in zip(a['episodes'], b['episodes']):
        le, re = left['events'], right['events']
        ld = next(x for x in le if x['kind'] == 'source_decision')
        rd = next(x for x in re if x['kind'] == 'source_decision')
        require(left['episode_id'] == right['episode_id'], 'paired episode identity mismatch')
        require(ld == rd, 'same-past source decision changed: possible lookahead')
        leftprefix = [x for x in le if x['tick'] <= ld['tick']]
        rightprefix = [x for x in re if x['tick'] <= rd['tick']]
        require(leftprefix == rightprefix, 'source-visible causal prefix differs')
        ls = [x for x in le if x['tick'] > ld['tick']]
        rs = [x for x in re if x['tick'] > rd['tick']]
        distinct_future += int(stable_hash(ls) != stable_hash(rs))
    require(distinct_future > 0, 'pair lacks future perturbation')
    return {'outcome':'SHADOW_CAUSAL_CUT_PASS', 'pairs':len(a['episodes']),
            'different_future_episodes':distinct_future, 'native_verification': False}

def make_witness(verdict: str='positive', *, silent: bool=False) -> dict[str, Any]:
    eid, did = 'ep-001', 'decision-001'
    def evt(i, kind, tick, author, **kw):
        return dict(event_id=f'e{i}', kind=kind, tick=tick, author=author, episode_id=eid, pass_id='observed', **kw)
    events = [evt(1, 'source_decision', 0, 'A', action='silent' if silent else 'emit', decision_id=did)]
    if not silent:
        events += [evt(2,'source_emission',1,'A',decision_id=did,parent='e1'),
                   evt(3,'receiver_ingress',2,'C',decision_id=did,parent='e2')]
    events += [evt(4, 'c_sensor',3,'host_adapter',authenticated=False, sensor_value=(verdict == 'positive'))]
    if not silent:
        events += [evt(5,'c_verdict',4,'C',decision_id=did,parent='e3',sensor_event_id='e4',verdict=verdict,policy_id='C_SENSOR_BOOL_SIGN_V0'),
                   evt(6,'credit_admission',5,'shadow_registry',decision_id=did,parent='e5',verdict=verdict)]
    grants = [] if silent else [{'grant_id': 'g1','tick':1,'units':1}, {'grant_id':'g2','tick':4,'units':1}]
    return {'schema':SCHEMA,'mode':'single_pass','environment':'research_shadow',
            'selection_after_replay':False,'authenticated_C_sensor':False,
            'native_learning':False,'native_semantic_BV':False,
            'episodes':[{'episode_id':eid,'events':events,'resources':{'per_tick_capacity':1,'grants':grants}}]}

def evaluate(reference: dict | None=None, trace: dict | None=None,
             alternate_trace: dict | None=None) -> dict[str,Any]:
    gates = {}
    if reference is not None: gates['R_reference_consistency'] = audit_reference(reference)
    if trace is not None: gates['S_single_pass'] = audit_trace(trace)
    if alternate_trace is not None:
        require(trace is not None, 'paired trace requires primary trace')
        gates['T_causal_cut'] = audit_pair(trace, alternate_trace)
    require(bool(gates), 'no audited inputs')
    return {'schema':'spk-v5-t3rst-audit/research-v0', 'gates':gates,
            'overall':'RESEARCH_ONLY_SOURCE_BOUND_UNVERIFIED',
            'no_native_learning': True, 'no_native_semantic_BV': True,
            'no_authenticated_C_sensor': True,
            'no_blind_evaluation': True,
            'promotion_allowed': False,
            'blockers': ['actual T3OPQ source archive not executable in this environment',
                         'trace provenance not independently authenticated',
                         'single-pass C verdict not observed in frozen native scheduler',
                         'no independent goal authority or blind evidence']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference-report', type=Path)
    p.add_argument('--trace', type=Path)
    p.add_argument('--alternate-trace', type=Path)
    p.add_argument('--output', type=Path)
    args=p.parse_args()
    read=lambda path: json.loads(path.read_text()) if path else None
    result=evaluate(read(args.reference_report),read(args.trace),read(args.alternate_trace))
    output=json.dumps(result, indent=2,sort_keys=True)+'\n'
    if args.output: args.output.write_text(output)
    else: print(output,end='')

if __name__ == '__main__':
    main()
