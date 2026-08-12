# `result-v1` contract

`result-v1` records one scenario execution and its independent verdict. Scenario and runbook identifiers plus hashes bind the result to immutable inputs; this document does not embed those input snapshots. A suite aggregator combines multiple `result-v1` files without changing their scenario-level verdicts.

A result sink MUST retain immutable scenario and runbook snapshots, or retain a resolver that returns bytes matching `scenario_hash` and `runbook_hash`. Snapshot location, resolver transport, and retention period belong to the sink contract rather than `result-v1`.

Target readers are runner-provider, independent-judge, result-sink, and contract-validator implementers.

## Contents

1. Normative language and serialization
2. Top-level fields
3. Execution subject and runtime identity
4. Evidence registry
5. Oracle results
6. Verdict contract
7. Security and redaction
8. Validation rules
9. Complete pass example

## 1. Normative language and serialization

`MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, and `MAY` are normative requirements.

- The canonical exchange format is a UTF-8 JSON object.
- `schema_version` MUST equal `result-v1`.
- One document represents one scenario and one execution attempt.
- Times use RFC 3339 UTC strings.
- Hashes use lowercase hexadecimal in the form `sha256:<64 hex characters>`.
- JSON hashes use UTF-8 JSON with object keys sorted, compact separators, and array order preserved. A referenced file hash uses the file's raw bytes.
- The result MUST be append-only after the judge signs its verdict. A correction creates a new `run_id` and identifies the replaced result outside this core contract.

## 2. Top-level fields

All fields in this table are REQUIRED. Conditional fields use `null` or an empty array when the condition does not apply.

| Field | Type | Contract |
| --- | --- | --- |
| `schema_version` | string | Exact value `result-v1`. |
| `run_id` | string | Unique execution identifier. |
| `scenario_id` | string | Exact `scenario-v1.id`. |
| `spec_version` | string | Exact scenario and input-bundle version. |
| `scenario_hash` | string | SHA-256 of the canonical scenario JSON. |
| `runbook_id` | string | Exact immutable `runbook-v1.runbook_id`. |
| `runbook_hash` | string | SHA-256 of the frozen `runbook-v1`. |
| `target` | object | Exact scenario target: `platform`, `device`, and conditional `artifact_type`. |
| `runner_provider` | enum | Exact provider selected by the scenario and runbook. |
| `started_at` | string | Execution start time. For a preflight rejection, use the preflight start time. |
| `finished_at` | string | Verdict completion time, not earlier than `started_at`. |
| `verdict` | enum | `pass`, `fail`, `conflict`, `insufficient_evidence`, `blocked`, or `unsupported`. |
| `execution` | execution object | Operational status and retry information. |
| `subject` | subject object | Build, app artifact, and native runtime identity. |
| `judge` | judge object | Independent judge mode, implementation identity, input hashes, and attempt. |
| `evidence` | array of evidence objects | Structured machine or manual evidence registry. Evidence identifiers MUST be unique. |
| `oracle_results` | array of oracle-result objects | One entry for every scenario oracle rule that reached the judge. |
| `blockers` | array of blocker objects | Non-empty only when an environment, authentication, fixture, or runtime condition stopped execution. |
| `conflicts` | array of conflict objects | Incompatible source expectations. |
| `missing_evidence` | array of missing-evidence objects | Required evidence that was absent or unusable. |
| `unsupported_reason` | string or null | Required text for `unsupported`; otherwise `null`. |
| `diagnostic_attachments` | array | Required array that MAY be empty. Non-empty entries are image, screenshot, or video references excluded from verdict evidence. |

`runner_provider` uses the `scenario-v1` enum: `web-playwright`, `native-android`, `native-ios`, `developer-test`, or `manual`.

### 2.1 Execution object

```json
{
  "status": "completed",
  "attempt": 1,
  "retry_count": 0,
  "command_evidence_ref": "runner-command",
  "runner_version": "1.0.0"
}
```

| Field | Type | Required | Contract |
| --- | --- | --- | --- |
| `status` | enum | yes | `not_started`, `partial`, or `completed`. |
| `attempt` | integer | yes | Positive attempt number. |
| `retry_count` | integer | yes | Non-negative. It MUST be `0` when a mutation step ran. |
| `command_evidence_ref` | string or null | yes | Evidence identifier of kind `test_command` or `structured_log`. |
| `runner_version` | string | yes | Version of the deterministic runner implementation. |

`completed` means the runner completed the frozen steps and evidence-collection attempts. It does not mean the scenario passed; only the independent judge evaluates the oracle.

### 2.2 Judge object

```json
{
  "mode": "deterministic",
  "name": "independent-judge",
  "version": "1.0.0",
  "attempt": 1,
  "model": null,
  "source_hashes": [
    "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  ],
  "evidence_hashes": [
    "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
  ],
  "decided_at": "2026-08-01T02:00:04Z"
}
```

`mode`, `name`, `version`, `attempt`, `model`, `source_hashes`, `evidence_hashes`, and `decided_at` are required. `mode` is `deterministic`, `semantic`, or `manual`. `attempt` is a positive integer. Hash arrays MUST contain the exact source and evidence inputs used for the verdict.

`model` is `null` for deterministic and manual judgments. When `mode` is `semantic`, `model` is required and has this exact shape:

```json
{
  "provider": "configured-model-provider",
  "model_version": "configured-model-version",
  "prompt_version": "semantic-judge-v1",
  "rubric_hash": "sha256:5555555555555555555555555555555555555555555555555555555555555555"
}
```

All four values are non-empty strings, and `rubric_hash` follows the contract hash format. The judge metadata records identity and inputs; it does not make the judge output itself admissible evidence.

## 3. Execution subject and runtime identity

The `subject` object freezes what the runner tested:

```json
{
  "build": {
    "ref": "sample-build-42",
    "sha256": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
  },
  "artifact": null,
  "native_runtime": null
}
```

### 3.1 Build

`build` is either `null` or an object with required `ref` and `sha256`. A completed automatic result SHOULD record a build. If the build is part of a required oracle chain and its identity is unavailable, the verdict cannot be `pass`.

### 3.2 Native artifact

`artifact` is either `null` or an object with these fields:

| Field | Type | Required | Contract |
| --- | --- | --- | --- |
| `id` | string | yes | Opaque registered artifact identifier. |
| `type` | enum | yes | Current executable native value is `apk`. `app_zip` is metadata for disabled iOS contracts only. |
| `sha256` | string | yes | Hash recorded by the artifact registry. |
| `package_id` | string | conditional | Required for Android execution. |

Artifact bytes, Base64, signing keys, and credentials MUST NOT appear. An Android execution MUST use an APK registered by reference and hash. A physical device or AAB is invalid.

### 3.3 Native runtime

`native_runtime` is required for an Android result that started execution. It contains:

| Field | Type | Contract |
| --- | --- | --- |
| `device_type` | enum | Exact value `emulator`. |
| `device_id` | string | Emulator identifier recorded by the provider. |
| `avd` | string | Android Virtual Device name selected by the binding. |
| `device_name` | string | Device name sent to Appium. |
| `os_version` | string | Android OS version. |
| `orientation` | enum | `portrait` or `landscape`. |
| `language` | string | Android language fixed by the binding. |
| `locale` | string | Android locale fixed by the binding. |
| `reset_policy` | enum | `clean` or `preserve`. |
| `appium_version` | string or null | Appium server version observed at execution. `null` is allowed only for `partial` execution that failed before the provider reported a version. |
| `automation_driver` | string | Exact value `uiautomator2`. |
| `automation_driver_version` | string or null | UiAutomator2 driver version observed at execution. `null` is allowed only for `partial` execution that failed before the provider reported a version. |

Completed Android execution requires non-empty `appium_version` and `automation_driver_version`. A partial result keeps these fields as `null` when session creation failed before the provider could observe them; it must not substitute an assumed version.

When an external provider omits these versions, a deterministic collector MAY derive them from the dedicated Appium debug log only if it verifies all of the following: exactly one successful `POST /session` response, that response timestamp falls inside the runner execution window, the expected package identifier appears in the log, and exactly one Appium and UiAutomator2 version can be parsed. The result stores the log SHA-256 and structured observations; it MUST NOT embed the raw log.

`reset_policy: preserve` records the observed setup but does not prove deterministic login state. If the oracle depends on an unverified preserved session, the result is `insufficient_evidence` or `blocked`, depending on whether execution began.

## 4. Evidence registry

Each evidence object has this minimum shape:

```json
{
  "id": "api-record-state",
  "kind": "api_state",
  "collected_at": "2026-08-01T02:00:03Z",
  "producer": {
    "type": "api_probe",
    "name": "project-api-state-probe",
    "version": "1"
  },
  "sha256": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
  "redactions": [],
  "record": {
    "status": 200,
    "body": {
      "state": "complete"
    }
  }
}
```

Required fields are `id`, `kind`, `collected_at`, `producer`, `sha256`, and `redactions`. `redactions` is an array of JSON Pointers removed before hashing and MAY be empty. Exactly one of `record` or `artifact_ref` MUST appear.

For `record`, `sha256` is calculated from the redacted record serialized as UTF-8 JSON with sorted object keys, compact separators, and preserved array order. For `artifact_ref`, it is the SHA-256 of the referenced file's raw bytes.

`artifact_ref` points to a result-relative, integrity-checked text or JSON file. It MUST NOT be absolute, contain `..`, or encode file bytes inline.

### 4.1 Evidence kinds

The closed evidence-kind enum is:

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

The `producer` object has required `type` and `name`; `version` is optional. `type` is `runner`, `developer_test`, `api_probe`, `db_probe`, `build_system`, `adapter`, or `human`.

An execution agent's narrative, assertion summary, or self-reported success is not evidence. A runner may emit machine-structured logs, but the independent judge evaluates those records rather than accepting the runner's verdict.

### 4.2 Diagnostic attachments

The top-level `diagnostic_attachments` field MUST always exist and MAY be an empty array. Image, screenshot, and video files MAY appear only in this array with `kind`, result-relative `artifact_ref`, and `sha256`. Oracle results MUST NOT reference these attachment identifiers. Their presence cannot turn a verdict into `pass` or repair missing structured evidence.

## 5. Oracle results

Each oracle result has these required fields:

| Field | Type | Contract |
| --- | --- | --- |
| `oracle_id` | string | Exact `scenario-v1.oracle.rules[].id`. |
| `expectation_id` | string | Exact expectation referenced by that oracle. |
| `status` | enum | `matched`, `mismatched`, or `not_evaluated`. |
| `evidence_refs` | array of strings | Evidence identifiers used for this decision. |
| `source_refs` | array of source-reference objects | Specification anchors used by a semantic decision; see the conditional rules below. |
| `actual` | any JSON value or null | Sanitized observed value. |
| `reason` | string or null | Required for `mismatched` and `not_evaluated`; optional for `matched`. |

`matched` and `mismatched` MUST cite at least one evidence identifier. Every identifier MUST resolve in the top-level evidence registry. `not_evaluated` MAY have no evidence when the required evidence is missing.

`source_refs` is required on every oracle result. Deterministic and manual results MAY use an empty array. A semantic `matched` or `mismatched` result MUST contain at least one `{source_id, anchor_id}` object. Every semantic source reference MUST appear in the referenced expectation's `source_refs`. A semantic `not_evaluated` result includes every source reference the judge successfully resolved; it MAY be empty only when no required source resolved.

Deterministic rules run first. A semantic rule is sent to an independent judge only when deterministic comparison cannot decide the documented semantic question. The judge receives only source references, expectation text, the bounded rubric, and cited evidence.

### 5.1 Complete semantic judge fragment

This fragment is not a standalone `result-v1`; it shows the complete `judge` and `oracle_results` fields for one semantic match:

```json
{
  "judge": {
    "mode": "semantic",
    "name": "independent-judge",
    "version": "1.0.0",
    "attempt": 1,
    "model": {
      "provider": "configured-model-provider",
      "model_version": "configured-model-version",
      "prompt_version": "semantic-judge-v1",
      "rubric_hash": "sha256:5555555555555555555555555555555555555555555555555555555555555555"
    },
    "source_hashes": [
      "sha256:bab4f79e0a0995c5918a945329728edca69d9b2008fce60bf935911de757295f"
    ],
    "evidence_hashes": [
      "sha256:3333333333333333333333333333333333333333333333333333333333333333"
    ],
    "decided_at": "2026-08-01T02:00:04Z"
  },
  "oracle_results": [
    {
      "oracle_id": "visible-state-semantic-check",
      "expectation_id": "visible-state-is-complete",
      "status": "matched",
      "evidence_refs": ["visible-record-state"],
      "source_refs": [
        {
          "source_id": "product-requirements",
          "anchor_id": "saved-record-becomes-complete"
        }
      ],
      "actual": "finished",
      "reason": "The observed state has the same meaning as the required complete state under the frozen rubric."
    }
  ]
}
```

## 6. Verdict contract

The verdict enum is closed. No aliases such as `success`, `error`, `skipped`, or `unknown` are valid.

| Verdict | Required condition | Required supporting field |
| --- | --- | --- |
| `pass` | Execution completed, every oracle matched, and every required evidence item is present and trusted. | `blockers`, `conflicts`, and `missing_evidence` are empty. |
| `fail` | At least one evaluated oracle mismatched the specification. | At least one `oracle_results[].status` is `mismatched` with evidence. |
| `conflict` | Two or more cited specification anchors require incompatible outcomes. | `conflicts` is non-empty and cites the conflicting source references. |
| `insufficient_evidence` | Execution began, but the judge cannot evaluate a required oracle from admissible evidence. | `missing_evidence` is non-empty and at least one oracle is `not_evaluated`. |
| `blocked` | Environment, authentication, fixture, artifact registration, or runtime failure prevented completion. | `blockers` is non-empty. |
| `unsupported` | The requested provider capability does not exist. Current iOS execution is the canonical case. | `execution.status` is `not_started` and `unsupported_reason` is non-empty. |

Verdict-specific objects have these shapes:

- blocker: `{"code": string, "description": string, "evidence_refs": [string]}`;
- conflict: `{"id": string, "description": string, "source_refs": [source-reference object, ...]}` with at least two references;
- missing evidence: `{"oracle_id": string, "evidence_kind": string, "reason": string}`.

A screen label that matches the expected text while the required API or DB state disagrees produces `fail`. A screen label with no required backend evidence produces `insufficient_evidence`, not `pass`.

Android evidence cannot establish an iOS verdict. A request to execute a valid iOS contract remains `unsupported` until an XCUITest provider exists.

## 7. Security and redaction

The runner MUST redact secrets before it writes evidence. The result validator recursively scans all fields, including logs, UI hierarchy, `actual`, diagnostic metadata, and extension data.

The validator MUST reject a result that contains:

- a credential, password, token, API key, private key, authorization header, or session cookie;
- a filled sensitive value recovered from DOM, accessibility state, UI hierarchy, or Android logcat;
- APK bytes, AAB data, Base64 artifacts, or `data:*;base64,` URIs;
- an absolute or parent-traversing evidence path;
- an Android physical-device result or AAB artifact result.

Redaction markers MAY identify removed JSON Pointer paths, but they MUST NOT preserve the original value. A hash of credential material is also prohibited because it can become a reusable secret verifier.

## 8. Validation rules

A conforming `result-v1` validation invocation MUST supply the exact `spec-bundle-v1`, `scenario-v1`, and `runbook-v1` snapshots. The validator recomputes the scenario and runbook hashes, checks their identities and target bindings, and resolves each oracle result against the frozen rule and expectation. A result without these contexts is not eligible for the contract gate.

When `validate-contracts.py` runs with `--output json`, it emits `contract-validation-report-v1`. The receipt includes the SHA-256 of the exact validator source, canonical hashes and input references for bundle·scenario·runbook contexts, and the canonical hash of every decoded report input. A downstream release or Done gate MUST pin the approved validator SHA-256, resolve every context snapshot, compare its canonical hash, and compare the receipt's result input and hash with the immutable `result-v1` snapshot. A plain `valid=true` object without this identity and context binding is not a contract-validation receipt.

The receipt hashes JSON documents with the canonical JSON rule in section 1. The validator source hash uses the raw bytes of `scripts/validate-contracts.py`. Changing the validator therefore requires an explicit downstream allowlist update.

The P4 `scripts/judge-results.mjs` command consumes those snapshots plus `runner-output-v1` and produces `result-v1`. Deterministic evidence selection requires exactly one admissible evidence record for the rule after applying the frozen runbook evidence plan. Ambiguous or missing records produce `not_evaluated`; the command does not select a record by arrival order. Semantic results require a separately produced `semantic-judge-response-batch-v1` bound to the frozen request and batch hashes described in [`judge-protocol.md`](judge-protocol.md).

A conforming validator MUST reject a result when any of these conditions applies:

- a required field is missing or has the wrong type;
- the schema, scenario, specification, target, provider, scenario hash, or runbook hash does not match the frozen inputs;
- a timestamp is invalid or `finished_at` precedes `started_at`;
- a verdict is outside the six-value enum;
- judge metadata omits its input hashes, or a semantic judgment omits model, prompt, or rubric identity;
- evidence identifiers are duplicated or an oracle refers to unknown evidence;
- an oracle result duplicates or invents a rule identifier, names the wrong expectation, cites the wrong evidence kind, or diverges from the frozen semantic source references;
- an oracle result omits `source_refs`, or a semantic result violates the source-reference conditions in section 5;
- evidence lacks a valid hash or has neither or both of `record` and `artifact_ref`;
- an attachment is cited as verdict evidence;
- `pass` lacks oracle results, contains a non-matched oracle, or lacks required structured evidence;
- the verdict-specific conditions in section 6 are not satisfied;
- a mutation execution reports a retry;
- Android execution omits APK hash, package identifier, Emulator and AVD identity, OS, orientation, language, locale, reset policy, Appium version, or UiAutomator2 version;
- iOS reports an executed `pass` or `fail` result;
- any nested field violates section 7.

## 9. Complete pass example

The example corresponds to the web scenario in [`scenario-schema.md`](scenario-schema.md) and the frozen runbook in [`runner-provider-contract.md`](runner-provider-contract.md). The DOM and API records independently satisfy the two oracles. The build hash and command evidence preserve execution identity.

```json
{
  "schema_version": "result-v1",
  "run_id": "run-web-save-completed-state-001",
  "scenario_id": "web-save-completed-state",
  "spec_version": "2026-08-01.1",
  "scenario_hash": "sha256:2f0f15e47e4f7786eaf52d6fad3dd1397de3746ca076366032569002c1b9abbf",
  "runbook_id": "web-save-completed-state-r1",
  "runbook_hash": "sha256:1c4bfe5a9e6ea2a092b753d56e616ba8a98c7a0111f328c96e2b5ebfd4729f58",
  "target": {
    "platform": "web",
    "device": "desktop"
  },
  "runner_provider": "web-playwright",
  "started_at": "2026-08-01T02:00:00Z",
  "finished_at": "2026-08-01T02:00:04Z",
  "verdict": "pass",
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
      "sha256": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    },
    "artifact": null,
    "native_runtime": null
  },
  "judge": {
    "mode": "deterministic",
    "name": "independent-judge",
    "version": "1.0.0",
    "attempt": 1,
    "model": null,
    "source_hashes": [
      "sha256:bab4f79e0a0995c5918a945329728edca69d9b2008fce60bf935911de757295f",
      "sha256:000482f09ca24c80cc88d197ccfe9eb711ecd682d514b54b5004e4a9f3e4e700"
    ],
    "evidence_hashes": [
      "sha256:f46ec65da10725c3a8deebe7545d2f0fae9f0fcc76a3ca0e98b6a8850791ea0d",
      "sha256:3523f3d00c490618520279d62c603ccfb5c6d675aca55a8a0c17a533b0423c5d"
    ],
    "decided_at": "2026-08-01T02:00:04Z"
  },
  "evidence": [
    {
      "id": "runner-command",
      "kind": "test_command",
      "collected_at": "2026-08-01T02:00:00Z",
      "producer": {
        "type": "runner",
        "name": "web-playwright",
        "version": "1.0.0"
      },
      "sha256": "sha256:34feb3cbc1a453620e03d9852b92fc49bc29b3ed3a6ac87d6da04d931e2fdc5c",
      "redactions": [],
      "record": {
        "runbook_ref": "qa/runbooks/web-save-completed-state-r1.json"
      }
    },
    {
      "id": "tested-build",
      "kind": "build_hash",
      "collected_at": "2026-08-01T02:00:00Z",
      "producer": {
        "type": "build_system",
        "name": "sample-build-registry",
        "version": "1"
      },
      "sha256": "sha256:bca9dd646e5df33c7fb8ef3fee2f42ca83ff405f00de79e7ba402e59d79f789d",
      "redactions": [],
      "record": {
        "build_ref": "sample-build-42",
        "build_sha256": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
      }
    },
    {
      "id": "visible-record-state",
      "kind": "dom_state",
      "collected_at": "2026-08-01T02:00:03Z",
      "producer": {
        "type": "runner",
        "name": "web-playwright",
        "version": "1.0.0"
      },
      "sha256": "sha256:f46ec65da10725c3a8deebe7545d2f0fae9f0fcc76a3ca0e98b6a8850791ea0d",
      "redactions": [],
      "record": {
        "state_text": "complete"
      }
    },
    {
      "id": "api-record-state",
      "kind": "api_state",
      "collected_at": "2026-08-01T02:00:03Z",
      "producer": {
        "type": "api_probe",
        "name": "project-api-state-probe",
        "version": "1"
      },
      "sha256": "sha256:3523f3d00c490618520279d62c603ccfb5c6d675aca55a8a0c17a533b0423c5d",
      "redactions": [],
      "record": {
        "status": 200,
        "body": {
          "state": "complete"
        }
      }
    }
  ],
  "oracle_results": [
    {
      "oracle_id": "visible-state-check",
      "expectation_id": "visible-state-is-complete",
      "status": "matched",
      "evidence_refs": ["visible-record-state"],
      "source_refs": [],
      "actual": "complete",
      "reason": null
    },
    {
      "oracle_id": "persisted-state-check",
      "expectation_id": "persisted-state-is-complete",
      "status": "matched",
      "evidence_refs": ["api-record-state"],
      "source_refs": [],
      "actual": "complete",
      "reason": null
    }
  ],
  "blockers": [],
  "conflicts": [],
  "missing_evidence": [],
  "unsupported_reason": null,
  "diagnostic_attachments": []
}
```
