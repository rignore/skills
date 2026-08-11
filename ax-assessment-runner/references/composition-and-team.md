# 팀 운영과 기존 스킬 조합 규약

## 기본 모델

역할 수를 참가자 수와 동일하게 만들지 않는다. 한 사람은 여러 역할을 맡을 수 있고, 한 역할에 여러 agent를 붙일 수 있다. 사람에게는 artifact의 최종 책임만 하나씩 배정한다.

공용 Source of Truth:

```text
hackathon/
├── competition-profile.md
├── team-operating-model.md
├── decision-log.md
├── evidence-register.md
├── integration-contract.md
├── judge-pack.md
├── submission-ledger.md
└── HACKATHON-HANDOFF.md
```

프로젝트에 기존 경로가 있으면 새 파일을 만들지 말고 매핑만 기록한다.

## 인원별 권장 배치

| 인원 | 기본 workstream | 운영 핵심 |
|---:|---|---|
| 1 | Product/Research + Build + Validation/Release | agent를 병렬 Scout/Judge로 쓰되 사람은 Problem/Taste/Submit을 소유 |
| 2 | A: Product/Research/Evidence, B: Tech/Integration/Release | 둘 다 Taste/Judge review 참여, 제출 owner는 한 명 |
| 3 | A: Product/Domain, B: AI/Data/Backend, C: Frontend/UX/Integration | C가 통합하되 A가 evidence, B가 model verification 소유 |
| 4 | A: Product/Research, B: AI/Data, C: App/Platform, D: Validation/Demo/Release | D가 독립 Judge 입력·submission ledger, C가 integration contract 소유 |

역량이 다르면 역할명을 고집하지 말고 DRI를 교체한다. 다만 다음 ownership은 중복시키지 않는다.

- 최종 Problem Decision
- integration contract와 merge order
- evidence claim 승인
- submission form과 receipt

## 두 번의 배치

### Problem Lock 전

- Competition/rules
- Domain/user research
- Problem candidate exploration
- Feasibility/data/API spike

### Problem Lock 후

- Product/PRD and evidence
- AI/data/backend
- Frontend/service integration
- Verification/demo/submission

Problem Lock에서 workstream을 다시 배치한다. 조사 담당자가 반드시 같은 기능을 구현할 필요는 없다.

## 병렬화 규칙

1. work package마다 Human DRI, agent/skill, 입력, 출력, file ownership, dependency, deadline을 기록한다.
2. 같은 파일을 둘 이상이 동시에 수정하지 않는다.
3. 공유 schema/API/UX flow를 `integration-contract.md`에 먼저 잠근다.
4. branch/worktree 전략은 기존 repository 규칙을 따른다.
5. 각 package는 self-report가 아니라 verify command와 evidence를 반환한다.
6. Integration DRI가 합친 뒤 전체 type/test/build/demo를 재실행한다.
7. 판단 충돌은 다수결로 숨기지 않고 decision-log에 owner와 근거를 남긴다.

## Sync cadence

절대 시간이 아니라 남은 시간 비율로 운영한다.

- 시작: Competition Lock + ownership 확정
- 30%: Problem Lock + team replan
- 40%: integration contract lock
- 70%: feature freeze + 전원 verification 전환
- 85%: submission freeze + demo rehearsal
- 종료 전: receipt + merged handoff

다일 대회에서는 매일 종료 시 15분 통합 sync를 추가한다. 상태 보고는 `done / evidence / blocker / next` 네 항목만 사용한다.

## 전문 스킬 routing

### prd-flow

다음 조건이면 사용한다.

- 정형 PRD가 없고 문제·페르소나·가치·solution scope를 팀이 함께 수렴해야 한다.
- 다일 일정이라 Gate 산출물을 재사용할 시간이 있다.
- 기획서와 구현 간 traceability가 중요하다.

매핑:

```text
AX Context/Problem Discovery
→ prd-flow domain-research + Gate 1
→ AX Human Problem Lock
→ prd-flow Gate 1.5 + Gate 2
→ AX Build Contract는 full-prd 링크로 대체
```

AX와 prd-flow가 문제 정의 문서를 각각 만들지 않는다. `prd-flow/{slug}/context.json`과 Gate 산출물이 제품 정의 SoT다.

### ai-dlc

Full PRD가 확정되고 남은 시간이 lifecycle overhead를 감당할 때 사용한다. ai-dlc의 설계·code·test 산출물을 기술 SoT로 삼고 AX는 timer, team ownership, evidence, judge, submission을 계속 관리한다. 짧은 대회에서는 필요한 P0 package만 직접 구현하는 편이 안전하다.

### loop-harness

다음이 모두 있을 때만 사용한다.

- 수정 가능한 solver 대상
- 고정된 dataset/condition
- 결정론 또는 재현 가능한 evaluator
- 반복할 time budget

예: fraud detection recall/false positive, response latency, extraction accuracy. `혁신성`, `기업 선호`, `Taste`는 loop-harness 대상이 아니다.

### ux-researcher / codex-delegate

- ux-researcher: 대표 data가 있는 통합 MVP를 검토할 때 사용한다.
- codex-delegate: file ownership이 독립된 work package의 실행에만 사용한다.

## 통합 실패 방지

- 한 스킬의 출력이 다음 스킬 입력 계약을 만족하는지 DRI가 확인한다.
- 서로 다른 status/handoff를 병렬 운영하지 않는다. 공용 ledger에서 링크한다.
- 전문 스킬의 gate를 통과했어도 Competition Lock과 Submission Ledger 위반이면 AX에서 FAIL이다.
- 팀원의 로컬 성공을 통합 성공으로 간주하지 않는다.
