# Aegis Phase 8-A Provider Secret Network Boundary Scope Plan v0

## 1. Phase 8-A purpose

Phase 8-A locks the trust boundary for provider integration, API keys, `.env`
loading, network calls, provider output, and secret-safe evidence before any
Phase 8 Model-backed Citizen One implementation begins.

This is a planning gate only. It does not implement a provider, provider
adapter, API key path, `.env` loader, network call, model-backed executor,
autonomous loop, actual mutation execution, or runtime behavior change.

The current baseline remains:

```text
PHASE8_SCOPE_PLAN_MAIN_SMOKE_EXTERNAL_PENDING
```

The true external unaided run is still:

```text
NOT_YET_TRUE_EXTERNAL
```

Aegis must not claim public readiness, dogfood readiness, release readiness, or
true external readiness from this document.

The safe default remains:

```text
hold_current_state
```

## 2. Why this gate exists before provider implementation

Provider integration must not enter Phase 8 implementation as an incidental
detail. Provider behavior crosses a separate trust boundary because it may
involve secrets, environment configuration, network calls, remote failures,
model-generated text, and logs that could otherwise pollute evidence.

This gate exists to keep Phase 8 implementation from silently changing the
security and evidence model. Before any provider code exists, Aegis must define
what is allowed, what is forbidden, which output is only `reported_only`, and
which existing judgment bases remain authoritative.

This document only permits future planning and review. It does not authorize
provider implementation.

## 3. Provider boundary

Provider implementation is not in scope for Phase 8-A.

OpenAI, Claude, Gemini, and other provider integrations are not implemented by
this work. Provider selection, SDK use, adapter shape, model configuration,
fallback behavior, retries, rate-limit handling, token accounting, streaming,
tool calling, and remote execution policy are not decided by this document.

Any future provider adapter must be handled in a separate PR after a separate
implementation gate. That PR must prove it preserves the boundaries in this
document before runtime behavior changes are accepted.

Provider result is `reported_only`. It is not a judgment basis and is not a
source of truth.

## 4. Secret/API key boundary

API keys, tokens, credentials, and secret-like values must not be recorded in
evidence, manifests, logs, reports, stdout, stderr, or `.aeg/` runtime files.

Secret presence can itself be sensitive. Future implementation must minimize
how it represents provider configuration state and avoid exposing specific
secret values, secret prefixes, secret lengths, key names tied to private
deployment details, or unnecessary presence details.

`.env` actual values must not be recorded. Git-tracked `.env` files remain
forbidden. `.aeg/` runtime files must not become a secret sink and must not be
tracked.

Missing or invalid credentials must not corrupt evidence. The safe behavior is
graceful hold or fail with secret-safe reporting.

## 5. `.env` loading boundary

This Phase 8-A work does not implement `.env` loading.

If future implementation needs `.env` loading, it requires a separate gate
before code is added. That gate must define:

- allowed environment variable names
- redaction rules for every configured value
- whether secret presence may be reported at all
- missing-key behavior
- invalid-key behavior
- precedence between process environment and `.env`
- rules that keep `.env` files untracked
- tests proving secret-safe behavior

Until that gate exists, `.env` loading remains out of scope.

## 6. Network call boundary

This Phase 8-A work does not implement network calls.

Future network calls must be explicit opt-in. No provider or network request may
occur by default, as a side effect of `aeg run`, as a side effect of `aeg
verify`, or because an API key happens to exist.

Provider and network failures must not pollute evidence. Timeouts, DNS errors,
rate limits, authentication failures, quota failures, provider outages, malformed
responses, and offline execution must produce graceful hold or fail behavior
with secret-safe logs.

Offline/core mode must remain usable. Aegis core runtime, classifier, evidence,
state, and verify behavior must continue to work without provider access,
network access, API keys, or `.env` loading.

## 7. Provider output trust boundary

Provider output is not a source of truth.

Model or provider self-report is not a judgment basis. Provider output may only
be treated as proposal text, dry-run content, rationale, or explanatory context.
It cannot prove correctness, verification success, mutation absence, policy
compliance, user approval, or readiness.

Provider output cannot turn `NOT_CHECKED` into PASS. Provider output cannot
redefine `REPLAY_CONSISTENT`. Provider output cannot downgrade HIGH risk or
bypass a user gate.

Verify correctness proof must come from deterministic verification and binding
validation, not from provider text.

## 8. Evidence and logging redaction rules

Evidence may only retain limited provider metadata candidates, and only after a
future implementation gate defines exact fields and tests. Candidate metadata
surfaces may include:

- provider mode opt-in status
- provider invocation status such as `NOT_CONFIGURED`, `HELD`, `FAILED`, or
  `RECORDED`
- redacted provider family label when safe
- redacted failure category
- optional output digest for binding without exposing raw content
- `reported_only` marker for provider-produced proposal or dry-run content
- mutation boundary status from the Phase 7 snapshot boundary

Raw prompts and raw responses are not approved for storage by this document.
Whether raw prompt/response retention is ever allowed requires a separate gate.

Secret-like values must be redacted from evidence, manifests, logs, reports,
stdout, stderr, and failure output. Redaction must apply to success and failure
paths. Failure logs must remain secret-safe even when provider SDKs or network
libraries return detailed errors.

## 9. Failure behavior / graceful hold

Provider, API key, `.env`, and network failures must preserve the safe default:

```text
hold_current_state
```

No provider failure may trigger autonomous retry loops, file mutation, release,
deploy, publish, main merge, GitHub API behavior, Slack behavior, DRA behavior,
Hermes behavior, telemetry, or evidence promotion.

When provider configuration is absent, invalid, blocked, offline, or not opted
in, future behavior must gracefully hold or fail without changing core runtime
behavior and without turning unchecked provider state into PASS.

## 10. Opt-in requirement

Provider mode must be explicit opt-in in any future implementation.

No network call may occur merely because a provider adapter exists, an API key
exists, a `.env` file exists, a user runs an existing command, or a model-backed
scope plan exists. Future opt-in design must be visible, testable, and
documented before runtime behavior changes are accepted.

Opt-in must not authorize mutation by default. Provider-backed proposal or
dry-run behavior remains separate from any future mutation permission.

## 11. Interaction with Phase 7 mutation boundary

Phase 7 Mutation Boundary / Pre-Post Diff v1 remains the mutation attribution
dependency for future model-backed behavior.

Model or provider output does not affect mutation attribution. If a provider
says it did not modify files, that statement is not a judgment basis.

The only mutation judgment-basis candidate is `computed_mutation_delta`, and
only when it is computed from trusted pre/post snapshots that satisfy the Phase
7 snapshot trust boundary.

Future provider-backed behavior must preserve:

1. trusted `pre_run_changed_files`
2. executor or dry-run candidate invocation
3. trusted `post_run_changed_files`
4. independently computed `computed_mutation_delta`
5. verify replay and binding validation

## 12. Interaction with user gate

HIGH remains `NEEDS_USER_GATE`.

Provider or model output must not bypass, downgrade, satisfy, or replace the
user gate. Provider-generated text cannot approve protected actions, authorize
HIGH behavior, merge to main, release, publish, deploy, perform mutation, or
convert `NEEDS_USER_GATE` into PASS.

The safe default remains:

```text
hold_current_state
```

## 13. Non-goals

Phase 8-A does not include:

- provider implementation
- OpenAI integration
- Claude integration
- Gemini integration
- model provider SDK integration
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

## 14. Future implementation acceptance criteria

Future implementation should be rejected unless it satisfies all of these
candidate acceptance criteria:

- provider mode explicit opt-in
- no API key produces graceful hold or fail
- no secret logging
- no `.env` value logging
- no `.env` tracked
- no `.aeg/` tracked
- no network call without explicit opt-in
- no autonomous loop
- no mutation by default
- provider output is `reported_only`
- provider output is not a source of truth
- model/provider self-report is not a judgment basis
- LOW, MEDIUM, and HIGH vocabulary is preserved
- HIGH remains `NEEDS_USER_GATE`
- `NOT_CHECKED` never becomes PASS
- `REPLAY_CONSISTENT` remains deterministic replay and binding validation only
- Phase 7 mutation boundary remains active
- offline/core mode remains usable
- provider and network failures produce secret-safe graceful hold or fail
- evidence, manifests, logs, reports, stdout, stderr, and `.aeg/` runtime files
  remain secret-safe
- raw prompt/response storage remains blocked unless separately gated

## 15. Go/no-go criteria

`GO_FOR_USER_REVIEW_GATE` requires:

- this scope plan is the only changed file
- no source, tests, README, architecture, packaging, or runtime files changed
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

## 16. Phase 8 implementation handoff criteria

Phase 8 implementation must not begin from this document alone.

A future Phase 8 implementation handoff requires:

- Phase 8-A user review gate approval
- provider boundary still closed unless separately gated
- API key boundary still closed unless separately gated
- `.env` loading boundary still closed unless separately gated
- network call boundary still closed unless separately gated
- provider output trust boundary preserved as `reported_only`
- evidence and logging redaction rules converted into executable checks or an
  equivalent review gate before provider behavior is added
- Phase 7 mutation boundary dependency preserved
- user gate dependency preserved
- true external unaided run limitation explicitly carried forward
- no public, dogfood, release, or true external readiness claim
- future implementation acceptance criteria converted into tests or equivalent
  review gates before runtime behavior changes

Until these conditions are met, the safe default remains:

```text
hold_current_state
```
