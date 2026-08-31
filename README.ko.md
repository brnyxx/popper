<div align="center">

<h1>Popper</h1>

<img src=".github/assets/logo.svg" alt="Popper 로고: 대비 페어 한쪽에 빨간 선을 긋고 가설을 하나의 생존자로 좁히는 모습" width="96">

<img src=".github/assets/hero.svg" alt="Popper — 대비 페어에서 틀린 쪽을 긋고 6,561개 선호 가설을 실행 규칙으로 좁히는 도구" width="920">

**소거로 찾는 선호.**

[English](README.md)

</div>

Popper는 설정 인터뷰를 하나의 동사로 바꿉니다. **틀린 쪽을 긋기.** 두 가지 구체적인 코딩 에이전트 행동을 보여 주고, 사용자가 거부한 것을 기록하며, 살아남은 선호를 로컬 Claude Code 규칙으로 컴파일합니다.

**v1.2.0 · Python 3.10–3.14 · MIT · 서드파티 Python 런타임 패키지 0개 · 런타임 LLM/외부 네트워크 호출 0회**

<details>
<summary><strong>실제 15긋기 세션 보기</strong> (1.6 MB GIF)</summary>
<br>
<img src=".github/assets/demo.gif" alt="실제 Popper 브라우저 UI가 0번부터 15번 긋기까지 진행하고 로컬 규칙을 컴파일한 뒤 세션을 완료하는 모습" width="860">
</details>

## 여기서 시작하세요

[v1.2.0 릴리스](../../releases/tag/v1.2.0)에서 `popper-plugin-1.2.0.zip`, `SHA256SUMS`, `verify_checksums.py`를 같은 디렉터리에 받은 뒤 압축을 풀기 전에 검증합니다.

macOS 또는 Linux:

```bash
python3 verify_checksums.py SHA256SUMS \
  --only popper-plugin-1.2.0.zip verify_checksums.py
DEST="$HOME/.local/share/popper-plugin-1.2.0"
test ! -e "$DEST" || { echo "destination already exists: $DEST" >&2; exit 1; }
python3 -m zipfile -e popper-plugin-1.2.0.zip "$DEST"
claude plugin marketplace add "$DEST"
claude plugin install popper@popper-marketplace
```

Windows PowerShell:

```powershell
py -3 verify_checksums.py SHA256SUMS `
  --only popper-plugin-1.2.0.zip verify_checksums.py
$Dest = Join-Path $env:LOCALAPPDATA "Popper\plugin-1.2.0"
if (Test-Path $Dest) { throw "destination already exists: $Dest" }
py -3 -m zipfile -e popper-plugin-1.2.0.zip $Dest
claude plugin marketplace add $Dest
claude plugin install popper@popper-marketplace
```

새 Claude Code 세션에서 실행합니다.

```text
/popper:popper doctor
/popper:popper open
```

각 대비 페어에서 한쪽을 긋습니다. 열다섯 번째 긋기가 끝나면 Popper가 소유한 세 파일이 `~/.claude/popper/`에 착지합니다.

```text
POPPER.md
manifest.json
settings.popper.json
```

활성화는 별도의 명시적 단계입니다.

```text
/popper:popper enable
/popper:popper status
```

`enable`은 `~/.claude/CLAUDE.md`에 Popper가 소유한 `@import` 한 줄만 추가합니다. `/popper:popper rollback`은 그 한 줄만 제거합니다.

소스 체크아웃에서는 릴리스 아카이브 없이 설치할 수 있습니다.

```bash
claude plugin marketplace add "$PWD"
claude plugin install popper@popper-marketplace
```

패키지 설치는 선택한 패키지 또는 플러그인 저장소에 접속할 수 있습니다. Popper 세션이 시작된 뒤에는 LLM이나 외부 네트워크를 호출하지 않으며, 브라우저는 Popper의 loopback HTTP 서버와만 통신합니다.

## 한 번의 긋기

Popper는 `3⁸ = 6,561`개의 선호 가설, 즉 축 여덟 개와 축당 값 세 개에서 시작합니다. 대비 페어는 숨어 있던 선호 하나를 눈에 보이는 행동으로 바꿉니다.

| 반증됨 | 생존자 |
|---|---|
| ~~페이지네이션을 고치기 전에 테스트와 정리도 범위인지 질문하라.~~ | 페이지네이션을 고치고 집중 테스트를 실행한 뒤 변경과 근거를 보고하라. |

값 하나를 거부하면 공간은 `6,561`에서 `4,374`로 줄어듭니다. 증거가 반복되면 다음과 같은 규칙으로 컴파일됩니다.

```text
먼저 행동하고 집중 검증을 실행한 뒤 변경과 근거를 보고하라.
```

브라우저 UI 자체가 제품 상호작용입니다. 설문도 아니고, 에이전트가 대신 추측하는 프롬프트도 아닙니다. 긋기는 즉시 append-only 이벤트로 저장되고 모든 화면은 replay 결과에서 다시 만들어집니다.

## 목적에 맞는 명령

### Claude Code 안에서 (주요 plugin 표면)

| 하려는 일 | 명령 | 경계 |
|---|---|---|
| 일반 흐름 시작 또는 계속 | `/popper:popper open` | 미완료 product 세션이 하나면 재개하고, 없으면 새 15긋기 세션을 엽니다 |
| 특정 중단 세션 재개 | `/popper:popper resume SESSION_ID` | 선택한 product/validation/recheck 세션을 봉인된 context에서 replay합니다 |
| 세션 목록 | `/popper:popper sessions` | 로컬 foreground 조회만 제공하며 삭제·재작성 경로가 없습니다 |
| 설치 진단 | `/popper:popper doctor` | 패키지 데이터, 봉인, replay, 착지 무결성, loopback bind를 검사합니다 |
| 착지 상태 확인 | `/popper:popper status` | `inactive`, `active`, `import-drift`를 구분합니다 |
| 불안정한 규칙 재심 | `/popper:popper recheck` | daemon이나 background poller 없이 수동으로 5–7번 긋습니다 |
| 봉인된 validation 실행 | `/popper:popper validate` | 판별 슬롯 13개와 mirrored probe 2개입니다 |
| 활성화 또는 롤백 | `/popper:popper enable` / `/popper:popper rollback` | plugin adapter가 명시적인 `enable` 요청만 consent-gated `enable --grant`로 바꾸며, rollback은 receipt가 소유한 import만 제거합니다 |

### 설치된 wheel 또는 `popper` console

| 하려는 일 | 명령 |
|---|---|
| 세션 상세 JSON 보기 | `popper sessions SESSION_ID --json` |
| 다른 에이전트용 export | `popper export --format agents --output AGENTS.md` |
| 이동 가능한 snapshot 생성 | `popper data backup /safe/path/popper.zip` |
| 압축을 풀지 않고 snapshot 검사 | `popper data inspect popper.zip --json` |
| 명시적 동의로 활성화 | `popper enable --grant` |

`python -m popper ...`는 `popper ...` console 명령과 같습니다.

## 중단을 전제로 설계했습니다

- 허용된 모든 행동은 세션별 append-only JSONL에 즉시 fsync됩니다.
- base 단위 프로세스 잠금이 세션 생성 전에 대화형 서버 하나만 admission합니다.
- 세션은 fixture catalog, 세션 규격, repository skin, canonical rendered-pair digest를 봉인합니다.
- 마지막 긋기 직후 프로세스가 죽어도 resume 시 idempotent하게 finalize하고 착지합니다.
- 부분 JSONL과 부분 착지는 조용히 수리하지 않고 fail-closed합니다.
- loopback 서버는 외부 bind, 잘못된 Host/Origin, stale pair 제출을 거부합니다.
- 세션이 끝나면 서버가 자동 종료되어 idle background process가 남지 않습니다.

## 구조적으로 로컬입니다

Popper는 `~/.claude/popper/`만 소유하며 프로젝트 파일을 몰래 편집하지 않습니다. 다음을 하지 않습니다.

- 세션 중 모델 또는 외부 서비스 호출
- telemetry, analytics, cookie, browser storage 수집
- 대비 페어로 드러나고 사용자가 긋지 않은 선호 추론
- 자동 업데이트, 자동 활성화, 손상 데이터의 silent reset
- Paperthin의 스킬 카탈로그나 Ouroboros의 오케스트레이션 런타임 복제

GitHub Pages도 같은 경계를 지킵니다. 국·영문 정적 HTML/CSS와 저장소 내부 자산만 사용하며 JavaScript, analytics, 원격 런타임 자산이 없습니다. [`scripts/build_site.py`](scripts/build_site.py)는 SHA가 고정된 [Pages workflow](.github/workflows/pages.yml)가 배포하기 전에 번역 parity, 링크, SEO metadata, 접근성 구조, 정확한 artifact 경계를 검증합니다.

## 공유와 검증

전체 이벤트 이력을 노출하지 않고 규칙만 공유할 수 있습니다.

```bash
popper export --format markdown > POPPER.export.md
popper export --format agents --output AGENTS.md
popper export --format json > popper-rules.json
```

릴리스에는 wheel, source archive, Claude plugin ZIP, 독립 실행형 검증기, `SHA256SUMS`, GitHub artifact provenance가 포함됩니다. 필요한 파일을 받은 뒤 표준 라이브러리 스크립트로 확인합니다.

```bash
python3 verify_checksums.py SHA256SUMS \
  --only popper-plugin-1.2.0.zip verify_checksums.py
```

Python matrix, Chromium/Firefox/WebKit 완료·복구 E2E, 깨끗한 Claude marketplace 설치, plugin lifecycle, package build, manifest version gate가 모두 통과해야 릴리스가 게시됩니다. GitHub Actions와 release action은 검토한 commit SHA로 고정했고 CI의 Claude CLI도 정확한 버전으로 고정했습니다.

## 업데이트

Popper는 background version check를 하지 않습니다.

### 기존 v1.1.0 marketplace를 v1.2.0으로 이동

v1.1.0 문서는 `~/.local/share/popper-1.1.0`을 등록했습니다. Claude가 이전 source를 계속 읽지 않도록 marketplace를 다시 등록합니다.

```bash
python3 verify_checksums.py SHA256SUMS \
  --only popper-plugin-1.2.0.zip verify_checksums.py
DEST="$HOME/.local/share/popper-plugin-1.2.0"
test ! -e "$DEST" || { echo "destination already exists: $DEST" >&2; exit 1; }
python3 -m zipfile -e popper-plugin-1.2.0.zip "$DEST"
claude plugin marketplace remove popper-marketplace
claude plugin marketplace add "$DEST"
claude plugin update popper@popper-marketplace
```

Claude Code를 다시 시작하고 `/popper:popper doctor`를 실행합니다. healthy 결과를 확인한 뒤에만 `~/.local/share/popper-1.1.0`을 제거합니다.

### 이후 릴리스

아래 `X.Y.Z`를 정확한 릴리스 버전으로 바꾸고 새 디렉터리에 압축을 풉니다.

```bash
VERSION=X.Y.Z
python3 verify_checksums.py SHA256SUMS \
  --only "popper-plugin-${VERSION}.zip" verify_checksums.py
DEST="$HOME/.local/share/popper-plugin-${VERSION}"
test ! -e "$DEST" || { echo "destination already exists: $DEST" >&2; exit 1; }
python3 -m zipfile -e "popper-plugin-${VERSION}.zip" "$DEST"
claude plugin marketplace remove popper-marketplace
claude plugin marketplace add "$DEST"
claude plugin marketplace update popper-marketplace
claude plugin update popper@popper-marketplace
```

Claude Code를 다시 시작한 뒤 `/popper:popper doctor`를 실행합니다. 기존 이벤트와 착지 규칙은 플러그인 패키지 밖에 그대로 남습니다. 새 설치가 `doctor`를 통과한 뒤에만 이전 버전 디렉터리를 제거합니다.

## 개발

```bash
python3 -m pip install -e '.[test,e2e,release]'
python3 -m pytest tests/ -q
python3 scripts/build_site.py \
  --output /tmp/popper-pages \
  --site-url "$POPPER_SITE_URL" \
  --repository-url "$POPPER_REPOSITORY_URL"
claude plugin validate .
```

CI는 Python 3.10–3.14, macOS/Linux/Windows, Chromium/Firefox/WebKit, 깨끗한 plugin 설치, wheel/sdist 검증, 결정적 plugin packaging, Pages contract를 다룹니다.

## 범위

Popper는 의도적으로 좁습니다. 동결된 여덟 개 선호 축을 명시적 거부로 수렴시킵니다. 범용 prompt manager, cloud profile service, autonomous agent orchestrator, 프로젝트별 지시사항의 대체물이 아닙니다.

봉인된 사전등록은 [`docs/prereg/prereg_sealed.json`](docs/prereg/prereg_sealed.json), 동결된 축 locality 판정표는 [`docs/axis_locality_table.md`](docs/axis_locality_table.md)에 있습니다.

MIT © 2026 Brian Kim.
