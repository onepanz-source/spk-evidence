"""SPK 24l: cooperative offline source pin and live single-writer lease.

The source digest detects accidental source drift in an explicitly trusted local
Python installation. It is NOT producer authentication or a Python sandbox.
The POSIX flock prevents overlapping executions only while participating
processes keep their lease on the SAME local lock file. It cannot prevent
sequential replay, file removal, nonparticipating writers or host crashes.
Neither operation spends a SPK SERVICE_TIME quantum.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import stat
from typing import Any


class SourcePinErrorV0(ValueError):
    """Unpinned, changed or noncanonical local source."""


class EpochLeaseBusyV0(RuntimeError):
    """Another cooperative process owns the local live epoch lease."""


class EpochLeasePolicyErrorV0(ValueError):
    """The caller supplied an unsafe or unsupported lease namespace."""


def _hex_sha256(value: str) -> bool:
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def source_file_sha256_v0(path: str | Path) -> str:
    """SHA256 of exactly the supplied local file's bytes (not its identity)."""
    candidate = Path(path)
    if not candidate.is_file():
        raise SourcePinErrorV0('provider source file does not exist')
    return hashlib.sha256(candidate.read_bytes()).hexdigest()


def resolve_pinned_factory_v0(spec: str, expected_sha256: str):
    """Resolve operator-chosen local code and check its source file digest.

    Imports can execute trusted package code *before* the check. Only use with
    an operator-managed Python environment and pre-approved factory path.
    The factory body is NOT called here. No anti-TOCTOU security guarantee.
    """
    if type(spec) is not str or spec.count(':') != 1:
        raise SourcePinErrorV0('provider must be module.path:factory')
    module_name, function_name = spec.split(':')
    if (not module_name or not all(x.isidentifier() for x in module_name.split('.'))
            or not function_name.isidentifier()):
        raise SourcePinErrorV0('invalid provider path')
    if not _hex_sha256(expected_sha256):
        raise SourcePinErrorV0('expected SHA256 must be 64 lowercase hex characters')
    module = importlib.import_module(module_name)
    factory = getattr(module, function_name, None)
    if not callable(factory):
        raise SourcePinErrorV0('factory is not callable')
    if getattr(factory, '__module__', None) != module_name:
        raise SourcePinErrorV0('factory is not defined in the pinned module')
    path = getattr(module, '__file__', None)
    if type(path) is not str or not path.endswith('.py'):
        raise SourcePinErrorV0('factory module has no canonical .py source')
    actual = source_file_sha256_v0(path)
    if actual != expected_sha256:
        raise SourcePinErrorV0('provider source SHA256 mismatch')
    return factory


def result_fingerprint_v0(result: Any) -> str:
    """Stable SHA256 over 24k's canonical public OfflineEpochResult fields.

    Not a digest of the complete neuron trace or an integrity signature.
    Distinct executions may share this digest despite different internal work.
    """
    required = (
        'provider_id', 'epoch_id', 'phase', 'completed', 'revision',
        'next_service_tick', 'actions', 'service_ticks_spent', 'handoffs',
        'old_version', 'new_version',
    )
    if any(not hasattr(result, field) for field in required):
        raise TypeError('result lacks canonical offline summary fields')
    values = {name: getattr(result, name) for name in required}
    if (any(type(values[k]) is not int or values[k] < 0 for k in
            ('revision', 'next_service_tick', 'actions', 'service_ticks_spent', 'handoffs'))
            or type(values['completed']) is not bool
            or any(type(values[k]) is not str or not values[k] for k in ('provider_id', 'epoch_id', 'phase'))
            or any(values[k] is not None and type(values[k]) is not int for k in ('old_version', 'new_version'))):
        raise TypeError('noncanonical offline result summary')
    encoded = json.dumps(values, sort_keys=True, ensure_ascii=True,
                         allow_nan=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(b'spk-offline-result/v0\x00' + encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class LocalEpochLeaseV0:
    """A handle kept alive by `with` for one cooperative local execution.

    Lock-file paths are stable hashes of exact epoch IDs within an operator-
    created private namespace. No automatic mkdir or file removal occurs.
    """
    epoch_id: str
    lock_dir: str
    _fd: int | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.epoch_id) is not str or not self.epoch_id:
            raise EpochLeasePolicyErrorV0('epoch ID required')
        if type(self.lock_dir) is not str or not self.lock_dir:
            raise EpochLeasePolicyErrorV0('private lock directory required')

    def __enter__(self):
        if self._fd is not None:
            raise EpochLeasePolicyErrorV0('lease handle cannot be acquired twice')
        directory = Path(self.lock_dir)
        info = directory.lstat()  # Symlinked directory is never accepted.
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o700):
            raise EpochLeasePolicyErrorV0('lease directory must be owned by this user and mode 0700')
        name = hashlib.sha256(self.epoch_id.encode('utf-8')).hexdigest() + '.lock'
        path = directory / name
        flags = os.O_RDWR | os.O_CREAT | os.O_CLOEXEC
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        try:
            locked = os.fstat(fd)
            if (not stat.S_ISREG(locked.st_mode) or locked.st_uid != os.geteuid()
                    or stat.S_IMODE(locked.st_mode) != 0o600
                    or locked.st_nlink != 1):
                raise EpochLeasePolicyErrorV0('unsafe lease file')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise EpochLeaseBusyV0('epoch already executing in the local lease namespace') from exc
            # The path must not have been replaced between open and acquisition.
            actual = path.stat()
            if (actual.st_dev, actual.st_ino) != (locked.st_dev, locked.st_ino):
                raise EpochLeasePolicyErrorV0('lease path replaced during acquisition')
            object.__setattr__(self, '_fd', fd)
            return self
        except BaseException:
            os.close(fd)
            raise

    def __exit__(self, exc_type, exc, tb):
        fd = self._fd
        if fd is None:
            raise EpochLeasePolicyErrorV0('lease handle was not acquired')
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
            object.__delattr__(self, '_fd')
        return False
