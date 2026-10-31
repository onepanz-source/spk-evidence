#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t11-macro-owned-memory-v1.json}"
PREV="$HOME/workspace/spk-evidence/spk-v5-t10stu-vwx-yza-cumulative.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T11 MACRO FAIL CLOSED: REPORT_ALREADY_EXISTS' >&2; exit 3; }
[[ -f "$PREV" && ! -L "$PREV" ]] || { echo 'T11 MACRO FAIL CLOSED: MISSING_GENUINE_T10STU_FWORK_REPORT' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-v5-t11-macro-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/7] Parent fwork evidence and frozen source custody\n'
PYTHONPATH=. python3 - "$PREV" <<'PY'
import json,sys
from pathlib import Path
from research.spk_v5_t11_macro_memory_v1.macro_gate import sha,T10_READINESS_FWORK_SHA,PE_SHA,BV_SHA
assert sha(sys.argv[1])==T10_READINESS_FWORK_SHA, 'T10_READINESS_REPORT_SHA_DRIFT'
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
 't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
 't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza',
 't9abc_def_ghi','t9jkl_mno_pqr','t9stu_vwx_yza','t10abc_def_ghi',
 't10jkl_mno_pqr','t10stu_vwx_yza','t11_macro_memory_v1')
for name in names:
 p=Path('research')/('spk_v5_'+name)/'manifest.json'
 assert p.is_file() and not p.is_symlink(),f'MISSING_MANIFEST:{name}'
 m=json.loads(p.read_text());assert m.get('promotion_allowed') is not True, name
 for rel,pinned in m['files'].items():
  f=Path(rel);assert f.is_file() and not f.is_symlink() and sha(f)==pinned,f'SHA_DRIFT:{rel}'
print('  22 manifests and all additive file pins PASS')
from research.spk_v5_t5mno import t5mno
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  12 authenticated frozen original file hashes PASS')
PY
printf '[2/7] Genuine BV-v0e preflight using original fwork admission dependencies\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
for c in (11,12):
 for g in (11,12):
  _,v=execute_raw(c,g)
  assert v['full_BV_scheduler'] and v['reverse_A_B_C'] and v['source_bv_deliveries']==2
_,v=execute_raw(12,11,drop_forward=True)
assert not v['reverse_A_B_C'] and v['source_bv_deliveries']==0
print('  true frozen BV runtime preflight PASS')
PY
printf '[3/7] All 22 cumulative test suites, never skip old regressions\n'
for name in t11_macro_memory_v1 t10stu_vwx_yza t10jkl_mno_pqr t10abc_def_ghi t9stu_vwx_yza t9jkl_mno_pqr t9abc_def_ghi t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[4/7] Integrated new-runtime V1 authority, cumulative reference, first report\n'
PYTHONPATH=. python3 -m research.spk_v5_t11_macro_memory_v1.macro_gate --root . --parent-readiness "$PREV" --out "$TMP/first.json"
printf '[5/7] Independent second report, byte equality, explicit frozen-native denial\n'
PYTHONPATH=. python3 -m research.spk_v5_t11_macro_memory_v1.macro_gate --root . --parent-readiness "$PREV" --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
python3 - "$TMP/first.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert [r['scenarios'][s]['successes'] for s in ('control','naive_three','context_affinity','serial')]==[48,84,88,88]
assert [r['scenarios'][s]['owned_memory']['new_v1_memory_grants'] for s in ('control','naive_three','context_affinity','serial')]==[0,8,8,8]
assert r['new_versioned_runtime_v1_P_grants']==r['new_versioned_runtime_v1_P_writes']==8
assert r['original_native_SPK_P_grants']==r['original_native_SPK_P_writes']==r['original_native_SPK_BV_semantic_deliveries']==0
assert not r['original_native_SPK_learning'] and not r['promotion_to_frozen_SPK_allowed']
assert r['macro_workstreams']['M6_legacy_compatibility_and_native_boundary']['T10_readiness_verified_in_full_gate']
assert r['macro_workstreams']['M5_recovery_and_adversarial']['host_still_controls_runtime_and_can_reseal']
print('  6 macro workstreams, parity, original SPK deny, replay/recovery PASS')
PY
printf '[6/7] Frozen source hash recheck\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t11_macro_memory_v1.macro_gate import sha,PE_SHA,BV_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
print('  no frozen source modification PASS')
PY
printf '[7/7] Immutable report publication\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
echo 'T11 MACRO OWNED MEMORY V1 REFERENCE EXECUTION PASS; 8 NEW-V1 GRANTS, ZERO FROZEN SPK NATIVE LEARNING'
