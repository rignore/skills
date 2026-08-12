#!/usr/bin/env node

import { pathToFileURL } from "node:url";
import {
  ContractError,
  assertPlainObject,
  assertSecretFree,
  canonicalJson,
  cloneJson,
  isPlainObject,
  jsonPointerGet,
  parseCli,
  printContractError,
  readJson,
  requireNonEmptyString,
  sha256Bytes,
  sha256Json,
  writeJson,
} from "./web-provider-lib.mjs";

const JUDGE_VERSION = "1.0.0";
const HASH_PATTERN = /^sha256:[0-9a-f]{64}$/;
const EVIDENCE_KINDS = new Set([
  "structured_log", "dom_state", "accessibility_state", "ui_hierarchy",
  "locator_result", "network_error", "console_error", "url_state",
  "api_state", "storage_state", "db_state", "test_command",
  "android_logcat", "build_hash", "artifact_hash",
]);
const VERDICTS = new Set([
  "pass", "fail", "conflict", "insufficient_evidence", "blocked", "unsupported",
]);

function requireArray(value, code, contractPath, message) {
  if (!Array.isArray(value)) throw new ContractError(code, message, contractPath);
  return value;
}

function normalizeSourceText(value) {
  const lines = value.normalize("NFC").replaceAll("\r\n", "\n").replaceAll("\r", "\n").split("\n").map((line) => line.replace(/[ \t]+$/u, ""));
  while (lines[0] === "") lines.shift();
  while (lines.at(-1) === "") lines.pop();
  return lines.join("\n");
}

export function sourceContentHash(source) {
  assertPlainObject(source, "E_SOURCE_INVALID", "$.sources[]", "source must be an object");
  const anchors = requireArray(source.anchors, "E_SOURCE_INVALID", "$.sources[].anchors", "source anchors must be an array").map((anchor) => {
    assertPlainObject(anchor, "E_SOURCE_INVALID", "$.sources[].anchors[]", "anchor must be an object");
    const projection = {
      id: requireNonEmptyString(anchor.id, "E_SOURCE_INVALID", "$.sources[].anchors[].id", "anchor id is required"),
      kind: requireNonEmptyString(anchor.kind, "E_SOURCE_INVALID", "$.sources[].anchors[].kind", "anchor kind is required"),
      title: normalizeSourceText(requireNonEmptyString(anchor.title, "E_SOURCE_INVALID", "$.sources[].anchors[].title", "anchor title is required")),
      statement: normalizeSourceText(requireNonEmptyString(anchor.statement, "E_SOURCE_INVALID", "$.sources[].anchors[].statement", "anchor statement is required")),
      status: requireNonEmptyString(anchor.status, "E_SOURCE_INVALID", "$.sources[].anchors[].status", "anchor status is required"),
    };
    if ("source_locator" in anchor) {
      if (typeof anchor.source_locator !== "string") throw new ContractError("E_SOURCE_INVALID", "source_locator must be a string when present", "$.sources[].anchors[].source_locator");
      projection.source_locator = normalizeSourceText(anchor.source_locator);
    }
    return projection;
  }).sort((left, right) => left.id.localeCompare(right.id));
  const projection = {
    id: requireNonEmptyString(source.id, "E_SOURCE_INVALID", "$.sources[].id", "source id is required"),
    kind: requireNonEmptyString(source.kind, "E_SOURCE_INVALID", "$.sources[].kind", "source kind is required"),
    title: normalizeSourceText(requireNonEmptyString(source.title, "E_SOURCE_INVALID", "$.sources[].title", "source title is required")),
    version: requireNonEmptyString(source.version, "E_SOURCE_INVALID", "$.sources[].version", "source version is required"),
    anchors,
  };
  return sha256Bytes(Buffer.from(`${canonicalJson(projection)}\n`, "utf8"));
}

function sourceIndex(bundle) {
  if (bundle?.schema_version !== "spec-bundle-v1") throw new ContractError("E_BUNDLE_SCHEMA", "bundle must be spec-bundle-v1", "$.schema_version");
  const sources = requireArray(bundle.sources, "E_BUNDLE_SOURCES", "$.sources", "bundle sources must be an array");
  const index = new Map();
  for (const source of sources) {
    if (index.has(source.id)) throw new ContractError("E_SOURCE_DUPLICATE", "source ids must be unique", "$.sources");
    const computed = sourceContentHash(source);
    if (source.content_hash !== computed) throw new ContractError("E_SOURCE_HASH_MISMATCH", "source content hash does not match canonical source content", `$.sources.${source.id}.content_hash`);
    const anchors = new Map();
    for (const anchor of source.anchors) {
      if (anchors.has(anchor.id)) throw new ContractError("E_ANCHOR_DUPLICATE", "anchor ids must be unique within a source", `$.sources.${source.id}.anchors`);
      anchors.set(anchor.id, anchor);
    }
    index.set(source.id, { source, anchors });
  }
  return index;
}

function resolveSourceRefs(refs, sources, contractPath) {
  return requireArray(refs, "E_SOURCE_REFS_INVALID", contractPath, "source_refs must be an array").map((ref, index) => {
    assertPlainObject(ref, "E_SOURCE_REF_INVALID", `${contractPath}[${index}]`, "source reference must be an object");
    const sourceEntry = sources.get(ref.source_id);
    const anchor = sourceEntry?.anchors.get(ref.anchor_id);
    if (!sourceEntry || !anchor) throw new ContractError("E_SOURCE_REF_UNRESOLVED", "source reference must resolve exactly", `${contractPath}[${index}]`);
    return { ref: { source_id: ref.source_id, anchor_id: ref.anchor_id }, source: sourceEntry.source, anchor };
  });
}

function validateFrozenInputs(bundle, scenario, runbook, runnerOutput) {
  const sources = sourceIndex(bundle);
  if (scenario?.schema_version !== "scenario-v1") throw new ContractError("E_SCENARIO_SCHEMA", "scenario must be scenario-v1", "$.schema_version");
  if (runbook?.schema_version !== "runbook-v1") throw new ContractError("E_RUNBOOK_SCHEMA", "runbook must be runbook-v1", "$.schema_version");
  if (runnerOutput?.schema_version !== "runner-output-v1") throw new ContractError("E_RUNNER_OUTPUT_SCHEMA", "runner output must be runner-output-v1", "$.schema_version");
  if (bundle.spec_version !== scenario.spec_version || scenario.spec_version !== runbook.spec_version || runbook.spec_version !== runnerOutput.spec_version) {
    throw new ContractError("E_SPEC_VERSION_MISMATCH", "bundle, scenario, runbook, and runner output spec versions must match");
  }
  const scenarioHash = sha256Json(scenario);
  const runbookHash = sha256Json(runbook);
  if (runbook.scenario_hash !== scenarioHash || runnerOutput.scenario_hash !== scenarioHash) throw new ContractError("E_SCENARIO_HASH_MISMATCH", "scenario hash binding failed");
  if (runnerOutput.runbook_hash !== runbookHash) throw new ContractError("E_RUNBOOK_HASH_MISMATCH", "runner output runbook hash binding failed");
  for (const [field, expected] of Object.entries({ scenario_id: scenario.id, runbook_id: runbook.runbook_id, target: scenario.target, runner_provider: scenario.runner_provider })) {
    if (canonicalJson(runnerOutput[field]) !== canonicalJson(expected)) throw new ContractError("E_RUNNER_IDENTITY_MISMATCH", `runner output ${field} differs from frozen input`, `$.${field}`);
  }
  if (canonicalJson(runbook.oracle) !== canonicalJson(scenario.oracle) || canonicalJson(runbook.expected) !== canonicalJson(scenario.expected)) {
    throw new ContractError("E_RUNBOOK_ORACLE_MISMATCH", "runbook must preserve scenario expected and oracle");
  }
  resolveSourceRefs(scenario.source_refs, sources, "$.scenario.source_refs");
  return { sources, scenarioHash, runbookHash };
}

function validateEvidence(evidence) {
  const items = requireArray(evidence, "E_EVIDENCE_INVALID", "$.evidence", "evidence must be an array");
  const byId = new Map();
  for (const [index, item] of items.entries()) {
    const itemPath = `$.evidence[${index}]`;
    assertPlainObject(item, "E_EVIDENCE_INVALID", itemPath, "evidence item must be an object");
    requireNonEmptyString(item.id, "E_EVIDENCE_ID", `${itemPath}.id`, "evidence id is required");
    if (byId.has(item.id)) throw new ContractError("E_EVIDENCE_ID_DUPLICATE", "evidence ids must be unique", `${itemPath}.id`);
    if (!EVIDENCE_KINDS.has(item.kind)) throw new ContractError("E_EVIDENCE_KIND_UNSUPPORTED", "unsupported or self-reported evidence kind", `${itemPath}.kind`);
    if (!isPlainObject(item.producer) || !["runner", "developer_test", "api_probe", "db_probe", "build_system", "adapter", "human"].includes(item.producer.type)) {
      throw new ContractError("E_EVIDENCE_PRODUCER_INVALID", "evidence producer is not admissible", `${itemPath}.producer`);
    }
    const hasRecord = Object.hasOwn(item, "record");
    const hasArtifact = Object.hasOwn(item, "artifact_ref");
    if (hasRecord === hasArtifact) throw new ContractError("E_EVIDENCE_PAYLOAD_INVALID", "evidence needs exactly one of record or artifact_ref", itemPath);
    if (!HASH_PATTERN.test(item.sha256)) throw new ContractError("E_EVIDENCE_HASH_INVALID", "evidence hash is invalid", `${itemPath}.sha256`);
    if (hasRecord && sha256Json(item.record) !== item.sha256) throw new ContractError("E_EVIDENCE_HASH_MISMATCH", "evidence record hash does not match", `${itemPath}.sha256`);
    if (hasArtifact && (typeof item.artifact_ref !== "string" || item.artifact_ref.startsWith("/") || item.artifact_ref.split("/").includes(".."))) {
      throw new ContractError("E_ARTIFACT_REF_INVALID", "artifact_ref must be a result-relative path", `${itemPath}.artifact_ref`);
    }
    byId.set(item.id, item);
  }
  assertSecretFree(items, "$.evidence");
  return byId;
}

function parseUtcTimestamp(value, contractPath) {
  if (typeof value !== "string" || !value.endsWith("Z") || Number.isNaN(Date.parse(value))) {
    throw new ContractError("E_TIMESTAMP_INVALID", "timestamp must be RFC 3339 UTC", contractPath);
  }
  return Date.parse(value);
}

function validateRunnerExecution(runnerOutput, evidenceById) {
  assertPlainObject(runnerOutput.execution, "E_EXECUTION_INVALID", "$.execution", "runner execution must be an object");
  if (!["not_started", "partial", "completed"].includes(runnerOutput.execution.status)) throw new ContractError("E_EXECUTION_STATUS_INVALID", "runner execution status is invalid", "$.execution.status");
  if (!Number.isInteger(runnerOutput.execution.attempt) || runnerOutput.execution.attempt < 1) throw new ContractError("E_EXECUTION_ATTEMPT_INVALID", "runner execution attempt must be positive", "$.execution.attempt");
  if (!Number.isInteger(runnerOutput.execution.retry_count) || runnerOutput.execution.retry_count < 0) throw new ContractError("E_EXECUTION_RETRY_INVALID", "runner retry_count must be non-negative", "$.execution.retry_count");
  const command = evidenceById.get(runnerOutput.execution.command_evidence_ref);
  if (!command || !["test_command", "structured_log"].includes(command.kind)) throw new ContractError("E_COMMAND_EVIDENCE_REQUIRED", "command_evidence_ref must resolve to command evidence", "$.execution.command_evidence_ref");
  const started = parseUtcTimestamp(runnerOutput.started_at, "$.started_at");
  const finished = parseUtcTimestamp(runnerOutput.finished_at, "$.finished_at");
  if (finished < started) throw new ContractError("E_TIMESTAMP_ORDER_INVALID", "runner finished_at precedes started_at", "$.finished_at");
  for (const field of ["step_results", "errors", "missing_evidence", "diagnostic_attachments"]) requireArray(runnerOutput[field], "E_RUNNER_OUTPUT_FIELD", `$.${field}`, `${field} must be an array`);
}

function evidenceCandidates(rule, runbook, runnerOutput, evidenceById) {
  const plan = runbook.evidence_plan?.find((item) => item.oracle_rule_id === rule.id);
  let ids = [];
  if (plan?.after_step_id) {
    const stepResult = runnerOutput.step_results?.find((item) => item.step_id === plan.after_step_id);
    ids = Array.isArray(stepResult?.evidence_refs) ? stepResult.evidence_refs : [];
  } else {
    ids = [...evidenceById.keys()];
  }
  return ids.map((id) => evidenceById.get(id)).filter((item) => item?.kind === rule.evidence_kind);
}

function contains(actual, expected) {
  if (typeof actual === "string" && typeof expected === "string") return actual.includes(expected);
  if (Array.isArray(actual)) return actual.some((item) => canonicalJson(item) === canonicalJson(expected));
  if (isPlainObject(actual) && typeof expected === "string") return Object.hasOwn(actual, expected);
  return false;
}

export function evaluateDeterministicRule(rule, evidenceItems) {
  if (!Array.isArray(evidenceItems) || evidenceItems.length === 0) {
    return { status: "not_evaluated", evidence_refs: [], actual: null, reason: `No admissible ${rule.evidence_kind} evidence was collected.` };
  }
  if (evidenceItems.length !== 1) {
    return { status: "not_evaluated", evidence_refs: evidenceItems.map((item) => item.id), actual: null, reason: `The oracle evidence selector resolved ${evidenceItems.length} records; exactly one is required.` };
  }
  const evidence = evidenceItems[0];
  if (!Object.hasOwn(evidence, "record")) {
    return { status: "not_evaluated", evidence_refs: [evidence.id], actual: null, reason: "The deterministic evaluator cannot dereference artifact_ref evidence." };
  }
  let actual;
  try {
    actual = jsonPointerGet(evidence.record, rule.actual_path);
  } catch (error) {
    return { status: "not_evaluated", evidence_refs: [evidence.id], actual: null, reason: `Invalid actual_path: ${error.message}` };
  }
  let matched;
  switch (rule.operator) {
    case "equals": matched = canonicalJson(actual) === canonicalJson(rule.value); break;
    case "not_equals": matched = canonicalJson(actual) !== canonicalJson(rule.value); break;
    case "contains": matched = contains(actual, rule.value); break;
    case "exists": matched = actual !== undefined; break;
    case "absent": matched = actual === undefined; break;
    case "status_code": matched = Number.isInteger(actual) && actual === rule.value; break;
    case "matches_regex": {
      try { matched = typeof actual === "string" && new RegExp(rule.value, "u").test(actual); }
      catch (error) { return { status: "not_evaluated", evidence_refs: [evidence.id], actual: actual ?? null, reason: `Invalid oracle regex: ${error.message}` }; }
      break;
    }
    default:
      return { status: "not_evaluated", evidence_refs: [evidence.id], actual: actual ?? null, reason: `Unsupported deterministic operator: ${rule.operator}` };
  }
  return {
    status: matched ? "matched" : "mismatched",
    evidence_refs: [evidence.id],
    actual: actual ?? null,
    reason: matched ? null : `Observed value did not satisfy operator ${rule.operator}.`,
  };
}

function normalizeMissingEvidence(runnerOutput, oracleResults, scenario) {
  const byOracle = new Map();
  for (const item of runnerOutput.missing_evidence ?? []) {
    const oracleId = item.oracle_id ?? item.oracle_rule_id;
    if (typeof oracleId === "string") byOracle.set(oracleId, { oracle_id: oracleId, evidence_kind: item.evidence_kind, reason: item.reason });
  }
  for (const result of oracleResults) {
    if (result.status !== "not_evaluated" || byOracle.has(result.oracle_id)) continue;
    const rule = scenario.oracle.rules.find((item) => item.id === result.oracle_id);
    byOracle.set(result.oracle_id, { oracle_id: result.oracle_id, evidence_kind: rule.evidence_kind, reason: result.reason });
  }
  return [...byOracle.values()];
}

function blockersFromRunner(runnerOutput) {
  if (!["not_started", "partial"].includes(runnerOutput.execution?.status)) return [];
  const errors = Array.isArray(runnerOutput.errors) ? runnerOutput.errors : [];
  if (errors.length === 0) return [{ code: "E_EXECUTION_INCOMPLETE", description: "Runner execution did not complete.", evidence_refs: [] }];
  return errors.map((error) => ({
    code: typeof error.code === "string" ? error.code : "E_RUNNER_BLOCKED",
    description: typeof error.message === "string" && error.message ? error.message : "Runner execution was blocked.",
    evidence_refs: Array.isArray(error.evidence_refs) ? error.evidence_refs : [],
  }));
}

export function decideVerdict({ executionStatus, conflicts, blockers, oracleResults, missingEvidence, unsupportedReason }) {
  if (conflicts.length > 0) return "conflict";
  if (executionStatus === "not_started" && typeof unsupportedReason === "string" && unsupportedReason) return "unsupported";
  if (["not_started", "partial"].includes(executionStatus) && blockers.length > 0) return "blocked";
  if (oracleResults.some((item) => item.status === "mismatched")) return "fail";
  if (oracleResults.some((item) => item.status === "not_evaluated") || missingEvidence.length > 0) return "insufficient_evidence";
  if (executionStatus === "completed" && oracleResults.length > 0 && oracleResults.every((item) => item.status === "matched")) return "pass";
  return "blocked";
}

function validateConflicts(value, sources) {
  if (value === null || value === undefined) return [];
  if (value.schema_version !== "source-conflicts-v1") throw new ContractError("E_CONFLICT_SCHEMA", "conflict input must be source-conflicts-v1", "$.schema_version");
  const ids = new Set();
  return requireArray(value.conflicts, "E_CONFLICTS_INVALID", "$.conflicts", "conflicts must be an array").map((item, index) => {
    assertPlainObject(item, "E_CONFLICT_INVALID", `$.conflicts[${index}]`, "conflict must be an object");
    requireNonEmptyString(item.id, "E_CONFLICT_INVALID", `$.conflicts[${index}].id`, "conflict id is required");
    if (ids.has(item.id)) throw new ContractError("E_CONFLICT_DUPLICATE", "conflict ids must be unique", `$.conflicts[${index}].id`);
    ids.add(item.id);
    requireNonEmptyString(item.description, "E_CONFLICT_INVALID", `$.conflicts[${index}].description`, "conflict description is required");
    const refs = resolveSourceRefs(item.source_refs, sources, `$.conflicts[${index}].source_refs`).map((entry) => entry.ref);
    const distinctRefs = new Set(refs.map((ref) => `${ref.source_id}\u0000${ref.anchor_id}`));
    if (distinctRefs.size < 2) throw new ContractError("E_CONFLICT_REFS_REQUIRED", "conflict needs at least two distinct source references", `$.conflicts[${index}].source_refs`);
    return { id: item.id, description: item.description, source_refs: refs };
  });
}

function modelIdentity(responses, rubricHash) {
  const identities = responses.map((item) => item.model);
  if (identities.length === 0) return null;
  const first = identities[0];
  assertPlainObject(first, "E_SEMANTIC_MODEL_REQUIRED", "$.responses[0].model", "semantic response model identity is required");
  const modelKeys = ["model_version", "prompt_version", "provider", "rubric_hash"];
  if (canonicalJson(Object.keys(first).sort()) !== canonicalJson(modelKeys)) throw new ContractError("E_SEMANTIC_MODEL_FIELDS", "semantic model identity has an unexpected field");
  for (const field of ["provider", "model_version", "prompt_version"]) requireNonEmptyString(first[field], "E_SEMANTIC_MODEL_REQUIRED", `$.responses[0].model.${field}`, `${field} is required`);
  if (first.rubric_hash !== rubricHash) throw new ContractError("E_SEMANTIC_RUBRIC_HASH_MISMATCH", "semantic response rubric hash differs from frozen batch");
  if (identities.some((item) => canonicalJson(item) !== canonicalJson(first))) throw new ContractError("E_SEMANTIC_MODEL_MIXED", "one result attempt must use one immutable semantic model identity");
  return cloneJson(first);
}

export function prepareSemanticBatch({ bundle, scenario, runbook, runnerOutput }) {
  const { sources } = validateFrozenInputs(bundle, scenario, runbook, runnerOutput);
  if (scenario.oracle?.mode !== "semantic") throw new ContractError("E_SEMANTIC_MODE_REQUIRED", "scenario oracle mode must be semantic", "$.oracle.mode");
  const evidenceById = validateEvidence(runnerOutput.evidence);
  validateRunnerExecution(runnerOutput, evidenceById);
  const expectations = new Map(scenario.expected.map((item) => [item.id, item]));
  const rubricHash = sha256Json(scenario.oracle.rules.map((rule) => ({ oracle_id: rule.id, rubric: rule.rubric })));
  const requests = [];
  for (const rule of scenario.oracle.rules) {
    const expectation = expectations.get(rule.expectation_id);
    if (!expectation) throw new ContractError("E_EXPECTATION_UNRESOLVED", "semantic rule expectation does not resolve", `$.oracle.${rule.id}`);
    const resolvedSources = resolveSourceRefs(expectation.source_refs, sources, `$.expected.${expectation.id}.source_refs`);
    const evidence = evidenceCandidates(rule, runbook, runnerOutput, evidenceById);
    if (resolvedSources.length === 0 || evidence.length !== 1) continue;
    const payload = {
      schema_version: "semantic-judge-request-v1",
      request_id: `${runnerOutput.run_id}.${rule.id}`,
      oracle_id: rule.id,
      expectation_id: expectation.id,
      source_refs: resolvedSources.map(({ ref, source, anchor }) => ({ ...ref, source_content_hash: source.content_hash, statement: anchor.statement })),
      expected: expectation.description,
      rubric: rule.rubric,
      evidence: evidence.map((item) => cloneJson(item)),
      rubric_hash: rubricHash,
    };
    requests.push({ ...payload, input_sha256: sha256Json(payload) });
  }
  const batchPayload = { schema_version: "semantic-judge-batch-v1", requests, rubric_hash: rubricHash };
  const batch = { ...batchPayload, batch_sha256: sha256Json(batchPayload) };
  assertSecretFree(batch);
  return batch;
}

function semanticOracleResults({ batch, responsesDocument, scenario, runbook, runnerOutput, evidenceById, sources }) {
  if (responsesDocument?.schema_version !== "semantic-judge-response-batch-v1") throw new ContractError("E_SEMANTIC_RESPONSE_SCHEMA", "semantic responses must use semantic-judge-response-batch-v1");
  if (canonicalJson(Object.keys(responsesDocument).sort()) !== canonicalJson(["batch_sha256", "responses", "schema_version"])) throw new ContractError("E_SEMANTIC_RESPONSE_FIELDS", "semantic response batch has an unexpected field");
  if (responsesDocument.batch_sha256 !== batch.batch_sha256) throw new ContractError("E_SEMANTIC_BATCH_HASH_MISMATCH", "semantic responses do not bind the frozen request batch");
  const responses = requireArray(responsesDocument.responses, "E_SEMANTIC_RESPONSES_INVALID", "$.responses", "semantic responses must be an array");
  const byRequest = new Map();
  for (const response of responses) {
    const responseKeys = ["actual", "evidence_refs", "input_sha256", "model", "reason", "request_id", "source_refs", "status"];
    if (!isPlainObject(response) || canonicalJson(Object.keys(response).sort()) !== canonicalJson(responseKeys)) throw new ContractError("E_SEMANTIC_RESPONSE_FIELDS", "semantic response has an unexpected or missing field");
    if (byRequest.has(response.request_id)) throw new ContractError("E_SEMANTIC_RESPONSE_DUPLICATE", "semantic request has duplicate responses");
    byRequest.set(response.request_id, response);
  }
  const requestByOracle = new Map(batch.requests.map((request) => [request.oracle_id, request]));
  const results = [];
  for (const rule of scenario.oracle.rules) {
    const expectation = scenario.expected.find((item) => item.id === rule.expectation_id);
    const request = requestByOracle.get(rule.id);
    if (!request) {
      const sourceRefs = resolveSourceRefs(expectation.source_refs, sources, `$.expected.${expectation.id}.source_refs`).map((item) => item.ref);
      const candidates = evidenceCandidates(rule, runbook, runnerOutput, evidenceById);
      results.push({ oracle_id: rule.id, expectation_id: expectation.id, status: "not_evaluated", evidence_refs: candidates.map((item) => item.id), source_refs: sourceRefs, actual: null, reason: candidates.length === 0 ? `No admissible ${rule.evidence_kind} evidence was collected.` : "The semantic evidence selector did not resolve exactly one record." });
      continue;
    }
    const response = byRequest.get(request.request_id);
    if (!response || response.input_sha256 !== request.input_sha256) throw new ContractError("E_SEMANTIC_RESPONSE_MISSING", "every semantic request needs a hash-bound response", `$.responses.${request.request_id}`);
    if (!["matched", "mismatched", "not_evaluated"].includes(response.status)) throw new ContractError("E_SEMANTIC_STATUS_INVALID", "semantic status is invalid");
    const allowedEvidence = new Set(request.evidence.map((item) => item.id));
    const evidenceRefs = requireArray(response.evidence_refs, "E_SEMANTIC_EVIDENCE_REFS", "$.responses[].evidence_refs", "semantic evidence_refs must be an array");
    if (evidenceRefs.some((id) => !allowedEvidence.has(id))) throw new ContractError("E_SEMANTIC_EVIDENCE_SCOPE", "semantic response cited evidence outside its request");
    const allowedSources = new Set(request.source_refs.map((ref) => `${ref.source_id}\u0000${ref.anchor_id}`));
    const sourceRefs = requireArray(response.source_refs, "E_SEMANTIC_SOURCE_REFS", "$.responses[].source_refs", "semantic source_refs must be an array");
    if (sourceRefs.some((ref) => !allowedSources.has(`${ref.source_id}\u0000${ref.anchor_id}`))) throw new ContractError("E_SEMANTIC_SOURCE_SCOPE", "semantic response cited a source outside its request");
    if (["matched", "mismatched"].includes(response.status) && (evidenceRefs.length === 0 || sourceRefs.length === 0)) throw new ContractError("E_SEMANTIC_CITATION_REQUIRED", "evaluated semantic responses require source and evidence citations");
    requireNonEmptyString(response.reason, "E_SEMANTIC_REASON_REQUIRED", "$.responses[].reason", "semantic response reason is required");
    results.push({ oracle_id: rule.id, expectation_id: expectation.id, status: response.status, evidence_refs: cloneJson(evidenceRefs), source_refs: cloneJson(sourceRefs), actual: response.actual ?? null, reason: response.reason });
  }
  if (byRequest.size !== batch.requests.length) throw new ContractError("E_SEMANTIC_RESPONSE_EXTRA", "semantic responses contain an unknown or extra request");
  return { results, model: modelIdentity(responses, batch.rubric_hash) };
}

export function judgeRunnerOutput({ bundle, scenario, runbook, runnerOutput, semanticResponses = null, conflictInput = null, decidedAt = new Date().toISOString(), judgeAttempt = 1 }) {
  const { sources, scenarioHash, runbookHash } = validateFrozenInputs(bundle, scenario, runbook, runnerOutput);
  const evidenceById = validateEvidence(runnerOutput.evidence);
  validateRunnerExecution(runnerOutput, evidenceById);
  if (!Number.isInteger(judgeAttempt) || judgeAttempt < 1) throw new ContractError("E_JUDGE_ATTEMPT_INVALID", "judge attempt must be positive", "$.judge.attempt");
  const decisionTime = parseUtcTimestamp(decidedAt, "$.judge.decided_at");
  if (decisionTime < parseUtcTimestamp(runnerOutput.started_at, "$.started_at")) throw new ContractError("E_TIMESTAMP_ORDER_INVALID", "judge decision precedes execution start", "$.judge.decided_at");
  const conflicts = validateConflicts(conflictInput, sources);
  let oracleResults;
  let model = null;
  let judgeMode = "deterministic";
  if (scenario.oracle.mode === "deterministic") {
    if (semanticResponses) throw new ContractError("E_SEMANTIC_RESPONSES_UNEXPECTED", "deterministic scenarios must not accept semantic responses");
    oracleResults = scenario.oracle.rules.map((rule) => {
      const evaluated = evaluateDeterministicRule(rule, evidenceCandidates(rule, runbook, runnerOutput, evidenceById));
      return { oracle_id: rule.id, expectation_id: rule.expectation_id, ...evaluated, source_refs: [] };
    });
  } else if (scenario.oracle.mode === "semantic") {
    const batch = prepareSemanticBatch({ bundle, scenario, runbook, runnerOutput });
    if (batch.requests.length === 0) {
      if (semanticResponses) throw new ContractError("E_SEMANTIC_RESPONSES_UNEXPECTED", "no semantic response is allowed when no request was emitted");
      oracleResults = scenario.oracle.rules.map((rule) => {
        const expectation = scenario.expected.find((item) => item.id === rule.expectation_id);
        const sourceRefs = resolveSourceRefs(expectation.source_refs, sources, `$.expected.${expectation.id}.source_refs`).map((item) => item.ref);
        const candidates = evidenceCandidates(rule, runbook, runnerOutput, evidenceById);
        return { oracle_id: rule.id, expectation_id: expectation.id, status: "not_evaluated", evidence_refs: candidates.map((item) => item.id), source_refs: sourceRefs, actual: null, reason: candidates.length === 0 ? `No admissible ${rule.evidence_kind} evidence was collected.` : "The semantic evidence selector did not resolve exactly one record." };
      });
    } else {
      if (!semanticResponses) throw new ContractError("E_SEMANTIC_RESPONSES_REQUIRED", "semantic scenarios require an isolated response batch");
      ({ results: oracleResults, model } = semanticOracleResults({ batch, responsesDocument: semanticResponses, scenario, runbook, runnerOutput, evidenceById, sources }));
      judgeMode = "semantic";
    }
  } else {
    throw new ContractError("E_JUDGE_MODE_UNSUPPORTED", "P4 automated judge supports deterministic and semantic oracle modes", "$.oracle.mode");
  }
  const blockers = blockersFromRunner(runnerOutput);
  const missingEvidence = normalizeMissingEvidence(runnerOutput, oracleResults, scenario);
  const verdict = decideVerdict({ executionStatus: runnerOutput.execution.status, conflicts, blockers, oracleResults, missingEvidence, unsupportedReason: runnerOutput.unsupported_reason });
  const referencedSourceIds = new Set(scenario.source_refs.map((ref) => ref.source_id));
  for (const conflict of conflicts) for (const ref of conflict.source_refs) referencedSourceIds.add(ref.source_id);
  const sourceHashes = [...referencedSourceIds].map((id) => sources.get(id).source.content_hash).sort();
  const result = {
    schema_version: "result-v1",
    run_id: runnerOutput.run_id,
    scenario_id: scenario.id,
    spec_version: scenario.spec_version,
    scenario_hash: scenarioHash,
    runbook_id: runbook.runbook_id,
    runbook_hash: runbookHash,
    target: cloneJson(scenario.target),
    runner_provider: scenario.runner_provider,
    started_at: runnerOutput.started_at,
    finished_at: decidedAt,
    verdict,
    execution: cloneJson(runnerOutput.execution),
    subject: { build: cloneJson(runnerOutput.subject?.build ?? null), artifact: cloneJson(runnerOutput.subject?.artifact ?? null), native_runtime: cloneJson(runnerOutput.subject?.native_runtime ?? null) },
    judge: { mode: judgeMode, name: "independent-judge", version: JUDGE_VERSION, attempt: judgeAttempt, model, source_hashes: sourceHashes, evidence_hashes: [...evidenceById.values()].map((item) => item.sha256).sort(), decided_at: decidedAt },
    evidence: cloneJson(runnerOutput.evidence),
    oracle_results: oracleResults,
    blockers: verdict === "blocked" ? blockers : [],
    conflicts: verdict === "conflict" ? conflicts : [],
    missing_evidence: verdict === "insufficient_evidence" ? missingEvidence : [],
    unsupported_reason: verdict === "unsupported" ? runnerOutput.unsupported_reason : null,
    diagnostic_attachments: cloneJson(runnerOutput.diagnostic_attachments ?? []),
  };
  if (!VERDICTS.has(result.verdict)) throw new ContractError("E_VERDICT_INVALID", "judge produced an invalid verdict");
  assertSecretFree(result);
  return result;
}

async function main() {
  const options = parseCli(process.argv.slice(2), {
    "--bundle": { name: "bundle", required: true },
    "--scenario": { name: "scenario", required: true },
    "--runbook": { name: "runbook", required: true },
    "--runner-output": { name: "runner_output", required: true },
    "--output": { name: "output", required: true },
    "--prepare-semantic": { name: "prepare_semantic", boolean: true },
    "--semantic-responses": { name: "semantic_responses" },
    "--conflicts": { name: "conflicts" },
  });
  const input = {
    bundle: await readJson(options.bundle), scenario: await readJson(options.scenario),
    runbook: await readJson(options.runbook), runnerOutput: await readJson(options.runner_output),
  };
  let output;
  if (options.prepare_semantic) {
    if (options.semantic_responses || options.conflicts) throw new ContractError("E_CLI_USAGE", "--prepare-semantic cannot be combined with response or conflict inputs");
    output = prepareSemanticBatch(input);
  } else {
    output = judgeRunnerOutput({
      ...input,
      semanticResponses: options.semantic_responses ? await readJson(options.semantic_responses) : null,
      conflictInput: options.conflicts ? await readJson(options.conflicts) : null,
    });
  }
  await writeJson(options.output, output);
  process.stdout.write(`${JSON.stringify({ valid: true, output: options.output, schema_version: output.schema_version, verdict: output.verdict ?? null })}\n`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => { printContractError(error); process.exitCode = 1; });
}
