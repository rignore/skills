#!/usr/bin/env python3
"""Validate Spec-driven QA JSON contracts without third-party packages.

The command exits with 0 for valid input, 1 for contract violations, and 2 for
invalid CLI usage or unreadable/invalid JSON input. Validation messages expose
stable error codes and JSON-style paths, but never echo rejected secret values.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit


CONTRACTS = {
    "spec-bundle-v1",
    "scenario-v1",
    "runbook-v1",
    "result-v1",
    "native-mcp-binding-v1",
}
VERDICTS = {
    "pass",
    "fail",
    "conflict",
    "insufficient_evidence",
    "blocked",
    "unsupported",
}
PLATFORMS = {"web", "mobile_web", "android", "ios"}
METHODS = {"web", "native", "unit", "integration", "manual"}
SOURCE_KINDS = {
    "prd",
    "acceptance_criteria",
    "policy",
    "design",
    "inspection_description",
    "other",
}
ANCHOR_KINDS = {
    "requirement",
    "acceptance_criterion",
    "policy_rule",
    "design_frame",
    "component_description",
    "other",
}
ANCHOR_STATUSES = {"approved", "draft", "deprecated"}
REVIEW_STATUSES = {"draft", "approved", "rejected"}
SEVERITIES = {"blocker", "critical", "high", "medium", "low"}
ORACLE_MODES = {"deterministic", "semantic", "manual"}
FIXTURE_KINDS = {"none", "seed", "mock", "test_endpoint", "snapshot", "manual"}
FIXTURE_PURPOSES = {"baseline", "error", "boundary"}
FIXTURE_ENVIRONMENTS = {"isolated", "shared_test", "production"}

EXPECTED_PROVIDER = {
    ("web", "web"): "web-playwright",
    ("mobile_web", "web"): "web-playwright",
    ("android", "native"): "native-android",
    ("ios", "native"): "native-ios",
}
EXPECTED_DEVICE = {
    "web": "desktop",
    "mobile_web": "responsive",
    "android": "emulator",
    "ios": "simulator",
}
EXPECTED_ARTIFACT = {"android": "apk", "ios": "app_zip"}
IMPLICIT_NATIVE_MUTATIONS = {"launch", "tap", "fill", "press_key", "back"}
IMPLICIT_STATE_MUTATIONS = {
    "activate",
    "click",
    "create",
    "delete",
    "press",
    "save",
    "select_option",
    "submit",
    "update",
    "upload",
}
IMPLICIT_MUTATIONS = IMPLICIT_NATIVE_MUTATIONS | IMPLICIT_STATE_MUTATIONS
PHYSICAL_DEVICE_VALUES = {
    "physical",
    "physical_device",
    "real",
    "real_device",
}

SENSITIVE_KEYS = {
    "authorization",
    "authheader",
    "credential",
    "credentials",
    "password",
    "passwd",
    "secret",
    "clientsecret",
    "apikey",
    "token",
    "tokens",
    "accesstoken",
    "refreshtoken",
    "bearertoken",
    "cookie",
    "cookies",
    "sessioncookie",
}
INLINE_ARTIFACT_KEYS = {
    "apkbytes",
    "artifactbytes",
    "artifactbase64",
    "apkbase64",
    "base64artifact",
    "contentbase64",
}
ARTIFACT_PAYLOAD_KEYS = {"bytes", "base64", "content", "data", "payload"}
ARTIFACT_BINARY_KEYS = {
    "aab",
    "aabblob",
    "apk",
    "apkblob",
    "binary",
    "blob",
    "filebytes",
}
EVIDENCE_KINDS = {
    "structured_log",
    "dom_state",
    "accessibility_state",
    "ui_hierarchy",
    "locator_result",
    "network_error",
    "console_error",
    "url_state",
    "api_state",
    "storage_state",
    "db_state",
    "test_command",
    "android_logcat",
    "build_hash",
    "artifact_hash",
}
SELF_REPORT_EVIDENCE_KINDS = {"agent_report", "agent_self_report", "self_report"}

IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
BEARER_PATTERN = re.compile(r"\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}", re.I)
JWT_PATTERN = re.compile(
    r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\b"
)
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
BASE64_DATA_URI_PATTERN = re.compile(r"^data:[^,;]+(?:;[^,]*)?;base64,", re.I)
EMBEDDED_CREDENTIAL_URL_PATTERN = re.compile(
    r"^[a-z][a-z0-9+.-]*://[^/@\s:]+:[^/@\s]+@", re.I
)
AUTH_QUERY_PATTERN = re.compile(
    r"[?&](?:access_token|refresh_token|token|api[_-]?key|password|signature)=",
    re.I,
)
BASE64_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")


@dataclass(frozen=True, order=True)
class ValidationIssue:
    """A stable, machine-readable contract violation."""

    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


def _key_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _path(parent: str, key: Any) -> str:
    if isinstance(key, int):
        return f"{parent}[{key}]"
    key_text = str(key)
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key_text):
        return f"{parent}.{key_text}"
    return f"{parent}[{json.dumps(key_text, ensure_ascii=False)}]"


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, Sequence, Mapping)):
        return len(value) > 0
    return True


def _enum_member(value: Any, allowed: set[str] | frozenset[str]) -> bool:
    return isinstance(value, str) and value in allowed


def _normalize_source_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in normalized.split("\n")]
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _canonical_source_content_hash(source: Mapping[str, Any]) -> str | None:
    required_source_fields = ("id", "kind", "title", "version", "anchors")
    if any(field not in source for field in required_source_fields):
        return None
    if not all(
        isinstance(source.get(field), str)
        for field in ("id", "kind", "title", "version")
    ):
        return None
    anchors = source.get("anchors")
    if not isinstance(anchors, list) or not anchors:
        return None

    projected_anchors: list[dict[str, Any]] = []
    for anchor in anchors:
        if not isinstance(anchor, Mapping):
            return None
        required_anchor_fields = ("id", "kind", "title", "statement", "status")
        if any(field not in anchor for field in required_anchor_fields):
            return None
        if not all(isinstance(anchor.get(field), str) for field in required_anchor_fields):
            return None
        projection: dict[str, Any] = {
            "id": anchor["id"],
            "kind": anchor["kind"],
            "title": _normalize_source_text(anchor["title"]),
            "statement": _normalize_source_text(anchor["statement"]),
            "status": anchor["status"],
        }
        if "source_locator" in anchor:
            if not isinstance(anchor.get("source_locator"), str):
                return None
            projection["source_locator"] = _normalize_source_text(
                anchor["source_locator"]
            )
        projected_anchors.append(projection)

    projected_anchors.sort(key=lambda item: item["id"])
    source_projection = {
        "id": source["id"],
        "kind": source["kind"],
        "title": _normalize_source_text(source["title"]),
        "version": source["version"],
        "anchors": projected_anchors,
    }
    serialized = json.dumps(
        source_projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"
    return "sha256:" + hashlib.sha256(serialized).hexdigest()


RUNBOOK_PLAN_FIELDS = (
    "scenario_id",
    "schema_version",
    "runbook_id",
    "spec_version",
    "scenario_hash",
    "source_refs",
    "review_status",
    "method",
    "execution",
    "target",
    "runner_provider",
    "provider_binding",
    "project_config_sha256",
    "preconditions",
    "fixture",
    "steps",
    "expected",
    "oracle",
    "mutation_policy",
    "evidence_plan",
)


def _canonical_runbook_plan_hash(document: Mapping[str, Any]) -> str | None:
    if any(field not in document for field in RUNBOOK_PLAN_FIELDS):
        return None
    projection = {field: document[field] for field in RUNBOOK_PLAN_FIELDS}
    try:
        serialized = json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return "sha256:" + hashlib.sha256(serialized).hexdigest()


def _canonical_json_hash(document: Mapping[str, Any]) -> str | None:
    """Hash a complete JSON contract using the canonical exchange encoding."""

    try:
        serialized = json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return "sha256:" + hashlib.sha256(serialized).hexdigest()


class ContractValidator:
    """Accumulate all contract violations in deterministic order."""

    def __init__(self) -> None:
        self._issues: list[ValidationIssue] = []
        self._seen: set[tuple[str, str, str]] = set()

    def add(self, code: str, path: str, message: str) -> None:
        key = (code, path, message)
        if key not in self._seen:
            self._issues.append(ValidationIssue(code, path, message))
            self._seen.add(key)

    def validate(
        self,
        document: Any,
        requested_contract: str | None = None,
        spec_bundle: Mapping[str, Any] | None = None,
        scenario: Mapping[str, Any] | None = None,
        runbook: Mapping[str, Any] | None = None,
    ) -> list[ValidationIssue]:
        if not isinstance(document, dict):
            self.add("E_DOCUMENT_TYPE", "$", "contract document must be a JSON object")
            return self.issues

        self._scan_forbidden_input(document, "$")
        schema_version = document.get("schema_version")

        if requested_contract is not None:
            contract = requested_contract
            if schema_version is not None and schema_version != requested_contract:
                self.add(
                    "E_SCHEMA_VERSION_MISMATCH",
                    "$.schema_version",
                    f"expected {requested_contract!r} for the selected contract",
                )
        else:
            contract = schema_version

        if not isinstance(contract, str) or not contract:
            self.add(
                "E_SCHEMA_VERSION_REQUIRED",
                "$.schema_version",
                "schema_version is required when --contract is not selected",
            )
            return self.issues
        if not _enum_member(contract, CONTRACTS):
            self.add(
                "E_SCHEMA_VERSION_UNSUPPORTED",
                "$.schema_version",
                f"unsupported schema_version; expected one of {', '.join(sorted(CONTRACTS))}",
            )
            return self.issues

        if schema_version is None:
            self.add(
                "E_REQUIRED",
                "$.schema_version",
                "required field is missing",
            )

        if contract == "spec-bundle-v1":
            self._validate_spec_bundle(document)
        elif contract == "scenario-v1":
            if spec_bundle is None:
                self.add(
                    "E_BUNDLE_CONTEXT_REQUIRED",
                    "$",
                    "scenario-v1 validation requires a linked spec-bundle-v1 context",
                )
            self._validate_scenario(document, spec_bundle)
        elif contract == "runbook-v1":
            if spec_bundle is None:
                self.add(
                    "E_BUNDLE_CONTEXT_REQUIRED",
                    "$",
                    "runbook-v1 validation requires a linked spec-bundle-v1 context",
                )
            if scenario is None:
                self.add(
                    "E_SCENARIO_CONTEXT_REQUIRED",
                    "$",
                    "runbook-v1 validation requires a linked scenario-v1 context",
                )
            self._validate_runbook(document, spec_bundle, scenario)
        elif contract == "result-v1":
            if spec_bundle is None:
                self.add(
                    "E_BUNDLE_CONTEXT_REQUIRED",
                    "$",
                    "result-v1 validation requires a linked spec-bundle-v1 context",
                )
            if scenario is None:
                self.add(
                    "E_SCENARIO_CONTEXT_REQUIRED",
                    "$",
                    "result-v1 validation requires a linked scenario-v1 context",
                )
            if runbook is None:
                self.add(
                    "E_RUNBOOK_CONTEXT_REQUIRED",
                    "$",
                    "result-v1 validation requires a linked runbook-v1 context",
                )
            self._validate_result(document, spec_bundle, scenario, runbook)
        elif contract == "native-mcp-binding-v1":
            self._validate_native_mcp_binding(document)
        return self.issues

    @property
    def issues(self) -> list[ValidationIssue]:
        return sorted(self._issues, key=lambda issue: (issue.path, issue.code, issue.message))

    def _require_fields(
        self, value: Mapping[str, Any], required: Iterable[str], path: str = "$"
    ) -> None:
        for field in required:
            if field not in value:
                self.add("E_REQUIRED", _path(path, field), "required field is missing")

    def _scan_forbidden_input(
        self, value: Any, path: str, artifact_context: bool = False
    ) -> None:
        if isinstance(value, dict):
            local_artifact_context = artifact_context or self._dict_is_artifact(value)
            for raw_key, child in value.items():
                child_path = _path(path, raw_key)
                normalized = _key_name(raw_key)
                if self._is_sensitive_key(raw_key, normalized) and _nonempty(child):
                    self.add(
                        "E_SENSITIVE_INPUT",
                        child_path,
                        "credential, password, secret, token, or authorization data is forbidden",
                    )
                if self._is_inline_artifact_key(normalized) and _nonempty(child):
                    self.add(
                        "E_ARTIFACT_INLINE_DATA",
                        child_path,
                        "APK bytes and Base64 artifact data are forbidden; use a local artifact reference",
                    )
                if (
                    local_artifact_context
                    and normalized in ARTIFACT_BINARY_KEYS
                    and _nonempty(child)
                ):
                    self.add(
                        "E_ARTIFACT_INLINE_DATA",
                        child_path,
                        "inline APK, AAB, blob, or binary artifact data is forbidden",
                    )
                if (
                    local_artifact_context
                    and normalized in ARTIFACT_PAYLOAD_KEYS
                    and _nonempty(child)
                ):
                    self.add(
                        "E_ARTIFACT_INLINE_DATA",
                        child_path,
                        "artifact payload data is forbidden; use a local path and content hash",
                    )

                child_is_artifact = local_artifact_context or normalized in {
                    "artifact",
                    "appartifact",
                }
                self._scan_forbidden_input(child, child_path, child_is_artifact)
            return

        if isinstance(value, list):
            if (
                artifact_context
                and value
                and all(
                    isinstance(item, int)
                    and not isinstance(item, bool)
                    and 0 <= item <= 255
                    for item in value
                )
            ):
                self.add(
                    "E_ARTIFACT_INLINE_DATA",
                    path,
                    "integer byte arrays are forbidden in artifact fields",
                )
            for index, child in enumerate(value):
                self._scan_forbidden_input(child, _path(path, index), artifact_context)
            return

        if isinstance(value, str):
            if (
                BEARER_PATTERN.search(value)
                or JWT_PATTERN.search(value)
                or PRIVATE_KEY_PATTERN.search(value)
                or EMBEDDED_CREDENTIAL_URL_PATTERN.search(value)
                or AUTH_QUERY_PATTERN.search(value)
            ):
                self.add(
                    "E_SENSITIVE_INPUT",
                    path,
                    "credential, password, secret, token, or authorization data is forbidden",
                )
            if BASE64_DATA_URI_PATTERN.search(value):
                self.add(
                    "E_ARTIFACT_INLINE_DATA",
                    path,
                    "Base64 data URIs are forbidden; use an opaque reference",
                )
            elif artifact_context and self._looks_like_base64_artifact(value):
                self.add(
                    "E_ARTIFACT_INLINE_DATA",
                    path,
                    "opaque Base64 artifact payloads are forbidden",
                )

    @staticmethod
    def _is_sensitive_key(raw_key: Any, normalized: str) -> bool:
        if normalized in SENSITIVE_KEYS:
            return True
        safe_reference_suffixes = (
            "env",
            "id",
            "ref",
            "version",
        )
        if any(normalized.endswith(suffix) for suffix in safe_reference_suffixes):
            return False

        raw_text = str(raw_key)
        separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw_text)
        parts = {
            part
            for part in re.split(r"[^A-Za-z0-9]+", separated.lower())
            if part
        }
        always_sensitive_parts = {
            "access",
            "auth",
            "authorization",
            "bearer",
            "credential",
            "credentials",
            "oauth",
            "passwd",
            "password",
            "private",
            "refresh",
            "secret",
            "session",
            "signing",
            "token",
        }
        if parts & always_sensitive_parts:
            return True
        return (
            "apikey" in normalized
            or "accesskey" in normalized
            or "accesstoken" in normalized
            or "refreshtoken" in normalized
            or "sessioncookie" in normalized
            or "privatekey" in normalized
            or "signingkey" in normalized
            or "bearertoken" in normalized
        )

    @staticmethod
    def _is_inline_artifact_key(normalized: str) -> bool:
        if normalized in INLINE_ARTIFACT_KEYS:
            return True
        if normalized.endswith(("hash", "id", "path", "ref", "version")):
            return False
        has_artifact_identity = any(
            identity in normalized for identity in ("apk", "aab", "artifact")
        )
        has_payload_marker = any(
            marker in normalized
            for marker in ("archive", "base64", "binary", "blob", "bytes", "payload")
        ) or normalized.endswith(("content", "data"))
        return has_artifact_identity and has_payload_marker

    @staticmethod
    def _looks_like_base64_artifact(value: str) -> bool:
        compact = "".join(value.split())
        if (
            len(compact) < 12
            or len(compact) % 4 != 0
            or not BASE64_VALUE_PATTERN.fullmatch(compact)
        ):
            return False
        try:
            decoded = base64.b64decode(compact, validate=True)
        except (binascii.Error, ValueError):
            return False
        return decoded.startswith(b"PK\x03\x04") or (
            len(decoded) >= 32
            and any(byte < 9 or (13 < byte < 32) or byte > 126 for byte in decoded)
        )

    @staticmethod
    def _dict_is_artifact(value: Mapping[str, Any]) -> bool:
        for key in ("artifact_type", "format"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.lower() in {
                "apk",
                "aab",
                "app_zip",
            }:
                return True
        return False

    def _validate_native_mcp_binding(self, document: Mapping[str, Any]) -> None:
        self._require_fields(
            document,
            ("schema_version", "binding_id", "server", "capabilities", "artifact", "readiness", "package_id", "device", "appium", "execution"),
        )
        self._validate_identifier(document.get("binding_id"), "$.binding_id")

        server = document.get("server")
        if not isinstance(server, dict):
            self.add("E_NATIVE_SERVER_INVALID", "$.server", "server must be an object")
        else:
            self._require_fields(server, ("name", "version", "protocol_version", "transport", "executable_sha256", "runtime_source", "contract_version", "launch"), "$.server")
            for field in ("name", "version", "protocol_version", "contract_version"):
                if not isinstance(server.get(field), str) or not server.get(field):
                    self.add("E_NATIVE_SERVER_INVALID", _path("$.server", field), "must be a non-empty string")
            if server.get("transport") != "stdio":
                self.add("E_NATIVE_TRANSPORT_UNSUPPORTED", "$.server.transport", "native MCP transport must be stdio")
            self._validate_hash(server.get("executable_sha256"), "$.server.executable_sha256")
            runtime_source = server.get("runtime_source")
            if not isinstance(runtime_source, dict):
                self.add("E_MCP_RUNTIME_SOURCE_INVALID", "$.server.runtime_source", "runtime_source must be an object")
            else:
                self._require_fields(
                    runtime_source,
                    ("kind", "root_path", "source_tree_sha256", "file_count", "total_bytes"),
                    "$.server.runtime_source",
                )
                if runtime_source.get("kind") != "directory_tree":
                    self.add("E_MCP_RUNTIME_SOURCE_INVALID", "$.server.runtime_source.kind", "kind must be directory_tree")
                root_path = runtime_source.get("root_path")
                if (
                    not isinstance(root_path, str)
                    or not Path(root_path).is_absolute()
                    or Path(root_path) == Path(Path(root_path).anchor)
                ):
                    self.add("E_MCP_RUNTIME_SOURCE_INVALID", "$.server.runtime_source.root_path", "root_path must be an absolute non-filesystem-root directory")
                self._validate_hash(runtime_source.get("source_tree_sha256"), "$.server.runtime_source.source_tree_sha256")
                for field in ("file_count", "total_bytes"):
                    value = runtime_source.get(field)
                    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                        self.add("E_MCP_RUNTIME_SOURCE_INVALID", _path("$.server.runtime_source", field), "must be a positive integer")
            launch = server.get("launch")
            if not isinstance(launch, dict):
                self.add("E_NATIVE_SERVER_LAUNCH_INVALID", "$.server.launch", "launch must be an object")
            else:
                self._require_fields(launch, ("executable_path", "arguments"), "$.server.launch")
                executable_path = launch.get("executable_path")
                if not isinstance(executable_path, str) or not Path(executable_path).is_absolute():
                    self.add("E_NATIVE_SERVER_LAUNCH_INVALID", "$.server.launch.executable_path", "executable_path must be absolute")
                arguments = launch.get("arguments")
                if not isinstance(arguments, list) or any(not isinstance(item, str) for item in arguments):
                    self.add("E_NATIVE_SERVER_LAUNCH_INVALID", "$.server.launch.arguments", "arguments must be an array of strings")
                working_directory = launch.get("working_directory")
                if working_directory is not None and (not isinstance(working_directory, str) or not Path(working_directory).is_absolute()):
                    self.add("E_NATIVE_SERVER_LAUNCH_INVALID", "$.server.launch.working_directory", "working_directory must be absolute when present")

        capabilities = document.get("capabilities")
        required_tools = {
            "get_native_video_scenario_schema", "register_native_app", "get_native_runtime_status",
            "inspect_native_app", "create_native_video_job", "preflight_video_job",
            "approve_video_job", "start_video_job", "get_video_job",
        }
        if not isinstance(capabilities, dict):
            self.add("E_NATIVE_CAPABILITIES_INVALID", "$.capabilities", "capabilities must be an object")
        else:
            self._require_fields(capabilities, ("discovered_at", "tools_list_sha256", "native_scenario_schema_sha256", "required_tools"), "$.capabilities")
            self._parse_timestamp(capabilities.get("discovered_at"), "$.capabilities.discovered_at")
            self._validate_hash(capabilities.get("tools_list_sha256"), "$.capabilities.tools_list_sha256")
            self._validate_hash(capabilities.get("native_scenario_schema_sha256"), "$.capabilities.native_scenario_schema_sha256")
            tools = capabilities.get("required_tools")
            if not isinstance(tools, list) or any(not isinstance(item, str) for item in tools) or not required_tools.issubset(set(tools) if isinstance(tools, list) else set()):
                self.add("E_NATIVE_REQUIRED_TOOLS_MISSING", "$.capabilities.required_tools", "all nine native MCP tools are required")

        artifact = document.get("artifact")
        if not isinstance(artifact, dict):
            self.add("E_ANDROID_APK_REQUIRED", "$.artifact", "artifact must be an object")
        else:
            self._require_fields(artifact, ("type", "local_path", "expected_sha256"), "$.artifact")
            if artifact.get("type") != "apk":
                self.add("E_ANDROID_AAB_UNSUPPORTED", "$.artifact.type", "native binding supports APK only")
            local_path = artifact.get("local_path")
            if not isinstance(local_path, str) or not Path(local_path).is_absolute() or not local_path.lower().endswith(".apk"):
                self.add("E_ANDROID_APK_REQUIRED", "$.artifact.local_path", "local_path must be an absolute APK path")
            self._validate_hash(artifact.get("expected_sha256"), "$.artifact.expected_sha256")

        readiness = document.get("readiness")
        if not isinstance(readiness, dict):
            self.add("E_ANDROID_READINESS_INVALID", "$.readiness", "readiness must be an object")
        else:
            self._require_fields(readiness, ("java", "apk_verifier"), "$.readiness")
            java = readiness.get("java")
            if not isinstance(java, dict):
                self.add("E_JAVA_READINESS_BINDING_INVALID", "$.readiness.java", "java readiness must be an object")
            else:
                self._require_fields(java, ("home_path", "executable_path", "executable_sha256"), "$.readiness.java")
                home_path = java.get("home_path")
                executable_path = java.get("executable_path")
                if not isinstance(home_path, str) or not Path(home_path).is_absolute():
                    self.add("E_JAVA_READINESS_BINDING_INVALID", "$.readiness.java.home_path", "home_path must be an absolute JAVA_HOME")
                if not isinstance(executable_path, str) or not Path(executable_path).is_absolute():
                    self.add("E_JAVA_READINESS_BINDING_INVALID", "$.readiness.java.executable_path", "executable_path must be absolute")
                elif isinstance(home_path, str) and Path(home_path).is_absolute() and Path(executable_path) != Path(home_path) / "bin" / "java":
                    self.add("E_JAVA_READINESS_BINDING_INVALID", "$.readiness.java.executable_path", "executable_path must equal JAVA_HOME/bin/java")
                self._validate_hash(java.get("executable_sha256"), "$.readiness.java.executable_sha256")
            apk_signing = readiness.get("apk_verifier")
            if not isinstance(apk_signing, dict):
                self.add("E_APK_SIGNING_BINDING_INVALID", "$.readiness.apk_verifier", "apk_verifier readiness must be an object")
            else:
                self._require_fields(apk_signing, ("verifier", "executable_path", "executable_sha256"), "$.readiness.apk_verifier")
                if apk_signing.get("verifier") != "apksigner":
                    self.add("E_APK_SIGNING_BINDING_INVALID", "$.readiness.apk_verifier.verifier", "verifier must be apksigner")
                executable_path = apk_signing.get("executable_path")
                if not isinstance(executable_path, str) or not Path(executable_path).is_absolute():
                    self.add("E_APK_SIGNING_BINDING_INVALID", "$.readiness.apk_verifier.executable_path", "executable_path must be absolute")
                self._validate_hash(apk_signing.get("executable_sha256"), "$.readiness.apk_verifier.executable_sha256")

        package_id = document.get("package_id")
        if not isinstance(package_id, str) or re.fullmatch(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+$", package_id) is None:
            self.add("E_ANDROID_PACKAGE_INVALID", "$.package_id", "package_id must be an Android application ID")

        device = document.get("device")
        if not isinstance(device, dict):
            self.add("E_ANDROID_EMULATOR_REQUIRED", "$.device", "device must be an object")
        else:
            self._require_fields(device, ("runtime", "orientation", "reset_policy"), "$.device")
            if device.get("runtime") != "emulator":
                self.add("E_ANDROID_PHYSICAL_DEVICE_UNSUPPORTED", "$.device.runtime", "only Android Emulator is supported")
            udid = device.get("udid")
            if udid is not None and (not isinstance(udid, str) or not udid.startswith("emulator-")):
                self.add("E_ANDROID_PHYSICAL_DEVICE_UNSUPPORTED", "$.device.udid", "udid must identify an Emulator")
            if not device.get("avd") and not udid:
                self.add("E_ANDROID_EMULATOR_REQUIRED", "$.device", "device requires avd or emulator udid")
            if device.get("orientation") not in {"portrait", "landscape"}:
                self.add("E_ANDROID_DEVICE_INVALID", "$.device.orientation", "orientation must be portrait or landscape")
            if device.get("reset_policy") not in {"clean", "preserve"}:
                self.add("E_ANDROID_DEVICE_INVALID", "$.device.reset_policy", "reset_policy must be clean or preserve")

        appium = document.get("appium")
        if not isinstance(appium, dict):
            self.add("E_APPIUM_LOCAL_REQUIRED", "$.appium", "appium must be an object")
        else:
            self._require_fields(appium, ("server_url", "driver"), "$.appium")
            server_url = appium.get("server_url")
            try:
                parsed = urlsplit(server_url) if isinstance(server_url, str) else None
            except ValueError:
                parsed = None
            if parsed is None or parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password:
                self.add("E_APPIUM_LOCAL_REQUIRED", "$.appium.server_url", "Appium URL must be credential-free local HTTP")
            if appium.get("driver") != "uiautomator2":
                self.add("E_APPIUM_DRIVER_UNSUPPORTED", "$.appium.driver", "driver must be uiautomator2")

        execution = document.get("execution")
        if not isinstance(execution, dict):
            self.add("E_NATIVE_EXECUTION_INVALID", "$.execution", "execution must be an object")
        else:
            duration = execution.get("max_duration_seconds")
            if not isinstance(duration, int) or isinstance(duration, bool) or not 10 <= duration <= 180:
                self.add("E_NATIVE_DURATION_INVALID", "$.execution.max_duration_seconds", "max_duration_seconds must be 10..180")
            poll = execution.get("poll_interval_ms", 500)
            if not isinstance(poll, int) or isinstance(poll, bool) or not 50 <= poll <= 5000:
                self.add("E_NATIVE_POLL_INVALID", "$.execution.poll_interval_ms", "poll_interval_ms must be 50..5000")

    def _validate_spec_bundle(self, document: Mapping[str, Any]) -> None:
        self._require_fields(
            document, ("schema_version", "bundle_id", "spec_version", "sources")
        )
        self._validate_identifier(document.get("bundle_id"), "$.bundle_id")
        if not isinstance(document.get("spec_version"), str) or not document.get(
            "spec_version"
        ):
            self.add("E_FIELD_TYPE", "$.spec_version", "must be a non-empty string")

        sources = document.get("sources")
        if not isinstance(sources, list) or not sources:
            self.add("E_SOURCES_REQUIRED", "$.sources", "sources must be a non-empty array")
            return
        source_ids: set[str] = set()
        for index, source in enumerate(sources):
            source_path = _path("$.sources", index)
            if not isinstance(source, dict):
                self.add("E_FIELD_TYPE", source_path, "source must be an object")
                continue
            self._require_fields(
                source,
                ("id", "kind", "title", "version", "content_hash", "anchors"),
                source_path,
            )
            source_id = source.get("id")
            self._validate_identifier(source_id, _path(source_path, "id"))
            if isinstance(source_id, str) and source_id in source_ids:
                self.add("E_DUPLICATE_ID", _path(source_path, "id"), "source id must be unique")
            elif isinstance(source_id, str):
                source_ids.add(source_id)
            if not _enum_member(source.get("kind"), SOURCE_KINDS):
                self.add(
                    "E_SOURCE_KIND_UNSUPPORTED",
                    _path(source_path, "kind"),
                    f"must be one of {', '.join(sorted(SOURCE_KINDS))}",
                )
            content_hash = source.get("content_hash")
            if not isinstance(content_hash, str) or not SHA256_PATTERN.fullmatch(content_hash):
                self.add(
                    "E_CONTENT_HASH_INVALID",
                    _path(source_path, "content_hash"),
                    "must use sha256:<64 hexadecimal characters>",
                )
            for field in ("title", "version"):
                field_value = source.get(field)
                if not isinstance(field_value, str) or not field_value.strip():
                    self.add(
                        "E_FIELD_TYPE",
                        _path(source_path, field),
                        "must be a non-empty string",
                    )
            self._validate_canonical_source_text(
                source.get("title"), _path(source_path, "title"), required=True
            )
            anchors = source.get("anchors")
            if not isinstance(anchors, list) or not anchors:
                self.add(
                    "E_ANCHORS_REQUIRED",
                    _path(source_path, "anchors"),
                    "anchors must be a non-empty array",
                )
                continue
            anchor_ids: set[str] = set()
            for anchor_index, anchor in enumerate(anchors):
                anchor_path = _path(_path(source_path, "anchors"), anchor_index)
                if not isinstance(anchor, dict):
                    self.add("E_FIELD_TYPE", anchor_path, "anchor must be an object")
                    continue
                self._require_fields(
                    anchor,
                    ("id", "kind", "title", "statement", "status"),
                    anchor_path,
                )
                anchor_id = anchor.get("id")
                self._validate_identifier(anchor_id, _path(anchor_path, "id"))
                if isinstance(anchor_id, str) and anchor_id in anchor_ids:
                    self.add(
                        "E_DUPLICATE_ID",
                        _path(anchor_path, "id"),
                        "anchor id must be unique within its source",
                    )
                elif isinstance(anchor_id, str):
                    anchor_ids.add(anchor_id)
                if not _enum_member(anchor.get("kind"), ANCHOR_KINDS):
                    self.add(
                        "E_ANCHOR_KIND_UNSUPPORTED",
                        _path(anchor_path, "kind"),
                        f"must be one of {', '.join(sorted(ANCHOR_KINDS))}",
                    )
                if not _enum_member(anchor.get("status"), ANCHOR_STATUSES):
                    self.add(
                        "E_ANCHOR_STATUS_UNSUPPORTED",
                        _path(anchor_path, "status"),
                        f"must be one of {', '.join(sorted(ANCHOR_STATUSES))}",
                    )
                for field in ("title", "statement"):
                    field_value = anchor.get(field)
                    if not isinstance(field_value, str) or not field_value.strip():
                        self.add(
                            "E_FIELD_TYPE",
                            _path(anchor_path, field),
                            "must be a non-empty string",
                        )
                self._validate_canonical_source_text(
                    anchor.get("title"), _path(anchor_path, "title"), required=True
                )
                self._validate_canonical_source_text(
                    anchor.get("statement"),
                    _path(anchor_path, "statement"),
                    required=True,
                )
                if "source_locator" in anchor:
                    self._validate_canonical_source_text(
                        anchor.get("source_locator"),
                        _path(anchor_path, "source_locator"),
                        required=False,
                    )

            recomputed_hash = _canonical_source_content_hash(source)
            if (
                recomputed_hash is not None
                and isinstance(content_hash, str)
                and SHA256_PATTERN.fullmatch(content_hash)
                and content_hash != recomputed_hash
            ):
                self.add(
                    "E_CONTENT_HASH_MISMATCH",
                    _path(source_path, "content_hash"),
                    "content_hash does not match the canonical source projection",
                )

    def _validate_scenario(
        self,
        document: Mapping[str, Any],
        spec_bundle: Mapping[str, Any] | None = None,
    ) -> None:
        self._require_fields(
            document,
            (
                "schema_version",
                "id",
                "title",
                "source_refs",
                "method",
                "preconditions",
                "fixture",
                "steps",
                "expected",
                "oracle",
                "severity",
                "spec_version",
                "review_status",
                "target",
                "runner_provider",
                "mutation_policy",
                "execution",
            ),
        )
        self._validate_identifier_and_title(document)
        self._validate_source_refs(document.get("source_refs"), "$.source_refs")
        if spec_bundle is not None:
            self._validate_linked_source_refs(document, spec_bundle)
        method = document.get("method")
        if not _enum_member(method, METHODS):
            self.add(
                "E_METHOD_UNSUPPORTED",
                "$.method",
                f"must be one of {', '.join(sorted(METHODS))}",
            )
        enabled = self._execution_enabled(document.get("execution"), "$.execution")
        self._validate_target(
            document.get("target"),
            method,
            document.get("runner_provider"),
            enabled,
        )

        self._validate_preconditions(document.get("preconditions"), "$.preconditions")
        self._validate_fixture(document.get("fixture"), "$.fixture")
        steps = self._validate_actions(
            document.get("steps"),
            "$.steps",
            context="scenario",
            android_native=(
                isinstance(document.get("target"), dict)
                and document["target"].get("platform") == "android"
                and method == "native"
            ),
        )
        self._validate_mutation_policy(
            steps,
            document.get("mutation_policy"),
            "$.mutation_policy",
        )
        self._validate_expected_oracle(
            document.get("expected"),
            document.get("oracle"),
            method,
            "$.expected",
            "$.oracle",
            source_refs=document.get("source_refs"),
            execution_enabled=enabled,
        )

        if not _enum_member(document.get("severity"), SEVERITIES):
            self.add(
                "E_SEVERITY_UNSUPPORTED",
                "$.severity",
                f"must be one of {', '.join(sorted(SEVERITIES))}",
            )
        if not isinstance(document.get("spec_version"), str) or not document.get(
            "spec_version"
        ):
            self.add("E_FIELD_TYPE", "$.spec_version", "must be a non-empty string")
        review_status = document.get("review_status")
        if not _enum_member(review_status, REVIEW_STATUSES):
            self.add(
                "E_REVIEW_STATUS_UNSUPPORTED",
                "$.review_status",
                f"must be one of {', '.join(sorted(REVIEW_STATUSES))}",
            )
        if enabled is True and review_status != "approved":
            self.add(
                "E_EXECUTION_REVIEW_REQUIRED",
                "$.review_status",
                "execution.enabled=true requires review_status='approved'",
            )

    def _validate_runbook(
        self,
        document: Mapping[str, Any],
        spec_bundle: Mapping[str, Any] | None = None,
        scenario: Mapping[str, Any] | None = None,
    ) -> None:
        self._require_fields(
            document,
            (
                "schema_version",
                "runbook_id",
                "scenario_id",
                "spec_version",
                "scenario_hash",
                "source_refs",
                "review_status",
                "method",
                "execution",
                "target",
                "runner_provider",
                "provider_binding",
                "project_config_sha256",
                "preconditions",
                "fixture",
                "steps",
                "expected",
                "oracle",
                "mutation_policy",
                "evidence_plan",
                "integrity",
                "approval_ref",
            ),
        )
        for field in ("runbook_id", "scenario_id"):
            self._validate_identifier(document.get(field), _path("$", field))
        if not isinstance(document.get("spec_version"), str) or not document.get(
            "spec_version"
        ):
            self.add("E_FIELD_TYPE", "$.spec_version", "must be a non-empty string")
        self._validate_hash(document.get("scenario_hash"), "$.scenario_hash")
        self._validate_source_refs(document.get("source_refs"), "$.source_refs")
        if spec_bundle is not None:
            self._validate_linked_source_refs(document, spec_bundle)
        enabled = self._execution_enabled(document.get("execution"), "$.execution")
        method = document.get("method")
        if not _enum_member(method, METHODS):
            self.add(
                "E_METHOD_UNSUPPORTED",
                "$.method",
                f"must be one of {', '.join(sorted(METHODS))}",
            )
        self._validate_target(
            document.get("target"),
            method,
            document.get("runner_provider"),
            enabled,
        )
        provider_defaults_version = self._validate_provider_binding(
            document.get("provider_binding")
        )
        self._validate_hash(
            document.get("project_config_sha256"), "$.project_config_sha256"
        )
        review_status = document.get("review_status")
        if not _enum_member(review_status, REVIEW_STATUSES):
            self.add(
                "E_REVIEW_STATUS_UNSUPPORTED",
                "$.review_status",
                f"must be one of {', '.join(sorted(REVIEW_STATUSES))}",
            )
        if enabled is True and review_status != "approved":
            self.add(
                "E_EXECUTION_REVIEW_REQUIRED",
                "$.review_status",
                "execution.enabled=true requires review_status='approved'",
            )
        self._validate_preconditions(document.get("preconditions"), "$.preconditions")
        self._validate_fixture(document.get("fixture"), "$.fixture")
        actions = self._validate_actions(
            document.get("steps"),
            "$.steps",
            context="runbook",
            provider_defaults_version=provider_defaults_version,
            android_native=(
                isinstance(document.get("target"), dict)
                and document["target"].get("platform") == "android"
                and method == "native"
            ),
        )
        self._validate_mutation_policy(
            actions,
            document.get("mutation_policy"),
            "$.mutation_policy",
        )
        self._validate_expected_oracle(
            document.get("expected"),
            document.get("oracle"),
            method,
            "$.expected",
            "$.oracle",
            source_refs=document.get("source_refs"),
            execution_enabled=enabled,
        )
        evidence_plan = document.get("evidence_plan")
        if not isinstance(evidence_plan, list) or not evidence_plan:
            self.add(
                "E_EVIDENCE_PLAN_REQUIRED",
                "$.evidence_plan",
                "evidence_plan must be a non-empty array",
            )
        else:
            oracle = document.get("oracle")
            oracle_rule_evidence = {
                rule.get("id"): rule.get("evidence_kind")
                for rule in (oracle.get("rules", []) if isinstance(oracle, dict) else [])
                if isinstance(rule, dict) and isinstance(rule.get("id"), str)
            }
            planned_rule_ids: set[str] = set()
            for index, item in enumerate(evidence_plan):
                item_path = _path("$.evidence_plan", index)
                if not isinstance(item, dict):
                    self.add(
                        "E_EVIDENCE_PLAN_INVALID",
                        item_path,
                        "evidence_plan entry must be an object",
                    )
                    continue
                self._require_fields(
                    item, ("oracle_rule_id", "evidence_kind"), item_path
                )
                oracle_rule_id = item.get("oracle_rule_id")
                evidence_kind = item.get("evidence_kind")
                if not isinstance(oracle_rule_id, str):
                    self.add(
                        "E_EVIDENCE_PLAN_INVALID",
                        _path(item_path, "oracle_rule_id"),
                        "oracle_rule_id must be a string",
                    )
                elif oracle_rule_id in planned_rule_ids:
                    self.add(
                        "E_EVIDENCE_PLAN_DUPLICATE",
                        _path(item_path, "oracle_rule_id"),
                        "each oracle rule must appear exactly once in evidence_plan",
                    )
                else:
                    planned_rule_ids.add(oracle_rule_id)
                if (
                    not isinstance(oracle_rule_id, str)
                    or oracle_rule_id not in oracle_rule_evidence
                ):
                    self.add(
                        "E_EVIDENCE_PLAN_ORACLE_UNKNOWN",
                        _path(item_path, "oracle_rule_id"),
                        "evidence plan must reference an existing oracle rule",
                    )
                if not _enum_member(evidence_kind, EVIDENCE_KINDS):
                    self.add(
                        "E_EVIDENCE_KIND_UNSUPPORTED",
                        _path(item_path, "evidence_kind"),
                        f"must be one of {', '.join(sorted(EVIDENCE_KINDS))}",
                    )
                elif (
                    isinstance(oracle_rule_id, str)
                    and oracle_rule_id in oracle_rule_evidence
                    and evidence_kind != oracle_rule_evidence[oracle_rule_id]
                ):
                    self.add(
                        "E_EVIDENCE_PLAN_KIND_MISMATCH",
                        _path(item_path, "evidence_kind"),
                        "evidence_plan.evidence_kind must equal the referenced oracle rule evidence_kind",
                    )
            for missing_rule_id in sorted(
                set(oracle_rule_evidence) - planned_rule_ids
            ):
                self.add(
                    "E_EVIDENCE_PLAN_COVERAGE_MISSING",
                    "$.evidence_plan",
                    f"oracle rule {missing_rule_id!r} must appear exactly once in evidence_plan",
                )

        integrity = document.get("integrity")
        if not isinstance(integrity, dict):
            self.add("E_INTEGRITY_INVALID", "$.integrity", "integrity must be an object")
            plan_sha256 = None
        else:
            plan_sha256 = integrity.get("plan_sha256")
            self._validate_hash(plan_sha256, "$.integrity.plan_sha256")
            recomputed_plan_sha256 = _canonical_runbook_plan_hash(document)
            if (
                recomputed_plan_sha256 is not None
                and isinstance(plan_sha256, str)
                and SHA256_PATTERN.fullmatch(plan_sha256)
                and plan_sha256 != recomputed_plan_sha256
            ):
                self.add(
                    "E_RUNBOOK_PLAN_HASH_MISMATCH",
                    "$.integrity.plan_sha256",
                    "integrity.plan_sha256 does not match the canonical runbook plan projection",
                )
        runbook_state = document.get("runbook_state")
        if document.get("runner_provider") == "native-android":
            if runbook_state is None:
                self.add(
                    "E_RUNBOOK_STATE_REQUIRED",
                    "$.runbook_state",
                    "native-android runbooks require an explicit preflight or executable state",
                )
            elif runbook_state not in ("preflight", "executable"):
                self.add(
                    "E_RUNBOOK_STATE_INVALID",
                    "$.runbook_state",
                    "native-android runbook_state must be 'preflight' or 'executable'",
                )
        self._validate_approval_ref(
            document.get("approval_ref"),
            actions,
            document.get("mutation_policy"),
            plan_sha256,
            enabled,
            document.get("runner_provider"),
            document.get("runbook_state"),
        )
        if self._validate_scenario_context(scenario, spec_bundle):
            assert scenario is not None
            self._validate_runbook_scenario_linkage(document, scenario)

    def _validate_result(
        self,
        document: Mapping[str, Any],
        spec_bundle: Mapping[str, Any] | None = None,
        scenario: Mapping[str, Any] | None = None,
        runbook: Mapping[str, Any] | None = None,
    ) -> None:
        self._require_fields(
            document,
            (
                "schema_version",
                "run_id",
                "scenario_id",
                "spec_version",
                "scenario_hash",
                "runbook_id",
                "runbook_hash",
                "target",
                "runner_provider",
                "started_at",
                "finished_at",
                "verdict",
                "execution",
                "subject",
                "judge",
                "evidence",
                "oracle_results",
                "blockers",
                "conflicts",
                "missing_evidence",
                "unsupported_reason",
                "diagnostic_attachments",
            ),
        )
        for field in ("run_id", "scenario_id", "runbook_id"):
            self._validate_identifier(document.get(field), _path("$", field))
        if not isinstance(document.get("spec_version"), str) or not document.get(
            "spec_version"
        ):
            self.add("E_FIELD_TYPE", "$.spec_version", "must be a non-empty string")
        self._validate_hash(document.get("scenario_hash"), "$.scenario_hash")
        self._validate_hash(document.get("runbook_hash"), "$.runbook_hash")

        verdict = document.get("verdict")
        if not _enum_member(verdict, VERDICTS):
            self.add(
                "E_VERDICT_UNSUPPORTED",
                "$.verdict",
                f"must be one of {', '.join(sorted(VERDICTS))}",
            )
        started = self._parse_timestamp(document.get("started_at"), "$.started_at")
        finished = self._parse_timestamp(document.get("finished_at"), "$.finished_at")
        if started is not None and finished is not None and finished < started:
            self.add(
                "E_TIMESTAMP_ORDER_INVALID",
                "$.finished_at",
                "finished_at must not precede started_at",
            )

        if spec_bundle is not None:
            self._validate_linked_source_refs(document, spec_bundle)

        execution = self._validate_result_execution(document.get("execution"))
        method = self._method_from_provider(document.get("runner_provider"))
        self._validate_target(
            document.get("target"), method, document.get("runner_provider"), None
        )
        self._validate_result_subject(document.get("subject"), document.get("target"), execution)
        judge = document.get("judge")
        judge_mode = self._validate_judge(judge)
        judge_evidence_hashes = self._hash_set(
            judge.get("evidence_hashes") if isinstance(judge, Mapping) else None
        )
        evidence_ids, evidence_kind_by_id, evidence_hash_by_id = self._validate_evidence(
            document.get("evidence")
        )
        evidence_kinds = set(evidence_kind_by_id.values())
        self._validate_command_evidence_ref(execution, evidence_kind_by_id)
        oracle_statuses, matched_oracle_evidence = self._validate_oracle_results(
            document.get("oracle_results"),
            evidence_ids,
            evidence_hash_by_id,
            judge_evidence_hashes,
            semantic=judge_mode == "semantic",
        )
        self._validate_result_context_linkage(
            document,
            spec_bundle,
            scenario,
            runbook,
            evidence_kind_by_id,
            semantic=judge_mode == "semantic",
        )

        collection_fields: dict[str, list[Any]] = {}
        for field in (
            "blockers",
            "conflicts",
            "missing_evidence",
            "diagnostic_attachments",
        ):
            value = document.get(field)
            if not isinstance(value, list):
                self.add("E_FIELD_TYPE", _path("$", field), "must be an array")
                collection_fields[field] = []
            else:
                collection_fields[field] = value

        self._validate_blockers(collection_fields["blockers"], evidence_ids)
        self._validate_conflicts(
            collection_fields["conflicts"],
            spec_bundle,
        )
        self._validate_missing_evidence(collection_fields["missing_evidence"])
        self._validate_diagnostic_attachments(
            collection_fields["diagnostic_attachments"]
        )
        if spec_bundle is not None:
            self._validate_result_judge_source_hashes(
                judge,
                spec_bundle,
                document.get("oracle_results"),
                collection_fields["conflicts"],
                semantic=judge_mode == "semantic",
            )

        status = execution.get("status") if isinstance(execution, dict) else None
        if verdict == "pass":
            if status != "completed":
                self.add(
                    "E_PASS_EXECUTION_INCOMPLETE",
                    "$.execution.status",
                    "pass requires execution.status='completed'",
                )
            if not oracle_statuses or any(value != "matched" for value in oracle_statuses):
                self.add(
                    "E_PASS_ORACLE_RESULT_REQUIRED",
                    "$.oracle_results",
                    "pass requires non-empty oracle results and every status must be matched",
                )
            if not evidence_kinds:
                self.add(
                    "E_PASS_EVIDENCE_REQUIRED",
                    "$.evidence",
                    "pass requires structured, independently inspectable evidence",
                )
            platform = (
                document.get("target", {}).get("platform")
                if isinstance(document.get("target"), dict)
                else None
            )
            if not isinstance(platform, str):
                platform = None
            required_state_kinds = {
                "web": {
                    "accessibility_state",
                    "api_state",
                    "db_state",
                    "dom_state",
                    "locator_result",
                },
                "mobile_web": {
                    "accessibility_state",
                    "api_state",
                    "db_state",
                    "dom_state",
                    "locator_result",
                },
                "android": {
                    "accessibility_state",
                    "android_logcat",
                    "api_state",
                    "db_state",
                    "locator_result",
                    "ui_hierarchy",
                },
            }.get(platform)
            if required_state_kinds is not None:
                for oracle_path, evidence_refs in matched_oracle_evidence:
                    referenced_kinds = {
                        evidence_kind_by_id[evidence_ref]
                        for evidence_ref in evidence_refs
                        if evidence_ref in evidence_kind_by_id
                    }
                    if referenced_kinds.isdisjoint(required_state_kinds):
                        self.add(
                            "E_PASS_OBJECTIVE_STATE_EVIDENCE_REQUIRED",
                            _path(oracle_path, "evidence_refs"),
                            "each matched web or Android oracle must cite provider-specific objective state evidence",
                        )
            for field in ("blockers", "conflicts", "missing_evidence"):
                if collection_fields[field]:
                    self.add(
                        "E_PASS_CONTRADICTORY_SUPPORT",
                        _path("$", field),
                        f"pass requires {field} to be empty",
                    )
        elif verdict == "fail" and "mismatched" not in oracle_statuses:
            self.add(
                "E_FAIL_MISMATCH_REQUIRED",
                "$.oracle_results",
                "fail requires at least one mismatched oracle result",
            )
        elif verdict == "conflict" and not collection_fields["conflicts"]:
            self.add(
                "E_CONFLICT_DETAILS_REQUIRED",
                "$.conflicts",
                "conflict requires at least one conflict record",
            )
        elif verdict == "insufficient_evidence" and (
            not collection_fields["missing_evidence"]
            or "not_evaluated" not in oracle_statuses
        ):
            self.add(
                "E_MISSING_EVIDENCE_DETAILS_REQUIRED",
                "$.missing_evidence",
                "insufficient_evidence requires missing evidence and a not_evaluated oracle",
            )
        elif verdict == "blocked":
            if not collection_fields["blockers"]:
                self.add(
                    "E_BLOCKER_DETAILS_REQUIRED",
                    "$.blockers",
                    "blocked requires at least one blocker record",
                )
            if status not in ("not_started", "partial"):
                self.add(
                    "E_BLOCKED_EXECUTION_STATUS_INVALID",
                    "$.execution.status",
                    "blocked requires execution.status='not_started' or 'partial'",
                )
        elif verdict == "unsupported":
            if status != "not_started" or not isinstance(
                document.get("unsupported_reason"), str
            ) or not document.get("unsupported_reason"):
                self.add(
                    "E_UNSUPPORTED_REASON_REQUIRED",
                    "$.unsupported_reason",
                    "unsupported requires execution.status='not_started' and a non-empty reason",
                )

        if verdict != "unsupported" and document.get("unsupported_reason") is not None:
            self.add(
                "E_UNSUPPORTED_REASON_FORBIDDEN",
                "$.unsupported_reason",
                "unsupported_reason must be null unless verdict='unsupported'",
            )

        target = document.get("target")
        if isinstance(target, dict) and target.get("platform") == "ios" and (
            status != "not_started" or verdict != "unsupported"
        ):
            self.add(
                "E_IOS_RESULT_EXECUTION_UNSUPPORTED",
                "$.verdict",
                "iOS results require execution.status='not_started' and verdict='unsupported'",
            )

    @staticmethod
    def _hash_set(value: Any) -> set[str]:
        if not isinstance(value, list):
            return set()
        return {item for item in value if isinstance(item, str)}

    def _validate_scenario_context(
        self,
        scenario: Mapping[str, Any] | None,
        spec_bundle: Mapping[str, Any] | None,
    ) -> bool:
        scenario_valid = isinstance(scenario, Mapping) and scenario.get(
            "schema_version"
        ) == "scenario-v1"
        if scenario is not None and not scenario_valid:
            self.add(
                "E_SCENARIO_CONTEXT_INVALID",
                "$",
                "linked scenario context must be a scenario-v1 object",
            )
            return False
        if scenario_valid and spec_bundle is not None:
            scenario_issues = validate_document(
                scenario, "scenario-v1", spec_bundle=spec_bundle
            )
            if scenario_issues:
                self.add(
                    "E_SCENARIO_CONTEXT_INVALID",
                    "$",
                    "linked scenario context does not satisfy scenario-v1",
                )
        return scenario_valid

    def _validate_runbook_scenario_linkage(
        self,
        runbook: Mapping[str, Any],
        scenario: Mapping[str, Any],
    ) -> None:
        scenario_hash = _canonical_json_hash(scenario)
        if scenario_hash is None:
            self.add(
                "E_SCENARIO_CONTEXT_INVALID",
                "$",
                "linked scenario cannot be serialized as canonical JSON",
            )
        identity = (
            ("scenario_id", scenario.get("id")),
            ("spec_version", scenario.get("spec_version")),
            ("scenario_hash", scenario_hash),
            ("method", scenario.get("method")),
            ("target", scenario.get("target")),
            ("runner_provider", scenario.get("runner_provider")),
        )
        for field, expected_value in identity:
            if runbook.get(field) != expected_value:
                self.add(
                    f"E_RUNBOOK_SCENARIO_{field.upper()}_MISMATCH",
                    _path("$", field),
                    f"runbook {field} must exactly match the linked scenario",
                )
        for field in (
            "source_refs",
            "preconditions",
            "fixture",
            "expected",
            "oracle",
            "mutation_policy",
        ):
            if runbook.get(field) != scenario.get(field):
                self.add(
                    f"E_RUNBOOK_SCENARIO_{field.upper()}_MISMATCH",
                    _path("$", field),
                    f"runbook {field} must preserve the linked scenario exactly",
                )

    def _validate_result_context_linkage(
        self,
        document: Mapping[str, Any],
        spec_bundle: Mapping[str, Any] | None,
        scenario: Mapping[str, Any] | None,
        runbook: Mapping[str, Any] | None,
        evidence_kind_by_id: Mapping[str, str],
        *,
        semantic: bool,
    ) -> None:
        scenario_valid = self._validate_scenario_context(scenario, spec_bundle)
        runbook_valid = isinstance(runbook, Mapping) and runbook.get(
            "schema_version"
        ) == "runbook-v1"

        if runbook is not None and not runbook_valid:
            self.add(
                "E_RUNBOOK_CONTEXT_INVALID",
                "$",
                "linked runbook context must be a runbook-v1 object",
            )
        if runbook_valid and spec_bundle is not None:
            runbook_issues = validate_document(
                runbook,
                "runbook-v1",
                spec_bundle=spec_bundle,
                scenario=scenario if scenario_valid else None,
            )
            if runbook_issues:
                self.add(
                    "E_RUNBOOK_CONTEXT_INVALID",
                    "$",
                    "linked runbook context does not satisfy runbook-v1",
                )

        if scenario_valid:
            assert scenario is not None
            scenario_hash = _canonical_json_hash(scenario)
            scenario_identity = (
                ("scenario_id", scenario.get("id")),
                ("spec_version", scenario.get("spec_version")),
                ("target", scenario.get("target")),
                ("runner_provider", scenario.get("runner_provider")),
            )
            for field, expected_value in scenario_identity:
                if document.get(field) != expected_value:
                    self.add(
                        f"E_RESULT_{field.upper()}_MISMATCH",
                        _path("$", field),
                        f"result {field} must exactly match the linked scenario",
                    )
            if scenario_hash is None:
                self.add(
                    "E_SCENARIO_CONTEXT_INVALID",
                    "$",
                    "linked scenario cannot be serialized as canonical JSON",
                )
            elif document.get("scenario_hash") != scenario_hash:
                self.add(
                    "E_RESULT_SCENARIO_HASH_MISMATCH",
                    "$.scenario_hash",
                    "result scenario_hash must equal the canonical linked scenario hash",
                )

            self._validate_linked_oracle_results(
                document,
                scenario,
                evidence_kind_by_id,
                semantic=semantic,
            )

        if runbook_valid:
            assert runbook is not None
            runbook_hash = _canonical_json_hash(runbook)
            if document.get("runbook_id") != runbook.get("runbook_id"):
                self.add(
                    "E_RESULT_RUNBOOK_ID_MISMATCH",
                    "$.runbook_id",
                    "result runbook_id must exactly match the linked runbook",
                )
            if runbook_hash is None:
                self.add(
                    "E_RUNBOOK_CONTEXT_INVALID",
                    "$",
                    "linked runbook cannot be serialized as canonical JSON",
                )
            elif document.get("runbook_hash") != runbook_hash:
                self.add(
                    "E_RESULT_RUNBOOK_HASH_MISMATCH",
                    "$.runbook_hash",
                    "result runbook_hash must equal the canonical linked runbook hash",
                )

            for field in (
                "scenario_id",
                "spec_version",
                "scenario_hash",
                "target",
                "runner_provider",
            ):
                if runbook.get(field) != document.get(field):
                    self.add(
                        f"E_RUNBOOK_RESULT_{field.upper()}_MISMATCH",
                        _path("$", field),
                        f"linked runbook {field} must exactly match the result identity",
                    )

        if scenario_valid and runbook_valid:
            assert scenario is not None and runbook is not None
            self._validate_runbook_scenario_linkage(runbook, scenario)

    def _validate_linked_oracle_results(
        self,
        document: Mapping[str, Any],
        scenario: Mapping[str, Any],
        evidence_kind_by_id: Mapping[str, str],
        *,
        semantic: bool,
    ) -> None:
        expected_by_id = {
            item.get("id"): item
            for item in (
                scenario.get("expected")
                if isinstance(scenario.get("expected"), list)
                else []
            )
            if isinstance(item, Mapping) and isinstance(item.get("id"), str)
        }
        oracle = scenario.get("oracle")
        rules = (
            oracle.get("rules")
            if isinstance(oracle, Mapping) and isinstance(oracle.get("rules"), list)
            else []
        )
        rules_by_id = {
            rule.get("id"): rule
            for rule in rules
            if isinstance(rule, Mapping) and isinstance(rule.get("id"), str)
        }
        oracle_results = document.get("oracle_results")
        if not isinstance(oracle_results, list):
            return

        counts: dict[str, int] = {}
        for index, oracle_result in enumerate(oracle_results):
            if not isinstance(oracle_result, Mapping):
                continue
            result_path = _path("$.oracle_results", index)
            oracle_id = oracle_result.get("oracle_id")
            if not isinstance(oracle_id, str) or oracle_id not in rules_by_id:
                self.add(
                    "E_ORACLE_RESULT_ORACLE_UNKNOWN",
                    _path(result_path, "oracle_id"),
                    "oracle_id must reference a linked scenario oracle rule",
                )
                continue
            counts[oracle_id] = counts.get(oracle_id, 0) + 1
            if counts[oracle_id] > 1:
                self.add(
                    "E_ORACLE_RESULT_DUPLICATE",
                    _path(result_path, "oracle_id"),
                    "each linked scenario oracle must appear at most once",
                )

            rule = rules_by_id[oracle_id]
            expected_id = rule.get("expectation_id")
            if oracle_result.get("expectation_id") != expected_id:
                self.add(
                    "E_ORACLE_RESULT_EXPECTATION_MISMATCH",
                    _path(result_path, "expectation_id"),
                    "expectation_id must exactly match the linked oracle rule",
                )

            evidence_refs = oracle_result.get("evidence_refs")
            cited_kinds = {
                evidence_kind_by_id[evidence_ref]
                for evidence_ref in evidence_refs
                if isinstance(evidence_refs, list)
                and isinstance(evidence_ref, str)
                and evidence_ref in evidence_kind_by_id
            } if isinstance(evidence_refs, list) else set()
            required_kind = rule.get("evidence_kind")
            if evidence_refs and (
                not isinstance(required_kind, str) or required_kind not in cited_kinds
            ):
                self.add(
                    "E_ORACLE_RESULT_EVIDENCE_KIND_MISMATCH",
                    _path(result_path, "evidence_refs"),
                    "cited evidence must include the linked oracle evidence_kind",
                )

            if semantic and isinstance(expected_id, str):
                expectation = expected_by_id.get(expected_id)
                expectation_refs = (
                    expectation.get("source_refs")
                    if isinstance(expectation, Mapping)
                    else None
                )
                result_ref_keys = self._source_ref_keys(
                    oracle_result.get("source_refs")
                )
                expectation_ref_keys = self._source_ref_keys(expectation_refs)
                if not result_ref_keys.issubset(expectation_ref_keys):
                    self.add(
                        "E_SEMANTIC_SOURCE_REF_OUT_OF_SCOPE",
                        _path(result_path, "source_refs"),
                        "semantic source_refs must be a subset of the linked expectation source_refs",
                    )

        execution = document.get("execution")
        execution_status = (
            execution.get("status") if isinstance(execution, Mapping) else None
        )
        if execution_status == "completed" or document.get("verdict") == "pass":
            for oracle_id in sorted(rules_by_id):
                if counts.get(oracle_id, 0) != 1:
                    self.add(
                        "E_ORACLE_RESULT_COVERAGE_INVALID",
                        "$.oracle_results",
                        "completed and pass results must cover each linked oracle exactly once",
                    )
                    break

    def _validate_blockers(
        self, blockers: Sequence[Any], evidence_ids: set[str]
    ) -> None:
        for index, blocker in enumerate(blockers):
            blocker_path = _path("$.blockers", index)
            if not isinstance(blocker, Mapping):
                self.add("E_BLOCKER_INVALID", blocker_path, "blocker must be an object")
                continue
            self._require_fields(
                blocker, ("code", "description", "evidence_refs"), blocker_path
            )
            for field in ("code", "description"):
                field_value = blocker.get(field)
                if not isinstance(field_value, str) or not field_value:
                    self.add(
                        "E_BLOCKER_INVALID",
                        _path(blocker_path, field),
                        "must be a non-empty string",
                    )
            self._validate_evidence_refs(
                blocker.get("evidence_refs"),
                _path(blocker_path, "evidence_refs"),
                evidence_ids,
            )

    def _validate_conflicts(
        self,
        conflicts: Sequence[Any],
        spec_bundle: Mapping[str, Any] | None,
    ) -> None:
        for index, conflict in enumerate(conflicts):
            conflict_path = _path("$.conflicts", index)
            if not isinstance(conflict, Mapping):
                self.add("E_CONFLICT_INVALID", conflict_path, "conflict must be an object")
                continue
            self._require_fields(
                conflict, ("id", "description", "source_refs"), conflict_path
            )
            self._validate_identifier(conflict.get("id"), _path(conflict_path, "id"))
            if not isinstance(conflict.get("description"), str) or not conflict.get(
                "description"
            ):
                self.add(
                    "E_CONFLICT_INVALID",
                    _path(conflict_path, "description"),
                    "description must be a non-empty string",
                )
            source_refs = conflict.get("source_refs")
            self._validate_source_refs(
                source_refs,
                _path(conflict_path, "source_refs"),
                require_nonempty=True,
            )
            if not isinstance(source_refs, list) or len(source_refs) < 2:
                self.add(
                    "E_CONFLICT_SOURCE_REFS_REQUIRED",
                    _path(conflict_path, "source_refs"),
                    "conflict records require at least two source_refs",
                )
            if spec_bundle is not None:
                self._validate_source_refs_against_bundle(
                    source_refs,
                    spec_bundle,
                    _path(conflict_path, "source_refs"),
                )

    def _validate_missing_evidence(self, items: Sequence[Any]) -> None:
        for index, item in enumerate(items):
            item_path = _path("$.missing_evidence", index)
            if not isinstance(item, Mapping):
                self.add(
                    "E_MISSING_EVIDENCE_INVALID",
                    item_path,
                    "missing_evidence entry must be an object",
                )
                continue
            self._require_fields(
                item, ("oracle_id", "evidence_kind", "reason"), item_path
            )
            for field in ("oracle_id", "reason"):
                field_value = item.get(field)
                if not isinstance(field_value, str) or not field_value:
                    self.add(
                        "E_MISSING_EVIDENCE_INVALID",
                        _path(item_path, field),
                        "must be a non-empty string",
                    )
            if not _enum_member(item.get("evidence_kind"), EVIDENCE_KINDS):
                self.add(
                    "E_EVIDENCE_KIND_UNSUPPORTED",
                    _path(item_path, "evidence_kind"),
                    f"must be one of {', '.join(sorted(EVIDENCE_KINDS))}",
                )

    def _validate_diagnostic_attachments(self, items: Sequence[Any]) -> None:
        for index, item in enumerate(items):
            item_path = _path("$.diagnostic_attachments", index)
            if not isinstance(item, Mapping):
                self.add(
                    "E_DIAGNOSTIC_ATTACHMENT_INVALID",
                    item_path,
                    "diagnostic attachment must be an object",
                )
                continue
            self._require_fields(item, ("kind", "artifact_ref", "sha256"), item_path)
            if item.get("kind") not in ("image", "screenshot", "video"):
                self.add(
                    "E_DIAGNOSTIC_ATTACHMENT_KIND_UNSUPPORTED",
                    _path(item_path, "kind"),
                    "kind must be image, screenshot, or video",
                )
            self._validate_relative_artifact_ref(
                item.get("artifact_ref"), _path(item_path, "artifact_ref")
            )
            self._validate_hash(item.get("sha256"), _path(item_path, "sha256"))

    def _validate_evidence_refs(
        self, value: Any, path: str, evidence_ids: set[str]
    ) -> list[str]:
        if not isinstance(value, list):
            self.add("E_FIELD_TYPE", path, "must be an array")
            return []
        resolved: list[str] = []
        for index, evidence_ref in enumerate(value):
            ref_path = _path(path, index)
            if not isinstance(evidence_ref, str) or evidence_ref not in evidence_ids:
                self.add(
                    "E_ORACLE_EVIDENCE_UNKNOWN",
                    ref_path,
                    "evidence reference must resolve to an evidence id",
                )
            else:
                resolved.append(evidence_ref)
        return resolved

    def _parse_timestamp(self, value: Any, path: str) -> datetime | None:
        if not isinstance(value, str) or not value.endswith("Z"):
            self.add("E_TIMESTAMP_INVALID", path, "must be an RFC 3339 UTC string")
            return None
        try:
            return datetime.fromisoformat(value[:-1] + "+00:00")
        except ValueError:
            self.add("E_TIMESTAMP_INVALID", path, "must be an RFC 3339 UTC string")
            return None

    def _validate_result_execution(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            self.add("E_EXECUTION_INVALID", "$.execution", "execution must be an object")
            return {}
        self._require_fields(
            value,
            ("status", "attempt", "retry_count", "command_evidence_ref", "runner_version"),
            "$.execution",
        )
        if value.get("status") not in ("not_started", "partial", "completed"):
            self.add(
                "E_EXECUTION_STATUS_UNSUPPORTED",
                "$.execution.status",
                "must be not_started, partial, or completed",
            )
        attempt = value.get("attempt")
        if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
            self.add(
                "E_EXECUTION_ATTEMPT_INVALID",
                "$.execution.attempt",
                "attempt must be a positive integer",
            )
        retry_count = value.get("retry_count")
        if (
            not isinstance(retry_count, int)
            or isinstance(retry_count, bool)
            or retry_count < 0
        ):
            self.add(
                "E_EXECUTION_RETRY_INVALID",
                "$.execution.retry_count",
                "retry_count must be a non-negative integer",
            )
        command_ref = value.get("command_evidence_ref")
        if command_ref is not None and not isinstance(command_ref, str):
            self.add(
                "E_FIELD_TYPE",
                "$.execution.command_evidence_ref",
                "must be a string or null",
            )
        if not isinstance(value.get("runner_version"), str) or not value.get(
            "runner_version"
        ):
            self.add(
                "E_FIELD_TYPE",
                "$.execution.runner_version",
                "must be a non-empty string",
            )
        return value

    def _validate_result_subject(
        self, value: Any, target: Any, execution: Mapping[str, Any]
    ) -> None:
        if not isinstance(value, dict):
            self.add("E_SUBJECT_INVALID", "$.subject", "subject must be an object")
            return
        self._require_fields(value, ("build", "artifact", "native_runtime"), "$.subject")
        build = value.get("build")
        if build is not None:
            if not isinstance(build, dict):
                self.add("E_SUBJECT_INVALID", "$.subject.build", "build must be an object or null")
            else:
                self._require_fields(build, ("ref", "sha256"), "$.subject.build")
                self._validate_hash(build.get("sha256"), "$.subject.build.sha256")

        platform = target.get("platform") if isinstance(target, dict) else None
        artifact = value.get("artifact")
        runtime = value.get("native_runtime")
        android_started = platform == "android" and execution.get("status") in (
            "partial",
            "completed",
        )
        if android_started:
            if not isinstance(artifact, dict):
                self.add(
                    "E_ANDROID_ARTIFACT_REQUIRED",
                    "$.subject.artifact",
                    "started Android execution requires registered APK metadata",
                )
            else:
                self._require_fields(
                    artifact, ("id", "type", "sha256", "package_id"), "$.subject.artifact"
                )
                if artifact.get("type") != "apk":
                    code = (
                        "E_ANDROID_AAB_UNSUPPORTED"
                        if artifact.get("type") == "aab"
                        else "E_TARGET_ARTIFACT_UNSUPPORTED"
                    )
                    self.add(code, "$.subject.artifact.type", "Android execution requires an APK")
                self._validate_hash(artifact.get("sha256"), "$.subject.artifact.sha256")
                if not isinstance(artifact.get("package_id"), str) or not artifact.get(
                    "package_id"
                ):
                    self.add(
                        "E_ANDROID_PACKAGE_ID_REQUIRED",
                        "$.subject.artifact.package_id",
                        "Android execution requires package_id",
                    )
            if not isinstance(runtime, dict):
                self.add(
                    "E_ANDROID_RUNTIME_REQUIRED",
                    "$.subject.native_runtime",
                    "started Android execution requires Emulator runtime identity",
                )
            else:
                self._require_fields(
                    runtime,
                    (
                        "device_type",
                        "device_id",
                        "avd",
                        "device_name",
                        "os_version",
                        "orientation",
                        "language",
                        "locale",
                        "reset_policy",
                        "appium_version",
                        "automation_driver",
                        "automation_driver_version",
                    ),
                    "$.subject.native_runtime",
                )
                if runtime.get("device_type") != "emulator":
                    self.add(
                        "E_ANDROID_PHYSICAL_DEVICE_UNSUPPORTED",
                        "$.subject.native_runtime.device_type",
                        "Android results support Emulator only",
                    )
                if runtime.get("orientation") not in ("portrait", "landscape"):
                    self.add(
                        "E_ANDROID_ORIENTATION_UNSUPPORTED",
                        "$.subject.native_runtime.orientation",
                        "orientation must be portrait or landscape",
                    )
                if runtime.get("reset_policy") not in ("clean", "preserve"):
                    self.add(
                        "E_ANDROID_RESET_POLICY_UNSUPPORTED",
                        "$.subject.native_runtime.reset_policy",
                        "reset_policy must be clean or preserve",
                    )
                if runtime.get("automation_driver") != "uiautomator2":
                    self.add(
                        "E_ANDROID_AUTOMATION_DRIVER_UNSUPPORTED",
                        "$.subject.native_runtime.automation_driver",
                        "automation_driver must be uiautomator2",
                    )
                for field in (
                    "device_id",
                    "avd",
                    "device_name",
                    "os_version",
                    "language",
                    "locale",
                ):
                    field_value = runtime.get(field)
                    if not isinstance(field_value, str) or not field_value:
                        self.add(
                            "E_ANDROID_RUNTIME_FIELD_REQUIRED",
                            _path("$.subject.native_runtime", field),
                            "Android runtime identity fields must be non-empty strings",
                        )
                for field in ("appium_version", "automation_driver_version"):
                    field_value = runtime.get(field)
                    if execution.get("status") == "completed" or field_value is not None:
                        if not isinstance(field_value, str) or not field_value:
                            self.add(
                                "E_ANDROID_RUNTIME_FIELD_REQUIRED",
                                _path("$.subject.native_runtime", field),
                                "completed Android execution requires observed runtime versions",
                            )

    def _validate_judge(self, value: Any) -> str | None:
        if not isinstance(value, dict):
            self.add("E_JUDGE_INVALID", "$.judge", "judge must be an object")
            return None
        self._require_fields(
            value,
            ("mode", "name", "version", "attempt", "model", "source_hashes", "evidence_hashes", "decided_at"),
            "$.judge",
        )
        mode = value.get("mode")
        if not _enum_member(mode, ORACLE_MODES):
            self.add("E_JUDGE_MODE_UNSUPPORTED", "$.judge.mode", "must be deterministic, semantic, or manual")
        attempt = value.get("attempt")
        if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
            self.add("E_JUDGE_ATTEMPT_INVALID", "$.judge.attempt", "attempt must be a positive integer")
        for field in ("source_hashes", "evidence_hashes"):
            hashes = value.get(field)
            if not isinstance(hashes, list) or not hashes:
                self.add("E_JUDGE_INPUT_HASHES_REQUIRED", _path("$.judge", field), "must be a non-empty hash array")
            else:
                for index, hash_value in enumerate(hashes):
                    self._validate_hash(hash_value, _path(_path("$.judge", field), index))
        self._parse_timestamp(value.get("decided_at"), "$.judge.decided_at")
        if mode == "semantic":
            model = value.get("model")
            if not isinstance(model, dict):
                self.add("E_SEMANTIC_MODEL_IDENTITY_REQUIRED", "$.judge.model", "semantic judge requires model metadata")
            else:
                self._require_fields(
                    model,
                    ("provider", "model_version", "prompt_version", "rubric_hash"),
                    "$.judge.model",
                )
                for field in (
                    "provider",
                    "model_version",
                    "prompt_version",
                    "rubric_hash",
                ):
                    field_value = model.get(field)
                    if not isinstance(field_value, str) or not field_value:
                        self.add(
                            "E_SEMANTIC_MODEL_IDENTITY_REQUIRED",
                            _path("$.judge.model", field),
                            "semantic model identity fields must be non-empty strings",
                        )
                self._validate_hash(model.get("rubric_hash"), "$.judge.model.rubric_hash")
        elif value.get("model") is not None:
            self.add("E_JUDGE_MODEL_FORBIDDEN", "$.judge.model", "non-semantic judge requires model=null")
        return mode if isinstance(mode, str) else None

    def _validate_evidence(
        self, value: Any
    ) -> tuple[set[str], dict[str, str], dict[str, str]]:
        if not isinstance(value, list):
            self.add("E_FIELD_TYPE", "$.evidence", "must be an array")
            return set(), {}, {}
        ids: set[str] = set()
        kind_by_id: dict[str, str] = {}
        hash_by_id: dict[str, str] = {}
        for index, item in enumerate(value):
            item_path = _path("$.evidence", index)
            if not isinstance(item, dict):
                self.add("E_FIELD_TYPE", item_path, "evidence item must be an object")
                continue
            self._require_fields(
                item, ("id", "kind", "collected_at", "producer", "sha256", "redactions"), item_path
            )
            evidence_id = item.get("id")
            self._validate_identifier(evidence_id, _path(item_path, "id"))
            if isinstance(evidence_id, str) and evidence_id in ids:
                self.add("E_DUPLICATE_ID", _path(item_path, "id"), "evidence id must be unique")
            elif isinstance(evidence_id, str):
                ids.add(evidence_id)
            kind = item.get("kind")
            if _enum_member(kind, SELF_REPORT_EVIDENCE_KINDS):
                self.add(
                    "E_SELF_REPORT_EVIDENCE_FORBIDDEN",
                    _path(item_path, "kind"),
                    "runner or agent self-report is not admissible evidence",
                )
            if not _enum_member(kind, EVIDENCE_KINDS):
                self.add(
                    "E_EVIDENCE_KIND_UNSUPPORTED",
                    _path(item_path, "kind"),
                    f"must be one of {', '.join(sorted(EVIDENCE_KINDS))}",
                )
            elif isinstance(kind, str) and isinstance(evidence_id, str):
                kind_by_id[evidence_id] = kind
            self._parse_timestamp(item.get("collected_at"), _path(item_path, "collected_at"))
            evidence_hash = item.get("sha256")
            self._validate_hash(evidence_hash, _path(item_path, "sha256"))
            if isinstance(evidence_id, str) and isinstance(evidence_hash, str):
                hash_by_id[evidence_id] = evidence_hash
            if not isinstance(item.get("redactions"), list):
                self.add("E_FIELD_TYPE", _path(item_path, "redactions"), "redactions must be an array")
            producer = item.get("producer")
            if not isinstance(producer, dict):
                self.add("E_EVIDENCE_PRODUCER_INVALID", _path(item_path, "producer"), "producer must be an object")
            else:
                self._require_fields(producer, ("type", "name"), _path(item_path, "producer"))
                if producer.get("type") not in ("runner", "developer_test", "api_probe", "db_probe", "build_system", "adapter", "human"):
                    self.add("E_EVIDENCE_PRODUCER_INVALID", _path(_path(item_path, "producer"), "type"), "unsupported producer type")
            record = item.get("record")
            if (
                kind == "structured_log"
                and isinstance(producer, dict)
                and producer.get("type") in ("runner", "adapter")
                and isinstance(record, (Mapping, list))
                and self._contains_self_report_claim(record)
            ):
                self.add(
                    "E_SELF_REPORT_EVIDENCE_FORBIDDEN",
                    _path(item_path, "record"),
                    "runner verdict, self_report, or success declarations are not evidence",
                )
            has_record = "record" in item
            has_artifact_ref = "artifact_ref" in item
            if has_record == has_artifact_ref:
                self.add("E_EVIDENCE_PAYLOAD_INVALID", item_path, "exactly one of record or artifact_ref is required")
            if has_artifact_ref:
                self._validate_relative_artifact_ref(item.get("artifact_ref"), _path(item_path, "artifact_ref"))
        return ids, kind_by_id, hash_by_id

    @staticmethod
    def _contains_self_report_claim(value: Any) -> bool:
        if isinstance(value, Mapping):
            for key, child in value.items():
                normalized_key = _key_name(key)
                if normalized_key in ("verdict", "selfreport", "success"):
                    return True
                if (
                    normalized_key == "status"
                    and isinstance(child, str)
                    and child.lower() == "pass"
                ):
                    return True
                if ContractValidator._contains_self_report_claim(child):
                    return True
        elif isinstance(value, list):
            return any(
                ContractValidator._contains_self_report_claim(item) for item in value
            )
        return False

    def _validate_command_evidence_ref(
        self, execution: Mapping[str, Any], evidence_kind_by_id: Mapping[str, str]
    ) -> None:
        command_ref = execution.get("command_evidence_ref")
        if command_ref is None:
            return
        if not isinstance(command_ref, str) or command_ref not in evidence_kind_by_id:
            self.add(
                "E_COMMAND_EVIDENCE_REF_UNKNOWN",
                "$.execution.command_evidence_ref",
                "command_evidence_ref must resolve to an evidence id",
            )
            return
        if evidence_kind_by_id[command_ref] not in ("test_command", "structured_log"):
            self.add(
                "E_COMMAND_EVIDENCE_KIND_INVALID",
                "$.execution.command_evidence_ref",
                "command_evidence_ref must reference test_command or structured_log evidence",
            )

    def _validate_oracle_results(
        self,
        value: Any,
        evidence_ids: set[str],
        evidence_hash_by_id: Mapping[str, str],
        judge_evidence_hashes: set[str],
        *,
        semantic: bool = False,
    ) -> tuple[list[str], list[tuple[str, list[str]]]]:
        if not isinstance(value, list):
            self.add("E_FIELD_TYPE", "$.oracle_results", "must be an array")
            return [], []
        statuses: list[str] = []
        matched_evidence: list[tuple[str, list[str]]] = []
        for index, item in enumerate(value):
            item_path = _path("$.oracle_results", index)
            if not isinstance(item, dict):
                self.add("E_FIELD_TYPE", item_path, "oracle result must be an object")
                continue
            status = item.get("status")
            self._require_fields(
                item,
                (
                    "oracle_id",
                    "expectation_id",
                    "status",
                    "evidence_refs",
                    "source_refs",
                    "actual",
                    "reason",
                ),
                item_path,
            )
            source_refs = item.get("source_refs")
            semantic_requires_refs = semantic and status in ("matched", "mismatched")
            self._validate_source_refs(
                source_refs,
                _path(item_path, "source_refs"),
                require_nonempty=semantic_requires_refs,
            )
            if semantic_requires_refs and (
                not isinstance(source_refs, list) or not source_refs
            ):
                self.add(
                    "E_SEMANTIC_SOURCE_REFS_REQUIRED",
                    _path(item_path, "source_refs"),
                    "semantic matched/mismatched oracle results require non-empty source_refs",
                )
            if status not in ("matched", "mismatched", "not_evaluated"):
                self.add("E_ORACLE_RESULT_STATUS_UNSUPPORTED", _path(item_path, "status"), "must be matched, mismatched, or not_evaluated")
            else:
                statuses.append(status)
            refs = self._validate_evidence_refs(
                item.get("evidence_refs"),
                _path(item_path, "evidence_refs"),
                evidence_ids,
            )
            for ref_index, evidence_ref in enumerate(refs):
                evidence_hash = evidence_hash_by_id.get(evidence_ref)
                if evidence_hash not in judge_evidence_hashes:
                    self.add(
                        "E_JUDGE_EVIDENCE_HASH_MISSING",
                        _path(_path(item_path, "evidence_refs"), ref_index),
                        "the cited evidence sha256 must be registered in judge.evidence_hashes",
                    )
            if status in ("matched", "mismatched") and not refs:
                self.add("E_ORACLE_EVIDENCE_REQUIRED", _path(item_path, "evidence_refs"), "evaluated oracle results require evidence")
            if status == "matched":
                matched_evidence.append((item_path, refs))
            if status in ("mismatched", "not_evaluated") and (
                not isinstance(item.get("reason"), str) or not item.get("reason")
            ):
                self.add("E_ORACLE_REASON_REQUIRED", _path(item_path, "reason"), "reason is required for mismatched and not_evaluated")
        return statuses, matched_evidence

    def _validate_relative_artifact_ref(self, value: Any, path: str) -> None:
        if not isinstance(value, str) or not value:
            self.add("E_ARTIFACT_REF_INVALID", path, "artifact_ref must be a non-empty relative path")
            return
        candidate = Path(value)
        if candidate.is_absolute() or ".." in candidate.parts:
            self.add("E_ARTIFACT_REF_INVALID", path, "artifact_ref must be result-relative and must not contain '..'")

    def _validate_identifier_and_title(self, document: Mapping[str, Any]) -> None:
        self._validate_identifier(document.get("id"), "$.id")
        title = document.get("title")
        if not isinstance(title, str) or not title.strip():
            self.add("E_FIELD_TYPE", "$.title", "must be a non-empty string")

    def _validate_identifier(self, value: Any, path: str) -> None:
        if not isinstance(value, str) or not IDENTIFIER_PATTERN.fullmatch(value):
            self.add(
                "E_IDENTIFIER_INVALID",
                path,
                "must match ^[a-z0-9][a-z0-9._-]{0,127}$",
            )

    def _validate_hash(self, value: Any, path: str) -> None:
        if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
            self.add(
                "E_HASH_INVALID",
                path,
                "must use lowercase sha256:<64 hexadecimal characters>",
            )

    def _validate_canonical_source_text(
        self, value: Any, path: str, *, required: bool
    ) -> None:
        if not isinstance(value, str):
            self.add("E_FIELD_TYPE", path, "must be a string")
            return
        normalized = _normalize_source_text(value)
        if required and not normalized:
            self.add(
                "E_FIELD_TYPE",
                path,
                "must remain non-empty after canonical text normalization",
            )
        if value != normalized:
            self.add(
                "E_SOURCE_TEXT_NOT_CANONICAL",
                path,
                "must already be in canonical NFC/LF/trimmed source text form",
            )

    def _validate_approval_ref(
        self,
        approval_ref: Any,
        actions: Sequence[Mapping[str, Any]],
        mutation_policy: Any,
        plan_sha256: Any,
        execution_enabled: bool | None,
        runner_provider: Any,
        runbook_state: Any,
    ) -> None:
        mutation_ids = {
            action.get("id")
            for action in actions
            if isinstance(action.get("id"), str)
            and (
                _enum_member(action.get("mutation"), {"potential", "confirmed"})
                or _enum_member(action.get("action"), IMPLICIT_MUTATIONS)
            )
        }
        if not mutation_ids:
            if approval_ref is not None:
                self.add(
                    "E_READ_ONLY_APPROVAL_REF_INVALID",
                    "$.approval_ref",
                    "read-only runbooks require approval_ref=null",
                )
            return
        if runner_provider == "native-android" and runbook_state == "preflight":
            if approval_ref is not None:
                self.add(
                    "E_PREFLIGHT_APPROVAL_FORBIDDEN",
                    "$.approval_ref",
                    "preflight runbooks require approval_ref=null",
                )
            return
        if runner_provider == "native-android" and runbook_state == "executable" and approval_ref is None:
            self.add(
                "E_MUTATION_APPROVAL_REF_REQUIRED",
                "$.approval_ref",
                "executable native-android runbooks require an immutable approval_ref object",
            )
            return
        if approval_ref is None and execution_enabled is not True:
            return
        if not isinstance(approval_ref, dict):
            self.add(
                "E_MUTATION_APPROVAL_REF_REQUIRED",
                "$.approval_ref",
                "executable mutation runbooks require an immutable approval_ref object",
            )
            return
        self._require_fields(
            approval_ref,
            (
                "id",
                "record_sha256",
                "plan_sha256",
                "approved_step_ids",
                "environment",
                "scope",
                "expires_at",
                "approved_by_ref",
            ),
            "$.approval_ref",
        )
        if runner_provider == "native-android":
            for field in ("provider_plan_hash", "runtime_binding_sha256"):
                if field not in approval_ref:
                    self.add(
                        "E_REQUIRED",
                        _path("$.approval_ref", field),
                        "required field is missing",
                    )
                self._validate_hash(
                    approval_ref.get(field),
                    _path("$.approval_ref", field),
                )
        for field in ("id", "environment", "approved_by_ref"):
            value = approval_ref.get(field)
            if not isinstance(value, str) or not value:
                self.add(
                    "E_FIELD_TYPE",
                    _path("$.approval_ref", field),
                    "must be a non-empty string",
                )
        self._validate_hash(
            approval_ref.get("record_sha256"), "$.approval_ref.record_sha256"
        )
        self._validate_hash(
            approval_ref.get("plan_sha256"), "$.approval_ref.plan_sha256"
        )
        if isinstance(plan_sha256, str) and approval_ref.get("plan_sha256") != plan_sha256:
            self.add(
                "E_APPROVAL_PLAN_HASH_MISMATCH",
                "$.approval_ref.plan_sha256",
                "approval plan_sha256 must equal integrity.plan_sha256",
            )
        approved_ids = approval_ref.get("approved_step_ids")
        policy_scope = (
            mutation_policy.get("approval_scope")
            if isinstance(mutation_policy, dict)
            else None
        )
        approved_set: set[str] = set()
        if not isinstance(approved_ids, list):
            self.add(
                "E_APPROVAL_SCOPE_INVALID",
                "$.approval_ref.approved_step_ids",
                "approved_step_ids must be an array of strings",
            )
        else:
            if any(not isinstance(item, str) for item in approved_ids):
                self.add(
                    "E_APPROVAL_SCOPE_INVALID",
                    "$.approval_ref.approved_step_ids",
                    "approved_step_ids entries must be strings",
                )
            approved_set = {item for item in approved_ids if isinstance(item, str)}
        if approved_set != mutation_ids:
            self.add(
                "E_APPROVAL_SCOPE_MISMATCH",
                "$.approval_ref.approved_step_ids",
                "approved_step_ids must exactly equal the mutation step ids",
            )
        if (
            isinstance(policy_scope, list)
            and all(isinstance(item, str) for item in policy_scope)
            and isinstance(approved_ids, list)
            and all(isinstance(item, str) for item in approved_ids)
            and approved_ids != policy_scope
        ):
            self.add(
                "E_APPROVAL_SCOPE_MISMATCH",
                "$.approval_ref.approved_step_ids",
                "approved_step_ids must equal mutation_policy.approval_scope",
            )
        if approval_ref.get("scope") not in ("single_run", "runbook_revision"):
            self.add(
                "E_APPROVAL_SCOPE_TYPE_UNSUPPORTED",
                "$.approval_ref.scope",
                "scope must be 'single_run' or 'runbook_revision'",
            )

    def _validate_source_refs(
        self, value: Any, path: str, *, require_nonempty: bool = True
    ) -> None:
        if not isinstance(value, list):
            self.add(
                "E_SOURCE_REFS_REQUIRED",
                path,
                "source_refs must be an array",
            )
            return
        if require_nonempty and not value:
            self.add(
                "E_SOURCE_REFS_REQUIRED",
                path,
                "source_refs must contain at least one specification anchor reference",
            )
            return
        for index, source_ref in enumerate(value):
            ref_path = _path(path, index)
            if not isinstance(source_ref, dict):
                self.add(
                    "E_SOURCE_REF_INVALID",
                    ref_path,
                    "source reference must be an object with source_id and anchor_id",
                )
                continue
            for field in ("source_id", "anchor_id"):
                field_value = source_ref.get(field)
                if not isinstance(field_value, str) or not field_value:
                    self.add(
                        "E_SOURCE_REF_INVALID",
                        _path(ref_path, field),
                        "must be a non-empty string",
                    )

    def _validate_linked_source_refs(
        self, document: Mapping[str, Any], spec_bundle: Mapping[str, Any]
    ) -> None:
        if not isinstance(spec_bundle, Mapping) or spec_bundle.get(
            "schema_version"
        ) != "spec-bundle-v1":
            self.add(
                "E_BUNDLE_CONTEXT_INVALID",
                "$",
                "linked source validation requires a spec-bundle-v1 context",
            )
            return
        if document.get("spec_version") != spec_bundle.get("spec_version"):
            self.add(
                "E_SPEC_VERSION_MISMATCH",
                "$.spec_version",
                "document spec_version must equal the linked spec bundle version",
            )

        self._validate_source_refs_against_bundle(
            document.get("source_refs"), spec_bundle, "$.source_refs"
        )

    def _validate_source_refs_against_bundle(
        self,
        source_refs: Any,
        spec_bundle: Mapping[str, Any],
        path: str,
    ) -> None:
        if not isinstance(source_refs, list):
            return
        sources_by_id: dict[str, list[Mapping[str, Any]]] = {}
        sources = spec_bundle.get("sources")
        if isinstance(sources, list):
            for source in sources:
                if isinstance(source, Mapping) and isinstance(source.get("id"), str):
                    sources_by_id.setdefault(source["id"], []).append(source)
        for index, source_ref in enumerate(source_refs):
            if not isinstance(source_ref, Mapping):
                continue
            ref_path = _path(path, index)
            source_id = source_ref.get("source_id")
            anchor_id = source_ref.get("anchor_id")
            if not isinstance(source_id, str) or not isinstance(anchor_id, str):
                continue
            matched_sources = sources_by_id.get(source_id, [])
            if len(matched_sources) != 1:
                code = (
                    "E_SOURCE_REF_SOURCE_UNKNOWN"
                    if not matched_sources
                    else "E_SOURCE_REF_SOURCE_AMBIGUOUS"
                )
                self.add(
                    code,
                    _path(ref_path, "source_id"),
                    "source_id must resolve to exactly one linked bundle source",
                )
                continue
            anchors = matched_sources[0].get("anchors")
            matched_anchors = [
                anchor
                for anchor in (anchors if isinstance(anchors, list) else [])
                if isinstance(anchor, Mapping) and anchor.get("id") == anchor_id
            ]
            if len(matched_anchors) != 1:
                code = (
                    "E_SOURCE_REF_ANCHOR_UNKNOWN"
                    if not matched_anchors
                    else "E_SOURCE_REF_ANCHOR_AMBIGUOUS"
                )
                self.add(
                    code,
                    _path(ref_path, "anchor_id"),
                    "anchor_id must resolve to exactly one anchor in the linked source",
                )

    def _validate_result_judge_source_hashes(
        self,
        judge: Any,
        spec_bundle: Mapping[str, Any],
        oracle_results: Any,
        conflicts: Sequence[Any],
        *,
        semantic: bool,
    ) -> None:
        if not isinstance(judge, Mapping):
            return
        sources = spec_bundle.get("sources")
        if not isinstance(sources, list):
            return
        sources_by_id: dict[str, list[Mapping[str, Any]]] = {}
        linked_hashes: set[str] = set()
        for source in sources:
            if not isinstance(source, Mapping):
                continue
            source_id = source.get("id")
            content_hash = source.get("content_hash")
            if isinstance(source_id, str):
                sources_by_id.setdefault(source_id, []).append(source)
            if isinstance(content_hash, str):
                linked_hashes.add(content_hash)

        judge_source_hashes = self._hash_set(judge.get("source_hashes"))
        raw_judge_hashes = judge.get("source_hashes")
        if isinstance(raw_judge_hashes, list):
            for index, source_hash in enumerate(raw_judge_hashes):
                if isinstance(source_hash, str) and source_hash not in linked_hashes:
                    self.add(
                        "E_JUDGE_SOURCE_HASH_UNLINKED",
                        _path("$.judge.source_hashes", index),
                        "judge.source_hashes entries must match linked bundle source content_hash values",
                    )

        if not semantic:
            return

        referenced_sources: list[tuple[str, str]] = []
        if isinstance(oracle_results, list):
            for index, oracle_result in enumerate(oracle_results):
                if not isinstance(oracle_result, Mapping) or oracle_result.get(
                    "status"
                ) not in ("matched", "mismatched"):
                    continue
                refs = oracle_result.get("source_refs")
                refs_path = _path(_path("$.oracle_results", index), "source_refs")
                self._validate_source_refs_against_bundle(
                    refs, spec_bundle, refs_path
                )
                if isinstance(refs, list):
                    for ref_index, source_ref in enumerate(refs):
                        if isinstance(source_ref, Mapping) and isinstance(
                            source_ref.get("source_id"), str
                        ):
                            referenced_sources.append(
                                (
                                    _path(_path(refs_path, ref_index), "source_id"),
                                    source_ref["source_id"],
                                )
                            )
        for index, conflict in enumerate(conflicts):
            if not isinstance(conflict, Mapping):
                continue
            refs = conflict.get("source_refs")
            refs_path = _path(_path("$.conflicts", index), "source_refs")
            if isinstance(refs, list):
                for ref_index, source_ref in enumerate(refs):
                    if isinstance(source_ref, Mapping) and isinstance(
                        source_ref.get("source_id"), str
                    ):
                        referenced_sources.append(
                            (
                                _path(_path(refs_path, ref_index), "source_id"),
                                source_ref["source_id"],
                            )
                        )

        for source_path, source_id in referenced_sources:
            matched_sources = sources_by_id.get(source_id, [])
            if len(matched_sources) != 1:
                continue
            content_hash = matched_sources[0].get("content_hash")
            if isinstance(content_hash, str) and content_hash not in judge_source_hashes:
                self.add(
                    "E_JUDGE_SOURCE_HASH_MISSING",
                    source_path,
                    "semantic source_refs require the linked source content_hash in judge.source_hashes",
                )

    def _execution_enabled(
        self, value: Any, path: str, required: bool = True
    ) -> bool | None:
        if not isinstance(value, dict):
            if value is not None or required:
                self.add("E_EXECUTION_INVALID", path, "execution must be an object")
            return None
        enabled = value.get("enabled")
        if not isinstance(enabled, bool):
            self.add(
                "E_EXECUTION_INVALID",
                _path(path, "enabled"),
                "execution.enabled must be a boolean",
            )
            return None
        return enabled

    def _validate_target(
        self,
        value: Any,
        method: Any,
        runner_provider: Any,
        execution_enabled: bool | None,
    ) -> None:
        if not isinstance(value, dict):
            self.add("E_TARGET_INVALID", "$.target", "target must be an object")
            return
        platform = value.get("platform")
        device_value = value.get("device")
        if isinstance(device_value, dict):
            device = device_value.get("kind")
            device_path = "$.target.device.kind"
        else:
            device = device_value
            device_path = "$.target.device"
        artifact_type = value.get("artifact_type")
        artifact = value.get("artifact")
        if artifact_type is None and isinstance(artifact, dict):
            artifact_type = artifact.get("format", artifact.get("type"))

        if not _enum_member(platform, PLATFORMS):
            self.add(
                "E_PLATFORM_UNSUPPORTED",
                "$.target.platform",
                f"must be one of {', '.join(sorted(PLATFORMS))}",
            )
            return

        if platform == "android" and _enum_member(device, PHYSICAL_DEVICE_VALUES):
            self.add(
                "E_ANDROID_PHYSICAL_DEVICE_UNSUPPORTED",
                device_path,
                "Android physical devices are unsupported; use an Emulator",
            )
        if platform == "android" and self._is_aab(artifact_type, artifact):
            self.add(
                "E_ANDROID_AAB_UNSUPPORTED",
                "$.target.artifact_type",
                "Android App Bundle (AAB) is unsupported; provide an APK reference",
            )

        mobile_native = platform == "mobile_web" and (
            method == "native"
            or runner_provider in ("native-android", "native-ios")
            or device in ("emulator", "simulator", *PHYSICAL_DEVICE_VALUES)
            or artifact_type in ("apk", "aab", "app_zip")
        )
        if mobile_native:
            self.add(
                "E_MOBILE_WEB_NATIVE_CONFLICT",
                "$.target.platform",
                "responsive mobile web must use method='web' and runner_provider='web-playwright'",
            )

        if method in ("unit", "integration"):
            expected_provider = "developer-test"
        elif method == "manual":
            expected_provider = "manual"
        elif not isinstance(method, str):
            expected_provider = None
        else:
            expected_provider = EXPECTED_PROVIDER.get((platform, method))
            if expected_provider is None and _enum_member(method, METHODS) and not mobile_native:
                self.add(
                    "E_PLATFORM_METHOD_UNSUPPORTED",
                    "$.method",
                    f"method={method!r} is unsupported for platform={platform!r}",
                )
        if expected_provider is not None and runner_provider != expected_provider:
            self.add(
                "E_RUNNER_PROVIDER_MISMATCH",
                "$.runner_provider",
                f"expected runner_provider={expected_provider!r} for this target and method",
            )

        if method in ("web", "native"):
            expected_device = EXPECTED_DEVICE.get(platform)
            if expected_device is not None and device != expected_device:
                code = (
                    "E_ANDROID_PHYSICAL_DEVICE_UNSUPPORTED"
                    if platform == "android" and _enum_member(device, PHYSICAL_DEVICE_VALUES)
                    else "E_TARGET_DEVICE_UNSUPPORTED"
                )
                self.add(
                    code,
                    device_path,
                    f"expected target.device={expected_device!r} for platform={platform!r}",
                )
            expected_artifact = EXPECTED_ARTIFACT.get(platform)
            if expected_artifact is not None and artifact_type != expected_artifact:
                if not (platform == "android" and self._is_aab(artifact_type, artifact)):
                    self.add(
                        "E_TARGET_ARTIFACT_UNSUPPORTED",
                        "$.target.artifact_type",
                        f"expected target.artifact_type={expected_artifact!r}",
                    )

        if platform == "ios" and execution_enabled is True:
            self.add(
                "E_IOS_EXECUTION_UNSUPPORTED",
                "$.execution.enabled",
                "iOS is contract-only and execution.enabled must be false",
            )

    @staticmethod
    def _is_aab(artifact_type: Any, artifact: Any) -> bool:
        if isinstance(artifact_type, str) and artifact_type.lower() == "aab":
            return True
        if isinstance(artifact, dict):
            for key in ("format", "type", "artifact_type"):
                value = artifact.get(key)
                if isinstance(value, str) and value.lower() == "aab":
                    return True
            path = artifact.get("path")
            if isinstance(path, str) and path.lower().endswith(".aab"):
                return True
        return False

    def _validate_preconditions(self, value: Any, path: str) -> None:
        if not isinstance(value, list):
            self.add("E_FIELD_TYPE", path, "preconditions must be an array")
            return
        seen_ids: set[str] = set()
        for index, precondition in enumerate(value):
            item_path = _path(path, index)
            if not isinstance(precondition, dict):
                self.add("E_FIELD_TYPE", item_path, "precondition must be an object")
                continue
            self._require_fields(
                precondition, ("id", "description", "verification"), item_path
            )
            precondition_id = precondition.get("id")
            self._validate_identifier(precondition_id, _path(item_path, "id"))
            if isinstance(precondition_id, str) and precondition_id in seen_ids:
                self.add(
                    "E_DUPLICATE_ID",
                    _path(item_path, "id"),
                    "precondition id must be unique",
                )
            elif isinstance(precondition_id, str):
                seen_ids.add(precondition_id)
            description = precondition.get("description")
            if not isinstance(description, str) or not description.strip():
                self.add(
                    "E_FIELD_TYPE",
                    _path(item_path, "description"),
                    "must be a non-empty string",
                )
            verification = precondition.get("verification")
            if verification not in ("runner", "manual"):
                self.add(
                    "E_PRECONDITION_VERIFICATION_UNSUPPORTED",
                    _path(item_path, "verification"),
                    "must be 'runner' or 'manual'",
                )
            if verification == "runner" and (
                not isinstance(precondition.get("check_ref"), str)
                or not precondition.get("check_ref")
            ):
                self.add(
                    "E_PRECONDITION_CHECK_REQUIRED",
                    _path(item_path, "check_ref"),
                    "runner preconditions require a non-empty check_ref",
                )

    def _validate_fixture(self, value: Any, path: str) -> None:
        if not isinstance(value, dict):
            self.add("E_FIXTURE_INVALID", path, "fixture must be an object")
            return
        self._require_fields(
            value, ("kind", "purpose", "destructive", "environment"), path
        )
        kind = value.get("kind")
        if not _enum_member(kind, FIXTURE_KINDS):
            self.add(
                "E_FIXTURE_KIND_UNSUPPORTED",
                _path(path, "kind"),
                f"must be one of {', '.join(sorted(FIXTURE_KINDS))}",
            )
        fixture_ref = value.get("ref")
        if kind != "none" and (not isinstance(fixture_ref, str) or not fixture_ref):
            self.add(
                "E_FIXTURE_REF_REQUIRED",
                _path(path, "ref"),
                "fixture.ref is required unless fixture.kind='none'",
            )
        purpose = value.get("purpose")
        if not _enum_member(purpose, FIXTURE_PURPOSES):
            self.add(
                "E_FIXTURE_PURPOSE_UNSUPPORTED",
                _path(path, "purpose"),
                f"must be one of {', '.join(sorted(FIXTURE_PURPOSES))}",
            )
        if purpose in ("error", "boundary") and kind == "none":
            self.add(
                "E_FIXTURE_KIND_REQUIRED",
                _path(path, "kind"),
                "error and boundary fixtures cannot use fixture.kind='none'",
            )
        destructive = value.get("destructive")
        if destructive is not None and not isinstance(destructive, bool):
            self.add(
                "E_FIELD_TYPE",
                _path(path, "destructive"),
                "fixture.destructive must be a boolean",
            )
        environment = value.get("environment")
        if not _enum_member(environment, FIXTURE_ENVIRONMENTS):
            self.add(
                "E_FIXTURE_ENVIRONMENT_UNSUPPORTED",
                _path(path, "environment"),
                f"must be one of {', '.join(sorted(FIXTURE_ENVIRONMENTS))}",
            )
        isolated = environment == "isolated" or (
            isinstance(environment, dict) and environment.get("isolated") is True
        )
        if (destructive is True or purpose in ("error", "boundary")) and not isolated:
            self.add(
                "E_DESTRUCTIVE_FIXTURE_NOT_ISOLATED",
                _path(path, "environment"),
                "destructive, error, and boundary fixtures require an isolated environment",
            )

    def _validate_provider_binding(self, value: Any) -> str | None:
        path = "$.provider_binding"
        if not isinstance(value, dict):
            self.add(
                "E_PROVIDER_BINDING_INVALID",
                path,
                "provider_binding must be an object",
            )
            return None
        fields = ("contract_version", "implementation_version", "defaults_version")
        self._require_fields(value, fields, path)
        for field in fields:
            field_value = value.get(field)
            if not isinstance(field_value, str) or not field_value:
                self.add(
                    "E_PROVIDER_BINDING_INVALID",
                    _path(path, field),
                    "provider binding versions must be non-empty strings",
                )
        defaults_version = value.get("defaults_version")
        return defaults_version if isinstance(defaults_version, str) and defaults_version else None

    def _scan_unresolved_provider_args(self, value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for raw_key, child in value.items():
                child_path = _path(path, raw_key)
                key_text = str(raw_key)
                separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key_text).lower()
                unresolved_key = (
                    separated.endswith("_ref")
                    or separated.endswith("_refs")
                    or "candidate" in separated
                    or "fallback" in separated
                    or separated.endswith("_template")
                    or separated.endswith("_env")
                    or separated
                    in {
                        "ref",
                        "refs",
                        "template",
                        "env",
                    }
                )
                if unresolved_key:
                    self.add(
                        "E_RUNBOOK_UNRESOLVED_PROVIDER_INPUT",
                        child_path,
                        "provider_args must contain resolved values, not references, candidates, templates, or environment substitutions",
                    )
                self._scan_unresolved_provider_args(child, child_path)
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                self._scan_unresolved_provider_args(child, _path(path, index))
            return
        if isinstance(value, str) and (
            "${" in value
            or "{{" in value
            or "{%" in value
            or re.search(r"\$[A-Za-z_][A-Za-z0-9_]*", value) is not None
            or re.search(r"%[A-Za-z_][A-Za-z0-9_]*%", value) is not None
            or value.startswith("env:")
            or value.startswith("template://")
            or value.startswith("project-config://")
        ):
            self.add(
                "E_RUNBOOK_UNRESOLVED_PROVIDER_INPUT",
                path,
                "provider_args must not contain runtime template or environment substitutions",
            )

    def _validate_actions(
        self,
        value: Any,
        path: str,
        *,
        context: str,
        android_native: bool = False,
        provider_defaults_version: str | None = None,
    ) -> list[dict[str, Any]]:
        if not isinstance(value, list) or not value:
            self.add("E_ACTIONS_REQUIRED", path, "steps/actions must be a non-empty array")
            return []
        valid: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for index, action in enumerate(value):
            action_path = _path(path, index)
            if not isinstance(action, dict):
                self.add("E_FIELD_TYPE", action_path, "step/action must be an object")
                continue
            valid.append(action)
            self._require_fields(
                action, ("id", "action", "description", "mutation"), action_path
            )
            action_id = action.get("id")
            self._validate_identifier(action_id, _path(action_path, "id"))
            if isinstance(action_id, str) and action_id in seen_ids:
                self.add(
                    "E_DUPLICATE_ID",
                    _path(action_path, "id"),
                    "step/action id must be unique",
                )
            elif isinstance(action_id, str):
                seen_ids.add(action_id)
            for field in ("action", "description"):
                field_value = action.get(field)
                if not isinstance(field_value, str) or not field_value.strip():
                    self.add(
                        "E_FIELD_TYPE",
                        _path(action_path, field),
                        "must be a non-empty string",
                    )
            mutation = action.get("mutation")
            if mutation not in ("none", "potential", "confirmed"):
                self.add(
                    "E_MUTATION_CLASSIFICATION_REQUIRED",
                    _path(action_path, "mutation"),
                    "mutation must be one of none, potential, confirmed",
                )
            if (
                android_native
                and _enum_member(action.get("action"), IMPLICIT_NATIVE_MUTATIONS)
                and mutation == "none"
            ):
                self.add(
                    "E_NATIVE_MUTATION_CLASSIFICATION_INVALID",
                    _path(action_path, "mutation"),
                    "Android launch, tap, fill, press_key, and back must be potential or confirmed mutations",
                )
            if _enum_member(action.get("action"), IMPLICIT_STATE_MUTATIONS) and mutation == "none":
                self.add(
                    "E_STATE_MUTATION_CLASSIFICATION_INVALID",
                    _path(action_path, "mutation"),
                    "state-changing web/API actions must be potential or confirmed mutations",
                )
            arguments = action.get("arguments")
            if context == "scenario":
                if "arguments" in action and not isinstance(arguments, dict):
                    self.add(
                        "E_FIELD_TYPE",
                        _path(action_path, "arguments"),
                        "scenario arguments must be an object when present",
                    )
            elif context == "runbook":
                self._require_fields(
                    action,
                    (
                        "arguments",
                        "provider_args",
                        "timeout_ms",
                        "retry_policy",
                        "max_attempts",
                        "provider_defaults_version",
                    ),
                    action_path,
                )
                if arguments is not None and not isinstance(arguments, dict):
                    self.add(
                        "E_FIELD_TYPE",
                        _path(action_path, "arguments"),
                        "runbook arguments must be an object or null",
                    )
                provider_args = action.get("provider_args")
                if not isinstance(provider_args, dict):
                    self.add(
                        "E_PROVIDER_ARGS_INVALID",
                        _path(action_path, "provider_args"),
                        "provider_args must be an object of resolved execution values",
                    )
                else:
                    self._scan_unresolved_provider_args(
                        provider_args, _path(action_path, "provider_args")
                    )
                timeout_ms = action.get("timeout_ms")
                if (
                    not isinstance(timeout_ms, int)
                    or isinstance(timeout_ms, bool)
                    or not 1 <= timeout_ms <= 120000
                ):
                    self.add(
                        "E_STEP_TIMEOUT_INVALID",
                        _path(action_path, "timeout_ms"),
                        "timeout_ms must be an integer from 1 through 120000",
                    )
                retry_policy = action.get("retry_policy")
                if retry_policy not in ("never", "safe"):
                    self.add(
                        "E_STEP_RETRY_POLICY_INVALID",
                        _path(action_path, "retry_policy"),
                        "retry_policy must be never or safe",
                    )
                max_attempts = action.get("max_attempts")
                if (
                    not isinstance(max_attempts, int)
                    or isinstance(max_attempts, bool)
                    or max_attempts < 1
                ):
                    self.add(
                        "E_STEP_MAX_ATTEMPTS_INVALID",
                        _path(action_path, "max_attempts"),
                        "max_attempts must be a positive integer",
                    )
                if retry_policy == "never" and max_attempts != 1:
                    self.add(
                        "E_STEP_RETRY_CONTRACT_INVALID",
                        _path(action_path, "max_attempts"),
                        "retry_policy='never' requires max_attempts=1",
                    )
                if mutation in ("potential", "confirmed") and (
                    retry_policy != "never" or max_attempts != 1
                ):
                    self.add(
                        "E_MUTATION_STEP_RETRY_FORBIDDEN",
                        action_path,
                        "mutation steps require retry_policy='never' and max_attempts=1",
                    )
                defaults_version = action.get("provider_defaults_version")
                if not isinstance(defaults_version, str) or not defaults_version:
                    self.add(
                        "E_PROVIDER_DEFAULTS_VERSION_INVALID",
                        _path(action_path, "provider_defaults_version"),
                        "provider_defaults_version must be a non-empty string",
                    )
                elif (
                    provider_defaults_version is not None
                    and defaults_version != provider_defaults_version
                ):
                    self.add(
                        "E_PROVIDER_DEFAULTS_VERSION_MISMATCH",
                        _path(action_path, "provider_defaults_version"),
                        "step provider_defaults_version must equal provider_binding.defaults_version",
                    )
        return valid

    def _validate_mutation_policy(
        self,
        actions: Sequence[Mapping[str, Any]],
        policy: Any,
        path: str,
    ) -> None:
        mutating_ids = {
            action.get("id")
            for action in actions
            if isinstance(action.get("id"), str)
            and (
                _enum_member(action.get("mutation"), {"potential", "confirmed"})
                or _enum_member(action.get("action"), IMPLICIT_MUTATIONS)
            )
        }
        if not isinstance(policy, dict):
            self.add(
                "E_MUTATION_POLICY_INVALID",
                path,
                "mutation_policy must be an object",
            )
            if mutating_ids:
                self.add(
                    "E_MUTATION_APPROVAL_REQUIRED",
                    path,
                    "mutation actions require an explicit approval policy",
                )
            elif policy is not None:
                self.add("E_FIELD_TYPE", path, "mutation_policy must be an object")
            return

        if not mutating_ids:
            if policy.get("mode") != "deny":
                self.add(
                    "E_READ_ONLY_MUTATION_POLICY_INVALID",
                    _path(path, "mode"),
                    "read-only scenarios/runbooks require mutation_policy.mode='deny'",
                )
            if policy.get("approval_scope") != []:
                self.add(
                    "E_READ_ONLY_MUTATION_POLICY_INVALID",
                    _path(path, "approval_scope"),
                    "read-only scenarios/runbooks require an empty approval_scope",
                )
            if policy.get("retry_policy") != "never":
                self.add(
                    "E_MUTATION_RETRY_FORBIDDEN",
                    _path(path, "retry_policy"),
                    "retry_policy must be 'never'",
                )
            return
        if policy.get("mode") != "require_approval":
            self.add(
                "E_MUTATION_APPROVAL_REQUIRED",
                _path(path, "mode"),
                "mutation actions require mutation_policy.mode='require_approval'",
            )
        scope = policy.get("approval_scope")
        scope_set: set[str] = set()
        if not isinstance(scope, list):
            self.add(
                "E_MUTATION_APPROVAL_SCOPE_INVALID",
                _path(path, "approval_scope"),
                "approval_scope must be an array of step ids",
            )
        else:
            invalid_scope_items = [item for item in scope if not isinstance(item, str)]
            if invalid_scope_items:
                self.add(
                    "E_MUTATION_APPROVAL_SCOPE_INVALID",
                    _path(path, "approval_scope"),
                    "approval_scope entries must be strings",
                )
            scope_set = {item for item in scope if isinstance(item, str)}
        if not mutating_ids.issubset(scope_set):
            self.add(
                "E_MUTATION_APPROVAL_SCOPE_INCOMPLETE",
                _path(path, "approval_scope"),
                "approval_scope must include every mutation action id",
            )
        if policy.get("retry_policy") != "never":
            self.add(
                "E_MUTATION_RETRY_FORBIDDEN",
                _path(path, "retry_policy"),
                "mutation actions require retry_policy='never'",
            )

    def _validate_expected_oracle(
        self,
        expected: Any,
        oracle: Any,
        method: Any,
        expected_path: str,
        oracle_path: str,
        *,
        source_refs: Any,
        execution_enabled: bool | None,
    ) -> None:
        must_have_outcomes = execution_enabled is True and _enum_member(method, METHODS)
        if not isinstance(expected, list):
            self.add(
                "E_AUTOMATED_EXPECTED_REQUIRED",
                expected_path,
                "expected must be an array",
            )
            expected = []
        elif must_have_outcomes and not expected:
            self.add(
                "E_AUTOMATED_EXPECTED_REQUIRED",
                expected_path,
                "enabled scenarios require a non-empty expected array",
            )

        expectation_ids: set[str] = set()
        scenario_ref_keys = self._source_ref_keys(source_refs)
        for index, expectation in enumerate(expected):
            item_path = _path(expected_path, index)
            if not isinstance(expectation, dict):
                self.add("E_FIELD_TYPE", item_path, "expectation must be an object")
                continue
            self._require_fields(
                expectation, ("id", "description", "source_refs"), item_path
            )
            expectation_id = expectation.get("id")
            self._validate_identifier(expectation_id, _path(item_path, "id"))
            if isinstance(expectation_id, str) and expectation_id in expectation_ids:
                self.add(
                    "E_DUPLICATE_ID",
                    _path(item_path, "id"),
                    "expectation id must be unique",
                )
            elif isinstance(expectation_id, str):
                expectation_ids.add(expectation_id)
            description = expectation.get("description")
            if not isinstance(description, str) or not description.strip():
                self.add(
                    "E_FIELD_TYPE",
                    _path(item_path, "description"),
                    "must be a non-empty string",
                )
            expectation_refs = expectation.get("source_refs")
            refs_path = _path(item_path, "source_refs")
            self._validate_source_refs(expectation_refs, refs_path)
            if not self._source_ref_keys(expectation_refs).issubset(scenario_ref_keys):
                self.add(
                    "E_EXPECTATION_SOURCE_REF_OUT_OF_SCOPE",
                    refs_path,
                    "expectation source_refs must be a subset of scenario source_refs",
                )

        if not isinstance(oracle, dict):
            self.add(
                "E_AUTOMATED_ORACLE_REQUIRED",
                oracle_path,
                "oracle must be an object",
            )
            return
        self._require_fields(oracle, ("mode", "rules"), oracle_path)
        mode = oracle.get("mode")
        if not _enum_member(mode, ORACLE_MODES):
            self.add(
                "E_ORACLE_MODE_UNSUPPORTED",
                _path(oracle_path, "mode"),
                f"must be one of {', '.join(sorted(ORACLE_MODES))}",
            )
        rules = oracle.get("rules")
        if not isinstance(rules, list):
            self.add(
                "E_AUTOMATED_ORACLE_REQUIRED",
                _path(oracle_path, "rules"),
                "oracle.rules must be an array",
            )
            return
        if must_have_outcomes and not rules:
            self.add(
                "E_AUTOMATED_ORACLE_REQUIRED",
                _path(oracle_path, "rules"),
                "enabled scenarios require at least one oracle rule",
            )

        seen_rule_ids: set[str] = set()
        covered_expectations: set[str] = set()
        for index, rule in enumerate(rules):
            rule_path = _path(_path(oracle_path, "rules"), index)
            if not isinstance(rule, dict):
                self.add("E_FIELD_TYPE", rule_path, "oracle rule must be an object")
                continue
            self._require_fields(
                rule,
                ("id", "kind", "expectation_id", "evidence_kind"),
                rule_path,
            )
            rule_id = rule.get("id")
            self._validate_identifier(rule_id, _path(rule_path, "id"))
            if isinstance(rule_id, str) and rule_id in seen_rule_ids:
                self.add(
                    "E_DUPLICATE_ID",
                    _path(rule_path, "id"),
                    "oracle rule id must be unique",
                )
            elif isinstance(rule_id, str):
                seen_rule_ids.add(rule_id)
            if rule.get("kind") != mode:
                self.add(
                    "E_ORACLE_RULE_KIND_MISMATCH",
                    _path(rule_path, "kind"),
                    "oracle rule kind must equal oracle.mode",
                )
            expectation_id = rule.get("expectation_id")
            if (
                not isinstance(expectation_id, str)
                or expectation_id not in expectation_ids
            ):
                self.add(
                    "E_ORACLE_EXPECTATION_UNKNOWN",
                    _path(rule_path, "expectation_id"),
                    "oracle rule must reference an existing expectation id",
                )
            elif isinstance(expectation_id, str):
                covered_expectations.add(expectation_id)
            if not _enum_member(rule.get("evidence_kind"), EVIDENCE_KINDS):
                self.add(
                    "E_EVIDENCE_KIND_UNSUPPORTED",
                    _path(rule_path, "evidence_kind"),
                    f"must be one of {', '.join(sorted(EVIDENCE_KINDS))}",
                )
            if mode == "deterministic":
                self._validate_deterministic_rule(rule, rule_path)
            elif mode == "semantic" and (
                not isinstance(rule.get("rubric"), str) or not rule.get("rubric")
            ):
                self.add(
                    "E_SEMANTIC_RUBRIC_REQUIRED",
                    _path(rule_path, "rubric"),
                    "semantic oracle rules require a non-empty rubric",
                )
            elif mode == "manual" and (
                not isinstance(rule.get("checklist"), list) or not rule.get("checklist")
            ):
                self.add(
                    "E_MANUAL_CHECKLIST_REQUIRED",
                    _path(rule_path, "checklist"),
                    "manual oracle rules require a non-empty checklist",
                )

        if must_have_outcomes:
            for expectation_id in sorted(expectation_ids - covered_expectations):
                self.add(
                    "E_EXPECTATION_ORACLE_MISSING",
                    oracle_path,
                    f"expectation {expectation_id!r} has no oracle rule",
                )

    def _validate_deterministic_rule(
        self, rule: Mapping[str, Any], path: str
    ) -> None:
        operator = rule.get("operator")
        allowed = {
            "equals",
            "not_equals",
            "contains",
            "exists",
            "absent",
            "matches_regex",
            "status_code",
        }
        if not _enum_member(operator, allowed):
            self.add(
                "E_ORACLE_OPERATOR_UNSUPPORTED",
                _path(path, "operator"),
                f"must be one of {', '.join(sorted(allowed))}",
            )
        actual_path = rule.get("actual_path")
        if not isinstance(actual_path, str) or not actual_path.startswith("/"):
            self.add(
                "E_ORACLE_ACTUAL_PATH_INVALID",
                _path(path, "actual_path"),
                "actual_path must be an RFC 6901 JSON Pointer",
            )
        if operator not in ("exists", "absent") and "value" not in rule:
            self.add(
                "E_ORACLE_VALUE_REQUIRED",
                _path(path, "value"),
                "this deterministic operator requires value",
            )

    @staticmethod
    def _source_ref_keys(value: Any) -> set[tuple[str, str]]:
        if not isinstance(value, list):
            return set()
        return {
            (item.get("source_id"), item.get("anchor_id"))
            for item in value
            if isinstance(item, dict)
            and isinstance(item.get("source_id"), str)
            and isinstance(item.get("anchor_id"), str)
        }

    @staticmethod
    def _method_from_provider(provider: Any) -> str | None:
        if not isinstance(provider, str):
            return None
        return {
            "web-playwright": "web",
            "native-android": "native",
            "native-ios": "native",
            "developer-test": "integration",
            "manual": "manual",
        }.get(provider)


def validate_document(
    document: Any,
    contract: str | None = None,
    spec_bundle: Mapping[str, Any] | None = None,
    scenario: Mapping[str, Any] | None = None,
    runbook: Mapping[str, Any] | None = None,
) -> list[ValidationIssue]:
    """Validate one decoded JSON document."""

    validator = ContractValidator()
    return validator.validate(document, contract, spec_bundle, scenario, runbook)


def _read_json(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _validation_input(path: str, document: Any) -> dict[str, str]:
    return {"input": path, "sha256": _canonical_json_hash(document)}


def _validator_sha256() -> str:
    return "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate spec-driven-qa JSON contracts."
    )
    parser.add_argument("inputs", nargs="+", help="JSON file path, or - for stdin")
    parser.add_argument(
        "--contract",
        choices=("auto", *sorted(CONTRACTS)),
        default="auto",
        help="select a contract explicitly; default: infer from schema_version",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="validation report format",
    )
    parser.add_argument(
        "--bundle",
        help="spec-bundle-v1 JSON used to resolve dependent contract source_refs",
    )
    parser.add_argument(
        "--scenario",
        help="scenario-v1 JSON used to bind runbook-v1 and result-v1 identity",
    )
    parser.add_argument(
        "--runbook",
        help="runbook-v1 JSON used to bind result-v1 execution identity",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    selected = None if args.contract == "auto" else args.contract
    reports: list[dict[str, Any]] = []
    parse_failed = False
    parsed_inputs: list[tuple[str, Any]] = []

    for input_path in args.inputs:
        try:
            document = _read_json(input_path)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            parse_failed = True
            reports.append(
                {
                    "input": input_path,
                    "valid": False,
                    "errors": [
                        {
                            "code": "E_INPUT_READ",
                            "path": "$",
                            "message": str(error),
                        }
                    ],
                }
            )
            continue
        parsed_inputs.append((input_path, document))

    bundle_context: Mapping[str, Any] | None = None
    bundle_context_input: dict[str, str] | None = None
    if args.bundle is not None:
        try:
            loaded_bundle = _read_json(args.bundle)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            parse_failed = True
            reports.append(
                {
                    "input": args.bundle,
                    "valid": False,
                    "errors": [
                        {
                            "code": "E_INPUT_READ",
                            "path": "$",
                            "message": str(error),
                        }
                    ],
                }
            )
        else:
            bundle_issues = validate_document(loaded_bundle, "spec-bundle-v1")
            if bundle_issues:
                reports.append(
                    {
                        "input": args.bundle,
                        "valid": False,
                        "errors": [issue.as_dict() for issue in bundle_issues],
                    }
                )
            if isinstance(loaded_bundle, Mapping):
                bundle_context = loaded_bundle
                bundle_context_input = _validation_input(args.bundle, loaded_bundle)
    else:
        bundle_candidates = [
            (input_path, document)
            for input_path, document in parsed_inputs
            if isinstance(document, Mapping)
            and document.get("schema_version") == "spec-bundle-v1"
        ]
        if len(bundle_candidates) == 1:
            bundle_input_path, bundle_context = bundle_candidates[0]
            bundle_context_input = _validation_input(bundle_input_path, bundle_context)
        elif len(bundle_candidates) > 1:
            reports.append(
                {
                    "input": "<auto-bundle>",
                    "valid": False,
                    "errors": [
                        {
                            "code": "E_BUNDLE_CONTEXT_AMBIGUOUS",
                            "path": "$",
                            "message": "multiple spec-bundle-v1 inputs require explicit --bundle selection",
                        }
                    ],
                }
            )

    scenario_context: Mapping[str, Any] | None = None
    scenario_context_input: dict[str, str] | None = None
    if args.scenario is not None:
        try:
            loaded_scenario = _read_json(args.scenario)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            parse_failed = True
            reports.append(
                {
                    "input": args.scenario,
                    "valid": False,
                    "errors": [
                        {
                            "code": "E_INPUT_READ",
                            "path": "$",
                            "message": str(error),
                        }
                    ],
                }
            )
        else:
            scenario_issues = validate_document(
                loaded_scenario,
                "scenario-v1",
                spec_bundle=bundle_context,
            )
            if scenario_issues:
                reports.append(
                    {
                        "input": args.scenario,
                        "valid": False,
                        "errors": [issue.as_dict() for issue in scenario_issues],
                    }
                )
            if isinstance(loaded_scenario, Mapping):
                scenario_context = loaded_scenario
                scenario_context_input = _validation_input(args.scenario, loaded_scenario)
    else:
        scenario_candidates = [
            (input_path, document)
            for input_path, document in parsed_inputs
            if isinstance(document, Mapping)
            and document.get("schema_version") == "scenario-v1"
        ]
        if len(scenario_candidates) == 1:
            scenario_input_path, scenario_context = scenario_candidates[0]
            scenario_context_input = _validation_input(
                scenario_input_path, scenario_context
            )
        elif len(scenario_candidates) > 1:
            reports.append(
                {
                    "input": "<auto-scenario>",
                    "valid": False,
                    "errors": [
                        {
                            "code": "E_SCENARIO_CONTEXT_AMBIGUOUS",
                            "path": "$",
                            "message": "multiple scenario-v1 inputs require explicit --scenario selection",
                        }
                    ],
                }
            )

    runbook_context: Mapping[str, Any] | None = None
    runbook_context_input: dict[str, str] | None = None
    if args.runbook is not None:
        try:
            loaded_runbook = _read_json(args.runbook)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            parse_failed = True
            reports.append(
                {
                    "input": args.runbook,
                    "valid": False,
                    "errors": [
                        {
                            "code": "E_INPUT_READ",
                            "path": "$",
                            "message": str(error),
                        }
                    ],
                }
            )
        else:
            runbook_issues = validate_document(
                loaded_runbook,
                "runbook-v1",
                spec_bundle=bundle_context,
                scenario=scenario_context,
            )
            if runbook_issues:
                reports.append(
                    {
                        "input": args.runbook,
                        "valid": False,
                        "errors": [issue.as_dict() for issue in runbook_issues],
                    }
                )
            if isinstance(loaded_runbook, Mapping):
                runbook_context = loaded_runbook
                runbook_context_input = _validation_input(args.runbook, loaded_runbook)
    else:
        runbook_candidates = [
            (input_path, document)
            for input_path, document in parsed_inputs
            if isinstance(document, Mapping)
            and document.get("schema_version") == "runbook-v1"
        ]
        if len(runbook_candidates) == 1:
            runbook_input_path, runbook_context = runbook_candidates[0]
            runbook_context_input = _validation_input(
                runbook_input_path, runbook_context
            )
        elif len(runbook_candidates) > 1:
            reports.append(
                {
                    "input": "<auto-runbook>",
                    "valid": False,
                    "errors": [
                        {
                            "code": "E_RUNBOOK_CONTEXT_AMBIGUOUS",
                            "path": "$",
                            "message": "multiple runbook-v1 inputs require explicit --runbook selection",
                        }
                    ],
                }
            )

    for input_path, document in parsed_inputs:
        schema_version = (
            document.get("schema_version") if isinstance(document, Mapping) else None
        )
        effective_contract = selected or schema_version
        linked_bundle = (
            bundle_context
            if effective_contract in ("scenario-v1", "runbook-v1", "result-v1")
            else None
        )
        linked_scenario = (
            scenario_context
            if effective_contract in ("runbook-v1", "result-v1")
            else None
        )
        linked_runbook = runbook_context if effective_contract == "result-v1" else None
        issues = validate_document(
            document,
            selected,
            linked_bundle,
            linked_scenario,
            linked_runbook,
        )
        reports.append(
            {
                "input": input_path,
                "sha256": _canonical_json_hash(document),
                "valid": not issues,
                "errors": [issue.as_dict() for issue in issues],
            }
        )

    if args.output == "json":
        print(
            json.dumps(
                {
                    "schema_version": "contract-validation-report-v1",
                    "validator": {
                        "name": "spec-driven-qa-contract-validator",
                        "sha256": _validator_sha256(),
                    },
                    "contexts": {
                        "bundle": bundle_context_input,
                        "scenario": scenario_context_input,
                        "runbook": runbook_context_input,
                    },
                    "reports": reports,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for report in reports:
            if report["valid"]:
                print(f"{report['input']}: valid")
                continue
            for issue in report["errors"]:
                print(
                    f"{report['input']}:{issue['path']}: "
                    f"{issue['code']}: {issue['message']}",
                    file=sys.stderr,
                )

    if parse_failed:
        return 2
    if any(not report["valid"] for report in reports):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
