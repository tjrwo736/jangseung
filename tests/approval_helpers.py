"""Authorize fixture rules through the same personal CLI a user runs."""

import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from jangseung.cli.policy import cmd_policy_add, policy_path


def isolate_unittest_home():
    """Also isolate unittest discover, which does not load pytest's conftest."""
    temp = tempfile.TemporaryDirectory()
    unittest.addModuleCleanup(temp.cleanup)
    mock = patch("jangseung.state.approvals._user_home", return_value=Path(temp.name))
    mock.start()
    unittest.addModuleCleanup(mock.stop)


def approve(project, **rules):
    # Tests which change the policy repeatedly model replacing it, not merging.
    policy_path(project).unlink(missing_ok=True)
    if any(rules.values()):
        out = io.StringIO()
        code = cmd_policy_add(project, commands=rules.get("allow_commands", ()),
                              allow_paths=rules.get("allow_paths", ()), protect_paths=rules.get("protect_paths", ()),
                              mcp_tools=rules.get("allow_mcp_tools", ()), input_stream=io.StringIO("y\n"), output_stream=out)
        assert code == 0, out.getvalue()
