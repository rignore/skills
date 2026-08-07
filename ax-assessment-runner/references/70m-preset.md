# 70분 PRD 구현 평가 프리셋

총 시간이 60~90분인 실무형 구현 평가에서 사용한다. 정확히 70분이면 아래 절대 시간을 적용하고, 다른 시간이면 같은 비율로 환산한다.

## 시간 배분

| 구간 | 70분 기준 | 목표 | 종료 조건 |
|---|---:|---|---|
| Assessment Setup + Context | 0~7분 | PRD·repo·규칙 파악 | Context Pack 완료 |
| Problem Gate | 7~12분 | 핵심 문제·P0·성공 기준 확정 | Scope Lock |
| Scaffold | 12~16분 | 3~4 task 구성 | 실행 계획 고정 |
| Core implementation | 16~38분 | P0 end-to-end slice | 핵심 happy path 연결 |
| Engineering Gate | 38~48분 | type/test/build + blocker 수정 | 가능한 기계 검증 통과 |
| Stabilize | 48~55분 | P0 누락·blocker 해결 | 제출 가능한 상태 |
| User Gate / Taste | 55~63분 | 실제 핵심 flow 주행 | blocker/high severity 제거 |
| Final Evidence | 63~67분 | 요구사항 추적 + regression | PASS/PARTIAL/CUT 근거 확보 |
| Freeze | 67~70분 | 제출 안정화 | 새 변경 없이 제출 |

## Hard Cut-off

### T+12분 — Scope Lock

이 시점까지 확정해야 한다.

- 핵심 사용자/JTBD
- P0
- CUT
- 성공 기준

아직 애매한 것이 남아도 구현을 막지 않는 항목은 assumption으로 기록하고 진행한다.

### T+38분 — Feature Pause

무조건 기능 추가를 잠시 중단하고 첫 Engineering Gate를 실행한다.

P0가 아직 연결되지 않았다면:

1. P1 전부 제거
2. P0 중 core journey 비필수 항목 제거
3. happy path를 먼저 연결
4. architecture polish 금지

### T+48분 — P0 Only

이 이후 새 P1은 기본적으로 금지한다.

P1을 추가할 수 있는 조건은 모두 충족될 때뿐이다.

- 현재 P0 type/compile PASS
- 핵심 tests PASS
- production build PASS 또는 build가 존재하지 않는 stack임을 확인
- core journey가 실제로 동작
- 남은 시간이 충분함

하나라도 만족하지 않으면 P0 안정화에 사용한다.

### T+55분 — User Gate

코드 정적 확인을 멈추고 실제 사용 흐름을 검증한다.

UI가 있으면 화면을 열어 핵심 journey를 처음부터 끝까지 실행한다. 자동 브라우저가 없으면 가능한 수단으로 직접 확인하고, E2E 미검증을 숨기지 않는다.

### T+63분 — Scope Freeze

새 기능, dependency, 대규모 refactor를 금지한다.

허용:

- blocker 수정
- regression 수정
- 제출/실행을 막는 설정 수정
- requirement traceability 확인

금지:

- 새로운 P1
- 디자인 리뉴얼
- "코드가 더 예뻐지도록" 하는 refactor
- framework/package 교체

### T+67분 — Code Freeze

가능하면 코드 변경을 멈춘다.

최종 확인:

1. 마지막 변경 후 검증을 다시 실행했는가
2. 실행 방법이 유효한가
3. 핵심 화면/API가 열리는가
4. 미완료 요구사항을 표시했는가
5. 제출 대상이 실제 저장됐는가

## Rescue Matrix

| 시점 | 상태 | 행동 |
|---|---|---|
| 25분 | 아직 기본 화면/핵심 API도 없음 | 구조 확장 중단, 최소 happy path 직결 |
| 38분 | P0 미완성 | P1/CUT 전부 동결, 첫 검증 시작 |
| 48분 | build/test FAIL | 새 기능 금지, 가장 직접적인 blocker만 수정 |
| 55분 | 앱은 빌드되나 flow 미검증 | 브라우저/API 주행으로 전환 |
| 63분 | 핵심 flow FAIL | UI polish·부가기능 롤백/비활성화해 core flow 복구 |
| 67분 | 부분 기능만 안정적 | 안정적인 부분을 보존하고 limitation 명시 |

## 시간 사용 원칙

**검증 시간을 기능 시간에 양보하지 않는다.**

시간이 부족하면 순서대로 줄인다.

1. P1
2. cosmetic polish
3. 비핵심 error/edge case
4. 내부 architecture 개선

다음은 마지막까지 유지한다.

1. 핵심 P0 happy path
2. type/compile 또는 동등한 기본 정합성 검증
3. 핵심 business rule 검증
4. 실제 실행/주행 증거
5. 미완료 상태의 정직한 보고
