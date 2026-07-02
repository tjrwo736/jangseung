# Aegis Phase 10-E E1 Write Bypass Known Gap Baseline v0

## Scope

This note records the first actual Phase 10-E E1 write bypass test harness
baseline. The harness uses tempdir repo-like fixtures only. It does not write
to the repository's real `.aeg` directory, does not create `.env`, and does not
track runtime ledger artifacts.

The implemented test outcomes use only this baseline vocabulary:

```text
CURRENTLY_BYPASSABLE
EXPECTED_RED
KNOWN_GAP_BASELINE
```

These outcomes mean the current system can still perform the attempted write
because no mediator or write mediation mechanism has been implemented. They
are not completion evidence, not enforcement evidence, and not live executor
authority evidence.

## Fixtures Covered

- `WBYP-001`: direct `.aeg` write in a tempdir repo-like fixture.
- `WBYP-002`: traversal path resolving into tempdir `.aeg`.
- `WBYP-003`: symlink alias resolving into tempdir `.aeg` when symlinks are
  available on the test host.
- `WBYP-004`: outside-repo sibling path write.
- `WBYP-004`: outside-repo absolute path write.
- `WBYP-022`: tempdir `.aeg` evidence overwrite.
- `WBYP-022`: tempdir `.aeg` manifest overwrite.
- `WBYP-022`: tempdir `.aeg` ledger append.

The existing WBYP registry remains scaffold metadata. This E1 harness connects
to registry IDs and titles from `src.evidence.write_bypass_harness`, but does
not change registry entries into execution proof.

## Safe Default

```text
hold_current_state
```
