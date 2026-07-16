---
name: prd-builder-auto
description: prd-builder-discovery로부터 호출되어 Auto Phase(솔루션 발산 / 상세화 / 항목 재작업)를 페르소나·가드레일 다층 검증으로 자동 진행하는 스킬. Hard Stop 트리거 6종(도메인 지식 충돌·페르소나 분기·Silent Default 누적·Devil critical·범위 이탈·Design Lint)과 Silent Default 감지기로 사람 개입이 필요한 시점만 정확히 포착해 거시 개입을 요청한다. 사용자가 "Auto Phase", "자동 진행", "Hard Stop", "Silent Default", "솔루션 발산", "솔루션 매트릭스", "PRD 상세 자동 작성", "항목 재작업", "페르소나 다관점 검토"와 같은 키워드를 언급하거나, prd-builder-discovery 워크플로우 내부에서 자동 위임으로 호출될 때 사용한다. 단독 실행보다는 prd-builder-discovery의 의존 스킬로서 호출되는 게 표준이지만, 기존 PRD의 특정 섹션만 자동 재생성할 때 단독 호출도 가능.
---

# PRD Builder · Auto

`prd-builder-discovery`의 의존 스킬. 사람 개입 없이 페르소나·가드레일 다층 검증으로 PRD 세부 항목을 자동 생성한다. Hard Stop 트리거 6종과 Silent Default 감지기를 항상 켜둔다.

## 핵심 원칙

1. **자동 진행이 기본**: 사용자에게 직접 묻지 않는다. 가드레일·페르소나 합의로 결정 → decision-log에 기록
2. **Hard Stop은 예외**: 6개 트리거 중 하나라도 발동되면 즉시 중단하고 prd-builder-discovery에 사용자 호출 요청
3. **Silent Default는 추적 가능**: PRD 입력에 명시되지 않은 결정이 발생하면 반드시 decision-log에 기록. Macro Gate 2에서 사용자가 일괄 검토
4. **격리 컨텍스트 가정**: 부모 대화를 못 본다. 입력 파일과 본 SKILL.md의 규칙만으로 의사결정
5. **모드 분리**: 솔루션 발산 / 상세화 / 항목 재작업 — 세 모드의 입출력과 동작이 다름

## 호출 인터페이스

`prd-builder-discovery`가 다음 형식으로 호출:

```
prd-builder-auto 호출
  mode: forward | backward | rework
  working_dir: ./prd-flow/{feature-slug}/
  rework_target: {파일 경로} (rework 모드에서만)
  silent_default_threshold: 3 (기본값, 호출 시 변경 가능)
```

**context.json 우선**: 호출 인자보다 working_dir의 `context.json`이 진실의 원천(SoT). 두 값이 다르면 context.json 우선. context.json에서 읽는 것은 경로 정보뿐이다 — `research_dir`(도메인 리서치 캐시 위치, 기본 `research/`), `design_system`(디자인 시스템 문서, 기본 `design/design-system.md`).

| 모드 | 입력 | 출력 |
|---|---|---|
| `forward` (솔루션 발산) | `gate1/01·02·03.md` | `auto-forward/04·05.md` |
| `backward` (상세화) | `gate1/` 전체 + `gate1.5/06.md` | `auto-backward/07~12.md` |
| `rework` (항목 재작업) | 재작업 대상 파일 1개 + 관련 컨텍스트 | 재작업 대상 파일 수정본 |

## 페르소나 그룹

`shared/reviewers/` 정의를 재사용. 모드별로 호출 조합이 다르다.

| 페르소나 | forward | backward | rework |
|---|---|---|---|
| Product Lead | ✅ | ✅ | ✅ |
| UX Researcher | ✅ | ✅ | ✅ |
| Staff Engineer | ✅ | ✅ | 조건부 |
| AI Agent Engineer | 조건부 (AI 기능 시) | 조건부 | 조건부 |
| Mobile Engineer | 조건부 (모바일 시) | 조건부 | 조건부 |
| QA Lead | — | ✅ | 조건부 |
| Data Analyst | — | ✅ (KPI 시) | 조건부 |
| Paranoid Reviewer (Devil's Advocate) | ✅ | ✅ | ✅ |
| Editorial Reviewer | — | ✅ (산출물 직후) | ✅ |

각 페르소나 정의는 `shared/reviewers/<persona>.md`를 직접 Read로 적재한다. 페르소나 리뷰 호출 시 "적재된 도메인 리서치 캐시: {목록}" 형태로 현재 참조 가능한 `research/domain-*.md` 캐시를 명시한다.

## 모드별 작업 흐름

### Mode A · Forward (솔루션 발산)

1. `gate1/` 3개 파일 적재
2. 메인 문제 + 핵심 가치 + 메인 페르소나의 JTBD를 입력으로 페르소나 그룹에 솔루션 후보 발산 요청
3. 후보 5~8개를 평가 차원 4개(문제 해결도 / 구현 복잡도 / 정합성 / Devil 반론)로 채점
4. Devil's Advocate가 각 후보에 대해 반론 1개 이상 제시
5. 산출물 작성: `auto-forward/04-solution-matrix.md`, `auto-forward/05-devil-advocate.md`

#### 발산 가드레일

- 후보는 **이미 페르소나의 JTBD와 매칭 가능한 것만**. 매칭 안 되는 후보는 제외 (범위 외 솔루션이 매트릭스를 오염시키지 않도록)
- 후보 간 **유의미한 차이**가 있어야 함. "S1: A를 한다 / S2: A를 잘한다"는 합쳐서 하나로
- **외부 리서치 (필수)**: 후보 발산 시 외부 리서치 프로토콜로 경쟁·대안 제품 패턴을 검색해 후보를 보강한다. 사용자가 직접 제공한 도메인 지식이 최우선이고, 그다음이 `research/domain-*.md` 리서치 캐시다. 리서치 출처는 decision-log에 기록하고, 재사용 가치가 있는 검색 결과는 `domain-research` 스킬을 통해 `research/domain-*.md` 캐시로 편입한다
- **정합성 검증**: 평가 차원의 "정합성" 컬럼은 (a) 범위 정합성 — Gate 1의 문제·페르소나 정합성, (b) 리서치 근거 정합성 — 적재된 `research/domain-*.md` 캐시와의 정합성을 함께 본다. 리서치는 확정 사양이 아닌 참고 근거이므로 단정하지 않고 출처를 병기한다

### Mode B · Backward (상세화)

1. `gate1/` + `gate1.5/` 전체 파일 적재
2. 채택 솔루션 + V1 범위 안에서 다음을 순차 생성:
   - 기능 정의 → AI 에이전트 사양 (해당 시) → 우선순위 → KPI → QA 리스트
3. **각 산출물 생성 직후** Generator-Evaluator 루프(아래 "산출물 검증 루프") 실행 → Hard Stop 감지기 + Silent Default 감지기 실행
4. `editorial-reviewer` 자동 호출로 표현·용어 일관성 검토
5. 최종 산출물 6개 작성

#### 산출물 검증 루프 (각 산출물 생성 직후)

산출물을 "생성 완료"로 선언하고 다음 산출물로 넘어가는 것을 금지한다. 생성 직후 가드레일과 1:1 대조한 결과를 **문제 목록으로 먼저 산출**(decision-log 또는 검증 로그에 텍스트로 기록)한 뒤 다음 단계로 넘어간다.

**Step 1 — 문제 목록 산출 (필수)**

상세화 가드레일 + Gate 1.5 V1 범위에 대조하고, 걸리는 항목을 아래 형식으로 나열한다. 없으면 "가드레일 대조: 이상 없음"을 명시한다. 이 결과는 Macro Gate 2 리포트의 근거로 누적된다.

```
[위치] [산출물 파일 / 항목]
[심각] [🔴 Hard Stop 후보 / 🟡 보완]
[원문] "문제가 있는 산출물 원문"
[문제] 어떤 가드레일·범위 기준에 미달하는지
```

**Step 2~4** — 🔴은 해당 Hard Stop 트리거(H1~H6)로 격상해 `prd-builder-discovery`에 사용자 호출 요청. 🟡은 자동 수정 후 수정 구간만 재대조. 통과 시 다음 산출물로 진행. 임의로 V1 범위 외를 만들지 않는다(시도 시 H5).

#### 상세화 가드레일

- V1 범위 외 기능은 생성하지 않음 (생성 시도 발생 시 → Hard Stop H5 트리거)
- **기능 정의(07-features)는 기능 단위로 작성한다**: 각 기능을 `FN-{n}` ID로 1개씩 정의한다. **P0/P1/P2 우선순위로 그룹핑하지 않고, §5/기능 항목에 우선순위를 표기하지도 않는다** — 우선순위 분류는 09-priorities에서 `FN-` ID로 매핑한다(중복 서술 금지). 이는 Full PRD 고정 양식(§5 기능 단위·우선순위 미표기 / §6 우선순위 별도)과 1:1 정합한다.
- **연관 수식 앵커는 메타 라인으로만 표기**: 기능 헤더 `### FN-{n} · {기능명}` 아래 줄에 인라인 코드 `` `앵커: F-n` ``(여러 개면 `` `앵커: F-2, F-3` ``)으로 적는다. "수식 F-4 참조"처럼 본문 서술에 섞지 않는다. 연관 수식이 없으면 앵커 라인을 생략한다.
- 우선순위 P0/P1/P2 분류는 페르소나 메인/서브 + KPI 영향도 기반. 09-priorities는 기능 본문을 반복하지 않고 `FN-` ID + 분류 근거만 적는다
- QA 케이스는 메인 페르소나의 JTBD 시나리오 기반
- **외부 리서치 (필수)**: 임계치·KPI·AI 모델 결정 시 외부 리서치 프로토콜로 업계 벤치마크·최신 모델을 검색해 근거를 병기한다. 리서치 기반 값은 Silent Default가 아닌 '리서치 기반 결정'으로 분류하고 출처를 decision-log에 남긴다. 재사용 가치가 있는 벤치마크·관행 결과는 `domain-research` 스킬을 통해 `research/domain-*.md` 캐시로 편입하고, 이후 정합성 검토는 그 캐시를 참조한다

### Mode C · Rework (항목 재작업)

1. 재작업 대상 파일 + 관련 컨텍스트(다른 산출물 파일들) 적재
2. 사용자에게 **정확히 3개 질문** 제시:

```markdown
{재작업 대상} 재작업. 3개 질문에 답해줘.

Q1. 현재 {대상}의 어떤 점이 문제인가?
  A) {페르소나가 발견한 이슈 후보 1}
  B) {페르소나가 발견한 이슈 후보 2}
  C) {페르소나가 발견한 이슈 후보 3}
  D) 기타 (직접 입력)

Q2. 수정 방향은?
  A) {방향 1}
  B) {방향 2}
  C) {방향 3}
  D) 기타 (직접 입력)

Q3. 수정 시 받아들일 수 있는 트레이드오프는?
  (예: '스프린트 1주 연장 가능', '디자이너 추가 투입 불가', '특정 페르소나의 만족도 일부 양보 가능')
```

3. 응답 기반으로 대상 파일 재생성
4. 의존성 있는 다른 파일도 영향 검사 → 영향 있으면 함께 갱신
5. 4개 이상 질문 필요 판단 시 → Hard Stop으로 격상

#### 의존성 매트릭스

| 재작업 대상 | 함께 갱신 가능 파일 |
|---|---|
| `07-features.md` | `09-priorities.md`, `11-qa-list.md` |
| `09-priorities.md` | `11-qa-list.md` (Task 우선순위) |
| `10-kpi.md` | `09-priorities.md` (P0 결정에 영향 시) |
| `08-ai-agent-spec.md` | `07-features.md`, `11-qa-list.md` |
| `11-qa-list.md` | (단독) |

## Hard Stop 트리거 6종 (의사코드)

```
function check_hard_stop(decision_event):
    # H1. 도메인 지식 충돌
    # (a) 사용자가 직접 제공한 도메인 지식과 충돌 — 사용자 지식이 최우선 SoT
    if user_domain_knowledge.detect_critical_conflict(decision_event):
        return STOP(reason="사용자 제공 도메인 지식과 직접 충돌",
                    detail=conflict_summary)
    # (b) research/domain-*.md 리서치 캐시의 근거와 정면 충돌
    #     (예: 업계 관행·규제와 정면 충돌)
    if research_cache.detect_critical_conflict(decision_event):
        return STOP(reason="리서치 캐시 근거와 정면 충돌",
                    detail=conflict_summary + evidence_with_sources)
    # 주의: 리서치 캐시는 확정 사양이 아니라 참고 근거다. (b)로 발동한 경우
    # 캐시가 옳다고 단정하지 말고, 충돌 근거(출처 포함)를 제시한 뒤
    # 어느 쪽을 따를지 사용자에게 판단을 요청한다.
    
    # H2. 트레이드오프 발견 (페르소나 의견 갈림)
    persona_votes = collect_votes(decision_event, personas)
    if vote_split_ratio(persona_votes) >= 0.4:  # 5명 중 2명 이상 다른 의견
        return STOP(reason="페르소나 의견 분기", 
                    detail=vote_breakdown)
    
    # H3. Silent Default 누적 임계 (기본 3)
    if decision_log.silent_default_count >= SILENT_DEFAULT_THRESHOLD:
        return STOP(reason="명시되지 않은 결정 누적", 
                    detail=silent_default_list)
    
    # H4. Devil's Advocate critical 반론
    devil_opinion = paranoid_reviewer.evaluate(decision_event)
    if devil_opinion.severity == "critical":
        return STOP(reason="Devil's Advocate critical 반론", 
                    detail=devil_opinion.argument)
    
    # H5. 범위 이탈
    if not solution_scope.contains(decision_event.target):
        return STOP(reason="Gate 1.5에서 합의한 V1 범위 이탈", 
                    detail=out_of_scope_target)
    
    # H6. Design Lint (Phase 2에서 prd-to-wireframe이 호출 시)
    if mode == "wireframe_review" and design_system.hard_constraints.detect_violation(decision_event):
        return STOP(reason="design/design-system.md §0 Hard Constraints 위반",
                    detail=design_violations)
    
    return CONTINUE
```

### H6 (Design Lint)의 적용 범위

- `prd-builder-auto` 자체는 와이어프레임을 생성하지 않지만, `prd-to-wireframe`이 본 스킬을 호출해 와이어프레임 검토를 의뢰할 수 있음
- 검토 의뢰 시 mode를 `wireframe_review`로 전달받고, `design-system-builder`가 생성한 `design/design-system.md`(context.json `design_system` 경로)의 **§0 Hard Constraints** 위반을 검사
- 위반 발견 시 H6 발동 → 사용자에게 의도된 위반인지 확인. `prd-to-wireframe` Phase 4는 재생성 3회 실패 시 이 H6으로 격상해 무한 재생성을 방지한다

### Hard Stop 발동 시 동작

1. Auto Phase 즉시 중단
2. `decision_log`에 발동 이유 + 시점 기록
3. `prd-builder-discovery`에 다음 형식으로 보고:

```markdown
⚡ Hard Stop 발동

Trigger: H{번호} - {이유}
Detail: {상세}
현재 작업: {모드 / 진행 중 산출물}
권고 조치:
  - {조치 1} (예: Gate 1.5로 복귀)
  - {조치 2} (예: 특정 결정만 인터랙티브 분리)
```

4. 사용자 응답을 받기 전까지 후속 산출물 생성 중단

## Silent Default 감지기 (의사코드)

```
function detect_silent_default(decision_event):
    # 입력 파일에 명시된 값인지 확인
    explicit_sources = [
        gate1.problem,
        gate1.value_hypothesis,
        gate1.personas,
        gate1_5.solution_scope,
        user_explicit_input,      # rework 모드의 사용자 답변
        research_backed_values    # 외부 리서치 프로토콜로 채운 값 (출처가 decision-log에 기록된 경우)
    ]
    
    for value in decision_event.derived_values:
        if not any(source.contains_explicit(value) for source in explicit_sources):
            # Silent Default 발생
            silent_default_log.append({
                "timestamp": now(),
                "decision_path": decision_event.path,
                "value": value,
                "derivation_basis": decision_event.reasoning,
                "alternatives_considered": decision_event.alternatives
            })
            
            if silent_default_log.count >= SILENT_DEFAULT_THRESHOLD:
                trigger_hard_stop("H3")
    
    return silent_default_log
```

**리서치 기반 값의 처리 (외부 리서치 프로토콜 연계)**: 외부 리서치로 채운 값(임계치·KPI·경쟁 패턴 등)은 출처가 decision-log에 기록되어 있으면 `research_backed_values`로 간주해 Silent Default 카운트에서 제외한다. 출처 없이 채운 값만 SD로 집계한다. 이로써 '리서치 필수'가 H3(SD 누적) Hard Stop을 과도하게 유발하는 것을 방지한다. 단 리서치 출처 자체는 decision-log와 Macro Gate 2 리포트의 '외부 리서치' 섹션에 반드시 노출한다.

### 기록 형식 (`12-decision-log.md`)

```markdown
# Decision Log

## Silent Defaults

### SD-001 · 결제 실패 자동 재시도 3회
- 시점: {timestamp}
- 결정 위치: features.md / 구독 결제 실패 처리
- 추정 근거: 일반적인 구독 커머스 재시도 관행 (1~5회) 중간값
- 검토된 대안: 1회 / 3회 / 5회
- 영향 받는 후속 결정: 우선순위 P0의 결제 성공률 KPI

### SD-002 · ...
```

### 임계값 (`SILENT_DEFAULT_THRESHOLD`)

기본값 **3**. `prd-builder-discovery` 호출 시 변경 가능.

- 낮추면(예: 2): 더 자주 Hard Stop, 더 적은 자동 진행, 사용자 부담 증가
- 높이면(예: 5): 더 적게 Hard Stop, 더 많은 자동 진행, Macro Gate 2에서 검토 부담 증가

## 페르소나 합의 점수 (Macro Gate 2 리포트용)

각 결정에 대해 페르소나들의 합의 정도를 기록.

```
function compute_consensus(decision_event):
    votes = collect_votes(decision_event, active_personas)
    agreement_ratio = max(votes) / total(votes)
    
    if agreement_ratio >= 0.8:
        return "강한 합의"
    elif agreement_ratio >= 0.6:
        return "약한 합의"  # Macro Gate 2 리포트에서 검토 권고 표시
    else:
        return "의견 갈림"  # 이 시점에 이미 H2로 Hard Stop 처리됨
```

Macro Gate 2 리포트의 "페르소나 합의 점수" 섹션에 집계.

## 횡단 검증 호출

| 시점 | 호출 대상 | 검증 내용 |
|---|---|---|
| 모든 산출물 작성 직후 | `editorial-reviewer` | 가독성·용어 일관성 |
| Forward 모드의 솔루션 후보 평가 시 | `research/domain-*.md` 캐시 | 리서치 근거 정합성 (참고 근거로서 대조) |
| Backward 모드의 기능·우선순위 결정 시 | `research/domain-*.md` 캐시 | 리서치 근거 정합성 지속 모니터링 |
| Forward 솔루션 발산 시 | 외부 리서치 (WebSearch) | 경쟁·대안 제품 패턴 |
| Backward 임계치·KPI·AI 모델 결정 시 | 외부 리서치 (WebSearch) | 업계 벤치마크·최신 모델 |
| `wireframe_review` 모드 호출 시 | `design/design-system.md` §0 Hard Constraints | Design Lint (H6 트리거) |

외부 리서치는 `prd-builder-discovery`의 **외부 리서치 프로토콜**을 따른다 (검색량 상한·원문 적재 금지·사용자 제공 지식 최우선·출처 병기·SD 제외). 리서치 값은 확정 사양이 아니므로 단정하지 않고 `editorial-reviewer` 사실 검증과 직렬 연결한다. 재사용 가치가 있는 결과는 `domain-research` 스킬로 `research/domain-*.md` 캐시에 편입한다.

`editorial-reviewer`가 critical 코멘트를 반환하면 자동 반영 후 decision-log에 기록.

## 사용자 대면 제시용 산출 규칙 (솔루션 매트릭스)

`prd-builder-discovery`가 솔루션 매트릭스를 사용자에게 제시(Gate 1.5)할 때 코드·압축 라벨이 새어 나가지 않도록, 본 스킬이 매트릭스를 산출하는 시점에 다음을 보장한다.

- **각 후보에 평이한 설명 필수**: 모든 솔루션 후보는 코드(S1 등)·명사구가 아니라 "이 후보가 실제로 무엇을 하는지, 무엇을 얻고 무엇을 잃는지"를 개발 배경 없는 PM이 이해할 완결문 `summary`로 반드시 포함한다. name/코드만 산출하지 않는다.
- **제시 자족성 신호**: 매트릭스 산출 시 `prd-builder-discovery`가 사용자에게 그대로 노출할 수 있는 '한 줄 평이 설명' 컬럼을 함께 제공한다. 이는 `prd-builder-discovery`의 '사용자 대면 커뮤니케이션 규칙'과 1:1 정합한다.
- **기술 용어 풀이**: 후보 설명에 등장하는 개발 용어(인입 스키마·웹훅·임계치 등)는 최초 1회 역할을 풀어 쓴다.

## 산출물 작성 규칙

`shared/references/`의 가드레일(writing-guardrails 등)을 동일하게 적용.

- 화살표(→) 금지
- 변수명·코드 표기 금지
- 디자인 심미성·개발 구현 디테일 배제
- 기능 정의 작성 고도(Altitude): high-level "왜·무엇"과 정책(Policy)·흐름(Flow)까지만. 버튼·레이블 텍스트, 필드·항목 구성 목록, 마이크로 인터랙션, 상태별 UI 표현 방식, 빈 상태·오류 문구, **계산 수식·임계치·파라미터 값·컴포넌트 동작 정책**은 PRD에 담지 않고 프로토타입/디스크립션(wireframe-description) 단계에서 작성
- 개조식 우선
- **계산 수식은 PRD(auto-backward 산출물 포함)에 작성하지 않는다**: 임계치·점수·차트 정책 등 모든 수식의 SoT는 프로토타입(디스크립션)이다. PRD/기능 정의에는 "임계 초과 시 알림" 수준의 high-level 서술만 둔다. 수식 앵커(`F-{n}`/`F-{n}.p{m}`)는 디스크립션에서 부여·관리하며(`prd-sync` 규약), PRD는 수식 앵커를 보유하지 않는다. 단 임계치·파라미터의 **근거가 된 리서치 출처는 decision-log에 계속 기록**한다(값 자체는 디스크립션으로 전달).
- UI 텍스트는 A/B/C 3요소·어조 규칙

각 산출물은 마크다운으로 `working_dir/auto-{forward|backward}/` 아래에 저장. **Notion 직접 쓰기 금지** — Notion 업로드는 `prd-builder-discovery`가 게이트 통과 시 `notion-organizer`로 위임.

## 단독 호출 시 동작

`prd-builder-discovery` 없이 단독 호출되면:

1. 사용자에게 모드(`forward`/`backward`/`rework`)와 작업 디렉토리 확인
2. 작업 디렉토리에 필요 입력 파일이 존재하는지 검증
3. 누락 파일이 있으면 단독 호출 거부 → `prd-builder-discovery` 권장

단독 호출은 기존 PRD의 특정 섹션만 자동 재생성하는 용도로 제한. Notion 업로드 없이 로컬 파일 수정만 수행.

## 호출 종료 시 보고

작업 종료 시 `prd-builder-discovery`에 다음 형식으로 보고.

```markdown
prd-builder-auto 종료
  mode: {모드}
  status: completed | hard_stop | error
  outputs: [생성 파일 목록]
  hard_stop_events: [발동 트리거 목록]
  silent_default_count: {숫자}
  research_count: {숫자}        # 외부 리서치 수행 건수 (Gate 2 리포트 '외부 리서치' 섹션 노출용)
  consensus_summary:
    strong: N
    weak: N
    split: N
```

`prd-builder-discovery`는 이 보고를 Macro Gate 2 리포트 생성에 활용.
