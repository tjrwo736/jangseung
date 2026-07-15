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

- 비밀 노출 위험: `.env`, 비밀키, 배포 설정 파일 수정
- 공급망/빌드 위험: `.github/workflows`, `Dockerfile`, 배포 스크립트 수정
- 되돌릴 수 없는 파괴: `rm -rf`, `git reset --hard`, `git clean -fd`
- 감시 기록 조작: executor가 `.aeg` 디렉토리에 직접 쓰는 행위 (장승의 신뢰된 내부 recorder만 전용 ledger에 기록)
- 범위 밖 접근: 프로젝트 폴더 바깥 경로 (`/etc`, `~/.ssh` 등)

이 판정은 파일을 직접 쓰는 경우(Write/Edit)뿐 아니라, Bash 명령이나 Windows Claude Code의 PowerShell 명령으로 우회하려는 경우(`echo > .env`, `Remove-Item .env` 같은)도 동일하게 적용됩니다.

막지 않습니다 (그냥 통과):

- 코드 읽기, 일반 파일 편집, README 수정
- 위험하지 않은 정상 작업은 방해하지 않습니다.

판단이 애매하면 (물어봅니다):

- 분류되지 않은 명령, 확실하지 않은 작업은 그냥 통과시키지 않고 확인을 요청합니다.

## 우리가 못 막는 것

장승(Jangseung)은 "완벽하게 안전하다"고 말하지 않습니다. 지키는 선을 정확히 말합니다.

장승(Jangseung)은 AI가 파일을 쓰거나 명령을 실행하는 등 도구를 사용하려는 순간에 끼어들어 판단합니다. 그래서 도구를 거치지 않는 것들 — AI가 참조로 직접 읽어 들이는 파일 내용, 이미 허용된 명령이 내부에서 실행하는 다른 프로그램 — 은 이 선 바깥에 있습니다.

또한 변수 치환이나 중첩 셸처럼 복잡하게 감춰진 명령은 대상을 정밀하게 판별하지 못해, 이 경우 자동 통과가 아니라 확인을 요청합니다.

다르게 말하면, 장승(Jangseung)은 문 앞을 지키는 경비이지 집 안 모든 방을 감시하는 CCTV가 아닙니다.

이 한계를 감추지 않는 것이 장승(Jangseung)이 신뢰를 얻는 방식입니다.

## 지원 범위

현재 구현과 실측 기준의 범위입니다. 장승(Jangseung)은 Claude Code 전체나 Codex 전체를 안전하게 만든다고 주장하지 않습니다.

| 상태 | 범위 |
| --- | --- |
| 지원됨 | 실행 환경: Linux/WSL, Windows 네이티브에서 실물 검증 |
| 지원됨 | Claude Code `Write`/`Edit`/`Read`/`Bash` 주요 PreToolUse hook 경로 (Linux/WSL 및 Windows 네이티브 실측) |
| 지원됨 | Windows Claude Code `PowerShell` 주요 PreToolUse hook 경로와 흔한 PowerShell 쓰기/삭제 target 판정 |
| 지원됨 | 프로젝트 로컬 Claude Code 설치: `aeg install --target claude-code` (기본값) |
| 지원됨 | 보호 경로(`.env`, `.github/workflows`, `Dockerfile`, `.aeg`, 정책/판정 코드 등)를 직접 대상으로 하는 `Read`/`Write`/`Edit` deny |
| 지원됨 | Bash의 보호 경로 쓰기/삭제 deny: 리다이렉트, heredoc 계열, `tee`, `cp`, `mv`, `rm`, `dd`, `truncate`, `ln` 등 구조적으로 파악 가능한 쓰기/삭제 타깃 포함 |
| 지원됨 | PowerShell의 보호 경로 쓰기/삭제 deny: `Remove-Item`/`rm`/`del`, `Set-Content`, `Out-File`, `>`/`>>`, `Move-Item`/`Copy-Item -Destination` 등 구조적으로 파악 가능한 쓰기/삭제 타깃 포함 |
| 지원됨 | PowerShell read-only 명령(`Get-Content`, `Get-ChildItem`, `Test-Path`)은 쓰기/삭제 타깃으로 오탐 deny하지 않음 |
| 지원됨 | 위험 명령 deny: `rm -rf`, `git reset --hard`, `git clean -fd`, `git push`, 배포 관련 명령 등 |
| 지원됨 | 정상 파일 작업 allow: repo 내부의 명확히 안전한 읽기/쓰기/편집은 방해하지 않음 |
| 지원됨 | Codex `apply_patch` tool call의 target-aware 판정: 보호 경로 deny, 정상 경로 allow (Windows 네이티브 hook exit code 처리 포함 실측) |
| 지원됨 | 프로젝트 로컬 Codex 설치: `aeg install --target codex` |
| 지원됨 | Codex substrate에서 `ask`/`defer`를 `deny`로 격상: Codex에서 `ask`가 실행 차단 안전망으로 동작하지 않는 실측 결과 반영 |
| 부분 지원 / 확인 중 | Bash 동적/난독화 명령: 변수 치환, 명령 치환, 중첩 셸, `find -delete`/`xargs` 등은 정밀 판별하지 못하면 자동 허용하지 않고 `ask`/`defer`로 보냄 (Codex substrate에서는 `deny`로 격상) |
| 부분 지원 / 확인 중 | PowerShell 동적/복잡 명령: target 변수, 동적 command invocation, 미지원 cmdlet, 복잡한 pipeline은 정밀 판별을 주장하지 않고 `ask`/`defer`로 보냄 |
| 부분 지원 / 확인 중 | `apply_patch` quoted path 처리: 대칭 따옴표는 정규화해서 판정하고, 비대칭/중간 따옴표/빈 경로처럼 애매한 입력은 fail-closed deny |
| 부분 지원 / 확인 중 | macOS: 테스터 검증 진행 중 (결과 대기) |
| 지원 안 됨 (로드맵) | 파일 내용 안의 실제 secret 값 스캔: 현재는 경로와 의도 기반 판정 |
| 지원 안 됨 (로드맵) | 사용자 정의 정책: 현재 정책은 하드코딩 |
| 지원 안 됨 | Codex에서 `Bash` tool name으로 들어오는 PowerShell 문법 명령(예: `Remove-Item` 등)의 구조적 파싱 |
| 지원 안 됨 | `@` 파일 참조처럼 tool call을 거치지 않고 모델 컨텍스트로 직접 읽히는 내용 |
| 지원 안 됨 | 이미 허용된 명령이 내부에서 실행하는 하위 프로세스의 모든 행동 추적 |
| 지원 안 됨 | 글로벌 설치: `~/.claude`, `~/.codex` 설치는 지원하지 않음 |
| 지원 안 됨 | PyPI 공개 배포: 현재는 소스 설치만 지원 |
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
- 기존 `.claude/settings.json`이 있으면 병합합니다. 기존에 등록된 다른 hook과 설정은 그대로 남고, 장승(Jangseung) hook만 추가됩니다.
- 쓰기 전에 변경 내용을 diff로 보여주고 확인(`y/N`)을 받습니다. 이미 승인한 자동화 환경이라면 `--yes`로 확인을 건너뛸 수 있습니다.
- 쓰기 전에 기존 파일을 `settings.json.aegis-backup-<timestamp>`로 백업합니다.

Codex 대상은 명시적으로 설치해야 합니다.

```bash
aeg install --target codex
```

Codex 대상 설치는 프로젝트 폴더의 `.codex/config.toml`에 `[[hooks.PreToolUse]]` command hook을 추가하고, hook command에 `aeg hook-run --substrate codex`를 기록합니다. 이 명시적 substrate 값이 있을 때만 장승(Jangseung)은 내부 판정이 `ask`/`defer`인 경계 사례를 `deny`로 격상합니다. `allow`와 기존 `deny` 판정은 바꾸지 않습니다.

주의: 이 변경은 Codex에서 `ask`가 실행 차단 안전망으로 동작하지 않는 문제를 보완하기 위한 좁은 조치입니다. Codex hook trust/review 동작은 Codex가 처리하며, quoted path 우회 등 전체 Codex 지원은 아직 별도 실물 재검증이 필요합니다.

Claude Code 제거는 반대로:

```bash
aeg uninstall
```

`aeg uninstall`은 `.claude/settings.json`에서 장승(Jangseung)이 추가한 hook만 찾아서 제거합니다. 다른 hook이나 다른 설정 항목은 건드리지 않습니다. 이 역시 백업 후 확인을 받습니다.

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
```

hook 기록에 실패해도 이미 계산된 `permissionDecision`과 exit code는 바뀌지 않습니다. 대신 응답 reason code에 `hook_decision_recording_failed`가 추가됩니다. 이는 기록 장치 장애가 정상 판정을 임의로 allow/deny로 재분류하지 않도록 판정 브레인과 recorder를 분리하기 위한 선택입니다. 단, 기존 판정 자체가 fail-closed deny인 경우에는 그대로 deny를 유지합니다.

두 ledger의 hash chain은 중간 레코드의 변경·삭제를 탐지하기 위한 tamper-evident 장치입니다. 외부 anchor가 없는 로컬 파일이므로 마지막 레코드와 파일 전체를 함께 삭제하는 공격까지 증명하는 tamper-proof 저장소는 아닙니다.

## 어떻게 작동하나

장승(Jangseung)은 PreToolUse hook으로 동작합니다. AI가 파일을 쓰거나 명령을 실행하는 tool call을 하려는 순간, 실행되기 직전에 그 요청이 장승(Jangseung)으로 전달됩니다. 장승(Jangseung)은 요청을 판정해서 위험하면 막고, 정상이면 통과시키고, 애매하면 확인을 요청합니다. 단, `--target codex`로 설치된 hook은 Codex가 `ask`를 강제 차단하지 않는 것으로 확인되어 애매한 `ask`/`defer` 판정을 `deny`로 응답합니다.

판정은 결정론적입니다 — 같은 입력에는 항상 같은 결과가 나옵니다. 그리고 판정 근거가 불확실할 때는 안전한 쪽(막거나 확인 요청)으로 실패합니다(fail-closed).

## 요구사항 / 현재 상태

- **Claude Code와 Codex에서 검증됨**: Linux/WSL과 Windows 네이티브 양쪽에서 실제 Claude Code 세션과 Codex CLI 세션으로 주요 PreToolUse hook 경로가 정상 작동하는 것을 확인했습니다. Windows에서는 각 substrate의 실행 방식 차이(Claude Code hook command 실행 형태, Codex deny 응답의 종료 코드 처리, PowerShell tool 등)에 맞춰 별도로 대응했습니다. `aeg install --target claude-code`(기본값) 또는 `aeg install --target codex`로 각각 설치합니다. 두 substrate는 판정 방식이 일부 다릅니다 — Claude Code에서는 애매한 작업에 확인을 요청(ask)하지만, Codex에서는 그 확인 요청이 실행을 막는 안전망으로 동작하지 않는다는 것이 실측으로 확인되어, Codex에서는 애매한 경우 더 엄격하게 차단(deny)합니다. 다만 Codex에서 `Bash` tool name으로 전달되는 PowerShell 문법 명령은 아직 구조적으로 파싱하지 않습니다.
- **정책은 현재 하드코딩되어 있습니다.** 사용자가 위험 기준을 직접 조정하는 기능은 아직 없습니다 (로드맵 예정).
- **비밀(secret) 판정은 경로와 의도 기반입니다.** `.env` 같은 파일에 쓰는 시도 자체는 막지만, 파일 내용에서 실제 API 키/비밀번호 값을 스캔하는 기능은 아직 없습니다 (로드맵 예정).
- Python 3.10 이상이 필요합니다.

## 개발

이 프로젝트는 Claude Code와 Codex를 사용해 개발했습니다. 모든 판정 로직은 실제 Claude Code / Codex 환경에서 반복 검증했으며, README에 적은 지원 범위와 한계는 그 실측 결과를 그대로 반영합니다.

## 라이선스

이 프로젝트는 MIT 라이선스로 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.
