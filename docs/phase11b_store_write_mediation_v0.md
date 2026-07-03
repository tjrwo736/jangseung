# Phase 11-B-0 store write mediation v0

Phase 11-B-0-b wires the actual `src/state/store.py` disk-write sinks to
record and enforce a narrow trusted-context mediated path for protected `.aeg`
writes. Phase 11-B-0-c reclassifies that line honestly: it is an in-process,
tamper-evident, overclaim-resistant sink guard under a structured-executor
assumption. It is not a security boundary against arbitrary in-process Python
code execution.

## In-process boundary limitation

The trusted-context sink guard runs in the same Python process and memory space
as `store.py`. A context variable, runtime-owned capability object, or private
marker in that same process can be useful as a structured runtime provenance
check, but it is not a security boundary against arbitrary code running with the
same interpreter authority.

Required invariant:

- `IN_PROCESS_TRUSTED_CONTEXT != SECURITY_BOUNDARY_AGAINST_ARBITRARY_CODE`
- `CAPABILITY_NOT_GRANTED_BY_POLICY != CAPABILITY_PHYSICALLY_IMPOSSIBLE`

## Arbitrary Python execution breaks trusted context secrecy

If an executor can run arbitrary Python in the same process, import modules,
perform introspection, call internal functions directly, or inspect process
memory, it can bypass or steal in-process context/capability material. Phase
11-B-0-c therefore rejects any claim that the trusted-context sink guard makes
arbitrary in-process Python execution safe.

This PR does not add a stronger secret token, call-stack inference, closure
secrecy claim, private marker claim, or ContextVar secrecy claim as a security
boundary.

## Trusted-context guard meaning under structured executor assumption

11-B-0-b now means:

- sink-level trusted-context guard under a structured-executor assumption
- tamper-evident and overclaim-resistant boundary
- accidental or declared-bypass path hardening
- trusted runtime `save_run` and ledger append preservation

11-B-0-b does not mean:

- tamper-proof
- arbitrary in-process code prevention
- physical impossibility proof
- OS/process isolation
- live executor ready
- executor `.aeg` writes fully blocked against all possible same-process code

## Tamper-evident vs tamper-proof distinction

This line is tamper-evident and overclaim-resistant, not tamper-proof. Evidence
records whether guarded sinks were exercised, whether trusted runtime writes
were preserved, and whether forbidden claims were rejected. It does not prove
that same-process arbitrary code cannot tamper with runtime state.

Required invariant:

- `TAMPER_EVIDENT != TAMPER_PROOF`
- `STRUCTURED_EXECUTOR_ASSUMPTION != ARBITRARY_CODE_EXECUTION_SAFE`

## Why 11-B-1 must restrict executor capability

Actual prevention requires the next strategy gate:

- 11-B-1 = Structured Executor Capability Restriction Gate
- executor output = data, not code
- executor cannot import Python modules
- executor cannot eval/exec
- executor cannot inspect memory
- executor cannot call `store.py` sinks directly
- executor cannot obtain trusted context/capability
- executor cannot use raw shell
- executor cannot use general `write_file`
- executor can only request mediated structured actions

The trusted-context guard is meaningful only if the executor lacks the ability
to steal or synthesize trusted context/capability material in the first place.

## Process/OS isolation as separate constitutional design gate

True tamper-proof isolation would require a process, OS, sandbox, container, or
IPC boundary. That is not implemented in PR #81 and must not be implemented in
this PR.

Such isolation may conflict with the portable single-entry and folder-local
constitution. It requires a separate strategy/user gate before design or
implementation.

Current status:

- `process_isolation_status=NOT_IMPLEMENTED`
- `os_sandbox_status=NOT_IMPLEMENTED`
- draft release = `HOLD`
- merge = `HOLD`
- live executor authority = `LIVE_EXECUTOR_AUTHORITY_ON_HOLD`

## Explicit non-claims

PR #81 must not claim:

- trusted context is a security boundary against arbitrary in-process Python
  code execution
- `.aeg` writes are structurally prevented against arbitrary same-process code
- raw bypass is physically impossible
- the guard is tamper-proof
- live executor is ready
- write authority is safe
- process/OS/sandbox/container isolation is implemented

Evidence and verify reject the following overclaim labels when they appear in
store-write mediation evidence:

- `TRUSTED_CONTEXT_SECURITY_BOUNDARY`
- `EXECUTOR_AEG_WRITE_FULLY_BLOCKED`
- `RAW_BYPASS_IMPOSSIBLE`
- `AEG_TAMPER_PROOF`

## Evidence Fields

The evidence packet and manifest bind a `STORE_WRITE_MEDIATION_FIELDS` group,
including:

- `store_write_mediation_enabled`
- `store_write_mediation_scope`
- `store_write_boundary`
- `store_write_boundary_strength=IN_PROCESS_TAMPER_EVIDENT_ONLY`
- `trusted_context_security_boundary=false`
- `requires_structured_executor=true`
- `arbitrary_in_process_code_breaks_boundary=true`
- `process_isolation_status=NOT_IMPLEMENTED`
- `os_sandbox_status=NOT_IMPLEMENTED`
- `executor_code_execution_model=STRUCTURED_ACTIONS_REQUIRED`
- `tamper_proof_claimed=false`
- `physical_prevention_claimed=false`
- `raw_bypass_impossible=false`
- `arbitrary_in_process_code_safe=false`
- `live_executor_ready=false`
- `write_authority_safe=false`
- `guarded_sinks`
- `write_json_sink_guarded`
- `ledger_append_sink_guarded`
- `trusted_context_required`
- `trusted_context_basis`
- `call_stack_inference_used_as_judgment_basis=false`
- `missing_context_result`
- `omitted_declaration_result`
- `executor_self_report_trusted_result`
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

- trusted-context guarded claims without both sink events
- `trusted_context_required=true` with `missing_context_result` other than
  `BLOCKED`
- `trusted_context_security_boundary=true` while process isolation is
  `NOT_IMPLEMENTED`
- `tamper_proof_claimed=true`
- `physical_prevention_claimed=true`
- `raw_bypass_impossible=true`
- `arbitrary_in_process_code_safe=true`
- `live_executor_ready=true`
- `write_authority_safe=true`
- forbidden overclaim labels listed above
- `call_stack_inference_used_as_judgment_basis=true`
- `blocked_write_created_files_count > 0` while claiming `BLOCKED`
- `executor_direct_sink_write_result=BLOCKED` when the target file exists
- `executor_direct_ledger_append_result=BLOCKED` when a forged entry appended
- `SINK_LEVEL_GUARDED` claims without both `_write_json` and
  `_append_ledger_unmediated` guarded sink events
- executor self-report trusted provenance
- omitted declaration treated as trusted provenance
- missing context treated as trusted provenance
- missing store write mediation binding
- trusted runtime write failure recorded as success
- trusted runtime ledger append failure recorded as success
- `rollback_used` / `fallback_to_unwired` mismatch
- live executor authority promotion
- Phase 11-B live executor start claims

## Safe default

The safe default remains `hold_current_state`.

Allowed honest state:

- `IN_PROCESS_TAMPER_EVIDENT_ONLY`
- `STRUCTURED_EXECUTOR_REQUIRED`
- `PROCESS_ISOLATION_NOT_IMPLEMENTED`
- `LIVE_EXECUTOR_AUTHORITY_ON_HOLD`
- `Phase 11-B live executor = NOT_STARTED`
- draft release = `NOT_PERFORMED`
- main merge = `NOT_PERFORMED`

Raw shell, outside-repo write, network/provider, general filesystem authority,
process isolation, OS enforcement, sandbox/container enforcement, and live
executor implementation remain out of scope and unchanged.
