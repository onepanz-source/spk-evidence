#!/usr/bin/env bash
# Cumulative incremental source observation gate. No writes to frozen files.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-/tmp/spk-v5-t4ghi-one-pass-sign.json}"
REF="research/spk_v5_t4ghi/reference/t4def-single-source.json"
PY="research/spk_v5_t4ghi/t4ghi.py"

[[ ! -e "$OUT" ]] || { echo "T4GHI FAIL CLOSED: OUTPUT_ALREADY_EXISTS: $OUT" >&2; exit 3; }
[[ -f "$REF" ]] || { echo 'T4GHI FAIL CLOSED: BUNDLED_REFERENCE_MISSING' >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-t4ghi-gate-XXXXXX)
trap 'rm -rf -- "$TMP"' EXIT

printf '[1/6] Inherited T4DEF regression suite\n'
python3 -m unittest discover -s research/spk_v5_t4def/tests -v
printf '[2/6] New T4GHI offline and adversarial suite\n'
python3 -m unittest discover -s research/spk_v5_t4ghi/tests -v
printf '[3/6] SHA custody and structural nonidentifiability of fixed-terminal projection\n'
PYTHONPATH=. python3 - "$REF" <<'PY'
import sys
from pathlib import Path
from research.spk_v5_t4ghi.t4ghi import read_reference,structural_nonidentifiability,custody
r=read_reference(Path(sys.argv[1])); p=structural_nonidentifiability(r['F_cases']);pins=custody(Path('.'))
assert p['historical_sign_rows']==72 and p['groups_with_both_signs']==20
print('source pins',len(pins),'72 sign observations; ambiguous structural signatures',p['groups_with_both_signs'])
PY
printf '[4/6] 180 source executions: single BV call per case, NO separate A1b verdict run\n'
PYTHONPATH=. python3 "$PY" --root . --reference "$REF" --out "$TMP/output.json"
printf '[5/6] Strict source parity / nonpromotion assertions\n'
python3 - "$TMP/output.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['status']=='SINGLE_SOURCE_SIGN_VISIBILITY_RESEARCH_ONLY'
assert r['G_single_BV_per_case'] is True and r['G_separate_A1b_verdict_execution'] is False
assert r['H_count']==180 and len(r['H_rows'])==180
assert all(r[k] is True for k in ('I_no_native_semantic_BV','I_no_signed_sensor','I_no_native_learning','I_no_blind'))
assert r['promotion_allowed'] is False
assert all(row['source_terminal_only_does_not_encode_sign'] is True and row['signed_C_to_A_native_BV_receipt_proven'] is False for row in r['H_rows'])
assert sum(r['H_statuses'].get(n,0) for n in ('SAME_SOURCE_EMISSION_CANDIDATE','SOURCE_SIGN_NOT_EXPOSED'))==180
assert r['D_structure_nonidentifiability']['groups_with_both_signs']==20
print('180/180 source-byte parity; visibility is not authenticated native semantic BV')
PY
printf '[6/6] Persist exact report and SHA256\n'
mkdir -p "$(dirname "$OUT")"
cp -- "$TMP/output.json" "$OUT"
sha256sum "$OUT"
echo 'T4GHI RESEARCH GATE PASS; SINGLE SOURCE OBSERVATION ONLY; NO NATIVE SEMANTIC BV OR LEARNING'
