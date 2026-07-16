# design-system.md 템플릿

`prd-flow/{feature-slug}/design/design-system.md`의 표준 골격. 모든 `{placeholder}`를 리서치·컨펌 결과의 구체 값으로 채운다. 섹션 순서는 유지하되, 프로젝트에 없는 요소(예: 차트가 없으면 차트 섹션)는 생략 가능.

```markdown
# {프로젝트명} Design System

> 생성 일시: {YYYY-MM-DD} · 레퍼런스: {제품 A, 제품 B} (근거: design-references.md)
> 카테고리: {B2B 대시보드 | 커머스 | ...} · 톤: {절제 | 활동적 | 보수적 | 친근}

## 0. Hard Constraints

화면 코드를 작성하기 전에 아래 블록을 컨텍스트에 적재한다. **절대 규칙 — 위반 시 재생성.**

​```text
You are designing UI for {프로젝트명} ({카테고리}, {톤} tone).

CORE PRINCIPLE: {이 프로젝트의 디자인 제1원칙 한 문장}

COMPONENT SOURCE
1. HTML semantic elements + Tailwind utility classes.
2. Complex components (DataGrid, Calendar, ComboBox): Radix UI
   primitives styled with Tailwind.
3. Do NOT import any proprietary/company component library.

HARD CONSTRAINTS
- Accent colors: exactly {N}. Primary {#hex}{, Secondary {#hex}}.
- Body text: {N}px / line-height {N}.
- Radius scale strictly: {0 / N / N / N / pill ...}. No in-between values.
- Shadows: {정책 — 예: none except overlay/modal}.
- Active state on interactive elements: {예: transform: scale(0.97)}.
- Touch targets: min {44}px.
- Text contrast: WCAG AA (4.5:1) minimum.
- {프로젝트 고유 제약 1~3개 — 페르소나 제약 반영}
​```

## 1. Colors

| 토큰 | 값 | 용도 | 근거 |
|---|---|---|---|
| `{colors.primary}` | {#hex} | 인터랙티브 요소 전반 | {레퍼런스/도메인 관행} |
| `{colors.primary-hover}` | {#hex} | hover/focus | |
| `{colors.canvas}` | {#hex} | 메인 배경 | |
| `{colors.surface}` | {#hex} | 카드·패널 배경 | |
| `{colors.ink}` | {#hex} | 본문·헤드라인 | 대비 {N}:1 |
| `{colors.ink-muted}` | {#hex} | 보조 텍스트 | 대비 {N}:1 |
| `{colors.border}` | {#hex or rgba} | 헤어라인·보더 | |
| `{colors.success/warning/danger}` | {#hex ×3} | 시맨틱 상태 | |

그라디언트 정책: {금지 | 허용 범위}. 다크 모드: {지원 여부·전략}.

## 2. Typography

폰트: {Display 폰트 스택} / {Body 폰트 스택 — 오픈소스 폴백 명시}

| 토큰 | 크기/행간/자간 | weight | 용도 |
|---|---|---|---|
| `{type.display}` | {N}px / {N} / {N} | {N} | 히어로·페이지 타이틀 |
| `{type.h1}`~`{type.h3}` | ... | | 섹션 계층 |
| `{type.body}` | {N}px / {N} | {400} | 본문 |
| `{type.caption}` | {N}px / {N} | | 보조 정보 |
| `{type.mono}` | {N}px | | 수치·코드 (데이터 밀집 UI일 때) |

허용 weight: {예: 400/600/700}. 금지 weight: {예: 500}.

## 3. Layout & Spacing

- Spacing 스케일: {예: 4px 기반 — 4/8/12/16/24/32/48/64}
- 컨테이너 최대 폭: {N}px · 그리드: {N}컬럼 / 거터 {N}px
- 여백 철학: {여백 중심 | 데이터 밀집 — 근거}
- 반응형 브레이크포인트: {sm/md/lg 값} · 모바일 전략: {컬럼 축소 방식}

## 4. Elevation & Shape

- Radius 스케일: `{rounded.none}` 0 / `{rounded.sm}` {N} / `{rounded.md}` {N} / `{rounded.lg}` {N} / `{rounded.pill}` 9999 — **중간값 금지**
- Shadow 정책: | Level | 값 | 적용 대상 | (예: 카드는 보더만, 모달·팝오버만 그림자)

## 5. Components

프로젝트 화면 수요(07-features.md)를 커버하는 인벤토리. 각 항목: 스타일 규칙 + 구현 소스.

| 컴포넌트 | 스타일 규칙 | 구현 |
|---|---|---|
| Primary CTA | {shape·색·패딩·상태} | button + Tailwind |
| Secondary CTA | ... | |
| 입력 필드 | {높이·보더·포커스 링·에러 상태} | input + Tailwind |
| 카드 | {radius·보더·패딩} | div + Tailwind |
| 테이블/리스트 | {행 높이·구분선·정렬 관행} | {table | Radix} |
| 모달/팝오버 | {폭·그림자·닫기 규칙} | Radix Dialog/Popover |
| 내비게이션 | {상단/사이드·높이·활성 표시} | nav + Tailwind |
| {프로젝트 고유 컴포넌트} | ... | |

## 6. Anti-patterns

이 프로젝트에서 금지하는 패턴 (근거 병기):

- {예: 장식용 그라디언트 배경 — 톤과 충돌}
- {예: 이중 accent — 레퍼런스 관행과 상충}
- {예: 320px 미만 대응 무시 — 페르소나가 소형 기기 사용}

## 7. Accessibility

- 대비: WCAG AA {4.5:1} (페르소나 제약 시 AAA {7:1})
- 터치 타깃: {44}px 이상 · 포커스 링: {스타일}
- {페르소나 고유 요구: 예. 시니어 — 최소 본문 {N}px}

## 변경 이력

| 일시 | 변경 | 사유 |
|---|---|---|
```

## 작성 규칙

- 모든 값은 구체 수치·hex. "적절히", "레퍼런스 참고" 같은 미확정 표현 금지.
- Hard Constraints(§0)와 본문 토큰(§1~5)이 모순되면 안 된다 — 생성 후 Lint로 교차 확인.
- 근거 없는 값 금지: 각 주요 토큰에 레퍼런스·접근성·도메인 관행 중 하나의 근거를 남긴다.
