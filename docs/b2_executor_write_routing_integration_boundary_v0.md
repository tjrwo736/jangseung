# B2-2 Executor Write Routing Integration Boundary v0

## 1. B2-2 scope

B2-2 is an investigation and boundary definition step only. It documents where
the B2-1 router could be connected in a later harness and what must remain out
of scope until that later work is reviewed.

In scope:

- survey current repo entry, adapter, command, executor-like, mediator, guard,
  evidence, ledger, and write-related structure.
- identify candidate integration seams for a later scoped B2-3 harness.
- document current B2 status and negative guarantees.
- add read-only/import-level/contract-level boundary tests.

Out of scope:

- actual wiring into a runtime executor write path.
- production adapter or production ingress changes.
- live executor code.
- runtime write authority grant.
- provider/model/network runtime calls, shell, command-runner, or broad file mutation
  capability.
- Phase 11-A start.
- B3 raw capability or worktree-scope closure.
- any B2 completion or live-readiness claim.

## 2. Current B2 state

The B2-1 router exists at `src/evidence/b2_executor_write_router.py`. It
accepts `PreLiveExecutorWriteRequest`, routes protected `.aeg/` targets through
the B1-B guard, the B1-C evidence binding, and the deny-only mediator model,
then returns a denial/no-mutation record.

Current authority and phase state remain:

- B2 state: open, not fully wired.
- Runtime write path: `NOT_WIRED_TO_EXECUTOR_WRITE_PATH`.
- Live executor authority: `LIVE_EXECUTOR_AUTHORITY_ON_HOLD`.
- Phase 11-A: `PHASE11A_NOT_STARTED`.
- B3: not started.
- Safe default: `hold_current_state`.

B2-2 does not change those labels. The B2-1 router remains a pre-live routing
component, not the runtime executor write path.

## 3. Repo structure survey

Checked files and directories:

- `src/cli/main.py`
- `src/agents/noop.py`
- `src/provider_adapter.py`
- `src/citizen_one.py`
- `src/state/store.py`
- `src/state/git.py`
- `src/evidence/packet.py`
- `src/evidence/b2_executor_write_router.py`
- `src/evidence/b1_aeg_integrity_guard.py`
- `src/evidence/b1_aeg_integrity_evidence_binding.py`
- `src/evidence/b1_aeg_integrity_verify.py`
- `src/evidence/deny_only_mediator.py`
- `src/evidence/mediated_aeg_write_path.py`
- `src/evidence/mediated_repo_boundary_write_path.py`
- `src/evidence/mediated_write_evidence_binding.py`
- `src/evidence/mediated_write_boundary.py`
- `docs/live_executor_entry_gate_v0.md`
- `docs/b2_executor_write_routing_through_mediator_guard_path_v0.md`
- `tests/test_b2_executor_write_routing.py`
- B1 integrity tests and Phase 10 mediated write tests.

Write-related candidates found:

- `src/state/store.py::ensure_initialized` creates the folder-local `.aeg/`
  state directory, config, runs directory, and ledger file.
- `src/state/store.py::save_run` writes `run.json`, `manifest.json`,
  `evidence.json`, and appends a ledger entry under `.aeg/`.
- `src/state/store.py::append_ledger` appends to `.aeg/ledger.jsonl`.
- Tests create temporary repo fixtures and perform known-gap or fixture writes
  under test-controlled temporary directories.
- `src/evidence/mediated_aeg_write_path.py` and
  `src/evidence/mediated_repo_boundary_write_path.py` model denied mediated
  write requests without mutating targets.

Executor-like ingress candidates found:

- `src/cli/main.py::_cmd_run` is the current CLI orchestration entry. It calls
  `execute_contract`, builds evidence, and saves run artifacts.
- `src/agents/noop.py::execute_contract` is the current Day-1 executor-like
  implementation. It returns a no-op contract and reports no file mutation,
  provider calls, network calls, or actions.
- `src/citizen_one.py` supplies opt-in proposal evidence, but it remains
  reported-only and is not a mutation ingress.
- `src/provider_adapter.py` records disabled provider metadata and does not call
  provider SDKs, environment secrets, or network paths.
- `src/evidence/b2_executor_write_router.py` is the B2-1 pre-live structured
  write routing component and is a direct candidate for a future harness seam.

Candidates explicitly not found:

- no live executor code.
- no production executor write adapter.
- no production command runner.
- no general-purpose file mutation tool surface.
- no provider/model runtime-call path.
- no network-call path.
- no runtime write path that already invokes the B2-1 router.
- no external enforcement implementation.
- no executor isolation implementation.

Assumptions not made:

- `save_run` and `build_evidence_packet` are not treated as executor write
  ingress. They are evidence/reporting state paths.
- The deny-only mediator model is not treated as runtime mediation.
- A passing B2-1 router test is not treated as runtime wiring evidence.
- Existing temporary test fixture writes are not treated as production executor
  writes.
- Disabled provider metadata is not treated as provider execution.
- The presence of write-related vocabulary is not treated as capability grant.

## 4. Integration seam candidates

| Candidate seam | Path | Existing or future fixture-only | Why suitable for B2-3 harness | Must not be inferred yet |
| --- | --- | --- | --- | --- |
| Pre-live router API | `src/evidence/b2_executor_write_router.py::route_pre_live_executor_write_request` | Existing | Already accepts a structured executor-like request and returns a guard/mediator-compatible routed denial record. | It is not invoked by the runtime executor path. |
| Request builder | `src/evidence/b2_executor_write_router.py::build_pre_live_executor_write_request` | Existing | Converts target, operation, payload digest, and metadata into the B2-1 request shape without storing raw payload. | It is not a production ingress and does not authorize writes. |
| CLI run boundary after executor result | `src/cli/main.py::_cmd_run` around `execute_contract(...)` | Existing code, future harness only | It is the current orchestration point where an executor result is available before evidence packet construction. A B2-3 harness could model a scoped executor-like write intent here without changing production behavior. | Current `_cmd_run` has no executor write intent and no router call. |
| No-op executor result model | `src/agents/noop.py::execute_contract` | Existing code, future harness only | It is the current executor-like component and records no actions or mutation. A future harness can define how a write-intent fixture differs from this no-op result. | The current no-op executor is not a write ingress. |
| Mediated request shape | `src/evidence/deny_only_mediator.py::WriteMediationRequest` | Existing downstream model | B2-1 already translates protected requests into this model, so B2-4 can bind routed decision/evidence/verify replay around it. | The mediator model is downstream of routing and is not runtime enforcement. |
| Phase 10 denied write helpers | `src/evidence/mediated_aeg_write_path.py`, `src/evidence/mediated_repo_boundary_write_path.py` | Existing evidence helpers | They show canonical path-resolution patterns and denied no-mutation result shapes useful for comparison. | They are not executor ingress and should not be wired as production adapters by B2-2. |
| Scoped B2-3 harness seam | proposed `tests/...` fixture only | Future fixture-only | A B2-3 test harness can build a synthetic executor-like write intent, route it through B2-1, and assert evidence fields before runtime wiring is attempted. | It must not grant runtime authority, execute a command, call a provider, use the network, or mutate a target file. |

## 5. `save_run` / evidence packet / ledger flow versus executor write routing

`build_evidence_packet` constructs a deterministic evidence dictionary from the
classification, law result, executor result, mutation boundary, and metadata
components. It does not itself write files.

`save_run` is a state recorder. It writes `.aeg/runs/<run_id>/run.json`,
`.aeg/runs/<run_id>/manifest.json`, `.aeg/runs/<run_id>/evidence.json`, and a
ledger entry. This is the Aegis reporting path, not the executor write path
that B2 must route.

B2 executor write routing is narrower: it concerns an executor-like requested
mutation target before file mutation. B2-1 currently models that request and
routes protected `.aeg/` targets through B1 guard/evidence and the deny-only
mediator model, but no current runtime write path feeds such requests into the
router.

## 6. Negative guarantees

B2-2 adds no production wiring.

B2-2 does not wire a router invocation into the live/runtime executor path.

B2-2 adds no production adapter.

B2-2 adds no command runner or broad raw write capability.

B2-2 adds no OS or filesystem hardening.

B2-2 adds no executor isolation.

B2-2 makes no B2 completion claim.

B2-2 makes no B3 claim.

B2-2 starts no Phase 11-A work.

B2-2 adds no provider/model/network runtime calls.

B2-2 tracks no `.aeg`, `.env`, ledger, or runtime artifact files.

## 7. Next-step recommendation

B2-3 should add a scoped executor-like ingress harness only after this B2-2
boundary is reviewed. That harness should remain pre-live and should use the
B2-1 request model to measure how an executor-like write intent would route.

B2-4 should bind routed decision, evidence, and verify replay after B2-3 has
an ingress harness.

B2-5 status note should happen only after B2-3 and B2-4 evidence exists.

B3 should not start before B2 has wired-but-prelive evidence.

Until then, the safe default remains `hold_current_state`.
