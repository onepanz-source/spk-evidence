"""A4b mode-bound P/S/E/O post-run authorization and finite service witness.

A4a and A2b frozen compiled-host witness paths are each invoked independently.
This combines two *logical* ledgers: the A3d execution under A4a and the A1d
reference memory trace verified in A2a/A2b. No claim that the latter was an
observed physical access trace during the former execution.
"""
from __future__ import annotations
import argparse
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a4a_mode_conformance_v1a import mode_case_v1a, SOURCE_SHA256
from search.spk_arch_a2b_access_conformance_v1b import evaluate_v1b
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_service_v1c import uniform_service_plan_v1c
from spk_architecture_v1.pe_fault_v1d import execute_failstop_v1d
from spk_architecture_v1.memory_projection_v1a import (
    admit_memory_v1a, project_execution_memory_v1a, uniform_memory_plan_v1a,
)
from spk_architecture_v1.memory_access_v1b import authorize_projection_v1b
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
from spk_architecture_v1.operating_modes_v1a import (
    ModeControllerV1a, context_fingerprint_v1a,
)
from spk_architecture_v1.mode_memory_v1b import (
    ModeMemoryDeniedV1b, issue_mode_memory_permit_v1b, serve_mode_memory_v1b,
)

SCHEMA = 'spk-architecture-a4b-mode-memory-evidence/v1b'


def mode_memory_case_v1b(cid, case, scheme):
    a4a_witness = mode_case_v1a(cid, case, scheme)  # real Compiler/host via A3d
    a2b_witness = evaluate_v1b(cid, case, scheme)  # real Compiler/host via A1d/A2a
    if a4a_witness['manifest_sha256'] != a2b_witness['manifest_sha256']:
        raise AssertionError('A4b frozen Compiler manifest mismatch')
    fabric = plan_v1a(case, scheme)
    pservice = uniform_service_plan_v1c(fabric, pe_slots=4096,
                                         fabric_slots_per_tick=4096)
    admission = admit_memory_v1a(case, fabric, pservice,
                                  uniform_memory_plan_v1a(fabric))
    projection = project_execution_memory_v1a(
        case, fabric, admission, execute_failstop_v1d(case, fabric, pservice))
    authorized = authorize_projection_v1b(admission, projection)
    if (sha(canonical(authorized)) != a2b_witness['nominal_authorization_sha256']
            or authorized['logical_units'] != a2b_witness['nominal_logical_units']):
        raise AssertionError('A4b A2b reference authorization mismatch')
    args = (case, fabric, TransportPlanV1a(2),
            uniform_causal_service_plan_v1b(fabric, pe_slots=128,
                                              fabric_slots_per_tick=128),
            uniform_causal_memory_plan_v1c(fabric),
            CausalLinkPlanV1d(1, 1, 128, 4096))
    context = context_fingerprint_v1a(*args)
    if context != a4a_witness['context_sha256']:
        raise AssertionError('A4b A4a context mismatch')
    controller = ModeControllerV1a(context)
    candidate = sha(SOURCE_SHA256 + '\n' + cid + '\n' + scheme)
    denials = 0
    for mode in ('TRAINING', 'REMODEL'):
        if controller.mode != 'VERIFY':
            controller.transition('VERIFY')
        controller.transition(mode)
        controller.stage(candidate)
        try:
            issue_mode_memory_permit_v1b(controller, admission, projection)
        except ModeMemoryDeniedV1b:
            denials += 1
        else:
            raise AssertionError('staging mode gained memory access')
        controller.transition('VERIFY')
    controller.transition('EXECUTE')
    live = controller.run(*args)
    live_permit = issue_mode_memory_permit_v1b(controller, admission, projection)
    live_service = serve_mode_memory_v1b(controller, live_permit, admission, projection)
    controller.transition('VERIFY')
    replay = controller.run(*args, expected_sha256=live['result_sha256'])
    replay_permit = issue_mode_memory_permit_v1b(controller, admission, projection)
    replay_service = serve_mode_memory_v1b(controller, replay_permit,
                                           admission, projection)
    if (replay['boundary'].audit_sha256 != a4a_witness['mode_audit_sha256']
            or controller.epoch != 6 or controller.status != 'QUIESCENT'
            or live['result_sha256'] != a4a_witness['mode_full_result_sha256']):
        raise AssertionError('A4b departed from certified A4a mode run')
    if (live_service['service']['logical_units'] != replay_service['service']['logical_units']
            or live_service['service']['logical_units'] != authorized['logical_units']
            or live_service['service']['request_count'] != authorized['request_count']
            or live_permit.request_sha256 != replay_permit.request_sha256
            or denials != 2):
        raise AssertionError('A4b lost logical memory access conservation')
    return {
        'id': cid, 'scheme': scheme,
        'manifest_sha256': a4a_witness['manifest_sha256'],
        'mode_audit_sha256': replay['boundary'].audit_sha256,
        'nominal_authorization_sha256': a2b_witness['nominal_authorization_sha256'],
        'execute_service_sha256': sha(canonical(live_service)),
        'verify_service_sha256': sha(canonical(replay_service)),
        'execute_priority': live_service['priority_order'],
        'verify_priority': replay_service['priority_order'],
        'logical_units': authorized['logical_units'],
        'stage_memory_denials': denials,
    }


def report_v1b():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('source catalog changed from frozen 216 cases')
    rows = [mode_memory_case_v1b(cid, case, scheme)
            for cid, case in checked_catalog_v0() for scheme in SCHEMES]
    if (len(rows) != 648 or sum(x['stage_memory_denials'] for x in rows) != 1296
            or any(x['execute_priority'] != ['E','S','P','O']
                   or x['verify_priority'] != ['P','S','E','O'] for x in rows)):
        raise AssertionError('A4b source coverage or mode priority drift')
    return {'schema': SCHEMA, 'source_sha256': SOURCE_SHA256,
            'source_cases': 216, 'compiled_host_comparisons': 648,
            'mode_logical_service_runs': 1296,
            'staging_memory_denials': 1296,
            'rows': rows,
            'limitations': [
                'mode-bound authorization of A2a/A2b reference logical aggregates',
                'A1d memory reference trace is NOT an A3d physical memory trace',
                'VERIFY private scope is logical, no hardware process isolation',
                'no program promotion, modification or live RAM access',
                'mode priorities are controller policy, not algebra laws',
            ]}


def seal_v1b():
    payload = report_v1b()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1b(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A4b mode memory evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('A4b evidence checksum mismatch')
    if obj['payload'] != report_v1b():
        raise ValueError('A4b semantic evidence replay mismatch')
    return {'status': 'PASS', 'source_cases': obj['payload']['source_cases'],
            'compiled_host_comparisons': obj['payload']['compiled_host_comparisons'],
            'mode_logical_service_runs': obj['payload']['mode_logical_service_runs'],
            'staging_memory_denials': obj['payload']['staging_memory_denials'],
            'evidence_sha256': sha(document)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--write', type=Path)
    g.add_argument('--verify', type=Path)
    a = p.parse_args()
    if a.write is not None:
        doc = seal_v1b()
        a.write.write_text(doc + '\n', encoding='utf-8')
        print(canonical({'status': 'WRITTEN', 'evidence_sha256': sha(doc)}))
    else:
        doc = a.verify.read_text(encoding='utf-8').rstrip('\n')
        print(canonical(verify_v1b(doc)))


if __name__ == '__main__':
    main()
