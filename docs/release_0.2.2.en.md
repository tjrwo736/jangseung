# Jangseung 0.2.2 release notes

0.2.2 was not released on its own; it ships in 0.3.0. Korean original: [release_0.2.2.md](release_0.2.2.md)

This release closes gaps where Jangseung fell behind similar tools. No change makes a judgment looser. Every judgment that changed moved up from `ask` to `deny`.

```bash
python -m pip install --upgrade jangseung
```

You do not need to register the hook again. If you use the plugin, update the plugin.

## Blocks commands that reach secret files without naming them

Up to 0.2.1, a secret file got `deny` only when its name appeared literally. The forms below got `ask`. If you allowed one in the approval prompt without thinking, the value was printed. Now they get `deny`.

- **Wildcards:** `cat .en?`, `cat .[e]nv`, `cat .env*`, `cat certs/*.p?m`, `cat **/id_rs?`, and `Get-Content .en*` in PowerShell. The hook matches the pattern against the real files in the project folder and blocks only when it reaches a secret file that exists now. Wildcards that reach no secret file, such as `wc -l *.py`, behave as before. When the command moves into a folder it names, as in `cd certs && cat s*`, the hook also matches in that folder.
- **`{a,b}` lists:** `cat .en{v,x}`, `cat {README.md,.env}`.
- **Names encoded whole:** `cat $(echo LmVudg== | base64 -d)`, `python -c "open(base64.b64decode('LmVudg=='))"`, hex (`2e656e76`). The hook decodes only when a single word is entirely base64 or hex.

Wildcard matching has the following limits. Commands outside these limits get `ask` as before.

- **It looks only inside the project.** The hook does not open the home folder (`~/.ss?/id_*`), other drives, or network shares (`\\서버\공유\a*`). The agent chooses the command text, so the hook must not follow that text outside the project or onto the network. The hook first checks from the path text alone whether a path is inside the project.
- **Reads are capped.** One call reads at most 64 folders and 6,000 entries.
- **Patterns with no letter or digit are not matched.** `*`, `.*` and `*.*` also appear in arithmetic (`2 * 3`), regular expressions, and PowerShell's `Select-Object *`. So `cat *` gets `ask`.
- **Commands that only use names are not matched.** `ls .en?`, `stat certs/s*`, `find` with no action, `git status` and `git add` do not open files (the same rule that allows `ls .env`). Output piped on, as in `ls certs/* | wc -l`, carries only name text, so this is not matched either. When a name can reach a reading command as an argument, the hook matches it: `ls .en? | xargs cat`, `cat $(ls .en?)`, `for f in .en?; do cat $f; done`. PowerShell passes wildcards to the command as they are, so the hook matches only file commands (`Get-Content`, `Select-String`, `Copy-Item`, `Remove-Item` and others) and listing commands that feed a file command (`Get-Item .en? | Get-Content`). `Get-Process *e*` has nothing to do with files.
- **Arguments in pattern position are not matched.** In `tar --exclude '.e*'`, `grep -rn '.en?' src` and `jq '.e*' package.json`, that argument is a pattern for the program, not a file name.
- **Links are not followed.** A symbolic link or junction inside the project can point outside it, so the hook does not open folders reached through a link.

Forms that build the name at run time (`chr(46)+'env'`, `printf '.e%s' nv`) get `ask` as before. The command text alone does not show the name. This is recorded as RR-2 and RR-2a in the [residual risk register](residual_risk.en.md).

## Blocks commands that destroy things outside the project

The following commands got `ask` up to 0.2.1. Now they get `deny`. Project files cannot undo this kind of destruction.

- **Deleting cloud and hosting resources:** `aws s3 rb`, `aws s3 rm`, `aws s3 sync --delete`, `aws ec2 terminate-instances`, `aws ... delete-*`, `az ... delete-batch`, `gcloud ... delete`, `az ... delete`, `firebase firestore:delete`, `vercel rm`, `fly apps destroy`, `heroku apps:destroy` and others. CLIs covered: aws, gcloud, gsutil, bq, az, doctl, fly, heroku, vercel, netlify, firebase, supabase, railway, wrangler, oci, ibmcloud, linode-cli, scw, hcloud.
- **Deleting database contents:** `DROP ...`, `TRUNCATE`, `DELETE FROM` without `WHERE`, `FLUSHALL`, `FLUSHDB` or `dropDatabase()` passed as an argument to `psql`, `mysql`, `mariadb`, `sqlcmd`, `mongosh`, `redis-cli`, `cqlsh`, `clickhouse-client` and others; also `dropdb`, `mysqladmin drop`, `pg_restore --clean`, `mongorestore --drop`.
- **Disks and the system:** `mkfs*`, `fdisk` and `parted` (except listing with `-l`), `wipefs`, `diskpart`, `diskutil erase...`, `format D:`, `Format-Volume`, `Clear-Disk`, `vssadmin delete`, `bcdedit /delete`, `shutdown` (except cancelling with `/a`, `-c`), `reboot`, `systemctl poweroff`, `init 0`, `Stop-Computer`, `Restart-Computer`, `kill -9 -1`, `kill 1`.

Ordinary commands such as `aws s3 ls`, `gcloud projects list`, `psql -c "select ..."`, `fdisk -l` and `kill 1234` get `ask` as before. For cloud CLIs, the hook looks only at the words in command position (`aws <서비스> <동작>`). A resource name after them such as `delete-me` is not blocked. For SQL, the hook looks only at statements that start with those words (`comment on table t is 'do not truncate me'` does not count). Disk tools are not blocked when the option only displays (`fdisk -l`, `sgdisk -p`, `parted ... print`, `mkfs -n`, PowerShell's `-WhatIf`). `docker compose down -v` and `sqlite3 app.db "drop table t"`, which delete local development resources, also stay at `ask` (register RR-11). If you want to hand such a command to the agent, you can approve it by prefix, as in `aeg policy add --command "aws s3 rm"`.

## Says why it blocked, by kind

When the hook blocked a dangerous command, the reason was always one sentence: "This is a dangerous command." Now it names the kind: publishing and deploying, deleting account resources, deleting databases, disks and the system, force-deleting folders, and network transfer, environment output and permission changes. Reason codes gain `dangerous_command_kind:<종류>`. Kind names come only from a fixed list and never contain command text.

## Hook calls are a little faster

The hook path no longer loads modules it does not use (`argparse`, `tempfile`, and what they pull in, such as `shutil`). Measured in the same place in the same way, the median time for one call fell from about 194 ms to about 180 ms (Windows, Python 3.14, two runs of 15 calls each, about 7%). Most of the remaining time is Python startup and loading the judgment modules. The judgment itself takes 3–5 ms. The arguments `aeg hook-run` accepts (`--substrate`, `--mcp`, `--ensure-state`) are unchanged, and unknown arguments still exit with code 2.

## `aeg evidence summary`

This command reads the ledger and shows judgment counts and the programs and files that stopped most often. Use it to decide what to open up with `aeg policy`. It only reads and does not change `.aeg`. The ledger does not hold the original command text, so the output goes no further than program names.

```bash
aeg evidence summary
aeg evidence summary --days 7 --json
```

## Residual risk register

[docs/residual_risk.en.md](residual_risk.en.md) collects what we know the hook cannot block and have accepted. It also lists what we do not accept (a defect if it gets through) and items not yet judged.

## Checks

- Automated tests: all pass on Windows, Python 3.14 (1592 passed, 20 skipped). The 405 new tests are in `tests/test_competitive_gaps_0_2_2.py`.
- Judgment survey (the same command list run on 0.2.1 and 0.2.2 and compared, Claude Code `default` mode):
  - 64 obfuscated secret-access commands: `deny` 51 → 56, `ask` 13 → 8, `allow` and host delegation 0 → 0.
  - 48 destructive commands: `deny` 30 → 42, `ask` 18 → 6, `allow` and host delegation 0 → 0.
  - 50 everyday commands: no change (`allow` 15, host delegation 23, `ask` 9, `deny` 3).
- Independent review: a separate agent on the same model reviewed the changes aggressively four times. None of the four found a judgment weaker than in 0.2.1 (2,800 commands compared and 3,000 random ones). Findings and actions:
  - Round 1: crafted wildcard and brace input made one call take 135 seconds and another 91 seconds (over the host's 30-second limit). We capped the amount read and changed brace handling to a single pass. We also fixed false positives on everyday commands (`2 * 3`, `Select-Object *`) and in the destruction rules (`fdisk -l`, resource name `delete-me`).
  - Round 2: fixing round 1 had widened matching to outside the project, and that was the problem. When a command held a network share path, the hook tried to connect and stalled for more than 21 seconds. We moved matching back inside the project and made it check from the path text alone first. We also fixed regex backtracking delays and misses and false positives in the destruction rules.
  - Round 3: no high-severity findings. We fixed three problems: matching turned off when the project path was written as a link or a short name, the hook read outside the project by following links inside it, and forms where a name passes to a reading command were missed.
  - Round 4: nothing of medium severity or higher. 0 accesses to folders outside the project (call tracing), no network delay, 0 internal errors. We narrowed the one remaining false positive (`ls certs/* | wc -l`). This last adjustment was not reviewed again.
- Worst-case time: one crafted 76 KB command takes about 1 second (about 0.27 seconds in 0.2.1). Ordinary commands show no difference.
- Real session: checked once each with the final code in Claude Code 2.1.316 `claude -p` (Windows, `default` mode, loaded as a plugin). `cat .en?`, `ls .en? | xargs cat` and `aws s3 rb s3://bucket-x` did not run and showed the new reason text. `ls .en? | wc -l` asked for approval as before, `git status` ran, and for `pytest --version` the host asked for approval.
- Not checked: Codex real sessions, interactive sessions, and what the host does when the hook exceeds its time limit. macOS and Linux are checked only by automated tests in CI (including symbolic link paths). There is no external security review.
