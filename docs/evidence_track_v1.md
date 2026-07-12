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
