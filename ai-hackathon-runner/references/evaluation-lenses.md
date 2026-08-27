# 해커톤 Winning Pattern, Problem Gate, Mock Judge 렌즈

공식 rubric과 대회 규칙이 항상 우선한다. 이 문서는 공식 점수를 예측하는 모델이 아니라, 제한 시간 안에 **수상 가능성을 깎는 병목을 찾고 교정하기 위한 휴리스틱**이다.

```text
수상 가능성 ≈ 문제 적합성 × 작동 증거 × 차별성 × 전달력 × 신뢰성
```

곱셈식은 통계식이 아니다. 한 축이 매우 낮으면 다른 축의 강점이 전체 경쟁력을 충분히 보상하지 못한다는 운영 원칙을 표현한다.

---

## 1. 수상형 서비스의 공통 패턴

### 1) 문제의 크기보다 문제의 해상도가 높다

문제는 `누가 / 어떤 상황에서 / 무엇을 하려다 / 왜 실패하고 / 어떤 결과가 발생하는가`까지 내려간다.

약한 정의:

> 금융사기를 예방한다.

강한 정의:

> 의심 통화와 원격제어 앱 설치가 동시에 발생한 금융소비자를 송금 전에 식별하고, 대응 담당자가 개입 우선순위를 결정하게 한다.

Problem Candidate는 solution 이름이나 기술명이 아니라 **사용자 실패와 바뀌어야 할 상태**로 쓴다.

### 2) 기능 수보다 하나의 완결된 Golden Path가 있다

수상형 MVP는 다음 흐름이 실제로 닫혀 있다.

```text
Trigger/Input → Processing/Judgment → Understandable Result → User/Operator Action → Outcome
```

대시보드·챗봇·알림·리포트·마이페이지를 넓게 만드는 것보다 한 흐름을 끝까지 연결한다. 비핵심 기능은 mock 또는 Wizard-of-Oz로 처리할 수 있지만, 실제 구현과 simulation을 명확히 구분한다.

### 3) AI가 장식이 아니라 가치 생성의 원인이다

다음 질문에 답하지 못하면 AI 사용은 decorative일 가능성이 높다.

- AI는 어떤 입력을 받는가.
- 어떤 판단·변환·우선순위화를 수행하는가.
- 그 결과가 사용자의 다음 행동을 어떻게 바꾸는가.
- rule/search/manual workflow 대비 무엇이 달라지는가.

강한 AI 역할의 예:

- 사람이 동시에 처리하기 어려운 비정형 신호 결합
- 대량 사건의 우선순위 결정
- 개인/상황 맥락에 따른 서로 다른 결과 생성
- 판단 근거·불확실성·추가 확인 항목 제시
- 사람이 수행하던 다단계 판단 순서 자체를 재구성

### 4) MVP는 작은 제품이 아니라 핵심 가설의 작동 증거다

MVP의 목적은 기능 완성도가 아니라 다음을 증명하는 것이다.

1. 대표 입력이 들어온다.
2. 핵심 로직/AI가 처리한다.
3. 사용자가 이해할 수 있는 결과가 나온다.
4. 결과가 실제 후속 행동으로 이어진다.

로드맵을 현재 구현처럼 설명하지 않는다. `WORKING / SIMULATED / PLANNED / NOT VERIFIED`를 분리한다.

### 5) 복잡한 기술을 익숙한 정신모형으로 번역한다

심사위원이 기억해야 하는 것은 내부 아키텍처보다 **결과 단위**다.

예:

- 위험도
- 개입 우선순위
- 예상 손실
- 지금 해야 할 행동
- 판단 근거 3개
- 추가 확인이 필요한 정보
- 자동 실행 가능 여부
- 담당자에게 넘길 증거 패키지

기술 설명은 사용 가치가 이해된 뒤에 배치한다.

### 6) 차별성은 새 기능보다 메커니즘의 변화다

기존 대안과의 차이를 다음 축에서 찾는다.

| Mechanism axis | 질문 |
|---|---|
| Timing | 사후 대응을 사전 개입으로 바꾸는가 |
| Information | 기존에 분리됐던 신호/맥락을 결합하는가 |
| Actor | 사용자가 직접 요청하던 것을 시스템이 먼저 탐지하는가 |
| Action | 안내에서 실제 다음 행동/실행으로 연결하는가 |
| Accountability | 불투명한 자동결정을 검증 가능한 판단지원으로 바꾸는가 |
| Unit | 개별 사건 처리에서 우선순위·포트폴리오 판단으로 바꾸는가 |

`기능이 하나 더 있음`보다 `누가, 언제, 어떤 정보로, 어떤 행동을 하는지가 달라짐`이 강한 차별성이다.

### 7) 실제 도입을 막는 장애물을 알고 있다

특히 금융·의료·공공 영역은 prototype이 작동하는 것만으로 부족하다.

최소한 다음을 설명할 수 있어야 한다.

- 필요한 data는 누가 보유하는가.
- 어떤 권한·동의·연동으로 접근하는가.
- 개인정보/민감정보를 어떻게 최소화하는가.
- 오탐·실패 시 누가 검토하고 어떻게 복구하는가.
- 자동 실행과 Human approval의 경계는 어디인가.
- 기존 workflow/system 어디에 들어가는가.
- 운영 주체와 비용/latency의 주요 제약은 무엇인가.

모든 것을 구현할 필요는 없지만, **MVP 경계와 실제 도입 경계**를 혼동하지 않는다.

### 8) 심사위원이 평가하기 쉬운 구조다

첫 30초 안에 심사위원이 다음 문장을 완성할 수 있어야 한다.

> 이 서비스는 `[누구]`의 `[어떤 상황의 문제]`를 `[핵심 메커니즘]`으로 해결해 `[기존 대비 변화]`를 만든다.

심사위원은 두 번째 사용자다. 실제 사용자 가치를 심사 기준의 언어로 번역하되, 심사위원 개인 취향에 맞추기 위해 문제 자체를 왜곡하지 않는다.

---

## 2. 반복 수상자의 운영 방식

### A. 아이디어보다 경기 규칙을 먼저 역설계한다

Competition Lock에서 공지·rubric·제출 형식만 수집하지 말고 **심사 계약(Judging Contract)**을 만든다.

```markdown
### Judging Contract
- Organizer/sponsor가 이 대회를 연 이유:
- 기대하는 사용자/산업 상태 변화:
- 공식 심사 항목과 weight:
- 반드시 보여줘야 할 evidence:
- 실격/감점 위험:
- 심사위원이 30초 뒤 기억해야 할 한 문장:
```

### B. 첫 아이디어에 몰입하지 않고 후보군을 만든다

아이디어 생성보다 **아이디어 폐기 능력**을 중시한다. 여러 Problem Candidate를 동일 schema로 비교하고, 다음 항목에서 약한 후보는 구현 전에 버린다.

- 실제 문제와 사용자 명확성
- 대회의 목적/스폰서 적합성
- data/access 가능성
- 제한 시간 내 검증 가능성
- AI 필요성
- 메커니즘 수준 차별성
- 데모 명료성
- 도입/안전 리스크
- 한 문장 기억성

### C. Problem Space와 Solution Space를 분리한다

금지 패턴:

```text
AI agent를 만들자 → 쓸 곳을 찾자 → 문제를 붙이자
```

권장 패턴:

```text
문제/사용자 탐색 → 실패 지점 수렴 → 필요한 판단/행동 정의
→ 여러 해결 방식 탐색 → 가장 작은 검증 가능한 mechanism 선택
```

### D. 개발 전에 데모를 먼저 설계한다 — Demo-Driven Development

Build Contract를 쓰기 전에 60~120초 데모를 먼저 글로 쓴다.

```markdown
### Demo Contract
- Trigger:
- User/operator context:
- Input shown:
- Core judgment/transformation:
- Result shown:
- Why this result matters:
- Next action:
- Observable outcome:
- What is actually implemented:
- What is simulated:
- Fallback if live dependency fails:
```

그 데모를 성립시키는 기능만 P0로 연다. 데모와 무관한 P1 기능은 P0가 안정적으로 닫히기 전 구현하지 않는다.

### E. 수평 확장보다 수직 slice를 먼저 닫는다

약한 MVP:

```text
로그인 일부 + 대시보드 일부 + AI notebook + 알림 UI + 미연결 API
```

강한 MVP:

```text
대표 입력 1개 → 핵심 판단 1개 → 이해 가능한 결과 1개 → 후속 행동 1개
```

작은 범위라도 end-to-end로 작동하는 것을 우선한다.

### F. 각 주장에 대응하는 증거를 설계한다

Build Contract와 발표 초안에 **Claim → Evidence Map**을 만든다.

| Claim | Required evidence | Artifact / source | Status |
|---|---|---|---|
| 실제 문제가 크다 | 통계·사건·인터뷰·workflow evidence |  |  |
| 기존 방식이 실패한다 | baseline·현재 프로세스·gap |  |  |
| AI가 필요하다 | 비AI baseline 또는 복합판단 근거 |  |  |
| 실제로 작동한다 | live demo·test·log·URL |  |  |
| 더 나은 결과를 낸다 | before/after·comparison |  |  |
| 도입 가능하다 | data flow·owner·integration |  |  |
| 안전하다 | privacy·HITL·failure handling |  |  |
| 확장 가능하다 | 주요 dependency와 확장 구조 |  |  |

증거가 없는 주장은 삭제·완화하거나 `ASSUMPTION / NOT VERIFIED`로 표시한다.

### G. 발표와 제출물을 별도 제품으로 취급한다

기획서·MVP·기능명세·영상·deck이 모두 동일한 서비스 약속을 증명해야 한다.

권장 전달 순서:

```text
사용자/사건 → 기존 실패 → 개입 순간 → 실제 데모
→ AI/기술이 맡는 판단 → 기존 대비 mechanism delta
→ evidence → 도입/안전 경계 → 기억할 한 문장
```

아키텍처부터 시작하지 않는다. 가치와 사용자 변화가 이해된 뒤 기술 구조를 보여준다.

### H. 아이디어가 아니라 실행 시스템을 재사용한다

반복 대회에서 재사용할 것은 다음이다.

- app scaffold / deployment pipeline
- auth / DB / upload / LLM / RAG / eval modules
- mock data generator
- architecture diagram template
- Demo Contract
- Claim → Evidence Map
- privacy/safety checklist
- judge question set
- submission checklist
- retrospective/handoff format

과거 제품에 문제 이름만 바꿔 붙이는 것은 금지한다. **프로세스와 인프라는 재사용하되, 문제와 해결 메커니즘은 다시 검증한다.**

---

## 3. Problem Gate

Problem Gate는 아이디어의 매력도를 묻는 단계가 아니라, **해커톤 안에서 증명 가능한 승부 가설인지**를 판정하는 단계다.

1. **Context** — 사용자·workflow·기업·도메인 제약이 source와 함께 설명되는가.
2. **Problem Resolution** — `누가/언제/무엇을 하다/왜 실패/무슨 결과`가 구체적인가.
3. **Evidence** — pain, 대안의 결함, 빈도/비용에 1차 또는 공식 근거가 있는가.
4. **Existing Alternative Gap** — 기존 제품/업무 방식이 실패하는 지점이 명시됐는가.
5. **Sponsor Fit** — 기업 logo가 아니라 실제 asset/product/strategy 연결이 있는가.
6. **AI Necessity** — AI를 제거하면 핵심 가치가 의미 있게 약해지는가.
7. **Mechanism Delta** — timing/information/actor/action/accountability/unit 중 구조적 변화가 있는가.
8. **Testability** — 제한 시간 안에 핵심 가설을 반증할 관찰이 있는가.
9. **Feasibility** — team/time/data/API 안에서 Golden Path를 실제로 닫을 수 있는가.
10. **Demo Clarity** — 60~120초 안에 before/after와 후속 행동을 보여줄 수 있는가.
11. **Trust/Deployability** — privacy/safety/operator/integration 경계를 설명할 수 있는가.
12. **Memorability** — 심사위원이 30초 뒤 한 문장으로 설명할 수 있는가.
13. **Human Judgment** — 복수 후보와 반론을 본 뒤 사람이 선택·trade-off를 확정했는가.

하나라도 치명적인 NO면 구현량으로 덮지 않는다. 특히 `Problem Resolution / Testability / Golden Path / Demo Clarity`가 낮으면 scope를 줄이거나 후보를 교체한다.

---

## 4. Winning Bottleneck Check

공식 rubric과 별개로 다음 5축을 병목 탐지에 사용한다.

| Axis | Judge question | Weak signal | Strong evidence |
|---|---|---|---|
| Problem fit | 왜 이 문제·사용자·지금인가 | 추상적 시장 문제 | 구체 workflow + pain evidence |
| Working proof | 실제로 핵심 흐름이 작동하는가 | mock 화면/미연결 기능 | end-to-end slice + test/log |
| Differentiation | 기존 대비 무엇이 구조적으로 달라지는가 | 기능 하나 추가 | mechanism delta + baseline |
| Communication | 짧은 시간에 가치가 이해되는가 | 기술/기능 나열 | 30초 pitch + Demo Contract |
| Trust | 실제 적용 경계와 실패를 알고 있는가 | 과장/모호한 데이터 | provenance + HITL + risk boundary |

한 축이 매우 낮으면 평균 점수로 감추지 않는다. 가장 낮은 축을 먼저 교정한다.

---

## 5. Two-way Mock Judge

문제 후보와 최종 제출물 모두 두 경로로 독립 심사한다.

- **AI Judge**: 공식 weight를 반영한 정량 rubric, 형식, evidence traceability, 실격 조건, Claim → Evidence completeness를 판정한다.
- **Persona Judge**: 기업 담당자 인터뷰·공식 전략·직무 맥락을 기반으로 현업 중요도, 적용성, 첫인상, 기억성, Taste를 판정한다. 실제 인물의 발언을 창작하지 않고 제공 근거에서 persona를 만든다.

각 판정은 `score / evidence / confidence / fatal gap / next test`를 반환한다. 합산 점수만 남기지 말고 disagreement를 보존한다.

### 30-second Memory Test

Persona Judge는 제출물을 본 뒤 다음 네 항목을 **자료를 다시 보지 않고** 재진술한다.

1. primary user
2. 실패 상황/problem
3. 핵심 mechanism
4. 기존 대비 변화/result

2개 이상 재진술하지 못하면 Clarity/Taste를 PASS로 처리하지 않는다.

---

## 6. 제출물 rubric

| Lens | Judge question | 강한 증거 |
|---|---|---|
| Relevance | 왜 이 사용자·기업·지금의 문제인가 | Context Pack, source, workflow |
| Impact | 해결 시 무엇이 얼마나 달라지는가 | baseline과 before/after |
| Innovation | 대안 대비 구조적 차이가 무엇인가 | mechanism comparison |
| AI Necessity | AI가 핵심 가치에 필수인가 | input→judgment→action trace, non-AI baseline |
| Feasibility | 실제 data·stack·비용으로 가능한가 | working slice, latency/cost |
| Execution | 핵심 flow가 안정적으로 닫혔는가 | test/build/demo log |
| Validation | Builder의 주장 외 검증이 있는가 | task observation, feedback, experiment |
| Clarity/Taste | 짧은 시간에 문제→해결→증거가 이해되는가 | Demo Contract, rehearsed demo, concise pitch |
| Trust/Deployability | 실제 운영·권한·실패 경계를 아는가 | data flow, operator, HITL, failure plan |
| Scalability | prototype 이후의 가장 큰 제약을 아는가 | dependency/risk plan |
| Compliance | 규칙·IP·privacy·safety를 지켰는가 | checklist와 provenance |

---

## 7. 자동 반려 / Hard Fail 후보

- 제출 요건 또는 eligibility 위반
- mock/sample 결과를 실제 성과로 표현
- simulation/planned 기능을 working으로 표현
- 실행하지 않은 test/E2E를 PASS로 표기
- source 없는 시장·사용자·기업 의도 주장
- prototype이 핵심 사용자 Golden Path를 완료하지 못함
- AI가 핵심 가치와 연결되지 않은 decorative integration
- 기존 대안 대비 차이를 설명하지 못함
- 심사 환경에서 접근 불가능한 link/credential
- 라이선스·개인정보·AI 사용 고지 누락
- 치명적 privacy/safety risk를 숨김

---

## 8. Judge 규율

- 모호하면 PASS가 아니라 gap으로 판정한다.
- Builder의 노력, 코드량, agent 수, 기술 복잡도는 그 자체로 근거가 아니다.
- rubric별로 artifact 위치와 verification을 인용한다.
- 공식 weight가 있으면 그 순서로 fix를 정한다.
- 공식 rubric이 모호하면 `Winning Bottleneck Check`의 최저 축을 먼저 고친다.
- 새 기능보다 unproven claim, demo blocker, 실격 위험을 먼저 교정한다.
- 문제 정의 단계부터 같은 rubric을 적용한다. 구현 품질이 문제 적합성의 낮은 점수를 가릴 수 없다.
- 기능 breadth보다 end-to-end Golden Path를 우선한다.
- `AI를 많이 사용함`이 아니라 `AI가 사용자의 판단/행동을 어떻게 바꿈`을 평가한다.
- milestone/commit별로 영향받은 항목만 빠르게 재심사하고, 제출 전 전체 심사를 수행한다.
- 반복 횟수를 품질로 착각하지 않는다. 종료 조건은 `hard fail 0 + critical gap 0 + Human Taste 승인 + Golden Path 안정 재현`이다.

---

## 9. 반복 수상형 실행 루프

전체 Runner에서 다음 루프를 보존한다.

```text
Competition/Judging Contract
→ Problem candidates
→ Problem Gate
→ Human Problem Lock
→ Demo Contract
→ Claim → Evidence Map
→ Vertical Golden Path
→ Engineering/Field Evidence
→ 30-second Memory Test
→ Two-way Mock Judge
→ Lowest-bottleneck fix
→ Submission Freeze
→ Retrospective/Handoff
```

핵심은 더 큰 제품을 만드는 것이 아니라, **올바른 문제를 선택하고, 가장 작은 작동 증거를 만들고, 차별적 메커니즘을 짧게 전달하며, 실제 도입 경계를 숨기지 않는 것**이다.
