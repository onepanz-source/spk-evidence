#!/usr/bin/env bash
# Research-only incremental recovery from already collected T3XYZ evidence.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-/tmp/spk-v5-t3xyz-trace-recovery.json}"
PREFIX="${2:-/tmp/spk-v5-t3xyz-passive-observation}"
if [[ "$OUT" != /* || "$PREFIX" != /* ]]; then
    echo 'FAIL CLOSED: output and original prefix must be absolute paths' >&2; exit 3
fi
mkdir -p "$(dirname "$OUT")"
echo '[1/4] Inherited T3XYZ 16 instrument/false-promotion tests'
python3 -m unittest discover -s "$ROOT/research/spk_v5_t3xyz/tests" -q
echo '[2/4] Trace-volume streaming and adversarial tests'
python3 -m unittest discover -s "$ROOT/research/spk_v5_t3xyz_recovery/tests" -q
echo '[3/4] Audit original T3OPQ and 47MB CPython evidence without producer replay'
python3 "$ROOT/research/spk_v5_t3xyz_recovery/trace_recovery.py" \
    --repo "$ROOT" \
    --trace "${PREFIX}-profile.jsonl" \
    --producer "${PREFIX}-original.json" \
    --log "${PREFIX}-original.log" \
    --output "$OUT"
echo '[4/4] Assert nonpromotion and report integrity'
python3 - "$OUT" <<'PY'
import sys,json
from pathlib import Path
s=json.loads(Path(sys.argv[1]).read_text())
assert s['promotion_allowed'] is False
assert s['native_single_pass_C_verdict_proven'] is False
assert s['native_semantic_BV_proven'] is False
assert s['native_learning_proven'] is False
assert s['passive_profile']['complete_execution_coverage_proven'] is False
assert s['original_T3OPQ']['producer_report_sha256']=='813753afd706eabff52653cf0a7674e1a44755981df61c6760fcbd4652c790d2'
assert s['passive_profile']['event_counts']['compute_call']>0
print('T3XYZ TRACE RECOVERY RESEARCH-ONLY BOUNDARY PASS')
PY
sha256sum "$OUT" "${PREFIX}-original.json" "${PREFIX}-profile.jsonl"
echo "T3XYZ RECOVERY COMPLETE: $OUT"
