# Aegis Phase 9 Action Interception Boundary Scope Plan v0

## 1. Phase 9 purpose

Phase 9 locks the Action Interception Boundary before any live executor,
model-backed executor, provider, actual model call, shell authority, network
authority, provider authority, remote write, deploy, release, publish, or
multi-citizen execution work can begin.

Phase 8 is not a completed live provider or model-backed executor. Phase 8
completed the provider/model boundary contract and disabled provider guard
metadata. Phase 7 Mutation Boundary covers the git working tree and diff axis:
what changed in the repository before and after an executor run.

Phase 9 covers a different axis: what actions were attempted or performed,
including actions that may leave no tracked working tree diff. Examples include
`git push`, deploy, network calls, external API calls, writes outside the repo,
credential or environment access attempts, provider invocation attempts, and
remote writes.

This is a planning gate only. It does not implement action interception,
sandboxing, shell wrappers, allowlists, denylists, live executors,
model-backed executors, providers, API key loading, environment loading,
network calls, prompt builders, response parsers, telemetry, release, publish,
deploy, or runtime behavior changes.

The current canonical baseline remains:

```text
PHASE8G_PROVIDER_RUNTIME_OPT_IN_GUARD_METADATA_MAIN_SMOKE_EXTERNAL_PENDING
```

The current known states remain:

```text
CLOSED_AT_PR28_MAIN_SMOKE
PHASE8H_HOLD_DO_NOT_START_NOW
NOT_YET_TRUE_EXTERNAL
PHASE6B_T_TRUE_EXTERNAL_UNAIDED_RUN_V0_FUTURE_MILESTONE
PROVIDER_API_ENV_NETWORK_MODEL_CALL_ON_HOLD
```

The safe default remains:

```text
hold_current_state
```

## 2. Non-goals

Phase 9 is not multi-citizen implementation. Phase 9 is not Citizens Few or
multi-citizen execution.

Phase 9 is the scope lock for how Aegis should capture and evidence actions
that are not visible through git diff. It defines future action categories,
risk taxonomy candidates, trust boundary candidates, evidence candidates,
verify replay candidates, acceptance criteria candidates, and live executor
hard blockers.

The following are non-goals for this planning gate:

- live executor implementation.
- model-backed executor implementation.
- provider implementation.
- actual model calls.
- OpenAI, Claude, Gemini, or other provider integration.
- API key, token, credential, `.env`, or environment loading.
- shell or process execution authority.
- network authority.
- provider authority.
- remote write authority.
- release, publish, or deploy implementation.
- prompt builder implementation.
- response parser implementation.
- action interception implementation.
- sandbox or container implementation.
- shell wrapper implementation.
- allowlist or denylist code implementation.
- telemetry implementation.
- new checker, report, manifest, or runtime artifact systems.
- changes to `aeg run`, `aeg verify`, source, tests, package metadata,
  architecture docs, or README behavior.

## 3. Action definition

An action is an attempted or completed operation by an executor, tool, process,
provider adapter, or future runtime path that crosses an authority boundary.
An action may or may not mutate tracked repository files.

Future Action Interception Boundary design must consider at least these action
categories:

- `git push`
- deploy
- release / publish
- network call
- external API call
- repo outside write/delete (`repo 밖 write/delete`)
- shell command / process execution
- credential/env access attempt
- provider/API invocation attempt
- remote write

Action classification must cover attempts as well as completed effects. A
blocked `git push` attempt, a blocked network call attempt, or a blocked
credential access attempt is still an action candidate and must be recordable
as an intercepted action candidate.

## 4. Action risk taxonomy candidates

Future implementation may consider the following action risk taxonomy:

- push/deploy/release/publish: `HIGH` or `BLOCKED` candidate.
- network/external API call: `HIGH` or `NOT_CHECKED`/`BLOCKED` candidate.
- repo outside write/delete: `HIGH` or `BLOCKED` candidate.
- credential/env access attempt: `HIGH` or `BLOCKED` candidate.
- raw shell command: `HIGH` or `BLOCKED` candidate before the action boundary.
- read-only command: `LOW` or `MEDIUM` candidate only when an interception and
  capability boundary exists.
- unknown/unintercepted action: must not be `CLEAN`; candidate status is
  `NOT_CHECKED` or `BLOCKED`.

Risk labels are candidates only. This document does not implement the
classifier, checker, action logger, interception layer, or executor behavior.

## 5. Interception mechanism candidates

Future Action Interception Boundary design may evaluate these mechanism
candidates:

- tool wrapper.
- sandbox/container.
- capability-based allowlist.
- filesystem scope restriction.
- network disabled by default.
- remote write disabled by default.
- no raw shell by default.
- no provider/network authority by default.
- shell, builtin, subprocess, and child-process bypass analysis.
- Aegis-controlled interception layer trust boundary.

Open questions for a future implementation gate:

- Which component owns the Aegis-controlled interception layer?
- How does the interception layer prove it is outside executor
  authorship/control?
- Which capabilities are unavailable by construction rather than detected by
  string matching?
- Which filesystem roots are readable, writable, or denied?
- How is network authority disabled by default and enabled only by an explicit
  future opt-in boundary?
- How are remote writes, deploys, releases, and publishes blocked by default?
- How are shell builtins, subprocesses, encoded commands, scripts, and provider
  SDK calls prevented from bypassing interception?
- What externally verifiable action log format can be replayed by `aeg verify`
  without trusting executor self-report?

## 6. Command enumeration vs capability isolation

### Command Enumeration

Command enumeration means using a denylist, allowlist, or string matching to
detect dangerous command text.

Judgment:

```text
INSUFFICIENT_AS_TRUST_BOUNDARY
```

Reasons:

- command strings can be constructed through variables.
- command strings can be hidden through encoding or indirection.
- shells have builtins and expansion behavior that can alter execution.
- subprocesses and child processes can perform actions not visible in the
  parent command string.
- scripts can perform network calls, credential reads, remote writes, deploys,
  releases, or publishes after a harmless-looking command starts them.
- external APIs and provider SDK calls can be invoked directly from language
  runtimes without matching a dangerous shell command string.

Required statements:

```text
Action interception cannot be secured by enumerating dangerous command strings.
NO_MATCHED_DANGEROUS_COMMAND != ACTION_BOUNDARY_CLEAN.
Command denylist alone is not sufficient to grant shell/network authority.
```

### Capability Isolation

Capability isolation means the executor does not receive the dangerous
capability in the first place, unless a future boundary explicitly grants it
under an Aegis-controlled interception layer and evidence contract.

Judgment:

```text
REQUIRED_FOR_LIVE_EXECUTOR_AUTHORITY
```

Required statements:

```text
Action boundary must be based on capability isolation, not only command matching.
Enumerate is not enough; isolate is required.
Command denylist alone is not sufficient to grant shell/network authority.
```

Future live executor authority must be based on isolation of shell, network,
remote write, provider, credential, and filesystem capabilities. Enumeration
may be useful as advisory metadata, but it cannot become the trust boundary.

## 7. Action capture trust boundary

Executor-reported action is `reported_only`.

`reported_only` is not a judgment basis. executor가 "위험한 action을 하지
않았다"고 말하는 것은 판단 근거가 아니다.

Required trust-boundary statements:

```text
executor-reported action = reported_only
reported_only is not judgment basis
intercepted action log is the only candidate judgment basis.
```

Judgment-basis candidates are only:

- Aegis-controlled interception layer.
- capability isolation boundary.
- externally verifiable action log.

The intercepted action log is the only candidate judgment basis. Even that
candidate is valid only when the action log source trust boundary is
Aegis-controlled and outside executor authorship/control.

Future implementation must preserve these rules:

- `executor_reported_actions` may be recorded as context only.
- `executor_reported_actions` must not certify action cleanliness.
- an executor statement of "no dangerous action" must not produce
  `ACTION_BOUNDARY_CLEAN`.
- an action log authored solely by the executor is not sufficient.
- action capture must be independently controlled or externally verifiable.

## 8. Diff vs action boundary relation

Pre/post diff answers:

```text
What changed?
```

Intercepted action log answers:

```text
What was done or attempted?
```

They are separate boundaries and do not replace each other. A clean git diff
does not prove no action happened. A logged action does not by itself prove
tracked repository mutation. Future evidence must keep the two axes distinct.

Required invariants:

```text
MUTATION_BOUNDARY_CLEAN does not imply ACTION_BOUNDARY_CLEAN.
NO_MATCHED_DANGEROUS_COMMAND != ACTION_BOUNDARY_CLEAN.
git diff clean != action clean.
mutation boundary clean != action boundary clean.
```

`git diff` clean means only that tracked working tree diff did not reveal a
tracked repository content change. It does not prove absence of `git push`,
deploy, release, publish, network, external API, credential access, provider
invocation, process execution, repo outside write/delete, or remote write
attempts.

## 9. No-op and unintercepted action rule

For a no-op executor, expected action count is:

```text
0
```

If a no-op executor performs an action, candidate status is `NEEDS_FIX` or
`BLOCKED`.

Required rules:

- unintercepted action != `CLEAN`.
- unknown action visibility = `NOT_CHECKED`.
- 감시하지 못한 action은 `PASS`/`CLEAN`으로 승격하지 않는다.
- command-matched only but not capability-isolated category must not be
  `CLEAN`.
- missing action log must not be treated as action cleanliness.
- no matched dangerous command must not be promoted to
  `ACTION_BOUNDARY_CLEAN`.

## 10. Evidence field candidates

Future evidence may consider these fields:

- `intercepted_actions`
- `action_log_source`
- `action_log_source_trust_boundary`
- `action_risk`
- `action_boundary_status`
- `action_interception_enabled`
- `action_interception_mode`
- `capability_isolation_enabled`
- `unintercepted_action_status`
- `executor_reported_actions`
- `computed_action_log_hash`
- `action_log_manifest_hash`
- `action_count`
- `expected_action_count`
- `command_enumeration_only`
- `no_matched_dangerous_command`
- `raw_shell_authority_granted`
- `network_authority_granted`
- `remote_write_authority_granted`
- `provider_authority_granted`

Candidate interpretation rules:

- `intercepted_actions` must come from an Aegis-controlled interception layer
  or externally verifiable action log before it can be a judgment-basis
  candidate.
- `executor_reported_actions` is `reported_only`.
- `command_enumeration_only=true` prevents `ACTION_BOUNDARY_CLEAN`.
- `no_matched_dangerous_command=true` does not imply
  `ACTION_BOUNDARY_CLEAN`.
- authority-granted fields must be false by default before a future
  implementation gate explicitly changes them.

These fields are not implemented by this document.

## 11. Verify replay candidates

Future verify replay may consider these checks:

- confirm saved action log hash.
- confirm manifest-bound action log hash.
- recompute action risk from the saved action log.
- if a `HIGH` action is marked `CLEAN`, return `INVALID_EVIDENCE`.
- if the action log is missing, return `NOT_CHECKED` or `INVALID_EVIDENCE`.
- if an unintercepted action is marked `CLEAN`, return `INVALID_EVIDENCE`.
- if `CLEAN` depends only on executor-reported action, return
  `INVALID_EVIDENCE`.
- if `command_enumeration_only=true` and status is
  `ACTION_BOUNDARY_CLEAN`, return `INVALID_EVIDENCE`.
- if `no_matched_dangerous_command` is promoted to
  `ACTION_BOUNDARY_CLEAN`, return `INVALID_EVIDENCE`.

Verify replay must not call providers, load secrets, load `.env`, use the
network, perform remote writes, run deploy/release/publish actions, or execute
live executor behavior to prove historical action cleanliness.

## 12. Future tests and acceptance criteria candidates

Future tests should include:

- no-op executor action count = 0.
- fake push/deploy/release/publish action is `HIGH` or `BLOCKED`.
- network/external API call is `HIGH` or `NOT_CHECKED`/`BLOCKED`.
- repo outside write/delete is `HIGH` or `BLOCKED`.
- credential/env access attempt is `HIGH` or `BLOCKED`.
- unintercepted action source is forbidden from becoming `CLEAN`.
- executor-reported action is forbidden as a judgment basis.
- dangerous command string not observed does not imply
  `ACTION_BOUNDARY_CLEAN`.
- simulated bypassable shell path must not become `CLEAN`.
- no raw shell authority before action boundary.
- `NO_MATCHED_DANGEROUS_COMMAND != ACTION_BOUNDARY_CLEAN`.
- `MUTATION_BOUNDARY_CLEAN does not imply ACTION_BOUNDARY_CLEAN`.

Planning gate acceptance criteria:

- this document is the only changed file.
- no source, test, package, README, architecture, runtime, or implementation
  files change.
- no action interception, sandbox, shell wrapper, allowlist, denylist, live
  executor, model-backed executor, provider, API key/env loading, network,
  prompt, parser, telemetry, release, publish, deploy, or multi-citizen
  implementation is added.
- no secret, token, credential, `.env` value, provider key, runtime artifact,
  or `.aeg/` tracked file is added.
- safe default remains `hold_current_state`.

## 13. Live executor hard blocker

Required hard blocker criteria:

```text
No live executor may receive shell/network/provider execution authority before Action Interception Boundary is implemented and verified.
No live executor may receive raw shell authority before capability isolation is defined.
No live executor may receive network authority before network isolation/opt-in boundary is implemented.
No live executor may perform remote write, deploy, release, publish, or external API calls before action boundary is implemented and verified.
```

Additional hard blockers:

- provider/model-backed executor is forbidden without action boundary.
- multi-citizen execution is forbidden without action boundary.
- action boundary 없이 provider/model-backed executor 금지.
- action boundary 없이 multi-citizen execution 금지.
- shell/network/provider execution authority remains on hold.
- raw shell authority remains on hold.
- remote write, deploy, release, publish, and external API calls remain on
  hold.
- actual provider/model call remains on hold.

The safe default for all blocked or unimplemented action authority remains:

```text
hold_current_state
```

## 14. Phase relation

Phase relation:

- Phase 9 = Action Interception Boundary.
- Phase 10 = Citizens Few / Multi-citizen, only after action boundary.
- Phase 6B-T True External Unaided Run v0 remains a future milestone.
- Phase 6B-T is an onboarding/external validation milestone.
- Phase 9 is a live executor safety hardening milestone.

Phase 10 handoff criteria candidates:

- Action Interception Boundary is implemented and verified in a future gate.
- capability isolation boundary is defined for shell, network, provider,
  remote write, credential/env, and filesystem scope.
- intercepted action log is externally verifiable or Aegis-controlled outside
  executor authorship/control.
- no-op executor action count behavior is verified.
- unintercepted action cannot become `CLEAN`.
- command enumeration alone cannot grant shell/network/provider authority.
- live executor hard blockers have been explicitly satisfied by future tests
  and verify replay behavior.

Phase 6B-T remains separate from Phase 9. Phase 6B-T True External Unaided Run
v0 is not claimed complete by this document and remains:

```text
FUTURE_MILESTONE
```

## 15. Review gate result candidates

If this planning gate adds only this document, includes the required scope
items, and avoids forbidden implementation, the candidate status is:

```text
PASS_READY_FOR_USER_REVIEW_GATE
```

If the change includes out-of-scope files or implementation work, the candidate
status is:

```text
NEEDS_SCOPE_FIX_BEFORE_REVIEW_GATE
```

If the change introduces provider/API/env/network/model calls, secrets,
release/deploy/publish behavior, tracked `.aeg/`, or tracked `.env`, the
candidate status is:

```text
BLOCKED
```

If recommended tests are not run, the status must be reported as
`NOT_CHECKED` and must not be promoted to pass on test evidence.
