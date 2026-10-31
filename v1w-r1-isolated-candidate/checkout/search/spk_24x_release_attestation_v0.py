"""SPK 24x: source-pinned bounded simulator release-candidate attestation.

This is an audit, not a new evaluator or scheduler. SHA-256 proves local
byte-level reproducibility, not signature/authenticity. Does not create tags.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

SCHEMA = 'spk-simulator-bounded-release-candidate/v0'
BASELINE_SUBJECT = 'checkpoint: SPK structural metamorphic conformance v0'
RELEASE_SUBJECT = 'checkpoint: SPK bounded simulator release candidate v0'
RELEASE_FILES = frozenset({
    'docs/spk-24x-bounded-release-candidate-v0.md',
    'search/spk_24x_release_attestation_v0.py',
    'search/spk_24x_final_gate_v0.sh',
    'tests/test_spk_24x_release_attestation_v0.py',
})
FREEZE_TAGS = {
    'spk-core-network-v0': ('spk_core', 'spk_network'),
    'spk-compiler-v0': ('spk_compiler',),
}
ALLOWED_UNTRACKED = frozenset({
    'search/core_temporal_depth5_v1.py',
    'search/core_temporal_quotient_alignment_v0.py',
    'spk_24d_collect.py',
    'docs/spk-24x-bounded-release-candidate-v0.md',
    'search/spk_24x_release_attestation_v0.py',
    'search/spk_24x_final_gate_v0.sh',
    'tests/test_spk_24x_release_attestation_v0.py',
})
REQUIRED_TRACKED = (
    'docs/spk-24u-cross-layer-conformance-v0.md',
    'docs/spk-24v-negative-admission-observer-fault-v0.md',
    'docs/spk-24w-structural-metamorphic-conformance-v0.md',
    'search/spk_24u_cross_layer_v0.py',
    'search/spk_24v_negative_conformance_v0.py',
    'search/spk_24w_cross_layer_metamorphic_v0.py',
    'search/spk_24t_diagnostic_manifest_host_v0.py',
    'tests/test_spk_24u_cross_layer_v0.py',
    'tests/test_spk_24v_frozen_negative_v0.py',
    'tests/test_spk_24w_frozen_metamorphic_v0.py',
)
# These are independently reported authoritative fwork evidence fingerprints.
EVIDENCE = {
    '24u': {
        'scope': '216 compiled three-node programs, 408 host runs',
        'sha256': 'e2ce01b440d019c0b33316c67858102310d889c92d71faa04a5e873540119099',
    },
    '24v': {
        'scope': '1512 admission rejections and bounded observer injections',
        'sha256': 'a5f23f7cf402bbc8289cb04d56ec0d66784bb4b713799da94b69c85ee0b4da3e',
    },
    '24w': {
        'scope': '648 compiled graph-isomorphism metamorphic runs',
        'sha256': '1e620306cad44da0f3b1d289a68fab751dc759e1ae243c97ff352354f2ca9e98',
    },
}
CORPUS_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
PLAN_W_SHA256 = '91dda6289f29b38a12a7672c36169003c3eddc27ff3d4b8abfd923d9f0565d0f'
EXPLICIT_GAPS = (
    'no arbitrary graph / cyclic-network equivalence',
    'no arbitrary observer sandboxing or callback recovery',
    'no durable exactly-once execution / signed receipts',
    'no PE contention or distributed scheduling invariance',
    'no learning or generalized liveness guarantees',
    'no universal Core semantic equivalence',
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(text):
    return sha256(text.encode('utf-8')).hexdigest()


def _git(repo: Path, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False)
    if result.returncode:
        raise ValueError('git ' + ' '.join(args[:2]) + ': ' + result.stderr.strip()[:260])
    return result.stdout.rstrip('\n')


def _baseline_commit_v0(repo: Path):
    """Return the attested 24w commit before OR after the exact 24x commit.

    After the release-candidate commit, permit only a direct child of 24w
    that adds precisely the four reviewed 24x files. No later HEAD qualifies.
    """
    subject = _git(repo, 'log', '-1', '--format=%s')
    head = _git(repo, 'rev-parse', 'HEAD')
    if subject == BASELINE_SUBJECT:
        return head
    if subject != RELEASE_SUBJECT:
        raise ValueError('24w accepted HEAD or exact 24x commit required')
    parent = _git(repo, 'rev-parse', 'HEAD^')
    if _git(repo, 'log', '-1', '--format=%s', parent) != BASELINE_SUBJECT:
        raise ValueError('release candidate must immediately follow 24w')
    changes = _git(repo, 'diff', '--name-status', parent, head).splitlines()
    expected = {'A\t' + name for name in RELEASE_FILES}
    if set(changes) != expected or len(changes) != len(expected):
        raise ValueError('release candidate changed unexpected paths')
    return parent


def assert_release_workspace_v0(repo: Path):
    """Fail closed on modified tracked files, staging, tags and unexpected files."""
    repo = Path(repo).resolve()
    if not (repo / '.git').exists():
        raise ValueError('release requires a Git checkout')
    _baseline_commit_v0(repo)
    if _git(repo, 'diff', '--name-only') or _git(repo, 'diff', '--cached', '--name-only'):
        raise ValueError('tracked/staged changes forbidden before candidate gate')
    if _git(repo, 'status', '--porcelain', '--untracked-files=all'):
        # read -z exactly to support filenames with spaces; reject aliases.
        r = subprocess.run(['git', '-C', str(repo), 'ls-files', '--others', '--exclude-standard', '-z'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        others = {x.decode('utf-8') for x in r.stdout.split(b'\0') if x}
        unexpected = others - ALLOWED_UNTRACKED
        if unexpected:
            raise ValueError('unexpected untracked sources: ' + repr(sorted(unexpected)))
    for path in REQUIRED_TRACKED:
        if path not in _git(repo, 'ls-files', '--full-name', '--', path).splitlines():
            raise ValueError('required 24u/v/w source missing from Git: ' + path)
    for tag, paths in FREEZE_TAGS.items():
        if not _git(repo, 'cat-file', '-t', 'refs/tags/' + tag) == 'tag':
            raise ValueError('annotated frozen tag required: ' + tag)
        if _git(repo, 'diff', '--name-only', tag, 'HEAD', '--', *paths):
            raise ValueError('frozen source drift since ' + tag)
    return repo


def source_identity_v0():
    """Pure independent fixture pins; no frozen engine is invoked."""
    from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0, catalog_v0
    from search.spk_24w_metamorphic_plan_v0 import identity_v0, plan_v0
    corpus = catalog_v0()
    if len(corpus) != 216 or catalog_fingerprint_v0() != CORPUS_SHA256:
        raise ValueError('source 24o corpus drift')
    if len(plan_v0()) != 648 or identity_v0() != PLAN_W_SHA256:
        raise ValueError('structural metamorphism plan drift')
    return {'corpus_sha256': CORPUS_SHA256, 'source_cases': 216,
            'structural_plan_sha256': PLAN_W_SHA256, 'structural_variants': 648}


def release_record_v0(repo: Path):
    repo = assert_release_workspace_v0(repo)
    sources = source_identity_v0()
    commit = _baseline_commit_v0(repo)
    tags = {t: _git(repo, 'rev-parse', t + '^{}') for t in sorted(FREEZE_TAGS)}
    files = {path: sha256((repo / path).read_bytes()).hexdigest()
             for path in REQUIRED_TRACKED}
    return {'schema': SCHEMA, 'baseline_commit': commit,
            'baseline_subject': BASELINE_SUBJECT,
            'freeze_tag_commit_ids': tags,
            'source': sources,
            'accepted_evidence': EVIDENCE,
            'required_source_digests': files,
            'declared_exclusions': list(EXPLICIT_GAPS),
            'release_character': 'bounded_reference_profile_only',
            'status': 'RELEASE_CANDIDATE'}


def seal_v0(repo: Path):
    payload = release_record_v0(repo)
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': digest(SCHEMA + '\n' + canonical(payload))})


def _no_duplicate_keys(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError('duplicate JSON key')
        d[k] = v
    return d


def _no_nonfinite(v):
    raise ValueError('nonfinite JSON constant: ' + v)


def verify_v0(document: str, repo: Path):
    if type(document) is not str:
        raise TypeError('document must be text')
    obj = json.loads(document, object_pairs_hook=_no_duplicate_keys,
                     parse_constant=_no_nonfinite)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('invalid noncanonical release attestation')
    if digest(SCHEMA + '\n' + canonical(obj['payload'])) != obj['payload_sha256']:
        raise ValueError('release attestation checksum mismatch')
    if release_record_v0(repo) != obj['payload']:
        raise ValueError('release attestation replay/source drift')
    return {'status': 'PASS', 'baseline_commit': obj['payload']['baseline_commit'],
            'release_character': obj['payload']['release_character'],
            'evidence_families': len(EVIDENCE),
            'attestation_sha256': digest(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', type=Path)
    mode.add_argument('--verify', type=Path)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    if args.write is not None:
        document = seal_v0(args.repo)
        args.write.write_text(document + '\n', encoding='utf-8')
    else:
        document = args.verify.read_text(encoding='utf-8').rstrip('\n')
    print(canonical(verify_v0(document, args.repo)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
