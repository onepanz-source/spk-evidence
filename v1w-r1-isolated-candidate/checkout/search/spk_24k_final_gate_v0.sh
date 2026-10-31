#!/usr/bin/env bash
# SPK 24k: reproduce one offline integration gate on the full fwork checkout.
# No git add/commit/tag, no modification to frozen components.
set -euo pipefail

if [[ ! -f spk_simulator/application_runtime_host_v0.py || ! -f tests/test_application_runtime_launcher_v0.py ]]; then
  echo 'ERROR: run from the SPK repository root after extracting the 24k bundle' >&2
  exit 2
fi

printf '\n[1/6] Provider/launcher tests\n'
python -m pytest -q tests/test_application_runtime_launcher_v0.py

printf '\n[2/6] Root -> terminal -> host -> launcher integration\n'
python -m pytest -q \
  tests/test_owned_root_single_clock_v0.py \
  tests/test_owned_root_terminal_commit_v0.py \
  tests/test_owned_root_authority_custody_v0.py \
  tests/test_owned_root_custody_execution_v0.py \
  tests/test_owned_root_execution_dispatch_v0.py \
  tests/test_application_runtime_host_v0.py \
  tests/test_application_runtime_launcher_v0.py

printf '\n[3/6] Complete finite demo: require EXIT 0 + real version increment\n'
python -m search.spk_application_runtime_launcher_v0 \
  --provider tests.spk_offline_demo_epoch_v0:make_epoch \
  --epoch-id E0 --max-actions 100 --chunk-size 6 \
  > /tmp/spk-24k-complete.json
python - <<'PY'
import json
from pathlib import Path
x=json.loads(Path('/tmp/spk-24k-complete.json').read_text())
assert x['completed'] is True and x['phase']=='CLOSED', x
assert x['old_version']==0 and x['new_version']==1, x
assert x['handoffs']==1, x
assert x['actions']==x['service_ticks_spent']+1, x
print(json.dumps(x,sort_keys=True))
PY

printf '\n[4/6] Limited demo: require EXIT 3 + incomplete with NO receipt\n'
set +e
python -m search.spk_application_runtime_launcher_v0 \
  --provider tests.spk_offline_demo_epoch_v0:make_epoch \
  --epoch-id E0 --max-actions 1 --chunk-size 1 \
  > /tmp/spk-24k-incomplete.json
status=$?
set -e
if [[ "$status" -ne 3 ]]; then
  echo "ERROR: incomplete run returned exit $status instead of 3" >&2
  cat /tmp/spk-24k-incomplete.json >&2
  exit 2
fi
python - <<'PY'
import json
from pathlib import Path
x=json.loads(Path('/tmp/spk-24k-incomplete.json').read_text())
assert x['completed'] is False and x['phase']=='INCOMPLETE', x
assert x['old_version'] is None and x['new_version'] is None, x
print(json.dumps(x,sort_keys=True))
PY

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Whitespace, tracked changes and untracked files\n'
python - <<'PY'
from pathlib import Path
files = [
    'docs/spk-application-provider-launcher-end-to-end-v0.md',
    'spk_simulator/application_epoch_provider_v0.py',
    'search/spk_application_runtime_launcher_v0.py',
    'search/spk_24k_final_gate_v0.sh',
    'tests/spk_offline_demo_epoch_v0.py',
    'tests/test_application_runtime_launcher_v0.py',
]
for name in files:
    assert Path(name).is_file(), name
    for number, line in enumerate(Path(name).read_text().splitlines(),1):
        assert line == line.rstrip(), (name, number)
print('new file whitespace: PASS')
PY
git diff --check
git status --short
printf '\nSPK 24k OFFLINE PROVIDER/LAUNCHER GATE: PASS (local finite reference scope)\n'
