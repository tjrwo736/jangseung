![장승(Jangseung) — 코딩 에이전트의 문지기](https://raw.githubusercontent.com/tjrwo736/jangseung/main/docs/assets/jangseung-hero.png)

# 장승(Jangseung) — AI 코딩 에이전트를 위한 방패

Claude Code에게 코드를 맡기되, 위험한 것이 실행되기 전에 막습니다.

장승은 한국 전통 마을 어귀에 세워져 나쁜 것을 막던 수호신상입니다. 이 도구도 AI 에이전트가 위험한 작업을 하기 전, 그 경계에 서 있습니다.

[![asciicast](https://asciinema.org/a/6B2AARAZCOKB9snJ.svg)](https://asciinema.org/a/6B2AARAZCOKB9snJ)

실제 Claude Code 세션에서 장승(Jangseung)이 위험한 작업을 막고 정상 작업은 통과시키는 데모

## 핵심 3가지

- **위험한 것만 막습니다**: `.env` 유출, `rm -rf` 같은 파괴 명령, 장승을 끄려는 시도를 실행 전에 멈춥니다. 빌드·의존성 파일 변경은 사람에게 묻습니다. 일반 파일 읽기와 편집은 방해하지 않습니다.
- **변조를 탐지할 수 있는 기록**: 판정마다 어떤 파일과 어떤 프로그램이 대상이었는지 기록하고, hash chain으로 사후 변조를 탐지합니다. 파일 내용과 명령 인자는 기록하지 않습니다. 로컬 파일이므로 tamper-proof라고 주장하지 않습니다.
- **직접 호출 차단**: 조작된 지시가 비밀 파일을 읽거나 위험한 명령을 실행하려 해도 tool call 단계에서 멈춥니다. 에이전트가 쓴 코드를 다른 명령이 실행하는 경로는 막지 못합니다. [우리가 못 막는 것](#우리가-못-막는-것)에 적었습니다.

영어 문서: [README.en.md](README.en.md)

## Claude Code도 위험하면 물어보는데?

맞아요. 근데 기본 승인은 세 가지가 아쉽습니다.

- 매번 다 물어봅니다. 그래서 결국 `--dangerously-skip-permissions`로 꺼버리게 되죠. 그러면 안전장치가 통째로 사라집니다.
- AI가 뭘 했는지 감사할 기록이 충분히 남지 않습니다. "어제 얘가 뭘 건드렸지?"를 나중에 추적하기 어렵습니다.
- 규칙이 흐트러지면 그냥 통과시킵니다(fail-open). 안전 도구인데 문제가 생기면 위험한 쪽으로 실패합니다.

장승(Jangseung)은 반대로 만들었습니다. 위험한 것만 골라 멈추고(정상 작업은 방해하지 않습니다), 판정 메타데이터를 변조 탐지 가능한 기록으로 남기고, 문제가 생기면 안전한 쪽으로 멈춥니다(fail-closed).

## 무엇을 막나 (그리고 안 막나)

방패는 앞을 막지, 지나가는 사람까지 막지 않습니다. 장승(Jangseung)은 명확한 기준으로 위험한 것만 막습니다.

막습니다 (사용자 승인 없이는 실행 안 됨):

- 비밀 노출 위험: `.env`와 `.env.*`, 비밀키(`id_rsa`, `*.pem`, `*.key` 등), 인증 파일(`.ssh/`, `.aws/`, `.npmrc`, `credentials.json` 등)의 읽기와 수정. 폴더 깊이와 대소문자 표기에 관계없이 적용합니다. `.env.example` 같은 템플릿은 비밀로 보지 않습니다. 다만 폴더 전체 `Grep`에서는 함께 건너뜁니다.
- 되돌릴 수 없는 파괴: `rm -rf`, `git reset --hard`, `git clean -f`, `git checkout -- .`
- 외부 반출과 배포: `git push`, `npm publish`, `gh release create`, `kubectl apply`, `terraform apply`, `curl`
- 장승 무력화: `.claude/settings*.json`, `.codex/`, `.mcp.json`, `.git/` 수정과 `aeg uninstall`, `aeg policy` 실행
- git이 실행하는 파일: `core.hooksPath`, `include.path`, `core.fsmonitor`, `gpg.program` 등 git 설정이 가리키는 프로젝트 안 경로의 수정 (0.1.7부터)
- 감시 기록 조작: executor가 `.aeg` 디렉토리에 직접 쓰는 행위 (장승의 신뢰된 내부 recorder만 전용 ledger에 기록)
- 범위 밖 접근: 프로젝트 폴더 바깥 경로 (`/etc`, `~/.ssh` 등). 작업 폴더가 프로젝트 밖인 읽기 명령도 포함합니다 (0.1.8부터)

이 판정은 파일을 직접 쓰는 경우(Write/Edit)뿐 아니라, Bash 명령이나 Windows Claude Code의 PowerShell 명령으로 우회하려는 경우(`echo > .env`, `Remove-Item .env` 같은)도 동일하게 적용됩니다. 줄바꿈, 괄호, `&`, `;`로 명령을 이어 붙여도 안에 든 명령을 따로 판정하고, 세션이 하위 폴더로 이동해도 보호 경로는 프로젝트 루트 기준으로 유지합니다.

막지 않습니다 (그냥 통과):

- 코드 읽기, 일반 파일 편집, README 수정, 빌드 설정 파일 읽기
- `ls`, `pwd`, `git status`, `git diff`, `git log`처럼 파일을 바꾸지 않는 명령
- 위험하지 않은 정상 작업은 방해하지 않습니다.

사람이 봐야 하는 변경 (물어봅니다, 0.2.0부터):

- 빌드·CI·의존성 파일 수정: `.github/workflows`, `.gitlab-ci.yml` 같은 CI 설정, `Dockerfile`, `pyproject.toml`, `setup.py`, `requirements*.txt`, `package.json`, `Makefile`, `conftest.py`, `.pre-commit-config.yaml`, 배포 스크립트. 하위 폴더에 있어도 같습니다. 이 파일들은 다음 설치·빌드·테스트·커밋 때 코드를 실행하므로 사람이 변경을 확인합니다. 읽기는 허용합니다.
- 묻는 것은 호스트가 사람에게 승인을 받는 경우뿐입니다. hook 입력의 `permission_mode`가 `default`(수동 승인) 또는 `acceptEdits`일 때만 `ask`로 답하고, 그 밖의 모드(`auto`, `dontAsk`, `bypassPermissions`, `plan`)와 Codex에서는 0.1.9까지와 같이 deny합니다.
- 근거: Claude Code 2.1.316 `claude -p`(Windows)에서 모드마다 한 번씩, 모든 `Edit`에 `ask`로 답하는 hook을 걸어 확인했습니다. `default`, `acceptEdits`, `auto` 모두 편집이 실행되지 않았습니다. `auto`는 분류기가 사람 대신 답할 수 있어 제외했고, `dontAsk`와 `bypassPermissions`는 확인하지 않았습니다. 대화형 세션에서 승인 창이 뜨는지도 확인하지 않았습니다.
- 0.1.9까지 막지 않던 `package.json`, `Makefile`, `conftest.py`, `.pre-commit-config.yaml`과 하위 폴더의 `pyproject.toml` 등이 새로 포함되었습니다. 계속 자동으로 수정하게 하려면 사람이 `aeg policy add --path <파일>`로 허용합니다.

실행 명령과 애매한 작업 (0.2.0부터):

- Claude Code의 `default` 모드에서는 `pytest`, `npm test`, `python src/app.py` 같은 제한된 실행 명령을 **호스트의 원래 승인 정책에 맡깁니다**. 장승이 안전하다고 `allow`하는 것이 아닙니다. 기존 호스트 허용 규칙이 있으면 추가 질문 없이 실행될 수 있습니다. `Bash(python -m:*)`, `Bash(uv run:*)`처럼 넓은 규칙 아래에서는 `python -m dotenv list`, `uv run printenv` 같은 비밀 출력 명령도 묻지 않고 실행됩니다. 장승은 사용자의 호스트 규칙을 덮어쓰지 않습니다.
- 0.2.1부터 내용을 출력하는 git 형태는 맡기지 않습니다: `git stash show`, `git stash list -p`, 그리고 `-p`·`-v`·`-i`(묶은 짧은 옵션 포함)나 `--patch`·`--verbose`·`--dry-run`·`--show-current-patch`·`--interactive`·`--long`·`--short`·`--porcelain`(축약 포함)이 붙은 git 명령. Claude Code가 이런 읽기 명령을 승인 없이 실행해, 0.2.0에서는 stash에 든 비밀 파일 변경이 그대로 출력되었습니다.
- 이 예외는 단순한 한 명령이며, 작업 폴더와 명시된 인자가 프로젝트 안의 비보호 경로이고 기존 차단 관문을 모두 통과할 때만 적용합니다. 다른 모드와 모드가 없는 입력은 기존대로 `ask`, Codex는 `deny`입니다. 정책/세션 표시를 읽지 못하거나 세션에 비밀 이름 작성 표시가 있어도 위임하지 않습니다.
- 미지원 프로그램, 내용 검색, 복잡한 셸 문법 등 나머지 미분류 작업은 계속 확인을 요청합니다. 별도로 신뢰할 명령은 [프로젝트 승인 정책](#프로젝트-승인-정책-015부터)에 등록할 수 있습니다.
- `.git`이 없는 폴더의 `git` 명령과 `git diff docs .`처럼 폴더를 비교하는 명령도 확인을 요청합니다.

## 우리가 못 막는 것

장승(Jangseung)은 "완벽하게 안전하다"고 말하지 않습니다. 지키는 선을 정확히 말합니다.

장승(Jangseung)은 AI가 파일을 쓰거나 명령을 실행하는 등 도구를 사용하려는 순간에 끼어들어 판단합니다. 그래서 도구를 거치지 않는 것들 — AI가 참조로 직접 읽어 들이는 파일 내용, 이미 허용된 명령이 내부에서 실행하는 다른 프로그램 — 은 이 선 바깥에 있습니다.

**가장 중요한 한계: 써 놓고 실행하는 경로.** 에이전트는 일반 소스 파일을 자유롭게 씁니다. 그 파일이 `.env`를 읽는 코드라도 쓰는 시점에는 내용을 판정하지 않습니다. 이후 사람이 승인 창에서 `python script.py`나 `pytest`를 허용하거나 `allow_commands`에 넣어 두면 그 코드가 실행됩니다. 장승은 실행된 프로그램이 무엇을 읽는지 보지 못합니다. 이 경로를 실제로 막으려면 OS 수준 샌드박스가 필요하며, 장승은 그 대체가 아닙니다.

0.2.0부터 이 경로를 한 가지만 좁힙니다. (0.2.1부터 자동 허용되는 `cp`, `mv`로 문서를 문서가 아닌 파일로 옮길 때도 원본 내용을 같은 기준으로 봅니다.) 에이전트가 문서가 아닌 파일에 비밀 파일 이름(`.env`, `id_rsa`, `.aws/credentials`, `*.pem` 등)이 든 내용을 쓰면 그 세션에 표시를 남기고, 같은 세션에서 `allow_commands` 자동 허용과 `default` 모드의 호스트 위임을 보류하고 사람에게 묻습니다(Codex에서는 deny). 이름을 보는 것이지 동작을 보는 것이 아닙니다. 이름을 조각내어 만드는 코드, 셸 명령으로 만든 파일, 다른 세션에서 쓴 파일은 표시되지 않습니다. 사람이 그 요청을 직접 승인하면 실행될 수 있습니다. 호스트의 기존 허용 규칙으로 실행되는 프로그램 내부도 장승은 보지 못합니다.

또한 변수 치환이나 중첩 셸처럼 복잡하게 감춰진 명령은 대상을 정밀하게 판별하지 못해, 이 경우 자동 통과가 아니라 확인을 요청합니다.

hook이 검사하는 도구는 `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Read`, `Grep`, `Glob`, `Bash`, Windows의 `PowerShell`, Codex의 `apply_patch`입니다. `WebFetch`, `WebSearch`는 검사 대상이 아니며, 이 도구들로 나가는 내용은 장승이 보지 못합니다. MCP 도구와 MCP 리소스 읽기는 [MCP 보호](#mcp-보호-019부터-선택)를 켠 프로젝트에서만 검사합니다. 켜지 않으면 코드를 실행하거나 파일을 읽는 MCP 도구, 파일을 리소스로 제공하는 MCP 서버는 장승의 판정을 거치지 않고 파일 내용을 에이전트에게 넘길 수 있습니다.

MCP 보호를 켜지 않은 설치로, 실제 세션(Claude Code 2.1.316 `claude -p`, Codex CLI 0.166.0 `codex exec`, Windows)에서 더미 `.env`로 경우마다 한 번씩 확인했습니다. 값이 출력된 경우에는 모두 장승 기록이 남지 않았습니다.

- **Claude Code의 MCP 도구:** auto 모드와, Manual 모드(도구마다 승인을 묻는 모드)에서 미리 허용한 도구는 값이 출력되었습니다. Manual 모드에서 미리 허용하지 않은 도구는 승인을 요구해 실행되지 않았습니다.
- **Claude Code의 MCP 리소스 읽기(`ReadMcpResourceTool`):** Manual 모드에서도 승인 요구 없이 값이 출력되었습니다. auto 모드도 같습니다.
- **Codex의 MCP 도구와 `read_mcp_resource`:** `approval_policy=never` 설정에서 값이 출력되었습니다. `mcp__node_repl__js`도 포함됩니다.

MCP 보호를 켠 0.1.9로는 Claude Code 2.1.316 `claude -p`(Windows)에서 같은 방법으로 확인했습니다.

- **MCP 도구:** auto 모드와, Manual 모드에서 미리 허용한 도구 모두 승인을 요구해 실행되지 않았습니다. MCP 서버에 호출이 가지 않았고 장승 기록에 `ask`가 남았습니다.
- **MCP 리소스 읽기:** Manual 모드와 auto 모드 모두 같은 결과였습니다.
- **허용 목록:** `allow_mcp_tools`에 넣은 도구는 승인 없이 실행되었고, 넣지 않은 도구는 계속 멈췄습니다. `Read` 도구는 전과 같이 한 번만 판정했습니다.
- **확인하지 못한 것:** `claude -p`에는 승인할 사람이 없어 `ask`가 실행 거부로 끝납니다. 대화형 세션에서 승인 창이 뜨는지는 확인하지 않았습니다. Codex에서 막히는지는 자동 테스트와 hook CLI로만 확인했습니다.

이런 MCP 서버가 등록되어 있으면 MCP 보호를 켜거나, 등록을 해제하거나, 호스트의 승인 설정을 확인하세요.

다음도 알아 두세요.

- **하위 폴더에서 시작한 세션:** Claude Code는 세션을 시작한 폴더의 `.claude/settings.json`만 읽습니다. 프로젝트의 하위 폴더에서 `claude`를 시작하면 장승 hook이 실행되지 않습니다. 프로젝트 루트에서 시작하세요.
- **이름이 기준입니다:** 비밀 판정은 파일 이름 기준입니다. `git diff`, `git show`, `git log -p`에는 비밀 파일 제외 조건을 붙이지만, 규칙에 없는 이름으로 커밋된 값은 출력됩니다.
- **입력을 바꾸는 다른 hook:** `Grep`과 `git` 출력 명령에는 장승이 비밀 파일 제외 조건을 붙입니다. 같은 도구에 `updatedInput`을 내는 다른 hook을 함께 걸면 이 조건이 사라질 수 있습니다.
- **승인한 명령:** `grep -r`, `rg`, `git grep`처럼 폴더를 훑는 셸 명령은 승인을 요구합니다. 사람이 승인하면 비밀 파일도 읽습니다.

다르게 말하면, 장승(Jangseung)은 문 앞을 지키는 경비이지 집 안 모든 방을 감시하는 CCTV가 아닙니다.

이 한계를 감추지 않는 것이 장승(Jangseung)이 신뢰를 얻는 방식입니다.

## 지원 범위

현재 구현과 실측 기준의 범위입니다. 장승(Jangseung)은 Claude Code 전체나 Codex 전체를 안전하게 만든다고 주장하지 않습니다.

| 상태 | 범위 |
| --- | --- |
| 지원됨 | 실행 환경: Linux/WSL, Windows 네이티브에서 실물 검증 |
| 지원됨 | Claude Code `Write`/`Edit`/`Read`/`Bash` 주요 PreToolUse hook 경로 (Linux/WSL 및 Windows 네이티브 실측) |
| 지원됨 (0.1.5부터) | Claude Code `Grep`/`Glob` 판정(Windows 실제 세션에서 확인), `MultiEdit`/`NotebookEdit` 판정(자동 테스트와 hook CLI로만 확인) |
| 지원됨 (0.1.7부터) | 폴더 전체 `Grep`의 비밀 파일 제외: hook이 `updatedInput`으로 제외 조건을 붙임. 호출 쪽 `glob`으로 다시 포함시킬 수 없음. `path`의 `~`와 드라이브 상대 경로는 deny (Claude Code 2.1.316, Windows 실제 세션에서 확인) |
| 지원됨 | Windows Claude Code `PowerShell` 주요 PreToolUse hook 경로와 흔한 PowerShell 쓰기/삭제 target 판정 |
| 지원됨 | 프로젝트 로컬 Claude Code 설치: `aeg install --target claude-code` (기본값) |
| 지원됨 | 비밀 파일, `.aeg`, 장승 자체 설정을 직접 대상으로 하는 `Write`/`Edit` deny. 0.1.5부터 `Read` deny는 비밀 파일, `.aeg`, 프로젝트 밖 경로로 좁혔습니다 |
| 지원됨 (0.2.0부터) | 빌드·CI·의존성 파일 수정은 Claude Code의 `default`·`acceptEdits` 모드에서 `ask`, 그 밖의 모드와 Codex에서 deny. `package.json`, `Makefile`, `conftest.py`, `.pre-commit-config.yaml`, 하위 폴더의 매니페스트 포함 (Claude Code 2.1.316 `claude -p`, Windows 실제 세션에서 `default` 모드의 `package.json` 편집이 `ask`로 멈추는 것을 확인. 대화형 승인 창은 확인하지 않음) |
| 지원됨 (0.2.0부터) | `aeg policy`: 승인 정책을 diff 확인 후 추가. 에이전트의 호출은 deny |
| 지원됨 (0.2.0부터) | 승인된 명령의 표기 차이 허용: 따옴표로 묶인 글, 끝의 `2>&1`, 앞의 `cd <프로젝트 안 폴더> &&` |
| 지원됨 (0.2.0부터) | 비밀 파일 이름이 든 내용을 쓴 세션에서는 승인된 명령을 자동 허용하지 않음. 이름 기준이며 우회 가능 |
| 지원됨 (0.2.0부터) | hook 기록에 프로젝트 상대 경로, 프로그램 이름, 세션 ID, 입력 해시 추가. 내용과 인자는 기록하지 않음 |
| 지원됨 (0.2.0부터) | Claude Code 플러그인 형태 설치, 개인 설정 파일 설치(`aeg install --scope local`). 플러그인은 Claude Code 2.1.316 `claude -p --plugin-dir`(Windows) 실제 세션에서 일반 편집 allow, `package.json` 편집 ask, `.env` 읽기 deny와 기록 생성을 확인. 마켓플레이스 설치(`/plugin install`), macOS·Linux, 개인 설정 파일 설치의 실제 세션은 확인하지 않음 |
| 지원됨 | Bash의 보호 경로 쓰기/삭제 deny: 리다이렉트, heredoc 계열, `tee`, `cp`, `mv`, `rm`, `dd`, `truncate`, `ln` 등 구조적으로 파악 가능한 쓰기/삭제 타깃 포함 |
| 지원됨 | PowerShell의 보호 경로 쓰기/삭제 deny: `Remove-Item`/`rm`/`del`/`ri`/`erase`, `Set-Content`/`sc`, `Add-Content`/`ac`, `Clear-Content`, `New-Item`, `Rename-Item`, `Out-File`, `Tee-Object`, `>`/`>>`, `Move-Item`/`Copy-Item` 등 구조적으로 파악 가능한 쓰기/삭제 타깃 포함 |
| 지원됨 (0.1.5부터) | PowerShell 자동 허용은 `Get-Content`, `Get-ChildItem`, `Test-Path` 등의 좁은 읽기 문법을 통과한 명령에만 적용. 비밀 파일과 프로젝트 밖 읽기는 deny. `Get-ChildItem`을 `Select-String`으로 넘기는 파일 검색, 유니코드 공백이나 기울어진 따옴표가 있는 명령은 0.1.7부터 자동 허용하지 않음 |
| 지원됨 | 위험 명령 deny: `rm -rf`, `git reset --hard`, `git clean -f`, `git checkout -- .`, `git push`, 공개·배포 명령(`npm publish`, `gh release create`, `kubectl apply`, `terraform apply` 등). 경로로 지정하거나 `git -C`, `bash -c`로 감싸도 적용 |
| 지원됨 | 정상 파일 작업 allow: repo 내부의 명확히 안전한 읽기/쓰기/편집은 방해하지 않음 |
| 지원됨 | Codex `apply_patch` tool call의 target-aware 판정: 보호 경로 deny, 정상 경로 allow (Windows 네이티브 hook exit code 처리 포함 실측). 프로젝트 안 파일은 0.1.8부터 절대 경로로 적어도 같은 판정 (Codex CLI 0.166.0, Windows 실제 세션에서 확인) |
| 지원됨 | 프로젝트 로컬 Codex 설치: `aeg install --target codex` |
| 지원됨 (0.1.9부터, 선택) | MCP 보호: `aeg install --mcp`가 별도 hook 항목을 추가. MCP 도구 호출과 MCP 리소스 읽기를 Claude Code에서는 승인 요구, Codex에서는 deny. `.aeg/policy.json`의 `allow_mcp_tools`에 적은 도구만 통과. 인자는 검사하지 않음 (Claude Code 2.1.316, Windows 실제 세션에서 확인. Codex는 자동 테스트와 hook CLI로만 확인) |
| 지원됨 (0.1.2부터) | Codex 제거: `aeg uninstall --target codex`; 다른 hook과 TOML 설정/주석 보존, diff 확인과 백업 |
| 지원됨 (0.1.2부터) | 프로젝트 내부 일반 파일의 제한된 셸 읽기: `cat`, `head`/`tail`, 출력 전용 `sed -n`, `rg --no-config`, `Get-Content` 및 단순 출력 pipeline |
| 지원됨 (0.1.7부터) | `git diff`, `git show`, `git log -p`의 비밀 파일 제외: 추적 파일과 이력 모두. 객체 ID는 커밋으로만 해석 (Claude Code 2.1.316, Windows 실제 세션에서 확인. Codex CLI 0.166.0은 `git diff`, `git log -p`를 Windows 실제 세션에서 확인) |
| 지원됨 (0.1.5부터) | 파일을 바꾸지 않는 명령 자동 허용: `ls`, `pwd`, `echo`, `grep`, `wc`, `test`, 읽기 전용 `git`(`status`, `diff`, `log`, `show`, `blame`, `branch` 조회 등). `git`은 0.1.7부터 작업 폴더나 상위 폴더에 `.git`이 있을 때만. 0.1.8부터 작업 폴더가 프로젝트 밖이면 이 명령들 모두 deny |
| 지원됨 (0.1.5부터) | 프로젝트 승인 정책: `.aeg/policy.json`으로 경로와 명령을 승인. 에이전트는 이 파일을 수정할 수 없음. 승인한 명령은 0.1.8부터 프로젝트 안에서만 자동 허용 |
| 지원 안 됨 | 에이전트가 쓴 코드를 승인된 명령이 실행할 때 그 코드의 동작 판정. [우리가 못 막는 것](#우리가-못-막는-것) 참고 |
| 지원됨 | Codex substrate에서 `ask`/`defer`를 `deny`로 격상: Codex에서 `ask`가 실행 차단 안전망으로 동작하지 않는 실측 결과 반영 |
| 부분 지원 / 확인 중 | Bash 동적/난독화 명령: 변수 치환, 명령 치환, 중첩 셸, `find -delete`/`xargs` 등은 정밀 판별하지 못하면 자동 허용하지 않고 `ask`/`defer`로 보냄 (Codex substrate에서는 `deny`로 격상) |
| 부분 지원 / 확인 중 | PowerShell 동적/복잡 명령: target 변수, 동적 command invocation, 미지원 cmdlet, 복잡한 pipeline은 정밀 판별을 주장하지 않고 `ask`/`defer`로 보냄 |
| 부분 지원 / 확인 중 | `apply_patch` quoted path 처리: 대칭 따옴표는 정규화해서 판정하고, 비대칭/중간 따옴표/빈 경로처럼 애매한 입력은 fail-closed deny |
| 부분 지원 / 확인 중 | macOS: 테스터 검증 진행 중 (결과 대기) |
| 지원 안 됨 (로드맵) | 파일 내용 안의 실제 secret 값 스캔: 현재는 경로와 의도 기반 판정 |
| 지원 안 됨 | Codex에서 `Bash` tool name으로 들어오는 PowerShell 쓰기/삭제 명령(예: `Remove-Item` 등)의 구조적 파싱. 제한된 `Get-Content` 읽기는 0.1.2부터 지원 |
| 지원 안 됨 | `@` 파일 참조처럼 tool call을 거치지 않고 모델 컨텍스트로 직접 읽히는 내용 |
| 지원 안 됨 | 이미 허용된 명령이 내부에서 실행하는 하위 프로세스의 모든 행동 추적 |
| 지원 안 됨 | 글로벌 설치: `~/.claude`, `~/.codex` 설치는 지원하지 않음 |
| 지원됨 | PyPI 공개 배포: `python -m pip install jangseung` |
| 지원 안 됨 | OS 수준 격리/샌드박스 |

## 설치

장승(Jangseung)은 PyPI에 배포되어 있습니다. `pip`으로 설치합니다.

```bash
# 가상환경 생성 (특히 macOS/최신 Linux 배포판에서 필요 — 시스템 Python에 직접 설치가 막힐 수 있습니다)
python -m venv venv
source venv/bin/activate
# Windows(PowerShell)는: venv\Scripts\Activate.ps1
pip install jangseung
```

설치가 끝나면 `aeg` 명령을 사용할 수 있습니다. 이후 `aeg` 명령을 쓸 때마다 이 가상환경을 활성화해야 합니다. 이제 hook을 걸고 싶은 프로젝트로 이동해서 등록합니다.

기존 사용자는 장승을 설치했던 가상환경을 활성화한 뒤 업데이트하세요. 0.1.2에는 제한된 셸 문서 읽기와 Codex hook 제거 수정이, 0.1.3에는 설치·제거 시 설정 보존과 기록 안정성 수정이, 0.1.5에는 보안 우회 수정이, 0.1.6에는 구형 hook 업그레이드 수정이, 0.1.7에는 검색과 셸 읽기 명령으로 비밀 값이 출력되고 `git` 명령으로 프로그램이 실행되던 결함 수정이, 0.1.8에는 프로젝트 밖 폴더의 `git` 명령이 자동 허용되던 결함과 `apply_patch` 절대 경로 과차단 수정이, 0.1.9에는 선택해서 켜는 [MCP 보호](#mcp-보호-019부터-선택)가 포함됩니다. **0.2.1은 0.2.0에서 생긴 비밀 노출 결함을 고친 보안 수정입니다**([0.2.1 릴리스 노트](docs/release_0.2.1.md)). 0.2.0은 빌드 파일 판정, 승인 정책 명령, 기록 내용을 바꾸고 `aeg run`, `aeg verify`, `aeg init` 명령을 제거합니다. 바뀐 점과 올릴 때 확인할 것은 [0.2.0 릴리스 노트](docs/release_0.2.0.md)에 있습니다.

```bash
python -m pip install --upgrade jangseung
```

**0.1.5 이상으로 올린 뒤에는 프로젝트마다 `aeg install`(Codex는 `aeg install --target codex`)을 다시 실행하세요.** 등록된 hook의 명령, 검사 도구 목록, 실패 시 차단 설정을 최신으로 고칩니다. 0.1.4 이하가 `python -m src.cli hook-run` 형태로 등록한 hook은 0.1.6부터 호환 모듈을 거쳐 계속 판정하지만, 프로젝트 파일을 먼저 찾습니다. `src/cli.py`가 있으면 그 파일이 장승 대신 판정하고, `src/__init__.py`가 있으면 hook이 시작되지 못합니다. 에이전트도 이 파일을 만들 수 있으므로 이 형태로 두면 안 됩니다. 새 검사 도구도 적용되지 않습니다. 이 형태의 hook은 0.1.5에서 시작되지 못해 Claude Code가 도구 호출을 그대로 통과시켰습니다. `aeg doctor --hooks`로 확인할 수 있습니다. 자세한 내용은 [0.1.6 릴리스 노트](docs/release_0.1.6.md)와 [0.1.7 릴리스 노트](docs/release_0.1.7.md)에 있습니다.

```bash
cd /path/to/your-project
aeg install
```

기본값은 Claude Code 대상입니다. 명시적으로 쓰면 다음과 같습니다.

```bash
aeg install --target claude-code
```

Claude Code 대상 `aeg install`은 다음을 확인하고 진행합니다.

- 프로젝트 폴더의 `.claude/settings.json`에 장승(Jangseung) PreToolUse hook을 등록합니다. **project-local만 지원합니다** — 글로벌(`~/.claude`) 설치는 이 버전에서 지원하지 않습니다.
- 기존 `.claude/settings.json`이 있으면 병합합니다. 기존에 등록된 다른 hook과 설정은 그대로 남고, 장승(Jangseung) hook만 추가됩니다. 이미 등록돼 있으면 그 항목만 최신 형태로 고칩니다.
- hook에 `"onFailure": "block"`을 설정합니다. hook이 시작되지 못하거나 비정상 종료해도 도구 호출이 그대로 실행되지 않게 하는 설정이며, Claude Code v2.1.295 이상에서 동작합니다.
- 쓰기 전에 변경 내용을 diff로 보여주고 확인(`y/N`)을 받습니다. 이미 승인한 자동화 환경이라면 `--yes`로 확인을 건너뛸 수 있습니다.
- 쓰기 전에 기존 파일을 `settings.json.aegis-backup-<timestamp>`로 백업합니다.
- 0.1.3부터 확인 후 프로젝트의 `.aeg/` 기록 폴더도 준비합니다. 새 폴더에는 내부 `.gitignore`를 넣고, 기존 기록과 프로젝트의 `.gitignore`는 변경하지 않습니다. 설정 파일은 완성된 임시 파일로 원자적으로 교체합니다.
- 0.2.0부터 hook 명령에는 `aeg install`을 실행한 인터프리터의 `aeg`를 적습니다. 그 인터프리터에 `aeg` 스크립트가 없을 때만 PATH에서 찾습니다. 0.1.9까지는 PATH를 먼저 찾아, 가상환경의 `aeg`로 설치해도 PATH에 있는 다른 설치본이 등록될 수 있었습니다.

**팀이 `.claude/settings.json`을 git으로 공유한다면 개인 설정 파일에 설치하세요 (0.2.0부터).** hook 명령은 이 PC의 절대 경로이므로 공유 파일에 적으면 다른 사람의 PC에서는 그 경로가 없습니다.

```bash
aeg install --scope local
aeg uninstall --scope local
```

`.claude/settings.local.json`에 등록합니다. 이 파일을 git이 무시하지 않으면 `.gitignore`에 추가하세요. 두 파일에 모두 등록하면 호출마다 두 번 판정하며, `aeg doctor --hooks`가 알려 줍니다. `--scope`는 Claude Code 대상에만 있습니다. 하위 폴더에서 시작한 세션에 이 파일의 hook이 적용되는지는 확인하지 않았습니다.

### Claude Code 플러그인으로 설치 (0.2.0부터)

`pip`과 `aeg install` 없이 Claude Code 플러그인으로도 쓸 수 있습니다.

```text
/plugin install jangseung --marketplace tjrwo736/jangseung
```

- 플러그인을 켠 모든 프로젝트에 hook이 걸립니다. 프로젝트별 설정 파일은 바꾸지 않습니다.
- PATH에 Python 3.10 이상(`python3` 또는 `python`)이 있어야 합니다. hook 명령은 `sh` 문법이므로 Windows에서는 Git Bash가 필요합니다. 둘 중 하나가 없으면 hook이 시작되지 못하고, `onFailure: block` 설정에 따라 도구 호출이 막힙니다. 이 설정은 Claude Code v2.1.295 이상에서 동작합니다. 그보다 낮은 버전에서는 시작되지 못한 hook이 도구 호출을 막지 못합니다.
- 기록 폴더 `.aeg/`가 없으면 hook이 처음 호출될 때 만듭니다. 내부 `.gitignore`를 함께 넣습니다.
- `aeg policy`, `aeg explain`, `aeg doctor`, `aeg evidence`와 Codex 설치, MCP 보호는 `pip` 설치가 필요합니다. 플러그인만 쓰면 `.aeg/policy.json`을 직접 편집합니다.
- 플러그인과 `aeg install`을 함께 쓰면 호출마다 두 번 판정합니다. 하나만 쓰세요.

Codex 대상은 명시적으로 설치해야 합니다.

```bash
aeg install --target codex
```

**Codex는 사용자가 신뢰를 승인한 hook만 실행합니다. 설치 후 Codex에서 이 hook을 검토해 승인하기 전까지는 hook이 실행되지 않고 아무것도 막지 않습니다.** Codex CLI 0.156.0의 `codex exec`에서 승인 전 hook이 실행되지 않는 것을 확인했습니다.

Codex 대상 설치는 프로젝트 폴더의 `.codex/config.toml`에 `[[hooks.PreToolUse]]` command hook을 추가하고, hook command에 `aeg hook-run --substrate codex`를 기록합니다. 이 명시적 substrate 값이 있을 때만 장승(Jangseung)은 내부 판정이 `ask`/`defer`인 경계 사례를 `deny`로 격상합니다. `allow`와 기존 `deny` 판정은 바꾸지 않습니다.

0.1.3부터 Codex 설치도 TOML 파서로 기존 설정·주석을 보존하며 병합하고, 잘못된 설정은 수정하지 않습니다. 기존에 `PreToolUse = []` 또는 inline 배열이 있어도 처리합니다. hook이 이미 최신 형태로 설치되어 있지만 `.aeg/`가 없는 경우에는 다시 `aeg install --target codex`(Claude Code는 `aeg install`)을 실행하면, 확인 후 설정을 바꾸지 않고 기록 폴더만 준비합니다.

주의: 이 변경은 Codex에서 `ask`가 실행 차단 안전망으로 동작하지 않는 문제를 보완하기 위한 좁은 조치입니다. Codex hook trust/review 동작은 Codex가 처리하며, quoted path 우회 등 전체 Codex 지원은 아직 별도 실물 재검증이 필요합니다.

Codex CLI 0.166.0(Windows) 실제 세션에서 `apply_patch` 판정, `git diff`와 `git log -p`의 `.env` 제외, 프로젝트 밖 `workdir` 차단을 확인했습니다. hook이 받는 `Bash` 입력은 명령과 작업 폴더입니다. `exec_command`의 `tty`, `shell` 옵션과 `write_stdin`은 보지 못합니다. Codex에 등록된 MCP 도구와 `read_mcp_resource`는 [MCP 보호](#mcp-보호-019부터-선택)를 켠 프로젝트에서만 검사합니다.

Claude Code 제거는 반대로:

```bash
aeg uninstall
```

`aeg uninstall`은 `.claude/settings.json`에서 장승(Jangseung)이 추가한 hook만 찾아서 제거합니다. 다른 hook이나 다른 설정 항목은 건드리지 않습니다. 이 역시 백업 후 확인을 받습니다.

Codex 제거는 설치 대상과 맞춰 실행합니다 (0.1.2 이상 필요).

```bash
aeg uninstall --target codex
# 다른 작업 폴더에서 지정할 때:
aeg uninstall --target codex --path /path/to/your-project
```

`.codex/config.toml`에서 장승 command hook만 제거하고 다른 hook, 설정과 주석은 보존합니다. 유효하지 않거나 예상 밖 구조의 TOML은 수정하지 않고 오류를 표시합니다. TOML 구조와 주석 보존을 위해 `tomlkit`을 런타임 의존성으로 사용합니다. 기본 `aeg uninstall`은 계속 Claude Code 대상입니다.

제거 명령 자체가 AI의 tool call로 실행되면 장승에 의해 차단될 수 있으므로, 제거는 사용자가 일반 터미널에서 실행하세요. `aeg uninstall`은 hook 등록을 해제하는 명령이며 Python 패키지를 삭제하지 않습니다.

### MCP 보호 (0.1.9부터, 선택)

기본 설치는 MCP 도구와 MCP 리소스 읽기를 검사하지 않습니다. 필요한 프로젝트에서만 켭니다.

```bash
aeg install --mcp
aeg install --target codex --mcp
```

- 기존 hook과 별도로 MCP용 hook 항목을 하나 더 등록합니다. 기존 항목은 바꾸지 않습니다.
- 켜면 MCP 도구 호출과 MCP 리소스 읽기(Claude Code `ReadMcpResourceTool`, Codex `read_mcp_resource`)는 Claude Code에서 매번 승인을 묻고, Codex에서는 막힙니다. Codex는 `ask`를 강제하지 않기 때문입니다.
- 믿는 도구는 `.aeg/policy.json`의 `allow_mcp_tools`에 정확한 이름(`mcp__서버__도구`)으로 적으면 승인 없이 통과합니다. `*` 같은 패턴은 쓸 수 없고, 리소스 읽기는 목록에 넣을 수 없습니다.
- 장승은 MCP 도구에 넘기는 인자를 검사하지 않습니다. 목록에 넣은 도구가 파일을 읽거나 코드를 실행하면 `.env`도 읽을 수 있습니다. 이런 도구는 목록에 넣지 마세요.
- **Codex는 MCP hook을 새 hook으로 봅니다. `/hooks`에서 따로 승인해야 하며, 승인 전에는 MCP 호출을 검사하지 않습니다.** 기존 장승 hook의 승인은 그대로 유지됩니다. 설치 미리보기에서 기존 항목도 바뀌면(예: 다른 가상환경에서 실행) 그 항목도 다시 승인해야 합니다. Codex CLI 0.166.0(Windows)에서 MCP 항목을 추가한 뒤에도 기존 항목이 계속 판정하고, 새 항목은 승인 전까지 실행되지 않는 것을 확인했습니다.
- 끄려면 `aeg uninstall --mcp`(Codex는 `aeg uninstall --target codex --mcp`)를 실행합니다. 기존 hook은 남습니다. `aeg uninstall`은 두 항목을 모두 제거합니다.
- 켠 뒤 `aeg install`을 다시 실행해도 MCP hook은 유지되고, 함께 최신 형태로 고쳐집니다.
- MCP 리소스 목록 조회(Claude Code `ListMcpResourcesTool` 등)는 검사하지 않습니다. 파일 내용이 아니라 리소스 이름 목록을 돌려주는 도구입니다.

### 읽기 전용 명령 (0.1.2부터, 0.1.5에서 확장)

프로젝트 안에 실제로 존재하는 일반 파일이면 다음과 같은 읽기를 허용합니다.

```bash
cat README.md
head -n 20 README.md
sed -n '1,80p' README.md
rg --no-config -n example README.md
cat README.md | head -n 20
grep -n example README.md
wc -l README.md
```

파일을 바꾸지 않는 다음 명령도 허용합니다.

```bash
ls -la docs
pwd
git status --short
git diff --stat
git log --oneline -5
git show HEAD
```

`git diff`, `git show`, `git log -p`는 비밀 파일을 뺀 결과를 보여 줍니다. `git` 명령은 작업 폴더나 상위 폴더에 `.git`이 있을 때만 허용합니다. 저장소가 아닌 폴더에서는 에이전트가 쓴 `config`로 git이 프로그램을 실행할 수 있습니다. 같은 이유로 git 설정이 가리키는 프로젝트 안 경로(`core.hooksPath` 등)는 쓰기를 막으며, `allow_paths`로도 풀리지 않습니다. `git diff docs .`처럼 폴더를 비교하는 명령은 자동 허용하지 않습니다.

PowerShell에서는 `Get-Content`(`gc`, `cat`, `type`), `Get-ChildItem`(`gci`, `dir`, `ls`), `Test-Path`, `Get-Location`, `Select-String`과 `Select-Object` 출력 pipeline, 위의 읽기 전용 `git`을 지원합니다. 이 제한된 읽기는 Codex가 tool name을 `Bash`로 전달하는 경우에도 판정합니다.

비밀 파일, `.aeg`, 프로젝트 밖 경로의 내용을 읽으면 deny합니다. 작업 폴더가 프로젝트 밖이면 경로를 적지 않은 `git status`, `ls` 같은 명령도 deny합니다 (0.1.8부터). wildcard·디렉터리 내용 검색, 검색어 자리까지 포함한 따옴표 없는 `*`, `?`, `[`, `Get-ChildItem`에서 `Select-String`으로 넘기는 파일 검색, 유니코드 공백이나 기울어진 따옴표, 파일이 없는 경로, 변수/명령 치환, 중첩 셸, 리다이렉트, 미지원 옵션은 이 읽기 문법의 자동 허용 대상에서 제외합니다. `git`은 `-c`, `-C`, `--output`, `--ext-diff`를 쓰면 자동 허용하지 않습니다. `sed`는 숫자 행 범위의 `p` 출력만 지원하고, `rg`는 환경 설정이 외부 프로그램 실행 옵션을 끼워 넣지 않도록 `--no-config`를 요구합니다. 제한된 실행 명령의 `default` 모드 호스트 위임 외에 미분류 작업은 Claude Code에서 확인 요청, Codex에서 차단됩니다. 명령 이름에 해당하는 표준 도구를 전제로 하며, 임의로 바꾼 실행 파일이나 셸 함수의 내부 동작까지 검증하지는 않습니다.

### 단순 파일 조작 (0.2.0부터)

프로젝트 안의 비보호 일반 파일만 다루는 좁은 문법은 자동 허용합니다. 예: `mkdir -p docs/new`, `touch notes.txt`, `cp README.md copy.md`, `mv notes.txt moved.txt`, `rm notes.txt`, `echo hello > notes.txt`. PowerShell은 `Copy-Item -LiteralPath README.md -Destination copy.md`, `Move-Item -LiteralPath notes.txt -Destination moved.txt`, `Remove-Item -LiteralPath notes.txt`, `Write-Output hello > notes.txt`도 지원합니다.

경로는 영문자·숫자·`_`·`-`·`.`과 `/` 구분자로 된 단순 상대 경로만 지원합니다. 재귀 삭제, 디렉터리 복사/이동, wildcard, 링크·junction·hard link, 변수, 여러 명령 연결은 자동 허용하지 않습니다. `cp`/`mv`의 목적지는 디렉터리가 아닌 파일 경로, `rm`은 기존 일반 파일 하나여야 합니다. 리다이렉트는 리터럴 `echo`/`Write-Output`의 `>`·`>>`만 지원하며 연산자 양옆에 공백이 필요합니다. 보호/검토 경로의 기존 deny/ask 규칙이 우선합니다. 검사와 실행 사이의 파일 교체를 막는 OS 샌드박스는 아닙니다.

새 문법과 호스트 위임은 자동 테스트로 검증했습니다. 파일 조작은 Windows의 실제 Git Bash와 PowerShell에서도 대조했습니다. 0.2.1에서 Claude Code 2.1.316 `claude -p`(Windows, `default` 모드, 허용 규칙 없음)로 장승이 호스트에 맡기는 명령 40종을 한 번씩 실행해, 모두 호스트가 승인을 요구하는 것을 확인했습니다. 호스트 허용 규칙이 있는 명령은 묻지 않고 실행되었고, `acceptEdits` 모드에서는 장승이 계속 물었습니다. 대화형 세션, macOS·Linux, Codex 실제 세션은 확인하지 않았습니다. 호스트가 스스로 허용하는 명령 목록은 호스트 버전에 따라 바뀔 수 있습니다.

macOS의 `/var` 별칭처럼 신뢰한 프로젝트 루트의 별칭은 정규화하지만, 프로젝트 내부 링크는 여전히 자동 허용하지 않습니다. 명령 끝의 따옴표 없는 백슬래시는 Bash 3.2와 5.3에서 의미가 달라 deny합니다. `aeg explain`은 이를 `ambiguous_shell_syntax`로 설명합니다.

### 프로젝트 승인 정책 (0.1.5부터)

내장 규칙이 정상 작업을 막으면 `.aeg/policy.json`으로 프로젝트별 예외를 둘 수 있습니다. 에이전트는 어떤 도구로도 `.aeg/`에 쓸 수 없으므로 사람만 이 파일을 바꿀 수 있습니다. `.aeg/`는 보통 Git에서 제외되므로 이 설정은 해당 PC에만 적용됩니다.

0.2.0부터 JSON을 직접 쓰지 않고 명령으로 추가할 수 있습니다. 변경 내용을 diff로 보여 주고 확인(`y/N`)을 받으며, hook이 무시할 값은 쓰지 않습니다. 사용자가 일반 터미널에서 실행하세요. 에이전트의 tool call로는 차단됩니다.

```bash
aeg policy show
aeg policy add --command "pytest" --command "npm test"
aeg policy add --path package.json
aeg policy add --protect infra/ --mcp-tool mcp__github__get_issue
aeg policy preset python   # python, node, git 가운데 하나
```

`preset`은 흔히 쓰는 명령 묶음을 `allow_commands`에 넣습니다. `python`은 `pytest`, `ruff check`, `mypy` 등, `node`는 `npm test`, `npm run build`, `npx tsc --noEmit` 등, `git`은 `git add`, `git commit`, `git fetch`, `git switch -c`입니다. **승인한 명령은 묻지 않고 실행되며, 대부분 프로젝트의 코드(테스트, 스크립트, git hook)를 실행합니다.** 에이전트가 쓴 코드를 확인 없이 실행해도 되는 명령만 넣으세요. `python`, `node`, `bash` 같은 인터프리터 이름만 넣지 마세요. 에이전트가 쓴 어떤 코드든 묻지 않고 실행되며, 그 코드는 `.aeg/policy.json`을 고치거나 장승을 해제할 수도 있습니다. 장승이 막는 것은 `aeg policy`, `python -m jangseung.cli ...`처럼 명령줄에 드러난 호출입니다.

```json
{
  "allow_paths": ["pyproject.toml", "requirements*.txt", "tests/fixtures/*.pem"],
  "protect_paths": ["infra/", "*.tfstate"],
  "allow_commands": ["pytest", "python -m pytest", "npm test"],
  "allow_mcp_tools": ["mcp__github__get_issue"]
}
```

- `allow_paths`: 비밀 경로와, 사람에게 묻는 빌드·의존성 파일을 허용합니다. 단, `.aeg`, `.git`, `.claude/settings*.json`, `.codex`, `.mcp.json` 같은 장승 자체 설정은 풀리지 않습니다. 폴더 전체 `Grep`과 git 출력에는 파일 규칙 하나를 통째로 허용할 때만 반영됩니다. `.env`나 `*.pem`을 허용하면 포함됩니다. `.env.local`이나 `tests/fixtures/*.pem`처럼 일부만 허용하거나 `secrets` 같은 폴더를 허용하면 제외되며, 허용한 파일은 직접 지정하면 나옵니다.
- `protect_paths`: 보호 경로를 추가합니다. `allow_paths`보다 우선합니다.
- 경로 규칙은 깊이를 가리지 않습니다. `.env`처럼 파일 이름만 적으면 모든 폴더의 그 이름에 적용됩니다. 한 파일만 열려면 `config/.env`처럼 경로로 적으세요.
- `allow_commands`: 앞부분이 일치하는 단일 명령을 허용합니다. `git push`처럼 내장 규칙이 막는 명령도 풀 수 있지만 `aeg uninstall` 같은 장승 해제 명령은 풀리지 않습니다. `;`, `&&`, `|`, `>`, `$()`가 들어간 명령에는 적용되지 않고, 비밀 파일이나 보호 경로를 대상으로 하면 그대로 deny합니다. 0.2.0부터 실행되는 프로그램을 바꾸지 않는 세 가지 표기는 읽고 넘어갑니다: 따옴표로 묶인 글 안의 문자(`git commit -m 'fix(parser): #12'`), 끝의 `2>&1`, 앞의 `cd <프로젝트 안에 있는 폴더> &&`. `cd` 형태에는 조건이 있습니다. 폴더는 따옴표 없이 영문자·숫자·`_`·`-`로 된 이름(`src`, `./packages/api`)이어야 하고, 승인한 명령에 파일 이름이 없어야 합니다. `pytest`, `python -m pytest`, `npm test`는 되고 `bash scripts/run.sh`, `python tool.py`는 안 됩니다. 폴더를 옮기면 같은 상대 경로가 다른 파일을 가리키기 때문입니다. hook이 받은 환경 변수에 `CDPATH`가 있으면 `./`로 시작하는 폴더만 승인합니다. 셸 프로파일에서만 설정한 `CDPATH`는 hook이 보지 못합니다. 따옴표 안에 `$`, 백틱, 큰따옴표가 있거나, 백슬래시·기울어진 따옴표·`--%`가 함께 있거나, 따옴표가 단어 중간에서 시작하면 이전처럼 엄격하게 판정합니다. 셸마다 따옴표가 끝나는 위치가 달라질 수 있기 때문입니다. `pytest | tail`, `git commit -m "$(cat <<'EOF' ...)"` 형태는 여전히 승인되지 않습니다. 같은 세션에서 비밀 파일 이름이 든 내용을 쓴 뒤에는 승인된 명령도 사람에게 묻습니다.
- `allow_mcp_tools` (0.1.9부터): [MCP 보호](#mcp-보호-019부터-선택)를 켠 프로젝트에서 승인 없이 통과시킬 MCP 도구의 정확한 이름입니다. 형식이 맞지 않는 이름이 하나라도 있으면 파일 전체를 무시합니다.

파일이 손상되었거나 모르는 항목이 있으면 전체를 무시하고 내장 규칙만 적용합니다. `aeg doctor --hooks`가 이 상태를 알려 줍니다. 0.1.8 이하는 `allow_mcp_tools`를 모르는 항목으로 보므로, 이 항목을 넣은 파일은 전체가 무시됩니다.

### 소스에서 설치 (개발/기여용)

개발하거나 기여하려면 저장소를 클론해서 editable install 합니다.

```bash
git clone https://github.com/tjrwo736/jangseung.git
cd jangseung
# 가상환경 생성 (특히 macOS/최신 Linux 배포판에서 필요 — 시스템 Python에 직접 설치가 막힐 수 있습니다)
python -m venv venv
source venv/bin/activate
# Windows(PowerShell)는: venv\Scripts\Activate.ps1
python -m pip install -e .
```

이후 `aeg install` 사용법은 위와 동일합니다.

## 판정 설명과 설치 상태 진단

차단 제보를 확인할 때는 실제 도구를 실행하지 않는 `aeg explain`을 사용합니다. 실제 hook과 같은 판정 함수를 호출하지만, 명령 실행이나 `.aeg/` 기록은 하지 않습니다. hook이 실행될 프로젝트 디렉터리에서 사용하세요.

```bash
aeg explain --command "cat README.md" --substrate codex
aeg explain --command "pytest" --substrate codex --json
aeg explain --command "pytest" --permission-mode default --json
aeg explain --file README.md
aeg explain --command "Get-Content README.md" --tool PowerShell
```

`--file`은 파일 내용이 아닌 `Read` 요청을 판정합니다. 완전한 PreToolUse JSON은 `aeg explain --stdin --substrate codex --json`의 표준 입력으로 전달할 수 있습니다. 셸 명령줄 기록에 민감한 내용이 남지 않도록 비밀값이 있는 입력은 명령줄에 직접 적지 마세요. 출력에는 raw 입력·명령·파일 경로·파일 내용을 넣지 않고, 검증기 reason code에 붙는 임의의 값도 표시하지 않습니다.

`--permission-mode`는 `--command`에만 적용하며 생략하면 모드가 없는 입력으로 판정합니다. `default` 모드의 호스트 위임은 `permission_decision: host`, `category: host_permission_flow`로 표시합니다. 실제 호스트에 보내는 응답은 permission decision이 없는 `{}`이며, 호스트에서 실행됐다는 뜻은 아닙니다.

예를 들어 현재 규칙에서 `pytest`를 Codex 대상으로 설명하면 다음과 같이 표시합니다(발췌).

```text
hook_decision: defer
permission_decision: deny
hook_exit_code: 0
category: unclassified
summary: Safety was not established by the current rules; this is not a finding that the command is dangerous.
```

즉, **위험하다고 판단한 차단**과 **안전성을 아직 확인하지 못한 차단**을 구분합니다. Codex에서 ask/defer가 deny로 매핑되는 이유도 별도로 표시합니다. 지원하는 셸 명령이나 허용 정책을 넓히는 기능은 아닙니다.

프로젝트의 hook 등록 상태도 읽기 전용으로 점검할 수 있습니다.

```bash
aeg doctor --hooks --target codex
aeg doctor --hooks --target claude-code --json
aeg doctor --hooks --json  # 두 대상 모두 확인
```

등록된 설정의 형식·substrate·matcher, 실패 시 차단 설정, 현재 환경의 실행 파일 존재, 기록 폴더·PID 잠금·guard·hook chain, 승인 정책 파일을 확인합니다. 설정을 수정하거나 실행 파일을 실행하지 않고, 쓰기 가능 여부도 권한 정보만 확인합니다. 종료된 PID 잠금을 발견해도 doctor가 삭제하지 않습니다. `.aeg/.gitignore` 내부 규칙과 실제 추적 제외 예외도 점검합니다. `aeg doctor --json`은 기존 기본 진단을 JSON으로 출력하며, `--hooks`가 없으면 hook 등록을 요구하지 않습니다.

주의: `explain`의 종료 코드 0은 **설명 완료**이지 실행 허가가 아닙니다. 실제 hook의 종료 코드는 별도 `hook_exit_code` 필드입니다. 잘못된 입력/fail-closed 또는 진단 실패는 1, 명령 사용법 오류는 2입니다. **설치된 `hook-run`을 `explain`으로 바꾸지 마세요.** 실제 앱의 신뢰 승인·전역 설정·hook 호출 여부, 기록 장치의 실제 쓰기 성공은 이 진단만으로 증명하지 않습니다(`NOT_CHECKED`).

## Evidence 조회와 라이브 hook 기록

`aeg hook-run` 판정은 `.aeg/hook_ledger.jsonl`에 append-only로 기록합니다. 쓰기 없이 조회하고 chain을 검증할 수 있습니다.

```bash
aeg evidence list --limit 20
aeg evidence list --json
aeg evidence show <hook-record-hash-prefix>
aeg evidence verify-hooks
aeg evidence repair-hooks
```

`list`는 최신순으로 시각, 판정, 도구, 대상을 보여 줍니다. `show`는 summary, decision, call, integrity 섹션으로 나눕니다. 조회 결과는 credential 형태 필터를 거치며 `.aeg`를 수정하지 않습니다. 손상된 행은 `UNREADABLE`로 표시합니다.

기록 한 건에 들어가는 것은 다음과 같습니다.

- 판정: substrate, tool name, 판정/permission, fail-closed 여부, reason code, exit code, hash chain
- 대상 (0.2.0부터): 프로젝트 상대 경로(`targets`), 명령의 프로그램 이름(`commands`, 예: `git push`, `pytest`), 호스트의 세션 ID(`session_id`), 입력 전체의 SHA-256(`input_hash`)

호스트 위임은 `HOST`로 표시하며 `hook_decision: defer`, `permission_decision: host`, `record_version: hook_decision_record_v2`로 기록합니다. 호스트의 최종 승인이나 실행 결과를 기록한 것은 아닙니다. 일반 allow/ask/deny는 기존 v1을 유지하고 0.2.0은 혼합 chain을 검증합니다. **0.1.9 이하에서는 v2가 들어간 chain을 검증하거나 이어 쓸 수 없습니다.** 다운그레이드 전에 기록을 보존하고 별도의 기록 운영 계획을 세우세요. 자동으로 변환하거나 삭제하지 않습니다.

들어가지 않는 것: 파일 내용, 명령 인자와 명령 원문, raw `tool_input`. 프로젝트 밖 경로는 `<outside-project>`로만 적습니다. 프로그램 이름은 명령 자리에 따옴표 없이 적힌 짧은 이름(24자 이하, 숫자 3개 이하, `-` 2개 이하)일 때만 적고 그 밖에는 `<other>`로 적습니다. 치환(`$()`, 백틱, `$변수`)이 든 Bash 명령은 `<dynamic>`으로만 적습니다. 이 꼴에 맞는 낱말이 명령 자리에 있으면 무엇이든 기록되고, 파일 이름도 그대로 기록됩니다. 이름 자체가 비밀이면 기록에도 남습니다. 0.1.9 이하가 쓴 기록에는 대상 항목이 없으며 그대로 검증됩니다.

0.1.9까지 있던 `aeg run`, `aeg verify`, `aeg init`과 run evidence 조회는 0.2.0에서 제거했습니다. `.aeg/ledger.jsonl`, `.aeg/runs/`, `.aeg/config.json`이 남아 있어도 읽거나 지우지 않습니다.

hook 기록에 실패해도 이미 계산된 `permissionDecision`과 exit code는 바뀌지 않습니다. 대신 응답 reason code에 `hook_decision_recording_failed`가 추가됩니다. 이는 기록 장치 장애가 정상 판정을 임의로 allow/deny로 재분류하지 않도록 판정 브레인과 recorder를 분리하기 위한 선택입니다. 단, 기존 판정 자체가 fail-closed deny인 경우에는 그대로 deny를 유지합니다.

호스트 위임에서 기록이 실패하면 permission decision을 만들지 않고 고정된 `systemMessage`에 실패 사유를 넣습니다. 호스트 승인 흐름은 그대로 유지합니다.

hook ledger의 hash chain은 중간 레코드의 변경·삭제를 탐지하기 위한 tamper-evident 장치입니다. 외부 anchor가 없는 로컬 파일이므로 마지막 레코드와 파일 전체를 함께 삭제하는 공격까지 증명하는 tamper-proof 저장소는 아닙니다.

0.1.3부터 잘못된 UTF-8 ledger 행은 `UNREADABLE`로 표시하면서 다른 항목을 계속 조회합니다. artifact가 없는 run도 목록에서 `UNREADABLE`로 표시합니다. 조회는 손상된 데이터를 고치거나 재작성하지 않습니다.

0.1.5부터 hook 호출은 마지막 기록만 확인하고 이어 씁니다. ledger가 커져도 호출이 느려지지 않게 하기 위해서이며, chain 전체 검증은 `aeg evidence verify-hooks`가 합니다. 중간 기록이 손상되면 기록은 계속되고 전체 검증이 실패합니다. 마지막 기록이 손상되면 추가 기록을 거부합니다. `aeg evidence repair-hooks`를 실행하면 손상된 행부터 끝까지 `.aeg/`의 격리 파일로 옮기고, 격리한 내용의 hash를 담은 복구 기록으로 chain을 이어 갑니다. 복구 명령은 사용자가 일반 터미널에서 실행하세요. 에이전트의 tool call로는 차단됩니다.

기록 시 `.aeg/hook_ledger.guard`의 OS 잠금과 기존 PID 잠금 파일을 함께 사용합니다. guard 파일이 남아 있는 것은 정상이며 삭제하지 마세요. 종료된 프로세스의 PID 잠금은 다음 기록 시 복구하지만, 실행 중이거나 소유자를 알 수 없는 잠금은 탈취하지 않습니다. 빈 파일·잘못된 PID 등은 관련 프로세스를 모두 중지한 뒤 별도 확인이 필요합니다. 네트워크 파일시스템의 잠금 동작까지 보장하지는 않습니다.

## 어떻게 작동하나

장승(Jangseung)은 PreToolUse hook으로 동작합니다. AI가 파일을 쓰거나 명령을 실행하는 tool call을 하려는 순간, 실행되기 직전에 그 요청이 장승(Jangseung)으로 전달됩니다. 장승(Jangseung)은 요청을 판정해서 위험하면 막고, 정상이면 통과시키고, 애매하면 확인을 요청합니다. 단, `--target codex`로 설치된 hook은 Codex가 `ask`를 강제 차단하지 않는 것으로 확인되어 애매한 `ask`/`defer` 판정을 `deny`로 응답합니다.

판정은 결정론적입니다 — 같은 입력, 같은 파일시스템 상태, 같은 세션 표시(`.aeg/session_marks.json`)에는 같은 결과가 나옵니다.

0.2.0의 제한된 실행 명령은 Claude Code `default`에서 위의 예외대로 호스트 승인 정책에 맡깁니다. 이는 [Claude Code hook 계약](https://code.claude.com/docs/en/hooks)의 permission decision 생략이며, `allow`나 wire 값 `defer`를 보내는 것이 아닙니다.

막거나 물을 때 호스트에 돌려주는 사유는 0.2.0부터 문장으로 시작합니다. 무엇 때문에 멈췄는지와 사람이 할 수 있는 일(`aeg policy add ...` 등)을 적고, 그 뒤에 기존 reason code를 붙입니다. 문장은 고정된 글이며 입력의 경로나 명령은 들어가지 않습니다. 경로 경계와 셸 읽기 판정은 파일의 실제 위치·존재 여부를 확인합니다. 판정 근거가 불확실할 때는 안전한 쪽(막거나 확인 요청)으로 실패합니다(fail-closed).

## 요구사항 / 현재 상태

- **Claude Code와 Codex에서 검증됨**: Linux/WSL과 Windows 네이티브 양쪽에서 실제 Claude Code 세션과 Codex CLI 세션으로 주요 PreToolUse hook 경로가 정상 작동하는 것을 확인했습니다. Windows에서는 각 substrate의 실행 방식 차이(Claude Code hook command 실행 형태, Codex deny 응답의 종료 코드 처리, PowerShell tool 등)에 맞춰 별도로 대응했습니다. `aeg install --target claude-code`(기본값) 또는 `aeg install --target codex`로 각각 설치합니다. 두 substrate는 판정 방식이 일부 다릅니다 — Claude Code에서는 애매한 작업에 확인을 요청(ask)하지만, Codex에서는 그 확인 요청이 실행을 막는 안전망으로 동작하지 않는다는 것이 실측으로 확인되어, Codex에서는 애매한 경우 더 엄격하게 차단(deny)합니다. 다만 Codex에서 `Bash` tool name으로 전달되는 PowerShell 쓰기/삭제 명령은 아직 구조적으로 파싱하지 않습니다. 제한된 `Get-Content` 읽기는 0.1.2부터 지원합니다. 0.1.5의 변경은 자동 회귀 테스트와 hook CLI 실측으로 검증했고, Windows의 Claude Code 2.1.316 비대화형 세션에서 주요 경로를 확인했습니다. 권한 우회 모드, Codex 실제 세션의 판정, Linux/macOS 실제 세션은 재확인이 필요합니다.
- **기본 정책은 코드에 하드코딩되어 있습니다.** 프로젝트별 예외는 `.aeg/policy.json`으로 둘 수 있습니다.
- **비밀(secret) 판정은 경로와 의도 기반입니다.** `.env` 같은 파일에 쓰는 시도 자체는 막지만, 파일 내용에서 실제 API 키/비밀번호 값을 스캔하는 기능은 아직 없습니다 (로드맵 예정).
- Python 3.10 이상이 필요합니다.

## 개발

이 프로젝트는 Claude Code와 Codex를 사용해 개발했습니다. 모든 판정 로직은 실제 Claude Code / Codex 환경에서 반복 검증했으며, README에 적은 지원 범위와 한계는 그 실측 결과를 그대로 반영합니다.

## 보안 문제 신고

취약점은 공개 이슈에 적지 말고 [보안 정책](https://github.com/tjrwo736/jangseung/blob/main/SECURITY.md)에 적힌 방법으로 알려 주세요.

## 라이선스

이 프로젝트는 MIT 라이선스로 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.
