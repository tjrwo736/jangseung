# Aegis Phase 8-B Citizen One Control Plane Scope Plan v0

## 1. Phase 8-B purpose

Phase 8-B locks the Citizen One control-plane boundary before any Citizen One
implementation begins.

The purpose is to define the explicit opt-in model, candidate CLI surface,
evidence recording candidates, provider-not-configured hold behavior, and
status vocabulary boundaries for a future Citizen One proposal or dry-run
mode.

This is a planning gate only. It does not implement Citizen One, a provider,
API key handling, `.env` loading, network calls, a model-backed executor,
autonomous loops, actual mutation execution, or runtime behavior changes.

The current canonical baseline remains:

```text
PHASE8A_PROVIDER_SECRET_NETWORK_SCOPE_PLAN_MAIN_SMOKE_EXTERNAL_PENDING
```

The current known prerequisite states remain:

```text
PASS_PHASE7_MUTATION_BOUNDARY_MAIN_SMOKE
PASS_PHASE8_SCOPE_PLAN_MAIN_SMOKE
PASS_PHASE8A_PROVIDER_SECRET_NETWORK_SCOPE_PLAN_MAIN_SMOKE
NOT_YET_TRUE_EXTERNAL
NOT_STARTED
SCOPE_LOCKED
```

The safe default remains:

```text
hold_current_state
```

## 2. Why a control plane is needed before implementation

Citizen One must not enter Aegis as an incidental runtime behavior change. A
model-backed proposal surface crosses multiple boundaries at once: CLI
activation, provider configuration, secret handling, network behavior, evidence
binding, status vocabulary, model-output trust, mutation attribution, and user
gate behavior.

The control plane is needed before implementation so future code has a narrow,
reviewable contract:

- Citizen One is not the default execution path.
- Citizen One is only allowed through explicit opt-in.
- missing provider configuration produces graceful hold or fail behavior.
- provider output is `reported_only`.
- model/provider self-report is not a judgment basis.
- no provider, API, `.env`, or network behavior exists until separately gated.
- file mutation is forbidden by default.
- Phase 7 mutation attribution remains authoritative.
- HIGH remains `NEEDS_USER_GATE`.

This document only permits future planning and review. It does not authorize
implementation.

## 3. Explicit opt-in model

Citizen One must be explicit opt-in only.

Citizen One must not automatically apply to the default `aeg run` path. Running
`aeg run` without a future Citizen One flag or separate Citizen One command
must preserve existing behavior.

Future implementation must expose opt-in through a visible, testable CLI
surface. The final CLI is deferred to the implementation PR, but the default
must remain off.

Candidate principles:

- no Citizen One behavior by default
- no network call by default
- no provider invocation merely because configuration exists
- no mutation permission implied by Citizen One opt-in
- no user-gate bypass implied by Citizen One opt-in
- no promotion of provider output into judgment-basis evidence

## 4. Proposed CLI surface candidates

Future implementation may consider one of these explicit CLI candidates:

```text
aeg run --citizen-one "<task>"
aeg citizen propose "<task>"
```

Candidate semantics:

- `aeg run --citizen-one "<task>"` would be an explicit opt-in extension of an
  existing command while preserving default `aeg run` behavior when the flag is
  absent.
- `aeg citizen propose "<task>"` would keep Citizen One behind a separate
  command surface and make proposal-only semantics easier to review.

This document does not choose the final command. The implementation PR must
choose and test the final CLI surface. In all cases, the default is off.

## 5. Provider-not-configured hold behavior

Provider-not-configured behavior must be graceful hold or fail.

If provider, API, environment, or network capability is absent, future Citizen
One behavior must not become a core runtime failure. The offline core loop must
continue to work without provider access, network access, API keys, or `.env`
loading.

Required behavior candidates:

- no API key state must not trigger secret discovery or secret printing.
- missing provider configuration is not a failure of `aeg run` default
  behavior.
- missing provider configuration may produce a Citizen One hold/fail status only
  when Citizen One was explicitly requested.
- no secret value, token, credential, `.env` value, key prefix, or private
  runtime value may be logged or committed.
- provider absence must not corrupt evidence or turn unchecked state into PASS.
- provider absence must not trigger autonomous retries, mutation, release,
  deploy, publish, main merge, telemetry, GitHub API, Slack, DRA, or Hermes
  behavior.

The safe default remains:

```text
hold_current_state
```

## 6. Citizen One evidence field candidates

Future implementation may consider these Citizen One evidence field candidates:

- `citizen_one_requested`
- `citizen_one_mode`
- `citizen_one_status`
- `citizen_one_provider_status`
- `citizen_one_output_present`
- `citizen_one_output_trust_boundary`
- `citizen_one_reported_only`
- `citizen_one_hold_reason`
- `provider_config_source`
- `provider_network_used`
- `provider_secret_observed`
- `model_output_hash_candidate`

Candidate meanings:

- `citizen_one_requested`: whether the user explicitly requested Citizen One.
- `citizen_one_mode`: candidate mode such as proposal or dry-run.
- `citizen_one_status`: Citizen One control-plane status, not law status.
- `citizen_one_provider_status`: redacted provider configuration/invocation
  state.
- `citizen_one_output_present`: whether provider/model output was present.
- `citizen_one_output_trust_boundary`: marker that output is `reported_only`.
- `citizen_one_reported_only`: explicit boolean or equivalent marker.
- `citizen_one_hold_reason`: redacted reason for hold/fail.
- `provider_config_source`: redacted source category only, if allowed by a
  future gate.
- `provider_network_used`: whether a provider network call was used after
  explicit opt-in.
- `provider_secret_observed`: secret-safe marker only, if separately gated.
- `model_output_hash_candidate`: optional digest candidate for binding without
  storing raw output.

These are candidates only. They are not implemented by this document.

Secret values and raw prompt/response storage remain blocked until a separate
gate explicitly allows and tests them.

## 7. Status vocabulary candidates

Future implementation may consider these Citizen One status vocabulary
candidates:

- `CITIZEN_ONE_NOT_REQUESTED`
- `CITIZEN_ONE_REQUESTED`
- `CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED`
- `CITIZEN_ONE_HELD_SECRET_BOUNDARY`
- `CITIZEN_ONE_PROPOSAL_RECORDED`
- `CITIZEN_ONE_REJECTED_BY_GATE`

Vocabulary boundaries:

- these statuses do not replace law status.
- these statuses do not redefine LOW, MEDIUM, or HIGH.
- HIGH remains `NEEDS_USER_GATE`.
- `NOT_CHECKED` is not PASS.
- `REPLAY_CONSISTENT` is deterministic replay and binding validation only; it
  is not external oracle proof.
- Citizen One status cannot satisfy user approval, prove mutation absence, or
  prove verification correctness.

## 8. Model output trust boundary

Model output is `reported_only`.

Model or provider self-report is not a judgment basis. Model output may be
recorded as proposal text, dry-run content, rationale, or explanatory context,
but it is not execution proof.

Required trust boundaries:

- model output cannot certify itself.
- model output cannot prove correctness.
- model output cannot prove verification success.
- model output cannot prove mutation absence.
- model output cannot prove policy compliance.
- model output cannot turn `NOT_CHECKED` into PASS.
- model output cannot redefine `REPLAY_CONSISTENT`.
- model output cannot downgrade HIGH risk.
- provider output cannot bypass, satisfy, or replace the user gate.

## 9. Interaction with Phase 7 mutation boundary

Phase 7 Mutation Boundary / Pre-Post Diff v1 remains the judgment basis for
mutation attribution.

If Citizen One exists in the future, mutation attribution must still be judged
through independent Phase 7 pre/post snapshots and `computed_mutation_delta`.
Model output is not mutation evidence. If a model says it did not modify files,
that statement is not a judgment basis.

Future Citizen One behavior must preserve:

1. trusted `pre_run_changed_files`
2. Citizen One proposal or dry-run candidate invocation
3. trusted `post_run_changed_files`
4. independently computed `computed_mutation_delta`
5. verify replay and binding validation

If file mutation appears, the Phase 7 boundary takes precedence over Citizen
One self-report.

## 10. Interaction with user gate

HIGH remains `NEEDS_USER_GATE`.

Citizen One output must not bypass, downgrade, satisfy, or replace the user
gate. Provider-generated text cannot approve protected actions, authorize HIGH
behavior, merge to main, release, publish, deploy, perform mutation, or convert
`NEEDS_USER_GATE` into PASS.

Citizen One may propose or explain after explicit opt-in. It cannot approve its
own proposal for execution.

The safe default remains:

```text
hold_current_state
```

## 11. Secret/network boundary dependency

Phase 8-B depends on the Phase 8-A provider, secret, and network boundary.

This document does not implement provider integration, API key loading, `.env`
loading, or network calls. Those remain `SCOPE_LOCKED` until a separate
implementation gate approves them.

Required dependency rules:

- no provider or network call without explicit opt-in.
- no network call merely because a provider adapter or API key exists.
- no API key logging.
- no `.env` tracked.
- no secret/token/API key recording.
- no raw prompt/response storage unless separately gated.
- no provider output promotion beyond `reported_only`.
- offline/core mode remains usable.

## 12. Non-goals

Phase 8-B does not include:

- Citizen One implementation
- provider implementation
- OpenAI integration
- Claude integration
- Gemini integration
- OpenAI API calls or any provider API calls
- API key loading
- `.env` loading
- network calls
- model-backed executor implementation
- autonomous loop implementation
- actual mutation execution
- changes to `aeg run` behavior
- changes to `aeg verify` behavior
- classifier, law, evidence, state, source, or test changes
- GitHub API integration
- Slack, DRA, or Hermes integration
- release, publish, or deploy work
- telemetry
- secret/token/API key recording
- `.env` value recording
- `.aeg/` tracking
- public, dogfood, release, or true external readiness claims

## 13. Future implementation acceptance criteria

Future implementation should be rejected unless it satisfies all of these
candidate acceptance criteria:

- explicit opt-in only
- default `aeg run` behavior preserved
- no provider configured produces graceful hold or fail
- no API key logging
- no `.env` tracked
- no network call without explicit opt-in
- no autonomous loop
- no file mutation by default
- Citizen One fields are evidence-bound
- model output is `reported_only`
- model/provider self-report is not a judgment basis
- LOW, MEDIUM, and HIGH vocabulary is preserved
- HIGH remains `NEEDS_USER_GATE`
- `NOT_CHECKED` never becomes PASS
- `REPLAY_CONSISTENT` remains deterministic replay and binding validation only
- Phase 7 mutation boundary remains active
- offline/core mode remains usable
- provider and network failures produce secret-safe graceful hold or fail
- no raw prompt/response storage unless separately gated
- no main merge, release, publish, deploy, GitHub API, Slack, DRA, Hermes, or
  telemetry behavior is introduced as part of Citizen One

## 14. Go/no-go criteria

`GO_FOR_USER_REVIEW_GATE` requires:

- this scope plan is the only changed file
- no source, tests, README, architecture, packaging, or runtime files changed
- no Citizen One implementation was added
- no provider implementation was added
- no OpenAI, Claude, Gemini, or other provider integration was added
- no API key loading was added
- no `.env` loading was added
- no network call path was added
- no model-backed executor was added
- no autonomous loop was added
- no actual mutation execution was added
- no `aeg run` or `aeg verify` behavior changed
- no classifier, law, evidence, state, source, or test behavior changed
- no GitHub API, Slack, DRA, Hermes, release, publish, deploy, or telemetry
  behavior was added
- no secret/token/API key values were recorded
- no `.env` or `.aeg/` files are tracked
- forbidden implementation and secret scans pass
- `git diff --check` passes
- unit tests pass

`NO_GO_SCOPE_FIX_REQUIRED` applies if README, `docs/architecture.md`,
`pyproject.toml`, source, tests, runtime behavior, or other out-of-scope files
change.

`BLOCKED` applies if provider/API/env/network/model-backed executor
implementation is added, secret/release scope is introduced, `.aeg/` or `.env`
is tracked, main is pushed or merged directly, or public/dogfood/release
readiness is claimed.

## 15. Handoff criteria to Citizen One implementation

Citizen One implementation must not begin from this document alone.

A future Citizen One implementation handoff requires:

- Phase 8-B user review gate approval
- explicit opt-in CLI surface chosen and tested
- default `aeg run` behavior preservation tested
- provider-not-configured graceful hold/fail behavior tested
- secret-safe evidence and logging checks defined
- no API key logging and no `.env` tracking checks defined
- network behavior still blocked unless separately gated
- Citizen One evidence fields converted into executable checks or an equivalent
  review gate
- Citizen One status vocabulary converted into executable checks or an
  equivalent review gate
- provider/model output trust boundary preserved as `reported_only`
- Phase 7 mutation boundary dependency preserved
- HIGH user gate dependency preserved
- LOW, MEDIUM, HIGH, `NOT_CHECKED`, and `REPLAY_CONSISTENT` semantics preserved
- true external unaided run limitation explicitly carried forward
- no public, dogfood, release, or true external readiness claim

Until these conditions are met, the safe default remains:

```text
hold_current_state
```
