# 장승 0.1.5 릴리스 노트

보안 수정 릴리스입니다. 0.1.4 이하를 쓰고 있다면 올리는 것을 권장합니다.

**0.1.5에는 구형 hook의 보호가 꺼지는 업그레이드 결함이 있습니다. 0.1.6으로 올리세요.**

## 업그레이드 절차

```bash
python -m pip install --upgrade jangseung
aeg install                  # Claude Code 프로젝트마다
aeg install --target codex   # Codex 프로젝트마다
aeg doctor --hooks
```

`aeg install`을 다시 실행해야 하는 이유는 다음과 같습니다.

- Python 패키지 이름이 `src`에서 `jangseung`으로 바뀌었습니다. 0.1.4 이하가 `python -m src.cli hook-run` 형태로 등록한 hook은 0.1.5에서 시작되지 않습니다. **Claude Code는 이 실패를 막지 않고 도구 호출을 통과시키므로, `aeg install`을 다시 실행할 때까지 보호가 경고 없이 꺼집니다.** 0.1.6에서 고쳤습니다. `aeg` 실행 파일로 등록된 hook은 계속 동작합니다.
- 검사 도구 목록에 `MultiEdit`, `NotebookEdit`, `Grep`, `Glob`이 추가되었습니다.
- Claude Code hook에 `"onFailure": "block"`이 추가되었습니다. Claude Code v2.1.295 이상에서 동작합니다.

`aeg install`은 장승 hook 항목만 고치고 다른 hook과 설정은 유지합니다. 쓰기 전에 diff를 보여 주고 백업을 남깁니다.

**Codex 사용자는 설치 후 Codex에서 hook을 검토해 승인해야 합니다.** Codex는 신뢰를 승인한 hook만 실행하며, 승인 전에는 아무것도 막지 않습니다. Codex CLI 0.156.0의 `codex exec`에서 승인 전 hook이 실행되지 않고 보호 파일이 수정되는 것을 확인했습니다.

`src`라는 이름으로 장승을 import하던 코드가 있다면 `jangseung`으로 바꿔야 합니다.

## 수정한 우회

- **PowerShell 자동 허용 (0.1.4의 치명 결함)**: `Get-ChildItem`처럼 읽기 명령으로 시작하면 줄바꿈, 괄호, `&` 뒤에 붙은 삭제 명령까지 allow했습니다. allow는 Claude Code의 승인 창도 생략합니다. 자동 허용은 이제 좁은 읽기 문법을 통과한 명령에만 적용합니다.
- **PowerShell 비밀 읽기**: `Get-Content .env`, 프로젝트 밖 경로 읽기가 allow였습니다. 이제 deny합니다.
- **장승 자체 해제**: `.claude/settings.json`, `.codex/config.toml`, `.mcp.json`, `.git/hooks` 수정이 allow였습니다. 이제 deny하며 승인 정책으로도 풀 수 없습니다.
- **하위 폴더 실행**: 프로세스의 현재 폴더를 프로젝트 루트로 보아, 세션이 `.github/workflows`로 이동하면 `ci.yml` 쓰기가 allow였습니다. 이제 `CLAUDE_PROJECT_DIR`, 없으면 `.aeg`나 `.git`이 있는 상위 폴더를 루트로 고정하고 상대 경로는 실제 작업 폴더 기준으로 해석합니다.
- **hook 비정상 종료**: 아주 깊게 중첩된 입력에 비정상 종료했고, 이때 Claude Code는 도구 호출을 그대로 실행합니다. 이제 프로세스 진입점에서 모든 실패를 deny로 응답합니다.
- **경로 표기 변형**: `.github//workflows/ci.yml`, `.ENV`, `.env::$DATA`, `.env.` 같은 표기가 상대 경로에서 allow였습니다. 이제 판정 전에 정규화합니다.
- **비밀 파일 범위**: 하위 폴더 `.env`, `id_rsa`, `*.pem`, `.aws/credentials`, `.npmrc`, `credentials.json`이 빠져 있었습니다. 이제 깊이와 무관하게 읽기와 쓰기를 deny합니다.
- **deny가 ask로 내려가던 명령**: `echo x>.env`, `rm .env;ls`, `sed -i`, `mv .env y`, `/bin/rm -rf`, `git -C . reset --hard`, `bash -c 'rm -rf x'`, PowerShell 별칭(`ri`, `sc`, `ac` 등)을 deny합니다. `git checkout -- .`, `npm publish`, `gh release create`, `kubectl apply`, `terraform apply`도 추가했습니다.

## 수정한 오탐과 사용성

- `src/cli/`, `src/state/` 등이 모든 프로젝트에서 보호 경로였습니다. 장승 자체 소스에만 적용되도록 바꿨습니다.
- `pyproject.toml`, `requirements.txt`, `Dockerfile` 읽기를 허용합니다. 쓰기는 계속 deny합니다. `.env.example` 같은 템플릿은 읽기와 쓰기를 허용합니다.
- `ls`, `pwd`, `git status`, `git diff`, `git log` 등 파일을 바꾸지 않는 명령을 자동 허용합니다.
- 명령 인자에 든 단어로 deny하던 오탐(`ls deploy`, `grep curl README.md`, `echo git push`, `python -m venv env`)을 없앴습니다.
- 한글 폴더 프로젝트가 Windows에서 deny되던 문제를 고쳤습니다. hook 입력을 항상 UTF-8로 읽습니다.
- `.aeg/policy.json`으로 프로젝트별 승인을 둘 수 있습니다. 내용은 README를 참고하세요.
- `src` 패키지가 사용자 프로젝트의 `src` 폴더와 충돌하던 문제를 패키지 이름 변경으로 없앴습니다.

## 기록 장치

- hook 호출마다 ledger 전체를 다시 검증하던 것을 마지막 기록만 확인하도록 바꿨습니다. 전체 검증은 `aeg evidence verify-hooks`가 합니다.
- `aeg evidence repair-hooks`를 추가했습니다. 손상된 행을 격리 파일로 옮기고 chain을 이어 갑니다.

## 내부 정리

CLI에서 쓰이지 않던 초기 단계 코드를 제거했습니다. 제품 동작은 바뀌지 않으며, 정리 전후 판정 시험 180건의 결과가 같습니다.

- CLI에서 도달하지 않는 모듈 26개와 그 전용 테스트를 제거했습니다.
- 테스트에서만 쓰이던 함수와 상수, 재공개만 되던 모듈 1개를 제거했습니다.
- 실제와 어긋난 계약 플래그(`hook_command_implemented: False` 등)와 완료 라벨(`..._NOT_INSTALLED_NOT_LIVE`)을 제거했습니다.
- `hook-run`이 다른 명령의 모듈을 불러오지 않습니다.

제거된 내부 모듈을 직접 import하던 코드가 있다면 이전 버전의 Git 이력에서 확인하세요. 공개 인터페이스는 `aeg` 명령입니다.

## 검증 범위와 남은 한계

자동 테스트와 hook CLI 실측으로 검증했습니다. Windows의 Claude Code 2.1.316 비대화형 세션에서 다음을 확인했습니다.

- PowerShell 우회 명령이 deny되고 대상 파일이 유지됨
- `Read`, `Grep`, `Glob`, `Bash`, `Write`의 실제 입력에 대한 판정과 기록
- 한글 폴더 프로젝트에서 hook 입력이 원시 UTF-8로 오며 정상 판정됨
- `cwd`와 `CLAUDE_PROJECT_DIR` 값이 프로젝트 경로와 일치함
- `"onFailure": "block"`이 시작하지 못한 hook의 도구 호출을 막음

다음은 아직 확인하지 못했습니다.

- 권한 우회 모드(`--dangerously-skip-permissions`)에서 hook의 `ask`와 `deny` 동작
- 신뢰를 승인한 뒤 Codex 실제 세션에서의 판정
- Linux, macOS 실제 세션과 앱 worktree 세션
- `MultiEdit`, `NotebookEdit`의 실제 입력 형태

`WebFetch`, `WebSearch`, MCP 도구는 검사하지 않습니다. 파일 내용 안의 비밀 값도 검사하지 않습니다.
