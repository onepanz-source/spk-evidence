# SPK V5 cumulative T5PQR + T5STU + T5VWX (research only)

**Single milestone, single install, single gate, single sealed JSON.**

- **T5PQR**: Show two conflicting potential-outcome worlds with identical 180 archived T5MNO observations. Reception is only a *hypothetical* treatment indicator. Observationally C's efficacy is non-identifiable.
- **T5STU**: Run 24 matched, host-generated, *synthetic* intervention pairs (48 simulated arms) with a known synthetic plant. Outcomes and sign of effects can be identified **within that defined model only**, not from the observed C path or real sensors.
- **T5VWX**: Issue 24 A-local research-only feedback packets, relay them through separate host-controlled Python B and C processes, validate monotonic SHA chains and reject six malformed/replayed/promoted messages. Require a host-forged *fresh* A ledger to be accepted, proving native source authentication is still missing.

This package deliberately has no direct write to C state, no learning, no credit, no new BV scheduler calls, and no PE compute calls. Frozen SPK Core/Network/Compiler/Architecture and BV-v0e must not be changed. The receiver-only classification and original 12 source SHA pins remain enforced in the on-workstation gate.

The reference T5MNO JSON is pinned to SHA256 `1eb6a4b43297cc8c111fb1811d00954ac119e2a9c604407785ec54059ee78706` and reexecuted byte-for-byte before the new tests.

## One-time installation + one gate

```bash
cd ~/workspace/spk-backvalidation-v0
tar --skip-old-files -xzf ~/Scaricati/SPK_V5_T5PQR_STU_VWX_Cumulative_Research_20261022.tar.gz
bash search/spk_v5_t5pqr_stu_vwx_cumulative_gate.sh ~/workspace/spk-evidence/spk-v5-t5pqr-stu-vwx-cumulative.json
```

Never run under an output path containing a prior report unless you intend fail-closed behavior. All incremental source files live under a new research package; extraction does not overwrite existing files.
