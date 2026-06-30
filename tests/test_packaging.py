import importlib
import sys
import unittest
from pathlib import Path


try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - only relevant on Python 3.10
    tomllib = None


REPO_ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(tomllib is None, "tomllib is unavailable")
class PackagingMetadataTests(unittest.TestCase):
    def test_console_script_points_at_existing_cli_main(self):
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(pyproject["project"]["name"], "aegis-runtime")
        self.assertEqual(pyproject["project"]["dependencies"], [])
        self.assertEqual(pyproject["project"]["scripts"]["aeg"], "src.cli:main")

        module_name, function_name = pyproject["project"]["scripts"]["aeg"].split(":", 1)
        module = importlib.import_module(module_name)
        self.assertTrue(callable(getattr(module, function_name)))

    def test_python_version_floor_matches_runtime_syntax(self):
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(pyproject["project"]["requires-python"], ">=3.10")
        self.assertGreaterEqual(sys.version_info, (3, 10))

    def test_readme_sandbox_quickstart_preseeds_runtime_ignores(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn('printf ".aeg/\\n.env\\n.env.*\\n" > .gitignore', readme)
        self.assertIn('git add README.md .gitignore', readme)
        self.assertIn('git commit -m "init sandbox repo"', readme)
        self.assertIn("python3 -m pip install -e .", readme)
        self.assertIn(
            "For a disposable local test, you may install inside a temporary virtual\n"
            "environment instead of your system Python.",
            readme,
        )
        self.assertIn(
            "Aegis writes\n"
            "folder-local runtime state under `.aeg/`; the target repository must\n"
            "git-ignore `.aeg/` before running Aegis.",
            readme,
        )
        self.assertIn(
            "`.aeg/` is local runtime state. Keep it in the\n"
            "target repo folder, but do not commit it.",
            readme,
        )
        self.assertIn(
            "If `.aeg/` is not ignored in the target repo, `aeg doctor` will report a\n"
            "problem. This is expected; fix it by adding `.aeg/` to `.gitignore`.",
            readme,
        )
        self.assertIn(
            "`REPLAY_CONSISTENT` means Aegis replayed the recorded evidence and binding\n"
            "deterministically. It is not an external oracle and does not mean the requested\n"
            "task was actually executed.",
            readme,
        )

        self.assertIn(
            "aeg doctor\n"
            "aeg init\n"
            "aeg doctor\n"
            'aeg run "fix typo in README"\n'
            "aeg verify\n"
            'aeg run "merge to main and deploy"\n'
            "aeg verify",
            readme,
        )


if __name__ == "__main__":
    unittest.main()
