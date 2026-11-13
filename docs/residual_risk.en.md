# Residual risk register

Korean original: [residual_risk.md](residual_risk.md)

This document records in one place **what Jangseung knows it cannot block and has accepted**. It has two purposes.

- Users know exactly where Jangseung draws its lines.
- Reviews converge. A bypass that falls into a class listed here has already been judged, so it is not argued again as a new defect. A bypass not listed here is treated as a defect.

Last updated: 0.3.0. Measurements are on Windows, Claude Code 2.1.316 `claude -p`, Codex CLI 0.166.0. Other host versions and operating systems were not checked.

## How to read

- **Current behavior:** the answer Jangseung actually gives to that request. `ask` means it asks a person; in Codex it becomes `deny`. `pass` means Jangseung does not block it.
- **Evidence:** `measured` means confirmed by running a real session or hook decisions, `test` means fixed by an automated test, `design` means it follows from the structure.

## What is not accepted as residual risk

If any of the following passes in any form, it is a defect. It is fixed, not added to the register.

- A secret file name appears in a command or tool argument **literally**, or in quoted, backslashed, `{a,b}` brace, wildcard, or whole base64/hex encoded form, and the request gets `allow` or host delegation.
- A command on the [README block list](../README.en.md), such as `rm -rf`, `git reset --hard`, `git push`, deploy and publish commands, cloud resource deletion, DB deletion or disk formatting, gets `allow` or host delegation.
- A request that turns off or changes Jangseung itself (`.claude/settings*.json`, `.aeg/`, `aeg uninstall`, `aeg policy`) gets something other than `deny`.
- An error during a decision ends in an answer other than `deny`.
- Something is allowed beyond the scope a person approved (`allow_commands`, `allow_paths`).
- A command the host runs without approval is left to the host (0.2.0's `git stash show` was such a case).
- A one-time allow appears without a person's `aeg allow-once`, is used more than once, or opens secret, Jangseung or target rules.
- `.jangseung/policy.json` opens anything, or the agent can change that file.
- Jangseung opens a folder outside the project or a network path to look inside.

## Accepted classes

### RR-1. Write then run

- **What:** the agent can write ordinary source files. Even if the file holds code that reads `.env`, it is not blocked at write time. If a person later approves `python script.py` or `pytest`, or has put it in `allow_commands`, that code runs.
- **Current behavior:** the write passes. A session that wrote content containing a secret file name gets a session mark, and in that session even commands approved through `allow_commands` are asked of a person again.
- **Why accepted:** blocking everything that is written would make the edit-test loop impossible. The mark is name based, so writing the name in pieces avoids it. This narrows one path; it does not close it.
- **Evidence:** test (`tests/test_approval_fatigue_0_2_0.py`), design.

### RR-2. Names built at run time

- **What:** forms where the file name is built while the command runs, such as `python -c "open(chr(46)+'env')"` and `cat "$(printf '.e%s' nv)"`. Split base64/hex and variables that pass through interpreter code are the same.
- **Current behavior:** `ask` (Codex `deny`). No automatic allow or host delegation.
- **Why accepted:** catching these exactly would need partial interpreters for the shell and each language, and endless variants would still remain. 0.2.2 raised to `deny` only the forms that can be known from the command text alone (wildcards, `{a,b}`, whole encoding).
- **Evidence:** measured (0.2.2 decision survey, 0 `allow` or host delegation among 64 obfuscations), test (`tests/test_competitive_gaps_0_2_2.py`).

### RR-2a. Wildcards not matched and matching limits

- **What:** wildcards are matched against real files only within these bounds.
  - Only folders inside the project are checked. Patterns in the home folder (`cat ~/.ss?/id_*`), other drives and network shares are not matched.
  - Patterns with no letters or digits (`cat *`, `cat .*`) are not matched.
  - Commands that use only names (`ls`, `stat`, `echo`, `test`, `find` with no action, `git status`, `git add` and others) are not matched. They are matched only when the same line has a reading command and a path for the name to flow into it (`xargs`, `$(...)`, variables). In PowerShell only file commands, and listing commands that feed into file commands, are matched.
  - Arguments in pattern positions (`--exclude X`, the first argument of `grep`, `sed` and `jq`) and folders reached through links or junctions are not matched.
  - Limits: per call, 64 folders and 6,000 entries, 32 wildcard words, 64 `{a,b}` combinations, 512 characters per word (2,048 for brace lists).
  - A pattern held in a shell variable is checked only when the text that sets the variable is in the same command, as in `f=.en?; cat $f`. Forms that pass the name through a pipe (`echo .en? | xargs cat`) are not checked.
- **Current behavior:** `ask` (Codex `deny`). Same as up to 0.2.1.
- **Why accepted:**
  - Matching outside the project would make the hook open paths the agent wrote. If such a path is a network share, the hook connects to the network. An independent review found that a draft which matched outside the project stalled one call for more than 21 seconds and tried to connect, so it was reverted.
  - `*` is also used for arithmetic, regular expressions and PowerShell's "all properties". Matching it would block `echo $((a * b))` and `Select-Object *` in folders that hold secret files.
  - The limits keep a crafted command from holding the hook for long. A draft without limits produced an input that took 135 seconds for one call.
  - If the working folder is a link pointing to a subfolder of the project, Jangseung cannot confirm it is inside the project, so it does not match.
- **Known false positives:**
  - A word that is whole hex or base64 and happens to decode to a secret file name is blocked (`git checkout 2e656e76`). A review that fed in 940,000 real words found no such word.
  - Commands that only handle a secret file without reading it are blocked when a wildcard reaches that file: `git restore --staged .e*`, `touch .e*`. This is the same rule as `touch .env` written with the name in full.
  - Even a command that uses only names is blocked when the same line has both a reading command and `$` (`ls certs/s* && echo $HOME && cat README.md`).
- **Evidence:** test (`tests/test_competitive_gaps_0_2_2.py`), independent review (0.2.2, 4 rounds).

### RR-3. Read commands that sweep folders

- **What:** `grep -r`, `rg`, `git grep`, `find`, `tar` and others reach the contents of secret files without naming them.
- **Current behavior:** `ask` (Codex `deny`). If a person approves, secret files are read too. For the `Grep` tool and `git diff`, `git show` and `git log -p`, Jangseung adds conditions that exclude secret files.
- **Why accepted:** there is no safe way to add exclusion conditions to every shell command. Handing it to a person instead of allowing it automatically is the limit.
- **Evidence:** measured, test (`tests/test_search_exclusions_0_1_7.py`).

### RR-4. Commands left to the host and broad host allow rules

- **What:** in Claude Code `default` and `acceptEdits` modes (from 0.3.0), `pytest`, `npm test`, `git commit` and the like, and lines that join them (`git add -A && git commit -m wip`), are not judged by Jangseung but left to the host's approval flow. If the user has set broad allow rules such as `Bash(python -m:*)` or `Bash(uv run:*)`, commands that print secrets, such as `python -m dotenv list`, also run without asking.
- **Current behavior:** host delegation (Jangseung does not answer).
- **Why accepted:** if Jangseung overrode host rules the user set, every "don't ask again" would stop working. That was the main cause of approval fatigue up to 0.1.9.
- **Evidence:** measured (0.2.1: with no allow rules, the host asked for approval for all 40 delegated commands. 0.3.0: in `default` and `acceptEdits`, the host asked for approval for all 33 run commands, and for joined lines too). `acceptEdits` runs file commands such as `rm`, `mv` and `sed -i` without asking, so file commands are not left to the host.

### RR-5. Parts that depend on host behavior

- **What:** which commands the host runs without approval can change with the host version. The delegation scope was measured only on 2.1.316. The hook also cannot know whether an `ask` actually reaches a person (in `auto` mode a classifier may answer instead).
- **Current behavior:** the review tier (`ask`) is used only in `default` and `acceptEdits` modes. In other modes and in Codex it is `deny`.
- **Why accepted:** the only thing the hook can know is the `permission_mode` in its input.
- **Evidence:** measured (0.2.0, once per mode), design. `dontAsk`, `bypassPermissions` and interactive sessions were not measured.

### RR-6. Name-based secret decisions

- **What:** whether something is secret is decided by file name and path. Names not in the rules (a token in `config.yaml`, a key in `settings.py`) and values already committed are not treated as secret.
- **Current behavior:** pass. If a person adds it to `protect_paths`, it is blocked.
- **Why accepted:** guessing secrets by reading file contents would raise both false positives and misses, and the hook would read the secrets itself.
- **Evidence:** design.

### RR-7. MCP tools

- **What:** the default install does not check MCP tools or MCP resource reads. MCP tools that run code (`mcp__node_repl__js` and others) bypass Jangseung.
- **Current behavior:** pass in the default install. With `aeg install --mcp` turned on, `ask` (Codex `deny`), and the arguments are not inspected.
- **Why accepted:** turning it on by default would ask on every MCP call. In Codex, widening the matcher requires approving `/hooks` again.
- **Evidence:** measured (0.1.9).

### RR-8. Tools that are not checked

- **What:** content sent out through `WebFetch` and `WebSearch`, files the agent pulls in directly as references (`@file`), and cases where another hook that returns `updatedInput` for the same tool removes Jangseung's exclusion conditions.
- **Current behavior:** pass.
- **Why accepted:** the hook is not called, or the other hook's output is outside Jangseung's control.
- **Evidence:** design.

### RR-9. What an approved command does inside

- **What:** programs run inside a prefix in `allow_commands` or a command a person allowed in the approval prompt. If an interpreter such as `python` is approved as a whole, code the agent wrote can do anything, including running `aeg policy`.
- **Current behavior:** `allow` (when approved). For `aeg policy`, this is shown on the screen before approval.
- **Why accepted:** approval is a person's decision. Jangseung is not a sandbox that confines processes.
- **Evidence:** design.

### RR-10. Gap between decision time and run time

- **What:** Jangseung decides based on the state of files at the moment the hook is called. Wildcard checks also match against files that exist at that moment. A `cd folder` written in the command is matched in that folder too, but matching can go wrong when the target folder is decided at run time (`cd "$DIR" && cat *`) or when the same command first creates a file and then reads it.
- **Current behavior:** most such compound commands get `ask` (Codex `deny`).
- **Why accepted:** the intermediate state cannot be known without running the command.
- **Evidence:** design.

### RR-11. Destruction that stays inside the project

- **What:** commands that delete local development resources, such as `docker system prune`, `docker compose down -v`, `sqlite3 app.db "drop table t"`, `truncate -s 0 file` and `find . -exec rm`.
- **Current behavior:** `ask` (Codex `deny`). Not fixed to `deny`.
- **Why accepted:** these are normal commands during development. Only destruction that project files cannot undo, such as of accounts, remote DBs and disks, is kept at `deny`.
- **Evidence:** test (`tests/test_competitive_gaps_0_2_2.py`).

### RR-12. Install and session location

- **What:** Claude Code reads only the `.claude/settings.json` of the folder where the session started. If a session starts in a subfolder of the project, the Jangseung hook is not called. Jangseung also cannot know when the host rewrites the settings file and removes the hook.
- **Current behavior:** pass (the hook is not called). `aeg doctor` can check the registration. From 0.3.0, the session start check (`SessionStart` hook) reports in one line when the PreToolUse hook is missing or the registered program is gone. If the whole hook setup is deleted, the check is deleted with it, so it cannot report. It is not registered in Codex (changing it requires approving `/hooks` again).
- **Why accepted:** a hook that is not called can do nothing.
- **Evidence:** design.

### RR-13. Automatic allow of multiple commands and status commands (0.3.0)

- **What:** lines where every part fits the read grammar, such as `ls; pwd`, `cd src && cat x`, `date` and `python --version`, are allowed without asking. The decision uses the command text and the state of files at decision time.
  - `cd` is followed only when the whole line is joined with `&&` alone, and the target folder must be a real folder inside the project. If CDPATH is set, only folders starting with `./` are followed.
  - A version check accepts only one fixed form per program (`--version` and the like). Programs whose check form runs project code (pytest and others) were not included.
  - Version and status commands are allowed only when the program found on PATH is outside the project. If a `.venv` inside the project comes first on PATH, `python --version` is asked. If the program is not found, it is asked.
  - Read programs themselves, such as `cat`, `ls` and `git`, are not checked against PATH (the same since 0.1.x). In an environment with a project folder first on PATH, a program of the same name written by the agent may run.
- **Current behavior:** `allow` (Codex and every Claude Code mode).
- **Why accepted:** the host also runs such lines on its own (measured: when Jangseung does not answer, `ls -la; pwd`, `cd sub && ls`, `date` and `python --version` ran without approval in `default` and `acceptEdits`). Jangseung picks out and blocks only the lines that read secret files.
- **Evidence:** measured (0.3.0, host behavior and real sessions), test (`tests/test_new_features_0_3_0.py`).

### RR-14. Allow once (0.3.0)

- **What:** `aeg allow-once "<command>"` allows, once, the command whose text matches what a person typed. What a person approves is that person's judgment. If the agent makes a long command and hides a dangerous part at the end, a person who copies and approves that text as is has approved that part too.
- **Current behavior:** exactly the same text, the same shell tool, in the project folder itself, once, 60 minutes at most. It opens only what `allow_commands` would open; secret, Jangseung and target rules stay. Commands that turn off Jangseung are not opened. Sessions are not told apart, so another session in the same project can use it first. `& aeg allow-once` (PowerShell) and `uvx --from jangseung aeg allow-once` get ask (Codex deny), not deny.
- **Why accepted:** in Codex the hook has no way to ask a person. Without this method, a person has to open a whole prefix with `allow_commands`.
- **Evidence:** test (`tests/test_new_features_0_3_0.py`).

### RR-15. Team-shared protection policy (0.3.0)

- **What:** `.jangseung/policy.json` is shared through Git, so its contents change when you switch branches or pull another person's commits. The agent cannot write this file directly, but `git checkout`, `git pull` and `git merge` left to the host can change it (the host asks for approval). If a malicious repository puts in broad `protect_paths`, work is blocked.
- **Current behavior:** it can only add protection. If the file has any other entry or is damaged, every path is protected (every file change by the agent is blocked).
- **Why accepted:** a team needs a committed file to share the same protection. Being blocked is less dangerous than being open.
- **Evidence:** test (`tests/test_new_features_0_3_0.py`).

### RR-16. The end of the ledger is taken from a marker name (0.3.1)

- **What:** the hook continues the chain from the previous record on every write. From 0.3.1 it no longer reads that record back; it trusts the name `.aeg/hook_ledger.head.<number>.<size>.<modification time>.<hash>` left after the last write, and only when the ledger's size and modification time still match the name. An edit that changes bytes, keeps the size and puts the modification time back is not caught at recording time.
- **Current behavior:** the next record after such an edit continues from the hash the marker names, and `aeg evidence verify-hooks` reports a broken chain. If the size or time differs (another version wrote, a repair, an archive, a torn record), the end is read and checked as before, and a damaged end refuses the write.
- **Why accepted:** the agent cannot write to `.aeg/`. Tampering that recomputed hashes was not caught at recording time before either; full verification is the job of `verify-hooks`. Reading a file that had just changed cost about 4 ms per call on Windows because of virus scanning.
- **Evidence:** test (`test_an_edit_that_restores_size_and_time_is_left_to_verify_hooks` in `tests/test_hook_speed_0_3_1.py`).

### RR-17. Same-user code can impersonate the resident judging process (0.3.1, Windows)

- **What:** hook calls started by `jangseung/_hook.py` or the `aeg` launcher ask a resident judging process over a named pipe. The key that process proves itself with is in `%LOCALAPPDATA%\jangseung\resident\<identity>.key`. Code running with the same user's rights can read or replace that file and run a pipe server that answers "allow".
- **Current behavior:**
  - The pipe can be opened only by the current user and SYSTEM, and takes no remote clients.
  - A hook first sends a challenge, and sends its call only after the server proves it holds the key; otherwise it judges the call itself and starts a new resident process.
  - Answers are signed with the key and bound to the call they answer.
  - The key file is outside the project, so agent tool calls that read or write it are denied or asked.
- **Why accepted:** running arbitrary code with the user's rights already lets the agent change Jangseung's code, settings or hook registration (see "write it, then run it" in the README). `JANGSEUNG_RESIDENT=off` judges every call in its own process.
- **Evidence:** tests in `tests/test_resident.py` (`test_a_pipe_without_the_key_gets_nothing_and_is_replaced`, `test_only_well_formed_pipe_names_are_used`), and an independent review that tried key reads and writes through Read, Write, Grep, Glob, Bash and PowerShell (none allowed).

### RR-18. A slow resident answer can leave two records (0.3.1, Windows)

- **What:** once the resident process has proved itself, a hook waits up to 10 seconds for its answer, then judges the call itself. If the resident process finishes that judgment later, the call has two ledger records, and an `aeg allow-once` grant could be used by the first.
- **Current behavior:** a judgment waits at most 1 second for the ledger lock, so normal judgments finish in milliseconds. A call whose hook has already stopped waiting is not judged at all. Both records carry the same decision inputs.
- **Why accepted:** it needs a judgment more than ten times slower than the lock limit, and errs toward stopping a call, not allowing one.
- **Evidence:** reasoning and the hung-process test (`test_a_hung_resident_process_costs_one_second_and_is_replaced`); the over-10-second case itself was not reproduced.

## Not yet decided

Items not yet decided between accepting and fixing. Once decided, they move to the list above or get fixed.

- **Names passed through a here-string:** `xargs cat <<< .env` gets `ask`. Whether to raise it to `deny` is not decided.
- **Everyday commands in Codex:** Codex treats `ask` as `deny`. 0.3.0 allows multiple commands and status commands and adds `aeg allow-once`, but run commands (`pytest`, `npm test`) still need `allow_commands` or a one-time allow.
- **Scope of the review tier:** widened in 0.3.0, but it is a list of names. Changes to run settings not on the list (for example `tasks.py`, `manage.py`, `Procfile`, `.idea/` run configurations) get `allow`.

## Rules for changing the register

- When adding a new class, actually run and confirm the **Current behavior** and record the evidence.
- Even for an accepted class, if a form appears that can be blocked in general with few false positives, block it and narrow the matching entry in this document.
- A leak that happens in real use is treated as a defect, whatever class it falls into.
