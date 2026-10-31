"""A5d: source-based, branch-anchored, reproducible bounded release custody.

No physical security or hardware conformance is implied by file hashes.
Historical phase receipts are audited metadata, not new full phase replays.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import re
import subprocess

SCHEMA = 'spk-architecture-a5d-bounded-release-evidence/v1d'
RELEASE_TAG = 'spk-architecture-bounded-reference-v1'
BRANCH = 'spk-architecture-v1'
A5C_EVIDENCE = '60b8ab0d078257c64fabad9264c50df519e4fd6743b47eb17fba35538fea1aa7'
A5C_FILES = (
    'docs/spk-architecture-a5-adversarial-boundaries-v1c.md',
    'spk_architecture_v1/adversarial_boundaries_v1c.py',
    'search/spk_arch_a5c_adversarial_conformance_v1c.py',
    'search/spk_arch_a5c_final_gate_v1c.sh',
    'tests/test_spk_arch_a5c_adversarial_v1c.py',
    'tests/test_spk_arch_a5c_frozen_v1c.py',
)
RELEASE_FILES = (
    'docs/spk-architecture-a5-release-conformance-v1d.md',
    'spk_architecture_v1/release_conformance_v1d.py',
    'search/spk_arch_a5d_release_evidence_v1d.py',
    'search/spk_arch_a5d_final_gate_v1d.sh',
    'tests/test_spk_arch_a5d_release_v1d.py',
    'tests/test_spk_arch_a5d_frozen_v1d.py',
)


class ReleaseRejectedV1d(ValueError):
    pass


def _git(root, *args):
    p = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)
    if p.returncode:
        raise ReleaseRejectedV1d('Git release boundary denied: ' + ' '.join(args[:4]))
    return p.stdout.strip()


def _source_ok(root, path):
    p = root / path
    if not p.is_file() or p.is_symlink():
        raise ReleaseRejectedV1d('missing/linked release file: ' + path)
    raw = p.read_bytes()
    if (not raw.endswith(b'\n') or b'\r' in raw
            or any(line.endswith((b' ', b'\t')) for line in raw.splitlines())):
        raise ReleaseRejectedV1d('release file hygiene rejected: ' + path)
    return {'path': path, 'sha256': sha256(raw).hexdigest()}


def release_preflight_v1d(root):
    """Allows A5d to be untracked. All nineteen predecessors must be committed."""
    root = Path(root).resolve()
    from spk_architecture_v1.conformance_inventory_v1a import (
        PHASES, FROZEN_TAG, FROZEN_COMMIT, FROZEN_DIRS,
    )
    from search.spk_arch_a5b_conformance_v1b import A5A_FILES
    from search.spk_arch_a5c_adversarial_conformance_v1c import (
        A5B_FILES, predecessor_v1c,
    )
    prev = predecessor_v1c(root)
    if prev['predecessor_phases'] != 18 or prev['predecessor_files'] != 109:
        raise ReleaseRejectedV1d('unexpected predecessor history size')
    prior = tuple(p for _, files in PHASES.values() for p in files) + tuple(A5A_FILES) + tuple(A5B_FILES) + A5C_FILES
    if len(prior) != 115 or len(set(prior)) != 115:
        raise ReleaseRejectedV1d('release phase inventory collision')
    if len(RELEASE_FILES) != 6 or len(set(RELEASE_FILES)) != 6 or set(prior) & set(RELEASE_FILES):
        raise ReleaseRejectedV1d('release package file collision')
    if _git(root, 'branch', '--show-current') != BRANCH:
        raise ReleaseRejectedV1d('wrong release branch')
    if _git(root, 'rev-parse', FROZEN_TAG + '^{}') != FROZEN_COMMIT:
        raise ReleaseRejectedV1d('frozen simulator tag drift')
    _git(root, 'merge-base', '--is-ancestor', FROZEN_TAG, 'HEAD')
    _git(root, 'diff', '--quiet', FROZEN_TAG, 'HEAD', '--', *FROZEN_DIRS)
    _git(root, 'diff', '--quiet', '--', *FROZEN_DIRS)
    _git(root, 'diff', '--cached', '--quiet', '--', *FROZEN_DIRS)
    tracked = set(_git(root, 'ls-files').splitlines())
    if not set(prior).issubset(tracked):
        raise ReleaseRejectedV1d('uncommitted earlier phase')
    _git(root, 'diff', '--quiet', 'HEAD', '--', *prior)
    _git(root, 'diff', '--cached', '--quiet', '--', *prior)
    if (root / A5C_FILES[0]).read_text().count(A5C_EVIDENCE) != 1 or (
        'INTEGRATION PASS' not in (root / A5C_FILES[0]).read_text()
    ):
        raise ReleaseRejectedV1d('A5c certification missing')
    source = [_source_ok(root, p) for p in prior + RELEASE_FILES]
    if len(source) != 121:
        raise ReleaseRejectedV1d('incomplete release source inventory')
    hist = {key: digest for key, (digest, _) in PHASES.items()}
    hist.update(a5a='123040eeb3ce4d8025c141c79acd0ff7c58dde33379eeadcb840989982dcc0fa',
                a5b='0d1967732deb7429a11d15955d8cf1b1f23a1feafade61e1c28dc96eb26be07b',
                a5c=A5C_EVIDENCE)
    if len(hist) != 19 or any(not re.fullmatch('[0-9a-f]{64}', x) for x in hist.values()):
        raise ReleaseRejectedV1d('incomplete historical certification records')
    return {'frozen_commit': FROZEN_COMMIT, 'frozen_tag': FROZEN_TAG,
            'release_tag_to_create': RELEASE_TAG, 'branch': BRANCH,
            'head_commit': _git(root, 'rev-parse', 'HEAD'),
            'predecessor_phases':19, 'predecessor_files':115,
            'candidate_release_files':6, 'source_files':121,
            'historical_evidence_sha256':hist, 'files':source}


def release_committed_v1d(root):
    root = Path(root).resolve()
    result = release_preflight_v1d(root)
    tracked = set(_git(root, 'ls-files').splitlines())
    if not set(RELEASE_FILES).issubset(tracked):
        raise ReleaseRejectedV1d('A5d source is not committed')
    if _git(root, 'status', '--porcelain', '--untracked-files=all'):
        raise ReleaseRejectedV1d('release checkout must be clean and without untracked files')
    # An independently cloned checkout must agree with HEAD for all 121 files.
    for f in RELEASE_FILES:
        _git(root, 'diff', '--quiet', 'HEAD', '--', f)
    if _git(root, 'rev-parse', '--is-shallow-repository') != 'false':
        raise ReleaseRejectedV1d('shallow release clone not admitted')
    return result
