"""A4a sealed mode epochs on real A3d PE-local causal executions.

Compiler/host witness is obtained through existing frozen A3d evaluator.
The mode controller has no authority to modify frozen neuron programs.
"""
from __future__ import annotations
import argparse
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a3d_link_conformance_v1d import (
    evaluate_v1d, SOURCE_SHA256, LATENCIES, REGIMES,
)
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
from spk_architecture_v1.operating_modes_v1a import (
    SCHEMA as MODE_SCHEMA, ModeControllerV1a, context_fingerprint_v1a,
)

SCHEMA = 'spk-architecture-a4a-operating-mode-evidence/v1a'


def mode_case_v1a(cid, case, scheme):
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('source case fingerprint drift')
    f = plan_v1a(case, scheme)
    t = TransportPlanV1a(2)
    p = uniform_causal_service_plan_v1b(f, pe_slots=128, fabric_slots_per_tick=128)
    m = uniform_causal_memory_plan_v1c(f)
    l = CausalLinkPlanV1d(1, 1, 128, 4096)
    binding = context_fingerprint_v1a(case, f, t, p, m, l)
    c = ModeControllerV1a(binding)
    candidate = sha(SOURCE_SHA256 + '\n' + cid + '\n' + scheme)
    c.transition('TRAINING')
    c.stage(candidate)
    c.transition('VERIFY')
    c.transition('REMODEL')
    c.stage(candidate)
    c.transition('VERIFY')
    c.transition('EXECUTE')
    live = c.run(case, f, t, p, m, l)
    assert live['boundary'].status == 'QUIESCENT'
    c.transition('VERIFY')
    replay = c.run(case, f, t, p, m, l, expected_sha256=live['result_sha256'])
    if replay['result_sha256'] != live['result_sha256']:
        raise AssertionError('inconsistent mode replay')
    witness = evaluate_v1d(cid, case, scheme)
    expected = next(r for r in witness['runs']
                    if r['latency_ticks'] == 2 and r['regime'] == 'link_limited')
    # Compare full A3d result projection with the previous signed result witness.
    from search.spk_arch_a3b_causal_service_conformance_v1b import projected_hash
    if projected_hash(live['output']['result']) != expected['result_sha256']:
        raise AssertionError('mode-controlled run differs from A3d witness')
    if (live['output']['transport']['cross_pe_occurrences'] !=
            expected['cross_pe_occurrences']):
        raise AssertionError('mode-controlled route tally differs from A3d')
    if (live['output']['transport']['source_blocked_ticks'] !=
            expected['source_blocked_ticks']):
        raise AssertionError('mode-controlled service trace differs from A3d')
    return {'id': cid, 'scheme': scheme, 'context_sha256': binding,
            'manifest_sha256': witness['manifest_sha256'],
            'a3d_result_sha256': expected['result_sha256'],
            'mode_full_result_sha256': live['result_sha256'],
            'mode_audit_sha256': replay['boundary'].audit_sha256,
            'epoch': replay['boundary'].epoch, 'status': replay['boundary'].status,
            'remote_occurrences': live['output']['transport']['cross_pe_occurrences'],
            'transitions': sum(x['kind'] == 'TRANSITION' for x in c.audit),
            'staged_references': sum(x['kind'] == 'STAGE' for x in c.audit),
            'live_runs': sum(x['kind'] == 'RUN' for x in c.audit),
            'verifications': sum(x['kind'] == 'REPLAY' for x in c.audit)}


def report_v1a():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('source fingerprint drift')
    rows = [mode_case_v1a(cid, case, scheme)
            for cid, case in checked_catalog_v0() for scheme in SCHEMES]
    if len(rows) != 648 or any(
            (r['epoch'], r['status'], r['transitions'], r['staged_references'],
             r['live_runs'], r['verifications']) != (6, 'QUIESCENT', 6, 2, 1, 1)
            for r in rows):
        raise AssertionError('missing/invalid mode ledger')
    return {'schema': SCHEMA, 'source_sha256': SOURCE_SHA256,
            'source_cases': 216, 'compiled_host_comparisons': 648,
            'mode_controlled_executions': 648, 'independent_mode_replays': 648,
            'staged_candidate_references': 1296,
            'rows': rows,
            'limitations': ['single trusted in-process controller and global logical epochs',
                            'TRAINING and REMODEL stage candidate digests only',
                            'VERIFY re-executes A3d without mutating deployed program',
                            'no actual training, remodeling, checkpoint migration or rollback']}


def seal_v1a():
    payload = report_v1a()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1a(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A4a evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('A4a evidence checksum mismatch')
    if obj['payload'] != report_v1a():
        raise ValueError('A4a semantic evidence replay mismatch')
    return {'status': 'PASS', 'source_cases': obj['payload']['source_cases'],
            'compiled_host_comparisons': obj['payload']['compiled_host_comparisons'],
            'mode_controlled_executions': obj['payload']['mode_controlled_executions'],
            'independent_mode_replays': obj['payload']['independent_mode_replays'],
            'staged_candidate_references': obj['payload']['staged_candidate_references'],
            'evidence_sha256': sha(document)}


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.write:
        document = seal_v1a()
        args.write.write_text(document + '\n')
        print(canonical({'status': 'WRITTEN', 'evidence_sha256': sha(document)}))
    else:
        print(canonical(verify_v1a(args.verify.read_text().rstrip('\n'))))


if __name__ == '__main__':
    main()
