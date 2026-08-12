#!/usr/bin/env node

import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

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
  sanitizeUrl,
  selectJsonPointers,
  sha256Bytes,
  sha256Json,
  truncateText,
  writeJson,
} from "./web-provider-lib.mjs";

const RUNNER_VERSION = "1.0.0";
const SHA256_PATTERN = /^sha256:[0-9a-f]{64}$/;
const WEB_OUTPUT_EVIDENCE_KINDS = new Set([
  "dom_state", "accessibility_state", "locator_result", "url_state",
  "network_error", "console_error", "api_state", "storage_state",
  "test_command", "build_hash",
]);

async function loadPlaywright(moduleRoot) {
  try {
    return await import("playwright");
  } catch (firstError) {
    if (!moduleRoot) {
      throw new ContractError(
        "E_PLAYWRIGHT_UNAVAILABLE",
        "playwright is not installed; provide --playwright-module-root or install the project dependency",
        "$",
      );
    }
    try {
      const requireFromRoot = createRequire(path.join(path.resolve(moduleRoot), "package.json"));
      return requireFromRoot("playwright");
    } catch {
      throw new ContractError("E_PLAYWRIGHT_UNAVAILABLE", "playwright could not be loaded from the explicit module root", "$", { module_root: path.resolve(moduleRoot) });
    }
  }
}

function validateRequest(request, runbook) {
  assertPlainObject(request, "E_RUNNER_REQUEST_INVALID", "$", "runner request must be an object");
  assertPlainObject(runbook, "E_RUNBOOK_INVALID", "$", "runbook must be an object");
  assertSecretFree(request);
  assertSecretFree(runbook);
  if (request.schema_version !== "runner-request-v1") throw new ContractError("E_REQUEST_SCHEMA_VERSION", "request must be runner-request-v1", "$.schema_version");
  if (runbook.schema_version !== "runbook-v1") throw new ContractError("E_RUNBOOK_SCHEMA_VERSION", "runbook must be runbook-v1", "$.schema_version");
  requireNonEmptyString(request.run_id, "E_RUN_ID_REQUIRED", "$.run_id", "run_id is required");
  requireInteger(request.attempt, 1, 1000, "E_ATTEMPT_INVALID", "$.attempt", "attempt must be a positive integer");
  if (Number.isNaN(Date.parse(request.requested_at))) throw new ContractError("E_REQUEST_TIME_INVALID", "requested_at must be RFC 3339", "$.requested_at");
  if (typeof request.runbook_ref !== "string" || path.isAbsolute(request.runbook_ref) || request.runbook_ref.split(/[\\/]/).includes("..")) {
    throw new ContractError("E_RUNBOOK_REF_INVALID", "runbook_ref must be project-relative without '..'", "$.runbook_ref");
  }
  const checks = [
    ["runbook_id", runbook.runbook_id],
    ["plan_sha256", runbook.integrity?.plan_sha256],
    ["runner_provider", runbook.runner_provider],
    ["project_config_sha256", runbook.project_config_sha256],
  ];
  for (const [field, expected] of checks) {
    if (request[field] !== expected) throw new ContractError("E_REQUEST_RUNBOOK_MISMATCH", `${field} does not match the frozen runbook`, `$.${field}`);
  }
  if (sha256Json(runbook) !== request.runbook_sha256) throw new ContractError("E_RUNBOOK_HASH_MISMATCH", "runbook_sha256 does not match canonical runbook JSON", "$.runbook_sha256");
  if (runbookPlanHash(runbook) !== runbook.integrity?.plan_sha256) throw new ContractError("E_RUNBOOK_PLAN_HASH_MISMATCH", "integrity.plan_sha256 does not match the canonical frozen plan", "$.integrity.plan_sha256");
  if (sha256Json(request.target) !== sha256Json(runbook.target)) throw new ContractError("E_REQUEST_TARGET_MISMATCH", "request target must equal runbook target", "$.target");
  if (request.runner_provider !== "web-playwright" || !["web", "mobile_web"].includes(request.target?.platform)) {
    throw new ContractError("E_WEB_TARGET_UNSUPPORTED", "runner supports web/desktop and mobile_web/responsive only", "$.target");
  }
  const expectedDevice = request.target.platform === "web" ? "desktop" : "responsive";
  if (request.target.device !== expectedDevice || runbook.review_status !== "approved" || runbook.execution?.enabled !== true) {
    throw new ContractError("E_WEB_TARGET_UNSUPPORTED", "runbook must be approved and executable for the platform device", "$.target");
  }
  if (request.runtime_binding !== null || request.artifact !== null) {
    throw new ContractError("E_WEB_NATIVE_BINDING_FORBIDDEN", "web requests require runtime_binding=null and artifact=null");
  }
  if (request.build !== null) {
    if (typeof request.build?.ref !== "string" || request.build.ref.length === 0 || !SHA256_PATTERN.test(request.build?.sha256)) {
      throw new ContractError("E_BUILD_BINDING_INVALID", "build must contain a non-empty ref and SHA-256", "$.build");
    }
  }
  if (runbook.fixture?.destructive === true && runbook.fixture.environment !== "isolated") {
    throw new ContractError("E_FIXTURE_ISOLATION_REQUIRED", "destructive fixtures require an isolated environment", "$.fixture.environment");
  }
  const mutations = runbook.steps.filter((step) => step.mutation !== "none").map((step) => step.id);
  if (mutations.length > 0) {
    const approval = runbook.approval_ref;
    if (
      !approval
      || approval.plan_sha256 !== runbook.integrity.plan_sha256
      || !SHA256_PATTERN.test(approval.record_sha256)
      || sha256Json(approval.approved_step_ids) !== sha256Json(mutations)
      || approval.environment !== runbook.fixture.environment
    ) {
      throw new ContractError("E_APPROVAL_INVALID", "mutation approval does not match the frozen plan and scope", "$.approval_ref");
    }
    if (approval.expires_at !== null && Date.parse(approval.expires_at) <= Date.now()) {
      throw new ContractError("E_APPROVAL_EXPIRED", "mutation approval has expired", "$.approval_ref.expires_at");
    }
  }
}

function locatorFor(page, descriptor) {
  assertPlainObject(descriptor, "E_LOCATOR_INVALID", "$", "resolved locator must be an object");
  let locator;
  const exact = descriptor.exact ?? true;
  switch (descriptor.by) {
    case "role": locator = page.getByRole(descriptor.value, { ...(descriptor.name === undefined ? {} : { name: descriptor.name }), exact }); break;
    case "label": locator = page.getByLabel(descriptor.value, { exact }); break;
    case "test_id": locator = page.getByTestId(descriptor.value); break;
    case "text": locator = page.getByText(descriptor.value, { exact }); break;
    case "placeholder": locator = page.getByPlaceholder(descriptor.value, { exact }); break;
    case "css": locator = page.locator(descriptor.value); break;
    default: throw new ContractError("E_LOCATOR_TYPE_UNSUPPORTED", `unsupported locator type: ${descriptor.by}`);
  }
  return descriptor.nth === undefined ? locator : locator.nth(descriptor.nth);
}

async function executeStep(page, step) {
  const args = step.provider_args;
  switch (step.action) {
    case "goto": await page.goto(args.url, { waitUntil: args.wait_until, timeout: step.timeout_ms }); break;
    case "click": await locatorFor(page, args.locator).click({ timeout: step.timeout_ms }); break;
    case "fill": await locatorFor(page, args.locator).fill(args.value, { timeout: step.timeout_ms }); break;
    case "press": await locatorFor(page, args.locator).press(args.key, { timeout: step.timeout_ms }); break;
    case "select_option": await locatorFor(page, args.locator).selectOption(args.value, { timeout: step.timeout_ms }); break;
    case "wait_for": await locatorFor(page, args.locator).waitFor({ state: args.state, timeout: step.timeout_ms }); break;
    default: throw new ContractError("E_WEB_ACTION_UNSUPPORTED", `unsupported frozen action: ${step.action}`);
  }
}

async function collectEvidence(page, plan, observations) {
  const collector = plan.collector ?? {};
  const locator = collector.locator ? locatorFor(page, collector.locator) : null;
  switch (plan.evidence_kind) {
    case "locator_result":
      return { locator: cloneJson(collector.locator), count: await locator.count(), visible: await locator.isVisible().catch(() => false) };
    case "dom_state": {
      const fields = collector.fields ?? ["text"];
      const attributes = collector.attributes ?? [];
      const record = {};
      if (fields.includes("text")) record.text = truncateText(await locator.textContent());
      if (fields.includes("value")) record.value = truncateText(await locator.inputValue());
      if (fields.includes("checked")) record.checked = await locator.isChecked();
      if (fields.includes("enabled")) record.enabled = await locator.isEnabled();
      if (fields.includes("visible")) record.visible = await locator.isVisible();
      if (attributes.length > 0) {
        record.attributes = Object.fromEntries(await Promise.all(attributes.map(async (name) => [name, truncateText(await locator.getAttribute(name))])));
      }
      return record;
    }
    case "accessibility_state":
      return locator.evaluate((element) => ({
        role: element.getAttribute("role"),
        aria_label: element.getAttribute("aria-label"),
        aria_checked: element.getAttribute("aria-checked"),
        aria_disabled: element.getAttribute("aria-disabled"),
        disabled: "disabled" in element ? Boolean(element.disabled) : null,
        checked: "checked" in element ? Boolean(element.checked) : null,
      }));
    case "url_state":
      return sanitizeUrl(page.url());
    case "network_error":
      return { entries: cloneJson(observations.networkErrors) };
    case "console_error":
      return { entries: cloneJson(observations.consoleErrors) };
    case "api_state": {
      const response = await page.request.get(collector.url, { timeout: collector.timeout_ms ?? 10_000 });
      const contentType = response.headers()["content-type"] ?? "";
      const body = contentType.includes("application/json") ? await response.json() : null;
      return { status: response.status(), selected: selectJsonPointers(body, collector.json_pointers ?? []) };
    }
    case "storage_state": {
      const area = collector.area ?? "localStorage";
      if (!["localStorage", "sessionStorage"].includes(area)) throw new ContractError("E_STORAGE_AREA_UNSUPPORTED", "storage area must be localStorage or sessionStorage");
      const keys = collector.allowed_keys ?? [];
      const selected = await page.evaluate(({ areaName, allowedKeys }) => {
        const storage = window[areaName];
        return Object.fromEntries(allowedKeys.map((key) => [key, storage.getItem(key)]));
      }, { areaName: area, allowedKeys: keys });
      return {
        area,
        keys: Object.fromEntries(Object.entries(selected).map(([key, value]) => [key, value === null ? { present: false, value_sha256: null } : { present: true, value_sha256: sha256Bytes(Buffer.from(value, "utf8")) }])),
      };
    }
    default:
      throw new ContractError("E_EVIDENCE_KIND_UNSUPPORTED", `unsupported web evidence kind: ${plan.evidence_kind}`);
  }
}

function evidenceItem(id, kind, record, collectedAt, redactions = []) {
  return {
    id,
    kind,
    collected_at: collectedAt,
    producer: { type: "runner", name: "web-playwright", version: RUNNER_VERSION },
    sha256: sha256Json(record),
    redactions,
    record,
  };
}

function safeRuntimeError(error, stepId) {
  return {
    code: error instanceof ContractError ? error.code : "E_PLAYWRIGHT_ACTION_FAILED",
    category: error instanceof ContractError ? "contract" : "product",
    message: error instanceof ContractError ? error.message : `Playwright action failed (${error?.name ?? "Error"})`,
    step_id: stepId,
    evidence_refs: [],
    retryable: false,
  };
}

export async function runWebPlaywright({ request, runbook, playwrightModuleRoot = undefined }) {
  const startedAt = new Date().toISOString();
  try {
    validateRequest(request, runbook);
  } catch (error) {
    if (
      !(error instanceof ContractError)
      || error.code === "E_SENSITIVE_INPUT"
      || typeof request?.run_id !== "string"
      || typeof runbook?.runbook_id !== "string"
      || typeof runbook?.scenario_id !== "string"
    ) {
      throw error;
    }
    return createNotStartedOutput(request, runbook, error, startedAt);
  }
  const playwright = await loadPlaywright(playwrightModuleRoot);
  const observations = { networkErrors: [], consoleErrors: [] };
  const evidence = [];
  const errors = [];
  const missingEvidence = [];
  const stepResults = [];
  const frozenContext = runbook.steps.find((step) => step.provider_args?.context)?.provider_args.context ?? {};
  const commandRecord = {
    provider: "web-playwright",
    runner_version: RUNNER_VERSION,
    browser: "chromium",
    headless: frozenContext.headless,
    context: {
      viewport: cloneJson(frozenContext.viewport ?? null),
      is_mobile: frozenContext.is_mobile ?? false,
      has_touch: frozenContext.has_touch ?? false,
      locale: frozenContext.locale ?? null,
    },
    runbook_id: runbook.runbook_id,
    plan_sha256: runbook.integrity.plan_sha256,
    attempt: request.attempt,
  };
  evidence.push(evidenceItem("runner-command", "test_command", commandRecord, startedAt));
  if (request.build !== null) {
    evidence.push(evidenceItem("runner-build", "build_hash", cloneJson(request.build), startedAt));
  }
  let browser;
  let context;
  let page;
  let stopped = false;
  try {
    browser = await playwright.chromium.launch({ headless: frozenContext.headless !== false });
    const firstContext = frozenContext;
    context = await browser.newContext({
      viewport: firstContext.viewport,
      locale: firstContext.locale,
      colorScheme: firstContext.color_scheme,
      reducedMotion: firstContext.reduced_motion,
      deviceScaleFactor: firstContext.device_scale_factor,
      isMobile: firstContext.is_mobile,
      hasTouch: firstContext.has_touch,
    });
    page = await context.newPage();
    page.on("console", (message) => {
      if (message.type() === "error") observations.consoleErrors.push({ type: "error", location: sanitizeUrl(message.location().url || page.url()), text_sha256: sha256Bytes(Buffer.from(message.text(), "utf8")) });
    });
    page.on("requestfailed", (failedRequest) => {
      observations.networkErrors.push({ url: sanitizeUrl(failedRequest.url()), method: failedRequest.method(), failure: failedRequest.failure()?.errorText ?? "request_failed" });
    });
    page.on("response", (response) => {
      if (response.status() >= 400) observations.networkErrors.push({ url: sanitizeUrl(response.url()), method: response.request().method(), status: response.status() });
    });

    for (const step of runbook.steps) {
      const result = { step_id: step.id, status: "not_started", attempt_count: 0, started_at: null, finished_at: null, evidence_refs: [], error: null };
      stepResults.push(result);
      if (stopped) {
        result.status = "skipped";
        continue;
      }
      result.started_at = new Date().toISOString();
      try {
        for (let attempt = 1; attempt <= step.max_attempts; attempt += 1) {
          result.attempt_count = attempt;
          try {
            await executeStep(page, step);
            break;
          } catch (error) {
            if (attempt === step.max_attempts) throw error;
          }
        }
        result.status = "completed";
      } catch (error) {
        result.status = "error";
        result.error = safeRuntimeError(error, step.id);
        errors.push(result.error);
        stopped = true;
      }
      result.finished_at = new Date().toISOString();
      if (result.status === "completed") {
        const planned = runbook.evidence_plan.filter((item) => item.after_step_id === step.id);
        for (const plan of planned) {
          try {
            const record = await collectEvidence(page, plan, observations);
            const id = `evidence-${String(evidence.length + 1).padStart(3, "0")}`;
            evidence.push(evidenceItem(id, plan.evidence_kind, record, new Date().toISOString(), plan.evidence_kind === "storage_state" ? ["storage values replaced with SHA-256"] : []));
            result.evidence_refs.push(id);
          } catch (error) {
            const evidenceError = { ...safeRuntimeError(error, step.id), code: "E_EVIDENCE_COLLECTION_FAILED", category: "evidence" };
            errors.push(evidenceError);
            missingEvidence.push({ oracle_rule_id: plan.oracle_rule_id, evidence_kind: plan.evidence_kind, reason: evidenceError.code });
          }
        }
      }
    }
  } finally {
    await context?.close().catch(() => {});
    await browser?.close().catch(() => {});
  }
  const completedSteps = stepResults.filter((step) => step.status === "completed").length;
  const status = completedSteps === runbook.steps.length ? "completed" : completedSteps === 0 ? "not_started" : "partial";
  const output = {
    schema_version: "runner-output-v1",
    run_id: request.run_id,
    runbook_id: runbook.runbook_id,
    runbook_hash: request.runbook_sha256,
    plan_sha256: runbook.integrity.plan_sha256,
    scenario_id: runbook.scenario_id,
    spec_version: runbook.spec_version,
    scenario_hash: runbook.scenario_hash,
    target: cloneJson(runbook.target),
    runner_provider: "web-playwright",
    provider_binding: cloneJson(runbook.provider_binding),
    project_config_sha256: runbook.project_config_sha256,
    started_at: startedAt,
    finished_at: new Date().toISOString(),
    execution: { status, attempt: request.attempt, retry_count: stepResults.reduce((sum, step) => sum + Math.max(0, step.attempt_count - 1), 0), command_evidence_ref: "runner-command", runner_version: RUNNER_VERSION },
    subject: { build: cloneJson(request.build), artifact: null, runtime_binding: null },
    step_results: stepResults,
    evidence,
    errors,
    unsupported_reason: null,
    missing_evidence: missingEvidence,
    diagnostic_attachments: [],
  };
  validateRunnerOutput(output);
  return output;
}

function createNotStartedOutput(request, runbook, error, startedAt) {
  const commandRecord = {
    provider: "web-playwright",
    runner_version: RUNNER_VERSION,
    phase: "preflight",
    runbook_id: runbook.runbook_id,
    attempt: Number.isInteger(request.attempt) ? request.attempt : 0,
    error_code: error.code,
  };
  const contractError = {
    code: error.code,
    category: "contract",
    message: error.message,
    step_id: null,
    evidence_refs: ["runner-command"],
    retryable: false,
  };
  const output = {
    schema_version: "runner-output-v1",
    run_id: request.run_id,
    runbook_id: runbook.runbook_id,
    runbook_hash: sha256Json(runbook),
    plan_sha256: runbook.integrity?.plan_sha256 ?? `sha256:${"0".repeat(64)}`,
    scenario_id: runbook.scenario_id,
    spec_version: runbook.spec_version ?? "unknown",
    scenario_hash: runbook.scenario_hash ?? `sha256:${"0".repeat(64)}`,
    target: cloneJson(runbook.target ?? request.target ?? {}),
    runner_provider: "web-playwright",
    provider_binding: cloneJson(runbook.provider_binding ?? {}),
    project_config_sha256: runbook.project_config_sha256 ?? `sha256:${"0".repeat(64)}`,
    started_at: startedAt,
    finished_at: new Date().toISOString(),
    execution: { status: "not_started", attempt: Number.isInteger(request.attempt) ? request.attempt : 0, retry_count: 0, command_evidence_ref: "runner-command", runner_version: RUNNER_VERSION },
    subject: { build: null, artifact: null, runtime_binding: null },
    step_results: (runbook.steps ?? []).map((step) => ({ step_id: step.id, status: "not_started", attempt_count: 0, started_at: null, finished_at: null, evidence_refs: [], error: null })),
    evidence: [evidenceItem("runner-command", "test_command", commandRecord, startedAt)],
    errors: [contractError],
    unsupported_reason: null,
    missing_evidence: (runbook.evidence_plan ?? []).map((plan) => ({ oracle_rule_id: plan.oracle_rule_id, evidence_kind: plan.evidence_kind, reason: error.code })),
    diagnostic_attachments: [],
  };
  validateRunnerOutput(output);
  return output;
}

export function validateRunnerOutput(output) {
  assertPlainObject(output, "E_RUNNER_OUTPUT_INVALID", "$", "runner output must be an object");
  if (output.schema_version !== "runner-output-v1") throw new ContractError("E_OUTPUT_SCHEMA_VERSION", "output must be runner-output-v1", "$.schema_version");
  if ("verdict" in output || "oracle_results" in output) throw new ContractError("E_RUNNER_SELF_JUDGMENT_FORBIDDEN", "runner output must not contain verdict or oracle_results");
  for (const field of ["step_results", "evidence", "errors", "missing_evidence", "diagnostic_attachments"]) {
    if (!Array.isArray(output[field])) throw new ContractError("E_RUNNER_OUTPUT_FIELD", `${field} must be an array`, `$.${field}`);
  }
  if (!["not_started", "partial", "completed"].includes(output.execution?.status)) throw new ContractError("E_RUNNER_STATUS_INVALID", "invalid runner execution status", "$.execution.status");
  const evidenceIds = new Set();
  for (const [index, item] of output.evidence.entries()) {
    if (evidenceIds.has(item.id)) throw new ContractError("E_EVIDENCE_ID_DUPLICATE", "evidence IDs must be unique", `$.evidence[${index}].id`);
    evidenceIds.add(item.id);
    if (sha256Json(item.record) !== item.sha256) throw new ContractError("E_EVIDENCE_HASH_MISMATCH", "evidence record hash does not match", `$.evidence[${index}].sha256`);
    if (!WEB_OUTPUT_EVIDENCE_KINDS.has(item.kind)) throw new ContractError("E_EVIDENCE_KIND_UNSUPPORTED", "runner emitted an unsupported evidence kind", `$.evidence[${index}].kind`);
    if (item.producer?.type !== "runner" || typeof item.producer?.name !== "string") throw new ContractError("E_EVIDENCE_PRODUCER_INVALID", "web evidence must identify the runner producer", `$.evidence[${index}].producer`);
  }
  if (!evidenceIds.has(output.execution.command_evidence_ref)) throw new ContractError("E_COMMAND_EVIDENCE_REQUIRED", "command_evidence_ref must resolve", "$.execution.command_evidence_ref");
  assertSecretFree(output);
  return output;
}

async function main() {
  const options = parseCli(process.argv.slice(2), {
    "--request": { name: "request", required: true },
    "--runbook": { name: "runbook", required: true },
    "--output": { name: "output", required: true },
    "--playwright-module-root": { name: "playwright_module_root" },
  });
  const output = await runWebPlaywright({
    request: await readJson(options.request),
    runbook: await readJson(options.runbook),
    playwrightModuleRoot: options.playwright_module_root,
  });
  await writeJson(options.output, output);
  process.stdout.write(`${JSON.stringify({ valid: true, output: options.output, execution_status: output.execution.status })}\n`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    printContractError(error);
    process.exitCode = 1;
  });
}
