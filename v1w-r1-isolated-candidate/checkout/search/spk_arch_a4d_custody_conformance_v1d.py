"""A4d source-pinned quiescent P/S/E/O custody, replay recovery, cold activation.

Frozen Compiler/host witness is consulted independently for baseline (A4b)
and for changed candidate (A4c). A3d is the live causal engine. Restoring
closed state requires full re-execution of the original bounded input case,
not injection of final S/E/O into a running neuron. Cross-program activation
must use explicit COLD_RESET and an A4c-approved logical pointer promotion.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from dataclasses import asdict

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a4b_mode_memory_conformance_v1b import mode_memory_case_v1b, SOURCE_SHA256
from search.spk_arch_a3b_causal_service_conformance_v1b import compiled_reference, projected_hash
from search.spk_arch_a4c_candidate_conformance_v1c import args_v1c
from spk_architecture_v1.pe_fabric_v1a import SCHEMES
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a, execute_temporal_v1a
from spk_architecture_v1.operating_modes_v1a import ModeControllerV1a, context_fingerprint_v1a
from spk_architecture_v1.candidate_promotion_v1c import CandidateRegistryV1c, describe_candidate_v1c
from spk_architecture_v1.state_custody_v1d import StateCustodyV1d, StateCustodyDeniedV1d

SCHEMA = 'spk-architecture-a4d-state-custody-evidence/v1d'


def custody_case_v1d(cid, case, target_id, target_case, scheme, producer_mode):
    original = mode_memory_case_v1b(cid, case, scheme)
    candidate = compiled_reference(target_id, target_case, scheme)
    old_args, target_args = args_v1c(case, scheme), args_v1c(target_case, scheme)
    old_context = context_fingerprint_v1a(*old_args)
    candidate_context = context_fingerprint_v1a(*target_args)
    if (original['execute_priority'] != ['E','S','P','O']
            or original['verify_priority'] != ['P','S','E','O']
            or old_context == candidate_context
            or candidate['canonical_result_sha256'] != projected_hash(
                execute_temporal_v1a(target_case, target_args[1], TransportPlanV1a(0))['result'])):
        raise AssertionError('A4d frozen baseline/changed candidate semantic provenance failure')

    registry = CandidateRegistryV1c(old_context)
    source = ModeControllerV1a(old_context)
    source.transition('EXECUTE')
    live = source.run(*old_args)
    custody = StateCustodyV1d(registry)
    snapshot = custody.capture(source, live, old_args)
    reconstructed = custody.recover_by_replay(old_args)
    if (reconstructed.replay_result_sha256 != live['result_sha256']
            or reconstructed.revision != 0 or registry.revision != 0):
        raise AssertionError('A4d replay did not reconstruct complete source state')

    desc = describe_candidate_v1c(target_id, SOURCE_SHA256,
                                  candidate['manifest_sha256'], target_args)
    producer = ModeControllerV1a(old_context)
    producer.transition(producer_mode)
    stage = registry.stage(producer, desc)
    verified = registry.verify(ModeControllerV1a(candidate_context), target_args,
                               trusted_ideal_witness={
                                   'source_sha256': SOURCE_SHA256,
                                   'manifest_sha256': candidate['manifest_sha256'],
                                   'ideal_result_sha256': candidate['canonical_result_sha256']})
    approved = registry.approve('SPK-operator', verified, expected_revision=0)
    promoted = registry.promote(producer, verified, approved)
    try:
        custody.recover_by_replay(old_args)
    except StateCustodyDeniedV1d:
        pass
    else:
        raise AssertionError('A4d allowed stale-state recovery after versioned promotion')
    activated = custody.activate_cold(promoted, old_args, target_args, policy='COLD_RESET')
    if (activated.result_sha256 != verified.execution_sha256
            or activated.revision != 1 or registry.revision != 1
            or registry.active_context_sha256 != candidate_context):
        raise AssertionError('A4d cold activation did not preserve verified target')
    return {'id': cid,'candidate_id': target_id,'scheme': scheme,
            'producer_mode':producer_mode,
            'baseline_manifest_sha256':original['manifest_sha256'],
            'candidate_manifest_sha256':candidate['manifest_sha256'],
            'source_context_sha256':old_context,'target_context_sha256':candidate_context,
            'snapshot_sha256':snapshot.checkpoint_sha256,
            'program_image_sha256':snapshot.program_sha256,
            'final_state_sha256':snapshot.states_sha256,
            'event_custody_sha256':snapshot.event_custody_sha256,
            'observation_sha256':snapshot.observations_sha256,
            'reconstructed_sha256':reconstructed.recovery_sha256,
            'approval_sha256':approved.approval_sha256,
            'promotion_sha256':promoted.promotion_sha256,
            'cold_activation_sha256':activated.activation_sha256,
            'source_result_sha256':live['result_sha256'],
            'target_result_sha256':activated.result_sha256,
            'revision':registry.revision}


def report_v1d():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('A4d source drift')
    catalog = checked_catalog_v0()
    if len(catalog) != 216:
        raise AssertionError('unexpected corpus size')
    rows = []
    for i, (cid, case) in enumerate(catalog):
        target_id, target_case = catalog[(i+36) % 216]
        for scheme in SCHEMES:
            rows.append(custody_case_v1d(
                cid,case,target_id,target_case,scheme,
                'TRAINING' if i % 2 == 0 else 'REMODEL'))
    if (len(rows) != 648 or any(row['revision'] != 1
            or row['source_context_sha256'] == row['target_context_sha256']
            for row in rows)):
        raise AssertionError('A4d replay/activation coverage drift')
    return {'schema': SCHEMA,'source_sha256': SOURCE_SHA256,'source_cases':216,
            'frozen_baseline_witnesses':648,'frozen_candidate_witnesses':648,
            'closed_state_snapshots':648,'same_context_replay_recoveries':648,
            'stale_revision_recovery_denials':648,'cold_reset_activations':648,
            'cross_program_migrations':0,'training_promotions':324,
            'remodel_promotions':324,'rows':rows,
            'limitations':[
                'recovery is re-execution from original bounded inputs, not live S/E/O injection',
                'changed program promotion permits only explicit cold reset, never state migration',
                'closed A3d output has no pending routes, in-flight occurrences or sender outbox',
                'no training algorithm, persistent journal, crash-atomic commit or rollback',
                'trusted logical in-memory authority, not hostile-process security',
            ]}


def seal_v1d():
    payload = report_v1d()
    return canonical({'schema':SCHEMA, 'payload':payload,
                      'payload_sha256':sha(SCHEMA+'\n'+canonical(payload))})


def verify_v1d(document):
    obj=strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema','payload','payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A4d custody evidence')
    if obj['payload_sha256'] != sha(SCHEMA+'\n'+canonical(obj['payload'])):
        raise ValueError('A4d custody evidence checksum mismatch')
    if obj['payload'] != report_v1d():
        raise ValueError('A4d custody evidence full replay mismatch')
    return {'status':'PASS','source_cases':216,
            'frozen_baseline_witnesses':obj['payload']['frozen_baseline_witnesses'],
            'frozen_candidate_witnesses':obj['payload']['frozen_candidate_witnesses'],
            'closed_state_snapshots':obj['payload']['closed_state_snapshots'],
            'same_context_replay_recoveries':obj['payload']['same_context_replay_recoveries'],
            'stale_revision_recovery_denials':obj['payload']['stale_revision_recovery_denials'],
            'cold_reset_activations':obj['payload']['cold_reset_activations'],
            'evidence_sha256':sha(document)}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    options=parser.add_mutually_exclusive_group(required=True)
    options.add_argument('--write',type=Path)
    options.add_argument('--verify',type=Path)
    parsed=parser.parse_args(argv)
    if parsed.write is not None:
        doc=seal_v1d()
        parsed.write.write_text(doc+'\n',encoding='utf8')
        print(canonical({'status':'WRITTEN','evidence_sha256':sha(doc)}))
    else:
        doc=parsed.verify.read_text(encoding='utf8').rstrip('\n')
        print(canonical(verify_v1d(doc)))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
