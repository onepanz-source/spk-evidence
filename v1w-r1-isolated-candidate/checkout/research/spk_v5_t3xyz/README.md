# SPK V5/T3XYZ | passively instrument original T3OPQ Python producer

## Scope

* **T3X:** inject `sitecustomize.py` into the existing T3OPQ gate Python children, with `sys.setprofile`, tracing `_compute_local` call/return without rewriting SPK source.
* **T3Y:** verify the three legacy BV-v0e frozen pins and declared additive files before and after. Require **byte-identical SHA-256 `813753afd706eabff52653cf0a7674e1a44755981df61c6760fcbd4652c790d2`** for the instrumented T3OPQ report.
* **T3Z:** negative controls on fake semantic credit, absent provenance, broken trace sequences, stale source and reporting. Native single-pass C-generated semantic verdict is **not inferred** from CPython `_compute_local` entry/exit or from host posthoc terminal selection.

## Run on fwork

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T3XYZ_Passive_Source_Observation_Milestone_20261021.tar.gz
bash search/spk_v5_t3xyz_passive_native_observation_gate.sh /tmp/spk-v5-t3xyz-passive-observation.json
```

Produced files: main report, `-original.json`, `-original.log`, `-profile.jsonl`.

## Security / semantics

Passive instrumentation is not hardware attestation. It records Python call boundaries, not a receiver-origin signed semantic verdict. `sys.setprofile` can be bypassed or reset; sampling is incomplete outside interpreter events. The effect of profiling on runtime timing is not assumed zero: byte-for-byte report parity is mandatory. The log is a host observation and could be fooled by a malicious source (no signer). Do not treat the recorded node argument as authenticated identity. It is not an independent physically-sourced sensor. The generated report always sets `promotion_allowed=false`.

If the frozen source report changes or Python probe fails, the gate exits nonzero rather than pretending semantic closure. The source pin check covers three legacy files plus nine additive scripts, **not the entire transitive import closure**. No Core/Network/Compiler/Architecture source files are patched by this milestone.

Note: a distribution-installed `sitecustomize` can shadow this module. In that case `usercustomize` is tried; the gate fails at an automatic-hook preflight before launching the original source gate instead of fabricating evidence. The isolated unit tests load the hook explicitly to remain independent from the host Python configuration.

The included `fixtures/reference_t3opq.json` is a byte-exact copy of the user-supplied T3UVW original run, SHA `813753...c790d2`; it is a test reference, not independently acquired native evidence.
