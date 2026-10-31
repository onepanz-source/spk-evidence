"""SPK BV v0o: source-bound pytest fixture capture and structural comparison.

Research only. Does not assert equal underlying workloads unless explicitly evidenced.
A structural match of selected workload fields is not causal identification.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .native_capture_v0k import canonical_fixture, shape_report, _json_bytes, _no_duplicate_keys, _reject_constant, _sha
from .native_dossier_v0l import _validate_typed, typed_path

SCHEMA = 'spk-bv-live-runs-capture/v0o'
INSPECT_SCHEMA = 'spk-bv-live-runs-inventory/v0o'
COMPARE_SCHEMA = 'spk-bv-declared-pair-comparison/v0o'
STATUS = 'NATIVE_FIXTURE_CAPTURED_NOT_CONTROLLED_COMPARISON'
PAIR_STATUS = 'DECLARED_SAME_PAYLOAD_FIELDS_NOT_CAUSAL_EFFECT'
TARGET = 'tests/test_spk_bv_live_dual_scheduler_v0e.py'
CASE = 'test_feedback_causes_forward_source_link_wait'
MODULE = 'spk_bv_live_dual_scheduler_v0e.py'  # legacy relative name only
# Frozen list of permissible paths: no filesystem-wide dynamic discovery.
PRODUCER_CANDIDATES = (
    'search/spk_bv_live_dual_scheduler_v0e.py',
    'spk_bv_research/live_dual_scheduler_v0e.py',
    'spk_bv_research/spk_bv_live_dual_scheduler_v0e.py',
    'spk_bv_live_dual_scheduler_v0e.py',
)
LIMIT = 16_000_000
MAX_METRICS = 32

class PairError(ValueError):
    pass


def fail(message: str):
    raise PairError(message)


def check_file(path: Path, *, bound=LIMIT) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > bound:
        fail('input is not a bounded regular non-symlink file')
    return path.read_bytes()


def load_json(path: Path, *, bound=LIMIT):
    try:
        return json.loads(check_file(path, bound=bound), object_pairs_hook=_no_duplicate_keys,
                          parse_constant=_reject_constant)
    except (ValueError, UnicodeError) as ex:
        raise PairError('invalid JSON: '+str(ex)) from ex


def _safe_source(root: Path, rel: str, *, required: bool = True) -> bytes | None:
    f = root / rel
    if f.is_symlink():
        fail('unsafe native producer symlink: ' + rel)
    if not f.exists():
        if required:
            fail('missing native producer: ' + rel)
        return None
    if not f.is_file() or f.resolve() != f or root not in f.parents:
        fail('unsafe native producer: ' + rel)
    return check_file(f, bound=600_000)


def _imports_from_test(raw: bytes) -> set[str]:
    """Static import hints only; importing a module is deliberately avoided."""
    import ast
    try:
        tree = ast.parse(raw, filename=TARGET)
    except (SyntaxError, UnicodeError) as exc:
        fail('unparsable native test source: ' + str(exc))
    refs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            refs.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            refs.add(node.module)
            refs.update(node.module + '.' + alias.name for alias in node.names)
    return refs


def _source_module(rel: str) -> str:
    return rel[:-3].replace('/', '.')


def _local_import_paths(source: bytes, *, src_label: str, root: Path) -> set[str]:
    """Resolve Python import spellings to existing, in-tree SPK .py sources.

    Only explicit AST imports and their in-tree transitive closure are considered;
    no module import, arbitrary filesystem glob, site-packages or runtime execution.
    This is source-byte custody, NOT a proof of what the Python import system loads.
    """
    import ast
    try:
        tree = ast.parse(source, filename=src_label)
    except (SyntaxError, UnicodeError) as ex:
        fail('unparsable local producer source: ' + str(ex))
    refs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            refs.update(x.name for x in node.names)
        elif isinstance(node, ast.ImportFrom):
            # Absolute imports and static relative package imports only.
            if node.level:
                if not src_label.endswith('.py') or '/' not in src_label:
                    continue
                parent = src_label[:-3].split('/')[:-1]
                if node.level > len(parent):
                    continue
                prefix = parent[:len(parent)-node.level+1]
                mod = '.'.join(prefix + ([node.module] if node.module else []))
            else:
                mod = node.module or ''
            if mod:
                refs.add(mod)
                refs.update(mod + '.' + x.name for x in node.names if x.name != '*')
    located = set()
    for name in sorted(refs):
        parts = name.split('.')
        if not parts or not all(part.isidentifier() for part in parts):
            continue
        if not (parts[0].startswith('spk_') or parts[0] == 'search'):
            continue
        rel = '/'.join(parts)
        candidates = (rel + '.py', rel + '/__init__.py')
        present = []
        for candidate in candidates:
            # _safe_source rejects any symlink or nonregular file, including a
            # dangling path; this cannot silently fall back to another source.
            raw = _safe_source(root, candidate, required=False)
            if raw is not None:
                present.append(candidate)
        if len(present) > 1:
            fail('ambiguous local Python module: ' + name)
        located.update(present)
    return located


def _static_local_custody(root: Path, test_source: bytes) -> dict:
    """Bounded, statically reachable in-repository import graph from native test."""
    pending = [(TARGET, test_source)]
    source_hashes = {TARGET: sha256(test_source).hexdigest()}
    while pending:
        caller, source = pending.pop(0)
        for rel in sorted(_local_import_paths(source, src_label=caller, root=root)):
            if rel in source_hashes:
                continue
            if len(source_hashes) >= 96:
                fail('static native import closure exceeds 96 source files')
            raw = _safe_source(root, rel, required=True)
            source_hashes[rel] = sha256(raw).hexdigest()
            pending.append((rel, raw))
    # A package initializer alone cannot identify the scheduler implementation.
    substantive = [x for x in source_hashes if x != TARGET and not x.endswith('/__init__.py')]
    if not substantive:
        fail('no concrete local SPK module reached by native test imports or approved paths; '
             'inspect: sed -n \'1,110p\' ' + TARGET)
    return {'status': 'LOCAL_SOURCE_BYTES_PINNED_NOT_INDEPENDENT',
            'source_sha256': dict(sorted(source_hashes.items())),
            'producer_resolution': 'STATIC_LOCAL_IMPORT_CLOSURE_NOT_RUNTIME_PROOF'}


def pins(root: Path) -> dict:
    root = root.resolve(strict=True)
    test_source = _safe_source(root, TARGET)
    observed = []
    for rel in PRODUCER_CANDIDATES:
        raw = _safe_source(root, rel, required=False)
        if raw is not None:
            observed.append((rel, raw))
    if not observed:
        # The historical filename was a hypothesis, not a contract. Resolve
        # local modules from actual native test imports without running code.
        return _static_local_custody(root, test_source)
    if len(observed) == 1:
        chosen, data = observed[0]
        choice = 'UNIQUE_APPROVED_PATH_NOT_IMPORT_PROOF'
    else:
        imports = _imports_from_test(test_source)
        referenced = [(rel, raw) for rel, raw in observed if _source_module(rel) in imports]
        if len(referenced) != 1:
            fail('ambiguous scheduler producers; cannot source-pin a unique import: ' +
                 ', '.join(rel for rel, _ in observed))
        chosen, data = referenced[0]
        choice = 'STATIC_DIRECT_IMPORT_MATCH_NOT_RUNTIME_PROOF'
    return {'status': 'LOCAL_SOURCE_BYTES_PINNED_NOT_INDEPENDENT',
            'source_sha256': {
                TARGET: sha256(test_source).hexdigest(),
                chosen: sha256(data).hexdigest()},
            'producer_resolution': choice}


def _validate_source_pins(p: dict) -> None:
    if type(p) is not dict or p.get('status') != 'LOCAL_SOURCE_BYTES_PINNED_NOT_INDEPENDENT':
        fail('invalid producer provenance')
    hashes=p.get('source_sha256')
    if type(hashes) is not dict or TARGET not in hashes:
        fail('invalid producer provenance')
    resolution = p.get('producer_resolution')
    paths = set(hashes) - {TARGET}
    if resolution == 'STATIC_LOCAL_IMPORT_CLOSURE_NOT_RUNTIME_PROOF':
        if not 1 <= len(paths) <= 95 or not any(not x.endswith('/__init__.py') for x in paths):
            fail('invalid static import closure')
        for rel in paths:
            parts = rel.removesuffix('.py').split('/')
            if (not rel.endswith('.py') or any(not segment.isidentifier() for segment in parts)
                or not (parts[0].startswith('spk_') or parts[0] == 'search')):
                fail('invalid static import source path')
    else:
        if len(paths) != 1 or next(iter(paths)) not in PRODUCER_CANDIDATES:
            fail('invalid producer provenance source path')
        if resolution is not None and resolution not in (
            'UNIQUE_APPROVED_PATH_NOT_IMPORT_PROOF',
            'STATIC_DIRECT_IMPORT_MATCH_NOT_RUNTIME_PROOF'):
            fail('invalid producer resolution')
    for v in hashes.values():
        if type(v) is not str or len(v) != 64 or any(c not in '0123456789abcdef' for c in v):
            fail('invalid producer source digest')

def capture(value: Any, producer_pins: dict):
    _validate_source_pins(producer_pins)
    encoded=canonical_fixture(value)
    return {'schema':SCHEMA,'status':STATUS,'selected_test':CASE,'selected_fixture':'runs',
            'producer_pins':producer_pins,'native_fixture_sha256':_sha(encoded),
            'native_fixture':encoded,'structure':shape_report(encoded),
            'claims_excluded':['equal-workload-proof','feedback-causal-effect','hardware-cost',
                               'v0h-528-stress-equivalence','learning','architecture-promotion']}


def load_capture(path: Path):
    data=load_json(path)
    if type(data) is not dict or data.get('schema')!=SCHEMA or data.get('status')!=STATUS or data.get('selected_test')!=CASE or data.get('selected_fixture')!='runs':
        fail('wrong capture envelope')
    p=data.get('producer_pins')
    _validate_source_pins(p)
    typed=data.get('native_fixture')
    _validate_typed(typed)
    if type(data.get('native_fixture_sha256')) is not str or _sha(typed)!=data['native_fixture_sha256']:
        fail('native fixture hash mismatch')
    if data.get('structure')!=shape_report(typed):
        fail('native shape mismatch')
    if type(data.get('claims_excluded')) is not list or 'feedback-causal-effect' not in data['claims_excluded']:
        fail('missing claim exclusions')
    return data


def _child_summary(node):
    if type(node) is dict and node.get('$t') in ('list','tuple','set','frozenset'):
        return {'type':node['$t'],'length':len(node['items'])}
    if type(node) is dict and node.get('$t') in ('dict','dataclass'):
        pairs=node['pairs'] if node['$t']=='dict' else node['fields']
        names=sorted(str(k) for k,v in pairs if type(k) is str)
        return {'type':node['$t'],'fields':names[:40], 'field_count':len(names)}
    if type(node) is dict and '$t' in node:
        return {'type':node['$t']}
    if type(node) in (int,bool,float):
        return {'type':type(node).__name__,'value':node}
    return {'type':type(node).__name__}


def inventory(data: dict):
    root=data['native_fixture']
    rows=[]
    stack=[([],root,0)]
    while stack and len(rows)<600:
        path,node,depth=stack.pop()
        rows.append({'path':path,'summary':_child_summary(node)})
        if depth>=4 or type(node) is not dict: continue
        typ=node.get('$t')
        if typ in ('dict','dataclass'):
            for k,v in reversed(node['pairs'] if typ=='dict' else node['fields']):
                if type(k) is str:
                    stack.append((path+[k],v,depth+1))
        elif typ in ('list','tuple'):
            for i in reversed(range(min(12,len(node['items'])))):
                stack.append((path+[i],node['items'][i],depth+1))
    return {'schema':INSPECT_SCHEMA,'status':'STRUCTURAL_INVENTORY_ONLY',
            'native_fixture_sha256':data['native_fixture_sha256'],
            'producer_pins':data['producer_pins'],
            'entries':rows,'inventory_truncated':bool(stack),
            'claims_excluded':['run-identity-inferred-from-key-name','equal-workload-proof','causal-effects']}


def _path(p):
    if type(p) is not list or len(p)>24 or any(type(x) not in (str,int) or (type(x) is str and (not x or len(x)>128)) or (type(x) is int and not 0<=x<=100000) for x in p):
        fail('invalid typed selector')
    return tuple(p)


def _metric(root, desc):
    if type(desc) is not dict or set(desc)!={'path','op'} or desc['op'] not in ('int','count'):
        fail('metric requires path/op int or count')
    obj=typed_path(root,_path(desc['path']))
    if desc['op']=='int':
        if type(obj) is not int: fail('metric not exact int')
        return obj
    if type(obj) is not dict or obj.get('$t') not in ('list','tuple'):
        fail('metric count not list/tuple')
    return len(obj['items'])


def compare(data: dict, config: dict):
    if type(config) is not dict or set(config)!={'baseline','enabled','workload_witnesses','metrics'}:
        fail('comparison config must declare all required sections and no extra fields')
    base=typed_path(data['native_fixture'],_path(config['baseline']))
    live=typed_path(data['native_fixture'],_path(config['enabled']))
    if config['baseline']==config['enabled'] or base==live:
        fail('identical pair selectors or identical outcome records')
    witnesses=config['workload_witnesses']
    if type(witnesses) is not list or len(witnesses)<1 or len(witnesses)>12:
        fail('need 1..12 explicit input witnesses')
    observations=[]
    for row in witnesses:
        if type(row) is not dict or set(row)!={'name','baseline_path','enabled_path'} or type(row['name']) is not str or not row['name']:
            fail('invalid workload witness')
        x=typed_path(base,_path(row['baseline_path']))
        y=typed_path(live,_path(row['enabled_path']))
        if x!=y:
            fail('declared workload witness not equal: '+row['name'])
        observations.append({'name':row['name'],'equal_selected_values':True,'selected_content_sha256':_sha(x)})
    if len({x['name'] for x in observations})!=len(observations): fail('repeated workload witness name')
    metrics=config['metrics']
    if type(metrics) is not dict or not 1<=len(metrics)<=MAX_METRICS:
        fail('invalid metrics section')
    comparisons={}
    for name, spec in sorted(metrics.items()):
        if type(name) is not str or not name or type(spec) is not dict or set(spec)!={'baseline','enabled'}:
            fail('invalid metric spec')
        a=_metric(base,spec['baseline']); b=_metric(live,spec['enabled'])
        comparisons[name]={'baseline':a,'enabled':b,'delta_enabled_minus_baseline':b-a}
    return {'schema':COMPARE_SCHEMA,'status':PAIR_STATUS,
            'native_fixture_sha256':data['native_fixture_sha256'],
            'producer_pins':data['producer_pins'],
            'selector_config_sha256':_sha(config),
            'declared_equal_witnesses':observations,'observed_metrics':comparisons,
            'claims_excluded':['complete-input-parity-unless-full-input-manifest-pinned',
                'source-level-treatment-isolation','matched-output-semantics','causal-feedback-cost',
                'hardware-cost','learning','v0h-stress-equivalence']}


def publish_new(path:Path, report:dict, forbidden:tuple[Path,...]=()):
    if path.exists() or path.is_symlink(): fail('refuse report overwrite')
    absout=path.absolute()
    for p in forbidden:
        if p.resolve()==absout or p.resolve() in absout.parents:
            fail('unsafe report output path')
    raw=_json_bytes(report)+b'\n'
    if len(raw)>LIMIT: fail('report exceeds bound')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f: f.write(raw)
