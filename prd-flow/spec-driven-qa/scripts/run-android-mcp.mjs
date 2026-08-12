#!/usr/bin/env node

import { createHash } from "node:crypto";
import { execFile as execFileCallback } from "node:child_process";
import { createReadStream } from "node:fs";
import { open, readdir, stat } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { promisify } from "node:util";

import { StdioMcpClient } from "./mcp-stdio-client.mjs";
import {
  ContractError,
  assertPlainObject,
  assertSecretFree,
  cloneJson,
  parseCli,
  printContractError,
  readJson,
  requireInteger,
  requireNonEmptyString,
  runbookPlanHash,
  sha256Json,
  writeJson,
} from "./web-provider-lib.mjs";

const ADAPTER_VERSION = "1.1.0";
const HASH = /^sha256:[0-9a-f]{64}$/;
const REQUIRED_TOOLS = [
  "get_native_video_scenario_schema", "register_native_app", "get_native_runtime_status",
  "inspect_native_app", "create_native_video_job", "preflight_video_job",
  "approve_video_job", "start_video_job", "get_video_job",
];
const TERMINAL_STATES = new Set(["SUCCEEDED", "FAILED", "CANCELLED", "NEEDS_USER"]);
const execFile = promisify(execFileCallback);

function normalizeProviderPlanHash(value) {
  if (typeof value !== "string") throw new ContractError("E_MCP_JOB_INVALID", "provider plan hash is required");
  const normalized = value.startsWith("sha256:") ? value : `sha256:${value}`;
  if (!HASH.test(normalized)) throw new ContractError("E_MCP_JOB_INVALID", "provider plan hash must be a SHA-256 value");
  return normalized;
}

export function toolsListProjection(tools) {
  if (!Array.isArray(tools)) throw new ContractError("E_MCP_TOOLS_INVALID", "tools/list must return an array");
  return tools
    .map((tool) => ({ name: tool?.name, inputSchema: tool?.inputSchema, outputSchema: tool?.outputSchema }))
    .sort((left, right) => String(left.name).localeCompare(String(right.name)));
}

export async function hashFile(filePath) {
  return new Promise((resolve, reject) => {
    const digest = createHash("sha256");
    const stream = createReadStream(filePath);
    stream.on("data", (chunk) => digest.update(chunk));
    stream.on("error", reject);
    stream.on("end", () => resolve(`sha256:${digest.digest("hex")}`));
  });
}

export async function hashRuntimeSourceTree(rootPath) {
  if (!path.isAbsolute(rootPath) || rootPath === path.parse(rootPath).root) {
    throw new ContractError("E_MCP_RUNTIME_SOURCE_INVALID", "runtime source root must be an absolute non-filesystem-root directory", "$.server.runtime_source.root_path");
  }
  const rootMetadata = await stat(rootPath).catch(() => null);
  if (!rootMetadata?.isDirectory()) {
    throw new ContractError("E_MCP_RUNTIME_SOURCE_UNAVAILABLE", "runtime source root must be an existing directory", "$.server.runtime_source.root_path");
  }
  const files = [];
  async function walk(directory, prefix = "") {
    const entries = await readdir(directory, { withFileTypes: true });
    for (const entry of entries) {
      const relativePath = prefix ? path.join(prefix, entry.name) : entry.name;
      const absolutePath = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) {
        throw new ContractError("E_MCP_RUNTIME_SOURCE_INVALID", "runtime source tree must not contain symbolic links", `$.server.runtime_source.root_path/${relativePath}`);
      }
      if (entry.isDirectory()) {
        await walk(absolutePath, relativePath);
      } else if (entry.isFile()) {
        const metadata = await stat(absolutePath);
        const canonicalPath = relativePath.split(path.sep).join("/").normalize("NFC");
        files.push({ path: canonicalPath, sha256: await hashFile(absolutePath), size_bytes: metadata.size });
      } else {
        throw new ContractError("E_MCP_RUNTIME_SOURCE_INVALID", "runtime source tree supports regular files and directories only", `$.server.runtime_source.root_path/${relativePath}`);
      }
    }
  }
  try {
    await walk(rootPath);
  } catch (error) {
    if (error instanceof ContractError) throw error;
    throw new ContractError("E_MCP_RUNTIME_SOURCE_UNAVAILABLE", "runtime source tree could not be read", "$.server.runtime_source.root_path", { cause: error.message });
  }
  files.sort((left, right) => left.path < right.path ? -1 : left.path > right.path ? 1 : 0);
  if (files.length === 0) throw new ContractError("E_MCP_RUNTIME_SOURCE_INVALID", "runtime source tree must contain at least one file", "$.server.runtime_source.root_path");
  if (new Set(files.map((item) => item.path)).size !== files.length) throw new ContractError("E_MCP_RUNTIME_SOURCE_INVALID", "runtime source paths collide after canonical normalization", "$.server.runtime_source.root_path");
  return {
    root_path: rootPath,
    source_tree_sha256: sha256Json({ schema_version: "runtime-source-tree-v1", files }),
    file_count: files.length,
    total_bytes: files.reduce((total, item) => total + item.size_bytes, 0),
  };
}

async function assertApk(filePath, expectedHash) {
  if (!path.isAbsolute(filePath) || path.extname(filePath).toLowerCase() !== ".apk") throw new ContractError("E_ANDROID_APK_REQUIRED", "artifact.local_path must be an absolute APK path", "$.artifact.local_path");
  const metadata = await stat(filePath).catch(() => null);
  if (!metadata?.isFile() || metadata.size <= 0) throw new ContractError("E_ANDROID_APK_UNAVAILABLE", "APK must be a non-empty regular file", "$.artifact.local_path");
  const handle = await open(filePath, "r");
  try {
    const header = Buffer.alloc(4);
    await handle.read(header, 0, 4, 0);
    if (!(header[0] === 0x50 && header[1] === 0x4b)) throw new ContractError("E_ANDROID_APK_INVALID", "APK must be a ZIP-based artifact", "$.artifact.local_path");
  } finally {
    await handle.close();
  }
  const actualHash = await hashFile(filePath);
  if (actualHash !== expectedHash) throw new ContractError("E_ARTIFACT_HASH_MISMATCH", "local APK hash does not match the binding", "$.artifact.expected_sha256");
  return { sha256: actualHash, size_bytes: metadata.size };
}

async function runReadinessCommand(executablePath, args, environment, errorCode, contractPath) {
  try {
    const { stdout, stderr } = await execFile(executablePath, args, {
      encoding: "utf8",
      env: environment,
      maxBuffer: 1024 * 1024,
      timeout: 30_000,
    });
    return `${stdout}${stderr}`;
  } catch (error) {
    throw new ContractError(errorCode, "Android readiness command failed", contractPath, {
      exit_code: Number.isInteger(error.code) ? error.code : null,
      signal: error.signal ?? null,
    });
  }
}

export async function verifyAndroidReadiness(binding) {
  const java = binding.readiness?.java;
  const apkSigning = binding.readiness?.apk_verifier;
  const artifactMeta = await assertApk(binding.artifact?.local_path, binding.artifact?.expected_sha256);
  for (const [tool, value, contractPath] of [
    ["java", java, "$.readiness.java"],
    ["apksigner", apkSigning, "$.readiness.apk_verifier"],
  ]) {
    const metadata = await stat(value?.executable_path ?? "").catch(() => null);
    if (!path.isAbsolute(value?.executable_path ?? "") || !metadata?.isFile()) {
      throw new ContractError("E_ANDROID_READINESS_TOOL_UNAVAILABLE", `${tool} must be an absolute regular file`, `${contractPath}.executable_path`);
    }
    if (await hashFile(value.executable_path) !== value.executable_sha256) {
      throw new ContractError("E_ANDROID_READINESS_TOOL_HASH_MISMATCH", `${tool} executable hash differs from binding`, `${contractPath}.executable_sha256`);
    }
  }
  const javaHome = java.home_path;
  const readinessEnvironment = {
    ...process.env,
    JAVA_HOME: javaHome,
    PATH: `${path.dirname(java.executable_path)}${path.delimiter}${process.env.PATH ?? ""}`,
  };
  const javaOutput = await runReadinessCommand(
    java.executable_path,
    ["-version"],
    readinessEnvironment,
    "E_JAVA_RUNTIME_NOT_READY",
    "$.readiness.java",
  );
  if (!/(?:openjdk|java)\s+(?:version\s+)?["']?\d/i.test(javaOutput)) {
    throw new ContractError("E_JAVA_RUNTIME_NOT_READY", "java -version did not report a recognizable JDK version", "$.readiness.java");
  }
  const signingOutput = await runReadinessCommand(
    apkSigning.executable_path,
    ["verify", "--print-certs", binding.artifact.local_path],
    readinessEnvironment,
    "E_APK_SIGNATURE_VERIFICATION_FAILED",
    "$.readiness.apk_verifier",
  );
  const signerIds = new Set([...signingOutput.matchAll(/Signer #(\d+) certificate\b/g)].map((match) => match[1]));
  if (signerIds.size < 1) {
    throw new ContractError("E_APK_SIGNATURE_VERIFICATION_FAILED", "apksigner did not report an APK signing certificate", "$.artifact.local_path");
  }
  return {
    schema_version: "android-readiness-v1",
    artifact_sha256: artifactMeta.sha256,
    java: {
      executable_sha256: java.executable_sha256,
      version_output_sha256: `sha256:${createHash("sha256").update(javaOutput).digest("hex")}`,
    },
    apk_verification: {
      verifier: "apksigner",
      executable_sha256: apkSigning.executable_sha256,
      verification_output_sha256: `sha256:${createHash("sha256").update(signingOutput).digest("hex")}`,
      signer_count: signerIds.size,
      verified: true,
    },
  };
}

export function validateNativeBinding(binding) {
  assertPlainObject(binding, "E_NATIVE_BINDING_INVALID", "$", "native binding must be an object");
  assertSecretFree(binding);
  if (binding.schema_version !== "native-mcp-binding-v1") throw new ContractError("E_NATIVE_BINDING_VERSION", "binding must be native-mcp-binding-v1", "$.schema_version");
  requireNonEmptyString(binding.binding_id, "E_NATIVE_BINDING_ID", "$.binding_id", "binding_id is required");
  for (const field of ["name", "version", "protocol_version", "transport", "executable_sha256", "contract_version"]) {
    requireNonEmptyString(binding.server?.[field], "E_NATIVE_SERVER_FIELD", `$.server.${field}`, `${field} is required`);
  }
  if (binding.server.transport !== "stdio" || !HASH.test(binding.server.executable_sha256)) throw new ContractError("E_NATIVE_SERVER_INVALID", "server must use stdio with an executable SHA-256", "$.server");
  const runtimeSource = binding.server.runtime_source;
  if (runtimeSource?.kind !== "directory_tree" || !path.isAbsolute(runtimeSource?.root_path ?? "") || runtimeSource.root_path === path.parse(runtimeSource.root_path).root || !HASH.test(runtimeSource?.source_tree_sha256)) {
    throw new ContractError("E_MCP_RUNTIME_SOURCE_INVALID", "server.runtime_source must bind an absolute non-root directory tree and SHA-256", "$.server.runtime_source");
  }
  for (const field of ["file_count", "total_bytes"]) {
    if (!Number.isSafeInteger(runtimeSource[field]) || runtimeSource[field] < 1) throw new ContractError("E_MCP_RUNTIME_SOURCE_INVALID", `${field} must be a positive safe integer`, `$.server.runtime_source.${field}`);
  }
  const launch = binding.server.launch;
  if (!path.isAbsolute(launch?.executable_path ?? "") || !Array.isArray(launch?.arguments) || launch.arguments.some((item) => typeof item !== "string")) {
    throw new ContractError("E_NATIVE_SERVER_LAUNCH_INVALID", "server.launch requires an absolute executable_path and string arguments", "$.server.launch");
  }
  if (launch.working_directory !== undefined && !path.isAbsolute(launch.working_directory)) throw new ContractError("E_NATIVE_SERVER_LAUNCH_INVALID", "working_directory must be absolute", "$.server.launch.working_directory");
  if (!HASH.test(binding.capabilities?.tools_list_sha256) || !HASH.test(binding.capabilities?.native_scenario_schema_sha256)) throw new ContractError("E_NATIVE_CAPABILITY_HASH_INVALID", "capability hashes must be SHA-256 values", "$.capabilities");
  if (!Array.isArray(binding.capabilities.required_tools) || REQUIRED_TOOLS.some((name) => !binding.capabilities.required_tools.includes(name))) throw new ContractError("E_NATIVE_REQUIRED_TOOLS_MISSING", "binding must require every P3 MCP tool", "$.capabilities.required_tools");
  if (!path.isAbsolute(binding.artifact?.local_path ?? "") || !HASH.test(binding.artifact?.expected_sha256) || binding.artifact?.type !== "apk") throw new ContractError("E_ANDROID_APK_REQUIRED", "binding artifact must be an absolute APK with expected SHA-256", "$.artifact");
  const java = binding.readiness?.java;
  const apkSigning = binding.readiness?.apk_verifier;
  if (!path.isAbsolute(java?.home_path ?? "") || !path.isAbsolute(java?.executable_path ?? "") || path.dirname(java.executable_path) !== path.join(java.home_path, "bin") || !HASH.test(java?.executable_sha256)) {
    throw new ContractError("E_JAVA_READINESS_BINDING_INVALID", "readiness.java must bind an absolute JAVA_HOME, its bin/java executable, and SHA-256", "$.readiness.java");
  }
  if (apkSigning?.verifier !== "apksigner" || !path.isAbsolute(apkSigning?.executable_path ?? "") || !HASH.test(apkSigning?.executable_sha256)) {
    throw new ContractError("E_APK_SIGNING_BINDING_INVALID", "readiness.apk_verifier must bind the apksigner executable and SHA-256", "$.readiness.apk_verifier");
  }
  if (typeof binding.package_id !== "string" || !/^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+$/.test(binding.package_id)) throw new ContractError("E_ANDROID_PACKAGE_INVALID", "package_id must be an Android application ID", "$.package_id");
  if (binding.device?.runtime !== "emulator" || (binding.device.udid !== undefined && !binding.device.udid.startsWith("emulator-")) || (!binding.device.avd && !binding.device.udid)) throw new ContractError("E_ANDROID_EMULATOR_REQUIRED", "device must identify an Android Emulator by AVD or emulator serial", "$.device");
  if (!["portrait", "landscape"].includes(binding.device.orientation) || !["clean", "preserve"].includes(binding.device.reset_policy)) throw new ContractError("E_ANDROID_DEVICE_INVALID", "orientation and reset_policy are invalid", "$.device");
  const appiumUrl = new URL(binding.appium?.server_url ?? "invalid:");
  if (appiumUrl.protocol !== "http:" || !["127.0.0.1", "localhost", "::1"].includes(appiumUrl.hostname) || appiumUrl.username || appiumUrl.password || binding.appium?.driver !== "uiautomator2") {
    throw new ContractError("E_APPIUM_LOCAL_REQUIRED", "Appium must use credential-free local HTTP and UiAutomator2", "$.appium");
  }
  requireInteger(binding.execution?.max_duration_seconds, 10, 180, "E_NATIVE_DURATION_INVALID", "$.execution.max_duration_seconds", "max duration must be 10..180 seconds");
  requireInteger(binding.execution?.poll_interval_ms ?? 500, 50, 5_000, "E_NATIVE_POLL_INVALID", "$.execution.poll_interval_ms", "poll interval must be 50..5000 ms");
  requireInteger(binding.execution?.request_timeout_ms ?? 30_000, 1_000, 120_000, "E_NATIVE_REQUEST_TIMEOUT_INVALID", "$.execution.request_timeout_ms", "request timeout must be 1000..120000 ms");
  return binding;
}

function validateRequest(request, runbook, binding, preflightOnly) {
  assertPlainObject(request, "E_RUNNER_REQUEST_INVALID", "$", "runner request must be an object");
  assertPlainObject(runbook, "E_RUNBOOK_INVALID", "$", "runbook must be an object");
  assertSecretFree(request);
  assertSecretFree(runbook);
  if (request.schema_version !== "runner-request-v1" || runbook.schema_version !== "runbook-v1") throw new ContractError("E_SCHEMA_VERSION", "request and runbook versions are invalid");
  if (request.runner_provider !== "native-android" || runbook.runner_provider !== "native-android") throw new ContractError("E_ANDROID_PROVIDER_REQUIRED", "native-android provider is required");
  if (runbook.target?.platform !== "android" || runbook.target?.device !== "emulator" || runbook.target?.artifact_type !== "apk") throw new ContractError("E_ANDROID_TARGET_UNSUPPORTED", "Android Emulator and APK are required", "$.target");
  if (runbook.review_status !== "approved" || runbook.execution?.enabled !== true) throw new ContractError("E_RUNBOOK_NOT_EXECUTABLE", "runbook must be approved and enabled");
  if (preflightOnly && (runbook.runbook_state !== "preflight" || runbook.approval_ref !== null)) throw new ContractError("E_RUNBOOK_PREFLIGHT_STATE_INVALID", "preflight-only requires runbook_state=preflight and approval_ref=null", "$.runbook_state");
  if (!preflightOnly && runbook.runbook_state !== "executable") throw new ContractError("E_RUNBOOK_EXECUTABLE_STATE_REQUIRED", "Android execution requires runbook_state=executable", "$.runbook_state");
  if (runbook.steps.some((step) => step.max_attempts !== 1)) throw new ContractError("E_NATIVE_RETRY_UNSUPPORTED", "external Native Scenario V1 requires max_attempts=1 for every step");
  const exact = [["runbook_id", runbook.runbook_id], ["plan_sha256", runbook.integrity?.plan_sha256], ["project_config_sha256", runbook.project_config_sha256]];
  for (const [field, expected] of exact) if (request[field] !== expected) throw new ContractError("E_REQUEST_RUNBOOK_MISMATCH", `${field} does not match runbook`, `$.${field}`);
  if (request.runbook_sha256 !== sha256Json(runbook) || runbook.integrity?.plan_sha256 !== runbookPlanHash(runbook)) throw new ContractError("E_RUNBOOK_HASH_MISMATCH", "runbook or plan hash does not match");
  if (sha256Json(request.target) !== sha256Json(runbook.target)) throw new ContractError("E_REQUEST_TARGET_MISMATCH", "request target must equal runbook target");
  if (request.runtime_binding?.binding_id !== binding.binding_id || request.runtime_binding?.sha256 !== sha256Json(binding)) throw new ContractError("E_RUNTIME_BINDING_MISMATCH", "request runtime binding does not match exact binding");
  if (request.artifact?.type !== "apk" || request.artifact?.sha256 !== binding.artifact.expected_sha256) throw new ContractError("E_REQUEST_ARTIFACT_MISMATCH", "request artifact must match binding APK");
  if (!preflightOnly) {
    const mutationIds = runbook.steps.filter((step) => step.mutation !== "none").map((step) => step.id);
    const approval = runbook.approval_ref;
    if (!approval || !HASH.test(approval.record_sha256) || approval.plan_sha256 !== runbook.integrity.plan_sha256 || !HASH.test(approval.provider_plan_hash) || !HASH.test(approval.runtime_binding_sha256) || approval.runtime_binding_sha256 !== request.runtime_binding.sha256 || JSON.stringify(approval.approved_step_ids) !== JSON.stringify(mutationIds) || approval.environment !== runbook.fixture.environment) {
      throw new ContractError("E_APPROVAL_INVALID", "Android execution approval does not match the frozen runbook");
    }
    if (approval.expires_at !== null && Date.parse(approval.expires_at) <= Date.now()) throw new ContractError("E_APPROVAL_EXPIRED", "Android execution approval has expired");
  }
  if (runbook.fixture?.destructive === true && runbook.fixture.environment !== "isolated") throw new ContractError("E_FIXTURE_ISOLATION_REQUIRED", "destructive fixture must be isolated");
}

function toNativeScenario(runbook, binding, artifactId) {
  const device = Object.fromEntries(Object.entries(binding.device).filter(([key]) => key !== "reset_policy"));
  return {
    schema_version: 1,
    title: runbook.scenario_id,
    platform: "android",
    app_artifact_id: artifactId,
    package_id: binding.package_id,
    device,
    reset_policy: binding.device.reset_policy,
    max_duration_seconds: binding.execution.max_duration_seconds,
    steps: runbook.steps.map((step) => {
      const action = step.action === "launch"
        ? { type: "launch" }
        : { type: "wait_for", target: cloneJson(step.provider_args.locator), state: step.provider_args.state };
      return {
        id: step.id,
        title: step.description,
        action,
        effects: step.mutation === "none" ? ["local_read"] : ["potential_mutation"],
        approval: step.mutation === "none" ? "none" : "required",
        retry_policy: step.retry_policy,
        timeout_ms: step.timeout_ms,
        hold_ms: step.provider_args.hold_ms,
      };
    }),
  };
}

function evidenceItem(id, kind, record, timestamp) {
  return { id, kind, collected_at: timestamp, producer: { type: "adapter", name: "native-mcp-adapter", version: ADAPTER_VERSION }, sha256: sha256Json(record), redactions: [], record };
}

function normalizeUtcTimestamp(value, fallback, contractPath) {
  const candidate = typeof value === "string" ? value : fallback;
  const parsed = Date.parse(candidate);
  if (Number.isNaN(parsed)) throw new ContractError("E_PROVIDER_TIMESTAMP_INVALID", "provider timestamp is invalid", contractPath);
  return new Date(parsed).toISOString();
}

function nativeRuntimeSubject(binding, runtime) {
  return {
    device_type: "emulator",
    device_id: binding.device.udid ?? runtime.connected_devices?.[0] ?? null,
    avd: binding.device.avd ?? null,
    device_name: binding.device.device_name ?? null,
    os_version: binding.device.platform_version ?? null,
    orientation: binding.device.orientation,
    language: binding.device.language ?? null,
    locale: binding.device.locale ?? null,
    reset_policy: binding.device.reset_policy,
    appium_version: runtime.appium_version ?? null,
    automation_driver: "uiautomator2",
    automation_driver_version: runtime.uiautomator2_version ?? null,
  };
}

function notStartedOutput(request, runbook, binding, error, startedAt, unsupportedReason = null) {
  const command = { phase: "preflight", adapter_version: ADAPTER_VERSION, error_code: error.code, runbook_id: runbook.runbook_id };
  const output = {
    schema_version: "runner-output-v1", run_id: request.run_id, runbook_id: runbook.runbook_id,
    runbook_hash: sha256Json(runbook), plan_sha256: runbook.integrity?.plan_sha256 ?? `sha256:${"0".repeat(64)}`,
    scenario_id: runbook.scenario_id, spec_version: runbook.spec_version, scenario_hash: runbook.scenario_hash,
    target: cloneJson(runbook.target ?? request.target), runner_provider: "native-android", provider_binding: cloneJson(runbook.provider_binding ?? {}),
    project_config_sha256: runbook.project_config_sha256, started_at: startedAt, finished_at: new Date().toISOString(),
    execution: { status: "not_started", attempt: request.attempt ?? 0, retry_count: 0, command_evidence_ref: "runner-command", runner_version: ADAPTER_VERSION },
    subject: { build: null, artifact: null, native_runtime: null },
    step_results: (runbook.steps ?? []).map((step) => ({ step_id: step.id, status: "not_started", attempt_count: 0, started_at: null, finished_at: null, evidence_refs: [], error: null })),
    evidence: [evidenceItem("runner-command", "test_command", command, startedAt)],
    errors: [{ code: error.code, category: unsupportedReason ? "unsupported" : "contract", message: error.message, step_id: null, evidence_refs: ["runner-command"], retryable: false }],
    unsupported_reason: unsupportedReason,
    missing_evidence: (runbook.evidence_plan ?? []).map((plan) => ({ oracle_rule_id: plan.oracle_rule_id, evidence_kind: plan.evidence_kind, reason: error.code })), diagnostic_attachments: [],
  };
  return validateAndroidOutput(output);
}

function unwrapJob(value) {
  assertPlainObject(value, "E_MCP_JOB_INVALID", "$", "MCP job payload must be an object");
  requireNonEmptyString(value.job_id, "E_MCP_JOB_INVALID", "$.job_id", "job_id is required");
  requireNonEmptyString(value.plan_hash, "E_MCP_JOB_INVALID", "$.plan_hash", "plan_hash is required");
  return value;
}

async function discoverAndVerify(client, binding) {
  const initialized = await client.initialize(binding.server.protocol_version);
  if (initialized?.protocolVersion !== binding.server.protocol_version || initialized?.serverInfo?.name !== binding.server.name || initialized?.serverInfo?.version !== binding.server.version) {
    throw new ContractError("E_MCP_SERVER_IDENTITY_MISMATCH", "MCP initialize identity differs from binding");
  }
  const listed = await client.listTools();
  const tools = listed?.tools;
  const names = new Set(Array.isArray(tools) ? tools.map((tool) => tool.name) : []);
  if (REQUIRED_TOOLS.some((name) => !names.has(name)) || sha256Json(toolsListProjection(tools)) !== binding.capabilities.tools_list_sha256) throw new ContractError("E_MCP_TOOLS_MISMATCH", "MCP tool surface differs from binding");
  const schemaPayload = await client.callTool("get_native_video_scenario_schema", {});
  if (!schemaPayload.schema || sha256Json(schemaPayload.schema) !== binding.capabilities.native_scenario_schema_sha256) throw new ContractError("E_MCP_SCHEMA_MISMATCH", "Native Scenario schema differs from binding");
}

async function lifecycle({ client, request, runbook, binding, preflightOnly, readiness }) {
  await discoverAndVerify(client, binding);
  const artifactMeta = await assertApk(binding.artifact.local_path, binding.artifact.expected_sha256);
  const registered = await client.callTool("register_native_app", { platform: "android", path: binding.artifact.local_path });
  const artifact = registered?.artifact;
  if (!artifact || artifact.format !== "apk" || artifact.platform !== "android" || `sha256:${String(artifact.sha256).replace(/^sha256:/, "")}` !== artifactMeta.sha256) throw new ContractError("E_MCP_ARTIFACT_MISMATCH", "registered artifact differs from local APK");
  const device = Object.fromEntries(Object.entries(binding.device).filter(([key]) => key !== "reset_policy"));
  const runtime = await client.callTool("get_native_runtime_status", { device });
  if (runtime.backend !== "native-android" || runtime.ready !== true) throw new ContractError("E_NATIVE_RUNTIME_NOT_READY", "external Android runtime is not ready");
  if (runtime.appium_server_url && runtime.appium_server_url !== binding.appium.server_url) throw new ContractError("E_APPIUM_BINDING_MISMATCH", "runtime Appium URL differs from binding");
  if (binding.device.udid && Array.isArray(runtime.connected_devices) && !runtime.connected_devices.includes(binding.device.udid)) throw new ContractError("E_ANDROID_EMULATOR_MISMATCH", "selected Emulator is not connected");
  const nativeScenario = toNativeScenario(runbook, binding, artifact.artifact_id);
  const created = unwrapJob(await client.callTool("create_native_video_job", { scenario: nativeScenario }));
  const preflightPayload = await client.callTool("preflight_video_job", { job_id: created.job_id });
  const preflight = preflightPayload?.preflight;
  const job = preflightPayload?.job;
  if (!preflight || preflight.passed !== true || preflight.backend !== "native-android" || preflight.plan_hash !== created.plan_hash || job?.plan_hash !== created.plan_hash) throw new ContractError("E_NATIVE_PREFLIGHT_FAILED", "external provider preflight did not pass");
  const mutationIds = preflight.mutations?.map((item) => item.step_id) ?? [];
  const expectedMutations = runbook.steps.filter((step) => step.mutation !== "none").map((step) => step.id);
  if (JSON.stringify(mutationIds) !== JSON.stringify(expectedMutations)) throw new ContractError("E_PROVIDER_MUTATION_SCOPE_MISMATCH", "provider mutation scope differs from runbook");
  if (preflightOnly) {
    return {
      schema_version: "native-mcp-preflight-v1", runbook_id: runbook.runbook_id, runbook_plan_sha256: runbook.integrity.plan_sha256,
      runtime_binding_sha256: sha256Json(binding), job_id: created.job_id, provider_plan_hash: normalizeProviderPlanHash(created.plan_hash),
      approved_step_ids: mutationIds, environment: runbook.fixture.environment, artifact: { id: artifact.artifact_id, type: "apk", sha256: artifactMeta.sha256 },
      runtime: nativeRuntimeSubject(binding, runtime), readiness, passed: true, requires_approval: preflight.requires_approval === true, errors: [],
    };
  }
  if (runbook.approval_ref.provider_plan_hash !== normalizeProviderPlanHash(created.plan_hash)) throw new ContractError("E_PROVIDER_PLAN_APPROVAL_MISMATCH", "approval provider plan hash differs from preflight");
  await client.callTool("approve_video_job", { job_id: created.job_id, plan_hash: created.plan_hash, approved_step_ids: mutationIds, confirm_external_changes: true });
  await client.callTool("start_video_job", { job_id: created.job_id, plan_hash: created.plan_hash });
  const deadline = Date.now() + binding.execution.max_duration_seconds * 1000 + 30_000;
  let terminal;
  while (Date.now() < deadline) {
    const polled = await client.callTool("get_video_job", { job_id: created.job_id });
    if (TERMINAL_STATES.has(polled.state)) { terminal = polled; break; }
    await new Promise((resolve) => setTimeout(resolve, binding.execution.poll_interval_ms ?? 500));
  }
  if (!terminal) throw new ContractError("E_NATIVE_JOB_TIMEOUT", "external Android job did not reach a terminal state");
  return buildOutput({ request, runbook, binding, artifact, artifactMeta, runtime, readiness, terminal });
}

function buildOutput({ request, runbook, binding, artifact, artifactMeta, runtime, readiness, terminal }) {
  const fallbackTimestamp = new Date().toISOString();
  const startedAt = normalizeUtcTimestamp(terminal.manifest?.started_at, fallbackTimestamp, "$.manifest.started_at");
  const timestamp = normalizeUtcTimestamp(terminal.manifest?.finished_at, fallbackTimestamp, "$.manifest.finished_at");
  const evidence = [];
  evidence.push(evidenceItem("runner-command", "test_command", { adapter_version: ADAPTER_VERSION, backend: "native-android", runbook_id: runbook.runbook_id, attempt: request.attempt }, startedAt));
  evidence.push(evidenceItem("registered-apk", "artifact_hash", { artifact_id: artifact.artifact_id, sha256: artifactMeta.sha256, size_bytes: artifactMeta.size_bytes }, startedAt));
  evidence.push(evidenceItem("android-readiness", "structured_log", readiness, startedAt));
  if (request.build) evidence.push(evidenceItem("runner-build", "build_hash", cloneJson(request.build), startedAt));
  const manifestSteps = new Map((terminal.manifest?.steps ?? []).map((step) => [step.step_id, step]));
  const stepResults = [];
  const errors = [];
  const missingEvidence = [];
  for (const step of runbook.steps) {
    const observed = manifestSteps.get(step.id);
    const refs = [];
    if (observed) {
      const observedStartedAt = observed.started_at === null || observed.started_at === undefined
        ? null
        : normalizeUtcTimestamp(observed.started_at, fallbackTimestamp, `$.manifest.steps.${step.id}.started_at`);
      const observedFinishedAt = observed.finished_at === null || observed.finished_at === undefined
        ? null
        : normalizeUtcTimestamp(observed.finished_at, fallbackTimestamp, `$.manifest.steps.${step.id}.finished_at`);
      const logId = `step-${step.id}-log`;
      evidence.push(evidenceItem(logId, "structured_log", { step_id: step.id, state: observed.state, started_at: observedStartedAt, finished_at: observedFinishedAt, error_present: Boolean(observed.error) }, timestamp));
      refs.push(logId);
      if (step.action === "wait_for") {
        const locatorId = `step-${step.id}-locator`;
        evidence.push(evidenceItem(locatorId, "locator_result", { locator: cloneJson(step.provider_args.locator), expected_state: step.provider_args.state, outcome: observed.state === "passed" ? "matched" : "not_matched" }, timestamp));
        refs.push(locatorId);
      }
    }
    const status = !observed ? "not_started" : observed.state === "passed" ? "completed" : "error";
    const error = status === "error" ? { code: "E_NATIVE_STEP_FAILED", category: "product", message: "Android native step failed", step_id: step.id, evidence_refs: refs, retryable: false } : null;
    if (error) errors.push(error);
    stepResults.push({
      step_id: step.id,
      status,
      attempt_count: observed ? 1 : 0,
      started_at: observed?.started_at === null || observed?.started_at === undefined ? null : normalizeUtcTimestamp(observed.started_at, fallbackTimestamp, `$.manifest.steps.${step.id}.started_at`),
      finished_at: observed?.finished_at === null || observed?.finished_at === undefined ? null : normalizeUtcTimestamp(observed.finished_at, fallbackTimestamp, `$.manifest.steps.${step.id}.finished_at`),
      evidence_refs: refs,
      error,
    });
  }
  for (const plan of runbook.evidence_plan) {
    const step = stepResults.find((item) => item.step_id === plan.after_step_id);
    if (!step || !step.evidence_refs.some((id) => evidence.find((item) => item.id === id)?.kind === plan.evidence_kind)) missingEvidence.push({ oracle_rule_id: plan.oracle_rule_id, evidence_kind: plan.evidence_kind, reason: "E_PROVIDER_EVIDENCE_UNAVAILABLE" });
  }
  const succeeded = terminal.state === "SUCCEEDED" && terminal.manifest?.state === "SUCCEEDED";
  if (!succeeded) {
    const providerRecord = {
      provider_state: terminal.state,
      manifest_state: terminal.manifest?.state ?? null,
      external_effect_state: terminal.manifest?.external_effect_state ?? null,
      review_required: terminal.manifest?.review_required === true,
      error_present: Boolean(terminal.manifest?.error),
    };
    evidence.push(evidenceItem("provider-terminal-state", "structured_log", providerRecord, timestamp));
    errors.push({
      code: "E_NATIVE_JOB_FAILED",
      category: "environment",
      message: "External Android provider did not complete successfully",
      step_id: null,
      evidence_refs: ["provider-terminal-state"],
      retryable: false,
    });
  }
  const output = {
    schema_version: "runner-output-v1", run_id: request.run_id, runbook_id: runbook.runbook_id, runbook_hash: request.runbook_sha256,
    plan_sha256: runbook.integrity.plan_sha256, scenario_id: runbook.scenario_id, spec_version: runbook.spec_version, scenario_hash: runbook.scenario_hash,
    target: cloneJson(runbook.target), runner_provider: "native-android", provider_binding: cloneJson(runbook.provider_binding), project_config_sha256: runbook.project_config_sha256,
    started_at: startedAt, finished_at: timestamp,
    execution: { status: succeeded ? "completed" : "partial", attempt: request.attempt, retry_count: 0, command_evidence_ref: "runner-command", runner_version: ADAPTER_VERSION },
    subject: { build: cloneJson(request.build), artifact: { id: artifact.artifact_id, type: "apk", sha256: artifactMeta.sha256, package_id: binding.package_id }, native_runtime: nativeRuntimeSubject(binding, runtime) },
    step_results: stepResults, evidence, errors, unsupported_reason: null, missing_evidence: missingEvidence, diagnostic_attachments: [],
  };
  return validateAndroidOutput(output);
}

export function validateAndroidOutput(output) {
  assertPlainObject(output, "E_RUNNER_OUTPUT_INVALID", "$", "runner output must be an object");
  if (output.schema_version !== "runner-output-v1" || "verdict" in output || "oracle_results" in output) throw new ContractError("E_RUNNER_SELF_JUDGMENT_FORBIDDEN", "Android runner output must not contain verdict or oracle_results");
  for (const field of ["step_results", "evidence", "errors", "missing_evidence", "diagnostic_attachments"]) if (!Array.isArray(output[field])) throw new ContractError("E_RUNNER_OUTPUT_FIELD", `${field} must be an array`, `$.${field}`);
  const ids = new Set();
  for (const item of output.evidence) {
    if (ids.has(item.id)) throw new ContractError("E_EVIDENCE_ID_DUPLICATE", "evidence IDs must be unique");
    ids.add(item.id);
    if (item.sha256 !== sha256Json(item.record)) throw new ContractError("E_EVIDENCE_HASH_MISMATCH", "evidence hash does not match record");
    if (item.producer?.type !== "adapter" || item.producer?.name !== "native-mcp-adapter") throw new ContractError("E_EVIDENCE_PRODUCER_INVALID", "Android evidence must identify the external adapter");
  }
  if (!ids.has(output.execution?.command_evidence_ref)) throw new ContractError("E_COMMAND_EVIDENCE_REQUIRED", "command evidence reference must resolve");
  assertSecretFree(output);
  return output;
}

export async function runAndroidMcp({ request, runbook, binding, preflightOnly = false, clientFactory = null }) {
  const startedAt = new Date().toISOString();
  if (runbook?.target?.platform !== "android" || runbook?.target?.device !== "emulator" || runbook?.target?.artifact_type !== "apk") {
    const error = new ContractError("E_ANDROID_CAPABILITY_UNSUPPORTED", "native adapter supports Android Emulator APK only");
    return notStartedOutput(request, runbook, binding, error, startedAt, "native-android supports Emulator and APK only");
  }
  let client;
  try {
    validateNativeBinding(binding);
    validateRequest(request, runbook, binding, preflightOnly);
    if (await hashFile(binding.server.launch.executable_path) !== binding.server.executable_sha256) throw new ContractError("E_MCP_EXECUTABLE_HASH_MISMATCH", "MCP executable hash differs from binding");
    const runtimeSource = await hashRuntimeSourceTree(binding.server.runtime_source.root_path);
    if (runtimeSource.source_tree_sha256 !== binding.server.runtime_source.source_tree_sha256
      || runtimeSource.file_count !== binding.server.runtime_source.file_count
      || runtimeSource.total_bytes !== binding.server.runtime_source.total_bytes) {
      throw new ContractError("E_MCP_RUNTIME_HASH_MISMATCH", "MCP runtime source tree differs from binding", "$.server.runtime_source");
    }
    const readiness = await verifyAndroidReadiness(binding);
    client = clientFactory ? await clientFactory() : new StdioMcpClient({
      executablePath: binding.server.launch.executable_path, arguments: binding.server.launch.arguments,
      workingDirectory: binding.server.launch.working_directory, timeoutMs: binding.execution.request_timeout_ms ?? 30_000,
    });
    await client.start?.();
    return await lifecycle({ client, request, runbook, binding, preflightOnly, readiness });
  } catch (error) {
    if (!(error instanceof ContractError)) throw error;
    if (preflightOnly) return { schema_version: "native-mcp-preflight-v1", runbook_id: runbook.runbook_id, runbook_plan_sha256: runbook.integrity?.plan_sha256, runtime_binding_sha256: sha256Json(binding), job_id: null, provider_plan_hash: null, approved_step_ids: [], environment: runbook.fixture?.environment ?? null, artifact: null, runtime: null, readiness: null, passed: false, requires_approval: true, errors: [error.toJSON()] };
    return notStartedOutput(request, runbook, binding, error, startedAt);
  } finally {
    await client?.close?.();
  }
}

async function main() {
  const options = parseCli(process.argv.slice(2), {
    "--request": { name: "request", required: true }, "--runbook": { name: "runbook", required: true },
    "--binding": { name: "binding", required: true }, "--output": { name: "output", required: true },
    "--preflight-only": { name: "preflight_only", boolean: true },
  });
  const output = await runAndroidMcp({ request: await readJson(options.request), runbook: await readJson(options.runbook), binding: await readJson(options.binding), preflightOnly: options.preflight_only === true });
  await writeJson(options.output, output);
  process.stdout.write(`${JSON.stringify({ valid: output.passed !== false, output: options.output, schema_version: output.schema_version })}\n`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => { printContractError(error); process.exitCode = 1; });
}
