"""SPK BV v0l: structure and provenance dossier from an actual v0k typed capture.

Only reads a v0k capture. No v0h execution, packet translation, identity inference,
credit, causal equivalence, scheduling, or runtime changes.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .native_capture_v0k import (
    CAPTURE_SCHEMA, NativeCaptureError, _json_bytes, _no_duplicate_keys,
    _reject_constant, _sha, shape_report,
)

DOSSIER_SCHEMA = 'spk-bv-native-typed-dossier/v0l'
MAX_BYTES = 16_000_000
MAX_DEPTH = 52
MAX_NODES = 120_000
MAX_ROWS = 100_000
MAX_FIELDS = 256
SHA = re.compile(r'[0-9a-f]{64}\Z')
GROUPS = {
    'feedback_deliveries': (3, 'feedback', 'deliveries'),
    'feedback_link_grants': (3, 'feedback', 'link_grants'),
    'feedback_assessments': (3, 'feedback', 'assessments'),
    'forward_batches': (3, 'forward', 'batches'),
}

class DossierError(ValueError):
    pass


def _digest(x: object) -> str:
    return sha256(_json_bytes(x)).hexdigest()


def _validate_typed(root: object) -> None:
    """Validate v0k typed wire representation, fail closed on malformed tags."""
    nodes = 0
    def walk(x: object, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise DossierError('typed fixture traversal bound exceeded')
        if x is None or type(x) in (bool, int, str):
            if type(x) is int and abs(x) > 2**63-1:
                raise DossierError('unbounded integer')
            if type(x) is str and len(x) > 500_000:
                raise DossierError('oversized string')
            return
        if type(x) is not dict or type(x.get('$t')) is not str:
            raise DossierError('unexpected untagged or malformed typed container')
        tag = x['$t']
        if tag in ('list', 'tuple', 'set', 'frozenset'):
            if set(x) != {'$t', 'items'} or type(x['items']) is not list:
                raise DossierError('bad typed sequence')
            for y in x['items']:
                walk(y, depth+1)
            if tag in ('set','frozenset'):
                digests=[_json_bytes(y) for y in x['items']]
                if digests != sorted(set(digests)):
                    raise DossierError('typed set not unique and sorted')
        elif tag == 'dict':
            if set(x) != {'$t','pairs'} or type(x['pairs']) is not list:
                raise DossierError('bad typed dict')
            keys=[]
            for p in x['pairs']:
                if type(p) is not list or len(p) != 2:
                    raise DossierError('bad typed pair')
                walk(p[0],depth+1);walk(p[1],depth+1)
                keys.append(_json_bytes(p[0]))
            if keys != sorted(set(keys)):
                raise DossierError('typed dict keys not unique and sorted')
        elif tag == 'dataclass':
            if set(x) != {'$t','class','fields'} or type(x['class']) is not str or not x['class'] or type(x['fields']) is not list:
                raise DossierError('bad dataclass')
            names=set()
            for p in x['fields']:
                if type(p) is not list or len(p) != 2 or type(p[0]) is not str or not p[0] or p[0] in names:
                    raise DossierError('duplicate/bad dataclass field')
                names.add(p[0]);walk(p[1],depth+1)
        elif tag == 'float':
            if set(x) != {'$t','v'} or type(x['v']) is not str:
                raise DossierError('bad tagged float')
            try:
                import math
                if not math.isfinite(float(x['v'])) or repr(float(x['v'])) != x['v']:
                    raise DossierError('noncanonical or nonfinite float')
            except ValueError as e:
                raise DossierError('bad float string') from e
        elif tag == 'bytes':
            if set(x) != {'$t','v'} or type(x['v']) is not str or len(x['v']) > 1_000_000:
                raise DossierError('bad tagged bytes')
            try:
                b=bytes.fromhex(x['v'])
                if b.hex()!=x['v']:
                    raise DossierError('noncanonical tagged bytes')
            except ValueError as e:
                raise DossierError('bad bytes hex') from e
        else:
            raise DossierError('unsupported typed tag: '+tag)
    walk(root,0)


def _field_get(node: object, field: str) -> object:
    if type(node) is not dict:
        raise DossierError('field parent not encoded container')
    if node.get('$t') == 'dict':
        values=[v for k,v in node['pairs'] if k == field]
    elif node.get('$t') == 'dataclass':
        values=[v for k,v in node['fields'] if k == field]
    else:
        raise DossierError('field parent is not dict/dataclass')
    if len(values)!=1:
        raise DossierError('native field missing/ambiguous: '+field)
    return values[0]


def typed_path(root: object, path: tuple[int | str,...]) -> object:
    node = root
    for segment in path:
        if type(segment) is int:
            if type(node) is not dict or node.get('$t') not in ('list','tuple') or segment >= len(node['items']) or segment < 0:
                raise DossierError('indexed native path absent')
            node=node['items'][segment]
        elif type(segment) is str:
            node=_field_get(node,segment)
        else:
            raise DossierError('bad native path type')
    return node


def _scalar_shape(node: object, prefix: str='', depth: int=0) -> dict[str,str]:
    if depth >= 3:
        return {}
    if type(node) is dict and node.get('$t') in ('dict','dataclass'):
        records = node['pairs'] if node['$t']=='dict' else node['fields']
        out={}
        for key,v in records:
            if type(key) is not str:
                continue
            p=prefix+('/' if prefix else '')+key
            if type(v) in (str,int,bool) or v is None:
                out[p] = type(v).__name__
            elif type(v) is dict and v.get('$t') in ('dict','dataclass'):
                out.update(_scalar_shape(v,p,depth+1))
            elif type(v) is dict:
                out[p]='tag:'+str(v.get('$t','unknown'))
        return out
    return {}


def _scalar_values(node:object, prefix:str='', depth:int=0)->dict[str,object]:
    if depth >= 3 or type(node) is not dict or node.get('$t') not in ('dict','dataclass'):
        return {}
    pairs=node['pairs'] if node['$t']=='dict' else node['fields']
    out={}
    for key,val in pairs:
        if type(key) is not str:
            continue
        p=prefix+('/' if prefix else '')+key
        if (type(val) in (str,int,bool) or val is None) and (type(val) is not str or len(val) <= 128):
            out[p]=val
        elif type(val) is dict and val.get('$t') in ('dict','dataclass'):
            out.update(_scalar_values(val,p,depth+1))
    return out


def _shape_signature(row:object)->str:
    shape=_scalar_shape(row)
    marker={'row_type': row.get('$t') if type(row) is dict else type(row).__name__,
            'fields':shape}
    return _digest(marker)


def group_report(encoded:object, *, name:str, sample_values:int=0)->dict:
    if type(encoded) is not dict or encoded.get('$t') not in ('list','tuple'):
        raise DossierError(name+': expected v0k list/tuple')
    rows=encoded['items']
    if len(rows)>MAX_ROWS:
        raise DossierError(name+': row bound exceeded')
    hashes=[_digest(row) for row in rows]
    shapes=Counter(_shape_signature(row) for row in rows)
    field_counts=Counter()
    types={}
    for row in rows:
        shape=_scalar_shape(row)
        for k,v in shape.items():
            field_counts[k]+=1
            types.setdefault(k,set()).add(v)
    if len(field_counts)>MAX_FIELDS:
        raise DossierError(name+': schema field bound exceeded')
    samples=[{'ordinal':i,'row_sha256':hashes[i], 'scalar_values':_scalar_values(rows[i])}
             for i in range(min(sample_values,len(rows)))]
    return {
        'source_path': '$'+''.join((f'[{s}]' if type(s) is int else '/'+s) for s in GROUPS[name]),
        'native_rows':len(rows),
        'unique_full_row_content':len(set(hashes)),
        'repeated_full_row_content':len(rows)-len(set(hashes)),
        'ordered_native_rows_sha256':_digest(rows),
        'native_row_multiset_sha256':_digest(sorted(hashes)),
        'shape_signature_counts':[{'signature_sha256':h,'rows':n} for h,n in sorted(shapes.items())],
        'field_coverage':[{'path':k,'rows':n,'scalar_types':sorted(types[k])}
                          for k,n in sorted(field_counts.items())],
        'scalar_samples':samples,
    }


def load_capture(path:Path)->dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise DossierError('capture must be bounded regular non-symlink file')
    try:
        doc=json.loads(path.read_bytes(),object_pairs_hook=_no_duplicate_keys,parse_constant=_reject_constant)
    except (ValueError,UnicodeError) as exc:
        raise DossierError('invalid capture JSON: '+str(exc)) from exc
    if (type(doc) is not dict or doc.get('schema')!=CAPTURE_SCHEMA or
        doc.get('status')!='NATIVE_FIXTURE_CAPTURED_NOT_EQUIVALENCE' or
        doc.get('native_v0h_verified') is not False or
        type(doc.get('native_fixture_sha256')) is not str or
        not SHA.fullmatch(doc['native_fixture_sha256']) or
        type(doc.get('producer_pins')) is not dict or
        doc['producer_pins'].get('status')!='PINNED_BYTES_ONLY' or
        type(doc.get('selected_test')) is not str or
        type(doc.get('excluded_claims')) is not list):
        raise DossierError('capture envelope is not pinned v0k observation')
    _validate_typed(doc.get('native_fixture'))
    if _sha(doc['native_fixture']) != doc['native_fixture_sha256']:
        raise DossierError('native fixture SHA mismatch')
    if shape_report(doc['native_fixture']) != doc.get('structure'):
        raise DossierError('native fixture shape report mismatch')
    return doc


def native_dossier(doc:dict,*,sample_values:int=0, expected_sha:str|None=None)->dict:
    if type(sample_values) is not int or not (0 <= sample_values <= 3):
        raise DossierError('sample_values must be 0..3')
    if expected_sha is not None and (not SHA.fullmatch(expected_sha) or doc['native_fixture_sha256'] != expected_sha):
        raise DossierError('unexpected native fixture digest')
    groups={}
    for name,path in GROUPS.items():
        groups[name]=group_report(typed_path(doc['native_fixture'],path),name=name,sample_values=sample_values)
    return {
        'schema':DOSSIER_SCHEMA,
        'status':'NATIVE_TYPED_GROUPS_INSPECTED_NOT_PACKET_MAPPING',
        'native_fixture_sha256':doc['native_fixture_sha256'],
        'selected_test':doc['selected_test'],
        'producer_pins':doc['producer_pins'],
        'groups':groups,
        'group_cardinality_equal_not_bijection': (
            groups['feedback_deliveries']['native_rows']==groups['feedback_link_grants']['native_rows']),
        'native_v0h_verified':False,
        'claim_exclusions':['physical-packet-identity','delivery-grant-pairing',
            '528-packet-v0h-stress-equivalence','causal-credit', 'learning',
            'true-hardware-cost','compression','scheduling-equivalence'],
    }
