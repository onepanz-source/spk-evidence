"""A4c source-pinned cold promotions of real changed candidate programs.

A4b authenticates the baseline through frozen Compiler/host A4a and A2b;
a second frozen compilation plus independent A3a zero-latency projection
anchors each candidate's ideal semantics. A4c replays its causal A3d variant,
then an explicit operator approval switches only the logical context pointer.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a4b_mode_memory_conformance_v1b import mode_memory_case_v1b, SOURCE_SHA256
from search.spk_arch_a3b_causal_service_conformance_v1b import compiled_reference, projected_hash
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.temporal_transport_v1a import (
    TransportPlanV1a, execute_temporal_v1a,
)
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
from spk_architecture_v1.operating_modes_v1a import (
    ModeControllerV1a, context_fingerprint_v1a,
)
from spk_architecture_v1.candidate_promotion_v1c import (
    CandidateRegistryV1c, describe_candidate_v1c,
)

SCHEMA = 'spk-architecture-a4c-candidate-promotion-evidence/v1c'


def args_v1c(case, scheme):
    fabric = plan_v1a(case, scheme)
    return (case, fabric, TransportPlanV1a(2),
            uniform_causal_service_plan_v1b(fabric, pe_slots=128,
                                             fabric_slots_per_tick=128),
            uniform_causal_memory_plan_v1c(fabric),
            CausalLinkPlanV1d(1, 1, 128, 4096))


def promotion_case_v1c(cid, case, target_id, target_case, scheme, producer_mode):
    original = mode_memory_case_v1b(cid, case, scheme)
    target = compiled_reference(target_id, target_case, scheme)
    old_args = args_v1c(case, scheme)
    target_args = args_v1c(target_case, scheme)
    old_context = context_fingerprint_v1a(*old_args)
    if (original['execute_priority'] != ['E', 'S', 'P', 'O']
            or original['verify_priority'] != ['P', 'S', 'E', 'O']
            or original['manifest_sha256'] == ''
            or canonical([asdict(x) for x in old_args]) == canonical([asdict(x) for x in target_args])):
        raise AssertionError('A4c baseline authority or actual candidate change absent')
    if target['canonical_result_sha256'] != projected_hash(
            execute_temporal_v1a(target_case, target_args[1], TransportPlanV1a(0))['result']):
        raise AssertionError('candidate frozen host and independent ideal PE differ')
    descriptor = describe_candidate_v1c(target_id, SOURCE_SHA256,
                                        target['manifest_sha256'], target_args)
    registry = CandidateRegistryV1c(old_context)
    producer = ModeControllerV1a(old_context)
    producer.transition(producer_mode)
    stage = registry.stage(producer, descriptor)
    if registry.active_context_sha256 != old_context:
        raise AssertionError('staging mutated active reference')
    target_controller = ModeControllerV1a(descriptor.context_sha256)
    verified = registry.verify(target_controller, target_args,
                               trusted_ideal_witness={
                                   'source_sha256': SOURCE_SHA256,
                                   'manifest_sha256': target['manifest_sha256'],
                                   'ideal_result_sha256': target['canonical_result_sha256']})
    if registry.active_context_sha256 != old_context:
        raise AssertionError('verification changed deployment')
    approval = registry.approve('SPK-operator', verified, expected_revision=0)
    promoted = registry.promote(producer, verified, approval)
    cold = registry.cold_start(promoted)
    if cold.status != 'QUIESCENT' or cold.mode != 'VERIFY' or cold.epoch != 0:
        raise AssertionError('fresh promoted controller was not quiescent')
    cold.transition('EXECUTE')
    cold_run = cold.run(*target_args)
    if (cold_run['result_sha256'] != verified.execution_sha256
            or registry.active_context_sha256 != descriptor.context_sha256
            or registry.revision != 1 or len(registry.history) != 1):
        raise AssertionError('cold promotion did not adopt verified target')
    return {'id':cid, 'candidate_id':target_id, 'scheme':scheme,
            'staging_mode':producer_mode,
            'original_manifest_sha256':original['manifest_sha256'],
            'candidate_manifest_sha256':target['manifest_sha256'],
            'candidate_ideal_sha256':target['canonical_result_sha256'],
            'from_context_sha256':old_context,
            'to_context_sha256':registry.active_context_sha256,
            'stage_sha256':stage.stage_sha256,
            'verification_sha256':verified.verification_sha256,
            'approval_sha256':approval.approval_sha256,
            'promotion_sha256':promoted.promotion_sha256,
            'cold_result_sha256':cold_run['result_sha256'],
            'revision':registry.revision}


def report_v1c():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('source catalog drift from frozen 216 cases')
    catalog = checked_catalog_v0()
    if len(catalog) != 216:
        raise AssertionError('unexpected frozen catalog size')
    rows=[]
    for i, (cid, case) in enumerate(catalog):
        target_id, target_case = catalog[(i+36) % 216]
        for scheme in SCHEMES:
            rows.append(promotion_case_v1c(
                cid, case, target_id, target_case, scheme,
                'TRAINING' if i % 2 == 0 else 'REMODEL'))
    if (len(rows) != 648
            or sum(x['staging_mode'] == 'TRAINING' for x in rows) != 324
            or sum(x['staging_mode'] == 'REMODEL' for x in rows) != 324
            or any(x['revision'] != 1 or x['from_context_sha256'] == x['to_context_sha256']
                   for x in rows)):
        raise AssertionError('A4c promotion coverage or authority drift')
    return {'schema': SCHEMA, 'source_sha256': SOURCE_SHA256,
            'source_cases':216, 'compiled_baseline_witnesses':648,
            'compiled_candidate_witnesses':648,
            'candidate_stagings':648,'independent_candidate_verifications':648,
            'explicit_promotions':648,'cold_executions':648,
            'training_promotions':324,'remodel_promotions':324,
            'rows':rows,
            'limitations':[
                'candidate programs are distinct frozen-corpus variants, not learned updates',
                'ideal v0 frozen witness anchors candidate semantics; timed A3d replay is deterministic',
                'operator approval is a trusted logical authority, not a cryptographic signature',
                'promotion changes only an in-memory logical active-context pointer',
                'cold controller starts with initial state; no live migration or rollback',
                'no hostile-process security, durable commit or training algorithm',
            ]}


def seal_v1c():
    payload=report_v1c()
    return canonical({'schema':SCHEMA,'payload':payload,
                      'payload_sha256':sha(SCHEMA+'\n'+canonical(payload))})


def verify_v1c(document):
    obj=strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema','payload','payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A4c evidence')
    if obj['payload_sha256'] != sha(SCHEMA+'\n'+canonical(obj['payload'])):
        raise ValueError('A4c evidence checksum mismatch')
    if obj['payload'] != report_v1c():
        raise ValueError('A4c full semantic replay mismatch')
    return {'status':'PASS','source_cases':216,
            'compiled_baseline_witnesses':obj['payload']['compiled_baseline_witnesses'],
            'compiled_candidate_witnesses':obj['payload']['compiled_candidate_witnesses'],
            'independent_candidate_verifications':obj['payload']['independent_candidate_verifications'],
            'explicit_promotions':obj['payload']['explicit_promotions'],
            'cold_executions':obj['payload']['cold_executions'],
            'evidence_sha256':sha(document)}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_mutually_exclusive_group(required=True)
    commands.add_argument('--write',type=Path)
    commands.add_argument('--verify',type=Path)
    args=parser.parse_args(argv)
    if args.write is not None:
        doc=seal_v1c()
        args.write.write_text(doc+'\n',encoding='utf-8')
        print(canonical({'status':'WRITTEN','evidence_sha256':sha(doc)}))
    else:
        doc=args.verify.read_text(encoding='utf-8').rstrip('\n')
        print(canonical(verify_v1c(doc)))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
