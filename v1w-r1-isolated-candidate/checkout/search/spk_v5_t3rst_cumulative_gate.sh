#!/usr/bin/env bash
# SPK V5 T3RST cumulative research gate. Does not modify frozen SPK modules.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE="$ROOT/research/spk_v5_t3rst"
REPORT="${1:-/tmp/spk-v5-t3rst-cumulative-research.json}"
T3OPQ_REPORT="${2:-/tmp/spk-v5-t3opq-source-bv-credit.json}"
SILENT_REPORT="${REPORT%.json}-silent.json"

if [[ ! -f "$T3OPQ_REPORT" ]]; then
    echo "ERROR: T3OPQ report not found: $T3OPQ_REPORT" >&2
    echo "Run the T3OPQ gate first, or supply its report as second argument." >&2
    exit 2
fi
if [[ ! -f "$BUNDLE/src/spk_t3rst.py" ]]; then
    echo "ERROR: T3RST checkpoint files are missing under $BUNDLE" >&2
    exit 2
fi
mkdir -p "$(dirname "$REPORT")"

echo '[1/4] T3RST 36 structural and adversarial research tests'
python3 -m unittest discover -s "$BUNDLE/tests" -v

echo '[2/4] T3R report consistency + T3S single-pass + T3T causal cut'
PYTHONPATH="$BUNDLE/src" python3 "$BUNDLE/src/spk_t3rst.py" \
  --reference-report "$T3OPQ_REPORT" \
  --trace "$BUNDLE/fixtures/single_pass_positive.json" \
  --alternate-trace "$BUNDLE/fixtures/single_pass_negative_future.json" \
  --output "$REPORT"

echo '[3/4] Silent-action negative control'
PYTHONPATH="$BUNDLE/src" python3 "$BUNDLE/src/spk_t3rst.py" \
  --trace "$BUNDLE/fixtures/single_pass_silent.json" \
  --output "$SILENT_REPORT"

echo '[4/4] Assert research-only nonpromotion and report integrity'
python3 - "$REPORT" "$SILENT_REPORT" <<'PY'
import json, sys
from pathlib import Path
main = json.loads(Path(sys.argv[1]).read_text())
silent = json.loads(Path(sys.argv[2]).read_text())
expected = {
    'R_reference_consistency': 'REPORT_INTERNAL_CONSISTENCY_PASS',
    'S_single_pass': 'SHADOW_CAUSAL_ORDER_PASS',
    'T_causal_cut': 'SHADOW_CAUSAL_CUT_PASS',
}
assert {k: main['gates'][k]['outcome'] for k in expected} == expected
assert main['gates']['S_single_pass']['source_structural_credit_events'] == 1
assert main['gates']['T_causal_cut']['different_future_episodes'] == 1
assert silent['gates']['S_single_pass']['source_structural_credit_events'] == 0
for output in (main, silent):
    assert output['overall'] == 'RESEARCH_ONLY_SOURCE_BOUND_UNVERIFIED'
    assert output['promotion_allowed'] is False
    assert output['no_native_learning'] and output['no_native_semantic_BV']
    assert output['no_authenticated_C_sensor'] and output['no_blind_evaluation']
assert main['gates']['R_reference_consistency']['source_sha_verified'] is False
print('T3RST CUMULATIVE RESEARCH GATE PASS: R/S/T + SILENCE; NO NATIVE PROMOTION')
PY
sha256sum "$REPORT" "$SILENT_REPORT"
echo "Reports: $REPORT ; $SILENT_REPORT"
