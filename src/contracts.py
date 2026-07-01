"""Shared Day-1 contract vocabulary."""

AEG_VERSION = "0.1.0"
SAFE_DEFAULT = "hold_current_state"

LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"
RISK_LEVELS = (LOW, MEDIUM, HIGH)
RISK_ORDER = {
    LOW: 0,
    MEDIUM: 1,
    HIGH: 2,
}

NO_CHANGED_FILES = "NO_CHANGED_FILES"
NOT_CHECKED = "NOT_CHECKED"
NOT_CHECKED_NO_MUTATION = "NOT_CHECKED_NO_MUTATION"
NOT_CHECKED_IMPACT_RISKS = (
    NOT_CHECKED,
    NOT_CHECKED_NO_MUTATION,
)
IMPACT_RISKS = (
    NO_CHANGED_FILES,
    NOT_CHECKED,
    NOT_CHECKED_NO_MUTATION,
    LOW,
    MEDIUM,
    HIGH,
)

GIT_WORKING_TREE = "git_working_tree"
GIT_STAGED = "git_staged"
GIT_TRACKED_DIFF = "git_tracked_diff"
NO_CHANGED_FILES_SOURCE = "no_changed_files"
NOT_CHECKED_SOURCE = "not_checked"
CHANGED_FILES_SOURCES = (
    GIT_WORKING_TREE,
    GIT_STAGED,
    GIT_TRACKED_DIFF,
    NO_CHANGED_FILES_SOURCE,
    NOT_CHECKED_SOURCE,
)

CLEAN_CORE = "CLEAN_CORE"
NEEDS_USER_GATE = "NEEDS_USER_GATE"
BLOCKED = "BLOCKED"
INVALID_EVIDENCE = "INVALID_EVIDENCE"
STATUSES = (
    CLEAN_CORE,
    NEEDS_USER_GATE,
    BLOCKED,
    NOT_CHECKED,
    INVALID_EVIDENCE,
)

STATE_DIR = ".aeg"
CONFIG_FILE = "config.json"
LEDGER_FILE = "ledger.jsonl"
RUNS_DIR = "runs"

CONTRACT_FIRST_NOOP = "contract_first_noop"
COMPLETION_CONTRACT_V0 = "completion_contract_v0"

RUN_MANIFEST_V1 = "run_manifest_v1"
EVIDENCE_BINDING_V1 = "evidence_binding_v1"
BOUND = "BOUND"
BINDING_STATUSES = (
    BOUND,
    INVALID_EVIDENCE,
    NOT_CHECKED,
)

GIT_STATUS_PORCELAIN_V1 = "git_status_porcelain_v1"
SNAPSHOT_COLLECTOR_GIT_STATUS_V1 = "aeg_git_status_snapshot_v1"
SNAPSHOT_TRUST_BOUNDARY_CLI_WRAPPER_V1 = "aeg_cli_pre_post_executor_wrapper_v1"

MUTATION_DELTA_SOURCE_COMPUTED = "computed_from_independent_snapshots"
MUTATION_DELTA_SOURCE_UNTRUSTED = "not_checked_untrusted_snapshot"
REPORTED_ONLY = "reported_only"

CITIZEN_ONE_NOT_REQUESTED = "CITIZEN_ONE_NOT_REQUESTED"
CITIZEN_ONE_REQUESTED = "CITIZEN_ONE_REQUESTED"
CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED = "CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED"
CITIZEN_ONE_HELD_SECRET_BOUNDARY = "CITIZEN_ONE_HELD_SECRET_BOUNDARY"
CITIZEN_ONE_PROPOSAL_RECORDED = "CITIZEN_ONE_PROPOSAL_RECORDED"
CITIZEN_ONE_REJECTED_BY_GATE = "CITIZEN_ONE_REJECTED_BY_GATE"
CITIZEN_ONE_STATUSES = (
    CITIZEN_ONE_NOT_REQUESTED,
    CITIZEN_ONE_REQUESTED,
    CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED,
    CITIZEN_ONE_HELD_SECRET_BOUNDARY,
    CITIZEN_ONE_PROPOSAL_RECORDED,
    CITIZEN_ONE_REJECTED_BY_GATE,
)
CITIZEN_ONE_MODE_OFF = "off"
CITIZEN_ONE_MODE_PROPOSE = "propose"
CITIZEN_ONE_PROVIDER_STATUS_NOT_REQUESTED = "not_requested"
CITIZEN_ONE_PROVIDER_STATUS_NOT_CONFIGURED = "not_configured"
CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NOT_REQUESTED = "not_requested"
CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NONE = "none"
CITIZEN_ONE_HOLD_REASON_NONE = ""
CITIZEN_ONE_HOLD_REASON_PROVIDER_NOT_CONFIGURED = "provider_not_configured"
CITIZEN_ONE_EVIDENCE_FIELDS = (
    "citizen_one_requested",
    "citizen_one_mode",
    "citizen_one_status",
    "citizen_one_provider_status",
    "citizen_one_output_present",
    "citizen_one_output_trust_boundary",
    "citizen_one_reported_only",
    "citizen_one_hold_reason",
    "provider_config_source",
    "provider_network_used",
    "provider_secret_observed",
    "model_output_hash_candidate",
)

PROVIDER_ADAPTER_DISABLED_REQUEST_ID = "provider_adapter_disabled_v0"
PROVIDER_MODE_NOT_REQUESTED = "not_requested"
PROVIDER_MODE_DISABLED = "disabled"
PROVIDER_NAME_NONE = "none"
PROVIDER_MODEL_NONE = "none"
PROVIDER_PROMPT_SOURCE_NONE = "none"
PROVIDER_PROMPT_SOURCE_DISABLED = "disabled"
PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED = "no_raw_prompt_or_response_stored"
PROVIDER_SECRET_SOURCE_NOT_REQUESTED = "not_requested"
PROVIDER_SECRET_SOURCE_NONE = "none"
PROVIDER_RESPONSE_STATUS_NOT_REQUESTED = "not_requested"
PROVIDER_RESPONSE_STATUS_PROVIDER_NOT_CONFIGURED = "provider_not_configured"
PROVIDER_RESPONSE_SOURCE_NONE = "none"
PROVIDER_RESPONSE_SOURCE_DISABLED_ADAPTER = "disabled_adapter"
PROVIDER_RESPONSE_ERROR_CLASS_NONE = ""
PROVIDER_RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED = "provider_not_configured"
PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NONE = ""
PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NOT_CONFIGURED = (
    "provider adapter disabled; provider not configured; no request built"
)
PROVIDER_MODES = (
    PROVIDER_MODE_NOT_REQUESTED,
    PROVIDER_MODE_DISABLED,
)
PROVIDER_PROMPT_SOURCES = (
    PROVIDER_PROMPT_SOURCE_NONE,
    PROVIDER_PROMPT_SOURCE_DISABLED,
)
PROVIDER_REDACTION_STATUSES = (
    PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
)
PROVIDER_SECRET_SOURCES = (
    PROVIDER_SECRET_SOURCE_NOT_REQUESTED,
    PROVIDER_SECRET_SOURCE_NONE,
)
PROVIDER_RESPONSE_STATUSES = (
    PROVIDER_RESPONSE_STATUS_NOT_REQUESTED,
    PROVIDER_RESPONSE_STATUS_PROVIDER_NOT_CONFIGURED,
)
PROVIDER_RESPONSE_SOURCES = (
    PROVIDER_RESPONSE_SOURCE_NONE,
    PROVIDER_RESPONSE_SOURCE_DISABLED_ADAPTER,
)
PROVIDER_RESPONSE_ERROR_CLASSES = (
    PROVIDER_RESPONSE_ERROR_CLASS_NONE,
    PROVIDER_RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
)
PROVIDER_ADAPTER_DISABLED_FIELDS = (
    "provider_request_id",
    "provider_mode",
    "provider_name",
    "provider_model",
    "provider_prompt_source",
    "provider_prompt_hash_candidate",
    "provider_request_redaction_status",
    "provider_network_opt_in",
    "provider_secret_source",
    "provider_secret_observed",
    "provider_response_present",
    "provider_response_status",
    "provider_response_source",
    "provider_response_reported_only",
    "provider_response_trust_boundary",
    "provider_response_hash_candidate",
    "provider_response_redaction_status",
    "provider_response_error_class",
    "provider_response_error_safe_summary",
)

PROMPT_BUILD_STATUS_NOT_BUILT = "not_built"
PROMPT_BUILD_STATUS_PROVIDER_DISABLED = "not_built_provider_disabled"
PROMPT_SOURCE_NONE = "none"
PROMPT_SOURCE_DISABLED = "disabled"
PROMPT_REDACTION_STATUS_NO_RAW_PROMPT_STORED = "no_raw_prompt_stored"
PROMPT_STORAGE_POLICY_NO_RAW_PROMPT_STORAGE = "no_raw_prompt_storage"
PROMPT_BUILD_STATUSES = (
    PROMPT_BUILD_STATUS_NOT_BUILT,
    PROMPT_BUILD_STATUS_PROVIDER_DISABLED,
)
PROMPT_SOURCES = (
    PROMPT_SOURCE_NONE,
    PROMPT_SOURCE_DISABLED,
)
PROMPT_REDACTION_STATUSES = (
    PROMPT_REDACTION_STATUS_NO_RAW_PROMPT_STORED,
)
PROMPT_STORAGE_POLICIES = (
    PROMPT_STORAGE_POLICY_NO_RAW_PROMPT_STORAGE,
)
PROMPT_REDACTION_METADATA_FIELDS = (
    "prompt_build_requested",
    "prompt_build_status",
    "prompt_source",
    "prompt_input_summary",
    "prompt_redaction_status",
    "prompt_hash_candidate",
    "prompt_storage_policy",
    "prompt_secret_detected",
    "prompt_raw_stored",
)

RESPONSE_STATUS_NOT_REQUESTED = "not_requested"
RESPONSE_STATUS_PROVIDER_DISABLED = "provider_disabled"
RESPONSE_SOURCE_NONE = "none"
RESPONSE_SOURCE_DISABLED_ADAPTER = "disabled_adapter"
RESPONSE_REDACTION_STATUS_NO_RAW_RESPONSE_STORED = "no_raw_response_stored"
RESPONSE_ERROR_CLASS_NONE = ""
RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED = "provider_not_configured"
RESPONSE_ERROR_SAFE_SUMMARY_NONE = ""
RESPONSE_ERROR_SAFE_SUMMARY_PROVIDER_DISABLED = (
    "provider adapter disabled; provider not configured; no response requested"
)
RESPONSE_STATUSES = (
    RESPONSE_STATUS_NOT_REQUESTED,
    RESPONSE_STATUS_PROVIDER_DISABLED,
)
RESPONSE_SOURCES = (
    RESPONSE_SOURCE_NONE,
    RESPONSE_SOURCE_DISABLED_ADAPTER,
)
RESPONSE_REDACTION_STATUSES = (
    RESPONSE_REDACTION_STATUS_NO_RAW_RESPONSE_STORED,
)
RESPONSE_ERROR_CLASSES = (
    RESPONSE_ERROR_CLASS_NONE,
    RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
)
RESPONSE_REDACTION_METADATA_FIELDS = (
    "response_present",
    "response_status",
    "response_source",
    "response_reported_only",
    "response_trust_boundary",
    "response_redaction_status",
    "response_hash_candidate",
    "response_raw_stored",
    "response_error_class",
    "response_error_safe_summary",
)
PROMPT_RESPONSE_REDACTION_METADATA_FIELDS = (
    *PROMPT_REDACTION_METADATA_FIELDS,
    *RESPONSE_REDACTION_METADATA_FIELDS,
)
FORBIDDEN_RAW_PROMPT_RESPONSE_KEYS = (
    "raw_prompt",
    "prompt_raw",
    "prompt_body",
    "raw_response",
    "response_raw",
    "response_body",
    "provider_raw_prompt",
    "provider_raw_response",
    "prompt_text",
    "response_text",
    # Historical aliases are also rejected to keep the disabled-provider
    # boundary closed around request/response bodies.
    "provider_prompt",
    "provider_response",
    "provider_request_body",
    "provider_response_body",
    "model_request_body",
    "model_response_body",
)

CITIZEN_ONE_PROPOSAL_CONTRACT_V0 = "citizen_one_proposal_contract_v0"
PROPOSAL_KIND_NOT_GENERATED = "not_generated"
PROPOSAL_KIND_DETERMINISTIC_STUB = "deterministic_stub"
PROPOSAL_STATUS_PROVIDER_NOT_CONFIGURED = "provider_not_configured"
PROPOSAL_STATUS_DETERMINISTIC_STUB_RECORDED = "deterministic_stub_recorded"
PROPOSAL_SOURCE_NONE = "none"
PROPOSAL_SOURCE_DETERMINISTIC_STUB = "deterministic_stub"
PROPOSAL_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED = "no_raw_prompt_or_response_stored"
PROPOSAL_HOLD_REASON_NONE = ""
PROPOSAL_HOLD_REASON_PROVIDER_NOT_CONFIGURED = "provider_not_configured"
DETERMINISTIC_STUB_PROPOSAL_ID = "deterministic_stub_v0"
DETERMINISTIC_STUB_PROPOSAL_SUMMARY = "Deterministic local proposal stub recorded without provider, API, network, or model call."
DETERMINISTIC_STUB_PROPOSAL_STEPS = (
    "Record fixed local proposal fields.",
    "Preserve classifier, law, evidence binding, and mutation boundary judgment.",
    "Perform no command execution and no file mutation.",
)
DETERMINISTIC_STUB_PROPOSAL_RISK_NOTES = (
    "reported_only; not a judgment basis",
    "does not satisfy, bypass, or downgrade any user gate",
    "no raw prompt or response stored",
)
PROPOSAL_STATUSES = (
    PROPOSAL_STATUS_PROVIDER_NOT_CONFIGURED,
    PROPOSAL_STATUS_DETERMINISTIC_STUB_RECORDED,
)
PROPOSAL_REDACTION_STATUSES = (
    PROPOSAL_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
)
PROPOSAL_CONTRACT_FIELDS = (
    "proposal_id",
    "proposal_version",
    "proposal_kind",
    "proposal_summary",
    "proposal_steps",
    "proposal_risk_notes",
    "proposal_requires_user_gate",
    "proposal_trust_boundary",
    "proposal_reported_only",
    "proposal_source",
    "proposal_output_hash_candidate",
    "proposal_redaction_status",
    "proposal_status",
    "proposal_present",
    "proposal_hold_reason",
)

MUTATION_BOUNDARY_CLEAN = "MUTATION_BOUNDARY_CLEAN"
MUTATION_BOUNDARY_DIRTY_PREEXISTING = "MUTATION_BOUNDARY_DIRTY_PREEXISTING"
MUTATION_BOUNDARY_DELTA_DETECTED = "MUTATION_BOUNDARY_DELTA_DETECTED"
MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT = "MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT"
MUTATION_BOUNDARY_NOT_CHECKED = "MUTATION_BOUNDARY_NOT_CHECKED"
MUTATION_BOUNDARY_STATUSES = (
    MUTATION_BOUNDARY_CLEAN,
    MUTATION_BOUNDARY_DIRTY_PREEXISTING,
    MUTATION_BOUNDARY_DELTA_DETECTED,
    MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT,
    MUTATION_BOUNDARY_NOT_CHECKED,
)
