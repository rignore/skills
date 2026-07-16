# PRD 컨텍스트 적재 가이드 (로컬 우선, Notion 옵션)

Phase 1(PRD 컨텍스트 적재)에서 어떤 파일/페이지를 읽고, 어떤 정보를 가져와야 하는지 정의한다.

**원칙: PRD의 SoT는 로컬 파일(`prd-flow/{slug}/`)이다.** Notion fetch는 context.json `notion_upload`가 `true`이고 사용자가 Notion URL을 제공했을 때만 사용하는 fallback이다.

---

## 1차 소스: 로컬 파일

| 파일 | 필수 여부 | 적재 목적 |
|-----------|---------|---------|
| `notion-pages/full-prd.md` | 필수 | 권한 매트릭스, Open Questions, 비기능 요구사항, 상태 머신·자동화 정책 등 비즈니스 로직 |
| `auto-backward/08-ai-agent-spec.md` | 있으면 | 에이전트 동작 사례, 허용된 분기, Reflection 루프 (Agent PRD 역할) |
| `auto-backward/07-features.md` | 있으면 | 기능 정의 상세 — Phase 3 화면 매핑의 기준 |
| `auto-backward/12-decision-log.md` | 있으면 | 결정(`D-`) 앵커, 수식 임계치·파라미터의 리서치 근거 |
| `gate2/13-discovery-report.md` | 있으면 | Discovery 종합 맥락 (선택 적재) |

---

## 소스별 추출 정보

### full-prd.md (Full PRD 본문)

| 섹션 | 디스크립션 활용 |
|-----|--------------|
| 문제 정의 / 목표 | 전제 맥락 파악 |
| 사용자/권한 | 권한별 화면 분기, 버튼 노출 조건 |
| 핵심 기능 목록 | 프로토타입 화면 매핑 기반 |
| 비즈니스 로직 (상태 머신·자동화 정책) | 카테고리 5 (상태별 화면 분기) |
| 비기능 요구사항 | 성능·SLA 관련 에러 처리 기준 |
| Open Questions | `*OQ-N` 형식의 백로그/논의 표시 |

### 프로토타입 (화면 단위 SoT)

화면 진입 조건·데이터 정의를 포함한 화면 단위 정의는 프로토타입 분석에서 직접 도출하여 디스크립션에 기술한다.

| 추출 항목 | 디스크립션 활용 |
|-----|--------------|
| 화면 단위 목록 | Phase 3 매핑의 기준점 |
| 컴포넌트 트리 | Phase 4 넘버링 이정표 |
| 인터랙션 (코드 분석) | 카테고리 4 (인터랙션) 작성 |
| 정보 배치·강조 | 카테고리 2 (데이터 바인딩) 작성 |

### 08-ai-agent-spec.md (Agent PRD)

| 섹션 | 디스크립션 활용 |
|-----|--------------|
| 에이전트 동작 사례 | 카테고리 4 (인터랙션), 카테고리 5 |
| 허용된 분기 목록 | 카테고리 5 상태 머신 보완 |
| Reflection 루프 | 백로그(`*`) 표기 여부 판단 |
| 사용자 개입 일감 | 카테고리 4, 카테고리 13 (백로그) |

> 계산식/수식의 SoT는 디스크립션이다(`F-{n}` 앵커 발급). PRD·decision-log에서는 high-level 서술과 임계치 근거만 가져온다.

---

## Notion Fallback (옵션)

아래 두 조건을 모두 만족할 때만 Notion MCP를 사용한다:
- context.json의 `notion_upload`가 `true`
- 사용자가 Notion PRD URL 또는 페이지 ID를 제공 (로컬 full-prd.md가 없거나, Notion 쪽이 최신이라고 사용자가 명시)

### 페이지 탐색 순서

```
1. Full PRD URL로 최상위 페이지 fetch (notion-fetch)
2. 본문에서 하위 페이지 링크 자동 탐색
3. 제목 패턴 매칭으로 하위 문서 식별: `비즈니스 로직`, `Business Logic`, `Agent PRD`, `에이전트 사양`, `상세`
4. 식별된 하위 페이지 일괄 fetch
5. 하위 페이지에서 재귀적으로 추가 하위 페이지 탐색 (1레벨 추가)
```

### 페이지 ID 직접 지정

사용자가 Notion 페이지 ID를 직접 제공하는 경우, 자동 탐색 없이 해당 ID로 fetch한다.
페이지 ID는 Notion URL에서 추출: `notion.so/{workspace}/{page_id}` 또는 `notion.so/{page_id}`

*페이지 ID는 스킬에 하드코딩하지 않는다. 사용자가 URL로 제공하거나 하위 페이지 탐색으로 처리.

---

## Fallback 처리

| 상황 | 처리 방식 |
|------|---------|
| 로컬 full-prd.md 없음 + Notion URL 없음 | PRD 미제출 모드. 비즈니스 로직·정책 항목 전부 `*` 인라인 노트 |
| auto-backward/ 하위 파일 없음 | full-prd.md만 컨텍스트로 사용 |
| 비즈니스 로직 섹션 미존재 | 계산식·상태 머신 항목은 `*` 인라인 노트 처리 |
| Notion MCP 연결 실패 (fallback 시) | 사용자에게 알림 후 로컬 파일 또는 PRD 미제출 모드로 전환 |
