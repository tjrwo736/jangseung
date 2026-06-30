# Aegis

Aegis is a greenfield project for a portable governed coding-agent runtime.
It carries the governance semantics of Agent Civitas into a standalone
runtime shape, but it is not a copy of Agent Civitas, DRA, or Hermes.
Aegis is a small civilization of coding agents governed by risk-proportionate law.
Zero required external accounts.

Day-1 v0.1 status: contract-first runtime spine. This repository implements a
minimal local CLI, deterministic risk classification, law gates, no-op
execution, evidence packets, folder-local state, and deterministic verification.
It does not implement providers, model execution, service integrations, release
automation, deploy automation, or autonomous loops.

## Identity

Aegis is built around six day-0 identity points:

- small civilization
- risk-proportional governance
- single CLI
- folder-local state
- evidence-first operation
- zero required external accounts

One-line promise:

The executor is not the source of truth.

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

## Bootstrap Scope

Repo Bootstrap v0 established:

- canonical README
- architecture v0 documentation
- minimum source and test directory layout
- ignore rules for local state, secrets, caches, logs, and editor files
- Day-1 bootstrap boundary

Day-1 v0.1 establishes:

- `aeg init`
- `aeg doctor`
- `aeg run "<task>"`
- `aeg verify`
- deterministic LOW / MEDIUM / HIGH intent classification
- deterministic law gates
- contract-first no-op execution
- evidence packets and ledger records under `.aeg/`

This bootstrap intentionally does not establish provider implementations,
model-backed execution, autonomous loops, external service automation, or
release, publish, or deploy flows.

Day-1 v0.1 keeps a single entry point, folder-local state under `.aeg/`, and
zero required external accounts. Aegis does not copy Agent Civitas, DRA, or
Hermes; it discards Slack, WSL, and multi-process plumbing as core
requirements. OpenAI, Claude, and Gemini providers are not core dependencies.

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

The Day-1 modules are standard-library Python and can be exercised through the
repository-local `aeg` launcher or `python -m src.cli`.

```bash
./aeg init
./aeg doctor
./aeg run "fix typo in README"
./aeg verify
```

## Packaging / Install Path v0 Quickstart

This is not a PyPI/public release yet. Install path v0 is for a local checkout
or a GitHub-accessible repository checkout. Provider/network access is not
required for the core loop, and OpenAI/Claude/Gemini accounts are not required.

Local editable install:

```bash
cd /path/to/Aegis
python -m pip install -e .
aeg --help
```

If your environment does not provide `python`, use `python3` instead:

```bash
python3 -m pip install -e .
```

For a disposable local test, you may install inside a temporary virtual
environment instead of your system Python.

Optional local `pipx` install, if `pipx` is available:

```bash
cd /path/to/Aegis
pipx install .
aeg --help
```

Fallback local checkout launcher:

```bash
PATH="/path/to/Aegis:$PATH" aeg --help
```

```bash
/path/to/Aegis/aeg --help
```

Use a disposable sandbox repo for unaided run testing. Aegis writes
folder-local runtime state under `.aeg/`; the target repository must
git-ignore `.aeg/` before running Aegis. Target repositories should also
ignore `.env` and `.env.*`. `.aeg/` is local runtime state. Keep it in the
target repo folder, but do not commit it.

```bash
mkdir -p /tmp/aegis-sandbox
cd /tmp/aegis-sandbox
git init
printf "# Sandbox\n" > README.md
printf ".aeg/\n.env\n.env.*\n" > .gitignore
git add README.md .gitignore
git commit -m "init sandbox repo"
```

Then run the installed `aeg` command in the sandbox repo:

```bash
aeg doctor
aeg init
aeg doctor
aeg run "fix typo in README"
aeg verify
aeg run "merge to main and deploy"
aeg verify
```

Expected contrast:

- LOW task -> `CLEAN_CORE`
- HIGH task -> `NEEDS_USER_GATE`
- `aeg verify` -> `REPLAY_CONSISTENT`
- `.aeg/` remains folder-local and git-ignored
- provider/network access is not required

`REPLAY_CONSISTENT` means Aegis replayed the recorded evidence and binding
deterministically. It is not an external oracle and does not mean the requested
task was actually executed.

If `.aeg/` is not ignored in the target repo, `aeg doctor` will report a
problem. This is expected; fix it by adding `.aeg/` to `.gitignore`.

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
They are not part of Day-1 v0.1 and are not core dependencies.

## Local State Boundary

Aegis uses folder-local `.aeg/` state for runtime records. The `.aeg/`
directory is local runtime state and must not be committed. Day-1 state records
include `config.json`, `ledger.jsonl`, and per-run `run.json` /
`evidence.json` files under `.aeg/runs/<run_id>/`.

## Day-1 Bootstrap Boundary

The next safe work after Day-1 v0.1 is to broaden validation and impact-risk
taxonomy before any mutating executor is introduced. The safe default remains
`hold_current_state`.
