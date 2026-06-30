# Aegis Phase 8-D Deterministic Proposal Stub Scope Plan v0

## 1. Phase 8-D purpose

Phase 8-D locks the scope for a future deterministic local proposal stub before
any stub implementation begins.

The purpose is to decide whether a deterministic local fixture may be used in a
future implementation to exercise the Phase 8-C proposal contract path without
provider configuration, API access, network access, environment loading, secret
handling, or a model call.

This is a planning gate only. It does not implement a deterministic proposal
stub, proposal generator, provider adapter, API key path, `.env` loader, network
call, model-backed executor, autonomous loop, file-editing executor, actual
mutation execution, or runtime behavior change.

The current canonical baseline remains:

```text
PHASE8C_PROPOSAL_CONTRACT_MAIN_SMOKE_EXTERNAL_PENDING
```

The current known prerequisite states remain:

```text
PASS_PHASE7_MUTATION_BOUNDARY_MAIN_SMOKE
PASS_PHASE8B_CITIZEN_ONE_CONTROL_PLANE_MAIN_SMOKE
PASS_PHASE8C_PROPOSAL_CONTRACT_MAIN_SMOKE
NOT_YET_TRUE_EXTERNAL
ON_OPT_IN_HOLD_ONLY
IMPLEMENTED_AND_BOUND
NOT_STARTED
SCOPE_LOCKED
NOT_STARTED
```

The safe default remains:

```text
hold_current_state
```

## 2. Why deterministic stub is needed before provider/model call

Phase 8-C implemented and bound the proposal contract, but the current
provider state is intentionally unconfigured. The validated path is therefore
limited to `proposal_present=false` with a provider-not-configured hold.

Before any provider, API, network, environment, secret, or model-backed path is
allowed, Aegis needs a way to test the `proposal_present=true` contract branch
under local, deterministic, offline conditions. A deterministic local stub can
exercise proposal field binding, replay behavior, tamper detection, and
reported-only trust boundaries without introducing remote output or secret
surfaces.

This document only permits scoping and review for that future stub. It does not
authorize implementation.

## 3. Deterministic stub definition

A deterministic proposal stub is a local deterministic fixture.

The stub is not model output. The stub is not provider output. The stub is not a
model-backed executor. The stub does not use network, API, environment, or
secret inputs. The stub produces only fixed, predictable proposal fields that
are suitable for exercising the proposal contract path.

The stub is a contract-test tool. It exists only to make a future
`proposal_present=true` path deterministic and reviewable without provider
access. It is not execution, not authorization, not a judgment basis, and not a
claim of readiness.

## 4. Allowed stub behavior

Future implementation may be considered only if the deterministic stub is
limited to explicit opt-in behavior.

Allowed candidate behavior:

- default `aeg run` behavior is preserved when the future opt-in is absent.
- the stub may create a deterministic `proposal_present=true` path.
- `proposal_summary` may contain only fixed local content with no secrets.
- `proposal_steps` may contain only fixed local content with no secrets.
- `proposal_risk_notes` may contain only fixed local content with no secrets.
- `proposal_reported_only=true` must be preserved.
- `proposal_trust_boundary=reported_only` must be preserved.
- offline/core mode must remain usable without provider access.

Stub proposal content remains advisory reported-only content. It is not
execution and does not authorize execution.

## 5. Forbidden stub behavior

Future implementation must reject any deterministic stub behavior that performs
or enables:

- file mutation.
- command execution.
- provider calls.
- network calls.
- environment or API key loading.
- secret discovery, logging, or recording.
- raw prompt storage.
- raw response storage.
- user gate satisfaction, bypass, simulation, or downgrade.
- law status replacement.
- LOW, MEDIUM, or HIGH risk replacement.
- conversion of `NOT_CHECKED` into PASS.
- autonomous loops.
- actual mutation execution.
- file-editing executor behavior.
- GitHub API behavior.
- Slack, DRA, or Hermes behavior.
- release, publish, deploy, direct main push, or main merge behavior.
- telemetry.

The stub cannot promote itself into a trusted executor or source of truth.

## 6. Proposal contract dependency

The deterministic stub depends on the Phase 8-C proposal contract.

Future stub output must fit the proposal contract fields and semantics rather
than creating a parallel proposal shape. It must preserve the proposal contract
requirements that proposal is not execution, not judgment basis, not user
approval, and not law or risk authority.

The stub exists to exercise the contract path. It does not loosen, replace, or
extend the contract without a separate gate.

## 7. Proposal trust boundary

Stub proposal output is `reported_only`.

Stub self-report is not a judgment basis. If a stub proposal says a plan is
safe, that statement is not a judgment basis. If a stub proposal says no files
were modified, that statement is not a judgment basis. If a stub proposal says
verification should pass, that statement is not a judgment basis.

Judgment basis remains with existing trusted mechanisms:

- classifier results for risk classification.
- law status for law evaluation.
- evidence binding for recorded run facts.
- Phase 7 pre/post snapshot and `computed_mutation_delta` for mutation
  attribution.
- deterministic verify replay and binding validation for verify results.

## 8. Evidence/manifest binding expectations

Future implementation must bind stub proposal fields into evidence and
manifest data when the future stub records `proposal_present=true`.

Expected binding surfaces include:

- proposal contract version.
- deterministic stub source marker.
- fixed proposal summary.
- fixed proposal steps.
- fixed proposal risk notes.
- `proposal_reported_only=true`.
- `proposal_trust_boundary=reported_only`.
- user-gate-required marker when applicable.
- approved deterministic output digest or equivalent binding marker if used.

Raw prompts, raw responses, secrets, API keys, tokens, credentials, `.env`
values, provider request bodies, provider response bodies, and private runtime
values must not be recorded.

Proposal tamper must be detected by future verify behavior as
`REPLAY_FAILED`.

## 9. Verify replay expectations

Future verify behavior for the deterministic stub must remain deterministic
replay and binding validation.

Expected verify semantics:

- unchanged stub proposal evidence replays as `REPLAY_CONSISTENT`.
- tampered stub proposal fields replay as `REPLAY_FAILED`.
- missing required bound proposal fields replay as failed or inconsistent,
  according to the future contract tests.
- `REPLAY_CONSISTENT` means deterministic replay consistency only.
- `REPLAY_CONSISTENT` is not external oracle proof.
- `REPLAY_CONSISTENT` is not provider correctness proof.
- `REPLAY_CONSISTENT` is not model quality proof.
- proposal content remains outside judgment-basis status.

This document does not change `aeg verify` behavior.

## 10. User gate dependency

HIGH remains `NEEDS_USER_GATE`.

The deterministic stub cannot satisfy, bypass, replace, simulate, or downgrade
the user gate. Stub proposal content cannot approve protected actions,
authorize HIGH behavior, merge to main, release, publish, deploy, mutate files,
execute commands, call providers, call networks, or convert `NEEDS_USER_GATE`
into PASS.

If a future stub proposal recommends protected behavior, the user gate remains
required. The safe default remains:

```text
hold_current_state
```

## 11. Phase 7 mutation boundary dependency

Phase 7 Mutation Boundary / Pre-Post Diff v1 remains the mutation attribution
dependency regardless of whether a deterministic stub proposal is generated.

Mutation attribution must come from trusted Phase 7 pre/post snapshots and the
independently computed `computed_mutation_delta`. Stub proposal text is not
mutation evidence.

If a stub says no files were modified, that statement is not a judgment basis.
If file mutation appears, `computed_mutation_delta` takes priority. Future
implementation must preserve:

1. trusted `pre_run_changed_files`
2. deterministic stub proposal-only invocation, if explicitly opted in
3. trusted `post_run_changed_files`
4. independently computed `computed_mutation_delta`
5. verify replay and binding validation

Stub existence cannot hide, downgrade, or reinterpret computed mutation.

## 12. Provider/secret/network boundary dependency

The deterministic stub must preserve the Phase 8-A provider, secret, and
network boundary.

The stub does not use providers, APIs, network calls, API keys, tokens,
credentials, `.env` files, environment loading, provider SDKs, model calls, or
remote services. Provider absence must not become a runtime failure for default
`aeg run`, and provider absence must not corrupt evidence or turn unchecked
state into PASS.

The stub must not log, store, hash, print, or commit secret values. The stub
must not store raw prompts or raw responses because it has no provider/model
prompt-response exchange.

## 13. Non-goals

Phase 8-D does not include:

- deterministic proposal stub implementation.
- proposal generator implementation.
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
- raw prompt storage.
- raw response storage.
- changes to `aeg run` behavior.
- changes to `aeg verify` behavior.
- classifier, law, evidence, state, source, or test changes.
- GitHub API integration.
- Slack, DRA, or Hermes integration.
- release, publish, or deploy work.
- telemetry.
- secret, token, or API key recording.
- `.env` value recording.
- `.aeg/` tracking.
- direct main push.
- main merge.
- public, dogfood, release, or true external readiness claims.

## 14. Future implementation acceptance criteria

Future deterministic stub implementation should be rejected unless it satisfies
all of these acceptance criteria:

- explicit opt-in only.
- default `aeg run` preserved.
- provider, API, environment, and network are not used.
- no secret logging.
- no raw prompt storage.
- no raw response storage.
- no autonomous loop.
- no file mutation.
- `proposal_present=true` deterministic path exists under explicit opt-in.
- proposal fields are evidence-bound.
- proposal tamper produces `REPLAY_FAILED`.
- proposal remains `reported_only`.
- proposal does not replace law, risk, or status.
- proposal does not bypass the user gate.
- LOW, MEDIUM, and HIGH are preserved.
- HIGH remains `NEEDS_USER_GATE`.
- `NOT_CHECKED` never becomes PASS.
- Phase 7 mutation boundary remains active.
- offline/core mode remains usable.

## 15. Go/no-go criteria

GO for a future deterministic stub implementation gate requires all of the
following:

- the implementation is explicitly scoped as local deterministic fixture work.
- no provider, API, environment, secret, network, or model-call behavior is
  introduced.
- no runtime default behavior changes.
- no file mutation or command execution behavior.
- proposal output remains `reported_only`.
- proposal fields bind into evidence and manifest data.
- proposal tamper is verified as `REPLAY_FAILED`.
- default offline/core behavior remains usable.
- HIGH remains `NEEDS_USER_GATE`.
- Phase 7 mutation attribution remains authoritative.

NO-GO applies if any future implementation includes provider calls, network
calls, environment or API key loading, raw prompt/response storage, secret
logging, user-gate bypass, law/risk/status replacement, autonomous loops, file
mutation, command execution, release, publish, deploy, direct main push, main
merge, telemetry, or tracked `.aeg/` or `.env` artifacts.

## 16. Handoff criteria to deterministic stub implementation

A future implementation PR may begin only after this scope is accepted and the
handoff confirms:

- implementation is limited to a deterministic local fixture.
- implementation is explicit opt-in only.
- default `aeg run` behavior remains unchanged.
- default `aeg verify` behavior remains unchanged except for separately
  reviewed deterministic replay checks for bound stub fields.
- proposal contract fields and trust boundaries from Phase 8-C remain binding.
- evidence and manifest binding expectations are testable.
- tamper behavior has a deterministic `REPLAY_FAILED` test path.
- Phase 7 mutation boundary tests remain active.
- provider, secret, environment, and network boundaries remain closed.
- safe default remains `hold_current_state`.
