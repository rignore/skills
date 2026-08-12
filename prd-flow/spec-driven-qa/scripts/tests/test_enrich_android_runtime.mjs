import assert from "node:assert/strict";
import test from "node:test";

import { enrichAndroidRuntimeFromAppiumLog } from "../enrich-android-runtime.mjs";
import { sha256Json } from "../web-provider-lib.mjs";

function runnerOutput() {
  const command = { adapter_version: "1.0.0" };
  return {
    schema_version: "runner-output-v1",
    started_at: "2026-08-10T00:00:00.000Z",
    finished_at: "2026-08-10T00:00:02.000Z",
    execution: { status: "completed", command_evidence_ref: "runner-command", runner_version: "1.0.0" },
    subject: {
      artifact: { package_id: "io.appium.android.apis" },
      native_runtime: { automation_driver: "uiautomator2", appium_version: null, automation_driver_version: null },
    },
    step_results: [],
    evidence: [{
      id: "runner-command", kind: "test_command", collected_at: "2026-08-10T00:00:00.000Z",
      producer: { type: "adapter", name: "native-mcp-adapter", version: "1.0.0" },
      sha256: sha256Json(command), redactions: [], record: command,
    }],
    errors: [], missing_evidence: [], diagnostic_attachments: [],
  };
}

const LOG = [
  "2026-08-09 23:59:59:000 [Appium] Welcome to Appium v3.6.0",
  "2026-08-10 00:00:00:100 [AppiumDriver] Appium v3.6.0 creating new AndroidUiautomator2Driver (v8.1.2) session",
  '2026-08-10 00:00:00:200 [HTTP] POST /session {"appium:appPackage":"io.appium.android.apis"}',
  "2026-08-10 00:00:01:000 [HTTP] <-- POST /session 200 800 ms",
].join("\n");

test("enriches completed Android output with hash-bound observed runtime versions", () => {
  const output = enrichAndroidRuntimeFromAppiumLog({ runnerOutput: runnerOutput(), appiumLog: LOG });
  assert.equal(output.subject.native_runtime.appium_version, "3.6.0");
  assert.equal(output.subject.native_runtime.automation_driver_version, "8.1.2");
  const evidence = output.evidence.find((item) => item.id === "android-runtime-versions");
  assert.equal(evidence.record.appium_create_status, "http_200");
  assert.match(evidence.record.source_log_sha256, /^sha256:[0-9a-f]{64}$/);
  assert.equal(evidence.sha256, sha256Json(evidence.record));
  assert.equal("appiumLog" in evidence.record, false);
});

test("rejects logs without a successful session", () => {
  assert.throws(
    () => enrichAndroidRuntimeFromAppiumLog({ runnerOutput: runnerOutput(), appiumLog: LOG.replace("<-- POST /session 200", "<-- POST /session 500") }),
    (error) => error.code === "E_APPIUM_SESSION_EVIDENCE_INVALID",
  );
});

test("rejects logs for a different package", () => {
  assert.throws(
    () => enrichAndroidRuntimeFromAppiumLog({ runnerOutput: runnerOutput(), appiumLog: LOG.replace("io.appium.android.apis", "org.example.other") }),
    (error) => error.code === "E_APPIUM_LOG_SUBJECT_MISMATCH",
  );
});

test("rejects ambiguous observed driver versions", () => {
  assert.throws(
    () => enrichAndroidRuntimeFromAppiumLog({ runnerOutput: runnerOutput(), appiumLog: `${LOG}\nAppium v3.6.0 creating new AndroidUiautomator2Driver (v9.0.0) session` }),
    (error) => error.code === "E_UIAUTOMATOR2_VERSION_EVIDENCE_INVALID",
  );
});

test("refreshes existing runtime evidence only when the source log hash matches", () => {
  const first = enrichAndroidRuntimeFromAppiumLog({ runnerOutput: runnerOutput(), appiumLog: LOG });
  const second = enrichAndroidRuntimeFromAppiumLog({ runnerOutput: first, appiumLog: LOG });
  assert.equal(second.evidence.filter((item) => item.id === "android-runtime-versions").length, 1);
  assert.equal(second.evidence.find((item) => item.id === "android-runtime-versions").record.appium_create_status, "http_200");
});

test("rejects a successful session outside the runner execution window", () => {
  const lateLog = LOG.replace("2026-08-10 00:00:01:000", "2026-08-10 00:00:03:000");
  assert.throws(
    () => enrichAndroidRuntimeFromAppiumLog({ runnerOutput: runnerOutput(), appiumLog: lateLog }),
    (error) => error.code === "E_APPIUM_SESSION_TIME_MISMATCH",
  );
});
