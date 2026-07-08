import inspect
import unittest
from pathlib import Path

from src.contracts import (
    CLEAN_CORE,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NEEDS_USER_GATE,
    NOT_CHECKED,
    SAFE_DEFAULT,
)
from src.evidence import hook_judgment_engine_alignment
from src.evidence.hook_decision_adapter import ALLOW, ASK, DEFER, DENY
from src.evidence.hook_judgment_engine_alignment import (
    ENGINE_BASIS_SOURCES,
    PHASE11C_8_COMPLETE_LABEL,
    build_hook_judgment_engine_alignment_evidence,
    judge_pretooluse_with_aeg_engine,
)
from src.evidence.structured_action_capabilities import (
    CAPABILITY_DENIED,
    CAPABILITY_GATE_LIMITED_ALLOWED,
    SCOPE_LIMIT_REJECTED,
)


DOC_PATH = Path("docs/phase11c_8_hook_judgment_engine_alignment_v0.md")
REPO_ROOT = Path.cwd()


class Phase11C8HookJudgmentEngineAlignmentTests(unittest.TestCase):
    def test_write_and_edit_github_workflow_do_not_leak_as_ask(self):
        for tool_name, tool_input in (
            ("Write", {"file_path": ".github/workflows/ci.yml", "content": "data"}),
            (
                "Edit",
                {
                    "file_path": ".github/workflows/ci.yml",
                    "old_string": "old",
                    "new_string": "new",
                },
            ),
        ):
            with self.subTest(tool_name=tool_name):
                decision = self._judge(tool_name, tool_input)

                self.assertEqual(decision.engine_decision, DENY)
                self.assertEqual(decision.hook_decision, DENY)
                self.assertNotEqual(decision.hook_decision, ASK)
                self._assert_engine_basis_includes_protected_path(
                    decision,
                    ".github/workflows/ci.yml",
                )
                self._assert_engine_parity(decision)

    def test_required_protected_write_edit_paths_deny_with_engine_basis(self):
        cases = (
            ("Write", {"file_path": "Dockerfile", "content": "data"}, "Dockerfile"),
            (
                "Edit",
                {
                    "file_path": "pyproject.toml",
                    "old_string": "old",
                    "new_string": "new",
                },
                "pyproject.toml",
            ),
            ("Write", {"file_path": "deploy/prod.yml", "content": "data"}, "deploy/prod.yml"),
            (
                "Edit",
                {
                    "file_path": "src/law/policy.py",
                    "old_string": "old",
                    "new_string": "new",
                },
                "src/law/policy.py",
            ),
        )

        for tool_name, tool_input, path in cases:
            with self.subTest(path=path):
                decision = self._judge(tool_name, tool_input)

                self.assertEqual(decision.engine_decision, DENY)
                self.assertEqual(decision.hook_decision, DENY)
                self.assertNotIn(decision.hook_decision, (ALLOW, ASK))
                self._assert_engine_basis_includes_protected_path(decision, path)
                basis = decision.engine_decision_basis
                self.assertEqual(basis["law"]["status"], NEEDS_USER_GATE)
                self.assertEqual(basis["capability_gate"]["gate_result"], CAPABILITY_DENIED)
                self._assert_engine_parity(decision)

    def test_read_env_deny_uses_protected_path_and_capability_scope_basis(self):
        decision = self._judge("Read", {"file_path": ".env"})

        self.assertEqual(decision.hook_decision, DENY)
        self.assertEqual(decision.engine_decision, DENY)
        self._assert_engine_basis_includes_protected_path(decision, ".env")
        self.assertEqual(
            decision.engine_decision_basis["capability_gate"]["gate_result"],
            SCOPE_LIMIT_REJECTED,
        )
        self.assertIn(
            "env/secret",
            decision.engine_decision_basis["capability_gate"]["gate_reason"],
        )
        self._assert_engine_parity(decision)

    def test_write_aeg_state_json_denies_through_existing_aeg_guard(self):
        decision = self._judge(
            "Write",
            {"file_path": ".aeg/state.json", "content": "data"},
        )

        self.assertEqual(decision.hook_decision, DENY)
        self.assertEqual(decision.engine_decision, DENY)
        self.assertEqual(
            decision.engine_decision_basis["capability_gate"]["gate_result"],
            CAPABILITY_DENIED,
        )
        self.assertTrue(decision.engine_decision_basis["aeg_guard"][0]["protected_target"])
        self.assertIn(
            "aeg_integrity_guard_denies_state_dir_target",
            decision.decision_reasons,
        )
        self._assert_engine_parity(decision)

    def test_traversal_and_absolute_write_paths_deny_with_repo_boundary_basis(self):
        for path in ("../outside.txt", "/absolute/path.txt"):
            with self.subTest(path=path):
                decision = self._judge(
                    "Write",
                    {"file_path": path, "content": "data"},
                )

                self.assertEqual(decision.hook_decision, DENY)
                self.assertEqual(decision.engine_decision, DENY)
                self.assertTrue(
                    decision.engine_decision_basis["repo_boundary_gate"][0][
                        "target_outside_repo"
                    ]
                )
                self.assertIn(
                    "repo_boundary_gate_denies_outside_repo_target",
                    decision.decision_reasons,
                )
                self._assert_engine_parity(decision)

    def test_normal_low_risk_read_allows_only_after_clean_engine_basis(self):
        decision = self._judge("Read", {"file_path": "docs/guide.md"})

        self.assertEqual(decision.engine_decision, ALLOW)
        self.assertEqual(decision.hook_decision, ALLOW)
        self.assertEqual(decision.engine_decision_basis["law"]["status"], CLEAN_CORE)
        self.assertEqual(
            decision.engine_decision_basis["capability_gate"]["gate_result"],
            CAPABILITY_GATE_LIMITED_ALLOWED,
        )
        self.assertFalse(
            decision.engine_decision_basis["protected_path_gate"][
                "protected_path_detected"
            ]
        )
        self._assert_engine_parity(decision)

    def test_normal_low_risk_edit_asks_via_target_path_risk_not_capability_gate(self):
        decision = self._judge(
            "Edit",
            {
                "file_path": "docs/guide.md",
                "old_string": "old",
                "new_string": "new",
            },
        )

        # Aegis's own WRITE_FILE/EDIT-shaped self-execution capability remains
        # denied (11-B propose-only policy, unchanged) but that denial is not
        # the hook judgment basis for a normal, non-protected Edit target: the
        # hook judges by target-path risk instead, so a normal low-risk edit
        # asks rather than being denied outright.
        self.assertEqual(decision.hook_decision, ASK)
        self.assertNotEqual(decision.hook_decision, DENY)
        self.assertEqual(decision.engine_decision_basis["law"]["status"], CLEAN_CORE)
        self.assertEqual(
            decision.engine_decision_basis["capability_gate"]["gate_result"],
            CAPABILITY_DENIED,
        )
        self._assert_engine_parity(decision)

    def test_dangerous_bash_git_reset_hard_and_clean_fd_deny(self):
        for command, reason in (
            ("git reset --hard", "dangerous_bash_git_reset_hard"),
            ("git clean -fd", "dangerous_bash_git_clean_force_delete"),
        ):
            with self.subTest(command=command):
                decision = self._judge("Bash", {"command": command})

                self.assertEqual(decision.engine_decision, DENY)
                self.assertEqual(decision.hook_decision, DENY)
                self.assertIn(
                    reason,
                    decision.engine_decision_basis["dangerous_bash_gate"]["reasons"],
                )
                self.assertTrue(
                    decision.engine_decision_basis["dangerous_bash_gate"][
                        "dangerous_bash"
                    ]
                )
                self._assert_engine_parity(decision)

    def test_unclassified_bash_is_deny_or_defer_never_allow(self):
        decision = self._judge("Bash", {"command": "python -m unittest"})

        self.assertIn(decision.hook_decision, (DENY, DEFER))
        self.assertNotEqual(decision.hook_decision, ALLOW)
        self.assertFalse(decision.unclassified_bash_is_allow)
        self.assertTrue(
            decision.engine_decision_basis["dangerous_bash_gate"]["unclassified_bash"]
        )
        self.assertFalse(
            decision.engine_decision_basis["dangerous_bash_gate"][
                "unclassified_bash_is_allow"
            ]
        )
        self._assert_engine_parity(decision)

    def test_unknown_tool_is_not_allow(self):
        decision = judge_pretooluse_with_aeg_engine(
            {"tool_name": "Task", "tool_input": {}, "tool_use_id": "toolu-unknown"},
            repo_root=REPO_ROOT,
        )

        self.assertEqual(decision.engine_decision, DEFER)
        self.assertEqual(decision.hook_decision, DEFER)
        self.assertNotEqual(decision.hook_decision, ALLOW)
        self.assertFalse(decision.not_checked_is_allow)
        self.assertFalse(decision.reported_only_trusted_as_judgment_basis)
        self._assert_engine_parity(decision)

    def test_not_checked_is_not_allow(self):
        decision = self._judge("Bash", {"command": NOT_CHECKED})

        self.assertNotEqual(decision.hook_decision, ALLOW)
        self.assertFalse(decision.not_checked_is_allow)
        self.assertIn(decision.hook_decision, (DENY, DEFER))
        self.assertEqual(
            decision.engine_decision_basis["law"]["status"],
            NOT_CHECKED,
        )
        self._assert_engine_parity(decision)

    def test_reported_only_is_not_judgment_basis(self):
        decision = judge_pretooluse_with_aeg_engine(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": ".github/workflows/ci.yml",
                    "content": "data",
                    "reported_only": {"decision": "allow"},
                },
                "tool_use_id": "toolu-reported-only",
                "reported_only": {"decision": "allow"},
                "basis": "reported_only",
            },
            repo_root=REPO_ROOT,
        )

        self.assertEqual(decision.hook_decision, DENY)
        self.assertFalse(decision.reported_only_trusted_as_judgment_basis)
        self.assertFalse(
            decision.engine_decision_basis["reported_only_trusted_as_judgment_basis"]
        )
        self.assertIn(
            "raw_hook_input.reported_only",
            decision.engine_decision_basis["ignored_reported_only_fields"],
        )
        self.assertIn(
            "raw_hook_input.basis",
            decision.engine_decision_basis["ignored_reported_only_fields"],
        )
        self.assertNotIn("reported_only", decision.engine_basis_sources)
        self._assert_engine_parity(decision)

    def test_hook_decision_record_includes_engine_basis(self):
        decision = self._judge("Read", {"file_path": "docs/guide.md"})
        record = decision.to_record()

        self.assertEqual(record["completion_label"], PHASE11C_8_COMPLETE_LABEL)
        self.assertIn("engine_decision_basis", record)
        self.assertEqual(record["engine_basis_sources"], ENGINE_BASIS_SOURCES)
        for key in (
            "classification",
            "law",
            "capability_gate",
            "protected_path_gate",
            "aeg_guard",
            "repo_boundary_gate",
            "dangerous_bash_gate",
        ):
            with self.subTest(key=key):
                self.assertIn(key, record["engine_decision_basis"])
        self._assert_engine_parity(decision)

    def test_alignment_evidence_records_forbidden_scope_and_reuse_points(self):
        evidence = build_hook_judgment_engine_alignment_evidence()

        self.assertEqual(evidence["completion_label"], PHASE11C_8_COMPLETE_LABEL)
        self.assertEqual(
            evidence["protected_path_policy_source"],
            "src.classify.is_protected_path",
        )
        self.assertIn("src.classify.classify_task", evidence["engine_basis_sources"])
        self.assertIn("src.law.apply_law", evidence["engine_basis_sources"])
        self.assertIn(
            "src.evidence.structured_action_capabilities.evaluate_action_capabilities",
            evidence["engine_basis_sources"],
        )
        self.assertTrue(evidence["hook_decision_matches_or_is_stricter_than_engine"])
        self.assertFalse(evidence["protected_path_policy_duplicated_in_hook"])
        self.assertFalse(evidence["hook_policy_divergence_allowed"])
        self.assertFalse(evidence["unclassified_bash_is_allow"])
        self.assertFalse(evidence["reported_only_trusted_as_judgment_basis"])
        self.assertFalse(evidence["not_checked_is_allow"])
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)
        self.assertEqual(
            evidence["live_executor_authority"],
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )
        for field in (
            "adapter_output_is_actual_hook_response",
            "hook_command_implemented",
            "hook_installation_implemented",
            "claude_code_execution_performed",
            "real_hook_response_emitted",
            "stdout_stderr_hook_output_written",
            "provider_model_network_implemented",
            "api_key_env_secret_loading_implemented",
            "store_write_binding_implemented",
            "aeg_write_performed",
            "write_authority_granted",
            "public_release_performed",
            "main_merge_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(evidence[field])

    def test_adapter_source_has_no_runtime_provider_store_or_process_surface(self):
        source = inspect.getsource(hook_judgment_engine_alignment)
        forbidden_fragments = (
            "Open" + "AI",
            "Oll" + "ama",
            "req" + "uests",
            "sock" + "et",
            "sub" + "process",
            "os." + "system",
            "po" + "pen",
            ".op" + "en(",
            "op" + "en(",
            ".write_" + "text(",
            ".write_" + "bytes(",
            ".to" + "uch(",
            ".mk" + "dir(",
            ".un" + "link(",
            ".re" + "name(",
            ".rep" + "lace(",
            "ex" + "ec(",
            "ev" + "al(",
            "__im" + "port__(",
            "import" + "lib",
            "src.state." + "store",
            "from src.state import " + "store",
            "sto" + "re.",
        )

        for forbidden_fragment in forbidden_fragments:
            with self.subTest(forbidden_fragment=forbidden_fragment):
                self.assertNotIn(forbidden_fragment, source)

    def test_doc_records_required_boundaries(self):
        doc = DOC_PATH.read_text(encoding="utf-8")

        for marker in (
            PHASE11C_8_COMPLETE_LABEL,
            "hook policy divergence was unsafe",
            "existing engine reuse rule",
            "src.classify",
            "src.law",
            "structured_action_capabilities",
            "is_protected_path",
            "dangerous Bash safety net",
            "unclassified Bash = deny/defer, never allow",
            "@ file references may not trigger Read tool calls",
            "Aegis PreToolUse governance is a tool-call boundary",
            "does not claim universal prompt-injection prevention",
            "evidence store binding is future gate",
            "no direct .aeg write",
            "actual hook install = NOT_PERFORMED",
            "stdout/stderr live hook emission = NOT_PERFORMED",
            "safe default = hold_current_state",
            "live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def _judge(self, tool_name, tool_input):
        return judge_pretooluse_with_aeg_engine(
            {
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_use_id": f"toolu-{tool_name.lower()}",
            },
            repo_root=REPO_ROOT,
        )

    def _assert_engine_basis_includes_protected_path(self, decision, path):
        basis = decision.engine_decision_basis
        self.assertIn(path, basis["classification"]["protected_paths_touched"])
        self.assertIn(path, basis["protected_path_gate"]["protected_paths"])
        self.assertTrue(basis["protected_path_gate"]["protected_path_detected"])
        self.assertEqual(
            basis["protected_path_gate"]["policy_source"],
            "src.classify.is_protected_path",
        )
        self.assertFalse(
            basis["protected_path_gate"]["protected_path_policy_duplicated_in_hook"]
        )

    def _assert_engine_parity(self, decision):
        self.assertTrue(decision.hook_decision_matches_or_is_stricter_than_engine)
        self.assertGreaterEqual(
            hook_judgment_engine_alignment.HOOK_DECISION_STRENGTH[
                decision.hook_decision
            ],
            hook_judgment_engine_alignment.HOOK_DECISION_STRENGTH[
                decision.engine_decision
            ],
        )
        self.assertFalse(decision.protected_path_policy_duplicated_in_hook)
        self.assertFalse(decision.hook_policy_divergence_allowed)
        self.assertEqual(decision.safe_default, SAFE_DEFAULT)
        self.assertEqual(
            decision.live_executor_authority,
            LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        )


class Phase11C8AbsolutePathNormalizationTests(unittest.TestCase):
    """Claude Code sends tool_input file paths as absolute paths; repo-internal
    absolute paths must normalize to repo-relative and judge normally, while
    repo-external / traversal / symlink-escape paths must still be rejected."""

    def setUp(self) -> None:
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.outside_root = Path(self._tmp.name)
        self.repo_root = self.outside_root / "repo"
        (self.repo_root / "src").mkdir(parents=True)
        (self.repo_root / "docs").mkdir(parents=True)
        (self.repo_root / ".github" / "workflows").mkdir(parents=True)
        (self.repo_root / "README.md").write_text("# r", encoding="utf-8")
        (self.repo_root / "src" / "app.py").write_text("x", encoding="utf-8")
        (self.repo_root / "docs" / "guide.md").write_text("y", encoding="utf-8")
        # sibling dir that shares the repo-name prefix (prefix-bypass vector)
        (self.outside_root / "repo-evil").mkdir()
        (self.outside_root / "repo-evil" / "secret.txt").write_text("S", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _judge(self, tool_name, tool_input):
        return judge_pretooluse_with_aeg_engine(
            {"tool_name": tool_name, "tool_input": tool_input, "tool_use_id": "toolu-x"},
            repo_root=str(self.repo_root),
        )

    def _abs(self, rel: str) -> str:
        return str(self.repo_root / rel)

    # --- repo-internal absolute normal: must NOT be scope-denied -----------

    def test_repo_internal_absolute_read_is_not_denied(self):
        decision = self._judge("Read", {"file_path": self._abs("README.md")})
        self.assertIn(decision.hook_decision, (ALLOW, ASK))
        self.assertNotEqual(decision.hook_decision, DENY)
        norm = decision.engine_decision_basis["path_normalization"][0]
        self.assertEqual(norm["action"], "repo_internal_absolute_normalized_to_relative")
        self.assertEqual(norm["normalized"], "README.md")

    def test_repo_internal_absolute_write_is_ask_not_deny(self):
        decision = self._judge("Write", {"file_path": self._abs("src/app.py"), "content": "x"})
        self.assertEqual(decision.hook_decision, ASK)

    def test_repo_internal_absolute_edit_is_not_deny(self):
        decision = self._judge(
            "Edit", {"file_path": self._abs("README.md"), "old_string": "a", "new_string": "b"}
        )
        self.assertIn(decision.hook_decision, (ALLOW, ASK))

    # --- repo-internal absolute protected: must STILL deny -----------------

    def test_repo_internal_absolute_protected_paths_still_deny(self):
        for rel in (".env", ".github/workflows/ci.yml", ".aeg/x"):
            with self.subTest(rel=rel):
                decision = self._judge("Write", {"file_path": self._abs(rel), "content": "x"})
                self.assertEqual(decision.hook_decision, DENY)

    # --- repo-external / traversal / symlink: must STILL deny -------------

    def test_repo_external_absolute_paths_still_deny(self):
        for path in ("/etc/passwd", "/root/.ssh/id_rsa", str(self.outside_root / "other" / "x")):
            with self.subTest(path=path):
                decision = self._judge("Read", {"file_path": path})
                self.assertEqual(decision.hook_decision, DENY)
                self.assertNotIn(decision.hook_decision, (ALLOW, ASK))

    def test_sibling_prefix_directory_is_not_treated_as_in_repo(self):
        # /tmp/x/repo-evil/secret.txt must NOT be considered under /tmp/x/repo.
        decision = self._judge(
            "Read", {"file_path": str(self.outside_root / "repo-evil" / "secret.txt")}
        )
        self.assertEqual(decision.hook_decision, DENY)
        norm = decision.engine_decision_basis["path_normalization"][0]
        self.assertFalse(norm["in_repo"])
        self.assertEqual(norm["action"], "outside_repo_kept_absolute_for_scope_rejection")

    def test_absolute_traversal_escaping_repo_still_denies(self):
        decision = self._judge(
            "Write", {"file_path": self._abs("../outside.txt"), "content": "x"}
        )
        self.assertEqual(decision.hook_decision, DENY)

    def test_symlink_inside_repo_pointing_outside_still_denies(self):
        link = self.repo_root / "link_to_passwd"
        try:
            link.symlink_to("/etc/passwd")
        except OSError:
            self.skipTest("symlinks not supported")
        decision = self._judge("Read", {"file_path": str(link)})
        self.assertEqual(decision.hook_decision, DENY)

    # --- relative behaviour unchanged ------------------------------------

    def test_relative_paths_unchanged(self):
        allow_or_ask = self._judge("Read", {"file_path": "README.md"})
        self.assertIn(allow_or_ask.hook_decision, (ALLOW, ASK))
        deny = self._judge("Write", {"file_path": "../outside.txt", "content": "x"})
        self.assertEqual(deny.hook_decision, DENY)


if __name__ == "__main__":
    unittest.main()
