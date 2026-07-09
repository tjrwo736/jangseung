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

    def test_readme_documents_hook_install_flow_and_honest_scope(self):
        # README.md was rewritten as the user-facing product README (Korean,
        # PreToolUse-hook framing). This locks in the actual install commands
        # and the honest-scope disclaimers so they cannot silently regress.
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        # real, verified install flow
        self.assertIn("git clone https://github.com/tjrwo736/aegis.git", readme)
        self.assertIn("python -m pip install -e .", readme)
        self.assertIn("aeg install", readme)
        self.assertIn("aeg uninstall", readme)

        # install safety properties must stay documented
        self.assertIn("project-local만 지원", readme)
        self.assertIn("병합", readme)
        self.assertIn("백업", readme)
        self.assertIn("y/N", readme)

        # honest current-scope disclaimers must stay documented
        self.assertIn("PyPI", readme)
        self.assertIn("Claude Code와 Codex에서 검증됨", readme)
        self.assertIn("Windows 네이티브", readme)
        self.assertIn("hook exit code 처리 포함 실측", readme)
        self.assertIn("macOS: 테스터 검증 진행 중", readme)
        self.assertIn("PowerShell 문법 명령은 아직 구조적으로 파싱하지 않습니다", readme)
        self.assertIn("Codex", readme)
        self.assertIn("하드코딩", readme)
        self.assertIn("스캔하는 기능은 아직 없습니다", readme)
        self.assertIn("fail-closed", readme)
        self.assertIn("3.10", readme)

        # what-it-blocks / does-not-block / limitations sections must stay present
        self.assertIn(".env", readme)
        self.assertIn(".github/workflows", readme)
        self.assertIn("rm -rf", readme)
        self.assertIn("완벽하게 안전", readme)


if __name__ == "__main__":
    unittest.main()
