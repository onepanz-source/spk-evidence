#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] Inherited BV v2n/v2m/v2l/v2k/v2j/v2i/v2h/v2g/v2f/v2e regressions'
bash search/spk_bv_v2n_inherited_regression_gate.sh

echo '[2/2] v2o inherited selected regression gate PASS'
