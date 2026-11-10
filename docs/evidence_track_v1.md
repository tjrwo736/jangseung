# Evidence track v1

## Scope

Evidence track v1 covers two capabilities without changing the
classification or law judgment brain:

1. a dedicated append-only ledger for live hook decisions;
2. read-only inspection of that ledger (`aeg evidence list`, `show`,
   `verify-hooks`) and an explicit repair command (`repair-hooks`).

Policy configuration is intentionally out of scope.

## Storage boundaries

Live hook decisions are stored in one file:

- `.aeg/hook_ledger.jsonl`

Every row of `aeg evidence list` is labeled `HOOK`. Files left by the removed
run runtime (`.aeg/ledger.jsonl`, `.aeg/runs/`, `.aeg/config.json`) are not
read, rewritten or deleted.

## Hook record contents

Each hook record contains:

- record version and sequence number;
- UTC timestamp;
- substrate and validated tool name;
- brain decision and substrate-mapped permission decision;
- fail-closed flag and reason codes;
- process exit code;
- previous record hash and record hash.

Since 0.2.0, optional call-summary fields are `targets` (project-relative paths),
`commands` (short program names only), `session_id`, and `input_hash` (SHA-256).
File contents and command arguments are not stored. These are redacted summaries,
not a content-secret scanner: a secret used as a file or program name may remain.

Normal allow/ask/deny records retain `hook_decision_record_v1`. A result delegated
to Claude Code's normal permission policy uses `hook_decision_record_v2` with:

- `substrate: claude-code`, `tool_name: Bash` or `PowerShell`;
- `hook_decision: defer`, `permission_decision: host`, `fail_closed: false`;
- `exit_code: 0` and reason code `claude_default_host_permission_flow`.

The verifier checks these semantic constraints as well as the chain. The host
receives no permission decision (`{}`); `host` is an internal/record value, not a
wire permission value. List/show render it as `HOST`. It proves neither the host's
final permission decision nor tool execution. There is no new record of the raw
command or final host result.

0.2.0 reads v1, v2, and mixed chains. **0.1.9 and earlier cannot verify or append
to a chain containing v2.** Downgrade requires a deliberate ledger-retention plan;
no records are automatically removed or converted.

Raw stdin and `tool_input` are not passed to the recorder. The hash chain is
tamper-evident, not tamper-proof. It detects record changes and middle-record
deletion, but a local ledger has no external anchor that can prove its final
record or the complete file was not deleted.

## Recording failure policy

The default is **preserve the judgment**. A recorder failure does not change
`permissionDecision` or the substrate-specific exit code. The response reason
codes gain `hook_decision_recording_failed`.

For a host-delegated result, the response still omits a permission decision and
reports the fixed failure reason in `systemMessage`. A failed append does not
turn host delegation into allow, ask, or deny.

This keeps the judgment brain authoritative and prevents an observability
failure from silently converting an allow to deny or a deny to allow. Existing
parse, validation, or judgment failures remain fail-closed deny exactly as
before. Deployments that require "no record, no execution" need an external
enforcement/availability policy; that policy is not introduced in this track.

## Concurrency and durability

Writers use a cross-platform exclusive lock file, verify the existing chain,
append one canonical JSON line, flush it, and call `fsync`. A lock acquisition
timeout is reported through the recording-failure policy above. The lock is a
local filesystem coordination mechanism, not a distributed lock.

As of 0.1.3, a persistent `hook_ledger.guard` file carries an OS-backed lock
(Windows byte-range lock or POSIX flock). It is not deleted between writers.
The existing `hook_ledger.lock` PID sentinel is retained to coordinate with
0.1.2 writers. While holding the OS guard, a new writer may remove a stale PID
sentinel only after positively establishing that its process has exited.
Active, inaccessible, reused or invalid PIDs are not treated as dead. Empty or
malformed legacy sentinel files need operator inspection with writers stopped.
The guard is released by the OS on process exit; network filesystem semantics
are outside the tested local-filesystem contract.

## Installation and damaged input (0.1.3)

After explicit confirmation, `aeg install` now prepares a missing `.aeg/` for
hook recording, including an internal `.gitignore` for newly created state.
It never rewrites existing records. Reinstalling an already registered hook may
repair missing recording state after confirmation without changing that hook's
config.

Read-only list/show keep their no-write boundary. Invalid UTF-8 ledger lines
are UNREADABLE, while other lines remain inspectable.
Invalid hook lines (including JSON null) still fail chain verification and block
subsequent appends. Inspection does not repair or discard damaged records.
