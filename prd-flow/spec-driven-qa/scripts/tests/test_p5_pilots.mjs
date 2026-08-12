import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { compileAndroidRunbook } from "../compile-android-runbook.mjs";
import { compileMarkdownSpec } from "../compile-markdown-spec.mjs";
import { compileWebRunbook } from "../compile-web-runbook.mjs";

const root = path.resolve(import.meta.dirname, "../../examples/p5");

async function json(filePath) {
  return JSON.parse(await readFile(filePath, "utf8"));
}

async function inputs(name) {
  const directory = path.join(root, name);
  return {
    bundle: compileMarkdownSpec({ markdown: await readFile(path.join(directory, "spec.md"), "utf8"), originRef: "spec.md" }),
    scenario: await json(path.join(directory, "scenario.json")),
    config: await json(path.join(directory, name === "web" ? "playwright-config.json" : "android-config.json")),
  };
}

test("P5 public web sample compiles from local Markdown without company adapters", async () => {
  const { bundle, scenario, config } = await inputs("web");
  const runbook = compileWebRunbook({ scenario, config });
  assert.equal(bundle.spec_version, scenario.spec_version);
  assert.equal(runbook.target.platform, "web");
  assert.equal(runbook.steps.some((step) => step.mutation !== "none"), false);
});

test("P5 public Android sample compiles an unapproved Emulator/APK preflight", async () => {
  const { bundle, scenario, config } = await inputs("android");
  const runbook = compileAndroidRunbook({ scenario, config, allowUnapprovedPreflight: true });
  assert.equal(bundle.spec_version, scenario.spec_version);
  assert.deepEqual(runbook.target, { platform: "android", device: "emulator", artifact_type: "apk" });
  assert.equal(runbook.approval_ref, null);
  assert.equal(runbook.runbook_state, "preflight");
  assert.deepEqual(runbook.mutation_policy.approval_scope, ["launch-app"]);
});

test("P5 examples contain no company adapter or product coupling", async () => {
  const files = [
    "web/spec.md", "web/scenario.json", "web/playwright-config.json",
    "android/spec.md", "android/scenario.json", "android/android-config.json",
  ];
  const joined = (await Promise.all(files.map((file) => readFile(path.join(root, file), "utf8")))).join("\n").toLowerCase();
  for (const forbidden of ["notion", "prd-flow-copilot", "protect go", "protectgo", "idbrnd", "database id"]) {
    assert.equal(joined.includes(forbidden), false, `forbidden coupling: ${forbidden}`);
  }
});
