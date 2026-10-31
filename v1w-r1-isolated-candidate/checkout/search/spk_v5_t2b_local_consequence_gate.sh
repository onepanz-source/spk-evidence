#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUTPUT="${1:?usage: bash search/spk_v5_t2b_local_consequence_gate.sh /tmp/new-report.json}"
printf '[1/6] V5-T2b source pins, frozen architecture and inherited reference\n'
python - <<'PY'
import hashlib,json,pathlib
root=pathlib.Path('.').resolve()
m=json.loads((root/'docs/spk-v5-t2b-manifest.json').read_text())
for rel,expected in m['pins_sha256'].items():
    p=root/rel
    if not p.is_file() or p.is_symlink(): raise SystemExit('invalid pinned file: '+rel)
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    if digest!=expected: raise SystemExit('source SHA drift: '+rel)
print('source pins PASS:',len(m['pins_sha256']))
PY
printf '[2/6] V5-T2b local consequence, witness and adversarial tests\n'
python -m unittest tests.test_spk_v5_t2b_local_consequence -q
printf '[3/6] Inherited V5-T1/T2 frozen boundary tests\n'
python -m unittest tests.test_spk_v5_t1_island_objective -q
printf '[4/6] Inherited frozen A1b PE conformance tests\n'
python -m pytest tests/test_spk_arch_a1b_pe_execution_v1b.py -q
printf '[5/6] A1b source-engine create-only report\n'
python search/spk_v5_t2b_local_consequence.py "$OUTPUT"
printf '[6/6] Canonical exact reference and research-only verdict\n'
python - "$OUTPUT" <<'PY'
import hashlib,pathlib,sys
expected=pathlib.Path('docs/spk-v5-t2b-reference.json').read_bytes()
actual=pathlib.Path(sys.argv[1]).read_bytes()
if expected!=actual:raise SystemExit('reference mismatch')
print('report_sha256',hashlib.sha256(actual).hexdigest())
print('T2b ENGINEERED POSITIVE CONTROL PASS; T2 INDEPENDENT NOT CERTIFIED; T3 RL/BLIND BLOCKED; NATIVE LEARNING NONE')
PY
