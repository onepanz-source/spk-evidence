"""A5a: source-pinned architectural inventory and Git custody of A1-A4.

This audit checks tracked source, frozen ancestry, module/receipt inventory and
prior certification strings. It does NOT re-run all 16 prior evidence reports.
A5a's independent cross-layer execution witness is in its conformance runner.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import re
import subprocess

FROZEN_TAG = 'spk-simulator-bounded-reference-v0'
FROZEN_COMMIT = 'a76ebaae49373a4c6b66f94465d78dbf1cf19f80'
FROZEN_DIRS = ('spk_core', 'spk_network', 'spk_compiler', 'spk_simulator', 'spk_architecture')
ARCH_BRANCH = 'spk-architecture-v1'
CORPUS_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
PHASES = {
    'a1a': ('3b650178521e2df512b5ebf86f8d49ae33ce6a4f96ff002ea3a7b8d6b515c5ee', ('docs/spk-architecture-a1-pe-fabric-v1a.md', 'search/spk_arch_a1_final_gate_v1a.sh', 'search/spk_arch_a1_pe_fabric_v1a.py', 'spk_architecture_v1/__init__.py', 'spk_architecture_v1/pe_fabric_v1a.py', 'tests/test_spk_arch_a1_frozen_integration_v1a.py', 'tests/test_spk_arch_a1_pe_fabric_v1a.py')),
    'a1b': ('cecf79b4156cd863940e5bbf8b3b33f004ec27a01faf9dc019f16c75971b8128', ('docs/spk-architecture-a1-pe-local-execution-v1b.md', 'search/spk_arch_a1b_final_gate_v1b.sh', 'search/spk_arch_a1b_pe_local_v1b.py', 'spk_architecture_v1/pe_execution_v1b.py', 'tests/test_spk_arch_a1b_frozen_integration_v1b.py', 'tests/test_spk_arch_a1b_pe_execution_v1b.py')),
    'a1c': ('9e35bef1a9c7f8b4db89831fdeeb79098f3072618d791cdb02b809eae23a7082', ('docs/spk-architecture-a1-pe-service-arbitration-v1c.md', 'search/spk_arch_a1c_final_gate_v1c.sh', 'search/spk_arch_a1c_service_conformance_v1c.py', 'spk_architecture_v1/pe_service_v1c.py', 'tests/test_spk_arch_a1c_frozen_service_v1c.py', 'tests/test_spk_arch_a1c_service_v1c.py')),
    'a1d': ('96c36f0306c044dee5a73d7c5c372ac2569e99fb1428cd40f4e6075dd1a4104f', ('docs/spk-architecture-a1-pe-failstop-v1d.md', 'search/spk_arch_a1d_fault_conformance_v1d.py', 'search/spk_arch_a1d_final_gate_v1d.sh', 'spk_architecture_v1/pe_fault_v1d.py', 'tests/test_spk_arch_a1d_failstop_v1d.py', 'tests/test_spk_arch_a1d_frozen_conformance_v1d.py')),
    'a2a': ('c7164a8abdf27e747f3522ec29b0449574aee219ab525b7f9cc1aff4acc80082', ('docs/spk-architecture-a2-memory-domains-v1a.md', 'search/spk_arch_a2a_final_gate_v1a.sh', 'search/spk_arch_a2a_memory_conformance_v1a.py', 'spk_architecture_v1/memory_projection_v1a.py', 'tests/test_spk_arch_a2a_frozen_v1a.py', 'tests/test_spk_arch_a2a_memory_v1a.py')),
    'a2b': ('22564bbdde8c5a3e1a358735498eb274d3e6c4eee3f1cbcc358a0b1a31bebacc', ('docs/spk-architecture-a2-memory-access-v1b.md', 'search/spk_arch_a2b_access_conformance_v1b.py', 'search/spk_arch_a2b_final_gate_v1b.sh', 'spk_architecture_v1/memory_access_v1b.py', 'tests/test_spk_arch_a2b_access_v1b.py', 'tests/test_spk_arch_a2b_frozen_v1b.py')),
    'a2c': ('2edce982d5a543d4a2342356fd6649ae4fcc549326b13ee28520b8f98d777140', ('docs/spk-architecture-a2-memory-service-v1c.md', 'search/spk_arch_a2c_final_gate_v1c.sh', 'search/spk_arch_a2c_memory_service_conformance_v1c.py', 'spk_architecture_v1/memory_service_v1c.py', 'tests/test_spk_arch_a2c_frozen_v1c.py', 'tests/test_spk_arch_a2c_memory_service_v1c.py')),
    'a2d': ('91d118030af6540bf7261f4dcb547f9edd30a4fd865ae49233544c51a08e13be', ('docs/spk-architecture-a2-memory-exhaustion-v1d.md', 'search/spk_arch_a2d_exhaustion_conformance_v1d.py', 'search/spk_arch_a2d_final_gate_v1d.sh', 'spk_architecture_v1/memory_exhaustion_v1d.py', 'tests/test_spk_arch_a2d_frozen_v1d.py', 'tests/test_spk_arch_a2d_memory_exhaustion_v1d.py')),
    'a3a': ('a8f94d1d729d0dfad728457e046fcac4d7110319ceea2156f0c224254b19f1f2', ('docs/spk-architecture-a3-causal-transport-v1a.md', 'search/spk_arch_a3a_final_gate_v1a.sh', 'search/spk_arch_a3a_temporal_conformance_v1a.py', 'spk_architecture_v1/temporal_transport_v1a.py', 'tests/test_spk_arch_a3a_frozen_v1a.py', 'tests/test_spk_arch_a3a_temporal_transport_v1a.py')),
    'a3b': ('b3fec71b9e54b7adff4cbe2b89f28fff774c62aba56d5bceade3ecc48f6b0891', ('docs/spk-architecture-a3-causal-service-v1b.md', 'search/spk_arch_a3b_causal_service_conformance_v1b.py', 'search/spk_arch_a3b_final_gate_v1b.sh', 'spk_architecture_v1/temporal_service_v1b.py', 'tests/test_spk_arch_a3b_causal_service_v1b.py', 'tests/test_spk_arch_a3b_frozen_v1b.py')),
    'a3c': ('47879a87837f19cd1b7994eb471c64cbb2ad5eb958c6c96f9fef5df39141c662', ('docs/spk-architecture-a3-causal-memory-v1c.md', 'search/spk_arch_a3c_final_gate_v1c.sh', 'search/spk_arch_a3c_memory_timing_conformance_v1c.py', 'spk_architecture_v1/causal_memory_v1c.py', 'tests/test_spk_arch_a3c_causal_memory_v1c.py', 'tests/test_spk_arch_a3c_frozen_v1c.py')),
    'a3d': ('38ad466b0eea78f83118498519069452cad934e5c0fa695128bf83e15372bdac', ('docs/spk-architecture-a3-causal-backpressure-v1d.md', 'search/spk_arch_a3d_final_gate_v1d.sh', 'search/spk_arch_a3d_link_conformance_v1d.py', 'spk_architecture_v1/causal_transport_v1d.py', 'tests/test_spk_arch_a3d_frozen_v1d.py', 'tests/test_spk_arch_a3d_link_backpressure_v1d.py')),
    'a4a': ('2bd988fe55ee7092553620c7a133cc457751816c194baad6e47da30f4339d505', ('docs/spk-architecture-a4-operating-modes-v1a.md', 'search/spk_arch_a4a_final_gate_v1a.sh', 'search/spk_arch_a4a_mode_conformance_v1a.py', 'spk_architecture_v1/operating_modes_v1a.py', 'tests/test_spk_arch_a4a_frozen_v1a.py', 'tests/test_spk_arch_a4a_operating_modes_v1a.py')),
    'a4b': ('f6960f1af5d335d97072dc8ac90299637f392bb81011c9a24ebe3c2266348df8', ('docs/spk-architecture-a4-mode-memory-v1b.md', 'search/spk_arch_a4b_final_gate_v1b.sh', 'search/spk_arch_a4b_mode_memory_conformance_v1b.py', 'spk_architecture_v1/mode_memory_v1b.py', 'tests/test_spk_arch_a4b_frozen_v1b.py', 'tests/test_spk_arch_a4b_mode_memory_v1b.py')),
    'a4c': ('29703896c4861f4905f1847a58157110a0eaa8144ae7aec14aebd83e0ecfd739', ('docs/spk-architecture-a4-candidate-promotion-v1c.md', 'search/spk_arch_a4c_candidate_conformance_v1c.py', 'search/spk_arch_a4c_final_gate_v1c.sh', 'spk_architecture_v1/candidate_promotion_v1c.py', 'tests/test_spk_arch_a4c_candidate_promotion_v1c.py', 'tests/test_spk_arch_a4c_frozen_v1c.py')),
    'a4d': ('8b4ada449fa0521dc9b3045776c36183a7d5fa7f14156d21d2b6815a0e4d91d5', ('docs/spk-architecture-a4-state-custody-v1d.md', 'search/spk_arch_a4d_custody_conformance_v1d.py', 'search/spk_arch_a4d_final_gate_v1d.sh', 'spk_architecture_v1/state_custody_v1d.py', 'tests/test_spk_arch_a4d_frozen_v1d.py', 'tests/test_spk_arch_a4d_state_custody_v1d.py')),
}

class InventoryRejectedV1a(ValueError):
    pass


def _git(root, *args):
    p = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)
    if p.returncode:
        raise InventoryRejectedV1a('Git boundary refused: ' + ' '.join(args[:3]))
    return p.stdout.strip()


def manifest_v1a(root):
    """Canonical committed-file inventory; reject uncommitted predecessor mutation."""
    root = Path(root).resolve()
    if not (root / '.git').exists():
        # Worktrees can use a .git text file; no faked non-Git release root.
        raise InventoryRejectedV1a('missing worktree Git custody')
    if _git(root, 'branch', '--show-current') != ARCH_BRANCH:
        raise InventoryRejectedV1a('incorrect architecture branch')
    if _git(root, 'rev-parse', FROZEN_TAG + '^{}') != FROZEN_COMMIT:
        raise InventoryRejectedV1a('frozen annotated tag moved')
    if _git(root, 'cat-file', '-t', 'refs/tags/' + FROZEN_TAG) != 'tag':
        raise InventoryRejectedV1a('baseline must be annotated tag')
    _git(root, 'merge-base', '--is-ancestor', FROZEN_TAG, 'HEAD')
    _git(root, 'diff', '--quiet', FROZEN_TAG, 'HEAD', '--', *FROZEN_DIRS)
    _git(root, 'diff', '--quiet', '--', *FROZEN_DIRS)
    _git(root, 'diff', '--cached', '--quiet', '--', *FROZEN_DIRS)
    if tuple(PHASES) != tuple(
            f'a{i}{c}' for i in range(1, 5) for c in 'abcd'):
        raise InventoryRejectedV1a('incomplete phase manifest')
    expected = [f for _, files in PHASES.values() for f in files]
    if len(expected) != 97 or len(set(expected)) != len(expected):
        raise InventoryRejectedV1a('missing/duplicate predecessor files')
    tracked = set(_git(root, 'ls-files').splitlines())
    if set(expected) - tracked:
        raise InventoryRejectedV1a('uncommitted or missing predecessor file')
    _git(root, 'diff', '--quiet', 'HEAD', '--', *expected)
    _git(root, 'diff', '--cached', '--quiet', '--', *expected)
    result=[]
    for phase, (digest, files) in PHASES.items():
        if not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise InventoryRejectedV1a('bad historical receipt digest')
        phase_rows = []
        for f in files:
            data = (root / f).read_bytes()
            if (not data.endswith(b'\n') or b'\r' in data or any(
                    x.endswith((b' ',b'\t')) for x in data.splitlines())):
                raise InventoryRejectedV1a('dirty predecessor source: '+f)
            phase_rows.append({'path': f, 'sha256': sha256(data).hexdigest()})
        doc_paths = [f for f in files if f.startswith('docs/')]
        if len(doc_paths) != 1 or 'INTEGRATION PASS' not in (root / doc_paths[0]).read_text():
            raise InventoryRejectedV1a('uncertified predecessor documentation: '+phase)
        if digest not in (root / doc_paths[0]).read_text():
            raise InventoryRejectedV1a('missing recorded historical gate evidence: '+phase)
        result.append({'phase': phase, 'reported_gate_evidence_sha256': digest,
                       'files': phase_rows})
    return {'schema': 'spk-architecture-a5a-inventory/v1a',
            'frozen_tag': FROZEN_TAG, 'frozen_commit': FROZEN_COMMIT,
            'head_commit': _git(root, 'rev-parse', 'HEAD'),
            'phase_count': len(result), 'tracked_source_files': len(expected),
            'phases': result}
