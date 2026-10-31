#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t10stu-vwx-yza-cumulative.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T10STU GATE FAIL CLOSED: REPORT_EXISTS' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-t10-native-surface-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/6] 21 source manifests, historical source pins, authenticated 12-source custody\n'
PYTHONPATH=. python3 - <<'PY'
import json
from pathlib import Path
from research.spk_v5_t10stu_vwx_yza.cumulative_surface_gate import sha,PARENT,PE_SHA,BV_SHA
from research.spk_v5_t5mno import t5mno
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
 't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
 't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza',
 't9abc_def_ghi','t9jkl_mno_pqr','t9stu_vwx_yza','t10abc_def_ghi',
 't10jkl_mno_pqr','t10stu_vwx_yza')
for name in names:
 p=Path('research')/('spk_v5_'+name)/'manifest.json'
 assert p.is_file() and not p.is_symlink(),'MISSING_MANIFEST '+name
 m=json.loads(p.read_bytes());assert m.get('promotion_allowed') is not True
 for rel,h in m['files'].items():
  f=Path(rel)
  assert f.is_file() and not f.is_symlink() and sha(f)==h,'SOURCE_SHA_DRIFT '+rel
 print('  PASS',name,len(m['files']))
assert sha('research/spk_v5_t10stu_vwx_yza/reference/t10jkl-mno-pqr-cumulative.json')==PARENT
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  genuine 12 original source pins and parent report SHA PASS')
PY
printf '[2/6] Genuine frozen BV-v0e preflight using fwork original dependencies\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
for c in (11,12):
 for g in (11,12):
  _,v=execute_raw(c,g)
  assert v['full_BV_scheduler'] and v['reverse_A_B_C'] and v['source_bv_deliveries']==2
_,v=execute_raw(12,11,drop_forward=True)
assert not v['reverse_A_B_C'] and v['source_bv_deliveries']==0
print('  authentic original BV admission PASS')
PY
printf '[3/6] 21 current and inherited test suites (no skipped regressions)\n'
for name in t10stu_vwx_yza t10jkl_mno_pqr t10abc_def_ghi t9stu_vwx_yza t9jkl_mno_pqr t9abc_def_ghi t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[4/6] Native Memory Contract surface discovery, previous byte parity, first report\n'
PYTHONPATH=. python3 -m research.spk_v5_t10stu_vwx_yza.cumulative_surface_gate --root . --out "$TMP/first.json"
printf '[5/6] Independent second report, byte exact and no-native assertions\n'
PYTHONPATH=. python3 -m research.spk_v5_t10stu_vwx_yza.cumulative_surface_gate --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
python3 - "$TMP/first.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]));a=x['T10STU'];b=x['T10VWX'];c=x['T10YZA']
assert a['native_surface']['native_memory_grant_executed'] is False
assert a['native_surface']['source_contract_api_authorized'] is False
assert b['native_memory_contract_call_count']==b['native_grants']==b['native_P_writes']==0
assert not b['reference_promotion_rejected']['promotion_allowed']
assert not b['host_claimed_native_promotion_rejected']['promotion_allowed']
assert [c['prior_results'][k]['successes'] for k in ('fixed_control','naive_three','context_affinity','serial')]==[48,84,88,88]
assert c['prior_report_regenerated_byte_exact']
assert (x['native_SPK_P_grants'],x['native_SPK_P_writes'],x['native_BV_semantic_deliveries'])==(0,0,0)
assert x['host_can_forge'] and not x['native_learning'] and not x['promotion_allowed']
print('  read-only API survey, exact T10 parity and no-native-promotion PASS')
PY
printf '[6/6] Frozen source pins and immutable publication\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t10stu_vwx_yza.cumulative_surface_gate import sha,PE_SHA,BV_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
PY
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
echo 'T10STU/VWX/YZA READ-ONLY NATIVE MEMORY CONTRACT SURFACE READINESS PASS; ZERO NATIVE SPK BV OR LEARNING'
