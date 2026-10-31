"""A5a inventory tests, including source/receipt mutation and frozen-branch denial."""
from pathlib import Path
import re
import pytest

from spk_architecture_v1 import conformance_inventory_v1a as m


def test_all_16_phases_are_complete_disjoint_and_hash_pinned():
    assert tuple(m.PHASES) == tuple(f'a{i}{c}' for i in range(1,5) for c in 'abcd')
    paths=[f for _, files in m.PHASES.values() for f in files]
    assert len(paths)==len(set(paths))==97
    for phase,(digest,files) in m.PHASES.items():
        assert re.fullmatch('[0-9a-f]{64}',digest)
        assert len([f for f in files if f.startswith('docs/')])==1
        assert len([f for f in files if f.startswith('spk_architecture_v1/')]) in (1,2)
        assert len([f for f in files if f.startswith('search/')])==2
        assert len([f for f in files if f.startswith('tests/')])==2
        assert not any(f.startswith(tuple(x+'/' for x in m.FROZEN_DIRS)) for f in files)


@pytest.fixture
def fake_repo(tmp_path,monkeypatch):
    (tmp_path/'.git').write_text('gitdir: fake.git\n')
    allfiles=[]
    for phase,(digest,files) in m.PHASES.items():
        for f in files:
            p=tmp_path/f; p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(('Status: INTEGRATION PASS\nEvidence '+digest+'\n') if f.startswith('docs/')
                         else 'verified test fixture\n')
            allfiles.append(f)
    def git(root,*args):
        if args==('branch','--show-current'): return m.ARCH_BRANCH
        if args==('rev-parse',m.FROZEN_TAG+'^{}'): return m.FROZEN_COMMIT
        if args==('cat-file','-t','refs/tags/'+m.FROZEN_TAG): return 'tag'
        if args==('rev-parse','HEAD'): return '2'*40
        if args==('ls-files',): return '\n'.join(allfiles)
        if args[0] in ('diff','merge-base'): return ''
        raise AssertionError('unexpected git command '+repr(args))
    monkeypatch.setattr(m,'_git',git)
    return tmp_path


def test_mock_committed_inventory_computes_97_actual_file_digests(fake_repo):
    v=m.manifest_v1a(fake_repo)
    assert v['phase_count']==16 and v['tracked_source_files']==97
    assert v['head_commit']=='2'*40
    assert len({x['path'] for p in v['phases'] for x in p['files']})==97
    assert len({x['sha256'] for p in v['phases'] for x in p['files']})>1


def test_damaged_phase_document_rejected(fake_repo):
    p=fake_repo/m.PHASES['a4d'][1][0]
    p.write_text('tampered\n')
    with pytest.raises(m.InventoryRejectedV1a,match='uncertified|missing'):
        m.manifest_v1a(fake_repo)


def test_dirty_whitespace_rejected(fake_repo):
    p=fake_repo/m.PHASES['a4a'][1][1]
    p.write_bytes(p.read_bytes()+b'trailing \n')
    with pytest.raises(m.InventoryRejectedV1a,match='dirty'):
        m.manifest_v1a(fake_repo)


def test_wrong_branch_fails_closed(fake_repo,monkeypatch):
    original=m._git
    def altered(root,*args):
        if args==('branch','--show-current'): return 'other'
        return original(root,*args)
    monkeypatch.setattr(m,'_git',altered)
    with pytest.raises(m.InventoryRejectedV1a,match='branch'):
        m.manifest_v1a(fake_repo)


def test_baseline_tag_move_denied(fake_repo,monkeypatch):
    original=m._git
    def altered(root,*args):
        if args==('rev-parse',m.FROZEN_TAG+'^{}'): return '0'*40
        return original(root,*args)
    monkeypatch.setattr(m,'_git',altered)
    with pytest.raises(m.InventoryRejectedV1a,match='tag moved'):
        m.manifest_v1a(fake_repo)


def test_predecessor_file_missing_in_index_denied(fake_repo,monkeypatch):
    original=m._git
    def altered(root,*args):
        result=original(root,*args)
        if args==('ls-files',):
            return '\n'.join(result.splitlines()[:-1])
        return result
    monkeypatch.setattr(m,'_git',altered)
    with pytest.raises(m.InventoryRejectedV1a,match='uncommitted or missing'):
        m.manifest_v1a(fake_repo)
