#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] Inherited BV v2i/v2h/v2g/v2f/v2e selected regressions'
bash search/spk_bv_v2i_inherited_regression_gate.sh

echo '[2/2] v2j inherited selected regression gate PASS'
