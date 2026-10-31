#!/usr/bin/env bash
# Source-pinned A-local research-only outcome prototype; no native BV promotion.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t5mno-A-local-outcome.json}"
[[ ! -e "$OUT" ]] || { echo "T5MNO FAIL CLOSED: OUTPUT_ALREADY_EXISTS $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-v5-t5mno-XXXXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] Incremental manifests and original frozen source custody\n'
PYTHONPATH=. python3 - <<'PYMANIFEST'
import json,hashlib
from pathlib import Path
from research.spk_v5_t5mno import t5mno
for name in ('t5abc','t5def','t5ghi','t5jkl','t5mno'):
    p=Path(f'research/spk_v5_{name}/manifest.json')
    if not p.is_file() or p.is_symlink():raise SystemExit('T5MNO FAIL CLOSED: missing manifest '+str(p))
    m=json.loads(p.read_bytes())
    for path,expected in m['files'].items():
        q=Path(path)
        if not q.is_file() or q.is_symlink() or hashlib.sha256(q.read_bytes()).hexdigest()!=expected:
            raise SystemExit('T5MNO FAIL CLOSED: source pin drift '+path)
    print('  ',name,'manifest PASS',len(m['files']))
print('  original source pins',t5mno.t5jkl.custody('.',True)['original_source_pins'],'PASS')
PYMANIFEST
printf '[2/8] New T5MNO A-local and adversarial unit tests\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t5mno/tests -q
printf '[3/8] Inherited T5JKL + T5GHI + T5DEF tests\n'
for id in t5jkl t5ghi t5def; do PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${id}/tests" -q; done
printf '[4/8] Inherited T5ABC + T4ZABC tests\n'
for id in t5abc t4zabc; do PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${id}/tests" -q; done
printf '[5/8] Process-isolated A-local 180-case judgment round 1\n'
PYTHONPATH=. python3 -m research.spk_v5_t5mno.t5mno --root . --out "$TMP/first.json"
printf '[6/8] Independent process A-local 180-case judgment round 2\n'
PYTHONPATH=. python3 -m research.spk_v5_t5mno.t5mno --root . --out "$TMP/second.json"
printf '[7/8] Exact reproducibility and mandatory nonpromotion\n'
cmp -- "$TMP/first.json" "$TMP/second.json"
python3 - "$TMP/first.json" <<'PYVERIFY'
import json,sys
v=json.load(open(sys.argv[1]))
assert (v['cases'],v['A_local_synthetic_observations'],v['A_paired_research_outcomes'])==(180,180,72)
assert v['A_local_outcomes']=={'IMPROVED':60,'WORSENED':60,'UNCHANGED':60}
assert v['paired_outcomes']=={'IMPROVED':24,'WORSENED':24,'UNCHANGED':24}
assert v['A_research_guard_candidates']==24 and v['A_source_fault_receipts']==48 and v['A_paired_without_frozen_emission_chain']==24
assert len(v['C_sign_cross_tab'])==6 and all(x['count']==12 for x in v['C_sign_cross_tab'])
assert v['host_can_forge_A_measurement'] is True and v['host_can_forge_C_result'] is True
assert v['A_sensor_source_authenticated'] is False and v['A_C_causal_attribution_proven'] is False
assert v['native_BV_credit']==0 and v['native_learning'] is False and v['promotion_allowed'] is False
assert v['new_PE_calls']==0 and v['new_frozen_scheduler_calls']==0
assert len(v['rows'])==180 and all(not x['A_causal_attribution_to_C'] and not x['A_to_C_credit'] for x in v['rows'])
print('T5MNO 180 A-LOCAL SYNTHETIC OBSERVATIONS, 72 RESEARCH PAIRS, 0 NATIVE CAUSAL BV')
PYVERIFY
printf '[8/8] Seal result and print SHA-256\n'
mkdir -p -- "$(dirname "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
echo 'T5MNO A-LOCAL STRUCTURAL JUDGMENT RESEARCH PASS; NO AUTHENTICATED SENSOR, CAUSAL BV OR LEARNING'
