# SPK BV v1c: native local operator-operand sensitivity (research only)

## Research question

Can the frozen A1 `_compute_local` kernel yield a **different local result** when
one operand of one real native instruction in the three-neuron pinned fixture
is changed on an **isolated dataclass copy**, under an identical, bounded,
predeclared input domain?

This is the first native *counterfactual sensitivity screen*, **not an
operator-learning or feedback value test**. The native runtime source, forward
scheduler, original neuron objects, frozen package files and all real programs
are untouched. The screen does not even call the network scheduler on variants.

## Custody

Before exploring variants, v1c invokes inherited v1b.1 `generate`, requiring
full source binding and the complete reconstructed v1b.1 report to match the
original user capture. Inputs remain SHA-bound to v0w and v1a. Programs must
match the original SHA of A, B and C and their exact instruction tuples.
Source hashes and immutable native fixture identity are checked before and
following the sensitivity screen.

## Predeclared interventions

Only instruction *operands* are changed; opcode strings are unchanged:

| Neuron | Index | Old | New |
|---|---:|---|---|
| A | 0 | `('SHIFT', 1)` | `('SHIFT', 0)` |
| A | 1 | `('ACC', (1, 0))` | `('ACC', (2, 0))` |
| A | 2 | `('CMP', 1)` | `('CMP', 2)` |
| B | 1 | `('CMP', 1)` | `('CMP', 2)` |
| C | 1 | `('CMP', 1)` | `('CMP', 2)` |

Probe inputs: `(raw=0,channels=(0,))`, `(0,(1,))`, `(0,(0,0))`,
`(0,(0,1))`, `(1,(0,))`, `(1,(1,))`; previous tick `9`, evaluation tick `10`.
All 30 paired native local-kernel calls must be accounted for as SAME,
DIFFERENT, or REJECTED (rejection type reported). This is a designed,
non-independent synthetic domain, *not* an external holdout sample.

The operator semantics are whatever frozen A1 implements. This research does
not assume that syntactically well-formed alternative operands are admissible
by the SPK algebra, so they remain hypothetical. Side effects, nondeterminism,
wrong types, unrecognized source, incomplete output or mutation cause failure.

## Interpretation / stop conditions

- `DIFFERENT` means only a deterministic local result differs, not that it is
  more correct or useful. `SAME` means no detectable difference on *these*
  probes, not semantic equivalence. `REJECTED` must be counted explicitly.
- No feedback packet is mapped to a proposed change and no score or judgment
  of an existing recipient is asserted. No action is committed.
- This does not test new network routes, forward or reverse scheduler budgets,
  cross-episode state evolution, causal credit, generalization, hardware, or
  Architecture v1 promotion.
- Native CLI reexecutes the exact frozen OFF control through the v1b.1
  harness; only the local copies differ during the subsequent screen.

## Run

```bash
bash search/spk_bv_v1c_research_gate.sh
python -m search.spk_bv_v1c_native_sensitivity \
  --v1b1 /tmp/spk-bv-v1b1-native-operator-replay.json \
  --v1a /tmp/spk-bv-v1a-symbolic-holdout.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --out /tmp/spk-bv-v1c-native-sensitivity.json
```

Expected local run count: five alternatives x six inputs = 30 paired
observations. Seed13/811 independent equality and complete full-regression
suite are additional tests not implied by this one report.
