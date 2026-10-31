#!/usr/bin/env bash
# Read-only T4ABC research checkpoint. No original producer rerun.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${1:-/tmp/spk-v5-t4abc-causal-origin.json}"
RECOVERY="${2:-/tmp/spk-v5-t3xyz-trace-recovery.json}"
TRACE="${3:-$HOME/workspace/spk-evidence/spk-v5-t3xyz-20261021/spk-v5-t3xyz-passive-observation-profile.jsonl}"
BUNDLE="${4:-$HOME/workspace/spk-evidence/spk-v5-t4abc-source-bundle.tar.gz}"
mkdir -p "$(dirname "$REPORT")" "$(dirname "$BUNDLE")"
echo '[1/4] Verify T4ABC test suite (read-only and adversarial)'
python3 -m unittest discover -s "$ROOT/research/spk_v5_t4abc/tests" -v
echo '[2/4] Validate T3XYZ recovery + 47 MB trace + frozen source pins'
echo '[3/4] Localize original C / BV bridge source boundaries and package allowlisted sources'
python3 "$ROOT/research/spk_v5_t4abc/t4abc.py" \
 --repo "$ROOT" --recovery "$RECOVERY" --trace "$TRACE" \
 --output "$REPORT" --bundle "$BUNDLE"
echo '[4/4] Final nonpromotion assertion and SHA256'
python3 - "$REPORT" "$BUNDLE" <<'PY'
import hashlib,json,sys
from pathlib import Path
report=Path(sys.argv[1]);bundle=Path(sys.argv[2]);r=json.loads(report.read_text())
assert r['promotion_allowed'] is False
assert r['single_pass_C_authored_semantic_verdict_proven'] is False
assert r['native_semantic_BV_proven'] is False
assert r['native_learning_proven'] is False
assert r['C_observed_profile']['coverage_complete'] is False
assert r['source_bundle']['sha256']==hashlib.sha256(bundle.read_bytes()).hexdigest()
assert not r['A_evidence_custody']['frozen_source_changed']
print('T4ABC RESEARCH-ONLY NONPROMOTION PASS')
PY
sha256sum "$REPORT" "$BUNDLE"
echo "T4ABC COMPLETE: $REPORT"
