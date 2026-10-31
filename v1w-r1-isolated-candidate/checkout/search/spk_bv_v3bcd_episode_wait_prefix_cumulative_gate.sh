#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <signed-v2yza-report.json> <new-v3bcd-report.json>" >&2
  exit 2
fi

export SPK_V2YZA_REPORT="$1"

echo '[1/4] BV v3b extended source episodes / ACK custody / adversarial unittest'
python -m unittest discover -s tests -p 'test_spk_bv_v3bcd_episode_wait_prefix.py' -v

echo '[2/4] BV v3c 18 native, 108 derived queue policies and 72 causal prefix comparisons'
python -m search.spk_bv_v3bcd_episode_wait_prefix_cumulative --v2yza "$1" --out "$2"

echo '[3/4] BV v3d 36 causal null runs; native veto unqualified ACK deadline counterexample PASS'
echo '[4/4] Universal native actor priority, learning and progress CONTRACT BLOCKED'
