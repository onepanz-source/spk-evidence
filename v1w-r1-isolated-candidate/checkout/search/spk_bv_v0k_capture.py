#!/usr/bin/env python3
"""Capture the real_trace fixture from a source-pinned BV v0h test in its native environment.

Runs test module imports and fixture setup (NOT safe against malicious native code);
does not execute the test body; does not alter architecture sources.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from spk_bv_research.native_capture_v0k import (
    DEFAULT_CASE, NativeCaptureError, capture_result, verify_probe, _json_bytes,
)


class FixtureCapturePlugin:
    def __init__(self, case):
        self.case = case
        self.called = False
        self.value = None
        self.error = None

    def pytest_runtest_call(self, item):
        import pytest
        if item.name != self.case:
            return
        if 'real_trace' not in item.funcargs:
            self.error = 'real_trace not found in resolved pytest fixtures'
            pytest.skip('v0k capture failed: missing fixture')
        self.called = True
        self.value = item.funcargs['real_trace']
        pytest.skip('v0k capture intentionally skips the target test body')


def capture_pytest(root: Path, case: str = DEFAULT_CASE):
    import pytest
    plugin = FixtureCapturePlugin(case)
    # pytest returns 0 even when one test was skipped; require the fixture to have
    # actually been resolved to avoid accidental success with a missing test/fixture.
    target = 'tests/test_spk_bv_identified_v0h.py::' + case
    ret = pytest.main(['-q', '-p', 'no:cacheprovider', '-o', 'addopts=', target],
                      plugins=[plugin])
    if int(ret) != 0 or not plugin.called or plugin.error is not None:
        raise NativeCaptureError('source-pinned native fixture capture failed: '
                                 f'pytest_exit={ret}, called={plugin.called}, error={plugin.error}')
    return plugin.value


def main(argv=None):
    p = argparse.ArgumentParser(description='BV v0k: pinned local native fixture capture, no synthetic records')
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--probe', type=Path, required=True, help='JSON emitted by v0j native probe')
    p.add_argument('--out', type=Path, required=True, help='new JSON output; refuses to overwrite')
    p.add_argument('--case', default=DEFAULT_CASE, choices=[DEFAULT_CASE])
    a = p.parse_args(argv)
    try:
        root = a.root.resolve(strict=True)
        out = a.out.absolute()
        if root == out or root in out.parents:
            raise NativeCaptureError('capture output must be outside the source tree')
        if out.exists() or out.is_symlink():
            raise NativeCaptureError('capture output already exists; refusing overwrite')
        pins = verify_probe(root,a.probe)
        # pytest rootdir might be different from CWD; set CWD explicitly using context.
        import os
        original = Path.cwd()
        try:
            os.chdir(root)
            value = capture_pytest(root,a.case)
        finally:
            os.chdir(original)
        after = verify_probe(root,a.probe)
        if after != pins:
            raise NativeCaptureError('native producer source changed while capturing fixture')
        receipt = capture_result(value,pins,a.case)
        raw = _json_bytes(receipt)
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('xb') as fh:
            fh.write(raw+b'\n')
        print(json.dumps({'status':receipt['status'], 'native_v0h_verified':False,
                          'fixture_sha256':receipt['native_fixture_sha256'],
                          'candidate_sequences':receipt['structure']['candidate_sequences'],
                          'file':str(out)},sort_keys=True))
    except Exception as exc:
        # Treat setup/fixture errors as fatal and never leave misleading output.
        print(f'BV v0k native capture: REJECTED: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
