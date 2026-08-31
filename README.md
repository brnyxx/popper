# Popper

반증(Popperian falsification)을 UX 문법으로 삼는 Claude Code 설정 수렴 도구.

설정 인터뷰 대신, 같은 장면을 서로 다른 방식으로 수행한 **대비 페어
트랜스크립트**를 제시한다. 사용자의 유일한 동사는 **긋기**(빨간펜)다.
틀렸다고 보이는 쪽을 그으면 그 값이 8축 x 3값 가설 공간(6,561조합)에서
빠지고, 살아남은 조합이 실행 가능한 룰로 컴파일된다. 확인/승인/예-아니오
컨트롤은 어디에도 없다 - 생존은 승인이 아니라 "아직 반증 안 됨"이다.

- 세션 런타임에 LLM 호출 0회, 네트워크 호출 0회 (로컬 픽스처 + 순수 fold만)
- 모든 상태는 append-only 이벤트 스트림의 파생값 (replay 결정적)
- 산출물은 `~/.claude/popper/` 단독 소유 - 사용자 파일은 허가된 @import 한 줄 외 무변경

## Quickstart

origin 없는 Popper 소스 체크아웃 루트에서 로컬 marketplace로 설치하고 첫
진단을 실행한다.

```bash
claude plugin marketplace add "$PWD"
claude plugin install popper@popper-marketplace
```

새 Claude Code 세션에서:

```text
/popper:popper doctor
/popper:popper open
```

브라우저에서 15번 긋고 나면 규칙이 `~/.claude/popper/`에 착지한다.
중간에 터미널이나 브라우저가 닫혀도 같은 `open` 명령이 유일한 미완료 일반
세션을 저장된 슬롯부터 계속한다. 여러 미완료 세션이 있으면
`/popper:popper sessions`로 ID를 보고 `resume <id>`를 사용한다.

## CLI

런타임은 Python 표준 라이브러리만 사용한다.

```bash
popper open                     # 미완료 1건 자동 재개, 없으면 새 일반 세션
popper resume [session-id]      # product/validation/recheck 중단 세션 재개
popper sessions [session-id]    # 최근 목록 또는 bounded 이벤트 상세
popper status [--json]          # 착지/활성화/재개/판정 진실
popper doctor [--json]          # 설치·봉인·replay·loopback 로컬 진단
popper recheck                  # 재심 큐 선두 5-7긋기
popper validate                 # 판별 13 + 미러 프로브 2
popper export --format agents   # markdown/agents/claude/json
```

소스 체크아웃에서는 `pip install -e .`, 릴리스 파일에서는
`pip install popper-1.1.0-py3-none-any.whl`로 `popper` 명령을 설치한다.
wheel에는 픽스처, 봉인 문서, 정답지가 모두 포함된다.

### Claude Code 플러그인으로

```bash
claude --plugin-dir /path/to/popper
```

이후 `/popper:popper` 스킬로 세션을 연다. 재심 대기 배너가 있으면 스킬이
먼저 알려준다. 플러그인 런처는 호출한 프로젝트의 `$PWD`를 보존해
`--repo "$PWD"`로 전달하므로 generic fixture로 조용히 퇴행하지 않는다.

## 세션 계약

| 프로파일 | 슬롯 | 구성 | 완주 시 |
|---|---|---|---|
| product | 15 | 판별 15, 프로브 0 | `~/.claude/popper/` 착지 |
| validation | 15 | 판별 13 + 슬롯 9/13 미러 프로브 2 | 착지 없음 (판정 표본만 적재) |
| recheck | 5-7 | 재심 큐 선두 (불안정 > untested-prior > 충돌) | 재착지 + last_review 갱신 |

- 완전 판별 축이 5 미만이면 `session_voided(axis_shortfall)` - 착지하지 않는다.
- 오긋기 복구는 명시 이벤트 채널뿐이다: **마지막 긋기 무르기**(undo_tombstone),
  막 경계의 revive, 축 3값 전멸 시 모순 이벤트. 무른 슬롯은 돌려주지 않는다 -
  캡은 봉인 수치다.
- 판정 영향 수치(cap 15, N_val 2, floor 5 등)의 소유자는 봉인 사전등록 문서
  `docs/prereg/prereg_sealed.json`이다. 코드는 수치를 소유하지 않는다.

## 반복 사용과 복구

- 각 선택은 즉시 세션 JSONL에 append되고 화면은 replay 결과만 보여 준다.
- `popper open`은 미완료 일반 세션이 정확히 하나일 때 자동 재개한다.
- 여러 미완료 세션은 임의 선택하지 않고 `popper resume <id>`를 요구한다.
- 동일 세션을 두 프로세스가 동시에 열면 수명주기 잠금이 두 번째 서버를 거부한다.
- 연결이 끊긴 웹 화면은 `popper resume`로 저장된 마지막 슬롯부터 이어진다고
  `role=alert`로 알린다.
- `popper data backup /safe/path/popper.zip`은 잠금 안에서 원자 snapshot과
  SHA-256 sidecar를 만들며, `popper data inspect <zip> --json`은 추출 없이
  경로·크기·checksum을 검증한다. 자동 restore나 silent repair는 없다.

## 산출물

세션 완주 시 `~/.claude/popper/`에 착지한다.

- `POPPER.md` - 8축 전부의 실행 가능한 룰만 (인식론 주석 0줄)
- `manifest.json` - 룰별 corroboration 등급, value_source, content hash,
  last_review, 재심 큐, 충돌 리포트
- `settings.popper.json` - 제안 파일 (라이브 settings.json에 자동 병합하지 않는다)
- `sessions/*.jsonl` - append-only 이벤트 스트림 (단일 진실원)

활성화와 롤백:

```bash
popper enable --grant    # CLAUDE.md 끝에 @import 한 줄 추가 (허가 기록)
popper rollback          # 그 한 줄만 제거 - 전체 롤백 지점
```

`popper status`는 생성과 소비를 섞지 않고 `inactive`, `active`,
`import-drift` 중 하나와 정확한 다음 명령을 보여 준다. Claude 외 호스트에는
자동으로 파일을 쓰지 않는다:

```bash
popper export --format agents --output ./AGENTS.md
popper export --format markdown
popper export --format json > popper-rules.json
```

착지된 파일을 수기로 편집하면 다음 착지가 **차단**된다 (content hash 불일치 =
최강 strike 신호, silent overwrite 금지). 의도한 편집이면:

```bash
popper land --acknowledge-mismatch
```

## 자기반증

이 도구의 핵심 추측("긋기만으로 설정이 수렴한다")도 반증 대상이다.
검증 세션 누적 + 봉인 정답지 5분류 채점으로 `refutation_condition_met`은
기계(fold)가 방출하고, 확정은 인간의 `refutation_acknowledged`로만 게이트된다.

```bash
popper status                     # 판정 fold 현황
popper acknowledge --actor <이름>  # 조건 성립 후 인간 확정
```

## 벤치마크에서 가져온 것과 버린 것

- **Paperthin에서 가져온 것:** 설치→첫 호출→검증의 짧은 흐름, 얇은 스킬
  어댑터, 사용자 호출 권한, manifest/문서 동기화 게이트.
- **Ouroboros에서 가져온 것:** 이벤트 replay 기반 중단 재개, bounded 세션
  목록, 완전 로컬 doctor, 명시적 backup/inspect.
- **의도적으로 버린 것:** 스킬 수 경쟁, 모델 오케스트레이션, MCP/daemon,
  텔레메트리, 자동 업데이트, 클라우드 동기화. Popper 런타임은 계속 LLM과
  외부 네트워크를 한 번도 호출하지 않는다.

## 개발

```bash
python3 -m pytest tests/ -q    # 전체 스위트
```

모듈 구성: `events`(strike-only 스키마) / `counter`(6,561 fold) /
`recovery`(undo·revive·모순) / `compiler`(룰 + manifest) / `writer`(소유권 분리)
/ `conflict`(수기 룰 충돌) / `session`(프로파일 봉인) / `judgment`(자기반증 fold)
/ `recheck`(4막 재심) / `scoring`(5분류 채점) / `fixtures`(고정 픽스처 렌더) /
`store`(append-only JSONL) / `sessions`(요약·재개) / `doctor`(로컬 진단) /
`backup`(snapshot 검사) / `exporter`(호스트 중립 출력) /
`web`(콜드 오픈 UI) / `cli`(진입점).

## 지원 환경 및 GA 설치

Popper 1.1.0은 Python 3.10–3.14, macOS/Linux/Windows에서 지원된다.
브라우저 검증은 Chromium, Firefox, WebKit을 사용한다.

릴리스 ZIP만 받은 경우 다음 경로에 풀어 같은 로컬 marketplace로 등록한다:

```bash
mkdir -p "$HOME/.local/share/popper-1.1.0"
python3 -m zipfile -e popper-plugin-1.1.0.zip "$HOME/.local/share/popper-1.1.0"
claude plugin marketplace add "$HOME/.local/share/popper-1.1.0"
claude plugin install popper@popper-marketplace
```

체크아웃한 플러그인을 시험할 때는 다음처럼 로컬 경로를 지정한다:

```bash
claude --plugin-dir /path/to/popper
```

런타임은 loopback 로컬 서버와 고정 fixture만 사용하며 외부 네트워크나
- 세션 이벤트와 생성물은 `~/.claude/popper/`에만
기록하고, 사용자 파일에는 허가된 `@import` 한 줄만 쓴다. 민감한 파일을
fixture나 프롬프트에 넣지 말고, 플러그인 권한과 로컬 파일 접근을 검토한
뒤 실행한다.

이벤트 append와 산출물 착지는 프로세스 간 파일 잠금으로 직렬화되며, 파일은
같은 디렉토리의 임시 파일을 `os.replace`하는 방식으로 원자 교체된다. 진행 중인
다른 세션은 착지 fold에서 제외된다. 웹 서버는 루프백 외 바인딩과 신뢰되지 않은
Host/Origin을 거부하고 세션 완료 응답 후 자동 종료된다.

릴리스 파일은 SHA-256으로 검증할 수 있다:

```bash
sha256sum -c SHA256SUMS
python -m zipfile -l popper-plugin-1.1.0.zip
```
