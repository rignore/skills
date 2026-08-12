import assert from "node:assert/strict";
import test from "node:test";

import { compileMarkdownSpec } from "../compile-markdown-spec.mjs";
import { sourceContentHash } from "../judge-results.mjs";

function markdown(statement = "The page exposes a visible status.") {
  return `# Local sample specification
@bundle_id local-sample
@spec_version local-sample-v1
@source_id local-spec
@source_kind acceptance_criteria
@source_version 1

## status-visible
kind: acceptance_criterion
status: approved
title: Status is visible

${statement}
`;
}

test("compiles constrained local Markdown to a hash-bound spec-bundle-v1", () => {
  const bundle = compileMarkdownSpec({ markdown: markdown(), originRef: "spec.md" });
  assert.equal(bundle.schema_version, "spec-bundle-v1");
  assert.equal(bundle.sources[0].origin_ref, "spec.md");
  assert.equal(bundle.sources[0].content_hash, sourceContentHash(bundle.sources[0]));
  assert.equal(bundle.sources[0].anchors[0].source_locator, "## status-visible");
});

test("normalizes CRLF and decomposed Unicode deterministically", () => {
  const first = compileMarkdownSpec({ markdown: markdown("Cafe\u0301 is visible.\r\n"), originRef: "spec.md" });
  const second = compileMarkdownSpec({ markdown: markdown("Café is visible.\n"), originRef: "spec.md" });
  assert.equal(first.sources[0].content_hash, second.sources[0].content_hash);
});

test("rejects secret-bearing Markdown before bundle emission", () => {
  assert.throws(
    () => compileMarkdownSpec({ markdown: markdown("Authorization: Bearer abcdefghijklmnop"), originRef: "spec.md" }),
    (error) => error.code === "E_SENSITIVE_INPUT",
  );
});

test("rejects absolute origin references", () => {
  assert.throws(
    () => compileMarkdownSpec({ markdown: markdown(), originRef: "/private/tmp/spec.md" }),
    (error) => error.code === "E_MARKDOWN_ORIGIN_REF",
  );
});
