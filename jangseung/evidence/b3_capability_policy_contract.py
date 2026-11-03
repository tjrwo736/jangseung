"""Capability names recognized in structured executor actions."""

from __future__ import annotations

CAPABILITY_FIELDS = (
    "raw_shell_authority",
    "write_file_authority",
    "run_command_authority",
    "process_spawn_authority",
    "network_authority",
    "provider_model_call_authority",
    "remote_write_authority",
    "repo_outside_write_authority",
    "aeg_state_write_authority",
    "aeg_state_read_authority",
    "env_read_authority",
    "secret_read_authority",
)
