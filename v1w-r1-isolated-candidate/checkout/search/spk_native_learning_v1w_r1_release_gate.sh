#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
OUT="${1:?Usage: bash search/spk_native_learning_v1w_r1_release_gate.sh /ABS/NEW_REPORT.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'R1 REJECT: OUTPUT_ALREADY_EXISTS' >&2; exit 3; }
printf '[r1 PRE] Exact versioned release manifest and original predecessor custody\n'
PYTHONPATH=. python3 - <<'PY_CHECK'
import hashlib, json
from pathlib import Path
root = Path('.').resolve()
m = json.loads((root / 'spk_native_learning_v1/ingress_manifest_v1w_r1.json').read_text())
assert m['schema'] == 'spk-native-learning-v1w-r1-erratum-manifest/v1'
assert m['parent'] == 'v1w' and m['frozen_components_modified'] is False
assert m['promotion_allowed'] is False
assert m['original_gate_sha256'] == '29a5853fdc3d411115c0b10d96dfba0a73c02c8a39967a52b866f6b700dd767d'
assert m['corrected_gate_sha256'] == '6d99000e75d7a6074a35e313a64f8d288e58400298d65f563fe4a3842a132e8a'
for rel, expected in m['files'].items():
    path = root / rel
    assert path.resolve().is_relative_to(root) and path.is_file() and not path.is_symlink(), 'R1_FILE_INVALID:' + rel
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'R1_SOURCE_PIN_DRIFT:' + rel
print('  R1 original v1w + isolated erratum + runner SHA-pinned PASS')
PY_CHECK
printf '[r1 RUN] Execute unmodified candidate 8-step v1w gate; no shim\n'
bash search/spk_native_learning_v1w_r1_queued_ingress_gate.sh "$OUT"
printf '[r1 POST] Exact original report + identity boundary\n'
PYTHONPATH=. python3 - "$OUT" <<'PY_RESULT'
import hashlib, json, pathlib, sys
p = pathlib.Path(sys.argv[1]); b = p.read_bytes(); r = json.loads(b)
assert hashlib.sha256(b).hexdigest() == '0f70b4711a3282375d388285462e4dbbb2614b1dfe7ab042800ef9234f511be1', 'R1_REPORT_SHA_DRIFT'
assert r['parent_v1v_SHA256'] == '172b2a1c72a526ca3cc49d9792d4d765b606f7d4b346f43a46ddc2ef50fdd59c'
assert r['native_v1_BV_and_P_after_ingress'] and not r['frozen_BV_v0e_learning']
assert not r['promotion_allowed']
print('V1W-R1 UNMODIFIED EIGHT-STEP CANDIDATE GATE PASS, NOT SIGNED/CANONICAL RELEASE')
PY_RESULT
