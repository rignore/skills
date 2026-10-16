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
  runbookPlanHash,
  sha256Json,
  writeJson,
} from "./web-provider-lib.mjs";

const LOCATOR_PRIORITY = ["accessibility_id", "id", "text"];
// launch, tap, fill, press_key, back can change app or backend state; scenario-schema forbids labeling them "none".
const MUTATING_ACTIONS = new Set(["launch", "tap", "fill", "press_key", "back"]);
const READ_ONLY_CAPABLE_ACTIONS = new Set(["wait_for", "swipe", "pause"]);
const SUPPORTED_ACTIONS = new Set([...MUTATING_ACTIONS, ...READ_ONLY_CAPABLE_ACTIONS]);
const NATIVE_KEYS = new Set(["BACK", "ENTER", "HOME", "TAB"]);
const SWIPE_DIRECTIONS = new Set(["up", "down", "left", "right"]);
const HASH = /^sha256:[0-9a-f]{64}$/;

function validateScenario(scenario) {
  assertPlainObject(scenario, "E_SCENARIO_INVALID", "$", "scenario must be an object");
  assertSecretFree(scenario);
  if (scenario.schema_version !== "scenario-v1") throw new ContractError("E_SCHEMA_VERSION", "scenario must be scenario-v1", "$.schema_version");
  if (
    scenario.method !== "native"
    || scenario.target?.platform !== "android"
    || scenario.target?.device !== "emulator"
    || scenario.target?.artifact_type !== "apk"
    || scenario.runner_provider !== "native-android"
  ) {
    throw new ContractError("E_ANDROID_TARGET_UNSUPPORTED", "P3 supports Android Emulator with APK only", "$.target");
  }
  if (scenario.review_status !== "approved" || scenario.execution?.enabled !== true) throw new ContractError("E_SCENARIO_NOT_EXECUTABLE", "Android compilation requires an approved, enabled scenario");
  if (!Array.isArray(scenario.source_refs) || scenario.source_refs.length === 0) throw new ContractError("E_SOURCE_REFS_REQUIRED", "source_refs must be non-empty", "$.source_refs");
  if (!Array.isArray(scenario.steps) || scenario.steps.length < 2 || scenario.steps[0]?.action !== "launch") {
    throw new ContractError("E_ANDROID_MVP_STEPS_INVALID", "Android scenarios require a first launch step followed by at least one wait_for step", "$.steps");
  }
  scenario.steps.forEach((step, index) => {
    if (!SUPPORTED_ACTIONS.has(step.action)) throw new ContractError("E_ANDROID_ACTION_UNSUPPORTED", `Android action ${step.action} is not supported`, `$.steps[${index}].action`);
    if (MUTATING_ACTIONS.has(step.action) && step.mutation === "none") {
      throw new ContractError("E_MUTATION_CLASSIFICATION_REQUIRED", `Android ${step.action} must be potential or confirmed`, `$.steps[${index}].mutation`);
    }
  });
  if (scenario.steps.filter((step) => step.action === "launch").length !== 1) {
    throw new ContractError("E_ANDROID_ACTION_UNSUPPORTED", "Android scenarios support exactly one launch, as the first step", "$.steps");
  }
  // A frozen runbook proves the final UI state with wait_for; an action-only tail would leave the last effect unobserved.
  if (!scenario.steps.some((step) => step.action === "wait_for")) {
    throw new ContractError("E_ANDROID_MVP_STEPS_INVALID", "Android scenarios require at least one wait_for step", "$.steps");
  }
  const mutations = scenario.steps.filter((step) => MUTATING_ACTIONS.has(step.action) || step.mutation !== "none").map((step) => step.id);
  if (
    scenario.mutation_policy?.mode !== "require_approval"
    || scenario.mutation_policy?.retry_policy !== "never"
    || JSON.stringify(scenario.mutation_policy?.approval_scope) !== JSON.stringify(mutations)
  ) {
    throw new ContractError("E_MUTATION_POLICY_INVALID", "Android mutation policy must cover the exact mutation step order", "$.mutation_policy");
  }
  if (!Array.isArray(scenario.expected) || scenario.expected.length === 0 || !Array.isArray(scenario.oracle?.rules) || scenario.oracle.rules.length === 0) {
    throw new ContractError("E_ORACLE_REQUIRED", "enabled Android scenarios require expected and oracle rules");
  }
}

function validateConfig(config) {
  assertPlainObject(config, "E_ANDROID_CONFIG_INVALID", "$", "Android config must be an object");
  assertSecretFree(config);
  if (config.schema_version !== "native-android-config-v1" || config.provider !== "native-android") {
    throw new ContractError("E_ANDROID_CONFIG_VERSION", "config must be native-android-config-v1 for native-android");
  }
  for (const field of ["runbook_id", "provider_contract_version", "implementation_version", "defaults_version"]) {
    requireNonEmptyString(config[field], "E_ANDROID_CONFIG_FIELD", `$.${field}`, `${field} is required`);
  }
  requireInteger(config.hold_ms ?? 800, 0, 30_000, "E_HOLD_INVALID", "$.hold_ms", "hold_ms must be 0..30000");
}

function resolveLocator(config, reference, contractPath) {
  requireNonEmptyString(reference, "E_LOCATOR_REF_REQUIRED", contractPath, "control_ref is required");
  const candidates = config.locators?.[reference];
  if (!Array.isArray(candidates) || candidates.length === 0) throw new ContractError("E_LOCATOR_UNRESOLVED", `locator ${reference} is not configured`, contractPath);
  for (const priority of LOCATOR_PRIORITY) {
    const matches = candidates.filter((candidate) => candidate?.by === priority);
    if (matches.length > 1) throw new ContractError("E_LOCATOR_AMBIGUOUS", `locator ${reference} has multiple ${priority} candidates`, contractPath);
    if (matches.length === 1) {
      const locator = matches[0];
      requireNonEmptyString(locator.value, "E_LOCATOR_VALUE_REQUIRED", contractPath, "locator value is required");
      if (locator.nth !== undefined) requireInteger(locator.nth, 0, 1000, "E_LOCATOR_NTH_INVALID", contractPath, "locator nth must be 0..1000");
      return cloneJson(locator);
    }
  }
  throw new ContractError("E_LOCATOR_TYPE_UNSUPPORTED", "Android locator must use accessibility_id, id, or text", contractPath);
}

function stepTimeout(config, action) {
  const defaults = { launch: 30_000, wait_for: 10_000 };
  const value = config.timeouts_ms?.[action] ?? defaults[action] ?? 10_000;
  return requireInteger(value, 1, 120_000, "E_STEP_TIMEOUT_INVALID", `$.timeouts_ms.${action}`, `${action} timeout must be 1..120000`);
}

function readOnlyRetry(config) {
  const retryPolicy = config.read_only_retry_policy ?? "safe";
  if (!["safe", "never"].includes(retryPolicy)) throw new ContractError("E_STEP_RETRY_POLICY_INVALID", "read_only_retry_policy must be safe or never", "$.read_only_retry_policy");
  const maxAttempts = retryPolicy === "safe" ? (config.read_only_max_attempts ?? 1) : 1;
  requireInteger(maxAttempts, 1, 3, "E_STEP_MAX_ATTEMPTS_INVALID", "$.read_only_max_attempts", "read-only max attempts must be 1..3");
  return { retryPolicy, maxAttempts };
}

function providerArgs(step, index, config) {
  const args = step.arguments ?? {};
  const hold = { hold_ms: config.hold_ms ?? 800 };
  const locator = () => resolveLocator(config, args.control_ref, `$.steps[${index}].arguments.control_ref`);
  switch (step.action) {
    case "launch":
    case "back":
      return hold;
    case "wait_for": {
      const state = args.state ?? "present";
      if (!["present", "absent"].includes(state)) throw new ContractError("E_WAIT_STATE_UNSUPPORTED", "Android wait_for state must be present or absent", `$.steps[${index}].arguments.state`);
      return { locator: locator(), state, ...hold };
    }
    case "tap":
      return { locator: locator(), ...hold };
    case "fill": {
      // The literal must come from the versioned project config so a scenario never carries entered values.
      const value = config.fixture_values?.[args.fixture_value_ref];
      if (typeof value !== "string") throw new ContractError("E_FIXTURE_VALUE_UNRESOLVED", "fixture_value_ref must resolve to a string", `$.steps[${index}].arguments.fixture_value_ref`);
      return { locator: locator(), value, ...hold };
    }
    case "press_key":
      if (!NATIVE_KEYS.has(args.key)) throw new ContractError("E_NATIVE_KEY_UNSUPPORTED", "press_key key must be BACK, ENTER, HOME, or TAB", `$.steps[${index}].arguments.key`);
      return { key: args.key, ...hold };
    case "swipe": {
      if (!SWIPE_DIRECTIONS.has(args.direction)) throw new ContractError("E_SWIPE_DIRECTION_UNSUPPORTED", "swipe direction must be up, down, left, or right", `$.steps[${index}].arguments.direction`);
      const percent = args.percent ?? 0.7;
      if (typeof percent !== "number" || !(percent >= 0.1 && percent <= 1.0)) throw new ContractError("E_SWIPE_PERCENT_INVALID", "swipe percent must be 0.1..1.0", `$.steps[${index}].arguments.percent`);
      return { direction: args.direction, percent, ...hold };
    }
    case "pause":
      return { milliseconds: requireInteger(args.milliseconds, 0, 30_000, "E_PAUSE_INVALID", `$.steps[${index}].arguments.milliseconds`, "pause milliseconds must be 0..30000"), ...hold };
    default:
      throw new ContractError("E_ANDROID_ACTION_UNSUPPORTED", `Android action ${step.action} is not supported`, `$.steps[${index}].action`);
  }
}

function compileSteps(scenario, config) {
  return scenario.steps.map((step, index) => {
    const mutation = step.mutation;
    if (step.action === "wait_for" && mutation !== "none") throw new ContractError("E_WAIT_MUTATION_INVALID", "Android wait_for steps must be read-only", `$.steps[${index}].mutation`);
    // Mutation-capable steps are never retried; read-only steps follow the configured read-only policy.
    const { retryPolicy, maxAttempts } = mutation === "none" ? readOnlyRetry(config) : { retryPolicy: "never", maxAttempts: 1 };
    return {
      id: step.id,
      action: step.action,
      description: step.description,
      mutation,
      arguments: cloneJson(step.arguments ?? null),
      provider_args: providerArgs(step, index, config),
      timeout_ms: stepTimeout(config, step.action),
      retry_policy: retryPolicy,
      max_attempts: maxAttempts,
      provider_defaults_version: config.defaults_version,
    };
  });
}

function compileEvidencePlan(scenario, config) {
  const stepIds = new Set(scenario.steps.map((step) => step.id));
  return scenario.oracle.rules.map((rule, index) => {
    const collector = config.evidence_collectors?.[rule.id];
    assertPlainObject(collector, "E_EVIDENCE_COLLECTOR_REQUIRED", `$.evidence_collectors.${rule.id}`, `collector for ${rule.id} is required`);
    if (collector.kind !== rule.evidence_kind || !["locator_result", "structured_log"].includes(collector.kind)) {
      throw new ContractError("E_EVIDENCE_KIND_UNSUPPORTED", "P3 MVP collects locator_result or structured_log only", `$.evidence_collectors.${rule.id}.kind`);
    }
    if (!stepIds.has(collector.after_step_id)) throw new ContractError("E_EVIDENCE_STEP_UNKNOWN", "collector after_step_id must reference a step", `$.evidence_collectors.${rule.id}.after_step_id`);
    if (collector.kind === "locator_result" && scenario.steps.find((step) => step.id === collector.after_step_id)?.action !== "wait_for") {
      throw new ContractError("E_EVIDENCE_STEP_INVALID", "locator_result must follow a wait_for step", `$.evidence_collectors.${rule.id}.after_step_id`);
    }
    return { oracle_rule_id: rule.id, evidence_kind: rule.evidence_kind, after_step_id: collector.after_step_id, collector: { source: "native_step_result" }, sequence: index + 1 };
  });
}

function validateApproval(approval, planHash, mutationIds, environment) {
  assertPlainObject(approval, "E_APPROVAL_REQUIRED", "$.approval_ref", "Android execution requires an external approval record");
  for (const field of ["id", "record_sha256", "plan_sha256", "provider_plan_hash", "runtime_binding_sha256", "environment", "scope", "approved_by_ref"]) {
    requireNonEmptyString(approval[field], "E_APPROVAL_INVALID", `$.approval_ref.${field}`, `${field} is required`);
  }
  for (const field of ["record_sha256", "plan_sha256", "provider_plan_hash", "runtime_binding_sha256"]) {
    if (!HASH.test(approval[field])) throw new ContractError("E_APPROVAL_HASH_INVALID", `${field} must be a SHA-256 value`, `$.approval_ref.${field}`);
  }
  if (approval.plan_sha256 !== planHash || JSON.stringify(approval.approved_step_ids) !== JSON.stringify(mutationIds) || approval.environment !== environment) {
    throw new ContractError("E_APPROVAL_SCOPE_MISMATCH", "approval must bind the exact plan, mutation scope, and environment", "$.approval_ref");
  }
  if (!["single_run", "runbook_revision"].includes(approval.scope)) throw new ContractError("E_APPROVAL_SCOPE_INVALID", "approval scope is unsupported", "$.approval_ref.scope");
  return cloneJson(approval);
}

export function compileAndroidRunbook({ scenario, config, approval = null, allowUnapprovedPreflight = false }) {
  validateScenario(scenario);
  validateConfig(config);
  const steps = compileSteps(scenario, config);
  const runbook = {
    schema_version: "runbook-v1",
    runbook_state: approval === null ? "preflight" : "executable",
    runbook_id: config.runbook_id,
    scenario_id: scenario.id,
    spec_version: scenario.spec_version,
    scenario_hash: sha256Json(scenario),
    source_refs: cloneJson(scenario.source_refs),
    review_status: scenario.review_status,
    method: scenario.method,
    execution: cloneJson(scenario.execution),
    target: cloneJson(scenario.target),
    runner_provider: "native-android",
    provider_binding: { contract_version: config.provider_contract_version, implementation_version: config.implementation_version, defaults_version: config.defaults_version },
    project_config_sha256: sha256Json(config),
    preconditions: cloneJson(scenario.preconditions),
    fixture: cloneJson(scenario.fixture),
    steps,
    expected: cloneJson(scenario.expected),
    oracle: cloneJson(scenario.oracle),
    mutation_policy: cloneJson(scenario.mutation_policy),
    evidence_plan: compileEvidencePlan(scenario, config),
    integrity: { plan_sha256: "" },
    approval_ref: null,
  };
  runbook.integrity.plan_sha256 = runbookPlanHash(runbook);
  const mutationIds = steps.filter((step) => step.mutation !== "none").map((step) => step.id);
  if (approval === null && allowUnapprovedPreflight) return runbook;
  if (approval === null) throw new ContractError("E_APPROVAL_REQUIRED", "Android runbook requires provider preflight approval", "$.approval_ref", { plan_sha256: runbook.integrity.plan_sha256, approved_step_ids: mutationIds, environment: scenario.fixture.environment });
  runbook.approval_ref = validateApproval(approval, runbook.integrity.plan_sha256, mutationIds, scenario.fixture.environment);
  return runbook;
}

async function main() {
  const options = parseCli(process.argv.slice(2), {
    "--scenario": { name: "scenario", required: true },
    "--config": { name: "config", required: true },
    "--approval": { name: "approval" },
    "--preflight": { name: "preflight", boolean: true },
    "--output": { name: "output", required: true },
  });
  const runbook = compileAndroidRunbook({ scenario: await readJson(options.scenario), config: await readJson(options.config), approval: options.approval ? await readJson(options.approval) : null, allowUnapprovedPreflight: options.preflight === true });
  await writeJson(options.output, runbook);
  process.stdout.write(`${JSON.stringify({ valid: true, output: options.output, plan_sha256: runbook.integrity.plan_sha256 })}\n`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => { printContractError(error); process.exitCode = 1; });
}
