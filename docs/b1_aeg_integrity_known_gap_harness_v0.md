# Aegis B1-A `.aeg/` Integrity Known-Gap Harness v0

## Scope

This note records the B1-A current-state known-gap harness. The harness uses
tempdir repo-like fixtures only. It does not write to the repository's real
`.aeg` directory, does not create `.env`, and does not track runtime ledger
artifacts.

This is a current-state baseline only. It adds no denial mechanism, no
authority grant, no runtime integration, and no Phase 11-A transition.

## Baseline Vocabulary

The harness labels successful fixture mutation with this vocabulary:

```text
B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE
CURRENTLY_BYPASSABLE
EXPECTED_RED
KNOWN_GAP_BASELINE
NOT_HARDENED
NOT_EXECUTOR_ISOLATED
NOT_FILESYSTEM_ENFORCED
LIVE_EXECUTOR_AUTHORITY_ON_HOLD
PHASE11A_NOT_STARTED
```

These labels mean the current fixture write or tamper path is reproducible.
They are not denial evidence and not enforcement evidence.

## Fixture Coverage

- direct tempdir `.aeg/` write.
- traversal path resolving into tempdir `.aeg/`.
- symlink alias resolving into tempdir `.aeg/` when available.
- tempdir `.aeg/ledger.jsonl` append and overwrite.
- tempdir `.aeg/manifest` overwrite.
- tempdir evidence packet rewrite.
- tempdir verify basis rewrite.
- known-gap labels preserved without enforcement claims.

## Safe Default

```text
hold_current_state
```
