# AX Hackathon Runner — Manual Fallback Prompt

> Skill 자동 로딩이 불가능한 환경에서만 사용한다.

```text
이번 작업은 AX 인재전쟁/기업 과제형 AI 해커톤이다. 목표는 기능 수가 아니라 근거 있는 문제 선택과 검증 가능한 사용자 변화를 제출하는 것이다.

Context → Problem Definition → Human Judgment → Scaffolding → Build → Verification → Evidence → Taste → Mock Judge → Submit → Handoff 순서로 진행하라.

대회별 차이는 competition profile로 고정하고, 참가자가 2명 이상이면 team operating model에서 workstream·artifact별 Human DRI와 Integration DRI를 먼저 배정하라. 동일 artifact는 한 명과 한 스킬만 Source of Truth로 소유한다.

1. 본선 진출/수상 목표에서 역산하라. 공식 공지·FAQ·트랙/기업 과제·rubric·제출 폼 원문에서 deadline/timezone, 참가 자격, 허용·금지 도구와 data, 필수 산출물, 심사 기준, IP/privacy 규칙, 제출 방식을 추출하라. 미확인은 UNKNOWN으로 남겨라.
2. 문제·기업/트랙·도메인·delivery 맥락을 조사하라. 기업 담당자 인터뷰 영상, 공식 IR/문서/기술 블로그, 실제 수치를 우선하고 사실/관계자 의견/가정/unknown과 source·시점을 분리하라. 남은 공백 중 사람이 답해야 할 것만 최대 3개 질문으로 인터뷰하라. 각 질문에 왜 필요한지와 영향받는 결정을 써라.
3. 트랙/기업이 여러 개면 같은 schema와 시간 상한으로 독립 병렬 탐색하라. 각 트랙에서 최소 2개, 필요하면 전체 12~20개의 Problem Candidate를 만들고 Scout별 상위 2개만 중앙 비교하라. 사용자 pain·근거·기업 fit·검증 가능성·실현 가능성·차별성·demo 명료성·위험으로 비교하라.
4. 문제 후보부터 AI Judge(공식 rubric·정량·실격)와 Persona Judge(기업 실무자 관점·현업성·첫인상·Taste)가 서로의 결과를 보지 않고 평가하게 하라. disagreement를 보존하라. AI가 최고 점수 후보를 자동 선택하지 말고 상위 2~3개와 반론을 보여준 뒤 사람이 트랙, problem, core hypothesis, success/failure criteria, accepted trade-off를 확정하게 하라.
5. 확정 후 Primary journey, P0/P1/CUT, Evidence Plan, demo story, dependency fallback을 Build Contract로 만들고 3~6개 task로 쪼개라. 병렬 구현은 파일/module ownership이 겹치지 않을 때만 한다.
   정형 PRD가 없고 팀 협업이 필요하면 prd-flow를 사용해 문제·페르소나·가치·solution scope·Full PRD를 제품 정의 SoT로 삼아라. Full PRD 이후 ai-dlc를 기술 실행 SoT로 사용할 수 있다. 반복 가능한 기계 지표가 있으면 loop-harness를 적용하되 주관적 심사 점수는 최적화하지 마라.
6. Scope Lock 뒤에는 Implement → targeted check → minimal fix → re-run을 자율 수행하라. scope·architecture·안전/개인정보/비용 위험이 바뀔 때만 사람에게 다시 올려라.
7. 실제 type/compile, test, build, API/data smoke test를 실행하라. 미실행은 NOT VERIFIED다. 핵심 가설은 사용자 task, before/after, real/sample data, 인터뷰/관찰 중 적합한 방법으로 실증하고 표본·환경 한계를 기록하라.
8. 사람이 실제 flow를 주행해 첫 30초 이해도, 다음 행동, 상태·실패 표현, demo 안정성을 판정하게 하라.
9. 생성 맥락을 받지 않은 AI Judge와 Persona Judge가 공식 rubric, 제출물, prototype, evidence만으로 eligibility, rubric gap, unproven claims, demo risk, top 3 fixes, submit verdict를 독립 판정하게 하라. milestone/commit마다 영향받은 rubric을 재심사하고, hard fail 0 + critical gap 0 + Human Taste 승인까지 반복하라.
10. 남은 시간 30%에는 feature freeze, 15%에는 submission freeze, 8%에는 code freeze를 적용하라. 파일·링크·권한·분량·팀 정보·license·출처·AI 고지·privacy·clean run·fallback·deadline을 확인하라. receipt 없이는 제출 완료로 보지 마라.
11. 세션 종료 전 Competition Lock, 사람의 결정, P0 상태, evidence, 변경 파일, 실행법, 검증 결과, 제출 상태, 다음 3개 행동을 HACKATHON-HANDOFF.md에 남겨라.

시간이 부족하면 다른 후보 탐색 → P1 → polish → 비핵심 edge path 순으로 줄이고, 검증과 제출 buffer는 보존하라. mock을 real result로 말하거나, 테스트를 삭제해 PASS를 만들거나, 제출 직전 framework를 교체하지 마라.
```
