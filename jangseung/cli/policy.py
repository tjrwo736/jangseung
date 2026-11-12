"""``aeg policy`` — let a person edit ``.aeg/policy.json`` without hand-writing JSON.

Only a person is meant to run this. The hook denies an agent's call to it in the
spellings it recognizes (``aeg policy``, ``python -m jangseung...``, the launcher
script), and denies every tool that writes under ``.aeg/``. Neither stops a program
an approved command starts: approving a bare interpreter such as ``python`` lets
agent-written code do anything, this included. Every change is shown as a diff and
confirmed before it is written, and the result is checked with the same parser the
hook uses, so a file this command wrote is never one the hook ignores.
"""

from __future__ import annotations

import difflib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence, TextIO

from jangseung.classify.hook_policy import (
    HOOK_POLICY_FILE,
    MAX_POLICY_BYTES,
    SHARED_POLICY_DIR,
    SHARED_POLICY_FILE,
    parse_policy,
    read_shared_protect_paths,
)
from jangseung.contracts import STATE_DIR

POLICY_KEYS = ("allow_paths", "protect_paths", "allow_commands", "allow_mcp_tools")

# Starting points for common projects. Every entry runs the project's own code, so
# each is a decision to trust what the agent writes there; that is said on screen.
PRESETS: dict[str, dict[str, tuple[str, ...]]] = {
    "python": {
        "allow_commands": (
            "pytest",
            "python -m pytest",
            "ruff check",
            "ruff format",
            "mypy",
            "python -m mypy",
        ),
    },
    "node": {
        "allow_commands": (
            "npm test",
            "npm run test",
            "npm run lint",
            "npm run build",
            "npm run typecheck",
            "npx tsc --noEmit",
            "pnpm test",
            "yarn test",
        ),
    },
    "git": {
        "allow_commands": (
            "git add",
            "git commit",
            "git fetch",
            "git switch -c",
        ),
    },
    "rust": {
        "allow_commands": (
            "cargo build",
            "cargo check",
            "cargo test",
            "cargo clippy",
            "cargo fmt",
        ),
    },
    "go": {
        "allow_commands": (
            "go build",
            "go test",
            "go vet",
            "gofmt",
        ),
    },
    "jvm": {
        "allow_commands": (
            "mvn test",
            "mvn compile",
            "mvn verify",
            "gradle test",
            "gradle build",
            "./gradlew test",
            "./gradlew build",
        ),
    },
    "dotnet": {
        "allow_commands": (
            "dotnet build",
            "dotnet test",
            "dotnet format",
        ),
    },
}

_RUNS_PROJECT_CODE_NOTE = (
    "Note: an approved command runs without a question, and most of these run the project's own "
    "code (tests, scripts, git hooks). Approve only what you would let the agent run unattended."
)


def policy_path(base_dir: str | Path) -> Path:
    return Path(base_dir) / STATE_DIR / HOOK_POLICY_FILE


def shared_policy_path(base_dir: str | Path) -> Path:
    return Path(base_dir) / SHARED_POLICY_DIR / SHARED_POLICY_FILE


def cmd_policy_add_shared(
    base_dir: str | Path,
    *,
    protect_paths: Sequence[str],
    assume_yes: bool = False,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int:
    """Add paths to the committed team policy, which can only protect."""

    out = output_stream if output_stream is not None else sys.stdout
    additions = [str(path).strip() for path in protect_paths if str(path).strip()]
    if not additions:
        print("aeg policy: --shared takes --protect paths only; the team file can only add protection.", file=out)
        return 2
    path = shared_policy_path(base_dir)
    current, error = read_shared_protect_paths(base_dir)
    if error is not None:
        print(f"aeg policy: aborted — {path} cannot be used ({error}). Fix or remove it yourself, then retry.", file=out)
        return 1
    merged = list(current) + [item for item in dict.fromkeys(additions) if item not in current]
    before = json.dumps({"protect_paths": list(current)}, ensure_ascii=False, indent=2) + "\n" if path.exists() else ""
    after = json.dumps({"protect_paths": merged}, ensure_ascii=False, indent=2) + "\n"
    if before == after:
        print("aeg policy: already in the shared policy; no changes.", file=out)
        return 0
    print(f"aeg policy: will write {path} (meant to be committed; it can only add protection)", file=out)
    out.write("".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"{path} (current)", tofile=f"{path} (proposed)",
    )))
    if not assume_yes:
        stream = input_stream if input_stream is not None else sys.stdin
        print("Write these changes? [y/N] ", end="", file=out)
        out.flush()
        if stream.readline().strip().lower() not in {"y", "yes"}:
            print("aeg policy: cancelled; no changes written.", file=out)
            return 0
    root = path.parent
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        print(f"aeg policy: aborted — {root} must be a local directory.", file=out)
        return 1
    root.mkdir(parents=True, exist_ok=True)
    temporary = root / f".policy-{os.getpid()}.tmp"
    temporary.write_text(after, encoding="utf-8", newline="\n")
    os.replace(temporary, path)
    print(f"aeg policy: wrote {path}. Commit it so every clone gets the same protection.", file=out)
    return 0


def _load(path: Path) -> tuple[dict[str, list[str]] | None, str | None]:
    """Return the current policy as plain lists, or an error a person must fix first."""

    if path.is_symlink():
        return None, f"{path} is a link; replace it with a regular file"
    if not path.exists():
        return {}, None
    try:
        if not path.is_file() or path.stat().st_size > MAX_POLICY_BYTES:
            return None, f"{path} is not a small regular file"
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError) as exc:
        return None, f"{path} cannot be read as JSON ({exc.__class__.__name__})"
    parsed = parse_policy(data)
    if parsed.error is not None:
        return None, f"{path} is not a valid policy ({parsed.error}); the hook ignores it as a whole"
    return {key: list(data.get(key, [])) for key in POLICY_KEYS}, None


def _text(policy: dict[str, list[str]]) -> str:
    ordered = {key: policy[key] for key in POLICY_KEYS if policy.get(key)}
    return json.dumps(ordered, ensure_ascii=False, indent=2) + "\n"


def _merged(current: dict[str, list[str]], additions: dict[str, Sequence[str]]) -> dict[str, list[str]]:
    merged = {key: list(current.get(key, [])) for key in POLICY_KEYS}
    for key, values in additions.items():
        for value in values:
            text = " ".join(str(value).split()) if key == "allow_commands" else str(value).strip()
            if text and text not in merged[key]:
                merged[key].append(text)
    return merged


def _write_atomically(path: Path, text: str) -> None:
    root = path.parent
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise ValueError(f"{root} must be a local directory")
    if not root.exists():
        root.mkdir(parents=True)
        (root / ".gitignore").write_text("*\n", encoding="utf-8")
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=root, prefix=".policy-", delete=False
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.replace(temporary, path)


# Never suggested: approving these lets any code or any network call through.
_NEVER_SUGGESTED = frozenset(
    {
        "python", "python3", "py", "pythonw", "node", "deno", "bun", "ruby", "perl", "php", "lua", "bash", "sh", "zsh",
        "fish", "dash", "ksh", "pwsh", "powershell", "cmd", "env", "sudo", "xargs", "eval", "exec", "curl", "wget",
        "ssh", "scp", "rsync", "nc", "aeg", "<other>", "npx", "uvx", "pipx", "docker", "kubectl", "rm", "git push",
    }
)


def _suggestable(program: str) -> bool:
    """A program name whose bare prefix approves nothing the danger rules stop.

    Records hold program names only, so ``terraform plan`` is seen as ``terraform``,
    and approving that prefix would also approve ``terraform destroy``. Programs with
    any subcommand the danger rules know are left out for that reason.
    """

    from jangseung.evidence.shell_command_risk import programs_with_dangerous_subcommands

    first = program.split(" ", 1)[0]
    return (
        program not in _NEVER_SUGGESTED
        and first not in _NEVER_SUGGESTED
        and first not in programs_with_dangerous_subcommands()
    )


def cmd_policy_suggest(
    base_dir: str | Path,
    *,
    days: int | None = 14,
    minimum: int = 3,
    output_stream: TextIO | None = None,
) -> int:
    """Name the programs a person was asked about most often. Prints only; writes nothing."""

    from jangseung.state.evidence_query import summarize_hook_evidence

    out = output_stream if output_stream is not None else sys.stdout
    summary = summarize_hook_evidence(base_dir, days=days)
    current = {" ".join(prefix) for prefix in (parse_policy(_load(policy_path(base_dir))[0] or {}).allow_commands)}
    rows = [
        row for row in summary["stopped"]
        if row["decision"] == "ask" and row["category"] == "unclassified" and row["tool_name"] in {"Bash", "PowerShell"}
        and row["count"] >= minimum and _suggestable(row["what"]) and row["what"] not in current
    ]
    span = "all records" if days is None else f"the last {days} day(s)"
    if not rows:
        print(f"aeg policy suggest: nothing was asked {minimum} or more times in {span}.", file=out)
        return 0
    print(f"aeg policy suggest: asked {minimum} or more times in {span} (program names only; nothing was written):", file=out)
    for row in rows:
        print(f"  {row['count']:4d}x  aeg policy add --command \"{row['what']}\"", file=out)
    print("Each runs the project's own code once approved. Interpreters, shells and network tools are never suggested.",
          file=out)
    print("Review the full command lines you were asked about before approving a prefix.", file=out)
    return 0


def cmd_policy_show(
    base_dir: str | Path,
    *,
    as_json: bool = False,
    output_stream: TextIO | None = None,
) -> int:
    out = output_stream if output_stream is not None else sys.stdout
    path = policy_path(base_dir)
    current, error = _load(path)
    if as_json:
        payload: dict[str, Any] = {"path": str(path), "present": path.exists(), "error": error}
        payload["policy"] = None if current is None else {key: current.get(key, []) for key in POLICY_KEYS}
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True), file=out)
        return 0 if error is None else 1
    print(f"aeg policy: {path}", file=out)
    shared, shared_error = read_shared_protect_paths(base_dir)
    if shared or shared_error:
        print(f"shared (committed) {shared_policy_path(base_dir)}: "
              + (f"error: {shared_error}; the hook treats the policy as failed" if shared_error
                 else f"protect_paths: {len(shared)}"), file=out)
        for value in shared:
            print(f"  - {value}", file=out)
    if error is not None:
        print(f"error: {error}", file=out)
        return 1
    if not path.exists():
        print("No policy file yet; the built-in rules apply.", file=out)
        return 0 if shared_error is None else 1
    for key in POLICY_KEYS:
        values = current.get(key, []) if current else []
        print(f"{key}: {len(values)}", file=out)
        for value in values:
            print(f"  - {value}", file=out)
    return 0 if shared_error is None else 1


def cmd_policy_add(
    base_dir: str | Path,
    *,
    commands: Sequence[str] = (),
    allow_paths: Sequence[str] = (),
    protect_paths: Sequence[str] = (),
    mcp_tools: Sequence[str] = (),
    preset: str | None = None,
    assume_yes: bool = False,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int:
    out = output_stream if output_stream is not None else sys.stdout
    additions: dict[str, list[str]] = {
        "allow_commands": list(commands),
        "allow_paths": list(allow_paths),
        "protect_paths": list(protect_paths),
        "allow_mcp_tools": list(mcp_tools),
    }
    if preset is not None:
        if preset not in PRESETS:
            print(f"aeg policy: unknown preset; choose one of: {', '.join(sorted(PRESETS))}", file=out)
            return 2
        for key, values in PRESETS[preset].items():
            additions[key].extend(values)
    if not any(additions.values()):
        print("aeg policy: nothing to add; pass --command, --path, --protect, --mcp-tool or a preset.", file=out)
        return 2

    path = policy_path(base_dir)
    current, error = _load(path)
    if error is not None or current is None:
        print(f"aeg policy: aborted — {error}", file=out)
        print("Fix or remove the file yourself, then retry.", file=out)
        return 1
    merged = _merged(current, additions)
    checked = parse_policy({key: values for key, values in merged.items() if values})
    if checked.error is not None:
        print(f"aeg policy: aborted — the result would not be a valid policy ({checked.error}).", file=out)
        print(
            "Commands are plain words (letters, digits, space and ./:=@+-); MCP tools are exact names "
            "such as mcp__server__tool.",
            file=out,
        )
        return 2

    before = _text(current) if path.exists() else ""
    after = _text(merged)
    if before == after:
        print("aeg policy: already in the policy; no changes.", file=out)
        return 0
    print(f"aeg policy: will write {path}", file=out)
    diff = difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"{path} (current)", tofile=f"{path} (proposed)",
    )
    out.write("".join(diff))
    if additions["allow_commands"]:
        print(_RUNS_PROJECT_CODE_NOTE, file=out)
    if additions["allow_paths"]:
        print(
            "Note: an allowed path loses its built-in protection for every agent tool. "
            "A bare file name such as .env applies in every folder; write a path to open one file.",
            file=out,
        )
    if not assume_yes:
        print("Proceed? [y/N]: ", end="", file=out, flush=True)
        stream = input_stream if input_stream is not None else sys.stdin
        if stream.readline().strip().lower() not in ("y", "yes"):
            print("aeg policy: cancelled; no changes written.", file=out)
            return 0
    try:
        _write_atomically(path, after)
    except (OSError, ValueError) as exc:
        print(f"aeg policy: failed to write the policy: {exc}", file=out)
        return 1
    print(f"aeg policy: done. {path} updated.", file=out)
    return 0


__all__ = ["POLICY_KEYS", "PRESETS", "cmd_policy_add", "cmd_policy_show", "policy_path"]
