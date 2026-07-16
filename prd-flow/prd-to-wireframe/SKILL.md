---
name: prd-to-wireframe
description: Discovery 산출물(prd-builder-discovery 작업 디렉토리)을 입력으로 받아 React 와이어프레임 코드를 자동 생성하는 스킬. 페르소나·V1 범위·기능 정의를 분석해 화면 목록을 도출하고, 화면별 React JSX 코드를 작성한다. 프로젝트 전용 디자인 시스템(design/design-system.md)이 없으면 design-system-builder를 호출해 생성하고, 있으면 로드해 화면 생성 기준으로 사용한다. 사용자가 "PRD에서 와이어프레임 만들어", "PRD로 프로토타입 만들어", "와이어프레임 생성", "React 화면 만들어", "PRD to wireframe", "prd-to-wireframe", "화면 자동 생성", "프로토타입 자동 생성", "Discovery 끝났으니 와이어프레임", "Phase 2 진행"과 같은 키워드를 언급하거나, prd-builder-discovery의 Gate 2 통과 후 자동 핸드오프로 호출될 때 사용한다. 자동 핸드오프와 사용자 명시 호출 둘 다 지원하며, 명시 호출 시 사용자가 작업 디렉토리 경로만 지정하면 된다.
---

# PRD to Wireframe

`prd-builder-discovery`의 Discovery 산출물을 입력받아 React 와이어프레임 코드를 자동 생성하는 스킬. Phase 2 (와이어프레임 생성) 단계 담당.

## 핵심 원칙

1. **작업 디렉토리 기반**: Notion URL이나 PDF가 아닌 `./prd-flow/{feature-slug}/` 디렉토리의 다중 파일을 입력으로 받는다
2. **V1 범위만 생성**: `gate1.5/06-solution-scope.md`의 V1 항목만 와이어프레임으로 만든다. V2·범위 외는 placeholder 또는 제외
3. **프로젝트 전용 디자인 시스템이 SoT**: 고정된 회사 디자인 시스템 대신, `design-system-builder`가 생성한 `design/design-system.md`가 이 프로젝트의 디자인 기준이다. 없으면 Phase 0에서 생성하고, 있으면 로드한다
4. **자동·수동 진입 둘 다 지원**: Discovery에서 핸드오프되거나, 사용자가 직접 호출하거나 동일하게 동작
5. **inspection-mode 연계 형식**: 산출물은 inspection-mode가 `desc` prop을 주입할 수 있는 React 컴포넌트 구조로 작성
6. **1렌더단위 = 1파일**: 모달·다이얼로그·오버레이 등 독립적으로 열리는 뷰는 화면 컴포넌트 안에 인라인 정의하지 않고 별도 파일로 분리해 `import`한다. 후속 파이프라인(figma sync의 routes.json 화면-파일 매핑, wireframe-description의 컴포넌트 단위 명세)이 **파일 단위**로 동작하므로, 인라인 정의는 동기화·명세 대상에서 누락된다

## 트리거 조건

다음 중 하나에 해당하면 이 스킬을 시작한다.

- 사용자가 "PRD로 와이어프레임", "PRD로 프로토타입", "와이어프레임 생성", "React 화면 만들어" 명시
- `prd-builder-discovery`의 Gate 2 통과 후 자동 핸드오프
- 사용자가 작업 디렉토리(`./prd-flow/{feature-slug}/`)를 명시하며 와이어프레임 생성 요청

## 진입 모드

### Mode 1 · Auto Handoff (Discovery → Wireframe)

`prd-builder-discovery`가 Macro Gate 2 통과 후 자동 호출. 호출 형식:

```
prd-to-wireframe 호출
  working_dir: ./prd-flow/{feature-slug}/
  handoff_from: prd-builder-discovery
```

이 모드에서는 추가 사용자 확인 없이 곧장 Phase 0 컨텍스트 적재에 들어간다 (단, `design/design-system.md`가 없어 design-system-builder가 새로 생성해야 하면 그 스킬의 방향 컨펌 1회는 발생한다).

### Mode 2 · Manual Trigger (사용자 명시 호출)

사용자가 직접 호출. 진입 시 **작업 디렉토리 경로**(`./prd-flow/{feature-slug}/`)만 확인한다 (없으면 사용자가 입력). 확인 후 곧장 Phase 0 진입.

## 작업 디렉토리 입력 파일

| 파일 | 용도 |
|---|---|
| `context.json` | 프로젝트 메타 (feature_slug, design_system 경로, ux_writing_skill 등) |
| `gate1/01-problem.md` | 화면별 핵심 사용자 흐름 파악 |
| `gate1/03-personas.md` | 화면별 메인 사용자 매핑 |
| `gate1.5/06-solution-scope.md` | V1에 포함될 화면·기능 범위 |
| `auto-backward/07-features.md` | 각 화면의 기능 단위 컴포넌트 도출 |
| `auto-backward/08-ai-agent-spec.md` (있을 때) | AI 호출이 UI에 노출되는 영역 표시 |
| `auto-backward/09-priorities.md` | P0 화면 우선 생성 → P1 → P2 순 |
| `research/domain-*.md` (있을 때) | 도메인 리서치 캐시 — 화면 정보 설계의 정합성 참고 근거 (단정 금지, 출처 병기) |

## 워크플로우

### Phase 0 — 컨텍스트 적재

1. **context.json Read**: 작업 디렉토리의 `context.json`을 읽어 프로젝트 메타를 확인한다.

```json
{
  "feature_slug": "...",
  "research_dir": "research/",
  "design_system": "design/design-system.md",
  "ux_writing_skill": "general-ux-writing",
  "notion_upload": false,
  "created_at": "..."
}
```

2. **디자인 시스템 확인·생성·로드**: `prd-flow/{feature-slug}/design/design-system.md` 존재 여부를 확인한다.
   - **없으면**: `design-system-builder` 스킬을 호출해 생성한다. 이 스킬은 페르소나·문제 정의·기능 요구사항에서 디자인 니즈를 도출하고, 레퍼런스를 웹 리서치(3~5회)한 뒤, **사용자 방향 컨펌 1회**를 거쳐 `design/design-system.md` + `design-references.md`를 생성한다.
   - **있으면**: 그대로 로드한다. `design/design-references.md`가 있으면 함께 참조.
3. **UX writing 적재**: `general-ux-writing/SKILL.md` + `general-ux-writing/references/ux-writing.md` (7개 섹션 보편 UX writing 가이드).
4. **Hard Constraints 격상**: 로드한 design-system.md의 **§0 Hard Constraints 블록**을 화면 생성의 시스템 제약(작업 컨텍스트 최상위 규칙)으로 격상한다. 이후 모든 Phase의 생성·검증이 이 블록을 기준으로 동작한다.
5. **워크플로우 입력 파일 Read**: 위 표의 Discovery 산출물을 모두 읽는다 (`research/domain-*.md`는 있을 때만).

### Phase 1 — 화면 목록 도출

다음 알고리즘으로 화면 목록을 생성한다.

```
function derive_screens():
    screens = []
    
    # 1. V1 범위의 기능 항목 추출
    v1_features = solution_scope.v1_items
    
    # 2. 페르소나별 JTBD를 기능과 매핑
    for persona in personas.main_and_sub:
        for jtbd in persona.jtbds:
            related_features = match(jtbd, v1_features)
            
            # 3. 기능 묶음을 화면 단위로 그룹화
            screen_groups = group_by_user_flow(related_features)
            
            for group in screen_groups:
                screens.append({
                    "name": derive_screen_name(group),
                    "primary_persona": persona,
                    "features": group,
                    "priority": max(features.priority)
                })
    
    # 4. P0 우선 정렬
    return sort_by_priority(screens)
```

도출된 화면 목록을 사용자에게 보여주고 추가/제외 의향을 묻는다. **인터랙션 1회**:

```markdown
V1 범위 분석 결과 {N}개 화면 도출:

| # | 화면명 | 메인 페르소나 | 우선순위 | 핵심 기능 |
|---|---|---|---|---|
| 1 | {화면명} | {페르소나} | P0 | {요약} |
| 2 | ... | ... | P0 | ... |
| ... |

추가/제외할 화면이 있는지? 없으면 "진행"으로 답.
```

응답이 "진행"이면 Phase 1.5(레퍼런스 리서치) 진입. 추가·제외 요청이 있으면 화면 목록만 수정 후 다시 확인.

> 전체 순서: 화면 목록 도출(1) → 인터페이스 레퍼런스 리서치(1.5) → 화면별 정보 설계 컨펌(1.7) → 컴포넌트 분해(2) → 코드 작성(3) → 목업 데이터 주입(3, MOCK_*).

### Phase 1.5 — 인터페이스 레퍼런스 리서치 (필수)

화면 목록 확정 후, 화면별 정보 설계(Phase 1.7) 전에 실행한다. 레퍼런스가 정보 설계를 뒷받침한다.

> 이 단계는 Discovery의 외부 리서치(경쟁 "기능" 패턴)와도, design-system-builder의 레퍼런스 리서치(토큰·비주얼 방향)와도 다르다. 여기서는 화면 단위로 "UI를 어떻게 표시하는가"(레이아웃·정보 계층·인터랙션 패턴)를 조사한다.

**검색 입력 2종**

| 입력 | 출처 |
|------|------|
| 컴포넌트 유형 | Phase 1 도출 화면의 주요 컴포넌트 (wizard, table, progress, dashboard 등) |
| 요구사항 | PRD V1 기능 정의 + 페르소나 JTBD 핵심 동작 |

**실행 방식**
- 화면 단위로 검색 쿼리 구성 (1화면 1~2회)
- 쿼리 예시: `"{컴포넌트 유형} UX best practices 2024"`, `"{기능 요구사항} UI patterns"`
- 검색 결과에서 레이아웃 구조·인터랙션 패턴·정보 계층만 추출. 원문 전체 적재 금지.

**디자인 시스템 우선 원칙**
Phase 0에서 로드한 프로젝트 생성물 `design/design-system.md`가 최우선이다.
- 리서치 결과 → "무엇을 배치할지, 어떤 흐름으로 구성할지" 결정
- 생성된 디자인 시스템 → "어떤 토큰·컴포넌트 스타일로 구현할지" 결정
- 충돌 시 디자인 시스템 우선. 리서치 결과가 design-system.md **§6 Anti-patterns**에 해당하면 적용하지 않고 폐기한다.

**산출**
- 화면별 UX 의사결정 요약 3~5줄 → Phase 1.7 정보 설계의 직접 입력으로 사용
- 적용한 레퍼런스 출처를 생성 코드 주석에 1줄 병기

### Phase 1.7 — 화면별 정보 설계 (필수 · 컨펌 게이트)

레퍼런스 리서치 직후, 컴포넌트 분해·코드 작성 전에 실행한다. **각 화면이 "무엇을·어떤 방식으로 표시할지"를 PRD의 페르소나와 문제 정의에 근거해 먼저 설계하고, 사용자 컨펌을 받는다.** 이 게이트 없이 Phase 2(컴포넌트 분해)로 넘어가지 않는다.

**설계 근거 (필수 2종)**
- 페르소나(`gate1/03-personas.md`): 메인 페르소나의 JTBD·Pain Point·사용 맥락. 이 사람이 화면에서 가장 먼저 봐야 하는 정보가 최상단.
- 문제 정의(`gate1/01-problem.md`): 메인 문제를 직접 해소하는 정보를 우선 배치. 문제와 무관한 정보는 후순위 또는 제외.

**화면별 정보 설계 표 (각 화면마다 작성)**

```markdown
#### 화면: {화면명} (메인 페르소나: {페르소나})

| 표시 정보 | 표시 방식 | 우선순위 | 근거 (페르소나/문제) |
|---|---|---|---|
| {정보 항목} | {카드/표/리스트/배지/차트 등 표시 형태와 정보 계층} | 1차/2차 | {이 페르소나의 어떤 JTBD·Pain 또는 어떤 문제에 대응하는지} |
```

- 표시 방식은 정보 구조·계층까지만 정의한다. 색상·폰트·여백 등 시각 디테일은 Phase 3에서 디자인 시스템이 결정한다.
- 계산 수식·임계값은 여기서 확정하지 않는다(디스크립션 SoT). "어떤 값을 보여줄지"까지만.
- `research/domain-*.md` 캐시가 있으면 정보 설계의 정합성 참고 근거로 활용한다. 단, 리서치는 확정 사양이 아니라 참고 근거 — 단정 금지, 사용자 제공 지식이 최우선.

**컨펌 게이트**
- 화면 전체의 정보 설계 표를 사용자에게 제시하고 컨펌을 받는다.
- 수정 요청 시 해당 화면 정보 설계만 갱신 후 재확인.
- 컨펌 완료된 정보 설계가 Phase 2 컴포넌트 분해·Phase 3 코드 생성의 직접 입력이 된다.

### Phase 2 — 화면별 컴포넌트 분해

각 화면에 대해 컴포넌트 트리를 정의한다.

```
화면 = Layout 
       └── Section 1 (예: 필터·검색)
            ├── Component A
            └── Component B
       └── Section 2 (예: 메인 콘텐츠)
            ├── Component C
            └── Component D
```

**매핑 규칙**

- 화면 요소를 `design/design-system.md` **§5 Components 인벤토리**에 매핑한다. 각 인벤토리 항목의 스타일 규칙·구현 소스를 그대로 따른다.
- 복잡한 컴포넌트(DataGrid, Calendar, ComboBox 등)는 인벤토리의 COMPONENT SOURCE 규칙대로 **Radix UI 프리미티브 + Tailwind 스타일링**으로 구현한다. 사내/상용 컴포넌트 라이브러리 import 금지.
- **인벤토리에 없는 컴포넌트가 필요하면**: design-system.md §5에 해당 컴포넌트를 그 문서의 스타일 규칙(토큰·shape·상태 정의 방식)에 맞춰 추가하고, 문서 하단 **변경 이력**에 추가 사실을 기록한다. 임의 스타일로 인벤토리 밖 컴포넌트를 만들지 않는다.

### Phase 3 — React JSX 코드 생성

각 화면을 단일 `.jsx` 파일로 작성. 디렉토리 구조:

```
./prd-flow/{feature-slug}/wireframe/
├── App.jsx                        # 라우터/네비게이션
├── screens/
│   ├── 01-{ScreenName}.jsx
│   ├── 02-{ScreenName}.jsx
│   ├── ...
│   └── {ModalName}Modal.jsx       # 모달·다이얼로그도 화면 단위로 분리 (부모에 인라인 정의 금지)
├── components/                    # 화면 간 공유 컴포넌트
│   ├── Header.jsx                 # design-system.md §5의 내비게이션 규칙에 따른 공통 레이아웃
│   ├── ModalOverlay.jsx           # 공용 오버레이 등 재사용 UI
│   └── ...
└── manifest.json                  # 화면 메타 (inspection-mode·후속 스킬 입력)
```

> 모달은 부모 화면이 `import` 후 `open`/`onClose`/데이터 props로 제어한다. routes.json·manifest에 독립 항목으로 등록될 수 있으면 `screens/`, 순수 재사용 UI(오버레이·버튼군)는 `components/`에 둔다.

#### `manifest.json` 스키마

```json
{
  "feature_slug": "team-notification-settings",
  "design_system": "design/design-system.md",
  "ux_writing_source": "general-ux-writing",
  "screens": [
    {
      "id": "screen-01",
      "name": "알림 설정",
      "file": "screens/01-NotificationSettings.jsx",
      "primary_persona": "팀 관리자",
      "priority": "P0",
      "features_ref": ["F-1", "F-3"],
      "components": [
        {
          "name": "ChannelPrioritySelector",
          "ds_component": "Select (design-system.md §5, Radix Select + Tailwind)",
          "feature_ref": "F-1"
        }
      ]
    }
  ]
}
```

- `design_system`: 작업 디렉토리 기준 상대 경로 (`design/design-system.md` 고정)
- `ux_writing_source`: UX writing 스킬명 (`general-ux-writing` 고정)
- `ds_component`: design-system.md §5 인벤토리의 항목명 + 구현 소스

`manifest.json`은 inspection-mode·wireframe-description의 핵심 입력. 누락 시 후속 스킬이 코드를 직접 파싱해야 하므로 반드시 생성.

#### 코드 작성 규칙

- React 함수 컴포넌트 + Hooks 사용
- 스타일링: HTML 시맨틱 요소 + Tailwind 유틸리티 클래스. 복잡 컴포넌트만 Radix UI primitives + Tailwind (design-system.md §5의 구현 소스 규칙 준수)
- 모든 색·타이포·radius·spacing은 design-system.md 토큰의 구체 값만 사용. 임의 hex/px 값 도입 금지
- 상태(useState)는 화면 단위로 격리, 글로벌 상태 사용 금지
- 더미 데이터는 화면 상단의 const로 분리 (`MOCK_*` 접두사)
- **모달·다이얼로그·오버레이는 화면 컴포넌트 안에 인라인 함수로 정의하지 않는다.** 별도 파일로 추출하고 부모가 `import` 후 `open`/`onClose` props로 제어. 인라인 정의 시 figma sync가 동기화 대상 파일을 못 찾고(routes.json 매핑이 dead-code를 가리킴), 시안을 반영해도 화면에 안 뜨는 결함이 발생한다
- inspection-mode 연계 위해 모든 인터랙티브 컴포넌트에 `desc=""` prop placeholder 추가 (빈 문자열, 후속에서 wireframe-description이 채움)
- UI 텍스트는 `general-ux-writing/references/ux-writing.md`의 7개 섹션 준수

### Phase 4 — 자체 검증 (Design Lint)

Lint 기준은 단일하다: **생성된 design-system.md §0 Hard Constraints + §7 Accessibility 준수**.

| 검증 항목 | 위반 시 |
|---|---|
| design-system.md §0 Hard Constraints 위반 (radius 스케일 외 값, accent 개수 초과, 본문 크기·그림자·상태 정책 위반 등 — 항목은 생성된 문서가 정의) | 즉시 재생성 (3회까지) |
| design-system.md 토큰 외 색상 hex/rgb·폰트 사이즈·여백 직접 사용 | 즉시 재생성 |
| §5 인벤토리 외 컴포넌트를 인벤토리 갱신 없이 사용 | 즉시 재생성 |
| §7 Accessibility 최소선 위반 (대비 WCAG AA, 터치 타깃 44px, 포커스 링 가시성 — 페르소나 제약 시 상향 값) | 즉시 재생성 |
| §6 Anti-patterns에 해당하는 패턴 사용 | 즉시 재생성 |
| 한국어 외 UI 텍스트 (단, 영문 고유명사 제외) | 즉시 재생성 |
| 화면 파일에 모달·다이얼로그·오버레이가 인라인 함수로 정의됨 | 별도 파일로 추출 후 재생성 |
| UX writing 자가 검증 5단계 미통과 | 즉시 재생성 |

3회 재생성 후에도 위반이 남으면 `prd-builder-auto`를 `wireframe_review` 모드로 호출해 H6 (Design Lint Hard Stop) 발동. 사용자에게 의도된 위반인지 확인 요청.

### Phase 5 — Coverage 검증

V1 범위의 모든 기능이 와이어프레임에 반영됐는지 검증.

```
function coverage_check():
    v1_features = solution_scope.v1_items
    covered_features = collect_feature_refs(manifest.screens)
    
    missing = v1_features - covered_features
    if missing:
        report_to_user(
            "V1 범위에 정의됐으나 와이어프레임에 누락된 기능: " + missing
        )
```

누락이 발견되면 사용자에게 다음 옵션 제시:

| 선택 | 동작 |
|---|---|
| "추가 화면 생성" | 누락 기능을 위한 새 화면 자동 생성 |
| "기존 화면에 통합" | 어느 화면에 통합할지 사용자가 지정 |
| "V1 범위에서 제외" | `gate1.5/06-solution-scope.md`를 V2로 이동 (단, Gate 1.5 파일 수정은 사용자 컨펌 필수) |

### Phase 6 — 산출물 전달 및 핸드오프

1. 사용자에게 와이어프레임 디렉토리 위치 안내
2. 화면 목록 + 메인 페르소나 매핑 요약 제시
3. 다음 단계 안내:
   - `wireframe-description`으로 컴포넌트 디스크립션 작성
   - `inspection-mode`로 DescTooltip 주입 + 챗봇 모드 활성화
   - **개발 진행 시 `/ai-dlc` 호출**: ai-dlc가 `prd-flow/{feature-slug}/`를 감지해 `notion-pages/full-prd.md` + `wireframe/*.jsx` + 디스크립션을 `requirements/`(화면은 `requirements/screens/`)로 인테이크하고, 유저스토리→유닛 분할·설계·코드 생성으로 진행한다

자동 핸드오프 모드면 사용자 확인 없이 다음 스킬 호출. 수동 호출 모드면 사용자 응답 대기.

## 의존 스킬

| 스킬 | 역할 | 호출 시점 |
|---|---|---|
| `design-system-builder` | 프로젝트 전용 `design/design-system.md` 생성 (없을 때) / 갱신 | Phase 0 |
| `domain-research` | `research/domain-*.md` 캐시 — 정보 설계 정합성 참고 근거 | Phase 1.7 (캐시가 있을 때) |
| `general-ux-writing` | UX writing 규칙 (7개 섹션) | Phase 0 자동 적재 |
| `prd-builder-auto` | Design Lint Hard Stop (H6) | Phase 4에서 위반 3회 반복 시 |
| `wireframe-description` / `inspection-mode` | 디스크립션 작성 / DescTooltip 주입 | Phase 6 핸드오프 |
| `ai-dlc` | PRD + 와이어프레임 인테이크 → 설계·코드 생성 | Phase 6 핸드오프 (개발 진행 시) |

## 산출물 (외부 인터페이스)

| 파일 | 소비자 |
|---|---|
| `wireframe/App.jsx` + `wireframe/screens/*.jsx` | `wireframe-description` (디스크립션 작성), `inspection-mode` (DescTooltip 주입), `ai-dlc` (requirements/screens/ 인테이크) |
| `wireframe/manifest.json` | `wireframe-description`, `inspection-mode`, `ai-dlc` (유저스토리-화면 매핑) |
| `wireframe/components/*.jsx` | 화면 간 공유 컴포넌트, 후속 스킬이 참조 |
| `design/design-system.md` (§5 갱신 시) | 이후 모든 화면 생성·린트·디스크립션 톤의 기준 |

## 작성 가드레일

- React 함수 컴포넌트 + Hooks. Class 컴포넌트 금지
- 외부 의존성 최소화: Tailwind + Radix UI primitives + lucide-react 정도까지. 사내/상용 컴포넌트 라이브러리 import 금지
- 절대 경로 import 금지 (`@/...` 같은 별칭 없음)
- 한 파일 500줄 초과 시 컴포넌트 분리
- 모든 인터랙티브 컴포넌트에 `desc=""` prop 자리 마련 (inspection-mode 연계용)
- 더미 데이터는 `MOCK_*` 접두사로 화면 상단 const로 분리
- TypeScript 사용하지 않음 — 빠른 프로토타입 우선

## 실행 시 첫 응답 패턴

### Auto Handoff 모드

prd-builder-discovery가 호출했음을 인지하고 곧장 Phase 0 컨텍스트 적재 → Phase 1 화면 목록 도출까지 자동 진행. 사용자 응답이 필요한 시점은 최대 세 번이다: (design-system.md 신규 생성 시) 디자인 방향 컨펌, Phase 1 화면 목록 확인, Phase 1.7 화면별 정보 설계 컨펌.

### Manual Trigger 모드

1. 작업 디렉토리 경로 확인 (없으면 질문)
2. Phase 0~1 진행 후 화면 목록 확인 질문 (design-system.md가 없으면 그 전에 디자인 방향 컨펌 1회)
