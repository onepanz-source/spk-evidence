# SPK Native Learning Runtime v1, first bounded release candidate

Contains a deliberately versioned fork of genuine frozen BV-v0e with the first same-clock endogenous A→B→C feedback-induced mutation to C's executable P program. The frozen original remains byte-identical and can be independently run for disabled-mode parity.

Entry point: `python3 -m spk_native_learning_v1.conformance_v1 evidence.json --root .` from the full SPK checkout. Use the release gate for checks before accepting evidence.

Scope is three-neuron binary semantic program switching, **not** general learning, not original BV-v0e native learning, and not durable P memory.
