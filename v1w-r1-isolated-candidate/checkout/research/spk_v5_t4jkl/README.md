# SPK V5 / T4JKL: Causal receipt and action guard, research only

One cumulative checkpoint:

- **T4J:** Pin the T4GHI report (SHA-256 `dc98a1a5e45270d665e5119540ae960e405f4d02b703bd0c52d04202873abef3`) and all inherited research/frozen source SHA hashes.
- **T4K:** Classify the 180 identical one-source cases without using the old A1b sign as a producer input. Explicitly distinguish BV emission timeline from *application* `forward_enabled` and `reverse_enabled` flags.
- **T4L:** Run the frozen BV scheduler once per case twice in independent Python processes (360 invocations total). Confirm exact old source receipt digest, exact emission paths, field inventories, and byte-level independent process agreement.

Expected partition of T4GHI observations: 108 no source sign; 24 source sign without C/B/A emission triple; 24 with C/B/A emission triple but application forward guard disabled; 24 research candidates with application guard on. This **reduces the 48 temporally coherent triples to 24 research-guard candidates**, but neither is a native semantically acknowledged receipt.

The `no_forward` cases are deliberately important: the BV source result can still expose a coherent C/B/A emission sequence although the separate application decision's `forward_enabled=False`. Conflating those is forbidden.

**Boundaries:** No source edits, no new native scheduler, no native C-authenticated semantic receipt, no signed or independently authenticated sensor, no blind goal truth, no learning or weight update. Provenance is current-checkout SHA and simulator Python return only. This is a *research admission guard*, not an application/native credit transaction.

Run inside `~/workspace/spk-backvalidation-v0` after T4DEF and T4GHI have been extracted:

```bash
bash search/spk_v5_t4jkl_causal_receipt_guard_gate.sh /tmp/spk-v5-t4jkl-causal-receipt-guard.json
```

Requires only Python standard library and previous milestone dependencies. Output filename must not already exist (fail closed). The exact T4GHI reference is bundled to avoid relying on `/tmp` persistence.
