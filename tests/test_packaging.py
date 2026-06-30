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


if __name__ == "__main__":
    unittest.main()
