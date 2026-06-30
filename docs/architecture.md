# Aegis Architecture v0

This document defines the Day-1 v0.1 architecture boundary for Aegis. It is a
contract-first runtime spine, not a model-backed executor.

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

## Module Boundaries

The Day-1 source layout keeps the module areas small and explicit:

| Path | Boundary |
| --- | --- |
| `src/cli/` | Single CLI entry point and command dispatch for `init`, `doctor`, `run`, and `verify`. |
| `src/classify/` | CLASSIFY is the heart. This module classifies each task or action as LOW, MEDIUM, or HIGH risk before gates or execution are selected. |
| `src/law/` | LAW selects gate thickness by risk and keeps deterministic STOP precedence. |
| `src/agents/` | AGENTS contains the Day-1 contract-first no-op executor. It does not mutate repository files. |
| `src/evidence/` | EVIDENCE writes and verifies bound packets tied to repo, branch, commit, tree, changed files, risk, and status. |
| `src/state/` | `.aeg/` is folder-local state and ledger. This module owns runtime state and ledger records under `.aeg/`. |
| `tests/` | Contract and behavior tests for classification, law, state, evidence, and verification. |

Day-1 v0.1 defines Python packages and executable commands. It does not define
provider adapters or model-backed execution.

## Runtime Shape

The intended runtime shape is:

```text
user intent
  -> single Aegis CLI
  -> CLASSIFY is the heart: classify task/action risk as LOW, MEDIUM, or HIGH
  -> LAW selects gate thickness by risk
  -> contract-first no-op execution
  -> EVIDENCE writes bound packets
  -> STATE appends .aeg/ ledger records
  -> VERIFY replays deterministic classification and law
  -> user-gated decisions where required
```

This shape is implemented only as a local no-op contract. No autonomous loop or
model-backed executor is implemented in Day-1 v0.1.

## Local State

Runtime state is folder-local under `.aeg/`. That directory is local
operational state and is ignored by Git. Day-1 writes only:

- `.aeg/config.json`
- `.aeg/ledger.jsonl`
- `.aeg/runs/<run_id>/run.json`
- `.aeg/runs/<run_id>/evidence.json`

.aeg/ is folder-local state and ledger: it is the intended home for runtime
state and ledger records, never a committed artifact.

Expected future state categories may include:

- run metadata
- evidence packets
- gate decisions
- validation summaries
- local runtime cache

Day-1 v0.1 creates `.aeg/` only at runtime. No `.aeg/` content is committed.

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

Bound packets should connect claims to concrete repository facts: commit, tree,
changed files, and status. Without those bindings, evidence is only narrative
and cannot carry a gate decision.

## Forbidden Scope in Day-1 v0.1

Day-1 v0.1 does not implement or connect:

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

## Day-1 Runtime Boundary

Day-1 v0.1 defines contracts before mutating behavior:

1. CLI command contract.
2. Local `.aeg/` state contract.
3. Evidence packet contract.
4. Risk classification contract.
5. Validation strategy.

v0.1 minimum cut is Citizen One. It remains an executor stub and
contract-first spine: enough structure to prove the CLI, classification, law,
evidence, state, and verification contracts before adding provider-backed
execution.

The safe default for ambiguous or high-risk actions remains:

```text
hold_current_state
```
