# SPK BV v0k · Source-bound native fixture capture (research)

## Inherited checkpoint (reported by user, 2026-10-17)

- v0j 45 new tests PASS; inherited v0i 34 PASS.
- Functional repository regression: **3754 passed, 6 historical branch-specific custody deselected**.
- v0j synthetic/counterfactual `native_v0h_verified=false`. Its output `528 units`, `128 peak global backlog` and `288 summed link-backlog peaks` is **not** a native schedule or capacity measurement.
- Uploaded v0j native source probe: 48 files, untruncated candidate scan. The probe identifies:
  - `search/spk_bv_v0h_identified_evidence.py` (source SHA256 `c4cd05220d8dfec0e0cbacd6cac6430c33b6e01d46dd3317d38af090bfa46ab1`)
  - `tests/test_spk_bv_identified_v0h.py` (`real_trace` fixture, source SHA256 `82c0a5dccb5f0d6a96c35b339187a2eed3904536463350ddd71a343d6958bf16`)
  - `search/spk_bv_v0h_research_gate.sh` (source SHA256 `f75cb5846b58b21274cbce62ceb3331f810139d305b54b4210870aea178e9e5`)
- The probe scanned **selected filenames**, NOT a complete import/dependency graph. Those source hashes are local identifiers, not signatures.

## New work in v0k

1. `verify_probe`: refuse stale/missing source by comparing the 3 relevant file hashes and sizes to a freshly generated v0j probe, before **and after** source execution. Reject duplicate keys, symlinks, incomplete probe, oversized input. This prevents accidental replay against the wrong code revision; it is not a security boundary against a malicious worktree.
2. `capture`: run only the selected native test's `real_trace` pytest fixture. The test body is intentionally skipped once fixture setup completes. Captured data is never fabricated. A bounded, explicit JSON codec preserves tuples vs lists, non-string dictionary keys, dataclass fields and repeated occurrences. Unsupported classes, cycles and non-finite floats cause **REJECTED**, not a `repr()` placeholder.
3. Independent Python processes with different `PYTHONHASHSEED`s capture the same fixture twice. The native fixture digest MUST match. A mismatch is informative native nondeterminism, NOT evidence of equivalence. The native gate also snapshots all statically resolved research-source imports before and after the two captures and rejects any differences (dynamic imports are not covered).
4. AST-only dependency census follows static local `search` and `spk_bv_research` import edges (bounded). This matters because the original v0j filename probe could omit modules with generic names. Dynamic imports remain unresolved and are explicitly excluded.
5. All scripts remain outside frozen architectural packages. No changes to scheduler, Network, Core, Compiler, observer authority, v0h or v0i/v0j. No writes to the source tree are intended, though **pytest imports/fixture setup execute existing project code** and may create Python caches or other test artifacts. Run in the trusted research worktree.

## Install v0k incrementally

```bash
cd ~/workspace/spk-backvalidation-v0
# Ensure no unexpected tracked/staged changes before extraction.
git status --short

tar -tzf ~/Scaricati/spk-bv-v0k-source-bound-native-capture-research.tar.gz
tar -xzf ~/Scaricati/spk-bv-v0k-source-bound-native-capture-research.tar.gz

bash search/spk_bv_v0k_research_gate.sh
```

The research gate tests the adapter on **synthetic temporary fixtures only**, runs inherited v0i/v0j tests, checks the actual source SHA and static dependency census, then checks frozen package paths. It does **not** claim a successful real fixture capture until the *separate native gate* completes.

## Native fixture gate

```bash
bash search/spk_bv_v0k_native_gate.sh /tmp/spk-bv-v0k-native-fixture.json
```

The native gate performs two real fixture acquisitions under distinct hash seeds, requires identical canonical native fixture SHA-256, then publishes **one** capture file to the requested fresh absolute destination (never overwrites). It prints the actual capture output path. If it fails, no successful native result is established. The command requires actual BV v0h source and the `real_trace` fixture to be available locally. If it finds an unsupported native object, inspect native classes rather than inventing a serialization.

For further analysis, provide:

- `/tmp/spk-bv-v0k-native-fixture.json`, **only when the native gate passed**;
- optional AST dependency census: `python -m search.spk_bv_v0k_dependency_census --root . > /tmp/spk-bv-v0k-dependencies.json`;
- the original v0h source files if a faithful field-to-field mapping is needed, e.g. a reviewed source-only archive, never compiled assets or secrets.

Run the inherited complete regression separately:

```bash
bash search/spk_bv_credit_v0a_full_regression.sh
```

At unchanged collection coverage, the expected **new** total is 3754 + 21 = **3775 passed, 6 deselected**, subject to local repository discovery and test environment.

## Strict non-claims

`NATIVE_FIXTURE_CAPTURED_NOT_EQUIVALENCE` does not prove that the fixture holds the large 528 physical packets, that every item is physically delivered, or that its native packet identity maps faithfully onto all twelve v0i fields. The snapshot will include `native_v0h_verified=false` until independent v0h replay, packet-level provenance and bijection are actually established. No energy, performance, compression, utility, causal credit or learning claim may be drawn from these captures.

## Next acceptance condition

Read the actual capture and native producer shapes, derive a complete **explicit**, evidence-backed mapping. For missing packet fields, fail closed and add isolated observability only in research modules. Once packet bijection is independently proven, compare native ledger and counterfactual pressure to measured (not hypothetical) forward/feedback contention before promoting any computational cost claim.
