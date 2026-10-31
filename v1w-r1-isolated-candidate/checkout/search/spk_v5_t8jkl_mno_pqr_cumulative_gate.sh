#!/usr/bin/env bash
# T8JKL/MNO/PQR: new reference v1 semantic bus + P authority, NOT native SPK.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t8jkl-mno-pqr-v1-reference.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T8 V1 REFERENCE FAIL CLOSED: REPORT_EXISTS' >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-t8-v1-reference-XXXXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/7] Verify 14 incremental manifests, reference report, frozen PE/BV and 12 original source pins\n'
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
import json
from research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate import sha,PE_SHA,BV_SHA,REFERENCE_T8_SHA
from research.spk_v5_t5mno import t5mno
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
    't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
    't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr')
for name in names:
    path=Path('research')/f'spk_v5_{name}'/'manifest.json'
    assert path.is_file() and not path.is_symlink(),'MISSING_MANIFEST '+name
    m=json.loads(path.read_bytes());assert m.get('promotion_allowed') is not True
    for rel,reference in m['files'].items():
        p=Path(rel)
        assert p.is_file() and not p.is_symlink() and sha(p)==reference,'SOURCE_DRIFT '+rel
    print('  PASS',name,len(m['files']))
assert sha('research/spk_v5_t8jkl_mno_pqr/reference/t8abc-def-ghi.json')==REFERENCE_T8_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  original frozen pins and T8 reference SHA PASS')
PY
printf '[2/7] Authentic frozen admission/scheduler preflight (no local stubs allowed)\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
for c in (11,12):
 for goal in (11,12):
  src,ev=execute_raw(c,goal)
  assert ev['full_BV_scheduler'] and ev['reverse_A_B_C'] and ev['source_bv_deliveries']==2
src,ev=execute_raw(12,11,drop_forward=True)
assert not ev['reverse_A_B_C'] and ev['source_bv_deliveries']==0
print('  5 genuine original BV epochs PASS')
PY
printf '[3/7] New semantic/P authority tests + inherited milestone regressions\n'
for name in t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
    PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[4/7] Full original 216 BV epoch executions with new v1 bus & reference P authority\n'
PYTHONPATH=. python3 -m research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate --root . --out "$TMP/first.json"
printf '[5/7] Independent full rerun and exact deterministic report comparison\n'
PYTHONPATH=. python3 -m research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
printf '[6/7] Assert 48/88/0 parity, 8 reference grants and 0 native grants + host forgery\n'
python3 - "$TMP/first.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
c=r['T8PQR']['baseline_96'];a=r['T8PQR']['adaptive_96'];d=r['T8PQR']['lost_forward_24']
assert (c['successes'],a['successes'],d['successes'])==(48,88,0)
assert (c['reference_v1_P_grants'],a['reference_v1_P_grants'],d['reference_v1_P_grants'])==(0,8,0)
assert a['reference_v1_P_writes']==8 and a['reference_v1_semantic_receipts']==96
assert d['reference_v1_semantic_receipts']==0 and d['reference_v1_P_writes']==0
assert r['T8PQR']['source_scheduler_calls']==216
assert r['T8PQR']['host_forgery_counterexample']['scheduler_calls']==0
assert r['T8PQR']['host_forgery_counterexample']['host_fake_source_accepted']
assert r['native_SPK_P_grants']==r['native_SPK_P_writes']==r['native_BV_semantic_deliveries']==0
assert r['host_can_forge'] and not r['native_learning'] and not r['promotion_allowed']
assert r['T8MNO']['reopen_and_replay']['replay_rejected']
print('  reference v1 grants/commit and strict native-nonpromotion PASS')
PY
printf '[7/7] Final frozen hash check and publish one cumulative evidence file\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate import sha,PE_SHA,BV_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
PY
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
echo 'T8JKL/MNO/PQR CUMULATIVE V1 REFERENCE SEMANTIC BUS & P AUTHORITY PASS; 8 REFERENCE GRANTS; ZERO NATIVE SPK GRANTS OR LEARNING'
