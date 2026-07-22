# Phase 3 - 비즈니스 모델 및 단위 경제성 (Business Model & Economics)

## 목적

프로덕트가 시장에서 팔릴 수 있는 방식과 수익 구조의 건전성을 검증한다. 이 Phase는 정량 가드레일을 자동 계산하여 단위 경제성이 마이너스이거나 성장할수록 현금이 소진되는 구조를 차단한다.

## 관여 페르소나

- **B2B Enterprise Sales** (`reviewers/b2b-sales.md`)
- **CFO** (`reviewers/cfo.md`)

## 핵심 질문

### 1) 비즈니스 모델 선택

- 수익 모델 유형 (복수 선택 가능):
  - 구독 (월간 / 연간 MRR)
  - 사용량 기반 (Usage-based, API 호출당 / 처리량당)
  - Freemium → Premium 전환
  - 일회성 라이선스 + 유지보수
  - 마켓플레이스 수익 공유
  - Servitization (성과 기반, IIoT)
- 각 모델의 매출 비중 가정 (3년차 기준)
- 패키징 (Tier) 구조: Starter / Pro / Enterprise — 각 Tier의 기능·가격·타겟

### 2) 가격 정책

- 가격 책정 근거:
  - Cost-plus (원가 + 마진)
  - Value-based (고객이 얻는 가치의 X%)
  - Competitor-based (경쟁사 대비 ±X%)
- ACV (Annual Contract Value) 목표 범위
- 할인 정책 (연납 할인 / 멀티이어 할인 / 볼륨 할인)
- 가격 인상 로드맵

### 3) 세일즈 모델 (PLG vs SLG vs Hybrid)

ACV 규모에 따라 모델을 결정한다.

| ACV 범위 | 권장 모델 | 근거 |
|---|---|---|
| < $5K | PLG (셀프 서브) | 인적 개입의 한계비용 부담 불가 |
| $5K ~ $25K | PLG + Inside Sales | 자동화 + 경량 영업 지원 |
| $25K ~ $100K | SLG (Inside Sales 중심) | 도입 컨설팅·POC 필요 |
| $100K ~ $500K | SLG (Field Sales) | 다중 이해관계자 의사결정 |
| > $500K | Enterprise SLG (Account Executive + SE) | 6~18개월 사이클, 법무·보안 검토 동반 |

❌ 반려: ACV $50K 이상인데 PLG만 가정
✅ 통과: ACV $50K → SLG로 Inside Sales 1명당 연 $1.5M 쿼터 가정

### 4) CAC (고객 획득 비용) 산정

**Fully Loaded** 로 산정해야 한다. 누락 시 반려.

CAC 구성 요소:
- 광고비 (Paid Marketing)
- 콘텐츠 마케팅 인건비 (콘텐츠 작성자, SEO 담당)
- 영업 인건비 (BDR / SDR / AE / SE 의 직접 인건비)
- 영업 커미션 (OTE 기준)
- 영업 도구 비용 (CRM, Sales Engagement, Intent Data)
- 마케팅 이벤트·컨퍼런스 비용
- 영업·마케팅 부서 간접비 (관리자 인건비, 사무 공간 등)

CAC 계산:
```
CAC = (해당 기간 영업·마케팅 총 비용) / (해당 기간 신규 유료 고객 수)
```

❌ 반려: "광고비 1억 / 신규 고객 100명 = CAC 100만원"
✅ 통과: "광고 1억 + 영업 인건비 3억 + 마케팅 인건비 1억 + 도구·이벤트 5천만원 = 5.5억 / 100명 = CAC 550만원"

### 5) LTV (고객 생애 가치) 산정

**총이익(Gross Profit) 기준** 으로 산정해야 한다. 매출 기준 사용 시 반려.

LTV 계산:
```
LTV = (ARPA × Gross Margin) / 월 이탈률
또는
LTV = (ARPA × Gross Margin × 평균 고객 수명) (개월 단위)
```

- ARPA (Average Revenue Per Account): 계정당 평균 매출
- Gross Margin: 매출 - COGS (인프라, AI 추론 비용, 고객 지원 인건비 차감)
- 월 이탈률 (Monthly Churn Rate): 보수적 추정

❌ 반려: "ARPA 100만원 × 24개월 = LTV 2,400만원"
✅ 통과: "ARPA 100만원 × Gross Margin 70% × (1 / 월 이탈률 2%) = LTV 3,500만원"

### 6) 3개년 재무 프로젝션

다음 시나리오를 모두 작성:
- **보수**: 시장 성장 둔화, 경쟁 심화, CAC 30% 증가
- **기본**: 현재 가설대로
- **낙관**: 시장 가속, 레퍼런스 효과, CAC 20% 감소

각 시나리오에서 다음 지표를 월별로 산정:
- 신규 고객 수, 이탈 고객 수, 누적 고객 수
- MRR / ARR
- COGS, Gross Profit, Gross Margin
- 영업·마케팅 비용 (CAC × 신규 고객 수)
- 운영 비용 (R&D, G&A)
- 영업 이익 / 손실
- 누적 Burn / 런웨이

## 외부 리서치 (필수)

산출물 작성 **전**에 `references/research-protocol.md`에 따라 수행한다.

1. **이탈률·CAC·가격 벤치마크** (검색 1~2회): 동일 세그먼트(사업 유형·ACV 범위·타겟 규모)의 최신 업계 이탈률, CAC 수준, 경쟁사 가격(공식 프라이싱 페이지 우선)을 확인. 확보한 값은 `[출처: 도메인, 조회일]` 병기 후 단위 경제성 추정의 근거로 사용.
2. **정적 벤치마크 최신성 확인** (검색 1회, 권장): `references/unit-economics-benchmarks.md`의 통과 기준과 최신 업계 값이 다르면 최신 값을 우선하고 차이·출처를 decision-log에 기록. 벤치마크 파일 자체는 수정하지 않는다.

이 Phase는 SD 최다 발생 구간이다. 이탈률·ARPA·전환율·CAC 구성 단가·성장률 중 사용자 명시도 리서치 출처도 없는 값은 전부 SD로 즉시 기록하고(`references/silent-defaults.md`), LTV·CAC 산정에 직결되는 SD는 발생 즉시 확인을 요청한다. 임계(기본 3) 도달 시 작성을 중단하고 일괄 확인한다.

## 산출물

다음 산출물을 로컬 `phase3/` 파일로 작성한다 (09-business-model-canvas.md / 10-unit-economics.md / 11-financial-projection.md / 12-pricing.md / 13-sales-model.md).

1. **비즈니스 모델 캔버스** (B2B SaaS 특화 변형)
   - 9개 블록 + 다중 페르소나 / 정량적 성과 / 구조적 해자 / 단위 경제성 추가
2. **단위 경제성 표** (자동 계산)
3. **3개년 재무 프로젝션** (보수·기본·낙관)
4. **가격 정책 및 패키징 표**
5. **세일즈 모델 정의서** (PLG/SLG 선택 근거 + 세일즈 사이클 단축 전술)

## 정량 가드레일 자동 검증 (필수)

산출물 작성 직후, `references/unit-economics-benchmarks.md` 의 모든 지표를 자동 계산하고 벤치마크 대비 평가한다. 결과는 `guardrail-results.md`에 기록하고, 이 계산이 Kill Switch 검증 루프의 결정론 검증 입력이 된다. notion_upload가 true면 Phase 3 통과 시 "정량 가드레일 검증 결과" 섹션에 반영.

핵심 지표 5개:
- LTV:CAC Ratio (≥ 3, 타겟 4~7)
- CAC Payback Period (중소 6~9개월, 엔터프라이즈 12~18개월)
- Rule of 40 (≥ 40%)
- NRR (≥ 120%)
- Gross Margin (SaaS 70%↑, AI 60%↑)

각 지표는 🟢 통과 / 🟡 경고 / 🔴 차단 으로 표시.

## 페르소나 리뷰 호출

1. **B2B Enterprise Sales** 리뷰 → PLG/SLG 정합성, ACV 기반 세일즈 전술, 레퍼런스 부재 시 트리거 점검
2. **CFO** 리뷰 → CAC Fully Loaded 검증, LTV 총이익 기준 검증, 런웨이 분석, Rule of 40 달성 가능성

## Kill Switch (다음 Phase 진입 차단 조건)

**판정 절차**: 미확인 SD 0개 확인(선행 조건) → `guardrail-results.md` 자동 계산 선행 → `references/evaluator-loop.md`의 검증 루프로 아래 전 항목을 1:1 대조한 목록을 출력한 뒤에만 판정한다. 정량 항목은 산출물의 수치를 옮겨 적지 않고 공식으로 재계산해 대조한다. 페르소나 리뷰의 🔴 차단 이슈는 임시 항목으로 승격해 함께 대조한다.

다음 중 **하나라도** 해당하면 Phase 4 진입 차단:

- [ ] LTV:CAC < 3 (단위 경제성 마이너스 또는 부족)
- [ ] CAC Payback > 18개월 (엔터프라이즈) 또는 > 9개월 (중소기업)
- [ ] LTV 산정에 매출액(Revenue) 사용 → 총이익 기준으로 재산정 강제
- [ ] CAC가 광고비만 반영하고 인건비·커미션·간접비 누락
- [ ] ACV $25K 이상인데 셀프 서브 PLG 모델 가정
- [ ] Gross Margin < 50% (SaaS 본질에서 이탈)
- [ ] 보수 시나리오에서 18개월 내 추가 자금 조달 없이 런웨이 소진
- [ ] 가격 정책에 가격 인상 또는 NRR 확장 메커니즘 부재 (이탈 100% 가정 등)

Kill Switch 발동 시:
- 어느 지표가 미달인지 수치로 명시
- 개선 방안 제시 (예: "Gross Margin 50% → 70% 도달을 위해 AI 추론 비용을 자체 모델 경량화로 절감")
- 재산정 후 다시 가드레일 검증

## Phase 3 통과 후

- `phase3/` 로컬 산출물 확정 + 리서치 집계(건수·출처) 제시
- `one-page-summary.md`에 정량 가드레일 검증 결과 반영
- notion_upload가 true면 Notion Phase 3 섹션 + 가드레일 검증 결과 섹션 반영, 상태 "통과" 마킹
- 사용자에게 Phase 4 진입 의사 확인
