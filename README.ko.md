<div align="center">

<h1>Popper</h1>

<img src=".github/assets/logo.svg" alt="Popper 로고: 두 에이전트 행동 카드 중 하나에 빨간 줄을 긋고 생존자가 규칙으로 이어지는 모습" width="96">

**로컬 CLAUDE.md 행동 컴파일러.**

<img src=".github/assets/hero.svg" alt="버그 수정 요청이 두 행동의 비교로 바뀌고 시작해도 될까요에는 줄이 그어지며 수정과 테스트 완료가 생존해 먼저 실행하고 나중에 보고하라는 규칙이 되는 모습" width="920">

**다시는 보고 싶지 않은 에이전트 행동에 빨간 줄을 긋고, 규칙만 남기세요.**

[English](README.md) · [실시간 설명 페이지](https://brnyxx.github.io/popper/ko/)

</div>

Popper는 코딩 에이전트가 취할 수 있는 구체적인 행동 두 가지를 보여 줍니다. 틀린 쪽에 빨간 줄을 그으면 15번 뒤 살아남은 선택이 Claude Code가 `CLAUDE.md`에서 읽을 수 있는 로컬 규칙으로 컴파일됩니다.

> **한국어 우선 v1:** 세션 UI와 생성 규칙 문구는 한국어입니다.

**v1.3.1 · Python 3.10–3.14 · MIT · 서드파티 Python 런타임 패키지 0개 · 런타임 LLM·텔레메트리·외부 네트워크 호출 0회**

## 제품 전체를 한 가지 예로 이해하기

Claude Code에 버그 수정을 맡길 때마다 에이전트가 멈춰서 진행 허가를 묻는 상황을 생각해 보세요.

1. **요청:** `버그를 고쳐.`
2. **두 행동:** `시작해도 될까요?` / `수정했습니다. 테스트 통과. 변경 사항은 다음과 같습니다.`
3. **사용자가 긋는 쪽:** `시작해도 될까요?`
4. **Popper가 컴파일하는 규칙:** `먼저 실행한 뒤 변경 내역을 요약해 보고한다.`
5. **소유한 import 한 줄을 활성화:** 새 Claude Code 세션에서 같은 요청을 다시 던져 에이전트가 컴파일된 규칙을 따르는지 확인합니다.

위의 “다음 응답”은 `POPPER.md`가 요구하는 행동 계약을 보여 주는 예시입니다. 모든 모델 실행 결과를 보장하는 벤치마크가 아닙니다. Popper가 보장하는 것은 지시문과 근거가 명시적이고 로컬에 있으며 살펴보고 되돌릴 수 있다는 점입니다.

<details>
<summary><strong>실제 15긋기 브라우저 세션 보기</strong> (1.6 MB GIF)</summary>
<br>
<img src=".github/assets/demo.gif" alt="실제 Popper 브라우저 UI가 0번부터 15번 긋기까지 진행하고 로컬 규칙을 컴파일한 뒤 세션을 완료하는 모습" width="860">
</details>

## 15번의 긋기가 구체화하는 것

Popper는 에이전트가 반복해서 다음과 같이 행동할 때 유용합니다.

- 명백한 다음 단계인데도 허가부터 묻는다.
- 원하는 것보다 범위를 넓히거나 지나치게 줄인다.
- 테스트를 빼먹거나 원하지 않는 순서로 작성한다.
- 코드 설명과 문서를 너무 많이 또는 너무 적게 남긴다.
- 오류가 나면 멈춤·재시도·자가 복구 중 원하지 않는 행동을 택한다.
- 워킹 트리만 남겨 달랬는데 커밋까지 만든다.

제품 세션은 여섯 개 행동 축을 직접 비교합니다.

| 축 | 구체적인 결정 |
|---|---|
| 자율성 | 먼저 질문, 알리고 바로 실행, 또는 실행 후 보고 |
| 범위 준수 | 요청만, 인접 결함까지, 또는 선제적 정리 |
| 테스트 규율 | 테스트 먼저, 구현 후 테스트, 또는 요청할 때만 |
| 주석·문서화 | 최소, docstring만, 또는 자세한 설명 |
| 오류 처리 | 중단, 한 번 재시도, 또는 자가 복구 |
| 커밋 스타일 | conventional, 서술형, 또는 자동 커밋 없음 |

응답 언어와 장황함 두 축은 제품 세션에서 직접 긋기 증거를 모으지 못했을 때 **마이닝된 사전 기본값**으로 착지할 수 있습니다. 이 값은 `manifest.json`에 `mined-prior`, `untested`로 표시되고 재심 대기열에 들어갑니다. Popper는 사용자가 긋기로 선택했다고 주장하지 않습니다.

`3⁸ = 6,561` 카운터는 값 세 개를 가진 여덟 축의 조합 수입니다. 정확성의 증명이 아니라 진행 상황을 보여 주는 시각화입니다. 실제 근거는 기록된 긋기, 컴파일된 규칙, 그리고 출처 라벨입니다.

## 무엇이 착지하고 무엇은 바뀌지 않는가

열다섯 번째 긋기 뒤 Popper는 `~/.claude/popper/` 아래에 소유한 산출물 세 개를 원자적으로 기록합니다.

| 파일 | 얻는 것 |
|---|---|
| `POPPER.md` | Claude Code용 한국어 실행 규칙 8줄 |
| `manifest.json` | 규칙 값, 증거 등급, 출처, 근거 이벤트, 콘텐츠 해시 |
| `settings.popper.json` | 검토 가능한 설정 제안 |

세션만으로는 어떤 규칙도 활성화되지 않습니다. `enable`은 `~/.claude/CLAUDE.md`에 receipt가 소유한 `@import` 한 줄을 추가하고, `rollback`은 그 occurrence만 제거합니다. 기존 지시문은 그대로 남습니다.

## 로컬 콘솔 도구로 바로 써 보기

가장 짧은 경로는 릴리스 wheel입니다. 패키지 설치는 GitHub에 접속하지만 Popper 세션은 모델이나 외부 서비스에 접속하지 않습니다.

macOS 또는 Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install \
  https://github.com/brnyxx/popper/releases/download/v1.3.1/popper-1.3.1-py3-none-any.whl
.venv/bin/popper doctor
.venv/bin/popper open
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install `
  https://github.com/brnyxx/popper/releases/download/v1.3.1/popper-1.3.1-py3-none-any.whl
.venv\Scripts\popper doctor
.venv\Scripts\popper open
```

브라우저가 끝날 때까지 틀린 행동을 긋습니다. 완료 뒤:

```bash
popper enable --grant
popper status
```

새 Claude Code 세션을 열고 이전에 거슬렸던 행동을 만들던 요청을 다시 던집니다. `popper rollback`은 활성화 전 상태로 되돌립니다.

## 체크섬을 검증해 Claude Code 안에 설치하기

[v1.3.1 릴리스](../../releases/tag/v1.3.1)에서 `popper-plugin-1.3.1.zip`, `SHA256SUMS`, `verify_checksums.py`를 같은 디렉터리에 받은 뒤 압축을 풀기 전에 검증합니다.

macOS 또는 Linux:

```bash
python3 verify_checksums.py SHA256SUMS \
  --only popper-plugin-1.3.1.zip verify_checksums.py
DEST="$HOME/.local/share/popper-plugin-1.3.1"
test ! -e "$DEST" || { echo "destination already exists: $DEST" >&2; exit 1; }
python3 -m zipfile -e popper-plugin-1.3.1.zip "$DEST"
claude plugin marketplace add "$DEST"
claude plugin install popper@popper-marketplace
```

Windows PowerShell:

```powershell
py -3 verify_checksums.py SHA256SUMS `
  --only popper-plugin-1.3.1.zip verify_checksums.py
$Dest = Join-Path $env:LOCALAPPDATA "Popper\plugin-1.3.1"
if (Test-Path $Dest) { throw "destination already exists: $Dest" }
py -3 -m zipfile -e popper-plugin-1.3.1.zip $Dest
claude plugin marketplace add $Dest
claude plugin install popper@popper-marketplace
```

새 Claude Code 세션을 열고 실행합니다.

```text
/popper:popper doctor
/popper:popper open
```

완료 뒤:

```text
/popper:popper enable
/popper:popper status
```

새 Claude Code 세션에서 같은 종류의 요청을 다시 던집니다. `/popper:popper rollback`은 Popper가 소유한 import 한 줄만 제거합니다. 소스 체크아웃은 `claude plugin marketplace add "$PWD"`로 직접 등록할 수도 있습니다.

## 목적별 명령

### Claude Code 안에서

| 원하는 일 | 명령 | 확인할 결과 |
|---|---|---|
| 시작 또는 계속 | `/popper:popper open` | 유일한 미완료 흐름을 재개하거나 새 15긋기 세션을 엽니다 |
| 세션 하나 재개 | `/popper:popper resume SESSION_ID` | 봉인된 해당 세션을 추가 전용 이벤트에서 재생합니다 |
| 세션 찾기 | `/popper:popper sessions` | 삭제하거나 다시 쓰지 않고 로컬 세션을 나열합니다 |
| 설치 진단 | `/popper:popper doctor` | 패키지 데이터, 봉인, 재생, 착지 무결성, loopback 바인딩을 검사합니다 |
| 활성화 확인 | `/popper:popper status` | `inactive`, `active`, `import-drift`를 구분합니다 |
| 규칙 재심 | `/popper:popper recheck` | daemon이나 polling 없이 수동 5–7긋기 재심을 실행합니다 |
| 봉인 검증 | `/popper:popper validate` | 판별 슬롯 13개와 mirrored probe 2개를 실행합니다 |
| 활성화 또는 취소 | `/popper:popper enable` / `/popper:popper rollback` | receipt가 소유한 import 하나를 추가하거나 제거합니다 |

### 설치된 wheel

| 원하는 일 | 명령 |
|---|---|
| 세션 하나를 JSON으로 보기 | `popper sessions SESSION_ID --json` |
| 다른 에이전트용 지시문 내보내기 | `popper export --format agents --output AGENTS.md` |
| 이동 가능한 스냅샷 만들기 | `popper data backup /safe/path/popper.zip` |
| 압축을 풀지 않고 스냅샷 검사 | `popper data inspect popper.zip --json` |
| 명시적 동의로 활성화 | `popper enable --grant` |

`python -m popper ...`는 `popper ...`와 같습니다.

## 로컬 근거 원장이 필요한 이유

내부 엔지니어링 계약은 다음과 같은 사용자 복구 동작으로 이어집니다.

- **중간에 끊겼나요?** 다시 열거나 resume하면 수락된 긋기가 이미 남아 있습니다.
- **마지막 긋기 직후 프로세스가 죽었나요?** resume이 같은 산출물을 한 번만 완성합니다.
- **실수로 세션 두 개를 열었나요?** 두 번째 세션은 경쟁 세션을 만들기 전에 거부됩니다.
- **파일을 직접 고쳤나요?** Popper는 덮어쓰지 않고 착지를 멈춥니다.
- **브라우저가 오래된 페어를 제출했나요?** stale 결정을 거부합니다.
- **규칙이 낡았나요?** 7일 재심 배너가 다시 비교하도록 안내합니다.
- **끄고 싶나요?** rollback은 Popper가 소유권을 증명한 import만 제거합니다.

내부적으로는 추가 전용 JSONL, fsync, 프로세스 잠금, 봉인된 fixture·세션 digest, 결정적 재생, 원자 교체, loopback Host·Origin 검사를 사용합니다.

## 경계

Popper는 `~/.claude/popper/`만 소유하며 프로젝트 파일을 몰래 수정하지 않습니다. 세션 중에는 다음을 하지 않습니다.

- LLM 또는 외부 서비스 호출
- 텔레메트리, 분석, 쿠키, 브라우저 저장소 수집
- 자동 업데이트, 자동 활성화, 손상된 근거의 자동 복구
- 생존을 승인으로 간주—생존자는 아직 반증되지 않았을 뿐입니다
- 마이닝된 사전 기본값을 사용자의 긋기 결과처럼 표현
- Paperthin skill catalog 또는 Ouroboros orchestration runtime 복제

Pages도 같은 경계를 따릅니다. 로컬 자산만 쓰는 이중언어 정적 HTML/CSS이며 JavaScript, 분석, 원격 런타임 리소스가 없습니다.

## 내보내기·검증·업데이트·제거

전체 이벤트 이력을 공유하지 않고 규칙을 내보낼 수 있습니다.

```bash
popper export --format markdown > POPPER.export.md
popper export --format agents --output AGENTS.md
popper export --format json > popper-rules.json
```

받은 릴리스 파일을 검증합니다.

```bash
python3 verify_checksums.py SHA256SUMS \
  --only popper-plugin-1.3.1.zip verify_checksums.py
```

이전 marketplace 설치를 v1.3.1로 옮길 때는 새 버전 디렉터리에 풀고 다시 등록합니다.

```bash
DEST="$HOME/.local/share/popper-plugin-1.3.1"
python3 -m zipfile -e popper-plugin-1.3.1.zip "$DEST"
claude plugin marketplace remove popper-marketplace
claude plugin marketplace add "$DEST"
claude plugin update popper@popper-marketplace
```

Claude Code를 다시 시작하고 `/popper:popper doctor`를 통과한 뒤에만 이전 버전 plugin 디렉터리를 제거합니다. 이벤트와 착지 규칙은 plugin package 밖에 남습니다.

근거와 규칙을 보존한 채 plugin만 제거하려면 먼저:

```text
/popper:popper rollback
```

```bash
claude plugin uninstall popper@popper-marketplace
claude plugin marketplace remove popper-marketplace
rm -rf "$HOME/.local/share/popper-plugin-1.3.1"
```

`~/.claude/popper/`는 사용자 데이터이므로 의도적으로 남깁니다. 먼저 백업하고, 이벤트 이력과 생성 규칙을 정말 폐기하려는 경우에만 해당 디렉터리를 직접 삭제하세요.

## 개발과 릴리스 근거

```bash
python3 -m pip install -e '.[test,e2e,release]'
python3 -m pytest tests/ -q
python3 scripts/build_site.py \
  --output /tmp/popper-pages \
  --site-url "$POPPER_SITE_URL" \
  --repository-url "$POPPER_REPOSITORY_URL"
claude plugin validate .
```

CI는 Python 3.10–3.14, macOS/Linux/Windows, Chromium/Firefox/WebKit, 깨끗하게 설치한 plugin, 결정적 패키지, Pages 계약을 검증합니다. 릴리스에는 wheel, sdist, plugin ZIP, 독립 검증기, `SHA256SUMS`, GitHub artifact provenance가 포함됩니다.

## 범위

Popper는 의도적으로 좁습니다. 동결된 여덟 축 catalog를 위한 로컬 행동 컴파일러이며 범용 prompt manager, cloud profile, model evaluator, autonomous-agent orchestrator가 아닙니다.

봉인된 사전등록은 [`docs/prereg/prereg_sealed.json`](docs/prereg/prereg_sealed.json), 동결된 축 지역성 표는 [`docs/axis_locality_table.md`](docs/axis_locality_table.md)에 있습니다.

MIT © 2026 Brian Kim.
