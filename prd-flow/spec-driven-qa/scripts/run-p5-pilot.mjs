#!/usr/bin/env node

import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

import { compileAndroidRunbook } from "./compile-android-runbook.mjs";
import { compileMarkdownSpec } from "./compile-markdown-spec.mjs";
import { compileWebRunbook } from "./compile-web-runbook.mjs";
import { enrichAndroidRuntimeFromAppiumLog } from "./enrich-android-runtime.mjs";
import { judgeRunnerOutput } from "./judge-results.mjs";
import { runAndroidMcp } from "./run-android-mcp.mjs";
import { runWebPlaywright } from "./run-web-playwright.mjs";
import {
  ContractError,
  parseCli,
  printContractError,
  readJson,
  sha256Bytes,
  sha256Json,
  writeJson,
} from "./web-provider-lib.mjs";

const EXAMPLES_ROOT = path.resolve(import.meta.dirname, "../examples/p5");

async function loadInputs(name) {
  const root = path.join(EXAMPLES_ROOT, name);
  const bundle = compileMarkdownSpec({ markdown: await readFile(path.join(root, "spec.md"), "utf8"), originRef: "spec.md" });
  return {
    bundle,
    scenario: await readJson(path.join(root, "scenario.json")),
    config: await readJson(path.join(root, name === "web" ? "playwright-config.json" : "android-config.json")),
  };
}

function runnerRequest({ runId, runbook, build, artifact = null, binding = null }) {
  return {
    schema_version: "runner-request-v1",
    run_id: runId,
    requested_at: new Date().toISOString(),
    attempt: 1,
    runbook_id: runbook.runbook_id,
    runbook_ref: `runbooks/${runbook.runbook_id}.json`,
    runbook_sha256: sha256Json(runbook),
    plan_sha256: runbook.integrity.plan_sha256,
    runner_provider: runbook.runner_provider,
    target: runbook.target,
    project_config_sha256: runbook.project_config_sha256,
    runtime_binding: binding ? { binding_id: binding.binding_id, sha256: sha256Json(binding) } : null,
    build,
    artifact,
  };
}

async function writeArtifacts(outputDir, artifacts) {
  await mkdir(outputDir, { recursive: true });
  for (const [name, value] of Object.entries(artifacts)) await writeJson(path.join(outputDir, `${name}.json`), value);
}

async function publicBuild(config) {
  const targetUrl = new URL(config.routes.home, config.origin).toString();
  const response = await fetch(targetUrl, { redirect: "follow", signal: AbortSignal.timeout(30_000) });
  if (!response.ok) throw new ContractError("E_P5_PUBLIC_BUILD_UNAVAILABLE", `public sample returned HTTP ${response.status}`);
  const body = Buffer.from(await response.arrayBuffer());
  return { ref: targetUrl, sha256: sha256Bytes(body) };
}

export async function runWebPilot({ outputDir, playwrightModuleRoot }) {
  const { bundle, scenario, config } = await loadInputs("web");
  const runbook = compileWebRunbook({ scenario, config });
  const request = runnerRequest({ runId: "p5-public-todomvc-web", runbook, build: await publicBuild(config) });
  const runnerOutput = await runWebPlaywright({ request, runbook, playwrightModuleRoot });
  const result = judgeRunnerOutput({ bundle, scenario, runbook, runnerOutput });
  const report = {
    schema_version: "p5-pilot-report-v1",
    pilot: "public-web",
    independent_of: ["company-source-adapter", "notion", "company-plugin"],
    target: scenario.target,
    runbook_sha256: sha256Json(runbook),
    runner_output_sha256: sha256Json(runnerOutput),
    result_sha256: sha256Json(result),
    execution_status: runnerOutput.execution.status,
    verdict: result.verdict,
  };
  await writeArtifacts(outputDir, { "spec-bundle": bundle, scenario, runbook, "runner-request": request, "runner-output": runnerOutput, result, report });
  if (result.verdict !== "pass") throw new ContractError("E_P5_WEB_PILOT_FAILED", `public web pilot verdict was ${result.verdict}`, "$", { output_dir: outputDir });
  return report;
}

export async function runAndroidPilot({ mode, outputDir, binding, approval = null, appiumLogPath = null }) {
  const { bundle, scenario, config } = await loadInputs("android");
  const preflightOnly = mode === "android-preflight";
  const runbook = compileAndroidRunbook({ scenario, config, approval, allowUnapprovedPreflight: preflightOnly });
  const request = runnerRequest({
    runId: preflightOnly ? "p5-api-demos-android-preflight" : "p5-api-demos-android-run",
    runbook,
    binding,
    build: { ref: "appium/android-apidemos@v6.0.10", sha256: binding.artifact.expected_sha256 },
    artifact: { id: "appium-api-demos-v6.0.10", type: "apk", sha256: binding.artifact.expected_sha256 },
  });
  const artifacts = { "spec-bundle": bundle, scenario, runbook, "runner-request": request };
  await writeArtifacts(outputDir, artifacts);
  let providerOutput = await runAndroidMcp({ request, runbook, binding, preflightOnly });
  if (!preflightOnly && providerOutput.execution.status === "completed") {
    if (!appiumLogPath) throw new ContractError("E_APPIUM_LOG_REQUIRED", "completed Android pilot requires --appium-log runtime evidence");
    providerOutput = enrichAndroidRuntimeFromAppiumLog({ runnerOutput: providerOutput, appiumLog: await readFile(appiumLogPath, "utf8") });
  }
  let report;
  if (preflightOnly) {
    artifacts.preflight = providerOutput;
    await writeArtifacts(outputDir, { preflight: providerOutput });
    report = {
      schema_version: "p5-pilot-report-v1",
      pilot: "public-android-preflight",
      independent_of: ["company-source-adapter", "notion", "company-plugin"],
      target: scenario.target,
      runbook_sha256: sha256Json(runbook),
      provider_plan_hash: providerOutput.provider_plan_hash,
      runtime_binding_sha256: providerOutput.runtime_binding_sha256,
      approved_step_ids: providerOutput.approved_step_ids,
      passed: providerOutput.passed,
      requires_approval: providerOutput.requires_approval,
    };
  } else {
    artifacts["runner-output"] = providerOutput;
    await writeArtifacts(outputDir, { "runner-output": providerOutput });
    const result = judgeRunnerOutput({ bundle, scenario, runbook, runnerOutput: providerOutput });
    artifacts.result = result;
    report = {
      schema_version: "p5-pilot-report-v1",
      pilot: "public-android",
      independent_of: ["company-source-adapter", "notion", "company-plugin"],
      target: scenario.target,
      runbook_sha256: sha256Json(runbook),
      runner_output_sha256: sha256Json(providerOutput),
      result_sha256: sha256Json(result),
      execution_status: providerOutput.execution.status,
      verdict: result.verdict,
    };
  }
  artifacts.report = report;
  await writeArtifacts(outputDir, artifacts);
  if (preflightOnly && providerOutput.passed !== true) throw new ContractError("E_P5_ANDROID_PREFLIGHT_FAILED", "Android provider preflight failed", "$", { output_dir: outputDir });
  if (!preflightOnly && report.verdict !== "pass") throw new ContractError("E_P5_ANDROID_PILOT_FAILED", `Android pilot verdict was ${report.verdict}`, "$", { output_dir: outputDir });
  return report;
}

export async function finalizeAndroidPilot({ outputDir, appiumLogPath }) {
  const bundle = await readJson(path.join(outputDir, "spec-bundle.json"));
  const scenario = await readJson(path.join(outputDir, "scenario.json"));
  const runbook = await readJson(path.join(outputDir, "runbook.json"));
  const rawRunnerOutput = await readJson(path.join(outputDir, "runner-output.json"));
  const runnerOutput = enrichAndroidRuntimeFromAppiumLog({ runnerOutput: rawRunnerOutput, appiumLog: await readFile(appiumLogPath, "utf8") });
  const result = judgeRunnerOutput({ bundle, scenario, runbook, runnerOutput });
  const report = {
    schema_version: "p5-pilot-report-v1",
    pilot: "public-android",
    independent_of: ["company-source-adapter", "notion", "company-plugin"],
    target: scenario.target,
    runbook_sha256: sha256Json(runbook),
    runner_output_sha256: sha256Json(runnerOutput),
    result_sha256: sha256Json(result),
    execution_status: runnerOutput.execution.status,
    verdict: result.verdict,
  };
  await writeArtifacts(outputDir, { "runner-output": runnerOutput, result, report });
  if (report.verdict !== "pass") throw new ContractError("E_P5_ANDROID_PILOT_FAILED", `Android pilot verdict was ${report.verdict}`, "$", { output_dir: outputDir });
  return report;
}

async function main() {
  const options = parseCli(process.argv.slice(2), {
    "--pilot": { name: "pilot", required: true },
    "--output-dir": { name: "output_dir", required: true },
    "--playwright-module-root": { name: "playwright_module_root" },
    "--binding": { name: "binding" },
    "--approval": { name: "approval" },
    "--appium-log": { name: "appium_log" },
  });
  let report;
  if (options.pilot === "web") {
    if (!options.playwright_module_root || options.binding || options.approval || options.appium_log) throw new ContractError("E_CLI_USAGE", "web pilot requires only --playwright-module-root");
    report = await runWebPilot({ outputDir: path.resolve(options.output_dir), playwrightModuleRoot: path.resolve(options.playwright_module_root) });
  } else if (["android-preflight", "android-run"].includes(options.pilot)) {
    if (!options.binding || options.playwright_module_root || (options.pilot === "android-preflight" && (options.approval || options.appium_log)) || (options.pilot === "android-run" && (!options.approval || !options.appium_log))) {
      throw new ContractError("E_CLI_USAGE", "Android preflight requires --binding; Android run also requires --approval and --appium-log");
    }
    report = await runAndroidPilot({
      mode: options.pilot,
      outputDir: path.resolve(options.output_dir),
      binding: await readJson(options.binding),
      approval: options.approval ? await readJson(options.approval) : null,
      appiumLogPath: options.appium_log ? path.resolve(options.appium_log) : null,
    });
  } else if (options.pilot === "android-finalize") {
    if (options.binding || options.approval || options.playwright_module_root || !options.appium_log) throw new ContractError("E_CLI_USAGE", "Android finalize requires only --appium-log and an existing --output-dir");
    report = await finalizeAndroidPilot({ outputDir: path.resolve(options.output_dir), appiumLogPath: path.resolve(options.appium_log) });
  } else {
    throw new ContractError("E_CLI_USAGE", "--pilot must be web, android-preflight, android-run, or android-finalize");
  }
  process.stdout.write(`${JSON.stringify(report)}\n`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => { printContractError(error); process.exitCode = 1; });
}
