# 장승 0.3.0 릴리스 노트

승인 피로를 줄이고, 보호 범위를 넓히고, 운영 도구를 더한 릴리스입니다. 0.2.2는 따로 배포하지 않았고 이 릴리스에 들어 있습니다([0.2.2 노트](release_0.2.2.md)).

```bash
python -m pip install --upgrade jangseung
aeg install          # 세션 시작 점검을 등록하려면 다시 실행합니다
```

플러그인으로 쓰면 플러그인을 업데이트하세요. 세션 시작 점검은 플러그인에 들어 있습니다.

## 판정이 느슨해진 것

다음은 0.2.2까지 묻던 것을 묻지 않게 바꾼 것입니다. 각각 실제 Claude Code 동작을 재서 정했습니다.

### 여러 명령과 상태 명령을 허용합니다

- `;`, `&&`, `||`로 이은 줄은 각 부분이 읽기 문법에 들면 허용합니다: `ls -la; pwd`, `cat README.md && pwd`, `git status && git diff`, `cd src && ls`.
  - 각 부분은 실제로 실행될 폴더에서 판정합니다. `cd`는 줄 전체가 `&&`로만 이어질 때만 따라가고, 폴더 이름 앞뒤에 공백이 있거나 끝에 점이 있으면 따라가지 않습니다.
  - `git diff`처럼 파일 내용을 출력하는 부분은 비밀 파일을 뺀 형태로 고쳐서 실행합니다.
  - 부분 하나라도 비밀 파일을 읽으면 deny입니다.
- 상태만 출력하는 명령을 허용합니다: `date`, `true`, `false`, `sleep 1`, `whoami`, `uname -a`, `which python`, `command -v git`, `cd src`, 알려진 프로그램의 정확한 버전 확인 형태(`python --version`, `node --version`, `java -version`).
  - 버전 확인은 프로그램마다 정해진 한 형태만 받습니다. `python version`은 `version`이라는 파일을 실행하고, `npm version`은 package.json을 바꾸고, `pytest -v`는 테스트를 실행하기 때문입니다. `pytest --version`도 conftest.py를 읽어 실행하므로 pytest는 빠졌습니다. 프로젝트 파일이 가리키는 다른 프로그램으로 넘기는 실행기(yarn의 `yarnPath`, cargo·rustc의 `rust-toolchain.toml`, dotnet의 `global.json`, go의 `toolchain`, npm·pnpm의 `packageManager`, poetry·pdm·composer의 플러그인)도 빠졌습니다.
  - 버전·상태 명령은 PATH에서 찾은 프로그램이 프로젝트 밖에 있을 때만 허용합니다. 프로젝트 안의 `.venv`가 PATH 앞에 있으면 에이전트가 그 안의 `python`을 바꿔 놓았을 수 있으므로 묻습니다.
- 이 허용은 Codex와 모든 Claude Code 모드에 적용됩니다.
- 근거: 장승이 답하지 않을 때 Claude Code가 이런 줄을 스스로 실행하는 것을 쟀습니다(`default`, `acceptEdits`). 장승은 그중 비밀 파일을 읽는 줄만 골라 막습니다.

### 실행 명령을 이은 줄도 호스트에 맡깁니다

`git add -A && git commit -m wip`, `npm install && npm test`처럼 호스트에 맡기는 실행 명령과 읽기 명령만 이은 줄은 호스트의 승인 흐름에 맡깁니다. 실제 세션에서 호스트가 "여러 작업이 들어 있다"며 승인을 요구했습니다. `cd`나 git 내용 출력이 들어 있으면 맡기지 않습니다. 호스트는 그런 읽기를 스스로 실행하기 때문입니다.

### `acceptEdits` 모드에서도 호스트에 맡깁니다

0.2.x는 `default` 모드에서만 실행 명령을 호스트에 맡겼습니다. Claude Code 2.1.316(Windows)에서 `acceptEdits` 모드로 실행 명령 33종(`git add`, `git commit`, `pytest`, `npm test`, `cargo build`, `python tool.py` 등)을 한 번씩 실행해 보니 모두 승인을 요구했습니다. 그래서 `acceptEdits`도 위임합니다.

`acceptEdits`는 `rm`, `mv`, `cp`, `sed -i`, `echo >` 같은 파일 명령을 묻지 않고 실행하는 것도 확인했습니다. 파일 명령은 어느 모드에서도 호스트에 맡기지 않습니다.

## 새 기능

### `aeg allow-once` — 한 번만 허용

```bash
aeg allow-once "docker compose up -d"
```

사람이 적은 글자와 같은 명령을 한 번 허용합니다. 10분(최대 60분) 뒤나 한 번 쓰이면 사라집니다. Codex는 hook이 사람에게 물을 수 없어서 장승이 증명하지 못한 명령을 deny하는데, 이때 접두사 전체를 열지 않고 한 번만 허용할 수 있습니다.

- `allow_commands`에 올린 것과 같은 것만 풉니다. 비밀 파일, 장승 설정, 프로젝트 밖 대상은 그대로 막습니다. 비밀 파일 이름이 든 내용을 쓴 세션에서는 다시 묻습니다.
- 에이전트는 실행할 수 없습니다. 파일에는 명령의 해시만 저장합니다.
- 프로젝트 폴더 자체에서 실행될 때만 씁니다. 같은 `pytest`라도 하위 폴더에서는 다른 conftest를 실행하기 때문입니다. 셸 도구도 구분합니다(`--tool PowerShell`, 기본 `Bash`, Codex는 늘 `Bash`).
- 허용은 답을 보내기 전에 소모합니다. 소모하지 못하면 허용하지 않습니다.
- 막힌 명령의 안내 문장에 이 방법이 추가되었습니다.

### 세션 시작 점검

`aeg install`과 플러그인이 `SessionStart` hook을 함께 등록합니다. 세션을 시작할 때 다음이면 한 줄로 알립니다.

- 장승의 PreToolUse hook이 등록되어 있지 않음
- 등록된 프로그램이 없어짐(가상 환경을 지운 경우 등)
- hook이 시작하지 못할 때 호출을 막도록 설정되어 있지 않음
- 정책 파일을 읽지 못함
- `.aeg`에 기록할 수 없음

문제가 없으면 아무것도 출력하지 않고, 세션을 막지 않습니다. hook 설정 전체가 지워지면 점검도 함께 사라지므로 그 경우는 알리지 못합니다. Codex에는 등록하지 않습니다.

### 팀 공유 보호 정책 `.jangseung/policy.json`

Git에 커밋하는 파일로, `protect_paths`만 담을 수 있습니다. 다른 항목이 있거나 손상되면 어떤 경로를 보호하려 했는지 알 수 없으므로 모든 경로를 보호합니다. 사람이 고칠 때까지 에이전트의 파일 수정이 모두 막히고, 호스트 위임과 파일 조작 자동 허용도 꺼집니다. 에이전트는 이 폴더에 쓸 수 없습니다.

```bash
aeg policy add --shared --protect infra/
```

### `aeg policy suggest`

기록을 읽어 자주 물어본 명령을 `aeg policy add --command` 줄로 보여 줍니다. 쓰지는 않습니다. 기록에는 프로그램 이름만 있어서 `terraform plan`도 `terraform`으로 보입니다. 그 접두사를 승인하면 `terraform destroy`까지 풀리므로, 위험한 하위 명령이 있는 프로그램(`terraform`, `docker`, `git`, `aws`, `npm` 등)과 인터프리터·셸·네트워크 도구는 제안하지 않습니다.

### `aeg evidence archive-hooks`

손상되지 않은 ledger를 `.aeg/archive/`로 옮기고 새 chain을 시작합니다. 새 chain의 첫 기록에 옮긴 파일의 기록 수, 마지막 해시, SHA-256을 적어 두 파일을 잇습니다. 손상된 ledger는 먼저 `repair-hooks`로 고쳐야 합니다. 사람이 실행하는 명령입니다.

### 프리셋 추가

`aeg policy preset rust | go | jvm | dotnet`.

## 보호 범위가 넓어진 것

검토 등급(`default`·`acceptEdits`에서 묻고, 다른 모드와 Codex에서 deny)에 다음을 더했습니다.

- 작업 실행기와 테스트 설정: `justfile`, `Taskfile.yml`, `tox.ini`, `noxfile.py`, `pytest.ini`, `lefthook.yml`
- 다른 언어의 빌드·의존성 파일: `Cargo.toml`, `build.rs`, `go.mod`, `go.work`, `build.gradle(.kts)`, `settings.gradle(.kts)`, `pom.xml`, `Gemfile`, `Rakefile`, `composer.json`, `CMakeLists.txt`, `*.cmake`, `meson.build`, `build.zig`, `deno.json`, `bunfig.toml`, `.yarnrc.yml`
- 실행되는 JavaScript 설정: `*.config.js/cjs/mjs/ts/cts/mts`, `.eslintrc.js`, `.babelrc.js`, `.prettierrc.js`, `gulpfile.*`, `gruntfile.*`
- 폴더를 열 때 명령을 실행하는 설정: `.vscode/tasks.json`, `.vscode/settings.json`, `.vscode/launch.json`, `.devcontainer/`
- 그 밖에: `compose.yaml`, `docker-compose.yaml`, `sitecustomize.py`, `usercustomize.py`, `netlify.toml`, `vercel.json`
- 에이전트 지시 파일: `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `.clinerules`, `.claude/commands/`, `.claude/agents/`, `.claude/skills/`, `.cursor/rules/`, `.github/copilot-instructions.md`, `.github/instructions/`, `.gemini/`. 이 파일들은 별도 문장으로 안내합니다.

`.claude/commands/` 등은 0.1.5부터 에이전트가 쓰는 폴더로 열어 두었던 것입니다. 계속 자동으로 쓰게 하려면 `aeg policy add --path .claude/commands`로 엽니다.

## 승인 피로 측정

같은 명령 목록을 0.2.1과 0.3.0에 돌려 비교했습니다(hook 판정, Claude Code `default` 모드).

| 묶음 | 0.2.1 | 0.3.0 |
|---|---|---|
| 일상 명령 50종(1차 목록), Claude Code | allow 15, 위임 23, ask 9, deny 3 | allow 18, 위임 24, ask 5, deny 3 |
| 같은 목록, Codex | allow 15, deny 35 | allow 18, deny 32 |
| 일상 명령 50종(2차 목록), Claude Code | ask 21 | ask 9 |
| 같은 목록, Codex | deny 44 | deny 33 |
| 2차 목록 앞 30종, `acceptEdits` | ask 30 | ask 5, 위임 22, allow 3 |
| 직접 공격 15종, 난독화 64종, 파괴 명령 48종 | `allow`·위임 0 | `allow`·위임 0 |

## 확인 결과

- 자동 테스트: Windows, Python 3.14에서 전체 통과(1839 passed, 20 skipped). 새 테스트는 `tests/test_new_features_0_3_0.py`입니다.
- 실제 세션(Claude Code 2.1.316 `claude -p`, Windows, 플러그인으로 로드, 각 1회, 독립 검토 수정 전 코드):
  - `ls -la; pwd`, `git status && git diff`, `date`, `python --version`: 실행됨.
  - `cat .env && pwd`: 막힘, 값 노출 없음.
  - `git add -A && git commit -m wip`(`default`), `git add -A`(`acceptEdits`): 호스트가 승인을 요구해 실행되지 않음.
  - `CLAUDE.md` 수정(`default`, `acceptEdits`): 묻고, 승인할 사람이 없어 바뀌지 않음.
  - 정책 파일이 손상된 프로젝트: 세션 시작 점검의 안내가 나옴.
- 독립 검토: 같은 모델의 별도 에이전트가 변경분을 공격적으로 검토했습니다. 찾은 것과 조치:
  - 높음: 버전 확인 문법이 `프로그램 + 낱말 하나`를 받아 `pytest -v`(테스트 실행), `python version`(같은 이름 파일 실행), `npm version`(package.json 변경)을 모든 모드와 Codex에서 묻지 않고 허용했습니다. 에이전트가 `version` 파일을 쓰고 `python version`을 실행하는 연쇄가 사람 없이 이어졌습니다. 프로그램마다 정확한 한 형태만 받도록 고쳤습니다.
  - 중간: 팀 공유 정책 파일이 손상되면 그 안의 보호가 Write·Edit에서 사라졌습니다. 모든 경로를 보호하도록 고쳤습니다.
  - 낮음: 앞뒤 공백·끝 점이 있는 `cd` 대상을 다른 폴더로 판정, 한 번 허용이 하위 폴더와 다른 셸 도구에서도 쓰임. 둘 다 고쳤습니다.
  - 낮음, 그대로 둠: `& aeg allow-once x`(PowerShell), `uvx --from jangseung aeg allow-once x`는 deny가 아니라 ask(Codex는 deny)입니다. 따옴표 안에 `;`가 있는 줄(`ls 'a;b'; pwd`)은 묻습니다.
  - 이상 없음으로 확인된 것: 분할기의 연산자 변형, `cd` 탈출(`.git`, `.aeg`, `..`, 정션), git 재작성의 제외 조건, `date -f .env`(deny), 한 번 허용의 1회 소모와 규칙 유지, `.jangseung/` 쓰기 차단, 새 경로의 내부 오류 0건.
  - 수정분 재검토: 네 가지 수정이 의도대로 동작했고 0.2.2보다 약해진 판정은 없었습니다. 남은 경로 하나를 찾았습니다. 버전 확인 목록에 프로젝트 파일이 가리키는 프로그램으로 넘기는 실행기(yarn, cargo, rustc, dotnet, poetry, pdm, composer)가 있었고, 그 설정 파일은 묻지 않고 쓸 수 있었습니다. 실제 도구가 없어 실행되는지는 확인하지 못했지만 목록에서 뺐습니다. 이 마지막 조정은 다시 검토하지 않았습니다.
  - 낮음, 그대로 둠: 팀 공유 정책 파일이 손상된 동안에는 `cd src && ls`도 Codex에서 deny됩니다.
- 확인하지 못한 것: Codex 실제 세션(`aeg allow-once` 포함), 대화형 세션의 승인 창, macOS·Linux 실제 세션, `dontAsk`·`bypassPermissions` 모드. 외부 보안 검토는 없습니다.

- hook 호출 시간: 0.2.1과 같은 수준입니다(같은 위치에서 잰 중앙값 차이가 측정 오차 안).

남은 위험은 [잔여 위험 등록부](residual_risk.md)의 RR-4, RR-13~RR-15에 적었습니다.
