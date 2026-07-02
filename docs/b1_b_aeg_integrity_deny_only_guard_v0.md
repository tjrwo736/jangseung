# Aegis B1-B `.aeg/` Integrity Deny-only Guard Component v0

## Scope

This note records the B1-B deny-only guard component for submitted `.aeg/`
paths. The component canonicalizes a submitted path, resolves traversal and
available symlink aliases, and returns a decision record.

This is a component-level guard only. It is not runtime write-path wiring, not
executor isolation, and not OS or filesystem hardening. Raw/direct filesystem
paths remain governed by the B1-A known-gap baseline.

## Decision Behavior

- Direct `.aeg/` targets return `DENIED_BY_B1_AEG_INTEGRITY_GUARD`.
- Traversal targets resolving into `.aeg/` return `DENIED_BY_B1_AEG_INTEGRITY_GUARD`.
- Symlink aliases resolving into `.aeg/` return `DENIED_BY_B1_AEG_INTEGRITY_GUARD`
  when the symlink fixture is available to the platform.
- `.aeg/ledger.jsonl` is classified as `B1_AEG_LEDGER_TARGET_DENIED`.
- `.aeg/manifest` is classified as `B1_AEG_MANIFEST_TARGET_DENIED`.
- `.aeg/runs/.../evidence_packet.json` is classified as `B1_AEG_EVIDENCE_TARGET_DENIED`.
- `.aeg/runs/.../verify_basis.json` is classified as `B1_AEG_VERIFY_BASIS_TARGET_DENIED`.
- Non-`.aeg/` targets are classified as `B1_AEG_NOT_PROTECTED_TARGET` with
  `B1_AEG_OUT_OF_SCOPE`; this does not create a capability grant.

Every decision includes the submitted path, resolved path, protected root,
target class, denial reason, and wiring status.

## Non-enforcement Boundary

The guard decision always records:

```text
NOT_WIRED_TO_EXECUTOR_WRITE_PATH
NOT_OS_ENFORCED
NOT_FILESYSTEM_ENFORCED
LIVE_EXECUTOR_AUTHORITY_ON_HOLD
PHASE11A_NOT_STARTED
```

The guard API performs no filesystem mutation. That no-mutation result applies
to the guard API only; it does not change the B1-A baseline for raw/direct write
paths.

## Safe Default

```text
hold_current_state
```
