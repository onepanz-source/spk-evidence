#!/usr/bin/env bash
# 24m: one Compiler -> frozen Network runtime -> observer -> evidence gate.
set -euo pipefail
cd "$(dirname "$0")/.."

[[ -f spk_compiler/compile_pipeline_v0.py ]] || { echo 'Missing frozen compiler checkout' >&2; exit 2; }
[[ -f spk_network/runtime_v0.py ]] || { echo 'Missing frozen network checkout' >&2; exit 2; }

printf '\n[1/5] Integrated compiler/network/observer/evidence tests\n'
python -m pytest -q tests/test_spk_24m_compiler_network_evidence_v0.py

printf '\n[2/5] Compiler / Network regressions and execution contract\n'
python -m pytest -q tests/test_compilation_manifest_v0.py tests/test_network_runtime_v0.py \
  tests/test_network_learning_interface_v0.py tests/test_spk_execution_contract_v0.py \
  tests/test_spk_24m_compiler_network_evidence_v0.py

printf '\n[3/5] Independent process artifacts and deterministic replay\n'
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
chmod 700 "$work"
PYTHONHASHSEED=1 python -m search.spk_24m_compiler_network_evidence_v0 --write "$work/evidence-1.json"
PYTHONHASHSEED=137 python -m search.spk_24m_compiler_network_evidence_v0 --write "$work/evidence-2.json"
cmp "$work/evidence-1.json" "$work/evidence-2.json"
python -m search.spk_24m_compiler_network_evidence_v0 --verify "$work/evidence-1.json"
python - "$work/evidence-1.json" <<'PY'
import json, sys
from pathlib import Path
p=json.loads(Path(sys.argv[1]).read_text())['payload']
r=p['result']
assert r['processed_events']==4 and r['processed_batches']==3, r
assert [(x['timestamp'],x['node_id'],x['channel']) for x in r['terminal_outputs']] == [(4,'B',7),(5,'B',7)]
assert len(p['observations']['routes'])==3
assert len(p['observations']['batches'])==3
print('network witness: PASS, A -> B parallel routes, delays 2/3')
PY

printf '\n[4/5] Entire repository regression\n'
python -m pytest -q

printf '\n[5/5] Patch and frozen-source boundary checks\n'
python - <<'PY'
from pathlib import Path
names=(
  'search/spk_24m_compiler_network_evidence_v0.py',
  'search/spk_24m_final_gate_v0.sh',
  'tests/test_spk_24m_compiler_network_evidence_v0.py',
  'docs/spk-24m-compiler-network-observer-evidence-v0.md',
)
for name in names:
    p=Path(name)
    assert p.is_file(),name
    for i,line in enumerate(p.read_text().splitlines(),1):
        assert line == line.rstrip(), (name,i)
print('patch structure/whitespace: PASS')
PY
git diff --check
# Do not silently certify an edited frozen module. Untracked files are
# handled by the explicit package allowlist, not by tracked-file git diff.
for path in spk_core spk_network spk_compiler spk_architecture; do
  if [[ -n "$(git diff --name-only HEAD -- "$path")" ]]; then
    echo "ERROR: frozen dependency has local tracked changes: $path" >&2
    exit 1
  fi
done
printf '\nSPK 24m COMPILER / NETWORK / OBSERVER / EVIDENCE GATE: PASS (finite reference scope)\n'
