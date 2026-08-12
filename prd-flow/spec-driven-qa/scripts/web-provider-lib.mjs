import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";

export class ContractError extends Error {
  constructor(code, message, contractPath = "$", details = undefined) {
    super(message);
    this.name = "ContractError";
    this.code = code;
    this.path = contractPath;
    this.details = details;
  }

  toJSON() {
    return {
      code: this.code,
      path: this.path,
      message: this.message,
      ...(this.details === undefined ? {} : { details: this.details }),
    };
  }
}

export function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function assertPlainObject(value, code, contractPath, message) {
  if (!isPlainObject(value)) {
    throw new ContractError(code, message, contractPath);
  }
}

function canonicalize(value) {
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }
  if (isPlainObject(value)) {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, canonicalize(value[key])]),
    );
  }
  return value;
}

export function canonicalJson(value) {
  return JSON.stringify(canonicalize(value));
}

export function sha256Bytes(value) {
  return `sha256:${createHash("sha256").update(value).digest("hex")}`;
}

export function sha256Json(value) {
  return sha256Bytes(Buffer.from(canonicalJson(value), "utf8"));
}

export const RUNBOOK_PLAN_FIELDS = Object.freeze([
  "scenario_id", "schema_version", "runbook_id", "spec_version", "scenario_hash",
  "source_refs", "review_status", "method", "execution", "target",
  "runner_provider", "provider_binding", "project_config_sha256", "preconditions",
  "fixture", "steps", "expected", "oracle", "mutation_policy", "evidence_plan",
]);

export function runbookPlanHash(runbook) {
  for (const field of RUNBOOK_PLAN_FIELDS) {
    if (!(field in runbook)) throw new ContractError("E_RUNBOOK_PLAN_FIELD_REQUIRED", `runbook plan field is missing: ${field}`, `$.${field}`);
  }
  return sha256Json(Object.fromEntries(RUNBOOK_PLAN_FIELDS.map((field) => [field, runbook[field]])));
}

export function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

export async function readJson(filePath) {
  const raw = await readFile(filePath, "utf8");
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new ContractError(
      "E_JSON_PARSE",
      `invalid JSON in ${path.basename(filePath)}: ${error.message}`,
    );
  }
}

export async function writeJson(filePath, value) {
  await writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

export function requireNonEmptyString(value, code, contractPath, message) {
  if (typeof value !== "string" || value.length === 0) {
    throw new ContractError(code, message, contractPath);
  }
  return value;
}

export function requireInteger(value, minimum, maximum, code, contractPath, message) {
  if (!Number.isInteger(value) || value < minimum || value > maximum) {
    throw new ContractError(code, message, contractPath);
  }
  return value;
}

export function sanitizeUrl(value) {
  const parsed = new URL(value);
  parsed.username = "";
  parsed.password = "";
  const queryKeys = [...new Set([...parsed.searchParams.keys()])].sort();
  return {
    origin: parsed.origin,
    pathname: parsed.pathname,
    query_keys: queryKeys,
  };
}

export function resolveRelativeUrl(origin, route, contractPath) {
  requireNonEmptyString(
    route,
    "E_WEB_ROUTE_INVALID",
    contractPath,
    "route must be a non-empty string",
  );
  if (!route.startsWith("/") || route.startsWith("//")) {
    throw new ContractError(
      "E_WEB_ROUTE_INVALID",
      "route must be an origin-relative path beginning with one slash",
      contractPath,
    );
  }
  const resolved = new URL(route, origin);
  if (resolved.origin !== new URL(origin).origin) {
    throw new ContractError(
      "E_WEB_ORIGIN_ESCAPE",
      "resolved route must remain within the configured origin",
      contractPath,
    );
  }
  return resolved.toString();
}

export function jsonPointerGet(value, pointer) {
  if (pointer === "") return value;
  if (typeof pointer !== "string" || !pointer.startsWith("/")) {
    throw new ContractError(
      "E_JSON_POINTER_INVALID",
      "JSON Pointer must be empty or start with '/'",
    );
  }
  return pointer
    .slice(1)
    .split("/")
    .map((token) => token.replaceAll("~1", "/").replaceAll("~0", "~"))
    .reduce((current, token) => {
      if (current === null || current === undefined) return undefined;
      return current[token];
    }, value);
}

export function selectJsonPointers(value, pointers) {
  const selected = {};
  for (const pointer of pointers) {
    selected[pointer] = jsonPointerGet(value, pointer);
  }
  return selected;
}

export function truncateText(value, maximum = 2_000) {
  if (typeof value !== "string") return value;
  return value.length <= maximum ? value : `${value.slice(0, maximum)}…`;
}

const SENSITIVE_KEY = /(authorization|credential|password|passwd|secret|token|api[_-]?key|session[_-]?cookie|private[_-]?key|signing[_-]?key)/i;
const SAFE_REFERENCE_SUFFIX = /(_ref|_id|_name|_type|_version)$/i;
const ARTIFACT_PAYLOAD_KEY = /(apk|aab|artifact|archive).*(base64|bytes|binary|blob|payload)|(base64|bytes|binary|blob|payload).*(apk|aab|artifact|archive)/i;
const SECRET_VALUE = /\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}|-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----|\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\b/i;

export function assertSecretFree(value, contractPath = "$") {
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertSecretFree(item, `${contractPath}[${index}]`));
    return;
  }
  if (isPlainObject(value)) {
    for (const [key, child] of Object.entries(value)) {
      const childPath = `${contractPath}.${key}`;
      if (
        (SENSITIVE_KEY.test(key) && !SAFE_REFERENCE_SUFFIX.test(key)) ||
        ARTIFACT_PAYLOAD_KEY.test(key)
      ) {
        if (child !== null && child !== "" && !(Array.isArray(child) && child.length === 0)) {
          throw new ContractError(
            "E_SENSITIVE_INPUT",
            "credential or inline artifact data is forbidden",
            childPath,
          );
        }
      }
      assertSecretFree(child, childPath);
    }
    return;
  }
  if (typeof value === "string" && SECRET_VALUE.test(value)) {
    throw new ContractError(
      "E_SENSITIVE_INPUT",
      "credential material is forbidden",
      contractPath,
    );
  }
}

export function parseCli(argv, definitions) {
  const values = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--") || !(token in definitions)) {
      throw new ContractError("E_CLI_USAGE", `unknown argument: ${token}`);
    }
    const definition = definitions[token];
    if (definition.boolean) {
      values[definition.name] = true;
      continue;
    }
    const next = argv[index + 1];
    if (next === undefined || next.startsWith("--")) {
      throw new ContractError("E_CLI_USAGE", `${token} requires a value`);
    }
    values[definition.name] = next;
    index += 1;
  }
  for (const definition of Object.values(definitions)) {
    if (definition.required && values[definition.name] === undefined) {
      throw new ContractError("E_CLI_USAGE", `--${definition.name.replaceAll("_", "-")} is required`);
    }
  }
  return values;
}

export function printContractError(error) {
  const payload =
    error instanceof ContractError
      ? error.toJSON()
      : { code: "E_INTERNAL", path: "$", message: error.message };
  process.stderr.write(`${JSON.stringify({ valid: false, errors: [payload] }, null, 2)}\n`);
}
