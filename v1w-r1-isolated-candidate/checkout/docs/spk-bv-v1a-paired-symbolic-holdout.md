# SPK/* BV v1a · Prospective paired symbolic holdout, research only

## Boundary and purpose

BV v0z formally admits no live native judgments or hypotheses. **The real user v0z report contains zero hypotheses**. This module adds the first executable evaluation *protocol* for a hypothetical **single local operator substitution** using a fixed, finite, **non-SPK** symbolic domain. The object is to test the harness for detecting improvement *and* degradation under paired controlled inputs, not to invent a learning signal in SPK. No frozen Architecture/Core/Network/Compiler changes, no native commits, no native judgments, no feedback-induced adaptation, no external oracle verification.

## Pure toy algebra

The toy domain is `B={0,1}`; input pairs `B × B` are exhaustively enumerated once per evaluation. Candidate operators are `toy.and`, `toy.or`, `toy.xor` and `toy.nand`. They are not asserted to be SPK Core algebra primitives. Given a predeclared baseline `f0` and alternative `f1`, and four *declared synthetic* truth labels `y_i`, calculate `C(f)=Σ_i [f(x_i)=y_i]`, compare `Δ=C(f1)-C(f0)`, and report the exact numerator over denominator `4`. No floating-point score, fitted weights, search, state mutation, or commits.

The evaluator binds the v0z hypothesis to its v0y decision and original preregistered criterion by calling `validate_hypotheses`. The objective/evaluator pair is fixed (`toy.binary_accuracy` / `toy.declared_truth_table`). The exact trial input and budget digests must match the **previously declared** paired digests in the v0z hypothesis. It requires a four-element complete input truth table with unique IDs, valid tick ordering inside the declared future window, binary labels, a checked label digest, and exactly one hypothetical operator change.

These checks prove **internal consistency of a synthetic prospective comparison**, not actual chronological preregistration, uncontaminated label selection, external objective truth, independent held-out sampling, or validity of a native SPK operator substitution. The protocol can detect an unfavorable counterfactual; it cannot establish its relevance to the real neuron.

## Native chain and default result

The CLI verifies that the supplied real v0z SHA-256 pins the v0y/v0x/v0w file bytes and that the inherited v0y upstream digests match. It rejects symlink/hardlink aliases, files within the research checkout, and output overwrite. It does not claim to reproduce native v0w execution again: those 45 checks belong to v0x. **Default CLI mode scores zero toy experiments** and reports zero native judgments, zero native operator commits, and no identified native learning. The optional `--demo-synthetic` scores three explicitly labeled toy examples only and reports +3, -3 and 0 correct answers over four binary input pairs; the demo shows the harness can report harm as well as benefit. These are not independent empirical trials.

## Use on fwork

```
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v1a_Prospective_Symbolic_Holdout.tar.gz
bash search/spk_bv_v1a_research_gate.sh
python -m search.spk_bv_v1a_symbolic_holdout \
  --v0z /tmp/spk-bv-v0z-shadow-update.json \
  --v0y /tmp/spk-bv-v0y-shadow-judgment-contract.json \
  --v0x /tmp/spk-bv-v0x-native-verified.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --demo-synthetic \
  --out /tmp/spk-bv-v1a-symbolic-holdout.json
bash search/spk_bv_credit_v0a_full_regression.sh
```

Remove `--demo-synthetic` to obtain a strict native-chain-only report (zero toy scores), and select a different output filename because overwrite is forbidden. Never pass the toy sample as native evidence.

## Remaining scientific obligations

Bind a real decision to frozen SPK operator semantics and state; introduce a scored judgment only with an authenticated independent evaluator; preregister an actual future-episode benchmark with separately withheld labels and verified identical source inputs; compare original/candidate in a native sandbox with bounded execution; isolate selection from evaluation; verify rollback and repeatability; test regressions and failure cases; measure resource overhead. Until then learned benefit remains `NOT_IDENTIFIABLE`.
