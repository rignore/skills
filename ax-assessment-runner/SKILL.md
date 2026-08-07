---
name: ax-assessment-runner
description: 시간 제한이 있는 PRD 기반 AI 활용 역량 평가·실무형 구현 시험에서 Context → Decide → Delegate → Verify → Taste 순서로 문제 정의, 범위 결정, 구현, 결정론 검증, 사용자 플로우 확인까지 닫는 실행 스킬. 사용자가 "AI 역량 평가", "AX 평가", "PRD 구현 시험", "Codex 평가", "70분 구현", "실무형 구현 과제", "시간 제한 코딩 과제", "assessment runner"처럼 제한 시간 안에 AI와 서비스를 구현하고 과정까지 평가받는 상황을 말할 때 사용한다. 일반적인 무제한 PRD 구현은 ai-dlc를 사용하며 이 스킬은 발동하지 않는다.
---

# AX Assessment Runner

시간 제한 PRD 구현형 평가에서 **AI가 많이 일한 흔적**이 아니라 **사람이 올바른 기준을 세우고 AI를 통제해 검증 가능한 결과까지 닫은 흔적**을 남기기 위한 경량 실행 프로토콜이다.

기본 루프:

```text
Context → Decide → Delegate → Verify → Taste → Evidence
```

이 스킬은 `ai-dlc`처럼 완전한 개발 라이프사이클 문서를 만들지 않는다. 평가 시간 자체가 핵심 자원이므로, 문제 정의·P0 범위·실제 구현·검증 증거에 직접 기여하지 않는 문서와 승인 게이트는 제거한다.

## 핵심 원칙

1. **Context before Code** — PRD와 현재 코드베이스를 읽기 전에 구현하지 않는다.
2. **Human owns the judgment** — AI는 후보와 반론을 만든다. 핵심 문제, P0, 성공 기준, 큰 범위 변경은 사용자가 최종 결정한다.
3. **Smallest valuable end-to-end slice** — 많은 기능을 반쯤 만드는 것보다 핵심 사용자 일이 처음부터 끝까지 완료되는 한 흐름을 먼저 완성한다.
4. **Evidence over self-report** — "구현했다", "통과했다"는 서술을 증거로 인정하지 않는다. 실제 명령 실행, 테스트, 빌드, 주행 결과만 PASS 근거로 사용한다.
5. **Autonomy between gates** — 문제 범위가 승인된 뒤의 반복 구현·오류 수정·테스트 재실행은 AI가 자율적으로 수행한다. 사소한 승인 요청으로 시간을 소모하지 않는다.
6. **Taste after machine pass** — 기계 검증 통과와 좋은 사용자 경험은 다르다. 마지막에는 실제 핵심 유저플로우와 첫인상·직관·상태 전이를 확인한다.
7. **Timer is a hard constraint** — 시간이 줄수록 범위를 줄이지 검증을 줄이지 않는다. 후반에는 새 기능보다 regression과 제출 가능 상태를 우선한다.
8. **No documentation theater** — 평가 로그가 이미 과정을 기록한다면 별도 감사로그·상태문서·장문의 설계서를 만들지 않는다. 제출 요구가 있을 때만 문서화한다.

## 평가 렌즈

이 스킬의 평가 렌즈는 **공식 채점표가 아니라 작업 품질을 위한 비공식 self-check**다. 공식 평가 기준처럼 주장하지 않는다.

필요 시 `references/evaluation-lenses.md`를 읽는다.

- Problem Definition — 핵심 문제를 좁혔는가
- Scope Judgment — 시간 대비 P0/non-goal을 잘 잘랐는가
- Human Control — AI 제안과 사람의 최종 판단이 구분되는가
- Evidence — 주장에 실행 증거가 있는가
- End-to-End Value — 사용자가 실제 일을 끝낼 수 있는가
- Roadmapping — 구현→검증→수정 순서가 합리적인가

## Reference 적재 규칙

| 파일 | 언제 읽나 | 용도 |
|---|---|---|
| `references/70m-preset.md` | 총 시간이 60~90분이거나 사용자가 "70분"을 명시 | 70분 기본 시간 배분·scope freeze·rescue rule |
| `references/evaluation-lenses.md` | Problem Gate, 최종 Evidence Gate | 비공식 평가 렌즈·실격성 안티패턴 점검 |

레퍼런스를 한 번에 모두 적재하지 않는다. 해당 게이트에 도달했을 때만 읽는다.

---

# Phase 0 — Assessment Setup

## 목적

시험 규칙과 시간 제약을 코드 요구사항과 동급의 hard constraint로 고정한다.

## 입력

가능한 범위에서 다음을 읽는다.

- 시험/평가 안내문
- 현재 단계의 지시문
- PRD 또는 요구사항 파일
- 현재 repository/workspace
- 남은 시간 또는 단계별 타이머

## 실행

1. 평가 규칙에서 다음을 추출한다.
   - 총 시간 / 현재 단계 시간
   - 허용 도구
   - 금지 도구·외부 검색 제한
   - 이전 단계 복귀 가능 여부
   - 자동 제출 여부
   - 필수 산출물
2. **시험 규칙이 일반 개발 관행보다 우선한다.**
3. 외부 문서·검색이 금지되면 절대 사용하지 않는다. 에이전트 자체 웹 검색이 명시적으로 허용된 경우에도 구현 blocker 또는 요구사항 사실 확인에만 제한적으로 사용하고 일반 리서치로 시간을 소비하지 않는다.
4. 60~90분 평가라면 `references/70m-preset.md`를 읽고 타임박스를 적용한다.
5. 시간이 명시되지 않으면 아래 비율을 사용한다.
   - Context + Decide: 20%
   - Core implementation: 35%
   - Engineering verification + fix: 25%
   - User flow + final evidence: 20%

## 출력

장문 계획 대신 다음 5줄 이내로만 시작 상태를 선언한다.

```text
Assessment mode: [총 시간/현재 단계]
Hard constraints: [핵심 규칙]
Current workspace: [greenfield/brownfield + stack]
Primary objective: [한 줄]
Next: Context scan — 구현은 아직 시작하지 않음
```

### Stage boundary mode

평가 UI가 여러 단계로 나뉘고 이전 단계로 돌아갈 수 없다면 각 단계 종료 전 반드시 **Stage Close Check**를 실행한다.

- 현재 단계의 필수 입력을 모두 반영했는가
- 저장/제출 대상이 실제로 존재하는가
- 다음 단계에서 고칠 수 있다고 가정하고 미완료 상태를 넘기고 있지 않은가
- 제출 직전 큰 수정은 하지 않았는가

---

# Phase 1 — Context Scan

## 목적

코드를 쓰기 전에 **무엇을 왜 만들어야 하는지와 이미 무엇이 있는지**를 짧고 정확하게 파악한다.

## 실행

아직 구현하지 않는다.

### A. PRD에서 추출

- Primary user / persona
- 사용자가 완료하려는 핵심 JTBD
- 핵심 pain/problem
- 명시적 functional requirements
- acceptance criteria로 변환 가능한 문장
- 정책·제약·non-goal
- 애매하거나 충돌하는 요구사항
- PRD에 없는 추정이 필요한 부분

### B. repository에서 추출

- greenfield / brownfield
- 실제 framework / language / package manager
- 기존 scripts와 테스트 명령
- 재사용 가능한 component/service/model
- 기존 architecture와 naming convention
- 변경 위험이 큰 영역

### C. Scope 후보

요구사항을 세 그룹으로 분류한다.

- **P0** — 핵심 사용자 일을 end-to-end 완료하는 데 필수
- **P1** — P0가 안정적일 때 추가
- **CUT** — 시간 대비 가치가 낮거나 core journey와 무관

## 출력 — Context Pack

```markdown
### Context Pack
- Primary user/JTBD: ...
- Core problem: ...
- Core journey: A → B → C
- Existing stack/reuse: ...
- P0 candidates: ...
- P1/CUT candidates: ...
- Ambiguities/assumptions: ...
- Highest implementation risk: ...
```

증거가 없는 내용은 `Assumption`으로 표시한다. PRD에 없는 요구사항을 사실처럼 추가하지 않는다.

---

# Phase 2 — Problem Gate / Human Decision

## 목적

잘못 정의된 문제를 빠르게 구현하는 것을 차단한다. **이 스킬의 핵심 Human-IN-the-loop 게이트다.**

## 2-1. Adversarial check

Context Pack의 첫 해석을 그대로 믿지 말고 스스로 반론을 만든다.

다음을 확인한다.

1. 이것이 정말 PRD에서 가장 중요한 사용자 문제인가?
2. 제안한 P0만 구현해도 사용자가 의미 있는 일을 처음부터 끝까지 완료할 수 있는가?
3. 구현 난이도 대비 가치가 낮은 기능이 P0에 섞였는가?
4. PRD 요구를 잘못 확대·축소한 부분이 있는가?
5. 시간이 부족하면 어떤 기능부터 자를 것인가?
6. 성공 기준이 관찰·테스트 가능한가?

`references/evaluation-lenses.md`의 Problem Definition / Scope Judgment 항목을 읽어 대조한다.

## 2-2. Decision Card

사용자에게 **한 번의 짧은 결정**만 요청한다.

```markdown
### Problem Gate
- 핵심 문제: ...
- P0: R1, R2, R4
- P1: R3
- CUT: R5
- 성공 기준: [검증 가능한 2~4개]
- 가장 큰 trade-off: ...
- 추천: [추천 범위]

`진행`하면 이 범위를 고정하고 구현한다. 수정할 항목만 말해도 된다.
```

### 게이트 규칙

- 사용자가 `진행` 또는 동등한 승인을 하면 P0를 **Scope Lock**한다.
- 사용자가 이미 명시적으로 P0·성공 기준을 지정했다면 다시 묻지 말고 그 판단을 Human Decision으로 기록한다.
- 사용자가 `자동 진행`을 명시한 경우에만 추천 범위를 자동 승인으로 간주한다.
- 구현을 막는 불확실성 외에는 추가 질문을 쌓지 않는다.
- 이후 P0 밖으로 범위를 넓히려면 P0가 Engineering Gate를 통과한 뒤에만 한다.

---

# Phase 3 — Scaffold & Delegate

## 목적

승인된 범위를 3~4개의 실행 가능한 task로 쪼개고, 이후 반복 실행은 AI에게 위임한다.

## Task 설계 규칙

각 task에 아래 4요소만 둔다.

```text
Task N
- Requirement: 어떤 P0를 구현하는가
- Files: 예상 수정/생성 경로
- Done: 사용자가 무엇을 할 수 있어야 하는가
- Verify: 어떤 명령/행동으로 확인할 것인가
```

### 가드레일

- 3~4개 task를 기본으로 한다. 작은 시험에서 10개 이상의 작업 분해는 planning overhead로 간주한다.
- 기존 stack·architecture·component를 우선 재사용한다.
- 단지 익숙하다는 이유로 framework/package manager를 교체하지 않는다.
- 새 dependency는 core journey에 실질적으로 필요할 때만 추가한다.
- brownfield에서는 기존 파일이 있으면 in-place 수정한다. `_new`, `_fixed`, `_v2` 복사본을 만들지 않는다.
- UI polish보다 **입력 → 처리 → 결과 → 다음 행동/상태 저장** 연결을 먼저 완성한다.

## 실행 모드 — Human ON the loop

Scope Lock 이후에는 다음 루프를 자율 수행한다.

```text
Implement → Run targeted check → Fix from evidence → Re-run
```

사소한 구현 선택마다 승인을 기다리지 않는다. 다음 상황만 사용자에게 다시 올린다.

- P0 범위를 바꿔야 함
- 큰 architecture 변경이 필요함
- 데이터 손실·보안·파괴적 변경 위험
- 시험 규칙과 충돌 가능성

---

# Phase 4 — Engineering Gate

## 목적

AI의 자기보고가 아니라 실제 실행 결과로 구현을 판정한다.

## 4-1. 실제 검증 명령 발견

repository를 보고 존재하는 명령을 사용한다. 이름을 추측하지 않는다.

예:

- JS/TS: `package.json` scripts, lockfile 기준 package manager
- Python: `pyproject.toml`, `requirements*.txt`, `pytest` 설정
- 기타 stack: 기존 build/test configuration

## 4-2. 검증 우선순위

가능한 항목을 실제 실행한다.

1. syntax/typecheck/compile
2. 핵심 로직 targeted test
3. 기존 unit/integration tests
4. production build
5. 핵심 API 또는 데이터 흐름 smoke test

테스트가 전혀 없고 시간이 허용되면 **핵심 P0 business rule 한두 개**를 검증하는 최소 테스트를 추가한다. coverage 숫자를 채우기 위한 테스트는 만들지 않는다.

## 4-3. Evidence Fix Loop

실패 시:

1. 실제 error output을 읽는다.
2. 가장 직접적인 원인 가설 하나를 세운다.
3. 최소 범위를 수정한다.
4. **같은 검증 명령을 다시 실행한다.**

같은 실패 계열을 두 번 수정해도 진전이 없으면 무작정 반복하지 않는다. 원인을 다시 분해하거나 P1/CUT을 제거해 P0 제출 가능 상태를 확보한다.

## PASS 규칙

- 실행하지 않은 검증은 `PASS`가 아니라 `NOT VERIFIED`다.
- 테스트를 수정해서 통과시켰다면 요구사항을 약화한 것이 아닌지 확인한다.
- "should work", "looks correct", "likely passes"를 증거 문구로 쓰지 않는다.

## 출력 — Engineering Evidence

```markdown
### Engineering Gate
| Check | Command/Action | Result |
|---|---|---|
| Type/Compile | `...` | PASS/FAIL |
| Tests | `...` | PASS/FAIL/NOT VERIFIED |
| Build | `...` | PASS/FAIL/NOT VERIFIED |

Remaining blocker: ...
```

---

# Phase 5 — User Gate / Taste

## 목적

기계적으로 맞는 코드가 아니라 **사용자가 실제 일을 완료할 수 있는 서비스**인지 확인한다.

## 실행

UI가 있는 서비스라면 가능한 브라우저/앱 실행 수단을 사용해 실제 핵심 플로우를 주행한다.

```text
Start state
→ 핵심 입력
→ 주요 action
→ 결과 확인
→ 상태 변화/저장
→ 다음 action 또는 완료
```

확인 항목:

- 첫 화면에서 다음 행동이 명확한가
- 실제 클릭/입력이 동작하는가
- 데이터/상태가 예상대로 바뀌는가
- 성공·실패·빈 상태가 깨지지 않는가
- 새로고침/재진입 후 유지되어야 할 상태가 유지되는가
- P0의 핵심 가치가 화면/결과에서 실제로 드러나는가

브라우저 자동화가 없거나 시험 규칙상 사용할 수 없으면 그 한계를 명시하고 API/컴포넌트 테스트 등 가능한 대체 증거를 사용한다. **주행하지 않았는데 E2E PASS라고 쓰지 않는다.**

### Taste Gate

기계 검증이 통과한 뒤 다음만 수정한다.

- 핵심 flow blocker
- 오해를 유발하는 정보 구조
- 주요 action이 보이지 않는 문제
- 명백한 loading/error/empty-state 결함

이 단계에서 새로운 P1 기능이나 대규모 디자인 리뉴얼을 시작하지 않는다.

---

# Phase 6 — Final Evidence / Freeze

## 목적

PRD → 구현 → 검증 사이의 traceability를 남기고 제출 직전 회귀를 막는다.

## 6-1. Requirement Traceability

```markdown
| Requirement | Implementation evidence | Verification | Status |
|---|---|---|---|
| R1 | `src/...` | test/build/flow | PASS |
| R2 | `src/...` | ... | PARTIAL |
| R3 | — | — | CUT |
```

- 검증하지 못한 것은 PASS 금지.
- 미완료 항목과 limitation을 숨기지 않는다.
- PRD의 핵심 요구사항이 표에서 누락되면 제출 전에 확인한다.

## 6-2. Regression

변경 이후 최소한의 최종 typecheck/test/build를 다시 실행한다. 이전 PASS 결과를 그대로 재사용하지 않는다.

## 6-3. Freeze

제출 직전에는:

- 새 feature 금지
- dependency 교체 금지
- 대규모 refactor 금지
- cosmetic-only 변경 금지
- blocker/regression만 수정

## 최종 보고

```markdown
### Final Evidence
1. Core user flow completed: ...
2. P0 implemented: ...
3. Verification actually executed: ...
4. Remaining/partial/cut: ...
5. Known limitations: ...
6. Run/demo path: ...
```

설명보다 증거를 우선한다.

---

# Rescue Rules

시간 압박이나 구현 실패가 발생하면 다음 순서로 회복한다.

1. **P1 즉시 중단**
2. P0 중 핵심 journey와 무관한 항목 제거
3. architecture 개선보다 현재 stack에서 동작 복구
4. happy path를 먼저 살리고 critical error path만 유지
5. 제출 가능한 상태 확보 후 검증
6. 시간이 남을 때만 polish

다음 행동은 금지한다.

- 실패했다고 framework 전체 교체
- 테스트를 삭제해 PASS 만들기
- 요구사항을 임의로 완화해 PASS 만들기
- 새로운 기능으로 기존 blocker를 가리기
- 검증 없이 "완료" 선언

70분 평가의 구체적 cut-off는 `references/70m-preset.md`를 따른다.

---

# 자가 검증 체크리스트

스킬 종료 전 확인한다.

```text
[ ] PRD와 repo를 구현 전에 읽었다
[ ] 핵심 문제와 P0를 사람의 판단으로 확정했다
[ ] P0가 하나의 end-to-end user journey를 완성한다
[ ] 구현 task가 3~4개 수준으로 작게 유지됐다
[ ] 실제 type/test/build 중 가능한 검증을 실행했다
[ ] 실행하지 않은 검증을 PASS라고 하지 않았다
[ ] 핵심 flow를 실제 주행했거나, 불가능한 이유와 대체 증거를 남겼다
[ ] Requirement ↔ Implementation ↔ Verification 추적이 된다
[ ] 미완료 항목을 명시했다
[ ] 후반에 새 scope를 벌리지 않았다
```

---

## 트리거 키워드

다음 표현에서 강하게 트리거한다.

- "AI 역량 평가", "AI 활용 역량 평가", "AX 평가", "AX 역량"
- "PRD 구현 시험", "PRD 받아서 구현하는 시험"
- "Codex 평가", "Codex 시험", "코덱스 시험"
- "70분 구현", "1시간 안에 구현", "시간 제한 구현"
- "실무형 구현 과제", "AI 코딩 평가", "AI 활용 시험"
- "assessment runner", "timed PRD implementation", "coding assessment"

### 부정 트리거

다음에는 발동하지 않는다.

- 일반 프로젝트에서 PRD를 받아 시간 제한 없이 구현 → `ai-dlc`
- 단순 기능 하나 코드 작성/버그 수정 → 직접 구현
- 반복 수치 최적화/통계 검증 → `loop-harness`
- 이미 구현된 제품의 정밀 UX 진단 → `ux-researcher`
- Claude가 설계하고 별도 Codex CLI에 위임 → `codex-delegate`

---

## 다른 스킬과의 관계

| 스킬 | 관계 |
|---|---|
| `ai-dlc` | 요구사항→설계→구현→테스트의 원칙을 차용하지만, 시간 제한 평가에서는 문서·다중 승인 게이트 overhead 때문에 **이 스킬이 우선**한다. 전체 ai-dlc를 중첩 실행하지 않는다. |
| `codex-delegate` | SPEC 자립성·결정론 검증 원칙을 차용한다. Codex-only 평가에서는 외부 Claude/Codex 이중 오케스트레이션을 호출하지 않는다. |
| `ux-researcher` | 실제 화면·유저플로우 관찰 원칙만 경량 적용한다. 평가 중 full UX research harness는 호출하지 않는다. |
| `loop-harness` | evaluator/self-report 불신 원칙만 적용한다. 짧은 평가에서 통계 라운드 하네스 전체를 돌리지 않는다. |

### 우선순위 규칙

**시간 제한 + 평가/시험 + PRD 구현**이 동시에 있으면 `ax-assessment-runner`가 위 스킬보다 우선한다.
