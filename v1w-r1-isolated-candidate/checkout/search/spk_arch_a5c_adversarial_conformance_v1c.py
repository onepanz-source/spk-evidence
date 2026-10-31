"""A5c independent adversarial execution/custody tests, source-pinned replay.

Fault matrix: forged event custody; context/epoch substitution; staged RUN;
failed VERIFY with irreversible FAULTED controller; fully recomputed false
snapshot, rejected by independently executed source transcript. Every check
runs on real A3d/A4a/A4d logic; it does not inject hostile host code.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a5a_conformance_v1a import sampled_indices_v1a
from search.spk_arch_a5b_conformance_v1b import predecessor_v1b
from spk_architecture_v1.conformance_inventory_v1a import CORPUS_SHA256
from spk_architecture_v1.adversarial_boundaries_v1c import adversarial_case_v1c
from spk_architecture_v1.pe_fabric_v1a import SCHEMES

SCHEMA='spk-architecture-a5c-adversarial-evidence/v1c'
A5B_EVIDENCE='0d1967732deb7429a11d15955d8cf1b1f23a1feafade61e1c28dc96eb26be07b'
A5B_FILES=(
    'docs/spk-architecture-a5-metamorphic-conformance-v1b.md',
    'spk_architecture_v1/metamorphic_v1b.py',
    'search/spk_arch_a5b_conformance_v1b.py',
    'search/spk_arch_a5b_final_gate_v1b.sh',
    'tests/test_spk_arch_a5b_metamorphic_v1b.py',
    'tests/test_spk_arch_a5b_frozen_v1b.py',
)


def predecessor_v1c(root):
    previous=predecessor_v1b(root)
    tracked=set(subprocess.check_output(['git','ls-files'],cwd=root,text=True).splitlines())
    if set(A5B_FILES)-tracked:
        raise ValueError('A5b predecessor is uncommitted')
    for f in A5B_FILES:
        if subprocess.run(['git','diff','--quiet','HEAD','--',f],cwd=root).returncode:
            raise ValueError('A5b predecessor source dirty: '+f)
    doc=(root/A5B_FILES[0]).read_text()
    if 'INTEGRATION PASS' not in doc or A5B_EVIDENCE not in doc:
        raise ValueError('A5b certificate missing from committed document')
    return {'predecessor_phases':previous['predecessor_phases']+1,
            'predecessor_files':previous['predecessor_files']+len(A5B_FILES),
            'a5b_recorded_evidence_sha256':A5B_EVIDENCE,
            'base_head_commit':subprocess.check_output(
                ['git','rev-parse','HEAD'],cwd=root,text=True).strip()}


def report_v1c(root):
    if catalog_fingerprint_v0()!=CORPUS_SHA256:
        raise AssertionError('frozen semantic corpus drift')
    provenance=predecessor_v1c(root)
    catalog=checked_catalog_v0()
    indices=frozenset(sampled_indices_v1a())
    if (len(catalog)!=216 or len(indices)!=36
            or tuple(SCHEMES)!=('single','split','spread')):
        raise AssertionError('bounded adversarial domain drift')
    rows=[adversarial_case_v1c(cid,case,scheme,deep=i in indices)
          for i,(cid,case) in enumerate(catalog) for scheme in SCHEMES]
    if (len(rows)!=648
            or len({(r['id'],r['scheme']) for r in rows})!=648
            or sum(r['deep_checkpoint_sha256'] is not None for r in rows)!=108
            or not all(r['cross_context_denied'] and r['staging_execution_denied']
                        and r['failed_verify_faulted'] and r['forged_custody_denied']
                       for r in rows)):
        raise AssertionError('incomplete A5c adversarial campaign')
    return {'schema':SCHEMA,'source_sha256':CORPUS_SHA256,
            'source_cases':216,'placements':3,
            'adversarial_runs':648,'cross_context_denials':648,
            'staging_execution_denials':648,'failed_replay_faults':648,
            'event_custody_tamper_denials':648,
            'fully_rehashed_snapshot_replay_denials':108,
            'remote_occurrences':sum(r['remote_occurrences'] for r in rows),
            'predecessor':provenance,'rows':rows,
            'limitations':[
                'trusted in-process controller, not security against hostile Python code',
                'recovery checks full replay from original inputs, not live checkpoint continuation',
                'injected denial is bounded logical corruption, not a physical fault injection',
                'full-host crash, distributed failure, and durable recovery are not certified',
                'historic gate digests are metadata, not freshly rerun signatures',
            ]}


def seal_v1c(root):
    payload=report_v1c(root)
    return canonical({'schema':SCHEMA,'payload':payload,
                      'payload_sha256':sha(SCHEMA+'\n'+canonical(payload))})


def verify_v1c(document,root):
    obj=strict_json(document)
    if (type(obj) is not dict or set(obj)!={'schema','payload','payload_sha256'}
            or obj['schema']!=SCHEMA or canonical(obj)!=document):
        raise ValueError('noncanonical A5c evidence')
    if obj['payload_sha256']!=sha(SCHEMA+'\n'+canonical(obj['payload'])):
        raise ValueError('A5c evidence checksum mismatch')
    if obj['payload']!=report_v1c(root):
        raise ValueError('A5c independent replay mismatch')
    p=obj['payload']
    return {'status':'PASS','source_cases':p['source_cases'],
            'adversarial_runs':p['adversarial_runs'],
            'cross_context_denials':p['cross_context_denials'],
            'staging_execution_denials':p['staging_execution_denials'],
            'failed_replay_faults':p['failed_replay_faults'],
            'event_custody_tamper_denials':p['event_custody_tamper_denials'],
            'fully_rehashed_snapshot_replay_denials':p['fully_rehashed_snapshot_replay_denials'],
            'predecessor_phases':p['predecessor']['predecessor_phases'],
            'evidence_sha256':sha(document)}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    modes=p.add_mutually_exclusive_group(required=True)
    modes.add_argument('--write',type=Path)
    modes.add_argument('--verify',type=Path)
    args=p.parse_args(argv)
    root=Path(__file__).resolve().parents[1]
    if args.write:
        document=seal_v1c(root)
        args.write.write_text(document+'\n',encoding='utf8')
        print(canonical({'status':'WRITTEN','evidence_sha256':sha(document)}))
    else:
        document=args.verify.read_text(encoding='utf8').rstrip('\n')
        print(canonical(verify_v1c(document,root)))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
