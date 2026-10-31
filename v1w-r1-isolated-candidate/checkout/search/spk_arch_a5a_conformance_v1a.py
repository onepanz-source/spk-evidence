"""A5a independent vertical witness: compiler -> A3d -> A4d + Git source custody.

The sampled cross-layer witnesses cover all 6 profiles x 6 graph families x
3 PE placements, with six input families represented. This is NOT exhaustive
16-phase evidence regeneration, and retains the bounded v0 semantics.
"""
from __future__ import annotations
import argparse
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a3d_link_conformance_v1d import evaluate_v1d
from search.spk_arch_a3b_causal_service_conformance_v1b import projected_hash
from search.spk_arch_a4d_custody_conformance_v1d import custody_case_v1d
from search.spk_arch_a4c_candidate_conformance_v1c import args_v1c
from spk_architecture_v1.pe_fabric_v1a import SCHEMES
from spk_architecture_v1.causal_transport_v1d import execute_causal_transport_v1d
from spk_architecture_v1.operating_modes_v1a import result_digest_v1a
from spk_architecture_v1.conformance_inventory_v1a import (
    manifest_v1a, CORPUS_SHA256,
)

SCHEMA = 'spk-architecture-a5a-vertical-conformance-evidence/v1a'


def sampled_indices_v1a():
    return tuple(36 * p + 6 * g + (p + g) % 6
                 for p in range(6) for g in range(6))


def cross_witness_v1a(catalog, index, scheme):
    cid, case = catalog[index]
    tid, target = catalog[(index + 36) % 216]
    mode = 'TRAINING' if index % 2 == 0 else 'REMODEL'
    # Custody through real frozen Compiler witnesses, A4b, A4c, A4d.
    state = custody_case_v1d(cid, case, tid, target, scheme, mode)
    # Independent route/latency/credit comparison against frozen host.
    link = evaluate_v1d(cid, case, scheme)
    # Independent invocation bypassing A4a/A4d mode/custody wrappers.
    actual = execute_causal_transport_v1d(*args_v1c(case, scheme))
    target_actual = execute_causal_transport_v1d(*args_v1c(target, scheme))
    digest = result_digest_v1a(actual)
    target_digest = result_digest_v1a(target_actual)
    transmitted = actual['transport']
    if (state['source_result_sha256'] != digest
            or state['target_result_sha256'] != target_digest
            or state['baseline_manifest_sha256'] != link['manifest_sha256']
            or state['baseline_manifest_sha256'] == state['candidate_manifest_sha256']
            or state['revision'] != 1
            or transmitted['outstanding_outbox_occurrences'] != 0
            or transmitted['remaining_inflight_occurrences'] != 0
            or transmitted['cross_pe_occurrences'] != transmitted['delivered_cross_pe_occurrences']
            or transmitted['cross_pe_occurrences'] != len(transmitted['link_grants'])
            or actual['result']['processed_events'] != len(case.events) + len(transmitted['transfers'])):
        raise AssertionError('A5a cross-layer custody/transport provenance drift: '+cid+'/'+scheme)
    # Source A4c config == A3d link_limited, 2-tick transport.
    timed = [r for r in link['runs']
             if r['latency_ticks'] == 2 and r['regime'] == 'link_limited']
    if len(timed) != 1 or timed[0]['result_sha256'] != projected_hash(actual['result']):
        raise AssertionError('A5a A3d differential link witness drift: '+cid+'/'+scheme)
    if timed[0]['routes_sha256'] != sha(canonical(transmitted['transfers'])):
        raise AssertionError('A5a canonical link transfer transcript mismatch')
    return {'id': cid, 'candidate_id': tid, 'scheme': scheme, 'producer_mode': mode,
            'baseline_manifest_sha256': state['baseline_manifest_sha256'],
            'candidate_manifest_sha256': state['candidate_manifest_sha256'],
            'source_result_sha256': digest, 'candidate_result_sha256': target_digest,
            'source_checkpoint_sha256': state['snapshot_sha256'],
            'recovery_sha256': state['reconstructed_sha256'],
            'approval_sha256': state['approval_sha256'],
            'cold_activation_sha256': state['cold_activation_sha256'],
            'delivered_remote_occurrences': transmitted['cross_pe_occurrences'],
            'link_trace_sha256': timed[0]['routes_sha256']}


def report_v1a(root):
    if catalog_fingerprint_v0() != CORPUS_SHA256:
        raise AssertionError('frozen semantic source corpus mismatch')
    inventory = manifest_v1a(root)
    catalog = checked_catalog_v0()
    if len(catalog) != 216 or len(SCHEMES) != 3:
        raise AssertionError('unexpected frozen source/placement set')
    selected = sampled_indices_v1a()
    if (len(selected) != 36 or len(set(selected)) != 36
            or {i // 36 for i in selected} != set(range(6))
            or {(i % 36)//6 for i in selected} != set(range(6))
            or {i % 6 for i in selected} != set(range(6))):
        raise AssertionError('bad cross-layer sample stratification')
    rows = [cross_witness_v1a(catalog, i, s) for i in selected for s in SCHEMES]
    if len(rows) != 108 or len({(r['id'], r['scheme']) for r in rows}) != 108:
        raise AssertionError('A5a sampled coverage incomplete')
    return {'schema': SCHEMA, 'source_sha256': CORPUS_SHA256,
            'source_cases': 216, 'sampled_cases': 36, 'cross_layer_witnesses':108,
            'independent_frozen_baseline_and_candidate_witnesses':216,
            'prior_phases': 16, 'prior_source_files': 97,
            'predecessor_git_inventory': inventory,
            'rows': rows, 'limitations': [
                '108 stratified cross-layer witnesses, NOT exhaustive full 648-case cross-phase replay',
                '16 prior gate digests are recorded from certified reports, NOT reexecuted by this report',
                'global deterministic arbitration; bounded corpus and software runtime',
                'trusted in-process custody; no physical NoC or durable crash recovery',
                'no hot neuronal state migration or hardware execution',
            ]}


def seal_v1a(root):
    payload=report_v1a(root)
    return canonical({'schema':SCHEMA,'payload':payload,
                      'payload_sha256':sha(SCHEMA+'\n'+canonical(payload))})


def verify_v1a(document, root):
    obj=strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema','payload','payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A5a evidence')
    if obj['payload_sha256'] != sha(SCHEMA+'\n'+canonical(obj['payload'])):
        raise ValueError('A5a evidence checksum mismatch')
    if obj['payload'] != report_v1a(root):
        raise ValueError('A5a independent replay mismatch')
    payload=obj['payload']
    return {'status':'PASS','prior_phases':payload['prior_phases'],
            'tracked_source_files':payload['prior_source_files'],
            'sampled_cases':payload['sampled_cases'],
            'cross_layer_witnesses':payload['cross_layer_witnesses'],
            'evidence_sha256':sha(document)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--write',type=Path)
    g.add_argument('--verify',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    if args.write is not None:
        doc=seal_v1a(root)
        args.write.write_text(doc+'\n',encoding='utf8')
        print(canonical({'status':'WRITTEN','evidence_sha256':sha(doc)}))
    else:
        doc=args.verify.read_text(encoding='utf8').rstrip('\n')
        print(canonical(verify_v1a(doc,root)))

if __name__ == '__main__':
    main()
