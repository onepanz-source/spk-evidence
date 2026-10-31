#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Pure 558 single-budget plus 504 causal diagnostic adjudications\n'
python -m pytest -q tests/test_spk_24t_diagnostic_contract_v0.py

printf '\n[2/6] Real manifest diagnostic reference host against frozen Compiler/Network\n'
python -m pytest -q tests/test_spk_24t_diagnostic_manifest_host_v0.py

printf '\n[3/6] Reproducible versioned host receipts in independent Python processes\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
for kind in closed event batch dual; do
  case "$kind" in
    closed) opts=() ;;
    event)  opts=(--max-events 1) ;;
    batch)  opts=(--max-batches 1) ;;
    dual)   opts=(--max-events 1 --max-batches 1) ;;
  esac
  python -m search.spk_24t_diagnostic_manifest_host_v0 --write-demo "$tmp/$kind-a.json" "${opts[@]}"
  python -m search.spk_24t_diagnostic_manifest_host_v0 --write-demo "$tmp/$kind-b.json" "${opts[@]}"
  cmp "$tmp/$kind-a.json" "$tmp/$kind-b.json"
  python -m search.spk_24t_diagnostic_manifest_host_v0 --verify "$tmp/$kind-a.json"
  python -m search.spk_24t_diagnostic_manifest_host_v0 --verify "$tmp/$kind-b.json"
done

printf '\n[4/6] Prior 24p/q/r/s reference and failure regression\n'
python -m pytest -q \
    tests/test_spk_24p_network_application_host_v0.py \
    tests/test_spk_24p_reference_protocol_v0.py \
    tests/test_spk_24q_limit_probe_plan_v0.py \
    tests/test_spk_24q_frozen_failure_parity_v0.py \
    tests/test_spk_24r_dual_limit_plan_v0.py \
    tests/test_spk_24r_frozen_dual_limit_v0.py \
    tests/test_spk_24s_budget_triads_v0.py \
    tests/test_spk_24s_frozen_causal_failure_v0.py

printf '\n[5/6] Complete repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen-source, staging and 24t hygiene\n'
git diff --check
if [[ -n "$(git diff --name-only HEAD -- spk_core spk_network spk_compiler spk_architecture spk_simulator)" ]]; then
  echo 'FAIL: modifications to frozen/previous modules' >&2
  exit 1
fi
if [[ -n "$(git diff --cached --name-only)" ]]; then
  echo 'FAIL: staged files before gate' >&2
  exit 1
fi
python - <<'PY'
from pathlib import Path
names = (
    'docs/spk-24t-diagnostic-equivalence-host-v0.md',
    'search/spk_24t_diagnostic_contract_v0.py',
    'search/spk_24t_diagnostic_manifest_host_v0.py',
    'search/spk_24t_final_gate_v0.sh',
    'tests/test_spk_24t_diagnostic_contract_v0.py',
    'tests/test_spk_24t_diagnostic_manifest_host_v0.py',
)
for name in names:
    raw = Path(name).read_bytes()
    if (b'\r' in raw or not raw.endswith(b'\n') or
            any(line.endswith((b' ', b'\t')) for line in raw.splitlines())):
        raise SystemExit('24t whitespace failure: ' + name)
print('24t patch structure/whitespace: PASS')
PY
git status --short
printf '\nSPK 24t DIAGNOSTIC EQUIVALENCE HOST GATE: PASS (bounded reference host scope)\n'
