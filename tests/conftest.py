"""Shared test setup."""

import os

# Hook processes started by tests judge every call themselves. A resident judging
# process (jangseung._resident) would outlive the test that started it; the tests
# in test_resident.py turn it back on in a private LOCALAPPDATA and stop it.
os.environ["JANGSEUNG_RESIDENT"] = "off"
