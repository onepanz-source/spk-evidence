#!/usr/bin/env bash
# Incremental checkpoint: inspect original source without editing frozen SPK files.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-/tmp/spk-v5-t3xyz-passive-observation.json}"
mkdir -p "$(dirname "$OUT")"
echo '[1/5] Inherited T3RST causal boundary tests'
python3 -m unittest discover -s "$ROOT/research/spk_v5_t3rst/tests" -q
echo '[2/5] Inherited T3UVW source custody tests'
python3 -m unittest discover -s "$ROOT/research/spk_v5_t3uvw/tests" -q
echo '[3/5] T3XYZ instrument/false-promotion adversarial tests'
python3 -m unittest discover -s "$ROOT/research/spk_v5_t3xyz/tests" -q
echo '[4/5] Passive CPython probe of actual T3OPQ launcher + byte-exact comparison'
python3 "$ROOT/research/spk_v5_t3xyz/t3xyz.py" --repo "$ROOT" --output "$OUT"
echo '[5/5] Audit invariants, report integrity, source unchanged'
python3 - "$OUT" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);r=json.loads(p.read_text())
assert r['promotion_allowed'] is False
assert r['Y_source_parity']['source_unchanged'] is True
assert r['Y_source_parity']['byte_identical_to_reference'] is True
assert r['Z_causal_semantic_boundary']['native_C_authored_single_pass_verdict_proven'] is False
assert r['Z_causal_semantic_boundary']['native_BV_semantic_receipt_proven'] is False
assert r['Z_causal_semantic_boundary']['native_operator_update_proven'] is False
assert r['X_passive_instrumentation']['events']['probe_loaded'] > 0
print('T3XYZ RESEARCH-ONLY BOUNDARY PASS')
PY
sha256sum "$OUT" "${OUT%.json}-original.json" "${OUT%.json}-profile.jsonl"
echo "T3XYZ PASSIVE OBSERVATION GATE COMPLETE: $OUT"
