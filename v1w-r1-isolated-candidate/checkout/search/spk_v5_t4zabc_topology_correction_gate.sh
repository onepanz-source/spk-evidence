#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t4zabc-topology.json}"
SOURCE_ARCHIVE="$(dirname "$OUT")/spk-v5-t4zabc-frozen-source-handoff.tar.gz"
[[ ! -e "$OUT" && ! -L "$OUT" && ! -e "$SOURCE_ARCHIVE" && ! -L "$SOURCE_ARCHIVE" ]] || { echo 'T4ZABC FAIL CLOSED: OUTPUT_ALREADY_EXISTS' >&2; exit 3; }
TMP=$(mktemp -d "${TMPDIR:-/tmp}/spk-v5-t4zabc-XXXXXXXX")
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] Inherited T4DEF–T4ZAB tests (the old observational premise remains frozen)\n'
for n in t4def t4ghi t4jkl t4jkl_fix t4nop t4qrs t4tuv t4wxy t4zab; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${n}/tests" -q
done
printf '[2/8] New adversarial differential topology tests\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t4zabc/tests -q
printf '[3/8] Manifest and old T4ZAB / frozen source custody\n'
PYTHONPATH=. python3 - <<'PY2'
import json,hashlib
from pathlib import Path
from research.spk_v5_t4zab import t4zab
m=json.loads(Path('research/spk_v5_t4zabc/manifest.json').read_text())
assert m['schema']=='spk-v5-t4zabc-additive-file-custody/v0'
assert len(m['files'])==4
for rel,pin in m['files'].items():
 p=Path(rel);assert p.is_file() and not p.is_symlink() and '..' not in p.parts
 assert hashlib.sha256(p.read_bytes()).hexdigest()==pin,rel
wxy=t4zab.wxy_ref('research/spk_v5_t4zab/reference/t4wxy-c-context-reference.json')
assert t4zab.verify_origins('.',wxy)==wxy['source_pins']
print('  additive 4 files, 12 original source pins PASS; prior T4ZAB source immutable')
PY2
for i in 1 2; do
 printf '[%d/8] Differential process %s: positive A1b PE control + 180 genuine BV-v0e cases\n' "$((i+3))" "$i"
 PYTHONPATH=. python3 research/spk_v5_t4zabc/t4zabc.py run --root . --out "$TMP/run-$i.json"
done
printf '[6/8] Byte-exact deterministic comparison and mandatory nonpromotion\n'
cmp -s "$TMP/run-1.json" "$TMP/run-2.json" || { echo 'T4ZABC FAIL CLOSED: DIFFERENTIAL_RUN_NONDETERMINISM' >&2;exit 4; }
PYTHONPATH=. python3 - "$TMP/run-1.json" <<'PY3'
import json,sys
from pathlib import Path
from research.spk_v5_t4zabc import t4zabc
x=json.loads(Path(sys.argv[1]).read_text())
assert x['status']==t4zabc.STATUS and x['source_BV_case_count']==180
assert x['BV_scheduler_entries']==180 and x['BV_observed_source_C_signs']==72
assert x['positive_A1B_control']['pe_C_compute_calls']>0
assert x['original_T4ZAB_fail_closed_preserved'] is True
assert x['frozen_runtime_changed'] is False
assert x['native_C_emission_proven'] is False
assert x['native_origin_authenticated'] is False
assert x['native_BV_receiver_receipt_proven'] is False
assert x['native_learning_proven'] is False and x['promotion_allowed'] is False
print('  measured topology',x['topology_interpretation'],'C PE',x['BV_PE_C_computes'])
PY3
printf '[7/8] Copy pinned frozen PE/BV sources for the derived fork\n'
mkdir -p "$(dirname "$OUT")"
PYTHONPATH=. python3 research/spk_v5_t4zabc/t4zabc.py bundle --root . --out "$SOURCE_ARCHIVE"
printf '[8/8] Persist sealed, tested diagnostic and source SHA evidence\n'
cp -- "$TMP/run-1.json" "$OUT"
sha256sum "$OUT" "$SOURCE_ARCHIVE"
echo 'T4ZABC DIFFERENTIAL TOPOLOGY PASS; T4ZAB FALSE PE PREMISE CORRECTED; NO NATIVE BV OR LEARNING'
