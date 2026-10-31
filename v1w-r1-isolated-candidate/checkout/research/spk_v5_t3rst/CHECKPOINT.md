# SPK V5 T3RST cumulative research checkpoint (2026-10-21)

## Scope
Combined T3R: reference accounting and boundaries, T3S: one-pass event custody, T3T: future-perturbation causal cut plus adversarial cases.

## Reproduced in this environment
- `python -m unittest discover -s tests -q` -> 36 tests OK.
- `PYTHONPATH=src python src/spk_t3rst.py --trace fixtures/single_pass_positive.json --alternate-trace fixtures/single_pass_negative_future.json --output paired_audit.json` -> S and T PASS in shadow fixture.
- `PYTHONPATH=src python src/spk_t3rst.py --trace fixtures/single_pass_silent.json --output silent_audit.json` -> no credit for silence.

## Boundary, strictly enforced
- The original SPK T3OPQ archive and native producer were not executed, and its reported SHA-256 was not recalculated.
- `audit_reference` checks internal consistency if supplied the original JSON report; no independent upstream attribution.
- Fixture event author fields and hashes do NOT authenticate a source. This is a structural non-promotion gate only.
- No authenticated C sensor, no native semantic feedback, no native policy update or learning, no blind objective labels.
- All frozen SPK source/architecture unaffected; this bundle is additive research code.

## Next native execution gate
Export actual single-pass scheduler event trace with pre-decision source prefix and independent C sensor receipt; require genuine receiver-origin judgment and authoritative data custody. Verify on two independent clones before discussing promotion.
