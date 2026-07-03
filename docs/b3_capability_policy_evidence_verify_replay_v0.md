# B3-3 Capability Policy Evidence and Verify Replay v0

## 1. Purpose

B3-3 binds the B3-2 capability policy validation result into a deterministic
evidence record and provides verify replay for mismatch, tamper, and overclaim
rejection.

The evidence line is policy validation evidence. It is not a capability grant,
runtime enforcement, tool execution gating, OS/filesystem enforcement, sandbox
work, live executor work, or Phase 11-A work.

## 2. B3-1 / B3-2 Recap

B3-1 documented the raw capability inventory, worktree scope requirements, and
non-grant baseline. B3-2 added a machine-checkable policy contract that defaults
raw shell, file write, command run, process spawn, network, provider/model,
remote write, outside-repo write, `.aeg` state, environment, and secret
capabilities to non-grant policy status.

B3-2 also rejects reported-only or unchecked promotion to PASS-like capability
claims and rejects overclaim flags in the policy contract.

## 3. B3-3 Scope

B3-3 adds:

- deterministic evidence record construction for B3-2 validation output.
- deterministic canonical JSON digest binding.
- verify replay that re-runs B3-2 validation.
- rejection of mismatch, tamper, and overclaim inputs.

B3-3 does not add command execution, provider calls, network calls, process
spawn, live executor authority, runtime write path wiring, `.aeg` write
hardening, or path/scope fixture work.

## 4. Evidence Record Schema

The evidence record contains:

| Field | Meaning |
| --- | --- |
| `record_kind` | `b3_capability_policy_validation_evidence`. |
| `record_version` | `b3_capability_policy_evidence_v0`. |
| `claim_type` | States that the record is policy validation evidence, not a capability grant. |
| `capability_policy_digest` | SHA-256 digest of the normalized policy input. |
| `policy_validation_outcome` | Bound B3-2 validation result summary. |
| `capability_fields_summary` | Bound per-capability fields used for replay comparison. |
| `rejected_overclaim_candidates` | Deterministic list of rejected overclaim candidates. |
| `authority_snapshot` | Current authority snapshot for B3-3. |
| `boundary_preservation` | B3-1 preserved and B3-4 not started flags. |
| `non_claim_caveats` | Explicit non-claims for the record. |
| `source_contract_module_version_note` | B3-2 source contract module and version note. |
| `deterministic_evidence_digest` | SHA-256 digest of the evidence payload without this field. |

## 5. Deterministic Canonicalization / Digest Rule

Canonical JSON uses `sort_keys=True`, ASCII output, and compact separators.

`capability_policy_digest` hashes the normalized capability policy input.
`deterministic_evidence_digest` hashes the evidence record after removing only
the `deterministic_evidence_digest` field. Replaying the same input produces the
same record and digest.

## 6. Verify Replay Behavior

Verify replay receives an evidence record and a capability policy input. It:

1. re-runs B3-2 validation against the policy input.
2. rebuilds the expected B3-3 evidence record from the replayed validation.
3. recomputes the policy digest.
4. recomputes the evidence digest.
5. compares authority snapshot, validation outcome, capability summary, source
   note, non-claim caveats, and boundary preservation.
6. returns `VERIFY_REPLAY_ACCEPTED` or `VERIFY_REPLAY_REJECTED`.

Rejection is a verify result only. It is not runtime enforcement.

## 7. Mismatch / Tamper / Overclaim Rejection Cases

Verify replay rejects:

- capability field summary mismatch.
- policy digest mismatch.
- evidence digest mismatch.
- authority snapshot mismatch.
- validation outcome mismatch.
- `granted=true` with missing evidence.
- `reported_only` with PASS-like claim.
- `NOT_CHECKED`, missing, or unknown check state with PASS-like claim.
- `granted=true` with unknown grant source.
- physical impossibility claim.
- external denial claim.
- composition closure or bypass impossibility claim.
- structured tool safety claim.
- live executor ready claim.
- Phase 11-A started claim.
- B3 closure claim.
- runtime enforcement or tool gating claim.

## 8. reported_only / NOT_CHECKED Handling

`reported_only` remains non-authoritative for PASS-like capability claims.
`NOT_CHECKED`, missing, and unknown check states remain non-PASS evidence. B3-3
does not promote either status. Replay rejects records or policy inputs that try
to promote them.

## 9. Current Authority Snapshot

| Item | Current status |
| --- | --- |
| Runtime write path | `NOT_WIRED_TO_EXECUTOR_WRITE_PATH` |
| Live executor authority | `LIVE_EXECUTOR_AUTHORITY_ON_HOLD` |
| Phase 11-A | `PHASE11A_NOT_STARTED` |
| Safe default | `hold_current_state` |

## 10. B3-4 Handoff

B3-3 does not start B3-4 path/scope fixture work. B3-4 remains the later line
for path normalization and worktree scope fixture measurement.

## 11. Explicit Non-Claims

B3-3 makes no claim of:

- raw shell authority grant.
- `write_file` tool.
- `run_command` tool.
- `process_spawn` tool.
- network authority grant.
- provider/model call authority grant.
- remote write authority grant.
- repo outside write authority grant.
- OS/filesystem enforcement.
- sandbox/container.
- physical impossibility proof.
- executor isolation.
- runtime tool gating.
- live executor.
- runtime write authority grant.
- Phase 11-A start.
- B3 closure.
- B1 hard blocker fully green.
- Live Executor Entry Gate approval.

## 12. Safe Default

```text
safe default = hold_current_state
```
