"""Hash-format helper shared by the tamper-evident hook ledger."""

from __future__ import annotations


def is_sha256_hex(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)
