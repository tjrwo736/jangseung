# Aegis B2-4 Executor-like Routing Evidence and Verify Replay v0

## Scope

This note records the B2-4 component that binds the B2-3 fixture-only
executor-like ingress harness result to deterministic B2-level routing evidence.
It is evidence binding plus verify replay rejection only.

This component is not a B2 closure/status note, not production executor
write-path wiring, not a live executor implementation, not runtime write
authority, not a Phase 11-A start, and not B3 raw capability/worktree closure.

## Bound Record

Each B2-4 record binds:

- fixture-only executor-like ingress source
- ingress id and harness id
- submitted path
- resolved target
- B2 routed denial result
- route id and route digest
- B1-C guard evidence digest embedded by the B2-1/B2-3 path
- no-mutation observation
- current non-wiring and non-live-authority statuses
- B2 open status and B3 not-started status
- the complete B2-3 harness result record

The digest is canonical JSON SHA-256 over the B2-4 evidence payload. The record
id is deterministic from that digest.

## Verify Behavior

`verify_b2_executor_like_routing_evidence_record` replays deterministic bindings
and rejects mismatch, tamper, and overclaim fields.

- Untampered B2-3 fixture-only routed denial evidence replays as
  `B2_4_EXECUTOR_LIKE_ROUTING_EVIDENCE_REPLAY_CONSISTENT`.
- B2-4 evidence record digest or record id mismatch is rejected with
  `B2_4_ROUTING_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED`.
- B2-3 harness digest mismatch is rejected with
  `B2_4_ROUTING_HARNESS_DIGEST_MISMATCH_REJECTED`.
- B2 routed result digest mismatch is rejected with
  `B2_4_ROUTING_ROUTE_DIGEST_MISMATCH_REJECTED`.
- Submitted path, resolved target, route id, route digest, denial fields, or
  bound B1-C digest mismatch is rejected with
  `B2_4_ROUTING_FIELD_MISMATCH_REJECTED`.
- No-mutation mismatch is rejected with
  `B2_4_ROUTING_NO_MUTATION_MISMATCH_REJECTED`.
- Embedded B1-C evidence tamper is replayed through the B1-D verifier and
  rejected with `B2_4_ROUTING_B1_REPLAY_REJECTED`.
- B2 closure, write-path wiring, live-authority, Phase 11-A, B3, production
  runtime, and write-capability overclaims are rejected with
  `B2_4_ROUTING_OVERCLAIM_REJECTED`.

## Boundary

The verifier records:

```text
B2_4_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERIFY_REJECTION
B2_4_VERIFY_REPLAY_MISMATCH_REJECTION_ONLY
B2_4_VERIFY_REPLAY_NOT_EXTERNAL_ORACLE
NOT_TAMPER_PROOF
NOT_EXTERNAL_ANCHORED
NOT_WIRED_TO_EXECUTOR_WRITE_PATH
NOT_OS_ENFORCED
NOT_FILESYSTEM_ENFORCED
LIVE_EXECUTOR_AUTHORITY_ON_HOLD
PHASE11A_NOT_STARTED
```

Verify replay is deterministic mismatch rejection. It is not proof that raw
filesystem writes are impossible and it is not an external oracle. The B1-A
known-gap baseline remains preserved.

## Preservation

- B1-A known-gap baseline remains preserved.
- B1-B deny-only guard remains present.
- B1-C evidence binding remains present and replayed by B1-D.
- B2-1 router component/harness remains present.
- B2-2 integration boundary remains present.
- B2-3 fixture-only executor-like ingress harness remains present.
- B2 remains open; B2-5 status note remains separate.
- Runtime write path remains `NOT_WIRED_TO_EXECUTOR_WRITE_PATH`.
- Live executor authority remains `LIVE_EXECUTOR_AUTHORITY_ON_HOLD`.
- Phase 11-A remains `PHASE11A_NOT_STARTED`.
- B3 remains `B3_NOT_STARTED`.

## Default

```text
hold_current_state
```
