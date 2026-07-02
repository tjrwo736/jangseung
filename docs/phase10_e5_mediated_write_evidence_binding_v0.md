# Aegis Phase 10-E E5 Evidence Binding for Mediated Writes v0

## Scope

Phase 10-E E5 adds a deterministic evidence record for denied mediated write
results from E3 and E4. The record binds the mediated request, denial decision,
canonical target, denial reason, policy source, and supplied no-mutation
observation into a stable SHA-256 binding digest and binding id.

E5 binding vocabulary:

```text
MEDIATED_WRITE_EVIDENCE_BOUND
DENIED_WRITE_DECISION_EVIDENCE_BOUND
EVIDENCE_BINDING_PRESENT
BINDING_DIGEST_PRESENT
NO_MUTATION_OBSERVATION_BOUND
NOT_TAMPER_PROOF
NOT_EXTERNAL_ANCHORED
VERIFY_MISMATCH_REJECTION_NOT_IMPLEMENTED
RAW_DIRECT_WRITE_STILL_BYPASSABLE
EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED
```

## Boundary

E5 evidence binding is not a tamper-proof evidence store, external anchor,
filesystem-level denial, OS permission hardening, broker, wrapper, tool
execution path, provider call, release path, deploy path, or live executor
authority grant.

Required distinction:

```text
evidence binding != tamper-proof evidence store
binding digest != external anchor
bound denial record != filesystem-level denial
no-mutation observation != external enforcement proof
record mismatch rejection belongs to E6
E1 raw/direct write still bypassable
live executor authority remains ON_HOLD
```

## Covered E5 Bindings

- E3 mediated `.aeg` denial records.
- E4 mediated outside-repo denial records.
- deterministic binding digest/id stability for identical inputs.
- digest/id changes for changed request, decision, target, or no-mutation
  observation input.

## Safe Default

```text
hold_current_state
```
