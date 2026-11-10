# 장승 0.2.1 릴리스 노트

0.2.0에서 생긴 비밀 노출 결함을 고친 보안 수정 릴리스입니다. 0.2.0을 쓰고 있다면 올리세요.

```bash
python -m pip install --upgrade jangseung
```

hook 등록은 다시 하지 않아도 됩니다. 플러그인으로 쓰면 플러그인을 업데이트하세요.

## 고친 결함: stash에 든 비밀 파일 변경이 승인 없이 출력됨

- **영향 버전:** 0.2.0. **대상:** Claude Code의 `default` 모드.
- **내용:** 0.2.0은 일부 실행 명령을 Claude Code의 원래 승인 정책에 맡기면서 `git stash` 전체를 맡겼습니다. Claude Code는 `git stash show`, `git stash show -p`, `git stash show --patch`를 읽기 명령으로 보고 승인 없이 실행합니다. 그래서 stash에 추적되는 비밀 파일(`.env` 등)의 변경이 들어 있으면 그 값이 에이전트에게 출력되었습니다. 0.1.9는 같은 명령에 `ask`로 답했습니다.
- **확인:** Claude Code 2.1.316 `claude -p`(Windows), 더미 `.env`를 stash에 넣은 임시 프로젝트에서 값이 출력되는 것을 확인했습니다.
- **수정:** 내용을 출력하는 git 형태는 호스트에 맡기지 않고 장승이 판정합니다. `git stash`는 상태를 바꾸는 형태(인자 없음, `push`, `pop`, `apply`, `save`, `branch`)만 맡깁니다. 짧은 옵션에 `p`, `v`, `i`가 들어 있거나(`-pq`처럼 묶은 것 포함), 긴 옵션이 `patch`, `verbose`, `dry-run`, `show-current-patch`, `interactive`, `long`, `short`, `porcelain`의 앞부분이면(`--patc` 같은 축약 포함) 맡기지 않습니다. git은 묶은 짧은 옵션과 축약한 긴 옵션을 받아들이고, `git commit --long`은 변경 내용을 출력하는 dry run이기 때문입니다. 이 명령들은 0.1.9와 같이 `ask`(Codex는 deny)로 답합니다. `git stash list`(이름만 출력)는 0.1.9부터 허용하던 읽기 명령이며 그대로입니다.

## 고친 결함: 세션 표시가 남지 않는 경로

비밀 파일 이름이 든 내용을 쓴 세션은 승인된 명령을 자동 허용하지 않습니다(0.2.0의 세션 표시). 다음 경로에서는 표시가 남지 않았습니다.

- **이름 바꾸기:** 0.2.0은 `cp`, `mv`를 자동 허용하면서 옮겨진 파일의 내용을 보지 않았습니다. 코드를 `.md`로 써서 표시를 피한 뒤 `mv plan.md run.py`로 바꿀 수 있었습니다. 이제 원본 내용을 같은 기준으로 봅니다.
- **실행되는 텍스트 파일:** `.txt`를 문서로 보아 검사하지 않았습니다. pytest는 `test*.txt`를 doctest로 실행하고 CMake는 `CMakeLists.txt`를 읽습니다. 이제 검사하지 않는 것은 `.md`, `.markdown`, `.rst`, `.adoc`, `README`, `CHANGELOG`, `LICENSE`, `.gitignore`뿐입니다. 프로젝트가 이런 파일을 실행하도록 설정했다면 그 파일에도 표시가 남지 않습니다.
- **긴 내용:** 앞 400,000자만 읽어, 그 뒤에 이름을 두면 표시를 피했습니다. 이제 그보다 긴 내용은 읽지 않고 표시합니다. `Write` 도구에도 적용됩니다.
- **승인된 복사:** `cp -f x.md conftest.py`, `cat x.md > conftest.py`처럼 장승이 묻는 복사는 사람이 승인해도 표시하지 않았습니다. 승인 창에는 파일 이름만 보입니다. 이제 명령에 적힌 프로젝트 파일(최대 8개)의 내용을 보고 표시합니다.
- **UTF-16 파일:** UTF-8로만 읽었습니다. PowerShell은 UTF-16 스크립트를 실행합니다. 이제 NUL 바이트가 있는 파일은 UTF-16으로도 읽습니다.

이름을 조각내는 코드가 표시를 피하는 한계는 그대로입니다.

## 확인 결과

- 자동 테스트: Windows, Python 3.14에서 전체 통과(1190 passed, 17 skipped). 회귀 테스트는 `tests/test_approval_fatigue_0_2_0.py` 끝부분에 있습니다.
- 실제 세션: Claude Code 2.1.316 `claude -p`(Windows, `default` 모드, 허용 규칙 없음)로 장승이 호스트에 맡기는 명령 40종(git, gh, npm, pip, go, cargo, make, ruff, mypy, pytest, uv, poetry, yarn, dotnet, gradle, mvn, python 스크립트)을 한 번씩 실행했습니다. 모두 호스트가 승인을 요구했습니다. 수정본에서 `git stash show`, `git stash show -p`, `git stash show --patch`, `git add -pu`, `git commit --long -vv`는 장승이 `ask`로 멈췄습니다. 의도한 위임은 그대로 동작했습니다: `python tool.py`는 호스트 허용 규칙이 있으면 실행되고 없으면 호스트가 물었으며, `mkdir -p src/utils`는 자동 허용되었습니다.
- 독립 검토: 같은 모델의 별도 에이전트가 수정본을 공격적으로 검토해 git 옵션 표기 우회(묶은 짧은 옵션, 축약 긴 옵션)와 세션 표시 누락 4건을 찾았고, 위와 같이 고쳤습니다. 이 2차 수정은 다시 검토하지 않았습니다.
- 남은 위험: 호스트에 맡기는 명령도 사용자가 넓은 허용 규칙(`Bash(git commit:*)`, `Bash(uv run:*)`, `Bash(python -m:*)` 등)을 두면 묻지 않고 실행됩니다. 그런 규칙 아래에서는 `python -m dotenv list`, `uv run printenv`처럼 비밀을 출력하는 명령도 실행될 수 있습니다. 장승은 사용자의 호스트 규칙을 덮어쓰지 않습니다.
- 확인하지 못한 것: 대화형 세션, macOS·Linux와 Codex 실제 세션, 외부 보안 검토. 호스트가 스스로 허용하는 명령 목록은 호스트 버전마다 바뀔 수 있어, 새 호스트 버전에서 다시 확인해야 합니다.
