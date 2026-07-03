# Phase 11-B-0 store write mediation v0

Phase 11-B-0R wires the actual `src/state/store.py` disk-write sinks to record
and enforce a narrow mediated path for executor-attributed `.aeg` writes.

## Scope

Implemented:

- `store.py` records Phase 11-B-0 store write mediation metadata before
  manifest and ledger hashes are finalized.
- `_write_json` is guarded immediately before `path.write_text`.
- `_append_ledger_unmediated` is guarded immediately before
  `open("a").write`. "Unmediated" means the trusted-runtime internal append
  path, not an executor-bypassable unguarded sink.
- Executor-attributed `.aeg` direct and traversal write attempts supplied to
  the actual `aeg run` save path are attempted at the `_write_json` sink and
  blocked before mutation.
- Executor-attributed forged ledger appends are attempted at the
  `_append_ledger_unmediated` sink and blocked before append.
- Guarded executor-attributed `.aeg` attempts create zero target files and
  append zero forged ledger entries.
- Trusted Aegis runtime writes for `run.json`, `manifest.json`,
  `evidence.json`, and `ledger.jsonl` remain allowed by deterministic
  `store.py` call-site provenance.
- Executor self-report, trusted-provenance claims, omitted declarations, and
  direct sink calls are not accepted as trusted provenance.

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
- `store_write_boundary`
- `guarded_sinks`
- `write_json_sink_guarded`
- `ledger_append_sink_guarded`
- `write_provenance_source`
- `executor_attributed_write_blocked`
- `executor_direct_sink_write_result`
- `executor_direct_sink_write_created_files_count`
- `executor_direct_ledger_append_result`
- `executor_direct_ledger_entries_appended_count`
- `trusted_runtime_write_allowed`
- `trusted_runtime_ledger_append_allowed`
- `executor_self_report_ignored`
- `executor_omitted_declaration_rejected`
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
- `executor_direct_sink_write_result=BLOCKED` when the target file exists
- `executor_direct_ledger_append_result=BLOCKED` when a forged entry appended
- `SINK_LEVEL_GUARDED` claims without both `_write_json` and
  `_append_ledger_unmediated` guarded sink events
- executor self-report trusted provenance
- omitted declaration treated as trusted provenance
- missing store write mediation binding
- trusted runtime write failure recorded as success
- trusted runtime ledger append failure recorded as success
- `rollback_used` / `fallback_to_unwired` mismatch
- live executor authority promotion
- Phase 11-B live executor start claims

## Known-Gap Transition

For this scoped actual run path only, `.aeg` direct/traversal executor-attributed
write attempts move from `CURRENTLY_BYPASSABLE` evidence baseline to `BLOCKED`
when exercised through `store.py`.

Raw shell, outside-repo write, network/provider, and general filesystem
known-gaps remain out of scope and unchanged.
