# 시간 제한 AI 구현 평가 — 비공식 Evaluation Lenses

이 문서는 공식 채점표가 아니다. 제한된 시간에 AI와 PRD를 구현할 때 **좋은 문제 해결 과정이 남는지** 점검하기 위한 self-check다. 평가 기관의 공식 루브릭으로 인용하거나 점수를 예측하는 데 사용하지 않는다.

## 1. Problem Definition

### 강한 신호

- Primary user와 핵심 JTBD가 한 문장으로 설명된다.
- PRD의 여러 기능을 하나의 핵심 문제로 묶을 수 있다.
- 문제 정의가 기능명("대시보드 만들기")이 아니라 사용자 상태 변화("사용자가 X를 확인하고 Y 결정을 내릴 수 있게")로 표현된다.
- PRD에 없는 추정은 assumption으로 분리된다.
- 첫 해석을 반론으로 한 번 검증했다.

### 약한 신호

- PRD를 읽자마자 전 기능 구현을 시작한다.
- AI가 고른 문제와 범위를 사용자가 검토하지 않는다.
- 솔루션/화면 이름이 곧 문제 정의다.
- 왜 중요한지 설명할 수 없는 기능이 P0에 들어 있다.

### Gate 질문

> 이 프로젝트의 UI를 모두 지워도 "사용자가 어떤 문제를 해결하려는 서비스인지" 한 문장으로 말할 수 있는가?

---

## 2. Scope Judgment

### 강한 신호

- P0 / P1 / CUT이 명시돼 있다.
- P0만으로 하나의 end-to-end user journey가 완료된다.
- 버릴 순서가 미리 정해져 있다.
- 시간이 줄면 검증이 아니라 범위를 줄인다.

### 약한 신호

- 모든 requirement를 동일 우선순위로 취급한다.
- 여러 화면을 만들었지만 어느 것도 끝까지 동작하지 않는다.
- 후반에도 새 기능을 추가한다.
- 어려운 기능을 만나면 framework를 갈아엎는다.

### Gate 질문

> 지금 P1을 전부 삭제해도 사용자가 핵심 일을 완료할 수 있는가?

---

## 3. Human Control

### 강한 신호

AI와 사람의 역할이 분리된다.

**AI가 잘하는 것**
- PRD/repo 탐색
- 후보 생성
- 구현
- 반복 수정
- 테스트 실행

**사람이 소유해야 하는 것**
- 무엇이 핵심 문제인지
- P0가 무엇인지
- 성공 기준이 무엇인지
- 큰 trade-off를 받아들일지
- 최종 결과가 충분히 좋은지(Taste)

AI 제안을 그대로 채택하지 않고, 최소 한 번 사람의 판단으로 범위를 확정한 흔적이 있다.

### 약한 신호

```text
AI가 문제 정의
→ AI가 범위 선택
→ AI가 구현
→ AI가 자기 결과 평가
→ 사용자 승인 없이 종료
```

### Gate 질문

> 프롬프트 로그에서 "이 사용자가 없으면 결과가 달라졌을 판단"을 최소 하나 찾을 수 있는가?

---

## 4. Evidence

### 강한 신호

주장마다 확인 가능한 evidence가 있다.

```text
Requirement
→ 구현 파일/동작
→ 실제 검증 명령 또는 사용자 플로우
→ PASS/PARTIAL/FAIL
```

- typecheck/compile을 실제 실행한다.
- test를 실제 실행한다.
- build를 실제 실행한다.
- UI라면 실제 흐름을 주행한다.
- 실패 결과도 숨기지 않는다.

### 약한 신호

- "코드를 확인했으니 동작할 것"이라고 한다.
- 실행하지 않은 테스트를 PASS로 표시한다.
- test failure를 없애려고 test 자체를 약화한다.
- AI가 "완료했습니다"라고 말한 것이 유일한 근거다.

### Gate 질문

> 제3자가 이 결과를 믿어야 할 이유가 말이 아니라 실행 결과로 남아 있는가?

---

## 5. End-to-End Value

### 강한 신호

핵심 user journey가 다음처럼 끊기지 않는다.

```text
Need/Start
→ Input
→ Processing
→ Result
→ Decision/Action
→ Persisted or Completed state
```

UI 구성요소의 개수보다 사용자가 일을 완료하는지가 중요하다.

### 약한 신호

- dashboard/card/filter는 많지만 실제 데이터 흐름이 없다.
- 버튼은 있으나 action이 연결되지 않았다.
- mock data로만 그럴듯하게 보인다.
- 결과를 보고 사용자가 다시 수작업/검색을 해야 핵심 일을 끝낼 수 있다.

### Gate 질문

> 사용자가 핵심 결과를 얻은 뒤 별도의 수작업 없이 다음 의사결정/행동까지 갈 수 있는가?

---

## 6. Roadmapping

### 강한 신호

```text
Context
→ Problem Gate
→ Scope Lock
→ Core implementation
→ Engineering Gate
→ User Gate
→ Regression
→ Freeze
```

작업 순서가 리스크를 앞에서 줄인다.

- 기존 코드를 먼저 재사용한다.
- 핵심 flow를 먼저 연결한다.
- 첫 검증을 후반까지 미루지 않는다.
- blocker를 고친 뒤 같은 검증을 재실행한다.

### 약한 신호

- UI polish를 먼저 한다.
- architecture 문서를 길게 쓴 뒤 시간이 부족해진다.
- 테스트를 마지막 몇 분에 처음 실행한다.
- 오류가 날 때마다 다른 접근으로 무작정 갈아탄다.

### Gate 질문

> 다음 10분의 작업이 실패하더라도 현재 제출 가능한 결과가 남는가?

---

# Critical Anti-patterns

아래는 단순 감점 요소가 아니라 **과정의 신뢰를 크게 떨어뜨리는 패턴**으로 취급한다.

## A. Problem Outsourcing

AI에게 "알아서 가장 좋은 걸 만들어"라고 하고 문제·범위·성공기준까지 전부 위임.

**교정:** AI는 후보와 반론을 만들고, 사용자가 Decision Card에서 범위를 확정한다.

## B. Scope Explosion

P0가 검증되지 않았는데 P1/P2를 계속 추가.

**교정:** Engineering Gate 통과 전 P0 밖 변경 금지.

## C. Verification Theater

테스트 파일은 만들었지만 실행하지 않거나, "검증 완료" 문서만 생성.

**교정:** command/action + actual result가 없으면 NOT VERIFIED.

## D. Self-report Trust

실행 에이전트의 "passed" 보고를 재실행 없이 신뢰.

**교정:** 가능한 결정론 명령을 직접 실행하고 최종 변경 뒤 regression 재실행.

## E. Demo-only UI

화면은 그럴듯하지만 입력·상태·저장·오류 흐름이 실제로 연결되지 않음.

**교정:** core journey를 실제 주행하고 사용자 상태 변화까지 확인.

## F. Late Heroics

마지막 5~10분에 dependency/framework/architecture를 크게 수정.

**교정:** Scope Freeze와 Code Freeze를 지키고 blocker만 수정.

---

# 최종 6문항 Self-check

각 문항을 YES/NO로만 답한다. 애매하면 NO다.

1. **Problem** — 핵심 사용자 문제를 한 문장으로 설명할 수 있는가?
2. **Scope** — P0만으로 핵심 journey가 완료되는가?
3. **Control** — 사람의 명시적 판단이 최소 한 번 범위를 바꾸거나 확정했는가?
4. **Evidence** — 주요 PASS 주장에 실제 실행 증거가 있는가?
5. **Value** — 실제 사용자가 핵심 일을 end-to-end 완료할 수 있는가?
6. **Freeze** — 마지막 변경 후 regression을 실행하고 새 scope를 열지 않았는가?

NO가 있으면 새 기능 추가보다 해당 항목을 먼저 복구한다.
