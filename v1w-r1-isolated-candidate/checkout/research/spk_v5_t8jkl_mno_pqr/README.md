# T8JKL + T8MNO + T8PQR (one cumulative reference-v1 milestone)

- **T8JKL** creates a new reference v1 semantic A→B→C event bus from original A PE emissions, binds it to unchanged source BV-v0e structural deliveries and decision/version metadata.
- **T8MNO** replaces T8's research-always-DENIED candidate with a working **reference-owned** P authority that issues, consumes and audits a one-shot grant and atomic C-owned P write. This is NOT a native Memory Contract grant.
- **T8PQR** drives 96+96+24 unchanged BV-v0e epochs, validates exact T8 source fingerprints on full checkout, restart/replay, and a deliberately successful host-forgery counterexample.

Full gate: `bash search/spk_v5_t8jkl_mno_pqr_cumulative_gate.sh ~/workspace/spk-evidence/spk-v5-t8jkl-mno-pqr-v1-reference.json`

Install additively with `tar --skip-old-files -xzf ...`; prior milestones through T8ABC required. Report path must not already exist. **Never edit frozen sources.**

Local development may run reference-v1 unit tests with synthetic `fake_source()` fixtures; the full gate requires all original admission modules and 12 original source pins, and strictly compares the original source SHA vectors to the T8 user-confirmed report. Hash mismatches MUST fail closed.

No sensor attestation, no native semantic BV, no native P grant, no native learning, no hardware claim.
