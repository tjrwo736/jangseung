# Evidence track v1

## Scope

Evidence track v1 adds two additive capabilities without changing the
classification or law judgment brain:

1. read-only inspection of existing run evidence;
2. a dedicated append-only ledger for live hook decisions.

Policy configuration is intentionally out of scope.

## Storage boundaries

Run evidence keeps its existing layout and schema:

- `.aeg/ledger.jsonl`
- `.aeg/runs/<run-id>/run.json`
- `.aeg/runs/<run-id>/evidence.json`
- `.aeg/runs/<run-id>/manifest.json`

Live hook decisions are a different evidence kind and are stored separately:

- `.aeg/hook_ledger.jsonl`

Mixing the two ledgers would overstate the audit scope of a run. The evidence
CLI may present both kinds in one list, but every row is labeled `RUN` or
`HOOK`, and the persisted formats remain separate.

## Hook record contents

Each hook record contains only:

- record version and sequence number;
- UTC timestamp;
- substrate and validated tool name;
- brain decision and substrate-mapped permission decision;
- fail-closed flag and reason codes;
- process exit code;
- previous record hash and record hash.

Raw stdin and `tool_input` are not passed to the recorder. The hash chain is
tamper-evident, not tamper-proof. It detects record changes and middle-record
deletion, but a local ledger has no external anchor that can prove its final
record or the complete file was not deleted.

## Recording failure policy

The default is **preserve the judgment**. A recorder failure does not change
`permissionDecision` or the substrate-specific exit code. The response reason
codes gain `hook_decision_recording_failed`.

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
It never rewrites existing records or initializes the run ledger. Reinstalling
an already registered hook may repair missing recording state after confirmation
without changing that hook's config. `aeg init` remains the separate full run
state initialization command.

Read-only list/show keep their no-write boundary. Missing run artifacts and
invalid UTF-8 ledger lines are UNREADABLE, while other lines remain inspectable.
Invalid hook lines (including JSON null) still fail chain verification and block
subsequent appends. Inspection does not repair or discard damaged records.
