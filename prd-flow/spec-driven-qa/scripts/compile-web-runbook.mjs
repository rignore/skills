#!/usr/bin/env node

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
  resolveRelativeUrl,
  runbookPlanHash,
  sha256Json,
  writeJson,
} from "./web-provider-lib.mjs";

const LOCATOR_TYPES = new Set(["role", "label", "test_id", "text", "placeholder", "css"]);
const EVIDENCE_KINDS = new Set([
  "dom_state",
  "accessibility_state",
  "locator_result",
  "url_state",
  "network_error",
  "console_error",
  "api_state",
  "storage_state",
  "test_command",
  "build_hash",
]);

function validateScenario(scenario) {
  assertPlainObject(scenario, "E_SCENARIO_INVALID", "$", "scenario must be an object");
  assertSecretFree(scenario);
  if (scenario.schema_version !== "scenario-v1") {
    throw new ContractError("E_SCHEMA_VERSION", "scenario schema_version must equal scenario-v1", "$.schema_version");
  }
  requireNonEmptyString(scenario.id, "E_SCENARIO_ID", "$.id", "scenario id is required");
  if (scenario.review_status !== "approved" || scenario.execution?.enabled !== true) {
    throw new ContractError("E_SCENARIO_NOT_EXECUTABLE", "web compilation requires an approved, enabled scenario");
  }
  const expectedTarget = scenario.target?.platform === "web"
    ? { platform: "web", device: "desktop" }
    : { platform: "mobile_web", device: "responsive" };
  if (
    !["web", "mobile_web"].includes(scenario.target?.platform)
    || scenario.method !== "web"
    || scenario.runner_provider !== "web-playwright"
    || scenario.target.device !== expectedTarget.device
  ) {
    throw new ContractError(
      "E_WEB_TARGET_UNSUPPORTED",
      "web-playwright supports web/desktop and mobile_web/responsive only",
      "$.target",
    );
  }
  if (!Array.isArray(scenario.source_refs) || scenario.source_refs.length === 0) {
    throw new ContractError("E_SOURCE_REFS_REQUIRED", "source_refs must be non-empty", "$.source_refs");
  }
  if (!Array.isArray(scenario.steps) || scenario.steps.length === 0) {
    throw new ContractError("E_STEPS_REQUIRED", "steps must be non-empty", "$.steps");
  }
  if (!Array.isArray(scenario.expected) || scenario.expected.length === 0 || !Array.isArray(scenario.oracle?.rules) || scenario.oracle.rules.length === 0) {
    throw new ContractError("E_ORACLE_REQUIRED", "enabled web scenarios require expected and oracle rules");
  }
  const mutatingActions = new Set(["activate", "click", "fill", "press", "select_option"]);
  const mutationIds = scenario.steps
    .filter((step) => step.mutation === "potential" || step.mutation === "confirmed" || mutatingActions.has(step.action))
    .map((step) => step.id);
  if (scenario.steps.some((step) => mutatingActions.has(step.action) && step.mutation === "none")) {
    throw new ContractError("E_MUTATION_CLASSIFICATION_REQUIRED", "state-changing web actions must be potential or confirmed", "$.steps");
  }
  if (mutationIds.length === 0) {
    if (scenario.mutation_policy?.mode !== "deny" || scenario.mutation_policy?.approval_scope?.length !== 0) {
      throw new ContractError("E_MUTATION_POLICY_INVALID", "read-only web scenarios require mode=deny and an empty approval_scope", "$.mutation_policy");
    }
  } else if (
    scenario.mutation_policy?.mode !== "require_approval"
    || JSON.stringify(scenario.mutation_policy?.approval_scope) !== JSON.stringify(mutationIds)
    || scenario.mutation_policy?.retry_policy !== "never"
  ) {
    throw new ContractError("E_MUTATION_POLICY_INVALID", "mutation policy must cover every mutation step in order and forbid retries", "$.mutation_policy");
  }
}

function validateConfig(config, target) {
  assertPlainObject(config, "E_WEB_CONFIG_INVALID", "$", "web config must be an object");
  assertSecretFree(config);
  if (config.schema_version !== "web-playwright-config-v1" || config.provider !== "web-playwright") {
    throw new ContractError("E_WEB_CONFIG_VERSION", "config must be web-playwright-config-v1 for web-playwright");
  }
  for (const field of ["provider_contract_version", "implementation_version", "defaults_version", "runbook_id", "browser", "origin"]) {
    requireNonEmptyString(config[field], "E_WEB_CONFIG_FIELD", `$.${field}`, `${field} is required`);
  }
  if (config.browser !== "chromium") {
    throw new ContractError("E_WEB_BROWSER_UNSUPPORTED", "P2 supports chromium only", "$.browser");
  }
  let origin;
  try {
    origin = new URL(config.origin);
  } catch {
    throw new ContractError("E_WEB_ORIGIN_INVALID", "origin must be an absolute URL", "$.origin");
  }
  if (!['http:', 'https:'].includes(origin.protocol) || origin.username || origin.password || origin.pathname !== "/" || origin.search || origin.hash) {
    throw new ContractError("E_WEB_ORIGIN_INVALID", "origin must be a credential-free HTTP(S) origin", "$.origin");
  }
  if (!Array.isArray(config.allowed_origins) || !config.allowed_origins.includes(origin.origin)) {
    throw new ContractError("E_WEB_ORIGIN_NOT_ALLOWED", "origin must appear in allowed_origins", "$.allowed_origins");
  }
  const profileName = target.platform === "web" ? "desktop" : "responsive";
  assertPlainObject(config.profiles?.[profileName], "E_WEB_PROFILE_REQUIRED", `$.profiles.${profileName}`, `${profileName} profile is required`);
  const viewport = config.profiles[profileName].viewport;
  requireInteger(viewport?.width, 240, 7680, "E_WEB_VIEWPORT_INVALID", `$.profiles.${profileName}.viewport.width`, "viewport width must be 240..7680");
  requireInteger(viewport?.height, 240, 7680, "E_WEB_VIEWPORT_INVALID", `$.profiles.${profileName}.viewport.height`, "viewport height must be 240..7680");
  if (profileName === "responsive" && config.profiles.responsive.is_mobile !== true) {
    throw new ContractError("E_MOBILE_WEB_PROFILE_INVALID", "responsive profile must set is_mobile=true", "$.profiles.responsive.is_mobile");
  }
  if (!['never', 'safe'].includes(config.read_only_retry_policy ?? "never")) {
    throw new ContractError("E_STEP_RETRY_POLICY_INVALID", "read_only_retry_policy must be never or safe", "$.read_only_retry_policy");
  }
  return { origin: origin.origin, profileName };
}

function resolveLocator(config, reference, contractPath) {
  requireNonEmptyString(reference, "E_LOCATOR_REF_REQUIRED", contractPath, "control_ref is required");
  const locator = config.locators?.[reference];
  assertPlainObject(locator, "E_LOCATOR_UNRESOLVED", contractPath, `locator ${reference} is not configured`);
  if (!LOCATOR_TYPES.has(locator.by)) {
    throw new ContractError("E_LOCATOR_TYPE_UNSUPPORTED", `unsupported locator type: ${locator.by}`, contractPath);
  }
  requireNonEmptyString(locator.value, "E_LOCATOR_VALUE_REQUIRED", contractPath, "locator value is required");
  const allowed = new Set(["by", "value", "name", "exact", "nth"]);
  for (const key of Object.keys(locator)) {
    if (!allowed.has(key)) {
      throw new ContractError("E_LOCATOR_AMBIGUOUS", "locator must be one resolved locator without candidates or fallback", `${contractPath}.${key}`);
    }
  }
  if (locator.by === "role" && locator.name !== undefined && typeof locator.name !== "string") {
    throw new ContractError("E_LOCATOR_VALUE_REQUIRED", "role locator name must be a string", `${contractPath}.name`);
  }
  if (locator.nth !== undefined) {
    requireInteger(locator.nth, 0, 1000, "E_LOCATOR_NTH_INVALID", `${contractPath}.nth`, "locator nth must be 0..1000");
  }
  return cloneJson(locator);
}

function timeoutFor(config, name) {
  const value = config.timeouts_ms?.[name] ?? config.timeouts_ms?.action ?? 10_000;
  return requireInteger(value, 1, 120_000, "E_STEP_TIMEOUT_INVALID", `$.timeouts_ms.${name}`, "timeout must be 1..120000");
}

function compileStep(step, index, config, origin, context) {
  assertPlainObject(step, "E_STEP_INVALID", `$.steps[${index}]`, "step must be an object");
  const args = step.arguments ?? {};
  let action;
  let providerArgs;
  let timeoutName = "action";
  switch (step.action) {
    case "navigate": {
      action = "goto";
      const route = config.routes?.[args.route_ref];
      providerArgs = { url: resolveRelativeUrl(origin, route, `$.routes.${args.route_ref}`), wait_until: "domcontentloaded" };
      timeoutName = "goto";
      break;
    }
    case "activate":
    case "click":
      action = "click";
      providerArgs = { locator: resolveLocator(config, args.control_ref, `$.steps[${index}].arguments.control_ref`) };
      break;
    case "fill": {
      action = "fill";
      const value = config.fixture_values?.[args.fixture_value_ref];
      if (typeof value !== "string") throw new ContractError("E_FIXTURE_VALUE_UNRESOLVED", "fixture_value_ref must resolve to a string", `$.steps[${index}].arguments.fixture_value_ref`);
      providerArgs = { locator: resolveLocator(config, args.control_ref, `$.steps[${index}].arguments.control_ref`), value };
      break;
    }
    case "press":
      action = "press";
      providerArgs = {
        locator: resolveLocator(config, args.control_ref, `$.steps[${index}].arguments.control_ref`),
        key: requireNonEmptyString(args.key, "E_PRESS_KEY_REQUIRED", `$.steps[${index}].arguments.key`, "press key is required"),
      };
      break;
    case "select_option": {
      action = "select_option";
      const value = config.options?.[args.option_ref];
      if (typeof value !== "string") throw new ContractError("E_OPTION_UNRESOLVED", "option_ref must resolve to a string", `$.steps[${index}].arguments.option_ref`);
      providerArgs = { locator: resolveLocator(config, args.control_ref, `$.steps[${index}].arguments.control_ref`), value };
      break;
    }
    case "wait_for":
      action = "wait_for";
      providerArgs = {
        locator: resolveLocator(config, args.control_ref, `$.steps[${index}].arguments.control_ref`),
        state: args.state ?? "visible",
      };
      if (!["attached", "detached", "visible", "hidden"].includes(providerArgs.state)) {
        throw new ContractError("E_WAIT_STATE_UNSUPPORTED", "unsupported wait_for state", `$.steps[${index}].arguments.state`);
      }
      break;
    default:
      throw new ContractError("E_WEB_ACTION_UNSUPPORTED", `unsupported web action: ${step.action}`, `$.steps[${index}].action`);
  }
  if (action === "goto") providerArgs.context = cloneJson(context);
  const mutation = step.mutation;
  const retryPolicy = mutation === "none" ? (config.read_only_retry_policy ?? "never") : "never";
  const maxAttempts = retryPolicy === "safe" ? (config.read_only_max_attempts ?? 1) : 1;
  requireInteger(maxAttempts, 1, 5, "E_STEP_MAX_ATTEMPTS_INVALID", "$.read_only_max_attempts", "max attempts must be 1..5");
  return {
    id: step.id,
    action,
    description: step.description,
    mutation,
    arguments: cloneJson(step.arguments ?? null),
    provider_args: providerArgs,
    timeout_ms: timeoutFor(config, timeoutName),
    retry_policy: retryPolicy,
    max_attempts: maxAttempts,
    provider_defaults_version: config.defaults_version,
  };
}

function compileEvidencePlan(scenario, config) {
  return scenario.oracle.rules.map((rule, index) => {
    const collector = config.evidence_collectors?.[rule.id];
    assertPlainObject(collector, "E_EVIDENCE_COLLECTOR_REQUIRED", `$.evidence_collectors.${rule.id}`, `collector for oracle rule ${rule.id} is required`);
    if (collector.kind !== rule.evidence_kind || !EVIDENCE_KINDS.has(collector.kind)) {
      throw new ContractError("E_EVIDENCE_KIND_UNSUPPORTED", "collector kind must match the oracle evidence_kind", `$.evidence_collectors.${rule.id}.kind`);
    }
    const stepIds = new Set(scenario.steps.map((step) => step.id));
    if (!stepIds.has(collector.after_step_id)) {
      throw new ContractError("E_EVIDENCE_STEP_UNKNOWN", "collector after_step_id must reference a scenario step", `$.evidence_collectors.${rule.id}.after_step_id`);
    }
    const resolved = cloneJson(collector);
    if (collector.locator_ref !== undefined) {
      resolved.locator = resolveLocator(config, collector.locator_ref, `$.evidence_collectors.${rule.id}.locator_ref`);
      delete resolved.locator_ref;
    }
    if (collector.route_ref !== undefined) {
      resolved.url = resolveRelativeUrl(config.origin, config.routes?.[collector.route_ref], `$.evidence_collectors.${rule.id}.route_ref`);
      delete resolved.route_ref;
    }
    delete resolved.kind;
    delete resolved.after_step_id;
    return {
      oracle_rule_id: rule.id,
      evidence_kind: rule.evidence_kind,
      after_step_id: collector.after_step_id,
      collector: resolved,
      sequence: index + 1,
    };
  });
}

function validateApproval(approval, planSha256, scope, environment) {
  assertPlainObject(approval, "E_APPROVAL_REQUIRED", "$.approval_ref", "mutation runbook requires an external approval record");
  for (const field of ["id", "record_sha256", "plan_sha256", "approved_by_ref", "scope"]) {
    requireNonEmptyString(approval[field], "E_APPROVAL_INVALID", `$.approval_ref.${field}`, `${field} is required`);
  }
  if (approval.plan_sha256 !== planSha256 || JSON.stringify(approval.approved_step_ids) !== JSON.stringify(scope)) {
    throw new ContractError("E_APPROVAL_SCOPE_MISMATCH", "approval must bind the exact plan hash and mutation step scope", "$.approval_ref");
  }
  if (approval.environment !== environment || !["single_run", "runbook_revision"].includes(approval.scope)) {
    throw new ContractError("E_APPROVAL_ENVIRONMENT_MISMATCH", "approval environment and scope must match the runbook", "$.approval_ref");
  }
  return { ...cloneJson(approval), provider_plan_hash: approval.provider_plan_hash ?? null };
}

export function compileWebRunbook({ scenario, config, approval = null, allowUnapprovedPreflight = false }) {
  validateScenario(scenario);
  const { origin, profileName } = validateConfig(config, scenario.target);
  const profile = {
    ...cloneJson(config.profiles[profileName]),
    browser: config.browser,
    headless: config.headless !== false,
  };
  const steps = scenario.steps.map((step, index) => compileStep(step, index, config, origin, profile));
  const evidencePlan = compileEvidencePlan(scenario, config);
  const projectConfigSha256 = sha256Json(config);
  const scenarioHash = sha256Json(scenario);
  const runbook = {
    schema_version: "runbook-v1",
    runbook_id: config.runbook_id,
    scenario_id: scenario.id,
    spec_version: scenario.spec_version,
    scenario_hash: scenarioHash,
    source_refs: cloneJson(scenario.source_refs),
    review_status: scenario.review_status,
    method: scenario.method,
    execution: cloneJson(scenario.execution),
    target: cloneJson(scenario.target),
    runner_provider: "web-playwright",
    provider_binding: {
      contract_version: config.provider_contract_version,
      implementation_version: config.implementation_version,
      defaults_version: config.defaults_version,
    },
    project_config_sha256: projectConfigSha256,
    preconditions: cloneJson(scenario.preconditions),
    fixture: cloneJson(scenario.fixture),
    steps,
    expected: cloneJson(scenario.expected),
    oracle: cloneJson(scenario.oracle),
    mutation_policy: cloneJson(scenario.mutation_policy),
    evidence_plan: evidencePlan,
    integrity: { plan_sha256: "" },
    approval_ref: null,
  };
  runbook.integrity.plan_sha256 = runbookPlanHash(runbook);
  const mutationScope = steps.filter((step) => step.mutation !== "none").map((step) => step.id);
  if (mutationScope.length > 0) {
    if (approval === null && allowUnapprovedPreflight) return runbook;
    if (approval === null) {
      throw new ContractError(
        "E_APPROVAL_REQUIRED",
        "mutation runbook requires approval bound to the frozen plan",
        "$.approval_ref",
        { plan_sha256: runbook.integrity.plan_sha256, approved_step_ids: mutationScope, environment: scenario.fixture.environment },
      );
    }
    runbook.approval_ref = validateApproval(approval, runbook.integrity.plan_sha256, mutationScope, scenario.fixture.environment);
  }
  return runbook;
}

async function main() {
  const options = parseCli(process.argv.slice(2), {
    "--scenario": { name: "scenario", required: true },
    "--config": { name: "config", required: true },
    "--approval": { name: "approval" },
    "--output": { name: "output", required: true },
    "--preflight": { name: "preflight", boolean: true },
  });
  const runbook = compileWebRunbook({
    scenario: await readJson(options.scenario),
    config: await readJson(options.config),
    approval: options.approval ? await readJson(options.approval) : null,
    allowUnapprovedPreflight: options.preflight === true,
  });
  await writeJson(options.output, runbook);
  process.stdout.write(`${JSON.stringify({ valid: true, output: options.output, plan_sha256: runbook.integrity.plan_sha256 })}\n`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    printContractError(error);
    process.exitCode = 1;
  });
}
