# SPK V5 | Cumulative T6JKL + T6MNO + T6PQR

Research-only bounded asynchronous feedback, multiple receiver objectives and policy drift using the **original pinned** `spk_architecture_v1.pe_execution_v1b._compute_local`. Frozen Core, Network, Compiler, PE, BV and Architecture v1 remain untouched.

## Architecture and trust boundary

Host-authored simulator: one C decision PE -> B forward PE -> A and D local PE evaluations -> A/D return PE -> B return PE -> C return PE -> C-side bounded experimental policy. A and D are *logical nodes in the same host-controlled interpreter*, not authenticated processes, physical sensors, trusted PE identities or proof of native multi-receiver deployment. All outcomes are synthetic and deterministic. An ID-labeled digest has no secret owner and is forgeable by the privileged host.

## Three cumulative research gates

- **T6JKL**, 96 matched decisions in four synthetic 24-step phases with two goal receivers and alternating environment targets. Each four-decision batch contains two outstanding decisions per context, issued before the feedback is delivered. Each update requires both A and D judgments to be negative, matching decision ID/context/policy version and bounded tick. Control = 48/96 jointly successful, adaptive = 80/96, eight updates and eight old-version rejections. Every phase has 20/24 joint successes; phase changes are not announced to C. This is 32 additional successes in this particular model only, **not a generalization claim**.
- **T6MNO**, reverse delivery order, jitter across ten deterministic random seeds and receiver message loss. Six suites verify that delayed, duplicate and obsolete messages cannot apply feedback incorrectly. Jitter runs reproduce 80/96, with 27 selected receiver messages lost in the bounded loss stress. Total loss is tested separately.
- **T6PQR**, disagreeing A and D goals in context 0 triggers abstention and no update for that context; context 1 can still adapt. Overconstraining the update budget yields 44/96, worse than fixed control (48/96). Loss of all feedback yields 48/96 with no updates. Host can reissue two forged outcomes or impersonate D despite structural source names; these adversarial **successes** are mandatory findings.

## One execution

```bash
cd ~/workspace/spk-backvalidation-v0
tar --skip-old-files -xzf ~/Scaricati/SPK_V5_T6JKL_MNO_PQR_Async_Multi_Receiver_Cumulative_20261022.tar.gz
bash search/spk_v5_t6jkl_mno_pqr_cumulative_gate.sh \
  ~/workspace/spk-evidence/spk-v5-t6jkl-mno-pqr-cumulative.json
```

The gate checks nine research manifests with SHA-256, the 12 original source pins, immutable PE/BV source, regression suites, exact replay of the T6 closed-loop source report twice and byte-exact equality across two independent Python processes. Output file must not already exist. No Git commits or frozen module edits are performed.

## What this does **not** prove

Full BV scheduler integration, native semantic credit, native C learning, trusted A/D sensors, host-proof identity, hardware concurrency, network contention, statistically generalizable learning or safety of applying adverse feedback in real systems. There is no promotion gate or hardware acquisition implied. Results are confined to a two-cue/two-choice host-authored deterministic plant. Sigma/sigma, source weights and frozen algebra remain unchanged.
