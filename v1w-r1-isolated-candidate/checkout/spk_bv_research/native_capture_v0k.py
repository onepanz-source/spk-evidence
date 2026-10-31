"""BV v0k: source-pinned, fail-closed native fixture capture for offline research.

No synthetic data, no native-to-v0i mapping, no claim of equivalence to v0h.
This executes one existing pytest fixture in the USER's local worktree.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any

PROBE_SCHEMA = 'spk-bv-native-source-probe/v0j'
CAPTURE_SCHEMA = 'spk-bv-fixture-capture/v0k'
TARGETS = (
    'search/spk_bv_v0h_identified_evidence.py',
    'tests/test_spk_bv_identified_v0h.py',
    'search/spk_bv_v0h_research_gate.sh',
)
DEFAULT_CASE = 'test_context_aggregation_refuses_unverified_trace'
SHA = re.compile(r'[0-9a-f]{64}\Z')
MAX_SOURCE = 600_000
MAX_PROBE = 2_000_000
MAX_DOCUMENT = 16_000_000
MAX_NODES = 120_000
MAX_DEPTH = 48
MAX_STRING = 500_000


class NativeCaptureError(ValueError):
    pass


def _json_bytes(value: object) -> bytes:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                         allow_nan=False).encode('ascii')
    except (TypeError, ValueError, OverflowError) as exc:
        raise NativeCaptureError(f'not canonical JSON: {exc}') from exc
    if len(raw) > MAX_DOCUMENT:
        raise NativeCaptureError('native fixture exceeds JSON byte bound')
    return raw


def _sha(v: object) -> str:
    return hashlib.sha256(_json_bytes(v)).hexdigest()


def _read_no_symlink(path: Path, max_size: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise NativeCaptureError(f'file must be regular (not symlink): {path}')
    if path.stat().st_size > max_size:
        raise NativeCaptureError(f'oversized file: {path}')
    return path.read_bytes()


def verify_probe(root: Path, probe_file: Path) -> dict:
    root = root.resolve(strict=True)
    raw = _read_no_symlink(probe_file, MAX_PROBE)
    try:
        doc = json.loads(raw, object_pairs_hook=_no_duplicate_keys,
                         parse_constant=_reject_constant)
    except (ValueError, UnicodeError) as exc:
        raise NativeCaptureError(f'invalid probe: {exc}') from exc
    if (type(doc) is not dict or doc.get('schema') != PROBE_SCHEMA or
        doc.get('scan_truncated') is not False or
        doc.get('status') != 'STATIC_DISCOVERY_ONLY' or
        not isinstance(doc.get('files'), list) or
        doc.get('files_scanned') != len(doc['files'])):
        raise NativeCaptureError('probe incomplete or wrong schema')
    entries = {}
    for f in doc['files']:
        if type(f) is not dict or type(f.get('path')) is not str:
            raise NativeCaptureError('invalid file entry')
        p = f['path']
        if p in entries:
            raise NativeCaptureError('duplicate path in probe')
        entries[p] = f
    matched = {}
    for relative in TARGETS:
        if relative not in entries:
            raise NativeCaptureError('required v0h source absent from probe: ' + relative)
        item = entries[relative]
        digest = item.get('source_sha256')
        if type(digest) is not str or not SHA.fullmatch(digest):
            raise NativeCaptureError('invalid SHA256 for ' + relative)
        target = root.joinpath(*relative.split('/'))
        if target.resolve() != root / relative or target.is_symlink():
            raise NativeCaptureError('unsafe target path ' + relative)
        raw_source = _read_no_symlink(target, MAX_SOURCE)
        if len(raw_source) != item.get('bytes') or hashlib.sha256(raw_source).hexdigest() != digest:
            raise NativeCaptureError('source hash/size mismatch (regenerate probe): ' + relative)
        matched[relative] = digest
    # Source identity is pinned; not a signed attestation. Includes the test fixture producer.
    return {'schema': 'spk-bv-v0h-producer-pins/v0k', 'status': 'PINNED_BYTES_ONLY',
            'source_sha256': matched, 'probe_sha256': hashlib.sha256(raw).hexdigest(),
            'claims_excluded': ['source-independence', 'trace-integrity-from-v0h',
                                'BV-v0h-equivalence', 'causal-credit']}


def _no_duplicate_keys(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise NativeCaptureError('duplicate JSON key')
        result[k] = v
    return result


def _reject_constant(value):
    raise NativeCaptureError('non-finite JSON literal: ' + value)


def canonical_fixture(value: object) -> object:
    """Lossless JSON-tagged representation for supported primitives/containers/dataclasses.

    A deliberately conservative codec: never repr(), id(), invent or stringify unknown
    native objects. Keep tuple distinct from list; distinguish int and bool.
    """
    active_ids = set()
    count = 0

    def encode(obj: object, depth: int):
        nonlocal count
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise NativeCaptureError('fixture node/depth bound reached')
        if obj is None or type(obj) is bool:
            return obj
        if type(obj) is str:
            if len(obj) > MAX_STRING:
                raise NativeCaptureError('fixture scalar string too large')
            return obj
        if type(obj) is int:
            if abs(obj) > 2**63-1:
                raise NativeCaptureError('fixture integer out of bound')
            return obj
        if type(obj) is float:
            if not math.isfinite(obj):
                raise NativeCaptureError('nonfinite float in fixture')
            return {'$t':'float', 'v':repr(obj)}
        if type(obj) is bytes:
            if len(obj) > MAX_STRING:
                raise NativeCaptureError('byte scalar too large')
            return {'$t':'bytes', 'v':obj.hex()}
        tracked = isinstance(obj, (dict, list, tuple, set, frozenset)) or dataclasses.is_dataclass(obj)
        ident = id(obj)
        if tracked and ident in active_ids:
            raise NativeCaptureError('cyclic object graph: source cannot be serialized')
        if tracked:
            active_ids.add(ident)
        try:
            if type(obj) is dict:
                # Preserve non-string key types and reject canonical key collisions.
                pairs = [[encode(k, depth+1),encode(v, depth+1)] for k,v in obj.items()]
                pairs.sort(key=lambda p:_json_bytes(p[0]))
                for a, b in zip(pairs,pairs[1:]):
                    if a[0] == b[0]:
                        raise NativeCaptureError('dict keys collapse under canonical codec')
                return {'$t':'dict', 'pairs':pairs}
            if type(obj) in (list, tuple, set, frozenset):
                vals = [encode(x, depth+1) for x in obj]
                if type(obj) in (set, frozenset):
                    vals.sort(key=_json_bytes)
                    for a,b in zip(vals,vals[1:]):
                        if a == b:
                            raise NativeCaptureError('set items collide under canonical codec')
                return {'$t':type(obj).__name__, 'items':vals}
            if dataclasses.is_dataclass(obj) and not isinstance(obj,type):
                typ = type(obj)
                if '<locals>' in typ.__qualname__:
                    raise NativeCaptureError('local-class dataclass cannot be pinned')
                return {'$t':'dataclass','class':typ.__module__+'.'+typ.__qualname__,
                        'fields':[[f.name,encode(getattr(obj,f.name),depth+1)]
                                  for f in dataclasses.fields(obj)]}
        finally:
            if tracked:
                active_ids.remove(ident)
        raise NativeCaptureError('unsupported native object type: '
                                 +type(obj).__module__+'.'+type(obj).__qualname__)
    result = encode(value, 0)
    _json_bytes(result)
    return result


def shape_report(encoded: object) -> dict:
    """Bounded tree-shape report. No packet schema assumed."""
    seen_types = {}
    candidate_lists = []
    seen_fields = set()
    stack=[('$',encoded,0)]
    while stack:
        path,x,depth=stack.pop()
        if depth > MAX_DEPTH + 1:
            raise NativeCaptureError('shape recursion bound')
        typ = x.get('$t') if type(x) is dict else type(x).__name__
        seen_types[typ]=seen_types.get(typ,0)+1
        if isinstance(x,dict) and x.get('$t') in ('list','tuple'):
            if len(x['items']) > 0:
                candidate_lists.append({'path':path,'count':len(x['items'])})
            for i,y in enumerate(x['items']):
                stack.append((path+f'[{i}]',y,depth+1))
        elif isinstance(x,dict) and x.get('$t') == 'dict':
            for key,val in x['pairs']:
                if isinstance(key,str):
                    if len(seen_fields) < 500:
                        seen_fields.add(key)
                    newpath = path+'/'+key
                else:
                    newpath = path+'/<non-string-key>'
                stack.append((newpath,val,depth+1))
        elif isinstance(x,dict) and x.get('$t') == 'dataclass':
            for key,val in x['fields']:
                stack.append((path+'/'+key,val,depth+1))
        elif isinstance(x,dict) and x.get('$t') in ('set','frozenset'):
            for i,val in enumerate(x['items']):
                stack.append((path+f'[{i}]',val,depth+1))
    return {'node_types':dict(sorted(seen_types.items())),
            'field_names':sorted(seen_fields),
            'candidate_sequences':sorted(candidate_lists, key=lambda x:(-x['count'],x['path']))[:24]}


def capture_result(value: object, pins: dict, case: str = DEFAULT_CASE) -> dict:
    encoded = canonical_fixture(value)
    return {'schema':CAPTURE_SCHEMA, 'status':'NATIVE_FIXTURE_CAPTURED_NOT_EQUIVALENCE',
            'selected_test':case, 'native_fixture': encoded,
            'native_fixture_sha256':_sha(encoded), 'producer_pins':pins,
            'structure':shape_report(encoded),
            'native_v0h_verified':False,
            'excluded_claims':['independent-v0h-replay', 'physical-packet-bijection',
                               'BV-v0h-equivalence', 'cost-truth', 'causal-credit',
                               'learning', 'compression']}
