# Aegis Philosophy Lineage v0

This is an internal design lineage record. It is not external positioning,
marketing copy, or a claim that future philosophy candidates are implemented.

## Implemented Code-Backed Principles

### 1. NOT_CHECKED != PASS

- Aegis principle: Unchecked evidence is not a pass condition.
- Philosophy lineage: Popperian falsification / 반증주의. A claim is not
  accepted merely because it has not been falsified.
- Implemented behavior: `NOT_CHECKED` is a first-class status and `PASS` is
  rejected in evidence and replay validation.
- Code / module location: `src/contracts.py`, `src/law/gates.py`,
  `src/evidence/schema.py`, `src/evidence/verify.py`.
- Observed behavior or test evidence: `tests/test_classify_law.py` covers
  medium and missing-source paths as `NOT_CHECKED`; `tests/test_cli_runtime.py`
  covers rejection of `NOT_CHECKED` promotion to `CLEAN_CORE` or `PASS`.
- Status: IMPLEMENTED_CODE_BACKED

### 2. reported_only is not judgment basis

- Aegis principle: A self-report may be recorded, but it cannot decide safety.
- Philosophy lineage: Evidence discipline / hearsay exclusion. A statement
  that something happened or did not happen is not the same as bounded proof.
- Implemented behavior: `reported_only` metadata is allowed as context for
  Citizen One, proposals, provider responses, executor mutation reports, and
  action reports, while schema and replay reject it as a judgment basis.
- Code / module location: `src/contracts.py`, `src/evidence/schema.py`,
  `src/evidence/mutation_boundary.py`, `src/evidence/verify.py`,
  `src/evidence/action_boundary.py`.
- Observed behavior or test evidence: `tests/test_cli_runtime.py` covers
  reported-only binding rejection, proposal reported-only preservation,
  executor-reported mutation replay rejection, and executor-reported action
  rejection as judgment basis.
- Status: IMPLEMENTED_CODE_BACKED

### 3. hold_current_state

- Aegis principle: When uncertainty remains, preserve the current state.
- Philosophy lineage: Precautionary principle / 예방원칙. Ambiguous or
  insufficiently checked situations default to non-action.
- Implemented behavior: `SAFE_DEFAULT` is `hold_current_state`; high-risk
  tasks require a user gate, medium/unchecked paths remain `NOT_CHECKED`, and
  disabled provider runtime records hold metadata instead of executing.
- Code / module location: `src/contracts.py`, `src/law/gates.py`,
  `src/provider_adapter.py`, `src/citizen_one.py`.
- Observed behavior or test evidence: `tests/test_classify_law.py` covers
  high-risk gating and medium `NOT_CHECKED`; `tests/test_cli_runtime.py`
  covers Citizen One provider-not-configured hold and provider guard metadata.
- Status: IMPLEMENTED_CODE_BACKED

### 4. evidence exists != evidence bound

- Aegis principle: Evidence presence is not the same as manifest/run/tree
  binding.
- Philosophy lineage: Chain of custody / 증거 보관 연쇄. Evidence must be
  linked to its run, manifest, repository state, and hashes before it can be
  replayed as bounded evidence.
- Implemented behavior: Evidence is bound to a run manifest with deterministic
  hashes for changed files, mutation boundary metadata, provider/proposal
  metadata, and action scaffold metadata; replay rejects missing or tampered
  bindings.
- Code / module location: `src/evidence/binding.py`,
  `src/evidence/schema.py`, `src/evidence/verify.py`, `src/state/store.py`.
- Observed behavior or test evidence: `tests/test_cli_runtime.py` covers
  manifest hash mismatch, missing manifest, run/path mismatches, bound hash
  mismatches, and action scaffold manifest tamper rejection.
- Status: IMPLEMENTED_CODE_BACKED

### 5. executor is not source of truth

- Aegis principle: The executor may report, but independent replay decides.
- Philosophy lineage: Separation of powers / 권한 분립. The actor that performs
  or reports work is separated from the component that validates evidence.
- Implemented behavior: Mutation judgment is computed from pre/post snapshots,
  not executor-reported mutation; action reports are scaffolded as
  `reported_only` and cannot become judgment basis.
- Code / module location: `src/evidence/mutation_boundary.py`,
  `src/evidence/schema.py`, `src/evidence/verify.py`,
  `src/evidence/action_boundary.py`, `src/agents/noop.py`.
- Observed behavior or test evidence: `tests/test_cli_runtime.py` covers
  recomputation of mutation delta from snapshots, ignored executor mutation
  self-report, and rejection of executor-reported actions as judgment basis.
- Status: IMPLEMENTED_CODE_BACKED

### 6. deterministic STOP > LLM

- Aegis principle: Deterministic stop conditions outrank model or proposal
  output.
- Philosophy lineage: Rule precedence over opinion. A deterministic safety
  gate is not overridden by generated text or provider self-report.
- Implemented behavior: HIGH risk remains `NEEDS_USER_GATE`; deterministic
  proposal stubs and disabled provider metadata are recorded as reported-only
  context and cannot satisfy, downgrade, or bypass law status.
- Code / module location: `src/law/gates.py`, `src/citizen_one.py`,
  `src/provider_adapter.py`, `src/evidence/schema.py`.
- Observed behavior or test evidence: `tests/test_cli_runtime.py` covers high
  risk remaining user-gated with Citizen One and deterministic proposal stubs,
  plus provider-disabled guard behavior with no provider/model call.
- Status: IMPLEMENTED_CODE_BACKED

### 7. verify = replay, not oracle

- Aegis principle: Verification is deterministic replay plus binding
  validation, not an external oracle.
- Philosophy lineage: Independent verification humility. Verify checks the
  recorded contract and bindings; it does not claim omniscience.
- Implemented behavior: `aeg verify` loads latest evidence, validates schema
  and binding, replays classification/law/mutation/action scaffold checks, and
  prints `independent_oracle: false`.
- Code / module location: `src/evidence/verify.py`, `src/evidence/schema.py`,
  `src/evidence/binding.py`, `src/cli/main.py`.
- Observed behavior or test evidence: `tests/test_cli_runtime.py` covers
  `REPLAY_CONSISTENT`, `REPLAY_FAILED`, manifest tamper failures, deterministic
  law replay, and action scaffold replay without provider/model/network/shell
  execution.
- Status: IMPLEMENTED_CODE_BACKED

## Future Philosophy Candidates

### 정반합 / 변증법

- Candidate: Phase 10 Citizens Few / Multi-citizen.
- Implementation note: No multi-citizen synthesis or dialectical resolution
  behavior exists in current code.
- Status: FUTURE_NOT_IMPLEMENTED

### 한론의 면도날

- Candidate: After Phase 9 action risk classification.
- Implementation note: No implemented rule currently uses this as a named
  action-risk or evidence-risk principle.
- Status: FUTURE_NOT_IMPLEMENTED

### 오컴의 면도날

- Candidate: Future evidence conflict resolution.
- Implementation note: Current verify replay validates deterministic bindings;
  it does not implement a simplicity-based conflict resolver.
- Status: FUTURE_NOT_IMPLEMENTED

### 체스터턴의 울타리

- Candidate: Protected path / law / classifier governance.
- Implementation note: Current protected path and law gates exist, but this
  named governance philosophy has not been implemented as a separate rule.
- Status: FUTURE_NOT_IMPLEMENTED
