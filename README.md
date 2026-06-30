# Aegis

Aegis is a greenfield project for a portable governed coding-agent runtime.
It carries the governance semantics of Agent Civitas into a standalone
runtime shape, but it is not a copy of Agent Civitas, DRA, or Hermes.

Day-0 status: repository bootstrap only. This repository currently contains
identity, architecture, and minimum project structure for Day-1 bootstrap work.
It does not implement the CLI, providers, model execution, service
integrations, release automation, or autonomous loops.

## Identity

Aegis is built around five day-0 identity points:

- small civilization
- risk-proportional governance
- single CLI
- folder-local state
- evidence-first operation

One-line promise:

```text
the executor is not the source of truth
```

Safe default:

```text
hold_current_state
```

## Source of Truth

The Aegis repository is the source of truth for Aegis runtime behavior,
CLI contracts, local state contracts, tests, and verification results.

Agent Civitas remains governance, memory, evidence, and gate ledger context.
DRA remains an execution worker and evidence return path. User approval remains
the final authority for main merges and high-risk decisions.

Executor reports are evidence, not truth by themselves. Completion claims must
be checked against workspace state, Git state, changed files, validation
results, secret scans, and forbidden-scope scans.

## Day-0 Scope

This bootstrap establishes:

- canonical README
- architecture v0 documentation
- minimum source and test directory layout
- ignore rules for local state, secrets, caches, logs, and editor files
- Day-1 bootstrap boundary

This bootstrap intentionally does not establish:

- `aeg init`
- `aeg doctor`
- `aeg run`
- `aeg verify`
- provider implementations
- model-backed execution
- autonomous loops
- external service automation
- release, publish, or deploy flows

## Project Layout

```text
Aegis/
  README.md
  docs/
    architecture.md
  src/
    cli/
    classify/
    law/
    agents/
    evidence/
    state/
  tests/
  .gitignore
```

Empty directories are kept with `.gitkeep` placeholders until Day-1 work adds
real modules and tests.

## Core Non-Dependencies

Aegis core must not require the following as runtime dependencies:

- Slack
- WSL
- multi-process runtime
- mandatory PR-promotion flow
- Agent Civitas copy
- DRA copy
- Hermes copy
- GitHub API
- OpenAI runtime
- Claude runtime
- Gemini runtime

Provider integrations may be considered only in later, explicitly scoped work.
They are not part of Repo Bootstrap v0 and are not core dependencies.

## Local State Boundary

Aegis is expected to use folder-local `.aeg/` state in future work. The `.aeg/`
directory is local runtime state and must not be committed. This repository
tracks only the contract documentation until a later scoped task defines the
state schema and CLI behavior.

## Day-1 Bootstrap Boundary

The next safe work is Day-1 bootstrap planning and implementation inside this
repository. It should remain small and explicit: define CLI contracts and local
state contracts before adding execution behavior. The safe default remains
`hold_current_state`.
