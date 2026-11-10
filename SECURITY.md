# 보안 정책

장승(Jangseung)의 취약점을 찾았다면 공개하기 전에 비공개로 알려 주세요.

## 지원 버전

보안 수정은 PyPI의 최신 릴리스에만 넣습니다. 이전 버전에는 따로 수정판을 내지 않습니다.

| 버전 | 보안 수정 |
| --- | --- |
| 최신 릴리스 | 지원 |
| 그 밖의 버전 | 지원 안 함 |

## 신고 방법

공개 이슈, 풀 리퀘스트, 토론에는 취약점 내용을 적지 마세요. 수정되기 전에 공개되면 사용자가 위험해집니다.

1. 저장소의 **Security** 탭에서 **Report a vulnerability**를 눌러 비공개로 신고하세요. 바로 가기: <https://github.com/tjrwo736/jangseung/security/advisories/new>
2. 이 버튼이 없으면 공개 이슈를 열어 비공개 연락 방법을 요청하세요. 이 이슈에는 취약점 내용을 적지 마세요.

다음을 함께 적어 주시면 확인이 빠릅니다.

- 장승 버전 (`python -m pip show jangseung`의 `Version`)
- 호스트와 버전 (Claude Code, Codex CLI), 운영체제
- 문제가 된 도구 호출, 기대한 판정, 실제 결과
- `aeg explain`으로 본 판정 (사용법은 README의 [판정 설명과 설치 상태 진단](README.md#판정-설명과-설치-상태-진단))
- 재현 절차

재현에는 실제 비밀 값 대신 더미 값을 쓰세요.

## 처리 방식

문제가 확인되면 수정 버전을 배포하고 GitHub 보안 권고를 공개합니다. 지금까지 공개한 권고는 <https://github.com/tjrwo736/jangseung/security/advisories>에 있습니다.

## 신고 대상

장승이 검사하는 도구 호출에서 판정을 피해 가는 방법은 신고 대상입니다. 예를 들면 다음과 같습니다.

- 비밀 파일 읽기, 보호 경로 수정, 위험 명령이 승인 없이 실행되는 경우
- 에이전트가 장승을 끄거나 기록을 조작할 수 있는 경우
- MCP 보호(`aeg install --mcp`)를 켰는데 목록에 없는 MCP 호출이 승인 없이 실행되는 경우
- 빌드·의존성 파일 수정이 승인 없이 실행되는 경우, 또는 비밀 파일·장승 설정 수정이 deny가 아닌 `ask`로 내려가는 경우 (0.2.0부터)
- 에이전트가 `aeg policy`나 다른 방법으로 `.aeg/policy.json`을 바꿀 수 있는 경우
- hook 기록(`.aeg/hook_ledger.jsonl`)에 파일 내용이나 명령 인자가 남는 경우
- README에 적은 판정과 실제 판정이 다른 경우

README의 [우리가 못 막는 것](README.md#우리가-못-막는-것)과 [지원 범위](README.md#지원-범위)에 적은 한계는 이미 알려진 제한입니다. 에이전트가 쓴 코드를 승인된 명령이 실행하는 경로, `WebFetch`, `WebSearch`를 검사하지 않는 것과, MCP 보호를 켜지 않은 프로젝트에서 MCP 도구와 MCP 리소스 읽기를 검사하지 않는 것도 여기에 속합니다. 다만 적힌 것보다 영향이 크면 신고해 주세요.

## English

- Security fixes go into the latest PyPI release only.
- Report privately from the **Security** tab with **Report a vulnerability** (<https://github.com/tjrwo736/jangseung/security/advisories/new>). Do not put details in public issues, pull requests or discussions. If the button is missing, open an issue that asks for a private contact and contains no details.
- Include the Jangseung version, the host and its version (Claude Code or Codex CLI), the OS, the tool call, the decision you expected, the result you got, and steps to reproduce. Use dummy values instead of real secrets.
- With MCP protection on (`aeg install --mcp`, 0.1.9 and later), an unlisted MCP call that runs without approval is in scope.
- From 0.2.0, also in scope: a build or dependency file changed without approval, a secret or guard path answered with `ask` instead of `deny`, an agent able to change `.aeg/policy.json`, and file content or command arguments appearing in the hook ledger.
- Limits documented in the README are known. These include code an agent wrote being run by a command a person approved, not inspecting `WebFetch` and `WebSearch`, and not inspecting MCP tools and MCP resource reads in projects without MCP protection. Report them if the impact is larger than documented.
