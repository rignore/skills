import assert from "node:assert/strict";
import http from "node:http";
import test from "node:test";

import { compileWebRunbook } from "../compile-web-runbook.mjs";
import { runWebPlaywright } from "../run-web-playwright.mjs";
import { sha256Json } from "../web-provider-lib.mjs";

const moduleRoot = process.env.SPEC_DRIVEN_QA_PLAYWRIGHT_MODULE_ROOT;

function startServer() {
  const server = http.createServer((request, response) => {
    if (request.url === "/api/state") {
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify({ record: { state: "ready" }, internal: "not-selected" }));
      return;
    }
    if (request.url === "/records/fixture") {
      response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
      response.end(`<!doctype html>
        <html lang="en"><body>
          <div data-testid="record-state" role="status" aria-label="Record state">ready</div>
          <script>localStorage.setItem("qa-state", "ready-secret-value");</script>
        </body></html>`);
      return;
    }
    response.writeHead(404);
    response.end("not found");
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}

function makeScenario(platform) {
  const evidenceKinds = ["dom_state", "accessibility_state", "locator_result", "url_state", "api_state", "storage_state", "network_error", "console_error"];
  return {
    schema_version: "scenario-v1",
    id: `web-observe-${platform}`,
    title: "Observe structured web state",
    source_refs: [{ source_id: "prd", anchor_id: "ready-state" }],
    method: "web",
    preconditions: [],
    fixture: { kind: "seed", ref: "ready-record-v1", purpose: "baseline", destructive: false, environment: "isolated" },
    steps: [
      { id: "open-record", action: "navigate", description: "Open the record", mutation: "none", arguments: { route_ref: "record" } },
      { id: "wait-state", action: "wait_for", description: "Wait for ready state", mutation: "none", arguments: { control_ref: "state", state: "visible" } },
    ],
    expected: [{ id: "ready", description: "Record state is ready", source_refs: [{ source_id: "prd", anchor_id: "ready-state" }] }],
    oracle: {
      mode: "deterministic",
      rules: evidenceKinds.map((kind) => ({
        id: `observe-${kind.replaceAll("_", "-")}`,
        kind: "deterministic",
        expectation_id: "ready",
        evidence_kind: kind,
        operator: "exists",
        actual_path: "/",
      })),
    },
    severity: "high",
    spec_version: "spec-integration-v1",
    review_status: "approved",
    target: platform === "web" ? { platform: "web", device: "desktop" } : { platform: "mobile_web", device: "responsive" },
    runner_provider: "web-playwright",
    mutation_policy: { mode: "deny", approval_scope: [], retry_policy: "never" },
    execution: { enabled: true },
  };
}

function makeConfig(origin, scenario) {
  const collectors = {};
  for (const rule of scenario.oracle.rules) {
    const base = { kind: rule.evidence_kind, after_step_id: "wait-state" };
    if (["dom_state", "accessibility_state", "locator_result"].includes(rule.evidence_kind)) base.locator_ref = "state";
    if (rule.evidence_kind === "dom_state") base.fields = ["text", "visible"];
    if (rule.evidence_kind === "api_state") Object.assign(base, { route_ref: "api_state", json_pointers: ["/record/state"] });
    if (rule.evidence_kind === "storage_state") Object.assign(base, { area: "localStorage", allowed_keys: ["qa-state"] });
    collectors[rule.id] = base;
  }
  return {
    schema_version: "web-playwright-config-v1",
    provider: "web-playwright",
    provider_contract_version: "web-playwright-runner-v1",
    implementation_version: "1.0.0",
    defaults_version: "web-playwright-defaults-v1",
    runbook_id: `${scenario.id}-r1`,
    browser: "chromium",
    headless: true,
    origin,
    allowed_origins: [origin],
    profiles: {
      desktop: { viewport: { width: 1280, height: 720 }, locale: "en-US", color_scheme: "light", reduced_motion: "reduce" },
      responsive: { viewport: { width: 390, height: 844 }, device_scale_factor: 1, is_mobile: true, has_touch: true, locale: "en-US", color_scheme: "light", reduced_motion: "reduce" },
    },
    routes: { record: "/records/fixture", api_state: "/api/state" },
    locators: { state: { by: "test_id", value: "record-state" } },
    fixture_values: {},
    options: {},
    timeouts_ms: { goto: 10_000, action: 5_000, evidence: 5_000 },
    read_only_retry_policy: "never",
    read_only_max_attempts: 1,
    evidence_collectors: collectors,
  };
}

function makeRequest(runbook, platform) {
  return {
    schema_version: "runner-request-v1",
    run_id: `integration-${platform}`,
    requested_at: new Date().toISOString(),
    attempt: 1,
    runbook_id: runbook.runbook_id,
    runbook_ref: `runbooks/${runbook.runbook_id}.json`,
    runbook_sha256: sha256Json(runbook),
    plan_sha256: runbook.integrity.plan_sha256,
    runner_provider: runbook.runner_provider,
    target: runbook.target,
    project_config_sha256: runbook.project_config_sha256,
    runtime_binding: null,
    build: { ref: "local-fixture-server", sha256: sha256Json({ build: "local-fixture-server" }) },
    artifact: null,
  };
}

test("returns not_started for a runbook hash mismatch before loading Playwright", async () => {
  const scenario = makeScenario("web");
  const runbook = compileWebRunbook({ scenario, config: makeConfig("http://127.0.0.1:4173", scenario) });
  const request = makeRequest(runbook, "web");
  request.runbook_sha256 = `sha256:${"0".repeat(64)}`;
  const output = await runWebPlaywright({ request, runbook });
  assert.equal(output.execution.status, "not_started");
  assert.equal(output.errors[0].code, "E_RUNBOOK_HASH_MISMATCH");
  assert.equal(output.step_results.every((step) => step.status === "not_started"), true);
  assert.equal("verdict" in output, false);
});

for (const platform of ["web", "mobile_web"]) {
  test(`runs ${platform} and records structured evidence without a verdict`, { skip: !moduleRoot }, async () => {
    const server = await startServer();
    try {
      const address = server.address();
      const origin = `http://127.0.0.1:${address.port}`;
      const scenario = makeScenario(platform);
      const runbook = compileWebRunbook({ scenario, config: makeConfig(origin, scenario) });
      const output = await runWebPlaywright({ request: makeRequest(runbook, platform), runbook, playwrightModuleRoot: moduleRoot });
      assert.equal(output.execution.status, "completed");
      assert.equal(output.target.platform, platform);
      assert.equal("verdict" in output, false);
      assert.equal("oracle_results" in output, false);
      const evidenceKinds = new Set(output.evidence.map((item) => item.kind));
      for (const kind of ["test_command", "dom_state", "accessibility_state", "locator_result", "url_state", "api_state", "storage_state", "network_error", "console_error"]) {
        assert.equal(evidenceKinds.has(kind), true, `missing ${kind}`);
      }
      const command = output.evidence.find((item) => item.kind === "test_command").record;
      assert.equal(command.context.is_mobile, platform === "mobile_web");
      assert.equal(command.context.viewport.width, platform === "mobile_web" ? 390 : 1280);
      const storage = output.evidence.find((item) => item.kind === "storage_state");
      assert.equal(JSON.stringify(storage).includes("ready-secret-value"), false);
      assert.match(storage.record.keys["qa-state"].value_sha256, /^sha256:[0-9a-f]{64}$/);
      const api = output.evidence.find((item) => item.kind === "api_state");
      assert.deepEqual(api.record.selected, { "/record/state": "ready" });
      assert.deepEqual(output.errors, []);
      assert.deepEqual(output.missing_evidence, []);
    } finally {
      await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
    }
  });
}
