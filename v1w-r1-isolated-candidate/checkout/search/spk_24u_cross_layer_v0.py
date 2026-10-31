"""SPK 24u: corpus-wide Compiler -> manifest -> reference host conformance.

No new evaluator or scheduler. Real frozen Compiler/Network are imported only
in this integration adapter; expected results come from independent 24n.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import (
    canonical, project_v0, sha, strict_json,
)
from search.spk_24n_independent_oracle_v0 import execute_v0
from search.spk_24o_extended_differential_v0 import to_frozen_v0
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_24q_limit_probe_plan_v0 import probes_for_case_v0
from search.spk_24s_budget_triads_v0 import plan_v0 as causal_plan_v0
from search.spk_24t_diagnostic_manifest_host_v0 import (
    execute_manifest_v0, seal_v0 as host_seal_v0, verify_v0 as host_verify_v0,
)
from search.spk_24u_conformance_plan_v0 import entries_v0, identity_v0, summary_v0
from spk_architecture.profile_v0 import ArchitectureProfileV0, ProcessingElementV0
from spk_compiler.compile_pipeline_v0 import compile_network_ir_v0
from spk_compiler.compilation_manifest_v0 import (
    dumps_compilation_manifest_v0, loads_compilation_manifest_v0,
)
from spk_compiler.network_ir_v0 import dumps_network_ir_v0, loads_network_ir_v0
from spk_compiler.pe_admission_v0 import NodePlacementV0
from spk_compiler.resource_admission_v0 import ResourceProfileV0

SCHEMA = 'spk-cross-layer-conformance-evidence/v0'
MAX_BATCHES = 128
MAX_EVENTS = 4096


def _event_counter(events):
    return Counter((e.timestamp, e.node_id, e.channel) for e in events)


def _architecture_v0():
    # Per-node placement avoids hiding resource and PE admission in a
    # shared-overcommit setup. Values mirror the accepted 24m reference PE.
    pe = ProcessingElementV0(
        pe_id='PE0', program_slots=8, state_slots=2,
        event_slots=8, output_slots=8, observation_slots=8,
        accesses_per_service_tick=2,
    )
    return ArchitectureProfileV0(
        'spk-24u-3-node-conformance',
        (pe, replace(pe, pe_id='PE1'), replace(pe, pe_id='PE2')),
    )


def compile_case_v0(case):
    frozen, events = to_frozen_v0(case)
    ir = dumps_network_ir_v0(frozen)
    if loads_network_ir_v0(ir) != frozen:
        raise AssertionError('Network IR roundtrip changed the source')
    compiled = compile_network_ir_v0(
        network_ir_json=ir, initial_events=events,
        resource_profile=ResourceProfileV0(),
        architecture=_architecture_v0(),
        placements=tuple(NodePlacementV0(n.node_id, f'PE{i}')
                         for i, n in enumerate(case.nodes)),
    )
    manifest = dumps_compilation_manifest_v0(compiled)
    roundtrip = loads_compilation_manifest_v0(manifest)
    if roundtrip != compiled:
        raise AssertionError('Compiler manifest roundtrip changed the result')
    # Source and reconstructed programs must be *identical*, not just produce
    # one coincident output. External events are compared as multisets because
    # their literal source order is not a semantic property.
    # The compiler may perform permitted rewrites; correctness is established
    # below against the original independent primitive source, not equality of
    # the serialized graph representation.
    if _event_counter(roundtrip.initial_events) != _event_counter(events):
        raise AssertionError('Compiler changed external event multiplicities')
    return manifest, sha(manifest)


def _expected_full(case):
    primitive = execute_v0(case, max_batches=MAX_BATCHES,
                           max_events=MAX_EVENTS)
    return project_v0(primitive, primitive['observations']['batches'],
                      primitive['observations']['routes'])


def _check_host(manifest, pin, budget, *, status, reason=None,
                eligible=None, expected_full=None):
    execution = execute_manifest_v0(manifest, pin, **budget)
    if execution['status'] != status:
        raise AssertionError(f'manifest host status: {execution["status"]} != {status}')
    if status == 'CLOSED':
        if (execution['adjudication'] != 'EXACT_PASS' or
                execution['result'] != expected_full or
                execution['selected_reason'] is not None or
                execution['eligible_reasons']):
            raise AssertionError('compiled host result != independent source')
    else:
        if (execution['result'] is not None or
                execution['selected_reason'] not in (eligible or (reason,)) or
                tuple(execution['eligible_reasons']) != tuple(eligible or (reason,))):
            raise AssertionError('compiled host violated failure eligibility')
        desired = ('AMBIGUOUS_TIE_PASS' if len(execution['eligible_reasons']) == 2
                   else 'EXACT_PASS')
        if execution['adjudication'] != desired:
            raise AssertionError('compiled host diagnostic adjudication mismatch')
        if reason is not None and execution['selected_reason'] != reason:
            raise AssertionError('compiled host isolated reason mismatch')
    return execution


def evaluate_case_v0(case_id, case, plan, causal_controls=()):
    manifest, pin = compile_case_v0(case)
    expected = _expected_full(case)
    full = _check_host(manifest, pin,
                       {'max_batches': MAX_BATCHES, 'max_events': MAX_EVENTS},
                       status='CLOSED', expected_full=expected)
    count = 1
    adjudications = Counter({'EXACT_PASS': 1})
    if plan.boundary_kinds:
        probes = probes_for_case_v0(case_id, case)
        assert tuple(p.kind for p in probes) == plan.boundary_kinds
        for p in probes:
            if p.kind == 'exact_success':
                out = _check_host(manifest, pin, dict(max_batches=p.max_batches,
                                                      max_events=p.max_events),
                                  status='CLOSED', expected_full=expected)
            else:
                out = _check_host(manifest, pin, dict(max_batches=p.max_batches,
                                                      max_events=p.max_events),
                                  status=p.expected_status, reason=p.expected_reason)
            adjudications[out['adjudication']] += 1
            count += 1
    if plan.dual_controls:
        assert tuple(c.condition for c in causal_controls) == plan.dual_controls
        for c in causal_controls:
            out = _check_host(manifest, pin, dict(max_batches=c.max_batches,
                                                  max_events=c.max_events),
                              status='LIMIT_REACHED', eligible=c.expected_violated)
            adjudications[out['adjudication']] += 1
            count += 1
    return {'case_id': case_id, 'manifest_sha256': pin,
            'result_sha256': sha(canonical(full['result'])),
            'compiled_nodes': len(case.nodes),
            'compiled_edges': len(case.edges),
            'host_runs': count,
            'exact_adjudications': adjudications['EXACT_PASS'],
            'ambiguous_adjudications': adjudications['AMBIGUOUS_TIE_PASS']}


def report_v0():
    cases = catalog_v0()
    plans = entries_v0()
    causal = {cid: controls for cid, _, controls in causal_plan_v0()}
    if len(cases) != len(plans):
        raise AssertionError('cross-layer corpus and plan length mismatch')
    rows = []
    for (cid, case), planned in zip(cases, plans):
        if cid != planned.case_id:
            raise AssertionError('cross-layer plan identity mismatch')
        rows.append(evaluate_case_v0(cid, case, planned, causal.get(cid, ())))
    runs = sum(r['host_runs'] for r in rows)
    return {'schema': SCHEMA, 'plan_sha256': identity_v0(),
            'plan_summary': summary_v0(), 'admitted_cases': len(rows),
            'compiled_three_node_cases': sum(r['compiled_nodes'] == 3 for r in rows),
            'host_runs': runs,
            'exact_adjudications': sum(r['exact_adjudications'] for r in rows),
            'ambiguous_adjudications': sum(r['ambiguous_adjudications'] for r in rows),
            'rows': rows}


def seal_v0():
    payload = report_v0()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v0(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical cross-layer conformance envelope')
    payload = obj['payload']
    if sha(SCHEMA + '\n' + canonical(payload)) != obj['payload_sha256']:
        raise ValueError('conformance checksum mismatch')
    if report_v0() != payload:
        raise ValueError('cross-layer replay mismatch')
    return {'status': 'PASS', 'admitted_cases': payload['admitted_cases'],
            'host_runs': payload['host_runs'],
            'exact_adjudications': payload['exact_adjudications'],
            'ambiguous_adjudications': payload['ambiguous_adjudications'],
            'plan_sha256': payload['plan_sha256'], 'evidence_sha256': sha(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', type=Path)
    mode.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
    if args.write is not None:
        document = seal_v0()
        args.write.write_text(document + '\n', encoding='utf-8')
    else:
        document = args.verify.read_text(encoding='utf-8').rstrip('\n')
    print(canonical(verify_v0(document)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
