#!/usr/bin/env bash
# Authoritative gate: run AFTER committing A5d; verify from two clean Git clones.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd -P)
cd "$repo"
branch=spk-architecture-v1
tag=spk-architecture-bounded-reference-v1
if [[ $(git -C "$repo" branch --show-current) != "$branch" ]]; then
  echo 'RELEASE DENIED: wrong source branch' >&2; exit 1
fi
if [[ -n $(git -C "$repo" status --porcelain --untracked-files=all) ]]; then
  echo 'RELEASE DENIED: source worktree not clean' >&2; exit 1
fi
if git -C "$repo" show-ref --verify --quiet "refs/tags/$tag"; then
  echo 'RELEASE DENIED: release tag already exists; never silently move tags' >&2; exit 1
fi
python -m search.spk_arch_a5d_release_evidence_v1d --preflight
source_head=$(git -C "$repo" rev-parse HEAD)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
# --no-hardlinks avoids cloned packs sharing files with the source repository.
# Both checkout heads must be the same committed candidate with original tag.
git clone -q --no-hardlinks --branch "$branch" "$repo" "$tmp/one"
git clone -q --no-hardlinks --branch "$branch" "$repo" "$tmp/two"
for clone in "$tmp/one" "$tmp/two"; do
  test "$(git -C "$clone" rev-parse HEAD)" = "$source_head"
  test "$(git -C "$clone" branch --show-current)" = "$branch"
  test "$(git -C "$clone" cat-file -t refs/tags/spk-simulator-bounded-reference-v0)" = tag
  test -z "$(git -C "$clone" status --porcelain --untracked-files=all)"
done

printf '\n[1/6] A5d committed source custody and release boundary tests in isolated clone\n'
(cd "$tmp/one" && python -m pytest -q tests/test_spk_arch_a5d_release_v1d.py)

printf '\n[2/6] Frozen Compiler and cross-system release witnesses in isolated clone\n'
(cd "$tmp/one" && python -m pytest -q tests/test_spk_arch_a5d_frozen_v1d.py)

printf '\n[3/6] Independent clone + process release evidence, source pinning and replay\n'
(cd "$tmp/one" && python -m search.spk_arch_a5d_release_evidence_v1d --write "$tmp/one.json")
(cd "$tmp/two" && python -m search.spk_arch_a5d_release_evidence_v1d --write "$tmp/two.json")
cmp "$tmp/one.json" "$tmp/two.json"
(cd "$tmp/one" && python -m search.spk_arch_a5d_release_evidence_v1d --verify "$tmp/two.json")
(cd "$tmp/two" && python -m search.spk_arch_a5d_release_evidence_v1d --verify "$tmp/one.json")

printf '\n[4/6] A5a/A5b/A5c and A4d protected regressions in isolated clone\n'
(cd "$tmp/one" && python -m pytest -q \
  tests/test_spk_arch_a5a_inventory_v1a.py \
  tests/test_spk_arch_a5b_metamorphic_v1b.py \
  tests/test_spk_arch_a5c_adversarial_v1c.py \
  tests/test_spk_arch_a4d_state_custody_v1d.py)

printf '\n[5/6] Full repository regression from clean isolated Git clone\n'
(cd "$tmp/one" && python -m pytest -q)

printf '\n[6/6] Frozen baseline, Git ancestry, tracked source and release freeze eligibility\n'
(cd "$tmp/one" && python - <<'PY'
from pathlib import Path
import subprocess
from spk_architecture_v1.release_conformance_v1d import release_committed_v1d, RELEASE_TAG
p=release_committed_v1d(Path.cwd())
assert p['predecessor_phases']==19 and p['predecessor_files']==115
assert p['candidate_release_files']==6 and p['source_files']==121
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head==p['head_commit']
assert subprocess.run(['git','show-ref','--verify','--quiet','refs/tags/'+RELEASE_TAG]).returncode!=0
print('SPK A5d committed source, frozen baseline and immutable release tag: PASS')
PY
)
(cd "$tmp/two" && python - <<'PY'
from pathlib import Path
from spk_architecture_v1.release_conformance_v1d import release_committed_v1d
assert release_committed_v1d(Path.cwd())['source_files']==121
print('SPK A5d second checkout independent source audit: PASS')
PY
)
printf '\nSPK ARCHITECTURE A5d BOUNDED RELEASE GATE: PASS (committed source, two independent clones)\n'
printf 'RELEASE_COMMIT=%s\n' "$source_head"
printf 'RELEASE_TAG_ELIGIBLE=%s (not created automatically)\n' "$tag"
