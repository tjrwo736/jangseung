# Aegis B1-C `.aeg/` Integrity Guard Evidence Binding v0

## Scope

This note records the B1-C component that binds a B1-B `.aeg/` deny-only guard
decision to a deterministic evidence record. It is evidence binding only.

This component is not `.aeg` external storage, not an external anchor, not OS or
filesystem hardening, not executor isolation, not runtime write-path wiring, and
not a live executor or Phase 11-A start.

## Bound Record

Each bound record includes:

- `submitted_path`
- `resolved_path`
- `protected_root`
- `target_class`
- `denial_reason`
- `wiring_status`

The record also embeds the B1-B guard decision, a no-mutation observation, the
B1-A raw known-gap baseline status, and the current non-wiring/non-enforcement
statuses.

The digest is canonical JSON SHA-256 over the evidence payload. The record id is
deterministic from that digest.

## Decision Coverage

- Direct `.aeg/` guard denial binds to a `B1_AEG_GUARD_EVIDENCE_RECORD`.
- Traversal `.aeg/` guard denial binds to a `B1_AEG_GUARD_EVIDENCE_RECORD`.
- Symlink `.aeg/` guard denial binds when the symlink fixture is available.
- `.aeg/ledger.jsonl` denial binds.
- `.aeg/manifest` denial binds.
- `.aeg/runs/.../evidence_packet.json` denial binds.
- `.aeg/runs/.../verify_basis.json` denial binds.

## Boundary

The binding records:

```text
B1_AEG_GUARD_DECISION_BOUND
B1_AEG_GUARD_NO_MUTATION_OBSERVATION_BOUND
B1_AEG_GUARD_EVIDENCE_DIGEST
B1_AEG_EVIDENCE_BINDING_NOT_TAMPER_PROOF
B1_AEG_EVIDENCE_BINDING_NOT_EXTERNAL_ANCHORED
NOT_WIRED_TO_EXECUTOR_WRITE_PATH
NOT_OS_ENFORCED
NOT_FILESYSTEM_ENFORCED
LIVE_EXECUTOR_AUTHORITY_ON_HOLD
PHASE11A_NOT_STARTED
```

The no-mutation observation applies to the guard API and binding API only. It
does not mean raw filesystem writes are impossible. The B1-A
`CURRENTLY_BYPASSABLE` raw/direct baseline remains valid.

## Safe Default

```text
hold_current_state
```
