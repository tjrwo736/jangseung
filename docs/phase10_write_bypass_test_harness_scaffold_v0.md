# Aegis Phase 10 Write Bypass Test Harness Scaffold v0

## 1. Scope

This document records the Phase 10 write bypass test harness scaffold v0.

This is metadata/schema/verify vocabulary only. It does not implement actual
bypass tests, actual fixtures, actual write attempts, mediator enforcement,
broker/wrapper/tool execution, external enforcement, OS/sandbox/IPC controls,
network/API/provider calls, `.aeg` permission hardening, or live executor
authority.

The safe default remains:

```text
hold_current_state
```

Live executor authority remains:

```text
ON_HOLD
```

## 2. Scaffold Additions

The scaffold adds a deterministic WBYP registry and evidence/manifest binding
fields for future harness reference:

- `WBYP-001` through `WBYP-025` are represented in
  `write_bypass_harness_registry_ids`.
- each registry entry is future-only metadata.
- per-entry execution status is `NOT_CHECKED`.
- per-entry scaffold/enforcement status is `SCAFFOLD_ONLY_NOT_ENFORCED`.
- actual test, fixture, and write-attempt flags are false.
- executor self-report is not proof.
- `reported_only` is not a judgment basis.
- registry and metadata hashes are deterministic.

The scaffold deliberately does not create files, directories, symlinks,
runtime artifacts, fixture payloads, write targets, or test runners.

## 3. Verify Vocabulary

Schema and verify must reject any current scaffold claim that promotes this
metadata into proof or enforcement:

- `PASS`, `SAFE`, `CLEAN`, `CLEAN_CORE`, `ENFORCED`, and
  `EXTERNALLY_ENFORCED` are overclaims for current harness scaffold status.
- `NOT_CHECKED` is not `PASS`.
- `SCAFFOLD_ONLY_NOT_ENFORCED` is not safe, pass, or enforced.
- actual bypass tests present is false.
- actual fixtures present is false.
- actual write attempts present is false.
- mediator enforcement present is false.
- external enforcement present is false.
- executor self-report proof allowed is false.
- `reported_only` judgment basis allowed is false.

## 4. Cross References

This scaffold is bounded by:

- `docs/phase10_write_bypass_test_plan_v0.md`
- `docs/phase10_write_bypass_test_harness_scope_v0.md`
- `docs/phase10_mediator_interface_contract_v0.md`
- `docs/phase10_write_mediation_verify_criteria_v0.md`

The WBYP plan and harness scope define future behavior. This scaffold only
records the current registry and validation vocabulary needed by that future
harness.

## 5. Review Checklist

This scaffold is ready for user review only if:

- WBYP-001 through WBYP-025 are complete in the registry.
- all WBYP entries remain future-only metadata.
- no actual bypass tests are implemented.
- no actual fixtures are created.
- no actual write attempts are added.
- no mediator, broker, wrapper, tool, or enforcement implementation is added.
- no external enforcement is added.
- no `.aeg` permission hardening, OS separation, sandbox, IPC, network/API, or
  provider/model boundary is added.
- live executor authority remains `ON_HOLD`.
- `NOT_CHECKED` is not promoted to `PASS`.
- self-report and `reported_only` are not proof or judgment basis.

Expected review status when checks pass:

```text
PASS_READY_FOR_USER_REVIEW_GATE
```

Final safe default:

```text
hold_current_state
```
