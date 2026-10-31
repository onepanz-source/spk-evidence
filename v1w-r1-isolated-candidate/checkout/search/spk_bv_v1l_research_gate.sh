#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1l isolated two-port observer, noninterference, negative authority tests'
python -m pytest -q tests/test_spk_bv_v1l_two_port_observer.py
python -m compileall -q spk_bv_research/observer_closed_world_v1l.py search/spk_bv_v1l_two_port_observer.py
echo '[2/3] Inherited BV v1k gate and frozen Architecture v1 custody chain'
bash search/spk_bv_v1k_research_gate.sh
echo '[3/3] True native replay and laboratory demonstration require separate CLI'
echo 'SPK BV v1l TWO-PORT OBSERVER LAB RESEARCH PASS (not a native witness or judgment)'
