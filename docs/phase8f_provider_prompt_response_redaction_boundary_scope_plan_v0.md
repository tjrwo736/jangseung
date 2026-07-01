# Aegis Phase 8-F Provider Prompt Response Redaction Boundary Scope Plan v0

## 1. Phase 8-F purpose

Phase 8-F locks the planning boundary for future provider prompt construction,
provider response handling, redaction, hash candidates, and storage rules before
any provider, API, network, environment, secret, or model-call implementation
begins.

This is a planning gate only. It does not implement a prompt builder, response
parser, provider adapter, OpenAI integration, Claude integration, Gemini
integration, API key loading, `.env` loading, network calls, model-backed
executor behavior, autonomous loops, file mutation, file-editing executor
behavior, GitHub API behavior, Slack behavior, DRA behavior, Hermes behavior,
telemetry, release, publish, deploy, or runtime behavior changes.

The current canonical baseline remains:

```text
PHASE8E_PROVIDER_ADAPTER_DISABLED_CONTRACT_MAIN_SMOKE_EXTERNAL_PENDING
```

The current known prerequisite states remain:

```text
PASS_PHASE7_MUTATION_BOUNDARY_MAIN_SMOKE
PASS_PHASE8B_CITIZEN_ONE_CONTROL_PLANE_MAIN_SMOKE
PASS_PHASE8C_PROPOSAL_CONTRACT_MAIN_SMOKE
PASS_PHASE8D_DETERMINISTIC_PROPOSAL_STUB_MAIN_SMOKE
PASS_PHASE8E_PROVIDER_ADAPTER_DISABLED_CONTRACT_MAIN_SMOKE
NOT_YET_TRUE_EXTERNAL
ON_OPT_IN
IMPLEMENTED_AND_BOUND
IMPLEMENTED_AND_BOUND
IMPLEMENTED_AND_BOUND
SCOPE_LOCKED
NOT_STARTED
NOT_ALLOWED_BEFORE_SEPARATE_GATE
```

The safe default remains:

```text
hold_current_state
```

## 2. Why prompt/response redaction boundary is needed before provider call

A provider call would introduce raw prompt bodies, provider request metadata,
raw response bodies, provider errors, model-generated text, network behavior,
API credentials, environment values, logs, and replay expectations.

The redaction boundary must be locked before any provider call exists so future
implementation cannot accidentally store raw prompt or response content in
evidence, manifests, logs, stdout, stderr, `.aeg/` runtime files, reports, field
reports, or tracked files.

This boundary also prevents provider output from becoming a source of truth.
Provider output is `reported_only`. Provider or model self-report is not a
judgment basis and cannot replace law status, risk classification, user gates,
Phase 7 mutation attribution, evidence binding, or deterministic verify replay.

This document only permits planning and review. It does not authorize provider
calls or raw prompt/response retention.

## 3. Prompt construction boundary

Prompt construction is future implementation.

The prompt is not a source of truth. The prompt body is not evidence, not a
manifest binding target, not a replay proof, not user approval, and not a
judgment basis.

Raw prompt body storage is forbidden until a separate future gate explicitly
approves prompt construction, redaction, retention policy, evidence binding,
verify behavior, and tests.

Prompt content must not include secrets, API keys, tokens, credentials, `.env`
values, private repo content, private runtime values, raw provider responses,
or any value that would be unsafe to record. Future prompt construction must
prefer minimal, redacted, non-secret metadata and must gracefully hold if safe
prompt construction cannot be proven.

Expected prompt storage principles:

- `prompt_raw_stored=false`
- `prompt_secret_detected=false` or hold
- `prompt_storage_policy=no_raw_prompt_storage`

## 4. Prompt input candidates

Future implementation may consider these prompt input candidates only after a
separate implementation gate:

- redacted task category.
- redacted law or classifier status.
- redacted LOW, MEDIUM, or HIGH risk status.
- redacted proposal contract state.
- deterministic stub state marker.
- provider disabled state marker.
- redacted mutation boundary status.
- safe, non-secret command mode metadata.
- safe, non-secret repository state summary.
- safe, non-secret user gate requirement marker.

Prompt input candidates must not include raw private repository content, raw
diffs, raw file contents, secret values, API keys, tokens, credentials, `.env`
values, raw prompt text from prior runs, raw provider responses, private runtime
values, or user-provided sensitive material that has not passed a separate
redaction gate.

Prompt source may be represented only as minimal metadata candidates. Candidate
fields:

- `prompt_build_requested`
- `prompt_build_status`
- `prompt_source`
- `prompt_input_summary`
- `prompt_redaction_status`
- `prompt_hash_candidate`
- `prompt_storage_policy`
- `prompt_secret_detected`
- `prompt_raw_stored`

These fields are candidates only. They are not implemented by this document.

## 5. Prompt redaction rules

Future prompt redaction must remove or block:

- API keys, tokens, credentials, and secret-like values.
- `.env` values and private deployment values.
- raw private repository content.
- raw file contents unless separately approved by a future gate.
- raw diffs unless separately approved by a future gate.
- raw provider request bodies.
- raw provider response bodies.
- provider SDK error bodies that echo request or response content.
- private runtime paths or values that are not safe to record.

If redaction cannot prove that the prompt candidate is secret-safe, future
behavior must hold. A redaction failure must not cause raw prompt fallback
storage, stdout printing, stderr printing, report insertion, evidence insertion,
manifest insertion, or `.aeg/` runtime retention.

Prompt redaction status may be a future metadata candidate, but it must not
include raw prompt text or values derived from secrets.

## 6. Prompt hash / metadata candidates

Future implementation may consider a prompt hash candidate only if it does not
expose raw prompt content, raw secrets, raw `.env` values, raw private repo
content, or provider request bodies.

Allowed candidate direction:

- hash only canonicalized, approved, redacted prompt material.
- bind the hash to redaction status and storage policy.
- record source categories rather than raw source text.
- record `prompt_raw_stored=false`.
- record `prompt_storage_policy=no_raw_prompt_storage`.
- record `prompt_secret_detected=false` only when secret-safe detection can be
  proven; otherwise hold.

Disallowed candidate direction:

- storing raw prompt text.
- storing reversible encodings of prompt text.
- storing excerpts, prefixes, suffixes, lengths, token windows, or embeddings
  that could reveal sensitive prompt content.
- hashing unredacted secret-bearing content and treating the digest as safe by
  itself.
- using prompt hash as a proof of correctness, safety, mutation absence, or
  user approval.

Prompt hash and metadata candidates are future evidence candidates only. They
are not implemented by this document.

## 7. Response handling boundary

Response handling is future implementation.

Raw provider response storage is forbidden until a separate future gate
explicitly approves response parsing, redaction, retention policy, evidence
binding, verify behavior, and tests.

The response body is not a judgment basis. A provider response is only a
proposal material candidate. If a provider says a plan is safe, that statement
is not a judgment basis. If a provider says no mutation occurred, that
statement is not a judgment basis. If a provider says no user gate is needed,
that statement is not a judgment basis.

Expected response storage principles:

- `response_reported_only=true`
- `response_trust_boundary=reported_only`
- `response_raw_stored=false`
- raw response storage is forbidden

## 8. Response redaction rules

Future response redaction must remove or block:

- secrets, API keys, tokens, credentials, and secret-like values.
- `.env` values and private deployment values.
- raw prompt echoes.
- raw provider request bodies.
- raw private repository content.
- raw file contents or diffs echoed by the provider.
- provider tool-call payloads unless separately approved by a future gate.
- provider SDK error bodies that include raw request or response content.
- private runtime values.

Response redaction failure must hold. It must not fall back to raw response
storage, stdout printing, stderr printing, report insertion, evidence insertion,
manifest insertion, field report insertion, or `.aeg/` runtime retention.

Response redaction status may be a future metadata candidate, but it must not
include raw provider output or values derived from secrets.

## 9. Response hash / metadata candidates

Future implementation may consider these response metadata candidates:

- `response_present`
- `response_status`
- `response_source`
- `response_reported_only`
- `response_trust_boundary`
- `response_redaction_status`
- `response_hash_candidate`
- `response_raw_stored`
- `response_error_class`
- `response_error_safe_summary`

Expected candidate values include:

- `response_reported_only=true`
- `response_trust_boundary=reported_only`
- `response_raw_stored=false`

Future response hash candidates may bind approved, redacted, canonicalized
response material only. They must not expose raw response content, raw prompt
content, secrets, `.env` values, private repo content, provider request bodies,
or reversible encodings of response text.

`response_error_safe_summary` may include only secret-safe error categories or
human-readable summaries that do not reveal credentials, tokens, raw prompts,
raw responses, provider request bodies, provider response bodies, private repo
content, or private runtime values.

These fields are candidates only. They are not implemented by this document.

## 10. Forbidden storage locations

Raw prompts, raw provider responses, raw provider request bodies, secrets, API
keys, tokens, credentials, `.env` values, private runtime values, and unsafe
provider SDK error bodies must not be stored in:

- evidence.
- manifest.
- logs.
- stdout.
- stderr.
- `.aeg` runtime files.
- tracked files.
- reports.
- field reports.

This prohibition applies to success paths, failure paths, hold paths, debug
paths, replay paths, tests, fixtures, and future migration paths unless a
separate gate explicitly approves a narrower safe representation.

## 11. Secret/API key/.env boundary

API keys, tokens, credentials, `.env` values, and secret-like values must never
be recorded through any path.

Secret presence can itself be sensitive. Future implementation must minimize
secret-presence metadata and must avoid exposing secret values, prefixes,
suffixes, lengths, fingerprints, key names tied to private deployments,
provider account details, or private environment layout.

Missing API keys or missing provider configuration must produce graceful hold or
fail behavior. Missing keys must not corrupt evidence, change default runtime
behavior, trigger network calls, print secret-adjacent diagnostics, or convert
unchecked provider state into PASS.

Tracked `.env` files remain forbidden. `.aeg/` runtime files must not become a
secret sink and must not be tracked.

## 12. Provider output trust boundary

Provider output is `reported_only`.

Provider and model self-report are not judgment bases. Provider output cannot
prove safety, correctness, verification success, mutation absence, policy
compliance, user approval, readiness, or external unaided status.

Provider output cannot:

- replace law status.
- replace LOW, MEDIUM, or HIGH risk classification.
- downgrade HIGH.
- satisfy, bypass, or simulate the user gate.
- replace Phase 7 mutation attribution.
- turn `NOT_CHECKED` into PASS.
- redefine `REPLAY_CONSISTENT`.
- authorize mutation, file edits, main merge, release, publish, or deploy.

Judgment basis remains with existing trusted mechanisms:

- classifier results for risk classification.
- law status for law evaluation.
- user gate state for protected behavior.
- evidence binding for recorded run facts.
- Phase 7 pre/post snapshot and `computed_mutation_delta` for mutation
  attribution.
- deterministic verify replay and binding validation for verify results.

## 13. Evidence/manifest binding candidates

Only redacted metadata and approved hash candidates may become future
evidence/manifest binding candidates.

Candidate binding surfaces may include:

- prompt build requested marker.
- prompt build status.
- prompt source category.
- prompt input summary category.
- prompt redaction status.
- prompt hash candidate.
- prompt storage policy.
- prompt secret detected marker when secret-safe and minimal.
- prompt raw stored marker, expected `false`.
- response present marker.
- response status.
- response source category.
- response reported-only marker.
- response trust boundary marker.
- response redaction status.
- response hash candidate.
- response raw stored marker, expected `false`.
- response error class.
- response error safe summary.

Raw prompts and raw responses are not binding targets. Raw provider request
bodies, provider response bodies, secrets, API keys, tokens, credentials, `.env`
values, private repo content, and private runtime values are not binding
targets.

## 14. Verify replay candidates

Future verify behavior may check redacted prompt/response metadata binding,
hash candidate binding, storage policy binding, and redaction status binding.

Prompt or response redaction status tamper may become a future verify candidate
for `REPLAY_FAILED`.

Verify success remains deterministic replay and binding validation. A successful
verify result means `REPLAY_CONSISTENT`; it is not external oracle proof, model
proof, provider proof, provider-output correctness proof, or public readiness
proof.

Raw prompt and raw response replay is not approved by this document.

## 15. User gate dependency

HIGH remains `NEEDS_USER_GATE`.

Prompt content, response content, prompt hash candidates, response hash
candidates, provider metadata, provider output, provider self-report, and model
self-report must not bypass, satisfy, simulate, or downgrade the user gate.

Provider-generated text cannot approve protected actions, authorize HIGH
behavior, merge to main, release, publish, deploy, perform mutation, execute
commands, or convert `NEEDS_USER_GATE` into PASS.

The safe default remains:

```text
hold_current_state
```

## 16. Phase 7 mutation boundary dependency

Phase 7 Mutation Boundary / Pre-Post Diff v1 remains the mutation attribution
dependency.

Prompt content and response content are irrelevant to mutation attribution. If a
provider or model says it did not modify files, that statement is not a
judgment basis.

The mutation judgment basis remains the trusted Phase 7 pre/post snapshot and
independently computed `computed_mutation_delta`.

Future prompt/response behavior must preserve:

1. trusted `pre_run_changed_files`.
2. executor, dry-run, stub, provider-disabled, or held invocation candidate.
3. trusted `post_run_changed_files`.
4. independently computed `computed_mutation_delta`.
5. verify replay and binding validation.

## 17. Deterministic stub dependency

The Phase 8-D deterministic proposal stub path remains preserved.

Future prompt/response redaction implementation must not remove, weaken, or
replace the deterministic stub path. The deterministic stub remains the local,
offline, predictable way to exercise proposal contract behavior without
provider access, network access, API keys, `.env` loading, raw prompts, raw
responses, or model calls.

Stub output remains `reported_only` and does not become a prompt/response
judgment basis.

## 18. Provider adapter disabled dependency

The Phase 8-E provider adapter disabled contract remains preserved.

Future prompt/response redaction implementation must not change the disabled
provider path into an active provider path. Provider/API/env/network/model-call
behavior remains scope locked until a separate implementation gate explicitly
permits it.

The disabled provider path must continue to preserve default `aeg run`, default
`aeg verify`, offline/core mode, safe hold behavior, no network calls, no
secret loading, no raw prompt storage, and no raw response storage.

## 19. Non-goals

This Phase 8-F work does not implement:

- prompt builder.
- response parser.
- provider adapter.
- OpenAI integration.
- Claude integration.
- Gemini integration.
- OpenAI API calls.
- API key loading.
- `.env` loading.
- network calls.
- model-backed executor behavior.
- autonomous loops.
- actual mutation execution.
- file-editing executor behavior.
- raw prompt storage.
- raw response storage.
- secret, token, credential, or API key recording.
- `.env` value recording.
- `.aeg/` git inclusion.
- `aeg run` behavior changes.
- `aeg verify` behavior changes.
- classifier, law, evidence, or state code changes.
- GitHub API behavior.
- Slack, DRA, or Hermes behavior.
- release, publish, deploy, direct main push, or main merge behavior.
- telemetry.

## 20. Future implementation acceptance criteria

Future implementation may be considered only if it proves all of the following:

- explicit opt-in only.
- default `aeg run` preserved.
- no raw prompt storage.
- no raw response storage.
- no API key or `.env` value logging.
- no network call without explicit opt-in.
- no autonomous loop.
- no file mutation.
- redacted metadata only.
- hash candidates do not expose raw content.
- provider/model output remains `reported_only`.
- prompt/response does not replace law, risk, or status.
- prompt/response does not bypass user gate.
- Phase 7 mutation boundary remains active.
- deterministic stub path remains preserved.
- provider disabled path remains preserved.
- offline/core mode remains usable.
- `NOT_CHECKED` never becomes PASS.
- HIGH remains `NEEDS_USER_GATE`.

Future implementation must include tests that prove success, failure, hold,
redaction, secret-safe error, opt-in, offline/core, deterministic stub, provider
disabled, evidence binding, and verify replay behavior remain inside this
boundary.

## 21. Go/no-go criteria

Go criteria for a future implementation gate:

- prompt/response raw storage remains forbidden by default.
- redaction rules are explicit and testable.
- storage policy is explicit and testable.
- hash candidates are non-reversible and do not expose raw content.
- secret/API key/`.env` handling is secret-safe.
- network behavior is explicit opt-in only.
- provider output remains `reported_only`.
- law, risk, status, user gate, Phase 7 mutation attribution, and verify replay
  remain authoritative.
- default `aeg run`, default `aeg verify`, deterministic stub path, provider
  disabled path, and offline/core mode remain usable.

No-go criteria:

- raw prompt storage is introduced.
- raw response storage is introduced.
- secrets, API keys, tokens, credentials, or `.env` values can be recorded.
- network calls occur without explicit opt-in.
- prompt or response content becomes a judgment basis.
- provider output can bypass user gates or downgrade HIGH.
- provider/model self-report can turn `NOT_CHECKED` into PASS.
- Phase 7 mutation attribution is weakened or replaced.
- deterministic stub or provider disabled behavior regresses.
- runtime behavior changes outside an approved implementation gate.

## 22. Handoff criteria to prompt/response redaction implementation

Handoff to a future prompt/response redaction implementation requires a
separate gate that defines:

- exact prompt metadata fields.
- exact response metadata fields.
- exact redaction statuses.
- exact hash canonicalization rules.
- exact storage policy markers.
- exact secret-detection behavior and hold behavior.
- exact evidence/manifest binding rules.
- exact verify replay and tamper behavior.
- exact stdout/stderr/log/report exclusions.
- exact tests for raw prompt absence and raw response absence.
- exact tests for API key, token, credential, and `.env` value absence.
- exact opt-in controls for any provider or network path.
- exact preservation tests for default `aeg run`, default `aeg verify`,
  deterministic stub path, provider disabled path, offline/core mode, HIGH
  user gate behavior, and Phase 7 mutation boundary behavior.

Until those criteria are met in a separate implementation gate, the only safe
default remains:

```text
hold_current_state
```
