# 장승 0.2.2 릴리스 노트

비슷한 도구들과 견주어 뒤지던 부분을 보강한 릴리스입니다. 판정을 느슨하게 만드는 변경은 없습니다. 바뀐 판정은 모두 `ask`에서 `deny`로 올라간 것입니다.

```bash
python -m pip install --upgrade jangseung
```

hook 등록은 다시 하지 않아도 됩니다. 플러그인으로 쓰면 플러그인을 업데이트하세요.

## 이름을 적지 않고 비밀 파일에 닿는 명령을 막습니다

0.2.1까지는 비밀 파일 이름이 글자 그대로 있을 때만 `deny`였고, 다음 형태는 `ask`였습니다. 승인 창에서 무심코 허용하면 값이 출력됩니다. 이제 `deny`합니다.

- **와일드카드:** `cat .en?`, `cat .[e]nv`, `cat .env*`, `cat certs/*.p?m`, `cat **/id_rs?`, PowerShell의 `Get-Content .en*`. 패턴을 프로젝트 폴더의 실제 파일에 대조해, 지금 있는 비밀 파일에 닿을 때만 막습니다. `wc -l *.py`처럼 비밀 파일에 닿지 않는 와일드카드는 전과 같습니다. `cd certs && cat s*`처럼 명령에 적힌 폴더로 옮겨 가면 그 폴더에서도 대조합니다.
- **`{a,b}` 나열:** `cat .en{v,x}`, `cat {README.md,.env}`.
- **통째로 인코딩한 이름:** `cat $(echo LmVudg== | base64 -d)`, `python -c "open(base64.b64decode('LmVudg=='))"`, hex(`2e656e76`). 단어 하나가 통째로 base64나 hex일 때만 풉니다.

와일드카드 대조에는 다음 선을 두었습니다. 선 밖의 명령은 전과 같이 `ask`입니다.

- **프로젝트 안만 봅니다.** 홈 폴더(`~/.ss?/id_*`), 다른 드라이브, 네트워크 공유(`\\서버\공유\a*`)는 폴더를 열어 보지 않습니다. 명령 글자는 에이전트가 정하므로, hook이 그 글자대로 프로젝트 밖이나 네트워크에 접근해서는 안 됩니다. 프로젝트 안인지는 경로 글자만으로 먼저 확인합니다.
- **읽는 양에 상한이 있습니다.** 한 번의 호출에 폴더 64개, 항목 6,000개까지입니다.
- **글자나 숫자가 없는 패턴은 대조하지 않습니다.** `*`, `.*`, `*.*`는 산술(`2 * 3`), 정규식, PowerShell의 `Select-Object *`에도 쓰입니다. 그래서 `cat *`은 `ask`입니다.
- **이름만 쓰는 명령은 대조하지 않습니다.** `ls .en?`, `stat certs/s*`, 동작 없는 `find`, `git status`·`git add`는 파일을 열지 않습니다(`ls .env`가 허용인 것과 같은 기준). `ls certs/* | wc -l`처럼 파이프로 넘어가는 것은 이름 글자뿐이므로 이것도 대조하지 않습니다. 이름이 읽는 명령의 인자로 넘어가는 길이 있을 때는 대조합니다: `ls .en? | xargs cat`, `cat $(ls .en?)`, `for f in .en?; do cat $f; done`. PowerShell은 와일드카드를 명령에 그대로 넘기므로 파일 명령(`Get-Content`, `Select-String`, `Copy-Item`, `Remove-Item` 등)과, 파일 명령으로 이어지는 목록 명령(`Get-Item .en? | Get-Content`)만 대조합니다. `Get-Process *e*`는 파일과 무관합니다.
- **패턴 자리의 인자는 대조하지 않습니다.** `tar --exclude '.e*'`, `grep -rn '.en?' src`, `jq '.e*' package.json`의 그 인자는 파일 이름이 아니라 프로그램에 주는 패턴입니다.
- **링크는 따라가지 않습니다.** 프로젝트 안의 심볼릭 링크나 정션이 프로젝트 밖을 가리킬 수 있으므로, 링크를 지나는 폴더는 열어 보지 않습니다.

실행 중에 이름을 조립하는 형태(`chr(46)+'env'`, `printf '.e%s' nv`)는 전과 같이 `ask`입니다. 명령 글자만으로는 알 수 없기 때문이며, [잔여 위험 등록부](residual_risk.md) RR-2와 RR-2a에 적었습니다.

## 프로젝트 밖을 파괴하는 명령을 막습니다

0.2.1까지 `ask`였던 다음 명령을 `deny`합니다. 프로젝트 파일로 되돌릴 수 없는 파괴입니다.

- **클라우드·호스팅 리소스 삭제:** `aws s3 rb`, `aws s3 rm`, `aws s3 sync --delete`, `aws ec2 terminate-instances`, `aws ... delete-*`, `az ... delete-batch`, `gcloud ... delete`, `az ... delete`, `firebase firestore:delete`, `vercel rm`, `fly apps destroy`, `heroku apps:destroy` 등. 대상 CLI: aws, gcloud, gsutil, bq, az, doctl, fly, heroku, vercel, netlify, firebase, supabase, railway, wrangler, oci, ibmcloud, linode-cli, scw, hcloud.
- **DB 내용 삭제:** `psql`, `mysql`, `mariadb`, `sqlcmd`, `mongosh`, `redis-cli`, `cqlsh`, `clickhouse-client` 등에 `DROP ...`, `TRUNCATE`, `WHERE` 없는 `DELETE FROM`, `FLUSHALL`, `FLUSHDB`, `dropDatabase()`가 인자로 들어간 경우와 `dropdb`, `mysqladmin drop`, `pg_restore --clean`, `mongorestore --drop`.
- **디스크와 시스템:** `mkfs*`, `fdisk`·`parted`(목록 보기 `-l` 제외), `wipefs`, `diskpart`, `diskutil erase...`, `format D:`, `Format-Volume`, `Clear-Disk`, `vssadmin delete`, `bcdedit /delete`, `shutdown`(취소 `/a`, `-c` 제외), `reboot`, `systemctl poweroff`, `init 0`, `Stop-Computer`, `Restart-Computer`, `kill -9 -1`, `kill 1`.

`aws s3 ls`, `gcloud projects list`, `psql -c "select ..."`, `fdisk -l`, `kill 1234` 같은 일반 명령은 전과 같이 `ask`입니다. 클라우드 CLI는 명령 자리의 단어만 봅니다(`aws <서비스> <동작>`). 그 뒤의 리소스 이름이 `delete-me`여도 막지 않습니다. SQL은 문장이 그 단어로 시작할 때만 봅니다(`comment on table t is 'do not truncate me'`는 해당 없음). 디스크 도구는 보여 주기만 하는 옵션(`fdisk -l`, `sgdisk -p`, `parted ... print`, `mkfs -n`, PowerShell의 `-WhatIf`)이면 막지 않습니다. 로컬 개발 자원을 지우는 `docker compose down -v`, `sqlite3 app.db "drop table t"`도 `ask`로 둡니다(등록부 RR-11). 사람이 에이전트에게 맡기려는 명령은 `aeg policy add --command "aws s3 rm"`처럼 접두사로 승인할 수 있습니다.

## 막은 이유를 종류별로 말합니다

위험 명령을 막을 때의 문장이 "위험한 명령입니다" 한 가지였습니다. 이제 종류를 말합니다: 게시·배포, 계정 리소스 삭제, DB 삭제, 디스크·시스템, 폴더 강제 삭제, 네트워크 전송·환경 출력·권한 변경. reason code에 `dangerous_command_kind:<종류>`가 추가됩니다. 종류 이름은 고정 목록에서만 나오며 명령의 글자는 들어가지 않습니다.

## hook 호출이 조금 빨라졌습니다

hook 경로에서 쓰지 않는 모듈(`argparse`, `tempfile`과 그것들이 끌어오는 `shutil` 등)을 읽지 않게 했습니다. 같은 위치에서 같은 방법으로 잰 호출 한 번의 중앙값이 약 194 ms에서 약 180 ms로 줄었습니다(Windows, Python 3.14, 15회씩 두 번, 약 7%). 남은 시간의 대부분은 Python 시작과 판정 모듈을 읽는 시간이며, 판정 자체는 3–5 ms입니다. `aeg hook-run`이 받는 인자(`--substrate`, `--mcp`, `--ensure-state`)는 전과 같고, 모르는 인자는 전과 같이 종료 코드 2로 끝납니다.

## `aeg evidence summary`

기록을 읽어 판정 수와, 자주 멈춘 프로그램·파일을 보여 줍니다. 무엇을 `aeg policy`로 풀어 줄지 정할 때 씁니다. 읽기만 하며 `.aeg`를 바꾸지 않습니다. 기록에는 명령 원문이 없으므로 프로그램 이름까지만 나옵니다.

```bash
aeg evidence summary
aeg evidence summary --days 7 --json
```

## 잔여 위험 등록부

막지 못한다고 알고 받아들인 것을 [docs/residual_risk.md](residual_risk.md)에 모았습니다. 받아들이지 않는 것(통과하면 결함인 것)의 목록과, 아직 판정하지 않은 항목도 함께 적었습니다.

## 확인 결과

- 자동 테스트: Windows, Python 3.14에서 전체 통과(1592 passed, 20 skipped). 새 테스트 405개는 `tests/test_competitive_gaps_0_2_2.py`입니다.
- 판정 조사(같은 명령 목록을 0.2.1과 0.2.2에 돌려 비교, Claude Code `default` 모드):
  - 난독화한 비밀 접근 64종: `deny` 51 → 56, `ask` 13 → 8, `allow`·호스트 위임 0 → 0.
  - 파괴적 명령 48종: `deny` 30 → 42, `ask` 18 → 6, `allow`·호스트 위임 0 → 0.
  - 일상 명령 50종: 변화 없음(`allow` 15, 호스트 위임 23, `ask` 9, `deny` 3).
- 독립 검토: 같은 모델의 별도 에이전트가 변경분을 네 번 공격적으로 검토했습니다. 네 번 모두 0.2.1보다 약해진 판정은 없었습니다(명령 2,800건 비교와 무작위 3,000건). 찾은 것과 조치는 다음과 같습니다.
  - 1차: 조작된 와일드카드·중괄호 입력에 한 호출이 135초, 91초 걸림(호스트 제한 30초 초과). 읽는 양에 상한을 두고 중괄호 처리를 한 번 훑는 방식으로 바꿨습니다. 일상 명령 오탐(`2 * 3`, `Select-Object *`)과 파괴 규칙 오탐(`fdisk -l`, 리소스 이름 `delete-me`)도 고쳤습니다.
  - 2차: 1차 지적을 고치며 대조 범위를 프로젝트 밖으로 넓힌 것이 문제였습니다. 명령에 네트워크 공유 경로가 있으면 hook이 접속을 시도하고 21초 이상 멈췄습니다. 대조를 프로젝트 안으로 되돌리고, 경로 글자만으로 먼저 확인하게 했습니다. 정규식 역추적 지연과 파괴 규칙 누락·오탐도 고쳤습니다.
  - 3차: 높은 등급 없음. 프로젝트 경로가 링크나 짧은 이름으로 적힌 경우 대조가 꺼지는 문제, 프로젝트 안 링크를 따라 밖을 읽는 문제, 이름이 읽는 명령으로 넘어가는 형태의 누락을 고쳤습니다.
  - 4차: 중간 등급 이상 없음. 프로젝트 밖 폴더 접근 0건(호출 추적), 네트워크 지연 없음, 내부 오류 0건. 남은 오탐 하나(`ls certs/* | wc -l`)를 좁혔고, 이 마지막 조정은 다시 검토하지 않았습니다.
- 최악 시간: 조작된 76 KB 명령 한 건이 약 1초입니다(0.2.1은 약 0.27초). 일반 명령은 차이가 없습니다.
- 실제 세션: 최종 코드로 Claude Code 2.1.316 `claude -p`(Windows, `default` 모드, 플러그인으로 로드)에서 한 번씩 확인했습니다. `cat .en?`, `ls .en? | xargs cat`, `aws s3 rb s3://bucket-x`는 실행되지 않고 새 사유 문장이 표시되었습니다. `ls .en? | wc -l`은 전과 같이 승인을 요구했고, `git status`는 실행되었으며, `pytest --version`은 호스트가 승인을 요구했습니다.
- 확인하지 못한 것: Codex 실제 세션, 대화형 세션, hook이 제한 시간을 넘겼을 때 호스트의 동작. macOS·Linux는 CI의 자동 테스트로만 확인합니다(심볼릭 링크 경로 포함). 외부 보안 검토는 없습니다.
