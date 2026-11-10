"""Command-line interface for the Jangseung guard hook."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jangseung.contracts import SAFE_DEFAULT
from jangseung.cli.hook_run import SUBSTRATE_CLAUDE_CODE, SUBSTRATE_CODEX, run_aeg_hook_run_from_process
from jangseung.cli.explain import cmd_explain
from jangseung.cli.install import (
    INSTALL_TARGETS,
    SCOPE_PROJECT,
    SETTINGS_SCOPES,
    TARGET_CLAUDE_CODE,
    cmd_install,
    cmd_uninstall,
)
from jangseung.cli.policy import PRESETS, cmd_policy_add, cmd_policy_show
from jangseung.state import git
from jangseung.state.doctor import DoctorCheck, doctor_status, run_doctor
from jangseung.state.evidence_query import (
    hook_detail_as_json,
    hook_human_sections,
    list_hook_evidence,
    load_hook_evidence,
    sanitize_for_display,
)
from jangseung.state.hook_ledger import hook_ledger_needs_repair, repair_hook_ledger, verify_hook_ledger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aeg", description="Jangseung guard hook CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="check local guard hook prerequisites")
    doctor_parser.add_argument("--hooks", action="store_true", help="also inspect project-local hook setup without executing it")
    doctor_parser.add_argument("--target", choices=(*INSTALL_TARGETS, "all"), default=None, help="hook target to inspect (requires --hooks; default: all)")
    doctor_parser.add_argument("--json", action="store_true", dest="as_json")
    explain_parser = subparsers.add_parser("explain", help="explain a hook decision without tool execution or recording")
    explain_input = explain_parser.add_mutually_exclusive_group(required=True)
    explain_input.add_argument("--command", dest="command_text", help="shell command to judge, never execute")
    explain_input.add_argument("--file", help="file path for a simulated Read request; content is not read")
    explain_input.add_argument("--stdin", action="store_true", help="read one PreToolUse JSON object from stdin")
    explain_parser.add_argument("--tool", choices=("Bash", "PowerShell"), default=None, help="tool for --command (default: Bash)")
    explain_parser.add_argument("--substrate", choices=(SUBSTRATE_CLAUDE_CODE, SUBSTRATE_CODEX), default=None)
    explain_parser.add_argument("--permission-mode", choices=("default", "acceptEdits", "auto", "dontAsk", "bypassPermissions", "plan"), default=None, help="host mode to simulate with --command; omitted keeps the conservative mapping")
    explain_parser.add_argument("--json", action="store_true", dest="as_json")
    evidence_parser = subparsers.add_parser(
        "evidence",
        help="inspect persisted hook records without modifying .aeg state",
    )
    evidence_subparsers = evidence_parser.add_subparsers(
        dest="evidence_command",
        required=True,
    )
    evidence_list_parser = evidence_subparsers.add_parser(
        "list",
        help="list persisted hook records newest-first",
    )
    evidence_list_parser.add_argument("--limit", type=_positive_int, default=20)
    evidence_list_parser.add_argument("--json", action="store_true", dest="as_json")
    evidence_show_parser = evidence_subparsers.add_parser(
        "show",
        help="show structured details for one hook record",
    )
    evidence_show_parser.add_argument(
        "evidence_id",
        help="an unambiguous hook record hash prefix",
    )
    evidence_show_parser.add_argument("--json", action="store_true", dest="as_json")
    evidence_verify_hooks_parser = evidence_subparsers.add_parser(
        "verify-hooks",
        help="verify the dedicated hook decision ledger hash chain",
    )
    evidence_verify_hooks_parser.add_argument("--json", action="store_true", dest="as_json")
    evidence_repair_hooks_parser = evidence_subparsers.add_parser(
        "repair-hooks",
        help="move damaged hook ledger lines into a quarantine file and continue the chain",
    )
    evidence_repair_hooks_parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    hook_run_parser = subparsers.add_parser(
        "hook-run",
        help=(
            "read a PreToolUse hook JSON from stdin, judge it with the "
            "existing Aegis engine, and write a permissionDecision to stdout (fail-closed)"
        ),
    )
    hook_run_parser.add_argument(
        "--substrate",
        choices=(SUBSTRATE_CLAUDE_CODE, SUBSTRATE_CODEX),
        default=None,
        help=(
            "explicit hook substrate; omitted defaults to claude-code behavior. "
            "Use codex only for hooks installed into Codex."
        ),
    )
    hook_run_parser.add_argument(
        "--mcp",
        action="store_true",
        help="marks the hook entry added by install --mcp; the judgment is the same",
    )
    hook_run_parser.add_argument(
        "--ensure-state",
        action="store_true",
        help="create .aeg/ for recording when it is missing; set by the plugin's hook entry",
    )
    install_parser = subparsers.add_parser(
        "install",
        help="register the Aegis PreToolUse hook in a project-local substrate config",
    )
    install_parser.add_argument(
        "--path", default=None, help="project directory to install into (default: cwd)"
    )
    install_parser.add_argument(
        "--yes", action="store_true", help="skip the confirmation prompt"
    )
    install_parser.add_argument(
        "--target",
        choices=INSTALL_TARGETS,
        default=TARGET_CLAUDE_CODE,
        help=(
            "hook substrate to install for: claude-code writes .claude/settings.json "
            "(default), codex writes .codex/config.toml"
        ),
    )
    install_parser.add_argument(
        "--scope",
        choices=SETTINGS_SCOPES,
        default=SCOPE_PROJECT,
        help=(
            "claude-code only: project writes .claude/settings.json, which a team usually shares "
            "(default); local writes your own .claude/settings.local.json"
        ),
    )
    install_parser.add_argument(
        "--global",
        dest="global_install",
        action="store_true",
        help="(unsupported) global ~/.claude install; project-local only in this version",
    )
    install_parser.add_argument(
        "--mcp",
        action="store_true",
        help=(
            "also add a separate hook for MCP tool calls and MCP resource reads: they need "
            "approval (denied on Codex) unless .aeg/policy.json lists the tool in allow_mcp_tools"
        ),
    )
    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="remove the Aegis PreToolUse hook from a project-local substrate config",
    )
    uninstall_parser.add_argument(
        "--path", default=None, help="project directory to uninstall from (default: cwd)"
    )
    uninstall_parser.add_argument(
        "--yes", action="store_true", help="skip the confirmation prompt"
    )
    uninstall_parser.add_argument(
        "--target", choices=INSTALL_TARGETS, default=TARGET_CLAUDE_CODE,
        help="hook substrate to remove: claude-code (default) or codex",
    )
    uninstall_parser.add_argument(
        "--mcp", action="store_true", help="remove only the MCP hook added by install --mcp",
    )
    uninstall_parser.add_argument(
        "--scope", choices=SETTINGS_SCOPES, default=SCOPE_PROJECT,
        help="claude-code only: which settings file to remove the hook from (default: project)",
    )
    policy_parser = subparsers.add_parser(
        "policy",
        help="show or extend the project approval policy in .aeg/policy.json (run by a person, not an agent)",
    )
    policy_subparsers = policy_parser.add_subparsers(dest="policy_command", required=True)
    policy_show_parser = policy_subparsers.add_parser("show", help="print the current policy")
    policy_show_parser.add_argument("--project", default=None, help="project directory (default: cwd)")
    policy_show_parser.add_argument("--json", action="store_true", dest="as_json")
    policy_add_parser = policy_subparsers.add_parser("add", help="add entries after showing a diff")
    policy_add_parser.add_argument("--command", dest="policy_commands", action="append", default=[],
                                   help="command prefix agents may run without a question, such as \"pytest\"")
    policy_add_parser.add_argument("--path", dest="policy_allow_paths", action="append", default=[],
                                   help="protected or secret path to open to agents")
    policy_add_parser.add_argument("--protect", dest="policy_protect_paths", action="append", default=[],
                                   help="extra path agents must not change")
    policy_add_parser.add_argument("--mcp-tool", dest="policy_mcp_tools", action="append", default=[],
                                   help="exact MCP tool name, such as mcp__server__tool")
    policy_preset_parser = policy_subparsers.add_parser("preset", help="add a starting set of commands")
    policy_preset_parser.add_argument("preset", choices=sorted(PRESETS))
    for policy_writer in (policy_add_parser, policy_preset_parser):
        policy_writer.add_argument("--project", default=None, help="project directory (default: cwd)")
        policy_writer.add_argument("--yes", action="store_true", help="skip the confirmation prompt")

    args = parser.parse_args(argv)
    if args.command == "doctor":
        if args.target is not None and not args.hooks:
            parser.error("--target requires doctor --hooks")
        return _cmd_doctor(Path.cwd(), hooks=args.hooks, target=args.target or "all", as_json=args.as_json)
    if args.command == "explain":
        if args.permission_mode is not None and args.command_text is None:
            parser.error("--permission-mode requires explain --command; with --stdin set it in the JSON input")
        if args.tool is not None and args.command_text is None:
            parser.error("--tool requires explain --command")
        return cmd_explain(Path.cwd(), command=args.command_text, file=args.file,
                           tool=args.tool or "Bash", substrate=args.substrate, as_json=args.as_json,
                           permission_mode=args.permission_mode,
                           stdin=sys.stdin, stdout=sys.stdout)
    if args.command == "evidence":
        if args.evidence_command == "list":
            return _cmd_evidence_list(Path.cwd(), limit=args.limit, as_json=args.as_json)
        if args.evidence_command == "show":
            return _cmd_evidence_show(Path.cwd(), args.evidence_id, as_json=args.as_json)
        if args.evidence_command == "verify-hooks":
            return _cmd_evidence_verify_hooks(Path.cwd(), as_json=args.as_json)
        if args.evidence_command == "repair-hooks":
            return _cmd_evidence_repair_hooks(Path.cwd(), assume_yes=args.yes)
    if args.command == "hook-run":
        return run_aeg_hook_run_from_process(substrate=args.substrate, ensure_state=args.ensure_state)
    if args.command == "policy":
        project = Path(args.project) if args.project else Path.cwd()
        if args.policy_command == "show":
            return cmd_policy_show(project, as_json=args.as_json)
        if args.policy_command == "preset":
            return cmd_policy_add(project, preset=args.preset, assume_yes=args.yes)
        return cmd_policy_add(
            project,
            commands=args.policy_commands,
            allow_paths=args.policy_allow_paths,
            protect_paths=args.policy_protect_paths,
            mcp_tools=args.policy_mcp_tools,
            assume_yes=args.yes,
        )
    if args.command == "install":
        return cmd_install(
            Path(args.path) if args.path else Path.cwd(),
            assume_yes=args.yes,
            global_requested=args.global_install,
            target=args.target,
            mcp=args.mcp,
            scope=args.scope,
        )
    if args.command == "uninstall":
        return cmd_uninstall(
            Path(args.path) if args.path else Path.cwd(),
            assume_yes=args.yes,
            target=args.target,
            mcp_only=args.mcp,
            scope=args.scope,
        )
    parser.error(f"unknown command: {args.command}")
    return 2


def _cmd_doctor(cwd: Path, *, hooks: bool = False, target: str = "all", as_json: bool = False) -> int:
    checks = run_doctor(cwd)
    if hooks:
        from jangseung.cli.hook_doctor import run_hook_doctor
        checks.extend(run_hook_doctor(cwd, target=target))
    status = doctor_status(checks)
    if as_json:
        from dataclasses import asdict
        print(json.dumps(sanitize_for_display({
            "status": status, "checks": [asdict(check) for check in checks],
            "store_write_performed": False, "hook_execution_performed": False,
            "host_execution": "NOT_CHECKED",
        }), ensure_ascii=True, sort_keys=True))
    else:
        _print_doctor_card(status, checks)
    return 1 if status == "FAIL" else 0


def _cmd_evidence_list(cwd: Path, *, limit: int = 20, as_json: bool = False) -> int:
    try:
        repo = git.repo_root(cwd)
        items = list_hook_evidence(repo, limit=limit)
    except Exception as exc:  # noqa: BLE001 - inspection errors must be reported, not crash.
        if as_json:
            print(json.dumps({"status": "FAIL", "error": str(exc), "items": []}, sort_keys=True))
        else:
            _print_card("Aegis evidence list", "FAIL", [("error", str(exc))])
        return 1

    summaries = [sanitize_for_display(item.to_summary()) for item in items]
    status = "EMPTY" if not summaries else (
        "DEGRADED" if any(item["readability"] == "UNREADABLE" for item in summaries) else "OK"
    )
    if as_json:
        print(json.dumps({"status": status, "items": summaries}, ensure_ascii=True, sort_keys=True))
        return 0

    print("Aegis evidence list")
    print(f"status: {status}")
    if not summaries:
        print("No persisted hook records found.")
        return 0
    rows = []
    for item in summaries:
        artifact = item["artifacts"]
        artifact_text = "/".join(
            f"{name}:{'yes' if present else 'no'}"
            for name, present in artifact.items()
        )
        decision = str(item["decision"])
        if item["risk_level"]:
            decision = f"{decision}/{item['risk_level']}"
        rows.append(
            (
                str(item["kind"]).upper(),
                str(item["id"]),
                str(item["timestamp"]),
                decision,
                artifact_text,
                str(item["readability"]),
                str(item.get("tool_name", "")),
                str(item.get("what", "")),
            )
        )
    _print_table(("TYPE", "ID", "TIMESTAMP", "DECISION", "ARTIFACTS", "READABILITY", "TOOL", "WHAT"), rows)
    for item in summaries:
        if item["error"]:
            print(f"warning: {item['id']}: {item['error']}")
    return 0


def _cmd_evidence_show(cwd: Path, evidence_id: str, *, as_json: bool = False) -> int:
    try:
        repo = git.repo_root(cwd)
        detail = load_hook_evidence(repo, evidence_id)
    except Exception as exc:  # noqa: BLE001 - inspection errors must be reported, not crash.
        if as_json:
            print(json.dumps({"status": "FAIL", "id": evidence_id, "error": str(exc)}, sort_keys=True))
        else:
            _print_card("Aegis evidence show", "FAIL", [("id", evidence_id), ("error", str(exc))])
        return 1

    if detail is None:
        payload = {"status": "NOT_FOUND", "id": evidence_id, "error": "evidence id not found"}
        if as_json:
            print(json.dumps(payload, sort_keys=True))
        else:
            _print_card(
                "Aegis evidence show",
                "NOT_FOUND",
                [("id", evidence_id), ("error", "evidence id not found")],
            )
        return 1

    if as_json:
        payload = hook_detail_as_json(detail)
        payload["status"] = "OK" if detail.readable else "UNREADABLE"
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
        return 0 if detail.readable else 1

    print("Aegis evidence show")
    print(f"status: {'OK' if detail.readable else 'UNREADABLE'}")
    if not detail.readable:
        print(f"id: {detail.item.identifier}")
        print(f"error: {sanitize_for_display(detail.item.error or 'unreadable evidence')}")
        return 1
    for section, rows in hook_human_sections(detail):
        print(f"[{section}]")
        for key, value in rows:
            print(f"{key}: {_display_value(value)}")
    return 0


def _cmd_evidence_repair_hooks(cwd: Path, *, assume_yes: bool = False) -> int:
    try:
        repo = git.repo_root(cwd)
        if not hook_ledger_needs_repair(repo):
            print("aeg evidence repair-hooks: the hook ledger is intact; nothing to repair.")
            return 0
        print("aeg evidence repair-hooks: the hook ledger has damaged lines.")
        print("Everything from the first damaged line moves to a quarantine file in .aeg/; the chain continues from the last good record.")
        if not assume_yes:
            print("Proceed? [y/N]: ", end="", flush=True)
            if sys.stdin.readline().strip().lower() not in ("y", "yes"):
                print("aeg evidence repair-hooks: cancelled; no changes written.")
                return 0
        report = repair_hook_ledger(repo)
    except Exception as exc:  # noqa: BLE001 - repair failures must be reported, not crash.
        print(f"aeg evidence repair-hooks: failed: {exc}")
        return 1
    print(f"aeg evidence repair-hooks: kept {report.kept_records} record(s), quarantined {report.quarantined_lines} line(s).")
    if report.quarantine_path:
        print(f"Quarantine file: {report.quarantine_path}")
    return 0


def _cmd_evidence_verify_hooks(cwd: Path, *, as_json: bool = False) -> int:
    try:
        repo = git.repo_root(cwd)
        result = verify_hook_ledger(repo)
    except Exception as exc:  # noqa: BLE001 - verification failures must be reported.
        if as_json:
            print(json.dumps({"status": "FAIL", "checks": [], "errors": [str(exc)]}, sort_keys=True))
        else:
            _print_card("Aegis evidence verify-hooks", "FAIL", [("error", str(exc))])
        return 1
    status = "PASS" if result.ok else "FAIL"
    payload = {
        "status": status,
        "record_count": len(result.records),
        "checks": list(result.checks),
        "errors": list(result.errors),
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    else:
        rows = [("record_count", str(payload["record_count"]))]
        rows.extend(("check", check) for check in result.checks)
        rows.extend(("error", error) for error in result.errors)
        _print_card("Aegis evidence verify-hooks", status, rows)
    return 0 if result.ok else 1


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def _display_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return str(value)


def _print_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def _print_card(title: str, status: str, rows: list[tuple[str, str]]) -> None:
    print(title)
    print(f"status: {status}")
    for key, value in rows:
        print(f"{key}: {value}")


def _print_doctor_card(status: str, checks: list[DoctorCheck]) -> None:
    print("Aegis doctor")
    print(f"status: {status}")
    print(f"overall_status: {status}")
    print(f"repo_root: {_doctor_detail(checks, 'repo_root')}")
    print(f"state_path: {_doctor_detail(checks, 'state_path')}")
    print(f"safe_default: {SAFE_DEFAULT}")
    print("checks:")
    for check in checks:
        print(f"- [{check.status}] {check.name}")
        print(f"  message: {check.message}")
        if check.fix_hint:
            print(f"  fix_hint: {check.fix_hint}")
        if check.next_step:
            print(f"  next_step: {check.next_step}")
        for key, value in check.details:
            print(f"  {key}: {value}")


def _doctor_detail(checks: list[DoctorCheck], key: str) -> str:
    for check in checks:
        for detail_key, detail_value in check.details:
            if detail_key == key:
                return detail_value
    return "NOT_AVAILABLE"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
