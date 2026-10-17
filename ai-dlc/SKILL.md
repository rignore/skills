---
name: ai-dlc
description: PRD(요구사항 문서) 하나만 주면 AWS AI-DLC(AI-Driven Development Life Cycle) 워크플로우를 처음부터 끝까지 자동으로 수행하는 스킬. INCEPTION(워크스페이스 감지 → 요구분석 → 유저스토리 → 워크플로우 계획 → 애플리케이션 설계 → 유닛 분할) → CONSTRUCTION(유닛별 기능설계·NFR·인프라설계·코드생성 → 빌드·테스트) → OPERATIONS 3단계를 각 단계 승인 게이트와 함께 적응적으로 진행하고, aidlc-docs/에 요구사항·설계·코드요약·감사로그를 남긴다. 사용자가 "AI-DLC", "AI DLC", "aidlc", "에이아이 디엘씨", "PRD로 개발 시작", "요구사항으로 워크플로우 돌려줘", "이 PRD로 AI-DLC 진행", "AI-DLC 워크플로우 시작", "PRD부터 코드까지", "요구사항 분석부터 코드 생성까지 자동으로"와 같이 PRD/요구사항 문서를 기반으로 AI-DLC 개발 라이프사이클을 실행하려는 의도를 보이거나 /ai-dlc 로 호출할 때 사용한다. 단순 PRD 작성(prd-builder-discovery)이나 와이어프레임 생성(prd-to-wireframe)과는 다르며, 이미 있는 PRD를 입력으로 받아 실제 설계·코드까지 만들어내는 풀 라이프사이클 실행이 목적이다.
---

# AI-DLC 워크플로우 실행 스킬

이 스킬은 **PRD(요구사항 문서)를 입력으로 받아 AWS AI-DLC 워크플로우를 처음부터 끝까지 수행**한다.
방법론 본체와 단계별 상세 규칙은 이 스킬 폴더 안에 모두 번들되어 있다.

## 이 스킬의 구성 (스킬 디렉토리 내부)

```text
<skill-dir>/
├── SKILL.md          # 이 파일 — 진입점
├── workflow.md       # AI-DLC 오케스트레이터(전체 워크플로우 규칙). SoT.
├── rules/            # 단계별 상세 규칙 (workflow.md가 참조하는 본문)
│   ├── common/       #   공통 규칙
│   ├── inception/    #   INCEPTION 단계
│   ├── construction/ #   CONSTRUCTION 단계
│   ├── operations/   #   OPERATIONS(placeholder)
│   └── extensions/   #   opt-in 확장(security, property-based testing)
└── templates/        # PRD.md / constraints.md 빈 템플릿
```

## STEP 0 — PRD 입력 확보 (가장 먼저)

워크플로우를 시작하기 전에 **이번 작업의 요구사항(PRD)을 먼저 확정**한다. 다음 중 하나로 확보:

0. **prd-flow 작업 디렉토리가 있다 (최우선 자동 감지)** → 현재 작업 디렉토리에서 `prd-flow/{feature-slug}/`를 탐색한다. 발견하면 사용자에게 해당 슬러그로 진행할지 1회 확인 후 다음을 인테이크한다:
   - `prd-flow/{slug}/notion-pages/full-prd.md` → `requirements/PRD.md`로 복사 (Full PRD가 없으면 `gate2/13-discovery-report.md`와 gate1/·auto-backward/ 산출물로 대체)
   - `prd-flow/{slug}/gate1.5/06-solution-scope.md`의 Non-Scope 항목 → `requirements/constraints.md` 초안 생성 (사용자 확인 후 확정)
   - `prd-flow/{slug}/wireframe/**/*.jsx` + `*_description.md`(화면 설계서) → `requirements/screens/`로 복사. Requirements Analysis·User Stories·Code Generation이 화면 사양 입력으로 사용한다
   - `prd-flow/{slug}/gate1/03-personas.md` → User Stories 단계에서 페르소나로 재사용
   여러 슬러그가 있으면 사용자에게 선택을 묻는다. prd-flow 디렉토리가 없으면 아래 1~3으로 진행한다.
1. **사용자가 PRD 파일 경로를 줬다** → 그 파일을 읽어 요구사항 입력으로 사용한다.
2. **사용자가 PRD 내용을 붙여넣었다** → 현재 작업 디렉토리에 `requirements/PRD.md`로 저장한 뒤 입력으로 사용한다.
3. **PRD가 아직 없다** → `templates/PRD.md`(와 필요 시 `templates/constraints.md`)를 현재 작업 디렉토리 `requirements/`로 복사해 주고, 사용자에게 채워 달라고 요청한 뒤 대기한다. 채워지기 전에는 워크플로우를 진행하지 않는다.

### 상태 태그가 붙은 PRD·사양을 받았을 때 (2026-08-27 신설)

기획 단계에서 만든 에이전트 사양에는 항목마다 상태 태그가 붙어 있을 수 있다. **이 워크플로우가 기획과 개발 사이의 개발 쪽을 맡으므로, 태그별로 다르게 다룬다.**

| 태그 | 이 워크플로우가 할 일 |
|---|---|
| `[기획 확정]` | **바꾸지 않는다.** 업무 의미는 확정된 계약이다 |
| `[개발 위임]` | **이 워크플로우가 확정한다.** 기획자가 적은 업무 제약과 수용 기준을 만족하는 기술 계약을 CONSTRUCTION 단계에서 정하고, 무엇을 왜 그렇게 정했는지 산출물에 남긴다 |
| `[확정 · 재검토 대상]` | 확정값으로 구현하되 **재검토 표시를 코드 주석과 산출물에 함께 남긴다** |
| `[미결]` | **진행하지 않고 사용자에게 되돌린다.** 업무 규칙을 이 워크플로우가 추정하면 그 오류는 구현이 끝난 뒤에야 드러난다 |

**업무 규칙을 추정해야 하는 자리를 만나면 멈추고 묻는다.** 무엇이 비었고 누가 답해야 하는지를 함께 전달한다. 멈추는 조건은 셋이다.

1. 구현하려면 새로운 업무 규칙을 추정해야 한다.
2. 결과가 요구사항과 맞는지 판단하려면 코드나 프롬프트 내부를 해석해야 한다.
3. 판단 기준의 출처와 적용 조건을 추적할 수 없다.

> 범위에서 제외할 항목이 있으면 `requirements/constraints.md`도 함께 입력으로 읽는다.
> PRD 파일명/개수/형식은 자유다 — 핵심은 "무엇을 만들지"가 문서로 확정되는 것.
> `prd-flow/{slug}/design/design-system.md`가 있으면 프론트엔드 코드 생성 시 그 §0 Hard Constraints를 준수한다.

## STEP 1 — 오케스트레이터 로드 및 실행

PRD가 확보되면:

1. 이 스킬 폴더의 **`workflow.md` 전체를 읽는다**. 이것이 워크플로우의 Source of Truth다.
2. `workflow.md`가 참조하는 모든 규칙 파일은 이 스킬 폴더의 **`rules/` 하위**에 있다.
   (`common/process-overview.md` → `<skill-dir>/rules/common/process-overview.md` 식으로 해석)
3. `workflow.md`의 지시에 따라 워크플로우를 시작한다:
   - 시작 시 **Welcome 메시지**(`rules/common/welcome-message.md`)를 1회 출력
   - **Workspace Detection** → 그린필드/브라운필드 판정, `aidlc-docs/aidlc-state.md` 생성(또는 있으면 재개)
   - **Requirements Analysis** — STEP 0에서 확보한 PRD를 읽고, 부족한 부분만 객관식 질문으로 보완
   - 이후 단계는 `workflow.md`의 적응적 규칙(ALWAYS/CONDITIONAL)에 따라 진행
4. `workflow.md`의 모든 **MANDATORY 규칙**을 그대로 따른다:
   - 각 단계 완료 시 명시적 **승인 게이트**(approval gate) — 사용자 컨펌 전 다음 단계로 넘어가지 않음
   - 모든 사용자 입력/응답을 `aidlc-docs/audit.md`에 원문 그대로 append(절대 덮어쓰기 금지)
   - 진행 상태를 `aidlc-docs/aidlc-state.md`에 갱신(중단 후 재개 지원)
   - 파일 생성 전 `rules/common/content-validation.md` 검증
   - 질문은 `rules/common/question-format-guide.md` 형식

## 산출물

워크플로우 실행 결과로 작업 디렉토리에 다음이 생성된다:

```text
<작업 루트>/        # 실제 애플리케이션 코드 (aidlc-docs/ 안에 두지 않음)
└── aidlc-docs/     # 문서 전용
    ├── inception/      # 요구사항·유저스토리·설계
    ├── construction/   # 유닛별 설계 + 코드 요약 + 빌드·테스트 지시서
    ├── aidlc-state.md  # 진행 상태(재개용)
    └── audit.md        # 전체 감사 로그
```

## 주의

- `workflow.md`와 `rules/`는 방법론 본체다 — 실행 중 수정하지 않는다.
- 이 스킬은 **이미 있는 PRD를 받아 설계·코드까지 만드는** 풀 라이프사이클 실행이 목적이다.
  PRD 자체를 새로 기획하는 작업은 `prd-builder-discovery`, 화면 와이어프레임은 `prd-to-wireframe`를 쓴다.
- 브라운필드(기존 코드 존재)면 `workflow.md` 규칙에 따라 Reverse Engineering 단계가 먼저 실행된다.
