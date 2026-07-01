# Aegis Phase 8-E Provider Adapter Contract Scope Plan v0

## 1. Phase 8-E purpose

Phase 8-E locks the contract scope for a future provider adapter before any
provider, API, network, environment, secret, or model-call implementation
begins.

The purpose is to define candidate request fields, response fields, error and
hold behavior, secret boundaries, network opt-in boundaries, trust boundaries,
evidence binding candidates, verify replay candidates, and handoff criteria for
a future provider adapter.

This is a planning gate only. It does not implement a provider adapter,
OpenAI integration, Claude integration, Gemini integration, API key loading,
`.env` loading, network calls, model-backed executor behavior, autonomous
loops, file mutation, command execution, or runtime behavior changes.

The current canonical baseline remains:

```text
PHASE8D_DETERMINISTIC_PROPOSAL_STUB_MAIN_SMOKE_EXTERNAL_PENDING
```

The current known prerequisite states remain:

```text
PASS_PHASE7_MUTATION_BOUNDARY_MAIN_SMOKE
PASS_PHASE8B_CITIZEN_ONE_CONTROL_PLANE_MAIN_SMOKE
PASS_PHASE8C_PROPOSAL_CONTRACT_MAIN_SMOKE
PASS_PHASE8D_DETERMINISTIC_PROPOSAL_STUB_MAIN_SMOKE
NOT_YET_TRUE_EXTERNAL
ON_OPT_IN
IMPLEMENTED_AND_BOUND
IMPLEMENTED_AND_BOUND
SCOPE_LOCKED
NOT_STARTED
```

The safe default remains:

```text
hold_current_state
```

## 2. Why provider adapter contract is needed before provider implementation

Provider implementation crosses several boundaries at once: remote model text,
network calls, API credentials, environment configuration, provider failures,
redaction, output retention, proposal binding, replay semantics, and user-gate
dependencies.

A provider adapter contract is needed before implementation so future code has
a narrow review target and cannot accidentally turn provider output into a
source of truth. The contract must make clear that provider output is
`reported_only`, provider self-report is not a judgment basis, provider
metadata is only a future binding candidate, and default offline/core behavior
must remain usable.

This document only permits planning and review. It does not authorize provider
implementation.

## 3. Provider adapter definition

A provider adapter is a future boundary candidate that may wrap a model or
provider call.

The provider adapter is not an executor. It does not execute commands, mutate
files, edit files, merge branches, release, publish, deploy, perform protected
actions, or operate an autonomous loop.

The provider adapter is not a source of truth. Provider adapter output is only
a candidate source of proposal material. It may be considered for future
proposal content only if separately implemented behind explicit opt-in and
preserved as `reported_only`.

The provider adapter cannot satisfy, bypass, downgrade, or replace any user
gate. It cannot replace law status, LOW/MEDIUM/HIGH risk classification,
Phase 7 mutation attribution, evidence binding, or deterministic verify replay.

## 4. Provider request contract candidates

Future implementation may consider these provider request contract candidates:

- `provider_request_id`
- `provider_mode`
- `provider_name`
- `provider_model`
- `provider_prompt_source`
- `provider_prompt_hash_candidate`
- `provider_request_redaction_status`
- `provider_network_opt_in`
- `provider_secret_source`
- `provider_secret_observed`

Candidate meanings:

- `provider_request_id`: stable identifier for a recorded provider request
  attempt or held request candidate.
- `provider_mode`: redacted provider mode such as disabled, stub, dry-run, or
  future opt-in provider mode.
- `provider_name`: redacted provider family label when safe to record.
- `provider_model`: redacted model label when safe to record and separately
  approved.
- `provider_prompt_source`: source category for prompt construction, not the
  raw prompt body.
- `provider_prompt_hash_candidate`: optional digest candidate for approved
  canonicalized prompt material without storing raw prompt text.
- `provider_request_redaction_status`: marker describing whether request
  metadata is redacted, raw storage is absent, or retention is blocked.
- `provider_network_opt_in`: explicit marker that a future network path was
  user opted-in before any call could be attempted.
- `provider_secret_source`: redacted source category only, not a secret value
  and not private deployment detail.
- `provider_secret_observed`: minimal secret-presence candidate only if a
  future gate proves it can be represented without leaking values, prefixes,
  lengths, key names tied to private deployments, or credentials.

Raw prompt storage is forbidden by this planning gate. Secret values, API keys,
tokens, credentials, `.env` values, provider request bodies, and private
runtime values must not be recorded.

These fields are candidates only. They are not implemented by this document.

## 5. Provider response contract candidates

Future implementation may consider these provider response contract candidates:

- `provider_response_present`
- `provider_response_status`
- `provider_response_source`
- `provider_response_reported_only`
- `provider_response_trust_boundary`
- `provider_response_hash_candidate`
- `provider_response_redaction_status`
- `provider_response_error_class`
- `provider_response_error_safe_summary`

Candidate meanings:

- `provider_response_present`: whether a provider response candidate exists,
  without implying correctness, safety, or approval.
- `provider_response_status`: redacted status such as not configured, held,
  failed, blocked, completed, or unavailable.
- `provider_response_source`: redacted provider source category when safe to
  record.
- `provider_response_reported_only`: explicit marker that provider output is
  non-authoritative reported-only material.
- `provider_response_trust_boundary`: marker preserving that provider output
  is outside judgment-basis state.
- `provider_response_hash_candidate`: optional digest candidate for approved
  redacted or canonicalized provider output without storing raw response text.
- `provider_response_redaction_status`: marker describing whether response
  metadata is redacted, raw storage is absent, or retention is blocked.
- `provider_response_error_class`: redacted error category, not a raw provider
  exception body.
- `provider_response_error_safe_summary`: secret-safe human summary with no
  credential, token, raw prompt, or raw response content.

Raw response storage is forbidden until a separate future gate explicitly
approves retention policy, redaction rules, verify behavior, and tests.

These fields are candidates only. They are not implemented by this document.

## 6. Provider error/hold contract candidates

Future provider behavior must preserve graceful hold or fail semantics.

If a provider is not configured, the future adapter candidate must gracefully
hold or fail without changing core runtime behavior. Missing API keys are not
core runtime failures. Network failures are not evidence failures and must not
pollute evidence, manifests, logs, stdout, stderr, or `.aeg/` runtime files.

Error messages must not include secrets, tokens, credentials, API key values,
`.env` values, raw prompts, raw responses, provider request bodies, provider
response bodies, or private runtime values.

Candidate error and hold statuses may include:

- `PROVIDER_NOT_CONFIGURED`
- `PROVIDER_DISABLED`
- `PROVIDER_NOT_OPTED_IN`
- `PROVIDER_SECRET_MISSING`
- `PROVIDER_NETWORK_BLOCKED`
- `PROVIDER_NETWORK_FAILED`
- `PROVIDER_RESPONSE_REDACTED`
- `PROVIDER_HELD`
- `PROVIDER_FAILED_SECRET_SAFE`

The safe default remains:

```text
hold_current_state
```

## 7. Provider output trust boundary

Provider output is `reported_only`.

Provider self-report is not a judgment basis. If a provider says a plan is
safe, that statement is not a judgment basis. If a provider says no mutation
occurred, that statement is not a judgment basis. If a provider says
verification passed, that statement is not a judgment basis.

Provider output cannot turn `NOT_CHECKED` into PASS. Provider output cannot
redefine `REPLAY_CONSISTENT`. Provider output cannot replace law status.
Provider output cannot replace LOW, MEDIUM, or HIGH risk classification.
Provider output cannot downgrade HIGH. HIGH remains `NEEDS_USER_GATE`.

Judgment basis remains with existing trusted mechanisms:

- classifier results for risk classification.
- law status for law evaluation.
- evidence binding for recorded run facts.
- Phase 7 pre/post snapshot and `computed_mutation_delta` for mutation
  attribution.
- deterministic verify replay and binding validation for verify results.

## 8. Secret/API key/.env boundary

API keys, `.env` values, tokens, credentials, and secret-like values must not
be recorded in evidence, manifests, logs, reports, stdout, stderr, tracked
files, or `.aeg/` runtime files.

This planning gate does not implement API key loading, environment loading, or
`.env` loading. `.env` loading requires a separate implementation gate before
code is added.

Future secret handling must define redaction rules for success and failure
paths before implementation. Provider SDK or network exceptions must not leak
secrets through error strings. Git-tracked `.env` files remain forbidden.
Tracked `.aeg/` runtime artifacts remain forbidden.

## 9. Network opt-in boundary

Network calls are not implemented by this document.

Any future provider network call must be explicit opt-in. No provider call may
occur by default, as a side effect of `aeg run`, as a side effect of `aeg
verify`, because a provider adapter exists, because an API key exists, because
`.env` exists, or because a deterministic stub path exists.

Offline/core mode must remain usable without provider access, API access,
network access, API keys, `.env` loading, provider SDKs, or model calls.

Provider opt-in must not authorize mutation by default. Provider-backed
proposal material remains separate from any future mutation permission.

## 10. Raw prompt/response storage boundary

Raw prompt storage is not approved by Phase 8-E.

Raw response storage is not approved by Phase 8-E.

Future implementation must not store raw prompts or raw provider/model
responses in evidence, manifests, logs, reports, stdout, stderr, `.aeg/`, or
tracked files without a separate gate. That gate must define retention policy,
redaction rules, prompt sensitivity, response sensitivity, secret handling,
failure behavior, verify behavior, and tests.

Until a separate gate exists, only redacted metadata candidates or approved
hash candidates may be considered. Hash candidates must not expose raw secrets,
raw prompts, raw responses, API keys, tokens, credentials, `.env` values,
provider request bodies, provider response bodies, or private runtime values.

## 11. Evidence/manifest binding candidates

Provider metadata may become a candidate for future evidence and manifest
binding after a separate implementation gate defines exact fields and tests.

Candidate binding surfaces may include:

- provider adapter contract version.
- provider request identifier.
- provider mode.
- redacted provider family or source category.
- redacted model category when safe and approved.
- provider network opt-in marker.
- provider request redaction status.
- provider response status.
- `provider_response_reported_only=true`.
- `provider_response_trust_boundary=reported_only`.
- provider response redaction status.
- provider response hash candidate for approved redacted or canonicalized
  content.
- redacted provider error class.
- provider error safe summary.
- proposal contract linkage when provider output becomes proposal material.

Provider metadata is only a future binding candidate. It is not source of truth
state and is not a judgment basis.

Raw prompts, raw responses, secrets, API keys, tokens, credentials, `.env`
values, provider request bodies, provider response bodies, and private runtime
values must not be recorded.

## 12. Verify replay candidates

Future verify behavior may consider provider-specific replay checks only after
a separate implementation gate defines exact metadata fields, hash behavior,
tamper behavior, and tests.

Candidate verify checks may include:

- required provider metadata fields are present when a provider response is
  recorded.
- provider response remains marked `reported_only`.
- provider trust boundary remains non-authoritative.
- provider metadata does not replace law status.
- provider metadata does not replace LOW/MEDIUM/HIGH risk classification.
- provider metadata does not satisfy or bypass a user gate.
- HIGH remains `NEEDS_USER_GATE`.
- `NOT_CHECKED` never becomes PASS because provider output exists.
- raw prompt and raw response content are absent unless a separate future gate
  approves storage.
- provider output hash candidate, if present, binds only approved redacted or
  canonicalized content.
- provider output tamper is detectable as a future verify candidate.
- Phase 7 mutation boundary remains active when mutation attribution is needed.
- offline/core mode remains usable without provider access.

Verify success remains:

```text
REPLAY_CONSISTENT
```

`REPLAY_CONSISTENT` means deterministic replay and binding validation only. It
is not external oracle proof, model proof, provider correctness proof, model
quality proof, or proof that provider output is safe.

This document does not change `aeg verify` behavior.

## 13. User gate dependency

HIGH remains `NEEDS_USER_GATE`.

The provider adapter cannot satisfy, bypass, replace, simulate, or downgrade
the user gate. Provider output cannot approve protected actions, authorize HIGH
behavior, merge to main, release, publish, deploy, mutate files, execute
commands, call networks, or convert `NEEDS_USER_GATE` into PASS.

If a future provider response recommends protected behavior, the user gate
remains required. The safe default remains:

```text
hold_current_state
```

## 14. Phase 7 mutation boundary dependency

Phase 7 Mutation Boundary / Pre-Post Diff v1 remains the mutation attribution
dependency for any future provider-backed behavior.

Mutation attribution must come from trusted Phase 7 pre/post snapshots and the
independently computed `computed_mutation_delta`. Provider output is not
mutation evidence.

If a provider says no files were modified, that statement is not a judgment
basis. If file mutation appears, `computed_mutation_delta` takes priority.
Future provider work must preserve:

1. trusted `pre_run_changed_files`
2. future provider proposal-material invocation only when explicitly opted in
3. trusted `post_run_changed_files`
4. independently computed `computed_mutation_delta`
5. verify replay and binding validation

Provider existence cannot hide, downgrade, or reinterpret computed mutation.

## 15. Deterministic stub dependency

The deterministic proposal stub path from Phase 8-D remains preserved.

Future provider adapter work must not remove, weaken, or replace the local
deterministic stub path. The deterministic stub remains the offline contract
exercise path for `proposal_present=true` without provider access, API access,
network access, environment loading, secret handling, or model calls.

Provider adapter work must preserve the proposal contract semantics established
by Phase 8-C and exercised by Phase 8-D: proposal output remains
`reported_only`, not execution, not source-of-truth evidence, not law or risk
authority, and not user approval.

## 16. Non-goals

Phase 8-E does not include:

- provider adapter implementation.
- provider implementation.
- OpenAI integration.
- Claude integration.
- Gemini integration.
- OpenAI API calls or any provider API calls.
- API key loading.
- `.env` loading.
- network calls.
- model-backed executor implementation.
- autonomous loop implementation.
- actual mutation execution.
- file-editing executor implementation.
- command execution.
- raw prompt storage.
- raw response storage.
- secret, token, credential, or API key recording.
- `.env` value recording.
- changes to `aeg run` behavior.
- changes to `aeg verify` behavior.
- classifier, law, evidence, state, source, or test changes.
- GitHub API integration.
- Slack, DRA, or Hermes integration.
- release, publish, or deploy work.
- telemetry.
- `.aeg/` tracking.
- `.env` tracking.
- direct main push.
- main merge.
- public, dogfood, release, or true external readiness claims.

## 17. Future implementation acceptance criteria

Future provider adapter implementation should be rejected unless it satisfies
all of these acceptance criteria:

- explicit opt-in only.
- default `aeg run` preserved.
- no provider call without explicit opt-in.
- no API key logging.
- no `.env` tracked.
- no raw prompt storage.
- no raw response storage.
- no autonomous loop.
- no file mutation.
- no command execution.
- provider output remains `reported_only`.
- provider output does not replace proposal, law, risk, or status.
- provider output does not bypass the user gate.
- Phase 7 mutation boundary remains active.
- deterministic stub path remains preserved.
- offline/core mode remains usable.
- `NOT_CHECKED` never becomes PASS.
- HIGH remains `NEEDS_USER_GATE`.
- missing provider configuration gracefully holds or fails.
- missing API key is not a core runtime failure.
- network failure is secret-safe and evidence-safe.
- provider errors do not include secrets.

## 18. Go/no-go criteria

GO for a future provider adapter implementation gate requires all of the
following:

- the implementation is explicitly scoped to provider adapter boundary work.
- network behavior is explicit opt-in only.
- default `aeg run` behavior remains unchanged.
- default `aeg verify` behavior remains unchanged except for separately
  reviewed deterministic replay checks for bound provider metadata.
- no provider call occurs without explicit opt-in.
- no API key, token, credential, or `.env` value can be logged or recorded.
- raw prompt and raw response storage remain absent unless a separate gate
  approves retention.
- provider output remains `reported_only`.
- provider output cannot replace law, risk, status, user-gate, or mutation
  judgment bases.
- Phase 7 mutation boundary tests remain active.
- deterministic stub path remains preserved.
- offline/core mode remains usable.

NO-GO applies if any future implementation includes default provider calls,
implicit network calls, API key logging, tracked `.env`, raw prompt/response
storage without a separate gate, provider output as source of truth, user-gate
bypass, law/risk/status replacement, Phase 7 mutation boundary weakening,
deterministic stub removal, autonomous loops, file mutation, command execution,
release, publish, deploy, direct main push, main merge, telemetry, or tracked
`.aeg/` artifacts.

## 19. Handoff criteria to provider adapter disabled/stub implementation

A future disabled or stub provider adapter implementation PR may begin only
after this scope is accepted and the handoff confirms:

- implementation starts with disabled or stub behavior only.
- implementation is explicit opt-in only.
- default `aeg run` behavior remains unchanged.
- default `aeg verify` behavior remains unchanged except for separately
  reviewed deterministic replay checks for bound metadata.
- no real provider, API, network, environment, secret, or model call behavior
  is introduced.
- request and response candidate fields are narrowed into exact schema fields
  before code is merged.
- redaction rules are testable before any provider metadata is recorded.
- evidence and manifest binding candidates are reviewed before runtime binding.
- provider output remains `reported_only`.
- provider output is proposal material only and not a judgment basis.
- raw prompt and raw response storage remain blocked.
- API key, token, credential, and `.env` value recording remain blocked.
- Phase 7 mutation boundary remains the mutation judgment basis.
- user gate behavior remains unchanged.
- deterministic stub path remains preserved.
- offline/core mode remains usable.
- safe default remains `hold_current_state`.
