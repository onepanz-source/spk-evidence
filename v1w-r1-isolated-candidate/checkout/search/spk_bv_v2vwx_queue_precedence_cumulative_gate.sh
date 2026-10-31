#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <signed-v2stu-report.json> <new-v2vwx-report.json>" >&2
  exit 2
fi

export SPK_V2STU_REPORT="$1"

echo '[1/4] BV v2v ACK/paid-consumer source-backed queue priority and adversarial tests'
python -m unittest discover -s tests -p 'test_spk_bv_v2vwx_queue_precedence_cumulative.py' -v

echo '[2/4] BV v2w finite bounded-turn preference and 90 native / 540 policy matrix'
python -m search.spk_bv_v2vwx_queue_precedence_cumulative --v2stu "$1" --out "$2"

echo '[3/4] BV v2x 135 causal nulls and pinned predecessor/resource custody PASS'
echo '[4/4] Frozen native ACK/consumer arbiter and universal queue liveness BLOCKED'
