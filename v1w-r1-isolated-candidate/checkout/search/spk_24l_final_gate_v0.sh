#!/usr/bin/env bash
# SPK 24l: one finite local authority / source-pin / replay-evidence gate.
# Run from repository root. Never creates a commit, tag or persisted authority.
set -euo pipefail

if [[ ! -f spk_simulator/application_runtime_host_v0.py || ! -f tests/test_application_trust_boundary_v0.py ]]; then
  echo 'ERROR: run from complete SPK checkout with 24l patch extracted' >&2
  exit 2
fi

printf '\n[1/6] Trust boundary / reference launcher tests\n'
python -m pytest -q tests/test_application_trust_boundary_v0.py

printf '\n[2/6] Root + host + launcher integration\n'
python -m pytest -q \
  tests/test_owned_root_single_clock_v0.py \
  tests/test_owned_root_terminal_commit_v0.py \
  tests/test_owned_root_authority_custody_v0.py \
  tests/test_owned_root_custody_execution_v0.py \
  tests/test_owned_root_execution_dispatch_v0.py \
  tests/test_application_runtime_host_v0.py \
  tests/test_application_runtime_launcher_v0.py \
  tests/test_application_trust_boundary_v0.py

printf '\n[3/6] Two independent finite lab runs: deterministic public summary\n'
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
chmod 700 "$work"
source_sha=$(python - <<'PY'
from spk_simulator.application_trust_boundary_v0 import source_file_sha256_v0
from pathlib import Path
print(source_file_sha256_v0(Path('tests/spk_offline_demo_epoch_v0.py')))
PY
)
for n in 1 8; do
  python -m search.spk_24l_pinned_offline_launcher_v0 \
    --provider tests.spk_offline_demo_epoch_v0:make_epoch \
    --provider-sha256 "$source_sha" --lock-dir "$work" \
    --epoch-id E0 --max-actions 100 --chunk-size "$n" > "$work/run-$n.json"
done
python - "$work/run-1.json" "$work/run-8.json" <<'PY'
import json, sys
from pathlib import Path
x, y = [json.loads(Path(p).read_text()) for p in sys.argv[1:]]
assert x == y, (x, y)
assert x['completed'] is True and x['phase'] == 'CLOSED', x
assert (x['old_version'], x['new_version']) == (0, 1), x
assert x['handoffs'] == 1 and x['actions'] == x['service_ticks_spent'] + 1, x
from spk_simulator.application_trust_boundary_v0 import result_fingerprint_v0
from types import SimpleNamespace
assert result_fingerprint_v0(SimpleNamespace(**x)) == x['result_sha256']
print(json.dumps(x, sort_keys=True))
PY

golden=$(python - "$work/run-1.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))['result_sha256'])
PY
)
python -m search.spk_24l_pinned_offline_launcher_v0 \
  --provider tests.spk_offline_demo_epoch_v0:make_epoch \
  --provider-sha256 "$source_sha" --lock-dir "$work" \
  --epoch-id E0 --max-actions 100 --chunk-size 3 \
  --expected-result-sha256 "$golden" > "$work/golden.json"

printf '\n[4/6] Negative routes: budget incomplete, source drift and result drift\n'
set +e
python -m search.spk_24l_pinned_offline_launcher_v0 \
  --provider tests.spk_offline_demo_epoch_v0:make_epoch \
  --provider-sha256 "$source_sha" --lock-dir "$work" \
  --epoch-id E0 --max-actions 1 --chunk-size 1 > "$work/incomplete.json"
inc=$?
python -m search.spk_24l_pinned_offline_launcher_v0 \
  --provider tests.spk_offline_demo_epoch_v0:make_epoch \
  --provider-sha256 "$(printf '%064d' 0)" --lock-dir "$work" \
  --epoch-id E0 --max-actions 100 > "$work/source-error.json"
src=$?
python -m search.spk_24l_pinned_offline_launcher_v0 \
  --provider tests.spk_offline_demo_epoch_v0:make_epoch \
  --provider-sha256 "$source_sha" --lock-dir "$work" \
  --epoch-id E0 --max-actions 100 --expected-result-sha256 "$(printf '%064d' 0)" \
  > "$work/result-error.json"
drift=$?
set -e
[[ "$inc" == 3 && "$src" == 2 && "$drift" == 2 ]] || { echo 'bad exit codes' >&2; exit 1; }
python - "$work" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
x=json.loads((p/'incomplete.json').read_text())
assert x['completed'] is False and x['phase']=='INCOMPLETE'
assert x['old_version'] is None and x['new_version'] is None
for name in ('source-error.json','result-error.json'):
    e=json.loads((p/name).read_text())
    assert e['status']=='ERROR' and 'completed' not in e, e
print('negative source/receipt/budget gates: PASS')
PY

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Patch whitespace and frozen-module non-interference\n'
python - <<'PY'
from pathlib import Path
names = [
    'docs/spk-application-trust-authority-replay-v0.md',
    'docs/spk-s3-criteria-recalibration-v0.md',
    'spk_simulator/application_trust_boundary_v0.py',
    'search/spk_24l_pinned_offline_launcher_v0.py',
    'search/spk_24l_final_gate_v0.sh',
    'tests/test_application_trust_boundary_v0.py',
]
for filename in names:
    p=Path(filename)
    assert p.is_file(), filename
    for number,line in enumerate(p.read_text().splitlines(),1):
        assert line == line.rstrip(), (filename,number)
print('patch whitespace: PASS')
PY
git diff --check
if git diff --name-only -- spk_core spk_network spk_compiler | grep .; then
  echo 'ERROR: frozen Core/Network/Compiler modifications detected' >&2
  exit 2
fi
git status --short
printf '\nSPK 24l TRUST/LEASE/REPLAY GATE: PASS (cooperative offline scope only)\n'
