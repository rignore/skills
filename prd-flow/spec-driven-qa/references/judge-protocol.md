# Independent Judge Protocol

대상 독자: Judge 구현자, QA gate 운영자, result sink adapter 개발자

목적: 승인된 명세와 runner가 수집한 구조화된 증거만 사용해 `result-v1.verdict`를 판정한다. 이 protocol은 scenario 생성, 실행, 판정을 분리하고 여섯 개 verdict 외의 값을 허용하지 않는다.

## 목차

1. 책임과 독립성
2. Judge 입력
3. Evidence 적격성
4. Oracle 평가
5. Semantic judge 제한
6. Verdict 결정 규칙
7. Result 작성
8. Calibration gate
9. 판정 예시
10. 적합성 기준

## 1. 책임과 독립성

Judge는 `expected`와 observed evidence를 대조한다. Runner를 실행하거나 fixture를 만들지 않는다.

독립성은 아래 조건을 모두 충족해야 한다.

- Scenario Planner와 Judge는 conversation state, hidden memory, prior conclusion을 공유하지 않는다.
- Judge는 planner가 제시한 예상 verdict나 실행 agent의 자연어 보고를 받지 않는다.
- Judge는 source anchor, expected, oracle, runner metadata, evidence registry, 고정 rubric만 받는다.
- Judge는 입력 evidence를 수정하지 않는다. 새 판정은 기존 판정을 덮어쓰지 않고 별도 attempt로 남긴다.
- LLM을 쓰는 semantic 평가도 별도 context에서 실행한다. 같은 model을 사용하더라도 독립 호출이어야 한다.

독립성의 목적은 generator가 만든 기대나 runner의 성공 보고가 판정에 섞이는 것을 막는 데 있다. 실행 agent가 "모든 단계가 성공했다"고 보고해도 그 문장은 Pass 증거가 아니다.

## 2. Judge 입력

Judge는 한 scenario 실행마다 아래 입력을 받는다.

| 입력 | 필수 내용 |
| --- | --- |
| Spec snapshot | `spec-bundle-v1`에서 정확히 해석한 source와 anchor 내용, 각 content hash |
| Scenario snapshot | `scenario-v1`, scenario hash, `spec_version`, `source_refs`, `expected`, `oracle`, severity |
| Runbook identity | `runbook_id`, `runbook_hash`, `integrity.plan_sha256` |
| Runner output | provider, version, execution status, target, build·artifact hash, step result, runtime error |
| Evidence registry | `result-v1` evidence item 후보와 payload 또는 artifact reference |
| Judge config | protocol version, deterministic evaluator version, semantic rubric·prompt version if used |

`source_refs`는 `{source_id, anchor_id}`로 정확히 해석되어야 한다. `expected[].source_refs`는 scenario 최상위 `source_refs`의 subset이어야 한다.

Judge 입력에 아래 항목을 넣으면 안 된다.

- credential, password, token, cookie, signing key
- APK bytes 또는 Base64 artifact
- planner의 chain-of-thought나 예상 답
- runner agent의 Pass·Fail 자기 보고
- screenshot이나 video

Scenario validation 단계에서 source anchor를 찾을 수 없거나 hash가 다르면 contract error로 거부해야 한다. Judge는 dangling source reference를 다른 요약으로 대체하거나 verdict를 만들면 안 된다.

## 3. Evidence 적격성

Evidence item은 아래 공통 필드를 가져야 한다.

- `id`
- `kind`
- `collected_at`
- `producer.type`, `producer.name`, 선택형 `producer.version`
- `sha256`
- `record` 또는 result-relative `artifact_ref` 중 정확히 하나

Judge는 hash를 검증하고 현재 run ID와 연결된 evidence만 사용해야 한다. Redaction 후 저장된 payload를 기준으로 hash를 계산한다.

허용 evidence kind는 다음과 같다.

- `structured_log`
- `dom_state`
- `accessibility_state`
- `ui_hierarchy`
- `locator_result`
- `network_error`
- `console_error`
- `url_state`
- `api_state`
- `storage_state`
- `db_state`
- `test_command`
- `android_logcat`
- `build_hash`
- `artifact_hash`

Screenshot, image, video, MP4는 evidence kind가 아니다. 이 파일은 `diagnostic_attachments`에만 둘 수 있고 Judge 입력에서 제외한다.

아래 값도 단독 증거로 인정하지 않는다.

- runner의 `completed` status
- action 성공 여부만 담은 요약
- LLM이 화면이나 로그를 해석한 자연어 문장
- 출처와 hash가 없는 복사된 log
- backend 상태 expected를 UI text만으로 확인한 관측

예를 들어 화면의 상태 label이 `complete`여도 API 상태가 `pending`이면 화면 관측만으로 저장 완료를 증명할 수 없다. Oracle이 backend 상태를 요구하면 `api_state`, `db_state` 또는 허용된 integration test evidence가 필요하다.

Manual method도 서술형 자기 보고만으로 Pass를 판정하지 않는다. `producer.type=human`인 `structured_log`에 수행자 reference, procedure revision, 시각, 관측 필드, 외부 시스템 evidence reference를 기록해야 한다.

## 4. Oracle 평가

Judge는 deterministic oracle을 먼저 평가한다. 의미 동치처럼 rule로 확정할 수 없는 조건만 semantic judge에 넘긴다.

`oracle`은 `mode`와 비어 있지 않은 `rules`를 포함한다. Rule 공통 필드는 아래와 같다.

- `id`
- `kind`
- `expectation_id`
- `evidence_kind`

### 4.1 Deterministic oracle

Deterministic rule은 `operator`, `actual_path`, 필요한 경우 `value`를 추가한다. 허용 operator는 다음과 같다.

- `equals`
- `not_equals`
- `contains`
- `exists`
- `absent`
- `matches_regex`
- `status_code`

평가기는 rule별로 아래 결과 중 하나를 만든다.

| `oracle_results[].status` | 의미 |
| --- | --- |
| `matched` | actual이 expected rule과 일치한다. |
| `mismatched` | 적격 evidence의 actual이 expected와 다르다. |
| `not_evaluated` | 필요한 evidence가 없거나 적격하지 않아 평가하지 못했다. |

각 oracle result는 `oracle_id`, `expectation_id`, `status`, 사용한 `evidence_refs`, 민감 정보를 제거한 `actual` 또는 `null`, `reason` 또는 `null`을 포함해야 한다. `matched`와 `mismatched`는 적격 evidence ID를 하나 이상 참조한다. `mismatched`와 `not_evaluated`에는 비어 있지 않은 `reason`을 반드시 쓴다.

Evidence가 없을 때 expected 값을 actual로 대체하면 안 된다. Locator를 찾지 못했다는 구조화된 결과는 `absent` rule의 actual이 될 수 있지만, locator 실행 자체가 없었다면 `not_evaluated`다.

### 4.2 Semantic oracle

Semantic rule은 `rubric`을 포함한다. Semantic evaluator는 아래 자료만 받는다.

- rule이 참조하는 source anchor 원문
- `expectation_id`가 가리키는 expected
- rule이 허용한 evidence item
- frozen rubric

Semantic evaluator는 rule마다 `matched`, `mismatched`, `not_evaluated` 중 하나와 source reference, evidence reference, 짧은 reason을 반환한다. Source나 evidence reference를 제시하지 못하면 `not_evaluated`다. Semantic `oracle_results[]`는 판정에 사용한 `{source_id, anchor_id}` 객체를 `source_refs`에 저장한다. 이 필드는 `judge.mode=semantic`일 때 필수다. `matched`와 `mismatched`에서는 비어 있을 수 없다. `not_evaluated`에서는 성공적으로 해석한 source reference를 모두 기록하며, 필수 source를 하나도 해석하지 못했을 때만 빈 배열을 허용한다.

Semantic model identity는 `result-v1.judge.model`에 아래 shape로 저장한다.

```json
{
  "provider": "<configured-provider>",
  "model_version": "<immutable-model-version>",
  "prompt_version": "<immutable-prompt-version>",
  "rubric_hash": "sha256:<64-lowercase-hex>"
}
```

값은 배포 환경 설정이 제공한다. 범용 contract는 특정 provider나 model을 고정하지 않는다.

### 4.3 Manual oracle

Manual rule은 versioned `checklist`를 포함한다. Judge는 checklist item별 관측값과 외부 evidence reference를 확인한다. 필수 item이 비어 있으면 `not_evaluated`다.

## 5. Semantic judge 제한

LLM은 semantic rule 판정에만 사용할 수 있다. 아래 작업에는 LLM을 사용하면 안 된다.

- CI runbook action 생성 또는 변경
- locator 탐색과 자동 대체
- exact value, 존재 여부, count, HTTP status, schema, state code 판정
- 누락 evidence 보완 또는 actual 값 추정
- source conflict를 임의 우선순위로 해소

Semantic LLM 출력은 evidence가 아니다. 독립 Judge의 rule evaluation일 뿐이며 반드시 원본 source와 evidence ID를 인용해야 한다.

Semantic judge 실행 metadata에는 아래 값을 기록한다.

- model provider와 model version
- prompt version
- rubric hash
- input source hash와 evidence hash
- 실행 시각과 attempt ID

같은 입력에서도 LLM 결과가 달라질 수 있다. 재판정은 새 attempt로 기록하고 기존 result를 덮어쓰면 안 된다.

## 6. Verdict 결정 규칙

허용 verdict는 아래 여섯 개로 고정한다.

- `pass`
- `fail`
- `conflict`
- `insufficient_evidence`
- `blocked`
- `unsupported`

Judge는 아래 순서로 첫 번째 해당 verdict를 선택한다.

1. `conflict`: 적용 가능한 source anchor 두 개 이상이 서로 양립할 수 없는 expected를 요구한다.
2. `unsupported`: target platform, device, artifact 또는 provider가 현재 실행 범위 밖이며 `execution.status=not_started`다.
3. `blocked`: 지원 대상이지만 runtime, 인증 상태, fixture, immutable approval, hash 문제로 실행을 완료하지 못했다. `execution.status`는 `not_started` 또는 `partial`이다.
4. `fail`: 적격 evidence를 가진 `oracle.rules[]` 항목이 하나 이상 `mismatched`다.
5. `insufficient_evidence`: mismatch는 없지만 `oracle.rules[]` 항목이 하나 이상 `not_evaluated`다.
6. `pass`: 모든 `oracle.rules[]` 항목이 `matched`이고 위 조건이 하나도 없다.

Severity는 보고와 release gate 우선순위를 바꾸지만 verdict 의미를 바꾸지 않는다.

### 6.1 `conflict`

`conflict`는 명세 출처가 서로 다른 정답을 요구할 때만 사용한다. LLM의 불확실성이나 evidence 누락을 conflict로 분류하면 안 된다.

Judge는 충돌하는 `source_id`, `anchor_id`, 각 요구값과 충돌 이유를 `conflicts`에 기록한다. Source 우선순위가 별도 정책으로 명시되지 않았다면 Judge가 PRD, Acceptance Criteria, 정책, 디자인 중 하나를 임의 선택하면 안 된다.

### 6.2 `unsupported`와 `blocked`

Provider 자체가 없는 경우는 `unsupported`다. 현재 iOS native 실행, Android physical device, AAB가 여기에 해당한다.

지원 provider가 있지만 local runtime, fixture, 인증 상태, 승인 기록이 준비되지 않은 경우는 `blocked`다. 이 두 verdict를 제품 결함인 `fail`과 섞으면 안 된다.

### 6.3 `fail`과 `insufficient_evidence`

제품 동작이 expected와 다르다는 적격 evidence가 있으면 `fail`이다. 앱 crash, HTTP 오류, 잘못된 persisted state도 expected와 대조할 수 있으면 fail 대상이다.

실행은 끝났지만 판정에 필요한 evidence가 없으면 `insufficient_evidence`다. Screenshot이나 video만 남은 경우, UI만 확인했고 backend oracle evidence가 없는 경우가 여기에 해당한다.

### 6.4 `pass`

`pass`는 모든 `oracle.rules[]` 항목이 적격 evidence로 `matched`일 때만 가능하다. 아래 항목은 `pass` 조건이 아니다.

- command exit code가 0이다.
- browser 또는 app action이 끝났다.
- runner가 성공을 보고했다.
- screenshot 또는 video에서 정상처럼 보인다.
- 일부 oracle만 matched다.

## 7. Result 작성

Judge는 한 scenario 실행마다 `result-v1` 하나를 작성한다. 최소한 아래 내용을 보존해야 한다.

- run, scenario, spec version, runbook hash
- target과 runner provider
- execution metadata
- build와 artifact hash
- immutable evidence registry
- `oracle_results`
- 여섯 값 중 하나인 `verdict`
- 해당하는 경우 `blockers`, `conflicts`, `missing_evidence`
- `judge.mode`, `judge.name`, `judge.version`, `judge.attempt`, `judge.model`, `judge.source_hashes`, `judge.evidence_hashes`, `judge.decided_at`

`judge.model`은 semantic LLM을 사용하지 않으면 `null`이다. Semantic mode에서는 위에서 정의한 `provider`, `model_version`, `prompt_version`, `rubric_hash` 객체를 기록한다. Semantic `oracle_results[]`는 판정에 사용한 `source_refs`도 기록한다.

Judge는 runner evidence의 record나 artifact를 수정하지 않는다. 판정 reason에는 source reference와 evidence reference를 함께 남겨 제3자가 판정을 재현할 수 있게 한다.

Result sink는 verdict를 저장할 뿐 다시 판정하면 안 된다. 조직별 Done gate나 workflow 상태 변경은 범용 Judge가 아니라 optional adapter가 담당한다.

### 7.1 P4 실행 경계

`scripts/judge-results.mjs`는 Node.js 표준 라이브러리만 사용한다. 입력은 정확한 `spec-bundle-v1`, `scenario-v1`, `runbook-v1`, `runner-output-v1` snapshot이다. Judge는 scenario·runbook·evidence hash를 다시 계산하며, runner가 기록한 evidence를 수정하지 않는다.

Deterministic scenario는 아래 명령으로 판정한다.

```bash
node scripts/judge-results.mjs \
  --bundle spec-bundle.json \
  --scenario scenario.json \
  --runbook runbook.json \
  --runner-output runner-output.json \
  --output result.json
```

Evaluator는 `runbook.evidence_plan[].after_step_id`가 지정한 step evidence 중 rule의 `evidence_kind`와 일치하는 항목을 선택한다. 정확히 한 항목을 선택하지 못하면 임의로 최신 항목을 고르지 않고 `not_evaluated`로 기록한다. `artifact_ref`는 core evaluator가 내용을 읽지 않으므로 deterministic `actual_path` 입력으로 사용할 수 없다.

Semantic scenario는 두 번에 나눠 실행한다.

```bash
node scripts/judge-results.mjs \
  --bundle spec-bundle.json \
  --scenario semantic-scenario.json \
  --runbook runbook.json \
  --runner-output runner-output.json \
  --prepare-semantic \
  --output semantic-request-batch.json

node scripts/judge-results.mjs \
  --bundle spec-bundle.json \
  --scenario semantic-scenario.json \
  --runbook runbook.json \
  --runner-output runner-output.json \
  --semantic-responses semantic-response-batch.json \
  --output result.json
```

첫 명령이 만드는 `semantic-judge-batch-v1`은 아래 정보만 포함한다.

- source ID, anchor ID, source content hash, anchor statement
- expectation ID와 expected description
- oracle ID와 frozen rubric
- 허용 evidence item과 evidence hash
- request·batch·rubric hash

Scenario title, precondition, step, runner error, runner status, 예상 verdict, planner 대화는 batch에 넣지 않는다. Semantic evaluator는 batch만 새 context에 전달받아야 한다. `semantic-judge-response-batch-v1`은 request와 batch hash를 그대로 인용하고, 각 결과에 사용한 source·evidence reference와 immutable model identity를 기록한다. 응답이 request 범위 밖 source나 evidence를 인용하면 core Judge가 거부한다.

적격 source나 evidence가 없어 request가 0건이면 LLM을 호출하지 않는다. Core Judge가 해당 rule을 `not_evaluated`로 기록하고 `judge.mode=deterministic`, `judge.model=null`인 `insufficient_evidence` 결과를 만든다.

명세 충돌은 source adapter나 별도 normalization 단계가 만든 `source-conflicts-v1`로 전달할 수 있다. 각 conflict는 `id`, `description`, 서로 다른 정답을 요구하는 source reference 두 개 이상을 포함한다. Judge는 모든 reference가 bundle에서 해석되는지만 확인하며 충돌을 새로 추론하거나 해소하지 않는다.

P4 자동 Judge는 `deterministic`과 `semantic` mode를 실행한다. `manual` oracle은 계약에 남아 있지만 이 script가 사람 관측을 대신 만들지 않는다.

## 8. Calibration gate

Deterministic rule은 기계 검증으로 테스트한다. Semantic judge를 자동 release gate에 사용하려면 별도 calibration을 통과해야 한다.

최소 calibration 절차는 다음과 같다.

1. 의미 판정 gold case를 30개 이상 준비한다.
2. 두 사람이 같은 rubric으로 독립 label을 작성한다.
3. 두 사람의 원 label로 Cohen's κ를 계산한다.
4. 불일치는 두 labeler와 제3의 도메인 책임자가 근거를 대조해 하나의 gold label로 확정한다. 조정 전 label도 보존한다.
5. 확정한 gold label을 기준으로 자동 `pass` precision을 `true positive pass / all predicted pass`로 계산한다. 예측한 `pass`가 0건이면 gate를 통과하지 못한다.

Semantic 자동 release gate는 아래 조건을 모두 만족해야 통과한다.

- gold case가 30개 이상이다.
- Cohen's κ가 0.6 이상이다.
- 배포 정책에 `minimum_pass_precision`이 설정돼 있다.
- 측정한 자동 `pass` precision이 `minimum_pass_precision` 이상이다.
- 조정되지 않은 label과 평가 오류가 남아 있지 않다.

30건과 Cohen's κ 0.6은 현재 아키텍처의 초기 release guardrail이며 외부 표준값이 아니다. 파일럿 결과로 재검토한다. `minimum_pass_precision`은 제품 위험도에 따라 배포 정책이 정하며, 값이 없으면 자동 판정을 배포하지 않는다. Calibration을 통과하기 전 semantic 판정은 사람 검토 없이 release gate를 자동 통과시키면 안 된다.

`scripts/calibrate-judge.py`는 Python 표준 라이브러리만 사용한다.

```bash
python3 scripts/calibrate-judge.py semantic-calibration.json --output calibration-report.json
```

`semantic-calibration-v1`은 아래 필드를 포함한다.

- `calibration_id`
- `judge`: provider, immutable model version, prompt version, rubric hash
- `policy.minimum_case_count`: 30 이상
- `policy.minimum_kappa`: 초기값 0.6
- `policy.minimum_pass_precision`: 배포 정책이 정한 0 이상 1 이하의 값
- `cases[]`: case ID, 서로 다른 frozen semantic request의 `input_sha256`, 두 사람의 원 label, 조정 결과, 같은 input hash에 묶인 자동 prediction

각 원 label은 `actor_type=human`, 서로 다른 `actor_ref`, 여섯 verdict 중 하나를 기록한다. 조직의 identity provider가 actor reference의 실제 사람 여부와 독립 작업 절차를 보증해야 한다. Core script는 문자열만으로 사람 여부를 증명하지 않는다.

모든 case는 `adjudication.status=resolved`와 최종 `gold_verdict`를 가져야 한다. 두 원 label이 같으면 gold verdict도 그 값을 유지한다. 두 원 label이 다르면 두 labeler와 다른 제3의 `adjudicator_ref`가 필요하다.

Prediction에는 `input_sha256`, verdict, `evaluation_error`를 기록한다. 평가 오류가 있으면 verdict는 `null`일 수 있다. Case가 30개 미만이거나 Cohen's κ를 계산할 수 없거나 예측 Pass가 0건이면 command는 gate 실패 exit code `1`을 반환한다. 입력 계약 위반은 exit code `2`를 반환한다.

예를 들어 30건 중 자동 Judge가 10건을 Pass로 예측했고 gold Pass가 9건이면 자동 Pass precision은 0.9다. `minimum_pass_precision=0.95`인 배포에서는 다른 조건을 충족해도 gate가 실패한다. Unit test가 만드는 30건 fixture는 계산 검증용 synthetic data이며 사람 calibration 결과로 사용할 수 없다.

## 9. 판정 예시

### 9.1 UI와 backend 상태 불일치

- Source expected: 저장 성공 뒤 persisted state는 `complete`다.
- Evidence: DOM state는 `complete`, API state는 `pending`이다.
- Oracle: API state `equals complete` rule이 `mismatched`다.
- Verdict: `fail`이다.

화면 표시가 expected와 같아도 backend 상태 evidence가 다르므로 Pass가 아니다.

### 9.2 영상만 남은 실행

- Source expected: Android control이 저장 뒤 사라진다.
- Evidence: MP4만 있고 locator result, UI hierarchy, API state가 없다.
- Oracle: 필수 `absent` rule을 평가할 수 없다.
- Verdict: `insufficient_evidence`다.

영상은 diagnostic attachment이므로 oracle evidence로 사용할 수 없다.

### 9.3 명세 출처 충돌

- Acceptance Criteria anchor: 저장 뒤 상태는 `complete`다.
- 정책 anchor: 승인 전 상태는 `pending`을 유지해야 한다.
- 두 anchor가 같은 precondition과 시점을 지칭한다.
- Verdict: `conflict`다.

Judge는 둘 중 하나를 선택하지 않고 두 source reference와 충돌 값을 기록한다.

### 9.4 iOS 실행 요청

- Scenario target: `platform=ios`, `runner_provider=native-ios`다.
- Contract: `execution.enabled=false`이며 XCUITest provider가 없다.
- Verdict: `unsupported`다.

Android 결과를 대신 사용하거나 responsive mobile web으로 바꾸면 안 된다.

## 10. 적합성 기준

Judge 구현은 아래 항목을 모두 충족해야 한다.

- generator와 runner의 conversation state를 받지 않는다.
- source anchor와 evidence hash를 검증한다.
- deterministic oracle을 semantic oracle보다 먼저 평가한다.
- exact rule 판정에 LLM을 사용하지 않는다.
- semantic 결과가 source와 evidence ID를 인용하게 한다.
- 실행 agent 자기 보고, screenshot, image, video를 증거로 채택하지 않는다.
- 여섯 verdict와 고정된 결정 순서만 사용한다.
- evidence가 없으면 Pass 대신 `insufficient_evidence`를 사용한다.
- provider 부재와 환경 blocker를 구분한다.
- source conflict를 임의로 해소하지 않는다.
- 기존 evidence와 result attempt를 덮어쓰지 않는다.
