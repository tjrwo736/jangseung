# 장승(Jangseung) 아키텍처

이 문서는 현재 코드의 구조를 설명합니다. `docs/` 안의 `phase*`, `b1_*` 같은 문서는 개발 과정의 기록이며 현재 동작의 기준이 아닙니다. 그 문서들이 말하는 모듈 일부는 0.1.5에서 제거되었습니다.

## 무엇을 하는 도구인가

장승은 Claude Code와 Codex의 PreToolUse hook입니다. 에이전트의 도구 호출이 실행되기 직전에 입력을 받아 `allow`, `ask`, `deny` 중 하나로 답하고, 판정 메타데이터를 `.aeg/hook_ledger.jsonl`에 기록합니다.

## 판정 흐름

1. **진입점** `jangseung/cli/entry.py`: 패키지를 불러오기 전에 보호를 시작합니다. hook 경로의 어떤 실패도 deny로 응답합니다. `hook-run`은 다른 명령의 모듈을 불러오지 않아 빠르게 시작합니다.
2. **입출력** `jangseung/cli/hook_run.py`: stdin을 UTF-8로 읽고, 고정된 프로젝트 루트와 실제 작업 폴더를 정합니다.
3. **입력 계약** `jangseung/evidence/claude_code_pretooluse_input_contract.py`: 지원 도구와 필수 필드를 확인합니다. 그 외에는 deny합니다.
4. **경로 정규화** `jangseung/evidence/hook_judgment_engine_alignment.py`: 대상 경로를 작업 폴더 기준으로 풀고, 심볼릭 링크와 표기 변형을 없앤 프로젝트 상대 경로로 바꿉니다.
5. **관문 판정**: 다음 관문을 모두 계산하고 하나라도 걸리면 deny합니다.
   - 프로젝트 경계, `.aeg` 보호, 보호 경로
   - 명령의 위험도(`jangseung/evidence/shell_command_risk.py`)
   - 명령의 쓰기·삭제 대상(`jangseung/evidence/claude_code_tool_call_mapping.py`)
   - 비밀 파일 읽기, 명령 인자에 든 비밀 경로
6. **허용 판정**: 다음 경우에만 allow합니다.
   - 명령이 좁은 읽기 문법을 통과하고 대상이 안전합니다(`jangseung/evidence/shell_read_only.py`).
   - 사람이 승인한 명령입니다(`.aeg/policy.json`).
   - 프로젝트 안 일반 파일을 다루는 `Read`, `Write`, `Edit` 계열입니다.
7. **나머지**: 위에 해당하지 않으면 `defer`이며, Claude Code에서는 `ask`, Codex에서는 `deny`로 응답합니다.

핵심 원칙은 **명령을 자동 허용하는 경로가 읽기 문법과 사람의 승인 둘뿐**이라는 점입니다. 위험 명령 파서는 deny만 만들 수 있으므로, 파서가 놓친 명령은 `ask`로 갑니다.

## 경로 정책

`jangseung/classify/rules.py` 한곳에서 정합니다. 강한 순서대로 다음과 같습니다.

| 분류 | 예 | 쓰기 | 읽기 | 승인 정책으로 해제 |
| --- | --- | --- | --- | --- |
| 장승 자체 설정 | `.aeg`, `.git`, `.claude/settings*.json`, `.codex`, `.mcp.json` | deny | `.aeg`만 deny | 불가 |
| 비밀 | `.env`, `*.pem`, `id_rsa`, `.aws/`, `.ssh/` | deny | deny | 가능 |
| 보호 | `.github/workflows`, `Dockerfile`, `pyproject.toml` | deny | allow | 가능 |

경로는 비교 전에 대소문자, 구분자, `.`, 빈 경로 조각, NTFS의 끝 점·공백·`:stream`을 정규화합니다.

## 모듈 지도

| 경로 | 역할 |
| --- | --- |
| `jangseung/cli/` | CLI 명령. `hook_run`, `install`, `hook_doctor`, `explain` |
| `jangseung/classify/` | 경로 정책(`rules`), 승인 정책 파일(`hook_policy`) |
| `jangseung/law/` | 위험도별 판정 규칙 |
| `jangseung/evidence/` | hook 판정 엔진과 초기 run evidence 계약 |
| `jangseung/state/` | `.aeg/` 저장소, hook ledger(`hook_ledger`), Git 도우미 |
| `jangseung/agents/` | `aeg run`에서 쓰는 no-op 실행기 |
| `src/cli/__main__.py` | 0.1.4 이하가 등록한 `python -m src.cli hook-run`을 진입점으로 넘기는 호환 모듈. `__init__.py`를 두지 않아 프로젝트의 `src`를 가리지 않습니다 |

## `aeg run` 계열

`aeg run`, `aeg verify`, `aeg evidence`는 hook과 별개인 run 기록 기능입니다. `jangseung/evidence/verify.py`, `schema.py`, `action_decision_routing.py`, `jangseung/state/store.py`가 여기에 속합니다. 실행기는 no-op이고 provider는 꺼져 있습니다. hook 판정은 이 모듈들을 불러오지 않습니다.
