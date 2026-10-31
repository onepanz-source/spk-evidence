#!/usr/bin/env bash
# T4DEF additive research-only gate, no code mutation, no scheduler replacements.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

OUT="${1:-/tmp/spk-v5-t4def-single-source.json}"
DOSSIER="${2:-/tmp/spk-v5-t4abc-causal-origin.json}"
PY=research/spk_v5_t4def/t4def.py
[[ ! -e "$OUT" ]] || { echo 'T4DEF FAIL CLOSED: OUTPUT_ALREADY_EXISTS' >&2; exit 3; }
[[ -f "$DOSSIER" ]] || { echo "T4DEF FAIL CLOSED: T4ABC_DOSSIER_MISSING:$DOSSIER" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-v5-t4def-gate-XXXXXX)
trap 'rm -rf -- "$TMP"' EXIT

printf '[1/6] Research-only unit/negative suite (real BV not exercised in unit tests)\n'
python3 -m unittest discover -s research/spk_v5_t4def/tests -v
printf '[2/6] Source SHA pins and original dual-replay AST custody\n'
PYTHONPATH=. python3 - "$DOSSIER" <<'PY'
import sys
from pathlib import Path
from research.spk_v5_t4def.t4def import verify_custody,dual_replay_locus
verify_custody(Path('.'),Path(sys.argv[1]))
x=dual_replay_locus(Path('spk_v5_research/island_source_bv_bridge_v5t3o.py'))
assert x['original_calls_two_source_passes'] and x['posthoc_sign_selection']
print('original host dual-pass locus verified: line',x['line'])
PY
printf '[3/6] T4E single BV invocation per case (static terminal, T3h separate)\n'
PYTHONPATH=. python3 "$PY" --root . --dossier "$DOSSIER" --out "$TMP/first.json"
printf '[4/6] Independent process determinism / source pins\n'
PYTHONPATH=. python3 "$PY" --root . --dossier "$DOSSIER" --out "$TMP/second.json"
cmp "$TMP/first.json" "$TMP/second.json"
printf '[5/6] Nonpromotion, parity, no forged semantic sign\n'
if ! python3 - "$TMP/first.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['E_one_source_BV_invocation_per_case'] is True
assert r['E_separate_T3h_A1b_invocation_per_case'] is True
assert r['E_source_receives_semantic_sign'] is False
assert r['F_case_count']==180 and r['F_reference_structural_parity'] is True and r['F_research_structural_eligible']==42 and r['F_rejected']==138
assert r['F_semantic_sign_counts']=={'-1':36,'1':36}
assert (r['native_semantic_BV_proven'],r['native_learning_proven'],r['single_native_semantic_execution_proven'],r['promotion_allowed'])==(False,False,False,False)
assert len(r['F_cases'])==180 and all(x['source_transmits_semantic_sign'] is False for x in r['F_cases'])
print('Research structural parity verified, semantic BV not promoted')
PY
then
  DIAG="${OUT%.json}-diagnostic.json"
  if [[ ! -e "$DIAG" ]]; then cp -- "$TMP/first.json" "$DIAG"; fi
  echo "T4DEF FAIL CLOSED: structural parity, see $DIAG" >&2
  exit 3
fi
printf '[6/6] Persist report and SHA256\n'
mkdir -p "$(dirname "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum "$OUT"
printf 'T4DEF SINGLE BV INVOCATION STRUCTURAL RESEARCH PASS; NO NATIVE SEMANTIC BV OR LEARNING\n'
