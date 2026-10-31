#!/usr/bin/env bash
# Source-pinned original T3OPQ rerun; never promotes native learning.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE="$ROOT/research/spk_v5_t3uvw"
OUT="${1:-/tmp/spk-v5-t3uvw-source-custody.json}"
mkdir -p "$(dirname "$OUT")"

echo '[1/5] Inherited T3RST 36 unit and adversarial tests'
python3 -m unittest discover -s "$ROOT/research/spk_v5_t3rst/tests" -q

echo '[2/5] T3UVW 29 source-custody and adversarial tests'
python3 -m unittest discover -s "$BUNDLE/tests" -q

echo '[3/5] Rerun original T3OPQ twice, pinned against legacy BV-v0e source hashes'
python3 "$BUNDLE/t3uvw.py" --repo "$ROOT" --output "$OUT"

echo '[4/5] Verify no native promotion and exact report references'
python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert r['promotion_allowed'] is False
assert r['U_frozen_source']['verified_legacy_pins'] is True
assert r['U_frozen_source']['unchanged_during_reexecution'] is True
assert r['V_original_gate']['comparison']['exact_json_equal'] is True
assert r['V_original_gate']['invocations']==2
assert r['W_causal_boundary']['dual_replay_confirmed'] is True
assert r['W_causal_boundary']['native_single_pass_C_verdict_evidence'] is False
assert r['W_causal_boundary']['native_semantic_BV_proven'] is False
assert r['W_causal_boundary']['native_learning_proven'] is False
print('T3UVW ASSERTIONS PASS: source-pinned original producer, research-only nonpromotion')
PY

echo '[5/5] Output integrity'
sha256sum "$OUT" "${OUT%.json}-original-1.json" "${OUT%.json}-original-2.json"
echo "T3UVW SOURCE CUSTODY GATE COMPLETE: $OUT"
