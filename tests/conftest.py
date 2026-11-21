"""Shared test setup."""

import os
import pytest

# Hook processes started by tests judge every call themselves. A resident judging
# process (jangseung._resident) would outlive the test that started it; the tests
# in test_resident.py turn it back on in a private LOCALAPPDATA and stop it.
os.environ["JANGSEUNG_RESIDENT"] = "off"


@pytest.fixture(autouse=True)
def isolated_approval_home(tmp_path_factory, monkeypatch):
    # Inject only the OS user-profile lookup, not the project identity, file
    # validation, CLI confirmation, or any authorization decision.
    from jangseung.state import approvals

    home = tmp_path_factory.mktemp("user-profile")
    monkeypatch.setattr(approvals, "_user_home", lambda: home)
    return home
