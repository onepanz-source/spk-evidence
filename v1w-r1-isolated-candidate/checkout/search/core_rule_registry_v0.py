from __future__ import annotations

import spk_core.canonicalize as core
import spk_core.semantic_canonicalize as semantic

from spk_core.rules import (
    RULE_SPECS,
    RuleLayer,
    RuleValidity,
    helper_names,
    rule_ids,
    rule_specs,
)


EXPECTED_CORE_DOMAIN = {
    "_cap_saturated_acc_before_guarded_reset",
    "_remove_shadowed_resets",
    "_remove_pre_acc_shift_under_cmp1_reset0",
    "_strip_state_before_lsb_annihilator",
}


EXPECTED_SEMANTIC_DOMAIN = {
    "_normalize_positive_acc_before_cmp1_zero_reset",
    "_normalize_shared_count_pre_shift_acc",
    "_normalize_temporal_shift_width",
    "_remove_dead_state_before_zero_barrier",
}


def main():
    print(
        "SPK CORE RULE REGISTRY v0"
    )

    ids = rule_ids()
    helpers = tuple(
        spec.helper
        for spec in RULE_SPECS
    )

    duplicate_ids = {
        rule_id
        for rule_id in ids
        if ids.count(rule_id) > 1
    }

    duplicate_helpers = {
        helper
        for helper in helpers
        if helpers.count(helper) > 1
    }

    missing_helpers = []

    for spec in RULE_SPECS:
        module = (
            core
            if spec.layer is RuleLayer.CORE
            else semantic
        )

        obj = getattr(
            module,
            spec.helper,
            None,
        )

        if not callable(obj):
            missing_helpers.append(
                (
                    spec.layer.value,
                    spec.helper,
                )
            )

    runtime_specs = rule_specs(
        validity=RuleValidity.RUNTIME
    )

    domain_specs = rule_specs(
        validity=RuleValidity.DOMAIN
    )

    core_runtime = helper_names(
        validity=RuleValidity.RUNTIME,
        layer=RuleLayer.CORE,
    )

    core_domain = helper_names(
        validity=RuleValidity.DOMAIN,
        layer=RuleLayer.CORE,
    )

    semantic_runtime = helper_names(
        validity=RuleValidity.RUNTIME,
        layer=RuleLayer.SEMANTIC,
    )

    semantic_domain = helper_names(
        validity=RuleValidity.DOMAIN,
        layer=RuleLayer.SEMANTIC,
    )

    print()
    print(
        "=" * 88
    )
    print(
        "REGISTRY COUNTS"
    )
    print(
        "=" * 88
    )

    print(
        f"rule specs: "
        f"{len(RULE_SPECS)}"
    )

    print(
        f"rule ids: "
        f"{len(ids)}"
    )

    print(
        f"runtime helpers: "
        f"{len(runtime_specs)}"
    )

    print(
        f"domain helpers: "
        f"{len(domain_specs)}"
    )

    print(
        f"core runtime helpers: "
        f"{len(core_runtime)}"
    )

    print(
        f"core domain helpers: "
        f"{len(core_domain)}"
    )

    print(
        f"semantic runtime helpers: "
        f"{len(semantic_runtime)}"
    )

    print(
        f"semantic domain helpers: "
        f"{len(semantic_domain)}"
    )

    print()
    print(
        "=" * 88
    )
    print(
        "CORE DOMAIN PROFILE"
    )
    print(
        "=" * 88
    )

    for name in core_domain:
        print(
            f"    {name}"
        )

    print()
    print(
        "=" * 88
    )
    print(
        "SEMANTIC DOMAIN PROFILE"
    )
    print(
        "=" * 88
    )

    for name in semantic_domain:
        print(
            f"    {name}"
        )

    errors = []

    if len(RULE_SPECS) != 29:
        errors.append(
            "expected 29 rewrite helpers"
        )

    if len(ids) != 31:
        errors.append(
            "expected 31 Rule IDs"
        )

    if duplicate_ids:
        errors.append(
            f"duplicate Rule IDs: "
            f"{sorted(duplicate_ids)}"
        )

    if duplicate_helpers:
        errors.append(
            f"duplicate helpers: "
            f"{sorted(duplicate_helpers)}"
        )

    if missing_helpers:
        errors.append(
            f"missing helpers: "
            f"{missing_helpers}"
        )

    if (
        set(core_domain)
        != EXPECTED_CORE_DOMAIN
    ):
        errors.append(
            "Core DOMAIN profile mismatch"
        )

    if (
        set(semantic_domain)
        != EXPECTED_SEMANTIC_DOMAIN
    ):
        errors.append(
            "semantic DOMAIN profile mismatch"
        )

    print()
    print(
        "=" * 88
    )
    print(
        "CHECKPOINT"
    )
    print(
        "=" * 88
    )

    if errors:
        for error in errors:
            print(
                f"ERROR: {error}"
            )

        raise SystemExit(1)

    print(
        "29 rewrite helpers registered"
    )

    print(
        "31 Rule IDs registered"
    )

    print(
        "Rule IDs unique"
    )

    print(
        "helper ownership unique"
    )

    print(
        "all helper implementations exist"
    )

    print(
        "Core DOMAIN profile = 4"
    )

    print(
        "semantic DOMAIN profile = 4"
    )

    print()
    print(
        "RULE REGISTRY CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
