# Read-only hook diagnostics v1

## Scope

This is an additive presentation/inspection layer. Classification, law, hook
judgment, permission mapping and live `hook-run` recording are unchanged.
No provider, network, tool execution, configuration write, record append or
lock recovery is performed by either diagnostic command.

## Explain

```text
aeg explain (--command TEXT | --file PATH | --stdin)
            [--tool Bash|PowerShell] [--substrate claude-code|codex] [--json]
```

`--tool` applies only to `--command` (default Bash). `--file` constructs a Read
request without reading the file content. `--stdin` accepts one PreToolUse JSON
object; use it for Write/Edit/apply_patch or complete host payloads. The default
substrate is claude-code, matching hook-run. Cwd is passed to the same pure
`render_hook_response` used by hook-run; it is not silently replaced by a Git
root. Filesystem metadata can influence the decision, so an earlier explanation
is not authorization for a later request in a changed context.

The output separates `hook_decision`, `permission_decision`, `hook_exit_code`
and `fail_closed`. Human-readable categories are derived from existing reason
codes, not a second policy engine. `unclassified` explicitly means that safety
was not established, not that a command was proven dangerous. Composite
protected/outside target codes are not falsely narrowed to a more specific
cause. Codex ask/defer-to-deny mapping is described separately.

Only known metadata and reason codes are displayed. Unknown tool names,
arbitrary validator suffixes, raw commands, paths, contents and raw input are
not echoed. Known required-field names and capability constants are retained.
`reason_details_redacted` identifies any such filtering. Input and exception
text are never included in diagnostic errors. CLI input is bounded to 1 Mi
characters. No history or report file is written by the command; users remain
responsible for their shell's own history/redirection behavior.

| Explain process exit | Meaning |
| --- | --- |
| 0 | Explanation completed, including a policy deny/ask |
| 1 | Simulated fail-closed input/error, or diagnostic failure |
| 2 | Invalid CLI usage |

The actual hook exit is only `hook_exit_code`. An explain process is never a
replacement for an installed hook. Recording is `NOT_ATTEMPTED`; live host
execution is `NOT_CHECKED` even for an allow result.

## Doctor

`aeg doctor --hooks [--target claude-code|codex|all] [--json]` adds hook checks
to the existing runtime checks. Default target is all. `--json` also works
without `--hooks`; legacy human output remains the default. A FAIL returns 1;
warnings alone return 0 with PASS_WITH_WARNINGS, as in the existing doctor.

Hook checks are a project-local snapshot at the detected Git root:

- Config structure, exact installer-recognized hook registration, target
  substrate and the literal current installer matcher (custom matchers are
  NOT_CHECKED, not inferred to cover tools).
- Current-platform executable existence/permissions. Nothing is executed;
  Python `-m src.cli` imports in another interpreter are NOT_CHECKED.
- Recording directory metadata and permissions, without any write probe.
- Persistent guard metadata (presence is normal; actual OS lock activity is
  NOT_CHECKED), PID sentinel state and existing ledger hash chain.
- Git ignore rules for expected state artifacts, plus any currently unignored
  state files. Internal `.aeg/.gitignore` and root ignore rules are supported;
  negation exceptions cannot be hidden by a directory-only check.

Malformed configuration, unexpected file types and linked config/state/ledger
paths are reported without following them. Configuration reads are limited to
1 MiB and the automatic hook-chain check to 16 MiB. Larger data is explicitly
NOT_CHECKED with a warning; `aeg evidence verify-hooks` remains the explicit
full-ledger inspection command. Parser/config/lock payloads are not printed.
Decoder recursion limits reached by deeply nested damaged ledger entries are
reported as FAIL without a traceback or record contents on supported Python
versions.

No lock is acquired, stale lock removed, missing directory created, input file
rewritten, or executable started. Concurrent writers may change the snapshot;
rerun after writers settle if necessary. Host-global settings, host approval,
actual dispatch, executable identity and successful disk writes remain
NOT_CHECKED. A matching local hash chain is tamper-evident, not tamper-proof.
