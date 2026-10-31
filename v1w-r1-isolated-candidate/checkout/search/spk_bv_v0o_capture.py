#!/usr/bin/env python3
"""Capture the native v0e pytest `runs` fixture, skipping the test body."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import os
import sys

from spk_bv_research.paired_runs_v0o import (
    CASE,TARGET,PairError, pins, capture, publish_new,
)

class CapturePlugin:
    def __init__(self): self.called=False; self.value=None
    def pytest_runtest_call(self,item):
        import pytest
        if item.name!=CASE: return
        if 'runs' not in item.funcargs: pytest.skip('BV v0o required runs fixture absent')
        self.value=item.funcargs['runs'];self.called=True
        pytest.skip('BV v0o fixture captured; target test body intentionally not run')


def run_native(root):
    import pytest
    plug=CapturePlugin()
    old=Path.cwd()
    try:
        os.chdir(root)
        rc=pytest.main(['-q','-p','no:cacheprovider','-o','addopts=',f'{TARGET}::{CASE}'],plugins=[plug])
    finally: os.chdir(old)
    if int(rc)!=0 or not plug.called: raise PairError(f'fixture capture failure rc={rc}, called={plug.called}')
    return plug.value


def main(argv=None):
    p=argparse.ArgumentParser(description='BV v0o native v0e source-pinned paired-runs fixture acquisition')
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        original_pins=pins(root)
        result=capture(run_native(root),original_pins)
        if pins(root)!=original_pins: raise PairError('producer changed during capture')
        publish_new(args.out,result,forbidden=(root,))
        print(json.dumps({'status':result['status'],'fixture_sha256':result['native_fixture_sha256'],
                          'candidate_sequences':result['structure']['candidate_sequences'],
                          'file':str(args.out)},sort_keys=True))
    except Exception as ex:
        print('BV v0o capture REJECTED: '+str(ex),file=sys.stderr);return 2
    return 0

if __name__=='__main__': raise SystemExit(main())
