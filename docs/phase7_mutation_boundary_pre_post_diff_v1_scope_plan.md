# Aegis Phase 7 Mutation Boundary / Pre-Post Diff v1 Scope Plan

## 1. Purpose

Phase 7 Mutation Boundary / Pre-Post Diff v1 is a hard blocker before Phase 8
Model-backed Citizen One.

Phase 7 is not mutation execution. It is the mutation attribution boundary
design that fixes how a future Aegis implementation will prove what changed
because of an executor run.

The purpose is to lock the scope for separating and evidencing the repository
state before work from the repository state after work. Future implementation
must be able to answer: "What changed because of the executor?" That answer
must come from independently captured git pre/post snapshots, not from executor
self-report.

The accepted baseline is Phase 0-6B-H as the canonical baseline:
`PHASE6B_HERMES_PROXY_PASS_EXTERNAL_PENDING`. The true external unaided run is
still not claimed complete and remains a separate future milestone:
`Aegis Phase 6B-T True External Unaided Run v0`.

## 2. Non-Goals

Phase 7 v1 scope planning does not include:

- actual mutation execution
- model-backed executor work
- provider integration
- OpenAI, Claude, or Gemini integration
- OpenAI API calls or any model API calls
- autonomous loop design or implementation
- GitHub, Slack, DRA, or Hermes integration
- release, publish, or deploy work
- public readiness claims
- true external validation complete claims
- changes to `aeg run` behavior
- changes to `aeg verify` behavior
- changes to classifier, law, evidence, state, packaging, source, or tests
- new checker, manifest, report, telemetry, or runtime artifact systems

## 3. Mutation Boundary Definitions

- `pre_run_changed_files`: the independently captured changed-file state before
  executor invocation. It includes tracked working tree, staged/index, and
  tracked diff state.
- `post_run_changed_files`: the independently captured changed-file state after
  executor completion, using the same snapshot collector and trust boundary as
  the pre-run snapshot.
- `pre_existing_dirty_tree`: any dirty tracked repository state already present
  in `pre_run_changed_files`. This is not executor-created mutation.
- `executor_created_mutation`: a repository state transition attributable to the
  executor because it appears in the trusted post-run snapshot compared with the
  trusted pre-run snapshot.
- `mutation_delta`: the state transition between pre-run and post-run snapshots.
  It is a computed repository-state transition, not an executor statement.
- `protected_path_mutation`: a computed mutation delta touching paths that carry
  higher impact risk, including source, tests, packaging, governance docs,
  runtime behavior, or other future protected path categories.
- `computed_mutation_delta`: the mutation delta independently computed from
  trusted `pre_run_changed_files` and `post_run_changed_files`. It is the only
  candidate judgment basis for mutation attribution, and only when the snapshot
  trust boundary is satisfied.
- `executor_reported_mutation_delta`: any changed-file or mutation list reported
  by the executor. It is `reported_only` and is not a judgment basis.
- `snapshot_trust_boundary`: the authorship and control boundary that keeps
  pre/post snapshot capture outside executor authorship/control.

## 4. Snapshot Trust Boundary

The executor's words are not the source of truth.

Required future principles:

- `pre_run` snapshot must be captured before executor invocation.
- `post_run` snapshot must be captured after executor completion.
- snapshot capture must be outside executor authorship/control.
- executor-reported `mutation_delta` is `reported_only` and not a judgment
  basis.
- `mutation_delta` must be computed from independent pre/post snapshots.

Korean meaning:

- `pre_run` snapshot은 executor 호출 전에 찍는다.
- `post_run` snapshot은 executor 종료 후 찍는다.
- executor가 직접 보고한 변경 목록은 참고 자료일 뿐 판단 근거가 아니다.
- 판단 근거는 독립적으로 캡처한 pre/post snapshot의 차이다.

The snapshot collector must not sit inside the same authorship/control boundary
as the executor. If the executor reports its own changed-file list, that is
self-certification. Self-certification can be recorded as context, but it cannot
carry a gate decision.

The only judgment-basis candidate is the delta computed from pre/post snapshots
captured by an independent snapshot collector. Even that computed delta is valid
only when the snapshot trust boundary itself is satisfied.

## 5. Independent Snapshot Capture Rule

Future implementation must capture snapshots as a wrapper around executor
invocation:

1. capture trusted `pre_run_changed_files`
2. invoke executor
3. wait for executor completion
4. capture trusted `post_run_changed_files`
5. compute `computed_mutation_delta` from the two trusted snapshots

The executor may provide an advisory report, but it must not author, replace, or
approve the snapshots used for mutation judgment.

## 6. Pre/Post Snapshot Owner

The pre/post snapshot owner should be a future Aegis evidence or verification
boundary component, not the executor. The owner must be able to produce evidence
that the snapshot was collected before or after executor invocation and that the
collector was outside executor authorship/control.

If future architecture cannot prove that ownership boundary, the mutation
boundary status must not be clean. The safe default is:

```text
hold_current_state
```

## 7. `pre_run_changed_files` Plan

`pre_run_changed_files` must be captured before executor invocation.

The future snapshot should include:

- tracked working tree changes
- staged/index changes
- tracked diff status
- file state categories such as added, deleted, modified, renamed, copied, type
  changed, and staged-vs-unstaged state
- enough repository metadata to bind the snapshot to a commit, branch, tree, and
  run context

The pre-run snapshot records the `pre_existing_dirty_tree`. A dirty pre-run tree
does not prove executor mutation; it proves that attribution must compare pre
state to post state. The pre-run snapshot should be a candidate for
manifest/evidence binding in a future implementation.

## 8. `post_run_changed_files` Plan

`post_run_changed_files` must be captured after executor completion.

The future implementation must capture a post-run snapshot even for a no-op
executor. It must use the same collector and trust boundary as the pre-run
snapshot.

The post-run snapshot should include the same categories as the pre-run snapshot:
tracked working tree changes, staged/index changes, tracked diff status, and
state categories such as added, deleted, modified, renamed, copied, type
changed, and staged-vs-unstaged state. It should also be a candidate for
manifest/evidence binding.

## 9. `mutation_delta` Rule

`mutation_delta` is the independent computed result of comparing
`post_run_changed_files` with `pre_run_changed_files`.

A simple set difference of paths is not sufficient. Future implementation should
model a state transition because the same path can move between clean, modified,
staged, unstaged, deleted, added, renamed, or type-changed states.

Rules:

- `executor_reported_mutation_delta` is `reported_only`.
- `executor_reported_*` fields are not a judgment basis.
- `computed_mutation_delta` is the only mutation judgment-basis candidate.
- `computed_mutation_delta` is valid only when the snapshot trust boundary is
  satisfied.
- `executor did not mutate` does not mean `no changed files in working tree`.
- `pre_existing_dirty_tree` does not mean `executor_created_mutation`.

## 10. No-Op Executor Expected Behavior

For the current no-op executor, trusted `computed_mutation_delta` should be
empty.

Folder-local `.aeg/` runtime artifacts are local runtime state and should be
handled separately from tracked source mutation. They must not be treated as
tracked source/test/docs mutation when they remain untracked and ignored.

If a no-op executor creates tracked file mutation, it is a mutation boundary
failure candidate. If the no-op executor changes source, tests, docs, packaging,
or governance files, the run is a failure for this boundary.

## 11. Dirty Tree Handling

Pre-existing dirty tree state is not executor-created mutation.

Future evidence must record the dirty pre-run state instead of flattening it
into the post-run result. If the post-run state is identical to the pre-run
state, there may be no executor-created mutation even though the working tree is
dirty.

If the post-run state is worse than the pre-run state, introduces new tracked
diff, changes staged state, or creates a protected path mutation, the result
must escalate. If the dirty tree is too complex to attribute safely, the safe
default is:

```text
hold_current_state
```

## 12. Protected Path Escalation After Mutation

Task text classified as LOW cannot remain LOW when trusted post-run evidence
shows a protected path mutation.

Protected path mutation is an impact-risk escalation candidate. Future
implementation should document and test escalation to HIGH or `NEEDS_USER_GATE`
when mutation touches protected paths. `NOT_CHECKED` must never be promoted to
PASS.

Examples of future protected path categories may include:

- source runtime behavior
- tests
- packaging files
- governance docs
- evidence, verification, classifier, law, and state boundaries
- secret, environment, release, deployment, or telemetry paths

## 13. Evidence Packet Field Candidates

Future evidence packet candidates:

- `pre_run_changed_files`
- `post_run_changed_files`
- `pre_snapshot_source`
- `post_snapshot_source`
- `snapshot_collector`
- `snapshot_trust_boundary`
- `executor_reported_changed_files`
- `executor_reported_mutation_delta`
- `computed_mutation_delta`
- `mutation_delta_source`
- `pre_existing_dirty_tree`
- `protected_path_mutation_detected`
- `mutation_boundary_status`

Clarifications:

- `executor_reported_*` fields are evidence context only.
- `executor_reported_*` fields are not a judgment basis.
- `computed_mutation_delta` is the only judgment-basis candidate.
- `computed_mutation_delta` is valid only when the snapshot trust boundary is
  satisfied.
- `mutation_delta_source` should distinguish `reported_only` from
  `computed_from_independent_snapshots`.

## 14. Verify Replay Change Candidates

Future `aeg verify` work should re-check pre/post snapshot binding.

Verify must not read `mutation_delta` from the executor report as the source of
truth. It should recompute mutation delta from independently captured snapshots
and compare the recomputed value to the evidence packet.

Future verify rules:

- replay checks pre/post snapshot bindings
- replay recomputes `computed_mutation_delta` from independent snapshots
- replay treats executor reports as `reported_only`
- `REPLAY_CONSISTENT` is not external oracle proof
- snapshot trust boundary violation cannot be promoted to replay-clean
- snapshot trust boundary violation cannot be promoted to PASS

## 15. Status Vocabulary Candidates

Candidate statuses:

- `MUTATION_BOUNDARY_CLEAN`: trusted pre/post snapshots exist, the snapshot trust
  boundary is satisfied, and no executor-created mutation is detected.
- `MUTATION_BOUNDARY_DIRTY_PREEXISTING`: the pre-run tree was dirty and this was
  recorded; no additional executor-created mutation is detected.
- `MUTATION_BOUNDARY_DELTA_DETECTED`: trusted pre/post snapshots identify a
  post-run state transition.
- `MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT`: snapshot capture was missing,
  executor-controlled, or otherwise outside the required trust boundary.
- `MUTATION_BOUNDARY_NOT_CHECKED`: mutation boundary evidence was not evaluated.
- `NEEDS_USER_GATE`: user approval is required before accepting or continuing,
  including protected path mutation or HIGH-risk escalation.

Principles:

- `NOT_CHECKED` is not PASS.
- `REPLAY_CONSISTENT` is not external oracle proof.
- clean judgment must not be issued when the snapshot trust boundary is broken.
- mutation delta touching protected paths is a user-gate candidate.
- HIGH remains `NEEDS_USER_GATE`.

## 16. Tests / Acceptance Criteria

Future implementation acceptance criteria:

- clean tree plus no-op executor produces empty `computed_mutation_delta`
- dirty pre tree plus no-op executor records `pre_existing_dirty_tree` and
  produces empty computed mutation
- dirty pre tree plus unchanged post state means no executor-created mutation
- post-run new tracked diff detects `mutation_delta`
- post-run protected path mutation escalates
- executor-reported mutation is ignored as a judgment basis
- untrusted snapshot collector produces boundary failure
- verify recomputes `mutation_delta` from independent snapshots
- `.aeg/` runtime artifacts are not treated as tracked source mutation
- status vocabulary preserves LOW, MEDIUM, and HIGH expectations
- HIGH remains `NEEDS_USER_GATE`
- `NOT_CHECKED` never becomes PASS

## 17. Required Questions Answered

1. `pre_run_changed_files` is collected before executor invocation by an
   independent snapshot collector, including tracked working tree, staged/index,
   and tracked diff state.
2. `post_run_changed_files` is collected after executor completion by the same
   independent collector and trust boundary used for the pre-run snapshot.
3. `mutation_delta` is computed as a state transition between the trusted
   pre-run and post-run snapshots, not as executor self-report.
4. For a no-op executor, trusted `computed_mutation_delta` should be empty.
5. A pre-existing dirty tree is recorded as `pre_existing_dirty_tree` and is not
   treated as executor-created mutation unless post-run state transitions prove
   additional mutation.
6. If task text is LOW but post-run protected path mutation appears, LOW cannot
   remain the final boundary judgment; escalation to HIGH or `NEEDS_USER_GATE`
   is a future candidate.
7. Evidence should add the field candidates listed in this document, especially
   pre/post snapshots, collector source, reported-only executor fields,
   `computed_mutation_delta`, protected path detection, and boundary status.
8. `aeg verify` should replay by validating snapshot bindings and recomputing
   mutation delta from independent snapshots, not from executor reports.
9. Mutation boundary failure can be expressed by candidates such as
   `MUTATION_BOUNDARY_DELTA_DETECTED`,
   `MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT`, or `NEEDS_USER_GATE`.
10. The Phase 8 blocker is Phase 7 implementation completion with verified
    pre/post snapshot capture, mutation delta computation, verify replay, and
    snapshot trust boundary behavior.
11. Pre/post snapshots are captured by an independent collector outside executor
    authorship/control. That separation is the trust boundary.

## 18. Phase 8 Hard Blocker / Handoff Criteria

Phase 7 Mutation Boundary / Pre-Post Diff v1 is a hard blocker before Phase 8
Model-backed Citizen One.

Phase 8 must not jump directly into provider-backed or model-backed executor
expansion. Before Phase 8 can begin, Phase 7 implementation must be complete and
smoke-tested for:

- pre/post snapshot capture
- `computed_mutation_delta` computation
- verify replay from independent snapshots
- snapshot trust boundary enforcement
- dirty tree attribution behavior
- protected path escalation behavior
- status vocabulary behavior where `NOT_CHECKED` is never PASS

The true external unaided run remains a separate milestone and is not claimed by
this Phase 7 scope plan.
