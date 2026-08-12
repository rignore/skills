from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "calibrate-judge.py"
SPEC = importlib.util.spec_from_file_location("calibrate_judge", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
calibrate_judge = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = calibrate_judge
SPEC.loader.exec_module(calibrate_judge)


def calibration(case_count: int = 30) -> dict:
    cases = []
    for index in range(case_count):
        gold = "pass" if index < case_count // 2 else "fail"
        label_b = gold
        if case_count >= 30 and index in (2, 18, 22):
            label_b = "fail" if gold == "pass" else "pass"
        prediction = gold
        cases.append(
            {
                "id": f"case-{index + 1:02d}",
                "input_sha256": "sha256:" + f"{index + 1:064x}",
                "labeler_a": {
                    "actor_type": "human",
                    "actor_ref": "human:labeler-a",
                    "verdict": gold,
                },
                "labeler_b": {
                    "actor_type": "human",
                    "actor_ref": "human:labeler-b",
                    "verdict": label_b,
                },
                "adjudication": {
                    "status": "resolved",
                    "adjudicator_ref": "human:domain-owner",
                    "gold_verdict": gold,
                },
                "prediction": {
                    "input_sha256": "sha256:" + f"{index + 1:064x}",
                    "verdict": prediction,
                    "evaluation_error": None,
                },
            }
        )
    return {
        "schema_version": "semantic-calibration-v1",
        "calibration_id": "semantic-judge-p4-fixture",
        "judge": {
            "provider": "configured-provider",
            "model_version": "immutable-model-1",
            "prompt_version": "semantic-judge-v1",
            "rubric_hash": "sha256:" + "a" * 64,
        },
        "policy": {
            "minimum_case_count": 30,
            "minimum_kappa": 0.6,
            "minimum_pass_precision": 0.95,
        },
        "cases": cases,
    }


class CalibrationTests(unittest.TestCase):
    def test_thirty_resolved_cases_pass_gate(self) -> None:
        report = calibrate_judge.calibrate(calibration())
        self.assertTrue(report["gate_passed"])
        self.assertEqual(report["case_count"], 30)
        self.assertGreaterEqual(report["labeler_agreement"]["cohens_kappa"], 0.6)
        self.assertEqual(report["automatic_pass"]["precision"], 1.0)

    def test_fewer_than_thirty_cases_fail_gate(self) -> None:
        report = calibrate_judge.calibrate(calibration(29))
        self.assertFalse(report["gate_passed"])
        self.assertFalse(report["checks"]["case_count"])

    def test_missing_pass_prediction_fails_gate(self) -> None:
        document = calibration()
        for case in document["cases"]:
            case["prediction"]["verdict"] = "fail"
        report = calibrate_judge.calibrate(document)
        self.assertFalse(report["gate_passed"])
        self.assertIsNone(report["automatic_pass"]["precision"])
        self.assertFalse(report["checks"]["pass_prediction_present"])

    def test_low_pass_precision_fails_gate(self) -> None:
        document = calibration()
        for case in document["cases"]:
            case["prediction"]["verdict"] = "pass"
        report = calibrate_judge.calibrate(document)
        self.assertFalse(report["gate_passed"])
        self.assertEqual(report["automatic_pass"]["precision"], 0.5)

    def test_unresolved_adjudication_fails_gate(self) -> None:
        document = calibration()
        document["cases"][0]["adjudication"] = {"status": "pending"}
        report = calibrate_judge.calibrate(document)
        self.assertFalse(report["gate_passed"])
        self.assertEqual(report["unresolved_adjudications"], 1)

    def test_evaluation_error_fails_gate(self) -> None:
        document = calibration()
        document["cases"][0]["prediction"]["evaluation_error"] = "timeout"
        document["cases"][0]["prediction"]["verdict"] = None
        report = calibrate_judge.calibrate(document)
        self.assertFalse(report["gate_passed"])
        self.assertEqual(report["evaluation_errors"], 1)

    def test_degenerate_labels_do_not_invent_kappa(self) -> None:
        document = calibration()
        for case in document["cases"]:
            case["labeler_a"]["verdict"] = "pass"
            case["labeler_b"]["verdict"] = "pass"
            case["adjudication"]["gold_verdict"] = "pass"
        report = calibrate_judge.calibrate(document)
        self.assertFalse(report["gate_passed"])
        self.assertIsNone(report["labeler_agreement"]["cohens_kappa"])

    def test_same_labeler_is_rejected(self) -> None:
        document = calibration()
        document["cases"][0]["labeler_b"]["actor_ref"] = "human:labeler-a"
        with self.assertRaises(calibrate_judge.CalibrationError) as raised:
            calibrate_judge.calibrate(document)
        self.assertEqual(raised.exception.code, "E_LABELERS_NOT_INDEPENDENT")

    def test_non_human_label_is_rejected(self) -> None:
        document = calibration()
        document["cases"][0]["labeler_a"]["actor_type"] = "agent"
        with self.assertRaises(calibrate_judge.CalibrationError) as raised:
            calibrate_judge.calibrate(document)
        self.assertEqual(raised.exception.code, "E_HUMAN_LABEL_REQUIRED")

    def test_prediction_must_bind_the_same_input(self) -> None:
        document = calibration()
        document["cases"][0]["prediction"]["input_sha256"] = "sha256:" + "f" * 64
        with self.assertRaises(calibrate_judge.CalibrationError) as raised:
            calibrate_judge.calibrate(document)
        self.assertEqual(raised.exception.code, "E_PREDICTION_INPUT_HASH_MISMATCH")

    def test_duplicate_gold_inputs_are_rejected(self) -> None:
        document = calibration()
        document["cases"][1]["input_sha256"] = document["cases"][0]["input_sha256"]
        document["cases"][1]["prediction"]["input_sha256"] = document["cases"][0]["input_sha256"]
        with self.assertRaises(calibrate_judge.CalibrationError) as raised:
            calibrate_judge.calibrate(document)
        self.assertEqual(raised.exception.code, "E_DUPLICATE_INPUT_HASH")

    def test_adjudicator_must_be_independent(self) -> None:
        document = calibration()
        document["cases"][2]["adjudication"]["adjudicator_ref"] = "human:labeler-a"
        with self.assertRaises(calibrate_judge.CalibrationError) as raised:
            calibrate_judge.calibrate(document)
        self.assertEqual(raised.exception.code, "E_ADJUDICATOR_NOT_INDEPENDENT")

    def test_agreement_does_not_require_a_third_adjudicator(self) -> None:
        document = calibration()
        document["cases"][0]["adjudication"]["adjudicator_ref"] = None
        report = calibrate_judge.calibrate(document)
        self.assertTrue(report["gate_passed"])

    def test_agreed_label_cannot_be_changed_during_adjudication(self) -> None:
        document = calibration()
        document["cases"][0]["adjudication"]["gold_verdict"] = "fail"
        with self.assertRaises(calibrate_judge.CalibrationError) as raised:
            calibrate_judge.calibrate(document)
        self.assertEqual(raised.exception.code, "E_AGREED_GOLD_LABEL_MISMATCH")

    def test_cli_exit_code_tracks_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "calibration.json"
            output_path = Path(directory) / "report.json"
            input_path.write_text(json.dumps(calibration()), encoding="utf-8")
            passed = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(input_path), "--output", str(output_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(passed.returncode, 0, passed.stderr)
            document = calibration(29)
            input_path.write_text(json.dumps(document), encoding="utf-8")
            failed = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(input_path), "--output", str(output_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(failed.returncode, 1, failed.stderr)


if __name__ == "__main__":
    unittest.main()
