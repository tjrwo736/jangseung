![Jangseung — the gatekeeper for coding agents](https://raw.githubusercontent.com/tjrwo736/jangseung/main/docs/assets/jangseung-hero.png)

# Jangseung — A shield for AI coding agents

Let Claude Code write your code, but stop dangerous actions before they run.

A jangseung is a guardian post that stood at the entrance of traditional Korean villages to keep bad things out. This tool also stands at that boundary, before an AI agent performs a dangerous action.

[![asciicast](https://asciinema.org/a/6B2AARAZCOKB9snJ.svg)](https://asciinema.org/a/6B2AARAZCOKB9snJ)

A demo of Jangseung blocking dangerous actions and letting normal work through in a real Claude Code session

## Three key points

- **Blocks only what is dangerous**: It stops `.env` leaks, destructive commands such as `rm -rf`, and attempts to turn Jangseung off, before they run. Changes to build and dependency files are put to a person. Ordinary file reads and edits are not interrupted.
- **A record in which tampering can be detected**: For every decision it records which files and which programs were the target, and a hash chain detects tampering after the fact. File contents and command arguments are not recorded. It is a local file, so we do not claim it is tamper-proof.
- **Blocks direct calls**: Even if a manipulated instruction tries to read a secret file or run a dangerous command, it is stopped at the tool call stage. It cannot block the path where another command runs code the agent wrote. This is written down in [What we cannot block](#what-we-cannot-block).

Korean (original): [README.md](README.md)

## Doesn't Claude Code already ask when something is risky?

It does. But the default approval falls short in three ways.

- It asks about everything, every time. So you end up turning it off with `--dangerously-skip-permissions`. Then the safety mechanism is gone entirely.
- Not enough of a record is left to audit what the AI did. It is hard to trace "what did it touch yesterday?" later.
- If the rules break down, it just lets things through (fail-open). It is a safety tool, yet when something goes wrong it fails toward the dangerous side.

Jangseung is built the other way. It picks out and stops only what is dangerous (normal work is not interrupted), leaves decision metadata as a record in which tampering can be detected, and when something goes wrong it stops on the safe side (fail-closed).

## What it blocks (and what it does not)

A shield blocks what is in front of it; it does not block people passing by. Jangseung blocks only what is dangerous, by clear criteria.

Blocked (does not run without user approval):

- Risk of secret exposure: reading and modifying `.env` and `.env.*`, private keys (`id_rsa`, `*.pem`, `*.key`, etc.), and credential files (`.ssh/`, `.aws/`, `.npmrc`, `credentials.json`, etc.). This applies regardless of folder depth and letter case. Templates such as `.env.example` are not treated as secrets. However, a folder-wide `Grep` skips them as well.
- Irreversible destruction: `rm -rf`, `git reset --hard`, `git clean -f`, `git checkout -- .`
- Outbound transfer and deployment: `git push`, `npm publish`, `gh release create`, `kubectl apply`, `terraform apply`, `curl`
- Disabling Jangseung: modifying `.claude/settings*.json`, `.codex/`, `.mcp.json`, `.git/`, and running `aeg uninstall`, `aeg policy`
- Files that git executes: modifying paths inside the project that git settings such as `core.hooksPath`, `include.path`, `core.fsmonitor`, `gpg.program` point to (since 0.1.7)
- Tampering with the audit record: an executor writing directly to the `.aeg` directory (only Jangseung's trusted internal recorder writes to the dedicated ledger)
- Out-of-scope access: paths outside the project folder (`/etc`, `~/.ssh`, etc.). This includes read commands whose working folder is outside the project (since 0.1.8)

This decision applies not only when a file is written directly (Write/Edit) but equally when a Bash command, or a PowerShell command in Windows Claude Code, is used to get around it (such as `echo > .env`, `Remove-Item .env`). Even when commands are chained with newlines, parentheses, `&`, or `;`, each command inside is judged separately, and even if the session moves to a subfolder, protected paths stay relative to the project root.

Not blocked (simply passes):

- Reading code, editing ordinary files, modifying the README, reading build configuration files
- Commands that do not change files, such as `ls`, `pwd`, `git status`, `git diff`, `git log`
- Normal work that is not dangerous is not interrupted.

Changes a person must look at (it asks, since 0.2.0):

- Modifying build, CI and dependency files: CI configuration such as `.github/workflows` and `.gitlab-ci.yml`, `Dockerfile`, `pyproject.toml`, `setup.py`, `requirements*.txt`, `package.json`, `Makefile`, `conftest.py`, `.pre-commit-config.yaml`, deployment scripts. The same applies when they are in a subfolder. These files run code at the next install, build, test or commit, so a person confirms the change. Reading is allowed.
- It asks only when the host obtains approval from a person. It answers `ask` only when `permission_mode` in the hook input is `default` (manual approval) or `acceptEdits`. In the other modes (`auto`, `dontAsk`, `bypassPermissions`, `plan`) and in Codex it returns deny, as it did through 0.1.9.
- Basis: On Claude Code 2.1.316 `claude -p` (Windows), we checked once per mode with a hook that answers `ask` to every `Edit`. In `default`, `acceptEdits` and `auto`, the edit did not run in any of them. `auto` was excluded because a classifier can answer in place of a person, and `dontAsk` and `bypassPermissions` were not verified. Whether an approval prompt appears in an interactive session was also not verified.
- `package.json`, `Makefile`, `conftest.py`, `.pre-commit-config.yaml`, and files such as `pyproject.toml` in subfolders, which were not blocked through 0.1.9, are newly included. To keep letting them be modified automatically, a person allows them with `aeg policy add --path <file>`.

Execution commands and unclear work (since 0.2.0):

- In Claude Code's `default` mode, a limited set of execution commands such as `pytest`, `npm test`, and `python src/app.py` use **the host's normal permission policy**. This is not a Jangseung safety `allow`. An existing host allow rule may let the command run without another question.
- This requires one simple command, an in-project working folder and literal non-protected arguments, and all existing deny gates to pass. Other or missing modes keep `ask`; Codex keeps `deny`. Invalid policy/session state and a secret-name session mark also prevent delegation.
- Unsupported programs, content searches, complex shell syntax, and other unclassified work still request confirmation. Separately trusted commands can be registered in the [project approval policy](#project-approval-policy-since-015).
- `git` commands in a folder without `.git`, and commands that compare folders such as `git diff docs .`, also request confirmation.

## What we cannot block

Jangseung does not say it is "perfectly safe". It states exactly the line it holds.

Jangseung steps in and decides at the moment the AI tries to use a tool, such as writing a file or running a command. So things that do not go through a tool — file contents the AI reads in directly by reference, and other programs that an already allowed command runs internally — are outside this line.

**The most important limit: the write-then-run path.** The agent writes ordinary source files freely. Even if that file is code that reads `.env`, its content is not judged at the time of writing. If a person later allows `python script.py` or `pytest` in the approval prompt, or has put it in `allow_commands`, that code runs. Jangseung does not see what the executed program reads. Actually blocking this path requires an OS-level sandbox, and Jangseung is not a substitute for one.

Since 0.2.0 this path is narrowed in one way only. If the agent writes content containing a secret file name (`.env`, `id_rsa`, `.aws/credentials`, `*.pem`, etc.) to a file that is not a document, a mark is left on that session. In the same session, both `allow_commands` auto-allow and `default` host delegation are held; a person is asked instead (deny in Codex). It looks at names, not behavior. Code that builds the name from fragments, files created by shell commands, and files written in another session are not marked. A person can still approve that request directly. Jangseung also cannot inspect the internals of programs executed under existing host allow rules.

Also, for commands hidden in complex ways, such as variable substitution or nested shells, the target cannot be determined precisely; in this case it requests confirmation instead of passing automatically.

The tools the hook inspects are `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Read`, `Grep`, `Glob`, `Bash`, `PowerShell` on Windows, and Codex's `apply_patch`. `WebFetch` and `WebSearch` are not inspected, and Jangseung does not see content that goes out through these tools. MCP tools and MCP resource reads are inspected only in projects where [MCP protection](#mcp-protection-since-019-opt-in) is turned on. If it is not turned on, MCP tools that run code or read files, and MCP servers that serve files as resources, can hand file contents to the agent without going through Jangseung's decision.

With an install that did not have MCP protection turned on, we checked once per case with a dummy `.env` in real sessions (Claude Code 2.1.316 `claude -p`, Codex CLI 0.166.0 `codex exec`, Windows). In every case where the value was printed, no Jangseung record was left.

- **MCP tools in Claude Code:** In auto mode, and for tools allowed in advance in Manual mode (the mode that asks for approval per tool), the value was printed. Tools not allowed in advance in Manual mode required approval and did not run.
- **MCP resource reads in Claude Code (`ReadMcpResourceTool`):** Even in Manual mode the value was printed without an approval request. Auto mode is the same.
- **MCP tools and `read_mcp_resource` in Codex:** With the `approval_policy=never` setting, the value was printed. This includes `mcp__node_repl__js`.

With 0.1.9 with MCP protection turned on, we checked the same way on Claude Code 2.1.316 `claude -p` (Windows).

- **MCP tools:** Both in auto mode and for tools allowed in advance in Manual mode, approval was required and the tool did not run. No call reached the MCP server, and `ask` was left in the Jangseung record.
- **MCP resource reads:** The result was the same in both Manual mode and auto mode.
- **Allow list:** Tools put in `allow_mcp_tools` ran without approval, and tools not put in it continued to be stopped. The `Read` tool was judged only once, as before.
- **Not verified:** `claude -p` has no person to approve, so `ask` ends as a refusal to run. Whether an approval prompt appears in an interactive session was not verified. Whether it is blocked in Codex was verified only by automated tests and the hook CLI.

If such an MCP server is registered, turn on MCP protection, unregister it, or check the host's approval settings.

Also be aware of the following.

- **Sessions started in a subfolder:** Claude Code reads only the `.claude/settings.json` of the folder where the session was started. If you start `claude` in a subfolder of the project, the Jangseung hook does not run. Start from the project root.
- **The name is the criterion:** Secret decisions are based on file names. A secret-file exclusion is attached to `git diff`, `git show` and `git log -p`, but values committed under a name that is not in the rules are printed.
- **Other hooks that change input:** Jangseung attaches a secret-file exclusion to `Grep` and to `git` output commands. If another hook that emits `updatedInput` is attached to the same tool, this exclusion can disappear.
- **Approved commands:** Shell commands that sweep folders, such as `grep -r`, `rg`, `git grep`, require approval. If a person approves, they read secret files too.

Put differently, Jangseung is a guard at the front door, not CCTV watching every room in the house.

Not hiding these limits is how Jangseung earns trust.

## Support scope

This is the scope based on the current implementation and on actual measurement. Jangseung does not claim to make all of Claude Code or all of Codex safe.

| Status | Scope |
| --- | --- |
| Supported | Runtime environment: verified in real use on Linux/WSL and native Windows |
| Supported | Main PreToolUse hook paths for Claude Code `Write`/`Edit`/`Read`/`Bash` (measured on Linux/WSL and native Windows) |
| Supported (since 0.1.5) | Claude Code `Grep`/`Glob` decisions (verified in a real Windows session), `MultiEdit`/`NotebookEdit` decisions (verified only by automated tests and the hook CLI) |
| Supported (since 0.1.7) | Secret-file exclusion in folder-wide `Grep`: the hook attaches the exclusion through `updatedInput`. The caller's `glob` cannot include them again. `~` and drive-relative paths in `path` are deny (Claude Code 2.1.316, verified in a real Windows session) |
| Supported | Main PreToolUse hook paths for Windows Claude Code `PowerShell`, and target decisions for common PowerShell writes/deletes |
| Supported | Project-local Claude Code install: `aeg install --target claude-code` (default) |
| Supported | `Write`/`Edit` deny when the direct target is a secret file, `.aeg`, or Jangseung's own settings. Since 0.1.5, `Read` deny is narrowed to secret files, `.aeg`, and paths outside the project |
| Supported (since 0.2.0) | Modifying build, CI and dependency files is `ask` in Claude Code's `default` and `acceptEdits` modes, and deny in the other modes and in Codex. Includes `package.json`, `Makefile`, `conftest.py`, `.pre-commit-config.yaml`, and manifests in subfolders (Claude Code 2.1.316 `claude -p`, verified in a real Windows session that a `package.json` edit in `default` mode stops with `ask`. The interactive approval prompt was not verified) |
| Supported (since 0.2.0) | `aeg policy`: adds to the approval policy after a diff confirmation. Calls by the agent are deny |
| Supported (since 0.2.0) | Tolerates notation differences in approved commands: quoted text, a trailing `2>&1`, a leading `cd <folder inside the project> &&` |
| Supported (since 0.2.0) | In a session that wrote content containing a secret file name, approved commands are not auto-allowed. Name-based and can be bypassed |
| Supported (since 0.2.0) | Adds the project-relative path, program name, session ID and input hash to the hook record. Contents and arguments are not recorded |
| Supported (since 0.2.0) | Install as a Claude Code plugin, and install into the personal settings file (`aeg install --scope local`). For the plugin, verified in a real session on Claude Code 2.1.316 `claude -p --plugin-dir` (Windows): allow for an ordinary edit, ask for a `package.json` edit, deny for a `.env` read, and record creation. Marketplace install (`/plugin install`), macOS and Linux, and a real session with the personal settings file install were not verified |
| Supported | Bash deny of writes/deletes to protected paths: includes write/delete targets that can be determined structurally, such as redirects, the heredoc family, `tee`, `cp`, `mv`, `rm`, `dd`, `truncate`, `ln` |
| Supported | PowerShell deny of writes/deletes to protected paths: includes write/delete targets that can be determined structurally, such as `Remove-Item`/`rm`/`del`/`ri`/`erase`, `Set-Content`/`sc`, `Add-Content`/`ac`, `Clear-Content`, `New-Item`, `Rename-Item`, `Out-File`, `Tee-Object`, `>`/`>>`, `Move-Item`/`Copy-Item` |
| Supported (since 0.1.5) | PowerShell auto-allow applies only to commands that pass a narrow read grammar such as `Get-Content`, `Get-ChildItem`, `Test-Path`. Secret files and reads outside the project are deny. File searches that pipe `Get-ChildItem` into `Select-String`, and commands with Unicode whitespace or curly quotes, are not auto-allowed since 0.1.7 |
| Supported | Dangerous command deny: `rm -rf`, `git reset --hard`, `git clean -f`, `git checkout -- .`, `git push`, publish and deploy commands (`npm publish`, `gh release create`, `kubectl apply`, `terraform apply`, etc.). Applies even when the command is specified by path or wrapped with `git -C` or `bash -c` |
| Supported | Normal file work allow: clearly safe reads/writes/edits inside the repo are not interrupted |
| Supported | Target-aware decisions for Codex `apply_patch` tool calls: deny for protected paths, allow for normal paths (measured, including native Windows hook exit code handling). Since 0.1.8, files inside the project get the same decision even when written as absolute paths (Codex CLI 0.166.0, verified in a real Windows session) |
| Supported | Project-local Codex install: `aeg install --target codex` |
| Supported (since 0.1.9, opt-in) | MCP protection: `aeg install --mcp` adds a separate hook entry. MCP tool calls and MCP resource reads require approval in Claude Code and are deny in Codex. Only tools written in `allow_mcp_tools` in `.aeg/policy.json` pass. Arguments are not inspected (Claude Code 2.1.316, verified in a real Windows session. Codex verified only by automated tests and the hook CLI) |
| Supported (since 0.1.2) | Codex removal: `aeg uninstall --target codex`; preserves other hooks and TOML settings/comments, with diff confirmation and backup |
| Supported (since 0.1.2) | Limited shell reads of ordinary files inside the project: `cat`, `head`/`tail`, output-only `sed -n`, `rg --no-config`, `Get-Content`, and simple output pipelines |
| Supported (since 0.1.7) | Secret-file exclusion in `git diff`, `git show`, `git log -p`: both tracked files and history. Object IDs are interpreted only as commits (Claude Code 2.1.316, verified in a real Windows session. For Codex CLI 0.166.0, `git diff` and `git log -p` were verified in a real Windows session) |
| Supported (since 0.1.5) | Auto-allow of commands that do not change files: `ls`, `pwd`, `echo`, `grep`, `wc`, `test`, read-only `git` (`status`, `diff`, `log`, `show`, `blame`, `branch` listing, etc.). Since 0.1.7, `git` only when the working folder or a parent folder has `.git`. Since 0.1.8, all of these commands are deny when the working folder is outside the project |
| Supported (since 0.1.5) | Project approval policy: approve paths and commands with `.aeg/policy.json`. The agent cannot modify this file. Since 0.1.8, approved commands are auto-allowed only inside the project |
| Not supported | Judging the behavior of code written by the agent when an approved command runs it. See [What we cannot block](#what-we-cannot-block) |
| Supported | Escalating `ask`/`defer` to `deny` on the Codex substrate: reflects the measured result that `ask` does not work as an execution-blocking safety net in Codex |
| Partial / under verification | Bash dynamic/obfuscated commands: variable substitution, command substitution, nested shells, `find -delete`/`xargs`, etc. are not auto-allowed when they cannot be determined precisely, and are sent to `ask`/`defer` (escalated to `deny` on the Codex substrate) |
| Partial / under verification | PowerShell dynamic/complex commands: target variables, dynamic command invocation, unsupported cmdlets, and complex pipelines are sent to `ask`/`defer` without claiming precise determination |
| Partial / under verification | `apply_patch` quoted path handling: symmetric quotes are normalized and then judged; ambiguous input such as asymmetric quotes, mid-path quotes, or an empty path is fail-closed deny |
| Partial / under verification | macOS: tester verification in progress (awaiting results) |
| Not supported (roadmap) | Scanning for actual secret values inside file contents: decisions are currently based on path and intent |
| Not supported | Structural parsing of PowerShell write/delete commands (e.g. `Remove-Item`) that arrive in Codex under the `Bash` tool name. Limited `Get-Content` reads are supported since 0.1.2 |
| Not supported | Content read directly into the model context without going through a tool call, such as `@` file references |
| Not supported | Tracking every action of subprocesses that an already allowed command runs internally |
| Not supported | Global install: installing into `~/.claude` or `~/.codex` is not supported |
| Supported | Public PyPI distribution: `python -m pip install jangseung` |
| Not supported | OS-level isolation/sandbox |

## Installation

Jangseung is published on PyPI. Install it with `pip`.

```bash
# Create a virtual environment (needed especially on macOS and recent Linux distributions — installing directly into the system Python may be blocked)
python -m venv venv
source venv/bin/activate
# On Windows (PowerShell): venv\Scripts\Activate.ps1
pip install jangseung
```

After installation the `aeg` command is available. You must activate this virtual environment each time you use the `aeg` command afterward. Now move to the project where you want to attach the hook and register it.

Existing users: activate the virtual environment where Jangseung was installed, then update. 0.1.2 includes limited shell document reads and the Codex hook removal fix. 0.1.3 includes settings preservation on install/uninstall and record stability fixes. 0.1.5 includes security bypass fixes. 0.1.6 includes the fix for upgrading old-style hooks. 0.1.7 includes fixes for defects where secret values were printed through search and shell read commands and programs were run through `git` commands. 0.1.8 includes fixes for the defect where `git` commands in folders outside the project were auto-allowed and for over-blocking of `apply_patch` absolute paths. 0.1.9 includes [MCP protection](#mcp-protection-since-019-opt-in), which you turn on by choice. 0.2.0 changes build file decisions, the approval policy command, and record contents, and removes the `aeg run`, `aeg verify`, `aeg init` commands. What changed and what to check when upgrading are in the [0.2.0 release notes](docs/release_0.2.0.md).

```bash
python -m pip install --upgrade jangseung
```

**After upgrading to 0.1.5 or later, run `aeg install` again in each project (`aeg install --target codex` for Codex).** It updates the registered hook's command, inspected tool list, and block-on-failure setting to the latest. Hooks that 0.1.4 or earlier registered in the form `python -m src.cli hook-run` continue to make decisions through a compatibility module from 0.1.6 on, but they look for project files first. If `src/cli.py` exists, that file decides instead of Jangseung, and if `src/__init__.py` exists, the hook fails to start. The agent can create these files too, so the hook must not be left in this form. New inspected tools are also not applied. Hooks in this form failed to start in 0.1.5, and Claude Code let tool calls through as they were. You can check with `aeg doctor --hooks`. Details are in the [0.1.6 release notes](docs/release_0.1.6.md) and the [0.1.7 release notes](docs/release_0.1.7.md).

```bash
cd /path/to/your-project
aeg install
```

The default target is Claude Code. Written explicitly, it is as follows.

```bash
aeg install --target claude-code
```

`aeg install` for the Claude Code target checks the following and proceeds.

- Registers the Jangseung PreToolUse hook in `.claude/settings.json` in the project folder. **Only project-local is supported** — global (`~/.claude`) install is not supported in this version.
- If `.claude/settings.json` already exists, it is merged. Other hooks and settings already registered stay as they are, and only the Jangseung hook is added. If it is already registered, only that entry is updated to the latest form.
- Sets `"onFailure": "block"` on the hook. This setting keeps a tool call from running as-is when the hook fails to start or exits abnormally, and it works on Claude Code v2.1.295 or later.
- Before writing, it shows the change as a diff and asks for confirmation (`y/N`). In an automation environment that has already approved, you can skip the confirmation with `--yes`.
- Before writing, it backs up the existing file as `settings.json.aegis-backup-<timestamp>`.
- Since 0.1.3, after confirmation it also prepares the project's `.aeg/` record folder. A new folder gets an internal `.gitignore`; existing records and the project's `.gitignore` are not changed. The settings file is replaced atomically with a completed temporary file.
- Since 0.2.0, the hook command records the `aeg` of the interpreter that ran `aeg install`. It looks on PATH only when that interpreter has no `aeg` script. Through 0.1.9 it looked on PATH first, so even when installing with a virtual environment's `aeg`, a different installation on PATH could be registered.

**If your team shares `.claude/settings.json` through git, install into the personal settings file (since 0.2.0).** The hook command is an absolute path on this PC, so if it is written in the shared file, that path does not exist on other people's PCs.

```bash
aeg install --scope local
aeg uninstall --scope local
```

It registers in `.claude/settings.local.json`. If git does not ignore this file, add it to `.gitignore`. If it is registered in both files, every call is judged twice, and `aeg doctor --hooks` reports this. `--scope` exists only for the Claude Code target. Whether the hook in this file applies to a session started in a subfolder was not verified.

### Install as a Claude Code plugin (since 0.2.0)

You can also use it as a Claude Code plugin, without `pip` and `aeg install`.

```text
/plugin install jangseung --marketplace tjrwo736/jangseung
```

- The hook is attached to every project where the plugin is turned on. Per-project settings files are not changed.
- Python 3.10 or later (`python3` or `python`) must be on PATH. The hook command uses `sh` syntax, so Git Bash is required on Windows. If either one is missing, the hook fails to start, and tool calls are blocked according to the `onFailure: block` setting. This setting works on Claude Code v2.1.295 or later. On a lower version, a hook that fails to start does not block tool calls.
- If the record folder `.aeg/` does not exist, the hook creates it the first time it is called. An internal `.gitignore` is added with it.
- `aeg policy`, `aeg explain`, `aeg doctor`, `aeg evidence`, Codex install, and MCP protection require the `pip` install. If you use only the plugin, edit `.aeg/policy.json` directly.
- If you use the plugin and `aeg install` together, every call is judged twice. Use only one.

The Codex target must be installed explicitly.

```bash
aeg install --target codex
```

**Codex runs only hooks whose trust the user has approved. After installing, until you review and approve this hook in Codex, the hook does not run and blocks nothing.** We verified with `codex exec` on Codex CLI 0.156.0 that the hook does not run before approval.

The Codex target install adds a `[[hooks.PreToolUse]]` command hook to `.codex/config.toml` in the project folder and records `aeg hook-run --substrate codex` in the hook command. Only when this explicit substrate value is present does Jangseung escalate boundary cases whose internal decision is `ask`/`defer` to `deny`. `allow` and existing `deny` decisions are not changed.

Since 0.1.3, the Codex install also merges with a TOML parser while preserving existing settings and comments, and does not modify invalid settings. It also handles an existing `PreToolUse = []` or inline array. If the hook is already installed in the latest form but `.aeg/` does not exist, run `aeg install --target codex` again (`aeg install` for Claude Code); after confirmation it prepares only the record folder without changing the settings.

Note: this change is a narrow measure to compensate for the problem that `ask` does not work as an execution-blocking safety net in Codex. Codex hook trust/review behavior is handled by Codex, and full Codex support, including quoted path bypasses, still needs separate re-verification in real use.

In a real session on Codex CLI 0.166.0 (Windows), we verified `apply_patch` decisions, the `.env` exclusion in `git diff` and `git log -p`, and blocking of a `workdir` outside the project. The `Bash` input the hook receives is the command and the working folder. It does not see the `tty` and `shell` options of `exec_command`, or `write_stdin`. MCP tools registered in Codex and `read_mcp_resource` are inspected only in projects where [MCP protection](#mcp-protection-since-019-opt-in) is turned on.

To remove from Claude Code, do the reverse:

```bash
aeg uninstall
```

`aeg uninstall` finds and removes only the hook that Jangseung added in `.claude/settings.json`. It does not touch other hooks or other settings entries. This too asks for confirmation after a backup.

For Codex removal, run it matching the install target (requires 0.1.2 or later).

```bash
aeg uninstall --target codex
# When specifying it from a different working folder:
aeg uninstall --target codex --path /path/to/your-project
```

It removes only the Jangseung command hook from `.codex/config.toml` and preserves other hooks, settings and comments. TOML that is invalid or has an unexpected structure is not modified, and an error is shown. `tomlkit` is used as a runtime dependency to preserve TOML structure and comments. The default `aeg uninstall` still targets Claude Code.

If the removal command itself is run as an AI tool call, Jangseung may block it, so the user should run removal in a regular terminal. `aeg uninstall` is a command that unregisters the hook; it does not delete the Python package.

### MCP protection (since 0.1.9, opt-in)

The default install does not inspect MCP tools or MCP resource reads. Turn it on only in projects that need it.

```bash
aeg install --mcp
aeg install --target codex --mcp
```

- It registers one more hook entry for MCP, separate from the existing hook. The existing entry is not changed.
- When it is on, MCP tool calls and MCP resource reads (Claude Code `ReadMcpResourceTool`, Codex `read_mcp_resource`) ask for approval every time in Claude Code and are blocked in Codex. This is because Codex does not enforce `ask`.
- Tools you trust pass without approval if you write their exact names (`mcp__server__tool`) in `allow_mcp_tools` in `.aeg/policy.json`. Patterns such as `*` cannot be used, and resource reads cannot be put in the list.
- Jangseung does not inspect the arguments passed to MCP tools. If a tool in the list reads files or runs code, it can read `.env` too. Do not put such tools in the list.
- **Codex treats the MCP hook as a new hook. It must be approved separately in `/hooks`, and MCP calls are not inspected before approval.** Approval of the existing Jangseung hook is kept as it is. If the existing entry also changes in the install preview (for example, when run from a different virtual environment), that entry must be approved again as well. On Codex CLI 0.166.0 (Windows), we verified that after the MCP entry was added the existing entry kept making decisions, and the new entry did not run until approved.
- To turn it off, run `aeg uninstall --mcp` (`aeg uninstall --target codex --mcp` for Codex). The existing hook remains. `aeg uninstall` removes both entries.
- If you run `aeg install` again after turning it on, the MCP hook is kept and is updated to the latest form along with it.
- Listing MCP resources (Claude Code `ListMcpResourcesTool`, etc.) is not inspected. It is a tool that returns a list of resource names, not file contents.

### Read-only commands (since 0.1.2, extended in 0.1.5)

For ordinary files that actually exist inside the project, reads such as the following are allowed.

```bash
cat README.md
head -n 20 README.md
sed -n '1,80p' README.md
rg --no-config -n example README.md
cat README.md | head -n 20
grep -n example README.md
wc -l README.md
```

The following commands, which do not change files, are also allowed.

```bash
ls -la docs
pwd
git status --short
git diff --stat
git log --oneline -5
git show HEAD
```

`git diff`, `git show`, `git log -p` show results with secret files removed. `git` commands are allowed only when the working folder or a parent folder has `.git`. In a folder that is not a repository, git can run a program through a `config` written by the agent. For the same reason, writes to paths inside the project that git settings point to (`core.hooksPath`, etc.) are blocked, and `allow_paths` does not release them. Commands that compare folders, such as `git diff docs .`, are not auto-allowed.

In PowerShell, `Get-Content` (`gc`, `cat`, `type`), `Get-ChildItem` (`gci`, `dir`, `ls`), `Test-Path`, `Get-Location`, `Select-String` and `Select-Object` output pipelines, and the read-only `git` above are supported. These limited reads are also judged when Codex passes the tool name as `Bash`.

Reading the contents of secret files, `.aeg`, or paths outside the project is deny. When the working folder is outside the project, commands such as `git status` and `ls` with no path written are also deny (since 0.1.8). The following are excluded from this read grammar's auto-allow: wildcard and directory content searches; unquoted `*`, `?`, `[`, including in the search-term position; file searches that pipe `Get-ChildItem` into `Select-String`; Unicode whitespace or curly quotes; paths where the file does not exist; variable/command substitution; nested shells; redirects; unsupported options. `git` is not auto-allowed when `-c`, `-C`, `--output`, or `--ext-diff` is used. `sed` supports only `p` output of a numeric line range, and `rg` requires `--no-config` so that environment configuration cannot insert options that run external programs. Except for the limited execution commands delegated in `default` mode, unclassified operations request confirmation in Claude Code and are blocked in Codex. This assumes the standard tool that corresponds to the command name; it does not verify the internal behavior of replaced executables or shell functions.

### Simple file operations (since 0.2.0)

A narrow grammar for ordinary non-protected files inside the project is auto-allowed. Examples: `mkdir -p docs/new`, `touch notes.txt`, `cp README.md copy.md`, `mv notes.txt moved.txt`, `rm notes.txt`, `echo hello > notes.txt`. PowerShell also supports `Copy-Item -LiteralPath README.md -Destination copy.md`, `Move-Item -LiteralPath notes.txt -Destination moved.txt`, `Remove-Item -LiteralPath notes.txt`, and `Write-Output hello > notes.txt`.

Paths must be simple relative paths made of ASCII letters, digits, `_`, `-`, `.`, and `/` separators. Recursive deletion, directory copy/move, globs, symlinks, junctions, hard links, variables, and chained commands are not auto-allowed. `cp`/`mv` destinations must be file paths, not directories; `rm` accepts one existing ordinary file. Redirects are limited to literal `echo`/`Write-Output` with `>` or `>>` and whitespace on both sides of the operator. Existing protected/review-path deny/ask gates take priority. This is not an OS sandbox preventing files from changing between inspection and execution.

The new grammar and host delegation have automated coverage. File operations were also compared against real Git Bash and PowerShell on Windows. A Claude Code session with these two changes could not run because of the account usage limit; a real Codex session is also unverified.

Aliases of the trusted project root, such as macOS's `/var`, are normalized; links inside the project are still excluded from auto-allow. An unquoted backslash at the end of a Bash command is denied because Bash 3.2 and 5.3 interpret it differently. `aeg explain` reports `ambiguous_shell_syntax` for this case.

### Project approval policy (since 0.1.5)

If the built-in rules block normal work, you can set per-project exceptions with `.aeg/policy.json`. The agent cannot write to `.aeg/` with any tool, so only a person can change this file. `.aeg/` is usually excluded from Git, so this setting applies only to that PC.

Since 0.2.0 you can add entries with a command instead of writing JSON by hand. It shows the change as a diff and asks for confirmation (`y/N`), and it does not write values the hook would ignore. The user should run it in a regular terminal. It is blocked as an agent tool call.

```bash
aeg policy show
aeg policy add --command "pytest" --command "npm test"
aeg policy add --path package.json
aeg policy add --protect infra/ --mcp-tool mcp__github__get_issue
aeg policy preset python   # one of python, node, git
```

`preset` puts a bundle of commonly used commands into `allow_commands`. `python` is `pytest`, `ruff check`, `mypy`, etc.; `node` is `npm test`, `npm run build`, `npx tsc --noEmit`, etc.; `git` is `git add`, `git commit`, `git fetch`, `git switch -c`. **Approved commands run without asking, and most of them run the project's code (tests, scripts, git hooks).** Put in only commands for which it is acceptable to run code written by the agent without confirmation. Do not add a bare interpreter name such as `python`, `node` or `bash`. Any code the agent wrote would then run without a question, and that code can also change `.aeg/policy.json` or turn Jangseung off. What Jangseung blocks is a call visible on the command line, such as `aeg policy` or `python -m jangseung.cli ...`.

```json
{
  "allow_paths": ["pyproject.toml", "requirements*.txt", "tests/fixtures/*.pem"],
  "protect_paths": ["infra/", "*.tfstate"],
  "allow_commands": ["pytest", "python -m pytest", "npm test"],
  "allow_mcp_tools": ["mcp__github__get_issue"]
}
```

- `allow_paths`: allows secret paths and the build and dependency files that are put to a person. However, Jangseung's own settings such as `.aeg`, `.git`, `.claude/settings*.json`, `.codex`, `.mcp.json` are not released. It is reflected in folder-wide `Grep` and git output only when one file rule is allowed as a whole. If you allow `.env` or `*.pem`, they are included. If you allow only part, such as `.env.local` or `tests/fixtures/*.pem`, or allow a folder such as `secrets`, they are excluded, and the allowed files appear when specified directly.
- `protect_paths`: adds protected paths. It takes precedence over `allow_paths`.
- Path rules apply at any depth. A bare file name such as `.env` applies to that name in every folder. To open one file only, write a path such as `config/.env`.
- `allow_commands`: allows a single command whose leading part matches. It can release commands the built-in rules block, such as `git push`, but commands that disable Jangseung, such as `aeg uninstall`, are not released. It does not apply to commands containing `;`, `&&`, `|`, `>`, `$()`, and if the target is a secret file or a protected path, the result stays deny. Since 0.2.0, three notations that do not change the program being run are read past: characters inside quoted text (`git commit -m 'fix(parser): #12'`), a trailing `2>&1`, and a leading `cd <folder that is inside the project> &&`. The `cd` form has conditions. The folder must be written without quotes as a name made of letters, digits, `_` and `-` (`src`, `./packages/api`), and the approved command must contain no file name. `pytest`, `python -m pytest` and `npm test` qualify; `bash scripts/run.sh` and `python tool.py` do not, because after changing folders the same relative path points at a different file. If `CDPATH` is in the environment the hook receives, only a folder that starts with `./` is approved. A `CDPATH` set only in a shell profile is not visible to the hook. If there is `$`, a backtick or a double quote inside the quotes, or a backslash, a curly quote, or `--%` is present with them, or a quote starts in the middle of a word, it is judged strictly as before. This is because the position where a quote ends can differ from shell to shell. Forms such as `pytest | tail` and `git commit -m "$(cat <<'EOF' ...)"` are still not approved. After content containing a secret file name has been written in the same session, even approved commands are put to a person.
- `allow_mcp_tools` (since 0.1.9): the exact names of MCP tools to pass without approval in projects where [MCP protection](#mcp-protection-since-019-opt-in) is turned on. If even one name does not match the format, the whole file is ignored.

If the file is corrupted or has an unknown entry, the whole file is ignored and only the built-in rules apply. `aeg doctor --hooks` reports this state. 0.1.8 and earlier treat `allow_mcp_tools` as an unknown entry, so a file containing this entry is ignored in full.

### Install from source (for development/contribution)

To develop or contribute, clone the repository and do an editable install.

```bash
git clone https://github.com/tjrwo736/jangseung.git
cd jangseung
# Create a virtual environment (needed especially on macOS and recent Linux distributions — installing directly into the system Python may be blocked)
python -m venv venv
source venv/bin/activate
# On Windows (PowerShell): venv\Scripts\Activate.ps1
python -m pip install -e .
```

After that, `aeg install` is used the same way as above.

## Explaining decisions and diagnosing install state

When checking a report of a block, use `aeg explain`, which does not run the actual tool. It calls the same decision function as the real hook, but does not run commands or write `.aeg/` records. Use it in the project directory where the hook will run.

```bash
aeg explain --command "cat README.md" --substrate codex
aeg explain --command "pytest" --substrate codex --json
aeg explain --command "pytest" --permission-mode default --json
aeg explain --file README.md
aeg explain --command "Get-Content README.md" --tool PowerShell
```

`--file` judges a `Read` request, not the file contents. A complete PreToolUse JSON can be passed on standard input to `aeg explain --stdin --substrate codex --json`. So that sensitive content does not remain in shell command-line history, do not write input containing secret values directly on the command line. The output does not include raw input, commands, file paths, or file contents, and arbitrary values attached to validator reason codes are not shown either.

`--permission-mode` applies only to `--command`; omission means a payload without a mode. Host delegation in `default` is shown as `permission_decision: host`, `category: host_permission_flow`. The actual host response is `{}` with no permission decision, not proof of execution by the host.

For example, explaining `pytest` for the Codex target under the current rules shows the following (excerpt).

```text
hook_decision: defer
permission_decision: deny
hook_exit_code: 0
category: unclassified
summary: Safety was not established by the current rules; this is not a finding that the command is dangerous.
```

That is, it distinguishes **a block because it was judged dangerous** from **a block because safety has not yet been established**. It also shows separately why ask/defer maps to deny in Codex. It is not a feature that widens the supported shell commands or the allow policy.

You can also check the project's hook registration state, read-only.

```bash
aeg doctor --hooks --target codex
aeg doctor --hooks --target claude-code --json
aeg doctor --hooks --json  # check both targets
```

It checks the format, substrate and matcher of the registered settings, the block-on-failure setting, whether the executable exists in the current environment, the record folder, PID lock, guard and hook chain, and the approval policy file. It does not modify settings or run executables, and for writability it checks only permission information. Even if it finds a PID lock of an exited process, doctor does not delete it. It also checks the internal rules of `.aeg/.gitignore` and actual tracking-exclusion exceptions. `aeg doctor --json` outputs the existing default diagnostics as JSON, and without `--hooks` it does not require hook registration.

Note: exit code 0 from `explain` means **the explanation completed**, not permission to run. The real hook's exit code is the separate `hook_exit_code` field. Invalid input/fail-closed or a diagnostic failure is 1, and a command usage error is 2. **Do not replace the installed `hook-run` with `explain`.** Trust approval in the real app, global settings, whether the hook is called, and whether the recording device actually writes successfully are not proven by this diagnostic alone (`NOT_CHECKED`).

## Viewing evidence and live hook records

`aeg hook-run` decisions are recorded append-only in `.aeg/hook_ledger.jsonl`. You can view them and verify the chain without writing.

```bash
aeg evidence list --limit 20
aeg evidence list --json
aeg evidence show <hook-record-hash-prefix>
aeg evidence verify-hooks
aeg evidence repair-hooks
```

`list` shows time, decision, tool and target, newest first. `show` is divided into summary, decision, call and integrity sections. View results pass through a credential-shape filter and do not modify `.aeg`. Corrupted rows are shown as `UNREADABLE`.

One record contains the following.

- Decision: substrate, tool name, decision/permission, whether fail-closed, reason code, exit code, hash chain
- Target (since 0.2.0): project-relative paths (`targets`), program names of commands (`commands`, e.g. `git push`, `pytest`), the host's session ID (`session_id`), SHA-256 of the whole input (`input_hash`)

Host delegation is displayed as `HOST` and recorded with `hook_decision: defer`, `permission_decision: host`, and `record_version: hook_decision_record_v2`. This does not record the host's final permission or execution outcome. Normal allow/ask/deny records keep v1; 0.2.0 verifies mixed chains. **0.1.9 and earlier cannot verify or append to a chain containing v2.** Preserve the records and plan ledger handling before downgrading; no automatic conversion or deletion is performed.

Not included: file contents, command arguments and the original command text, raw `tool_input`. Paths outside the project are written only as `<outside-project>`. A program name is written only when it is a short name written without quotes in the command position (24 characters or fewer, at most 3 digits, at most 2 `-`), and otherwise it is written as `<other>`. A Bash command containing a substitution (`$()`, backticks, `$variable`) is written only as `<dynamic>`. Any word of that shape in the command position is recorded, and file names are recorded as they are. If the name itself is a secret, it remains in the record too. Records written by 0.1.9 and earlier have no target fields and are verified as they are.

`aeg run`, `aeg verify`, `aeg init` and run evidence viewing, which existed through 0.1.9, were removed in 0.2.0. Even if `.aeg/ledger.jsonl`, `.aeg/runs/`, `.aeg/config.json` remain, they are not read or deleted.

Even if hook recording fails, the already computed `permissionDecision` and exit code do not change. Instead, `hook_decision_recording_failed` is added to the response reason codes. This is a choice to separate the decision brain from the recorder, so that a recording device failure does not arbitrarily reclassify a normal decision as allow/deny. However, if the existing decision itself is a fail-closed deny, deny is kept as it is.

If recording a host-delegated result fails, a fixed `systemMessage` reports the failure without adding a permission decision. The host permission flow is preserved.

The hook ledger's hash chain is a tamper-evident mechanism for detecting changes to or deletion of intermediate records. Because it is a local file with no external anchor, it is not a tamper-proof store that also proves an attack that deletes the last record and the whole file together.

Since 0.1.3, invalid UTF-8 ledger rows are shown as `UNREADABLE` while other entries can still be viewed. Runs with no artifact are also shown as `UNREADABLE` in the list. Viewing does not fix or rewrite corrupted data.

Since 0.1.5, a hook call checks only the last record and appends. This is so that calls do not slow down as the ledger grows; full chain verification is done by `aeg evidence verify-hooks`. If an intermediate record is corrupted, recording continues and full verification fails. If the last record is corrupted, further recording is refused. Running `aeg evidence repair-hooks` moves everything from the corrupted row to the end into a quarantine file in `.aeg/`, and continues the chain with a recovery record that holds the hash of the quarantined content. The user should run the repair command in a regular terminal. It is blocked as an agent tool call.

When recording, the OS lock on `.aeg/hook_ledger.guard` and the existing PID lock file are used together. It is normal for the guard file to remain; do not delete it. A PID lock of an exited process is recovered at the next recording, but a lock that is running or whose owner is unknown is not taken over. Empty files, invalid PIDs and the like need separate checking after all related processes are stopped. Lock behavior on network filesystems is not guaranteed.

## How it works

Jangseung works as a PreToolUse hook. At the moment the AI is about to make a tool call that writes a file or runs a command, just before it runs, the request is passed to Jangseung. Jangseung judges the request: it blocks if dangerous, passes if normal, and requests confirmation if unclear. However, a hook installed with `--target codex` responds to unclear `ask`/`defer` decisions with `deny`, because it was confirmed that Codex does not enforce blocking on `ask`.

Decisions are deterministic — the same input, the same filesystem state, and the same session marks (`.aeg/session_marks.json`) give the same result.

The limited execution commands in 0.2.0 use host permission rules in Claude Code `default` as described above. This omits the permission decision under the [Claude Code hook contract](https://code.claude.com/docs/en/hooks); it sends neither `allow` nor the wire value `defer`.

Since 0.2.0, the reason returned to the host when blocking or asking starts with a sentence. It states what caused the stop and what a person can do (`aeg policy add ...`, etc.), and the existing reason code is attached after it. The sentence is fixed text and does not contain paths or commands from the input. Path boundary and shell read decisions check the file's actual location and whether it exists. When the basis for a decision is uncertain, it fails on the safe side (block or request confirmation) (fail-closed).

## Requirements / current status

- **Verified on Claude Code and Codex**: On both Linux/WSL and native Windows, we confirmed with real Claude Code sessions and Codex CLI sessions that the main PreToolUse hook paths work correctly. On Windows, we handled separately the differences in how each substrate executes (the form in which Claude Code runs the hook command, exit code handling for Codex deny responses, the PowerShell tool, etc.). Install each with `aeg install --target claude-code` (default) or `aeg install --target codex`. The two substrates differ in part in how decisions are made — in Claude Code it requests confirmation (ask) for unclear operations, but measurement confirmed that in Codex that confirmation request does not work as a safety net that blocks execution, so in Codex unclear cases are blocked more strictly (deny). However, PowerShell write/delete commands passed in Codex under the `Bash` tool name are not yet parsed structurally. Limited `Get-Content` reads are supported since 0.1.2. The 0.1.5 changes were verified by automated regression tests and hook CLI measurement, and the main paths were confirmed in a non-interactive Claude Code 2.1.316 session on Windows. Permission bypass modes, decisions in real Codex sessions, and real Linux/macOS sessions need re-verification.
- **The default policy is hardcoded in the code.** Per-project exceptions can be set with `.aeg/policy.json`.
- **Secret decisions are based on path and intent.** The attempt to write to a file such as `.env` is itself blocked, but there is not yet a feature that scans file contents for actual API key/password values (planned on the roadmap).
- Python 3.10 or later is required.

## Development

This project was developed using Claude Code and Codex. All decision logic was verified repeatedly in real Claude Code / Codex environments, and the support scope and limits written in the README reflect those measured results as they are.

## Reporting security issues

Do not write vulnerabilities in public issues; report them by the method described in the [security policy](https://github.com/tjrwo736/jangseung/blob/main/SECURITY.md).

## License

This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.
