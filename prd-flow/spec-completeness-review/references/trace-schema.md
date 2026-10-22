# 추적표 형식

추적표는 JSON 파일 하나다. 원문에서 뽑은 요구사항 한 행마다 원문 위치, 대상 위치, 판정 상태, 근거를 적는다. 기계 검사(`scripts/check_trace.py`)가 이 형식을 확인한다. 경로는 모두 검사를 실행하는 폴더(`--root`) 기준의 상대 경로다.

## 1. 최상위

```json
{
  "schema_version": 1,
  "metadata": { ... },
  "requirements": [ ... ],
  "exclusions": [ ... ]
}
```

## 2. metadata

| 필드 | 뜻 | 누가 채우나 |
|---|---|---|
| `mode` | `initial`(첫 작성) 또는 `revision`(개정) | 사람 |
| `purpose` | 무엇을 무엇에 대조하는지 한 문장 | 사람 |
| `extraction_rule` | 원문을 행으로 쪼갠 규칙. 3.1절의 규칙을 그대로 적거나 바꾼 점을 적는다 | 사람 |
| `machine_validation_limit` | "기계 검사는 문장의 의미 동등성을 판정하지 못한다"처럼 기계 검사의 한계를 적는다. '의미'라는 낱말이 들어가야 검사를 통과한다 | 사람 |
| `sources` | 원문 목록. 항목마다 `id`, `path`, `sha256`, `role`(무엇의 정본인가) | 사람. 지문은 `shasum -a 256`으로 구한다 |
| `id_families` | 행 번호 접두어와 원문 id의 대응. 예: `{"PRD": "prd", "AC": "tickets", "SC": "baseline"}` | 사람 |
| `active_target` | 검토 대상 사양. `path`는 사람이 적고, `sha256`과 `line_count`는 스크립트가 채운다 | `refresh_trace.py`, `freeze_snapshot.py` |
| `snapshots` | 차수별 불변 사본. 항목마다 `round`, `path`, `sha256`, `line_count`, `state`, `frozen_at` | `freeze_snapshot.py` |
| `review_records` | 회차별 판정 기록. 항목마다 `round`, `path`, `result`, `subject_sha256`(그 회차가 본 사본의 지문), `requirement_fail`, `exclusion_fail` | `record_round.py` |
| `criteria_rulings` | 판정 기준 기록. 추가만 한다(6절) | 사람 |
| `requirement_count`, `status_counts`, `disposition_counts`, `exclusion_count` | 합계. 검사기가 실제 행과 대조한다 | `refresh_trace.py`와 다른 스크립트가 행에서 다시 센다. 손으로 쓰지 않는다 |

개정 모드에서는 개정 전 판본을 `sources`에 `baseline`으로 넣고, 같은 파일을 `freeze_snapshot.py --baseline`으로 차수 0 사본으로도 얼린다. 원문이 git에 있으면 `source_commit`(커밋 해시)과 `source_path_at_commit`을 함께 적어 두면 나중에 출처를 증명하기 쉽다.

## 3. requirements 행

```json
{
  "id": "PRD-012",
  "source_location": "4.5:L88-L90",
  "summary": "승인 회신이 반려나 보류이면 설비 재가동을 실행하지 않는다.",
  "target_locations": ["docs/agents/08-ai-agent-spec.md#5.6"],
  "verification_status": "unverified",
  "evidence": "사양 5.6 셋째 행이 반려·보류 시 수행 금지를 적는다.",
  "disposition": "preserved",
  "pending_reason": ""
}
```

| 필드 | 뜻 |
|---|---|
| `id` | `접두어-세자리번호`. 접두어마다 001부터 빈틈 없이 잇는다. 빈틈이 있으면 누가 행을 지웠다는 신호라 검사가 실패한다 |
| `source_location` | `절:L시작-L끝`. 절 표기는 원문 제목의 앞부분과 맞아야 하고, 시작 줄은 그 제목 줄이거나 그 절 안(하위 절 포함)에 있어야 한다. 첫 제목 전의 줄은 절 표기를 `머리말`로 쓴다. 예: `§3.1:L40-L42`, `4.5 인수 조건:L88-L90` |
| `summary` | 이 행이 요구하는 것 한 문장. 주체·조건·동작·부정을 원문 그대로 유지한다 |
| `target_locations` | 사양에서 이 요구를 담는 곳. `경로#절` 배열. 여러 절에 나뉘어 있으면 모두 적는다 |
| `verification_status` | 5절 |
| `evidence` | 판정 근거. 사양의 어느 문장이 어떻게 담는지 적는다 |
| `disposition` | 개정 모드에서만 필수. 개정 전 판본 대비 이 요구가 어떻게 됐나: `preserved`(그대로), `condensed_equivalent`(줄였지만 같은 뜻), `weakened`(약해짐), `missing`(빠짐), `move_candidate`(다른 문서로 옮길 후보), `source_revised`(상위 원문이 바뀌어 의도적으로 고침. 새 원문을 `sources`에 올리고 그 원문 위치를 가리키는 행을 따로 둔다) |
| `pending_reason` | 상태가 대기 중일 때 무엇을 기다리는지 |
| `source_id` | 선택. 같은 접두어의 행이 서로 다른 원문에서 왔을 때 이 행의 원문 id. 없으면 `id_families`를 따른다 |
| `destination` | 목적지 확인 대기·확인 행에만. 옮겨 갈 다른 문서의 `경로#절`. 원문이나 이 사양을 가리키면 검사가 실패한다. 목적지가 아직 정해지지 않았으면 비워 두고, `target_locations`에는 옮기기 전까지 이 사양 안에 임시로 둔 곳을 적는다 |

### 3.1 한 행으로 쪼개는 규칙

- 한 행에는 "누가, 어떤 조건에서, 무엇을 한다 또는 하지 않는다" 하나만 담는다.
- 업무 의미 6요소, 곧 발동 조건·주체·의무·예외·실패 처리·권한 경계 가운데 하나가 따로 빠질 수 있으면 별도 행으로 둔다. 검토자도 이 6요소로 판정한다.
- 같은 뜻이 원문 여러 곳에 반복되면 한 행만 만들고 `evidence`에 다른 위치를 적는다. 첫 작성 모드에서는 PRD와 티켓에 흩어진 같은 요구를 한 행으로 합치는 판단이 자주 필요하다.
- "A하고 B한다"는 두 행이다. 금지와 허용이 한 문장에 있으면 나눈다.
- 예외 조건("다만 ~이면")은 본 규칙과 따로 한 행으로 둔다. 예외가 빠지는 것이 가장 흔한 누락이다.
- 실패했을 때의 처리, 기록 의무, 사람에게 알리는 의무는 각각 한 행이다.
- 수치(시간, 횟수, 임계)는 그 값이 있는 행의 `summary`에 그대로 적는다.

## 4. exclusions

원문에 있지만 사양에 두지 않는 것이다. 행마다 `id`(`EX-01`), `source_location`, `category`, `summary`, `evidence`(왜 두지 않는가)를 적는다. 원문이 둘 이상이면 `source_id`도 적는다. 검사기는 제외 행의 위치도 요구사항 행과 같은 방식으로 확인한다. 검토 뒤에는 `record_round.py`가 `review_verdict`와 `review_reason`을 적는다.

제외 행의 줄 범위가 요구사항 행과 겹치면 `check_trace.py`가 경고를 낸다. 같은 원문 줄을 요구와 제외에 동시에 두면, 뜻이 빠져도 제외를 근거로 통과할 수 있기 때문이다. 한 줄에 요구와 비요구가 섞여 있어 겹침이 정당하면 `overlap_reason`에 무엇을 뺐는지 적어 경고를 끈다.

두지 않아도 되는 대표 범주는 4가지다.

- 작성 경위와 판본 이력
- 개발자가 정할 구현 상세(식별자, 필드, 자료형, API, 저장, 배포)
- 다른 문서가 정본인 내용(그 문서 경로를 `evidence`에 적는다)
- 화면 배치처럼 에이전트 동작이 아닌 것

업무 동작을 바꾸는 내용은 제외할 수 없다. 제외하려면 사람의 결정이 필요하고, 그 경우 요구사항 행으로 두고 상태를 `approved_removal`로 적는다. 그리고 판정 기준 기록에 그 행 id를 `affects`에 넣고 `decided_by`를 적은 결정 항목을 더한다. 이 항목이 없으면 기계 검사가 실패한다.

## 5. verification_status

| 값 | 뜻 | 다음 행동 |
|---|---|---|
| `unverified` | 아직 판정 전 | 검토 회차를 돈다 |
| `verified_equivalent` | 검토자가 뜻이 같다고 판정 | 없음 |
| `restore_required` | 검토자가 빠지거나 약해졌다고 판정 | 사양을 고친다. 사유는 `pending_reason` |
| `restored_pending_review` | 고쳤지만 아직 다시 판정받지 않음. `pending_reason`에 무엇을 고쳤는지 적는다 | 다음 회차 |
| `destination_pending` | 다른 문서로 옮기기로 사람이 정했으나 아직 확인하지 않음. 판정 기준 기록에 결정 항목이 있어야 한다 | 검토자가 `destination` 문서에 있다고(목적지가 없으면 이 사양에 임시 경계로 남아 있다고) 판정하면 `destination_verified`가 된다. 확인되지 않으면 회차가 `FAIL`이다. 판정 전 대기 상태 자체는 마감을 막지 않는다 |
| `destination_verified` | 다른 문서로 옮겼고 확인됨 | 없음 |
| `approved_removal` | 사람이 삭제를 결정함 | 없음. 판정 기준 기록에 이 행을 가리키는 결정 항목이 있어야 한다 |
| `source_conflict_pending` | 원문끼리 같은 경우를 다르게 적어 어느 쪽을 따를지 정해지지 않음. 이 행이 남아 있으면 회차가 통과하지 않는다 | 사람이 정해 판정 기준 기록에 적은 뒤 `unverified`로 되돌린다 |

## 6. criteria_rulings — 판정 기준 기록

검토 중에 "이 경우는 이렇게 판정한다"고 정한 것을 쌓는다. **지우지 않고 추가만 하며, 같은 대상에 대해 뒤 항목이 앞 항목을 대체한다.** 앞 항목을 대체할 때는 새 항목에 "앞 판정 기준 가운데 ~를 대체한다"고 적는다. 앞 항목의 문구를 고쳐 쓰지 않는다.

`approved_by`는 사람이 결정한 항목에만 적는다. 결정한 사람이나 직책(예: 기획자, 품질 책임자)이다. "작성자", "자동", "에이전트" 같은 값은 사람의 결정을 증명하지 못해 검사가 거부한다. `basis`에는 결정이 남은 곳(회의록, 결정 로그 항목)을 적는다. 승인된 삭제와 목적지 확인 대기 행은 이 칸이 있는 항목이 그 행을 `affects`로 가리켜야 기계 검사를 통과한다.

`decided_by`에는 누가 어떤 성격으로 정했는지를 적는다. 예: 기획자 결정, 기획자 결정의 적용, 작성 정책(템플릿이 고정한 구조), 원문 해석(더 엄격한 쪽 채택), 사람 판단이 필요 없는 문장 정리. 검토자가 어느 기준을 다시 따져도 되는지 알 수 있어야 한다.

```json
{
  "decided_at": "2026-09-22",
  "decided_by": "기획자",
  "affects": ["SC-031"],
  "ruling": "템플릿이 고정한 제목과 번호는 구조 지적 대상이 아니다.",
  "basis": "사양 템플릿 3절이 제목을 글자 그대로 고정한다.",
  "effect": "검토자는 이 제목을 바꾸라는 지적을 내지 않는다.",
  "approved_by": "기획자"
}
```

검토자에게 이 기록 전체를 함께 준다. 주지 않으면 이미 결정한 지적이 다음 회차에 다시 올라온다.
