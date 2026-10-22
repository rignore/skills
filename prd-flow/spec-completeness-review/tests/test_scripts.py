"""스킬 스크립트 자기 시험. 실행: python3 -m unittest discover -s tests"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from check_trace import overlap_warnings, pass_errors, sha256, validate  # noqa: E402

PRD = """# 기능 PRD
## 4.5 인수 조건
- 승인 회신이 없으면 실행하지 않는다.
- 반려되면 실행하지 않는다.
"""
SPEC = """# 사양
## 5. 권한
### 5.1 승인 후 실행
승인 회신과 근거를 받은 뒤에만 실행하며, 반려나 보류이면 실행하지 않는다.
"""


def run(script: str, *args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=cwd, text=True, capture_output=True)


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "prd.md").write_text(PRD, encoding="utf-8")
        (self.root / "spec.md").write_text(SPEC, encoding="utf-8")
        self.trace = self.root / "trace.json"
        rows = [
            {"id": "PRD-001", "source_location": "4.5:L3-L3", "summary": "승인 회신이 없으면 실행하지 않는다",
             "target_locations": ["spec.md#5.1"], "verification_status": "unverified", "evidence": "5.1 첫 문장"},
            {"id": "PRD-002", "source_location": "4.5:L4-L4", "summary": "반려되면 실행하지 않는다",
             "target_locations": ["spec.md#5.1"], "verification_status": "unverified", "evidence": "5.1 뒷부분"},
        ]
        data = {
            "schema_version": 1,
            "metadata": {
                "mode": "initial",
                "machine_validation_limit": "기계 검사는 문장의 의미 동등성을 판정하지 못한다",
                "sources": [{"id": "prd", "path": "prd.md", "sha256": sha256(self.root / "prd.md")}],
                "id_families": {"PRD": "prd"},
                "active_target": {"path": "spec.md", "sha256": sha256(self.root / "spec.md"),
                                  "line_count": len(SPEC.splitlines())},
                "snapshots": [], "review_records": [], "criteria_rulings": [],
                "requirement_count": 2, "status_counts": {"unverified": 2}, "exclusion_count": 0,
            },
            "requirements": rows,
            "exclusions": [],
        }
        self.trace.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def data(self) -> dict:
        return json.loads(self.trace.read_text(encoding="utf-8"))

    def write(self, data: dict) -> None:
        self.trace.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def review(self, name: str, items: list[tuple[str, str]], **extra) -> Path:
        path = self.root / f"review-{name}.json"
        body = {"reviewer": name, "result": "PASS",
                "requirements": [{"id": i, "verdict": v, "reason": "근거"} for i, v in items]}
        body.update(extra)
        path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        return path


class CheckTraceTest(Fixture):
    def test_valid_trace_passes(self):
        self.assertEqual(validate(self.trace, self.root), [])

    def test_changed_source_fails(self):
        (self.root / "prd.md").write_text(PRD + "- 추가\n", encoding="utf-8")
        self.assertTrue(any("source 지문" in e for e in validate(self.trace, self.root)))

    def test_changed_target_fails(self):
        (self.root / "spec.md").write_text(SPEC + "추가\n", encoding="utf-8")
        self.assertTrue(any("active_target.sha256" in e for e in validate(self.trace, self.root)))

    def test_location_outside_section_fails(self):
        d = self.data(); d["requirements"][0]["source_location"] = "9.9:L3-L3"; self.write(d)
        self.assertTrue(any("절 9.9" in e for e in validate(self.trace, self.root)))

    def test_location_in_later_sibling_section_fails(self):
        (self.root / "prd.md").write_text("# PRD\n## 4.1 앞 절\n- a\n## 4.2 뒤 절\n- b\n", encoding="utf-8")
        d = self.data()
        d["metadata"]["sources"][0]["sha256"] = sha256(self.root / "prd.md")
        d["requirements"][0]["source_location"] = "4.1:L5-L5"
        d["requirements"][1]["source_location"] = "4.2:L5-L5"
        self.write(d)
        errors = validate(self.trace, self.root)
        self.assertTrue(any("requirements[1]" in e and "4.1 안에" in e for e in errors), errors)
        self.assertFalse(any("requirements[2]" in e for e in errors), errors)

    def test_exclusion_location_is_checked(self):
        d = self.data()
        d["exclusions"] = [{"id": "EX-01", "source_location": "99 없는절:L500-L900", "category": "c", "summary": "x", "evidence": "y"}]
        d["metadata"]["exclusion_count"] = 1
        self.write(d)
        self.assertTrue(any("exclusions[1].source_location" in e for e in validate(self.trace, self.root)))

    def test_revision_disposition_counts_checked(self):
        d = self.data(); d["metadata"]["mode"] = "revision"
        for r in d["requirements"]:
            r["disposition"] = "preserved"
        d["metadata"]["disposition_counts"] = {"missing": 99}
        self.write(d)
        self.assertTrue(any("disposition_counts" in e for e in validate(self.trace, self.root)))

    def test_missing_target_section_fails(self):
        d = self.data(); d["requirements"][0]["target_locations"] = ["spec.md#7.2"]; self.write(d)
        self.assertTrue(any("대상 절이 없다" in e for e in validate(self.trace, self.root)))

    def test_id_gap_fails(self):
        d = self.data(); d["requirements"][1]["id"] = "PRD-003"; self.write(d)
        self.assertTrue(any("연속 번호" in e for e in validate(self.trace, self.root)))

    def test_hand_written_count_mismatch_fails(self):
        d = self.data(); d["metadata"]["requirement_count"] = 3; self.write(d)
        self.assertTrue(any("requirement_count" in e for e in validate(self.trace, self.root)))

    def test_revision_requires_baseline_snapshot(self):
        d = self.data(); d["metadata"]["mode"] = "revision"
        for r in d["requirements"]:
            r["disposition"] = "preserved"
        self.write(d)
        self.assertTrue(any("차수 0" in e for e in validate(self.trace, self.root)))

    def test_exclusion_overlapping_requirement_warns(self):
        d = self.data()
        d["exclusions"] = [{"id": "EX-01", "source_location": "4.5:L3-L3", "category": "작성 경위",
                            "summary": "x", "evidence": "y"}]
        d["metadata"]["exclusion_count"] = 1
        self.write(d)
        self.assertEqual(validate(self.trace, self.root), [])
        self.assertTrue(any("같은 원문 줄" in w for w in overlap_warnings(self.trace, self.root)))

    def test_exclusion_with_overlap_reason_passes(self):
        d = self.data()
        d["exclusions"] = [{"id": "EX-01", "source_location": "4.5:L3-L3", "category": "작성 경위",
                            "summary": "x", "evidence": "y", "overlap_reason": "같은 줄의 작성 날짜만 뺐다"}]
        d["metadata"]["exclusion_count"] = 1
        self.write(d)
        self.assertEqual(validate(self.trace, self.root), [])
        self.assertEqual(overlap_warnings(self.trace, self.root), [])

    def test_row_source_id_overrides_family(self):
        (self.root / "other.md").write_text("# 다른 원문\n## 2.1 규칙\n- 요구\n", encoding="utf-8")
        d = self.data()
        d["metadata"]["sources"].append({"id": "other", "path": "other.md", "sha256": sha256(self.root / "other.md")})
        d["requirements"][1]["source_id"] = "other"
        d["requirements"][1]["source_location"] = "2.1:L3-L3"
        self.write(d)
        self.assertEqual(validate(self.trace, self.root), [])

    def test_location_end_crossing_sections_fails(self):
        (self.root / "prd.md").write_text("# PRD\n## 4.1 앞\n- a\n## 4.2 뒤\n- b\n", encoding="utf-8")
        d = self.data(); d["metadata"]["sources"][0]["sha256"] = sha256(self.root / "prd.md")
        d["requirements"][0]["source_location"] = "4.1:L3-L5"; d["requirements"][1]["source_location"] = "4.2:L5-L5"
        self.write(d)
        self.assertTrue(any("L3-L5" in e for e in validate(self.trace, self.root)))

    def test_hash_in_code_fence_is_not_heading(self):
        from check_trace import line_in_section
        lines = ["# T", "## 1. A", "```", "# not heading", "```", "x"]
        self.assertTrue(line_in_section(lines, 6, "1"))
        self.assertTrue(line_in_section(["# T", "## 1. A", "~~~", "# no", "~~~", "x"], 6, "1"))
        self.assertTrue(line_in_section(["# T", "## 1. A", "````", "```", "# no", "```", "````", "x"], 8, "1"))


class FreezeAndRecordTest(Fixture):
    def freeze(self) -> None:
        out = run("freeze_snapshot.py", "trace.json", "--history-dir", "history", "--state", "초안", cwd=self.root)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_freeze_makes_readonly_copy_and_trace_stays_valid(self):
        self.freeze()
        snap = self.data()["metadata"]["snapshots"][0]
        path = self.root / snap["path"]
        self.assertEqual(snap["round"], 1)
        self.assertFalse(path.stat().st_mode & 0o222)
        self.assertEqual(validate(self.trace, self.root), [])

    def test_freeze_refuses_unchanged_target(self):
        self.freeze()
        out = run("freeze_snapshot.py", "trace.json", "--history-dir", "history", "--state", "다시", cwd=self.root)
        self.assertNotEqual(out.returncode, 0)

    def test_tampered_snapshot_fails(self):
        self.freeze()
        path = self.root / self.data()["metadata"]["snapshots"][0]["path"]
        path.chmod(0o644); path.write_text("변조", encoding="utf-8")
        self.assertTrue(any("불변 사본 지문" in e for e in validate(self.trace, self.root)))

    def rec(self, *reviews, rnd="1", out="records/r1.json"):
        return run("record_round.py", "trace.json", "--round", rnd, "--reviews", *map(str, reviews), "--out", out, cwd=self.root)

    def edit_and_freeze(self, text="추가 문장\n"):
        spec = self.root / "spec.md"
        spec.write_text(spec.read_text(encoding="utf-8") + text, encoding="utf-8")
        out = run("freeze_snapshot.py", "trace.json", "--history-dir", "history", "--state", "수정", cwd=self.root)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_stale_round_is_refused(self):
        self.freeze(); self.edit_and_freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        out = self.rec(a, rnd="1")
        self.assertEqual(out.returncode, 1); self.assertIn("가장 최근", out.stderr)

    def test_round_zero_is_refused(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        self.assertEqual(self.rec(a, rnd="0").returncode, 1)

    def test_same_round_cannot_be_recorded_twice(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "FAIL")])
        self.assertEqual(self.rec(a).returncode, 2)
        b = self.review("B", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        self.assertEqual(self.rec(b, out="records/r1b.json").returncode, 1)
        self.assertEqual(self.rec(b).returncode, 1)
        self.assertFalse((self.root / "records/r1.json").stat().st_mode & 0o222)

    def test_edit_after_pass_fails_require_pass(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        self.assertEqual(self.rec(a).returncode, 0)
        self.assertEqual(pass_errors(self.trace), [])
        self.edit_and_freeze("금지 삭제\n")
        self.assertEqual(validate(self.trace, self.root), [])
        self.assertTrue(any("통과 뒤 사양이 바뀌었다" in e for e in pass_errors(self.trace)))

    def test_source_conflict_row_blocks_pass_and_keeps_status(self):
        d = self.data(); d["requirements"][1]["verification_status"] = "source_conflict_pending"
        d["requirements"][1]["pending_reason"] = "티켓과 충돌"; d["metadata"]["status_counts"] = {"unverified": 1, "source_conflict_pending": 1}
        self.write(d); self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        self.assertEqual(self.rec(a).returncode, 2)
        self.assertEqual(self.data()["requirements"][1]["verification_status"], "source_conflict_pending")

    def test_approved_removal_is_not_reverted_by_fail(self):
        d = self.data(); d["requirements"][1]["verification_status"] = "approved_removal"
        d["requirements"][1]["evidence"] = "2026-09-20 기획자 결정으로 삭제"; d["requirements"][1]["target_locations"] = []
        d["metadata"]["status_counts"] = {"unverified": 1, "approved_removal": 1}
        d["metadata"]["criteria_rulings"] = [{"decided_at": "2026-09-20", "decided_by": "기획자", "affects": ["PRD-002"],
                                              "ruling": "PRD-002는 이 사양에서 뺀다", "basis": "범위 조정", "approved_by": "기획자"}]
        self.write(d); self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "FAIL")])
        out = self.rec(a)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("이견 1", out.stdout)
        self.assertEqual(self.data()["requirements"][1]["verification_status"], "approved_removal")

    def test_destination_pending_pass_becomes_verified(self):
        (self.root / "dest.md").write_text("# 다른 사양\n## 3. 기록\n반려되면 실행하지 않는다.\n", encoding="utf-8")
        d = self.data(); d["requirements"][1]["verification_status"] = "destination_pending"
        d["requirements"][1]["destination"] = "dest.md#3"
        d["metadata"]["criteria_rulings"] = [{"decided_at": "2026-09-20", "decided_by": "기획자", "affects": ["PRD-002"],
                                              "ruling": "PRD-002는 다른 사양으로 옮긴다", "basis": "소유 문서", "approved_by": "기획자"}]
        d["requirements"][1]["pending_reason"] = "다른 사양으로 옮김"; d["metadata"]["status_counts"] = {"unverified": 1, "destination_pending": 1}
        self.write(d); self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        self.assertEqual(self.rec(a).returncode, 0)
        self.assertEqual(self.data()["requirements"][1]["verification_status"], "destination_verified")

    def test_unknown_id_is_refused(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS"), ("PRD-999", "FAIL")])
        out = self.rec(a)
        self.assertEqual(out.returncode, 1); self.assertIn("PRD-999", out.stderr)

    def test_exclusion_fail_is_recorded_on_row(self):
        d = self.data()
        d["exclusions"] = [{"id": "EX-01", "source_location": "4.5:L4-L4", "category": "c", "summary": "x", "evidence": "y", "overlap_reason": "o"}]
        d["metadata"]["exclusion_count"] = 1
        self.write(d); self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")], exclusions=[{"id": "EX-01", "verdict": "FAIL", "reason": "권한성 요구"}])
        self.assertEqual(self.rec(a).returncode, 2)
        d = self.data()
        self.assertEqual(d["exclusions"][0]["review_verdict"], "FAIL")
        self.assertEqual(d["metadata"]["review_records"][-1]["exclusion_fail"], 1)

    def test_out_outside_root_writes_nothing(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        out = self.rec(a, out="../outside.json")
        self.assertEqual(out.returncode, 1)
        self.assertFalse((self.root.parent / "outside.json").exists())

    def test_refresh_then_check_passes_before_first_freeze(self):
        d = self.data(); d["metadata"]["active_target"] = {"path": "spec.md"}
        d["metadata"].pop("requirement_count"); d["metadata"].pop("status_counts"); self.write(d)
        self.assertNotEqual(validate(self.trace, self.root), [])
        out = run("refresh_trace.py", "trace.json", cwd=self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(validate(self.trace, self.root), [])

    def test_reviewer_view_hides_author_claims(self):
        out = run("reviewer_view.py", "trace.json", "--out", "records/view.json", cwd=self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        view = json.loads((self.root / "records/view.json").read_text(encoding="utf-8"))
        self.assertNotIn("evidence", view["requirements"][0])
        self.assertIn("summary", view["requirements"][0])

    def test_record_requires_snapshot(self):
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        out = run("record_round.py", "trace.json", "--round", "1", "--reviews", str(a), "--out", "r1.json", cwd=self.root)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("불변 사본", out.stderr)

    def test_split_review_passes_and_updates_status(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS")]); b = self.review("B", [("PRD-002", "PASS")])
        out = run("record_round.py", "trace.json", "--round", "1", "--reviews", str(a), str(b), "--out", "r1.json", cwd=self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        d = self.data()
        self.assertEqual(d["metadata"]["status_counts"], {"verified_equivalent": 2})
        self.assertEqual(validate(self.trace, self.root), [])

    def test_uncovered_row_is_rejected(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS")])
        out = run("record_round.py", "trace.json", "--round", "1", "--reviews", str(a), "--out", "r1.json", cwd=self.root)
        self.assertEqual(out.returncode, 1)
        self.assertIn("PRD-002", out.stderr)

    def test_double_coverage_is_rejected(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")]); b = self.review("B", [("PRD-002", "PASS")])
        out = run("record_round.py", "trace.json", "--round", "1", "--reviews", str(a), str(b), "--out", "r1.json", cwd=self.root)
        self.assertEqual(out.returncode, 1)

    def test_unproven_contradiction_is_discarded(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")],
                        contradictions=[{"rule_1": "5.1", "rule_2": "4.5", "scenario": ""}])
        out = run("record_round.py", "trace.json", "--round", "1", "--reviews", str(a), "--out", "r1.json", cwd=self.root)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("버린 것 1", out.stdout)

    def test_proven_contradiction_fails_round(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")],
                        contradictions=[{"scenario": "반려 회신 뒤 재요청 없음", "rule_1": "5.1 실행 금지", "rule_2": "x 실행 허용"}])
        out = run("record_round.py", "trace.json", "--round", "1", "--reviews", str(a), "--out", "r1.json", cwd=self.root)
        self.assertEqual(out.returncode, 2)

    def test_failed_row_becomes_restore_required(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "FAIL")])
        out = run("record_round.py", "trace.json", "--round", "1", "--reviews", str(a), "--out", "r1.json", cwd=self.root)
        self.assertEqual(out.returncode, 2)
        row = self.data()["requirements"][1]
        self.assertEqual(row["verification_status"], "restore_required")
        self.assertIn("차수 1", row["pending_reason"])

    def test_internal_contradictions_field_is_counted(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")],
                        internal_contradictions=[{"scenario": "s", "rule_1": "r1", "rule_2": "r2"}])
        out = run("record_round.py", "trace.json", "--round", "1", "--reviews", str(a), "--out", "r1.json", cwd=self.root)
        self.assertEqual(out.returncode, 2)

    def test_approved_removal_without_ruling_fails_check(self):
        d = self.data(); d["requirements"][1]["verification_status"] = "approved_removal"
        d["requirements"][1]["evidence"] = "결정"; d["requirements"][1]["target_locations"] = []
        d["metadata"]["status_counts"] = {"unverified": 1, "approved_removal": 1}
        self.write(d)
        self.assertTrue(any("사람의 결정" in e for e in validate(self.trace, self.root)))

    def test_destination_fail_blocks(self):
        (self.root / "dest.md").write_text("# 다른 사양\n## 3. 기록\n반려되면 실행하지 않는다.\n", encoding="utf-8")
        d = self.data(); d["requirements"][1]["verification_status"] = "destination_pending"
        d["requirements"][1]["destination"] = "dest.md#3"
        d["metadata"]["criteria_rulings"] = [{"decided_at": "2026-09-20", "decided_by": "기획자", "affects": ["PRD-002"],
                                              "ruling": "PRD-002는 다른 사양으로 옮긴다", "basis": "소유 문서", "approved_by": "기획자"}]
        d["requirements"][1]["pending_reason"] = "다른 사양"; d["metadata"]["status_counts"] = {"unverified": 1, "destination_pending": 1}
        self.write(d); self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "FAIL")])
        out = self.rec(a)
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertIn("목적지 미확인 1", out.stdout)

    def test_destination_without_ruling_or_pointing_to_source_fails(self):
        d = self.data(); d["requirements"][1]["verification_status"] = "destination_pending"
        d["requirements"][1]["pending_reason"] = "x"; d["requirements"][1]["destination"] = "prd.md#4.5"
        d["metadata"]["status_counts"] = {"unverified": 1, "destination_pending": 1}
        self.write(d)
        errors = validate(self.trace, self.root)
        self.assertTrue(any("사람의 결정" in e for e in errors), errors)
        self.assertTrue(any("목적지는 원문" in e for e in errors), errors)

    def test_carry_over_refused_when_source_changed(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        self.assertEqual(self.rec(a).returncode, 0)
        (self.root / "prd.md").write_text(PRD.replace("반려되면", "반려·취소되면"), encoding="utf-8")
        d = self.data(); d["metadata"]["sources"][0]["sha256"] = sha256(self.root / "prd.md"); self.write(d)
        spec = self.root / "spec.md"; spec.write_text(spec.read_text(encoding="utf-8").replace("실행하지 않는다.", "실행하지 않는다. "), encoding="utf-8")
        run("freeze_snapshot.py", "trace.json", "--history-dir", "history", "--state", "s", cwd=self.root)
        b = self.review("B", [("PRD-001", "PASS")])
        out = run("record_round.py", "trace.json", "--round", "2", "--reviews", str(b), "--out", "records/r2.json", "--carry-over", cwd=self.root)
        self.assertEqual(out.returncode, 1, out.stdout + out.stderr)

    def test_carry_over_refused_when_unmapped_lines_change(self):
        (self.root / "spec.md").write_text(SPEC + "## 6. 기록\n기록한다.\n", encoding="utf-8")
        d = self.data(); d["requirements"][1]["target_locations"] = ["spec.md#6"]; self.write(d)
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        self.assertEqual(self.rec(a).returncode, 0)
        spec = self.root / "spec.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("반려나 보류이면", "반려·보류·무응답이면") + "## 9. 부록\n반려되어도 긴급 시 재가동할 수 있다.\n", encoding="utf-8")
        run("freeze_snapshot.py", "trace.json", "--history-dir", "history", "--state", "s", cwd=self.root)
        b = self.review("B", [("PRD-001", "PASS")])
        out = run("record_round.py", "trace.json", "--round", "2", "--reviews", str(b), "--out", "records/r2.json", "--carry-over", cwd=self.root)
        self.assertEqual(out.returncode, 1, out.stdout + out.stderr)

    def test_carry_over_refused_with_zero_verdicts(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        self.assertEqual(self.rec(a).returncode, 0)
        self.edit_and_freeze("x\n")
        empty = self.review("B", [])
        out = run("record_round.py", "trace.json", "--round", "2", "--reviews", str(empty), "--out", "records/r2.json", "--carry-over", cwd=self.root)
        self.assertEqual(out.returncode, 1)

    def test_refreeze_same_spec_after_criteria_change(self):
        self.freeze()
        out = run("freeze_snapshot.py", "trace.json", "--history-dir", "history", "--state", "기준만", "--criteria-changed", cwd=self.root)
        self.assertEqual(out.returncode, 1)
        d = self.data(); d["metadata"]["criteria_rulings"] = [{"decided_at": "2026-09-26", "decided_by": "기획자", "affects": [], "ruling": "r", "basis": "b"}]
        self.write(d)
        out = run("freeze_snapshot.py", "trace.json", "--history-dir", "history", "--state", "기준만", "--criteria-changed", cwd=self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.data()["metadata"]["snapshots"][-1]["round"], 2)

    def test_carry_over_for_unchanged_sections(self):
        (self.root / "spec.md").write_text(SPEC + "## 6. 기록\n기록한다.\n", encoding="utf-8")
        d = self.data(); d["requirements"][1]["target_locations"] = ["spec.md#6"]; self.write(d)
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        self.assertEqual(self.rec(a).returncode, 0)
        spec = self.root / "spec.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("반려나 보류이면", "반려·보류·무응답이면"), encoding="utf-8")
        out = run("freeze_snapshot.py", "trace.json", "--history-dir", "history", "--state", "5.1만 고침", cwd=self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        b = self.review("B", [("PRD-001", "PASS")])
        out = run("record_round.py", "trace.json", "--round", "2", "--reviews", str(b), "--out", "records/r2.json", "--carry-over", cwd=self.root)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("이어받음 1", out.stdout)

    def test_carry_over_refuses_changed_section(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        self.assertEqual(self.rec(a).returncode, 0)
        self.edit_and_freeze("5.1에 붙은 문장\n")
        b = self.review("B", [("PRD-001", "PASS")])
        out = run("record_round.py", "trace.json", "--round", "2", "--reviews", str(b), "--out", "records/r2.json", "--carry-over", cwd=self.root)
        self.assertEqual(out.returncode, 1)
        self.assertIn("PRD-002", out.stderr)

    def test_reviewer_view_keeps_human_status(self):
        (self.root / "dest.md").write_text("# 다른 사양\n## 3. 기록\n반려되면 실행하지 않는다.\n", encoding="utf-8")
        d = self.data(); d["requirements"][1]["verification_status"] = "destination_pending"
        d["requirements"][1]["destination"] = "dest.md#3"
        d["metadata"]["criteria_rulings"] = [{"decided_at": "2026-09-20", "decided_by": "기획자", "affects": ["PRD-002"],
                                              "ruling": "PRD-002는 다른 사양으로 옮긴다", "basis": "소유 문서", "approved_by": "기획자"}]
        d["requirements"][1]["pending_reason"] = "x"; d["metadata"]["status_counts"] = {"unverified": 1, "destination_pending": 1}
        self.write(d)
        run("reviewer_view.py", "trace.json", "--out", "records/view.json", cwd=self.root)
        view = json.loads((self.root / "records/view.json").read_text(encoding="utf-8"))
        self.assertNotIn("verification_status", view["requirements"][0])
        self.assertEqual(view["requirements"][1]["verification_status"], "destination_pending")

    def test_author_as_decider_is_refused(self):
        d = self.data(); d["requirements"][1]["verification_status"] = "approved_removal"; d["requirements"][1]["target_locations"] = []
        d["metadata"]["status_counts"] = {"unverified": 1, "approved_removal": 1}
        d["metadata"]["criteria_rulings"] = [{"decided_at": "2026-09-26", "decided_by": "기획자", "affects": ["PRD-002"],
                                              "ruling": "r", "basis": "b", "approved_by": "작성자"}]
        self.write(d)
        self.assertTrue(any("사람의 결정" in e for e in validate(self.trace, self.root)))

    def test_criteria_changed_refused_after_only_recording(self):
        self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "FAIL")])
        self.assertEqual(self.rec(a).returncode, 2)
        out = run("freeze_snapshot.py", "trace.json", "--history-dir", "history", "--state", "같음", "--criteria-changed", cwd=self.root)
        self.assertEqual(out.returncode, 1, out.stdout)

    def test_destination_without_target_doc_stays_pending(self):
        d = self.data(); d["requirements"][1]["verification_status"] = "destination_pending"; d["requirements"][1]["pending_reason"] = "x"
        d["metadata"]["status_counts"] = {"unverified": 1, "destination_pending": 1}
        d["metadata"]["criteria_rulings"] = [{"decided_at": "2026-09-26", "decided_by": "기획자", "affects": ["PRD-002"],
                                              "ruling": "옮긴다", "basis": "결정 로그", "approved_by": "기획자"}]
        self.write(d); self.freeze()
        a = self.review("A", [("PRD-001", "PASS"), ("PRD-002", "PASS")])
        self.assertEqual(self.rec(a).returncode, 0)
        self.assertEqual(self.data()["requirements"][1]["verification_status"], "destination_pending")


if __name__ == "__main__":
    unittest.main()
