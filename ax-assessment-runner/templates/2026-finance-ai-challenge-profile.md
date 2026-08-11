# Competition Profile — 2026 Finance AI Challenge

> Generic preset. Copy to `hackathon/competition-profile.md`, re-open every official source, download current forms, and update `last_verified_at` before use.

## Metadata

- competition: 2026 금융 AI Challenge
- profile_version: 1
- last_verified_at: 2026-08-08 KST
- official_sources:
  - https://daker.ai/public/hackathons/2026-finance-ai-challenge
  - https://www.fsec.or.kr/bbs/detail?bbsNo=11997&menuNo=66
- target_outcome: qualify → final award

## Competition Lock

- deadline / timezone: 2026-09-07 10:00 KST
- eligibility / team size: 전 국민, 개인 또는 최대 4인, 중복 등록 금지
- preliminary deliverables: 기획서 PDF, 기능명세서 PDF, 실행 가능한 웹서비스 URL
- deployment survival: 2026-09-07 11:00 ~ 2026-09-11 23:59 KST; 접근 불가는 결격
- finalist deliverables: 2026-10-08 23:59 KST까지 발표자료 PDF + 소스코드 ZIP
- presentation: 2026-10-13 오프라인, PDF로 진행
- official Q&A: 대회 페이지 게시판

## Goal Backward Map

| Goal | Required evidence/artifact |
|---|---|
| 본선 진출 | 근거 있는 금융 현안 + 명확한 소비자/channel + 작동 MVP + 양식 준수 |
| 발표 심사 통과 | 재현 가능한 demo + 금융 현업성 + AI 필요성 + 검증 근거 + 안정적 source package |
| 공동개최사 우수상 | 선택 금융영역과 공동개최사 customer/channel/asset의 구조적 fit |

## Exploration Lanes

| Lane | Example user/problem | Recommended owner |
|---|---|---|
| 금융소비자 보호·포용 | 청년·고령층·장애인 디지털 격차 | Product/Research |
| 금융사기·AI 보안 | 보이스피싱·이상거래·프론티어 AI 공격 | Security/Data |
| 소상공인·창업금융 | 맞춤 금융 매칭·접근성 | Product/Finance |
| 외국인 금융 정착 | 언어·신원·채널·상품 이해 | User Research |
| 투자·기업평가 | 비정형 데이터 성장성 평가·매칭 | AI/Data |
| 보험 | 보험사기 탐지·보험소비자 지원 | Domain/Compliance |

Scout별 2개 후보를 만들고 중앙에는 lane별 상위 1~2개만 올린다.

## Required Judge Pack

- AI Judge: 양식·제출·URL·evidence traceability·unproven claim
- 금융소비자/현업 Persona: 실제 workflow, 소비자 이해·행동 변화
- 금융회사 Persona: 운영·채널·integration·비용·오류 처리
- 금융보안/준법 Persona: 개인정보, 설명 가능성, 피해 가능성, model abuse, human control

## Recommended Composition

- `prd-flow`: 사용 권장. 문제 lane 비교 후 선정 후보를 Gate 1~2로 수렴하고 Full PRD를 기획서·기능명세서의 제품 SoT로 사용
- `ai-dlc`: Full PRD 확정 후 남은 일정과 team capacity를 보고 적용. 기술 설계·구현·test SoT
- `loop-harness`: labeled sample이 있는 탐지/분류/추출, latency/cost에만 적용
- `ux-researcher`: 대표 금융 data와 핵심 flow가 통합된 뒤 적용

## Mandatory Domain Guardrails

- 개인정보·신용정보 최소 수집과 sample/가명 data provenance
- 금융상품 추천·위험판단의 근거, 불확실성, 책임 범위
- AI 오판이 소비자 손실로 이어지는 경로와 Human-IN control
- prompt injection, data leakage, model abuse 등 AI 보안
- mock/synthetic result와 실제 검증 결과의 명확한 구분

## Unknowns — resolve before Problem Lock

| Unknown | Action |
|---|---|
| 공식 심사 기준과 배점 | 공고문 첨부·대회 게시판·양식에서 확인 |
| 기획서/기능명세서 필드·분량 | 최신 원본 양식 다운로드 후 artifact mapping |
| 생성형 AI 사용·고지 조건 | 공식 게시판 문의/공지 확인 |
| 기존 code/open-source/API 사용 범위 | 공식 규정·게시판 확인 |
| 로그인 서비스와 심사 계정 허용 방식 | 공식 게시판 확인 |
| 외부 API 장애·quota 책임 | 공식 규정 확인 후 fallback 설계 |
