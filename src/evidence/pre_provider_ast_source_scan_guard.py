"""Phase 11-B-4-A pre-provider AST source scan guard.

This helper parses Python source and reports executable/import surfaces that
must remain absent before a separate provider gate exists. It does not import
provider SDKs, network clients, process helpers, or environment loaders.
"""

from __future__ import annotations

import ast
import io
import tokenize
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PRE_PROVIDER_AST_SOURCE_SCAN_GUARD_VERSION = (
    "phase11b_4_a_pre_provider_ast_source_scan_guard_v0"
)

PROVIDER_SDK_MODULES = frozenset(
    (
        "openai",
        "anthropic",
        "google.generativeai",
        "cohere",
        "litellm",
        "ollama",
    )
)

NETWORK_CLIENT_MODULES = frozenset(
    (
        "requests",
        "httpx",
        "urllib.request",
        "socket",
        "aiohttp",
    )
)

NETWORK_CLIENT_CALLS = frozenset(
    (
        "requests.get",
        "requests.post",
        "httpx.Client",
        "socket.socket",
    )
)

DYNAMIC_IMPORT_CALLS = frozenset(
    (
        "importlib.import_module",
        "__import__",
    )
)

IMPORTLIB_DYNAMIC_LOADING_CALLS = frozenset(
    (
        "importlib.util.spec_from_file_location",
        "importlib.util.module_from_spec",
        "importlib.machinery.SourceFileLoader",
        "importlib.machinery.FileFinder",
    )
)

ENV_LOADING_CALLS = frozenset(
    (
        "os.getenv",
        "dotenv.load_dotenv",
    )
)

SHELL_PROCESS_CALLS = frozenset(
    (
        "subprocess.run",
        "subprocess.Popen",
        "os.system",
        "runpy.run_path",
    )
)

BUILTIN_CODE_EXECUTION_CALLS = frozenset(("eval", "exec", "compile"))

_PROVIDER_CONTEXT_TERMS = frozenset(
    (
        "openai",
        "anthropic",
        "gemini",
        "generativeai",
        "google_generativeai",
        "cohere",
        "litellm",
        "ollama",
        "provider",
        "llm",
        "model",
    )
)

_SENSITIVE_NAME_MARKERS = frozenset(("api_key", "secret", "token", "password"))


@dataclass(frozen=True)
class PreProviderAstFinding:
    """Structured finding for an executable/import source surface."""

    finding_type: str
    symbol: str
    lineno: int
    col_offset: int
    reason: str
    severity: str
    source_surface: str
    is_executable_surface: bool = True
    path: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "finding_type": self.finding_type,
            "symbol": self.symbol,
            "lineno": self.lineno,
            "col_offset": self.col_offset,
            "reason": self.reason,
            "severity": self.severity,
            "source_surface": self.source_surface,
            "is_executable_surface": self.is_executable_surface,
            "path": self.path,
        }


def scan_pre_provider_source(
    source: str,
    *,
    path: str = "<memory>",
) -> tuple[PreProviderAstFinding, ...]:
    """Return AST findings for pre-provider forbidden executable surfaces."""

    findings: list[PreProviderAstFinding] = []
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return tuple(_scan_token_dynamic_import_calls(source, path=path))

    aliases = _collect_import_aliases(tree)
    env_path_names = _collect_env_path_names(tree, aliases)
    provider_context = _has_provider_context(tree, aliases)

    visitor = _PreProviderSurfaceVisitor(
        aliases=aliases,
        env_path_names=env_path_names,
        provider_context=provider_context,
        path=path,
    )
    visitor.visit(tree)
    findings.extend(visitor.findings)
    findings.extend(_scan_token_dynamic_import_calls(source, path=path))

    return tuple(
        sorted(
            _deduplicate_findings(findings),
            key=lambda finding: (
                finding.path,
                finding.lineno,
                finding.col_offset,
                finding.finding_type,
                finding.symbol,
            ),
        )
    )


def scan_pre_provider_paths(
    paths: Iterable[str | Path],
    *,
    python_suffixes: Sequence[str] = (".py",),
) -> tuple[PreProviderAstFinding, ...]:
    """Scan Python source paths and skip non-Python text by default."""

    findings: list[PreProviderAstFinding] = []
    suffixes = tuple(python_suffixes)
    for source_path in paths:
        path = Path(source_path)
        if suffixes and path.suffix not in suffixes:
            continue
        source = path.read_text(encoding="utf-8")
        findings.extend(scan_pre_provider_source(source, path=path.as_posix()))
    return tuple(findings)


def _collect_import_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
                else:
                    local_name = alias.name.split(".", 1)[0]
                    aliases[local_name] = local_name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            module = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    continue
                symbol = f"{module}.{alias.name}" if module else alias.name
                local_name = alias.asname or alias.name
                aliases[local_name] = symbol
    return aliases


def _collect_env_path_names(
    tree: ast.AST,
    aliases: dict[str, str],
) -> frozenset[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        value: ast.AST | None = None
        targets: Sequence[ast.expr] = ()
        if isinstance(node, ast.Assign):
            value = node.value
            targets = tuple(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value = node.value
            targets = (node.target,)

        if value is None or not _is_env_path_value(value, aliases):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return frozenset(names)


def _has_provider_context(tree: ast.AST, aliases: dict[str, str]) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for symbol in _import_symbols_from_node(node):
                if _matches_provider_module(symbol):
                    return True
        elif isinstance(node, ast.Call):
            symbol = _resolve_symbol(node.func, aliases)
            target = _first_string_arg(node)
            if symbol in DYNAMIC_IMPORT_CALLS and target:
                if _matches_provider_module(target):
                    return True
    return False


def _import_symbols_from_node(node: ast.Import | ast.ImportFrom) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)

    if node.level:
        return ()
    module = node.module or ""
    symbols: list[str] = []
    for alias in node.names:
        if alias.name == "*":
            continue
        symbol = f"{module}.{alias.name}" if module else alias.name
        symbols.append(symbol)
        if module:
            symbols.append(module)
    return tuple(symbols)


class _PreProviderSurfaceVisitor(ast.NodeVisitor):
    def __init__(
        self,
        *,
        aliases: dict[str, str],
        env_path_names: frozenset[str],
        provider_context: bool,
        path: str,
    ) -> None:
        self.aliases = aliases
        self.env_path_names = env_path_names
        self.provider_context = provider_context
        self.path = path
        self.findings: list[PreProviderAstFinding] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._record_import_symbol(alias.name, node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level:
            return
        module = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                continue
            symbol = f"{module}.{alias.name}" if module else alias.name
            self._record_import_symbol(symbol, node)
            if module:
                self._record_import_symbol(module, node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        symbol = _resolve_symbol(node.func, self.aliases)
        target = _first_string_arg(node)

        if symbol in DYNAMIC_IMPORT_CALLS:
            target_symbol = target or symbol
            self._add(
                "dynamic_import_call",
                target_symbol,
                node,
                "dynamic import call before provider gate",
                "HIGH",
                "ast_call",
            )
        elif symbol in IMPORTLIB_DYNAMIC_LOADING_CALLS:
            self._add(
                "dynamic_import_call",
                symbol,
                node,
                "importlib dynamic loading call before provider gate",
                "HIGH",
                "ast_call",
            )
        elif symbol in NETWORK_CLIENT_CALLS:
            self._add(
                "network_client_call",
                symbol,
                node,
                "network client call before provider/network gate",
                "HIGH",
                "ast_call",
            )
        elif symbol in ENV_LOADING_CALLS:
            self._add(
                "env_secret_loading",
                symbol,
                node,
                "environment or dotenv loading before provider gate",
                "HIGH",
                "ast_call",
            )
        elif symbol == "open" and target and _is_env_path_string(target):
            self._add(
                "env_secret_loading",
                "open(.env)",
                node,
                ".env file open before provider secret gate",
                "HIGH",
                "ast_call",
            )
        elif _is_env_read_text_call(node, self.aliases, self.env_path_names):
            self._add(
                "env_secret_loading",
                "Path(.env).read_text",
                node,
                ".env read_text before provider secret gate",
                "HIGH",
                "ast_call",
            )
        elif symbol in SHELL_PROCESS_CALLS:
            self._add(
                "shell_process_call",
                symbol,
                node,
                "shell/process call before provider gate",
                "HIGH",
                "ast_call",
            )
        elif symbol in BUILTIN_CODE_EXECUTION_CALLS:
            self._add(
                "code_execution_call",
                symbol,
                node,
                "eval/exec/compile call before provider gate",
                "HIGH",
                "ast_call",
            )

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        symbol = _resolve_symbol(node, self.aliases)
        if symbol == "os.environ" or symbol.startswith("os.environ."):
            self._add(
                "env_secret_loading",
                "os.environ",
                node,
                "process environment access before provider secret gate",
                "HIGH",
                "ast_attribute",
            )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._record_sensitive_target(target, node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._record_sensitive_target(node.target, node)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        if _is_sensitive_provider_name(node.arg, self.provider_context):
            self._add(
                "provider_context_sensitive_name",
                node.arg,
                node,
                "provider-context sensitive variable name before provider gate",
                "MEDIUM",
                "ast_argument",
            )
        self.generic_visit(node)

    def _record_import_symbol(
        self,
        symbol: str,
        node: ast.Import | ast.ImportFrom,
    ) -> None:
        if _matches_provider_module(symbol):
            self._add(
                "provider_sdk_import",
                symbol,
                node,
                "provider/model SDK import before provider gate",
                "HIGH",
                "ast_import",
            )
        elif _matches_network_module(symbol):
            self._add(
                "network_client_import",
                symbol,
                node,
                "network client import before network gate",
                "HIGH",
                "ast_import",
            )

    def _record_sensitive_target(self, target: ast.AST, node: ast.AST) -> None:
        for name in _target_names(target):
            if _is_sensitive_provider_name(name, self.provider_context):
                self._add(
                    "provider_context_sensitive_name",
                    name,
                    node,
                    "provider-context sensitive variable name before provider gate",
                    "MEDIUM",
                    "ast_assignment",
                )

    def _add(
        self,
        finding_type: str,
        symbol: str,
        node: ast.AST,
        reason: str,
        severity: str,
        source_surface: str,
    ) -> None:
        self.findings.append(
            PreProviderAstFinding(
                finding_type=finding_type,
                symbol=symbol,
                lineno=getattr(node, "lineno", 0),
                col_offset=getattr(node, "col_offset", 0),
                reason=reason,
                severity=severity,
                source_surface=source_surface,
                is_executable_surface=True,
                path=self.path,
            )
        )


def _target_names(target: ast.AST) -> tuple[str, ...]:
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in target.elts:
            names.extend(_target_names(element))
        return tuple(names)
    return ()


def _is_sensitive_provider_name(name: str, provider_context: bool) -> bool:
    normalized = name.lower()
    has_sensitive_marker = any(
        marker in normalized for marker in _SENSITIVE_NAME_MARKERS
    )
    if not has_sensitive_marker:
        return False
    has_provider_term = any(term in normalized for term in _PROVIDER_CONTEXT_TERMS)
    return provider_context or has_provider_term


def _resolve_symbol(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        base = _resolve_symbol(node.value, aliases)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _first_string_arg(node: ast.Call) -> str | None:
    if not node.args:
        return None
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def _matches_provider_module(symbol: str) -> bool:
    return any(_module_matches(symbol, module) for module in PROVIDER_SDK_MODULES)


def _matches_network_module(symbol: str) -> bool:
    return any(_module_matches(symbol, module) for module in NETWORK_CLIENT_MODULES)


def _module_matches(symbol: str, module: str) -> bool:
    return symbol == module or symbol.startswith(f"{module}.")


def _is_env_read_text_call(
    node: ast.Call,
    aliases: dict[str, str],
    env_path_names: frozenset[str],
) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "read_text":
        return False

    value = func.value
    if isinstance(value, ast.Name) and value.id in env_path_names:
        return True
    return _is_env_path_value(value, aliases)


def _is_env_path_value(node: ast.AST, aliases: dict[str, str]) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return _is_env_path_string(node.value)
    if isinstance(node, ast.Call):
        symbol = _resolve_symbol(node.func, aliases)
        first_arg = _first_string_arg(node)
        return (
            symbol in {"Path", "pathlib.Path"}
            and first_arg is not None
            and _is_env_path_string(first_arg)
        )
    return False


def _is_env_path_string(value: str) -> bool:
    normalized = value.replace("\\", "/").rstrip("/")
    if not normalized:
        return False
    final_part = normalized.rsplit("/", 1)[-1]
    return final_part == ".env" or final_part.startswith(".env.")


def _scan_token_dynamic_import_calls(
    source: str,
    *,
    path: str,
) -> tuple[PreProviderAstFinding, ...]:
    findings: list[PreProviderAstFinding] = []
    try:
        tokens = tuple(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError:
        return ()

    for index, token in enumerate(tokens[:-2]):
        next_token = tokens[index + 1]
        target_token = tokens[index + 2]
        if (
            token.type == tokenize.NAME
            and token.string == "import"
            and next_token.type == tokenize.OP
            and next_token.string == "("
            and target_token.type == tokenize.STRING
        ):
            target = _literal_string_from_token(target_token.string)
            findings.append(
                PreProviderAstFinding(
                    finding_type="dynamic_import_call",
                    symbol=target or "import(...)",
                    lineno=token.start[0],
                    col_offset=token.start[1],
                    reason="dynamic import call token before provider gate",
                    severity="HIGH",
                    source_surface="token_call",
                    is_executable_surface=True,
                    path=path,
                )
            )
    return tuple(findings)


def _literal_string_from_token(token_text: str) -> str | None:
    try:
        value = ast.literal_eval(token_text)
    except (SyntaxError, ValueError):
        return None
    if isinstance(value, str):
        return value
    return None


def _deduplicate_findings(
    findings: Iterable[PreProviderAstFinding],
) -> tuple[PreProviderAstFinding, ...]:
    seen: set[tuple[Any, ...]] = set()
    deduplicated: list[PreProviderAstFinding] = []
    for finding in findings:
        key = (
            finding.finding_type,
            finding.symbol,
            finding.lineno,
            finding.col_offset,
            finding.source_surface,
            finding.path,
        )
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(finding)
    return tuple(deduplicated)


__all__ = [
    "BUILTIN_CODE_EXECUTION_CALLS",
    "DYNAMIC_IMPORT_CALLS",
    "ENV_LOADING_CALLS",
    "IMPORTLIB_DYNAMIC_LOADING_CALLS",
    "NETWORK_CLIENT_CALLS",
    "NETWORK_CLIENT_MODULES",
    "PRE_PROVIDER_AST_SOURCE_SCAN_GUARD_VERSION",
    "PROVIDER_SDK_MODULES",
    "SHELL_PROCESS_CALLS",
    "PreProviderAstFinding",
    "scan_pre_provider_paths",
    "scan_pre_provider_source",
]
