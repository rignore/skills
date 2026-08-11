# 해커톤 Problem Gate와 Mock Judge 렌즈

공식 rubric이 있으면 그것이 우선한다. 이 문서는 누락을 찾는 비공식 self-check이며 예상 점수로 주장하지 않는다.

## Problem Gate

1. **Context** — 사용자·workflow·기업·도메인 제약이 source와 함께 설명되는가.
2. **Problem Definition** — solution 이름이 아니라 반복되는 사용자 실패와 결과로 정의됐는가.
3. **Evidence** — pain, 대안의 결함, 빈도/비용에 1차 또는 공식 근거가 있는가.
4. **Human Judgment** — 복수 후보와 반론을 본 뒤 사람이 선택·trade-off를 확정했는가.
5. **Testability** — 제한 시간 안에 핵심 가설을 반증할 관찰이 있는가.
6. **Sponsor Fit** — 기업 logo가 아니라 실제 asset/product/strategy 연결이 있는가.

하나라도 NO면 구현량보다 해당 공백을 먼저 줄인다.

## Two-way Mock Judge

문제 후보와 최종 제출물 모두 두 경로로 독립 심사한다.

- **AI Judge**: 공식 weight를 반영한 정량 rubric, 형식, evidence traceability, 실격 조건을 판정한다.
- **Persona Judge**: 기업 담당자 인터뷰·공식 전략·직무 맥락을 기반으로 현업 중요도, 적용성, 첫인상, Taste를 판정한다. 실제 인물의 발언을 창작하지 않고 제공 근거에서 persona를 만든다.

각 판정은 `score / evidence / confidence / fatal gap / next test`를 반환한다. 합산 점수만 남기지 말고 disagreement를 보존한다.

## 제출물 rubric

| Lens | Judge question | 강한 증거 |
|---|---|---|
| Relevance | 왜 이 사용자·기업·지금의 문제인가 | Context Pack, source, workflow |
| Impact | 해결 시 무엇이 얼마나 달라지는가 | baseline과 before/after |
| Innovation | 대안 대비 구조적 차이가 무엇인가 | 비교표, unique mechanism |
| Feasibility | 실제 data·stack·비용으로 가능한가 | working slice, latency/cost |
| Execution | 핵심 flow가 안정적으로 닫혔는가 | test/build/demo log |
| Validation | 사용자가 아니라 Builder의 주장만 있는가 | task observation, feedback |
| Clarity/Taste | 짧은 시간에 문제→해결→증거가 이해되는가 | rehearsed demo, concise pitch |
| Scalability | prototype 이후의 가장 큰 제약을 아는가 | dependency/risk plan |
| Compliance | 규칙·IP·privacy·safety를 지켰는가 | checklist와 provenance |

## 자동 반려 후보

- 제출 요건 또는 eligibility 위반
- mock/sample 결과를 실제 성과로 표현
- 실행하지 않은 test/E2E를 PASS로 표기
- source 없는 시장·사용자·기업 의도 주장
- prototype이 핵심 사용자 flow를 완료하지 못함
- 심사 환경에서 접근 불가능한 link/credential
- 라이선스·개인정보·AI 사용 고지 누락

## Judge 규율

- 모호하면 PASS가 아니라 gap으로 판정한다.
- Builder의 노력과 코드량은 근거가 아니다.
- rubric별로 artifact 위치와 verification을 인용한다.
- 공식 weight가 있으면 그 순서로 fix를 정한다.
- 새 기능보다 unproven claim, demo blocker, 실격 위험을 먼저 교정한다.
- 문제 정의 단계부터 같은 rubric을 적용한다. 구현 품질이 문제 적합성의 낮은 점수를 가릴 수 없다.
- milestone/commit별로 영향받은 항목만 빠르게 재심사하고, 제출 전 전체 심사를 수행한다.
- 반복 횟수를 품질로 착각하지 않는다. 종료 조건은 hard fail 0, critical gap 0, Human Taste 승인이다.
