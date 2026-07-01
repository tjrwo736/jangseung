# Aegis Phase 8-G Provider Runtime Opt-in Boundary Scope Plan v0

## 1. Phase 8-G purpose

Phase 8-G locks the provider runtime opt-in boundary before any real provider,
API, environment, network, or model-call implementation begins.

Provider runtime support introduces a new trust boundary. Provider selection,
API key and environment handling, network use, provider request construction,
provider response handling, and provider error reporting are not equivalent to
the existing offline Aegis core runtime. They can expose secrets, raw prompt
material, raw request bodies, raw response bodies, SDK error bodies, network
state, model self-reports, and external service behavior.

This scope plan exists so future implementation must preserve the safe default
and the existing evidence, law, risk, user gate, mutation, and verify semantics
before any provider call can be added.

This is a planning gate only. It does not implement provider selection, provider
adapters, API key loading, environment loading, network calls, actual model
calls, prompt builders, response parsers, model-backed executors, autonomous
loops, file mutation executors, command execution, telemetry, release, publish,
deploy, GitHub API behavior, Slack behavior, DRA behavior, Hermes behavior, or
runtime behavior changes.

The current canonical baseline remains:

```text
PHASE8F_PROMPT_RESPONSE_REDACTION_METADATA_MAIN_SMOKE_EXTERNAL_PENDING
```

The current known prerequisite states remain:

```text
PASS_PHASE7_MUTATION_BOUNDARY_MAIN_SMOKE
PASS_PHASE8B_CITIZEN_ONE_CONTROL_PLANE_MAIN_SMOKE
PASS_PHASE8C_PROPOSAL_CONTRACT_MAIN_SMOKE
PASS_PHASE8D_DETERMINISTIC_PROPOSAL_STUB_MAIN_SMOKE
PASS_PHASE8E_PROVIDER_ADAPTER_DISABLED_CONTRACT_MAIN_SMOKE
PASS_PHASE8F_PROVIDER_PROMPT_RESPONSE_REDACTION_BOUNDARY_SCOPE_PLAN_MAIN_SMOKE
PASS_PHASE8F_PROMPT_RESPONSE_REDACTION_METADATA_MAIN_SMOKE
NOT_YET_TRUE_EXTERNAL
ON_OPT_IN
IMPLEMENTED_AND_BOUND
IMPLEMENTED_AND_BOUND
IMPLEMENTED_AND_BOUND
IMPLEMENTED_AND_BOUND
NOT_ALLOWED
SCOPE_LOCKED
NOT_STARTED
```

The safe default remains:

```text
hold_current_state
```

## 2. Provider runtime state machine candidates

Future implementation may consider the following provider runtime states:

- `provider_disabled`: provider runtime is unavailable or explicitly disabled.
- `provider_not_configured`: provider runtime was requested, but no safe
  provider configuration is available.
- `provider_config_present_but_network_not_opted_in`: provider configuration is
  present, but network use has not been explicitly opted in.
- `provider_runtime_opt_in_requested`: a future caller explicitly requested
  provider runtime behavior, subject to all guards.
- `provider_request_allowed_future`: all future guards required to construct
  and send a provider request are satisfied.
- `provider_request_blocked`: a request is blocked because a provider, key,
  network opt-in, redaction, or trust-boundary precondition is missing.
- `provider_error_safe_hold`: provider runtime reached a safe hold because a
  provider or network error can be represented only as a secret-safe class and
  summary.
- `provider_response_recorded_as_reported_only`: provider output exists only as
  reported-only proposal material after safe response metadata processing.

Missing provider selection, missing provider configuration, missing key status,
or missing network opt-in must be a graceful hold or graceful fail. It must not
become a core runtime failure.

The safe default remains `hold_current_state`.

## 3. Provider selection boundary

Provider selection is future implementation and must be explicit opt-in only.
Default `aeg run` must not select or use a provider.

Provider name and provider model may become future metadata candidates, but a
provider selection value is not a law result, not a risk result, not user
approval, not a mutation boundary result, not verify proof, and not evidence of
correctness.

Provider selection cannot replace or downgrade:

- law status.
- risk classification.
- user gate requirements.
- Phase 7 mutation attribution.
- Phase 8-F redaction metadata.
- deterministic proposal stub behavior.
- provider disabled behavior.

Candidate fields:

- `provider_selection_requested`
- `provider_selected`
- `provider_name`
- `provider_model`
- `provider_selection_source`
- `provider_selection_status`

Expected principles:

- provider selection requires explicit opt-in.
- default `aeg run` does not use a provider.
- selected provider metadata is safe metadata only.
- selected provider metadata is never a judgment basis.

## 4. API key and environment loading boundary

API key loading and environment loading are future implementation. This document
does not authorize either behavior.

API key values, token values, credential values, and `.env` values must not be
stored in any location. Key prefix, suffix, length, fingerprint, digest, hash,
or other derived identifier must not be stored. Secret presence must be handled
only through minimal safe boolean or status metadata when future implementation
has a separate approved gate.

Tracked `.env` files remain forbidden. Missing key state must be a graceful hold
or graceful fail and must not become a core runtime failure.

Candidate fields:

- `provider_secret_required`
- `provider_secret_source`
- `provider_secret_observed`
- `provider_secret_value_recorded`
- `provider_secret_redaction_status`
- `provider_env_loading_requested`
- `provider_env_loading_status`

Expected principles:

- `provider_secret_value_recorded=false`
- `provider_secret_observed` does not mean a secret value is recorded.
- `provider_secret_redaction_status=secret_value_not_recorded` or an equivalent
  secret-safe status.
- raw secret storage is forbidden.
- secret value, prefix, suffix, length, fingerprint, digest, and hash logging
  are forbidden.

## 5. Network opt-in boundary

Network calls are future implementation and require explicit opt-in even after a
provider runtime implementation exists.

Default mode, offline mode, and core mode must not use the network. If network
opt-in is absent, a provider request must be blocked or held. Network-used state
may be recorded only as safe metadata.

Candidate fields:

- `provider_network_opt_in_requested`
- `provider_network_opt_in_allowed`
- `provider_network_used`
- `provider_network_status`
- `provider_network_block_reason`

Expected principles:

- default `provider_network_used=false`
- network calls without explicit opt-in are forbidden.
- network-used metadata is not external oracle proof.
- network-used metadata is not verify proof.
- network-used metadata is not a judgment basis.

## 6. Provider request boundary

Provider request construction is future implementation. This document does not
authorize prompt construction, request body construction, SDK calls, API calls,
or network calls.

Raw prompt bodies and raw provider request bodies must not be stored. Future
request metadata must use the Phase 8-F prompt redaction metadata contract.
Only request safe metadata may be considered as a future evidence or manifest
candidate.

Candidate fields:

- `provider_request_requested`
- `provider_request_status`
- `provider_request_id`
- `provider_request_metadata_hash`
- `provider_request_redaction_status`
- `provider_request_raw_stored`

Expected principles:

- `provider_request_raw_stored=false`
- raw request storage is forbidden.
- raw prompt storage is forbidden.
- request metadata is safe metadata only.
- request metadata is not a judgment basis.

## 7. Provider response and error boundary

Provider response handling and provider error handling are future
implementation. This document does not authorize response parsing, error parsing,
SDK error capture, or raw response retention.

Raw provider responses must not be stored. Raw SDK or API error bodies must not
be stored. A provider response is only a proposal material candidate. Provider
and model self-report is not a judgment basis. Provider errors may be recorded
only as safe class and safe summary metadata.

Candidate fields:

- `provider_response_present`
- `provider_response_status`
- `provider_response_reported_only`
- `provider_response_trust_boundary`
- `provider_response_metadata_hash`
- `provider_response_redaction_status`
- `provider_response_raw_stored`
- `provider_error_class`
- `provider_error_safe_summary`

Expected principles:

- `provider_response_reported_only=true`
- `provider_response_trust_boundary=reported_only`
- `provider_response_raw_stored=false`
- `provider_error_safe_summary` is secret-safe.
- raw response storage is forbidden.
- raw SDK or API error body storage is forbidden.

## 8. Forbidden storage locations

Raw prompt, request, response, error, and secret material must not be stored in:

- evidence.
- manifest.
- logs.
- stdout.
- stderr.
- `.aeg/` runtime files.
- tracked files.
- reports.
- field reports.

Forbidden material includes:

- raw prompt text.
- raw provider request body.
- raw provider response body.
- raw SDK or API error body.
- API key value.
- token value.
- credential value.
- `.env` value.
- secret prefix.
- secret suffix.
- secret length.
- secret fingerprint.
- secret digest or hash.

## 9. Evidence and manifest binding candidates

Future implementation may consider binding only safe provider runtime metadata:

- provider selection metadata.
- secret redaction metadata.
- network opt-in metadata.
- request safe metadata.
- response safe metadata.
- error safe metadata.
- metadata hashes over approved safe metadata.

Raw prompt, request, response, error, and secret material are not binding
targets. A digest of unsafe raw material does not make that material safe.

Metadata tamper may become a future verify candidate, but only for approved safe
metadata. Metadata binding must not imply provider correctness, model
correctness, network trust, external oracle proof, user approval, mutation
absence, or legal/risk judgment.

## 10. Verify replay candidates

Future verify replay behavior must preserve existing replay semantics:

- verify success remains `REPLAY_CONSISTENT`.
- verify failure remains `REPLAY_FAILED`.
- verify output must not use `status: PASS`.
- `REPLAY_CONSISTENT` is not provider proof.
- `REPLAY_CONSISTENT` is not model proof.
- `REPLAY_CONSISTENT` is not external oracle proof.
- provider or model output is not a verify judgment basis.

Provider metadata may be replayed only as safe metadata if a separate
implementation gate approves it. Provider output must not determine verify
success or failure.

## 11. User gate dependency

`HIGH` remains `NEEDS_USER_GATE`.

Provider output must not bypass, satisfy, downgrade, or remove a user gate.
Provider self-report must not convert `NEEDS_USER_GATE` into approval. Provider
selection, network opt-in, and response metadata are not user approval.

The safe default remains `hold_current_state`.

## 12. Phase 7 mutation boundary dependency

Mutation attribution remains based on the Phase 7 pre/post snapshot and
`computed_mutation_delta`.

Provider or model claims about whether a mutation happened are not a judgment
basis. If a provider or model says there were no changes, that statement cannot
override the Phase 7 mutation boundary.

## 13. Phase 8-F redaction dependency

Prompt and response redaction metadata must use the Phase 8-F contract.

Raw prompt and raw response storage remain forbidden. Future request and
response metadata must bind to redaction status without retaining raw prompt,
request, response, error, or secret material.

If redaction cannot prove safe metadata, future provider runtime behavior must
hold instead of recording raw material.

## 14. Offline and core mode dependency

Default `aeg run` must continue to work without provider configuration, network
access, API keys, or environment loading.

`aeg run --citizen-one` provider-not-configured hold behavior must be preserved.
The deterministic proposal stub path must be preserved. The provider disabled
path must be preserved.

Offline and core behavior must remain usable even if future provider runtime
metadata exists.

## 15. Non-goals

The following are explicit non-goals for Phase 8-G:

- provider implementation.
- OpenAI integration.
- Claude integration.
- Gemini integration.
- API key loading.
- environment loading.
- `.env` loading.
- network calls.
- actual model calls.
- prompt builder.
- response parser.
- model-backed executor.
- autonomous loop.
- file mutation executor.
- command execution.
- raw prompt storage.
- raw request storage.
- raw response storage.
- raw error storage.
- raw secret storage.
- GitHub API implementation.
- Slack integration.
- DRA integration.
- Hermes integration.
- telemetry.
- release.
- publish.
- deploy.

## 16. Future implementation acceptance criteria

Future provider runtime implementation must satisfy all of the following before
it can be accepted:

- explicit opt-in only.
- default `aeg run` preserved.
- offline and core mode usable.
- missing provider opt-in is graceful hold or graceful fail.
- missing key status is graceful hold or graceful fail.
- missing network opt-in is graceful hold or graceful fail.
- no raw prompt storage.
- no raw request storage.
- no raw response storage.
- no raw error storage.
- no secret value, prefix, suffix, length, fingerprint, digest, or hash logging.
- no network call without explicit opt-in.
- provider output remains reported-only.
- provider self-report is not a judgment basis.
- provider output does not replace law status.
- provider output does not replace risk status.
- provider output does not replace user gate status.
- provider output does not replace mutation boundary status.
- Phase 7 mutation boundary remains active.
- Phase 8-F redaction metadata remains active.
- deterministic proposal stub path preserved.
- provider disabled path preserved.
- `HIGH` remains `NEEDS_USER_GATE`.
- `NOT_CHECKED` never becomes `PASS`.
- verify success remains `REPLAY_CONSISTENT`.
- verify output has no `status: PASS`.

## 17. Handoff criteria

The next implementation gate may begin only after:

- this scope plan is merged and main-smoked.
- implementation scope is limited to provider runtime opt-in guards and safe
  metadata unless separately approved.
- actual provider calls remain blocked behind a separate implementation gate.
- any real network call requires explicit opt-in and tests.
- raw prompt and response storage remain disallowed.
- raw request, error, and secret storage remain disallowed.
- offline and core mode behavior remains preserved.

The handoff state after Phase 8-G should be:

```text
PROVIDER_RUNTIME_OPT_IN_BOUNDARY_SCOPE_PLAN_READY
safe_default=hold_current_state
provider/API/env/network=still_scope_locked_until_implementation_gate
actual_model_call=NOT_STARTED
raw_prompt/request/response/error/secret_storage=NOT_ALLOWED
```
