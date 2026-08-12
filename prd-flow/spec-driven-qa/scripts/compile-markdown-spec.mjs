#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

import { sourceContentHash } from "./judge-results.mjs";
import {
  ContractError,
  assertSecretFree,
  parseCli,
  printContractError,
  writeJson,
} from "./web-provider-lib.mjs";

const IDENTIFIER = /^[a-z0-9][a-z0-9._-]{0,127}$/;
const SOURCE_KINDS = new Set([
  "prd", "acceptance_criteria", "policy", "design",
  "inspection_description", "other",
]);
const ANCHOR_KINDS = new Set([
  "requirement", "acceptance_criterion", "policy_rule", "design_frame",
  "component_description", "other",
]);
const STATUSES = new Set(["approved", "draft", "deprecated"]);
const HEADER_KEYS = new Set([
  "bundle_id", "spec_version", "source_id", "source_kind", "source_version",
]);
const ANCHOR_KEYS = new Set(["kind", "status", "title"]);

function normalize(value) {
  const lines = value.normalize("NFC").replaceAll("\r\n", "\n").replaceAll("\r", "\n")
    .split("\n").map((line) => line.replace(/[ \t]+$/u, ""));
  while (lines[0] === "") lines.shift();
  while (lines.at(-1) === "") lines.pop();
  return lines.join("\n");
}

function parseMetadata(line, allowed, contractPath) {
  const match = /^([a-z_]+):[ \t]+(.+)$/.exec(line);
  if (!match || !allowed.has(match[1])) {
    throw new ContractError("E_MARKDOWN_SPEC_METADATA", `invalid metadata line: ${line}`, contractPath);
  }
  return [match[1], normalize(match[2])];
}

export function compileMarkdownSpec({ markdown, originRef = "spec.md" }) {
  if (typeof markdown !== "string") throw new ContractError("E_MARKDOWN_SPEC_INPUT", "markdown must be a string");
  if (typeof originRef !== "string" || !originRef || path.isAbsolute(originRef) || originRef.split("/").includes("..")) {
    throw new ContractError("E_MARKDOWN_ORIGIN_REF", "origin_ref must be a non-empty relative reference", "$.origin_ref");
  }
  const lines = normalize(markdown).split("\n");
  if (!lines[0]?.startsWith("# ")) throw new ContractError("E_MARKDOWN_SPEC_TITLE", "first line must be a level-one title");
  const sourceTitle = normalize(lines.shift().slice(2));
  const header = {};
  while (lines.length > 0 && !lines[0].startsWith("## ")) {
    const line = lines.shift();
    if (line === "") continue;
    if (!line.startsWith("@")) throw new ContractError("E_MARKDOWN_SPEC_HEADER", `unexpected header line: ${line}`);
    const separator = line.indexOf(" ");
    const key = line.slice(1, separator);
    const value = normalize(line.slice(separator + 1));
    if (separator < 2 || !HEADER_KEYS.has(key) || !value || Object.hasOwn(header, key)) {
      throw new ContractError("E_MARKDOWN_SPEC_HEADER", `invalid or duplicate header: ${line}`);
    }
    header[key] = value;
  }
  for (const key of HEADER_KEYS) {
    if (!header[key]) throw new ContractError("E_MARKDOWN_SPEC_HEADER", `missing @${key}`);
  }
  if (!IDENTIFIER.test(header.bundle_id) || !IDENTIFIER.test(header.source_id)) {
    throw new ContractError("E_MARKDOWN_SPEC_ID", "bundle_id and source_id must use contract identifiers");
  }
  if (!SOURCE_KINDS.has(header.source_kind)) throw new ContractError("E_MARKDOWN_SOURCE_KIND", "unsupported source_kind");

  const anchors = [];
  while (lines.length > 0) {
    while (lines[0] === "") lines.shift();
    if (lines.length === 0) break;
    const heading = lines.shift();
    if (!heading.startsWith("## ")) throw new ContractError("E_MARKDOWN_ANCHOR_HEADING", "anchor must start with a level-two heading");
    const id = normalize(heading.slice(3));
    if (!IDENTIFIER.test(id)) throw new ContractError("E_MARKDOWN_ANCHOR_ID", "anchor heading must be a contract identifier");
    const metadata = {};
    while (lines.length > 0 && lines[0] !== "" && !lines[0].startsWith("## ")) {
      const [key, value] = parseMetadata(lines.shift(), ANCHOR_KEYS, `$.anchors.${id}`);
      if (Object.hasOwn(metadata, key)) throw new ContractError("E_MARKDOWN_SPEC_METADATA", `duplicate anchor metadata: ${key}`);
      metadata[key] = value;
    }
    while (lines[0] === "") lines.shift();
    const body = [];
    while (lines.length > 0 && !lines[0].startsWith("## ")) body.push(lines.shift());
    const statement = normalize(body.join("\n"));
    if (!metadata.title || !ANCHOR_KINDS.has(metadata.kind) || !STATUSES.has(metadata.status) || !statement) {
      throw new ContractError("E_MARKDOWN_ANCHOR_INVALID", `anchor ${id} requires kind, status, title, and statement`);
    }
    anchors.push({
      id,
      kind: metadata.kind,
      title: metadata.title,
      statement,
      status: metadata.status,
      source_locator: `## ${id}`,
    });
  }
  if (anchors.length === 0) throw new ContractError("E_MARKDOWN_ANCHORS_REQUIRED", "at least one anchor is required");
  if (new Set(anchors.map((anchor) => anchor.id)).size !== anchors.length) throw new ContractError("E_MARKDOWN_ANCHOR_DUPLICATE", "anchor ids must be unique");
  const source = {
    id: header.source_id,
    kind: header.source_kind,
    title: sourceTitle,
    version: header.source_version,
    content_hash: "",
    origin_ref: originRef,
    anchors,
  };
  source.content_hash = sourceContentHash(source);
  const bundle = {
    schema_version: "spec-bundle-v1",
    bundle_id: header.bundle_id,
    spec_version: header.spec_version,
    sources: [source],
  };
  assertSecretFree(bundle);
  return bundle;
}

async function main() {
  const options = parseCli(process.argv.slice(2), {
    "--input": { name: "input", required: true },
    "--output": { name: "output", required: true },
  });
  const bundle = compileMarkdownSpec({ markdown: await readFile(options.input, "utf8"), originRef: path.basename(options.input) });
  await writeJson(options.output, bundle);
  process.stdout.write(`${JSON.stringify({ valid: true, output: options.output, content_hash: bundle.sources[0].content_hash })}\n`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => { printContractError(error); process.exitCode = 1; });
}
