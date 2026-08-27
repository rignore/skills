---
name: ai-hackathon-runner
description: AI 활용 해커톤·프로토타입 대회·기업/공공/오픈 챌린지에서 공식 규칙과 주최사·도메인 맥락을 조사하고, 대회가 허용하는 규모의 팀이 하나 이상의 트랙에서 문제 후보를 탐색·검증·우선순위화한 뒤, 사람이 핵심 판단을 소유한 상태로 prototype을 구현·실증·심사·제출하도록 운영하는 상위 오케스트레이션 스킬. 사용자가 "AI 해커톤", "해커톤 준비", "해커톤 문제 정의", "해커톤 팀 구성", "해커톤 데모", "해커톤 제출", "prototype challenge", "hackathon runner"처럼 시간 제한 안에 문제 발굴부터 데모·제출까지 진행하려 할 때 사용한다. 대회별 차이는 competition profile template로 주입하며 prd-flow, ai-dlc, loop-harness, ux-researcher, codex-delegate를 단계별 실행 자산으로 조합할 수 있다.
---

# AI Hackathon Runner

해커톤의 목표는 기능 수가 아니라 **근거 있는 문제 선택과 검증 가능한 변화**다.

```text
Context → Problem Definition → Human Judgment → Scaffolding
→ Build → Verification → Evidence → Taste → Mock Judge → Submit → Handoff
```

## 운영 원칙

1. **Context before solution** — 문제·기업·도메인·심사·제출 맥락을 확인하기 전에 솔루션을 고정하지 않는다.
2. **Work backward from winning** — 본선 진출·수상·기업 채택이라는 목표에서 rubric, 실격 조건, 필요한 증거를 역산한다.
3. **Problem candidates, not first idea** — 첫 아이디어를 채택하지 않는다. 복수 후보를 독립 탐색하고 근거로 비교한다.
4. **Human owns judgment** — AI는 조사·후보·반론·구현을 맡고, 사람은 문제 선택·trade-off·scope·taste·최종 제출을 승인한다.
5. **Scaffold before scale** — Context Pack, Problem Card, Evidence Plan, task map을 먼저 고정한다. 긴 문서가 아니라 판단을 보존하는 최소 구조만 만든다.
6. **Evidence over plausibility** — 인터뷰·공개 데이터·관찰·실행 로그·테스트·실제 주행이 없는 주장은 `ASSUMPTION` 또는 `NOT VERIFIED`다.
7. **End-to-end before breadth** — 입력→처리→결과→사용자 행동까지 닫힌 한 흐름을 먼저 만든다.
8. **Taste after proof** — 기계 PASS 뒤에 메시지 명료성, 데모 이해도, 상호작용 품질을 사람이 판정한다.
9. **Time protects verification** — 시간이 줄면 기능을 자르고 검증·제출 시간을 보존한다.
10. **Handoff is state, not summary** — 세션이 바뀌어도 결정·증거·실행법·다음 행동을 재구성할 수 있게 남긴다.
11. **One artifact, one owner, one SoT** — 팀원과 스킬이 많아도 같은 산출물을 중복 생성하지 않는다. 각 artifact의 DRI와 Source of Truth를 하나로 고정한다.

## 역할과 루프

- **Human-IN-the-loop**: 트랙 선택, 문제·사용자 확정, P0, 성공 기준, 위험한 변경, 최종 제출.
- **Human-ON-the-loop**: Scope Lock 이후 탐색·구현·오류 수정·검증 재실행을 감독하되 사소한 선택마다 승인하지 않는다.
- **Scout**: 트랙/기업별 Context Pack과 문제 후보를 만든다. 가능하면 서로 독립된 agent/session으로 병렬 실행한다.
- **Builder**: 승인된 P0를 구현한다.
- **AI Judge**: 공식 rubric·정량 조건·실격 위험을 기계적으로 판정한다.
- **Persona Judge**: 기업 실무자/심사위원의 목적·현업성·첫인상·완성도 관점에서 판정한다.

같은 agent가 Builder와 Judge를 겸해야 한다면 컨텍스트를 새로 구성하고, 자기 설명이 아니라 제출물·증거만 입력으로 사용한다. AI Judge와 Persona Judge도 가능하면 서로의 판정을 보지 않고 먼저 독립 평가한다.

## Reference 적재

| 파일 | 읽는 시점 | 목적 |
|---|---|---|
| `references/context-and-problem.md` | Phase 1~2 | 조사 깊이, 후보 카드, 병렬 탐색·우선순위 규약 |
| `references/timebox-and-submission.md` | Phase 0 및 종료 20% | 비율 기반 시간 운영, 제출·실격 체크 |
| `references/evaluation-lenses.md` | Phase 2, 7 | 문제 선택·Mock Judge 렌즈 |
| `references/composition-and-team.md` | Phase 0, 4 | 대회 허용 팀 규모에 맞춘 운영과 기존 스킬 조합 규약 |

필요한 시점에만 읽는다.

## Competition Pack

대회별 차이를 SKILL 본문에 하드코딩하지 않는다. Phase 0에서 다음 템플릿을 프로젝트의 `hackathon/` 디렉토리로 복사해 채운다.

| Template | Project artifact | 용도 |
|---|---|---|
| `templates/competition-profile.md` | `hackathon/competition-profile.md` | 규칙·목표·도메인 lane·단계 override |
| `templates/team-operating-model.md` | `hackathon/team-operating-model.md` | 팀 규모별 역할·ownership·sync |
| `templates/judge-pack.md` | `hackathon/judge-pack.md` | AI/Persona Judge와 종료 조건 |
| `templates/submission-ledger.md` | `hackathon/submission-ledger.md` | 단계별 제출·실격·receipt |

특정 대회의 규정·날짜·URL을 스킬에 보존하지 않는다. 주최사가 공식 starter 문서나 양식을 제공하면 generic template의 대응 필드에 옮기고 원문 출처를 연결한다. 실행할 때마다 공식 원문을 다시 확인하고 `last_verified_at`을 갱신한다.

---

# Phase 0 — Competition Lock

대회 공지·공식 FAQ·트랙/기업 과제·rubric·제출 폼의 **원문**을 먼저 읽는다. 요약만으로 규칙을 대체하지 않고 추측으로 빈칸을 채우지 않는다. 목표 결과에서 역산해 어떤 evidence와 artifact가 최종 판정을 통과시켜야 하는지 정한다.

다음을 `Competition Lock`으로 고정한다.

```markdown
- Deadline / timezone:
- Track/company choices:
- Eligibility/team rules:
- Required deliverables and format:
- Allowed/prohibited tools, data, APIs:
- Judging criteria and weights:
- IP/privacy/open-source constraints:
- Submission channel and edit policy:
- Demo environment constraints:
- Unknowns requiring organizer confirmation:
```

`references/timebox-and-submission.md`에서 전체 시간에 맞는 비율을 적용한다. 규칙 미확인 사항은 `UNKNOWN`으로 남기고, 실격 가능성이 있으면 구현보다 먼저 해소한다.

이어서 `references/composition-and-team.md`를 읽고 참가 인원·역량·가용 시간을 기준으로 `team-operating-model.md`를 확정한다. 2명 이상이면 개인별 역할명보다 **workstream과 artifact ownership**을 먼저 배정한다.

---

# Phase 1 — Context Acquisition

`references/context-and-problem.md`를 읽고 다음 4개 층을 조사한다.

1. **Problem** — 누가, 어떤 상황에서, 어떤 job을 수행하다 무엇 때문에 실패하는가.
2. **Company/track** — 기업의 고객·제품·사업모델·전략·제공 자산·과제 의도.
3. **Domain** — workflow, 이해관계자, 규제·안전·데이터 제약, 현재 대안과 전환 비용.
4. **Delivery** — 팀 역량, 사용 가능한 data/API, 구현 시간, demo 환경, 제출 요구.

컨텍스트 공백을 agent가 먼저 찾게 한다. 답이 repository·공식 자료·웹에 없고 사람의 경험·선호·관계자 정보가 필요한 경우, agent는 사용자에게 최대 3개의 높은 레버리지 질문을 한 번에 묻는다. 질문마다 `왜 필요한가 / 답에 따라 무엇이 달라지는가`를 붙인다. 기업 담당자 인터뷰 영상·발언은 transcript/요약을 확보하되, 발언 시점과 화자를 보존하고 추론과 분리한다.

근거 우선순위:

```text
공식 대회/기업 자료 → 사용자·현업 1차 정보 → 공신력 있는 통계/논문
→ 제품·경쟁사 관찰 → 합리적 추론
```

각 주장에 source와 확인 시점을 남긴다. 외부 검색이 허용되지 않으면 제공 자료와 repository만 사용하고 공백을 명시한다.

출력은 트랙별 `Context Pack`이다.

```markdown
### Context Pack — [track/company]
- Target user / buyer / beneficiary:
- Job and current workflow:
- Pain evidence and frequency/severity:
- Existing alternatives and gap:
- Company/track fit:
- Available assets/data/API:
- Constraints and risks:
- Facts / assumptions / unknowns:
- Sources:
```

---

# Phase 2 — Parallel Problem Discovery

트랙이나 기업이 둘 이상이면 각 Scout에 같은 출력 schema와 시간 상한을 주고 **병렬 탐색**한다. 사람 Scout와 agent Scout를 같은 규약으로 다룬다. 각 workstream에 DRI를 한 명만 두고 같은 workspace 파일을 동시에 수정하지 않게 한다. 결과는 후보 카드만 반환하게 한다. 병렬 실행 수단이 없으면 동일 schema로 순차 실행하되 시간 상한은 유지한다.

각 트랙에서 최소 2개의 Problem Candidate를 만든다. 기업/트랙 수가 많으면 전체 후보를 12~20개까지 넓힐 수 있으나, Scout별 상위 후보만 중앙 비교표로 올린다. 후보는 solution 이름이 아니라 사용자 상태 변화로 쓴다.

각 후보를 다음으로 검증한다.

- 실제 사용자의 반복·고비용 문제인가
- 현재 대안이 왜 충분하지 않은가
- 기업/트랙과 구조적으로 맞는가
- 제한 시간 안에 핵심 가설을 실증할 수 있는가
- 필요한 data/access를 확보할 수 있는가
- demo에서 전후 차이를 이해시킬 수 있는가
- privacy/safety/IP/규칙 위험은 무엇인가

독립 반론을 한 번 붙인 뒤 다음 기준으로 상대 비교한다. 숫자는 정밀한 사실이 아니라 **비교 도구**이며 근거 문장이 우선한다.

| Criterion | 질문 |
|---|---|
| User pain | 빈도·심각도·현재 비용이 입증되는가 |
| Evidence strength | 1차/공식 근거가 있는가 |
| Sponsor fit | 기업 자산·과제와 결합 이유가 있는가 |
| Testability | 해커톤 안에 핵심 가설을 검증할 수 있는가 |
| Feasibility | team/time/data/API 제약 안에서 가능한가 |
| Differentiation | 기존 대안 대비 변화가 선명한가 |
| Demo clarity | 짧은 demo로 before/after가 보이는가 |
| Risk | 실격·법무·안전·의존성 위험이 감당 가능한가 |

AI가 최고 점수 후보를 자동 채택하지 않는다.

---

# Phase 3 — Problem Gate / Human Judgment

후보 전부를 먼저 동일 rubric으로 AI Judge와 Persona Judge가 독립 평가한다. 점수에는 근거, confidence, hard-fail 여부를 붙인다. 두 Judge의 순위가 크게 다르면 평균으로 덮지 말고 disagreement와 그 원인을 사람에게 올린다. 상위 2~3개만 최종 Human Gate에 제시한다.

```markdown
### Problem Gate
| Candidate | User/problem | Evidence | Test in event | Sponsor fit | Main risk |
|---|---|---|---|---|---|

Recommendation: ...
Why now: ...
Rejected alternative and why: ...
Decision needed: track / problem / accepted trade-off
```

사람이 다음을 확정하면 `Problem Lock`한다.

- 한 명확한 primary user와 context
- 검증된 problem statement
- 핵심 가설
- 성공/실패 기준
- 선택한 트랙/기업과 연결 이유

문제 근거가 약하면 구현으로 넘어가지 말고 짧은 인터뷰·관찰·data check를 먼저 수행한다. 확정되지 않은 후보는 backlog로만 남긴다.

---

# Phase 4 — Evidence-first Scaffolding

솔루션을 가장 작은 검증 가능한 slice로 바꾼다.

```markdown
### Build Contract
- Problem statement:
- Core hypothesis:
- Primary journey: Start → Input → Processing → Result → Action
- P0 / P1 / CUT:
- Success signals:
- Evidence to collect:
- Demo story:
- Technical reuse/stack:
- Top dependency and fallback:
```

Problem Lock 이후 사용할 기존 자산을 먼저 선택한다. `references/composition-and-team.md`의 routing을 적용하고 선택한 스킬 산출물을 해당 phase의 SoT로 선언한다. 같은 내용의 Runner artifact를 다시 만들지 않는다.

3~6개 work package로 나눈다.

```text
Work Package N — Requirement | Human DRI | Agent/skill | Files | Dependencies | Done | Verify | Evidence
```

병렬 구현은 파일·module·산출물 ownership이 독립일 때만 한다. 공유 파일이나 선행 contract가 필요한 작업은 먼저 interface/schema를 잠그거나 순차 실행한다. 한 명을 Integration DRI로 지정하고 병렬 결과를 통합한 뒤 전체 회귀를 실행한다. Integration DRI는 모든 코드를 직접 작성하는 사람이 아니라 contract·merge order·release state를 소유하는 사람이다.

---

# Phase 5 — Build / Human-ON-the-loop

Scope Lock 이후 다음 루프를 자율 실행한다.

```text
Implement → targeted check → inspect evidence → minimal fix → re-run
```

- 기존 stack·component·API를 우선 재사용한다.
- 실제 data가 없으면 mock임을 표시하고, mock으로 검증할 수 없는 가설을 분리한다.
- UI보다 핵심 data/action path를 먼저 연결한다.
- P0 Engineering Gate 전 P1을 열지 않는다.
- scope, architecture, 안전·개인정보·비용 위험이 바뀔 때만 Human-IN gate로 되돌아간다.

---

# Phase 6 — Verification, Evidence, Taste

## Engineering Gate

repository에 실제 존재하는 명령을 찾아 다음 중 가능한 것을 실행한다.

1. type/compile
2. 핵심 rule targeted test
3. unit/integration test
4. production build
5. API/data smoke test

실행하지 않은 항목은 `NOT VERIFIED`다. 실패를 고친 뒤 같은 명령을 다시 실행한다.

## Field Evidence

핵심 가설에 맞는 실증을 수행한다.

- 실제/대표 사용자 task completion
- before/after time, error, steps 또는 decision quality
- real/sample data 결과 비교
- 사용자 관찰·인터뷰·feedback
- 실패/edge condition

표본과 환경 한계를 함께 기록한다. demo가 곧 validation은 아니다.

## Taste Gate

사람이 실제 핵심 flow를 주행하고 다음을 판정한다.

- 첫 30초 안에 문제와 가치가 이해되는가
- 다음 행동과 결과가 명확한가
- 중요한 상태·실패·불확실성을 숨기지 않는가
- 기술이 아니라 사용자 변화가 중심인가
- 심사 demo가 안정적으로 재현되는가

정밀 UX 진단이 필요하고 시간이 허용되면 `ux-researcher`를 별도 호출한다. 이 스킬 안에서는 demo blocker와 핵심 flow만 본다.

---

# Phase 7 — Two-way Mock Judge

`references/evaluation-lenses.md`를 읽는다. Mock Judge에게 다음만 준다.

- 공식 rubric과 제출 요구
- Problem/Build Contract
- 실행 가능한 prototype 또는 영상
- evidence와 verification log
- pitch/deck/submission draft

Builder의 의도·변명·자기평가는 주지 않는다. 두 Judge를 독립 실행한다.

- **AI Judge**: rubric weight, 형식, traceability, 실행 증거, 실격 조건, unproven claim.
- **Persona Judge**: 기업 실무자 관점의 문제 중요도, 현업 적용성, 첫인상, 직관, 완성도, Taste.

두 결과를 병합하되 판정 충돌을 보존한다. 각 Judge는 다음을 반환한다.

```markdown
### Mock Judge
- Eligibility / disqualification: PASS | FAIL | UNKNOWN
- Rubric-by-rubric verdict: evidence / gap / severity
- Unproven claims:
- Demo failure risks:
- Top 3 fixes by score impact:
- Submit / conditional submit / do not submit:
```

결정론 체크(파일 존재, 길이, build/test, 링크 접근, 영상 재생)는 agent 판단보다 우선한다. 구현 milestone 또는 commit마다 영향받은 rubric을 재심사하고, 제출 전에는 전체 심사를 반복한다. 횟수 자체를 목표로 삼지 말고 `hard fail 없음 + critical gap 없음 + 사람이 Taste 승인`까지 반복한다. 수정 후 관련 검증과 두 Judge를 다시 실행한다.

---

# Phase 8 — Submission Freeze

`references/timebox-and-submission.md`의 체크리스트를 적용한다.

- 요구 파일·링크·권한·형식·분량·언어·팀 정보 확인
- 라이선스·출처·AI 사용 고지·개인정보 확인
- clean environment에서 실행법 확인
- 마지막 변경 후 regression과 demo rehearsal 재실행
- backup video/screenshots와 fallback demo path 준비
- deadline/timezone 전에 제출하고 receipt를 보존

Freeze 이후에는 실격·blocker·regression만 수정한다. 제출 성공 화면/메일/ID가 없으면 제출 완료로 간주하지 않는다.

---

# Phase 9 — Handoff

세션 종료·담당 변경·장시간 중단 전에 `HACKATHON-HANDOFF.md`를 갱신한다.

```markdown
# Hackathon Handoff
- Competition Lock + remaining time
- Selected problem and rejected alternatives
- Human decisions and accepted trade-offs
- P0/P1/CUT and current status
- Evidence collected / missing
- Changed files and run commands
- Verification results and known failures
- Submission checklist status
- Exact next 3 actions
- Risks, credentials/access needed, owners
```

팀 작업이면 workstream별 handoff를 따로 늘어놓지 않고 Integration DRI가 공용 handoff에 병합한다. 각 항목에는 `owner / last updated / next action / blocker`를 남긴다.

프로젝트에 기존 handoff/status 규약이 있으면 그 경로를 사용한다. 장문의 세션 요약이 필요하면 `handoff-writer`를 호출하되, 이 스킬의 실행 상태 필드는 유지한다.

## 기존 자산과의 조합 원칙

기존 스킬을 기본적으로 배제하지 않는다. `ai-hackathon-runner`는 대회 규칙·시간·팀·심사·제출을 소유하고, 전문 스킬은 선택된 phase의 실행과 산출물을 소유한다.

| 스킬 | 조합 지점 | SoT / 제한 |
|---|---|---|
| `prd-flow` | Context 이후 문제 정의·페르소나·가치 가설·solution scope·Full PRD | `prd-flow/{slug}/`를 제품 정의 SoT로 사용한다. Runner의 Problem/Build Contract와 중복 작성하지 않고 필요한 필드만 링크한다. 팀의 research/product workstream에 우선 권장한다. |
| `ai-dlc` | Full PRD 또는 Build Contract 확정 후 설계·구현·테스트 | `aidlc-docs/`와 code를 기술 실행 SoT로 사용한다. 해커톤 시간·제출 gate는 Runner가 계속 소유한다. 짧은 대회에서는 full lifecycle overhead를 비교하고 선택한다. |
| `loop-harness` | 정확도·latency·cost·task completion처럼 반복 측정 가능한 핵심 가설 최적화 | 정답표·기계 판정이 있는 지표에만 사용한다. 주관적 우승 가능성이나 Persona Judge 점수를 정답표처럼 최적화하지 않는다. |
| `ux-researcher` | 통합 MVP의 대표 flow가 나온 뒤 정밀 UX 검증 | UX finding을 evidence register에 연결한다. 제출 직전 시간이 부족하면 Runner의 Taste Gate만 사용한다. |
| `codex-delegate` | 독립 work package를 별도 Codex CLI에 자립 SPEC으로 위임 | 해당 package의 실행 수단일 뿐 제품 판단·팀 통합·제출 owner가 아니다. |

조합 시 precedence는 `공식 대회 규칙 > competition profile > Runner phase gate > 전문 스킬 workflow > 일반 개발 관행` 순서다.

## 종료 조건

다음을 모두 만족해야 종료한다.

- 공식 규칙과 제출 요구가 출처와 함께 고정됐다.
- 복수 문제 후보를 비교했고 사람의 선택 근거가 남았다.
- P0 user journey가 실제로 실행된다.
- 핵심 가설에 대한 실증과 한계가 남았다.
- 기계 검증과 Mock Judge를 통과했거나 gap을 명시했다.
- 제출 receipt가 보존됐다.
- 다음 세션이 재탐색 없이 이어갈 handoff가 있다.
