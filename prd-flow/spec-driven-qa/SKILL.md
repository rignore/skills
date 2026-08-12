---
name: spec-driven-qa
description: Generate and validate traceable QA scenarios and deterministic runbooks from PRDs, policies, acceptance criteria, and designs; verify actual desktop or responsive web services with a configured Playwright provider; verify Android native apps through an external Appium UiAutomator2 adapter; define the iOS execution contract while reporting it as unsupported; and judge recorded test evidence. Use for spec-driven QA planning, test scenario generation, contract validation, real web or Android app verification, and execution-result adjudication.
---

# Spec-driven QA

Build traceable QA artifacts from product specifications, replay reviewed runbooks without LLM decisions, and judge only recorded evidence. Keep source, runner, judge, and result-sink providers replaceable.

## Workflow

1. Identify the authoritative PRD, policy, acceptance criteria, design references, target build, and test environment.
2. Normalize those inputs as `spec-bundle-v1`. Read [input-contract.md](references/input-contract.md) before creating or accepting a bundle.
3. Generate `scenario-v1` scenarios. Read [scenario-schema.md](references/scenario-schema.md). Use an LLM only to draft scenarios or assess meaning that deterministic rules cannot decide.
4. Validate each artifact with `scripts/validate-contracts.py`. Do not compile or execute invalid scenarios.
5. Require human review before compiling mutation-capable scenarios. Freeze the reviewed scenario, source version, fixture, target, and oracle in a deterministic runbook.
6. Select a runner with the routing table below. Read [runner-provider-contract.md](references/runner-provider-contract.md) before producing or replaying a runbook.
7. Record structured observations without letting the execution agent declare its own Pass result.
8. Apply deterministic oracles first. Read [judge-protocol.md](references/judge-protocol.md) before any semantic judgment.
9. Emit `result-v1` according to [result-schema.md](references/result-schema.md), then send it to a configured sink. Use a local file when no external sink is configured.
10. For a company-independent end-to-end smoke test, follow [p5-pilot.md](references/p5-pilot.md). Keep its public target configuration under `examples/p5`; do not replace it with company data.

## Route Providers

| Target | Method | Provider | Current execution rule |
| --- | --- | --- | --- |
| Desktop web | `web` | `web-playwright` | Replay a stored Playwright runbook. |
| Responsive mobile web | `web` | `web-playwright` | Use a Playwright device context; never classify it as native. |
| Android native app | `native` | `native-android` | Use the external Appium UiAutomator2 adapter described in [native-mcp-adapter.md](references/native-mcp-adapter.md). |
| iOS native app | `native` | `native-ios` | Keep the contract but return `unsupported`; do not execute. |
| Unit or integration test | `unit` or `integration` | `developer-test` | Replay the project-owned test command and capture its structured output. |
| Human-only check | `manual` | `manual` | Record supplied evidence without inventing observations. |

Treat a missing web or Android provider as `blocked`, not `fail`. Treat iOS execution, Android physical devices, and AAB artifacts as `unsupported` in the current contract.

## Preserve Validation Integrity

- Require at least one resolvable entry in `source_refs` on every scenario.
- Keep `expected` and `oracle` separate: expected describes required behavior; oracle defines how evidence proves or disproves it.
- Run saved runbooks deterministically in CI. Do not call an LLM to select actions, locators, fixtures, retries, or verdicts during replay.
- Accept structured logs, DOM or accessibility state, UI hierarchy, locator results, network or console errors, API or database state, Android logcat, test command output, and build or artifact hashes as evidence.
- Treat images, screenshots, and video as optional context only. Never require them for Pass and never use them as the sole Pass evidence.
- Reject an execution agent's self-reported success as evidence.
- Return exactly one verdict: `pass`, `fail`, `conflict`, `insufficient_evidence`, `blocked`, or `unsupported`.

## Enforce Safety

- Keep credentials, tokens, passwords, signing material, APK bytes, and Base64 artifacts out of bundles, scenarios, runbooks, results, and logs.
- Reference installable Android artifacts by a local path or opaque artifact ID plus SHA-256. Accept APK only; reject AAB and physical-device execution.
- Treat native `launch`, `tap`, `fill`, `press_key`, and `back`, plus any state-changing web or API action, as potential mutations.
- Require an explicit approval policy for every mutation action. Never retry mutation actions automatically.
- Create destructive and boundary states only with fixtures, mocks, seed scripts, or test endpoints in an isolated environment. Do not modify production data.
- Redact secrets and sensitive entered values from evidence.

## Load References Selectively

- Read [input-contract.md](references/input-contract.md) for `spec-bundle-v1` sources, provenance, target, and prohibited input.
- Read [scenario-schema.md](references/scenario-schema.md) for `scenario-v1`, platform routing, fixtures, mutation policy, and examples.
- Read [runner-provider-contract.md](references/runner-provider-contract.md) for immutable runbooks, provider lifecycle, evidence envelopes, and error handling.
- Read [web-playwright-provider.md](references/web-playwright-provider.md) for desktop or responsive web config, runbook compilation, Playwright replay, and structured web evidence.
- Read [native-mcp-adapter.md](references/native-mcp-adapter.md) only for Android native work or iOS capability checks.
- Read [judge-protocol.md](references/judge-protocol.md) for deterministic and independent semantic judging.
- Read [result-schema.md](references/result-schema.md) for `result-v1` serialization and sink behavior.
- Read [p5-pilot.md](references/p5-pilot.md) only when running or adapting the public web and Android Emulator pilots.

## Validate Artifacts

Run the validator with Python's standard library only:

```bash
python3 scripts/validate-contracts.py <artifact.json>
python3 scripts/validate-contracts.py --bundle <spec-bundle.json> <scenario.json>
python3 scripts/validate-contracts.py --bundle <spec-bundle.json> --scenario <scenario.json> <runbook.json>
python3 scripts/validate-contracts.py --bundle <spec-bundle.json> --scenario <scenario.json> --runbook <runbook.json> <result.json>
python3 scripts/validate-contracts.py <native-mcp-binding.json>
```

The validator accepts five schemas: `spec-bundle-v1`, `scenario-v1`, `runbook-v1`, `result-v1`, and `native-mcp-binding-v1`. A scenario requires the bundle. A runbook also requires its exact scenario so the validator can recompute the scenario hash and compare every preserved contract field. A result additionally requires the runbook so the validator can resolve oracle IDs, expectations, evidence kinds, and source references. Native binding validation is standalone and enforces stdio MCP, local Appium, UiAutomator2, Emulator, and APK boundaries. Web and Android request/output conformance is also enforced by their runtime scripts. Use the validator's nonzero exit status and stable issue codes as the contract gate. Fix the artifact rather than bypassing validation.

Compile and replay web runbooks with Node.js:

```bash
node scripts/compile-web-runbook.mjs --scenario scenario.json --config web-project-config.json --output runbook.json
node scripts/run-web-playwright.mjs --request runner-request.json --runbook runbook.json --output runner-output.json
```

The compiler uses only Node.js standard-library modules. The runner requires a version-pinned Playwright installation and Chromium binary supplied by the host project or an explicit `--playwright-module-root`.

Compile a constrained local Markdown source to `spec-bundle-v1` with:

```bash
node scripts/compile-markdown-spec.mjs --input spec.md --output spec-bundle.json
```

Compile and preflight Android runbooks before creating an external approval record:

```bash
node scripts/compile-android-runbook.mjs --scenario scenario.json --config native-android-config.json --preflight --output runbook-preflight.json
node scripts/run-android-mcp.mjs --request runner-request-preflight.json --runbook runbook-preflight.json --binding native-mcp-binding.json --preflight-only --output native-preflight.json
```

The preflight compiler emits `runbook_state=preflight` with `approval_ref=null`; the approved compiler emits `runbook_state=executable`. The plan hash stays identical because authorization state and the approval record are outside the frozen plan projection. Before starting the MCP process, the adapter must verify the hash-bound `JAVA_HOME/bin/java`, run `java -version`, and run the bound `apksigner verify --print-certs` against the exact APK.

Bind `native-mcp-preflight-v1.provider_plan_hash`, `runtime_binding_sha256`, and the runbook plan hash into the immutable approval record. Recompile with `--approval`, then run the same adapter without `--preflight-only`. The Android MCP adapter supports a first `launch` step and deterministic `wait_for present|absent` steps using `accessibility_id` or Android resource `id`. The adapter calls an external stdio MCP server and does not embed Appium runtime code. Completed Android results must bind observed Appium and UiAutomator2 versions. When the external MCP omits them, use `enrich-android-runtime.mjs` with the exact Appium debug log before judging; never substitute configured or assumed versions.

Judge deterministic runner output with the frozen source, scenario, and runbook snapshots:

```bash
node scripts/judge-results.mjs --bundle spec-bundle.json --scenario scenario.json --runbook runbook.json --runner-output runner-output.json --output result.json
```

For a semantic scenario, run the same command first with `--prepare-semantic`. Send only the emitted `semantic-judge-batch-v1` to an independent model context. Supply the hash-bound `semantic-judge-response-batch-v1` with `--semantic-responses` in a second invocation. Never send planner conversation, runbook steps, runner status, runner errors, or a proposed verdict to the semantic context.

Before allowing semantic verdicts to control a release gate, calculate calibration from at least 30 independently human-labeled cases:

```bash
python3 scripts/calibrate-judge.py semantic-calibration.json --output calibration-report.json
```

Treat exit code `1` as a failed release gate and exit code `2` as invalid calibration input. Synthetic unit-test cases do not satisfy the human-label requirement.
