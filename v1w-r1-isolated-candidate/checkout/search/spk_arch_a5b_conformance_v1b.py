"""A5b cross-system metamorphic conformance over the frozen 216x3 domain.

Properties: alpha-renaming of PE IDs; expansion of *nonbinding* capacity;
remote-link parameter irrelevance on single-PE placement; exact delivery and
source accounting under finite causal congestion. Capacity growth from an
already bottlenecked system is NOT presumed to preserve spike timing.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
from pathlib import Path
import subprocess

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a4c_candidate_conformance_v1c import args_v1c
from spk_architecture_v1.pe_fabric_v1a import SCHEMES
from spk_architecture_v1.causal_transport_v1d import (
    CausalLinkPlanV1d, execute_causal_transport_v1d,
)
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
from spk_architecture_v1.operating_modes_v1a import context_fingerprint_v1a
from spk_architecture_v1.metamorphic_v1b import alpha_rename_v1b, normalize_pe_names_v1b
from spk_architecture_v1.conformance_inventory_v1a import CORPUS_SHA256, manifest_v1a

SCHEMA = 'spk-architecture-a5b-metamorphic-evidence/v1b'
A5A_EVIDENCE = '123040eeb3ce4d8025c141c79acd0ff7c58dde33379eeadcb840989982dcc0fa'
A5A_FILES = (
    'docs/spk-architecture-a5-vertical-conformance-v1a.md',
    'spk_architecture_v1/conformance_inventory_v1a.py',
    'search/spk_arch_a5a_conformance_v1a.py',
    'search/spk_arch_a5a_final_gate_v1a.sh',
    'tests/test_spk_arch_a5a_inventory_v1a.py',
    'tests/test_spk_arch_a5a_frozen_v1a.py',
)


def predecessor_v1b(root):
    """Source custody: A5a committed, clean, recorded as historical gate."""
    manifest = manifest_v1a(root)
    tracked = set(subprocess.check_output(['git', 'ls-files'], cwd=root, text=True).splitlines())
    if set(A5A_FILES) - tracked:
        raise ValueError('A5a predecessor is not committed')
    for path in A5A_FILES:
        if subprocess.run(['git','diff','--quiet','HEAD','--',path],cwd=root).returncode:
            raise ValueError('A5a predecessor source changed: '+path)
    doc = (root / A5A_FILES[0]).read_text()
    if 'INTEGRATION PASS' not in doc or A5A_EVIDENCE not in doc:
        raise ValueError('A5a historical acceptance not recorded in committed document')
    return {'predecessor_phases': manifest['phase_count']+1,
            'predecessor_files': manifest['tracked_source_files']+len(A5A_FILES),
            'a5a_recorded_evidence_sha256': A5A_EVIDENCE,
            'base_head_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()}


def ideal_args_v1b(case, scheme, quota):
    """Two manifestly nonbinding resource profiles for the bounded corpus."""
    original = args_v1c(case, scheme)
    fabric = original[1]
    return (case, fabric, original[2],
            uniform_causal_service_plan_v1b(fabric, pe_slots=quota,
                                             fabric_slots_per_tick=quota),
            uniform_causal_memory_plan_v1c(fabric, pe_slots=quota,
                          domain_slots=quota, fabric_slots_per_tick=quota),
            CausalLinkPlanV1d(quota,quota,quota,4096))


def conservation_v1b(output, external_count):
    """Preserve *actual* events and transport occurrences, not ideal emissions."""
    result, routed = output['result'], output['transport']
    remote = routed['cross_pe_occurrences']
    if (result['processed_events'] != external_count + len(routed['transfers'])
            or remote != routed['delivered_cross_pe_occurrences']
            or remote != len(routed['link_grants'])
            or routed['outstanding_outbox_occurrences'] != 0
            or routed['remaining_inflight_occurrences'] != 0):
        raise AssertionError('A5b lost, duplicated or left causal event occurrences')
    return remote


def metamorphic_case_v1b(cid, case, scheme):
    args = args_v1c(case, scheme)
    original = execute_causal_transport_v1d(*args)
    renamed_args, mapping = alpha_rename_v1b(args)
    renamed = execute_causal_transport_v1d(*renamed_args)
    if canonical(original) != canonical(normalize_pe_names_v1b(renamed, mapping)):
        raise AssertionError('A5b PE alpha-renaming changed full execution: '+cid+'/'+scheme)
    original_context = context_fingerprint_v1a(*args)
    renamed_context = context_fingerprint_v1a(*renamed_args)
    if original_context == renamed_context:
        raise AssertionError('A5b PE renaming did not change context authority digest')

    first_args = ideal_args_v1b(case, scheme, 256)
    second_args = ideal_args_v1b(case, scheme, 1024)
    first = execute_causal_transport_v1d(*first_args)
    second = execute_causal_transport_v1d(*second_args)
    if (canonical(first['result']) != canonical(second['result'])
            or canonical(first['transport']['transfers']) !=
               canonical(second['transport']['transfers'])
            or first['transport']['link_congestion_wait_ticks'] != 0
            or second['transport']['link_congestion_wait_ticks'] != 0):
        raise AssertionError('A5b nonbinding resource expansion drift: '+cid+'/'+scheme)
    original_remote=conservation_v1b(original, len(case.events))
    conservation_v1b(first, len(case.events))
    conservation_v1b(second, len(case.events))

    inert = None
    if scheme == 'single':
        single_variant = (args[0], args[1], TransportPlanV1a(9,1),
                          args[3], args[4], CausalLinkPlanV1d(1,1,128,4096))
        alternate = execute_causal_transport_v1d(*single_variant)
        if (canonical(original['result']) != canonical(alternate['result'])
                or alternate['transport']['link_grants']
                or conservation_v1b(alternate,len(case.events)) != 0):
            raise AssertionError('A5b all-local network affected by remote links: '+cid)
        inert = sha(canonical(alternate['result']))
    return {'id':cid,'scheme':scheme,
            'original_result_sha256': sha(canonical(original['result'])),
            'renamed_full_result_sha256': sha(canonical(normalize_pe_names_v1b(renamed,mapping))),
            'original_full_result_sha256': sha(canonical(original)),
            'nonbinding_result_sha256': sha(canonical(first['result'])),
            'nonbinding_expanded_result_sha256': sha(canonical(second['result'])),
            'original_context_sha256': original_context,
            'renamed_context_sha256': renamed_context,
            'remote_occurrences': original_remote,
            'single_remote_inert_result_sha256': inert}


def report_v1b(root):
    if catalog_fingerprint_v0()!=CORPUS_SHA256:
        raise AssertionError('frozen A5b source corpus drift')
    provenance=predecessor_v1b(root)
    catalog=checked_catalog_v0()
    if len(catalog)!=216 or tuple(SCHEMES)!=('single','split','spread'):
        raise AssertionError('unexpected metamorphic source/placement domain')
    rows=[metamorphic_case_v1b(cid,case,scheme) for cid,case in catalog for scheme in SCHEMES]
    if (len(rows)!=648 or len({(r['id'],r['scheme']) for r in rows})!=648
            or sum(r['scheme']=='single' for r in rows)!=216):
        raise AssertionError('A5b incomplete metamorphic coverage')
    return {'schema':SCHEMA,'corpus_sha256':CORPUS_SHA256,
            'source_cases':216,'placements':3,'metamorphic_witnesses':648,
            'alpha_rename_witnesses':648,'nonbinding_expansion_witnesses':648,
            'single_pe_remote_inert_witnesses':216,
            'cross_pe_occurrences':sum(r['remote_occurrences'] for r in rows),
            'predecessor':provenance,'rows':rows,
            'limitations':[
                'PE renaming preserves ordering; arbitrary arbitration order changes are not inferred invariant',
                'nonbinding quota equivalence does NOT imply monotonic spike results under saturated quotas',
                'remote link irrelevance applies only to all-local single-PE placements',
                'conservation applies to actual dynamically generated and delivered events',
                'physical NoC, durable recovery, distributed clocks and hostile-code security out of scope',
            ]}


def seal_v1b(root):
    payload=report_v1b(root)
    return canonical({'schema':SCHEMA,'payload':payload,
                      'payload_sha256':sha(SCHEMA+'\n'+canonical(payload))})


def verify_v1b(document,root):
    obj=strict_json(document)
    if (type(obj) is not dict or set(obj)!={'schema','payload','payload_sha256'}
            or obj['schema']!=SCHEMA or canonical(obj)!=document):
        raise ValueError('noncanonical A5b evidence')
    if obj['payload_sha256']!=sha(SCHEMA+'\n'+canonical(obj['payload'])):
        raise ValueError('A5b evidence checksum mismatch')
    if obj['payload']!=report_v1b(root):
        raise ValueError('A5b independent replay mismatch')
    payload=obj['payload']
    return {'status':'PASS','source_cases':payload['source_cases'],
            'metamorphic_witnesses':payload['metamorphic_witnesses'],
            'nonbinding_expansion_witnesses':payload['nonbinding_expansion_witnesses'],
            'single_pe_remote_inert_witnesses':payload['single_pe_remote_inert_witnesses'],
            'cross_pe_occurrences':payload['cross_pe_occurrences'],
            'predecessor_phases':payload['predecessor']['predecessor_phases'],
            'evidence_sha256':sha(document)}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--write',type=Path)
    group.add_argument('--verify',type=Path)
    a=p.parse_args(argv)
    root=Path(__file__).resolve().parents[1]
    if a.write:
        doc=seal_v1b(root)
        a.write.write_text(doc+'\n',encoding='utf8')
        print(canonical({'status':'WRITTEN','evidence_sha256':sha(doc)}))
    else:
        print(canonical(verify_v1b(a.verify.read_text(encoding='utf8').rstrip('\n'),root)))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
