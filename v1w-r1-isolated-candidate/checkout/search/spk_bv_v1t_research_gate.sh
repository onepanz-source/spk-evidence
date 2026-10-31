#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1t source-to-lab adapter, receiver knowledge isolation, adversarial custody'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1t_native_trace_mailbox_adapter.py
python -m compileall -q spk_bv_research/native_trace_mailbox_adapter_v1t.py search/spk_bv_v1t_native_trace_mailbox_adapter.py
echo '[2/3] Inherited v1s -> frozen native scheduler and Architecture custody gate'
bash search/spk_bv_v1s_research_gate.sh
echo '[3/3] Native source-bound replay requires explicit v1t CLI; shadow packets remain NONNATIVE'
echo 'SPK BV v1t POSTHOC NATIVE TRACE TO ISOLATED MAILBOX PASS (NO NATIVE RECEIVER AUTHORITY)'
