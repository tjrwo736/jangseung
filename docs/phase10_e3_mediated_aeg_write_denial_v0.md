# Aegis Phase 10-E E3 Mediated `.aeg` Write Denial v0

## Scope

Phase 10-E E3 connects the E2 deny-only mediator skeleton to a narrow mediated
write request helper for `.aeg` targets. The helper canonicalizes the submitted
target path and returns a path-level denial when the target resolves under the
repository `.aeg` directory.

E3 denial vocabulary:

```text
AEG_WRITE_DENIED_BY_MEDIATED_PATH
MEDIATED_WRITE_DENIED
DENIED_BY_MEDIATOR
DENIED_BY_PATH_POLICY
NOT_FILESYSTEM_ENFORCED
RAW_DIRECT_WRITE_STILL_BYPASSABLE
EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED
```

## Boundary

The E3 helper does not implement OS permission hardening, chmod/chown handling,
external enforcement, raw/direct filesystem write blocking, outside-repo denial,
broker execution, tool execution, provider calls, release, publish, deploy, or
live executor authority.

Required distinction:

```text
mediated path denial != filesystem-level denial
.aeg mediated denial != .aeg executor isolation
denied by mediator/path policy != externally enforced denial
raw/direct write still bypassable
E1 known-gap baseline remains valid
tests passing != live executor safe
live executor authority remains ON_HOLD
```

## Covered E3 Denials

- direct mediated `.aeg` write requests.
- traversal requests that resolve under `.aeg`.
- symlink alias requests that resolve under `.aeg`.
- evidence overwrite attempts under `.aeg`.
- manifest overwrite attempts under `.aeg`.
- ledger append or overwrite attempts under `.aeg`.

Denied mediated `.aeg` requests do not create or modify the target file.

## Safe Default

```text
hold_current_state
```
