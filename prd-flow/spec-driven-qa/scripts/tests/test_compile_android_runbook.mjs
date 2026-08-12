import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { compileAndroidRunbook } from "../compile-android-runbook.mjs";
import { ContractError, sha256Json } from "../web-provider-lib.mjs";

export function androidScenario(overrides = {}) {
  return {
    schema_version: "scenario-v1",
    id: "android-ready-state",
    title: "Android ready state appears",
    source_refs: [{ source_id: "ticket-spec", anchor_id: "save-status-ac" }],
    method: "native",
    preconditions: [],
    fixture: { kind: "seed", ref: "android-ready-v1", purpose: "baseline", destructive: false, environment: "isolated" },
    steps: [
      { id: "launch-app", action: "launch", description: "Launch the approved APK", mutation: "potential" },
      { id: "wait-ready", action: "wait_for", description: "Wait for the ready control", mutation: "none", arguments: { control_ref: "ready_control", state: "present" } },
    ],
    expected: [{ id: "ready-visible", description: "The ready control is present", source_refs: [{ source_id: "ticket-spec", anchor_id: "save-status-ac" }] }],
    oracle: { mode: "deterministic", rules: [{ id: "ready-present", kind: "deterministic", expectation_id: "ready-visible", evidence_kind: "locator_result", operator: "equals", actual_path: "/outcome", value: "matched" }] },
    severity: "high",
    spec_version: "spec-2026-08-01",
    review_status: "approved",
    target: { platform: "android", device: "emulator", artifact_type: "apk" },
    runner_provider: "native-android",
    mutation_policy: { mode: "require_approval", approval_scope: ["launch-app"], retry_policy: "never" },
    execution: { enabled: true },
    ...overrides,
  };
}

export function androidConfig(overrides = {}) {
  return {
    schema_version: "native-android-config-v1",
    provider: "native-android",
    provider_contract_version: "native-mcp-adapter-v1",
    implementation_version: "1.1.0",
    defaults_version: "native-android-defaults-v1",
    runbook_id: "android-ready-state-r1",
    locators: {
      ready_control: [
        { by: "id", value: "org.example.qa:id/ready" },
        { by: "accessibility_id", value: "qa-ready" },
      ],
    },
    timeouts_ms: { launch: 30_000, wait_for: 10_000 },
    hold_ms: 0,
    read_only_retry_policy: "safe",
    read_only_max_attempts: 1,
    evidence_collectors: { "ready-present": { kind: "locator_result", after_step_id: "wait-ready" } },
    ...overrides,
  };
}

function makeApproval(preflight, providerPlanHash = `sha256:${"9".repeat(64)}`) {
  return {
    id: "approval-android-1",
    record_sha256: sha256Json({ approval: "android-1" }),
    plan_sha256: preflight.integrity.plan_sha256,
    provider_plan_hash: providerPlanHash,
    runtime_binding_sha256: `sha256:${"8".repeat(64)}`,
    approved_step_ids: ["launch-app"],
    environment: "isolated",
    scope: "single_run",
    expires_at: null,
    approved_by_ref: "approver-directory-id",
  };
}

test("compiles first launch and wait_for with accessibility locator priority", () => {
  const preflight = compileAndroidRunbook({ scenario: androidScenario(), config: androidConfig(), allowUnapprovedPreflight: true });
  const runbook = compileAndroidRunbook({ scenario: androidScenario(), config: androidConfig(), approval: makeApproval(preflight) });
  assert.equal(preflight.runbook_state, "preflight");
  assert.equal(preflight.approval_ref, null);
  assert.equal(runbook.runbook_state, "executable");
  assert.equal(runbook.steps[0].action, "launch");
  assert.equal(runbook.steps[0].retry_policy, "never");
  assert.deepEqual(runbook.steps[1].provider_args.locator, { by: "accessibility_id", value: "qa-ready" });
  assert.equal(runbook.approval_ref.plan_sha256, runbook.integrity.plan_sha256);
  assert.equal(preflight.integrity.plan_sha256, runbook.integrity.plan_sha256);
  assert.notEqual(sha256Json(preflight), sha256Json(runbook));
});

test("falls back to resource id when accessibility id is unavailable", () => {
  const config = androidConfig({ locators: { ready_control: [{ by: "id", value: "org.example.qa:id/ready" }] } });
  const runbook = compileAndroidRunbook({ scenario: androidScenario(), config, allowUnapprovedPreflight: true });
  assert.equal(runbook.steps[1].provider_args.locator.by, "id");
});

test("requires provider-plan approval after frozen runbook preflight", () => {
  assert.throws(
    () => compileAndroidRunbook({ scenario: androidScenario(), config: androidConfig() }),
    (error) => error instanceof ContractError && error.code === "E_APPROVAL_REQUIRED" && /^sha256:/.test(error.details.plan_sha256),
  );
});

test("requires runtime binding hash in Android approval", () => {
  const preflight = compileAndroidRunbook({ scenario: androidScenario(), config: androidConfig(), allowUnapprovedPreflight: true });
  const approval = makeApproval(preflight);
  delete approval.runtime_binding_sha256;
  assert.throws(
    () => compileAndroidRunbook({ scenario: androidScenario(), config: androidConfig(), approval }),
    (error) => error instanceof ContractError && error.code === "E_APPROVAL_INVALID",
  );
});

test("rejects physical Android and AAB targets", () => {
  for (const target of [
    { platform: "android", device: "physical", artifact_type: "apk" },
    { platform: "android", device: "emulator", artifact_type: "aab" },
  ]) {
    assert.throws(() => compileAndroidRunbook({ scenario: androidScenario({ target }), config: androidConfig(), allowUnapprovedPreflight: true }), (error) => error.code === "E_ANDROID_TARGET_UNSUPPORTED");
  }
});

test("rejects actions outside the P3 vertical slice", () => {
  const input = androidScenario({ steps: [...androidScenario().steps, { id: "tap-ready", action: "tap", description: "Tap ready", mutation: "potential", arguments: { control_ref: "ready_control" } }], mutation_policy: { mode: "require_approval", approval_scope: ["launch-app", "tap-ready"], retry_policy: "never" } });
  assert.throws(() => compileAndroidRunbook({ scenario: input, config: androidConfig(), allowUnapprovedPreflight: true }), (error) => error.code === "E_ANDROID_ACTION_UNSUPPORTED");
});

test("approved compiled runbook passes Python runbook-v1 validation", () => {
  const scenario = androidScenario();
  const preflight = compileAndroidRunbook({ scenario, config: androidConfig(), allowUnapprovedPreflight: true });
  const runbook = compileAndroidRunbook({ scenario, config: androidConfig(), approval: makeApproval(preflight) });
  const bundle = {
    schema_version: "spec-bundle-v1", bundle_id: "sample-bundle", spec_version: "spec-2026-08-01",
    sources: [{ id: "ticket-spec", kind: "acceptance_criteria", title: "Save behavior", version: "1", content_hash: "sha256:4e8d7f41a2abf3d2484f39c4e9c8c650bb4f4758609cd21ee44addf2099ee179", anchors: [{ id: "save-status-ac", kind: "acceptance_criterion", title: "Saved state", statement: "A successful save exposes the saved state.", status: "approved" }] }],
  };
  const directory = mkdtempSync(path.join(os.tmpdir(), "android-runbook-"));
  const paths = { bundle: path.join(directory, "bundle.json"), scenario: path.join(directory, "scenario.json"), runbook: path.join(directory, "runbook.json") };
  writeFileSync(paths.bundle, JSON.stringify(bundle)); writeFileSync(paths.scenario, JSON.stringify(scenario)); writeFileSync(paths.runbook, JSON.stringify(runbook));
  const validator = path.resolve(import.meta.dirname, "../validate-contracts.py");
  const result = spawnSync("python3", [validator, "--bundle", paths.bundle, "--scenario", paths.scenario, paths.runbook], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr || result.stdout);
});

test("preflight compiled runbook passes Python runbook-v1 validation without approval", () => {
  const scenario = androidScenario();
  const runbook = compileAndroidRunbook({ scenario, config: androidConfig(), allowUnapprovedPreflight: true });
  const bundle = {
    schema_version: "spec-bundle-v1", bundle_id: "sample-bundle", spec_version: "spec-2026-08-01",
    sources: [{ id: "ticket-spec", kind: "acceptance_criteria", title: "Save behavior", version: "1", content_hash: "sha256:4e8d7f41a2abf3d2484f39c4e9c8c650bb4f4758609cd21ee44addf2099ee179", anchors: [{ id: "save-status-ac", kind: "acceptance_criterion", title: "Saved state", statement: "A successful save exposes the saved state.", status: "approved" }] }],
  };
  const directory = mkdtempSync(path.join(os.tmpdir(), "android-runbook-preflight-"));
  const paths = { bundle: path.join(directory, "bundle.json"), scenario: path.join(directory, "scenario.json"), runbook: path.join(directory, "runbook.json") };
  writeFileSync(paths.bundle, JSON.stringify(bundle)); writeFileSync(paths.scenario, JSON.stringify(scenario)); writeFileSync(paths.runbook, JSON.stringify(runbook));
  const validator = path.resolve(import.meta.dirname, "../validate-contracts.py");
  const result = spawnSync("python3", [validator, "--bundle", paths.bundle, "--scenario", paths.scenario, paths.runbook], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr || result.stdout);
});
