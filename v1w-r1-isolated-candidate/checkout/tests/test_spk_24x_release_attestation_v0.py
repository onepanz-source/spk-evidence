"""24x bounded release gate policy and byte-level provenance unit tests."""
from pathlib import Path
import subprocess
import json
import pytest
from search import spk_24x_release_attestation_v0 as r


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def write(repo, name, value='fixture'):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + '\n')


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, 'init', '-q')
    git(tmp_path, 'config', 'user.name', 'Release Gate Fixture')
    git(tmp_path, 'config', 'user.email', 'test@example.invalid')
    for p in ('spk_core/core.py', 'spk_network/network.py', 'spk_compiler/compiler.py'):
        write(tmp_path, p)
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-qm', 'frozen files')
    for tag in r.FREEZE_TAGS:
        git(tmp_path, 'tag', '-a', tag, '-m', 'freeze')
    for p in r.REQUIRED_TRACKED:
        write(tmp_path, p)
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-qm', r.BASELINE_SUBJECT)
    return tmp_path


def test_declared_release_character_and_source_identity():
    assert r.source_identity_v0() == {
        'corpus_sha256': r.CORPUS_SHA256, 'source_cases': 216,
        'structural_plan_sha256': r.PLAN_W_SHA256, 'structural_variants': 648}
    assert len(r.EXPLICIT_GAPS) >= 5


def test_fingerprint_families_are_pinned_and_distinct():
    pins = [v['sha256'] for v in r.EVIDENCE.values()]
    assert len(pins) == len(set(pins)) == 3
    assert all(len(p) == 64 for p in pins)


def test_clean_release_workspace_with_annotated_frozen_tags(repo):
    assert r.assert_release_workspace_v0(repo) == repo
    document = r.seal_v0(repo)
    outcome = r.verify_v0(document, repo)
    assert outcome['status'] == 'PASS'
    assert outcome['baseline_commit'] == git(repo, 'rev-parse', 'HEAD')
    assert json.loads(document)['payload']['status'] == 'RELEASE_CANDIDATE'


def test_postcommit_replay_retains_exact_precommit_attestation(repo):
    original = r.seal_v0(repo)
    baseline = git(repo, 'rev-parse', 'HEAD')
    for name in sorted(r.RELEASE_FILES):
        write(repo, name, 'accepted release candidate source')
    git(repo, 'add', *sorted(r.RELEASE_FILES))
    git(repo, 'commit', '-qm', r.RELEASE_SUBJECT)
    assert r.assert_release_workspace_v0(repo) == repo
    assert r.seal_v0(repo) == original
    outcome = r.verify_v0(original, repo)
    assert outcome['baseline_commit'] == baseline
    assert json.loads(original)['payload']['baseline_commit'] == baseline


def test_wrong_subject_for_candidate_commit_is_rejected(repo):
    for name in sorted(r.RELEASE_FILES):
        write(repo, name)
    git(repo, 'add', *sorted(r.RELEASE_FILES))
    git(repo, 'commit', '-qm', 'arbitrary later commit')
    with pytest.raises(ValueError, match='24w accepted HEAD'):
        r.assert_release_workspace_v0(repo)


def test_candidate_commit_with_unexpected_addition_is_rejected(repo):
    for name in sorted(r.RELEASE_FILES):
        write(repo, name)
    write(repo, 'search/unapproved_extra.py')
    git(repo, 'add', *sorted(r.RELEASE_FILES), 'search/unapproved_extra.py')
    git(repo, 'commit', '-qm', r.RELEASE_SUBJECT)
    with pytest.raises(ValueError, match='changed unexpected paths'):
        r.assert_release_workspace_v0(repo)


def test_candidate_commit_with_missing_release_file_is_rejected(repo):
    selected = sorted(r.RELEASE_FILES)[:-1]
    for name in selected:
        write(repo, name)
    git(repo, 'add', *selected)
    git(repo, 'commit', '-qm', r.RELEASE_SUBJECT)
    with pytest.raises(ValueError, match='changed unexpected paths'):
        r.assert_release_workspace_v0(repo)


def test_release_cannot_be_replayed_after_subsequent_commit(repo):
    original = r.seal_v0(repo)
    for name in sorted(r.RELEASE_FILES):
        write(repo, name)
    git(repo, 'add', *sorted(r.RELEASE_FILES))
    git(repo, 'commit', '-qm', r.RELEASE_SUBJECT)
    git(repo, 'commit', '--allow-empty', '-qm', 'future development')
    with pytest.raises(ValueError, match='24w accepted HEAD'):
        r.verify_v0(original, repo)


def test_three_legacy_untracked_and_expected_candidate_sources_allowed(repo):
    for name in r.ALLOWED_UNTRACKED:
        write(repo, name)
    assert r.assert_release_workspace_v0(repo) == repo


def test_unexpected_untracked_file_is_fail_closed(repo):
    write(repo, 'search/unreviewed_adaptor.py')
    with pytest.raises(ValueError, match='unexpected untracked'):
        r.assert_release_workspace_v0(repo)


def test_staged_change_is_fail_closed(repo):
    write(repo, 'README.md', 'surprise')
    git(repo, 'add', 'README.md')
    with pytest.raises(ValueError, match='staged'):
        r.assert_release_workspace_v0(repo)


def test_frozen_source_drift_detected_against_annotated_tag(repo):
    write(repo, 'spk_compiler/compiler.py', 'changed since freeze')
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', r.BASELINE_SUBJECT)
    with pytest.raises(ValueError, match='frozen source drift'):
        r.assert_release_workspace_v0(repo)


def test_wrong_baseline_subject_is_rejected(repo):
    git(repo, 'commit', '--allow-empty', '-qm', 'unrelated work')
    with pytest.raises(ValueError, match='24w accepted HEAD'):
        r.assert_release_workspace_v0(repo)


def test_forged_evidence_field_rejected_even_with_resealed_hash(repo):
    obj = json.loads(r.seal_v0(repo))
    obj['payload']['accepted_evidence']['24w']['sha256'] = '0'*64
    obj['payload_sha256'] = r.digest(r.SCHEMA + '\n' + r.canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay/source drift'):
        r.verify_v0(r.canonical(obj), repo)


def test_corrupted_hash_and_noncanonical_document_rejected(repo):
    doc = r.seal_v0(repo)
    obj = json.loads(doc)
    obj['payload_sha256'] = 'f'*64
    with pytest.raises(ValueError, match='checksum'):
        r.verify_v0(r.canonical(obj), repo)
    with pytest.raises(ValueError, match='noncanonical'):
        r.verify_v0(' ' + doc, repo)
    with pytest.raises(ValueError, match='duplicate JSON'):
        r.verify_v0(doc[:-1] + ',"schema":"forged"}', repo)


def test_unannotated_freeze_tag_is_rejected(repo):
    git(repo, 'tag', '-d', 'spk-compiler-v0')
    git(repo, 'tag', 'spk-compiler-v0')
    with pytest.raises(ValueError, match='annotated frozen tag'):
        r.assert_release_workspace_v0(repo)


def test_missing_required_source_is_rejected(repo):
    p = r.REQUIRED_TRACKED[0]
    git(repo, 'rm', '-q', p)
    git(repo, 'commit', '-qm', r.BASELINE_SUBJECT)
    with pytest.raises(ValueError, match='required 24u/v/w'):
        r.assert_release_workspace_v0(repo)
