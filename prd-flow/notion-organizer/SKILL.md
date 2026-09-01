---
name: notion-organizer
description: >
  Notion 페이지에 작성된 텍스트를 업무용으로 재구조화하는 스킬. prd-flow의 선택적
  Notion 업로더로서 3종 모드(live-page-update · prd-consolidation · bulk-upload)를
  지원한다. 사용자가 기존 Notion 페이지나 텍스트를 정리·구조화·재구성해 달라고
  요청할 때 사용한다.
---

# Notion Organizer

Notion에 이미 작성된 텍스트를 업무 문서 수준으로 재구조화하는 스킬. 새 문서를 생성하는 것이 아니라 **기존 문서의 정보를 보존하면서, 문서의 목적과 맥락에 맞는 Notion 컴포넌트를 선택해 가독성을 극대화하는 것**이 목적이다.

또한 prd-flow 파이프라인의 **선택적 Notion 업로더**를 겸한다. prd-flow의 모든 산출물은 로컬 파일(`prd-flow/{feature-slug}/`, 특히 `notion-pages/*.md`)이 SoT이고 **Notion 없이도 전체 파이프라인이 동작한다**. 이 스킬의 연계 모드는 `context.json`의 `notion_upload`가 `true`인 프로젝트에서만 호출되어, 로컬 산출물을 Notion에 미러링한다.

## 핵심 원칙

1. **정보 보존**: 원문에 있는 사실·숫자·의사결정·담당자·일정은 절대 누락·왜곡하지 않는다. 의역은 허용하되 창작은 금지.
2. **컴포넌트 최적 선택**: 텍스트를 단순 개조식으로 바꾸는 데 그치지 않는다. 문서 목적·섹션 성격에 맞는 Notion 블록을 골라 정보를 가장 효과적으로 전달한다.
3. **간결함**: 줄글을 개조식으로, 장문을 짧은 문장으로, 중복을 제거한다.
4. **전문성**: 업무 문서 톤을 유지. 구어체·감탄사·불필요한 수식어 제거.
5. **아이콘 최소화**: 이모지·아이콘을 기본적으로 사용하지 않는다. 단, 사용자가 명시적으로 허용한 경우에만 섹션 구분용으로 최소한 허용.
6. **원본 확인 우선**: 정리 전에 반드시 원본을 fetch하여 전체 내용을 파악한 뒤 작업한다.

---

## 작성 가드레일

모든 정리 작업에 공통으로 적용되는 규칙.

- **이모지·아이콘 금지**: 제목·불릿·콜아웃에 이모지 사용하지 않음. Notion 블록의 기본 스타일만 사용.
- **화살표(→) 금지**: "A → B" 형태 금지. "A로 인한 B" / "A 이후 B" / "A에서 B로 변경" 형태로 풀어 씀. 단, 플로우차트·프로세스 다이어그램 내부는 예외.
- **구어체 제거**: "~인 것 같아요", "~하면 좋을 듯", "아무튼" 등 비공식 표현을 "~으로 판단됨", "~검토 필요" 등으로 치환.
- **수식어 제거**: "정말", "매우", "엄청", "굉장히" 등 주관적 강조어 삭제. 정량 표현으로 치환 가능하면 그렇게.
- **개조식 우선**: 2줄 이상의 줄글은 번호·불릿 계층으로 분해. 단 결론·요약 단락은 줄글 유지 가능.
- **중복 병합**: 같은 정보가 여러 곳에 등장하면 한 곳으로 통합하고 나머지는 제거.
- **미결정 사항 분리**: "논의 필요", "확정 안 됨" 항목은 별도 섹션으로 모은다.
- **책임·일정 표기 통일**: "담당: 홍길동 / 마감: 2026-04-20" 형식으로 통일. 상대 날짜("다음 주")는 절대 날짜로 변환.

---

## Notion 컴포넌트 선택 기준

### 텍스트·구조 블록

| 블록 | 사용 시점 | 피해야 할 경우 |
|------|----------|--------------|
| **Heading 1** | 페이지당 1개, 문서 전체 제목 | 섹션 구분에 남용 금지 |
| **Heading 2** | 주요 섹션 (페이지당 3–6개 권장) | H3 건너뛰고 H4 직접 사용 금지 |
| **Heading 3** | H2 하위 소섹션 | 2단계 이상 중첩 시 Toggle로 대체 검토 |
| **Bulleted List** | 순서 없는 항목 나열, 요건·특징 열거 | 5개 이상이면 Toggle이나 Table 검토 |
| **Numbered List** | 순서 있는 절차, 우선순위 목록 | 단순 나열에 번호 부여 시 의미 혼란 |
| **Toggle** | 부가 설명, 세부 내용 접기, FAQ | 핵심 정보를 숨길 때 — 중요한 내용은 노출 유지 |
| **Toggle Heading** | H2/H3 섹션 전체를 접을 때 | 3단계 이상 중첩 |
| **Quote** | 외부 인용, 이해관계자 피드백, 원문 보존 필요 구간 | 내부 서술문에 남용 |
| **Callout** | TL;DR 요약, 경고·주의, 핵심 결정사항, 중요 공지 | 일반 설명 텍스트에 남용 — 임팩트 희석 |
| **Divider** | 대섹션 경계 구분 | H2 바로 위에 중복 배치 |
| **Code Block** | URL, 경로, 파라미터, 명령어 등 literal 문자열 | 설명 텍스트 코드 블록에 포함 |
| **Table of Contents** | 긴 문서(H2 5개 이상)의 상단 네비게이션 | 짧은 문서에 불필요 배치 |

### 데이터 블록

| 블록 | 사용 시점 | 선택 기준 |
|------|----------|----------|
| **Simple Table** | 정적 비교표, 단순 참조 데이터 | 속성·필터·관계 필요 없을 때 |
| **Inline Database** | 페이지 맥락에 묶인 정형 데이터 (액션 아이템, 이슈 목록) | 담당자·기한·상태 속성이 필요할 때 |
| **Full-Page Database** | 팀 전체가 관리하는 독립 데이터셋 | 문서와 분리된 중심 데이터일 때 |

**데이터 블록 선택 판단 흐름**:
1. 속성(담당자·기한·상태)·필터·관계가 필요한가? **예** — Database 사용
2. 페이지 맥락 내 데이터인가? **예** — Inline Database
3. 팀 공용 독립 데이터셋인가? **예** — Full-Page Database
4. 그 외 단순 비교표 — Simple Table

### 레이아웃 블록

| 블록 | 사용 시점 | 권장 패턴 |
|------|----------|----------|
| **2단 컬럼** | 가정 vs 의존성, 이전 vs 이후, 옵션 A vs B 비교 | 왼쪽 = 주정보, 오른쪽 = 보조/메타 |
| **3단 컬럼** | 진행 현황·블로커·다음 단계 동시 표시 | 균등 분량일 때만 사용; 내용 차이 크면 2단 선택 |

컬럼은 모바일에서 수직 적재됨 — 읽기 순서가 깨지지 않는지 확인 후 사용.

### Callout 색상 의미 체계 (이모지 없이 색상으로만 구분)

| 색상 | 의미 | 사용 예 |
|------|------|---------|
| 기본(흰 배경) | 일반 강조, TL;DR, 메타 정보 | 문서 상태, 작성자, 업데이트 일자 |
| 파란 배경 | 참고 정보, 배경 맥락 | "이 문서는 ~를 전제로 작성됨" |
| 노란 배경 | 주의, 미결 사항, 확인 필요 | "아래 수치는 추정값이며 확인 필요" |
| 빨간 배경 | 경고, 차단 이슈, 되돌릴 수 없는 작업 | "이 설정 변경 시 기존 데이터 삭제됨" |
| 초록 배경 | 확정·승인 완료, 성공 상태 | "2026-05-10 최종 승인 완료" |

Callout 남용 금지 — 페이지당 최대 3–4개. 그 이상이면 중요도 희석.

---

## 문서 유형별 표준 구조 + 컴포넌트 패턴

### A. 회의록 (Meeting Notes)

**추천 컴포넌트**: Callout(메타), Toggle(안건별), Simple Table(액션 아이템), Divider

```
H1: [회의명] — YYYY-MM-DD
Callout(기본): 일시 / 참석자 / 목적 / 회의록 작성자
Divider
H2: 논의 요약
  Bulleted List (3–5개 핵심 포인트)
H2: 주요 안건
  Toggle H3: [안건 1]
    논의 내용 (Bulleted)
    결론 (Callout 기본 또는 Bold 처리)
  Toggle H3: [안건 2]
    ...
H2: 결정 사항
  Numbered List — 각 항목: 결정 내용 / 근거 / 담당 / 기한
H2: 액션 아이템
  Simple Table: 항목 | 담당자 | 기한 | 상태
H2: 미결·이월 사항 (있을 때만)
  Bulleted List
```

**설계 포인트**:
- 안건이 3개 이상이면 Toggle Heading으로 접어 스캔 가능하게.
- 결정사항과 액션 아이템은 별도 섹션으로 반드시 분리.
- 긴 회의록이면 상단에 Table of Contents 추가.

---

### B. 리서치·자료 정리

**추천 컴포넌트**: Callout(핵심 발견), Quote(인용), Toggle(부록), Simple Table(비교), 2단 컬럼(시사점 구조화)

```
H1: [리서치 제목]
Callout(기본): 핵심 인사이트 1–2줄 (TL;DR)
Divider
H2: 배경 및 목적
  단문 1–2문단
H2: 조사 방법
  Numbered List (절차)
  Callout(파란): 표본 수, 조사 기간, 주요 제약
H2: 주요 발견
  H3: [발견 1]
    Bulleted List
    Quote: 주요 인터뷰·설문 응답 인용
  Divider
  H3: [발견 2]
    ...
H2: 시사점
  2단 컬럼: [왼쪽] 발견 요약 | [오른쪽] 업무 관점 해석
H2: 권고사항
  Numbered List (우선순위 순)
H2: 부록 (Toggle)
  Toggle: 원데이터 / 인터뷰 전문 / 상세 방법론
H2: 참고 자료
  Bulleted List (링크)
```

**설계 포인트**:
- Quote 블록으로 인터뷰·VOC 직인용 — 단순 요약과 원문 구분.
- 부록은 Toggle으로 접어 메인 흐름 방해 금지.
- 시사점 섹션에 2단 컬럼 사용 시 "발견(좌) / 해석(우)" 패턴 권장.

---

### C. 아이디어·브레인스토밍 정리

**추천 컴포넌트**: Callout(배경), Toggle(아이디어별), Simple Table(우선순위 매트릭스)

```
H1: [브레인스토밍 주제]
Callout(기본): 배경 — 무엇을 위한 논의였는가 (2–3줄)
Divider
H2: 아이디어 목록
  Toggle: [아이디어 이름]
    제안 내용 / 기대 효과 / 잠재 리스크
  Toggle: [아이디어 이름]
    ...
H2: 우선순위 검토
  Simple Table: 아이디어 | 임팩트(상/중/하) | 실행 난이도(상/중/하) | 우선순위
H2: 다음 단계
  Numbered List (실행 가능한 항목만)
  담당 / 기한 표기
H2: 보류·재검토 필요 (있을 때만)
  Bulleted List
```

**설계 포인트**:
- 아이디어가 5개 이상이면 카테고리별 Toggle Heading으로 묶기.
- 우선순위 매트릭스는 Simple Table로 충분 (속성 필요 없음).
- "다음 단계"에 포함되지 않은 아이디어는 보류 섹션에 명시적으로 이동.

---

### D. 업무 보고·상태 공유

**추천 컴포넌트**: Callout(전체 상태), 3단 컬럼(성과·이슈·계획), Simple Table(이슈 트래킹)

```
H1: [프로젝트명] 상태 보고 — YYYY-MM-DD
Callout(초록/노란/빨간): 전체 상태 — 한 문장 요약
Divider
3단 컬럼:
  [1] H3: 이번 주 성과
      Bulleted List (3–5개)
  [2] H3: 진행 중 이슈
      Callout(노란): 각 이슈 1줄 요약
  [3] H3: 다음 주 계획
      Bulleted List
H2: 이슈 상세
  Simple Table: 이슈 | 영향 | 대응 방안 | 담당 | 기한
H2: 주요 결정사항 (있을 때만)
  Callout(기본): 결정 내용 / 근거 / 날짜
H2: 지원 필요 사항 (있을 때만)
  Bulleted List
```

**설계 포인트**:
- 전체 상태 Callout 색상이 문서의 시그널 — 초록(정상), 노란(주의), 빨간(위험).
- 3단 컬럼으로 성과·이슈·계획 한 화면에 스캔 가능하게 배치.
- 이슈가 없으면 이슈 상세 섹션 생략.

---

### E. PRD·기획서

**추천 컴포넌트**: Callout(상태·메타), 2단 컬럼(가정 vs 의존성), Inline Database(요구사항), Toggle(상세 시나리오)

```
H1: [기능명] | v[버전]
Callout(기본): 상태: [작성 중/검토 중/확정] | 담당: [이름] | 최종 수정: YYYY-MM-DD
Divider
H2: 배경 및 문제 정의
  단문 2–3문단
  Quote: 핵심 VOC 또는 데이터 인용
H2: 목표 및 성공 지표
  Bulleted List (목표)
  Simple Table: KPI | 현재값 | 목표값 | 측정 방법
H2: 사용자 시나리오
  Toggle H3: [시나리오 1 — 주요 경로]
    Step-by-step Numbered List
  Toggle H3: [시나리오 2 — 예외 경로]
    ...
H2: 기능 요구사항
  Inline Database: 기능 | 우선순위 | 담당 | 상태
H2: 비기능 요구사항
  Bulleted List (성능, 보안, 접근성 등)
H2: 가정 및 의존성
  2단 컬럼:
    [왼쪽] H3: 가정
    Bulleted List
    [오른쪽] H3: 의존성
    Bulleted List
H2: 미결 사항
  Simple Table: 질문 | 담당 | 기한 | 상태
```

**설계 포인트**:
- 기능 요구사항은 Inline Database로 — 담당·우선순위·상태 속성 필수.
- 시나리오가 3개 이상이면 Toggle Heading으로 접기.
- 가정 vs 의존성은 2단 컬럼 대표 사용처.

---

### F. 위키·지식베이스

**추천 컴포넌트**: Table of Contents, Toggle(FAQ), Callout(메타·주의), Inline Database(리소스 목록)

```
H1: [주제명]
Callout(파란): 최종 수정: YYYY-MM-DD | 담당: [이름]
Table of Contents
Divider
H2: 개요
  단문 1–2문단
H2: 상세 가이드
  Numbered List (절차)
  Toggle: [세부 단계명] — 상세 설명 접기
H2: 자주 묻는 질문
  Toggle: [질문 1]
    답변
  Toggle: [질문 2]
    ...
H2: 주의사항 (있을 때만)
  Callout(노란 또는 빨간): 각 주의사항
H2: 관련 리소스
  Inline Database 또는 Bulleted List (링크)
```

**설계 포인트**:
- H2 5개 이상이면 Table of Contents 필수.
- FAQ는 Toggle List 패턴 — 질문이 스캔 가능, 답은 접혀 있음.
- 긴 위키는 Synced Block 푸터 적용 검토 ("문의: [링크] | 수정 요청: [링크]").

---

### G. 일반 메모 (유형 불명)

```
H1: [메모 제목]
Callout(기본): 요약 — 3줄 이내
Divider
H2: 핵심 내용
  주제별 H3 + Bulleted List
H2: 후속 조치 (있을 때만)
  Bulleted List — 담당 / 기한 표기
```

---

## Toggle 사용 판단 기준

Toggle을 사용하면 좋은 경우:
- 내용이 부가적이어서 모든 독자가 읽을 필요 없을 때
- 세부 사항이 메인 흐름을 끊을 때 (예: 방법론 상세, 부록, FAQ)
- 동일 패턴이 반복될 때 (예: 안건 5개, 아이디어 8개)

Toggle을 피해야 하는 경우:
- 핵심 결정사항·경고·필수 읽기 정보를 숨길 때
- Toggle 안에 Toggle을 2단계 이상 중첩할 때
- 접힌 내용이 없어서 Toggle이 의미 없을 때

### 점진적 정보 노출 (Progressive Disclosure) 패턴

항목의 핵심 요약은 항상 노출하고, 상세 내용만 Toggle로 접는다. Toggle Heading으로 섹션 전체를 숨기는 방식은 지양한다.

**적용 기준**:

| 노출 수준 | 내용 | 블록 |
|----------|------|------|
| 항상 표시 | 항목명·핵심 역할·즉각 액션 (1\~3줄) | H3 + 본문 텍스트 |
| 클릭 시 표시 | 상세 판단 로직·데이터 매트릭스·보완 설명 | `<details>` 토글 |

**`<details>` 토글 레이블 네이밍**:
- 데이터 매트릭스: "데이터 매트릭스 보기"
- 판단 로직 상세: "판단 로직 및 데이터 매트릭스"
- 예시·사례: "상세 예시"
- 보완 설명: "추가 설명"

**잘못된 예**:
```
### 결제 실패 감시 에이전트 {toggle="true"}
	(내용 전체가 숨겨짐 — 클릭해야만 무엇을 하는 에이전트인지 알 수 있음)
```

**올바른 예**:
```
### 결제 실패 감시 에이전트

**관찰 대상**: 구독 결제 시도·실패 이벤트
**즉각 액션**: 결제 실패 3회 연속 시 자동 재시도 중단·사용자에게 카드 갱신 알림 전송

<details>
<summary>판단 로직 및 데이터 매트릭스</summary>
(상세 판단 기준, 실패 유형 분류 테이블 등)
</details>
```

---

## 워크플로우

### 1단계 - 원본 확인

사용자가 Notion URL 또는 페이지 지정 후 정리 요청 시:

1. `notion-fetch` 또는 `notion-search`로 페이지를 가져와 전체 내용을 읽는다.
2. 문서 유형을 판단한다 (A–G 중 선택 또는 혼합형 판단).
3. 판단한 유형·적용 템플릿·주요 컴포넌트 선택 이유를 1–3줄로 사용자에게 알린다.
4. 원본을 덮어쓸지, 사본을 새로 만들지 사용자에게 확인.

**중요**: 원본 보존이 기본값. 사용자가 명시적으로 "원본 수정"이라고 하지 않는 한 사본을 새로 만든다.

### 2단계 - 구조 + 컴포넌트 초안 제시

1. 섹션 헤더 + 각 섹션에 사용할 컴포넌트를 함께 사용자에게 보여준다.
   예: "H2: 액션 아이템 — Simple Table 사용 (담당·기한·상태 컬럼)"
2. 사용자가 섹션 추가·삭제·순서 변경·컴포넌트 변경을 요청하면 수용.
3. 구조·컴포넌트 확정 후에야 본문 정리 시작.

### 3단계 - 섹션별 정리

1. 각 섹션을 순차로 작성. 한 번에 전부 쓰지 말고 1–2개 섹션씩 Notion에 반영.
2. 가드레일(이모지 금지, 화살표 금지, 구어체 제거) 체크하며 작성.
3. 원본에 없는 정보는 절대 추가하지 않는다. 필요하면 "(원문 불명확, 확인 필요)"로 표시.
4. Callout은 페이지당 3–4개 상한으로 절제해 사용.

### 4단계 - 검토 및 완료

1. 전체 완성 후 사용자에게 미리보기(제목 + 섹션 개요 + 사용 컴포넌트 목록)를 전달하고 승인 요청.
2. 승인 후 원본에 "정리본 링크" 또는 "정리 완료일" 표시 옵션 제안.
3. 정리 과정에서 발견된 미결 사항·모순점은 별도 메시지로 사용자에게 리포트.

---

## 금지 사항

- 원본에 없는 내용을 추측으로 추가하지 않는다.
- 사용자 확인 없이 원본을 직접 수정하지 않는다.
- 섹션을 임의로 생략하지 않는다 (원본에 해당 정보가 있었다면 반드시 포함).
- 이모지·아이콘·컬러 콜아웃을 사용자 요청 없이 추가하지 않는다.
- 영어 용어를 불필요하게 남용하지 않는다 (업계 표준 용어는 예외).
- Callout을 강조가 필요하지 않은 일반 텍스트에 사용하지 않는다.
- Toggle 안에 핵심 결정사항·경고를 숨기지 않는다.
- 3단 컬럼을 내용 불균형이 심한 섹션에 억지로 적용하지 않는다.

---

## 빠른 요청 시 축약 워크플로우

사용자가 "그냥 빨리 정리해줘"라고 할 때:

1. 원본 fetch
2. 유형 자동 판단 + 적용 컴포넌트 1–2줄로 통지
3. 사본 생성 후 일괄 정리
4. 완료 링크 전달

이 경우에도 가드레일(이모지·화살표·구어체 금지)과 컴포넌트 선택 기준은 동일하게 적용.

---

## 추가 모드 (PRD-Flow 워크플로우 연계 — 선택적 업로더)

기존 단일 페이지 정리 기능에 더해, `prd-flow` 워크플로우의 각 게이트 통과 시점에 자동 호출되는 3종 모드를 지원한다. 이 모드들은 `prd-builder-discovery`가 직접 호출하며, 일반 정리 요청(단일 URL 정리)과는 독립적으로 동작한다.

**전제 (필수 체크)**:
- `context.json`의 `notion_upload`가 `true`일 때만 동작한다. `false`(또는 필드 없음)면 아무 것도 업로드하지 않고 "Notion 업로드 비활성 — 로컬 `notion-pages/*.md`가 SoT"라고 안내 후 종료한다.
- SoT는 항상 로컬 파일이다. Notion 페이지는 미러이며, 충돌 시 로컬 파일이 우선한다.
- 모든 업로드는 표준 Notion MCP 도구(`notion-create-pages`, `notion-update-page`, `notion-fetch`)로 **사용자 지정 부모 페이지** 하위에 수행한다.

### 호출 인터페이스

```
notion-organizer 호출
  mode: live-page-update | prd-consolidation | bulk-upload
  working_dir: ./prd-flow/{feature-slug}/
  notion_parent_page_id: {사용자 지정 Notion 부모 페이지 ID}  (첫 호출 시만 필수 — 없으면 사용자에게 요청)
```

| 모드 | 호출 시점 | 동작 요약 |
|---|---|---|
| `live-page-update` | Gate 1 통과 후 | Problem One-Pager 생성. Gate 2 후 재호출 시 Status 업데이트 |
| `prd-consolidation` | Gate 2 통과 후 | 1-Pager 전체 업데이트 + Full PRD 하위 페이지 신규 생성 |
| `bulk-upload` | Phase 5 (전체 워크플로우 종료 후) | 작업 디렉토리 산출물(PRD 페이지·디스크립션) → Notion 페이지 일괄 매핑 |

---

### 모드 1 · live-page-update

**Gate 1 통과 후 호출** — Problem One-Pager 생성.

**동작:**

1. `context.json`에서 `feature_slug`, `notion_upload` 읽기 (`notion_upload: false`면 종료)
2. `context.json.notion_pages.one_pager_id` 확인
   - **없으면**: `notion_parent_page_id` 하위에 새 페이지 생성 → ID를 `context.json.notion_pages.one_pager_id`에 기록
   - **있으면**: 기존 페이지 업데이트 (append-only: 기존 콘텐츠 유지, Status Callout만 갱신)
3. 생성 소스: `gate1/01-problem.md`, `gate1/02-value-hypothesis.md`, `gate1/03-personas.md`

**Problem One-Pager 구조:**

```
H1: {feature_slug} — Problem One-Pager
Callout(기본): 상태: Problem 정의 완료 | 최종 수정: {YYYY-MM-DD}
Divider
H2: 문제 정의
  (01-problem.md 내용 — Callout + Bulleted List)
H2: 핵심 가치 가설
  (02-value-hypothesis.md 내용)
H2: 주요 페르소나
  Toggle H3 per persona (03-personas.md 핵심만 노출, 상세는 접힘)
```

**Gate 2 이후 재호출 시:**
- 페이지 본문 유지 (append-only)
- Status Callout 텍스트만 "Discovery 완료"로 업데이트
- prd-consolidation 모드로 이어서 진행

---

### 모드 2 · prd-consolidation

**Gate 2 통과 후 호출** — 기존 1-Pager 업데이트 + Full PRD 하위 페이지 신규 생성.

**동작:**

1. `context.json.notion_pages.one_pager_id` 페이지를 "전체 1-Pager"로 업데이트
   - 기존 Problem 섹션 유지 (append-only)
   - 솔루션 범위 섹션 추가 (`gate1.5/06-solution-scope.md`)
   - KPI 섹션 추가 (`auto-backward/10-kpi.md`)
   - Status Callout: "Discovery 완료"로 업데이트
   - Full PRD 페이지 링크 추가 (생성 후)
2. 하위 페이지로 Full PRD 신규 생성(`notion-create-pages`, 부모 = 사용자 지정 페이지) → 반환된 page_id를 `context.json.notion_pages.full_prd_id`에 기록
   - 소스는 로컬 `notion-pages/full-prd.md`. PRD 본문은 표·콜아웃(`> [!NOTE]`)·토글(`<details>`)·코드블록을 지원하되, 계산 수식·임계치는 PRD가 아니라 디스크립션이 SoT다.
   - 이후 버전 갱신은 동일 페이지를 `notion-update-page`로 업데이트하고 페이지 상단 변경이력에 1줄 추가한다(상세: prd-sync의 "Notion 반영 (옵션)").

**Full PRD 페이지 구조:**

```
H1: {feature_slug} — Full PRD
Callout(기본): 상태: Discovery 완료 | 최종 수정: {YYYY-MM-DD}
Table of Contents
Divider
H2: 문제 정의             (gate1/01-problem.md)
H2: 핵심 가치 가설         (gate1/02-value-hypothesis.md)
H2: 페르소나              (gate1/03-personas.md)
H2: 솔루션 범위           (gate1.5/06-solution-scope.md)
H2: Epic 정의            (auto-backward/07-epics.md — H3 per Epic)
H2: AI 에이전트 사양       (auto-backward/08-ai-agent-spec.md — 파일 존재 시만)
H2: 우선순위              (auto-backward/09-priorities.md — P0/P1/P2 Toggle H3)
H2: KPI                  (auto-backward/10-kpi.md — Simple Table)
H2: QA 시나리오           (auto-backward/11-qa-list.md)
H2: 결정 로그 (Toggle)    (auto-backward/12-decision-log.md)
```

---

### 모드 3 · bulk-upload

**Phase 5 호출** — 작업 디렉토리 산출물(PRD 페이지·디스크립션) → Notion 일괄 업로드.

**동작:**

1. `context.json` 읽어서 `notion_upload` 확인(`false`면 종료) + `notion_pages` 기생성 ID 확인
2. 파일 → Notion 매핑 표 순서대로 읽기 → 페이지 생성 또는 append-only 업데이트
3. 기생성 페이지(one_pager_id, full_prd_id)는 덮어쓰지 않고 하단에 신규 섹션 추가
4. 완료 후 요약 리포트 (업로드 페이지 N개, 실패 항목)

**파일 → Notion 매핑:**

| 파일 | Notion 페이지명 | Notion 블록 | 모드 |
|---|---|---|---|
| gate1/01-problem.md | 01-문제 정의 | Callout + Bulleted List | bulk |
| gate1/02-value-hypothesis.md | 02-핵심 가치 가설 | Simple Table | bulk |
| gate1/03-personas.md | 03-페르소나 | Toggle H3 per persona | bulk |
| gate1.5/06-solution-scope.md | 04-솔루션 범위 | Simple Table + Toggle | prd-consolidation, bulk |
| auto-backward/07-epics.md | 05-Epic 정의 | H3 per Epic | bulk |
| auto-backward/08-ai-agent-spec.md | 06-AI 에이전트 사양 (조건부) | Toggle H2 | bulk |
| auto-backward/09-priorities.md | 07-우선순위 | P0/P1/P2 Toggle H3 | bulk |
| auto-backward/10-kpi.md | 08-KPI | Simple Table + placeholder | prd-consolidation, bulk |
| auto-backward/11-qa-list.md | 09-QA 시나리오 | Inline Database | bulk |
| auto-backward/12-decision-log.md | Full PRD 하단 (Toggle) | Full PRD 페이지 하단 추가 | bulk |
| notion-pages/full-one-pager.md | (기존 one_pager_id 업데이트) | prd-consolidation 결과 보강 | bulk |
| notion-pages/full-prd.md | (기존 full_prd_id 업데이트) | prd-consolidation 결과 보강 | bulk |
| wireframe/manifest.json + {screen}_description.md | 10-디스크립션 | H2 per screen | bulk |
| gate2/13-discovery-report.md | Full PRD 상단 요약 Callout | Callout(초록) 삽입 | bulk |

신규 Full PRD는 `07-epics.md`를 사용한다. 기존 프로젝트에 `07-features.md`만 있으면 읽기·재업로드 호환을 위해 `05-기능 정의`로 유지하되, 이를 신규 Epic 형식으로 임의 변환하지 않는다. Epic은 `목적`, `완료 후 상태`, `포함 범위`, `핵심 요구사항`, `범위 밖·주요 연계`, `Epic 완료 판단`을 본문에 펼쳐 보여야 하므로 Inline Database에 넣지 않는다.

**페이지 계층:** 사용자 지정 부모 페이지 하위 평면 나열. 페이지명 prefix(`01-`, `02-`...)로 Notion 내 정렬 유지.

**톤 참조:** 디스크립션 페이지의 문체·용어 기준이 필요하면 작업 디렉토리의 `design/design-system.md`(design-system-builder 산출물)를 참조한다.

---

### context.json 확장 스키마 (PRD-Flow 연계 시)

`live-page-update` 최초 호출 후 `notion_pages` 필드를 context.json에 추가·기록:

```json
{
  "feature_slug": "...",
  "research_dir": "research/",
  "design_system": "design/design-system.md",
  "ux_writing_skill": "general-ux-writing",
  "notion_upload": true,
  "created_at": "...",
  "notion_pages": {
    "one_pager_id": "abc123...",   // Gate 1 통과 후 채워짐
    "full_prd_id": null            // Gate 2 통과 후 채워짐
  }
}
```

페이지 ID는 Notion MCP 생성 응답에서 추출해 자동 기록. 이후 동일 모드 재호출 시 해당 ID 사용.
