# 장승 0.2.0 릴리스 노트

판정 방식, 기록 내용, 설치 방법을 바꾸고 hook과 무관한 예전 명령을 제거한 릴리스입니다. **기본 동작이 바뀝니다.** 올리기 전에 "올릴 때 확인할 것"을 읽으세요.

## 바뀐 판정

### 빌드·의존성 파일은 사람에게 묻습니다

0.1.9까지 `pyproject.toml`, `requirements*.txt`, `Dockerfile`, CI 설정 수정은 항상 deny였습니다. 의존성 하나를 추가하려 해도 사람이 직접 고치거나 `allow_paths`로 보호를 통째로 풀어야 했습니다.

- hook 입력의 `permission_mode`가 `default` 또는 `acceptEdits`이면 `ask`로 답합니다. 그 밖의 모드(`auto`, `dontAsk`, `bypassPermissions`, `plan`), 모드가 없는 입력, Codex에서는 이전처럼 deny합니다.
- 대상이 늘었습니다: `package.json`, `Makefile`, `GNUmakefile`, `conftest.py`, `.pre-commit-config.yaml`, 그리고 하위 폴더의 `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements*.txt`. 0.1.9까지 이 파일들은 묻지 않고 수정되었습니다.
- 비밀 파일, `.aeg`, `.git`, `.claude/settings*.json`, `.codex`, `.mcp.json`, `protect_paths`에 적은 경로는 어떤 모드에서도 deny입니다.
- 셸 명령으로 이 파일을 쓰거나 지우는 경우(`echo x > package.json`)도 같은 판정입니다.

### 이 저장소 전용 규칙을 뺐습니다

내장 보호 경로에 장승 자신의 소스 폴더(`jangseung/cli/` 등)가 들어 있었습니다. 다른 프로젝트에는 의미가 없어 뺐습니다. 실행 중인 장승이 프로젝트 안에 설치되어 있으면 그 폴더는 이전처럼 보호합니다.

### 제한된 실행 명령은 호스트 승인 정책에 맡깁니다

Claude Code의 정확한 `default` 모드에서는 `pytest`, `npm test`, `python src/app.py` 등 정해진 프로그램 계열의 단순 실행 명령에 장승이 매번 `ask`를 강제하지 않습니다. permission decision 없는 `{}`를 보내 호스트의 원래 승인 정책에 맡깁니다. **안전하다는 `allow`가 아니며, 기존 호스트 허용 규칙이 있으면 다시 묻지 않고 실행될 수 있습니다.**

기존 차단 관문, 프로젝트 내부 작업 폴더·명시 인자 검사, 정상 정책/세션 표시가 전제입니다. 미지원 프로그램, 내용 검색, 복잡한 셸 문법, 보호 경로 인자에는 적용하지 않습니다. 다른 모드나 모드가 없는 입력은 기존 ask, Codex는 deny입니다. 세션에 비밀 이름 작성 표시가 있으면 위임도 보류합니다. 실행 프로그램 내부의 비밀 읽기나 외부 작업까지 검사하지 않습니다.

### 일반 파일의 단순 조작을 허용합니다

프로젝트 내부 비보호 경로만 대상으로 하는 좁은 문법의 `mkdir`, `touch`, 파일 간 `cp`/`mv`, 기존 일반 파일 하나의 `rm`, 리터럴 `echo`/`Write-Output` 리다이렉트를 허용합니다. PowerShell의 `Copy-Item`/`Move-Item`/`Remove-Item`은 명시적 `-LiteralPath` 형식도 지원합니다. 재귀 작업, 디렉터리 복사·이동, 링크/junction/hard link, 변수·wildcard·명령 연결은 제외합니다. 보호/검토 경로의 deny/ask는 우선 적용합니다. 검사와 실행 사이의 파일 교체를 막는 기능은 아닙니다.

### 승인된 명령의 표기 차이

`allow_commands`는 명령에 `(`나 `#`가 하나라도 있으면 승인하지 않았습니다. `git commit -m 'fix(parser): typo'`, `pytest 2>&1`, `cd src && pytest`가 모두 걸렸습니다. 이제 실행되는 프로그램을 바꾸지 않는 세 가지 표기는 읽고 넘어갑니다: 따옴표로 묶인 글, 끝의 `2>&1`, 앞의 `cd <프로젝트 안 폴더> &&`. bash와 PowerShell이 따옴표의 끝을 다르게 볼 수 있는 표기는 이전처럼 엄격하게 봅니다. `cd` 형태는 폴더가 따옴표 없는 단순한 이름이고 승인한 명령에 파일 이름이 없을 때만 적용합니다(`cd src && pytest`는 되고 `cd sub && bash scripts/run.sh`는 안 됩니다).

### 비밀 파일 이름을 쓴 세션은 승인을 보류합니다

에이전트가 문서가 아닌 파일에 `.env`, `id_rsa`, `.aws/credentials`, `*.pem` 같은 이름이 든 내용을 쓰면 그 세션에 표시를 남깁니다. 같은 세션에서 `allow_commands` 자동 허용과 `default` 호스트 위임을 보류하고 `ask`로 답합니다(Codex는 deny). 읽기 전용 명령은 그대로 허용합니다.

이것은 "써 놓고 실행하는 경로"를 막는 기능이 아닙니다. 이름을 조각내어 만드는 코드는 표시되지 않습니다. README의 [우리가 못 막는 것](../README.md#우리가-못-막는-것)에 한계를 적었습니다.

## 새 기능

- **`aeg policy`**: `aeg policy show`, `aeg policy add --command/--path/--protect/--mcp-tool`, `aeg policy preset python|node|git`. diff를 보여 주고 확인을 받습니다. 에이전트의 호출은 deny합니다.
- **사유 문장**: 막거나 물을 때의 사유가 문장으로 시작하고, 사람이 할 수 있는 일(`aeg policy add ...`)을 적습니다. 기존 reason code는 뒤에 그대로 붙습니다.
- **기록에 대상 추가**: hook 기록에 `targets`(프로젝트 상대 경로), `commands`(프로그램 이름), `session_id`, `input_hash`가 들어갑니다. 파일 내용, 명령 인자, 명령 원문은 넣지 않습니다. `aeg evidence list`에 TOOL, WHAT 열이 생겼습니다.
- **개인 설정 파일 설치**: `aeg install --scope local`은 `.claude/settings.local.json`에 등록합니다. 공유되는 `.claude/settings.json`에 PC별 절대 경로를 적지 않아도 됩니다.
- **Claude Code 플러그인**: `/plugin install jangseung --marketplace tjrwo736/jangseung`. `pip` 설치 없이 hook이 동작합니다. PATH에 Python 3.10 이상이 필요하고, Windows에서는 Git Bash가 필요합니다.
- **셸 파서 차등 테스트**: 장승의 bash·PowerShell 낱말 분리를 실제 `bash`와 PowerShell 파서의 결과와 비교하는 테스트를 추가했습니다(고정 사례와 난수 사례 841건). 이 테스트로 찾은 차이는 없습니다.

## 고친 결함

- **다른 설치본이 등록되던 문제**: `aeg install`은 PATH의 `aeg`를 먼저 찾았습니다. 가상환경의 `aeg`로 설치해도 PATH에 있는 다른 설치본이 hook으로 등록될 수 있었고, 그 설치본이 예전 버전이면 예전 규칙이 판정했습니다. 이제 설치를 실행한 인터프리터의 `aeg`를 먼저 씁니다. 0.1.9 이하로 설치한 프로젝트는 `aeg doctor --hooks`로 등록된 경로를 확인하고, 다르면 `aeg install`을 다시 실행하세요.

## 제거

- `aeg run`, `aeg verify`, `aeg init` 명령과 run evidence 조회를 제거했습니다. no-op 실행기와 꺼진 provider만 있던 초기 런타임이며 hook 판정에 쓰이지 않았습니다.
- 개발 과정 기록 문서 95개를 `docs/`에서 뺐습니다. 전체 이력은 `archive/aeg-run-runtime-0.1.9` 브랜치에 있습니다.
- `.aeg/ledger.jsonl`, `.aeg/runs/`, `.aeg/config.json`이 남아 있어도 읽거나 지우지 않습니다. 필요 없으면 직접 지우세요.

## 올릴 때 확인할 것

1. **새로 묻거나 막는 파일**: `package.json`, `Makefile`, `conftest.py`, `.pre-commit-config.yaml`, 하위 폴더의 매니페스트. `auto`·`bypassPermissions` 모드와 Codex에서는 deny입니다. 에이전트가 계속 수정해야 하면 `aeg policy add --path <파일>`로 허용하세요.
2. **`aeg run`·`aeg verify`·`aeg init`을 쓰는 스크립트**는 동작하지 않습니다.
3. **0.1.9 이하로 내리는 경우**: 호스트 위임은 `hook_decision_record_v2`, `permission_decision: host`로 기록하며 예전 버전은 v2가 든 chain을 검증하거나 이어 쓸 수 없습니다. 일반 allow/ask/deny는 v1을 유지합니다. 0.2.0은 v1/v2 혼합 chain을 검증합니다. 기록을 보존하고 다운그레이드 시 기록 운영 계획을 먼저 세우세요. 자동 삭제/변환은 하지 않습니다. `.aeg/session_marks.json`은 예전 버전이 쓰지 않습니다.
4. hook 등록은 다시 하지 않아도 됩니다. 등록된 명령은 그대로 동작합니다.

## 확인 결과

- 자동 테스트: Windows, Python 3.14에서 전체 통과. 다른 OS와 Python 버전은 CI에서 확인합니다.
- 후속 승인 피로도 변경: 자동 테스트로 `default` 위임/다른 모드 유지, Codex deny, 보호 경로, 세션 표시, 기록 실패, 혼합 chain과 의미 검증을 확인했습니다. 실제 Git Bash·PowerShell의 단순 파일 조작 14건도 임시 프로젝트에서 대조했습니다. `aeg explain --command pytest --permission-mode default`는 `host_permission_flow`를 표시하며 기록하지 않습니다.
- 실제 세션 1: Claude Code 2.1.316 `claude -p --plugin-dir`(Windows, `default` 모드), 더미 프로젝트에서 한 번. `notes.txt` 편집은 실행, `package.json` 편집은 `ask`로 멈춤(파일 변경 없음), `.env` 읽기는 deny. 세 건 모두 기록에 대상 경로가 남았습니다.
- 실제 세션 2: 같은 버전에서 모든 `Edit`에 `ask`로 답하는 탐침 hook으로 모드마다 한 번. `default`, `acceptEdits`, `auto` 모두 편집이 실행되지 않았습니다.
- 독립 검토: 구현과 별도로 변경분을 공격적으로 검토해 결함 11건을 찾았고 릴리스 전에 고쳤습니다. 그중 2건은 `cd` 형태에서 승인된 명령이 프로젝트 밖 폴더에서 자동 허용되는 우회였습니다(따옴표 친 폴더, `cd --`와 `cd -`, 줄바꿈). 회귀 테스트는 `tests/test_review_findings_0_2_0.py`에 있습니다. 같은 모델이 한 검토이며 외부 보안 검토는 아닙니다.
- 확인하지 못한 것: 외부 보안 검토, 대화형 세션의 승인 창, `dontAsk`·`bypassPermissions` 모드, Codex 실제 세션, 마켓플레이스를 통한 플러그인 설치, macOS·Linux 실제 세션, `.claude/settings.local.json`에 설치한 hook의 실제 세션.
- 위의 실제 세션과 별도 검토는 후속 승인 피로도 두 변경 이전의 결과입니다. 후속 변경을 포함한 Claude Code 실사용 시험은 5시간 사용 한도로 도구 호출 전에 종료되어 **미확인**입니다. 이 두 변경에 대한 독립 검토도 아직 수행하지 않았습니다.
