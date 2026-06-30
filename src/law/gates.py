"""Risk-proportionate deterministic gate rules."""

from __future__ import annotations

from dataclasses import dataclass

from src.contracts import (
    CLEAN_CORE,
    HIGH,
    LOW,
    MEDIUM,
    NEEDS_USER_GATE,
    NOT_CHECKED,
    NOT_CHECKED_IMPACT_RISKS,
    SAFE_DEFAULT,
)
from src.classify import Classification


@dataclass(frozen=True)
class LawResult:
    status: str
    status_reasons: list[str]
    user_gate_reason_card: dict[str, object] | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "status": self.status,
            "status_reasons": list(self.status_reasons),
        }
        if self.user_gate_reason_card is not None:
            result["user_gate_reason_card"] = dict(self.user_gate_reason_card)
        return result


def apply_law(classification: Classification) -> LawResult:
    risk = classification.risk_level
    if risk == HIGH:
        reasons = [
            "law.high.requires_user_gate",
            "law.high.irreversible_action_blocked",
            "law.stop_precedence.provider_cannot_override",
        ]
        if classification.impact_risk in NOT_CHECKED_IMPACT_RISKS:
            reasons.append("law.impact.not_checked_is_not_pass")
        return LawResult(
            status=NEEDS_USER_GATE,
            status_reasons=reasons,
            user_gate_reason_card={
                "risk_level": classification.risk_level,
                "status": NEEDS_USER_GATE,
                "why_gate_is_required": "High-risk task requires an explicit user gate before execution.",
                "irreversible_action_blocked": True,
                "intent_risk": classification.intent_risk,
                "impact_risk": classification.impact_risk,
                "protected_paths_touched": list(classification.protected_paths_touched),
                "safe_default": SAFE_DEFAULT,
            },
        )
    if classification.impact_risk in NOT_CHECKED_IMPACT_RISKS:
        return LawResult(
            status=NOT_CHECKED,
            status_reasons=[
                "law.impact.changed_files_source_not_checked",
                "law.not_checked_is_not_pass",
                "law.safe_default_hold_current_state",
            ],
        )
    if risk == MEDIUM:
        return LawResult(
            status=NOT_CHECKED,
            status_reasons=[
                "law.medium.evidence_binding_required",
                "law.medium.completion_contract_placeholder_required",
                "law.not_checked_is_not_pass",
            ],
        )
    if risk == LOW:
        return LawResult(
            status=CLEAN_CORE,
            status_reasons=[
                "law.low.light_local_evidence",
                "law.low.noop_executor_allowed",
                "law.low.irreversible_action_still_forbidden",
            ],
        )
    return LawResult(
        status=NOT_CHECKED,
        status_reasons=["law.unknown_risk.safe_default_hold_current_state"],
    )
