---
name: codex-delegate
description: >
  [WHAT] "설계=Claude / 실행=Codex / 이중 교차검증" 로컬 위임 파이프라인 스킬.
  Phase 0 적합성 판정 → Phase 1 설계(자립 SPEC 작성·입력 스테이징·하드 제약) →
  Phase 2 실행(codex exec 또는 companion으로 위임) → Phase 3 교차검증(Claude evaluator 주 게이트
  + Codex adversarial-review 보조, judge≠solver·결정론 게이트) → Phase 4 판정·수렴의 4단계를 수행한다.
  단일 태스크 모드와 태스크 체인 모드(큰 작업을 작은 태스크로 절단, 태스크마다 git worktree 격리)를 지원한다.
  [WHEN] 사용자가 "코덱스한테 시켜", "codex로 실행", "codex한테 위임", "코덱스 위임",
  "설계는 클로드 실행은 코덱스", "codex 분배", "교차검증해서 위임", "코덱스랑 나눠서",
  "codex-delegate" 같은 표현을 쓰거나, 실행 작업을 Codex에 위임하고 검증 게이트를 두려는
  의도를 보일 때 트리거된다. 단순 "코드 작성해줘"·"파일 고쳐줘"에는 트리거하지 않는다
  (그건 Claude가 직접 수행). GitHub Actions PR 기반 위임은 claude-codex-framework의 영역이다.
---

# codex-delegate — 설계=Claude / 실행=Codex / 이중 교차검증

실행 작업을 Codex에 위임하되, 설계(자립 SPEC)와 검증(이중 교차검증 + 결정론 게이트)을 Claude가 쥐는 파이프라인. 서로 다른 두 경로로 실증됐다:

- **실증 1 — companion 경로**: knowledge-base Phase 1(정책 원문 이관·구조화). Round 1 반려(파싱 시 원자 59% 소실) 후 SPEC 수정, Round 2 조건부 승인.
- **실증 2 — `codex exec` + 태스크 체인**: manager PRD-A 구현. PRD를 태스크 4개로 절단, 태스크마다 worktree 격리·위임·검토·병합 사이클. 태스크당 실소비 약 4만 토큰(캐시 적중 91%).

## 실행 절차 (진입 시 이 순서대로)

1. **Phase 0 적합성 판정**. 부적합이면 스킬을 쓰지 않고 Claude가 직접 수행한다.
2. **모드 결정**: 단일 태스크 vs 태스크 체인 (§모드 분기).
3. **경로 결정**: `codex exec` vs companion (§Phase 2의 표).
4. Phase 1~4를 수행한다. 단계별 상세:
   - SPEC 작성 전 `references/spec-guide.md`를 읽어라 (실증에서 반려를 부른 SPEC 결함과 교정 규율).
   - 명령 실행 시 `references/commands.md`를 참조하라 (복붙 가능한 전체 명령).
   - Phase 2 착수 전 `references/pitfalls.md`를 읽어라 (이미 겪은 함정 9건 — 반복 금지).

## Phase 0 — 적합성 판정

| 판정 | 작업 유형 |
|---|---|
| 적합 (위임) | 파일 조작·구조화·코드 생성·데이터 이관 — 자립 SPEC으로 완전히 명세 가능한 실행 작업 |
| 부적합 (Claude 직접) | 전략 판단·요구사항 정의·이해관계자 조율 — 대화 맥락과 판단이 본체인 작업 |

부적합이면 여기서 종료한다. 적합이면 환경을 점검한다:

- `codex --version` — 모델-CLI 버전 불일치는 400 에러로 나타난다(pitfalls #8). 400 "requires a newer version"이면 `codex update`.
- `codex login status` — "Logged in using ChatGPT" 확인.

## Phase 1 — 설계 (Claude)

세 가지를 만든다. 상세 규율은 `references/spec-guide.md`.

- **(a) 자립 SPEC**: Codex는 이 대화를 못 본다. SPEC만으로 실행 가능해야 한다. 빈칸이 있으면 Codex가 창작으로 메운다.
- **(b) 입력 스테이징**: Codex가 읽을 원본을 작업 리포 안 `_codex-inbox/`(또는 유사 디렉토리)로 복사한다. 원본은 Codex sandbox 밖(작업 리포 밖)에 남아 구조적으로 보존된다.
- **(c) 하드 제약**: 원본 경로 접근 금지 / 수정 대상 파일 한정 / 스테이징 읽기 전용 / 수치 창작 금지. SPEC에 명시한다.

## Phase 2 — 실행 (Codex)

두 경로 모두 같은 Codex 엔진이다(세션 로그·인증·과금 동일). 선택 기준:

| 경로 | 쓸 때 | 비고 |
|---|---|---|
| `codex exec` | 플러그인 불필요·스크립트/체인 자동화 | 1회 실행. SPEC 파일을 통째로 프롬프트에 |
| companion | 세션 안에서 잡 여러 개 추적 | `task --write --background`, job-id 폴링 |

두 경로 다 Bash `run_in_background: true`로 감싼다. 명령 전체는 `references/commands.md`.

## Phase 3 — 교차검증 (이중·병렬)

두 검증자를 동시에 돌린다:

- **Claude `evaluator` subagent = 주 게이트.** 입력에 명세·산출물·정답표(원본) 경로만 준다. **생성 맥락("이건 우리가 만든 것")을 넘기지 않는다** — judge≠solver. 어기면 자기 산출물을 관대하게 채점해 검증이 무의미해진다.
- **Codex `adversarial-review` = 보조.** 대형 diff에서 hung 이력이 있다(pitfalls #1). 검증 대상 diff를 작게 유지한다.

**결정론 게이트가 승인 조건이다.** Codex·evaluator의 self-report를 그대로 믿지 않는다:

- 데이터 태스크: 파서 무손실(기계 재집계)·수치 일치. 실증 1에서 evaluator가 파서를 직접 재집계해 원자 59% 소실을 잡았다.
- 코드 태스크: 검토자가 typecheck·테스트를 **직접 재실행**한다. Codex의 "passed" 보고를 재실행 없이 받지 않는다.

## Phase 4 — 판정·수렴

두 검증 결과를 대조해 판정한다:

- **반려**: SPEC을 고쳐 재실행한다. 재실행 SPEC에는 반려 이유를 명시하고, 이미 승인된 산출물은 "건드리지 마라"로 범위를 잠근다(spec-guide 참조).
- **조건부 승인**: minor 결함은 Claude가 직접 정정하고 커밋한다.
- **커밋·병합은 항상 검토자(Claude)가 한다.** Codex 샌드박스는 worktree 커밋이 차단되기도 하고(pitfalls #7), 검토 전 커밋이 생기지 않아 규율에 유리하다.

반복 수렴이 여러 라운드 필요하면 loop-harness와 결합한다(현재 결합 방식 미설계 — §알려진 한계). v1은 단일 패스 + 수동 재실행이다.

## 모드 분기 — 단일 태스크 vs 태스크 체인

- **단일 태스크**: Phase 1~4를 1회.
- **태스크 체인**: 큰 작업(예: PRD 구현)을 작은 태스크로 절단하고, 태스크마다 Phase 1~4 사이클을 돈다. 작게 자르면 검토 가능성과 완료 속도가 확보된다(실증 2). 규율 3개:
  1. 태스크마다 **git worktree로 격리**한다. 같은 디렉토리에 병렬 위임하면 쓰기가 유실된다.
  2. 병합·worktree 정리 후 다음 태스크의 worktree를 **갱신된 main에서** 딴다 — 직전 태스크 결과 위에서 작업하게.
  3. 앞 태스크에서 배운 함정을 다음 SPEC에 즉시 반영한다(예: 커밋 지시 제거).

## 규율 6 (어기면 파이프라인 신뢰가 무효)

1. **원본 보존 = 스테이징 + sandbox 격리.** 원본을 직접 읽히지 말고 `_codex-inbox/` 사본을 읽힌다. 하드 제약으로 원본 경로 접근 금지를 SPEC에 박는다. 어기면 원본이 오염돼 되돌릴 기준을 잃는다.
2. **judge ≠ solver.** 검증자를 실행자와 분리하고, evaluator에 생성 맥락을 넘기지 않는다.
3. **SPEC 자립성.** 맥락 없이 실행 가능해야 한다. 어기면 Codex가 빈칸을 창작으로 메운다(실증 1의 "시계열 데이터" 창작 사례).
4. **결정론 게이트로 승인.** 기계 검증(파서·수치·typecheck·테스트 직접 재실행) 통과가 승인 조건. self-report 불신.
5. **설계 판단은 위임하되 보고를 강제.** SPEC에 모든 값을 못 박지 말고 "스스로 정한 값과 근거를 최종 보고에 적어라"를 넣는다. 과잉 명세는 SPEC을 늘리고, 무명세는 창작을 부른다 — 판단 위임 + 보고 강제가 중간값이다. (실증 2: Codex가 절단 길이를 기존 필드 관례 200자에서 스스로 찾아 맞췄고, 이관 멱등성을 undefined/명시적 null 구분으로 해석해 해제된 매핑의 부활 버그를 사전에 막았다.)
6. **"하지 못한 것과 이유"를 필수 보고 항목으로.** 결과 self-report는 불신하되(4번), 실패 보고 채널은 열어 둔다 — 조용한 실패가 최악이다. (실증 2: Codex가 커밋 실패를 에러 원문과 함께 보고해 검토자가 원인을 즉시 파악했다.)

## 기존 자산과 경계

| 자산 | 관계 |
|---|---|
| loop-harness | 지표를 정답표로 반복 수렴하는 하네스. 이 스킬은 위임 실행 1패스 + 교차검증. 반복이 필요하면 이 스킬을 loop-harness의 Solver 단계에 끼운다. 대체가 아니다 |
| claude-codex-framework (`~/claude-codex-framework`) | Claude 설계 + Codex 구현을 **GitHub Actions PR**로 수행. 이 스킬은 **로컬 세션 안** 위임. 축이 다르다 |
| evaluator subagent | 이 스킬이 Phase 3에서 그대로 호출한다 |

## 알려진 한계

- **Codex adversarial-review의 대형 diff hung 근본 원인 미규명.** 회피책만 있다: diff를 작게 쪼개고 Claude evaluator를 주 게이트로 둔다.
- **loop-harness 결합 방식 미설계.** 다회 반복 위임을 loop-harness의 어느 단계에 끼울지 미확정. v1은 단일 패스 + 수동 재실행.

## 산 교재 (실증 원본 — SPEC 작성이 막히면 열어볼 것)

- `~/knowledge-base/_codex-inbox/TASK-SPEC.md` — 결함 있는 v1 SPEC (Round 1 반려 원인).
- `~/knowledge-base/_codex-inbox/TASK-SPEC-v2.md` — 교정한 v2 SPEC (Round 2 승인).
- `~/knowledge-base/kb/example-domain/policy/example-output.md` — v2가 만든 승인 산출물.
- v1과 v2의 diff가 "좋은 SPEC 규율"의 산 교재다. `references/spec-guide.md`는 이 대조에서 추출했다.
