---
name: design-system-builder
description: 프로젝트의 페르소나·문제 정의·기능 요구사항에 맞는 바탕 DESIGN.md(awesome-design-md)를 고르고 taste 스킬 규칙과 보강 리서치를 더해 프로젝트 전용 디자인 시스템 문서(./prd-flow/{slug}/design/design-system.md)를 구축하는 스킬. 고정된 회사 디자인 시스템이나 정적 토큰 스펙 대신, 제품 카테고리(B2B 대시보드/커머스/생산성/헬스케어 등)와 사용자 특성에 맞는 레퍼런스 제품·디자인 패턴·접근성 관행을 검색해 컬러·타이포·간격·radius·elevation 토큰과 컴포넌트 인벤토리, Hard Constraints를 생성한다. prd-to-wireframe Phase 0에서 자동 호출되며, 사용자가 "디자인 시스템 만들어줘", "이 프로젝트 디자인 방향 잡아줘", "레퍼런스 조사해서 디자인 시스템 구축"이라고 요청할 때도 사용한다.
---

# Design System Builder

프로젝트별 디자인 시스템을 **레퍼런스 리서치 기반으로 생성**하는 스킬. 어떤 프로젝트든 페르소나와 요구사항에서 디자인 니즈를 도출하고, 그에 맞는 레퍼런스를 웹에서 조사한 뒤, 와이어프레임·프로토타입 생성이 준수할 디자인 시스템 문서를 만든다.

## 이 스킬의 위치

| 호출 주체 | 시점 | 동작 |
|---|---|---|
| `prd-to-wireframe` | Phase 0 | `design/design-system.md` 없으면 생성, 있으면 로드 |
| `inspection-mode` | 컨텍스트 로드 | 생성된 design-system.md의 톤·토큰 참조 |
| `prd-builder-auto` | H6 Design Lint | 생성된 Hard Constraints를 린트 기준으로 사용 |
| 사용자 직접 요청 | 임의 | 디자인 시스템 생성/갱신 |

## 산출물

```
prd-flow/{feature-slug}/design/
├── design-system.md        # 프로젝트 전용 디자인 시스템 (템플릿: references/design-system-template.md)
└── design-references.md    # 조사한 레퍼런스 목록·선정 근거·출처
```

한 번 생성되면 프로젝트의 **디자인 SoT**다. 이후 화면 생성·린트·디스크립션 톤이 모두 이 문서를 따른다. 갱신은 사용자 요청 시에만.

## 워크플로우

### Phase 0 — 입력 수집

작업 디렉토리에서 다음을 Read로 적재한다 (없는 파일은 건너뛰고, 모두 없으면 사용자에게 제품 개요·타깃 사용자·핵심 기능 3가지를 직접 묻는다):

- `gate1/01-problem.md` — 문제 정의 (제품이 뭘 해결하는가)
- `gate1/03-personas.md` — 페르소나 (누가, 어떤 환경에서 쓰는가)
- `gate1.5/06-solution-scope.md` — 솔루션 범위
- `auto-backward/07-epics.md` — Epic 범위 (화면 밀도·컴포넌트 수요 추정)
- `research/domain-*.md` — 도메인 리서치 캐시 (있으면)

### Phase 1 — 디자인 니즈 도출

입력에서 다음을 판정해 요약표로 정리한다:

| 판정 항목 | 예시 |
|---|---|
| 제품 카테고리 | B2B 대시보드 / 커머스 / 생산성 도구 / 헬스케어 / 소셜 / 교육 |
| 플랫폼 | 웹 / 모바일 웹 / 앱 / 혼합 |
| 정보 밀도 | 데이터 밀집(테이블·차트 중심) / 콘텐츠 중심 / 태스크 중심 |
| 톤·무드 | 절제 / 활동적 / 보수적(금융·의료) / 친근 |
| 페르소나 제약 | 연령대(큰 터치 타깃·고대비), 사용 환경(야외·한 손 조작·저조도), 접근성 요구 |
| 브랜드 단서 | 사용자가 제시한 색·로고·기존 브랜드 (있으면 최우선 반영) |

### Phase 2 — 바탕 DESIGN.md 선택과 보강 리서치 (필수)

2026-09-26 사용자 지시로 사외 프로젝트의 디자인 출발점을 고정했다. 레퍼런스를 검색으로만 모으면 토큰 값을 매번 새로 지어내 결과가 투박해진다(협업 대시보드 v1에서 "디자인이 너무 밤티난다"는 지적). 그래서 검증된 사이트의 디자인 규칙 파일 하나를 바탕으로 삼고, 검색은 보강에만 쓴다.

**1. 바탕 DESIGN.md 고르기.** awesome-design-md(github.com/VoltAgent/awesome-design-md, MIT)의 `design-md/{사이트}/DESIGN.md` 가운데 Phase 1 판정과 가장 가까운 파일 1개를 고른다. 각 파일은 색 역할, 글꼴 위계, 부품 모양, 간격, 그림자, 해도 되는 것과 안 되는 것 등 9개 절로 되어 있다. 후보 목록은 저장소의 `design-md/` 폴더 이름으로 확인한다.

| 제품 카테고리 | 먼저 볼 후보 |
|---|---|
| 개발 도구·업무 대시보드·이슈 관리 | linear.app, vercel, raycast, supabase, sentry, posthog |
| 문서·지식 도구 | notion, mintlify |
| 커머스·결제 | stripe, shopify |
| AI·에이전트 제품 | claude, mistral.ai, elevenlabs |
| 소비자 앱·브랜드 | airbnb, spotify, pinterest |

- 후보 2~3개와 각각의 인상·밀도·강조색을 한 줄씩 적어 Phase 3에서 사용자에게 고르게 한다. 권고안 1개를 붙인다.
- 파일을 받는 것은 외부 다운로드다. 사용자가 고른 뒤 확인을 받고 받는다. 받은 파일은 `design/DESIGN.{사이트}.md`로 두고 출처(저장소 경로·받은 날)를 `design/design-references.md`에 적는다.
- DESIGN.md가 마케팅 사이트 기준이면(예: Linear의 다크 마케팅 캔버스) 제품 화면에는 표면 층위·강조색·모서리·간격 같은 규칙만 가져오고, 밝은 모드·정보 밀도는 Phase 1 판정에 맞게 조정한다. 가져온 것과 버린 것을 design-system.md에 표로 남긴다.

**2. taste 스킬 규칙 적용 범위 정하기.** taste-skill(github.com/Leonxlnx/taste-skill, MIT, 공통 스킬 경로 `~/.agents/skills/taste-skill/`) 가운데 화면 종류에 맞는 것만 쓴다.

| 화면 종류 | 쓸 스킬 | 쓰지 않는 이유가 있는 스킬 |
|---|---|---|
| 제품 화면(대시보드·목록·폼·설정) | `minimalist-ui`(절제 규칙), `redesign-existing-projects`(점검 목록) | `design-taste-frontend`는 스스로 "대시보드·데이터 표는 대상 아님"이라고 적는다 |
| 랜딩·소개·포트폴리오 페이지 | `design-taste-frontend`, `minimalist-ui` 또는 `high-end-visual-design` | — |

taste 스킬 규칙이 한글 표시와 부딪히면 한글을 우선한다(예: minimalist-ui는 Inter 금지를 요구하지만 한글에는 Pretendard가 필요하다). 부딪힌 규칙과 처리를 design-system.md에 적는다.

**3. 보강 리서치.** 바탕 DESIGN.md가 답하지 못하는 것만 WebSearch **1~3회**로 채운다(접근성 제약, 도메인 색 관행, 한글 글꼴 등). 추출 대상과 기록 방식은 이전과 같다. 조사 결과는 `design/design-references.md`에 레퍼런스별로 이름, 적합한 이유, 차용할 요소, 출처를 적는다.

### Phase 3 — 디자인 방향 컨펌 (사용자 1회 인터랙션)

리서치 결과로 방향 제안서를 제시하고 **1회 컨펌**받는다:

```
디자인 방향 제안 ({카테고리} / {톤}):

바탕 DESIGN.md 후보(awesome-design-md):
1. {사이트 A} — {인상·밀도·강조색 한 줄} (권고)
2. {사이트 B} — {한 줄}
적용할 taste 스킬: {minimalist-ui / redesign-existing-projects / design-taste-frontend 중 화면 종류에 맞는 것}

제안 토큰 방향:
- Primary: {색·근거 1줄} / 톤: {절제|활동적|...}
- 타이포: {본문 크기·스케일 방향}
- 밀도: {여백 중심 | 데이터 밀집}

이 방향으로 디자인 시스템을 생성할까요? (조정할 부분이 있으면 알려주세요)
```

### Phase 4 — 디자인 시스템 생성

컨펌된 방향으로 `references/design-system-template.md` 구조에 따라 `design/design-system.md`를 생성한다. 필수 규칙:

1. **모든 토큰에 구체 값**: "적절한 파랑" 금지 → `#0B6E4F` 형태. 값의 근거(레퍼런스/접근성 대비)를 주석으로.
2. **Hard Constraints 블록 필수**: 화면 생성 시 시스템 프롬프트로 적재되는 절대 규칙 6~10개. radius 스케일 고정값, accent 개수, 본문 크기, 그림자 정책, active 상태 등을 이 프로젝트 값으로 명시.
3. **구현 스택**: 프로젝트에 기술 스택 결정이 있으면 그것을 따른다(예: 빌드 없는 정적 HTML이면 CSS 변수와 브라우저 기본 요소). 결정이 없을 때만 HTML 시맨틱 요소 + Tailwind 유틸리티, 복잡 컴포넌트는 Radix UI 프리미티브를 기본으로 한다. 특정 상용/사내 컴포넌트 라이브러리 import 금지.
4. **안티패턴 섹션 필수**: 이 프로젝트에서 금지할 패턴을 리서치 근거와 함께 명시.
5. **접근성 최소선**: 텍스트 대비 WCAG AA(4.5:1), 터치 타깃 44px, 포커스 링 가시성 — 페르소나 제약이 있으면 상향.
6. **바탕 DESIGN.md와 taste 스킬 반영**: 토큰 값은 바탕 DESIGN.md의 역할·값에서 출발하고, 대비 계산으로 조정한 값만 바꾼다. taste 스킬의 금지 목록(보라·파랑 AI 그라데이션, 강조색 여러 개, 따뜻한 회색과 차가운 회색 혼용, 무거운 그림자, 대문자 제목 남발 등)을 안티패턴 절에 옮긴다.

### Phase 5 — Lint 자가 검증

생성 직후 셀프 체크:

```
□ 모든 컬러·타이포·radius·spacing 토큰에 구체 값이 있는가?
□ Hard Constraints가 생성된 토큰 값과 모순되지 않는가?
□ 컴포넌트 인벤토리가 07-epics.md의 화면 수요(테이블? 차트? 폼?)를 커버하는가?
□ 접근성 최소선(대비·터치 타깃)이 명시됐는가?
□ design-references.md에 모든 차용 요소의 출처가 있는가?
□ 바탕 DESIGN.md에서 가져온 것과 버린 것이 표로 있는가?
□ 화면을 만든 뒤 `redesign-existing-projects`의 점검 목록(글꼴·색과 표면·레이아웃·상태·문구)을 한 번 돌려 걸린 항목을 고쳤는가?
```

위반 시 해당 섹션 재생성. 이 체크리스트는 이후 `prd-to-wireframe` Phase 4의 Design Lint에서 "생성된 Hard Constraints 준수" 검사로 재사용된다.

## 갱신 정책

- 프로젝트 진행 중 디자인 시스템은 **불변**이 기본. 화면을 만들다 시스템과 충돌하면 시스템이 이긴다 (레이아웃·플로우는 화면 리서치가 결정하되, 토큰·스타일은 이 문서가 결정).
- 사용자가 방향 변경을 요청하면 Phase 3부터 재실행하고, 변경 이력을 design-system.md 하단에 기록한다.

## 의존 스킬

| 스킬 | 역할 |
|---|---|
| `domain-research` | 도메인 캐시가 있으면 Phase 1 판정에 활용 |
| awesome-design-md(외부, MIT) | 바탕 DESIGN.md 후보. 고른 파일만 사용자 확인 뒤 받는다 |
| `minimalist-ui`, `redesign-existing-projects`, `design-taste-frontend` (taste-skill, `~/.agents/skills/taste-skill/`) | 화면 종류별 절제 규칙과 점검 목록 |
| `prd-to-wireframe` | Phase 0에서 본 스킬 호출, 산출물을 화면 생성 기준으로 사용 |
| `general-ux-writing` | UX writing 규칙 (본 스킬은 비주얼만, 문구는 저쪽) |
| `inspection-mode` | 디스크립션·챗봇 컨텍스트의 디자인 참조 |
