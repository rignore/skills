#!/usr/bin/env python3
"""Calculate the semantic judge release gate from independent human labels."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


VERDICTS = {
    "pass",
    "fail",
    "conflict",
    "insufficient_evidence",
    "blocked",
    "unsupported",
}
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class CalibrationError(ValueError):
    def __init__(self, code: str, path: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.path = path

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": str(self)}


def _require_object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CalibrationError("E_FIELD_TYPE", path, "must be an object")
    return value


def _require_nonempty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise CalibrationError("E_FIELD_TYPE", path, "must be a non-empty string")
    return value


def _require_verdict(value: Any, path: str) -> str:
    if value not in VERDICTS:
        raise CalibrationError(
            "E_VERDICT_UNSUPPORTED",
            path,
            f"must be one of {', '.join(sorted(VERDICTS))}",
        )
    return value


def _validate_label(value: Any, path: str) -> tuple[str, str]:
    label = _require_object(value, path)
    if label.get("actor_type") != "human":
        raise CalibrationError(
            "E_HUMAN_LABEL_REQUIRED",
            f"{path}.actor_type",
            "independent calibration labels require actor_type='human'",
        )
    actor_ref = _require_nonempty_string(label.get("actor_ref"), f"{path}.actor_ref")
    verdict = _require_verdict(label.get("verdict"), f"{path}.verdict")
    return actor_ref, verdict


def cohens_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float | None:
    if len(labels_a) != len(labels_b) or not labels_a:
        raise ValueError("label sequences must have the same non-zero length")
    count = len(labels_a)
    observed = sum(left == right for left, right in zip(labels_a, labels_b)) / count
    counts_a = Counter(labels_a)
    counts_b = Counter(labels_b)
    expected = sum(
        (counts_a[label] / count) * (counts_b[label] / count)
        for label in VERDICTS
    )
    if math.isclose(expected, 1.0):
        return None
    return (observed - expected) / (1.0 - expected)


def calibrate(document: Mapping[str, Any]) -> dict[str, Any]:
    if document.get("schema_version") != "semantic-calibration-v1":
        raise CalibrationError(
            "E_SCHEMA_VERSION",
            "$.schema_version",
            "must equal semantic-calibration-v1",
        )
    policy = _require_object(document.get("policy"), "$.policy")
    judge = _require_object(document.get("judge"), "$.judge")
    for field in ("provider", "model_version", "prompt_version"):
        _require_nonempty_string(judge.get(field), f"$.judge.{field}")
    rubric_hash = judge.get("rubric_hash")
    if not isinstance(rubric_hash, str) or not SHA256_PATTERN.fullmatch(rubric_hash):
        raise CalibrationError(
            "E_RUBRIC_HASH_INVALID",
            "$.judge.rubric_hash",
            "must be sha256:<64 lowercase hex>",
        )
    minimum_case_count = policy.get("minimum_case_count")
    if not isinstance(minimum_case_count, int) or isinstance(minimum_case_count, bool) or minimum_case_count < 30:
        raise CalibrationError(
            "E_MINIMUM_CASE_COUNT_INVALID",
            "$.policy.minimum_case_count",
            "must be an integer of at least 30",
        )
    minimum_kappa = policy.get("minimum_kappa")
    if not isinstance(minimum_kappa, (int, float)) or isinstance(minimum_kappa, bool) or not 0 <= minimum_kappa <= 1:
        raise CalibrationError(
            "E_MINIMUM_KAPPA_INVALID",
            "$.policy.minimum_kappa",
            "must be a number from 0 through 1",
        )
    minimum_precision = policy.get("minimum_pass_precision")
    if not isinstance(minimum_precision, (int, float)) or isinstance(minimum_precision, bool) or not 0 <= minimum_precision <= 1:
        raise CalibrationError(
            "E_MINIMUM_PASS_PRECISION_REQUIRED",
            "$.policy.minimum_pass_precision",
            "must be a configured number from 0 through 1",
        )
    cases = document.get("cases")
    if not isinstance(cases, list):
        raise CalibrationError("E_FIELD_TYPE", "$.cases", "must be an array")

    ids: set[str] = set()
    input_hashes: set[str] = set()
    labels_a: list[str] = []
    labels_b: list[str] = []
    predicted_pass = 0
    true_positive_pass = 0
    unresolved = 0
    evaluation_errors = 0
    for index, raw_case in enumerate(cases):
        path = f"$.cases[{index}]"
        case = _require_object(raw_case, path)
        case_id = _require_nonempty_string(case.get("id"), f"{path}.id")
        if case_id in ids:
            raise CalibrationError("E_DUPLICATE_CASE_ID", f"{path}.id", "case ids must be unique")
        ids.add(case_id)
        input_sha256 = case.get("input_sha256")
        if not isinstance(input_sha256, str) or not SHA256_PATTERN.fullmatch(input_sha256):
            raise CalibrationError(
                "E_INPUT_HASH_INVALID",
                f"{path}.input_sha256",
                "must bind the frozen semantic request as sha256:<64 lowercase hex>",
            )
        if input_sha256 in input_hashes:
            raise CalibrationError(
                "E_DUPLICATE_INPUT_HASH",
                f"{path}.input_sha256",
                "gold cases must bind distinct frozen semantic requests",
            )
        input_hashes.add(input_sha256)
        actor_a, verdict_a = _validate_label(case.get("labeler_a"), f"{path}.labeler_a")
        actor_b, verdict_b = _validate_label(case.get("labeler_b"), f"{path}.labeler_b")
        if actor_a == actor_b:
            raise CalibrationError(
                "E_LABELERS_NOT_INDEPENDENT",
                path,
                "labeler_a and labeler_b must identify different human actors",
            )
        labels_a.append(verdict_a)
        labels_b.append(verdict_b)
        adjudication = _require_object(case.get("adjudication"), f"{path}.adjudication")
        if adjudication.get("status") != "resolved":
            unresolved += 1
            gold_verdict = None
        else:
            gold_verdict = _require_verdict(adjudication.get("gold_verdict"), f"{path}.adjudication.gold_verdict")
            adjudicator_ref = adjudication.get("adjudicator_ref")
            if verdict_a != verdict_b:
                adjudicator_ref = _require_nonempty_string(adjudicator_ref, f"{path}.adjudication.adjudicator_ref")
                if adjudicator_ref in (actor_a, actor_b):
                    raise CalibrationError(
                        "E_ADJUDICATOR_NOT_INDEPENDENT",
                        f"{path}.adjudication.adjudicator_ref",
                        "disagreements require an adjudicator who differs from both original labelers",
                    )
            elif gold_verdict != verdict_a:
                raise CalibrationError(
                    "E_AGREED_GOLD_LABEL_MISMATCH",
                    f"{path}.adjudication.gold_verdict",
                    "when labelers agree, gold_verdict must preserve their common verdict",
                )
        prediction = _require_object(case.get("prediction"), f"{path}.prediction")
        if prediction.get("input_sha256") != input_sha256:
            raise CalibrationError(
                "E_PREDICTION_INPUT_HASH_MISMATCH",
                f"{path}.prediction.input_sha256",
                "prediction must bind the same frozen semantic request as the human labels",
            )
        evaluation_error = prediction.get("evaluation_error")
        if evaluation_error not in (None, ""):
            evaluation_errors += 1
            predicted_verdict = prediction.get("verdict")
            if predicted_verdict is not None:
                predicted_verdict = _require_verdict(predicted_verdict, f"{path}.prediction.verdict")
        else:
            predicted_verdict = _require_verdict(prediction.get("verdict"), f"{path}.prediction.verdict")
        if predicted_verdict == "pass":
            predicted_pass += 1
            if gold_verdict == "pass":
                true_positive_pass += 1

    kappa = cohens_kappa(labels_a, labels_b) if cases else None
    pass_precision = true_positive_pass / predicted_pass if predicted_pass else None
    checks = {
        "case_count": len(cases) >= minimum_case_count,
        "kappa_defined": kappa is not None,
        "kappa": kappa is not None and kappa >= minimum_kappa,
        "pass_prediction_present": predicted_pass > 0,
        "pass_precision": pass_precision is not None and pass_precision >= minimum_precision,
        "adjudications_resolved": unresolved == 0,
        "evaluation_errors_absent": evaluation_errors == 0,
    }
    return {
        "schema_version": "semantic-calibration-report-v1",
        "calibration_id": _require_nonempty_string(document.get("calibration_id"), "$.calibration_id"),
        "judge": dict(judge),
        "case_count": len(cases),
        "labeler_agreement": {
            "cohens_kappa": kappa,
            "minimum_required": minimum_kappa,
        },
        "automatic_pass": {
            "predicted_pass": predicted_pass,
            "true_positive_pass": true_positive_pass,
            "precision": pass_precision,
            "minimum_required": minimum_precision,
        },
        "unresolved_adjudications": unresolved,
        "evaluation_errors": evaluation_errors,
        "checks": checks,
        "gate_passed": all(checks.values()),
    }


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CalibrationError("E_INPUT_READ", "$", "input is unreadable or invalid JSON") from error
    return _require_object(value, "$")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = calibrate(_read_json(args.input))
    except CalibrationError as error:
        print(json.dumps({"valid": False, "errors": [error.as_dict()]}, ensure_ascii=False), file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
