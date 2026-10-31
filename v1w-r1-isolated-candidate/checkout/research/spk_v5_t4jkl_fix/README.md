# SPK V5 T4JKL-M additive control flag hotfix (research only)

## Failure repaired

Original T4JKL fails on row 2 (`no_marker`) with
`ACTION_FORWARD_FLAG_MISMATCH_2`: it wrongly equates *not sending a decision*
with *disabling application forwarding*.

The source case generator `research/spk_v5_t4def/t4def.py:table_cases`
defines independent controls:

- `send_decision = failure != 'no_marker'`
- `forward_enabled = failure != 'no_forward'`
- `reverse_enabled = failure != 'no_reverse'`

For `no_marker` the three values are `False, True, True`. The original guard
incorrectly returned `False` for forwarding, though no delivery was proven.

## Design / nonpromotion

This additive hotfix introduces the corrected gate at
`search/spk_v5_t4jklm_control_flag_hotfix_gate.sh`. It keeps the prior
T4JKL source unchanged, preserving the previous failure as research evidence.
The corrected version strictly verifies the THREE recipe controls against
`Measurement` objects on each of 180 cases, while maintaining the existing
source receipt exact SHA checks and separate independent-process deterministic
reruns of all 180 source calls.

The controls are *inputs to the application test*, not authoritative delivery
receipts. C/B/A emission candidates remain descriptive. There is no
native receiver-authenticated signed semantic BV and no neural weight update.
No frozen runtime, compiler, algebra, architecture, or source bridge edits.

## Run

```
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T4JKLM_Control_Flag_Hotfix_Milestone_20261022.tar.gz
bash search/spk_v5_t4jklm_control_flag_hotfix_gate.sh /tmp/spk-v5-t4jklm-control-flag.json
```

This requires existing T4DEF, T4GHI and T4JKL milestone installations.
The failed original T4JKL did not persist its final JSON; the hotfix
re-executes it cleanly under a new output name.
