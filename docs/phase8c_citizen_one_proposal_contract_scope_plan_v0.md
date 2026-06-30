# Aegis Phase 8-C Citizen One Proposal Contract Scope Plan v0

## 1. Phase 8-C purpose

Phase 8-C locks the Citizen One proposal contract boundary before any
model-backed proposal implementation begins.

The purpose is to define the candidate proposal structure, trust boundary,
evidence binding candidates, verification candidates, storage boundary, user
gate dependency, Phase 7 mutation boundary dependency, and provider/secret/
network dependency for a future Citizen One proposal surface.

This is a planning gate only. It does not implement a proposal generator,
provider adapter, API key path, `.env` loader, network call, model-backed
executor, autonomous loop, file-editing executor, actual mutation execution, or
runtime behavior change.

The current canonical baseline remains:

```text
PHASE8B_CITIZEN_ONE_CONTROL_PLANE_MAIN_SMOKE_EXTERNAL_PENDING
```

The current known prerequisite states remain:

```text
PASS_PHASE7_MUTATION_BOUNDARY_MAIN_SMOKE
PASS_PHASE8A_PROVIDER_SECRET_NETWORK_SCOPE_PLAN_MAIN_SMOKE
PASS_PHASE8B_CITIZEN_ONE_CONTROL_PLANE_MAIN_SMOKE
NOT_YET_TRUE_EXTERNAL
ON_OPT_IN_HOLD_ONLY
SCOPE_LOCKED
NOT_STARTED
```

The safe default remains:

```text
hold_current_state
```

## 2. Why proposal contract is needed before proposal implementation

Citizen One must not introduce model-backed proposal behavior as an incidental
runtime change. A proposal surface crosses multiple boundaries at once: model
output trust, provider configuration, secret handling, network behavior,
evidence binding, raw prompt/response retention, user gate behavior, law status
interaction, LOW/MEDIUM/HIGH risk preservation, and Phase 7 mutation
attribution.

A proposal contract is needed before implementation so future code has a
narrow, reviewable contract:

- proposal is not execution.
- proposal is not a source of truth.
- proposal is `reported_only`.
- model/provider self-report is not a judgment basis.
- proposal cannot bypass, satisfy, or replace the user gate.
- proposal cannot replace law status or risk classification.
- proposal cannot prove mutation absence.
- raw prompt/response storage remains blocked until a separate gate.
- provider/API/env/network implementation remains blocked until a separate
  gate.
- Phase 7 mutation boundary remains authoritative for mutation attribution.
- safe default remains `hold_current_state`.

This document only permits future planning and review. It does not authorize
implementation.

## 3. Proposal contract definition

A Citizen One proposal is an execution-plan candidate or recommendation
candidate only.

A proposal does not mean that Aegis modified files, executed commands, merged
branches, released, published, deployed, or performed any protected action. A
proposal is not a mutation executor and is not evidence that mutation did or did
not occur.

A proposal does not replace law status. A proposal does not replace LOW,
MEDIUM, or HIGH risk classification. A proposal cannot convert `NOT_CHECKED`
into PASS. A proposal cannot redefine `REPLAY_CONSISTENT`.

Future implementation must keep proposal state separate from judgment-basis
state. Proposal content may be shown to a user as advisory context, but it must
not become the source of truth for safety, readiness, mutation attribution,
verification success, or user approval.

## 4. Proposal field candidates

Future implementation may consider these proposal field candidates:

- `proposal_id`
- `proposal_version`
- `proposal_kind`
- `proposal_summary`
- `proposal_steps`
- `proposal_risk_notes`
- `proposal_requires_user_gate`
- `proposal_trust_boundary`
- `proposal_reported_only`
- `proposal_source`
- `proposal_output_hash_candidate`
- `proposal_redaction_status`

Candidate meanings:

- `proposal_id`: stable identifier for a recorded proposal candidate.
- `proposal_version`: contract/schema version for future compatibility checks.
- `proposal_kind`: proposal category, such as explanation, plan, dry-run
  recommendation, or implementation candidate.
- `proposal_summary`: redacted human-readable proposal summary.
- `proposal_steps`: redacted advisory step list, not command authorization.
- `proposal_risk_notes`: advisory risk notes, not LOW/MEDIUM/HIGH authority.
- `proposal_requires_user_gate`: candidate marker that protected or HIGH-risk
  actions still require the user gate.
- `proposal_trust_boundary`: marker that proposal content is `reported_only`.
- `proposal_reported_only`: explicit boolean or equivalent marker preserving
  non-authoritative status.
- `proposal_source`: redacted source category, such as deterministic fixture,
  local stub, or future provider category if separately gated.
- `proposal_output_hash_candidate`: optional digest candidate for binding
  redacted proposal output without exposing raw secrets or prompts.
- `proposal_redaction_status`: candidate marker describing whether proposal
  content is redacted, raw storage is absent, or retention was blocked.

These fields are candidates only. They are not implemented by this document.
Raw prompt/response storage remains blocked until a separate gate explicitly
allows and tests it.

## 5. Proposal trust boundary

Proposal output is `reported_only`.

Proposal self-report is not a judgment basis. If a proposal says it is safe,
that statement is not a judgment basis. If a proposal says no mutation occurred,
that statement is not a judgment basis. If a proposal says verification passed,
that statement is not a judgment basis.

Judgment basis remains with existing trusted mechanisms:

- classifier results for risk classification.
- law status for law evaluation.
- evidence binding for recorded run facts.
- Phase 7 pre/post snapshot and `computed_mutation_delta` for mutation
  attribution.
- deterministic verify replay and binding validation for verify results.

Proposal content may be a candidate reference shown to a user. It must not
approve itself, certify itself, promote itself to source-of-truth evidence, or
replace Aegis judgment-basis mechanisms.

## 6. Proposal evidence binding candidates

Proposal metadata may become a candidate for future evidence binding after a
separate implementation gate defines exact fields and tests.

Candidate binding surfaces may include:

- proposal contract version.
- proposal identifier.
- proposal kind.
- redacted proposal summary.
- `reported_only` trust-boundary marker.
- user-gate-required marker.
- redaction status.
- output hash candidate.
- deterministic local stub or fixture source marker, if separately approved.

Raw output storage is not approved by this document. Whether raw prompt or raw
response retention is ever allowed requires a separate gate.

Hash candidates must not expose raw secrets, raw prompts, API keys, tokens,
credentials, `.env` values, provider request bodies, provider response bodies,
or private runtime values. Hash candidates must be designed so they bind only
approved redacted content or approved canonicalized output.

Proposal tamper detection may be treated as a future verify candidate, but this
document does not implement tamper detection.

## 7. Proposal verification candidates

Future verification may consider these proposal-specific checks:

- proposal schema/contract version is recognized.
- required proposal metadata fields are present when proposal recording is
  enabled.
- `proposal_reported_only` is present and true, or equivalent.
- `proposal_trust_boundary` preserves the non-authoritative boundary.
- proposal does not replace law status.
- proposal does not replace LOW/MEDIUM/HIGH risk classification.
- proposal does not satisfy or bypass a user gate.
- HIGH remains `NEEDS_USER_GATE`.
- `NOT_CHECKED` never becomes PASS because proposal content exists.
- `REPLAY_CONSISTENT` remains deterministic replay and binding validation.
- raw prompt/response content is absent unless a separate future gate approves
  storage.
- proposal output hash candidate, if present, binds only approved redacted or
  canonicalized content.
- proposal tamper is detectable as a verification candidate.
- Phase 7 mutation boundary remains active when mutation attribution is needed.
- offline/core mode remains usable without provider access.

These are verification candidates only. This document does not change `aeg
verify` behavior.

## 8. Raw prompt/response storage boundary

Raw prompt and raw response storage is not approved by Phase 8-C.

Future implementation must not store raw prompts or raw model/provider
responses in evidence, manifests, logs, reports, stdout, stderr, `.aeg/`, or
tracked files without a separate gate. That future gate must define retention
policy, redaction rules, secret handling, prompt sensitivity, response
sensitivity, failure behavior, verify behavior, and tests.

Until a separate gate exists, only redacted metadata candidates or approved
hash candidates may be considered. Secret values, tokens, API keys, `.env`
values, provider request bodies, and provider response bodies must not be
recorded.

## 9. User gate dependency

HIGH remains `NEEDS_USER_GATE`.

A proposal cannot satisfy, bypass, replace, or simulate the user gate. A
proposal cannot approve protected actions. A proposal cannot downgrade HIGH to
LOW or MEDIUM. A proposal cannot authorize merge, release, publish, deploy,
mutation, file editing, command execution, GitHub API behavior, Slack behavior,
DRA behavior, Hermes behavior, or telemetry.

If a future proposal recommends protected behavior, the user gate remains
required. The safe default remains:

```text
hold_current_state
```

## 10. Phase 7 mutation boundary dependency

Phase 7 Mutation Boundary / Pre-Post Diff v1 remains the mutation attribution
dependency regardless of whether a proposal is generated.

Mutation attribution must come from trusted Phase 7 pre/post snapshots and the
independently computed `computed_mutation_delta`. Proposal text is not a
mutation judgment basis.

If a proposal says no files were modified, that statement is not a judgment
basis. If file mutation appears, the Phase 7 mutation boundary takes priority.
Future implementation must preserve:

1. trusted `pre_run_changed_files`
2. candidate invocation or proposal-only action
3. trusted `post_run_changed_files`
4. independently computed `computed_mutation_delta`
5. verify replay and binding validation

Proposal existence cannot hide, downgrade, or reinterpret computed mutation.

## 11. Provider/secret/network dependency

Provider, API, environment, and network behavior remains `SCOPE_LOCKED`.

This document does not implement provider integration, OpenAI integration,
Claude integration, Gemini integration, SDK use, API key handling, `.env`
loading, network calls, retries, streaming, tool calling, or model-backed
execution.

If future proposal implementation proceeds before provider implementation, a
separate gate must decide whether deterministic local stubs or fixtures are
allowed, how they are identified, and how they remain isolated from provider,
secret, and network behavior.

Secrets and API keys must not be recorded in evidence, logs, stdout, stderr,
reports, manifests, `.aeg/`, or tracked files. Secret/API key presence must not
trigger provider calls, network calls, mutation, retry loops, or evidence
promotion.

Offline/core mode must remain usable without provider access, network access,
API keys, or `.env` loading.

## 12. Non-goals

Phase 8-C does not include:

- proposal generator implementation
- provider implementation
- OpenAI, Claude, Gemini, or other model integration
- OpenAI API calls or any model API calls
- API key or token loading
- `.env` loading
- network calls
- model-backed executor implementation
- autonomous loop implementation
- actual mutation execution
- file-editing executor implementation
- `aeg run` behavior changes
- `aeg verify` behavior changes
- classifier, law, evidence, or state code changes
- source code changes
- test code changes
- README changes
- architecture document changes
- packaging changes
- GitHub API implementation
- Slack, DRA, or Hermes integration
- release, publish, or deploy behavior
- telemetry
- secret/token/API key recording
- `.aeg/` tracking
- `.env` tracking
- main merge or main direct push

## 13. Future implementation acceptance criteria

Future implementation must satisfy all of these before it can be accepted:

- explicit opt-in only.
- default `aeg run` behavior preserved.
- no provider/API/env/network behavior by default.
- no secret logging.
- no raw prompt/response storage without a separate gate.
- no autonomous loop.
- no file mutation by default.
- proposal recorded as `reported_only`.
- proposal does not replace law status.
- proposal does not bypass user gate.
- LOW/MEDIUM/HIGH preserved.
- HIGH remains `NEEDS_USER_GATE`.
- `NOT_CHECKED` never becomes PASS.
- `REPLAY_CONSISTENT` remains deterministic replay and binding validation.
- Phase 7 mutation boundary remains active.
- offline/core mode remains usable.

Additional acceptance expectations:

- proposal schema is explicit and versioned.
- proposal trust-boundary fields are testable.
- proposal evidence fields are redacted and bounded.
- proposal output hash candidate does not reveal raw secret or prompt content.
- proposal absence does not fail default core behavior.
- provider absence produces hold/fail behavior only on explicit opt-in paths.
- safe default remains `hold_current_state`.

## 14. Go/no-go criteria

Go criteria for a future proposal implementation gate:

- proposal contract fields are explicitly selected from or justified against
  this candidate set.
- trust boundary is implemented as `reported_only`.
- law status and LOW/MEDIUM/HIGH status remain independent.
- HIGH remains `NEEDS_USER_GATE`.
- raw prompt/response storage remains absent or has a separate approved gate.
- provider/API/env/network behavior remains absent or has a separate approved
  gate.
- Phase 7 mutation boundary is preserved.
- tests prove default `aeg run` behavior is preserved.
- tests prove offline/core mode remains usable.
- tests prove proposal cannot bypass user gate.

No-go criteria:

- proposal generator, provider, network, API, env, or model-backed executor
  behavior is introduced without a separate gate.
- proposal content is treated as source of truth.
- proposal self-report is used as a judgment basis.
- proposal downgrades HIGH risk or satisfies the user gate.
- proposal changes `aeg run` or `aeg verify` default behavior.
- proposal hides or overrides Phase 7 mutation attribution.
- raw prompts, raw responses, secrets, API keys, tokens, or `.env` values are
  recorded without an approved separate gate.
- `.aeg/` or `.env` becomes tracked.
- main is pushed to or merged by the implementation work.

## 15. Handoff criteria to proposal implementation

Phase 8-C may hand off to proposal implementation only when:

- this scope plan is reviewed and accepted.
- implementation scope remains proposal-only and explicit opt-in.
- provider/API/env/network behavior remains separately gated.
- raw prompt/response storage remains separately gated.
- deterministic local stub or fixture use, if desired, is separately approved.
- proposal schema fields are selected and documented.
- evidence binding fields are selected and redaction rules are documented.
- verification candidates are converted into testable implementation checks.
- user gate preservation is tested.
- Phase 7 mutation boundary preservation is tested.
- default `aeg run` and `aeg verify` behavior preservation is tested.
- offline/core mode preservation is tested.
- safe default remains `hold_current_state`.

Until those handoff criteria are met, the correct state is:

```text
hold_current_state
```
