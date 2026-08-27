# Context 수집과 Problem Candidate 규약

## 조사 중단 기준

각 트랙/기업 Context Pack은 다음 질문에 답할 수 있을 때 충분하다.

1. primary user가 누구인가.
2. 어떤 workflow에서 문제가 발생하는가.
3. 빈도·심각도·현재 비용을 뒷받침하는 근거가 무엇인가.
4. 현재 대안과 결함이 무엇인가.
5. 기업/트랙 자산이 왜 필요한가.
6. 해커톤 안에 어떤 관찰로 핵심 가설을 반증할 수 있는가.

답이 없는 항목을 검색량으로 감추지 않는다. `UNKNOWN`으로 표시하고 인터뷰, organizer 질문, prototype test 중 가장 싼 검증을 선택한다.

## 목표 역산과 interactive interview

먼저 목표 결과(본선 진출, 수상, 기업 선택 등)를 적고 다음을 역산한다.

```text
Goal → official decision criteria → required evidence → required context → cheapest acquisition
```

규칙과 rubric은 가능하면 요약이 아니라 원문을 보존한다. 기업 인터뷰 영상은 화자·timestamp·원문/요약을 함께 남긴다. IR·공식 문서·기술 블로그는 실제 수치와 발표 시점을 기록한다.

자료 조사 후 남은 공백 중 사람이 답해야 하는 것만 질문한다.

```markdown
### Context Interview
1. Question: ...
   Why: ...
   Decision affected: ...
```

한 번에 최대 3개만 묻고, 답을 Fact로 둘지 stakeholder opinion으로 둘지 구분한다.

## Source discipline

각 핵심 주장에 다음을 붙인다.

```text
Claim | Source/link | Source type | Published/observed date | Confidence | Implication
```

- 회사의 미래 의도는 공식 자료 없이 단정하지 않는다.
- 시장 규모는 문제 심각도의 대체물이 아니다.
- 사용자 quote 한 개를 전체 시장의 대표로 일반화하지 않는다.
- 경쟁사 기능 부재만으로 사용자 pain을 입증하지 않는다.
- source가 오래됐거나 이해관계가 있으면 표시한다.

## Problem Candidate Card

```markdown
### Candidate: [short name]
- User/context:
- Current job/workflow:
- Friction and consequence:
- Evidence:
- Current workaround:
- Why sponsor/track matters:
- Core hypothesis:
- Cheapest falsification test:
- P0 demo slice:
- Dependencies/data access:
- Main counterargument:
- Risks:
```

## 병렬 탐색 규약

- Scout마다 트랙/기업 하나를 소유한다.
- 모든 Scout에 같은 Competition Lock, 시간 상한, Candidate Card schema를 준다.
- Scout는 code와 공용 문서를 수정하지 않고 조사 결과만 반환한다.
- 서로의 후보를 보지 않고 1차 탐색해 anchoring을 줄인다.
- 통합자는 중복을 병합하되 반대 근거를 삭제하지 않는다.
- 후보 수보다 근거 품질을 우선한다. 트랙당 2개를 넘긴 뒤에는 새 후보보다 검증에 시간을 쓴다.
- 많은 기업을 동시에 볼 때는 후보 12~20개까지 허용하되, 중앙 오케스트레이터에는 Scout별 상위 2개와 탈락 사유만 전달해 context를 통제한다.

## 우선순위 규약

1. hard fail을 먼저 제거한다: 규칙 위반, data/access 부재, 안전·법무 위험, 핵심 demo 불가능.
2. 남은 후보를 공통 기준으로 비교한다.
3. 점수마다 한 문장 이상의 근거를 남긴다.
4. sensitivity check를 한다: 특정 기준 하나가 바뀌면 1위가 뒤집히는가.
5. 상위 후보의 가장 강한 반론과 중단 조건을 적는다.
6. 사람은 최고 점수뿐 아니라 evidence quality와 accepted trade-off를 보고 선택한다.

## 최소 실증 선택

| Hypothesis | 우선 실증 |
|---|---|
| 문제 존재/빈도 | 사용자 인터뷰, workflow 관찰, 운영 data |
| 시간·단계 감소 | 동일 task before/after 측정 |
| 정확도·품질 개선 | 작은 labeled set, expert blind comparison |
| 사용 가능성 | representative user task completion |
| 기술 가능성 | real/sample data spike, latency/cost 측정 |
| 기업 fit | 공식 product/API/strategy와 traceability |

설문 의향만으로 행동 가설을 PASS 처리하지 않는다. prototype 만족도만으로 business outcome을 입증하지 않는다.
