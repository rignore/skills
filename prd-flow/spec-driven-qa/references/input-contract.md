# `spec-bundle-v1` input contract

`spec-bundle-v1` freezes product requirements, acceptance criteria, policy rules, design references, and inspection descriptions into one source-neutral input. A source adapter creates the bundle. The scenario planner consumes it without querying the original system during planning or CI replay.

Target readers are source-adapter implementers, scenario-planner implementers, and contract-validator maintainers.

## Contents

1. Normative language and serialization
2. Top-level object
3. Source and anchor objects
4. Source hash canonicalization
5. Reference resolution
6. Sensitive-data and artifact restrictions
7. Validation rules
8. Complete example

## 1. Normative language and serialization

`MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, and `MAY` are normative requirements.

- The canonical exchange format is a UTF-8 JSON object.
- `schema_version` MUST equal `spec-bundle-v1`.
- A producer MUST omit unknown fields or place namespaced data under `extensions`.
- A consumer MAY ignore unknown keys inside `extensions`, but MUST scan their values for prohibited sensitive data and binary artifacts.
- Hashes use lowercase hexadecimal in the form `sha256:<64 hex characters>`.
- Identifiers MUST be stable within one `spec_version`. Changing an anchor's meaning requires a new anchor identifier or a new `spec_version`.

## 2. Top-level object

| Field | Type | Required | Contract |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Exact value `spec-bundle-v1`. |
| `bundle_id` | string | yes | Stable bundle identifier. It MUST match `^[a-z0-9][a-z0-9._-]{0,127}$`. |
| `spec_version` | string | yes | Immutable version of the normalized bundle. A scenario copies this exact value. |
| `sources` | array of source objects | yes | Non-empty. Source `id` values MUST be unique. |
| `extensions` | object | no | Namespaced adapter metadata. It MUST NOT contain secrets, binary data, or executable selectors. |

`spec_version` is an opaque value. Consumers compare it for exact equality and MUST NOT infer chronological order from its text.

## 3. Source and anchor objects

### 3.1 Source object

| Field | Type | Required | Contract |
| --- | --- | --- | --- |
| `id` | string | yes | Stable identifier, unique in `sources`. It follows the `bundle_id` identifier pattern. |
| `kind` | enum | yes | `prd`, `acceptance_criteria`, `policy`, `design`, `inspection_description`, or `other`. |
| `title` | string | yes | Human-readable source name. It MUST NOT be empty. |
| `version` | string | yes | Version reported by the source adapter. |
| `content_hash` | string | yes | SHA-256 of the canonical source projection defined in section 4. |
| `origin_ref` | string | no | Opaque source-system reference for audit. It MUST NOT embed credentials, query tokens, or session data. |
| `anchors` | array of anchor objects | yes | Non-empty. Anchor `id` values MUST be unique within the source. |
| `extensions` | object | no | Namespaced, secret-free source metadata. |

An adapter MAY use a local path, URI, or provider-specific opaque identifier as `origin_ref`. The core treats it as data and does not fetch it.

### 3.2 Anchor object

| Field | Type | Required | Contract |
| --- | --- | --- | --- |
| `id` | string | yes | Stable identifier, unique within its source. It follows the `bundle_id` identifier pattern. |
| `kind` | enum | yes | `requirement`, `acceptance_criterion`, `policy_rule`, `design_frame`, `component_description`, or `other`. |
| `title` | string | yes | Human-readable meaning of the anchor. |
| `statement` | string | yes | Normalized requirement or design statement used to derive an expectation. It MUST NOT be empty. |
| `status` | enum | yes | `approved`, `draft`, or `deprecated`. |
| `source_locator` | string | no | Location inside the source document, such as a heading or frame identifier. It is not an application UI selector. |
| `extensions` | object | no | Namespaced, secret-free anchor metadata. |

The adapter MUST preserve conflicting approved statements as separate anchors. It MUST NOT silently choose one statement as the correct answer. The independent judge reports such incompatible requirements as `conflict`.

Only `approved` anchors are executable inputs by default. A planner MAY create a non-executable draft scenario from a `draft` anchor. It MUST NOT create an executable scenario solely from `deprecated` anchors.

## 4. Source hash canonicalization

`content_hash` binds the exact normalized source fields that the planner can use. It is recomputable from the bundle and does not hash an unavailable source-system snapshot.

The producer builds the canonical source projection with these fields:

- source `id`, `kind`, `title`, and `version`;
- `anchors`, sorted by ascending anchor `id`;
- each anchor's `id`, `kind`, `title`, `statement`, and `status`;
- `source_locator` only when it is present.

The projection excludes `content_hash`, `origin_ref`, and every `extensions` object. Those fields describe transport or adapters and cannot change the requirement used for QA.

Before projection, the producer normalizes every source or anchor `title`, `statement`, and `source_locator` string in this order:

1. Apply Unicode Normalization Form C (NFC).
2. Replace CRLF and CR line endings with LF.
3. Remove ASCII space and tab characters from the end of every line.
4. Remove empty lines from the beginning and end of the string.
5. Preserve embedded empty lines and all other characters.

The normalized string stored in the bundle has no trailing LF. Required strings remain non-empty after normalization.

The producer serializes the projection as canonical JSON with these byte rules:

- sort object keys by Unicode code point;
- use `,` and `:` without surrounding whitespace;
- preserve the sorted anchor-array order;
- emit non-ASCII Unicode characters directly rather than ASCII escape sequences;
- encode as UTF-8 without a byte-order mark;
- append exactly one LF byte after the closing object.

The SHA-256 of those bytes becomes `content_hash`.

### 4.1 Test vector

Assume the input statement is `Cafe\u0301  \r\nready\r\n`. Unicode normalization, line-ending conversion, trailing-space removal, and final-empty-line removal produce `Café\nready`.

The complete canonical source projection is the following one-line JSON followed by one LF byte:

```text
{"anchors":[{"id":"a","kind":"requirement","statement":"Café\nready","status":"approved","title":"Greeting"}],"id":"sample","kind":"prd","title":"Sample","version":"1"}
```

Its hash is:

```text
sha256:17bdc0b6d586bdf36fe6e71df16c15a77c895d212fde4d29473f9605c8eb780d
```

A producer or validator that computes a different value from this vector is not compatible with `spec-bundle-v1`.

## 5. Reference resolution

A scenario points to an anchor with this exact object:

```json
{
  "source_id": "product-requirements",
  "anchor_id": "saved-record-becomes-complete"
}
```

Resolution has three rules.

1. `source_id` MUST match exactly one `sources[].id`.
2. `anchor_id` MUST match exactly one anchor in that source.
3. The scenario's `spec_version` MUST equal the bundle's `spec_version`.

A dangling, ambiguous, or cross-version reference is invalid. The planner MUST NOT replace a missing reference with an untraceable summary.

## 6. Sensitive-data and artifact restrictions

The bundle is specification text, not a credential store or artifact transport.

The producer and validator MUST reject the whole bundle when any nested field, including `extensions`, contains one of these values:

- a password, credential, access token, refresh token, API key, private key, session cookie, or authorization header;
- APK bytes, an encoded application archive, or any other executable artifact bytes;
- a Base64 artifact, including a `data:*;base64,` URI or a long opaque Base64 payload in an artifact field;
- a URL or source reference with embedded user information, credential material, or authentication query parameters.

Hashes, media types, artifact types, and opaque non-secret references are metadata and MAY appear. Artifact bytes and signing material MUST NOT appear. Runtime authentication is configured outside `spec-bundle-v1` and is exposed to a runner only by an approved secure runtime mechanism.

## 7. Validation rules

A conforming validator MUST reject a bundle when any of these conditions applies:

- `schema_version` is missing or differs from `spec-bundle-v1`;
- a required field is missing, has the wrong type, or is empty where this contract requires content;
- `sources` is empty;
- a source identifier is duplicated;
- a source has no anchors or duplicates an anchor identifier;
- a `title`, `statement`, or `source_locator` value differs from its normalized form defined in section 4;
- `content_hash` is not a valid SHA-256 reference;
- recomputing the canonical source projection does not equal `content_hash`;
- an identifier does not match the required pattern;
- any nested value violates the sensitive-data or artifact restrictions.

Validation does not prove that a statement is correct. It proves that the input is structurally traceable and safe to hand to the planner.

## 8. Complete example

This example contains one product requirement and one policy rule. The second source makes the expected backend state independently traceable instead of relying on a screen label alone.

```json
{
  "schema_version": "spec-bundle-v1",
  "bundle_id": "sample-record-workflow",
  "spec_version": "2026-08-01.1",
  "sources": [
    {
      "id": "product-requirements",
      "kind": "prd",
      "title": "Record workflow requirements",
      "version": "1.0",
      "content_hash": "sha256:bab4f79e0a0995c5918a945329728edca69d9b2008fce60bf935911de757295f",
      "anchors": [
        {
          "id": "saved-record-becomes-complete",
          "kind": "requirement",
          "title": "Saved record state",
          "statement": "After a successful save, the record state is complete.",
          "status": "approved"
        }
      ]
    },
    {
      "id": "workflow-policy",
      "kind": "policy",
      "title": "Record state policy",
      "version": "3",
      "content_hash": "sha256:000482f09ca24c80cc88d197ccfe9eb711ecd682d514b54b5004e4a9f3e4e700",
      "anchors": [
        {
          "id": "complete-state-requires-persisted-value",
          "kind": "policy_rule",
          "title": "Persisted completion rule",
          "statement": "A complete screen state is valid only when the persisted record state is complete.",
          "status": "approved"
        }
      ]
    }
  ]
}
```

See [`scenario-schema.md`](scenario-schema.md) for scenario references and [`result-schema.md`](result-schema.md) for observed evidence.
