# Aegis Phase 9 Capability Isolation Boundary Scope Plan v0

## 1. Purpose

This document locks the planning scope for the Phase 9 Capability Isolation
Boundary before any live executor, raw shell authority, process execution
authority, network authority, provider/API authority, remote write authority,
deploy, release, publish, external API call, or model call is introduced.

The Capability Isolation Boundary exists to ensure that an executor does not
receive dangerous capabilities in the first place. It is a prevention boundary,
not a post-hoc claim about executor behavior.

The action log answers:

```text
what was done
```

The capability isolation boundary answers:

```text
what the executor was made unable to do
```

Action logging and action boundary evidence remain necessary, but they are not
enough to grant dangerous authority. Before live authority can exist, Aegis
must define which capabilities are denied by construction, which future layer
may grant them, and what proof would be acceptable.

This is a planning gate only. It does not implement capability isolation,
action interception, runtime behavior changes, sandboxing, containers, shell
wrappers, tool wrappers, allowlist enforcement, denylist enforcement, live
executors, model-backed executors, providers, API key loading, environment
loading, network calls, prompt builders, response parsers, multi-step
execution, planners, schedulers, resume behavior, recovery behavior, telemetry,
release, publish, deploy, or external integrations.

The current canonical baseline is:

```text
PHASE9_ACTION_BOUNDARY_SCAFFOLD_PHILOSOPHY_LINEAGE_MAIN_SMOKE
```

The latest completed status is:

```text
PASS_PHASE9_ACTION_BOUNDARY_SCAFFOLD_PHILOSOPHY_LINEAGE_MAIN_SMOKE
```

The safe default remains:

```text
hold_current_state
```

## 2. Non-goals

The following are non-goals for this planning gate:

- sandbox or container implementation.
- shell wrapper implementation.
- tool wrapper implementation.
- allowlist or denylist enforcement implementation.
- live executor implementation.
- model-backed executor implementation.
- provider implementation.
- API key or environment loading implementation.
- network call implementation.
- prompt builder or response parser implementation.
- multi-step execution, planner, scheduler, resume, or recovery
  implementation.
- action interception implementation.
- raw shell authority grant.
- process execution authority grant.
- network authority grant.
- provider/API authority grant.
- credential or environment access authority grant.
- remote write authority grant.
- deploy, release, or publish authority grant.
- repo outside filesystem write/delete authority grant.
- package install or dependency mutation authority grant.
- telemetry implementation.
- OpenAI, Claude, Gemini, or other provider integration.
- runtime behavior changes.
- new checker, report, manifest, or runtime artifact systems.

This document only records scope, default-deny authority expectations, future
evidence candidates, future replay candidates, future test candidates, and hard
blockers.

## 3. Capability Categories

Future Capability Isolation Boundary design must cover at least these
capability categories:

- raw shell authority: direct access to an unrestricted shell or shell-like
  command surface.
- process execution authority: ability to spawn child processes, invoke
  interpreters, run binaries, or execute scripts.
- network authority: ability to initiate outbound or inbound network activity,
  including SDK calls that use the network.
- provider/API authority: ability to invoke provider SDKs, model APIs, external
  APIs, or provider-backed runtimes.
- credential/env access authority: ability to read credentials, tokens,
  process environment values, `.env` files, secret stores, or secret-like
  configuration.
- remote write authority: ability to write to remote services, repositories,
  APIs, queues, buckets, issue trackers, chat systems, or other external
  systems.
- deploy/release/publish authority: ability to deploy, release, publish, tag,
  upload artifacts, or trigger distribution.
- repo outside filesystem write/delete authority: ability to write, delete, or
  mutate files outside approved repository roots.
- package install / dependency mutation authority: ability to install packages,
  update lockfiles, mutate dependency metadata, or alter runtime dependencies.
- telemetry authority: ability to emit usage, traces, logs, metrics, events, or
  other runtime data to external or persistent telemetry sinks.

These categories are scope categories only. They do not grant authority and do
not implement enforcement.

## 4. Default Authority Matrix

The default authority matrix is deny by default, false by default, and on hold
by default.

```text
raw_shell_authority_granted = false
process_execution_authority_granted = false
network_authority_granted = false
provider_authority_granted = false
remote_write_authority_granted = false
deploy_release_publish_authority_granted = false
credential_env_access_authority_granted = false
repo_outside_write_authority_granted = false
package_install_dependency_mutation_authority_granted = false
telemetry_authority_granted = false
```

No default false value may be interpreted as proof that a capability was
securely isolated. Default false is a safe planning stance. A future CLEAN
judgment would require verifiable isolation evidence, not absence of observed
use.

## 5. Command Enumeration vs Capability Isolation

Command enumeration means attempting to secure action interception by matching,
allowing, or denying command strings.

Required principles:

```text
Action interception cannot be secured by enumerating dangerous command strings.
Action boundary must be based on capability isolation, not only command matching.
Enumerate is not enough; isolate is required.
Command denylist alone is not sufficient to grant shell/network authority.
NO_MATCHED_DANGEROUS_COMMAND != ACTION_BOUNDARY_CLEAN.
```

Command enumeration is insufficient as a trust boundary because commands can be
constructed dynamically, hidden through encoding or indirection, delegated to
child processes, moved into scripts, executed through language runtimes, or
performed through SDKs without a dangerous-looking command string.

Command matching may become advisory metadata in a future design, but command
matching alone cannot authorize raw shell authority, process execution
authority, network authority, provider/API authority, remote write authority,
deploy/release/publish authority, credential/env access authority, or telemetry
authority.

## 6. Isolation Mechanism Candidates

Future implementation gates may evaluate these candidates. This document does
not implement any of them:

- no raw shell by default.
- explicit tool surface.
- tool wrapper.
- sandbox/container.
- filesystem allowlisted roots.
- network disabled by default.
- provider authority disabled by default.
- remote write disabled by default.
- deploy/release/publish disabled by default.
- credential/env access disabled by default.
- read-only command lane candidate.
- future opt-in gate candidate.

Open questions for a future implementation gate:

- Which layer owns capability isolation and how is it kept outside executor
  authorship/control?
- Which capabilities are unavailable by construction rather than detected after
  the fact?
- Which filesystem roots are readable, writable, or denied?
- How is network authority disabled by default and enabled only through an
  explicit future opt-in boundary?
- How are provider/API calls denied by default before provider and action
  boundaries are implemented and verified?
- How are remote write, deploy, release, and publish capabilities blocked by
  default?
- How is credential/env access denied or mediated without recording secret
  values?
- What externally verifiable proof can be replayed without trusting executor
  self-report?

## 7. Trust Boundary

Executor self-report is `reported_only`.

An executor statement such as "I did not use authority" or "I did not perform a
dangerous action" is not a judgment basis.

Candidate judgment bases for a capability boundary are only:

- Aegis-controlled isolation layer.
- externally verifiable isolation proof.

If isolation proof is unavailable, the candidate status is not `CLEAN`. The
candidate status is `NOT_CHECKED` or `BLOCKED`.

Required trust-boundary statements:

```text
executor self-report = reported_only
reported_only is not judgment basis
executor-reported no-authority is not judgment basis
executor-reported no-action is not judgment basis
capability boundary judgment requires Aegis-controlled isolation or externally verifiable isolation proof
missing isolation proof != CLEAN
```

## 8. Relationship to Action Boundary Scaffold

PR #30 introduced an Action Boundary Scaffold based on metadata, binding, and
verify behavior.

This Capability Isolation Boundary Scope Plan is the next design boundary after
that scaffold. It defines the scope and hard blockers that must exist before
dangerous authority can be granted to any live executor.

Required relationship statements:

```text
multi-action-ready scaffold != multi-action execution implemented
future planner premise != planner implemented
capability isolation scope != capability isolation implementation
```

The PR #30 scaffold has a multi-action-ready list/count/hash structure, but
multi-action execution is not implemented by that scaffold and is not
implemented by this document.

Actual action interception remains not started by this document.

## 9. Status Rules

Future status semantics must preserve these rules:

- capability not implemented != `CLEAN`.
- capability not observed != `CLEAN`.
- unavailable proof = `NOT_CHECKED`.
- bypassable capability = `BLOCKED` or `NOT_CHECKED`.
- if raw shell, network, or provider authority is granted and isolation proof
  is missing, status is `BLOCKED`.
- command enumeration only must not produce `CLEAN`.
- executor self-report only must not produce `CLEAN`.
- missing isolation proof must not be promoted to PASS.

Candidate status mapping:

```text
capability_not_implemented -> NOT_CHECKED
capability_not_observed -> NOT_CHECKED
proof_unavailable -> NOT_CHECKED
proof_missing_with_granted_raw_shell_authority -> BLOCKED
proof_missing_with_granted_network_authority -> BLOCKED
proof_missing_with_granted_provider_authority -> BLOCKED
command_enumeration_only_clean_claim -> INVALID_EVIDENCE
executor_report_only_clean_claim -> INVALID_EVIDENCE
```

## 10. Future Evidence Field Candidates

Future implementation may consider these evidence fields. This document does
not add them to any manifest, report, checker, runtime output, or verify
surface:

- `capability_isolation_version`
- `capability_isolation_enabled`
- `capability_isolation_mode`
- `capability_boundary_status`
- `capability_boundary_source`
- `capability_boundary_trust_boundary`
- `raw_shell_authority_granted`
- `process_execution_authority_granted`
- `network_authority_granted`
- `provider_authority_granted`
- `credential_env_access_authority_granted`
- `remote_write_authority_granted`
- `deploy_release_publish_authority_granted`
- `repo_outside_write_authority_granted`
- `telemetry_authority_granted`
- `capability_isolation_proof_hash`
- `capability_matrix_hash`

Additional future candidates may be needed for package install/dependency
mutation authority, but this document does not define a schema.

## 11. Future Verify Replay Candidates

Future verify replay may consider these checks. This document does not
implement verify replay changes:

- confirm the capability matrix hash.
- confirm the capability isolation proof hash.
- confirm consistency between granted authority and isolation proof.
- mark evidence `INVALID_EVIDENCE` or `BLOCKED` if raw shell, network, or
  provider authority is granted and proof is missing.
- mark evidence `INVALID_EVIDENCE` if command enumeration only produces
  `CLEAN`.
- mark evidence `INVALID_EVIDENCE` if executor-reported capability statements
  alone produce `CLEAN`.

Verify replay must not trust executor self-report as capability proof.

## 12. Future Tests / Acceptance Criteria

Future implementation gates may consider these tests and acceptance criteria.
This document does not add tests:

- default authority flags are false.
- no raw shell authority before capability boundary.
- no process execution authority before capability boundary.
- no network authority before isolation/opt-in boundary.
- no provider authority before provider boundary.
- no remote write/deploy/release/publish authority before explicit boundary.
- no repo outside filesystem write/delete authority before explicit boundary.
- no package install/dependency mutation authority before explicit boundary.
- no telemetry authority before explicit boundary.
- command denylist alone cannot grant shell/network authority.
- executor-reported no-action/no-authority is not judgment basis.
- missing isolation proof is `NOT_CHECKED` or `BLOCKED`, not `CLEAN`.

Candidate acceptance requires proof that dangerous capabilities are unavailable
or mediated by an Aegis-controlled isolation layer. Absence of observed use is
not sufficient.

## 13. Live Executor Hard Blocker

The following hard blockers apply before any live executor receives dangerous
authority:

```text
No live executor may receive raw shell authority before capability isolation is implemented and verified.
No live executor may receive network authority before network isolation/opt-in boundary is implemented and verified.
No live executor may receive provider authority before provider boundary and action boundary are implemented and verified.
No live executor may perform remote write, deploy, release, publish, or external API calls before capability isolation and action boundary are implemented and verified.
```

Additional hard blockers:

- no live executor may receive credential/env access authority before a
  secret-safe credential/env boundary is implemented and verified.
- no live executor may receive repo outside filesystem write/delete authority
  before filesystem roots are isolated and verified.
- no live executor may receive package install/dependency mutation authority
  before an explicit dependency mutation boundary is implemented and verified.
- no live executor may receive telemetry authority before a telemetry boundary
  is implemented and verified.
- no model-backed executor, provider-backed executor, or multi-citizen executor
  may bypass the same capability isolation hard blockers.

## 14. Future Complexity Premise

Complex work remains a future premise only.

This document does not implement:

- planner.
- task decomposition.
- multi-step execution.
- scheduler.
- resume.
- recovery.
- autonomous loop.
- multi-citizen execution.

Danger-unit decomposition may become a future `CLASSIFY` extension candidate,
but it is not implemented here.

Required future complexity statements:

```text
planner is not authorization
multi-action-ready scaffold remains
multi-action execution is not implemented
complex task support is a future premise only
```

Any future planner, scheduler, resume path, recovery path, or multi-step
execution path must remain subject to the same action boundary and capability
isolation boundary. Planning cannot grant authority.

## 15. Scope Lock

This scope plan adds documentation only. It does not change source code, tests,
package metadata, architecture docs, README content, runtime behavior, evidence
formats, manifests, checkers, reports, or verification behavior.

Safe default:

```text
hold_current_state
```
