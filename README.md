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

## 실행

표준 라이브러리만 쓴다. 의존성 설치가 필요 없다.

```bash
python3 -m popper open          # 일반 세션 - 15긋기, 완주 시 착지
python3 -m popper recheck       # 4막 경량 재심 - 재심 큐 선두 5-7긋기
python3 -m popper validate      # 검증 세션 - 판별 13 + 미러 프로브 2
python3 -m popper status        # 착지/재심 배너/자기반증 판정 요약
```

`pip install -e .` 하면 `popper` 명령으로도 쓸 수 있다 (레포 체크아웃 기준 -
픽스처와 봉인 문서가 레포 루트에 있다).

### Claude Code 플러그인으로

```bash
claude --plugin-dir /path/to/popper
```

이후 `/popper:popper` 스킬로 세션을 연다. 재심 대기 배너가 있으면 스킬이
먼저 알려준다.

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

## 산출물

세션 완주 시 `~/.claude/popper/`에 착지한다.

- `POPPER.md` - 8축 전부의 실행 가능한 룰만 (인식론 주석 0줄)
- `manifest.json` - 룰별 corroboration 등급, value_source, content hash,
  last_review, 재심 큐, 충돌 리포트
- `settings.popper.json` - 제안 파일 (라이브 settings.json에 자동 병합하지 않는다)
- `sessions/*.jsonl` - append-only 이벤트 스트림 (단일 진실원)

활성화와 롤백:

```bash
python3 -m popper enable --grant    # CLAUDE.md 끝에 @import 한 줄 추가 (허가 기록)
python3 -m popper rollback          # 그 한 줄만 제거 - 전체 롤백 지점
```

착지된 파일을 수기로 편집하면 다음 착지가 **차단**된다 (content hash 불일치 =
최강 strike 신호, silent overwrite 금지). 의도한 편집이면:

```bash
python3 -m popper land --acknowledge-mismatch
```

## 자기반증

이 도구의 핵심 추측("긋기만으로 설정이 수렴한다")도 반증 대상이다.
검증 세션 누적 + 봉인 정답지 5분류 채점으로 `refutation_condition_met`은
기계(fold)가 방출하고, 확정은 인간의 `refutation_acknowledged`로만 게이트된다.

```bash
python3 -m popper status                     # 판정 fold 현황
python3 -m popper acknowledge --actor <이름>  # 조건 성립 후 인간 확정
```

## 개발

```bash
python3 -m pytest tests/ -q    # 전체 스위트
```

모듈 구성: `events`(strike-only 스키마) / `counter`(6,561 fold) /
`recovery`(undo·revive·모순) / `compiler`(룰 + manifest) / `writer`(소유권 분리)
/ `conflict`(수기 룰 충돌) / `session`(프로파일 봉인) / `judgment`(자기반증 fold)
/ `recheck`(4막 재심) / `scoring`(5분류 채점) / `fixtures`(고정 픽스처 렌더) /
`store`(append-only JSONL) / `web`(콜드 오픈 UI) / `cli`(진입점).
