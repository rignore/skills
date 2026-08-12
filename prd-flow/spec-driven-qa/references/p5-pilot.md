# P5 company-independent pilots

P5 verifies the generic pipeline against two public targets without a company source adapter, result sink, database, account, product selector, or plugin.

Target readers are QA infrastructure engineers and skill maintainers who need to reproduce the generic pipeline before connecting a project-specific adapter.

## Public web pilot

The checked-in `examples/p5/web/spec.md` is the authoritative local source. `compile-markdown-spec.mjs` converts its constrained Markdown fields and anchors into a content-hashed `spec-bundle-v1`. The pilot then compiles a read-only runbook and runs Chromium against the configured [Playwright TodoMVC sample](https://demo.playwright.dev/todomvc/). It records a SHA-256 of the fetched entry document as the tested build reference before invoking the independent deterministic judge.

Run it with a version-pinned Playwright module root:

```bash
node scripts/run-p5-pilot.mjs \
  --pilot web \
  --playwright-module-root /absolute/path/to/node_modules \
  --output-dir /absolute/path/to/p5-web-output
```

The command succeeds only when it emits `result-v1` with `verdict: pass`. Network access and the remote sample's availability remain external dependencies.

## Public Android pilot

Use Appium `android-apidemos` v6.0.10 `ApiDemos-debug.apk` by local absolute path. The [v6.0.10 release](https://github.com/appium/android-apidemos/releases/tag/v6.0.10) publishes digest `sha256:896aa7053742cd8e4e19911038af59afff69d04f4a971adf8e946743ed0e2c8b`. Do not check the APK into the skill and do not encode its bytes in a binding. Verify the local file against that digest before preparing the binding.

Generate `native-mcp-binding-v1` by discovering and hashing the external MCP tool surface, Native Scenario schema, MCP launcher, dedicated runtime source directory, and APK. The runtime root must contain executable source only; do not point it at a repository root, virtual environment, data directory, or generated artifacts:

```bash
PYTHONDONTWRITEBYTECODE=1 node scripts/prepare-native-mcp-binding.mjs \
  --mcp-executable /absolute/path/to/demo-video-mcp \
  --mcp-runtime-root /absolute/path/to/demo-video-mcp-source-package \
  --working-directory /absolute/path/to/demo-video-mcp-project \
  --apk /absolute/path/to/ApiDemos-debug.apk \
  --expected-apk-sha256 sha256:896aa7053742cd8e4e19911038af59afff69d04f4a971adf8e946743ed0e2c8b \
  --java-home /absolute/path/to/jdk \
  --apksigner /absolute/path/to/android-sdk/build-tools/35.0.0/apksigner \
  --package-id io.appium.android.apis \
  --binding-id p5-api-demos-emulator \
  --avd Pixel_7_API_35 \
  --output /absolute/path/to/native-binding.json
```

Run preflight before any app launch:

The Appium process must inherit the same absolute `JAVA_HOME` used in the binding, put its `bin` directory first in `PATH`, and inherit equal absolute `ANDROID_HOME` and `ANDROID_SDK_ROOT` values. The core preflight runs `java -version` and `apksigner verify --print-certs` before starting the MCP process. The external provider separately checks `adb`, the Emulator, Appium, UiAutomator2, and FFmpeg.

```bash
node scripts/run-p5-pilot.mjs \
  --pilot android-preflight \
  --binding /absolute/path/to/native-binding.json \
  --output-dir /absolute/path/to/p5-android-preflight
```

The preflight requires `runbook_state=preflight`, registers and hashes the APK, verifies JDK readiness and the APK signature, verifies the local Appium UiAutomator2 runtime and Emulator, verifies the bound external MCP runtime source tree, creates the external job, and returns `provider_plan_hash` and `runtime_binding_sha256`. It does not call `approve_video_job` or `start_video_job`.

Bindings created before the mandatory readiness fields are historical artifacts only. Regenerate the binding and external approval before any new Android run; do not reuse the earlier runtime binding hash or approval record.

Preflight and the approved run must use the same external MCP data root. The provider plan binds the registered APK `artifact_id`; registering the same APK in a fresh data root creates a different identity and therefore a different provider plan hash. The adapter rejects that mismatch before `approve_video_job`.

An external approver must create an immutable approval record after reviewing all of these exact values:

- `runbook.integrity.plan_sha256`
- `preflight.provider_plan_hash`
- `preflight.runtime_binding_sha256`
- `preflight.approved_step_ids`
- `preflight.environment`

The record must include a non-secret `approved_by_ref`; the execution agent must not impersonate the approver. After approval, execute the same frozen inputs:

```json
{
  "id": "approval-p5-android-001",
  "record_sha256": "sha256:<external-approval-record-digest>",
  "plan_sha256": "<runbook.integrity.plan_sha256>",
  "provider_plan_hash": "<preflight.provider_plan_hash>",
  "runtime_binding_sha256": "<preflight.runtime_binding_sha256>",
  "approved_step_ids": ["launch-app"],
  "environment": "isolated",
  "scope": "single_run",
  "expires_at": null,
  "approved_by_ref": "<non-secret-external-approver-reference>"
}
```

Replace every angle-bracket placeholder with the reviewed value. See [native-mcp-adapter.md](native-mcp-adapter.md) for the normative approval fields and hash rules.

```bash
node scripts/run-p5-pilot.mjs \
  --pilot android-run \
  --binding /absolute/path/to/native-binding.json \
  --approval /absolute/path/to/approval.json \
  --appium-log /absolute/path/to/appium-debug.log \
  --output-dir /absolute/path/to/p5-android-run
```

The Appium process must write a dedicated debug log for one pilot run. The adapter extracts the observed Appium server version, UiAutomator2 driver version, successful session timestamp, and package identity. It stores only a hash-bound structured record; it does not copy the raw log or Base64 recording payload into QA evidence.

If the external job completed before runtime-version enrichment was available, finalize the existing artifacts without replaying mutation steps:

```bash
node scripts/run-p5-pilot.mjs \
  --pilot android-finalize \
  --appium-log /absolute/path/to/appium-debug.log \
  --output-dir /absolute/path/to/existing-p5-android-run
```

The Android command succeeds only when the external job completes, runtime evidence is contract-valid, and the independent judge emits `result-v1` with `verdict: pass`. The Pass oracle uses the structured `wait_for` locator result, not screenshots or video.
