# Phase 11-B-0 store write mediation v0

Phase 11-B-0 wires the actual `src/state/store.py` run-save path to record and
enforce a narrow mediated path for executor-attributed `.aeg` writes.

## Scope

Implemented:

- `store.py` records Phase 11-B-0 store write mediation metadata before
  manifest and ledger hashes are finalized.
- Executor-attributed `.aeg` direct and traversal write attempts supplied to
  the actual `aeg run` save path are routed through the B1 `.aeg` guard and the
  deny-only mediator before mutation.
- Guarded executor-attributed `.aeg` attempts are blocked and do not create the
  target file.
- Trusted Aegis runtime writes for `run.json`, `manifest.json`,
  `evidence.json`, and `ledger.jsonl` remain allowed by deterministic
  `store.py` call-site provenance.
- Trusted runtime wired-path failure falls back to the existing unwired store
  write path, records fallback evidence, and keeps `save_run` from crashing.

Not implemented:

- live model executor
- provider/model/network call
- raw shell authority
- general `write_file` or `run_command` tool
- unrestricted runtime write authority
- OS/filesystem/sandbox/container enforcement
- IPC or external enforcement
- outside-repo/general filesystem known-gap hardening

## Evidence Fields

The evidence packet and manifest now bind a `STORE_WRITE_MEDIATION_FIELDS`
group, including:

- `store_write_mediation_enabled`
- `store_write_mediation_scope`
- `write_provenance_source`
- `executor_attributed_write_blocked`
- `trusted_runtime_write_allowed`
- `blocked_write_target_count`
- `blocked_write_created_files_count`
- `write_mediation_result`
- `write_mediation_reason`
- `rollback_used`
- `fallback_to_unwired`
- `live_executor_authority`
- `phase11b_live_executor_status`
- `store_write_mediation_metadata_hash`

The legacy Phase 10 broad scaffold fields remain unchanged:
`write_mediation_enabled=false` and `write_mediation_enforced=false`.

## Replay Rejection

`aeg verify` rejects:

- `blocked_write_created_files_count > 0` while claiming `BLOCKED`
- executor self-report trusted provenance
- missing store write mediation binding
- trusted runtime write failure recorded as success
- `rollback_used` / `fallback_to_unwired` mismatch
- live executor authority promotion
- Phase 11-B live executor start claims

## Known-Gap Transition

For this scoped actual run path only, `.aeg` direct/traversal executor-attributed
write attempts move from `CURRENTLY_BYPASSABLE` evidence baseline to `BLOCKED`
when exercised through `store.py`.

Raw shell, outside-repo write, network/provider, and general filesystem
known-gaps remain out of scope and unchanged.
