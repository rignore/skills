# 페르소나 라우팅

산출물 완성 시 어떤 페르소나를 호출할지 정의. gstack의 "smart review routing" 차용 — 모든 페르소나가 모든 산출물을 보지 않는다. Phase 번호가 아닌 **검토 영역** 기준으로 라우팅하므로, 호출하는 스킬(prd-builder-auto의 Forward/Backward/Rework 모드 등)이 자기 산출물을 해당 검토 영역에 대응시켜 사용한다.

## 라우팅 매트릭스

| 검토 영역 | 권장 페르소나 | 선택 페르소나 | 모바일 PRD일 때 추가 |
|---|---|---|---|
| 문제 정의 | CEO/Founder, Product Lead | Paranoid Reviewer, Editorial Reviewer | - |
| 사용자 & 시나리오 | Product Lead, UX Researcher | QA Lead, Editorial Reviewer | Mobile Engineer (선택) |
| 기능 정의 | Staff Engineer, UX Researcher, UX Writer, QA Lead | Paranoid Reviewer, Editorial Reviewer | **Mobile Engineer (강력 권장)** |
| AI 에이전트 사양 | AI/Agent Engineer, Staff Engineer, Paranoid Reviewer | QA Lead, Editorial Reviewer | - |
| 우선순위 | CEO/Founder, Product Lead, Staff Engineer | Editorial Reviewer | Mobile Engineer (선택, OS·기기 분할 영향 시) |
| KPI | Data Analyst, Product Lead, QA Lead | Editorial Reviewer | - |
| 통합 리뷰 | Paranoid Reviewer, Editorial Reviewer (둘 다 강력 권장) | CEO/Founder, 미진했던 페르소나 | - |
| QA 테스트 리스트 | QA Lead (강력 권장), Staff Engineer, Paranoid Reviewer | AI/Agent Engineer(에이전트 사양 있을 때), Data Analyst, Editorial Reviewer | **Mobile Engineer (강력 권장)** |
| 통합 산출 (1-Pager / Full PRD) | Editorial Reviewer (선택, 가독성·용어·논리 통합 검토) | Paranoid Reviewer (선택, 통합 일관성), CEO/Founder (선택, 1-Pager 임원 시각) | **Mobile Engineer (조건부 — 모바일 키워드 감지 시에만, OS·기기·배포 정책 통합 누락 점검)** |

> **Editorial Reviewer 사용 기준**: 다른 페르소나가 *내용*을 본다면 Editorial Reviewer는 *문서 자체의 품질*(가독성·용어 일관성·논리·사실 정확성)을 본다. 모든 검토 영역에서 호출 가능하지만, 통합 리뷰 영역에서는 Paranoid Reviewer와 함께 강력 권장.

> **Mobile Engineer 사용 기준 (조건부)**: 모바일 관련 키워드가 PRD에 등장할 때만 권장 목록에 추가. 키워드가 없는 순수 백엔드/웹 PRD에는 호출하지 않는다. 트리거 키워드는 `shared/reviewers/mobile-engineer.md`의 "호출 조건" 섹션과 아래 "모바일 키워드 자동 감지" 섹션을 따른다.

## 모바일 키워드 자동 감지

문제 정의·사용자 시나리오·기능 정의 작성 중 다음 키워드가 등장하면 해당 산출물 완료 후 페르소나 선택지에 Mobile Engineer를 자동으로 포함시킨다.

`모바일 앱, iOS, Android, 네이티브, 하이브리드, 웹뷰, 푸시 알림, 백그라운드, 권한(카메라·위치·마이크·블루투스·알림), 오프라인, 동기화, 앱 업데이트, OTA, 강제 업데이트, 스토어 심사, 웨어러블, BLE, 페어링, 디바이스 토큰, FCM, APNs, 딥링크, 크래시 리포트, 배터리, 셀룰러`

키워드가 감지되면 다음과 같이 안내:

```
이 PRD에 모바일 관련 내용이 포함되어 있어 Mobile Engineer 페르소나를 선택지에 추가했습니다.
호출 시 OS 정책·기기 호환성·권한·배포·런타임 제약을 함께 검토합니다.
```

## 호출 절차

1. 산출물 완성 후 사용자에게 묻기:
   ```
   {검토 영역} 산출물이 작성되었습니다. 페르소나 리뷰를 진행할까요?

   이 영역에 권장되는 페르소나:
   - {권장 페르소나 1}: {관점 한 줄}
   - {권장 페르소나 2}: {관점 한 줄}

   선택 페르소나:
   - {선택 페르소나}: {관점 한 줄}

   호출할 페르소나를 선택해 주세요. (전체/개별 선택/건너뛰기)
   ```

2. 사용자가 선택한 페르소나만 `shared/reviewers/<persona>.md` 읽고 해당 관점으로 리뷰 작성

3. 페르소나별 리뷰 결과를 다음 형식으로 출력:
   ```
   [페르소나명]
   🟢 강점:
   - {강점 1}

   🟡 보완 제안:
   - {제안 1}

   🔴 차단 이슈: (있을 때만)
   - {이슈 1}

   ❓ 질문: (PM에게 확인 필요)
   - {질문 1}
   ```

4. 사용자에게 채택 여부 묻기:
   ```
   {페르소나}의 피드백입니다.

   각 항목에 대해 채택 여부를 알려주세요:
   - 보완 제안 1: 채택 / 거부
   - 보완 제안 2: 채택 / 거부
   - 차단 이슈 1: 채택 / 거부 (거부 시 사유 필요)

   질문에 대한 답변도 함께 알려주세요.
   ```

5. 채택된 피드백만 해당 산출물에 반영
6. 변경 이력 테이블에 기록 (반영된 페르소나 명시)
7. 페르소나 리뷰 로그에 전체 리뷰 누적 (채택/거부 여부 포함)

## 멀티 페르소나 호출

여러 페르소나를 동시에 호출한 경우, 각각 독립적으로 리뷰 작성. 페르소나 간 상충하는 의견은 사용자에게 명시:

```
페르소나 간 상충 의견:
- CEO/Founder: 스코프를 더 확장해야 한다
- Staff Engineer: 현재 스코프도 일정 위험이 크다

어떻게 결정하시겠어요?
```

## 자체 판단 모드

사용자가 "자체 판단해줘", "알아서 반영해줘", "판단해서 적용해줘", "네가 결정해줘" 같이 개별 채택 확인 없이 반영을 위임하면, 아래 기준으로 채택/거부를 결정하고 결과를 보고한다. 채택 여부 확인 절차(Step 4)는 건너뛴다.

### 채택 기준

| 기준 | 처리 |
|---|---|
| 구현이 간단하고 사용자 가치에 직결되는 보완 제안 | 채택 후 즉시 반영 |
| 차단 이슈(🔴) — 근거가 명확한 경우 | 채택 후 즉시 반영 |
| 산출물 전체 재작성이 필요하거나 범위가 큰 보완 제안 | 거부 + 사유 기록 |
| 다른 페르소나 피드백과 충돌하는 제안 | 거부 + 충돌 항목 명시 |
| 의도가 불명확해 판단 불가능한 항목 | 보류 + 사용자에게 질문 |

### 보고 형식

```
[자체 판단 모드]
채택 (반영):
- {항목}: {채택 이유}

거부 (미반영):
- {항목}: {거부 이유}

보류 (확인 필요):
- {항목}: {무엇을 확인해야 하는지}
```

---

## 페르소나 호출 건너뛰기

사용자가 "건너뛰기"를 선택하면 페르소나 리뷰 없이 다음 산출물로 진행. 단, 통합 리뷰·QA 테스트 리스트 영역에는 강력 권장 페르소나가 있음:

```
통합 리뷰는 전체 정합성을 점검하는 단계이므로 Paranoid Reviewer 호출을 강력히 권장합니다.
정말 건너뛰시겠어요?
```

```
QA 테스트 리스트 단계에서는 QA Lead 호출을 강력히 권장합니다.
케이스 커버리지·측정 가능성·경계값 누락은 QA Lead 리뷰 없이 놓치기 쉽습니다.
정말 건너뛰시겠어요?
```

## 페르소나별 파일 위치

- `shared/reviewers/ceo-founder.md`
- `shared/reviewers/product-lead.md`
- `shared/reviewers/ux-researcher.md`
- `shared/reviewers/ux-writer.md`
- `shared/reviewers/staff-engineer.md`
- `shared/reviewers/mobile-engineer.md` (조건부 — 모바일 키워드 감지 시)
- `shared/reviewers/ai-agent-engineer.md`
- `shared/reviewers/qa-lead.md`
- `shared/reviewers/data-analyst.md`
- `shared/reviewers/paranoid-reviewer.md`
- `shared/reviewers/editorial-reviewer.md`

## 도메인 리서치 캐시 페르소나 전달

도메인 리서치 캐시(`prd-flow/{slug}/research/domain-*.md` — `domain-research` 스킬이 웹 검색으로 생성)가 적재되어 있다면, 페르소나 호출 시 다음 형식으로 안내한다.

```
[{페르소나명} 호출]
적재된 도메인 리서치 캐시:
- research/domain-{topic-1}.md
- research/domain-{topic-2}.md

위 리서치 근거와 PRD 간 충돌·중복·정합성을 함께 검토해 주세요.
리서치는 확정 사양이 아닌 참고 근거입니다 — 충돌은 단정하지 말고 질문으로 표면화하고, 출처를 병기해 주세요.
```

이 안내가 포함되면 각 페르소나는 자기 페르소나 파일에 "도메인 리서치 캐시 활용" 섹션이 정의된 경우 그 섹션을 따라 추가 검토를 수행한다. 섹션이 없는 페르소나는 자기 관점 범위 안에서 리서치 근거와의 충돌·중복만 ❓ 질문으로 보고한다. 사용자가 직접 제공한 도메인 지식은 항상 리서치 캐시보다 우선한다.
