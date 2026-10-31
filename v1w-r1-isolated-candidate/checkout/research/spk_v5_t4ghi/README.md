# SPK V5 T4GHI, source sign observability (research only)

Scope:
- **T4G**: demonstrate that the *restricted* static-terminal/BV-timeline structural projection cannot determine the positive vs negative sign. In T4DEF, 72 observed signed rows form 20 structural projection groups, all containing both signs. This does **not** prove that the complete BV result is sign-indistinguishable.
- **T4H**: execute the frozen `execute_live_v0e` exactly once per case (180 cases) using the original T3h case with fixed terminal channel 30 added at conditional C branches, as T4DEF did. Unlike T4DEF, this caller DOES NOT invoke the separate T3h `execute` (A1b replay). The C program still contains source channels 11 and 12, and B/A return programs. Search for declaratively labeled emissions in the **same returned forward result**, never in independently generated credits, inputs or a hash.
- **T4I**: compare each fresh full BV source result SHA with the pinned T4DEF historical source result SHA *after* execution. Reject drift; retain explicit no-promotion boundary. An observed C11/12 event in a returned Python dict remains only a candidate, not an authenticated receiver-readable BV semantic packet.

Run from the cumulative checkout:

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T4GHI_One_Pass_Sign_Observation_Milestone_20261022.tar.gz
bash search/spk_v5_t4ghi_one_pass_sign_observation_gate.sh /tmp/spk-v5-t4ghi-one-pass-sign.json
```

The reference T4DEF report is bundled with a fixed SHA so `/tmp` cleanup cannot break the gate. Generated report includes 180 per-case diagnostics and output shape observations. No new dependencies. No modifications to frozen Architecture/Core/Network/Compiler/BV. Inherited T4DEF + new T4GHI unittest suites are run before the source experiment.

The output status `SINGLE_SOURCE_SIGN_VISIBILITY_RESEARCH_ONLY` indicates the experiment was completed with parity. It does NOT imply single-clock semantic native BV, external sensor authentication, native learning, genuine receiver authorization, blind evaluation or real-world goal alignment.

On failure, the command stops before persisting the final report, leaving the frozen sources untouched.
