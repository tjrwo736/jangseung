# B2-3 Executor-like Write Ingress Harness Through Router v0

## 1. Scope

B2-3 adds a fixture-only executor-like write ingress harness. The harness
models an executor-like write intent, converts it into the existing B2-1
pre-live router request, calls the B2-1 router API, and observes the routed
denial/no-mutation result for protected `.aeg/` targets.

This work is test-only / fixture-only support. It does not connect production
CLI/runtime behavior, production adapters, live executor code, provider/model
execution, network calls, command execution, or broad mutation capability.

## 2. Fixture-only ingress design

The fixture ingress record captures:

- source: `fixture-only executor-like ingress`.
- submitted path.
- intended operation.
- payload digest and metadata, without retaining raw payload in the record.
- `live_executor_request = false`.
- `production_runtime_ingress = false`.
- `live_executor_authority_status = LIVE_EXECUTOR_AUTHORITY_ON_HOLD`.
- `runtime_write_path_status = NOT_WIRED_TO_EXECUTOR_WRITE_PATH`.
- `phase11a_status = PHASE11A_NOT_STARTED` through the routed result.

The implementation lives in
`src/evidence/b2_executor_like_ingress_harness.py` as fixture support and is
covered by `tests/test_b2_executor_like_write_ingress_harness.py`.

## 3. Harness routing flow

The harness flow is:

1. Build a fixture-only executor-like ingress request.
2. Convert that ingress request into a B2-1 `PreLiveExecutorWriteRequest`.
3. Call `route_pre_live_executor_write_request`.
4. Reuse the B1-B guard to classify protected `.aeg/` targets.
5. Reuse the B1-C evidence binding and deny-only mediator compatible path.
6. Observe a routed denial/no-mutation result.

The direct `.aeg/` fixture and traversal fixture both route through the B2-1
router. The traversal fixture resolves under `.aeg/` before denial.

## 4. Boundary preservation

B2-3 does not alter `src/cli/main.py`, `src/agents/noop.py`,
`src/provider_adapter.py`, or production state recording paths.

Current authority and phase state remain:

- B2 state: open, not fully routed into runtime.
- Runtime write path: `NOT_WIRED_TO_EXECUTOR_WRITE_PATH`.
- Live executor authority: `LIVE_EXECUTOR_AUTHORITY_ON_HOLD`.
- Phase 11-A: `PHASE11A_NOT_STARTED`.
- B3: not started.
- Safe default: `hold_current_state`.

B2-4 evidence/verify replay and B2-5 status note work remain after B2-3.

## 5. B1/B2 preservation

B2-3 preserves:

- B1-A known-gap baseline.
- B1-B deny-only guard reuse.
- B1-C evidence binding compatibility.
- B1-D verify-only replay compatibility.
- B2-1 pre-live router behavior.
- B2-2 integration boundary accuracy.

The passing B2-3 tests measure fixture ingress through the B2-1 router only.
They are not a production runtime wiring claim and not a live authority claim.

## 6. Negative guarantees

B2-3 adds no production runtime connection.

B2-3 adds no production adapter.

B2-3 invokes no live executor.

B2-3 performs no provider/model/network runtime call.

B2-3 adds no command runner.

B2-3 grants no raw or broad file mutation capability.

B2-3 performs no actual filesystem mutation for the protected target.

B2-3 starts no Phase 11-A work.

B2-3 starts no B3 work.

B2-3 tracks no `.aeg`, `.env`, ledger, or runtime artifact files.

## 7. Next steps

B2 remains open after B2-3. The next scoped steps are B2-4 evidence/verify
replay and B2-5 status note work. Until those are reviewed, the safe default
remains `hold_current_state`.
