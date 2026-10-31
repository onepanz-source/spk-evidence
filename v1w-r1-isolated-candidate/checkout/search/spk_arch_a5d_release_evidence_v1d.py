"""A5d canonical release attestation: pinned source + fresh cross-system replay.

Must be generated and verified from two separate clean Git clones of the
candidate release commit, not a dirty or untracked worktree.
"""
from __future__ import annotations
import argparse
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a5a_conformance_v1a import sampled_indices_v1a, cross_witness_v1a
from search.spk_arch_a5b_conformance_v1b import metamorphic_case_v1b
from spk_architecture_v1.adversarial_boundaries_v1c import adversarial_case_v1c
from spk_architecture_v1.pe_fabric_v1a import SCHEMES
from spk_architecture_v1.conformance_inventory_v1a import CORPUS_SHA256
from spk_architecture_v1.release_conformance_v1d import (
    SCHEMA, release_committed_v1d, release_preflight_v1d,
)


def report_v1d(root):
    history = release_committed_v1d(root)
    if catalog_fingerprint_v0() != CORPUS_SHA256:
        raise AssertionError('A5d frozen semantic corpus mismatch')
    catalog = checked_catalog_v0()
    indices = sampled_indices_v1a()
    if (len(catalog) != 216 or len(indices) != 36 or len(set(indices)) != 36
            or tuple(SCHEMES) != ('single', 'split', 'spread')):
        raise AssertionError('A5d stratified architecture domain mismatch')
    rows = []
    for i in indices:
        cid, case = catalog[i]
        for scheme in SCHEMES:
            vertical = cross_witness_v1a(catalog, i, scheme)
            metamorphic = metamorphic_case_v1b(cid, case, scheme)
            adversarial = adversarial_case_v1c(cid, case, scheme)
            if (vertical['id'] != metamorphic['id'] or vertical['id'] != adversarial['id']
                    or vertical['scheme'] != scheme or metamorphic['scheme'] != scheme
                    or not adversarial['cross_context_denied']
                    or not adversarial['forged_custody_denied']
                    or not adversarial['failed_verify_faulted']
                    or metamorphic['original_context_sha256'] == metamorphic['renamed_context_sha256']):
                raise AssertionError('A5d release witness boundary mismatch')
            rows.append({'source_id': cid, 'scheme':scheme,
                         'vertical_sha256':sha(canonical(vertical)),
                         'metamorphic_sha256':sha(canonical(metamorphic)),
                         'adversarial_sha256':sha(canonical(adversarial))})
    if len(rows) != 108 or len({(x['source_id'], x['scheme']) for x in rows}) != 108:
        raise AssertionError('A5d cross-system source coverage mismatch')
    return {'schema':SCHEMA, 'source_sha256':CORPUS_SHA256,
            'release':history, 'sampled_cases':36, 'placements':3,
            'fresh_vertical_witnesses':108, 'fresh_metamorphic_witnesses':108,
            'fresh_adversarial_witnesses':108, 'rows':rows,
            'scope':[
                'software bounded reference, not a physical neuromorphic chip',
                'historic 19 gate digests are recorded certificates, not new exhaustive replay',
                'global deterministic scheduler and trusted in-process control only',
                'no asynchronous crash recovery, hot state migration or distributed clock',
                'no hostile-code security claim or hardware timing guarantee',
            ]}


def seal_v1d(root):
    payload = report_v1d(root)
    return canonical({'schema':SCHEMA,'payload':payload,
                      'payload_sha256':sha(SCHEMA+'\n'+canonical(payload))})


def verify_v1d(document,root):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema','payload','payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A5d release evidence')
    if obj['payload_sha256'] != sha(SCHEMA+'\n'+canonical(obj['payload'])):
        raise ValueError('A5d release evidence checksum mismatch')
    if obj['payload'] != report_v1d(root):
        raise ValueError('A5d independent checkout replay mismatch')
    p = obj['payload']
    return {'status':'PASS', 'release_commit':p['release']['head_commit'],
            'predecessor_phases':p['release']['predecessor_phases'],
            'source_files':p['release']['source_files'],
            'fresh_cross_layer_witnesses':len(p['rows']),
            'evidence_sha256':sha(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--preflight', action='store_true')
    modes.add_argument('--write', type=Path)
    modes.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    if args.preflight:
        inventory = release_preflight_v1d(root)
        print(canonical({'status':'PREFLIGHT_PASS', 'predecessor_phases':19,
                         'source_files':inventory['source_files'],
                         'candidate_files':6}))
    elif args.write:
        doc = seal_v1d(root)
        args.write.write_text(doc+'\n',encoding='utf8')
        print(canonical({'status':'WRITTEN', 'evidence_sha256':sha(doc)}))
    else:
        doc = args.verify.read_text(encoding='utf8').rstrip('\n')
        print(canonical(verify_v1d(doc,root)))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
