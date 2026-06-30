"""Risk-proportionate deterministic gate rules."""

from __future__ import annotations

from dataclasses import dataclass

from src.contracts import CLEAN_CORE, HIGH, LOW, MEDIUM, NEEDS_USER_GATE, NOT_CHECKED, NOT_CHECKED_IMPACT_RISKS
from src.classify import Classification


@dataclass(frozen=True)
class LawResult:
    status: str
    status_reasons: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "status_reasons": list(self.status_reasons),
        }


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
        return LawResult(status=NEEDS_USER_GATE, status_reasons=reasons)
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
