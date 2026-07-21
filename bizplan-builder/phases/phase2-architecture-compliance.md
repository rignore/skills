# Phase 2 - 솔루션 기술 아키텍처 및 법무 리스크 평가 (Architecture & Compliance)

## 목적

솔루션이 기술적으로 확장 가능하며, 법적·규제적 치명타(Showstopper) 가 없는지 검증한다. 엔터프라이즈 도입 요건을 원천적으로 충족하지 못하는 설계는 이 단계에서 차단한다.

## 관여 페르소나

- **Staff Engineer / CTO** (`reviewers/staff-engineer.md`)
- **Legal & Compliance Reviewer** (`reviewers/legal-compliance.md`)

## 사업 유형별 검증 항목

Phase 0에서 선택한 사업 유형에 따라 검증 항목이 달라진다.

### 공통 (모든 B2B SaaS)

- 멀티 테넌트 아키텍처 설계 (테넌트 격리 수준, 데이터 분리 방식)
- 제로 트러스트 보안 (마이크로 세그멘테이션, IAM, MFA)
- SSO / SAML / SCIM 지원 (엔터프라이즈 IdP 통합)
- 감사 로그 (Audit Log) 설계
- 백업·복구 (RPO / RTO 목표)
- SLA 정의 (가용성 99.9% / 99.95% / 99.99% 중 선택)
- 데이터 잔류성 (Data Residency) 옵션 (한국·EU·US)

### AI 에이전트 추가

- AI 환각 (Hallucination) 통제 장치
  - 출력 검증 레이어 (Confidence score, citation 강제)
  - Human-in-the-loop 개입 지점 정의
  - Confusion Matrix 기반 평가 프레임워크
- 학습 데이터 거버넌스
  - 데이터 출처 (1차 / 2차 / 합성)
  - 저작권·개인정보 처리 동의 확보 방식
  - 학습 데이터 변경 이력 추적 (Data Lineage)
- 생성물 IP 귀속
  - 고객 입력 데이터 / AI 생성물의 IP 귀속 조항
  - 배상 책임 (Indemnity) 조항 설계
- EU AI Act 대응
  - '고위험 AI' 분류 가능성 평가
  - FRIA (Fundamental Rights Impact Assessment) 계획
  - Human Oversight 메커니즘 구현 위치
  - 시스템 로깅 정책 (의사결정 추적 기간)
- Algorithmic Bias 추적
  - Policy-as-code Audit Trail
  - 편향 측정 지표 (예: Demographic Parity, Equalized Odds)
  - 편향 감지 시 대응 SLA

### IIoT 추가

- IT/OT 통합 설계
  - OT 프로토콜 지원 (Modbus, OPC UA, MQTT, BACnet 등)
  - 레거시 PLC/SCADA/DCS 연동 방식
  - OT 네트워크 격리 정책 (Purdue Model 준수)
- 엣지 vs 클라우드 부하 분산
  - 엣지에서 처리 (저지연 필요): ...
  - 클라우드에서 처리 (장기 분석): ...
  - 데이터 트래픽 추산 (디바이스당 GB/월)
- 하드웨어 BOM (Bill of Materials)
  - 센서 단가 + 게이트웨이 + 통신 모듈
  - 설치·시운전 비용
  - 5년 유지보수·교체 비용 (TCO)
- CapEx 부담 주체
  - 고객 부담 / 우리 부담 / 리스 / Servitization
- Servitization 로드맵
  - 1단계: 장비 판매 + 소프트웨어 구독
  - 2단계: 성과 기반 구독 (예: 사고 감소율 비례 과금)

## 핵심 질문 (사용자에게 단계적으로 제시)

### 1) 아키텍처 확장성

- 단일 테넌트 PoC를 넘어 100개 / 1,000개 / 10,000개 테넌트로 확장 가능한가?
- 가장 큰 고객의 데이터 규모 (TB) 와 동시 사용자 수를 처리할 수 있는가?
- 다국가·다지역 고객 대응 시 데이터 잔류성·지연시간을 어떻게 해결하는가?

### 2) 보안 및 컴플라이언스 인증

- ISO 27001 / SOC 2 Type II / K-ISMS / 클라우드 보안 인증 중 어느 것을 언제까지 획득할 것인가?
- 산업별 추가 인증 필요 여부 (의료 HIPAA, 금융 PCI-DSS, 제조 IEC 62443)
- 개인정보보호 (한국 PIPA, EU GDPR, 미국 CCPA) 대응

### 3) AI 영역 (해당 시)

- AI 환각이 발생했을 때의 비즈니스 영향과 대응 시나리오는?
- 고객 데이터로 모델을 학습할 것인가? 동의 획득 방식은?
- 생성물에 대해 누가 IP를 가지며, 침해 발생 시 누가 배상 책임을 지는가?

### 4) IIoT 영역 (해당 시)

- 하드웨어 단가가 5년 후에도 경제성을 유지하는가?
- 고객사 OT 시스템과의 통합 비용·기간을 누가 부담하는가?
- 통신 두절·전원 차단 등 산업 환경 특수 조건에 대한 Fallback 설계는?

## 산출물

다음 산출물을 Notion Phase 2 섹션에 채운다.

1. **시스템 아키텍처 다이어그램**
   - 멀티 테넌시 + 보안 계층 시각화
   - 주요 컴포넌트 + 데이터 흐름
   - Mermaid 또는 외부 도구 (Excalidraw, draw.io) 링크

2. **규제 대응 매트릭스**
   - 적용 규제 / 요건 / 우리의 대응 / 책임자 / 기한
   - 인증 로드맵 (현재 / Q+1 / Q+2 / Q+3)

3. **데이터 거버넌스 정책**
   - 데이터 분류 (Public / Internal / Confidential / Restricted)
   - 저장 위치·암호화·접근 통제
   - 학습 데이터 / 추론 데이터 / 고객 입력 / AI 생성물 각각의 처리 정책
   - 보존 기간 + 파기 정책

4. **인프라 비용 추산표**
   - 클라우드 비용 (고객 1개당 / 100개당 / 1,000개당)
   - AI 추론 비용 (Token 단가 × 예상 사용량)
   - IIoT의 경우 하드웨어 BOM + 5년 TCO

## 페르소나 리뷰 호출

산출물 작성 완료 후 페르소나 리뷰 자동 실행:

1. **Staff Engineer / CTO** 리뷰 → 아키텍처 확장성, 보안 설계, AI 환각·MLOps, IT/OT 통합 점검
2. **Legal & Compliance Reviewer** 리뷰 → EU AI Act, GDPR, IP 귀속·배상, Audit Trail 점검

## Kill Switch (다음 Phase 진입 차단 조건)

다음 중 **하나라도** 해당하면 Phase 3 진입 차단:

- [ ] 핵심 규제 (GDPR, EU AI Act, 도메인별 필수 인증) 위반 소지
- [ ] 데이터 보안 설계 누락 → 엔터프라이즈 도입 요건 원천 미충족
- [ ] AI 영역인데 환각 통제 장치 또는 IP 귀속 조항 부재
- [ ] IIoT 영역인데 하드웨어 BOM, IT/OT 통합 비용, 클라우드 트래픽 비용 중 하나라도 누락
- [ ] 멀티 테넌시 설계 부재 (단일 테넌트 PoC만 가정)
- [ ] 최대 고객 규모 처리 능력에 대한 부하 추산 부재
- [ ] 인증 로드맵에서 1차 목표 인증의 획득 기한·예산이 비현실적

Kill Switch 발동 시 어느 항목이 차단 사유인지 명시하고, 재설계 가이드 제공.

## Phase 2 통과 후

- Notion 페이지 Phase 2 섹션을 "통과"로 마킹
- 인프라 비용 추산이 Phase 3 (단위 경제성) 의 COGS 입력값으로 자동 연동됨을 사용자에게 고지
- 사용자에게 Phase 3 진입 의사 확인
