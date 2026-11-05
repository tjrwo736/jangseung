# 장승 0.1.8 릴리스 노트

보안 수정 릴리스입니다. 0.1.5부터 0.1.7까지 쓰고 있다면 올리세요. 첫 실제 Codex 세션 점검에서 아래 결함을 찾았습니다.

## 고친 결함

**프로젝트 밖 폴더의 명령 자동 허용:** 읽기 명령은 명령에 적힌 경로만 판정했습니다. 경로를 적지 않은 `git status`, `git log -p`, `git diff`, `ls`, `Get-ChildItem`, `pwd`는 어느 폴더에서 실행되는지 보지 않았습니다. Codex의 `exec_command`는 `workdir`로 실행 폴더를 지정할 수 있어서, 승인 없이 다음이 가능했습니다.

- `git log -p`, `git diff`: 다른 프로젝트의 이력과 변경 내용 출력
- `git status`: 다른 저장소의 `.git/config`에 적힌 프로그램 실행 (`core.fsmonitor`)
- `ls`, `Get-ChildItem`: 프로젝트 밖 폴더의 파일 이름 출력

0.1.7이 막은 프로그램 실행은 프로젝트 안 파일과 에이전트가 쓸 수 있는 폴더가 대상이었습니다. 프로젝트 밖 저장소의 `.git`은 대상이 아니었습니다.

이제 호스트가 알린 작업 폴더도 판정합니다. 프로젝트 밖이면 deny합니다. `.aeg` 안이면 Claude Code에서는 `ask`, Codex에서는 `deny`입니다. `.aeg/policy.json`의 `allow_commands`로 승인한 명령도 프로젝트 안에서만 자동 허용합니다. 호스트가 상대 경로 `cwd`를 보내면 hook이 실행 중인 폴더 기준으로 풀어 판정합니다.

Claude Code도 판정은 같았습니다. 다만 세션의 작업 폴더가 프로젝트 밖으로 나가려면 먼저 `cd`가 승인되어야 하며, 이 경로는 실제 세션으로 확인하지 않았습니다.

**`apply_patch` 절대 경로 과차단:** 프로젝트 안 파일도 절대 경로로 적으면 deny했습니다. 실제 Codex 세션에서 모델이 절대 경로를 적어 정상 패치가 막혔습니다. 같은 파일의 `Write`는 allow였습니다.

이제 이 컴퓨터의 절대 경로 형식(Windows `C:\...`, 그 밖에는 `/...`)이고 프로젝트 안이면 상대 경로와 똑같이 판정합니다. 비밀 파일, 보호 파일, 프로젝트 밖 경로, 링크로 그곳에 닿는 경로는 그대로 deny입니다. `\\?\`, UNC, `/c/...` 표기도 deny입니다. hook은 패치 원문을 바꾸지 않습니다.

## 확인 결과

실제 Codex CLI 0.166.0 세션(Windows, `codex exec`, 설정 `approval_policy=never`, `sandbox_mode=danger-full-access`)에서 더미 파일로 확인한 결과입니다. 0.1.8은 릴리스 전 빌드입니다.

| 요청 | 0.1.7 | 0.1.8 |
| --- | --- | --- |
| `git status --short`, `workdir` 다른 저장소(`core.fsmonitor` 있음) | **심은 프로그램 실행됨** | 차단, 실행 안 됨 |
| 같은 명령, `workdir` 상대 경로 `..\outside-repo` | 허용 | 차단 |
| 같은 명령, `workdir` `C:/.../outside-repo/` 표기 | 허용 | 차단 |
| `git log -p`, `workdir` 다른 저장소 | **다른 프로젝트 내용 출력** | 차단 |
| `Get-ChildItem`, `workdir` 프로젝트 상위 폴더 | 판정 allow, 실행 안 함 | 차단 |
| `git status --short`, 프로젝트 안 | 허용 | 허용 |
| `git status --short`, `workdir` `.github` | 허용 | 허용 |
| `git diff`, 추적 중인 `.env` 변경 | `.env` 제외 | `.env` 제외 |
| `git diff`, `workdir` `.github` | 실행 안 함 | `.env` 제외 |
| `git log -p`, 이력에 `.env` 있음 | `.env` 제외 | `.env` 제외 |
| `apply_patch` `notes.md` 상대 경로 | 허용 | 허용 |
| `apply_patch` `notes.md` 절대 경로 | **차단** | 허용 |
| `apply_patch` `.env` 절대 경로 | 판정 deny, 실행 안 함 | 차단, 파일 그대로 |
| `apply_patch` `.github\workflows\ci.yml` 절대 경로 | 판정 deny, 실행 안 함 | 차단, 파일 그대로 |
| `apply_patch` 프로젝트 밖 절대 경로 | 판정 deny, 실행 안 함 | 차단, 파일 그대로 |
| `Get-Content notes.md`, 프로젝트 안 | 허용 | 허용 |
| `Get-Content .env` | 실행 안 함 | 차단 |

- **`updatedInput`:** Codex CLI 0.166.0은 `Bash`의 `updatedInput`을 적용합니다. 제외 조건이 붙은 명령이 실제로 실행되었고, 같은 명령을 직접 실행한 대조군에서는 `.env` 값이 나왔습니다.
- **hook이 받는 입력:** `tool_input`에는 `command`만 있습니다. `cwd`는 실제 실행 폴더이며, 상대 경로 `workdir`도 절대 경로로 풀려 옵니다. 0.1.8은 이 `cwd`를 판정합니다.
- **`shell` 옵션:** `exec_command`의 `shell`에 프로젝트 안 `pwsh.cmd`, `pwsh.exe`를 지정한 시험 2건에서 지정한 프로그램은 실행되지 않았습니다.
- **`tty` 옵션:** Microsoft Store판 `pwsh`를 쓰는 환경에서는 프로세스 생성이 실패했습니다(2건). PATH에서 그 경로를 뺀 Windows PowerShell 환경에서는 `git log -p`가 페이저 없이 끝났습니다(1건). 페이저가 뜨지 않은 원인은 확인하지 못했습니다.
- **판정 회귀:** 기존 판정 시험 86건의 결과는 0.1.7과 같습니다(allow 1, ask 3, deny 82).

## 업그레이드 절차

```bash
python -m pip install --upgrade jangseung
aeg doctor --hooks
```

- `aeg install`을 0.1.5 이상에서 실행한 프로젝트는 올리기만 하면 적용됩니다. Codex 승인도 다시 받지 않아도 됩니다.
- `matcher`가 WARN이거나 `executable`이 FAIL이면 `aeg install`을 다시 실행하세요. Codex는 `aeg install --target codex`이며, 이후 `/hooks`에서 다시 승인해야 합니다.

## 동작 변화

- 작업 폴더가 프로젝트 밖이면 `pwd`, `ls`, `git status` 같은 읽기 명령도 Claude Code와 Codex 모두 deny합니다. Claude Code에서 프로젝트 밖 폴더로 `cd`한 뒤 쓰던 읽기 명령도 해당합니다.
- `.aeg/policy.json`으로 승인한 명령은 프로젝트 밖 폴더에서 자동 허용하지 않습니다. Claude Code에서는 `ask`, Codex에서는 `deny`입니다.
- `.aeg` 안을 작업 폴더로 쓰는 읽기 명령은 Claude Code에서 `ask`, Codex에서 `deny`입니다.
- `apply_patch`는 프로젝트 안 파일을 절대 경로로 적어도 allow합니다.

## 남는 제한

- **코드를 실행하는 MCP 도구:** hook은 MCP 도구를 검사하지 않습니다. 실제 Codex 세션에서 `mcp__node_repl__js`가 hook 기록 없이 `.env` 값을 읽었습니다. 이런 도구는 파일 읽기, 쓰기, 프로그램 실행을 모두 할 수 있으므로 장승의 보호를 통째로 넘어섭니다. 등록된 도구를 확인하고, 필요 없으면 등록을 해제하세요. MCP 도구를 hook 대상에 넣는 일은 이번 릴리스에 포함하지 않았습니다. Codex에서 hook을 다시 승인해야 하고 다른 MCP 도구까지 막을 수 있습니다.
- **hook이 보지 못하는 Codex 옵션:** `exec_command`의 `tty`, `shell`과 `write_stdin`은 hook 입력에 없습니다. 위 시험에서 문제를 재현하지 못했지만 다른 버전이나 운영체제에서는 확인하지 않았습니다.
- **있는 폴더만 판정합니다:** 호스트가 없는 폴더를 알리면 hook이 실행 중인 폴더 기준으로 판정합니다. Codex CLI 0.166.0은 없는 폴더에서 프로세스를 만들지 못해 명령이 실행되지 않았습니다.
- [0.1.7의 남는 제한](release_0.1.7.md#남는-제한)은 그대로입니다.

다음은 아직 확인하지 못했습니다.

- Codex CLI 0.166.0 외 버전, Linux와 macOS의 실제 Codex 세션
- MCP 도구 호출에 Codex의 PreToolUse hook이 걸리는지
- Claude Code에서 작업 폴더가 프로젝트 밖으로 나간 실제 세션
- 숨은 지시로 에이전트를 움직이는 경우

## 문서 정정

- **README:** Codex 실측 범위를 고치고, 코드를 실행하는 MCP 도구가 hook을 거치지 않는다는 점을 적었습니다.
- **0.1.5, 0.1.6, 0.1.7 릴리스 노트:** 최신 버전으로 올리라는 안내에 0.1.8을 넣었습니다.
