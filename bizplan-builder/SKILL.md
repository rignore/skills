---
name: bizplan-builder
description: B2B SaaS, AI 에이전트, 산업용 IoT(IIoT) 신사업 사업계획서를 단계별 대화형으로 작성하고 검증하는 스킬. 한 번에 완성하지 않고 4개 Phase(시장·문제 정의 → 기술·규제 검증 → 비즈니스 모델·단위 경제성 → 해자·통합 스토리텔링)로 분할하여, 각 Phase마다 글로벌 탑티어 VC 심사역과 컨설팅 펌 수준의 7개 전문가 페르소나(CEO, Top-tier VC, CFO, GTM Strategy Lead, B2B Enterprise Sales, Staff Engineer/CTO, Legal & Compliance)가 킬러 질문(Killer Questions)과 정량 가드레일로 가설을 스트레스 테스트한다. Kill Switch는 Generator-Evaluator 검증 루프로 체크리스트 1:1 대조 후에만 판정하고, 미명시 가정은 Silent Default로 추적하며, 시장·벤치마크 수치는 외부 리서치 프로토콜로 출처를 강제한다. 산출물의 진실의 원천은 로컬 파일이고 Notion 업로드는 옵션이다. LTV:CAC, CAC Payback, Rule of 40, NRR 등 단위 경제성 벤치마크를 자동 검증하고, MECE·Minto Pyramid·확증 편향 방지 등 컨설팅 사고 체계를 적용한다. 사용자가 "사업계획서 작성", "사업계획서 검토", "BP 만들어", "비즈니스 플랜", "투자 제안서", "피치덱 검토", "신사업 검증", "VC 관점 리뷰", "단위 경제성 검토", "사업 모델 검증", "Lean Canvas", "Pitch Deck", "신규 사업 기획", "사업 타당성", "투자자 검토" 같은 키워드를 언급하거나 신사업/제품 라인의 정식 사업계획서를 작성·검토하려는 의도를 보일 때 반드시 이 스킬을 사용한다. 단순 PRD나 기능 단위 기획은 prd-builder를 사용하고, 이 스킬은 사업·수익 모델 단위의 검증에 한정한다.
---

# Business Plan Builder

B2B SaaS / AI 에이전트 / IIoT 신사업 사업계획서를 단계별로 작성·검증하는 스킬. 한 번에 끝내지 않고, 4개 Phase로 나누어 글로벌 탑티어 VC와 컨설팅 펌 수준의 다중 전문가 페르소나가 가설을 스트레스 테스트한다. 산출물의 진실의 원천(SoT)은 로컬 작업 디렉토리이며, Notion 업로드는 옵션이다.

## 핵심 원칙

1. **단계별 대화형**: 각 Phase 완료 시 반드시 사용자 컨펌을 받고 다음 Phase로 진행. 한 번에 전체 사업계획서를 작성하지 않는다.
2. **Kill Switch + 검증 루프 강제**: 각 Phase에 통과 조건이 있고, 판정은 반드시 검증 루프(`references/evaluator-loop.md`)를 거친다 — 체크리스트 전 항목을 산출물과 1:1 대조한 결과를 먼저 출력한 뒤에만 통과를 선언할 수 있다. 미통과 시 다음 Phase 진입을 차단하고 재기획을 요구한다.
3. **페르소나 교차 검증**: 단일 부서 시각의 맹점을 차단하기 위해, 각 Phase에 적합한 페르소나 2명이 킬러 질문으로 공격적 피드백 제공. 🔴 차단 이슈는 Kill Switch 항목으로 승격된다.
4. **정량 가드레일 자동 적용**: 단위 경제성 지표를 자동 계산하고 벤치마크 미달 시 경고. 상세는 `references/unit-economics-benchmarks.md`.
5. **반증 가능한 가설 강제**: 검증 불가능한 모호한 서술은 반려. 상세는 `references/writing-guardrails.md`.
6. **Silent Default 추적**: 사용자가 명시하지 않았고 출처도 없는 추정값은 전부 SD로 기록하고, 임계 누적 시 작성을 중단해 일괄 확인받는다. 미확인 SD가 남아 있으면 Kill Switch 판정에 진입하지 않는다. 상세는 `references/silent-defaults.md`.
7. **수치에 출처 강제**: 시장·경쟁·벤치마크 수치는 외부 리서치 프로토콜(`references/research-protocol.md`)로 확보하고 `[출처: 도메인, 조회일]`을 병기한다. Phase별 필수 리서치 지점을 스킵하지 않는다.
8. **로컬 파일 SoT**: 모든 산출물의 진실의 원천은 `bizplan/{slug}/` 로컬 파일이다. Notion 업로드는 context.json `notion_upload: true`일 때만, **Phase 통과 시점에만** 수행한다. 중간 미확정 산출물을 Notion에 쓰지 않는다.

## 작성 가드레일 (모든 Phase 공통)

모든 산출물은 다음 규칙을 따른다. 상세는 `references/writing-guardrails.md`.

- **Answer First (Minto Pyramid)**: 결론 → 근거 → 데이터 순서
- **MECE 원칙**: 시장·수익·고객 분류 시 교집합·누락 금지
- **개조식 우선**: C-level 임원 검토용 구조
- **수치 기반 서술**: 정성적 수사 금지, 모든 주장은 수치·기간·대상으로 치환
- **출처 병기**: 외부에서 확보한 수치는 `[출처: 도메인, 조회일]` 필수
- **반증 가능성**: 측정 가능한 형태의 가설만 허용
- **레드팀 사고**: 최악의 시나리오에서도 버틸 수 있는지 스트레스 테스트
- **한국어 우선, 고유명사 보존**: LTV, CAC, MECE 등 원문 유지

## 산출물 관리 (로컬 SoT)

### 작업 디렉토리 구조

Phase 0에서 생성한다. 기본 경로: `./bizplan/{business-slug}/`.

```
bizplan/{business-slug}/
├── context.json                  # 사업 메타·옵션 (모든 후속 판단의 단일 출처)
├── research/                     # 리서치 캐시 (research-protocol.md)
│   └── {topic}.md
├── phase1/
│   ├── 01-problem.md             # 문제 정의서
│   ├── 02-market-sizing.md       # TAM/SAM/SOM 산정표
│   ├── 03-icp.md                 # ICP 카드
│   └── 04-value-matrix.md        # 다중 페르소나 가치 제안
├── phase2/
│   ├── 05-architecture.md
│   ├── 06-compliance-matrix.md
│   ├── 07-data-governance.md
│   └── 08-infra-cost.md
├── phase3/
│   ├── 09-business-model-canvas.md
│   ├── 10-unit-economics.md
│   ├── 11-financial-projection.md
│   ├── 12-pricing.md
│   └── 13-sales-model.md
├── phase4/
│   ├── 14-moat.md
│   ├── 15-positioning.md
│   ├── 16-narrative.md           # 통합 내러티브 5기둥
│   └── 17-redteam.md
├── decision-log.md               # SD·리서치 출처·피드백 채택·변경 이력
├── review-log.md                 # 페르소나 리뷰 원문 로그
├── guardrail-results.md          # Phase 3 정량 가드레일 자동 계산 결과
├── one-page-summary.md           # Phase 1·3·4 통과 시 점진 갱신
└── business-plan-full.md         # Phase 4 통과 시 전체 통합본 생성
```

### context.json 스키마

작업 디렉토리 생성 직후 작성한다. 이후 모든 Phase가 사업 유형·단계·옵션 판단의 단일 출처로 참조한다.

```json
{
  "business_slug": "protect-go-saas",
  "business_name": "Protect GO AI",
  "business_type": "AI 에이전트",
  "stage": "Series A",
  "purpose": "IR",
  "stakeholders": ["CEO", "리드 투자자"],
  "notion_upload": false,
  "notion_parent_page": null,
  "notion_page_url": null,
  "silent_default_threshold": 3,
  "created_at": "2026-07-22T10:00:00+09:00"
}
```

| 필드 | 의미 |
|---|---|
| `business_type` | B2B SaaS / AI 에이전트 / IIoT / 하이브리드 — Phase 2 필수 항목 분기 |
| `stage` | Pre-seed / Seed / Series A↑ — 가드레일 가중치 차등 |
| `purpose` | 내부 검토 / IR / 파트너십 — 산출물 톤 + IR 시 리서치 강화 규칙 적용 |
| `notion_upload` | 기본 `false`. `true`일 때만 Notion 뼈대 생성 + Phase 통과 시 반영 |
| `notion_page_url` | 뼈대 페이지 생성 후 기록 (`notion_upload: true` 시) |
| `silent_default_threshold` | SD 누적 임계 (기본 3) |

### Phase 파일 해석 규칙

`phases/` 파일에 "Notion Phase N 섹션에 채운다"로 표기된 산출물 지시는 **"해당 phaseN/ 로컬 파일로 작성하고, Phase 통과 시점에 notion_upload가 true면 Notion 해당 섹션에 반영한다"**로 읽는다. 로컬 작성이 항상 선행한다.

## 워크플로우

### 0단계 - 시작 전 확인

사업계획서 작성 요청 시 절대 바로 작성에 들어가지 않는다. `phases/phase0-setup.md`를 읽고 6가지 확인 항목 질문 → 작업 디렉토리 + context.json 생성 → (notion_upload 시) Notion 뼈대 페이지 생성 → Phase 1 진입 의사 확인.

### Phase 진행

각 Phase 진입 시 해당 `phases/phaseN-*.md` 파일을 읽고 그 안의 핵심 질문·산출물 스펙·Kill Switch를 따른다. 각 Phase는 다음 순서로 진행한다:

1. **필수 리서치 수행**: `references/research-protocol.md`의 해당 Phase 적용 지점을 확인하고, 산출물 작성 전에 필수 지점 리서치를 수행. 결과는 출처 병기 + `research/` 캐시 저장
2. **산출물 로컬 작성**: 해당 `phaseN/` 파일에 작성. 작성 중 미명시 추정값 발생 시 SD로 decision-log에 즉시 기록, 임계(기본 3) 도달 시 작성 중단하고 일괄 확인
3. **산출물 제시**: 사용자에게 산출물 + 해당 Phase 리서치 집계(건수·출처) 제시
4. **페르소나 리뷰**: `reviewers/routing.md`에 따라 해당 Phase 페르소나 2명 호출 (SD 목록·리서치 캐시 목록을 프롬프트에 명시) → 채택할 피드백 선택받기 → 채택 결과 decision-log 기록. 🔴 차단 이슈는 Kill Switch 항목으로 승격
5. **SD 일괄 확인**: 미확인 SD가 남아 있으면 `references/silent-defaults.md` §5 형식으로 확인. 전부 해소해야 다음 단계 진입
6. **Kill Switch 검증 루프**: `references/evaluator-loop.md` 절차로 체크리스트 1:1 대조 목록 출력 → 판정. Phase 3는 `references/unit-economics-benchmarks.md` 자동 계산(`guardrail-results.md` 기록)을 대조의 결정론 입력으로 선행
7. **통과 처리**: 로컬 산출물 확정 → `one-page-summary.md` 갱신(Phase 1·3·4) → notion_upload가 true면 Notion 해당 섹션 반영 + 상태 변경 → 다음 Phase 진입 의사 확인

### Phase 목록

| Phase | 파일 | 핵심 산출물 | 페르소나 |
|---|---|---|---|
| 0 | `phases/phase0-setup.md` | 작업 디렉토리 + context.json (+ Notion 뼈대) | - |
| 1 | `phases/phase1-market-problem.md` | 문제 정의, TAM/SAM/SOM, ICP | CEO, GTM Lead |
| 2 | `phases/phase2-architecture-compliance.md` | 아키텍처, 규제 매트릭스, 데이터 거버넌스 | Staff Engineer, Legal |
| 3 | `phases/phase3-business-model-economics.md` | 단위 경제성, 가격 정책, 재무 프로젝션 | B2B Sales, CFO |
| 4 | `phases/phase4-moat-synthesis.md` | 해자 정의, 경쟁 포지셔닝, 통합 내러티브 | Top-tier VC, CEO |

## 페르소나 시스템

각 Phase에 적합한 페르소나만 선택적으로 호출. 라우팅 표는 `reviewers/routing.md`. 페르소나 정의 파일:

- `reviewers/ceo-founder.md` — 시장 생존성, 피벗 가능성, 장기 비전
- `reviewers/vc-partner.md` — 방어 가능한 해자, 자본 효율성, 10배 ROI
- `reviewers/cfo.md` — 단위 경제성, Burn Rate, 런웨이
- `reviewers/gtm-lead.md` — 정밀 ICP, 다크 퍼널, 가치 제안 5기둥
- `reviewers/b2b-sales.md` — PLG/SLG 정합성, ACV, 세일즈 트리거
- `reviewers/staff-engineer.md` — 멀티 테넌시, 제로 트러스트, AI 환각 제어
- `reviewers/legal-compliance.md` — EU AI Act, GDPR, IP 귀속, Audit Trail

페르소나 출력 형식 (모든 페르소나 공통):

```
[페르소나명]
🟢 강점: ...
🟡 보완 제안: ...
🔴 차단 이슈: ... (Kill Switch 항목으로 승격)
❓ 킬러 질문: ... (사용자가 추가 답변해야 할 사항)
```

호출 시 프롬프트에 다음을 명시한다: ① 해당 Phase의 SD 목록(상태 포함) ② 참조 가능한 `research/` 캐시 목록. CFO·Top-tier VC는 `가정 유지` 상태 SD를 킬러 질문의 우선 대상으로 삼는다.

## Silent Default 추적

미명시 추정값은 전부 `decision-log.md`에 SD로 기록하고 상태(미확인/확정/수정/가정 유지)를 관리한다. 리서치 기반 값(출처 기록)은 SD에서 제외. Phase당 누적 임계 도달 시 작성 중단 + 일괄 확인, Kill Switch 판정 전 미확인 SD 0개가 선행 조건. `가정 유지` SD는 One-Page Summary 리스크 섹션에 노출. 상세는 `references/silent-defaults.md`.

## 외부 리서치 프로토콜

Phase별 필수 리서치 지점과 검색 상한, 출처 병기·캐시·SD 회계 규칙은 `references/research-protocol.md`를 따른다. 핵심: 필수 지점 스킵 금지, 지점당 1~2회 상한, 사용자 제공 지식 최우선, 복수 출처 시 범위 제시, 하향식 시장 수치는 상향식 교차 필수.

## 인지 편향 탐지

모든 Phase에서 자동 적용되는 편향 감지 로직. 상세는 `references/cognitive-biases.md`.

- 확증 편향 (Cherry-picking 감지)
- 자동화 편향 (AI 산출물 맹신 차단)
- MECE 위배 (텍사스 명사수 오류)
- 검증 불가능한 서술 반려
- 하향식 시장 추정 → 상향식 보강 요구 (research-protocol §3과 연동)

## Notion 작업 (옵션)

`notion_upload: true`일 때만 수행한다. 페이지 구조 표준은 `references/notion-template.md`.

- **뼈대 생성**: Phase 0에서 1회. 페이지 URL을 context.json `notion_page_url`에 기록
- **내용 반영**: 각 Phase 통과 시점에만 해당 섹션 + Phase 상태 프로퍼티 업데이트. 작성 중·검토 중 산출물은 Notion에 쓰지 않는다 (토큰 비용·중간본 오염 방지)
- **로그 동기화**: 페르소나 리뷰 로그·변경 이력은 로컬(`review-log.md`·`decision-log.md`)이 원본. Phase 통과 시 채택 요약만 Notion 로그 섹션에 반영
- **최종**: Phase 4 통과 시 One-Page Summary 완성 + `가정 유지` SD 리스크 노출

`notion_upload: false`이면 전 과정 로컬 파일로만 진행하고, Phase 4 통과 시 `business-plan-full.md` 통합본을 생성해 전달한다.

## 트리거 키워드

다음 키워드/맥락에서 무조건 트리거:

- "사업계획서 작성/만들어/검토", "BP", "비즈니스 플랜", "사업 계획"
- "투자 제안서", "IR 자료", "피치덱"
- "신사업 검증", "신규 사업 기획", "사업 타당성"
- "VC 관점 리뷰", "투자자 검토"
- "단위 경제성 검토", "Unit Economics"
- "사업 모델 검증", "비즈니스 모델 캔버스"
- "Lean Canvas", "Pitch Deck"
- "CFO 관점", "CEO 관점에서 검토"
- "해자 분석", "Moat 검증"

## 다른 스킬과의 관계

- **사업 단위 vs 제품 단위**: 이 스킬은 신사업·수익 모델 단위. 특정 제품·기능의 PRD는 `prd-builder` 사용.
- **사업계획서 → PRD**: Phase 4 완료 후, 핵심 제품에 대해 `prd-builder`로 상세 PRD 분할 작성.
- **사업계획서 → 티켓**: PRD 작성 후 `prd-to-tickets`로 Epic/Story/Task 분해.

### 권장 워크플로우 체인

```
bizplan-builder (사업계획서 4-Phase 검증)
  ↓
prd-builder (핵심 제품·기능별 PRD)
  ↓
prd-to-wireframe (프로토타입)
  ↓
wireframe-description (개발 명세)
  ↓
prd-to-tickets (Epic/Story/Task 분해)
```

## 실행 시 첫 응답 패턴

사업계획서 작성 요청을 받으면 절대 바로 작성에 들어가지 않는다. 항상 다음 순서:

1. Phase 0 시작 알림 + 4-Phase 워크플로우 개요 제시
2. `phases/phase0-setup.md` 읽고 6가지 확인 항목 질문
3. 모든 답변 수령 후 작업 디렉토리 생성 + context.json 작성
4. notion_upload가 true면 Notion 뼈대 페이지 생성 후 URL 기록
5. Phase 1 진입 의사 확인

**중요**: 사용자가 "한 번에 다 써줘"라고 요청해도 거부한다. 단계별 검증의 본질은 초기 가설 오류가 전체를 오염시키는 것을 방지하는 것이며, 일괄 작성은 이 스킬의 존재 이유와 모순된다.
