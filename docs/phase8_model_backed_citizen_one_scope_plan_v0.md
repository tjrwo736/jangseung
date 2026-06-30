# Aegis Phase 8 Model-backed Citizen One Scope Plan v0

## 1. Phase 8 purpose

Phase 8 defines the scope for the first model-backed component candidate in
Aegis.

The goal is not autonomous execution. The goal is to lock a controlled
proposal or dry-run behavior boundary before any implementation work begins.
Phase 8 is a planning gate for a future minimal model-backed proposal generator
or dry-run executor candidate.

This document does not implement a model-backed executor, provider, network
call, API key path, autonomous loop, or runtime behavior change.

The safe default remains:

```text
hold_current_state
```

## 2. Why Phase 8 is allowed after Phase 7

Phase 8 scope planning is allowed because Phase 7 Mutation Boundary /
Pre-Post Diff v1 passed on main as:

```text
PASS_PHASE7_MUTATION_BOUNDARY_MAIN_SMOKE
```

The accepted canonical baseline is:

```text
PHASE7_MUTATION_BOUNDARY_MAIN_SMOKE_EXTERNAL_PENDING
```

Phase 7 cleared the hard blocker for scope planning by establishing that future
executor behavior must be judged through independent pre/post repository
snapshots, `computed_mutation_delta`, and verify replay/binding validation.

This only allows planning. It does not allow implementation of model-backed
execution, provider integration, API calls, autonomous behavior, or actual file
mutation.

## 3. True external limitation

The true external unaided run is still not complete:

```text
NOT_YET_TRUE_EXTERNAL
```

Phase 8 scope planning may proceed, but Aegis must not claim public release
readiness, dogfood readiness, or true external readiness from this document.
Any future readiness claim remains blocked until the true external unaided run
is separately completed and evidenced.

## 4. Citizen One definition

Citizen One is the minimal candidate unit that can produce model output for a
single task.

Citizen One is not an autonomous agent. It is limited to a future
model-backed proposal generator or dry-run executor candidate. Its output may
be a proposal, explanation, plan, or dry-run description for one task.

Citizen One output is not a source of truth. It is not proof of execution
correctness, mutation absence, verification success, or policy compliance.

File mutation is forbidden by default. Any future mode that permits mutation
must be separately gated and must pass the Phase 7 mutation boundary.

## 5. Allowed model-backed behavior

Allowed future behavior candidates are limited to:

- explicitly opt-in model-backed proposal generation
- explicitly opt-in dry-run explanation for a single task
- model-generated plan text recorded as `reported_only`
- model-generated rationale or summary recorded as `reported_only`
- graceful hold or fail when provider configuration is absent or invalid
- evidence/reporting fields that clearly distinguish model output from
  judgment-basis evidence

The allowed behavior must preserve existing LOW, MEDIUM, and HIGH vocabulary.
It must preserve HIGH as `NEEDS_USER_GATE`. It must preserve `NOT_CHECKED` as
not PASS. It must preserve `REPLAY_CONSISTENT` as deterministic replay and
binding validation only.

## 6. Non-goals

Phase 8 v0 scope planning does not include:

- model-backed executor implementation
- provider implementation
- OpenAI, Claude, Gemini, or other model provider integration
- OpenAI API calls or any other model API calls
- API key loading
- `.env` loading
- network calls
- autonomous loops
- actual file mutation execution
- changes to `aeg run` behavior
- changes to `aeg verify` behavior
- classifier, law, evidence, state, source, or test changes
- GitHub API integration
- Slack, DRA, or Hermes integration
- release, publish, or deploy work
- telemetry
- public readiness claims
- dogfood readiness claims

## 7. Provider boundary

This Phase 8 scope plan is not a provider implementation.

OpenAI, Claude, Gemini, and other provider integrations are out of scope.
Future implementation of any provider, API key path, `.env` loading, model API
call, or network call requires a separate explicit gate.

Provider selection, provider fallback, retries, rate-limit handling, model
configuration, token accounting, and remote execution policy are not decided by
this document.

## 8. Secret/API key boundary

Phase 8 v0 must not record or require secrets, tokens, API keys, provider
credentials, `.env` values, private repository URLs, or private runtime logs.

Future implementation must satisfy at least these boundaries before any
provider or network behavior is allowed:

- no API key is required for default behavior
- missing API key produces graceful hold or fail
- no secret value is logged
- no secret value is committed
- no `.env` file is tracked
- no `.aeg/` runtime directory is tracked
- provider or network errors do not corrupt evidence

## 9. Mutation boundary dependency

Phase 7 pre/post snapshot capture, `computed_mutation_delta`, and verify replay
are prerequisites for any future model-backed behavior.

If a future model-backed mode exists, mutation attribution must still be judged
through the Phase 7 boundary:

1. capture trusted `pre_run_changed_files`
2. invoke the executor or dry-run candidate
3. capture trusted `post_run_changed_files`
4. compute `computed_mutation_delta`
5. bind and replay through verify

Model output is not mutation evidence. If a model says it did not modify files,
that self-report is not a judgment basis. The judgment basis for mutation
attribution must come from the independent Phase 7 snapshot boundary.

## 10. User gate dependency

HIGH risk must continue to produce `NEEDS_USER_GATE`.

Model-backed output must never bypass the user gate. A model-generated plan,
proposal, rationale, or self-assessment cannot downgrade HIGH risk, approve a
HIGH action, merge to main, deploy, release, publish, or authorize protected
mutation.

The safe default remains:

```text
hold_current_state
```

## 11. Model output trust boundary

Model output is `reported_only`.

Model self-report is not a judgment basis. Model-generated proposals and plans
may be recorded in evidence as context, but they are not correctness proofs for
verify, execution, mutation attribution, risk classification, or user-gate
decisions.

Required trust rules:

- model output can explain or propose
- model output cannot certify itself
- model output cannot replace deterministic verification
- model output cannot replace independent mutation snapshots
- model output cannot turn `NOT_CHECKED` into PASS
- model output cannot redefine `REPLAY_CONSISTENT`

## 12. Evidence/reporting candidates

Future evidence fields may include:

- `model_mode`: an explicit opt-in mode marker
- `model_provider_configured`: a boolean or redacted status, not a secret value
- `model_invocation_status`: `NOT_CONFIGURED`, `HELD`, `FAILED`, or `RECORDED`
- `model_output_reported_only`: the proposal or explanation text, if retained
- `model_output_hash`: an optional digest for binding without exposing content
- `model_error_reported_only`: redacted provider or network error context
- `citizen_one_task_scope`: the single task boundary for the model output
- `mutation_boundary_status`: the Phase 7 boundary result

These candidates are reporting surfaces only. They must not become judgment
basis fields unless a later scope plan explicitly defines and gates that change.

## 13. Tests / acceptance criteria for future implementation

Future implementation should be rejected unless it satisfies all of these
candidate acceptance criteria:

- model-backed mode is explicitly opt-in
- absence of an API key produces graceful hold or fail
- no secret logging
- no `.env` value logging
- no autonomous loop
- no file mutation by default
- LOW, MEDIUM, and HIGH vocabulary is preserved
- HIGH remains `NEEDS_USER_GATE`
- `NOT_CHECKED` never becomes PASS
- `REPLAY_CONSISTENT` remains deterministic replay and binding validation only
- Phase 7 mutation boundary remains active
- model output is recorded as `reported_only`
- model self-report is not a judgment basis
- provider and network errors do not corrupt evidence
- no main merge, release, publish, deploy, GitHub API, Slack, DRA, or Hermes
  behavior is introduced as part of Citizen One

## 14. Phase 8 go/no-go criteria

`GO_FOR_USER_REVIEW_GATE` requires:

- this scope plan is the only changed file
- no source, tests, README, architecture, or packaging files changed
- no model-backed executor implementation was added
- no provider implementation was added
- no API key, `.env` loading, or network call path was added
- no runtime behavior changed
- no `.aeg/` or `.env` file is tracked
- forbidden implementation and secret scans pass
- `git diff --check` passes
- unit tests pass

`NO_GO_SCOPE_FIX_REQUIRED` applies if README, `docs/architecture.md`,
`pyproject.toml`, source, tests, runtime behavior, or other out-of-scope files
change.

`BLOCKED` applies if provider/API/release/secret handling is added, `.aeg/` or
`.env` is tracked, main is pushed or merged directly, or an actual
model-backed executor/provider/autonomous loop is implemented.

## 15. Phase 9 handoff criteria

Phase 9 must not begin from this document alone.

A Phase 9 handoff requires:

- Phase 8 user review gate approval
- true external unaided limitation explicitly carried forward
- provider boundary still closed unless separately gated
- secret/API key boundary still closed unless separately gated
- mutation boundary dependency preserved
- user gate dependency preserved
- model output trust boundary preserved as `reported_only`
- future implementation acceptance criteria converted into executable tests or
  equivalent review gates before runtime behavior changes

Until those conditions are met, the safe default remains:

```text
hold_current_state
```
