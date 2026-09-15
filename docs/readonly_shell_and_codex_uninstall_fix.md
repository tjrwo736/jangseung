# Read-only shell and Codex uninstall fixes

Status: source changes; not yet a PyPI release. Based on 0.1.1 / main
`1e99f5c55346b8658d51fe7e924d43d388c5bbbe`.

## Reproductions

- `Bash: cat README.md` previously reached BASH_NOT_CHECKED -> defer. Codex
  upgraded that to deny even for an ordinary existing project document.
- Codex installation wrote `.codex/config.toml`, but uninstall had no target
  option and inspected only `.claude/settings.json`.

## Behavior

The new shell classifier accepts a deliberately small grammar. It recognizes
file operands and only read-only options for cat/head/tail, sed numeric print
ranges, rg with --no-config, and Get-Content. It also recognizes pipelines whose
every segment fits this grammar (Select-Object only supports numeric
First/Last/Skip). PowerShell Get-Content may arrive as tool name Bash.

File operands must be literal, regular, existing files inside the supplied repo
root. The existing path resolver, protected-path classifier and .aeg integrity
guard determine their scope, including symlink resolution. Unclassified
commands retain the previous ask/defer/deny behavior; dangerous gates are
evaluated before the new allow branch. Path checking is performed at hook time,
not an OS-enforced lock against subsequent file replacement.

The additional decision basis is `shell_read_gate`. An allow decision records
`structurally_classified_read_only_shell_command` without storing the raw
command in the hook ledger. Existing direct Read and PowerShell decisions remain
unchanged except newly recognized safe pipelines. This does not generally
enable PowerShell write parsing under a Bash tool name.

Codex uninstall parses TOML with tomlkit, removes exact managed commands from
PreToolUse entries, and preserves other hook commands/events and settings.
Quoted keys, inline arrays and multiline strings are handled by the parser.
Ambiguous mixed-platform hooks are preserved. Invalid structures abort before
backup or write. A diff precedes confirmation; an existing file is backed up
before mutation. Repeated uninstall is a no-op. Run removal in a manual terminal
because the agent's own attempt to run uninstall may itself be gated.

## Verification scope

Local Windows / Python 3.14 full suite: **985 passed, 11 skipped**, including
120 added cases (119 passed and one symlink case skipped). The wheel build
contains the new classifier and declares the TOML dependency. CI separately
checks Windows/Linux and Python 3.10-3.13.

Regression tests cover safe reads, denied write/execution options, protected and
outside paths, symlinks, Windows path syntax, Unicode/space paths, real hook CLI
responses/recording, Codex install/remove round trips, confirmation cancellation,
backup failure, invalid TOML, non-managed command preservation, quoted keys and
multiline strings. Live integration with the reporter's application version
still requires their exact tool payload and error message. No new provider,
OS sandbox, global install, or configurable read policy is introduced.
