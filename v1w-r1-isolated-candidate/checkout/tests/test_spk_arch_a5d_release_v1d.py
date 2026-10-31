"""A5d integrity and fail-closed checks for the committed bounded release."""
import json
from pathlib import Path
import subprocess
import pytest
from spk_architecture_v1 import release_conformance_v1d as c


def test_release_file_set_unique_and_closed():
    assert len(c.RELEASE_FILES) == len(set(c.RELEASE_FILES)) == 6
    assert all(x.startswith(('docs/', 'search/', 'tests/', 'spk_architecture_v1/')) for x in c.RELEASE_FILES)
    assert c.RELEASE_TAG != c.BRANCH


def test_all_new_release_sources_clean():
    for name in c.RELEASE_FILES:
        result = c._source_ok(Path.cwd(), name)
        assert result['path'] == name and len(result['sha256']) == 64


def test_source_hygiene_rejects_trailing_space(tmp_path):
    (tmp_path / 'bad').write_bytes(b'good\nbad \n')
    with pytest.raises(c.ReleaseRejectedV1d, match='hygiene'):
        c._source_ok(tmp_path, 'bad')


def test_source_hygiene_rejects_missing_newline(tmp_path):
    (tmp_path / 'bad').write_bytes(b'no newline')
    with pytest.raises(c.ReleaseRejectedV1d, match='hygiene'):
        c._source_ok(tmp_path, 'bad')


def test_source_hygiene_rejects_crlf(tmp_path):
    (tmp_path / 'bad').write_bytes(b'crlf\r\n')
    with pytest.raises(c.ReleaseRejectedV1d, match='hygiene'):
        c._source_ok(tmp_path, 'bad')


def test_source_hygiene_rejects_symlink(tmp_path):
    (tmp_path / 'real').write_bytes(b'clean\n')
    (tmp_path / 'link').symlink_to('real')
    with pytest.raises(c.ReleaseRejectedV1d, match='linked'):
        c._source_ok(tmp_path, 'link')


def test_missing_a5d_commit_is_denied(monkeypatch, tmp_path):
    monkeypatch.setattr(c, 'release_preflight_v1d', lambda root: {'source_files':121})
    monkeypatch.setattr(c, '_git', lambda root, *args: '' if args[0]=='ls-files' else '')
    with pytest.raises(c.ReleaseRejectedV1d, match='not committed'):
        c.release_committed_v1d(tmp_path)


def test_dirty_release_clone_denied(monkeypatch, tmp_path):
    monkeypatch.setattr(c, 'release_preflight_v1d', lambda root: {'source_files':121})
    def fake_git(root,*args):
        if args[0]=='ls-files':return '\n'.join(c.RELEASE_FILES)
        if args[0]=='status':return '?? untracked'
        return ''
    monkeypatch.setattr(c,'_git',fake_git)
    with pytest.raises(c.ReleaseRejectedV1d,match='clean'):
        c.release_committed_v1d(tmp_path)


def test_actual_committed_clean_release_inventory():
    p=c.release_committed_v1d(Path.cwd())
    assert p['predecessor_phases']==19
    assert p['predecessor_files']==115
    assert p['source_files']==121
    assert len(p['files'])==121 and len({r['path'] for r in p['files']})==121
    assert p['head_commit']==subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    assert len(p['historical_evidence_sha256'])==19


def test_manifest_refuses_dirty_a5c_source(monkeypatch):
    # Pure boundary, executed before touching any real source.
    original=c._source_ok
    def reject(root,path):
        if path==c.A5C_FILES[0]:
            raise c.ReleaseRejectedV1d('source tampered')
        return original(root,path)
    monkeypatch.setattr(c,'_source_ok',reject)
    with pytest.raises(c.ReleaseRejectedV1d, match='source tampered'):
        c.release_preflight_v1d(Path.cwd())
