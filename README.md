![장승(Jangseung) — 코딩 에이전트의 문지기](https://raw.githubusercontent.com/tjrwo736/jangseung/main/docs/assets/jangseung-hero.png)

# 장승(Jangseung) — AI 코딩 에이전트를 위한 방패

Claude Code에게 코드를 맡기되, 위험한 것이 실행되기 전에 막습니다.

장승은 한국 전통 마을 어귀에 세워져 나쁜 것을 막던 수호신상입니다. 이 도구도 AI 에이전트가 위험한 작업을 하기 전, 그 경계에 서 있습니다.

[![asciicast](https://asciinema.org/a/6B2AARAZCOKB9snJ.svg)](https://asciinema.org/a/6B2AARAZCOKB9snJ)

실제 Claude Code 세션에서 장승(Jangseung)이 위험한 작업을 막고 정상 작업은 통과시키는 데모

## 핵심 3가지

- **위험한 것만 막습니다**: `.env` 유출, 배포 설정 변경, `rm -rf` 같은 파괴 명령을 실행 전에 멈춥니다. 정상 작업은 방해하지 않습니다.
- **변조를 탐지할 수 있는 기록**: 일반 run evidence와 라이브 hook 판정을 분리해 기록하고, 각 ledger의 hash chain으로 사후 변조를 탐지합니다. 로컬 파일이므로 tamper-proof라고 주장하지 않습니다.
- **프롬프트 인젝션 방어**: 조작된 지시로 위험한 행동을 하려 해도 tool call 단계에서 걸러냅니다.

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
- 공급망/빌드 위험: `.github/workflows`, `.gitlab-ci.yml` 같은 CI 설정, `Dockerfile`, `pyproject.toml`, `requirements*.txt`, 배포 스크립트 수정. 읽기는 허용합니다.
- 되돌릴 수 없는 파괴: `rm -rf`, `git reset --hard`, `git clean -f`, `git checkout -- .`
- 외부 반출과 배포: `git push`, `npm publish`, `gh release create`, `kubectl apply`, `terraform apply`, `curl`
- 장승 무력화: `.claude/settings*.json`, `.codex/`, `.mcp.json`, `.git/` 수정과 `aeg uninstall` 실행
- git이 실행하는 파일: `core.hooksPath`, `include.path`, `core.fsmonitor`, `gpg.program` 등 git 설정이 가리키는 프로젝트 안 경로의 수정 (0.1.7부터)
- 감시 기록 조작: executor가 `.aeg` 디렉토리에 직접 쓰는 행위 (장승의 신뢰된 내부 recorder만 전용 ledger에 기록)
- 범위 밖 접근: 프로젝트 폴더 바깥 경로 (`/etc`, `~/.ssh` 등). 작업 폴더가 프로젝트 밖인 읽기 명령도 포함합니다 (0.1.8부터)

이 판정은 파일을 직접 쓰는 경우(Write/Edit)뿐 아니라, Bash 명령이나 Windows Claude Code의 PowerShell 명령으로 우회하려는 경우(`echo > .env`, `Remove-Item .env` 같은)도 동일하게 적용됩니다. 줄바꿈, 괄호, `&`, `;`로 명령을 이어 붙여도 안에 든 명령을 따로 판정하고, 세션이 하위 폴더로 이동해도 보호 경로는 프로젝트 루트 기준으로 유지합니다.

막지 않습니다 (그냥 통과):

- 코드 읽기, 일반 파일 편집, README 수정, 빌드 설정 파일 읽기
- `ls`, `pwd`, `git status`, `git diff`, `git log`처럼 파일을 바꾸지 않는 명령
- 위험하지 않은 정상 작업은 방해하지 않습니다.

판단이 애매하면 (물어봅니다):

- 분류되지 않은 명령, 확실하지 않은 작업은 그냥 통과시키지 않고 확인을 요청합니다.
- `pytest`, `npm test`처럼 프로젝트 코드를 실행하는 명령도 여기에 속합니다. 반복해서 쓰는 명령은 [프로젝트 승인 정책](#프로젝트-승인-정책-015부터)에 등록할 수 있습니다.
- `.git`이 없는 폴더의 `git` 명령과 `git diff docs .`처럼 폴더를 비교하는 명령도 확인을 요청합니다.

## 우리가 못 막는 것

장승(Jangseung)은 "완벽하게 안전하다"고 말하지 않습니다. 지키는 선을 정확히 말합니다.

장승(Jangseung)은 AI가 파일을 쓰거나 명령을 실행하는 등 도구를 사용하려는 순간에 끼어들어 판단합니다. 그래서 도구를 거치지 않는 것들 — AI가 참조로 직접 읽어 들이는 파일 내용, 이미 허용된 명령이 내부에서 실행하는 다른 프로그램 — 은 이 선 바깥에 있습니다.

또한 변수 치환이나 중첩 셸처럼 복잡하게 감춰진 명령은 대상을 정밀하게 판별하지 못해, 이 경우 자동 통과가 아니라 확인을 요청합니다.

hook이 검사하는 도구는 `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Read`, `Grep`, `Glob`, `Bash`, Windows의 `PowerShell`, Codex의 `apply_patch`입니다. `WebFetch`, `WebSearch`, MCP 도구, MCP 리소스 읽기는 검사 대상이 아니며, 이 도구들로 나가는 내용은 장승이 보지 못합니다. 코드를 실행하거나 파일을 읽는 MCP 도구, 파일을 리소스로 제공하는 MCP 서버는 장승의 판정을 거치지 않고 파일 내용을 에이전트에게 넘길 수 있습니다.

실제 세션(Claude Code 2.1.316 `claude -p`, Codex CLI 0.166.0 `codex exec`, Windows)에서 더미 `.env`로 경우마다 한 번씩 확인했습니다. 값이 출력된 경우에는 모두 장승 기록이 남지 않았습니다.

- **Claude Code의 MCP 도구:** auto 모드와, Manual 모드(도구마다 승인을 묻는 모드)에서 미리 허용한 도구는 값이 출력되었습니다. Manual 모드에서 미리 허용하지 않은 도구는 승인을 요구해 실행되지 않았습니다.
- **Claude Code의 MCP 리소스 읽기(`ReadMcpResourceTool`):** Manual 모드에서도 승인 요구 없이 값이 출력되었습니다. auto 모드도 같습니다.
- **Codex의 MCP 도구와 `read_mcp_resource`:** `approval_policy=never` 설정에서 값이 출력되었습니다. `mcp__node_repl__js`도 포함됩니다.

이런 MCP 서버가 등록되어 있으면 등록을 해제하거나 호스트의 승인 설정을 확인하세요.

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
| 지원됨 | 보호 경로(`.env`, `.github/workflows`, `Dockerfile`, `.aeg`, 정책/판정 코드 등)를 직접 대상으로 하는 `Write`/`Edit` deny. 0.1.5부터 `Read` deny는 비밀 파일, `.aeg`, 프로젝트 밖 경로로 좁혔습니다 |
| 지원됨 | Bash의 보호 경로 쓰기/삭제 deny: 리다이렉트, heredoc 계열, `tee`, `cp`, `mv`, `rm`, `dd`, `truncate`, `ln` 등 구조적으로 파악 가능한 쓰기/삭제 타깃 포함 |
| 지원됨 | PowerShell의 보호 경로 쓰기/삭제 deny: `Remove-Item`/`rm`/`del`/`ri`/`erase`, `Set-Content`/`sc`, `Add-Content`/`ac`, `Clear-Content`, `New-Item`, `Rename-Item`, `Out-File`, `Tee-Object`, `>`/`>>`, `Move-Item`/`Copy-Item` 등 구조적으로 파악 가능한 쓰기/삭제 타깃 포함 |
| 지원됨 (0.1.5부터) | PowerShell 자동 허용은 `Get-Content`, `Get-ChildItem`, `Test-Path` 등의 좁은 읽기 문법을 통과한 명령에만 적용. 비밀 파일과 프로젝트 밖 읽기는 deny. `Get-ChildItem`을 `Select-String`으로 넘기는 파일 검색, 유니코드 공백이나 기울어진 따옴표가 있는 명령은 0.1.7부터 자동 허용하지 않음 |
| 지원됨 | 위험 명령 deny: `rm -rf`, `git reset --hard`, `git clean -f`, `git checkout -- .`, `git push`, 공개·배포 명령(`npm publish`, `gh release create`, `kubectl apply`, `terraform apply` 등). 경로로 지정하거나 `git -C`, `bash -c`로 감싸도 적용 |
| 지원됨 | 정상 파일 작업 allow: repo 내부의 명확히 안전한 읽기/쓰기/편집은 방해하지 않음 |
| 지원됨 | Codex `apply_patch` tool call의 target-aware 판정: 보호 경로 deny, 정상 경로 allow (Windows 네이티브 hook exit code 처리 포함 실측). 프로젝트 안 파일은 0.1.8부터 절대 경로로 적어도 같은 판정 (Codex CLI 0.166.0, Windows 실제 세션에서 확인) |
| 지원됨 | 프로젝트 로컬 Codex 설치: `aeg install --target codex` |
| 지원됨 (0.1.2부터) | Codex 제거: `aeg uninstall --target codex`; 다른 hook과 TOML 설정/주석 보존, diff 확인과 백업 |
| 지원됨 (0.1.2부터) | 프로젝트 내부 일반 파일의 제한된 셸 읽기: `cat`, `head`/`tail`, 출력 전용 `sed -n`, `rg --no-config`, `Get-Content` 및 단순 출력 pipeline |
| 지원됨 (0.1.7부터) | `git diff`, `git show`, `git log -p`의 비밀 파일 제외: 추적 파일과 이력 모두. 객체 ID는 커밋으로만 해석 (Claude Code 2.1.316, Windows 실제 세션에서 확인. Codex CLI 0.166.0은 `git diff`, `git log -p`를 Windows 실제 세션에서 확인) |
| 지원됨 (0.1.5부터) | 파일을 바꾸지 않는 명령 자동 허용: `ls`, `pwd`, `echo`, `grep`, `wc`, `test`, 읽기 전용 `git`(`status`, `diff`, `log`, `show`, `blame`, `branch` 조회 등). `git`은 0.1.7부터 작업 폴더나 상위 폴더에 `.git`이 있을 때만. 0.1.8부터 작업 폴더가 프로젝트 밖이면 이 명령들 모두 deny |
| 지원됨 (0.1.5부터) | 프로젝트 승인 정책: `.aeg/policy.json`으로 경로와 명령을 승인. 에이전트는 이 파일을 수정할 수 없음. 승인한 명령은 0.1.8부터 프로젝트 안에서만 자동 허용 |
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

기존 사용자는 장승을 설치했던 가상환경을 활성화한 뒤 업데이트하세요. 0.1.2에는 제한된 셸 문서 읽기와 Codex hook 제거 수정이, 0.1.3에는 설치·제거 시 설정 보존과 기록 안정성 수정이, 0.1.5에는 보안 우회 수정이, 0.1.6에는 구형 hook 업그레이드 수정이, 0.1.7에는 검색과 셸 읽기 명령으로 비밀 값이 출력되고 `git` 명령으로 프로그램이 실행되던 결함 수정이, 0.1.8에는 프로젝트 밖 폴더의 `git` 명령이 자동 허용되던 결함과 `apply_patch` 절대 경로 과차단 수정이 포함됩니다.

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

Codex 대상은 명시적으로 설치해야 합니다.

```bash
aeg install --target codex
```

**Codex는 사용자가 신뢰를 승인한 hook만 실행합니다. 설치 후 Codex에서 이 hook을 검토해 승인하기 전까지는 hook이 실행되지 않고 아무것도 막지 않습니다.** Codex CLI 0.156.0의 `codex exec`에서 승인 전 hook이 실행되지 않는 것을 확인했습니다.

Codex 대상 설치는 프로젝트 폴더의 `.codex/config.toml`에 `[[hooks.PreToolUse]]` command hook을 추가하고, hook command에 `aeg hook-run --substrate codex`를 기록합니다. 이 명시적 substrate 값이 있을 때만 장승(Jangseung)은 내부 판정이 `ask`/`defer`인 경계 사례를 `deny`로 격상합니다. `allow`와 기존 `deny` 판정은 바꾸지 않습니다.

0.1.3부터 Codex 설치도 TOML 파서로 기존 설정·주석을 보존하며 병합하고, 잘못된 설정은 수정하지 않습니다. 기존에 `PreToolUse = []` 또는 inline 배열이 있어도 처리합니다. hook이 이미 최신 형태로 설치되어 있지만 `.aeg/`가 없는 경우에는 다시 `aeg install --target codex`(Claude Code는 `aeg install`)을 실행하면, 확인 후 설정을 바꾸지 않고 기록 폴더만 준비합니다. 일반 `aeg run`에 필요한 전체 상태 초기화는 별도로 `aeg init`을 사용합니다.

주의: 이 변경은 Codex에서 `ask`가 실행 차단 안전망으로 동작하지 않는 문제를 보완하기 위한 좁은 조치입니다. Codex hook trust/review 동작은 Codex가 처리하며, quoted path 우회 등 전체 Codex 지원은 아직 별도 실물 재검증이 필요합니다.

Codex CLI 0.166.0(Windows) 실제 세션에서 `apply_patch` 판정, `git diff`와 `git log -p`의 `.env` 제외, 프로젝트 밖 `workdir` 차단을 확인했습니다. hook이 받는 `Bash` 입력은 명령과 작업 폴더입니다. `exec_command`의 `tty`, `shell` 옵션과 `write_stdin`은 보지 못합니다. Codex에 등록된 MCP 도구와 `read_mcp_resource`도 검사하지 않습니다.

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

비밀 파일, `.aeg`, 프로젝트 밖 경로의 내용을 읽으면 deny합니다. 작업 폴더가 프로젝트 밖이면 경로를 적지 않은 `git status`, `ls` 같은 명령도 deny합니다 (0.1.8부터). wildcard·디렉터리 내용 검색, 검색어 자리까지 포함한 따옴표 없는 `*`, `?`, `[`, `Get-ChildItem`에서 `Select-String`으로 넘기는 파일 검색, 유니코드 공백이나 기울어진 따옴표, 파일이 없는 경로, 변수/명령 치환, 중첩 셸, 리다이렉트, 미지원 옵션은 자동 허용 대상에서 제외합니다. `git`은 `-c`, `-C`, `--output`, `--ext-diff`를 쓰면 자동 허용하지 않습니다. `sed`는 숫자 행 범위의 `p` 출력만 지원하고, `rg`는 환경 설정이 외부 프로그램 실행 옵션을 끼워 넣지 않도록 `--no-config`를 요구합니다. 미분류 작업은 기존처럼 Claude Code에서 확인 요청, Codex에서 차단됩니다. 명령 이름에 해당하는 표준 도구를 전제로 하며, 임의로 바꾼 실행 파일이나 셸 함수의 내부 동작까지 검증하지는 않습니다.

### 프로젝트 승인 정책 (0.1.5부터)

내장 규칙이 정상 작업을 막으면 `.aeg/policy.json`으로 프로젝트별 예외를 둘 수 있습니다. 에이전트는 어떤 도구로도 `.aeg/`에 쓸 수 없으므로 사람만 이 파일을 바꿀 수 있습니다. `.aeg/`는 보통 Git에서 제외되므로 이 설정은 해당 PC에만 적용됩니다.

```json
{
  "allow_paths": ["pyproject.toml", "requirements*.txt", "tests/fixtures/*.pem"],
  "protect_paths": ["infra/", "*.tfstate"],
  "allow_commands": ["pytest", "python -m pytest", "npm test"]
}
```

- `allow_paths`: 보호 경로나 비밀 경로를 허용합니다. 단, `.aeg`, `.git`, `.claude/settings*.json`, `.codex`, `.mcp.json` 같은 장승 자체 설정은 풀리지 않습니다. 폴더 전체 `Grep`과 git 출력에는 파일 규칙 하나를 통째로 허용할 때만 반영됩니다. `.env`나 `*.pem`을 허용하면 포함됩니다. `.env.local`이나 `tests/fixtures/*.pem`처럼 일부만 허용하거나 `secrets` 같은 폴더를 허용하면 제외되며, 허용한 파일은 직접 지정하면 나옵니다.
- `protect_paths`: 보호 경로를 추가합니다. `allow_paths`보다 우선합니다.
- `allow_commands`: 앞부분이 일치하는 단일 명령을 허용합니다. `git push`처럼 내장 규칙이 막는 명령도 풀 수 있지만 `aeg uninstall` 같은 장승 해제 명령은 풀리지 않습니다. `;`, `&&`, `|`, `>`, `$()`가 들어간 명령에는 적용되지 않고, 비밀 파일이나 보호 경로를 대상으로 하면 그대로 deny합니다.

파일이 손상되었거나 모르는 항목이 있으면 전체를 무시하고 내장 규칙만 적용합니다. `aeg doctor --hooks`가 이 상태를 알려 줍니다.

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
aeg explain --file README.md
aeg explain --command "Get-Content README.md" --tool PowerShell
```

`--file`은 파일 내용이 아닌 `Read` 요청을 판정합니다. 완전한 PreToolUse JSON은 `aeg explain --stdin --substrate codex --json`의 표준 입력으로 전달할 수 있습니다. 셸 명령줄 기록에 민감한 내용이 남지 않도록 비밀값이 있는 입력은 명령줄에 직접 적지 마세요. 출력에는 raw 입력·명령·파일 경로·파일 내용을 넣지 않고, 검증기 reason code에 붙는 임의의 값도 표시하지 않습니다.

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

기존 run evidence는 쓰기 없이 조회할 수 있습니다.

```bash
aeg evidence list --limit 20
aeg evidence show <run-id>
aeg evidence list --json
aeg evidence show <run-id> --json
```

`list`는 최신순으로 run id, 시각, 판정 요약과 artifact 존재 여부를 보여 줍니다. `show`는 100개가 넘는 필드를 평면으로 덤프하지 않고 summary, decision, artifacts, provenance, integrity 섹션으로 나눕니다. 조회 결과는 credential 형태 필터를 거치며 `.aeg`를 수정하지 않습니다. 손상된 ledger line이나 누락 artifact는 `UNREADABLE`로 표시합니다.

라이브 `aeg hook-run` 판정은 일반 run ledger와 섞지 않고 `.aeg/hook_ledger.jsonl`에 append-only로 기록합니다. 기록에는 substrate, tool name, 판정/permission, fail-closed 여부, reason code, exit code와 hash chain만 포함되며 raw `tool_input`은 저장하지 않습니다. 다음 명령으로 함께 조회하고 chain을 검증할 수 있습니다.

```bash
aeg evidence list
aeg evidence show <hook-record-hash-prefix>
aeg evidence verify-hooks
aeg evidence repair-hooks
```

hook 기록에 실패해도 이미 계산된 `permissionDecision`과 exit code는 바뀌지 않습니다. 대신 응답 reason code에 `hook_decision_recording_failed`가 추가됩니다. 이는 기록 장치 장애가 정상 판정을 임의로 allow/deny로 재분류하지 않도록 판정 브레인과 recorder를 분리하기 위한 선택입니다. 단, 기존 판정 자체가 fail-closed deny인 경우에는 그대로 deny를 유지합니다.

두 ledger의 hash chain은 중간 레코드의 변경·삭제를 탐지하기 위한 tamper-evident 장치입니다. 외부 anchor가 없는 로컬 파일이므로 마지막 레코드와 파일 전체를 함께 삭제하는 공격까지 증명하는 tamper-proof 저장소는 아닙니다.

0.1.3부터 잘못된 UTF-8 ledger 행은 `UNREADABLE`로 표시하면서 다른 항목을 계속 조회합니다. artifact가 없는 run도 목록에서 `UNREADABLE`로 표시합니다. 조회는 손상된 데이터를 고치거나 재작성하지 않습니다.

0.1.5부터 hook 호출은 마지막 기록만 확인하고 이어 씁니다. ledger가 커져도 호출이 느려지지 않게 하기 위해서이며, chain 전체 검증은 `aeg evidence verify-hooks`가 합니다. 중간 기록이 손상되면 기록은 계속되고 전체 검증이 실패합니다. 마지막 기록이 손상되면 추가 기록을 거부합니다. `aeg evidence repair-hooks`를 실행하면 손상된 행부터 끝까지 `.aeg/`의 격리 파일로 옮기고, 격리한 내용의 hash를 담은 복구 기록으로 chain을 이어 갑니다. 복구 명령은 사용자가 일반 터미널에서 실행하세요. 에이전트의 tool call로는 차단됩니다.

기록 시 `.aeg/hook_ledger.guard`의 OS 잠금과 기존 PID 잠금 파일을 함께 사용합니다. guard 파일이 남아 있는 것은 정상이며 삭제하지 마세요. 종료된 프로세스의 PID 잠금은 다음 기록 시 복구하지만, 실행 중이거나 소유자를 알 수 없는 잠금은 탈취하지 않습니다. 빈 파일·잘못된 PID 등은 관련 프로세스를 모두 중지한 뒤 별도 확인이 필요합니다. 네트워크 파일시스템의 잠금 동작까지 보장하지는 않습니다.

## 어떻게 작동하나

장승(Jangseung)은 PreToolUse hook으로 동작합니다. AI가 파일을 쓰거나 명령을 실행하는 tool call을 하려는 순간, 실행되기 직전에 그 요청이 장승(Jangseung)으로 전달됩니다. 장승(Jangseung)은 요청을 판정해서 위험하면 막고, 정상이면 통과시키고, 애매하면 확인을 요청합니다. 단, `--target codex`로 설치된 hook은 Codex가 `ask`를 강제 차단하지 않는 것으로 확인되어 애매한 `ask`/`defer` 판정을 `deny`로 응답합니다.

판정은 결정론적입니다 — 같은 입력과 같은 파일시스템 상태에는 같은 결과가 나옵니다. 경로 경계와 셸 읽기 판정은 파일의 실제 위치·존재 여부를 확인합니다. 판정 근거가 불확실할 때는 안전한 쪽(막거나 확인 요청)으로 실패합니다(fail-closed).

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
