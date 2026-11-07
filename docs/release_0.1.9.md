# 장승 0.1.9 릴리스 노트

MCP 보호를 선택해서 켤 수 있게 한 릴리스입니다. 기본 동작은 바뀌지 않습니다.

## 새 기능: MCP 보호 (선택)

0.1.8까지 장승은 MCP 도구와 MCP 리소스 읽기를 검사하지 않았습니다. 파일을 읽거나 코드를 실행하는 MCP 도구는 장승의 판정 없이 `.env` 같은 파일 내용을 에이전트에게 넘길 수 있었습니다. 이제 필요한 프로젝트에서 켤 수 있습니다.

```bash
aeg install --mcp
aeg install --target codex --mcp
```

- **별도 항목:** 기존 hook과 별도로 MCP용 hook 항목을 하나 더 등록합니다. 기존 항목은 바꾸지 않습니다. Codex는 항목마다 승인하므로, 기존 항목을 고치면 장승 전체가 다시 승인받을 때까지 꺼집니다.
- **판정:** MCP 도구 호출과 MCP 리소스 읽기(Claude Code `ReadMcpResourceTool`, Codex `read_mcp_resource`)는 Claude Code에서 매번 승인을 묻고, Codex에서는 막힙니다.
- **허용 목록:** `.aeg/policy.json`의 `allow_mcp_tools`에 정확한 도구 이름(`mcp__서버__도구`)을 적으면 승인 없이 통과합니다. 패턴은 쓸 수 없고, 리소스 읽기는 목록에 넣을 수 없습니다.
- **인자는 보지 않습니다:** 장승은 도구 이름만 봅니다. 목록에 넣은 도구가 파일을 읽거나 코드를 실행하면 `.env`도 읽을 수 있습니다.
- **Codex 승인:** Codex는 MCP 항목을 새 hook으로 봅니다. `/hooks`에서 따로 승인해야 하며, 승인 전에는 MCP 호출을 검사하지 않습니다.
- **끄기:** `aeg uninstall --mcp`(Codex는 `aeg uninstall --target codex --mcp`)는 MCP 항목만 지웁니다. `aeg uninstall`은 두 항목을 모두 지웁니다.

기본값으로 켜지 않은 이유는 불편 때문입니다. 켜면 Claude Code에서는 모든 MCP 호출이 승인을 묻고, Codex에서는 허용 목록을 채우기 전까지 모든 MCP 도구가 막힙니다.

## 확인 결과

Claude Code 2.1.316 `claude -p`(Windows)에서 더미 `.env`와 더미 MCP 서버로 경우마다 한 번씩 확인했습니다.

| 경우 | 결과 |
| --- | --- |
| MCP 도구로 `.env` 읽기, auto | 승인 요구, 실행 안 됨 |
| MCP 도구로 `.env` 읽기, Manual, 도구 미리 허용 | 승인 요구, 실행 안 됨 |
| MCP 리소스 읽기, Manual | 승인 요구, 실행 안 됨 |
| MCP 리소스 읽기, auto | 승인 요구, 실행 안 됨 |
| 목록에 넣은 `mcp__probe__echo`, Manual, 미리 허용 안 함 | 실행됨 |
| 목록에 없는 도구로 `.env` 읽기(`echo`만 목록에 있음), auto | 승인 요구, 실행 안 됨 |
| `Read` README.md (대조군) | 허용, 한 번만 판정 |
| `Read` .env (대조군) | 차단 |
| MCP 보호 없이 MCP 도구로 `.env` 읽기, auto (대조군) | 값 출력, 장승 기록 없음 (0.1.8과 같음) |

- 실행되지 않은 경우에는 모두 MCP 서버에 호출이 가지 않았고, 장승 기록에 `ask`가 남았습니다.
- `claude -p`에는 승인할 사람이 없어 `ask`가 실행 거부로 끝났습니다. 대화형 세션에서 승인 창이 뜨는지는 확인하지 않았습니다.

Codex CLI 0.166.0 `codex exec`(Windows, `approval_policy=never`)에서는 승인 전 상태만 확인했습니다.

| 경우 | 결과 |
| --- | --- |
| MCP 항목 추가 뒤 `git status --short` | 기존 항목이 계속 판정 (`Bash:allow`) |
| MCP 항목 승인 전, MCP 도구로 `.env` 읽기 | 값 출력, 장승 기록 없음 (승인 전에는 검사하지 않음) |

- 기존 항목의 설정 문구는 MCP 항목을 추가한 뒤에도 한 글자도 바뀌지 않았습니다.
- 승인 후 Codex가 MCP 호출을 막는지는 자동 테스트와 hook CLI로만 확인했습니다.

## 업그레이드 절차

```bash
python -m pip install --upgrade jangseung
aeg doctor --hooks
```

- 올려도 MCP 보호는 꺼져 있습니다. 켜려면 위의 `aeg install --mcp`를 실행하세요.
- 이미 등록한 hook은 그대로 동작합니다. Codex 승인도 다시 받지 않아도 됩니다.

## 동작 변화

- **기본 설치:** 바뀌지 않습니다.
- **직접 넓힌 matcher:** 기존 hook의 matcher에 MCP 도구를 직접 넣은 경우, 0.1.8은 MCP 호출을 모르는 도구로 보고 모두 deny했습니다. 0.1.9는 MCP 규칙(Claude Code `ask`, Codex `deny`)으로 판정합니다.
- **`.aeg/policy.json`:** `allow_mcp_tools` 항목이 생겼습니다. 0.1.8 이하는 이 항목이 있는 파일 전체를 무시합니다.
- **`aeg doctor --hooks`:** MCP 보호가 켜져 있는지 보여 줍니다.
- **`aeg explain --stdin`:** MCP 호출의 판정도 설명합니다.

## 그 밖의 변경

- **보안 정책:** `SECURITY.md`를 추가했습니다. 취약점은 공개 이슈 대신 이 문서의 방법으로 알려 주세요.
- **패키지 정보:** 라이선스를 SPDX 형식(`License-Expression: MIT`)으로 적고, 빌드 요구 버전을 `setuptools>=77.0.3`으로 올렸습니다.
- **CI:** `actions/checkout`과 `actions/setup-python`을 v7으로 올렸습니다.

## 남는 제한

- **허용한 도구:** 장승은 인자를 보지 않으므로, 목록에 넣은 도구가 하는 일은 막지 않습니다.
- **리소스 목록 조회:** `ListMcpResourcesTool` 같은 목록 조회는 검사하지 않습니다. 파일 내용이 아니라 리소스 이름 목록을 돌려주는 도구입니다.
- **Codex 리소스 읽기:** MCP 보호를 켜면 허용할 방법이 없습니다. 항상 막힙니다.
- [0.1.8의 남는 제한](release_0.1.8.md#남는-제한)은 그대로입니다. MCP 도구에 관한 첫 항목은 MCP 보호를 켜지 않은 프로젝트에 해당합니다.

다음은 아직 확인하지 못했습니다.

- 대화형 Claude Code 세션의 승인 창
- 승인 후 Codex 실제 세션에서 MCP 호출이 막히는지
- Linux와 macOS의 실제 세션
