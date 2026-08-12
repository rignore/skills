# `scenario-v1` contract

`scenario-v1` is a reviewed, source-traceable QA scenario. It describes what to verify without embedding a live URL, account, credential, binary artifact, or provider-specific selector. A compiler converts an approved scenario into a frozen `runbook-v1`; CI replays that runbook without asking an LLM to generate steps.

Target readers are scenario-planner, runbook-compiler, runner-provider, and contract-validator implementers.

## Contents

1. Normative language and serialization
2. Top-level fields
3. Nested object contracts
4. Platform and provider matrix
5. Mutation and fixture safety
6. Oracle and evidence rules
7. Prohibited input
8. Validation rules
9. Complete web example
10. iOS contract example

## 1. Normative language and serialization

`MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, and `MAY` are normative requirements.

- The canonical exchange format is a UTF-8 JSON object.
- `schema_version` MUST equal `scenario-v1`.
- Hashes use lowercase hexadecimal in the form `sha256:<64 hex characters>`.
- Identifiers MUST match `^[a-z0-9][a-z0-9._-]{0,127}$` and be unique in their containing array.
- Unknown provider data belongs in the compiled runbook, not in this platform-neutral scenario.

## 2. Top-level fields

All fields in this table are REQUIRED.

| Field | Type | Contract |
| --- | --- | --- |
| `schema_version` | string | Exact value `scenario-v1`. |
| `id` | string | Stable scenario identifier. |
| `title` | string | Human-readable scenario meaning. It MUST NOT be empty. |
| `source_refs` | array of source-reference objects | Non-empty. Every reference MUST resolve in the selected `spec-bundle-v1`. |
| `method` | enum | `web`, `native`, `unit`, `integration`, or `manual`. |
| `preconditions` | array of precondition objects | Conditions checked before the first step. It MAY be empty. |
| `fixture` | fixture object | Fixed test state and its isolation classification. |
| `steps` | array of step objects | Ordered and non-empty. Step identifiers MUST be unique. |
| `expected` | array of expectation objects | Required outcomes. See automated-execution rules in section 6. |
| `oracle` | oracle object | Rules that compare evidence with `expected`. |
| `severity` | enum | `blocker`, `critical`, `high`, `medium`, or `low`. |
| `spec_version` | string | Exact `spec-bundle-v1.spec_version` used to create the scenario. |
| `review_status` | enum | `draft`, `approved`, or `rejected`. |
| `target` | target object | Platform, device class, and native artifact type. |
| `runner_provider` | enum | `web-playwright`, `native-android`, `native-ios`, `developer-test`, or `manual`. |
| `mutation_policy` | mutation-policy object | Policy for actions that may change state. It is required even for read-only scenarios. |
| `execution` | execution object | Whether the current implementation may compile and run this scenario. |

`execution.enabled: true` means the scenario is eligible for runbook compilation. It does not prove that a required mutation approval exists. The runbook must carry the immutable approval record before a mutation run starts.

`severity` controls reporting and release-gate priority. It does not change oracle behavior or any verdict meaning.

## 3. Nested object contracts

### 3.1 Source reference

```json
{
  "source_id": "product-requirements",
  "anchor_id": "saved-record-becomes-complete"
}
```

Both fields are required strings. They resolve exactly as defined in [`input-contract.md`](input-contract.md). An expectation's references MUST be a subset of the scenario's top-level `source_refs`.

### 3.2 Preconditions

Each precondition has these fields:

| Field | Type | Required | Contract |
| --- | --- | --- | --- |
| `id` | string | yes | Unique precondition identifier. |
| `description` | string | yes | Observable condition that must hold. |
| `verification` | enum | yes | `runner` or `manual`. |
| `check_ref` | string | conditional | Required when `verification` is `runner`. It points to a check defined in project configuration or the runbook. |

`check_ref` is an opaque identifier. It MUST NOT contain a credential or executable script body.

### 3.3 Fixture

```json
{
  "kind": "seed",
  "ref": "record-ready-to-save-v1",
  "purpose": "baseline",
  "destructive": false,
  "environment": "isolated"
}
```

| Field | Type | Required | Contract |
| --- | --- | --- | --- |
| `kind` | enum | yes | `none`, `seed`, `mock`, `test_endpoint`, `snapshot`, or `manual`. |
| `ref` | string | conditional | Required unless `kind` is `none`. It is an opaque fixture identifier, not fixture data. |
| `purpose` | enum | yes | `baseline`, `error`, or `boundary`. |
| `destructive` | boolean | yes | Whether setup or teardown deletes, overwrites, or irreversibly changes state. |
| `environment` | enum | yes | `isolated`, `shared_test`, or `production`. |

An error or boundary fixture MUST use `isolated`. A destructive fixture MUST use `isolated`, regardless of purpose. Production data MUST NOT be altered to create a fixture.

### 3.4 Steps

Each step has these fields:

| Field | Type | Required | Contract |
| --- | --- | --- | --- |
| `id` | string | yes | Unique step identifier. |
| `action` | string | yes | Semantic action name, such as `navigate`, `activate`, `launch`, or `wait_for`. |
| `description` | string | yes | Human-readable action and intended target. |
| `mutation` | enum | yes | `none`, `potential`, or `confirmed`. |
| `arguments` | object | no | Secret-free semantic references. Provider locators and raw runtime values do not belong here. |

Examples of valid arguments are `route_ref`, `control_ref`, and `fixture_value_ref`. An XPath, screen coordinate, live product URL, password, or session token is not valid scenario input.

### 3.5 Expectations

Each expectation has this exact minimum shape:

```json
{
  "id": "persisted-state-is-complete",
  "description": "The persisted record state equals complete.",
  "source_refs": [
    {
      "source_id": "workflow-policy",
      "anchor_id": "complete-state-requires-persisted-value"
    }
  ]
}
```

`id`, `description`, and the non-empty `source_refs` array are required. A description states an observable outcome, not an implementation plan.

### 3.6 Oracle

The oracle object has two required fields:

| Field | Type | Contract |
| --- | --- | --- |
| `mode` | enum | `deterministic`, `semantic`, or `manual`. |
| `rules` | array | Ordered oracle rules. See the variants below. |

Every rule has `id`, `kind`, `expectation_id`, and `evidence_kind`. `expectation_id` MUST resolve to one `expected[].id`. `kind` MUST equal the containing oracle's `mode`.

A deterministic rule adds these fields:

- `operator`: `equals`, `not_equals`, `contains`, `exists`, `absent`, `matches_regex`, or `status_code`;
- `actual_path`: an RFC 6901 JSON Pointer into the evidence record;
- `value`: the expected JSON value, except when the operator is `exists` or `absent`.

A semantic rule adds `rubric`, a bounded question that an independent judge can answer from the cited source, expectation, and collected evidence. A manual rule adds `checklist`, a non-empty array of observable checks.

### 3.7 Mutation policy

```json
{
  "mode": "require_approval",
  "approval_scope": ["submit-record"],
  "retry_policy": "never"
}
```

| Field | Type | Contract |
| --- | --- | --- |
| `mode` | enum | `deny` or `require_approval`. |
| `approval_scope` | array of step identifiers | Exact mutation steps covered by the policy. |
| `retry_policy` | enum | Exact value `never` in `scenario-v1`. Polling inside a read-only wait is not a step retry. |

If every step has `mutation: none`, `mode` MUST be `deny` and `approval_scope` MUST be empty. If any step has `potential` or `confirmed`, `mode` MUST be `require_approval` and `approval_scope` MUST contain every such step identifier.

### 3.8 Target and execution

The target object contains `platform` and `device`. Native targets also contain `artifact_type`.

| Platform | Required target fields |
| --- | --- |
| `web` | `{"platform":"web","device":"desktop"}` |
| `mobile_web` | `{"platform":"mobile_web","device":"responsive"}` |
| `android` | `{"platform":"android","device":"emulator","artifact_type":"apk"}` |
| `ios` | `{"platform":"ios","device":"simulator","artifact_type":"app_zip"}` |

The execution object has a required boolean `enabled`. When `enabled` is `false`, it MAY also contain a non-secret `disabled_reason`.

Only `approved` scenarios MAY set `execution.enabled` to `true`. An iOS scenario MUST set it to `false` until a native iOS runner exists.

## 4. Platform and provider matrix

The validator applies this matrix before runbook compilation.

| Method | Allowed platform | Required provider | Additional rule |
| --- | --- | --- | --- |
| `web` | `web` | `web-playwright` | Device is `desktop`. |
| `web` | `mobile_web` | `web-playwright` | Device is `responsive`; Playwright uses a device context. |
| `native` | `android` | `native-android` | Emulator and APK only. |
| `native` | `ios` | `native-ios` | Contract only; `execution.enabled` is `false`. |
| `unit` | any defined platform | `developer-test` | A developer test command evaluates the target. |
| `integration` | any defined platform | `developer-test` | A developer test command evaluates the target. |
| `manual` | any defined platform | `manual` | A person supplies structured results. |

The following classifications are invalid:

- `mobile_web` with `method: native` or a native provider;
- `web` with `device: responsive`;
- Android with `device: physical`, an AAB artifact, or a provider other than `native-android` for native execution;
- iOS with `execution.enabled: true`;
- any platform, method, and provider tuple absent from the matrix.

An unsupported tuple is a contract error at scenario authoring time. A valid contract whose provider is intentionally unavailable, such as iOS, produces `unsupported` only when execution is requested downstream.

## 5. Mutation and fixture safety

`launch`, `tap`, `fill`, `press_key`, and `back` are potential mutations for Android native scenarios. A planner MUST label each of these actions `potential` or `confirmed`; it MUST NOT label them `none`.

A conforming runner applies four safeguards:

1. It resolves fixture, environment, and approval state before the first mutation.
2. It refuses a mutation not listed in `approval_scope`.
3. It never retries a mutation action automatically.
4. It creates error and boundary states with an isolated fixture, mock, seed script, or test endpoint rather than modifying production data.

`require_approval` states the approval policy. The compiled runbook records the approval reference, approved step identifiers, scenario hash, artifact hash where applicable, and expiry before it becomes executable.

## 6. Oracle and evidence rules

For `web`, `native`, `unit`, and `integration` scenarios with `execution.enabled: true`:

- `expected` MUST contain at least one expectation;
- `oracle.rules` MUST contain at least one rule;
- every expectation MUST have a matching rule;
- every deterministic rule MUST identify a structured evidence kind;
- semantic rules are allowed only when a deterministic rule cannot decide semantic equivalence.

An approved manual scenario MUST contain at least one expectation and one manual checklist rule. A draft, disabled manual scenario MAY leave these arrays empty while it is being authored.

The scenario planner MAY use an LLM to draft steps and semantic rubrics. CI MUST execute only the saved runbook. The execution agent's narrative or self-reported success is never an oracle input.

## 7. Prohibited input

The validator recursively scans the full scenario. It MUST reject these values even when they appear under `arguments` or another extension object:

- credentials, passwords, tokens, API keys, private keys, authorization headers, or session cookies;
- APK bytes, AAB data, application archive bytes, or Base64 artifact payloads;
- `data:*;base64,` URIs and long opaque Base64 payloads in artifact fields;
- physical Android device requests;
- executable iOS requests;
- live project selectors or coordinate-based taps in the platform-neutral scenario.

An opaque reference to project configuration or an artifact type such as `apk` is allowed. Actual artifact paths, hashes, runtime locators, and secure authentication handles belong in project configuration or the compiled runbook.

## 8. Validation rules

A conforming validator MUST reject a scenario when any of these conditions applies:

- a required field is missing or has the wrong type;
- `source_refs` is empty or contains a malformed reference;
- `spec_version` differs from the selected input bundle;
- the platform, device, artifact type, method, or provider combination violates section 4;
- Android requests a physical device or AAB;
- iOS sets `execution.enabled` to `true`;
- `execution.enabled` is `true` while `review_status` is not `approved`;
- a mutation step lacks the approval policy and scope required by section 3.7;
- a destructive, error, or boundary fixture is not isolated;
- responsive mobile web is classified as native;
- an enabled automated scenario lacks `expected` or `oracle.rules`;
- an oracle refers to an unknown expectation or evidence kind;
- any nested value violates section 7.

## 9. Complete web example

This scenario checks both the visible state and the persisted API state after a save. The mutation policy covers the one state-changing step.

```json
{
  "schema_version": "scenario-v1",
  "id": "web-save-completed-state",
  "title": "Saving a record persists and displays the complete state",
  "source_refs": [
    {
      "source_id": "product-requirements",
      "anchor_id": "saved-record-becomes-complete"
    },
    {
      "source_id": "workflow-policy",
      "anchor_id": "complete-state-requires-persisted-value"
    }
  ],
  "method": "web",
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
      "action": "navigate",
      "description": "Open the seeded record editor.",
      "mutation": "none",
      "arguments": {
        "route_ref": "record-editor"
      }
    },
    {
      "id": "submit-record",
      "action": "activate",
      "description": "Activate the save control.",
      "mutation": "confirmed",
      "arguments": {
        "control_ref": "save-control"
      }
    }
  ],
  "expected": [
    {
      "id": "visible-state-is-complete",
      "description": "The visible record state equals complete.",
      "source_refs": [
        {
          "source_id": "product-requirements",
          "anchor_id": "saved-record-becomes-complete"
        }
      ]
    },
    {
      "id": "persisted-state-is-complete",
      "description": "The persisted record state equals complete.",
      "source_refs": [
        {
          "source_id": "workflow-policy",
          "anchor_id": "complete-state-requires-persisted-value"
        }
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
  "severity": "high",
  "spec_version": "2026-08-01.1",
  "review_status": "approved",
  "target": {
    "platform": "web",
    "device": "desktop"
  },
  "runner_provider": "web-playwright",
  "mutation_policy": {
    "mode": "require_approval",
    "approval_scope": ["submit-record"],
    "retry_policy": "never"
  },
  "execution": {
    "enabled": true
  }
}
```

## 10. iOS contract example

An iOS scenario can preserve source traceability before a runner exists, but it cannot be enabled. This complete example is a valid `scenario-v1` contract and is intentionally non-executable:

```json
{
  "schema_version": "scenario-v1",
  "id": "ios-save-completed-state-contract",
  "title": "Saving a record displays the complete state on iOS",
  "source_refs": [
    {
      "source_id": "product-requirements",
      "anchor_id": "saved-record-becomes-complete"
    }
  ],
  "method": "native",
  "preconditions": [],
  "fixture": {
    "kind": "none",
    "purpose": "baseline",
    "destructive": false,
    "environment": "isolated"
  },
  "steps": [
    {
      "id": "launch-app",
      "action": "launch",
      "description": "Launch the registered iOS application artifact.",
      "mutation": "potential"
    },
    {
      "id": "wait-for-complete-state",
      "action": "wait_for",
      "description": "Wait for the complete-state accessibility control.",
      "mutation": "none",
      "arguments": {
        "control_ref": "complete-state-control"
      }
    }
  ],
  "expected": [
    {
      "id": "visible-state-is-complete",
      "description": "The visible record state equals complete.",
      "source_refs": [
        {
          "source_id": "product-requirements",
          "anchor_id": "saved-record-becomes-complete"
        }
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
        "evidence_kind": "accessibility_state",
        "operator": "equals",
        "actual_path": "/state_text",
        "value": "complete"
      }
    ]
  },
  "severity": "high",
  "spec_version": "2026-08-01.1",
  "review_status": "approved",
  "target": {
    "platform": "ios",
    "device": "simulator",
    "artifact_type": "app_zip"
  },
  "runner_provider": "native-ios",
  "mutation_policy": {
    "mode": "require_approval",
    "approval_scope": ["launch-app"],
    "retry_policy": "never"
  },
  "execution": {
    "enabled": false,
    "disabled_reason": "native-ios provider is not implemented"
  }
}
```

If downstream execution is requested for this contract, the result verdict is `unsupported`; it is not `blocked` and Android evidence cannot substitute for it.
