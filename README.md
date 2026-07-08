# Aegis — AI 코딩 에이전트를 위한 방패

Claude Code에게 코드를 맡기되, 위험한 것이 실행되기 전에 막습니다.

[![asciicast](https://asciinema.org/a/6B2AARAZCOKB9snJ.svg)](https://asciinema.org/a/6B2AARAZCOKB9snJ)

실제 Claude Code 세션에서 Aegis가 위험한 작업을 막고 정상 작업은 통과시키는 데모

## 핵심 3가지

- **위험한 것만 막습니다**: `.env` 유출, 배포 설정 변경, `rm -rf` 같은 파괴 명령을 실행 전에 멈춥니다. 정상 작업은 방해하지 않습니다.
- **조작할 수 없는 기록**: AI가 무엇을 하려 했는지, 무엇이 막혔는지 남깁니다.
- **프롬프트 인젝션 방어**: 조작된 지시로 위험한 행동을 하려 해도 tool call 단계에서 걸러냅니다.

## Claude Code도 위험하면 물어보는데?

맞아요. 근데 기본 승인은 세 가지가 아쉽습니다.

- 매번 다 물어봅니다. 그래서 결국 `--dangerously-skip-permissions`로 꺼버리게 되죠. 그러면 안전장치가 통째로 사라집니다.
- AI가 뭘 했는지 조작할 수 없는 기록이 안 남습니다. "어제 얘가 뭘 건드렸지?"를 나중에 추적하기 어렵습니다.
- 규칙이 흐트러지면 그냥 통과시킵니다(fail-open). 안전 도구인데 문제가 생기면 위험한 쪽으로 실패합니다.

Aegis는 반대로 만들었습니다. 위험한 것만 골라 멈추고(정상 작업은 방해하지 않습니다), 모든 판정을 조작 불가능한 기록으로 남기고, 문제가 생기면 안전한 쪽으로 멈춥니다(fail-closed).

## 무엇을 막나 (그리고 안 막나)

방패는 앞을 막지, 지나가는 사람까지 막지 않습니다. Aegis는 명확한 기준으로 위험한 것만 막습니다.

막습니다 (사용자 승인 없이는 실행 안 됨):

- 비밀 노출 위험: `.env`, 비밀키, 배포 설정 파일 수정
- 공급망/빌드 위험: `.github/workflows`, `Dockerfile`, 배포 스크립트 수정
- 되돌릴 수 없는 파괴: `rm -rf`, `git reset --hard`, `git clean -fd`
- 감시 기록 조작: `.aeg` 디렉토리 쓰기
- 범위 밖 접근: 프로젝트 폴더 바깥 경로 (`/etc`, `~/.ssh` 등)

이 판정은 파일을 직접 쓰는 경우(Write/Edit)뿐 아니라, Bash 명령으로 우회하려는 경우(`echo > .env` 같은)도 동일하게 적용됩니다.

막지 않습니다 (그냥 통과):

- 코드 읽기, 일반 파일 편집, README 수정
- 위험하지 않은 정상 작업은 방해하지 않습니다.

판단이 애매하면 (물어봅니다):

- 분류되지 않은 명령, 확실하지 않은 작업은 그냥 통과시키지 않고 확인을 요청합니다.

## 우리가 못 막는 것

Aegis는 "완벽하게 안전하다"고 말하지 않습니다. 지키는 선을 정확히 말합니다.

Aegis는 AI가 파일을 쓰거나 명령을 실행하는 등 도구를 사용하려는 순간에 끼어들어 판단합니다. 그래서 도구를 거치지 않는 것들 — AI가 참조로 직접 읽어 들이는 파일 내용, 이미 허용된 명령이 내부에서 실행하는 다른 프로그램 — 은 이 선 바깥에 있습니다.

또한 변수 치환이나 중첩 셸처럼 복잡하게 감춰진 명령은 대상을 정밀하게 판별하지 못해, 이 경우 자동 통과가 아니라 확인을 요청합니다.

다르게 말하면, Aegis는 문 앞을 지키는 경비이지 집 안 모든 방을 감시하는 CCTV가 아닙니다.

이 한계를 감추지 않는 것이 Aegis가 신뢰를 얻는 방식입니다.

## 설치

현재 PyPI에 공개 배포되어 있지 않습니다. 소스에서 설치합니다 (로컬 클론).

```bash
git clone https://github.com/tjrwo736/aegis.git
cd aegis
python -m pip install -e .
```

설치가 끝나면 `aeg` 명령을 사용할 수 있습니다. 이제 hook을 걸고 싶은 프로젝트로 이동해서 등록합니다.

```bash
cd /path/to/your-project
aeg install
```

기본값은 Claude Code 대상입니다. 명시적으로 쓰면 다음과 같습니다.

```bash
aeg install --target claude-code
```

Claude Code 대상 `aeg install`은 다음을 확인하고 진행합니다.

- 프로젝트 폴더의 `.claude/settings.json`에 Aegis PreToolUse hook을 등록합니다. **project-local만 지원합니다** — 글로벌(`~/.claude`) 설치는 이 버전에서 지원하지 않습니다.
- 기존 `.claude/settings.json`이 있으면 병합합니다. 기존에 등록된 다른 hook과 설정은 그대로 남고, Aegis hook만 추가됩니다.
- 쓰기 전에 변경 내용을 diff로 보여주고 확인(`y/N`)을 받습니다. 이미 승인한 자동화 환경이라면 `--yes`로 확인을 건너뛸 수 있습니다.
- 쓰기 전에 기존 파일을 `settings.json.aegis-backup-<timestamp>`로 백업합니다.

Codex 대상은 명시적으로 설치해야 합니다.

```bash
aeg install --target codex
```

Codex 대상 설치는 프로젝트 폴더의 `.codex/config.toml`에 `[[hooks.PreToolUse]]` command hook을 추가하고, hook command에 `aeg hook-run --substrate codex`를 기록합니다. 이 명시적 substrate 값이 있을 때만 Aegis는 내부 판정이 `ask`/`defer`인 경계 사례를 `deny`로 격상합니다. `allow`와 기존 `deny` 판정은 바꾸지 않습니다.

주의: 이 변경은 Codex에서 `ask`가 실행 차단 안전망으로 동작하지 않는 문제를 보완하기 위한 좁은 조치입니다. Codex hook trust/review 동작은 Codex가 처리하며, quoted path 우회 등 전체 Codex 지원은 아직 별도 실물 재검증이 필요합니다.

Claude Code 제거는 반대로:

```bash
aeg uninstall
```

`aeg uninstall`은 `.claude/settings.json`에서 Aegis가 추가한 hook만 찾아서 제거합니다. 다른 hook이나 다른 설정 항목은 건드리지 않습니다. 이 역시 백업 후 확인을 받습니다.

## 어떻게 작동하나

Aegis는 PreToolUse hook으로 동작합니다. AI가 파일을 쓰거나 명령을 실행하는 tool call을 하려는 순간, 실행되기 직전에 그 요청이 Aegis로 전달됩니다. Aegis는 요청을 판정해서 위험하면 막고, 정상이면 통과시키고, 애매하면 확인을 요청합니다. 단, `--target codex`로 설치된 hook은 Codex가 `ask`를 강제 차단하지 않는 것으로 확인되어 애매한 `ask`/`defer` 판정을 `deny`로 응답합니다.

판정은 결정론적입니다 — 같은 입력에는 항상 같은 결과가 나옵니다. 그리고 판정 근거가 불확실할 때는 안전한 쪽(막거나 확인 요청)으로 실패합니다(fail-closed).

## 요구사항 / 현재 상태

- **Claude Code와 Codex에서 검증됨**: 실제 Claude Code 세션과 Codex CLI 세션 양쪽에서 PreToolUse hook으로 정상 작동을 확인했습니다. `aeg install --target claude-code`(기본값) 또는 `aeg install --target codex`로 각각 설치합니다. 두 substrate는 판정 방식이 일부 다릅니다 — Claude Code에서는 애매한 작업에 확인을 요청(ask)하지만, Codex에서는 그 확인 요청이 실행을 막는 안전망으로 동작하지 않는다는 것이 실측으로 확인되어, Codex에서는 애매한 경우 더 엄격하게 차단(deny)합니다.
- **정책은 현재 하드코딩되어 있습니다.** 사용자가 위험 기준을 직접 조정하는 기능은 아직 없습니다 (로드맵 예정).
- **비밀(secret) 판정은 경로와 의도 기반입니다.** `.env` 같은 파일에 쓰는 시도 자체는 막지만, 파일 내용에서 실제 API 키/비밀번호 값을 스캔하는 기능은 아직 없습니다 (로드맵 예정).
- Python 3.10 이상이 필요합니다.

## 라이선스

이 프로젝트는 MIT 라이선스로 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.
