#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUTPUT="${1:?usage: bash search/spk_v5_t1_island_gate.sh /tmp/new-report.json}"
printf '[1/5] V5 pinned sources, A1b and T1/T2 SHA custody\n'
python - <<'PY'
import json,hashlib,pathlib
root=pathlib.Path('.').resolve()
m=json.loads((root/'docs/spk-v5-t1-island-manifest.json').read_text())
for rel, expected in m['pins_sha256'].items():
    p=root/rel
    got=hashlib.sha256(p.read_bytes()).hexdigest()
    if got != expected: raise SystemExit(f'SHA drift: {rel} {got} != {expected}')
print('pinned',len(m['pins_sha256']),'files OK')
PY
printf '[2/5] V5-T1/T2 bounded objective/adversarial tests\n'
python -m unittest tests.test_spk_v5_t1_island_objective -q
printf '[3/5] Inherited frozen A1b PE conformity\n'
python -m pytest tests/test_spk_arch_a1b_pe_execution_v1b.py -q
printf '[4/5] Source-engine V5 exact create-only observational report\n'
python search/spk_v5_t1_island_gate.py "$OUTPUT"
printf '[5/5] Exact pinned reference and research boundary\n'
python - "$OUTPUT" <<'PY'
import hashlib,pathlib,sys
r=pathlib.Path('docs/spk-v5-t1-island-reference.json').read_bytes()
a=pathlib.Path(sys.argv[1]).read_bytes()
if r!=a: raise SystemExit('reference observation drift')
print('report_sha256',hashlib.sha256(a).hexdigest())
print('V5-T1 CAPABILITY PASS; T2 ACK-ONLY NON-IDENTIFIABILITY NO-GO; NO NATIVE LEARNING')
PY
