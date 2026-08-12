from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "validate-contracts.py"
SPEC = importlib.util.spec_from_file_location("validate_contracts", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
validate_contracts = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validate_contracts
SPEC.loader.exec_module(validate_contracts)

BUNDLE_SOURCE_HASH = (
    "sha256:4e8d7f41a2abf3d2484f39c4e9c8c650bb4f4758609cd21ee44addf2099ee179"
)


def web_scenario() -> dict:
    return {
        "schema_version": "scenario-v1",
        "id": "web-save-status",
        "title": "Saved state is exposed to the user",
        "source_refs": [
            {"source_id": "ticket-spec", "anchor_id": "save-status-ac"}
        ],
        "method": "web",
        "preconditions": [
            {
                "id": "fixture-ready",
                "description": "The deterministic account fixture exists.",
                "verification": "runner",
                "check_ref": "fixture-health",
            }
        ],
        "fixture": {
            "kind": "seed",
            "ref": "fixture://account/ready",
            "purpose": "baseline",
            "destructive": False,
            "environment": "shared_test",
        },
        "steps": [
            {
                "id": "open-page",
                "action": "navigate",
                "description": "Open the fixture route.",
                "mutation": "none",
                "arguments": {"route_ref": "saved-item"},
            }
        ],
        "expected": [
            {
                "id": "saved-state-visible",
                "description": "The saved state is present in the accessibility tree.",
                "source_refs": [
                    {"source_id": "ticket-spec", "anchor_id": "save-status-ac"}
                ],
            }
        ],
        "oracle": {
            "mode": "deterministic",
            "rules": [
                {
                    "id": "saved-state-rule",
                    "kind": "deterministic",
                    "expectation_id": "saved-state-visible",
                    "evidence_kind": "accessibility_state",
                    "operator": "contains",
                    "actual_path": "/state_text",
                    "value": "saved",
                }
            ],
        },
        "severity": "high",
        "spec_version": "spec-2026-08-01",
        "review_status": "approved",
        "target": {"platform": "web", "device": "desktop"},
        "runner_provider": "web-playwright",
        "mutation_policy": {
            "mode": "deny",
            "approval_scope": [],
            "retry_policy": "never",
        },
        "execution": {"enabled": True},
    }


def android_scenario() -> dict:
    scenario = web_scenario()
    scenario.update(
        {
            "id": "android-save-status",
            "method": "native",
            "target": {
                "platform": "android",
                "device": "emulator",
                "artifact_type": "apk",
            },
            "runner_provider": "native-android",
            "steps": [
                {
                    "id": "launch-app",
                    "action": "launch",
                    "description": "Launch the registered test APK.",
                    "mutation": "potential",
                },
                {
                    "id": "wait-saved",
                    "action": "wait_for",
                    "description": "Wait for the saved accessibility state.",
                    "mutation": "none",
                },
            ],
            "mutation_policy": {
                "mode": "require_approval",
                "approval_scope": ["launch-app"],
                "retry_policy": "never",
            },
        }
    )
    return scenario


def ios_scenario() -> dict:
    scenario = android_scenario()
    scenario.update(
        {
            "id": "ios-save-status-contract",
            "target": {
                "platform": "ios",
                "device": "simulator",
                "artifact_type": "app_zip",
            },
            "runner_provider": "native-ios",
            "execution": {"enabled": False},
        }
    )
    return scenario


def passing_web_result() -> dict:
    command_hash = "sha256:" + "d" * 64
    state_hash = "sha256:" + "e" * 64
    scenario = web_scenario()
    runbook = web_runbook()
    return {
        "schema_version": "result-v1",
        "run_id": "run-web-save-status-001",
        "scenario_id": "web-save-status",
        "spec_version": "spec-2026-08-01",
        "scenario_hash": validate_contracts._canonical_json_hash(scenario),
        "runbook_id": "web-save-status-r1",
        "runbook_hash": validate_contracts._canonical_json_hash(runbook),
        "target": {"platform": "web", "device": "desktop"},
        "runner_provider": "web-playwright",
        "started_at": "2026-08-01T02:00:00Z",
        "finished_at": "2026-08-01T02:00:04Z",
        "verdict": "pass",
        "execution": {
            "status": "completed",
            "attempt": 1,
            "retry_count": 0,
            "command_evidence_ref": "runner-command",
            "runner_version": "1.0.0",
        },
        "subject": {
            "build": {"ref": "sample-build", "sha256": "sha256:" + "c" * 64},
            "artifact": None,
            "native_runtime": None,
        },
        "judge": {
            "mode": "deterministic",
            "name": "independent-judge",
            "version": "1.0.0",
            "attempt": 1,
            "model": None,
            "source_hashes": [BUNDLE_SOURCE_HASH],
            "evidence_hashes": [command_hash, state_hash],
            "decided_at": "2026-08-01T02:00:04Z",
        },
        "evidence": [
            {
                "id": "runner-command",
                "kind": "test_command",
                "collected_at": "2026-08-01T02:00:00Z",
                "producer": {"type": "runner", "name": "web-playwright"},
                "sha256": command_hash,
                "redactions": [],
                "record": {"runbook_ref": "runbooks/web-save-status-r1.json"},
            },
            {
                "id": "visible-saved-state",
                "kind": "accessibility_state",
                "collected_at": "2026-08-01T02:00:03Z",
                "producer": {"type": "runner", "name": "web-playwright"},
                "sha256": state_hash,
                "redactions": [],
                "record": {"state_text": "saved"},
            }
        ],
        "oracle_results": [
            {
                "oracle_id": "saved-state-rule",
                "expectation_id": "saved-state-visible",
                "status": "matched",
                "evidence_refs": ["visible-saved-state"],
                "source_refs": [],
                "actual": "saved",
                "reason": None,
            }
        ],
        "blockers": [],
        "conflicts": [],
        "missing_evidence": [],
        "unsupported_reason": None,
        "diagnostic_attachments": [],
    }


def web_runbook() -> dict:
    scenario = web_scenario()
    document = {
        "schema_version": "runbook-v1",
        "runbook_id": "web-save-status-r1",
        "scenario_id": scenario["id"],
        "spec_version": scenario["spec_version"],
        "scenario_hash": validate_contracts._canonical_json_hash(scenario),
        "source_refs": scenario["source_refs"],
        "review_status": scenario["review_status"],
        "method": scenario["method"],
        "execution": {"enabled": True},
        "target": scenario["target"],
        "runner_provider": scenario["runner_provider"],
        "provider_binding": {
            "contract_version": "runner-provider-v1",
            "implementation_version": "web-playwright-1.0.0",
            "defaults_version": "web-defaults-v1",
        },
        "project_config_sha256": "sha256:" + "8" * 64,
        "preconditions": scenario["preconditions"],
        "fixture": scenario["fixture"],
        "steps": [
            {
                **scenario["steps"][0],
                "provider_args": {"url": "https://qa.invalid/saved-item"},
                "timeout_ms": 10000,
                "retry_policy": "safe",
                "max_attempts": 2,
                "provider_defaults_version": "web-defaults-v1",
            }
        ],
        "expected": scenario["expected"],
        "oracle": scenario["oracle"],
        "mutation_policy": scenario["mutation_policy"],
        "evidence_plan": [
            {
                "oracle_rule_id": "saved-state-rule",
                "evidence_kind": "accessibility_state",
            }
        ],
        "integrity": {"plan_sha256": "sha256:" + "0" * 64},
        "approval_ref": None,
    }
    document["integrity"]["plan_sha256"] = (
        validate_contracts._canonical_runbook_plan_hash(document)
    )
    return document


def android_runbook() -> dict:
    scenario = android_scenario()
    document = web_runbook()
    document.update(
        {
            "runbook_id": "android-save-status-r1",
            "runbook_state": "executable",
            "scenario_id": scenario["id"],
            "scenario_hash": validate_contracts._canonical_json_hash(scenario),
            "method": scenario["method"],
            "target": scenario["target"],
            "runner_provider": scenario["runner_provider"],
            "provider_binding": {
                "contract_version": "native-mcp-adapter-v1",
                "implementation_version": "external-adapter-1.0.0",
                "defaults_version": "android-defaults-v1",
            },
            "steps": [
                {
                    **scenario["steps"][0],
                    "arguments": None,
                    "provider_args": {"package_id": "com.example.qa"},
                    "timeout_ms": 30000,
                    "retry_policy": "never",
                    "max_attempts": 1,
                    "provider_defaults_version": "android-defaults-v1",
                },
                {
                    **scenario["steps"][1],
                    "arguments": None,
                    "provider_args": {"accessibility_id": "saved-status"},
                    "timeout_ms": 10000,
                    "retry_policy": "safe",
                    "max_attempts": 2,
                    "provider_defaults_version": "android-defaults-v1",
                },
            ],
            "mutation_policy": scenario["mutation_policy"],
        }
    )
    plan_hash = validate_contracts._canonical_runbook_plan_hash(document)
    document["integrity"] = {"plan_sha256": plan_hash}
    document["approval_ref"] = {
        "id": "approval:android-save-status-r1",
        "record_sha256": "sha256:" + "f" * 64,
        "plan_sha256": plan_hash,
        "provider_plan_hash": "sha256:" + "9" * 64,
        "runtime_binding_sha256": "sha256:" + "8" * 64,
        "approved_step_ids": ["launch-app"],
        "environment": "isolated-test",
        "scope": "single_run",
        "expires_at": None,
        "approved_by_ref": "approver:test",
    }
    return document


def ios_runbook() -> dict:
    scenario = ios_scenario()
    document = android_runbook()
    document.update(
        {
            "runbook_id": "ios-save-status-contract-r1",
            "scenario_id": scenario["id"],
            "scenario_hash": validate_contracts._canonical_json_hash(scenario),
            "execution": {"enabled": False},
            "target": scenario["target"],
            "runner_provider": scenario["runner_provider"],
            "provider_binding": {
                "contract_version": "native-ios-contract-v1",
                "implementation_version": "unsupported",
                "defaults_version": "ios-defaults-v1",
            },
            "approval_ref": None,
        }
    )
    for step in document["steps"]:
        step["provider_defaults_version"] = "ios-defaults-v1"
    document["integrity"] = {
        "plan_sha256": validate_contracts._canonical_runbook_plan_hash(document)
    }
    return document


def rehash_runbook(document: dict) -> None:
    plan_hash = validate_contracts._canonical_runbook_plan_hash(document)
    document["integrity"]["plan_sha256"] = plan_hash
    if isinstance(document.get("approval_ref"), dict):
        document["approval_ref"]["plan_sha256"] = plan_hash


def passing_android_result() -> dict:
    document = passing_web_result()
    document["run_id"] = "run-android-save-status-001"
    document["scenario_id"] = "android-save-status"
    document["runbook_id"] = "android-save-status-r1"
    document["target"] = {
        "platform": "android",
        "device": "emulator",
        "artifact_type": "apk",
    }
    document["runner_provider"] = "native-android"
    document["scenario_hash"] = validate_contracts._canonical_json_hash(
        android_scenario()
    )
    document["runbook_hash"] = validate_contracts._canonical_json_hash(
        android_runbook()
    )
    document["subject"] = {
        "build": {"ref": "sample-build", "sha256": "sha256:" + "c" * 64},
        "artifact": {
            "id": "registered-apk",
            "type": "apk",
            "sha256": "sha256:" + "4" * 64,
            "package_id": "com.example.qa",
        },
        "native_runtime": {
            "device_type": "emulator",
            "device_id": "emulator-5554",
            "avd": "qa-api-35",
            "device_name": "qa-emulator",
            "os_version": "15",
            "orientation": "portrait",
            "language": "en",
            "locale": "en-US",
            "reset_policy": "clean",
            "appium_version": "2.0.0",
            "automation_driver": "uiautomator2",
            "automation_driver_version": "4.0.0",
        },
    }
    return document


def spec_bundle() -> dict:
    return {
        "schema_version": "spec-bundle-v1",
        "bundle_id": "sample-bundle",
        "spec_version": "spec-2026-08-01",
        "sources": [
            {
                "id": "ticket-spec",
                "kind": "acceptance_criteria",
                "title": "Save behavior",
                "version": "1",
                "content_hash": BUNDLE_SOURCE_HASH,
                "anchors": [
                    {
                        "id": "save-status-ac",
                        "kind": "acceptance_criterion",
                        "title": "Saved state",
                        "statement": "A successful save exposes the saved state.",
                        "status": "approved",
                    }
                ],
            }
        ],
    }


def canonical_hash_test_bundle() -> dict:
    return {
        "schema_version": "spec-bundle-v1",
        "bundle_id": "hash-test-vector",
        "spec_version": "1",
        "sources": [
            {
                "id": "sample",
                "kind": "prd",
                "title": "Sample",
                "version": "1",
                "content_hash": "sha256:17bdc0b6d586bdf36fe6e71df16c15a77c895d212fde4d29473f9605c8eb780d",
                "anchors": [
                    {
                        "id": "a",
                        "kind": "requirement",
                        "title": "Greeting",
                        "statement": "Café\nready",
                        "status": "approved",
                    }
                ],
            }
        ],
    }


def native_mcp_binding() -> dict:
    return {
        "schema_version": "native-mcp-binding-v1",
        "binding_id": "sample-native-binding-r1",
        "server": {
            "name": "demo-video-mcp",
            "version": "1.0.0",
            "protocol_version": "2025-06-18",
            "transport": "stdio",
            "executable_sha256": "sha256:" + "a" * 64,
            "runtime_source": {
                "kind": "directory_tree",
                "root_path": "/absolute/external-provider/src/external_mcp_server",
                "source_tree_sha256": "sha256:" + "e" * 64,
                "file_count": 12,
                "total_bytes": 4096,
            },
            "contract_version": "native-scenario-v1",
            "launch": {
                "executable_path": "/absolute/runtime/python",
                "arguments": ["-m", "external_mcp_server"],
                "working_directory": "/absolute/external-provider",
            },
        },
        "capabilities": {
            "discovered_at": "2026-08-02T00:00:00Z",
            "tools_list_sha256": "sha256:" + "b" * 64,
            "native_scenario_schema_sha256": "sha256:" + "c" * 64,
            "required_tools": [
                "get_native_video_scenario_schema",
                "register_native_app",
                "get_native_runtime_status",
                "inspect_native_app",
                "create_native_video_job",
                "preflight_video_job",
                "approve_video_job",
                "start_video_job",
                "get_video_job",
            ],
        },
        "artifact": {
            "type": "apk",
            "local_path": "/absolute/artifacts/sample.apk",
            "expected_sha256": "sha256:" + "d" * 64,
        },
        "readiness": {
            "java": {
                "home_path": "/absolute/jdk",
                "executable_path": "/absolute/jdk/bin/java",
                "executable_sha256": "sha256:" + "1" * 64,
            },
            "apk_verifier": {
                "verifier": "apksigner",
                "executable_path": "/absolute/android-sdk/build-tools/35.0.0/apksigner",
                "executable_sha256": "sha256:" + "2" * 64,
            },
        },
        "package_id": "org.example.qasample",
        "device": {
            "runtime": "emulator",
            "avd": "qa-api-35",
            "udid": "emulator-5554",
            "device_name": "qa-emulator",
            "platform_version": "35",
            "orientation": "portrait",
            "language": "en",
            "locale": "US",
            "reset_policy": "preserve",
        },
        "appium": {
            "server_url": "http://127.0.0.1:4723",
            "driver": "uiautomator2",
        },
        "execution": {
            "max_duration_seconds": 180,
            "poll_interval_ms": 500,
        },
    }


class ContractValidatorTests(unittest.TestCase):
    @staticmethod
    def bundle_for(
        document: dict,
        contract: str | None,
        bundle_context: dict | None,
    ) -> dict | None:
        effective_contract = contract or document.get("schema_version")
        if (
            bundle_context is None
            and effective_contract in ("scenario-v1", "runbook-v1", "result-v1")
        ):
            return spec_bundle()
        return bundle_context

    @staticmethod
    def result_contexts_for(
        document: dict,
        contract: str | None,
        scenario_context: dict | None,
        runbook_context: dict | None,
    ) -> tuple[dict | None, dict | None]:
        effective_contract = contract or document.get("schema_version")
        if effective_contract == "runbook-v1":
            if document.get("scenario_id") == "android-save-status":
                return scenario_context or android_scenario(), runbook_context
            if document.get("scenario_id") == "ios-save-status-contract":
                return scenario_context or ios_scenario(), runbook_context
            return scenario_context or web_scenario(), runbook_context
        if effective_contract != "result-v1":
            return scenario_context, runbook_context
        if document.get("scenario_id") == "android-save-status":
            return (
                scenario_context or android_scenario(),
                runbook_context or android_runbook(),
            )
        if document.get("scenario_id") == "ios-save-status-contract":
            return (
                scenario_context or ios_scenario(),
                runbook_context or ios_runbook(),
            )
        return scenario_context or web_scenario(), runbook_context or web_runbook()

    def codes(
        self,
        document: dict,
        contract: str | None = None,
        bundle_context: dict | None = None,
        scenario_context: dict | None = None,
        runbook_context: dict | None = None,
    ) -> set[str]:
        bundle_context = self.bundle_for(document, contract, bundle_context)
        scenario_context, runbook_context = self.result_contexts_for(
            document, contract, scenario_context, runbook_context
        )
        return {
            issue.code
            for issue in validate_contracts.validate_document(
                document,
                contract,
                bundle_context,
                scenario_context,
                runbook_context,
            )
        }

    def assertValid(
        self,
        document: dict,
        contract: str | None = None,
        bundle_context: dict | None = None,
        scenario_context: dict | None = None,
        runbook_context: dict | None = None,
    ) -> None:
        bundle_context = self.bundle_for(document, contract, bundle_context)
        scenario_context, runbook_context = self.result_contexts_for(
            document, contract, scenario_context, runbook_context
        )
        issues = validate_contracts.validate_document(
            document,
            contract,
            bundle_context,
            scenario_context,
            runbook_context,
        )
        self.assertEqual([], issues, [issue.as_dict() for issue in issues])

    def assertHasCode(
        self,
        document: dict,
        expected_code: str,
        contract: str | None = None,
        bundle_context: dict | None = None,
        scenario_context: dict | None = None,
        runbook_context: dict | None = None,
    ) -> None:
        codes = self.codes(
            document,
            contract,
            bundle_context,
            scenario_context,
            runbook_context,
        )
        self.assertIn(expected_code, codes, sorted(codes))

    def test_valid_web_scenario_passes(self) -> None:
        self.assertValid(web_scenario())

    def test_valid_native_mcp_binding_passes(self) -> None:
        self.assertValid(native_mcp_binding())

    def test_native_mcp_binding_requires_runtime_source_digest(self) -> None:
        document = native_mcp_binding()
        document["server"].pop("runtime_source")
        self.assertHasCode(document, "E_REQUIRED")

    def test_native_mcp_binding_rejects_filesystem_root_as_runtime_source(self) -> None:
        document = native_mcp_binding()
        document["server"]["runtime_source"]["root_path"] = "/"
        self.assertHasCode(document, "E_MCP_RUNTIME_SOURCE_INVALID")

    def test_native_mcp_binding_rejects_physical_device(self) -> None:
        document = native_mcp_binding()
        document["device"]["runtime"] = "physical"
        document["device"]["udid"] = "device-1234"
        self.assertHasCode(document, "E_ANDROID_PHYSICAL_DEVICE_UNSUPPORTED")

    def test_native_mcp_binding_rejects_aab(self) -> None:
        document = native_mcp_binding()
        document["artifact"]["type"] = "aab"
        document["artifact"]["local_path"] = "/absolute/artifacts/sample.aab"
        self.assertHasCode(document, "E_ANDROID_AAB_UNSUPPORTED")

    def test_native_mcp_binding_rejects_remote_appium(self) -> None:
        document = native_mcp_binding()
        document["appium"]["server_url"] = "https://remote.example.invalid/wd/hub"
        self.assertHasCode(document, "E_APPIUM_LOCAL_REQUIRED")

    def test_native_mcp_binding_requires_all_tools(self) -> None:
        document = native_mcp_binding()
        document["capabilities"]["required_tools"].remove("approve_video_job")
        self.assertHasCode(document, "E_NATIVE_REQUIRED_TOOLS_MISSING")

    def test_native_mcp_binding_requires_jdk_readiness(self) -> None:
        document = native_mcp_binding()
        document["readiness"].pop("java")
        self.assertHasCode(document, "E_JAVA_READINESS_BINDING_INVALID")

    def test_native_mcp_binding_requires_apksigner_readiness(self) -> None:
        document = native_mcp_binding()
        document["readiness"]["apk_verifier"]["verifier"] = "jarsigner"
        self.assertHasCode(document, "E_APK_SIGNING_BINDING_INVALID")

    def test_web_url_state_evidence_kind_passes(self) -> None:
        document = web_scenario()
        document["oracle"]["rules"][0]["evidence_kind"] = "url_state"
        self.assertValid(document)

    def test_web_storage_state_evidence_kind_passes(self) -> None:
        document = web_scenario()
        document["oracle"]["rules"][0]["evidence_kind"] = "storage_state"
        self.assertValid(document)

    def test_valid_android_emulator_scenario_passes(self) -> None:
        self.assertValid(android_scenario())

    def test_valid_spec_bundle_passes(self) -> None:
        self.assertValid(spec_bundle())

    def test_canonical_source_hash_test_vector_passes(self) -> None:
        self.assertValid(canonical_hash_test_bundle())

    def test_source_content_hash_mismatch_fails(self) -> None:
        document = canonical_hash_test_bundle()
        document["sources"][0]["content_hash"] = "sha256:" + "0" * 64
        self.assertHasCode(document, "E_CONTENT_HASH_MISMATCH")

    def test_noncanonical_source_text_fails_even_when_normalized_hash_matches(self) -> None:
        document = canonical_hash_test_bundle()
        document["sources"][0]["anchors"][0]["statement"] = (
            "Cafe\u0301  \r\nready\r\n"
        )
        self.assertHasCode(document, "E_SOURCE_TEXT_NOT_CANONICAL")

    def test_valid_web_runbook_passes(self) -> None:
        self.assertValid(web_runbook())

    def test_valid_runbook_passes_with_explicit_scenario_context(self) -> None:
        issues = validate_contracts.validate_document(
            web_runbook(),
            spec_bundle=spec_bundle(),
            scenario=web_scenario(),
        )
        self.assertEqual([], issues, [issue.as_dict() for issue in issues])

    def test_runbook_rejects_invented_scenario_id(self) -> None:
        document = web_runbook()
        document["scenario_id"] = "invented-scenario"
        self.assertHasCode(document, "E_RUNBOOK_SCENARIO_SCENARIO_ID_MISMATCH")

    def test_runbook_rejects_arbitrary_scenario_hash(self) -> None:
        document = web_runbook()
        document["scenario_hash"] = "sha256:" + "1" * 64
        self.assertHasCode(document, "E_RUNBOOK_SCENARIO_SCENARIO_HASH_MISMATCH")

    def test_runbook_rejects_changed_expected_after_plan_rehash(self) -> None:
        document = web_runbook()
        document["expected"][0]["description"] = "Invented compiled outcome."
        rehash_runbook(document)
        self.assertHasCode(document, "E_RUNBOOK_SCENARIO_EXPECTED_MISMATCH")

    def test_runbook_evidence_plan_requires_evidence_kind(self) -> None:
        document = web_runbook()
        document["evidence_plan"][0].pop("evidence_kind")
        self.assertHasCode(document, "E_EVIDENCE_KIND_UNSUPPORTED")

    def test_valid_result_passes(self) -> None:
        self.assertValid(passing_web_result())

    def test_result_verdict_enum_is_closed(self) -> None:
        document = passing_web_result()
        document["verdict"] = "success"
        self.assertHasCode(document, "E_VERDICT_UNSUPPORTED")

    def test_ios_executed_result_fails(self) -> None:
        document = passing_web_result()
        document["target"] = {
            "platform": "ios",
            "device": "simulator",
            "artifact_type": "app_zip",
        }
        document["runner_provider"] = "native-ios"
        self.assertHasCode(document, "E_IOS_RESULT_EXECUTION_UNSUPPORTED")

    def test_android_physical_device_result_fails(self) -> None:
        document = passing_web_result()
        document["target"] = {
            "platform": "android",
            "device": "physical",
            "artifact_type": "apk",
        }
        document["runner_provider"] = "native-android"
        self.assertHasCode(document, "E_ANDROID_PHYSICAL_DEVICE_UNSUPPORTED")

    def test_android_aab_result_fails(self) -> None:
        document = passing_web_result()
        document["target"] = {
            "platform": "android",
            "device": "emulator",
            "artifact_type": "aab",
        }
        document["runner_provider"] = "native-android"
        self.assertHasCode(document, "E_ANDROID_AAB_UNSUPPORTED")

    def test_missing_source_refs_fails(self) -> None:
        document = web_scenario()
        document["source_refs"] = []
        self.assertHasCode(document, "E_SOURCE_REFS_REQUIRED")

    def test_ios_executable_request_fails(self) -> None:
        document = android_scenario()
        document["target"] = {
            "platform": "ios",
            "device": "simulator",
            "artifact_type": "app_zip",
        }
        document["runner_provider"] = "native-ios"
        document["execution"] = {"enabled": True}
        self.assertHasCode(document, "E_IOS_EXECUTION_UNSUPPORTED")

    def test_ios_contract_only_scenario_passes(self) -> None:
        document = android_scenario()
        document["target"] = {
            "platform": "ios",
            "device": "simulator",
            "artifact_type": "app_zip",
        }
        document["runner_provider"] = "native-ios"
        document["execution"] = {"enabled": False}
        self.assertValid(document)

    def test_mutation_without_approval_policy_fails(self) -> None:
        document = android_scenario()
        document.pop("mutation_policy")
        self.assertHasCode(document, "E_MUTATION_APPROVAL_REQUIRED")

    def test_mutation_approval_scope_must_cover_each_action(self) -> None:
        document = android_scenario()
        document["mutation_policy"]["approval_scope"] = []
        self.assertHasCode(document, "E_MUTATION_APPROVAL_SCOPE_INCOMPLETE")

    def test_credential_input_fails_without_echoing_value(self) -> None:
        document = web_scenario()
        document["fixture"]["credentials"] = {
            "username": "qa-user",
            "password": "do-not-print-this-value",
        }
        issues = validate_contracts.validate_document(document)
        self.assertIn("E_SENSITIVE_INPUT", {issue.code for issue in issues})
        rendered = json.dumps([issue.as_dict() for issue in issues])
        self.assertNotIn("do-not-print-this-value", rendered)

    def test_bearer_token_value_fails(self) -> None:
        document = web_scenario()
        document["preconditions"].append("Bearer abcdefghijklmnopqrstuvwxyz")
        self.assertHasCode(document, "E_SENSITIVE_INPUT")

    def test_apk_bytes_input_fails(self) -> None:
        document = android_scenario()
        document["target"]["artifact"] = {
            "format": "apk",
            "bytes": [80, 75, 3, 4],
        }
        self.assertHasCode(document, "E_ARTIFACT_INLINE_DATA")

    def test_base64_artifact_input_fails(self) -> None:
        document = android_scenario()
        document["target"]["artifact"] = {
            "format": "apk",
            "base64": "UEsDBAoAAAAA",
        }
        self.assertHasCode(document, "E_ARTIFACT_INLINE_DATA")

    def test_sensitive_alias_key_fails(self) -> None:
        document = web_scenario()
        document["fixture"]["oauth_token_value"] = "opaque-secret-value"
        self.assertHasCode(document, "E_SENSITIVE_INPUT")

    def test_apk_blob_base64_input_fails(self) -> None:
        document = android_scenario()
        document["target"]["artifact"] = {
            "format": "apk",
            "apk_blob": "UEsDBAoAAAAA",
        }
        self.assertHasCode(document, "E_ARTIFACT_INLINE_DATA")

    def test_artifact_apk_integer_array_fails(self) -> None:
        document = android_scenario()
        document["target"]["artifact"] = {
            "format": "apk",
            "apk": [80, 75, 3, 4],
        }
        self.assertHasCode(document, "E_ARTIFACT_INLINE_DATA")

    def test_direct_base64_in_artifact_context_fails(self) -> None:
        document = android_scenario()
        document["target"]["artifact"] = {
            "format": "apk",
            "archive": "UEsDBAoAAAAA",
        }
        self.assertHasCode(document, "E_ARTIFACT_INLINE_DATA")

    def test_direct_aab_in_artifact_context_fails(self) -> None:
        document = android_scenario()
        document["target"]["artifact"] = {
            "format": "apk",
            "aab": "UEsDBAoAAAAA",
        }
        self.assertHasCode(document, "E_ARTIFACT_INLINE_DATA")

    def test_android_physical_device_fails(self) -> None:
        document = android_scenario()
        document["target"]["device"] = "physical"
        self.assertHasCode(document, "E_ANDROID_PHYSICAL_DEVICE_UNSUPPORTED")

    def test_android_aab_artifact_fails(self) -> None:
        document = android_scenario()
        document["target"]["artifact_type"] = "aab"
        self.assertHasCode(document, "E_ANDROID_AAB_UNSUPPORTED")

    def test_destructive_fixture_without_isolation_fails(self) -> None:
        document = web_scenario()
        document["fixture"]["destructive"] = True
        document["fixture"]["environment"] = "shared_test"
        self.assertHasCode(document, "E_DESTRUCTIVE_FIXTURE_NOT_ISOLATED")

    def test_destructive_fixture_in_isolation_passes(self) -> None:
        document = web_scenario()
        document["fixture"]["destructive"] = True
        document["fixture"]["environment"] = "isolated"
        self.assertValid(document)

    def test_error_fixture_cannot_use_none_kind(self) -> None:
        document = web_scenario()
        document["fixture"].update(
            {"kind": "none", "purpose": "error", "environment": "isolated"}
        )
        document["fixture"].pop("ref")
        self.assertHasCode(document, "E_FIXTURE_KIND_REQUIRED")

    def test_mobile_web_native_classification_conflict_fails(self) -> None:
        document = android_scenario()
        document["target"] = {"platform": "mobile_web", "device": "responsive"}
        document["runner_provider"] = "native-android"
        self.assertHasCode(document, "E_MOBILE_WEB_NATIVE_CONFLICT")

    def test_unsupported_platform_method_combination_fails(self) -> None:
        document = web_scenario()
        document["target"] = {
            "platform": "android",
            "device": "emulator",
            "artifact_type": "apk",
        }
        self.assertHasCode(document, "E_PLATFORM_METHOD_UNSUPPORTED")

    def test_automated_scenario_without_expected_fails(self) -> None:
        document = web_scenario()
        document["expected"] = []
        self.assertHasCode(document, "E_AUTOMATED_EXPECTED_REQUIRED")

    def test_automated_scenario_without_oracle_fails(self) -> None:
        document = web_scenario()
        document["oracle"] = {}
        self.assertHasCode(document, "E_AUTOMATED_ORACLE_REQUIRED")

    def test_runner_self_report_structured_log_is_forbidden(self) -> None:
        document = passing_web_result()
        document["evidence"].append(
            {
                "id": "runner-summary",
                "kind": "structured_log",
                "collected_at": "2026-08-01T02:00:03Z",
                "producer": {"type": "runner", "name": "web-playwright"},
                "sha256": "sha256:" + "7" * 64,
                "redactions": [],
                "record": {"verdict": "pass", "success": True},
            }
        )
        self.assertHasCode(document, "E_SELF_REPORT_EVIDENCE_FORBIDDEN")

    def test_web_pass_requires_objective_state_evidence(self) -> None:
        document = passing_web_result()
        document["evidence"] = [document["evidence"][0]]
        document["oracle_results"][0]["evidence_refs"] = ["runner-command"]
        self.assertHasCode(document, "E_PASS_OBJECTIVE_STATE_EVIDENCE_REQUIRED")

    def test_ios_result_must_be_not_started_and_unsupported(self) -> None:
        document = passing_web_result()
        document["target"] = {
            "platform": "ios",
            "device": "simulator",
            "artifact_type": "app_zip",
        }
        document["runner_provider"] = "native-ios"
        document["execution"]["status"] = "not_started"
        document["verdict"] = "blocked"
        document["blockers"] = [
            {"code": "runtime", "description": "No provider", "evidence_refs": []}
        ]
        self.assertHasCode(document, "E_IOS_RESULT_EXECUTION_UNSUPPORTED")

    def test_valid_ios_unsupported_result_passes(self) -> None:
        document = passing_web_result()
        scenario = ios_scenario()
        runbook = ios_runbook()
        document["scenario_id"] = scenario["id"]
        document["scenario_hash"] = validate_contracts._canonical_json_hash(scenario)
        document["runbook_id"] = runbook["runbook_id"]
        document["runbook_hash"] = validate_contracts._canonical_json_hash(runbook)
        document["target"] = scenario["target"]
        document["runner_provider"] = scenario["runner_provider"]
        document["execution"]["status"] = "not_started"
        document["verdict"] = "unsupported"
        document["unsupported_reason"] = "native-ios provider is unavailable"
        self.assertValid(document)

    def test_valid_android_mutation_runbook_passes(self) -> None:
        self.assertValid(android_runbook())

    def test_valid_android_preflight_runbook_passes_without_approval(self) -> None:
        document = android_runbook()
        document["runbook_state"] = "preflight"
        document["approval_ref"] = None
        self.assertValid(document)

    def test_android_runbook_requires_explicit_state(self) -> None:
        document = android_runbook()
        document.pop("runbook_state")
        self.assertHasCode(document, "E_RUNBOOK_STATE_REQUIRED")

    def test_android_preflight_runbook_forbids_approval(self) -> None:
        document = android_runbook()
        document["runbook_state"] = "preflight"
        self.assertHasCode(document, "E_PREFLIGHT_APPROVAL_FORBIDDEN")

    def test_android_executable_runbook_requires_approval_when_disabled(self) -> None:
        document = android_runbook()
        document["execution"] = {"enabled": False}
        document["approval_ref"] = None
        rehash_runbook(document)
        self.assertHasCode(document, "E_MUTATION_APPROVAL_REF_REQUIRED")

    def test_android_mutation_approval_requires_provider_plan_hash(self) -> None:
        document = android_runbook()
        document["approval_ref"].pop("provider_plan_hash")
        self.assertHasCode(document, "E_HASH_INVALID")

    def test_android_provider_plan_hash_format_is_checked(self) -> None:
        document = android_runbook()
        document["approval_ref"]["provider_plan_hash"] = "not-a-hash"
        self.assertHasCode(document, "E_HASH_INVALID")

    def test_android_mutation_approval_requires_runtime_binding_hash(self) -> None:
        document = android_runbook()
        document["approval_ref"].pop("runtime_binding_sha256")
        self.assertHasCode(document, "E_HASH_INVALID")

    def test_android_runtime_binding_hash_format_is_checked(self) -> None:
        document = android_runbook()
        document["approval_ref"]["runtime_binding_sha256"] = "not-a-hash"
        self.assertHasCode(document, "E_HASH_INVALID")

    def test_evidence_plan_kind_must_match_oracle_rule(self) -> None:
        document = web_runbook()
        document["evidence_plan"][0]["evidence_kind"] = "api_state"
        self.assertHasCode(document, "E_EVIDENCE_PLAN_KIND_MISMATCH")

    def test_command_evidence_ref_must_resolve(self) -> None:
        document = passing_web_result()
        document["execution"]["command_evidence_ref"] = "missing-command"
        self.assertHasCode(document, "E_COMMAND_EVIDENCE_REF_UNKNOWN")

    def test_command_evidence_ref_kind_is_restricted(self) -> None:
        document = passing_web_result()
        document["execution"]["command_evidence_ref"] = "visible-saved-state"
        self.assertHasCode(document, "E_COMMAND_EVIDENCE_KIND_INVALID")

    def test_blocker_severity_is_supported(self) -> None:
        document = web_scenario()
        document["severity"] = "blocker"
        self.assertValid(document)

    def test_implicit_state_changing_actions_require_mutation_approval(self) -> None:
        for action in (
            "delete",
            "submit",
            "save",
            "create",
            "update",
            "upload",
            "click",
            "activate",
            "press",
            "select_option",
        ):
            with self.subTest(action=action):
                document = web_scenario()
                document["steps"][0]["action"] = action
                codes = self.codes(document)
                self.assertIn("E_STATE_MUTATION_CLASSIFICATION_INVALID", codes)
                self.assertIn("E_MUTATION_APPROVAL_REQUIRED", codes)

    def test_unhashable_mutation_scope_returns_type_error(self) -> None:
        document = android_scenario()
        document["mutation_policy"]["approval_scope"] = [
            {"step_id": "launch-app"}
        ]
        self.assertHasCode(document, "E_MUTATION_APPROVAL_SCOPE_INVALID")

    def test_unhashable_approved_step_ids_returns_type_error(self) -> None:
        document = android_runbook()
        document["approval_ref"]["approved_step_ids"] = [
            {"step_id": "launch-app"}
        ]
        self.assertHasCode(document, "E_APPROVAL_SCOPE_INVALID")

    def test_null_mutation_policy_returns_object_error(self) -> None:
        document = web_scenario()
        document["mutation_policy"] = None
        self.assertHasCode(document, "E_MUTATION_POLICY_INVALID")

    def test_linked_source_reference_resolves(self) -> None:
        self.assertValid(web_scenario(), bundle_context=spec_bundle())

    def test_linked_dangling_source_reference_fails(self) -> None:
        document = web_scenario()
        document["source_refs"][0]["anchor_id"] = "missing-anchor"
        document["expected"][0]["source_refs"] = document["source_refs"]
        self.assertHasCode(
            document,
            "E_SOURCE_REF_ANCHOR_UNKNOWN",
            bundle_context=spec_bundle(),
        )

    def test_linked_spec_version_mismatch_fails(self) -> None:
        document = web_scenario()
        document["spec_version"] = "different-version"
        self.assertHasCode(
            document,
            "E_SPEC_VERSION_MISMATCH",
            bundle_context=spec_bundle(),
        )

    def test_semantic_result_requires_source_refs(self) -> None:
        document = passing_web_result()
        document["judge"]["mode"] = "semantic"
        document["judge"]["model"] = {
            "provider": "model-provider",
            "model_version": "model-v1",
            "prompt_version": "prompt-v1",
            "rubric_hash": "sha256:" + "6" * 64,
        }
        self.assertHasCode(document, "E_SEMANTIC_SOURCE_REFS_REQUIRED")

    def test_semantic_result_with_source_refs_passes(self) -> None:
        document = passing_web_result()
        document["judge"]["mode"] = "semantic"
        document["judge"]["model"] = {
            "provider": "model-provider",
            "model_version": "model-v1",
            "prompt_version": "prompt-v1",
            "rubric_hash": "sha256:" + "6" * 64,
        }
        document["oracle_results"][0]["source_refs"] = [
            {"source_id": "ticket-spec", "anchor_id": "save-status-ac"}
        ]
        self.assertValid(document)

    def test_every_oracle_result_requires_source_refs_array(self) -> None:
        document = passing_web_result()
        document["oracle_results"][0].pop("source_refs")
        self.assertHasCode(document, "E_REQUIRED")

    def test_oracle_result_source_ref_shape_is_checked(self) -> None:
        document = passing_web_result()
        document["oracle_results"][0]["source_refs"] = [{"source_id": "ticket-spec"}]
        self.assertHasCode(document, "E_SOURCE_REF_INVALID")

    def test_semantic_not_evaluated_may_have_empty_source_refs(self) -> None:
        document = passing_web_result()
        document["judge"]["mode"] = "semantic"
        document["judge"]["model"] = {
            "provider": "model-provider",
            "model_version": "model-v1",
            "prompt_version": "prompt-v1",
            "rubric_hash": "sha256:" + "6" * 64,
        }
        document["verdict"] = "insufficient_evidence"
        document["oracle_results"][0].update(
            {
                "status": "not_evaluated",
                "evidence_refs": [],
                "source_refs": [],
                "actual": None,
                "reason": "The required source could not be resolved.",
            }
        )
        document["missing_evidence"] = [
            {
                "oracle_id": "saved-state-rule",
                "evidence_kind": "accessibility_state",
                "reason": "The source could not be resolved.",
            }
        ]
        self.assertValid(document)

    def test_semantic_model_identity_fields_must_be_nonempty(self) -> None:
        document = passing_web_result()
        document["judge"]["mode"] = "semantic"
        document["judge"]["model"] = {
            "provider": "",
            "model_version": "model-v1",
            "prompt_version": "prompt-v1",
            "rubric_hash": "sha256:" + "6" * 64,
        }
        document["oracle_results"][0]["source_refs"] = [
            {"source_id": "ticket-spec", "anchor_id": "save-status-ac"}
        ]
        self.assertHasCode(document, "E_SEMANTIC_MODEL_IDENTITY_REQUIRED")

    def test_dependent_contracts_require_bundle_context(self) -> None:
        for document in (web_scenario(), web_runbook(), passing_web_result()):
            with self.subTest(schema_version=document["schema_version"]):
                codes = {
                    issue.code
                    for issue in validate_contracts.validate_document(document)
                }
                self.assertIn("E_BUNDLE_CONTEXT_REQUIRED", codes)
                if document["schema_version"] in ("runbook-v1", "result-v1"):
                    self.assertIn("E_SCENARIO_CONTEXT_REQUIRED", codes)
                if document["schema_version"] == "result-v1":
                    self.assertIn("E_RUNBOOK_CONTEXT_REQUIRED", codes)

    def test_result_rejects_invented_oracle_id(self) -> None:
        document = passing_web_result()
        document["oracle_results"][0]["oracle_id"] = "invented-rule"
        self.assertHasCode(document, "E_ORACLE_RESULT_ORACLE_UNKNOWN")

    def test_result_rejects_invented_expectation_id(self) -> None:
        document = passing_web_result()
        document["oracle_results"][0]["expectation_id"] = "invented-expectation"
        self.assertHasCode(document, "E_ORACLE_RESULT_EXPECTATION_MISMATCH")

    def test_result_rejects_wrong_oracle_evidence_kind(self) -> None:
        document = passing_web_result()
        document["evidence"][1]["kind"] = "dom_state"
        self.assertHasCode(document, "E_ORACLE_RESULT_EVIDENCE_KIND_MISMATCH")

    def test_result_rejects_duplicate_oracle_result(self) -> None:
        document = passing_web_result()
        document["oracle_results"].append(dict(document["oracle_results"][0]))
        self.assertHasCode(document, "E_ORACLE_RESULT_DUPLICATE")

    def test_result_identity_is_bound_to_canonical_context_hashes(self) -> None:
        document = passing_web_result()
        document["scenario_hash"] = "sha256:" + "1" * 64
        document["runbook_hash"] = "sha256:" + "2" * 64
        codes = self.codes(document)
        self.assertIn("E_RESULT_SCENARIO_HASH_MISMATCH", codes)
        self.assertIn("E_RESULT_RUNBOOK_HASH_MISMATCH", codes)

    def test_linked_runbook_must_preserve_scenario_contract(self) -> None:
        document = passing_web_result()
        runbook = web_runbook()
        runbook["fixture"] = {
            "kind": "none",
            "purpose": "baseline",
            "destructive": False,
            "environment": "shared_test",
        }
        rehash_runbook(runbook)
        document["runbook_hash"] = validate_contracts._canonical_json_hash(runbook)
        self.assertHasCode(
            document,
            "E_RUNBOOK_SCENARIO_FIXTURE_MISMATCH",
            runbook_context=runbook,
        )

    def test_semantic_result_source_refs_stay_within_linked_expectation(self) -> None:
        bundle = spec_bundle()
        second_source = {
            "id": "policy-spec",
            "kind": "policy",
            "title": "Independent policy",
            "version": "1",
            "content_hash": "",
            "anchors": [
                {
                    "id": "other-policy",
                    "kind": "policy_rule",
                    "title": "Other policy",
                    "statement": "An unrelated policy remains active.",
                    "status": "approved",
                }
            ],
        }
        second_source["content_hash"] = (
            validate_contracts._canonical_source_content_hash(second_source)
        )
        bundle["sources"].append(second_source)

        scenario = web_scenario()
        scenario["source_refs"].append(
            {"source_id": "policy-spec", "anchor_id": "other-policy"}
        )
        runbook = web_runbook()
        runbook["source_refs"] = scenario["source_refs"]
        runbook["scenario_hash"] = validate_contracts._canonical_json_hash(scenario)
        rehash_runbook(runbook)

        document = passing_web_result()
        document["scenario_hash"] = validate_contracts._canonical_json_hash(scenario)
        document["runbook_hash"] = validate_contracts._canonical_json_hash(runbook)
        document["judge"]["mode"] = "semantic"
        document["judge"]["model"] = {
            "provider": "model-provider",
            "model_version": "model-v1",
            "prompt_version": "prompt-v1",
            "rubric_hash": "sha256:" + "6" * 64,
        }
        document["judge"]["source_hashes"].append(second_source["content_hash"])
        document["oracle_results"][0]["source_refs"] = [
            {"source_id": "policy-spec", "anchor_id": "other-policy"}
        ]
        self.assertHasCode(
            document,
            "E_SEMANTIC_SOURCE_REF_OUT_OF_SCOPE",
            bundle_context=bundle,
            scenario_context=scenario,
            runbook_context=runbook,
        )

    def test_runbook_provider_binding_and_project_hash_are_required(self) -> None:
        document = web_runbook()
        document.pop("provider_binding")
        document.pop("project_config_sha256")
        codes = self.codes(document)
        self.assertIn("E_PROVIDER_BINDING_INVALID", codes)
        self.assertIn("E_HASH_INVALID", codes)

    def test_runbook_step_materialization_fields_are_required(self) -> None:
        document = web_runbook()
        for field in (
            "arguments",
            "provider_args",
            "timeout_ms",
            "retry_policy",
            "max_attempts",
            "provider_defaults_version",
        ):
            document["steps"][0].pop(field)
        codes = self.codes(document)
        self.assertIn("E_PROVIDER_ARGS_INVALID", codes)
        self.assertIn("E_STEP_TIMEOUT_INVALID", codes)
        self.assertIn("E_STEP_RETRY_POLICY_INVALID", codes)
        self.assertIn("E_STEP_MAX_ATTEMPTS_INVALID", codes)
        self.assertIn("E_PROVIDER_DEFAULTS_VERSION_INVALID", codes)

    def test_runbook_arguments_may_be_null(self) -> None:
        document = web_runbook()
        document["steps"][0]["arguments"] = None
        rehash_runbook(document)
        self.assertValid(document)

    def test_scenario_arguments_may_not_be_null(self) -> None:
        document = web_scenario()
        document["steps"][0]["arguments"] = None
        self.assertHasCode(document, "E_FIELD_TYPE")

    def test_runbook_provider_args_must_be_fully_resolved(self) -> None:
        for provider_args in (
            {"locator_ref": "project-locator"},
            {"locator_candidates": ["first", "second"]},
            {"url": "${QA_BASE_URL}/saved-item"},
        ):
            with self.subTest(provider_args=provider_args):
                document = web_runbook()
                document["steps"][0]["provider_args"] = provider_args
                self.assertHasCode(
                    document, "E_RUNBOOK_UNRESOLVED_PROVIDER_INPUT"
                )

    def test_runbook_timeout_retry_and_defaults_are_bounded(self) -> None:
        document = web_runbook()
        document["steps"][0].update(
            {
                "timeout_ms": 120001,
                "retry_policy": "never",
                "max_attempts": 2,
                "provider_defaults_version": "different-defaults",
            }
        )
        codes = self.codes(document)
        self.assertIn("E_STEP_TIMEOUT_INVALID", codes)
        self.assertIn("E_STEP_RETRY_CONTRACT_INVALID", codes)
        self.assertIn("E_PROVIDER_DEFAULTS_VERSION_MISMATCH", codes)

    def test_mutation_runbook_steps_cannot_retry(self) -> None:
        document = android_runbook()
        document["steps"][0]["retry_policy"] = "safe"
        document["steps"][0]["max_attempts"] = 2
        self.assertHasCode(document, "E_MUTATION_STEP_RETRY_FORBIDDEN")

    def test_evidence_plan_covers_each_oracle_exactly_once(self) -> None:
        duplicate = web_runbook()
        duplicate["evidence_plan"].append(dict(duplicate["evidence_plan"][0]))
        self.assertHasCode(duplicate, "E_EVIDENCE_PLAN_DUPLICATE")

        missing = web_runbook()
        missing["oracle"]["rules"].append(
            {
                "id": "second-rule",
                "kind": "deterministic",
                "expectation_id": "saved-state-visible",
                "evidence_kind": "dom_state",
                "operator": "contains",
                "actual_path": "/state_text",
                "value": "saved",
            }
        )
        self.assertHasCode(missing, "E_EVIDENCE_PLAN_COVERAGE_MISSING")

    def test_runbook_plan_hash_covers_materialized_step_description(self) -> None:
        document = web_runbook()
        document["steps"][0]["description"] = "Changed after approval."
        self.assertHasCode(document, "E_RUNBOOK_PLAN_HASH_MISMATCH")

    def test_runbook_plan_hash_uses_exact_canonical_projection(self) -> None:
        document = web_runbook()
        projection = {
            field: document[field]
            for field in validate_contracts.RUNBOOK_PLAN_FIELDS
        }
        serialized = json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        expected = "sha256:" + hashlib.sha256(serialized).hexdigest()
        self.assertEqual(expected, document["integrity"]["plan_sha256"])

    def test_each_matched_oracle_must_cite_its_own_objective_state(self) -> None:
        document = passing_web_result()
        document["evidence"].append(
            {
                "id": "second-command",
                "kind": "test_command",
                "collected_at": "2026-08-01T02:00:02Z",
                "producer": {"type": "runner", "name": "web-playwright"},
                "sha256": "sha256:" + "7" * 64,
                "redactions": [],
                "record": {"status": "completed"},
            }
        )
        document["judge"]["evidence_hashes"].append("sha256:" + "7" * 64)
        document["oracle_results"].append(
            {
                "oracle_id": "second-rule",
                "expectation_id": "second-expectation",
                "status": "matched",
                "evidence_refs": ["second-command"],
                "source_refs": [],
                "actual": "completed",
                "reason": None,
            }
        )
        self.assertHasCode(
            document, "E_PASS_OBJECTIVE_STATE_EVIDENCE_REQUIRED"
        )

    def test_oracle_evidence_hash_must_be_registered_by_judge(self) -> None:
        document = passing_web_result()
        document["judge"]["evidence_hashes"].remove("sha256:" + "e" * 64)
        self.assertHasCode(document, "E_JUDGE_EVIDENCE_HASH_MISSING")

    def test_nested_runner_status_pass_is_self_report(self) -> None:
        document = passing_web_result()
        document["evidence"].append(
            {
                "id": "runner-summary",
                "kind": "structured_log",
                "collected_at": "2026-08-01T02:00:03Z",
                "producer": {"type": "adapter", "name": "provider-adapter"},
                "sha256": "sha256:" + "7" * 64,
                "redactions": [],
                "record": {"events": [{"result": {"status": "pass"}}]},
            }
        )
        self.assertHasCode(document, "E_SELF_REPORT_EVIDENCE_FORBIDDEN")

    def test_operational_structured_log_statuses_are_allowed(self) -> None:
        for status in ("completed", "partial", "not_started", "error", "skipped"):
            with self.subTest(status=status):
                document = passing_web_result()
                document["evidence"].append(
                    {
                        "id": "runner-operation",
                        "kind": "structured_log",
                        "collected_at": "2026-08-01T02:00:03Z",
                        "producer": {"type": "runner", "name": "web-playwright"},
                        "sha256": "sha256:" + "7" * 64,
                        "redactions": [],
                        "record": {"operation": {"status": status}},
                    }
                )
                self.assertNotIn(
                    "E_SELF_REPORT_EVIDENCE_FORBIDDEN", self.codes(document)
                )

    def test_valid_started_android_result_records_runtime_identity(self) -> None:
        self.assertValid(passing_android_result())

    def test_partial_android_result_allows_unobserved_runtime_versions(self) -> None:
        document = passing_android_result()
        document["execution"]["status"] = "partial"
        document["subject"]["native_runtime"]["appium_version"] = None
        document["subject"]["native_runtime"]["automation_driver_version"] = None
        self.assertNotIn("E_ANDROID_RUNTIME_FIELD_REQUIRED", self.codes(document))

    def test_completed_android_result_requires_observed_runtime_versions(self) -> None:
        document = passing_android_result()
        document["subject"]["native_runtime"]["appium_version"] = None
        document["subject"]["native_runtime"]["automation_driver_version"] = None
        self.assertHasCode(document, "E_ANDROID_RUNTIME_FIELD_REQUIRED")

    def test_started_android_result_requires_every_runtime_identity_field(self) -> None:
        required_fields = (
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
        )
        for field in required_fields:
            with self.subTest(field=field):
                document = passing_android_result()
                document["subject"]["native_runtime"].pop(field)
                self.assertHasCode(document, "E_REQUIRED")

    def test_android_result_requires_uiautomator2(self) -> None:
        document = passing_android_result()
        document["subject"]["native_runtime"]["automation_driver"] = "espresso"
        self.assertHasCode(document, "E_ANDROID_AUTOMATION_DRIVER_UNSUPPORTED")

    def test_semantic_result_source_refs_resolve_against_bundle(self) -> None:
        document = passing_web_result()
        document["judge"]["mode"] = "semantic"
        document["judge"]["model"] = {
            "provider": "model-provider",
            "model_version": "model-v1",
            "prompt_version": "prompt-v1",
            "rubric_hash": "sha256:" + "6" * 64,
        }
        document["oracle_results"][0]["source_refs"] = [
            {"source_id": "ticket-spec", "anchor_id": "missing-anchor"}
        ]
        self.assertHasCode(document, "E_SOURCE_REF_ANCHOR_UNKNOWN")

    def test_result_spec_version_must_match_bundle(self) -> None:
        document = passing_web_result()
        document["spec_version"] = "different-version"
        self.assertHasCode(document, "E_SPEC_VERSION_MISMATCH")

    def test_judge_source_hashes_must_belong_to_bundle(self) -> None:
        document = passing_web_result()
        document["judge"]["source_hashes"] = ["sha256:" + "f" * 64]
        self.assertHasCode(document, "E_JUDGE_SOURCE_HASH_UNLINKED")

    def test_semantic_referenced_source_hash_must_be_judge_input(self) -> None:
        document = passing_web_result()
        document["judge"]["mode"] = "semantic"
        document["judge"]["model"] = {
            "provider": "model-provider",
            "model_version": "model-v1",
            "prompt_version": "prompt-v1",
            "rubric_hash": "sha256:" + "6" * 64,
        }
        document["judge"]["source_hashes"] = []
        document["oracle_results"][0]["source_refs"] = [
            {"source_id": "ticket-spec", "anchor_id": "save-status-ac"}
        ]
        self.assertHasCode(document, "E_JUDGE_SOURCE_HASH_MISSING")

    def test_sensitive_hash_and_inline_artifact_aliases_are_rejected(self) -> None:
        probes = (
            ("password_hash", "sha256:" + "1" * 64),
            ("apk_payload_bytes", [80, 75, 3, 4]),
            ("apk_archive_payload", "UEsDBAoAAAAA"),
        )
        for key, value in probes:
            with self.subTest(key=key):
                document = android_scenario()
                document["fixture"][key] = value
                expected = (
                    "E_SENSITIVE_INPUT"
                    if key == "password_hash"
                    else "E_ARTIFACT_INLINE_DATA"
                )
                issues = validate_contracts.validate_document(
                    document, spec_bundle=spec_bundle()
                )
                self.assertIn(expected, {issue.code for issue in issues})
                rendered = json.dumps([issue.as_dict() for issue in issues])
                self.assertNotIn(str(value), rendered)

    def test_blocked_result_requires_partial_or_not_started_status(self) -> None:
        document = passing_web_result()
        document["verdict"] = "blocked"
        document["blockers"] = [
            {
                "code": "runtime-unavailable",
                "description": "The provider did not start.",
                "evidence_refs": ["runner-command"],
            }
        ]
        self.assertHasCode(document, "E_BLOCKED_EXECUTION_STATUS_INVALID")

    def test_blocker_evidence_refs_must_resolve(self) -> None:
        document = passing_web_result()
        document["verdict"] = "blocked"
        document["execution"]["status"] = "partial"
        document["blockers"] = [
            {
                "code": "runtime-unavailable",
                "description": "The provider stopped.",
                "evidence_refs": ["unknown-evidence"],
            }
        ]
        self.assertHasCode(document, "E_ORACLE_EVIDENCE_UNKNOWN")

    def test_conflict_requires_two_source_refs(self) -> None:
        document = passing_web_result()
        document["verdict"] = "conflict"
        document["conflicts"] = [
            {
                "id": "source-conflict",
                "description": "Two sources disagree.",
                "source_refs": [
                    {"source_id": "ticket-spec", "anchor_id": "save-status-ac"}
                ],
            }
        ]
        self.assertHasCode(document, "E_CONFLICT_SOURCE_REFS_REQUIRED")

    def test_missing_evidence_entries_have_fixed_shape(self) -> None:
        document = passing_web_result()
        document["verdict"] = "insufficient_evidence"
        document["oracle_results"][0].update(
            {
                "status": "not_evaluated",
                "evidence_refs": [],
                "actual": None,
                "reason": "State evidence is missing.",
            }
        )
        document["missing_evidence"] = [
            {"oracle_id": "saved-state-rule", "evidence_kind": "screen_capture"}
        ]
        codes = self.codes(document)
        self.assertIn("E_REQUIRED", codes)
        self.assertIn("E_EVIDENCE_KIND_UNSUPPORTED", codes)

    def test_unsupported_reason_is_forbidden_for_pass(self) -> None:
        document = passing_web_result()
        document["unsupported_reason"] = "provider unavailable"
        self.assertHasCode(document, "E_UNSUPPORTED_REASON_FORBIDDEN")

    def test_diagnostic_attachment_shape_is_validated_separately(self) -> None:
        document = passing_web_result()
        attachment_hash = "sha256:" + "7" * 64
        document["diagnostic_attachments"] = [
            {
                "kind": "screenshot",
                "artifact_ref": "diagnostics/failure.png",
                "sha256": attachment_hash,
            }
        ]
        self.assertNotIn(attachment_hash, document["judge"]["evidence_hashes"])
        self.assertValid(document)

        invalid = passing_web_result()
        invalid["diagnostic_attachments"] = [
            {
                "kind": "dom_state",
                "artifact_ref": "/absolute/failure.json",
                "sha256": "invalid",
            }
        ]
        codes = self.codes(invalid)
        self.assertIn("E_DIAGNOSTIC_ATTACHMENT_KIND_UNSUPPORTED", codes)
        self.assertIn("E_ARTIFACT_REF_INVALID", codes)
        self.assertIn("E_HASH_INVALID", codes)

    def test_enum_fields_reject_container_values_without_crashing(self) -> None:
        documents_and_mutations = (
            (web_scenario, lambda value: value.update({"method": []})),
            (web_scenario, lambda value: value.update({"severity": {}})),
            (
                web_scenario,
                lambda value: value["target"].update({"platform": set()}),
            ),
            (passing_web_result, lambda value: value.update({"verdict": set()})),
            (
                passing_web_result,
                lambda value: value["judge"].update({"mode": []}),
            ),
            (
                passing_web_result,
                lambda value: value["evidence"][0].update({"kind": {}}),
            ),
            (
                passing_web_result,
                lambda value: value["execution"].update(
                    {"command_evidence_ref": []}
                ),
            ),
            (
                web_runbook,
                lambda value: value["evidence_plan"][0].update(
                    {"oracle_rule_id": []}
                ),
            ),
        )
        for factory, mutate in documents_and_mutations:
            with self.subTest(factory=factory.__name__):
                document = factory()
                mutate(document)
                issues = validate_contracts.validate_document(
                    document, spec_bundle=spec_bundle()
                )
                self.assertTrue(issues)

    def test_explicit_contract_selection_validates_document(self) -> None:
        document = web_scenario()
        document.pop("schema_version")
        codes = self.codes(document, "scenario-v1")
        self.assertIn("E_REQUIRED", codes)
        self.assertNotIn("E_SCHEMA_VERSION_REQUIRED", codes)

    def test_cli_returns_nonzero_and_stable_error_code(self) -> None:
        document = web_scenario()
        document["source_refs"] = []
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "scenario.json"
            input_path.write_text(json.dumps(document), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--output",
                    "json",
                    str(input_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(1, completed.returncode)
        report = json.loads(completed.stdout)
        codes = {item["code"] for item in report["reports"][0]["errors"]}
        self.assertIn("E_SOURCE_REFS_REQUIRED", codes)

    def test_cli_bundle_rejects_dangling_source_reference(self) -> None:
        document = web_scenario()
        document["source_refs"][0]["source_id"] = "missing-source"
        document["expected"][0]["source_refs"] = document["source_refs"]
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_path = Path(temporary_directory) / "bundle.json"
            scenario_path = Path(temporary_directory) / "scenario.json"
            bundle_path.write_text(json.dumps(spec_bundle()), encoding="utf-8")
            scenario_path.write_text(json.dumps(document), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--bundle",
                    str(bundle_path),
                    "--output",
                    "json",
                    str(scenario_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(1, completed.returncode)
        report = json.loads(completed.stdout)
        codes = {
            item["code"]
            for result in report["reports"]
            for item in result["errors"]
        }
        self.assertIn("E_SOURCE_REF_SOURCE_UNKNOWN", codes)

    def test_cli_auto_links_bundle_from_multiple_inputs(self) -> None:
        document = web_scenario()
        document["source_refs"][0]["anchor_id"] = "missing-anchor"
        document["expected"][0]["source_refs"] = document["source_refs"]
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_path = Path(temporary_directory) / "bundle.json"
            scenario_path = Path(temporary_directory) / "scenario.json"
            bundle_path.write_text(json.dumps(spec_bundle()), encoding="utf-8")
            scenario_path.write_text(json.dumps(document), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--output",
                    "json",
                    str(bundle_path),
                    str(scenario_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(1, completed.returncode)
        report = json.loads(completed.stdout)
        codes = {
            item["code"]
            for result in report["reports"]
            for item in result["errors"]
        }
        self.assertIn("E_SOURCE_REF_ANCHOR_UNKNOWN", codes)

    def test_cli_bundle_is_applied_to_semantic_result(self) -> None:
        document = passing_web_result()
        document["judge"]["mode"] = "semantic"
        document["judge"]["model"] = {
            "provider": "model-provider",
            "model_version": "model-v1",
            "prompt_version": "prompt-v1",
            "rubric_hash": "sha256:" + "6" * 64,
        }
        document["oracle_results"][0]["source_refs"] = [
            {"source_id": "ticket-spec", "anchor_id": "missing-anchor"}
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_path = Path(temporary_directory) / "bundle.json"
            result_path = Path(temporary_directory) / "result.json"
            bundle_path.write_text(json.dumps(spec_bundle()), encoding="utf-8")
            result_path.write_text(json.dumps(document), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--bundle",
                    str(bundle_path),
                    "--output",
                    "json",
                    str(result_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(1, completed.returncode)
        report = json.loads(completed.stdout)
        codes = {
            item["code"]
            for result in report["reports"]
            for item in result["errors"]
        }
        self.assertIn("E_SOURCE_REF_ANCHOR_UNKNOWN", codes)

    def test_cli_explicit_result_contexts_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = {
                "bundle": root / "bundle.json",
                "scenario": root / "scenario.json",
                "runbook": root / "runbook.json",
                "result": root / "result.json",
            }
            documents = {
                "bundle": spec_bundle(),
                "scenario": web_scenario(),
                "runbook": web_runbook(),
                "result": passing_web_result(),
            }
            for name, path in paths.items():
                path.write_text(json.dumps(documents[name]), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--bundle",
                    str(paths["bundle"]),
                    "--scenario",
                    str(paths["scenario"]),
                    "--runbook",
                    str(paths["runbook"]),
                    "--output",
                    "json",
                    str(paths["result"]),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(0, completed.returncode, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual("contract-validation-report-v1", report["schema_version"])
        self.assertEqual(
            "spec-driven-qa-contract-validator", report["validator"]["name"]
        )
        self.assertRegex(report["validator"]["sha256"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(
            "sha256:" + hashlib.sha256(SCRIPT_PATH.read_bytes()).hexdigest(),
            report["validator"]["sha256"],
        )
        self.assertEqual(
            validate_contracts._canonical_json_hash(spec_bundle()),
            report["contexts"]["bundle"]["sha256"],
        )
        self.assertEqual(
            validate_contracts._canonical_json_hash(web_scenario()),
            report["contexts"]["scenario"]["sha256"],
        )
        self.assertEqual(
            validate_contracts._canonical_json_hash(web_runbook()),
            report["contexts"]["runbook"]["sha256"],
        )
        self.assertEqual(
            validate_contracts._canonical_json_hash(passing_web_result()),
            report["reports"][0]["sha256"],
        )
        self.assertTrue(all(item["valid"] for item in report["reports"]))

    def test_cli_auto_links_result_contexts_from_multiple_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            documents = (
                ("bundle.json", spec_bundle()),
                ("scenario.json", web_scenario()),
                ("runbook.json", web_runbook()),
                ("result.json", passing_web_result()),
            )
            paths = []
            for name, document in documents:
                path = root / name
                path.write_text(json.dumps(document), encoding="utf-8")
                paths.append(path)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--output",
                    "json",
                    *(str(path) for path in paths),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(0, completed.returncode, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(4, len(report["reports"]))
        self.assertTrue(all(item["valid"] for item in report["reports"]))


if __name__ == "__main__":
    unittest.main()
