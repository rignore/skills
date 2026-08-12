import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { compileWebRunbook } from "../compile-web-runbook.mjs";
import { ContractError, sha256Json } from "../web-provider-lib.mjs";

function scenario(overrides = {}) {
  return {
    schema_version: "scenario-v1",
    id: "web-read-record",
    title: "Read a record state",
    source_refs: [{ source_id: "ticket-spec", anchor_id: "save-status-ac" }],
    method: "web",
    preconditions: [],
    fixture: { kind: "seed", ref: "record-v1", purpose: "baseline", destructive: false, environment: "isolated" },
    steps: [
      { id: "open-record", action: "navigate", description: "Open the record route", mutation: "none", arguments: { route_ref: "record" } },
      { id: "wait-state", action: "wait_for", description: "Wait for the state field", mutation: "none", arguments: { control_ref: "state", state: "visible" } },
    ],
    expected: [{ id: "state-ready", description: "The record state is ready", source_refs: [{ source_id: "ticket-spec", anchor_id: "save-status-ac" }] }],
    oracle: { mode: "deterministic", rules: [{ id: "state-equals-ready", kind: "deterministic", expectation_id: "state-ready", evidence_kind: "dom_state", operator: "equals", actual_path: "/text", value: "ready" }] },
    severity: "high",
    spec_version: "spec-2026-08-01",
    review_status: "approved",
    target: { platform: "web", device: "desktop" },
    runner_provider: "web-playwright",
    mutation_policy: { mode: "deny", approval_scope: [], retry_policy: "never" },
    execution: { enabled: true },
    ...overrides,
  };
}

function config(overrides = {}) {
  return {
    schema_version: "web-playwright-config-v1",
    provider: "web-playwright",
    provider_contract_version: "web-playwright-runner-v1",
    implementation_version: "1.0.0",
    defaults_version: "web-playwright-defaults-v1",
    runbook_id: "web-read-record-r1",
    browser: "chromium",
    headless: true,
    origin: "http://127.0.0.1:4173",
    allowed_origins: ["http://127.0.0.1:4173"],
    profiles: {
      desktop: { viewport: { width: 1280, height: 720 }, locale: "en-US", color_scheme: "light", reduced_motion: "reduce" },
      responsive: { viewport: { width: 390, height: 844 }, device_scale_factor: 1, is_mobile: true, has_touch: true, locale: "en-US", color_scheme: "light", reduced_motion: "reduce" },
    },
    routes: { record: "/records/fixture" },
    locators: { state: { by: "test_id", value: "record-state" }, mutate: { by: "role", value: "button", name: "Mutate" } },
    fixture_values: {},
    options: {},
    timeouts_ms: { goto: 20_000, action: 5_000, evidence: 5_000 },
    read_only_retry_policy: "never",
    read_only_max_attempts: 1,
    evidence_collectors: { "state-equals-ready": { kind: "dom_state", after_step_id: "wait-state", locator_ref: "state", fields: ["text"] } },
    ...overrides,
  };
}

function reorder(value) {
  if (Array.isArray(value)) return value.map(reorder);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).reverse().map(([key, child]) => [key, reorder(child)]));
  }
  return value;
}

test("semantically identical key order produces the same runbook and hashes", () => {
  const first = compileWebRunbook({ scenario: scenario(), config: config() });
  const second = compileWebRunbook({ scenario: reorder(scenario()), config: reorder(config()) });
  assert.deepEqual(second, first);
  assert.equal(second.project_config_sha256, first.project_config_sha256);
  assert.equal(second.integrity.plan_sha256, first.integrity.plan_sha256);
});

test("route and locator changes change config and plan hashes", () => {
  const baseline = compileWebRunbook({ scenario: scenario(), config: config() });
  const changedRoute = compileWebRunbook({ scenario: scenario(), config: config({ routes: { record: "/records/other" } }) });
  const changedLocator = compileWebRunbook({
    scenario: scenario(),
    config: config({ locators: { ...config().locators, state: { by: "test_id", value: "other-state" } } }),
  });
  for (const changed of [changedRoute, changedLocator]) {
    assert.notEqual(changed.project_config_sha256, baseline.project_config_sha256);
    assert.notEqual(changed.integrity.plan_sha256, baseline.integrity.plan_sha256);
  }
});

test("responsive mobile web freezes a mobile context and remains web", () => {
  const input = scenario({ target: { platform: "mobile_web", device: "responsive" } });
  const runbook = compileWebRunbook({ scenario: input, config: config() });
  assert.equal(runbook.target.platform, "mobile_web");
  assert.equal(runbook.method, "web");
  assert.equal(runbook.steps[0].provider_args.context.is_mobile, true);
  assert.deepEqual(runbook.steps[0].provider_args.context.viewport, { width: 390, height: 844 });
});

test("unresolved locator fails compilation", () => {
  assert.throws(
    () => compileWebRunbook({ scenario: scenario(), config: config({ locators: {} }) }),
    (error) => error instanceof ContractError && error.code === "E_LOCATOR_UNRESOLVED",
  );
});

test("mutation compilation reports a frozen preflight hash and requires exact approval", () => {
  const input = scenario({
    steps: [
      scenario().steps[0],
      { id: "mutate", action: "activate", description: "Mutate the fixture", mutation: "confirmed", arguments: { control_ref: "mutate" } },
    ],
    mutation_policy: { mode: "require_approval", approval_scope: ["mutate"], retry_policy: "never" },
    oracle: { mode: "deterministic", rules: [{ id: "state-equals-ready", kind: "deterministic", expectation_id: "state-ready", evidence_kind: "dom_state", operator: "equals", actual_path: "/text", value: "ready" }] },
  });
  const inputConfig = config({ evidence_collectors: { "state-equals-ready": { kind: "dom_state", after_step_id: "mutate", locator_ref: "state", fields: ["text"] } } });
  let preflight;
  try {
    compileWebRunbook({ scenario: input, config: inputConfig });
    assert.fail("expected approval error");
  } catch (error) {
    assert.equal(error.code, "E_APPROVAL_REQUIRED");
    preflight = error.details;
  }
  const approval = {
    id: "approval-1",
    record_sha256: sha256Json({ id: "approval-1" }),
    plan_sha256: preflight.plan_sha256,
    approved_step_ids: preflight.approved_step_ids,
    environment: preflight.environment,
    scope: "single_run",
    expires_at: null,
    approved_by_ref: "approver-directory-id",
  };
  const runbook = compileWebRunbook({ scenario: input, config: inputConfig, approval });
  assert.equal(runbook.approval_ref.plan_sha256, runbook.integrity.plan_sha256);
  assert.equal(runbook.steps[1].retry_policy, "never");
  assert.equal(runbook.steps[1].max_attempts, 1);
});

test("secret material in project config is rejected", () => {
  assert.throws(
    () => compileWebRunbook({ scenario: scenario(), config: config({ access_token: "not-allowed-token-value" }) }),
    (error) => error instanceof ContractError && error.code === "E_SENSITIVE_INPUT",
  );
});

test("compiled runbook passes the Python runbook-v1 validator with exact context", () => {
  const inputScenario = scenario();
  const runbook = compileWebRunbook({ scenario: inputScenario, config: config() });
  const bundle = {
    schema_version: "spec-bundle-v1",
    bundle_id: "sample-bundle",
    spec_version: "spec-2026-08-01",
    sources: [{
      id: "ticket-spec",
      kind: "acceptance_criteria",
      title: "Save behavior",
      version: "1",
      content_hash: "sha256:4e8d7f41a2abf3d2484f39c4e9c8c650bb4f4758609cd21ee44addf2099ee179",
      anchors: [{ id: "save-status-ac", kind: "acceptance_criterion", title: "Saved state", statement: "A successful save exposes the saved state.", status: "approved" }],
    }],
  };
  const directory = mkdtempSync(path.join(os.tmpdir(), "spec-driven-qa-"));
  const files = { bundle: path.join(directory, "bundle.json"), scenario: path.join(directory, "scenario.json"), runbook: path.join(directory, "runbook.json") };
  writeFileSync(files.bundle, JSON.stringify(bundle));
  writeFileSync(files.scenario, JSON.stringify(inputScenario));
  writeFileSync(files.runbook, JSON.stringify(runbook));
  const validator = path.resolve(import.meta.dirname, "../validate-contracts.py");
  const result = spawnSync("python3", [validator, "--bundle", files.bundle, "--scenario", files.scenario, files.runbook], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  assert.match(result.stdout, /: valid\s*$/);
});
