#!/usr/bin/env python3
"""Exact-hash install of v1v mutable-source exception-boundary hotfix."""
from pathlib import Path
import hashlib,json,os,tempfile,sys

SRC='spk_native_learning_v1/sensed_context_v1v.py'
MAN='spk_native_learning_v1/sensed_context_manifest_v1v.json'
BEFORE_SRC='184b67afc93722a2f59f4ca0a5a3eff5a9fafdbe27e66e613e2f831d89160de3'
AFTER_SRC='0c57ea48429b1449b0ca5257c99979cef51397f2e6f82bbb70362e19a976ac9a'
BEFORE_MAN='c4e3bbaf86a0c2c1059b0bb7f2b7cc1284897133c1b856db34f812729bb89e4b'
AFTER_MAN='13926f5badd0fde54473bd7a8c91e08766eec14990c31f5a41f4ac59edd5d171'

def sha(b):return hashlib.sha256(b).hexdigest()

def atomic_replace(path,payload):
    fd,name=tempfile.mkstemp(prefix='.spk_v1v_fix_',dir=str(path.parent))
    try:
        with os.fdopen(fd,'wb') as out:
            out.write(payload);out.flush();os.fsync(out.fileno())
        os.chmod(name,0o644)
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def main():
    root=Path(__file__).resolve().parents[2]
    source=root/SRC;manifest=root/MAN
    payload_dir=Path(__file__).resolve().parent
    payload_source=(payload_dir/'sensed_context_v1v.py').read_bytes()
    payload_manifest=(payload_dir/'sensed_context_manifest_v1v.json').read_bytes()
    assert sha(payload_source)==AFTER_SRC, 'HOTFIX_PAYLOAD_SOURCE_DRIFT'
    assert sha(payload_manifest)==AFTER_MAN, 'HOTFIX_PAYLOAD_MANIFEST_DRIFT'
    assert not source.is_symlink() and not manifest.is_symlink(), 'HOTFIX_TARGET_SYMLINK'
    before_source=sha(source.read_bytes());before_manifest=sha(manifest.read_bytes())
    assert before_source in (BEFORE_SRC,AFTER_SRC), 'HOTFIX_REFUSES_UNRECOGNIZED_V1V_SOURCE:'+before_source
    assert before_manifest in (BEFORE_MAN,AFTER_MAN), 'HOTFIX_REFUSES_UNRECOGNIZED_V1V_MANIFEST:'+before_manifest
    obj=json.loads(payload_manifest)
    assert obj['files'][SRC]==AFTER_SRC, 'HOTFIX_INVALID_MANIFEST_PIN'
    if before_source!=AFTER_SRC:atomic_replace(source,payload_source)
    if before_manifest!=AFTER_MAN:atomic_replace(manifest,payload_manifest)
    assert sha(source.read_bytes())==AFTER_SRC and sha(manifest.read_bytes())==AFTER_MAN,'HOTFIX_POST_INSTALL_DRIFT'
    print('  v1v source exception boundary + manifest pinned; frozen originals untouched')

if __name__=='__main__':main()
