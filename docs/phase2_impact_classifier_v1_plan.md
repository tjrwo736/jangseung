## 1. Phase 2 scope

Phase 2 adds Impact-aware Classifier v1 before any mutating executor work.

Scope:

- Keep existing Day-1 intent classification behavior and add separate impact risk.
- Classify impact from repository changed files, not from executor self-report.
- Produce one final `risk_level` by merging `intent_risk` and `impact_risk`.
- Preserve deterministic STOP precedence and the safe default:

```text
hold_current_state
```

If this planning PR is accepted, the next work is exactly:

```text
Aegis Phase 2 Impact-aware Classifier v1 Implementation
```

## 2. Non-goals

Phase 2 planning does not implement:

- changed-files classifier code
- protected path taxonomy code
- executor changes
- provider or model-backed execution
- autonomous loop behavior
- GitHub, Slack, DRA, or Hermes integration
- release, publish, or deploy flow
- secret, token, API key, or real `.env` value handling

## 3. Protected path taxonomy v0

Impact-aware classification must treat these paths as protected:

- `.github/workflows/**`
- `.github/actions/**`
- `Dockerfile`
- `docker-compose.yml`
- `docker-compose.*.yml`
- `pyproject.toml`
- `requirements*.txt`
- `setup.py`
- `setup.cfg`
- `src/cli/**`
- `src/classify/**`
- `src/law/**`
- `src/evidence/**`
- `src/state/**`
- `.env`
- `.env.*`
- `secrets/**`
- `config/**/secrets*`
- `release/**`
- `deploy/**`
- `scripts/release*`
- `scripts/deploy*`

Risk mapping:

- docs-only changes are LOW.
- normal non-protected source changes are MEDIUM.
- protected path changes are HIGH.

## 4. intent_risk / impact_risk / final risk_level merge rule

Phase 2 must keep `intent_risk` and `impact_risk` separate.

Risk ordering:

```text
LOW < MEDIUM < HIGH
```

The final `risk_level` is:

```text
max(intent_risk, impact_risk)
```

Required behavior:

- A LOW task touching a protected path is escalated to final HIGH.
- If changed files cannot be checked, the result remains in a NOT_CHECKED family state, not PASS.
- NOT_CHECKED is not PASS.
- `reported_only` evidence is not a judgment basis.
- Deterministic STOP cannot be reversed by a provider or LLM.

## 5. Changed files source

Phase 2 implementation must make the changed-files source explicit.

Allowed source categories:

- git working tree diff
- git staged diff
- git tracked diff against the relevant base

The source must be distinct from Day-1 no-op executor `NO_CHANGED_FILES`.
`NO_CHANGED_FILES` means the no-op executor did not mutate files; it does not
prove impact was checked.

If the changed-files source is missing or unclear, impact classification remains
NOT_CHECKED-family and cannot become PASS.

## 6. Evidence packet change plan

Existing Day-1 evidence fields remain. Phase 2 may add or clarify only the
fields needed to bind impact classification to repository facts:

- `impact_reasons`
- `protected_paths_touched`
- `changed_files_source`
- `risk_escalation_applied`
- `final_risk_rule`
- `impact_checked_at`

These fields must describe deterministic inputs and decisions. They must not
depend on provider judgment or reported-only executor claims.

## 7. Verify replay change plan

Verify replay must recompute risk from saved evidence:

- Recompute `intent_risk` from saved `task_text`.
- Recompute `impact_risk` from saved `changed_files`.
- Verify saved `risk_level` equals `max(intent_risk, impact_risk)`.
- If a protected path change remains LOW, return INVALID_EVIDENCE or a BLOCKED-family result.
- If `changed_files_source` is missing, return NOT_CHECKED-family, not PASS.

## 8. Acceptance tests

Minimum Phase 2 acceptance test plan:

- docs-only change -> LOW
- normal non-protected `src/**` change -> MEDIUM
- workflow or CI path change -> HIGH
- secret or env path change -> HIGH
- deploy or release path change -> HIGH
- task text LOW + protected path touched -> final HIGH
- changed files source missing -> NOT_CHECKED-family, not PASS
- verify replay detects mismatched saved `risk_level`

## 9. Forbidden scope

Phase 2 implementation must not include:

- `aeg init`, `aeg doctor`, `aeg run`, or `aeg verify` behavior changes outside the impact classifier and replay boundary
- executor behavior changes
- state or ledger behavior changes
- OpenAI, Claude, or Gemini providers
- OpenAI API calls
- model-backed executor
- autonomous loop
- GitHub API automation
- Slack integration
- DRA or Hermes integration
- release, publish, or deploy automation
- committed `.aeg/` runtime artifacts
- secrets, tokens, API keys, or real `.env` values

## 10. Implementation handoff criteria

Implementation may begin when this document is merged through a PR and main is
not directly pushed.

The implementation PR must:

- implement the taxonomy and merge rule above
- preserve existing Day-1 evidence fields
- bind impact decisions to explicit changed-files source
- keep NOT_CHECKED distinct from PASS
- add focused tests for the acceptance cases above
- avoid provider, executor, integration, release, deploy, and secret-handling scope

Next action after this planning PR:

```text
Aegis Phase 2 Impact-aware Classifier v1 Implementation
```
