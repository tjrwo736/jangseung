# Aegis Architecture v0

This document defines the Day-0 architecture boundary for Aegis. It is a
bootstrap architecture, not a runtime implementation.

## Purpose

Aegis is a standalone, portable governed coding-agent runtime. Its architecture
starts from governance semantics rather than provider integration. The system is
intended to preserve evidence-first operation, risk-proportional gates, a single
CLI entry point, and folder-local state.

## Architectural Principles

- The executor is not the source of truth.
- Repository state and validation evidence outrank executor self-report.
- Risk controls should scale with the blast radius of an action.
- Local project state should live under a folder-local `.aeg/` directory.
- Core runtime behavior should be usable without Slack, GitHub API automation,
  OpenAI runtime, Claude runtime, Gemini runtime, DRA, Hermes, or Agent Civitas.
- Main merge, release, publish, deploy, provider integration, and autonomous
  execution require explicit user-gated scope.

## Initial Module Boundaries

The Day-0 source layout reserves module areas without implementing behavior:

| Path | Boundary |
| --- | --- |
| `src/cli/` | Future single CLI entry point and command contracts. |
| `src/classify/` | Future risk and task classification logic. |
| `src/law/` | Future governance rules, policy evaluation, and gates. |
| `src/agents/` | Future executor abstractions, without provider implementations in v0. |
| `src/evidence/` | Future evidence capture, validation, and reporting contracts. |
| `src/state/` | Future folder-local `.aeg/` state contracts. |
| `tests/` | Future tests for contracts and behavior. |

These directories are placeholders only. Bootstrap v0 does not define Python
packages, executable commands, provider adapters, or model-backed execution.

## Runtime Shape

The intended runtime shape is:

```text
user intent
  -> single Aegis CLI
  -> classification
  -> governance and risk gates
  -> bounded execution
  -> evidence capture
  -> validation report
  -> user-gated decisions where required
```

This shape is a design boundary. No autonomous loop or model-backed executor is
implemented in Repo Bootstrap v0.

## Local State

Future Aegis runtime state should be folder-local under `.aeg/`. That directory
is local operational state and is ignored by Git. A future scoped task should
define the state schema before any command writes to it.

Expected future state categories may include:

- run metadata
- evidence packets
- gate decisions
- validation summaries
- local runtime cache

Bootstrap v0 creates no `.aeg/` directory and commits no local state.

## Evidence and Validation

Aegis completion claims should be backed by direct evidence:

- workspace path confirmation
- Git branch and status
- changed files
- tree summary
- validation output
- secret-like scan
- forbidden-scope scan

Reported-only evidence is not sufficient by itself. Not-checked evidence is not
a pass. DRA or other executor self-report is input to review, not the source of
truth.

## Forbidden Scope in Bootstrap v0

Repo Bootstrap v0 does not implement or connect:

- `aeg init`
- `aeg doctor`
- `aeg run`
- `aeg verify`
- OpenAI, Claude, or Gemini providers
- OpenAI API calls or any model API calls
- model-backed executor
- autonomous loop
- GitHub API automation
- Slack integration
- DRA integration
- Hermes integration
- release, publish, or deploy flow
- secret, token, API key, or actual `.env` value handling

## Day-1 Readiness

Day-1 work can begin from this repository by defining contracts before behavior:

1. CLI command contract.
2. Local `.aeg/` state contract.
3. Evidence packet contract.
4. Risk classification contract.
5. Validation strategy.

The safe default for ambiguous or high-risk actions remains:

```text
hold_current_state
```
