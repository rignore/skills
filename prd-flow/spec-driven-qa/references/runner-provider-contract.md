# Runner Provider 및 Runbook 계약 (`runbook-v1`)

대상 독자: runner provider 구현자, CI 운영자, QA adapter 개발자

목적: 승인된 `scenario-v1`을 반복 실행할 수 있는 저장형 runbook과 provider 입출력 경계를 정의한다. 시나리오 필드의 원본 계약은 [scenario-schema.md](scenario-schema.md), 최종 판정 결과는 [result-schema.md](result-schema.md)를 따른다.

`validate-contracts.py`는 이 문서에서 `runbook-v1`을 기계 검증한다. 검증 호출은 exact `spec-bundle-v1`과 원본 `scenario-v1`도 함께 제공해야 한다. Validator는 scenario hash와 보존 필드를 다시 계산하며, context가 없는 runbook은 실행 gate를 통과하지 못한다. P2(Playwright web runner)의 `run-web-playwright.mjs`는 `runner-request-v1` preflight와 `runner-output-v1` conformance를 실행 경계에서 검증한다. Web 전용 config와 collector 규칙은 [web-playwright-provider.md](web-playwright-provider.md)를 따른다.

## 목차

1. 규범 용어와 책임 경계
2. Provider 지원 행렬
3. Runbook 생성과 고정
4. `runbook-v1` 필드
5. Mutation 승인 계약
6. 결정론적 실행 규칙
7. `runner-request-v1` 실행 요청
8. `runner-output-v1` 관측 출력
9. 종료 상태 mapping
10. 완전 예시
11. Provider 적합성 기준

## 1. 규범 용어와 책임 경계

이 문서의 `MUST`, `MUST NOT`, `SHOULD`는 각각 필수, 금지, 권고를 뜻한다.

실행 계층은 아래 책임을 분리해야 한다.

| 계층 | 책임 | 금지 사항 |
| --- | --- | --- |
| Scenario Planner | 명세에서 시나리오 후보를 만든다. | 실행 결과를 예측하거나 Pass를 선언하면 안 된다. |
| Runbook Compiler | 검토가 끝난 시나리오를 provider별 명령으로 고정한다. | CI 실행 중 locator, action, oracle을 새로 추론하면 안 된다. |
| Runner Provider | 저장된 runbook을 그대로 실행하고 관측값을 수집한다. | 최종 `pass` 또는 `fail`을 스스로 판정하면 안 된다. |
| Independent Judge | 명세, expected, oracle, 관측 증거를 대조한다. | 실행 agent의 서술형 자기 보고를 증거로 채택하면 안 된다. |

LLM은 시나리오 후보 생성과 의미 판정에만 사용할 수 있다. CI runner는 LLM을 호출하면 안 된다. CI는 저장된 `runbook-v1`만 재생해야 한다.

Runner의 `completed` 보고는 실행 완료 상태일 뿐 Pass 증거가 아니다. Runner가 계산한 assertion도 실제값, 기대값, 사용한 evidence ID를 함께 남겨야 한다.

## 2. Provider 지원 행렬

| `target.platform` | `method` | `runner_provider` | `target.device` | 실행 지원 |
| --- | --- | --- | --- | --- |
| `web` | `web` | `web-playwright` | `desktop` | 지원 |
| `mobile_web` | `web` | `web-playwright` | `responsive` | 지원 |
| `android` | `native` | `native-android` | `emulator` | APK만 지원 |
| `ios` | `native` | `native-ios` | `simulator` | contract only |
| 모든 명시된 platform | `unit`, `integration` | `developer-test` | scenario와 동일 | 프로젝트 runner가 있을 때 지원 |
| 모든 명시된 platform | `manual` | `manual` | scenario와 동일 | 사람 실행 결과를 구조화해 수집 |

아래 조합은 허용하지 않는다.

- `mobile_web`을 `native` method나 `native-android` provider로 실행하면 안 된다.
- Android physical device, device farm, 원격 Appium endpoint를 현재 지원 대상으로 표시하면 안 된다.
- Android artifact는 `apk`만 허용한다. `aab`는 실행 artifact로 받으면 안 된다.
- iOS는 `execution.enabled`를 반드시 `false`로 저장한다. iOS 실행 요청에는 `execution.status=not_started`와 non-empty unsupported reason을 반환한다.
- Android 결과를 iOS 결과로 일반화하면 안 된다.

## 3. Runbook 생성과 고정

Runbook Compiler는 아래 순서로 runbook을 만든다.

1. `scenario-v1` 계약과 provider 지원 행렬을 검증한다.
2. `review_status`가 실행 승인을 뜻하는 값인지 확인한다.
3. scenario의 `source_refs`, target, fixture, expected, oracle, mutation 정책을 runbook에 그대로 고정한다.
4. versioned project config에서 provider argument를 해석한다.
5. 해석에 사용한 secret-free project config projection의 SHA-256을 `project_config_sha256`에 저장한다.
6. locator 후보 중 provider 우선순위가 가장 높은 locator 하나를 선택한다.
7. 실제 실행값만 가진 `provider_args`, `timeout_ms`, `retry_policy`, `provider_defaults_version`을 step에 고정한다.
8. `evidence_plan`에 oracle별 필수 증거를 연결한다.
9. 고정 plan의 SHA-256을 계산한다.
10. mutation이 있으면 고정 plan과 step ID에 결합된 승인 기록을 연결한다.
11. 완성된 runbook JSON의 SHA-256을 계산해 실행 요청과 결과에 기록한다.

`native-android` runbook은 top-level `runbook_state`를 반드시 포함한다. 허용 값은 두 개다.

| 값 | 의미 | 승인 규칙 |
| --- | --- | --- |
| `preflight` | Provider plan과 runtime readiness만 확인한다. Mutation 실행은 금지한다. | `approval_ref`는 반드시 `null`이다. Runner는 `--preflight-only`에서만 받는다. |
| `executable` | 승인된 mutation run을 재생할 수 있다. | Exact `approval_ref`가 필수다. Runner는 일반 실행에서만 받는다. |

`runbook_state`와 `approval_ref`는 authorization 상태이므로 `integrity.plan_sha256` projection에 포함하지 않는다. Preflight와 executable runbook의 action, fixture, locator, timeout, oracle 등 plan 필드는 동일해야 하며 plan hash도 같아야 한다. 완성된 JSON의 SHA-256은 두 상태를 구분하므로 runner request는 선택한 상태까지 고정한다.

Runbook을 저장한 뒤 action, fixture, oracle, locator, timeout, retry, provider default, target 또는 evidence plan을 바꾸면 새 runbook revision을 만들어야 한다. Project config hash가 바뀐 경우에도 새 runbook을 compile해야 한다. 기존 runbook과 승인 기록을 덮어쓰면 안 된다.

Runbook에는 `project-config://...` 같은 mutable reference, locator candidate 목록, 환경변수 치환식 또는 실행 시점 template을 남기면 안 된다. Scenario의 의미 reference는 `arguments`에 보존할 수 있지만 Runner는 이를 실행값으로 사용하지 않는다. Runner가 사용하는 값은 compile 시점에 해석한 `provider_args`뿐이다.

### 3.1 Hash 계산

`integrity.plan_sha256`은 아래 필드를 선택한 고정 plan projection의 SHA-256이다.

- `scenario_id`
- `schema_version`
- `runbook_id`
- `spec_version`
- `scenario_hash`
- `source_refs`
- `review_status`
- `method`
- `execution`
- `target`
- `runner_provider`
- `provider_binding`
- `project_config_sha256`
- `preconditions`
- `fixture`
- `steps`
- `expected`
- `oracle`
- `mutation_policy`
- `evidence_plan`

계산기는 object key를 정렬하고 불필요한 공백을 제거한 UTF-8 JSON을 사용해야 한다. 배열 순서는 보존한다. `runbook_state`, `approval_ref`, `integrity`는 plan projection에서 제외한다.

완성된 runbook 파일의 hash는 파일 외부에서 계산한다. Runner는 실행 요청의 `runbook_sha256`과 실제 파일 hash가 다르면 실행하지 않는다. 이때 `execution.status=not_started`와 blocker 후보를 반환한다.

## 4. `runbook-v1` 필드

| Field | Type | 요구사항 |
| --- | --- | --- |
| `schema_version` | string | 반드시 `runbook-v1`이어야 한다. |
| `runbook_state` | string | `native-android`에서는 `preflight` 또는 `executable`이 필수다. 다른 provider에서는 사용하지 않는다. |
| `runbook_id` | string | revision을 식별하는 불변 ID다. |
| `scenario_id` | string | 원본 `scenario-v1.id`와 같아야 한다. |
| `spec_version` | string | 원본 `scenario-v1.spec_version`과 같아야 한다. |
| `scenario_hash` | string | canonical `scenario-v1` JSON의 SHA-256이다. |
| `source_refs` | array | 원본 scenario의 비어 있지 않은 목록을 보존해야 한다. |
| `review_status` | string | 실행 가능한 runbook에서는 반드시 `approved`다. |
| `method` | string | 원본 scenario의 method를 보존해야 한다. |
| `execution.enabled` | boolean | 자동 또는 지정 provider 실행 가능 여부다. iOS는 `false`다. |
| `target` | object | `platform`, `device`, 필요한 경우 `artifact_type`을 포함한다. |
| `runner_provider` | string | 지원 행렬의 provider 중 하나다. |
| `provider_binding` | object | `contract_version`, `implementation_version`, `defaults_version`을 고정한다. |
| `project_config_sha256` | string | `provider_args` 해석에 사용한 secret-free project config projection의 SHA-256이다. |
| `preconditions` | array | 실행 전에 기계적으로 확인할 조건이다. |
| `fixture` | object | 고정 test data와 환경 분리 정보를 담는다. |
| `steps` | array | 순서가 고정된 provider action이다. scenario step ID를 보존한다. |
| `expected` | array | 명세가 요구하는 결과다. 자동 실행에서는 비어 있을 수 없다. |
| `oracle` | object | `mode`와 비어 있지 않은 `rules`를 포함한다. |
| `mutation_policy` | object | mutation 유무와 관계없이 반드시 존재한다. |
| `evidence_plan` | array | 각 oracle rule을 증명할 구조화된 증거를 지정한다. |
| `integrity.plan_sha256` | string | 고정 plan projection의 SHA-256이다. |
| `approval_ref` | object 또는 null | mutation 승인 기록을 참조한다. 읽기 전용 runbook은 `null`이다. |

### 4.1 Step 요구사항

모든 step은 아래 필드를 포함해야 한다.

| Field | Type | 요구사항 |
| --- | --- | --- |
| `id` | string | Scenario step ID를 보존한다. |
| `action` | string | Provider가 실행할 고정 action이다. |
| `description` | string | Step의 관측 가능한 목적이다. |
| `mutation` | enum | `none`, `potential`, `confirmed` 중 하나다. |
| `arguments` | object 또는 null | Scenario의 secret-free 의미 reference다. Runner 실행 입력이 아니다. |
| `provider_args` | object | Project config에서 해석한 실제 실행값이다. `_ref`, candidate 목록, template을 포함하면 안 된다. |
| `timeout_ms` | integer | `1..120000` 범위에서 고정한다. |
| `retry_policy` | enum | `never` 또는 `safe`다. Mutation step은 `never`다. |
| `max_attempts` | integer | `retry_policy=never`이면 `1`이다. `safe`도 고정된 양의 값을 가져야 한다. |
| `provider_defaults_version` | string | `provider_binding.defaults_version`과 정확히 같아야 한다. |

Runbook Compiler는 scenario step을 삭제하거나 의미를 바꾸면 안 된다. 여러 provider action으로 나눠야 하면 파생 ID를 `<scenario-step-id>.<sequence>` 형식으로 만들고 원본 step ID를 `source_step_id`에 남겨야 한다.

Provider default를 적용한 경우에도 최종 `timeout_ms`, `retry_policy`, `max_attempts`를 각 step에 materialize해야 한다. `provider_defaults_version`은 어떤 default set에서 값을 얻었는지 추적하는 값이며 실행 시점 default 재해석을 허용하지 않는다.

### 4.2 Fixture 요구사항

오류와 경계 상태는 fixture, mock, seed script 또는 test endpoint로 만들어야 한다. 운영 데이터를 직접 수정해 상태를 만들면 안 된다.

`fixture.destructive`가 `true`이면 `fixture.environment`는 `isolated`여야 한다. Runner는 이 조건을 실행 직전에 다시 검사해야 한다. 격리 환경을 확인할 수 없으면 `execution.status=not_started`와 blocker 후보를 반환한다.

Runbook과 fixture에 credential, password, token, signing key, APK bytes, Base64 artifact를 넣으면 안 된다. 인증 상태는 project runtime이 runbook 밖에서 준비하고, 수집 로그는 secret 값을 제거해야 한다.

## 5. Mutation 승인 계약

`mutation_policy`는 아래 규칙을 따른다.

| Field | 요구사항 |
| --- | --- |
| `mode` | `deny` 또는 `require_approval`이다. |
| `approval_scope` | 승인할 step ID 목록이다. `mode=require_approval`이면 비어 있을 수 없다. |
| `retry_policy` | mutation이 있으면 반드시 `never`다. |

`mutation`이 `potential` 또는 `confirmed`인 모든 step ID는 `approval_scope`에 포함되어야 한다. `mode=deny`인 runbook에 mutation step이 있으면 실행하면 안 된다.

`approval_ref`는 아래 필드를 포함해야 한다.

| Field | 요구사항 |
| --- | --- |
| `id` | 외부 승인 저장소의 불변 기록 ID다. |
| `record_sha256` | 승인 기록 원문의 SHA-256이다. |
| `plan_sha256` | `integrity.plan_sha256`과 같아야 한다. |
| `provider_plan_hash` | Provider가 별도 preflight hash를 만들면 필수다. Android MCP가 여기에 해당한다. |
| `runtime_binding_sha256` | Android MCP에서는 필수다. 승인한 launcher, runtime source, tool·schema, artifact, JDK·APK verifier, device, Appium 설정을 포함한 `native-mcp-binding-v1` 전체 hash와 같아야 한다. |
| `approved_step_ids` | `mutation_policy.approval_scope`와 같아야 한다. |
| `environment` | 실행할 격리 환경 식별자 또는 환경 등급이다. |
| `scope` | `single_run` 또는 `runbook_revision`이다. |
| `expires_at` | 승인 만료 시각이다. 만료가 없으면 명시적으로 `null`을 저장한다. |
| `approved_by_ref` | 승인 주체의 감사용 reference다. credential을 넣으면 안 된다. |

실행 agent가 승인 기록을 만들거나 승인했다고 자기 보고하면 안 된다. CI는 실행 전에 승인 기록의 hash, plan hash, provider plan hash, runtime binding hash, step ID, 환경, 만료를 검증해야 한다. 하나라도 다르면 `execution.status=not_started`와 blocker 후보를 반환한다.

Mutation step은 자동 재시도하면 안 된다. Runner 프로세스가 중단된 경우에도 같은 step을 자동으로 다시 실행하면 안 된다.

## 6. 결정론적 실행 규칙

Provider는 아래 값을 runbook에 고정해야 한다.

- action 순서와 정확히 하나의 resolved locator
- timeout, wait condition, retry 횟수
- viewport 또는 Emulator configuration
- fixture version과 seed
- mock 또는 test endpoint version
- expected와 oracle rule
- build reference와 artifact hash

Provider는 실행 중 DOM, accessibility tree, UI hierarchy를 보고 새 action이나 locator를 생성하면 안 된다. Locator가 해석되지 않으면 임의 selector, 두 번째 candidate 또는 좌표 tap으로 우회하지 않는다.

읽기 전용 step만 안전하다고 입증된 경우에 한해 고정 횟수 retry를 허용한다. Mutation step의 retry는 항상 `never`다.

## 7. `runner-request-v1` 실행 요청

Runner는 `runner-request-v1` 한 건과 hash가 일치하는 `runbook-v1` 한 건을 입력으로 받는다. Request는 runbook 내용을 바꾸지 않고 실행 대상을 결합한다.

| Field | Type | 요구사항 |
| --- | --- | --- |
| `schema_version` | string | 반드시 `runner-request-v1`이다. |
| `run_id` | string | 실행 attempt를 식별하는 불변 ID다. |
| `requested_at` | RFC 3339 string | 요청 생성 시각이다. |
| `attempt` | integer | 1 이상의 실행 attempt 번호다. |
| `runbook_id` | string | 대상 `runbook-v1.runbook_id`와 같아야 한다. |
| `runbook_ref` | string | Project-relative JSON path다. 절대 경로와 `..`를 허용하지 않는다. |
| `runbook_sha256` | string | Canonical runbook JSON의 SHA-256이다. |
| `plan_sha256` | string | `runbook.integrity.plan_sha256`과 같아야 한다. |
| `runner_provider` | string | Runbook provider와 같아야 한다. |
| `target` | object | Runbook target과 같아야 한다. |
| `project_config_sha256` | string | Runbook에 저장된 project config hash와 같아야 한다. |
| `runtime_binding` | object 또는 null | External runtime binding의 `binding_id`와 `sha256`이다. Android에서는 필수다. |
| `build` | object 또는 null | 선택한 build의 `ref`와 `sha256`이다. |
| `artifact` | object 또는 null | Native artifact의 `id`, `type`, `sha256`이다. Android에서는 APK만 허용한다. |

Runner는 request, runbook, project config, runtime binding의 hash를 실행 전에 비교해야 한다. 값이 다르면 step을 시작하지 않는다. Request에 credential, token, binary artifact, Base64 또는 secret runtime value를 넣으면 안 된다.

## 8. `runner-output-v1` 관측 출력

Runner는 Judge 호출 전에 `runner-output-v1`을 작성한다. 이 envelope는 관측 사실만 담으며 `verdict`, `oracle_results`, 예상 판정 또는 실행 agent의 성공 주장을 포함하면 안 된다.

### 8.1 Top-level fields

| Field | Type | 요구사항 |
| --- | --- | --- |
| `schema_version` | string | 반드시 `runner-output-v1`이다. |
| `run_id` | string | Request의 `run_id`와 같다. |
| `runbook_id`, `runbook_hash`, `plan_sha256` | string | 실제 실행한 frozen runbook을 식별한다. |
| `scenario_id`, `spec_version`, `scenario_hash` | string | Runbook의 scenario identity를 보존한다. |
| `target` | object | 실제 target이다. |
| `runner_provider` | string | 실제 provider다. |
| `provider_binding` | object | Runbook의 contract, implementation, defaults version을 보존한다. |
| `project_config_sha256` | string | Runbook의 hash와 같아야 한다. |
| `started_at`, `finished_at` | RFC 3339 string | Runner attempt의 시작·종료 시각이다. |
| `execution` | object | Status, attempt, retry, runner version, command evidence를 기록한다. |
| `subject` | object | Build, native artifact, native runtime identity다. 해당하지 않는 값은 `null`이다. |
| `step_results` | array | 모든 runbook step에 대한 관측 결과다. |
| `evidence` | array | 구조화된 evidence registry다. |
| `errors` | array | Sanitization된 runner error다. 없으면 빈 배열이다. |
| `unsupported_reason` | string 또는 null | Capability가 없을 때만 non-empty다. |
| `missing_evidence` | array | 수집하지 못한 oracle evidence 후보다. |
| `diagnostic_attachments` | array | 판정 입력에서 제외할 image, screenshot, video다. |

`execution`은 아래 필드를 모두 포함한다.

```json
{
  "status": "completed",
  "attempt": 1,
  "retry_count": 0,
  "command_evidence_ref": "runner-command",
  "runner_version": "1.0.0"
}
```

`status`는 `not_started`, `partial`, `completed` 중 하나다. Mutation step을 시작했다면 `retry_count`는 `0`이어야 한다.

### 8.2 Step result와 error

각 `step_results[]`는 아래 필드를 모두 포함한다.

| Field | Type | 요구사항 |
| --- | --- | --- |
| `step_id` | string | Runbook step ID다. |
| `status` | enum | `not_started`, `completed`, `error`, `skipped` 중 하나다. |
| `attempt_count` | integer | 0 이상의 실제 시도 횟수다. |
| `started_at`, `finished_at` | string 또는 null | 실행하지 않은 step은 `null`이다. |
| `evidence_refs` | array | 이 step이 생성한 evidence ID다. |
| `error` | object 또는 null | 오류가 있으면 top-level error와 같은 shape를 쓴다. |

각 `errors[]`는 `code`, `category`, `message`, `step_id`, `evidence_refs`, `retryable`을 포함한다. `category`는 `contract`, `unsupported`, `environment`, `runtime`, `product`, `evidence` 중 하나다. Error message에는 credential, token, raw response body 또는 민감한 UI text를 넣으면 안 된다.

### 8.3 Evidence

Provider는 대상에 맞는 구조화된 증거를 수집해야 한다.

| Provider | 필수 또는 조건부 증거 |
| --- | --- |
| `web-playwright` | locator 결과, DOM·accessibility state, URL·route, network·console 오류, 허용된 API·storage 상태, 실행 명령, build reference |
| `native-android` | step result, locator 결과, `wait_for` 상태, sanitization된 UI hierarchy, Android logcat, APK hash, package ID, Emulator·OS·orientation·reset policy |
| `developer-test` | 명령, exit code, test case 결과, sanitization된 stdout·stderr, build hash |
| `manual` | `producer.type=human`인 `structured_log`, 수행 절차 revision, 외부 시스템이 생성한 상태 증거 |

실행 대상은 `subject`에 한 번 기록한다. 각 evidence item은 `id`, `kind`, `collected_at`, `producer`, `sha256`, `redactions`를 포함한다. Payload는 `record`에, result-relative file은 `artifact_ref`에 두며 두 필드 중 정확히 하나만 사용한다.

`sha256`은 [result-schema.md](result-schema.md)의 evidence hash 규칙을 따른다. Redaction된 `record`는 canonical JSON bytes를, `artifact_ref`는 참조 파일의 raw bytes를 hash한다.

Screenshot과 video는 선택형 diagnostic attachment다. 이미지나 영상만으로 oracle을 충족하거나 `pass`를 판정하면 안 된다. 실행 agent의 자연어 요약도 evidence item으로 등록하면 안 된다.

## 9. 종료 상태 mapping

Runner는 최종 verdict가 아니라 실행 진행 상태와 종료 원인을 반환한다.

| 상황 | `execution.status` | Runner가 남길 추가 정보 | Judge가 사용할 후보 verdict |
| --- | --- | --- | --- |
| 모든 실행 step과 증거 수집 시도가 끝남 | `completed` | 관측 evidence와 누락 evidence | `pass`, `fail`, `conflict`, `insufficient_evidence` |
| 지원 대상이지만 runtime, 인증, fixture, 승인, hash 문제로 시작하지 못함 | `not_started` | `environment` 또는 `runtime` error | `blocked` |
| 실행 도중 environment 문제가 생겨 완료하지 못함 | `partial` | error와 수집 완료 evidence | `blocked` |
| provider가 없는 platform 또는 artifact 요청 | `not_started` | `unsupported` error와 non-empty reason | `unsupported` |

제품 동작이 expected와 다르거나 앱이 실행 중 crash한 사실을 구조화된 증거로 수집했다면 environment error로 바꾸면 안 된다. Runner는 `product` error와 관측 evidence를 반환하고 Judge가 expected와 대조하게 한다.

## 10. 완전 예시

이 절의 origin, route, locator는 범용 default가 아닌 합성 sample 값이다.

### 10.1 Compiler 입력 project config projection

```json
{
  "schema_version": "project-runner-config-v1",
  "provider": "web-playwright",
  "provider_contract_version": "web-playwright-runner-v1",
  "defaults_version": "web-playwright-defaults-v1",
  "origin": "http://127.0.0.1:4173",
  "routes": {"record": "/qa-sample/records/fixture-record"},
  "locators": {
    "save_control": {"by": "test_id", "value": "qa-sample-save-control"}
  },
  "timeouts_ms": {"goto": 30000, "click": 10000},
  "read_only_max_attempts": 1
}
```

### 10.2 Frozen `runbook-v1`

```json
{
  "schema_version": "runbook-v1",
  "runbook_id": "web-save-completed-state-r1",
  "scenario_id": "web-save-completed-state",
  "spec_version": "2026-08-01.1",
  "scenario_hash": "sha256:2f0f15e47e4f7786eaf52d6fad3dd1397de3746ca076366032569002c1b9abbf",
  "source_refs": [
    {"source_id": "product-requirements", "anchor_id": "saved-record-becomes-complete"},
    {"source_id": "workflow-policy", "anchor_id": "complete-state-requires-persisted-value"}
  ],
  "review_status": "approved",
  "method": "web",
  "execution": {"enabled": true},
  "target": {"platform": "web", "device": "desktop"},
  "runner_provider": "web-playwright",
  "provider_binding": {
    "contract_version": "web-playwright-runner-v1",
    "implementation_version": "1.0.0",
    "defaults_version": "web-playwright-defaults-v1"
  },
  "project_config_sha256": "sha256:981a4f2b6d84210a3614688834962ee8d5d98d653ae2a64db33576c528489887",
  "preconditions": [
    {
      "id": "test-session-ready",
      "description": "An isolated test session is available.",
      "verification": "runner",
      "check_ref": "test-session-health"
    }
  ],
  "fixture": {
    "kind": "seed",
    "ref": "record-ready-to-save-v1",
    "purpose": "baseline",
    "destructive": false,
    "environment": "isolated"
  },
  "steps": [
    {
      "id": "open-record",
      "action": "goto",
      "description": "Open the seeded record",
      "mutation": "none",
      "arguments": {"route_ref": "record-editor"},
      "provider_args": {
        "url": "http://127.0.0.1:4173/qa-sample/records/fixture-record",
        "wait_until": "domcontentloaded"
      },
      "timeout_ms": 30000,
      "retry_policy": "never",
      "max_attempts": 1,
      "provider_defaults_version": "web-playwright-defaults-v1"
    },
    {
      "id": "submit-record",
      "action": "click",
      "description": "Activate the save control",
      "mutation": "confirmed",
      "arguments": {"control_ref": "save-control"},
      "provider_args": {
        "locator": {"by": "test_id", "value": "qa-sample-save-control"}
      },
      "timeout_ms": 10000,
      "retry_policy": "never",
      "max_attempts": 1,
      "provider_defaults_version": "web-playwright-defaults-v1"
    }
  ],
  "expected": [
    {
      "id": "visible-state-is-complete",
      "description": "The visible record state equals complete.",
      "source_refs": [
        {"source_id": "product-requirements", "anchor_id": "saved-record-becomes-complete"}
      ]
    },
    {
      "id": "persisted-state-is-complete",
      "description": "The persisted record state equals complete.",
      "source_refs": [
        {"source_id": "workflow-policy", "anchor_id": "complete-state-requires-persisted-value"}
      ]
    }
  ],
  "oracle": {
    "mode": "deterministic",
    "rules": [
      {
        "id": "visible-state-check",
        "kind": "deterministic",
        "expectation_id": "visible-state-is-complete",
        "evidence_kind": "dom_state",
        "operator": "equals",
        "actual_path": "/state_text",
        "value": "complete"
      },
      {
        "id": "persisted-state-check",
        "kind": "deterministic",
        "expectation_id": "persisted-state-is-complete",
        "evidence_kind": "api_state",
        "operator": "equals",
        "actual_path": "/body/state",
        "value": "complete"
      }
    ]
  },
  "mutation_policy": {
    "mode": "require_approval",
    "approval_scope": ["submit-record"],
    "retry_policy": "never"
  },
  "evidence_plan": [
    {"oracle_rule_id": "visible-state-check", "evidence_kind": "dom_state"},
    {"oracle_rule_id": "persisted-state-check", "evidence_kind": "api_state"}
  ],
  "integrity": {"plan_sha256": "sha256:c3d335f10d71a2a61e50b6ce4730bd2de2a5450c97e68e62454134d5bac720bb"},
  "approval_ref": {
    "id": "approval:sample",
    "record_sha256": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "plan_sha256": "sha256:c3d335f10d71a2a61e50b6ce4730bd2de2a5450c97e68e62454134d5bac720bb",
    "approved_step_ids": ["submit-record"],
    "environment": "isolated",
    "scope": "single_run",
    "expires_at": null,
    "approved_by_ref": "approver:sample"
  }
}
```

### 10.3 `runner-request-v1`

```json
{
  "schema_version": "runner-request-v1",
  "run_id": "run-save-state-web-001",
  "requested_at": "2026-08-01T02:00:00Z",
  "attempt": 1,
  "runbook_id": "web-save-completed-state-r1",
  "runbook_ref": "qa/runbooks/web-save-completed-state-r1.json",
  "runbook_sha256": "sha256:1c4bfe5a9e6ea2a092b753d56e616ba8a98c7a0111f328c96e2b5ebfd4729f58",
  "plan_sha256": "sha256:c3d335f10d71a2a61e50b6ce4730bd2de2a5450c97e68e62454134d5bac720bb",
  "runner_provider": "web-playwright",
  "target": {"platform": "web", "device": "desktop"},
  "project_config_sha256": "sha256:981a4f2b6d84210a3614688834962ee8d5d98d653ae2a64db33576c528489887",
  "runtime_binding": null,
  "build": {
    "ref": "sample-build-42",
    "sha256": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
  },
  "artifact": null
}
```

### 10.4 `runner-output-v1`

```json
{
  "schema_version": "runner-output-v1",
  "run_id": "run-save-state-web-001",
  "runbook_id": "web-save-completed-state-r1",
  "runbook_hash": "sha256:1c4bfe5a9e6ea2a092b753d56e616ba8a98c7a0111f328c96e2b5ebfd4729f58",
  "plan_sha256": "sha256:c3d335f10d71a2a61e50b6ce4730bd2de2a5450c97e68e62454134d5bac720bb",
  "scenario_id": "web-save-completed-state",
  "spec_version": "2026-08-01.1",
  "scenario_hash": "sha256:2f0f15e47e4f7786eaf52d6fad3dd1397de3746ca076366032569002c1b9abbf",
  "target": {"platform": "web", "device": "desktop"},
  "runner_provider": "web-playwright",
  "provider_binding": {
    "contract_version": "web-playwright-runner-v1",
    "implementation_version": "1.0.0",
    "defaults_version": "web-playwright-defaults-v1"
  },
  "project_config_sha256": "sha256:981a4f2b6d84210a3614688834962ee8d5d98d653ae2a64db33576c528489887",
  "started_at": "2026-08-01T02:00:00Z",
  "finished_at": "2026-08-01T02:00:04Z",
  "execution": {
    "status": "completed",
    "attempt": 1,
    "retry_count": 0,
    "command_evidence_ref": "runner-command",
    "runner_version": "1.0.0"
  },
  "subject": {
    "build": {
      "ref": "sample-build-42",
      "sha256": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    },
    "artifact": null,
    "native_runtime": null
  },
  "step_results": [
    {
      "step_id": "open-record",
      "status": "completed",
      "attempt_count": 1,
      "started_at": "2026-08-01T02:00:01Z",
      "finished_at": "2026-08-01T02:00:02Z",
      "evidence_refs": ["opened-route"],
      "error": null
    },
    {
      "step_id": "submit-record",
      "status": "completed",
      "attempt_count": 1,
      "started_at": "2026-08-01T02:00:02Z",
      "finished_at": "2026-08-01T02:00:03Z",
      "evidence_refs": ["submit-locator", "visible-record-state", "api-record-state"],
      "error": null
    }
  ],
  "evidence": [
    {
      "id": "runner-command",
      "kind": "test_command",
      "collected_at": "2026-08-01T02:00:00Z",
      "producer": {"type": "runner", "name": "web-playwright", "version": "1.0.0"},
      "sha256": "sha256:34feb3cbc1a453620e03d9852b92fc49bc29b3ed3a6ac87d6da04d931e2fdc5c",
      "redactions": [],
      "record": {"runbook_ref": "qa/runbooks/web-save-completed-state-r1.json"}
    },
    {
      "id": "opened-route",
      "kind": "dom_state",
      "collected_at": "2026-08-01T02:00:02Z",
      "producer": {"type": "runner", "name": "web-playwright", "version": "1.0.0"},
      "sha256": "sha256:918352055c443faee7d8d02e04b7023f7603535c8b3eebafd24b518bb541afb0",
      "redactions": [],
      "record": {"route": "/qa-sample/records/fixture-record"}
    },
    {
      "id": "submit-locator",
      "kind": "locator_result",
      "collected_at": "2026-08-01T02:00:03Z",
      "producer": {"type": "runner", "name": "web-playwright", "version": "1.0.0"},
      "sha256": "sha256:2a6f04df2a031a18957918e35ab42046d132b20b20bd92b43c88a6c59618e36c",
      "redactions": [],
      "record": {"match_count": 1, "action": "click"}
    },
    {
      "id": "visible-record-state",
      "kind": "dom_state",
      "collected_at": "2026-08-01T02:00:03Z",
      "producer": {"type": "runner", "name": "web-playwright", "version": "1.0.0"},
      "sha256": "sha256:f46ec65da10725c3a8deebe7545d2f0fae9f0fcc76a3ca0e98b6a8850791ea0d",
      "redactions": [],
      "record": {"state_text": "complete"}
    },
    {
      "id": "api-record-state",
      "kind": "api_state",
      "collected_at": "2026-08-01T02:00:03Z",
      "producer": {"type": "api_probe", "name": "sample-api-probe", "version": "1"},
      "sha256": "sha256:3523f3d00c490618520279d62c603ccfb5c6d675aca55a8a0c17a533b0423c5d",
      "redactions": [],
      "record": {"status": 200, "body": {"state": "complete"}}
    }
  ],
  "errors": [],
  "unsupported_reason": null,
  "missing_evidence": [],
  "diagnostic_attachments": []
}
```

`runner-output-v1`에 verdict가 없는 것이 정상이다. `api-record-state` evidence를 Independent Judge가 oracle과 대조한 뒤 `result-v1`을 만든다.

## 11. Provider 적합성 기준

Provider 구현은 아래 항목을 모두 충족해야 한다.

- Project config를 compile 시점에 해석하고 `project_config_sha256`과 resolved `provider_args`를 runbook에 고정한다.
- Runbook에 mutable project config reference나 locator candidate 목록을 남기지 않는다.
- 지원 행렬 밖의 target을 실행하지 않고 `execution.status=not_started`와 unsupported reason을 반환한다.
- Request, runbook, plan, project config, runtime binding hash를 검증한다.
- CI 실행 중 LLM을 호출하지 않는다.
- 저장된 step 순서, locator, timeout, retry, provider default, oracle을 바꾸지 않는다.
- mutation 승인 범위와 격리 환경을 실행 직전에 재검증한다.
- mutation step을 자동 재시도하지 않는다.
- credential, token, binary artifact를 runbook이나 결과에 직렬화하지 않는다.
- 구조화된 증거와 diagnostic attachment를 분리한다.
- `runner-output-v1`에 verdict나 `oracle_results`를 쓰지 않는다.
