# Aegis Phase 10-E E4 Outside-repo Write Denial v0

## Scope

Phase 10-E E4 adds a narrow mediated write request helper for targets that
canonicalize outside the repository boundary. The helper resolves the repo root
and submitted target, detects sibling, absolute, traversal, and symlink alias
escapes, and returns a deny decision before any file mutation.

E4 denial vocabulary:

```text
OUTSIDE_REPO_WRITE_DENIED_BY_MEDIATED_PATH
REPO_BOUNDARY_WRITE_DENIED
DENIED_BY_REPO_BOUNDARY_POLICY
MEDIATED_WRITE_DENIED
DENIED_BY_MEDIATOR
NOT_FILESYSTEM_ENFORCED
RAW_DIRECT_WRITE_STILL_BYPASSABLE
EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED
```

## Boundary

The E4 helper is a mediated path policy only. It does not implement OS
permission hardening, raw/direct filesystem write blocking, broker execution,
tool execution, provider calls, release, publish, deploy, or live executor
authority.

Required distinction:

```text
mediated outside-repo denial != filesystem-level denial
denied by repo boundary policy != external enforcement
raw/direct outside-repo write still bypassable
E1 known-gap baseline remains valid
E3 .aeg mediated denial remains valid
tests passing != live executor authority
live executor authority remains ON_HOLD
```

## Covered E4 Denials

- sibling outside-repo mediated write requests.
- absolute outside-repo mediated write requests.
- traversal requests that escape the repo boundary.
- symlink alias requests that lexically start under the repo but canonicalize
  outside it.

Denied mediated outside-repo requests do not create or modify the requested
target file.

## Safe Default

```text
hold_current_state
```
