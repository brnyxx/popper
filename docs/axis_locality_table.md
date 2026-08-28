# 8축 국소성 판정표 (locality decision table)

catalog_version: v1
status: 픽스처 저작 이전에 확정. 이 표가 fixtures/ 저작 형태를 결정한다.

## 판정 기준

- **국소(local) = 슬롯화**: 축의 값 차이가 트랜스크립트의 *특정 지점 한 곳*에서만 관측된다.
  같은 skeleton을 공유하고 그 축의 슬롯 조각만 3변형으로 교체하면 대비가 성립한다.
  배경 7축은 채굴 최빈값(카탈로그 튜플 index 0)으로 고정된다.
- **전역(global) = 통짜**: 축의 값 차이가 문장 전체에 번져서 어느 한 조각으로 오려낼 수 없다.
  슬롯 교체로는 대비가 성립하지 않으므로 값마다 트랜스크립트 3본을 통째로 저작한다.

판별 질문: "이 축의 값을 바꿀 때, 바뀌는 문자 구간이 연속된 한 덩어리인가?"
아니오이면 전역이다.

## 판정표

| # | axis | 한국어 | 값 3종 (index 0 = 채굴 최빈값) | 판정 | 대비가 걸리는 지점 | 근거 |
|---|------|--------|--------------------------------|------|--------------------|------|
| 1 | `response_language` | 응답언어 | korean / english / mirror_user | **전역(통짜)** | 응답 전체 | 값이 바뀌면 모든 문장이 다시 쓰인다. 잘라낼 조각이 없다 |
| 2 | `verbosity` | 장황함 | terse / balanced / explanatory | **전역(통짜)** | 응답 전체 | 값 차이가 조각 개수와 문장 길이 자체를 바꾼다. 슬롯 경계가 값마다 달라진다 |
| 3 | `autonomy` | 자율성 | ask_first / propose_then_act / act_then_report | 국소(슬롯) | 착수 선언 1문장 | 나머지 본문은 동일하고 "물을지/알리고 할지/하고 보고할지"만 갈린다 |
| 4 | `commit_style` | 커밋스타일 | conventional / narrative / no_auto_commit | 국소(슬롯) | 커밋 줄 | 커밋 제목 한 줄에 국한된다 |
| 5 | `test_discipline` | 테스트규율 | test_first / test_after / on_request | 국소(슬롯) | 테스트 언급 1문장 | 수정 본문은 그대로이고 테스트를 언제 썼는지만 갈린다 |
| 6 | `comment_doc` | 주석문서화 | minimal / docstring_only / thorough | 국소(슬롯) | 패치 코드블록 | 코드블록 한 덩어리 안에서만 변한다 |
| 7 | `error_behavior` | 에러시행동 | stop_and_report / retry_then_report / self_heal | 국소(슬롯) | 예외 처리 서술 1문장 | 실패 시 행동 문장 하나에 국한된다 |
| 8 | `scope_adherence` | 범위준수 | strict / adjacent_fix_ok / proactive | 국소(슬롯) | 범위 선언 1문장 | 인접 수정을 건드렸는지 한 문장에 국한된다 |

## 귀결

- 전역 2축 (`response_language`, `verbosity`) -> `fixtures/global_wholes.json`, 축당 통짜 3본.
- 국소 6축 -> `fixtures/scene_skeleton.json` 공통 skeleton 1본 + `fixtures/axis_slots.json` 축당 대비 슬롯 3변형.
- 저작 상한 준수: 국소 6축 x 3변형 = 18조각(짧은 문장/코드블록) + 전역 2축 x 3본 = 6본.
  시나리오 1개(S_scn=1) 기준 LLM 저작 호출 10회 내, 재생성 버퍼 포함 20회 내에 든다.
- 첫 페어는 `autonomy`(자율성) 축으로 고정한다. 국소 축이므로 콜드 오픈 10초 계약을 해치지 않는다.

## 이 표가 없으면 깨지는 것

전역 축을 슬롯으로 잘못 저작하면 좌우가 같은 skeleton을 공유하게 되어
"응답언어를 바꿨는데 문장 구조는 그대로"인 비현실 페어가 만들어진다.
그 페어에서의 긋기는 축에 귀속되지 못하고 판별력을 잃는다.
