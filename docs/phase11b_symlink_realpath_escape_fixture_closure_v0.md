# Phase 11-B-1f Symlink Realpath Escape Fixture Closure v0

## 1. Purpose

This closure adds deterministic fixtures for the remaining classified-only
symlink realpath escape gap from the 11-B-1 audit line. A structured action can
look lexically repo-relative while resolving through a symlink into protected
state, a secret/env target, or outside the repository. The fixture closure
checks those cases before any live executor work.

This does not change the accepted Phase 11-B-1 completion status. It is an
addendum fixture closure before live executor work.

## 2. Relationship to 11-B-1d

11-B-1d established deterministic structured action injection fixtures and
left symlink escape as a future classified fixture. This closure adds a
separate symlink realpath fixture harness and wires optional `repo_root`
realpath checks into the structured action validator and capability gate.

The 11-B-1d fixture set remains a tool-injection baseline. This addendum
focuses only on realpath target scope.

## 3. Why lexical path checks are insufficient

Lexical checks catch paths such as `.aeg/ledger.jsonl`, `.env`, absolute paths,
and parent traversal. They do not prove the final filesystem target when a
repo-relative path crosses a symlink. For example, `link_to_aeg/evil.json` can
look like a normal repo-relative target while resolving to `.aeg/evil.json`.

Therefore target scope checks need a repo-root realpath pass when symlink
fixtures are evaluated.

## 4. Realpath / symlink escape threat model

The fixture threat model covers structured action target fields that resolve
through symlinks into:

- `.aeg/` runtime state
- a path outside the repository root
- `.env` or env/secret-like targets
- nested symlink chains
- traversal plus symlink combinations

All such cases fail closed as data validation or limited-scope gate rejection.

## 5. Supported symlink fixtures

The deterministic fixture set covers:

- `repo/link_to_aeg -> repo/.aeg`, target `link_to_aeg/evil.json`
- `repo/link_to_outside -> outside tempdir`, target `link_to_outside/outside.txt`
- `repo/link_to_env -> repo/.env`, target `link_to_env`
- nested `repo/link_a -> repo/link_b -> repo/.aeg`
- `safe_dir/../link_to_aeg/evil.json`
- `PROPOSE_PATCH` with `target_files = ["link_to_aeg/evil.json"]`
- `REQUEST_REPO_READ` with `target = link_to_aeg/ledger.jsonl`
- inert `PROPOSE_PATCH` to a normal repo-relative target

The test fixture creates all symlinks and files only under
`tempfile.TemporaryDirectory`.

## 6. Unsupported platform handling

If symlink creation is unavailable or blocked by platform permissions, the
fixture status must remain `NOT_CHECKED_SYMLINK_UNSUPPORTED` or
`NOT_CHECKED_PLATFORM_PERMISSION_LIMIT`. It must not be promoted to PASS, and
the verifier rejects `PASS_WITHOUT_SYMLINK_REALPATH_TEST` and
`SYMLINK_SAFE_WITHOUT_REALPATH_TEST`.

`NOT_CHECKED` is not a pass condition.

## 7. PROPOSE_PATCH data-vs-target-scope distinction

`PROPOSE_PATCH` patch text remains inert review data. The patch diff is not
executed and does not grant write authority.

The target list is different: `target_files` and target-scope paths are still
scope-bearing data. If a target resolves through a symlink into `.aeg/`, `.env`,
or outside the repo, the action is rejected even when the patch diff itself is
valid inert data.

## 8. Non-execution guarantee

The fixture harness calls only the structured action validator and capability
gate. It does not run patch text, dispatch actions, spawn processes, invoke
shells, import modules dynamically, call providers, or use the network.

The result fields remain:

- `execution_allowed = false`
- `live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD`

## 9. Non-mutation guarantee

Fixture setup creates tempdir-only test files and symlinks. Fixture evaluation
does not mutate the repository filesystem, `.aeg`, `.env`, or target files.

The result fields remain:

- `mutation_allowed = false`
- `write_authority_granted = false`

## 10. Fixture rejection is not bypass impossible

Rejecting these deterministic fixtures means the covered structured action
validator/gate path rejects the listed symlink realpath cases. It is not a
proof that every possible bypass is impossible. It is also not a claim that the
tool system is safe, that write authority is safe, or that a live executor is
ready.

## 11. Relationship to PR #81

This closure does not modify PR #81. It does not release PR #81 from draft,
merge PR #81, rebase PR #81, or sync PR #81.

The contract status remains:

- `pr_81_status = HOLD_OPEN_DRAFT_UNTOUCHED`
- `pr_81_draft_release = NOT_PERFORMED`
- `pr_81_merge = NOT_PERFORMED`

## 12. Explicit non-goals

This closure does not implement:

- live model executor
- runtime action execution engine
- provider/model/network path
- raw shell, `write_file`, `run_command`, or process spawn authority
- eval, exec, or dynamic import execution path
- store sink guard changes
- process isolation, OS permission enforcement, sandbox, container, or IPC
- PR #81 changes
- main direct push

## 13. Safe default

The safe default remains `hold_current_state`.

Evidence direction added by this closure:

- `symlink_realpath_fixture_status`
- `symlink_realpath_checked`
- `symlink_realpath_support_status`
- `symlink_escape_rejected_count`
- `symlink_escape_allowed_count`
- `realpath_escape_rejected_count`
- `realpath_escape_allowed_count`
- `execution_allowed = false`
- `mutation_allowed = false`
- `write_authority_granted = false`
- `live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD`
