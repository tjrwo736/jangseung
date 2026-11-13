"""Opt-in MCP gate: an MCP call needs a person's approval unless the project allows it.

Jangseung cannot see what an MCP server does with the arguments. A tool that
reads files or runs code can return any file, so the gate judges the call by
tool name alone and never treats an argument as safe. Calls reach this gate only
through the separate hook entry that ``aeg install --mcp`` adds.
"""

from __future__ import annotations

from jangseung.records import dataclass
TYPE_CHECKING = False
if TYPE_CHECKING:  # typing costs about 2 ms to import on every hook call
    from typing import Any

from jangseung.classify.hook_policy import HookPolicy
from jangseung.evidence.claude_code_pretooluse_input_contract import MCP_RESOURCE_READ_TOOL_NAMES
from jangseung.evidence.hook_decision_adapter import ALLOW, ASK

MCP_TOOL_APPROVED_BY_POLICY = "mcp_tool_approved_by_project_policy"
MCP_TOOL_REQUIRES_APPROVAL = "mcp_tool_requires_user_approval"
MCP_RESOURCE_READ_REQUIRES_APPROVAL = "mcp_resource_read_requires_user_approval"
MCP_GATE_REASON_CODES = (
    MCP_TOOL_APPROVED_BY_POLICY,
    MCP_TOOL_REQUIRES_APPROVAL,
    MCP_RESOURCE_READ_REQUIRES_APPROVAL,
)


@dataclass(frozen=True)
class McpToolGateResult:
    hook_decision: str
    reasons: tuple[str, ...]
    resource_read: bool
    approved_by_policy: bool

    def to_record(self) -> dict[str, Any]:
        return {
            "resource_read": self.resource_read,
            "approved_by_policy": self.approved_by_policy,
            "arguments_inspected": False,
        }


def judge_mcp_tool_call(tool_name: str, policy: HookPolicy) -> McpToolGateResult:
    if tool_name in MCP_RESOURCE_READ_TOOL_NAMES:
        # The policy names tools, not servers, so no entry approves a resource read.
        return McpToolGateResult(ASK, (MCP_RESOURCE_READ_REQUIRES_APPROVAL,), True, False)
    if policy.approves_mcp_tool(tool_name):
        return McpToolGateResult(ALLOW, (MCP_TOOL_APPROVED_BY_POLICY,), False, True)
    return McpToolGateResult(ASK, (MCP_TOOL_REQUIRES_APPROVAL,), False, False)


__all__ = [
    "MCP_GATE_REASON_CODES",
    "MCP_RESOURCE_READ_REQUIRES_APPROVAL",
    "MCP_TOOL_APPROVED_BY_POLICY",
    "MCP_TOOL_REQUIRES_APPROVAL",
    "McpToolGateResult",
    "judge_mcp_tool_call",
]
