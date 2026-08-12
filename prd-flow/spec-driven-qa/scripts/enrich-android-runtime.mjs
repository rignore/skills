#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

import { validateAndroidOutput } from "./run-android-mcp.mjs";
import {
  ContractError,
  cloneJson,
  parseCli,
  printContractError,
  readJson,
  sha256Bytes,
  sha256Json,
  writeJson,
} from "./web-provider-lib.mjs";

function uniqueMatches(text, pattern) {
  return [...new Set([...text.matchAll(pattern)].map((match) => match[1]))];
}

function exactlyOne(values, code, message) {
  if (values.length !== 1) throw new ContractError(code, message);
  return values[0];
}

function successfulCreateTimestamp(appiumLog, runnerOutput) {
  const matches = [...appiumLog.matchAll(/^(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2}):(\d{3}).*<-- POST \/session 200\b/gm)];
  if (matches.length !== 1) throw new ContractError("E_APPIUM_SESSION_EVIDENCE_INVALID", "Appium log must contain exactly one timestamped successful session response");
  const match = matches[0];
  const observed = `${match[1]}T${match[2]}:${match[3]}:${match[4]}.${match[5]}Z`;
  const observedMs = Date.parse(observed);
  const startedMs = Date.parse(runnerOutput.started_at);
  const finishedMs = Date.parse(runnerOutput.finished_at);
  if (Number.isNaN(observedMs) || Number.isNaN(startedMs) || Number.isNaN(finishedMs) || observedMs < startedMs || observedMs > finishedMs) {
    throw new ContractError("E_APPIUM_SESSION_TIME_MISMATCH", "successful Appium session response falls outside the runner execution window");
  }
  return observed;
}

export function enrichAndroidRuntimeFromAppiumLog({ runnerOutput, appiumLog }) {
  validateAndroidOutput(runnerOutput);
  if (runnerOutput.execution?.status !== "completed") {
    throw new ContractError("E_APPIUM_RUNTIME_ENRICHMENT_STATUS", "Appium runtime enrichment requires completed Android execution", "$.execution.status");
  }
  if (typeof appiumLog !== "string" || appiumLog.length === 0) {
    throw new ContractError("E_APPIUM_LOG_REQUIRED", "Appium debug log must be non-empty");
  }
  const packageId = runnerOutput.subject?.artifact?.package_id;
  if (typeof packageId !== "string" || !appiumLog.includes(packageId)) {
    throw new ContractError("E_APPIUM_LOG_SUBJECT_MISMATCH", "Appium log does not identify the executed package", "$.subject.artifact.package_id");
  }
  const appiumCreateAt = successfulCreateTimestamp(appiumLog, runnerOutput);
  const appiumVersion = exactlyOne(
    uniqueMatches(appiumLog, /Welcome to Appium v([0-9A-Za-z.+-]+)/g),
    "E_APPIUM_VERSION_EVIDENCE_INVALID",
    "Appium log must contain exactly one observed Appium server version",
  );
  const driverVersion = exactlyOne(
    uniqueMatches(appiumLog, /creating new AndroidUiautomator2Driver \(v([0-9A-Za-z.+-]+)\) session/g),
    "E_UIAUTOMATOR2_VERSION_EVIDENCE_INVALID",
    "Appium log must contain exactly one observed UiAutomator2 driver version",
  );
  const output = cloneJson(runnerOutput);
  if (!output.subject?.native_runtime || output.subject.native_runtime.automation_driver !== "uiautomator2") {
    throw new ContractError("E_ANDROID_RUNTIME_SUBJECT_INVALID", "completed Android output must identify UiAutomator2 runtime", "$.subject.native_runtime");
  }
  const evidenceId = "android-runtime-versions";
  const sourceLogSha256 = sha256Bytes(Buffer.from(appiumLog, "utf8"));
  const existingEvidence = output.evidence.find((item) => item.id === evidenceId);
  if (existingEvidence) {
    const observedIdentity = {
      package_id: packageId,
      appium_create_status: "http_200",
      appium_create_at: appiumCreateAt,
      appium_version: appiumVersion,
      automation_driver: "uiautomator2",
      automation_driver_version: driverVersion,
    };
    if (Object.entries(observedIdentity).some(([key, value]) => existingEvidence.record?.[key] !== undefined && existingEvidence.record[key] !== value)) {
      throw new ContractError("E_RUNTIME_VERSION_EVIDENCE_MISMATCH", `${evidenceId} identifies a different Appium execution`, "$.evidence");
    }
  }
  output.evidence = output.evidence.filter((item) => item.id !== evidenceId);
  const record = {
    source_kind: "appium_debug_log",
    source_log_sha256: sourceLogSha256,
    package_id: packageId,
    appium_create_status: "http_200",
    appium_create_at: appiumCreateAt,
    appium_version: appiumVersion,
    automation_driver: "uiautomator2",
    automation_driver_version: driverVersion,
  };
  output.subject.native_runtime.appium_version = appiumVersion;
  output.subject.native_runtime.automation_driver_version = driverVersion;
  output.evidence.push({
    id: evidenceId,
    kind: "structured_log",
    collected_at: output.finished_at,
    producer: { type: "adapter", name: "native-mcp-adapter", version: output.execution.runner_version },
    sha256: sha256Json(record),
    redactions: ["appium_log_body_omitted"],
    record,
  });
  return validateAndroidOutput(output);
}

async function main() {
  const options = parseCli(process.argv.slice(2), {
    "--runner-output": { name: "runner_output", required: true },
    "--appium-log": { name: "appium_log", required: true },
    "--output": { name: "output", required: true },
  });
  const output = enrichAndroidRuntimeFromAppiumLog({
    runnerOutput: await readJson(options.runner_output),
    appiumLog: await readFile(options.appium_log, "utf8"),
  });
  await writeJson(options.output, output);
  process.stdout.write(`${JSON.stringify({ valid: true, output: options.output, runner_output_sha256: sha256Json(output) })}\n`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => { printContractError(error); process.exitCode = 1; });
}
