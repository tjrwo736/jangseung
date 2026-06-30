# Phase 6B External Unaided Run Scope Lock v0

## 1. Phase 6B purpose

Phase 6B is not a public launch. It is a restricted external dogfood run:
one external person, one unaided run.

The purpose is to confirm that a user can read only the current
README/Quickstart, run Aegis in a disposable repository, see the LOW path pass
lightly, and see the HIGH path stop at the user gate. Failure is still useful
if the blocked point can be captured as install, documentation, or doctor
backlog.

## 2. Target user criteria

The Phase 6B user should be one external person who:

- was not involved in building Aegis;
- can use a terminal, Git, and Python at a basic level;
- is willing to follow README/Quickstart without live help;
- can create a disposable local Git repository;
- can redact local paths, repo names, usernames, tokens, secrets, and private
  content before sharing output;
- is not required to run Aegis inside a workplace, private, regulated, or
  production repository.

## 3. Target repo criteria

Use only a disposable sandbox repository. Recommended choices:

- a temporary test repository created by the external user;
- a fresh Git repository containing only a README;
- a user-created sandbox repository with no private or production content.

Do not use:

- real work, private, customer, or production repositories;
- repositories containing secrets, tokens, credentials, or private file content;
- repositories with a tracked `.env` file;
- repositories where company policy restricts external tooling;
- repositories connected to release, deploy, or production workflows.

## 4. Setup/run scenario

The external user should use the current README/Quickstart as the only setup
and run guide. The default candidate flow is:

```sh
aeg --help
aeg doctor
aeg init
aeg doctor
aeg run "fix typo in README"
aeg verify
aeg run "do the thing"
aeg verify
aeg run "merge to main and deploy"
aeg verify
```

No maintainer should provide live correction during the run. If the user gets
stuck, stop the run and capture where the README, install path, command
discovery, or doctor output failed.

## 5. Expected LOW/MEDIUM/HIGH outputs

LOW path, expected from `aeg run "fix typo in README"`:

- `risk_level = LOW`
- evidence status is `CLEAN_CORE`
- `binding_status = BOUND`
- verify command status is `REPLAY_CONSISTENT`
- no user gate is required

MEDIUM path, expected from `aeg run "do the thing"`:

- `risk_level = MEDIUM`
- evidence status is `NOT_CHECKED`
- `binding_status = BOUND`
- verify command status is `REPLAY_CONSISTENT`
- `NOT_CHECKED` is not promoted to PASS

HIGH path, expected from `aeg run "merge to main and deploy"`:

- `risk_level = HIGH`
- evidence status is `NEEDS_USER_GATE`
- a `user_gate_reason_card` exists
- `binding_status = BOUND`
- verify command status is `REPLAY_CONSISTENT`
- no real merge, deploy, release, publish, or production action occurs

## 6. Success criteria

Phase 6B succeeds when:

- one external user can run Aegis using only README/Quickstart;
- the target repository is disposable and contains no secrets or private
  content;
- the LOW and HIGH contrast is directly observed;
- HIGH does not false-accept;
- `.aeg/` remains local runtime state and is not tracked by Git;
- no provider, network, API key, model-backed executor, or autonomous loop is
  required;
- any friction is minor documentation polish rather than a blocker.

## 7. Failure/friction capture criteria

Capture failures and friction as backlog if the user hits:

- command discovery problems;
- install or PATH ambiguity;
- confusing `aeg doctor` output;
- confusion about `REPLAY_CONSISTENT`;
- README/Quickstart gaps;
- inability to initialize or verify in a fresh repository;
- uncertainty about whether `.aeg/` or `.env` should be shared or tracked.

Allowed shared context:

- command execution order;
- selected stdout/stderr snippets from each command;
- `aeg doctor` result;
- `aeg run` result card;
- `aeg verify` result card;
- description of the blocked point;
- non-sensitive OS, shell, and Python version information.

## 8. Privacy/secret redaction boundary

External users must redact before sharing. Use this instruction:

```text
Please hide sensitive paths, usernames, repository names, tokens, secrets, and
.env values before sharing. Do not share private file content, private repo
URLs, raw .aeg/ archives, or logs containing company, customer, or personal
data.
```

Do not request or accept:

- `.env` contents;
- API keys, tokens, passwords, credentials, or secrets;
- private repository URLs;
- private file content;
- raw `.aeg/` directory archives;
- unredacted absolute local paths if the path is sensitive;
- filenames or logs containing company, customer, or personal data.

If a shared snippet accidentally includes sensitive content, delete or discard
the snippet and ask for a redacted replacement. Do not copy secrets into issues,
PRs, commits, docs, chat summaries, or runtime artifacts.

## 9. Forbidden scope

Phase 6B scope lock does not allow implementation work. Do not change:

- Aegis core code;
- `aeg init`, `aeg doctor`, `aeg run`, or `aeg verify` behavior;
- classifier, law, evidence, state, verify, executor, or CLI behavior;
- README or Quickstart content;
- `docs/architecture.md`;
- tests or test fixtures.

Do not add:

- new checkers, manifests, report systems, telemetry, or runtime artifacts;
- OpenAI, Claude, Gemini, or other provider implementation;
- API calls, API keys, model-backed executors, or autonomous loops;
- GitHub API, Slack, DRA, Hermes, release, publish, deploy, or main-merge
  automation.

Do not track `.aeg/`, `.env`, secrets, tokens, or runtime output in Git.

## 10. Go / no-go criteria after Phase 6B

Use exactly one of these outcomes after the external run.

`GO_TO_PHASE_7_CANDIDATE`:

- one external user can run Aegis from README/Quickstart only;
- LOW/HIGH contrast is confirmed;
- HIGH false-accept does not occur;
- `.aeg/` is not tracked;
- no provider, network, API, or model-backed dependency appears;
- friction is only minor documentation polish.

`FIX_DOC_OR_INSTALL_BEFORE_PHASE_7`:

- command discovery or install path blocks the user again;
- doctor messages are insufficient;
- `REPLAY_CONSISTENT` meaning is confusing;
- README/Quickstart remains insufficient for external unaided use.

`BLOCKED_BEFORE_EXTERNAL_CONTINUATION`:

- core command execution fails;
- secret or runtime artifact exposure occurs;
- provider, API, network, or model-backed dependency appears;
- HIGH risk false-accept occurs;
- a real work, private, customer, or production repository is at risk of use.

Safe default remains:

```text
hold_current_state
```
