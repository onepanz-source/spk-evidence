"""Bounded AST dependency census for BV v0h producers. Never imports source modules."""
from __future__ import annotations
import ast
import hashlib
from pathlib import Path
from .native_capture_v0k import NativeCaptureError, TARGETS, MAX_SOURCE

PREFIXES = ('spk_bv_research.', 'search.')
ROOT_NAMES = ('spk_bv_research', 'search')
MAX_MODULES = 96
MAX_DEPTH = 7


def _resolve(root: Path, module: str) -> Path | None:
    if not module or module.split('.')[0] not in ROOT_NAMES:
        return None
    for suffix in ('.py', '/__init__.py'):
        target = root / (module.replace('.', '/') + suffix)
        if target.is_symlink():
            raise NativeCaptureError('dependency is a symlink: ' + str(target))
        if target.is_file():
            if target.resolve() != target:
                raise NativeCaptureError('unsafe dependency path: ' + str(target))
            return target
    return None


def _imports(tree: ast.AST, source_module: str):
    found=set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package = source_module.rpartition('.')[0]
                pieces = package.split('.')
                if node.level > len(pieces):
                    continue
                stem='.'.join(pieces[:len(pieces)-node.level+1])
                module=stem+'.'+node.module if node.module else stem
            else:
                module=node.module or ''
            if module:
                found.add(module)
                for alias in node.names:
                    if alias.name != '*':
                        found.add(module+'.'+alias.name)
    return sorted(found)


def census(root: Path):
    root=root.resolve(strict=True)
    pending=[(relative,0) for relative in TARGETS if relative.endswith('.py')]
    completed={}
    missing=[]
    while pending:
        rel, depth=pending.pop(0)
        if rel in completed:
            continue
        if len(completed)>=MAX_MODULES:
            raise NativeCaptureError('dependency census file bound exceeded')
        target = root/rel
        if target.is_symlink() or not target.is_file() or target.resolve()!=target:
            raise NativeCaptureError('source must be regular and local: ' + rel)
        raw=target.read_bytes()
        if len(raw)>MAX_SOURCE:
            raise NativeCaptureError('dependency source too large: ' + rel)
        try:
            tree=ast.parse(raw,filename=rel)
        except (SyntaxError,UnicodeError) as exc:
            raise NativeCaptureError('dependency AST parse failure: ' + rel) from exc
        module=rel[:-3].replace('/','.')
        names=_imports(tree,module)
        related=[]
        for name in names:
            f=_resolve(root,name)
            if f is None:
                continue
            dep=f.relative_to(root).as_posix()
            related.append(dep)
            if dep not in completed and not any(v[0]==dep for v in pending):
                if depth+1>MAX_DEPTH:
                    raise NativeCaptureError('dependency depth bound exceeded')
                pending.append((dep,depth+1))
        literal_keys=sorted({n.slice.value for n in ast.walk(tree)
                             if isinstance(n,ast.Subscript) and isinstance(n.slice,ast.Constant)
                             and type(n.slice.value) is str})[:120]
        completed[rel]={'path':rel,'source_sha256':hashlib.sha256(raw).hexdigest(),
                        'bytes':len(raw),'depth':depth,
                        'resolved_local_imports':sorted(set(related)),
                        'literal_subscript_keys':literal_keys}
    return {'schema':'spk-bv-native-dependency-census/v0k',
            'status':'STATIC_DEPENDENCY_ONLY',
            'files_scanned':len(completed),
            'files':[completed[k] for k in sorted(completed)],
            'limitations':['static imports only','no dynamic import resolution',
                           'transitive files not a signed attestation',
                           'not a native trace or v0h equivalence witness']}
