# Jangseung 0.3.0 release notes

Korean original: [release_0.3.0.md](release_0.3.0.md)

This release reduces approval fatigue, widens protection, and adds operating tools. 0.2.2 was not released on its own; it is part of this release ([0.2.2 notes](release_0.2.2.en.md)).

```bash
python -m pip install --upgrade jangseung
aeg install          # run again to register the session start check
```

If you use the plugin, update the plugin. The session start check is part of the plugin.

## Decisions that got looser

Up to 0.2.2 Jangseung asked about the following. It no longer asks. Each change was decided by measuring real Claude Code behavior.

### Multiple commands and status commands are allowed

- A line joined with `;`, `&&` or `||` is allowed when every part fits the read grammar: `ls -la; pwd`, `cat README.md && pwd`, `git status && git diff`, `cd src && ls`.
  - Each part is judged in the folder where it will actually run. `cd` is followed only when the whole line is joined with `&&` alone. It is not followed when the folder name has leading or trailing spaces or ends with a dot.
  - A part that prints file contents, such as `git diff`, is rewritten to leave out secret files before it runs.
  - If any part reads a secret file, the line is deny.
- Commands that only print status are allowed: `date`, `true`, `false`, `sleep 1`, `whoami`, `uname -a`, `which python`, `command -v git`, `cd src`, and the exact version-check form of known programs (`python --version`, `node --version`, `java -version`).
  - A version check accepts only one fixed form per program. `python version` runs a file named `version`, `npm version` changes package.json, and `pytest -v` runs the tests. `pytest --version` also reads and runs conftest.py, so pytest was left out. Runners that hand off to another program named by a project file were also left out (yarn's `yarnPath`, cargo and rustc's `rust-toolchain.toml`, dotnet's `global.json`, go's `toolchain`, npm and pnpm's `packageManager`, plugins for poetry, pdm and composer).
  - Version and status commands are allowed only when the program found on PATH is outside the project. If a `.venv` inside the project comes first on PATH, the agent may have replaced the `python` in it, so Jangseung asks.
- These allows apply to Codex and to every Claude Code mode.
- Evidence: we measured that Claude Code runs such lines on its own when Jangseung does not answer (`default`, `acceptEdits`). Jangseung picks out and blocks only the lines that read secret files.

### Lines that join run commands are also left to the host

A line that joins only run commands left to the host and read commands, such as `git add -A && git commit -m wip` or `npm install && npm test`, is left to the host's approval flow. In a real session the host asked for approval, saying the line "contains multiple operations". If the line contains `cd` or a git form that prints contents, it is not left to the host. The host runs such reads on its own.

### Commands are left to the host in `acceptEdits` mode too

0.2.x left run commands to the host only in `default` mode. On Claude Code 2.1.316 (Windows), we ran 33 run commands (`git add`, `git commit`, `pytest`, `npm test`, `cargo build`, `python tool.py` and others) once each in `acceptEdits` mode. All of them asked for approval. So `acceptEdits` is now delegated too.

We also confirmed that `acceptEdits` runs file commands such as `rm`, `mv`, `cp`, `sed -i` and `echo >` without asking. File commands are not left to the host in any mode.

## New features

### `aeg allow-once` — allow once

```bash
aeg allow-once "docker compose up -d"
```

This allows, once, the command whose text matches what a person typed. It expires after 10 minutes (60 minutes at most) or after one use. In Codex the hook cannot ask a person, so Jangseung denies commands it cannot prove safe. This lets a person allow such a command once without opening the whole prefix.

- It opens only what `allow_commands` would open. Secret files, Jangseung settings and targets outside the project stay blocked. In a session that wrote content containing a secret file name, Jangseung asks again.
- The agent cannot run it. The file stores only a hash of the command.
- It is used only when the command runs in the project folder itself. The same `pytest` runs a different conftest in a subfolder. It also tells shell tools apart (`--tool PowerShell`, default `Bash`, always `Bash` in Codex).
- The allow is consumed before the answer is sent. If it cannot be consumed, the command is not allowed.
- The message for a blocked command now mentions this method.

### Session start check

`aeg install` and the plugin also register a `SessionStart` hook. When a session starts, it reports in one line if any of these holds:

- Jangseung's PreToolUse hook is not registered
- The registered program is gone (for example, the virtual environment was deleted)
- The hook is not set to block calls when it fails to start
- The policy file cannot be read
- `.aeg` cannot be written

If nothing is wrong, it prints nothing. It does not block the session. If the whole hook setup is deleted, the check is deleted with it, so that case is not reported. It is not registered in Codex.

### Team-shared protection policy `.jangseung/policy.json`

This file is committed to Git and can hold only `protect_paths`. If it has any other entry or is damaged, Jangseung cannot tell which paths it meant to protect, so it protects every path. Until a person fixes it, every file change by the agent is blocked, and host delegation and automatic allow for file operations are turned off. The agent cannot write to this folder.

```bash
aeg policy add --shared --protect infra/
```

### `aeg policy suggest`

Reads the records and shows frequently asked commands as `aeg policy add --command` lines. It does not write them. The records hold only the program name, so `terraform plan` shows up as `terraform`. Approving that prefix would also open `terraform destroy`. So it does not suggest programs with dangerous subcommands (`terraform`, `docker`, `git`, `aws`, `npm` and others), or interpreters, shells and network tools.

### `aeg evidence archive-hooks`

Moves an undamaged ledger to `.aeg/archive/` and starts a new chain. The first record of the new chain stores the moved file's record count, last hash and SHA-256, which links the two files. A damaged ledger must first be fixed with `repair-hooks`. A person runs this command.

### More presets

`aeg policy preset rust | go | jvm | dotnet`.

## Wider protection

The following were added to the review tier (ask in `default` and `acceptEdits`, deny in other modes and in Codex).

- Task runners and test settings: `justfile`, `Taskfile.yml`, `tox.ini`, `noxfile.py`, `pytest.ini`, `lefthook.yml`
- Build and dependency files for other languages: `Cargo.toml`, `build.rs`, `go.mod`, `go.work`, `build.gradle(.kts)`, `settings.gradle(.kts)`, `pom.xml`, `Gemfile`, `Rakefile`, `composer.json`, `CMakeLists.txt`, `*.cmake`, `meson.build`, `build.zig`, `deno.json`, `bunfig.toml`, `.yarnrc.yml`
- JavaScript settings that run as code: `*.config.js/cjs/mjs/ts/cts/mts`, `.eslintrc.js`, `.babelrc.js`, `.prettierrc.js`, `gulpfile.*`, `gruntfile.*`
- Settings that run commands when a folder is opened: `.vscode/tasks.json`, `.vscode/settings.json`, `.vscode/launch.json`, `.devcontainer/`
- Others: `compose.yaml`, `docker-compose.yaml`, `sitecustomize.py`, `usercustomize.py`, `netlify.toml`, `vercel.json`
- Agent instruction files: `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `.clinerules`, `.claude/commands/`, `.claude/agents/`, `.claude/skills/`, `.cursor/rules/`, `.github/copilot-instructions.md`, `.github/instructions/`, `.gemini/`. These files get their own message.

`.claude/commands/` and the like had been left open since 0.1.5 as folders the agent writes. To keep letting the agent write them without asking, open them with `aeg policy add --path .claude/commands`.

## Approval fatigue measurements

We ran the same command lists on 0.2.1 and 0.3.0 and compared them (hook decisions, Claude Code `default` mode).

| Set | 0.2.1 | 0.3.0 |
|---|---|---|
| 50 everyday commands (first list), Claude Code | allow 15, delegated 23, ask 9, deny 3 | allow 18, delegated 24, ask 5, deny 3 |
| Same list, Codex | allow 15, deny 35 | allow 18, deny 32 |
| 50 everyday commands (second list), Claude Code | ask 21 | ask 9 |
| Same list, Codex | deny 44 | deny 33 |
| First 30 of the second list, `acceptEdits` | ask 30 | ask 5, delegated 22, allow 3 |
| 15 direct attacks, 64 obfuscations, 48 destructive commands | `allow` or delegated 0 | `allow` or delegated 0 |

## Check results

- Automated tests: all passed on Windows, Python 3.14 (1839 passed, 20 skipped). The new tests are in `tests/test_new_features_0_3_0.py`.
- Real sessions (Claude Code 2.1.316 `claude -p`, Windows, loaded as a plugin, once each, code before the fixes from the independent review):
  - `ls -la; pwd`, `git status && git diff`, `date`, `python --version`: ran.
  - `cat .env && pwd`: blocked, no value exposed.
  - `git add -A && git commit -m wip` (`default`), `git add -A` (`acceptEdits`): the host asked for approval, so they did not run.
  - Editing `CLAUDE.md` (`default`, `acceptEdits`): asked, and with no person to approve, the file did not change.
  - Project with a damaged policy file: the session start check message appeared.
- Independent review: a separate agent of the same model reviewed the changes aggressively. Findings and actions:
  - High: the version-check grammar accepted `program + one word`. So `pytest -v` (runs tests), `python version` (runs a file of that name) and `npm version` (changes package.json) were allowed without asking in every mode and in Codex. A chain where the agent writes a `version` file and runs `python version` went through with no person involved. Fixed so that each program accepts only one exact form.
  - Medium: when the team-shared policy file was damaged, its protection disappeared for Write and Edit. Fixed to protect every path.
  - Low: a `cd` target with leading or trailing spaces or a trailing dot was judged as a different folder, and a one-time allow could be used in a subfolder and with a different shell tool. Both fixed.
  - Low, left as is: `& aeg allow-once x` (PowerShell) and `uvx --from jangseung aeg allow-once x` get ask (deny in Codex), not deny. A line with `;` inside quotes (`ls 'a;b'; pwd`) gets asked.
  - Confirmed with no issue: operator variants in the splitter, `cd` escapes (`.git`, `.aeg`, `..`, junctions), the exclusion conditions in the git rewrite, `date -f .env` (deny), single use of a one-time allow and keeping the rules, blocking writes to `.jangseung/`, 0 internal errors on the new paths.
  - Re-review of the fixes: all four fixes worked as intended, and no decision was weaker than in 0.2.2. It found one remaining path. The version-check list held runners that hand off to a program named by a project file (yarn, cargo, rustc, dotnet, poetry, pdm, composer), and their settings files could be written without asking. We could not confirm whether this actually runs, because the real tools were not available, but we removed them from the list. This last adjustment was not reviewed again.
  - Low, left as is: while the team-shared policy file is damaged, `cd src && ls` is also denied in Codex.
- Not checked: real Codex sessions (including `aeg allow-once`), the approval prompt in interactive sessions, real macOS and Linux sessions, `dontAsk` and `bypassPermissions` modes. There is no external security review.

- Hook call time: about the same as 0.2.1 (the difference in medians measured at the same spot is within measurement error).

The remaining risks are recorded in RR-4 and RR-13 to RR-15 of the [residual risk register](residual_risk.en.md).
