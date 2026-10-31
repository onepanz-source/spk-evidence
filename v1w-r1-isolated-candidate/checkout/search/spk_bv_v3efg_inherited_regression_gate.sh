#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] BV v3b-v3d inherited source episode and ACK wait regressions'
python -m unittest discover -s tests -p 'test_spk_bv_v3bcd_episode_wait_prefix.py' -v
bash search/spk_bv_v3bcd_inherited_regression_gate.sh

echo '[2/2] BV v3e-v3g inherited selected regression gate PASS'
