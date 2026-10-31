"""Additive V5-T3b ingress for the authentic UCI CSV's unnamed row-index column.

The T3a source, pinned manifest and frozen architecture are NOT modified.
Do not expose id or occupancy label to A's sensor input. No native learning.
"""
from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from math import isfinite
from pathlib import Path

from spk_v5_research.island_external_task_v5t3a import (
    DatasetRow, FEATURE_FIELDS, sha_bytes,
)

SCHEMA = 'spk-v5-t3b-authentic-uci-row-index/research-v0'


def read_authentic_uci(path: Path, *, expected_filename: str) -> tuple[tuple[DatasetRow, ...], str]:
    """Parse original UCI bytes (7-cell header + 8-cell indexed records).

    Reject malformed/index-spoofed/unsorted records; SHA binds ORIGINAL bytes.
    No automatic header modification, synthetic observations, or label repair.
    """
    if (not isinstance(path, Path) or path.is_symlink() or not path.is_file()
            or path.name != expected_filename
            or expected_filename not in ('datatraining.txt', 'datatest.txt', 'datatest2.txt')):
        raise ValueError('wrong or unsafe original UCI input')
    size = path.stat().st_size
    if not 120 < size < 2_000_000:
        raise ValueError('empty or unbounded original source')
    raw = path.read_bytes()
    if b'\x00' in raw:
        raise ValueError('binary source rejected')
    try:
        reader = csv.reader(StringIO(raw.decode('utf-8-sig'), newline=''), strict=True)
        header = next(reader)
        if tuple(header) != FEATURE_FIELDS:
            raise ValueError('unrecognized original UCI header')
        output=[]
        previous_time=None
        previous_id=None
        for row in reader:
            if len(row)!=8 or any(not cell.strip() for cell in row):
                raise ValueError('record must have 8 cells including unnamed ID')
            id_str=row[0]
            if not id_str.isascii() or not id_str.isdecimal() or id_str.startswith('0'):
                raise ValueError('invalid source record ID')
            record_id=int(id_str)
            if record_id <= 0 or (previous_id is not None and record_id!=previous_id+1):
                raise ValueError('nonconsecutive source record IDs')
            previous_id=record_id
            stamp=row[1]
            dt=datetime.strptime(stamp,'%Y-%m-%d %H:%M:%S')
            if previous_time is not None and dt<=previous_time:
                raise ValueError('nonmonotone timestamp')
            previous_time=dt
            # Check every measured field: leave unused fields entirely out of A's input.
            measures=tuple(float(x) for x in row[2:7])
            if not all(map(isfinite, measures)):
                raise ValueError('nonfinite sensor reading')
            temp,humidity,light,co2,ratio=measures
            if not (-50 <= temp <= 100 and 0 <= humidity <= 100 and
                    0 <= light <= 200_000 and 0 < co2 <= 100_000 and 0 <= ratio < 1):
                raise ValueError('out-of-domain sensor reading')
            if row[7] not in ('0','1'):
                raise ValueError('invalid occupancy target')
            output.append(DatasetRow(stamp,light,co2,row[7]=='1'))
            if len(output)>25_000:
                raise ValueError('record count limit exceeded')
    except (ValueError, UnicodeError, TypeError, OverflowError, csv.Error, StopIteration) as exc:
        raise ValueError(f'original UCI data rejected: {exc}') from exc
    if len(output)<30:
        raise ValueError('not enough original UCI records')
    return tuple(output), sha_bytes(raw)
