#!/usr/bin/env bash
set -euo pipefail

ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.."
    pwd
)"

cd "$ROOT"

section()
{
    echo
    echo "================================================================================"
    echo "$1"
    echo "================================================================================"
}

run_capture()
{
    local title="$1"
    shift

    section "$title"

    local output

    if ! output="$("$@" 2>&1)"; then
        printf '%s\n' "$output"
        echo
        echo "N4 FINAL GATE: FAIL in $title"
        exit 1
    fi

    printf '%s\n' "$output"

    REPLY="$output"
}

require()
{
    local text="$1"
    local expected="$2"

    if ! grep -Fq "$expected" <<<"$text"; then
        echo
        echo "EXPECTED CHECKPOINT NOT FOUND:"
        echo "  $expected"
        exit 1
    fi
}


section "STATIC CHECKS"

python -m py_compile \
    spk_core/rules.py \
    spk_core/canonicalize.py \
    spk_core/semantic_canonicalize.py \
    search/core_rule_registry_v0.py \
    search/core_rule_audit_v0.py \
    search/core_abstract_soundness_v0.py \
    search/core_rule_soundness_v0.py \
    search/core_runtime_profile_equivalence_v0.py \
    search/core_semantic_runtime_profile_equivalence_v0.py \
    search/core_runtime_joint_normalize_v0.py \
    search/core_domain_definedness_v0.py \
    search/core_domain_promotion_v0.py

git diff --check

echo "STATIC CHECKS: PASS"


run_capture \
    "PYTEST" \
    pytest -q

require "$REPLY" "331 passed"


run_capture \
    "RULE REGISTRY" \
    python -m search.core_rule_registry_v0

require "$REPLY" \
    "RULE REGISTRY CHECKPOINT: PASS"


run_capture \
    "RULE AUDIT" \
    python -m search.core_rule_audit_v0

require "$REPLY" \
    "AUDIT STATUS: PASS"


run_capture \
    "ABSTRACT SOUNDNESS" \
    python -m search.core_abstract_soundness_v0


run_capture \
    "RULE SOUNDNESS" \
    python -m search.core_rule_soundness_v0

require "$REPLY" \
    "RULE SOUNDNESS CHECKPOINT: PASS WITH DECLARED DOMAIN EXCLUSIONS"

require "$REPLY" \
    "observation mismatches: 0"

require "$REPLY" \
    "runtime source-overflow removals: 0"

require "$REPLY" \
    "runtime target-overflow failures: 0"


run_capture \
    "CORE RUNTIME PROFILE EQUIVALENCE" \
    python -m search.core_runtime_profile_equivalence_v0

require "$REPLY" \
    "programs checked: 7380"

require "$REPLY" \
    "profile mismatches: 0"

require "$REPLY" \
    "RUNTIME PROFILE EQUIVALENCE CHECKPOINT: PASS"


run_capture \
    "SEMANTIC RUNTIME PROFILE EQUIVALENCE" \
    python -m search.core_semantic_runtime_profile_equivalence_v0

require "$REPLY" \
    "programs checked: 7380"

require "$REPLY" \
    "Core DOMAIN helpers: 6"

require "$REPLY" \
    "semantic DOMAIN helpers: 6"

require "$REPLY" \
    "profile mismatches: 0"

require "$REPLY" \
    "SEMANTIC RUNTIME PROFILE EQUIVALENCE CHECKPOINT: PASS"


run_capture \
    "RUNTIME CORE + TEMPORAL JOINT NORMALIZATION" \
    python -m search.core_runtime_joint_normalize_v0

require "$REPLY" \
    "runtime Core classes: 744"

require "$REPLY" \
    "joint classes: 608"

require "$REPLY" \
    "runtime Core mismatches: 0"

require "$REPLY" \
    "joint semantic mismatches: 0"

require "$REPLY" \
    "joint cycles: 0"

require "$REPLY" \
    "joint idempotence failures: 0"

require "$REPLY" \
    "runtime Core quotient splits: 0"

require "$REPLY" \
    "RUNTIME CORE/TEMPORAL JOINT CHECKPOINT: PASS"


run_capture \
    "DOMAIN DEFINEDNESS CENSUS" \
    python -m search.core_domain_definedness_v0

require "$REPLY" \
    "cases: 1151400"

require "$REPLY" \
    "DD both defined: 1113405"

require "$REPLY" \
    "DO source defined / target overflow: 1455"

require "$REPLY" \
    "OD source overflow / target defined: 1432"

require "$REPLY" \
    "OO both overflow: 35108"

require "$REPLY" \
    "DD observation mismatches: 0"

require "$REPLY" \
    "R0 reconstructed source exclusions: 36540"

require "$REPLY" \
    "R0 reconstructed target escapes: 1455"

require "$REPLY" \
    "DOMAIN DEFINEDNESS CHECKPOINT: PASS"


run_capture \
    "DOMAIN PROMOTION STRESS SEARCH" \
    python -m search.core_domain_promotion_v0

require "$REPLY" \
    "initial raws: 256"

require "$REPLY" \
    "stress trains: 112"

require "$REPLY" \
    "supported: 5"

require "$REPLY" \
    "refuted: 0"

require "$REPLY" \
    "_cap_shift_before_zero_reset_from_compare_bound"

require "$REPLY" \
    "_pull_saturated_acc_across_compare"

require "$REPLY" \
    "_normalize_temporal_cmp2_barrier"

require "$REPLY" \
    "_normalize_temporal_guarded_reset_commute"

require "$REPLY" \
    "_normalize_temporal_shift_width"


section "FINAL CHECKPOINT"

echo "N4 FINAL CHECKPOINT: PASS"
echo
echo "Core runtime quotient:       7380 -> 744"
echo "Core + temporal quotient:     744 -> 608"
echo "Runtime profile mismatches:   0"
echo "Semantic profile mismatches:  0"
echo "Domain DD mismatches:         0"
echo "Promotion candidates:         5"
echo "Promotion candidates refuted: 0"
