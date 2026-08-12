#!/usr/bin/env node

import path from "node:path";
import { pathToFileURL } from "node:url";

import { StdioMcpClient } from "./mcp-stdio-client.mjs";
import {
  hashFile,
  hashRuntimeSourceTree,
  toolsListProjection,
  validateNativeBinding,
  verifyAndroidReadiness,
} from "./run-android-mcp.mjs";
import {
  ContractError,
  parseCli,
  printContractError,
  sha256Json,
  writeJson,
} from "./web-provider-lib.mjs";

const REQUIRED_TOOLS = [
  "get_native_video_scenario_schema", "register_native_app", "get_native_runtime_status",
  "inspect_native_app", "create_native_video_job", "preflight_video_job",
  "approve_video_job", "start_video_job", "get_video_job",
];

function integerOption(value, fallback, minimum, maximum, name) {
  if (value === undefined) return fallback;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < minimum || parsed > maximum) {
    throw new ContractError("E_CLI_USAGE", `${name} must be an integer from ${minimum} to ${maximum}`);
  }
  return parsed;
}

export async function prepareNativeMcpBinding({
  executablePath,
  runtimeSourceRoot,
  apkPath,
  javaHome,
  apksignerPath,
  packageId,
  bindingId,
  avd,
  udid = undefined,
  workingDirectory = path.dirname(executablePath),
  protocolVersion = "2025-06-18",
  appiumUrl = "http://127.0.0.1:4723",
  platformVersion = undefined,
  maxDurationSeconds = 30,
  requestTimeoutMs = 30_000,
  expectedApkSha256 = undefined,
}) {
  if (![executablePath, runtimeSourceRoot, apkPath, javaHome, apksignerPath, workingDirectory].every(path.isAbsolute)) {
    throw new ContractError("E_NATIVE_PATH_ABSOLUTE", "MCP executable, runtime source root, APK, JAVA_HOME, apksigner, and working directory must be absolute paths");
  }
  const runtimeSource = await hashRuntimeSourceTree(runtimeSourceRoot);
  const apkSha256 = await hashFile(apkPath);
  if (expectedApkSha256 !== undefined && apkSha256 !== expectedApkSha256) {
    throw new ContractError("E_ARTIFACT_HASH_MISMATCH", "APK does not match --expected-apk-sha256", "$.artifact.expected_sha256", { actual_sha256: apkSha256 });
  }
  const readiness = {
    java: {
      home_path: javaHome,
      executable_path: path.join(javaHome, "bin", "java"),
      executable_sha256: await hashFile(path.join(javaHome, "bin", "java")),
    },
    apk_verifier: {
      verifier: "apksigner",
      executable_path: apksignerPath,
      executable_sha256: await hashFile(apksignerPath),
    },
  };
  await verifyAndroidReadiness({ artifact: { type: "apk", local_path: apkPath, expected_sha256: apkSha256 }, readiness });
  const client = new StdioMcpClient({ executablePath, arguments: [], workingDirectory, timeoutMs: requestTimeoutMs });
  try {
    await client.start();
    const initialized = await client.initialize(protocolVersion);
    const listed = await client.listTools();
    const schemaPayload = await client.callTool("get_native_video_scenario_schema", {});
    const listedNames = new Set(listed.tools?.map((tool) => tool.name) ?? []);
    const missingTools = REQUIRED_TOOLS.filter((name) => !listedNames.has(name));
    if (missingTools.length > 0) throw new ContractError("E_NATIVE_REQUIRED_TOOLS_MISSING", `MCP is missing required tools: ${missingTools.join(", ")}`);
    const binding = {
      schema_version: "native-mcp-binding-v1",
      binding_id: bindingId,
      server: {
        name: initialized.serverInfo?.name,
        version: initialized.serverInfo?.version,
        protocol_version: initialized.protocolVersion,
        transport: "stdio",
        executable_sha256: await hashFile(executablePath),
        runtime_source: { kind: "directory_tree", ...runtimeSource },
        contract_version: "native-scenario-v1",
        launch: { executable_path: executablePath, arguments: [], working_directory: workingDirectory },
      },
      capabilities: {
        discovered_at: new Date().toISOString(),
        tools_list_sha256: sha256Json(toolsListProjection(listed.tools)),
        native_scenario_schema_sha256: sha256Json(schemaPayload.schema),
        required_tools: [...REQUIRED_TOOLS],
      },
      artifact: { type: "apk", local_path: apkPath, expected_sha256: apkSha256 },
      readiness,
      package_id: packageId,
      device: {
        runtime: "emulator",
        ...(avd ? { avd } : {}),
        ...(udid ? { udid } : {}),
        device_name: "P5 Android Emulator",
        ...(platformVersion ? { platform_version: platformVersion } : {}),
        orientation: "portrait",
        language: "en",
        locale: "US",
        reset_policy: "clean",
      },
      appium: { server_url: appiumUrl, driver: "uiautomator2" },
      execution: { max_duration_seconds: maxDurationSeconds, poll_interval_ms: 500, request_timeout_ms: requestTimeoutMs },
    };
    validateNativeBinding(binding);
    const runtimeSourceAfterDiscovery = await hashRuntimeSourceTree(runtimeSourceRoot);
    if (runtimeSourceAfterDiscovery.source_tree_sha256 !== runtimeSource.source_tree_sha256
      || runtimeSourceAfterDiscovery.file_count !== runtimeSource.file_count
      || runtimeSourceAfterDiscovery.total_bytes !== runtimeSource.total_bytes) {
      throw new ContractError("E_MCP_RUNTIME_CHANGED_DURING_DISCOVERY", "MCP runtime source tree changed during capability discovery", "$.server.runtime_source");
    }
    return binding;
  } finally {
    await client.close();
  }
}

async function main() {
  const options = parseCli(process.argv.slice(2), {
    "--mcp-executable": { name: "mcp_executable", required: true },
    "--mcp-runtime-root": { name: "mcp_runtime_root", required: true },
    "--working-directory": { name: "working_directory" },
    "--apk": { name: "apk", required: true },
    "--java-home": { name: "java_home", required: true },
    "--apksigner": { name: "apksigner", required: true },
    "--expected-apk-sha256": { name: "expected_apk_sha256" },
    "--package-id": { name: "package_id", required: true },
    "--binding-id": { name: "binding_id", required: true },
    "--avd": { name: "avd" },
    "--udid": { name: "udid" },
    "--platform-version": { name: "platform_version" },
    "--protocol-version": { name: "protocol_version" },
    "--appium-url": { name: "appium_url" },
    "--max-duration-seconds": { name: "max_duration_seconds" },
    "--request-timeout-ms": { name: "request_timeout_ms" },
    "--output": { name: "output", required: true },
  });
  if (!options.avd && !options.udid) throw new ContractError("E_CLI_USAGE", "--avd or --udid is required");
  const binding = await prepareNativeMcpBinding({
    executablePath: path.resolve(options.mcp_executable),
    runtimeSourceRoot: path.resolve(options.mcp_runtime_root),
    workingDirectory: options.working_directory ? path.resolve(options.working_directory) : undefined,
    apkPath: path.resolve(options.apk),
    javaHome: path.resolve(options.java_home),
    apksignerPath: path.resolve(options.apksigner),
    expectedApkSha256: options.expected_apk_sha256,
    packageId: options.package_id,
    bindingId: options.binding_id,
    avd: options.avd,
    udid: options.udid,
    platformVersion: options.platform_version,
    protocolVersion: options.protocol_version,
    appiumUrl: options.appium_url,
    maxDurationSeconds: integerOption(options.max_duration_seconds, 30, 10, 180, "--max-duration-seconds"),
    requestTimeoutMs: integerOption(options.request_timeout_ms, 30_000, 1_000, 120_000, "--request-timeout-ms"),
  });
  await writeJson(options.output, binding);
  process.stdout.write(`${JSON.stringify({ valid: true, output: options.output, binding_sha256: sha256Json(binding) })}\n`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => { printContractError(error); process.exitCode = 1; });
}
