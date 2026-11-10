# 장승(Jangseung) 아키텍처

이 문서는 현재 코드의 구조를 설명합니다. hook 이전의 run 런타임(계약 우선 실행·검증 명령, run evidence 저장소, 개발 과정 기록 문서)은 제거되었으며, 전체 이력은 `archive/aeg-run-runtime-0.1.9` 브랜치에 보존되어 있습니다.

## 무엇을 하는 도구인가

장승은 Claude Code와 Codex의 PreToolUse hook입니다. 에이전트의 도구 호출이 실행되기 직전에 입력을 받아 `allow`, `ask`, `deny`로 답하거나, 제한된 실행 명령에 한해 Claude Code `default` 모드의 원래 승인 정책에 맡깁니다. 판정과 대상(프로젝트 상대 경로, 프로그램 이름, 세션 ID, 입력 해시)을 `.aeg/hook_ledger.jsonl`에 기록합니다. 파일 내용과 명령 인자는 기록하지 않습니다.

## 판정 흐름

1. **진입점** `jangseung/cli/entry.py`: 패키지를 불러오기 전에 보호를 시작합니다. hook 경로의 어떤 실패도 deny로 응답합니다. `hook-run`은 다른 명령의 모듈을 불러오지 않아 빠르게 시작합니다.
2. **입출력** `jangseung/cli/hook_run.py`: stdin을 UTF-8로 읽고, 고정된 프로젝트 루트와 실제 작업 폴더를 정합니다.
3. **입력 계약** `jangseung/evidence/claude_code_pretooluse_input_contract.py`: 지원 도구와 필수 필드를 확인합니다. 그 외에는 deny합니다.
4. **경로 정규화** `jangseung/evidence/hook_judgment_engine_alignment.py`: 대상 경로를 작업 폴더 기준으로 풀고, 심볼릭 링크와 표기 변형을 없앤 프로젝트 상대 경로로 바꿉니다. `~`와 드라이브 상대 경로(`C:x`)는 호스트가 따로 해석하므로 deny합니다. `apply_patch`는 판정용 사본에서 프로젝트 안 절대 경로를 같은 방식으로 바꾸며, Codex에는 패치 원문이 그대로 적용됩니다.
5. **관문 판정**: 다음 관문을 모두 계산하고 하나라도 걸리면 deny합니다.
   - 프로젝트 경계, `.aeg` 보호, 보호 경로
   - 명령의 위험도(`jangseung/evidence/shell_command_risk.py`)
   - 명령의 쓰기·삭제 대상(`jangseung/evidence/claude_code_tool_call_mapping.py`)
   - 비밀 파일 읽기, 명령 인자에 든 비밀 경로
6. **허용 판정**: 다음 경우에만 allow합니다.
   - 명령이 좁은 읽기 문법을 통과하고 대상이 안전합니다(`jangseung/evidence/shell_read_only.py`). 호스트가 알린 작업 폴더도 대상으로 보므로, 프로젝트 밖에서 실행되는 명령은 경로를 적지 않아도 deny합니다. `git`은 작업 폴더에서 위로 올라가며 `.git`을 찾을 때만 해당합니다. 그 밖의 폴더는 에이전트가 쓸 수 있으므로 git이 읽을 설정을 믿을 수 없습니다.
   - 사람이 승인한 명령이고 작업 폴더가 프로젝트 안입니다(`.aeg/policy.json`).
   - `shell_normal_work.py`의 좁은 파일 조작 문법이며 모든 대상이 프로젝트 안의 비보호 경로입니다. 파일 종류, symlink/reparse point, hard link를 따로 검사합니다. `cp`/`mv`는 일반 파일 간, `rm`은 일반 파일 하나만 허용하며 디렉터리 재귀 작업은 포함하지 않습니다.
   - 프로젝트 안 일반 파일을 다루는 `Read`, `Write`, `Edit` 계열입니다.
   - `Grep`은 입력에 비밀 파일 제외 조건을 붙여(`updatedInput`) allow합니다. 호출 쪽 `glob`이 `.gitignore`를 넘어서므로 요청만으로는 읽을 파일을 판정할 수 없습니다. 명시한 파일에는 ripgrep이 이 조건을 적용하지 않으며, 그 파일은 경로 관문이 판정합니다.
   - `git diff`, `git show`, `git log -p`도 같은 이유로 제외 경로를 붙여 allow합니다. 객체 ID는 커밋으로만 해석되게 바꿉니다.
7. **나머지**: 위에 해당하지 않으면 브레인 판정은 `defer`입니다. 기본 매핑은 Claude Code `ask`, Codex `deny`입니다. 예외적으로 `shell_normal_work.py`가 인식한 단순 실행 명령이고, 작업 폴더·명시 인자·정책·세션 표시 관문을 통과하면 wiring 계층에서 Claude Code의 정확한 `default` 모드에만 permission decision 없는 `{}`를 보냅니다. 이는 안전하다는 `allow`도, wire 값 `defer`도 아닙니다. 호스트의 기존 승인 규칙에 따라 실행될 수 있습니다. 다른 모드, 모드가 없는 입력, Codex에는 적용하지 않습니다.
8. **검토 단계 재판정** (0.2.0부터): 5단계에서 deny가 나왔고 호스트가 사람에게 승인을 받는 모드(`permission_mode`가 `default` 또는 `acceptEdits`)이면, 검토 단계 경로를 보호 대상에서 뺀 채 한 번 더 판정합니다. 두 번째 판정이 deny가 아니면 걸린 것은 빌드·의존성 파일뿐이므로 `ask`로 답합니다. 두 번째도 deny이면 첫 판정을 그대로 씁니다. 사유를 해석하지 않고 두 판정의 차이만 쓰므로, 다른 관문이 걸린 호출이 `ask`로 내려가지 않습니다.
9. **승인 보류** (0.2.0부터): 같은 세션이 비밀 파일 이름이 든 내용을 쓴 적이 있으면(`.aeg/session_marks.json`) 승인된 명령의 자동 허용과 7단계의 호스트 위임을 보류하고 `ask`로 답합니다(Codex는 deny). 표시는 판정이 끝난 뒤 `hook_run`이 남깁니다. 표시 파일을 읽지 못하면 표시가 있는 것으로 봅니다.

명령을 장승이 자동 허용하는 경로는 **읽기 문법, 좁은 파일 조작 문법, 사람의 승인 정책**입니다. 위험 명령 파서는 deny만 만들 수 있습니다. 파서가 놓쳤다고 allow가 되지 않으며, 제한된 실행 명령의 호스트 위임은 별개의 미판정 상태로 취급합니다. 파일 종류 검사는 실행 시점까지 파일이 바뀌지 않음을 보장하지 않고, 프로그램 이름은 표준 도구를 전제로 합니다.

승인된 명령의 대조(`_approvable_command`)는 따옴표로 묶인 글을 같은 길이의 채움 문자로 바꾼 뒤 셸이 해석할 문자가 남았는지 봅니다. bash와 PowerShell이 따옴표의 끝을 다르게 볼 수 있는 표기(백슬래시, 기울어진 따옴표, `--%`, 단어 중간의 따옴표, 큰따옴표 안의 `$`와 백틱)는 채우지 않고 원문 그대로 엄격하게 봅니다. Codex는 Windows에서 `Bash` 도구를 PowerShell로 실행하므로 두 셸 모두에서 안전해야 합니다.

## 경로 정책

`jangseung/classify/rules.py` 한곳에서 정합니다. 강한 순서대로 다음과 같습니다.

| 분류 | 예 | 쓰기 | 읽기 | 승인 정책으로 해제 |
| --- | --- | --- | --- | --- |
| 장승 자체 설정 | `.aeg`, `.git`, `.claude/settings*.json`, `.codex`, `.mcp.json` | deny | `.aeg`만 deny | 불가 |
| git 실행 경로 | `core.hooksPath`, `include.path`, `core.fsmonitor`, `gpg.program` 등이 가리키는 프로젝트 안 경로 | deny | allow | 불가 |
| 비밀 | `.env`, `*.pem`, `id_rsa`, `.aws/`, `.ssh/` | deny | deny | 가능 |
| 프로젝트가 추가한 보호 | `protect_paths`에 적은 경로, `config/` 아래 `secrets*` | deny | allow | `protect_paths`는 불가, 나머지는 가능 |
| 검토 | `.github/workflows`, `Dockerfile`, `pyproject.toml`, `package.json`, `Makefile`, `conftest.py` | 사람에게 승인받는 모드에서 ask, 그 밖에는 deny | allow | 가능 |

경로는 비교 전에 대소문자, 구분자, `.`, 빈 경로 조각, NTFS의 끝 점·공백·`:stream`을 정규화합니다.

## 모듈 지도

| 경로 | 역할 |
| --- | --- |
| `jangseung/cli/` | CLI 명령. 진입점(`entry`), 명령 분기와 `evidence`·`doctor` 출력(`main`), `hook_run`, `install`, `hook_doctor`, `explain`, 승인 정책 편집(`policy`), 판정 사유 문장(`reason_text`) |
| `jangseung/classify/` | 경로 정책(`rules`), 승인 정책 파일(`hook_policy`), git 설정이 가리키는 실행 경로(`git_program_paths`) |
| `jangseung/law/` | 위험도별 판정 규칙 |
| `jangseung/evidence/` | hook 판정 엔진. 입력 계약, 도구 호출 매핑, 판정 정렬(`hook_judgment_engine_alignment`), 명령 위험도와 읽기 문법, MCP 관문(`mcp_tool_gate`), `.aeg` 보호(`b1_aeg_integrity_guard`), 프로젝트 경계(`mediated_repo_boundary_write_path`), 구조화된 동작과 권한(`structured_actions`, `structured_action_capabilities`) |
| `jangseung/state/` | hook ledger(`hook_ledger`)와 잠금(`file_lock`), 세션 표시(`session_marks`), 기록 조회(`evidence_query`), 기본 진단(`doctor`), Git 도우미(`git`) |
| `.claude-plugin/`, `hooks/hooks.json` | Claude Code 플러그인 포장. hook 명령은 저장소의 `aeg` 실행 파일을 `python -I`로 실행하며 `pip` 설치가 필요 없습니다 |
| `jangseung/contracts.py` | 판정과 기록에 쓰는 공용 상수 |
| `src/cli/__main__.py` | 0.1.4 이하가 등록한 `python -m src.cli hook-run`을 진입점으로 넘기는 호환 모듈. `__init__.py`를 두지 않아 프로젝트의 `src`를 가리지 않습니다 |

## 기록 조회와 진단

판정 외의 명령은 모두 hook을 설치하고 살펴보는 용도입니다.

- `aeg install`, `aeg uninstall`: 프로젝트 로컬 설정에 hook을 등록하거나 제거하고, 기록용 `.aeg/`를 준비합니다.
- `aeg evidence list`, `show`, `verify-hooks`, `repair-hooks`: `.aeg/hook_ledger.jsonl`의 hook 기록만 다룹니다. 조회는 `.aeg`를 수정하지 않습니다.
- `aeg doctor`: Git, `.aeg/` 폴더, ignore 규칙을 확인합니다. `--hooks`를 붙이면 등록된 hook 설정과 hook 기록의 chain도 확인합니다.
- `aeg explain`: 도구 호출을 실행하거나 기록하지 않고 판정만 설명합니다.
- `aeg policy show`, `add`, `preset`: `.aeg/policy.json`을 diff 확인 후 고칩니다. hook과 같은 파서로 검사하므로 hook이 무시할 파일을 쓰지 않습니다. 에이전트의 호출은 장승 해제 명령과 같이 deny합니다.

예전 버전이 남긴 `.aeg/ledger.jsonl`, `.aeg/runs/`, `.aeg/config.json`은 읽지도 고치지도 지우지도 않습니다.

호스트 위임 기록은 `hook_decision_record_v2`에 `permission_decision: host`로 남기며 실제 호스트 실행을 증명하지 않습니다. 기존 allow/ask/deny는 v1입니다. 0.2.0은 혼합 chain을 검증하지만 0.1.9 이하에서는 v2가 포함된 chain을 검증하거나 이어 쓰지 못합니다. 자세한 기록 계약은 [evidence_track_v1.md](evidence_track_v1.md)를 참조하세요.
