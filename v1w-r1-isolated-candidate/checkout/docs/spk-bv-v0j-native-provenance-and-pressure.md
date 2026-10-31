# SPK BV v0j: native provenance reconnaissance + hypothetical capacity pressure

**Research-only, read-only.** Built on top of the prior BV v0i bundle; it does not modify frozen Architecture v1, scheduler, Core, Network, Compiler, native BV v0h producer, or BV v0i classes.

## Established baseline (user gate)
- BV v0i: 34 tests PASS, 528 synthetic receptions, 33 synthetic distinct contextual votes, 495 additional receptions, 528 abstract transport units, hashseed-invariant physical/vote digest.
- Repo full regression: **3709 passed, 6 branch-specific custody deselected**.
- BV v0h native research replay (separate): 528 physical feedback packets, 33 unique receiver votes, 495 duplicated-path receptions; native evidence SHA-256 `82cf4a16a175e3e4d20ede4f13da8b350bf5374e08c16df7500b905840b05a7b`.
- These two witnesses are NOT cryptographically tied. Matching summary counts is **not** a provenance proof.

## Deliverable A: static discovery of v0h source shape

`python -m search.spk_bv_v0j_probe --root . > /tmp/spk-bv-v0j-native-probe.json`

Scans only `.py` and `.sh` candidate files under `spk_bv_research/`, `search/`, `tests/`. Does not import or execute target code. Reports source SHA-256, selected function/class names, dataclass annotated members and relevant literal keys, within hard scanning bounds. Candidate matches are not automatically API contracts; inspect the actual native source before writing a mapping.

## Deliverable B: explicit native-to-v0i mapping boundary

`NativeMapping` requires paths to **all twelve** BV v0i `Reception` attributes. It never guesses `origin`, `batch_id`, `context_id`, `path_id`, or `transmission_id`. It rejects duplicate JSON keys, missing paths, changed IDs, inconsistent evidence, replayed transmission IDs and non-bijective packet mappings. Each input NDJSON row MUST be a real recorded physical feedback reception, not merely a unique vote or summary aggregate. Native provenance is preserved in an independent canonical whole-record SHA-256. `source_ordered_sha256` depends on row order; `source_multiset_sha256` does not.

Abstract cost units are either present in the native record (`native_positive_units`) or exactly one per native packet (`uniform_abstract_unit`); the latter assumption must be declared. No default physical unit, link, context, ID or timing field is silently invented. The bridge validates structural one-to-one mapping **only**. Its output always excludes source authenticity and equivalence to the original v0h witness.

**Manifest template (schematic; not executable until names verified):**

```json
{
  "schema": "spk-bv-native-packet-mapping/v0j",
  "source_label": "BV-v0h-inspected-native-physical-feedback-packets",
  "cost_model": "uniform_abstract_unit",
  "assumptions": ["One native NDJSON line equals one physically observed packet; verified against source producer"],
  "field_paths": {
    "epoch": ["native", "ACTUAL_EPOCH_KEY"],
    "transmission_id": ["native", "ACTUAL_PHYSICAL_PACKET_ID_KEY"],
    "observed_tick": ["native", "ACTUAL_DELIVERY_TICK_KEY"],
    "batch_tick": ["native", "ACTUAL_ORIGIN_BATCH_TICK_KEY"],
    "origin": ["native", "ACTUAL_SOURCE_NEURON_KEY"],
    "batch_id": ["native", "ACTUAL_UNIQUE_BATCH_ID_KEY"],
    "receiver": ["native", "ACTUAL_TARGET_NEURON_KEY"],
    "context_id": ["native", "ACTUAL_RECEPTION_CONTEXT_ID_KEY"],
    "evidence_code": ["native", "ACTUAL_SYMBOLIC_EVIDENCE_KEY"],
    "link_id": ["native", "ACTUAL_NETWORK_LINK_KEY"],
    "path_id": ["native", "ACTUAL_PHYSICAL_PATH_KEY"],
    "transport_units": 1
  }
}
```

If the native producer has no packet ID, link, or path, this mapping CANNOT be used faithfully. Do not substitute a row number, timestamp, or synthetic ID and then claim native equivalence. Instead report the missing dimension and revisit trace instrumentation as a future, non-frozen, research extension.

Once an authentic packet NDJSON + inspected manifest exists:

```bash
python -m search.spk_bv_v0j_bridge_cli \
  --mapping /path/to/inspected-v0h-mapping.json \
  --packets /path/to/authentic-native-physical-packets.ndjson
```

No new output path is written. On rejection, nothing is emitted to stdout.

## Deliverable C: pressure accounting, not an admission/scheduling model

For a hypothetical service capacity `C > 0` units/tick, the idealized residual queue is:

`B[t] = max(0, B[t-1] + arrivals[t] - C)`

Blank ticks are bridged analytically: no O(gap) iteration. Arrivals from independent epochs or links are never merged unless a separate global capacity is explicitly specified. The report includes backlog peak, overloaded ticks, and an **idealized** drain tick under infinite buffering, ideal work-conserving service, no setup/propagation and no priority differences. It does not produce actual message delay, A3d grant cycles, spike/feedback contention, energy, implementation scheduling or any savings claim. Only link feedback arrivals are available; sharing resources with spikes can change real pressure.

Example hypothetical capacities: `--link-capacity link-0:60 --link-capacity link-1:60 ... --global-capacity 200` for a native trace with exactly those link IDs. Do **not** interpret these example capacities as SPK hardware specifications.

## Gate

```bash
bash search/spk_bv_v0j_research_gate.sh
bash search/spk_bv_credit_v0a_full_regression.sh
```

The first includes v0j and inherited v0i tests, independent hashseed witness, static discovery, and a frozen package path guard. The second is the inherited full-functional suite with six historical branch-specific custody checks intentionally excluded.

## Next acceptance condition

An end-to-end native v0h producer must emit a packet-level trace with preserved identities, and its **independent** v0h replay evidence must be tied to the source trace under a documented algorithm. Passing the v0j synthetic adapter alone must NOT promote v0j to a validated BV v0h native bridge. No credit, learning or compression is allowed yet.
