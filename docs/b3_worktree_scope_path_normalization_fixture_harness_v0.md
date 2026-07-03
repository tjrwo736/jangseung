# B3-4 Worktree Scope and Path Normalization Fixture Harness v0

## 1. Purpose

B3-4 turns the B3 worktree and path-scope bypass candidates into executable
fixtures. The fixture harness classifies candidate paths and records required
future closure work in deterministic in-memory data.

This is fixture, measurement, and classification work only. It does not deny
paths, harden the operating system or filesystem, create a sandbox, wire a
runtime executor write path, start live executor work, or start Phase 11-A.

## 2. B3-1/B3-2/B3-3 Recap

B3-1 documented raw capability and worktree scope inventory. It preserved
worktree scope, `.aeg/` scope-out, outside-repo, parent traversal, absolute path,
sibling worktree, symlink escape, Unicode ambiguity, and structured tool
broad-scope candidates as open future closure items.

B3-2 defined the capability non-grant policy contract. Capability non-grant
means policy contract state, not runtime denial proof.

B3-3 added deterministic capability policy evidence and verify replay. That
evidence remains about policy validation replay and is not a capability grant or
path-boundary proof.

## 3. B3-4 Scope

B3-4 adds `src/evidence/b3_worktree_scope_path_fixtures.py` as a pure
in-memory fixture harness. It classifies fixture cases into candidate/status
labels and required future closure labels.

The fixture harness does not create files, create symlinks, change permissions,
write `.aeg/`, write a ledger, call a network, call a provider/model, spawn a
process, add a command runner, or connect to any runtime executor path.

## 4. Fixture Case Schema

Each fixture case has:

- `case_id`
- `input_path`
- `worktree_root`
- optional `synthetic_symlink_map`
- `expected_candidate_type`
- `expected_required_closure`
- `note`

Each classification result has:

- `case_id`
- `input_path`
- `worktree_root`
- `normalized_input_path`
- `synthetic_resolved_path`
- `candidate_type`
- `classification_statuses`
- `required_closure`
- `interpretation`
- `note`

## 5. Path Normalization Assumptions

The harness uses POSIX-like string normalization for fixtures. It normalizes
separators, collapses `.` and `..` segments, treats relative paths as relative
to the synthetic worktree root, and resolves only the provided synthetic symlink
map.

No real path is probed. No filesystem metadata is read. No symlink is created.
The normalized and synthetic-resolved paths are fixture observations only.

## 6. `.aeg/` Scope-Out Fixture Cases

Included cases:

- `aeg_direct_path`: `.aeg/evidence.jsonl`
- `aeg_via_parent_traversal`: `src/../.aeg/ledger.jsonl`
- `symlink_escape_to_aeg`: `links/aeg-state/evidence.jsonl` with a synthetic
  symlink map to `.aeg`

Expected classification includes `AEG_SCOPE_OUT_REQUIRED`,
`FUTURE_CLOSURE_REQUIRED`, and `EXPECTED_RED_OR_KNOWN_GAP`.

## 7. Outside-Repo / Traversal / Absolute Path Fixture Cases

Included cases:

- `outside_repo_via_parent_traversal`: `../outside-repo/file.txt`
- `absolute_path_outside_repo`: `/var/tmp/aegis-output.txt`

Expected classification includes outside-repo, parent traversal, and absolute
path candidate labels as applicable. These are fixture observations and future
closure inputs.

## 8. Symlink Escape Fixture Cases

Included cases:

- `symlink_escape_to_aeg`
- `symlink_escape_to_outside_repo`

The symlink map is synthetic data. The harness resolves aliases only from this
map and never creates an actual symlink.

## 9. Sibling Worktree Fixture Cases

Included case:

- `sibling_worktree_path`: `../Aegis-sibling/src/file.py`

This captures adjacent checkout/worktree confusion as a measurable candidate.

## 10. Unicode Ambiguity Fixture Cases

Included case:

- `unicode_path_ambiguity_candidate`: `src/．aeg/report.txt`

The fullwidth dot has different normalization behavior. The harness records it
as `UNICODE_AMBIGUITY_CANDIDATE` and future path canonicalization work.

## 11. Structured Tool Broad-Filesystem Scope Fixture Cases

Included case:

- `structured_tool_broad_filesystem_scope`: `structured://filesystem/{workspace}/**`

This captures broad structured filesystem scope as a candidate that can exist
without raw shell authority.

## 12. Expected Red / Known Gap Interpretation

Every fixture result includes `EXPECTED_RED_OR_KNOWN_GAP`. This means the
candidate is intentionally measured as open B3 closure work. It does not mean
the path is denied, impossible, externally blocked, or closed.

## 13. Future B3 Closure Candidates

Future B3 closure candidates include:

- canonical worktree scope decisions
- `.aeg/` scope-out decisions
- outside-repo scope decisions
- parent traversal handling
- absolute path handling
- sibling worktree handling
- symlink escape handling
- Unicode ambiguity handling
- structured tool broad-filesystem scope handling

## 14. B3-5 Handoff

B3-5 can consume B3-4 fixture results as status-note input only. It does not
upgrade these fixture results into runtime write authority or live executor
approval. It does not start Phase 11-A or close B3.

## 15. Explicit Non-Claims

B3-4 makes these explicit non-claims:

- no path denial enforcement
- no raw shell authority grant
- no write_file tool
- no run_command tool
- no process_spawn tool
- no network authority grant
- no provider/model call authority grant
- no remote write authority grant
- no repo outside write authority grant
- no OS/filesystem enforcement
- no sandbox/container
- no physical impossibility proof
- no executor isolation
- no runtime tool gating
- no live executor
- no runtime write authority grant
- no Phase 11-A start
- no B3 closure
- no B1 hard blocker fully green
- no Live Executor Entry Gate approval

## 16. Safe Default

```text
safe default = hold_current_state
```
