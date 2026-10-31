# SPK V5 T7JKL + T7MNO + T7PQR cumulative research

One additive checkpoint, one fwork gate. **No changes to frozen SPK Core, Network, Compiler, Architecture, or BV v0e.**

## T7JKL: source-bound semantic handoff (SHADOW)

The unchanged frozen BV-v0e genuinely runs C -> B -> A and transports *structural* BV A -> B -> C. The output channel 21/22 is **still a separate PE-A emission**. A research host adapter binds the PE-A semantic emission, forward ancestry, BV-A assessment, BV A->B->C deliveries, decision ID, C policy version, and source digest into a shadow A/B/C capsule. It verifies complete objects against actual raw BV source before accepting, not just caller-supplied checksums.

**Important:** this is host-managed *semantic custody*, NOT semantic payload inside the frozen BV packet and NOT authenticated producer custody. We specifically reject the description “native semantic BV”.

## T7MNO: bounded research P-write intent

Only verified shadow receipts may produce a strict research P-write intent for `owner=C, domain=P, mode=execute`, bound to decision identity and expected version. The intent is checked before a single transactional settlement by the existing research SQLite WAL C state. It does NOT go through the frozen SPK Memory Contract admission, does NOT update SPK's native P domain and cannot be promoted to native memory authority.

## T7PQR: counterexamples and controls

Full fwork gate: 96 fixed and 96 adaptive real BV-v0e epochs, 24 no-forward episodes, one genuine scheduler recovery episode, two deterministic runs, 34 new tests plus inherited regressions, source/manifest SHA pins. Compare successful A assessments against T7: control=48, adaptive=88, 8 P updates. Shadow receipt counts track native structural propagation, not native semantic BV.

The host remains powerful enough to forge a *complete coherent raw BV-looking source* without any scheduler call, pass the shadow envelope checks, and trick the SQLite P adapter. This is a **required negative witness** rather than an implementation flaw to conceal. No native learning, sensor authentication, origin attestation or physical causal effect claimed.

## fwork

```bash
cd ~/workspace/spk-backvalidation-v0
tar --skip-old-files -xzf ~/Scaricati/SPK_V5_T7JKL_MNO_PQR_Semantic_Custody_P_Intent_Cumulative_20261022.tar.gz
bash search/spk_v5_t7jkl_mno_pqr_cumulative_gate.sh ~/workspace/spk-evidence/spk-v5-t7jkl-mno-pqr-cumulative.json
```

The launcher refuses to overwrite its output and verifies legacy + new manifest custody. Avoid using `--overwrite` to unpack: this is an additive research archive.
