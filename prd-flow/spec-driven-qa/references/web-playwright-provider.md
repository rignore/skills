# Playwright Web Provider (`web-playwright-runner-v1`)

대상 독자: project adapter 개발자, CI 운영자, QA runner 구현자

목적: Desktop web과 responsive mobile web 시나리오를 deterministic `runbook-v1`으로 compile하고 Playwright에서 재생하는 범용 provider 계약을 정의한다. Project URL, selector, fixture value는 이 core 문서나 코드에 넣지 않고 versioned project config로 주입한다.

## 1. 실행 경계

`web-playwright`는 아래 조합만 실행한다.

| Platform | Method | Device | 실행 방식 |
| --- | --- | --- | --- |
| `web` | `web` | `desktop` | 고정 desktop browser context |
| `mobile_web` | `web` | `responsive` | 고정 responsive browser context |

Responsive mobile web은 native app이 아니다. Android package, APK, Appium capability, touch coordinate를 이 provider에 전달하면 안 된다. CI는 저장된 runbook만 재생한다. 실행 중 LLM 호출, locator 후보 선택, fallback selector 생성, action 보강, verdict 판정을 금지한다.

## 2. Project config (`web-playwright-config-v1`)

Project adapter는 아래 secret-free JSON을 소유한다. Core repository는 실제 회사명, 서비스 URL, 계정, selector를 소유하지 않는다.

```json
{
  "schema_version": "web-playwright-config-v1",
  "provider": "web-playwright",
  "provider_contract_version": "web-playwright-runner-v1",
  "implementation_version": "1.0.0",
  "defaults_version": "web-playwright-defaults-v1",
  "runbook_id": "record-state-r1",
  "browser": "chromium",
  "headless": true,
  "origin": "http://127.0.0.1:4173",
  "allowed_origins": ["http://127.0.0.1:4173"],
  "profiles": {
    "desktop": {
      "viewport": { "width": 1280, "height": 720 },
      "locale": "en-US",
      "color_scheme": "light",
      "reduced_motion": "reduce"
    },
    "responsive": {
      "viewport": { "width": 390, "height": 844 },
      "device_scale_factor": 1,
      "is_mobile": true,
      "has_touch": true,
      "locale": "en-US",
      "color_scheme": "light",
      "reduced_motion": "reduce"
    }
  },
  "routes": { "record": "/records/fixture" },
  "locators": {
    "record_state": { "by": "test_id", "value": "record-state" }
  },
  "fixture_values": {},
  "options": {},
  "timeouts_ms": { "goto": 20000, "action": 5000, "evidence": 5000 },
  "read_only_retry_policy": "never",
  "read_only_max_attempts": 1,
  "evidence_collectors": {
    "state-equals-ready": {
      "kind": "dom_state",
      "after_step_id": "wait-state",
      "locator_ref": "record_state",
      "fields": ["text", "visible"]
    }
  }
}
```

규칙:

- `origin`은 credential이 없는 HTTP(S) origin이어야 하며 `allowed_origins`에 포함돼야 한다.
- Route는 `/`로 시작하는 origin-relative path만 허용한다.
- Browser는 P2에서 `chromium`만 지원한다.
- Locator는 `role`, `label`, `test_id`, `text`, `placeholder`, `css` 중 하나다. 한 reference는 resolved locator 하나만 가져야 한다.
- `candidate`, `fallback`, runtime template, 환경변수 치환식을 compile 결과에 남기면 안 된다.
- `fixture_values`는 격리된 test fixture 값만 가리킨다. Credential, token, 운영 계정 데이터는 금지한다.
- Config 전체를 canonical JSON으로 직렬화한 SHA-256이 `project_config_sha256`이다.

Config key 순서는 hash에 영향을 주지 않는다. Route, locator, profile, timeout, collector가 바뀌면 config hash가 바뀌며 해당 값이 frozen plan에 반영되면 `integrity.plan_sha256`도 바뀐다.

## 3. Runbook compiler

`scripts/compile-web-runbook.mjs`는 승인되고 `execution.enabled=true`인 `scenario-v1`만 compile한다.

| Scenario action | Frozen Playwright action | 필수 semantic argument |
| --- | --- | --- |
| `navigate` | `goto` | `route_ref` |
| `activate`, `click` | `click` | `control_ref` |
| `fill` | `fill` | `control_ref`, `fixture_value_ref` |
| `press` | `press` | `control_ref`, `key` |
| `select_option` | `select_option` | `control_ref`, `option_ref` |
| `wait_for` | `wait_for` | `control_ref`, 선택형 `state` |

Compiler는 `provider_args`에 실제 URL, locator, value, context를 materialize한다. Scenario의 reference는 감사 추적용 `arguments`에 보존하지만 runner는 실행값으로 사용하지 않는다.

```bash
node scripts/compile-web-runbook.mjs \
  --scenario scenario.json \
  --config web-project-config.json \
  --output runbook.json
```

Mutation step이 있으면 첫 호출은 `E_APPROVAL_REQUIRED`와 frozen `plan_sha256`, `approved_step_ids`, environment를 반환한다. 외부 승인 시스템이 이 값을 결합한 immutable approval record를 만든 뒤 다시 compile한다.

```bash
node scripts/compile-web-runbook.mjs \
  --scenario scenario.json \
  --config web-project-config.json \
  --approval approval.json \
  --output runbook.json
```

`--preflight`는 승인 요청용 plan을 파일로 만들 수 있지만 executable runbook으로 사용하면 안 된다. 승인 기록은 exact plan hash, mutation step 목록, fixture environment와 일치해야 한다. Runner는 이 조건을 다시 검사한다.

## 4. Runner request와 replay

`scripts/run-web-playwright.mjs`는 `runner-request-v1`과 hash가 일치하는 `runbook-v1`을 받는다.

```bash
node scripts/run-web-playwright.mjs \
  --request runner-request.json \
  --runbook runbook.json \
  --output runner-output.json
```

실행 전 gate는 아래 값을 확인한다.

1. Request와 runbook의 ID, target, provider, project config hash, plan hash가 일치한다.
2. `runbook_sha256`이 canonical runbook JSON hash와 일치한다.
3. Web request의 `runtime_binding`과 `artifact`가 `null`이다.
4. Destructive fixture가 `isolated` environment를 사용한다.
5. Mutation approval의 plan hash, scope, environment, expiry가 유효하다.

Runner는 Playwright package를 일반 Node module resolution으로 먼저 찾는다. 격리된 host가 별도 versioned module store를 쓰면 `--playwright-module-root <node_modules>`를 명시할 수 있다. CI는 어느 방식을 쓰든 Playwright version과 browser binary를 lock해야 한다.

## 5. Evidence collector

`evidence_collectors`는 각 oracle rule마다 정확히 하나 필요하다. `kind`는 scenario oracle의 `evidence_kind`와 같아야 하고 `after_step_id`는 frozen step을 가리켜야 한다.

| Kind | 수집 내용 | Sanitization |
| --- | --- | --- |
| `dom_state` | 허용한 text, value, checked, enabled, visible, attribute | 명시한 locator와 field만 수집 |
| `accessibility_state` | role, ARIA state, disabled, checked | 전체 accessibility tree를 수집하지 않음 |
| `locator_result` | locator, match count, visible | fallback을 실행하지 않음 |
| `url_state` | origin, pathname, query key 목록 | query value와 URL credential 제거 |
| `network_error` | failed request와 HTTP error의 method, sanitized URL, status | request/response body와 header 제외 |
| `console_error` | error 위치와 message hash | console text 원문 제외 |
| `api_state` | status와 허용 JSON Pointer 값 | GET만 사용하고 raw body 제외 |
| `storage_state` | 허용 key의 존재 여부와 value SHA-256 | raw storage value 제외 |
| `test_command` | runner, browser, context, runbook, attempt | 실행 secret 제외 |
| `build_hash` | build ref와 SHA-256 | build bytes 제외 |

Screenshot과 video는 Pass 증거가 아니다. P2 runner는 이를 수집하지 않으며 `diagnostic_attachments`를 빈 배열로 반환한다.

## 6. Runner output

Runner는 `runner-output-v1`만 반환한다. Output에는 `verdict`, `oracle_results`, 성공 주장 문장을 넣으면 안 된다. 각 evidence record는 redaction 이후 canonical JSON hash를 포함한다.

Step 실패는 `execution.status=partial` 또는 `not_started`, sanitized error, 미실행 step을 남긴다. Evidence 수집 실패는 product failure로 바꾸지 않고 `missing_evidence`와 `category=evidence` error로 분리한다. Independent Judge가 이 output과 명세를 대조해 여섯 verdict 중 하나를 결정한다.

## 7. Conformance

Provider 변경은 아래 검증을 통과해야 한다.

- Config key 순서가 달라도 runbook과 hash가 같다.
- Route 또는 locator가 바뀌면 `project_config_sha256`과 `plan_sha256`이 바뀐다.
- Desktop과 responsive context가 각각 고정된다.
- Mutation은 exact plan-bound approval 없이 compile 또는 replay되지 않는다.
- Request/runbook hash mismatch는 browser를 시작하기 전에 거부한다.
- Runner output에 verdict가 없고 evidence hash가 재계산된다.
- Storage value, console text, query value, credential이 output에 남지 않는다.
- 실제 Chromium 통합 테스트에서 desktop web과 responsive mobile web을 모두 실행한다.
