import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  decideVerdict,
  evaluateDeterministicRule,
  judgeRunnerOutput,
  prepareSemanticBatch,
  sourceContentHash,
} from "../judge-results.mjs";
import { runbookPlanHash, sha256Json } from "../web-provider-lib.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const VALIDATOR = path.resolve(HERE, "../validate-contracts.py");
const JUDGE = path.resolve(HERE, "../judge-results.mjs");
const DECIDED_AT = "2026-08-02T04:00:05Z";

function assertValidatorAccepts(input, result) {
  const directory = mkdtempSync(path.join(tmpdir(), "spec-qa-judge-"));
  const paths = Object.fromEntries(Object.entries({ bundle: input.bundle, scenario: input.scenario, runbook: input.runbook, result }).map(([name, document]) => {
    const file = path.join(directory, `${name}.json`);
    writeFileSync(file, `${JSON.stringify(document)}\n`);
    return [name, file];
  }));
  const output = execFileSync("python3", [VALIDATOR, "--bundle", paths.bundle, "--scenario", paths.scenario, "--runbook", paths.runbook, paths.result], { encoding: "utf8" });
  assert.match(output, /result\.json: valid/);
}

function source(id = "ticket-spec", anchorId = "state-ac", statement = "The saved state is visible.") {
  const value = {
    id, kind: "acceptance_criteria", title: "Saved state", version: "1",
    anchors: [{ id: anchorId, kind: "acceptance_criterion", title: "State", statement, status: "approved" }],
  };
  return { ...value, content_hash: sourceContentHash(value) };
}

function fixture({ mode = "deterministic", operator = "equals", value = "saved" } = {}) {
  const primarySource = source();
  const bundle = { schema_version: "spec-bundle-v1", bundle_id: "judge-fixture", spec_version: "spec-1", sources: [primarySource], target_defaults: { platform: "web", device: "desktop" }, extensions: {} };
  const rule = {
    id: "state-rule", kind: mode, expectation_id: "state-expected", evidence_kind: "accessibility_state",
    ...(mode === "deterministic" ? { operator, actual_path: "/state", ...(operator === "exists" || operator === "absent" ? {} : { value }) } : { rubric: "Decide whether the observed state has the same meaning as the required saved state." }),
  };
  const scenario = {
    schema_version: "scenario-v1", id: "web-saved-state", title: "Saved state is visible",
    source_refs: [{ source_id: "ticket-spec", anchor_id: "state-ac" }], method: "web",
    preconditions: [{ id: "fixture-ready", description: "Fixture exists.", verification: "runner", check_ref: "fixture-health" }],
    fixture: { kind: "seed", ref: "fixture://saved", purpose: "baseline", destructive: false, environment: "shared_test" },
    steps: [{ id: "open-state", action: "navigate", description: "Open state page.", mutation: "none", arguments: { route_ref: "saved" } }],
    expected: [{ id: "state-expected", description: "The visible state is saved.", source_refs: [{ source_id: "ticket-spec", anchor_id: "state-ac" }] }],
    oracle: { mode, rules: [rule] }, severity: "high", spec_version: "spec-1", review_status: "approved",
    target: { platform: "web", device: "desktop" }, runner_provider: "web-playwright",
    mutation_policy: { mode: "deny", approval_scope: [], retry_policy: "never" }, execution: { enabled: true },
  };
  const runbook = {
    schema_version: "runbook-v1", runbook_id: "web-saved-state-r1", scenario_id: scenario.id,
    spec_version: scenario.spec_version, scenario_hash: sha256Json(scenario), source_refs: scenario.source_refs,
    review_status: scenario.review_status, method: scenario.method, execution: scenario.execution, target: scenario.target,
    runner_provider: scenario.runner_provider,
    provider_binding: { contract_version: "runner-provider-v1", implementation_version: "web-playwright-1.0.0", defaults_version: "web-defaults-v1" },
    project_config_sha256: `sha256:${"8".repeat(64)}`, preconditions: scenario.preconditions, fixture: scenario.fixture,
    steps: [{ ...scenario.steps[0], provider_args: { url: "https://qa.invalid/saved" }, timeout_ms: 10000, retry_policy: "safe", max_attempts: 2, provider_defaults_version: "web-defaults-v1" }],
    expected: scenario.expected, oracle: scenario.oracle, mutation_policy: scenario.mutation_policy,
    evidence_plan: [{ oracle_rule_id: "state-rule", evidence_kind: "accessibility_state", after_step_id: "open-state", collector: { source: "accessibility" }, sequence: 1 }],
    integrity: { plan_sha256: `sha256:${"0".repeat(64)}` }, approval_ref: null,
  };
  runbook.integrity.plan_sha256 = runbookPlanHash(runbook);
  const command = { runbook_id: runbook.runbook_id };
  const state = { state: "saved" };
  const evidence = [
    { id: "runner-command", kind: "test_command", collected_at: "2020-01-01T00:00:00Z", producer: { type: "runner", name: "web-playwright", version: "1.0.0" }, sha256: sha256Json(command), redactions: [], record: command },
    { id: "visible-state", kind: "accessibility_state", collected_at: "2020-01-01T00:00:03Z", producer: { type: "runner", name: "web-playwright", version: "1.0.0" }, sha256: sha256Json(state), redactions: [], record: state },
  ];
  const runnerOutput = {
    schema_version: "runner-output-v1", run_id: "run-web-saved-state-1", runbook_id: runbook.runbook_id,
    runbook_hash: sha256Json(runbook), plan_sha256: runbook.integrity.plan_sha256, scenario_id: scenario.id,
    spec_version: scenario.spec_version, scenario_hash: sha256Json(scenario), target: scenario.target,
    runner_provider: scenario.runner_provider, provider_binding: runbook.provider_binding,
    project_config_sha256: runbook.project_config_sha256, started_at: "2020-01-01T00:00:00Z", finished_at: "2020-01-01T00:00:04Z",
    execution: { status: "completed", attempt: 1, retry_count: 0, command_evidence_ref: "runner-command", runner_version: "1.0.0" },
    subject: { build: { ref: "build-1", sha256: `sha256:${"c".repeat(64)}` }, artifact: null, runtime_binding: null },
    step_results: [{ step_id: "open-state", status: "completed", attempt_count: 1, started_at: "2020-01-01T00:00:01Z", finished_at: "2020-01-01T00:00:03Z", evidence_refs: ["visible-state"], error: null }],
    evidence, errors: [], unsupported_reason: null, missing_evidence: [], diagnostic_attachments: [],
  };
  return { bundle, scenario, runbook, runnerOutput };
}

test("deterministic judge emits a validator-conformant pass result", () => {
  const input = fixture();
  const result = judgeRunnerOutput({ ...input, decidedAt: DECIDED_AT });
  assert.equal(result.verdict, "pass");
  assert.equal(result.oracle_results[0].status, "matched");
  assertValidatorAccepts(input, result);
});

test("judge CLI writes result-v1", () => {
  const input = fixture();
  const directory = mkdtempSync(path.join(tmpdir(), "spec-qa-judge-cli-"));
  const paths = {};
  for (const [name, document] of Object.entries(input)) {
    paths[name] = path.join(directory, `${name}.json`);
    writeFileSync(paths[name], `${JSON.stringify(document)}\n`);
  }
  paths.result = path.join(directory, "result.json");
  const output = execFileSync(process.execPath, [JUDGE, "--bundle", paths.bundle, "--scenario", paths.scenario, "--runbook", paths.runbook, "--runner-output", paths.runnerOutput, "--output", paths.result], { encoding: "utf8" });
  assert.match(output, /"schema_version":"result-v1"/);
});

test("deterministic mismatch produces fail", () => {
  const input = fixture();
  input.runnerOutput.evidence[1].record.state = "pending";
  input.runnerOutput.evidence[1].sha256 = sha256Json(input.runnerOutput.evidence[1].record);
  const result = judgeRunnerOutput({ ...input, decidedAt: DECIDED_AT });
  assert.equal(result.verdict, "fail");
  assert.equal(result.oracle_results[0].status, "mismatched");
});

test("missing required evidence produces insufficient_evidence", () => {
  const input = fixture();
  input.runnerOutput.evidence.splice(1, 1);
  input.runnerOutput.step_results[0].evidence_refs = [];
  const result = judgeRunnerOutput({ ...input, decidedAt: DECIDED_AT });
  assert.equal(result.verdict, "insufficient_evidence");
  assert.equal(result.oracle_results[0].status, "not_evaluated");
  assert.equal(result.missing_evidence[0].oracle_id, "state-rule");
});

test("partial execution produces blocked before oracle mismatch", () => {
  const input = fixture();
  input.runnerOutput.execution.status = "partial";
  input.runnerOutput.errors = [{ code: "E_BROWSER_EXIT", message: "Browser exited.", evidence_refs: ["runner-command"] }];
  input.runnerOutput.evidence[1].record.state = "pending";
  input.runnerOutput.evidence[1].sha256 = sha256Json(input.runnerOutput.evidence[1].record);
  const result = judgeRunnerOutput({ ...input, decidedAt: DECIDED_AT });
  assert.equal(result.verdict, "blocked");
  assert.equal(result.blockers[0].code, "E_BROWSER_EXIT");
});

test("unsupported not-started execution remains unsupported", () => {
  const input = fixture();
  input.runnerOutput.execution.status = "not_started";
  input.runnerOutput.unsupported_reason = "Provider capability is unavailable.";
  input.runnerOutput.errors = [{ code: "E_CAPABILITY", message: "Unsupported.", evidence_refs: ["runner-command"] }];
  const result = judgeRunnerOutput({ ...input, decidedAt: DECIDED_AT });
  assert.equal(result.verdict, "unsupported");
  assert.equal(result.unsupported_reason, "Provider capability is unavailable.");
});

test("source conflict has the highest verdict priority", () => {
  const input = fixture();
  const second = source("policy-spec", "state-policy", "The state remains pending.");
  input.bundle.sources.push(second);
  const conflictInput = { schema_version: "source-conflicts-v1", conflicts: [{ id: "saved-state-conflict", description: "Approved sources require incompatible states at the same point.", source_refs: [{ source_id: "ticket-spec", anchor_id: "state-ac" }, { source_id: "policy-spec", anchor_id: "state-policy" }] }] };
  const result = judgeRunnerOutput({ ...input, conflictInput, decidedAt: DECIDED_AT });
  assert.equal(result.verdict, "conflict");
  assert.equal(result.conflicts.length, 1);
});

test("tampered evidence is rejected before judging", () => {
  const input = fixture();
  input.runnerOutput.evidence[1].record.state = "tampered";
  assert.throws(() => judgeRunnerOutput({ ...input, decidedAt: DECIDED_AT }), (error) => error.code === "E_EVIDENCE_HASH_MISMATCH");
});

test("ambiguous evidence cannot be selected implicitly", () => {
  const rule = { evidence_kind: "accessibility_state", operator: "equals", actual_path: "/state", value: "saved" };
  const evidence = [{ id: "a", record: { state: "saved" } }, { id: "b", record: { state: "saved" } }];
  const result = evaluateDeterministicRule(rule, evidence);
  assert.equal(result.status, "not_evaluated");
  assert.match(result.reason, /exactly one/);
});

test("all deterministic operators have fixed behavior", () => {
  const evidence = [{ id: "state", record: { text: "saved complete", list: ["a", "b"], status: 201 } }];
  const cases = [
    ["equals", "/status", 201, "matched"], ["not_equals", "/status", 200, "matched"],
    ["contains", "/text", "saved", "matched"], ["contains", "/list", "b", "matched"],
    ["exists", "/status", undefined, "matched"], ["absent", "/missing", undefined, "matched"],
    ["matches_regex", "/text", "^saved", "matched"], ["status_code", "/status", 201, "matched"],
  ];
  for (const [operator, actualPath, value, expected] of cases) {
    const rule = { evidence_kind: "accessibility_state", operator, actual_path: actualPath, ...(value === undefined ? {} : { value }) };
    assert.equal(evaluateDeterministicRule(rule, evidence).status, expected, operator);
  }
});

test("semantic request batch exposes only frozen source, expected, rubric, and evidence", () => {
  const input = fixture({ mode: "semantic" });
  const batch = prepareSemanticBatch(input);
  assert.equal(batch.schema_version, "semantic-judge-batch-v1");
  assert.equal(batch.requests.length, 1);
  assert.deepEqual(Object.keys(batch.requests[0]).sort(), ["evidence", "expectation_id", "expected", "input_sha256", "oracle_id", "request_id", "rubric", "rubric_hash", "schema_version", "source_refs"].sort());
  const requestText = JSON.stringify(batch.requests[0]);
  assert.doesNotMatch(requestText, /Saved state is visible/);
  assert.doesNotMatch(requestText, /step_results|runner_provider|verdict|errors/);
  assert.match(requestText, /The visible state is saved/);
  assert.match(requestText, /The saved state is visible/);
});

function semanticResponse(batch, overrides = {}) {
  const request = batch.requests[0];
  return {
    schema_version: "semantic-judge-response-batch-v1", batch_sha256: batch.batch_sha256,
    responses: [{ request_id: request.request_id, input_sha256: request.input_sha256, status: "matched", evidence_refs: ["visible-state"], source_refs: [{ source_id: "ticket-spec", anchor_id: "state-ac" }], actual: "saved", reason: "Observed and required meanings match under the frozen rubric.", model: { provider: "configured-provider", model_version: "immutable-model-1", prompt_version: "semantic-judge-v1", rubric_hash: batch.rubric_hash }, ...overrides }],
  };
}

test("hash-bound isolated semantic response can produce pass", () => {
  const input = fixture({ mode: "semantic" });
  const batch = prepareSemanticBatch(input);
  const result = judgeRunnerOutput({ ...input, semanticResponses: semanticResponse(batch), decidedAt: DECIDED_AT });
  assert.equal(result.verdict, "pass");
  assert.equal(result.judge.mode, "semantic");
  assert.equal(result.judge.model.prompt_version, "semantic-judge-v1");
  assertValidatorAccepts(input, result);
});

test("semantic scenario with no admissible evidence is judged insufficient without an LLM call", () => {
  const input = fixture({ mode: "semantic" });
  input.runnerOutput.evidence.splice(1, 1);
  input.runnerOutput.step_results[0].evidence_refs = [];
  const batch = prepareSemanticBatch(input);
  assert.equal(batch.requests.length, 0);
  const result = judgeRunnerOutput({ ...input, decidedAt: DECIDED_AT });
  assert.equal(result.verdict, "insufficient_evidence");
  assert.equal(result.judge.mode, "deterministic");
  assert.equal(result.judge.model, null);
  assertValidatorAccepts(input, result);
});

test("semantic response cannot cite out-of-scope evidence", () => {
  const input = fixture({ mode: "semantic" });
  const batch = prepareSemanticBatch(input);
  assert.throws(
    () => judgeRunnerOutput({ ...input, semanticResponses: semanticResponse(batch, { evidence_refs: ["runner-command"] }), decidedAt: DECIDED_AT }),
    (error) => error.code === "E_SEMANTIC_EVIDENCE_SCOPE",
  );
});

test("verdict decision order is fixed", () => {
  const base = { executionStatus: "partial", conflicts: [{ id: "c" }], blockers: [{ code: "b" }], oracleResults: [{ status: "mismatched" }], missingEvidence: [], unsupportedReason: null };
  assert.equal(decideVerdict(base), "conflict");
  assert.equal(decideVerdict({ ...base, conflicts: [] }), "blocked");
  assert.equal(decideVerdict({ ...base, conflicts: [], blockers: [], executionStatus: "completed" }), "fail");
});
