#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Multineuron reference-host, admission and failure-parity tests\n'
python -m pytest -q \
  tests/test_spk_24p_network_application_host_v0.py \
  tests/test_spk_24p_reference_protocol_v0.py

printf '\n[2/6] Previous Compiler/Network/observer/independent-oracle regression\n'
python -m pytest -q \
  tests/test_spk_24m_compiler_network_evidence_v0.py \
  tests/test_spk_24n_independent_oracle_v0.py \
  tests/test_spk_24n_frozen_differential_v0.py \
  tests/test_spk_24o_semantic_corpus_v0.py \
  tests/test_spk_24o_frozen_extended_v0.py

printf '\n[3/6] Separate Python processes: closed host artifact + replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_24p_network_application_host_v0 --write-demo "$tmp/closed-a.json"
python -m search.spk_24p_network_application_host_v0 --write-demo "$tmp/closed-b.json"
cmp "$tmp/closed-a.json" "$tmp/closed-b.json"
python -m search.spk_24p_network_application_host_v0 --verify "$tmp/closed-a.json"
python -m search.spk_24p_network_application_host_v0 --verify "$tmp/closed-b.json"

printf '\n[4/6] Separate process exact failure reasons; no successful receipt\n'
python -m search.spk_24p_network_application_host_v0 \
    --max-events 3 --write-demo "$tmp/event-limit.json"
python -m search.spk_24p_network_application_host_v0 \
    --max-batches 2 --write-demo "$tmp/batch-limit.json"
python -m search.spk_24p_network_application_host_v0 --verify "$tmp/event-limit.json"
python -m search.spk_24p_network_application_host_v0 --verify "$tmp/batch-limit.json"
python - "$tmp" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
for file,status,reason in (
  ('closed-a.json','CLOSED',None),
  ('event-limit.json','LIMIT_REACHED','max_events'),
  ('batch-limit.json','LIMIT_REACHED','max_batches'),
):
    doc=json.loads((root/file).read_text())
    result=doc['payload']['execution']
    assert result['status']==status and result['reason']==reason
    if status=='LIMIT_REACHED':
        assert result['result'] is None and result['comparison'] is None
        assert result['observations'] is None
print('closed and budget-limited end-to-end receipts: PASS')
PY

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen-boundary and patch hygiene\n'
git diff --check
if [[ -n "$(git diff --name-only HEAD -- spk_core spk_network spk_compiler spk_architecture spk_simulator)" ]]; then
    echo 'FAIL: tracked frozen code / previous simulator changed' >&2
    exit 1
fi
if [[ -n "$(git diff --cached --name-only)" ]]; then
    echo 'FAIL: unexpected staged files before 24p acceptance' >&2
    exit 1
fi
python - <<'PY'
from pathlib import Path
paths=(
 'search/spk_24p_network_application_host_v0.py',
 'search/spk_24p_final_gate_v0.sh',
 'tests/test_spk_24p_network_application_host_v0.py',
 'tests/test_spk_24p_reference_protocol_v0.py',
 'docs/spk-24p-multineuron-host-failure-differential-v0.md',
)
for path in paths:
    p=Path(path)
    if not p.is_file():
        raise SystemExit('missing file: '+path)
    b=p.read_bytes()
    if b'\r' in b or not b.endswith(b'\n') or any(x.endswith((b' ',b'\t')) for x in b.splitlines()):
        raise SystemExit('bad whitespace: '+path)
print('patch structure/whitespace: PASS')
PY
git status --short
printf '\nSPK 24p MULTINEURON HOST / FAILURE DIFFERENTIAL GATE: PASS (bounded reference scope)\n'
