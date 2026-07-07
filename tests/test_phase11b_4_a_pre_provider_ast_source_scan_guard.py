import unittest
from pathlib import Path

from src.evidence.pre_provider_ast_source_scan_guard import (
    PRE_PROVIDER_AST_SOURCE_SCAN_GUARD_VERSION,
    PreProviderAstFinding,
    scan_pre_provider_paths,
    scan_pre_provider_source,
)


DOC_PATH = Path("docs/phase11b_4_a_pre_provider_ast_source_scan_guard_v0.md")
HELPER_PATH = Path("src/evidence/pre_provider_ast_source_scan_guard.py")
TEST_PATH = Path("tests/test_phase11b_4_a_pre_provider_ast_source_scan_guard.py")
BASELINE_DOC_PATH = Path("docs/phase11b_4_pre_provider_completion_baseline_v0.md")

COMPLETE_LABEL = (
    "PHASE11B_4_A_PRE_PROVIDER_AST_SOURCE_SCAN_GUARD_COMPLETE_NOT_PROVIDER"
)

REQUIRED_STATUS_MARKERS = (
    "provider/model/network implementation = NOT_STARTED / NOT_GRANTED",
    "provider SDK import = NOT_ADDED",
    "network client implementation = NOT_ADDED",
    "API key/env/secret loading = NOT_ADDED",
    "action execution engine = NOT_STARTED",
    "write authority = NOT_GRANTED",
    "tool runtime = NOT_STARTED / NOT_GRANTED",
    "store routing = NOT_GRANTED",
    "patch application = NOT_STARTED",
    "autonomous loop = NOT_STARTED",
    "live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD",
    "safe default = hold_current_state",
    "main merge = NOT_PERFORMED",
)

REQUIRED_PROVENANCE_MARKERS = (
    "current main SHA = d004e02f01852b59ac6ae9137a8200f6e6b81c7b",
    "PR #100 merge commit = d004e02f01852b59ac6ae9137a8200f6e6b81c7b",
    "PR #100 merged_at = 2026-07-07T03:11:47Z",
    "source_of_truth = GitHub metadata / merged main",
    "stale local pre-merge snapshot SHA = 2cf5dfabdceb2ec038bdf7be932fb38b7d92bb4d",
    "stale local pre-merge snapshot SHA != current main SHA",
)

FORBIDDEN_LABELS = (
    "LIVE_EXECUTOR_" + "READY",
    "MODEL_EXECUTOR_" + "READY",
    "PROVIDER_" + "READY",
    "NETWORK_" + "READY",
    "ACTION_EXECUTION_" + "READY",
    "WRITE_AUTHORITY_" + "SAFE",
    "MUTATION_AUTHORITY_" + "GRANTED",
    "TOOL_RUNTIME_" + "READY",
    "PATCH_" + "APPLIED",
    "BYPASS_" + "IMPOSSIBLE",
    "TAMPER_" + "PROOF",
    "LIVE-" + "READY",
    "WRITE-" + "SAFE",
    "ARBITRARY-CODE-" + "SAFE",
)


class Phase11B4APreProviderAstSourceScanGuardTests(unittest.TestCase):
    def test_guard_records_expected_version_and_structured_finding_shape(self):
        findings = scan_pre_provider_source("import openai\n")

        self.assertEqual(
            PRE_PROVIDER_AST_SOURCE_SCAN_GUARD_VERSION,
            "phase11b_4_a_pre_provider_ast_source_scan_guard_v0",
        )
        self.assertTrue(findings)
        self.assertIsInstance(findings[0], PreProviderAstFinding)
        finding_dict = findings[0].as_dict()
        for key in (
            "finding_type",
            "symbol",
            "lineno",
            "col_offset",
            "reason",
            "severity",
            "source_surface",
            "is_executable_surface",
        ):
            with self.subTest(key=key):
                self.assertIn(key, finding_dict)
        self.assertTrue(finding_dict["is_executable_surface"])

    def test_catches_import_openai(self):
        self._assert_finding(
            "import openai\n",
            "provider_sdk_import",
            "openai",
        )

    def test_catches_from_openai_import_openai_class(self):
        self._assert_finding(
            "from openai import OpenAI\n",
            "provider_sdk_import",
            "openai.OpenAI",
        )

    def test_catches_provider_model_sdk_imports(self):
        cases = (
            ("import anthropic\n", "anthropic"),
            ("import google.generativeai\n", "google.generativeai"),
            ("import cohere\n", "cohere"),
            ("import litellm\n", "litellm"),
            ("import ollama\n", "ollama"),
            ("from anthropic import Anthropic\n", "anthropic.Anthropic"),
        )
        for source, symbol in cases:
            with self.subTest(symbol=symbol):
                self._assert_finding(source, "provider_sdk_import", symbol)

    def test_catches_import_requests_alias(self):
        self._assert_finding(
            "import requests as r\n",
            "network_client_import",
            "requests",
        )

    def test_catches_from_urllib_import_request(self):
        self._assert_finding(
            "from urllib import request\n",
            "network_client_import",
            "urllib.request",
        )

    def test_catches_network_client_imports_and_calls(self):
        cases = (
            ("import httpx\n", "network_client_import", "httpx"),
            ("import urllib.request\n", "network_client_import", "urllib.request"),
            ("import socket\n", "network_client_import", "socket"),
            ("import aiohttp\n", "network_client_import", "aiohttp"),
            (
                "import requests\nrequests.get('https://example.invalid')\n",
                "network_client_call",
                "requests.get",
            ),
            (
                "import requests\nrequests.post('https://example.invalid')\n",
                "network_client_call",
                "requests.post",
            ),
            (
                "import httpx\nhttpx.Client()\n",
                "network_client_call",
                "httpx.Client",
            ),
            (
                "import socket\nsocket.socket()\n",
                "network_client_call",
                "socket.socket",
            ),
        )
        for source, finding_type, symbol in cases:
            with self.subTest(symbol=symbol):
                self._assert_finding(source, finding_type, symbol)

    def test_catches_importlib_import_module_openai(self):
        self._assert_finding(
            "import importlib\nimportlib.import_module('openai')\n",
            "dynamic_import_call",
            "openai",
        )

    def test_catches_importlib_import_module_requests(self):
        self._assert_finding(
            "import importlib\nimportlib.import_module('requests')\n",
            "dynamic_import_call",
            "requests",
        )

    def test_catches_invalid_token_dynamic_import_openai(self):
        self._assert_finding(
            'import("openai")\n',
            "dynamic_import_call",
            "openai",
        )

    def test_catches_invalid_token_dynamic_import_requests(self):
        self._assert_finding(
            'import("requests")\n',
            "dynamic_import_call",
            "requests",
        )

    def test_catches_os_environ(self):
        self._assert_finding(
            "import os\nvalue = os.environ['OPENAI_API_KEY']\n",
            "env_secret_loading",
            "os.environ",
        )

    def test_catches_os_getenv(self):
        self._assert_finding(
            "import os\nvalue = os.getenv('OPENAI_API_KEY')\n",
            "env_secret_loading",
            "os.getenv",
        )

    def test_catches_dotenv_load_dotenv(self):
        self._assert_finding(
            "import dotenv\ndotenv.load_dotenv()\n",
            "env_secret_loading",
            "dotenv.load_dotenv",
        )

    def test_catches_open_dotenv(self):
        self._assert_finding(
            "open('.env')\n",
            "env_secret_loading",
            "open(.env)",
        )

    def test_catches_path_dotenv_read_text(self):
        self._assert_finding(
            "from pathlib import Path\nPath('.env').read_text()\n",
            "env_secret_loading",
            "Path(.env).read_text",
        )

    def test_catches_read_text_on_dotenv_path_variable(self):
        self._assert_finding(
            "from pathlib import Path\np = Path('.env')\np.read_text()\n",
            "env_secret_loading",
            "Path(.env).read_text",
        )

    def test_catches_provider_context_sensitive_variable_name(self):
        self._assert_finding(
            "openai_api_key = 'redacted-test-fixture'\n",
            "provider_context_sensitive_name",
            "openai_api_key",
        )

    def test_catches_subprocess_run(self):
        self._assert_finding(
            "import subprocess\nsubprocess.run(['true'])\n",
            "shell_process_call",
            "subprocess.run",
        )

    def test_catches_subprocess_popen(self):
        self._assert_finding(
            "import subprocess\nsubprocess.Popen(['true'])\n",
            "shell_process_call",
            "subprocess.Popen",
        )

    def test_catches_os_system(self):
        self._assert_finding(
            "import os\nos.system('true')\n",
            "shell_process_call",
            "os.system",
        )

    def test_catches_eval_exec_compile(self):
        cases = (
            ("eval('1')\n", "eval"),
            ("exec('x = 1')\n", "exec"),
            ("compile('x = 1', '<fixture>', 'exec')\n", "compile"),
        )
        for source, symbol in cases:
            with self.subTest(symbol=symbol):
                self._assert_finding(source, "code_execution_call", symbol)

    def test_catches_runpy_run_path(self):
        self._assert_finding(
            "import runpy\nrunpy.run_path('script.py')\n",
            "shell_process_call",
            "runpy.run_path",
        )

    def test_catches_importlib_dynamic_loading_surfaces(self):
        self._assert_finding(
            (
                "import importlib.util\n"
                "importlib.util.spec_from_file_location('x', 'x.py')\n"
            ),
            "dynamic_import_call",
            "importlib.util.spec_from_file_location",
        )

    def test_distinguishes_documentation_strings_from_executable_surfaces(self):
        source = '''
"""Forbidden text mentions OpenAI/Ollama/LLM/API key/env/secret/network.

Examples that must remain text-only here:
import openai
from openai import OpenAI
requests.get("https://example.invalid")
Path(".env").read_text()
subprocess.run(["true"])
eval("1")
"""

FORBIDDEN_SCOPE_TEXT_ONLY = """
provider/model/network = NOT_STARTED / NOT_GRANTED
API key/env/secret loading = NOT_STARTED / NOT_GRANTED
"""

# import requests
# os.environ
'''

        findings = scan_pre_provider_source(source)

        self.assertEqual(findings, ())

    def test_changed_phase_files_pass_ast_guard_except_text_fixtures(self):
        findings = scan_pre_provider_paths(
            (
                HELPER_PATH,
                TEST_PATH,
                BASELINE_DOC_PATH,
                DOC_PATH,
            )
        )

        self.assertEqual(findings, ())

    def test_ast_guard_doc_records_label_status_and_provenance(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        self.assertIn(COMPLETE_LABEL, doc)
        for marker in REQUIRED_STATUS_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)
        for marker in REQUIRED_PROVENANCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_ast_guard_doc_does_not_claim_forbidden_ready_or_safety_labels(self):
        doc_lines = {
            line.strip() for line in DOC_PATH.read_text(encoding="utf-8").splitlines()
        }

        for label in FORBIDDEN_LABELS:
            with self.subTest(label=label):
                self.assertNotIn(label, doc_lines)

    def _assert_finding(
        self,
        source: str,
        finding_type: str,
        symbol: str,
    ) -> None:
        findings = scan_pre_provider_source(source)

        self.assertTrue(
            any(
                finding.finding_type == finding_type and finding.symbol == symbol
                for finding in findings
            ),
            msg=f"expected {finding_type}:{symbol}, got {findings!r}",
        )
        for finding in findings:
            self.assertTrue(finding.is_executable_surface)


if __name__ == "__main__":
    unittest.main()
