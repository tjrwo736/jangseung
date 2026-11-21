# Jangseung 0.3.2 — personal approvals and local records

[한국어](release_0.3.2.md)

## After upgrading

1. Run `python -m pip install --upgrade jangseung==0.3.2` in the environment where you installed Jangseung. If you use the plugin, update the plugin too.
2. Re-approve just the exceptions you still need with `aeg policy add`, or run `aeg policy adopt` in each project and review the complete list before accepting. The checkout's old exceptions are no longer grants. Its additional path protections still apply. Old one-time approvals are not imported.
3. If you registered hooks with the installer, run `aeg install` for Claude Code or `aeg install --target codex` for Codex, then run `aeg doctor --hooks` for that target. If Codex prompts for trust, review and approve the new command yourself.

## What changed

- Personal and one-time grants are stored under the user's profile, separately for each project. A checkout cannot grant them by supplying a policy file. A linked project state directory is rejected.
- Ambiguous PowerShell arguments are not stored as target paths in new records. Existing records are not rewritten; review them before sharing.
- A write is denied if its required session mark cannot be saved. A failure to record only the audit entry still preserves the decision and reports the failure.
- Full ledger verification now flags an unterminated last record. Verification is read-only.
- The installer checks that settings still match the preview before replacing them. Reinstall repairs stale managed matchers on both hosts while preserving unrelated hooks and their matchers.
- CI exercises interpreter selection and the resident process in an editable Windows virtual environment.

Local diagnostics do not claim that a host actually dispatched its hook.
