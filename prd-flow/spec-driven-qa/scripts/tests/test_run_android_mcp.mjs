import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { compileAndroidRunbook } from "../compile-android-runbook.mjs";
import { hashRuntimeSourceTree, runAndroidMcp, toolsListProjection, validateNativeBinding } from "../run-android-mcp.mjs";
import { sha256Json } from "../web-provider-lib.mjs";

const PROVIDER_PLAN_HASH = `sha256:${"7".repeat(64)}`;
const NATIVE_SCHEMA = { type: "object", title: "Synthetic Native Scenario V1" };
const TOOL_NAMES = [
  "get_native_video_scenario_schema", "register_native_app", "get_native_runtime_status",
  "inspect_native_app", "create_native_video_job", "preflight_video_job",
  "approve_video_job", "start_video_job", "get_video_job",
];
const TOOLS = TOOL_NAMES.map((name) => ({ name, inputSchema: { type: "object" }, outputSchema: { type: "object" } }));

function androidScenario() {
  return {
    schema_version: "scenario-v1", id: "android-ready-state", title: "Android ready state appears",
    source_refs: [{ source_id: "ticket-spec", anchor_id: "save-status-ac" }], method: "native", preconditions: [],
    fixture: { kind: "seed", ref: "android-ready-v1", purpose: "baseline", destructive: false, environment: "isolated" },
    steps: [
      { id: "launch-app", action: "launch", description: "Launch the approved APK", mutation: "potential" },
      { id: "wait-ready", action: "wait_for", description: "Wait for the ready control", mutation: "none", arguments: { control_ref: "ready_control", state: "present" } },
    ],
    expected: [{ id: "ready-visible", description: "The ready control is present", source_refs: [{ source_id: "ticket-spec", anchor_id: "save-status-ac" }] }],
    oracle: { mode: "deterministic", rules: [{ id: "ready-present", kind: "deterministic", expectation_id: "ready-visible", evidence_kind: "locator_result", operator: "equals", actual_path: "/outcome", value: "matched" }] },
    severity: "high", spec_version: "spec-2026-08-01", review_status: "approved",
    target: { platform: "android", device: "emulator", artifact_type: "apk" }, runner_provider: "native-android",
    mutation_policy: { mode: "require_approval", approval_scope: ["launch-app"], retry_policy: "never" }, execution: { enabled: true },
  };
}

function androidConfig() {
  return {
    schema_version: "native-android-config-v1", provider: "native-android", provider_contract_version: "native-mcp-adapter-v1",
    implementation_version: "1.1.0", defaults_version: "native-android-defaults-v1", runbook_id: "android-ready-state-r1",
    locators: { ready_control: [{ by: "id", value: "org.example.qa:id/ready" }, { by: "accessibility_id", value: "qa-ready" }] },
    timeouts_ms: { launch: 30_000, wait_for: 10_000 }, hold_ms: 0, read_only_retry_policy: "safe", read_only_max_attempts: 1,
    evidence_collectors: { "ready-present": { kind: "locator_result", after_step_id: "wait-ready" } },
  };
}

function hashBytes(value) {
  return `sha256:${createHash("sha256").update(value).digest("hex")}`;
}

async function fixture() {
  const directory = mkdtempSync(path.join(os.tmpdir(), "native-adapter-"));
  const apkPath = path.join(directory, "sample.apk");
  writeFileSync(apkPath, Buffer.from([0x50, 0x4b, 0x03, 0x04, 1, 2, 3, 4]));
  const executablePath = process.execPath;
  const runtimeSourceRoot = path.join(directory, "runtime-source");
  mkdirSync(runtimeSourceRoot);
  writeFileSync(path.join(runtimeSourceRoot, "server.mjs"), "export const serverVersion = '1.0.0';\n");
  const runtimeSource = await hashRuntimeSourceTree(runtimeSourceRoot);
  const javaHome = path.join(directory, "jdk");
  const javaPath = path.join(javaHome, "bin", "java");
  const apksignerPath = path.join(directory, "android-sdk", "build-tools", "35.0.0", "apksigner");
  mkdirSync(path.dirname(javaPath), { recursive: true });
  mkdirSync(path.dirname(apksignerPath), { recursive: true });
  writeFileSync(javaPath, "#!/bin/sh\nprintf '%s\\n' 'openjdk version \"21.0.1\"' >&2\n");
  writeFileSync(apksignerPath, "#!/bin/sh\nprintf '%s\\n' 'Signer #1 certificate DN: CN=synthetic'\n");
  chmodSync(javaPath, 0o755);
  chmodSync(apksignerPath, 0o755);
  const binding = {
    schema_version: "native-mcp-binding-v1",
    binding_id: "synthetic-native-binding-r1",
    server: {
      name: "demo-video-mcp", version: "1.0.0", protocol_version: "2025-06-18", transport: "stdio",
      executable_sha256: hashBytes(readFileSync(executablePath)), contract_version: "native-scenario-v1",
      runtime_source: { kind: "directory_tree", ...runtimeSource },
      launch: { executable_path: executablePath, arguments: [] },
    },
    capabilities: {
      discovered_at: "2026-08-02T00:00:00Z",
      tools_list_sha256: sha256Json(toolsListProjection(TOOLS)),
      native_scenario_schema_sha256: sha256Json(NATIVE_SCHEMA),
      required_tools: [...TOOL_NAMES],
    },
    artifact: { type: "apk", local_path: apkPath, expected_sha256: hashBytes(readFileSync(apkPath)) },
    readiness: {
      java: { home_path: javaHome, executable_path: javaPath, executable_sha256: hashBytes(readFileSync(javaPath)) },
      apk_verifier: { verifier: "apksigner", executable_path: apksignerPath, executable_sha256: hashBytes(readFileSync(apksignerPath)) },
    },
    package_id: "org.example.qasample",
    device: { runtime: "emulator", avd: "qa-api-35", udid: "emulator-5554", device_name: "qa-emulator", platform_version: "35", orientation: "portrait", language: "en", locale: "US", reset_policy: "preserve" },
    appium: { server_url: "http://127.0.0.1:4723", driver: "uiautomator2" },
    execution: { max_duration_seconds: 10, poll_interval_ms: 50 },
  };
  return { directory, apkPath, runtimeSourceRoot, javaPath, apksignerPath, binding };
}

class FakeMcpClient {
  constructor(binding, { providerPlanHash = PROVIDER_PLAN_HASH, terminalState = "SUCCEEDED", offsetTimestamps = false } = {}) {
    this.binding = binding;
    this.providerPlanHash = providerPlanHash;
    this.terminalState = terminalState;
    this.offsetTimestamps = offsetTimestamps;
    this.calls = [];
    this.closed = false;
  }
  async start() { this.calls.push(["start", {}]); }
  async initialize(protocolVersion) {
    this.calls.push(["initialize", { protocolVersion }]);
    return { protocolVersion, capabilities: { tools: {} }, serverInfo: { name: this.binding.server.name, version: this.binding.server.version } };
  }
  async listTools() { this.calls.push(["tools/list", {}]); return { tools: TOOLS }; }
  async callTool(name, args) {
    this.calls.push([name, args]);
    if (name === "get_native_video_scenario_schema") return { schema: NATIVE_SCHEMA };
    if (name === "register_native_app") return { artifact: { artifact_id: "apk-synthetic", platform: "android", format: "apk", sha256: this.binding.artifact.expected_sha256, size_bytes: 8 }, execution_support: { android: "available", ios: "contract_only" } };
    if (name === "get_native_runtime_status") return { backend: "native-android", ready: true, connected_devices: ["emulator-5554"], checks: [], appium_version: "2.0.0", uiautomator2_version: "4.0.0" };
    if (name === "create_native_video_job") return { job_id: "job-synthetic", state: "DRAFT", plan_hash: this.providerPlanHash, artifacts: [] };
    if (name === "preflight_video_job") return { job: { job_id: "job-synthetic", state: "AWAITING_APPROVAL", plan_hash: this.providerPlanHash }, preflight: { job_id: "job-synthetic", backend: "native-android", plan_hash: this.providerPlanHash, checks: [], runtime: {}, mutations: [{ step_id: "launch-app", title: "Launch", effects: ["potential_mutation"], retry_policy: "never" }], requires_approval: true, passed: true } };
    if (name === "approve_video_job") return { job_id: "job-synthetic", state: "READY", plan_hash: this.providerPlanHash, artifacts: [] };
    if (name === "start_video_job") return { job_id: "job-synthetic", state: "QUEUED", plan_hash: this.providerPlanHash, artifacts: [] };
    if (name === "get_video_job") return {
      job_id: "job-synthetic", state: this.terminalState, plan_hash: this.providerPlanHash, artifacts: [],
      manifest: {
        state: this.terminalState,
        started_at: this.offsetTimestamps ? "2026-08-02T09:00:00+09:00" : "2026-08-02T00:00:00Z",
        finished_at: this.offsetTimestamps ? "2026-08-02T09:00:02+09:00" : "2026-08-02T00:00:02Z",
        external_effect_state: this.terminalState === "SUCCEEDED" ? "MUTATION_POSSIBLE" : "UNTOUCHED",
        review_required: false,
        error: this.terminalState === "SUCCEEDED" ? null : "synthetic provider failure",
        steps: this.terminalState === "SUCCEEDED" ? [
          { step_id: "launch-app", state: "passed", started_at: "2026-08-02T00:00:00Z", finished_at: "2026-08-02T00:00:01Z", error: null },
          { step_id: "wait-ready", state: "passed", started_at: "2026-08-02T00:00:01Z", finished_at: "2026-08-02T00:00:02Z", error: null },
        ] : [],
      },
    };
    throw new Error(`unexpected tool ${name}`);
  }
  async close() { this.closed = true; }
}

function requestFor(runbook, binding) {
  return {
    schema_version: "runner-request-v1", run_id: "run-android-synthetic-1", requested_at: "2026-08-02T00:00:00Z", attempt: 1,
    runbook_id: runbook.runbook_id, runbook_ref: `runbooks/${runbook.runbook_id}.json`, runbook_sha256: sha256Json(runbook),
    plan_sha256: runbook.integrity.plan_sha256, runner_provider: "native-android", target: runbook.target,
    project_config_sha256: runbook.project_config_sha256,
    runtime_binding: { binding_id: binding.binding_id, sha256: sha256Json(binding) },
    build: { ref: "synthetic-debug-build", sha256: sha256Json({ build: "synthetic" }) },
    artifact: { id: "local-apk", type: "apk", sha256: binding.artifact.expected_sha256 },
  };
}

function approvalFor(preflightRunbook, providerPlanHash, binding) {
  return {
    id: "approval-native-1", record_sha256: sha256Json({ approval: "native-1" }),
    plan_sha256: preflightRunbook.integrity.plan_sha256, provider_plan_hash: providerPlanHash,
    runtime_binding_sha256: sha256Json(binding),
    approved_step_ids: ["launch-app"], environment: "isolated", scope: "single_run", expires_at: null,
    approved_by_ref: "approver-directory-id",
  };
}

test("validates native-mcp-binding-v1 local Emulator boundary", async () => {
  const { binding } = await fixture();
  assert.equal(validateNativeBinding(binding), binding);
  const remote = structuredClone(binding);
  remote.appium.server_url = "https://remote.example.invalid/wd/hub";
  assert.throws(() => validateNativeBinding(remote), (error) => error.code === "E_APPIUM_LOCAL_REQUIRED");
});

test("runtime source tree digest is deterministic across file creation order", async () => {
  const first = mkdtempSync(path.join(os.tmpdir(), "runtime-source-first-"));
  const second = mkdtempSync(path.join(os.tmpdir(), "runtime-source-second-"));
  for (const directory of [first, second]) mkdirSync(path.join(directory, "nested"));
  writeFileSync(path.join(first, "nested", "b.py"), "B = 2\n");
  writeFileSync(path.join(first, "a.py"), "A = 1\n");
  writeFileSync(path.join(second, "a.py"), "A = 1\n");
  writeFileSync(path.join(second, "nested", "b.py"), "B = 2\n");
  const firstDigest = await hashRuntimeSourceTree(first);
  const secondDigest = await hashRuntimeSourceTree(second);
  assert.equal(firstDigest.source_tree_sha256, secondDigest.source_tree_sha256);
  assert.equal(firstDigest.file_count, 2);
  assert.equal(firstDigest.total_bytes, secondDigest.total_bytes);
});

test("runtime source change stops before MCP client creation", async () => {
  const { binding, runtimeSourceRoot } = await fixture();
  const runbook = compileAndroidRunbook({ scenario: androidScenario(), config: androidConfig(), allowUnapprovedPreflight: true });
  writeFileSync(path.join(runtimeSourceRoot, "server.mjs"), "export const serverVersion = '1.0.1';\n");
  let clientCreated = false;
  const output = await runAndroidMcp({
    request: requestFor(runbook, binding),
    runbook,
    binding,
    preflightOnly: true,
    clientFactory: async () => { clientCreated = true; return new FakeMcpClient(binding); },
  });
  assert.equal(output.passed, false);
  assert.equal(output.errors[0].code, "E_MCP_RUNTIME_HASH_MISMATCH");
  assert.equal(clientCreated, false);
});

test("preflight flag requires an explicit preflight runbook state", async () => {
  const { binding } = await fixture();
  const runbook = compileAndroidRunbook({ scenario: androidScenario(), config: androidConfig(), allowUnapprovedPreflight: true });
  runbook.runbook_state = "executable";
  let clientCreated = false;
  const output = await runAndroidMcp({
    request: requestFor(runbook, binding),
    runbook,
    binding,
    preflightOnly: true,
    clientFactory: async () => { clientCreated = true; return new FakeMcpClient(binding); },
  });
  assert.equal(output.passed, false);
  assert.equal(output.errors[0].code, "E_RUNBOOK_PREFLIGHT_STATE_INVALID");
  assert.equal(clientCreated, false);
});

test("preflight returns provider plan hash without approval or execution", async () => {
  const { binding } = await fixture();
  const runbook = compileAndroidRunbook({ scenario: androidScenario(), config: androidConfig(), allowUnapprovedPreflight: true });
  const fake = new FakeMcpClient(binding);
  const output = await runAndroidMcp({ request: requestFor(runbook, binding), runbook, binding, preflightOnly: true, clientFactory: async () => fake });
  assert.equal(output.schema_version, "native-mcp-preflight-v1");
  assert.equal(output.passed, true);
  assert.equal(output.provider_plan_hash, PROVIDER_PLAN_HASH);
  assert.deepEqual(output.approved_step_ids, ["launch-app"]);
  assert.equal(output.readiness.schema_version, "android-readiness-v1");
  assert.equal(output.readiness.apk_verification.verified, true);
  assert.equal(output.readiness.apk_verification.signer_count, 1);
  assert.equal(fake.calls.some(([name]) => name === "approve_video_job"), false);
  assert.equal(fake.calls.some(([name]) => name === "start_video_job"), false);
});

test("JDK executable drift stops before MCP client creation", async () => {
  const { binding, javaPath } = await fixture();
  const runbook = compileAndroidRunbook({ scenario: androidScenario(), config: androidConfig(), allowUnapprovedPreflight: true });
  writeFileSync(javaPath, "#!/bin/sh\nprintf '%s\\n' 'openjdk version \"22\"' >&2\n");
  chmodSync(javaPath, 0o755);
  let clientCreated = false;
  const output = await runAndroidMcp({
    request: requestFor(runbook, binding),
    runbook,
    binding,
    preflightOnly: true,
    clientFactory: async () => { clientCreated = true; return new FakeMcpClient(binding); },
  });
  assert.equal(output.passed, false);
  assert.equal(output.errors[0].code, "E_ANDROID_READINESS_TOOL_HASH_MISMATCH");
  assert.equal(clientCreated, false);
});

test("unsigned APK verification stops before MCP client creation", async () => {
  const { binding, apksignerPath } = await fixture();
  writeFileSync(apksignerPath, "#!/bin/sh\nprintf '%s\\n' 'DOES NOT VERIFY' >&2\nexit 1\n");
  chmodSync(apksignerPath, 0o755);
  binding.readiness.apk_verifier.executable_sha256 = hashBytes(readFileSync(apksignerPath));
  const runbook = compileAndroidRunbook({ scenario: androidScenario(), config: androidConfig(), allowUnapprovedPreflight: true });
  let clientCreated = false;
  const output = await runAndroidMcp({
    request: requestFor(runbook, binding),
    runbook,
    binding,
    preflightOnly: true,
    clientFactory: async () => { clientCreated = true; return new FakeMcpClient(binding); },
  });
  assert.equal(output.passed, false);
  assert.equal(output.errors[0].code, "E_APK_SIGNATURE_VERIFICATION_FAILED");
  assert.equal(clientCreated, false);
});

test("preflight normalizes the current MCP raw provider plan digest", async () => {
  const { binding } = await fixture();
  const runbook = compileAndroidRunbook({ scenario: androidScenario(), config: androidConfig(), allowUnapprovedPreflight: true });
  const rawHash = "a".repeat(64);
  const output = await runAndroidMcp({
    request: requestFor(runbook, binding),
    runbook,
    binding,
    preflightOnly: true,
    clientFactory: async () => new FakeMcpClient(binding, { providerPlanHash: rawHash }),
  });
  assert.equal(output.provider_plan_hash, `sha256:${rawHash}`);
});

test("approved execution replays MCP lifecycle and returns evidence without verdict", async () => {
  const { binding } = await fixture();
  const scenario = androidScenario();
  const preflightRunbook = compileAndroidRunbook({ scenario, config: androidConfig(), allowUnapprovedPreflight: true });
  const runbook = compileAndroidRunbook({ scenario, config: androidConfig(), approval: approvalFor(preflightRunbook, PROVIDER_PLAN_HASH, binding) });
  const fake = new FakeMcpClient(binding);
  const output = await runAndroidMcp({ request: requestFor(runbook, binding), runbook, binding, clientFactory: async () => fake });
  assert.equal(output.execution.status, "completed");
  assert.equal(output.execution.runner_version, "1.1.0");
  assert.equal("verdict" in output, false);
  assert.equal("oracle_results" in output, false);
  assert.deepEqual(output.errors, []);
  assert.deepEqual(output.missing_evidence, []);
  const kinds = new Set(output.evidence.map((item) => item.kind));
  for (const kind of ["test_command", "artifact_hash", "build_hash", "structured_log", "locator_result"]) assert.equal(kinds.has(kind), true, `missing ${kind}`);
  assert.equal(output.subject.native_runtime.device_type, "emulator");
  assert.equal(output.subject.native_runtime.automation_driver, "uiautomator2");
  const names = fake.calls.map(([name]) => name);
  assert.equal(names.includes("inspect_native_app"), false);
  assert.ok(names.indexOf("preflight_video_job") < names.indexOf("approve_video_job"));
  assert.ok(names.indexOf("approve_video_job") < names.indexOf("start_video_job"));
});

test("provider plan mismatch stops before approve and start", async () => {
  const { binding } = await fixture();
  const scenario = androidScenario();
  const preflightRunbook = compileAndroidRunbook({ scenario, config: androidConfig(), allowUnapprovedPreflight: true });
  const runbook = compileAndroidRunbook({ scenario, config: androidConfig(), approval: approvalFor(preflightRunbook, `sha256:${"8".repeat(64)}`, binding) });
  const fake = new FakeMcpClient(binding);
  const output = await runAndroidMcp({ request: requestFor(runbook, binding), runbook, binding, clientFactory: async () => fake });
  assert.equal(output.execution.status, "not_started");
  assert.equal(output.errors[0].code, "E_PROVIDER_PLAN_APPROVAL_MISMATCH");
  assert.equal(fake.calls.some(([name]) => name === "approve_video_job"), false);
  assert.equal(fake.calls.some(([name]) => name === "start_video_job"), false);
});

test("runtime binding approval mismatch stops before MCP client creation", async () => {
  const { binding } = await fixture();
  const scenario = androidScenario();
  const preflightRunbook = compileAndroidRunbook({ scenario, config: androidConfig(), allowUnapprovedPreflight: true });
  const approval = approvalFor(preflightRunbook, PROVIDER_PLAN_HASH, binding);
  approval.runtime_binding_sha256 = `sha256:${"6".repeat(64)}`;
  const runbook = compileAndroidRunbook({ scenario, config: androidConfig(), approval });
  let clientCreated = false;
  const output = await runAndroidMcp({
    request: requestFor(runbook, binding),
    runbook,
    binding,
    clientFactory: async () => { clientCreated = true; return new FakeMcpClient(binding); },
  });
  assert.equal(output.execution.status, "not_started");
  assert.equal(output.errors[0].code, "E_APPROVAL_INVALID");
  assert.equal(clientCreated, false);
});

test("failed provider jobs normalize offset timestamps and remain partial", async () => {
  const { binding } = await fixture();
  const scenario = androidScenario();
  const preflightRunbook = compileAndroidRunbook({ scenario, config: androidConfig(), allowUnapprovedPreflight: true });
  const runbook = compileAndroidRunbook({ scenario, config: androidConfig(), approval: approvalFor(preflightRunbook, PROVIDER_PLAN_HASH, binding) });
  const output = await runAndroidMcp({
    request: requestFor(runbook, binding),
    runbook,
    binding,
    clientFactory: async () => new FakeMcpClient(binding, { terminalState: "FAILED", offsetTimestamps: true }),
  });
  assert.equal(output.execution.status, "partial");
  assert.equal(output.started_at, "2026-08-02T00:00:00.000Z");
  assert.equal(output.finished_at, "2026-08-02T00:00:02.000Z");
  assert.equal(output.errors[0].code, "E_NATIVE_JOB_FAILED");
  assert.equal(output.evidence.some((item) => item.id === "provider-terminal-state"), true);
});

test("unsupported native target returns not_started without calling MCP", async () => {
  const { binding } = await fixture();
  const runbook = compileAndroidRunbook({ scenario: androidScenario(), config: androidConfig(), allowUnapprovedPreflight: true });
  runbook.target = { platform: "ios", device: "simulator", artifact_type: "app_zip" };
  let clientCreated = false;
  const output = await runAndroidMcp({
    request: { ...requestFor(runbook, binding), target: runbook.target, runbook_sha256: sha256Json(runbook) },
    runbook,
    binding,
    clientFactory: async () => { clientCreated = true; return new FakeMcpClient(binding); },
  });
  assert.equal(output.execution.status, "not_started");
  assert.match(output.unsupported_reason, /Emulator and APK/);
  assert.equal(clientCreated, false);
});
