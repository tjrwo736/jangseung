# 장승 0.1.6 릴리스 노트

0.1.5의 업그레이드 결함을 고친 릴리스입니다. 0.1.5를 쓰고 있다면 바로 올리세요. 판정 규칙은 0.1.5와 같습니다.

**0.1.6에는 검색과 셸 읽기 명령으로 비밀 값이 출력되는 결함이 남아 있습니다. 최신 버전으로 올리세요.** [0.1.7](release_0.1.7.md)과 [0.1.8](release_0.1.8.md) 릴리스 노트를 참고하세요.

## 고친 결함

0.1.4 이하는 `aeg`가 PATH에 없으면 hook을 `python -m src.cli hook-run` 형태로 등록합니다. 0.1.5에서 패키지 이름을 바꾸면서 이 명령은 시작되지 않게 되었습니다.

Claude Code는 이렇게 실패한 hook을 막지 않고 도구 호출을 통과시킵니다. 그래서 0.1.5로 `pip install --upgrade`만 하고 `aeg install`을 다시 실행하지 않으면, 0.1.4가 막던 쓰기까지 통과했습니다. Claude Code 문서에 따르면 `hook error` 알림만 표시됩니다.

0.1.6은 이 명령을 판정 코드로 넘기는 작은 호환 모듈 `src/cli/__main__.py`를 넣었습니다. 올리기만 해도 판정이 돌아옵니다.

실제 Claude Code 2.1.316 세션(Windows)에서 옛 명령으로 등록한 프로젝트에 `.env.production` 쓰기를 요청한 결과입니다.

| 상태 | 결과 |
| --- | --- |
| 0.1.4 | 차단 |
| 0.1.5, `aeg install` 전 | **통과, 파일 생성됨** |
| 0.1.6, `aeg install` 전 | 차단 |
| 0.1.6, `aeg install` 후 | 차단 |

## 영향 범위

- **해당:** hook이 `python -m src.cli hook-run`으로 등록된 프로젝트. `aeg doctor --hooks`의 `executable` 항목이 FAIL로 나옵니다.
- **해당 없음:** `aeg` 실행 파일로 등록된 hook. 0.1.5에서도 계속 판정했습니다.
- **미확인:** Codex가 시작에 실패한 hook을 막는지 통과시키는지. 옛 명령은 Codex 형식(`--substrate codex`)도 0.1.5에서 시작되지 않습니다.

## 업그레이드 절차

```bash
python -m pip install --upgrade jangseung
aeg install                  # Claude Code 프로젝트마다
aeg install --target codex   # Codex 프로젝트마다
aeg doctor --hooks
```

호환 모듈은 보호가 끊기지 않게 하는 임시 장치입니다. `aeg install`을 다시 실행해야 하는 이유는 다음과 같습니다.

- 옛 hook의 검사 도구 목록에는 `MultiEdit`, `NotebookEdit`, `Grep`, `Glob`이 없습니다.
- 옛 hook에는 시작에 실패할 때 차단하는 `"onFailure": "block"` 설정이 없습니다.
- 옛 명령은 작업 폴더의 Python 모듈을 먼저 찾습니다. 프로젝트 파일이 호환 모듈이나 판정 코드를 가릴 수 있습니다.

**Codex 사용자:** `aeg install --target codex`로 hook 명령이 바뀌면, Codex는 승인이 풀린 것으로 보고 다시 승인할 때까지 그 hook을 건너뜁니다. 설치 후 Codex의 `/hooks`에서 승인하세요.

## 남는 제한

옛 명령은 작업 폴더의 모듈을 먼저 찾기 때문에, 다음 프로젝트에서는 호환 모듈이 실행되지 않습니다. 장승이 판정하지 않거나, 프로젝트 파일이 장승 대신 판정합니다.

| 프로젝트에 있는 파일 | 0.1.6에서 옛 명령의 동작 | 0.1.4에서 옛 명령의 동작 |
| --- | --- | --- |
| `src/__init__.py` 또는 `src.py` | 시작하지 못함 | 시작하지 못함 |
| `src/__init__.py` 없이 `src/cli/__init__.py` | 시작하지 못함 | 판정 |
| `src/cli.py` 또는 `src/cli/__main__.py` | **그 파일이 hook 대신 실행됨** | `src/__init__.py`가 있으면 같음, 없으면 판정 |

**에이전트가 이 파일을 직접 만들 수 있습니다.** 실제 세션에서 에이전트가 `src/cli.py`를 쓰자 그 파일의 판정으로 `.env.production`이 승인 없이 생성되었고, `src/__init__.py`를 쓰자 `.env` 값이 출력되었습니다. `aeg install` 후에는 둘 다 막혔습니다. 패키지 코드로는 막을 수 없으므로 `aeg install`을 다시 실행해야 합니다.

## 그 밖의 변경

- `python -m src.cli`는 `hook-run`만 받습니다. 다른 명령은 `aeg`를 쓰세요.
- 프로젝트에 `src`가 없을 때 `import src`가 오류 없이 빈 namespace로 잡힙니다. 프로젝트의 `src`를 가리지는 않습니다.
- 호환 모듈은 사용자가 옮겨 갈 시간을 둔 뒤 제거합니다.
