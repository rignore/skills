#!/usr/bin/env python3
"""격리 검토자들의 판정 JSON을 합쳐 회차 결과를 판정하고 기록한다.

거부하는 경우(종료 코드 1, 아무것도 쓰지 않는다):
- 추적표가 기계 검사를 통과하지 못한다.
- --round가 0(개정 전 기준본)이거나, 가장 최근에 얼린 차수가 아니거나, 그 사본의 지문이 현재 대상 지문과 다르다.
- 같은 차수를 이미 기록했거나 --out 파일이 이미 있다. 판정 기록은 덮어쓰지 않는다.
- 추적표에 없는 id, 제외 id를 requirements에 넣은 것처럼 배열을 잘못 고른 id, 판정값 오류가 있다.
- 행을 아무도 판정하지 않았거나 두 검토자가 겹쳐 판정했다.
- --carry-over(고친 범위만 재검토)를 줬는데 아래 조건을 하나라도 어긴다. 이 조건을 모두 지킨 행만 직전 PASS를 이어받는다.
  · 이번 회차 검토자가 한 행 이상 판정했다.
  · 직전 기록 이후 원문 지문이 하나도 바뀌지 않았다.
  · 그 행의 요약·원문 위치·대상 위치가 직전 기록 때와 같다.
  · 그 행의 대상 위치가 모두 이 사양 안에 있고, 그 절 본문이 직전 사본과 글자까지 같다.
  · 직전 사본 대비 바뀐 줄이 모두, 이번 회차 검토자가 판정한 행의 대상 절 안에 있다. 어떤 행도 가리키지 않는 곳이 바뀌면
    이어받기를 거부하고 전체 재검토를 요구한다.
  이어받은 행은 기록에 carried_over로 남는다.

판정 규칙(검토자 출력 형식은 references/reviewer-prompt.md):
- 모순(contradictions 또는 internal_contradictions)은 scenario·rule_1·rule_2가 모두 있어야 센다.
  하나라도 없으면 '증명 없는 모순'으로 버리고 버린 수만 남긴다.
- PASS는 요구사항 FAIL 0, 제외 FAIL 0, 추적표 밖 요구 0, 증명된 모순 0, 규칙 위반 0,
  사람 결정 대기 행(source_conflict_pending) 0일 때뿐이다. 목적지 확인 대기 행이 목적지에서 확인되지 않은 FAIL도 막는다.
  승인된 삭제(approved_removal)에 대한 검토자 FAIL만 통과를 막지 않고 "이견"으로 따로 보고한다. 승인된 삭제는
  검사기가 판정 기준 기록에 결정한 사람(approved_by)을 요구하기 때문이다.
- 행 상태 갱신: 사람 결정으로 정해진 상태(approved_removal, source_conflict_pending)는 판정으로 바꾸지 않는다.
  destination_pending은 PASS면 destination_verified가 된다. 그 밖의 행은 PASS면 verified_equivalent,
  FAIL이면 restore_required(사유는 검토자 이유)가 된다. 제외 행에는 review_verdict와 review_reason을 적는다.
- 기준 이의(criteria_objections)는 통과를 막지 않고 기록만 한다. 받아들이면 사람이 criteria_rulings에 적는다.

  record_round.py TRACE --root DIR --round N --reviews a.json b.json --out records/round-N.json [--purpose "..."]
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import stat
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load, recount, save  # noqa: E402
from check_trace import section_span, section_text, validate  # noqa: E402

VERDICTS = {"PASS", "FAIL", "OUT_OF_SCOPE"}
HUMAN_DECIDED = {"approved_removal", "source_conflict_pending"}


def proven(item: dict) -> bool:
    return all(isinstance(item.get(k), str) and item[k].strip() for k in ("scenario", "rule_1", "rule_2"))


def row_fingerprint(row: dict) -> str:
    keys = ("summary", "source_location", "source_id", "target_locations", "category")
    payload = json.dumps({k: row.get(k) for k in keys}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fingerprints(data: dict) -> dict:
    meta = data["metadata"]
    return {
        "sources": {s_.get("id"): s_.get("sha256") for s_ in meta.get("sources", [])},
        "rows": {r["id"]: row_fingerprint(r) for r in data.get("requirements", []) + data.get("exclusions", [])},
    }


def carry_over(root: Path, data: dict, ids: list[str], rnd: int, judged: set[str]) -> tuple[list[tuple[str, dict]], list[str]]:
    """고친 범위만 재검토할 때, 조건을 모두 지킨 행만 직전 PASS를 이어받는다. 조건은 모듈 설명에 있다."""
    meta = data["metadata"]
    records = [r for r in meta.get("review_records", []) if r.get("round", 0) < rnd]
    snaps = {s_.get("round"): s_ for s_ in meta.get("snapshots", [])}
    if not records:
        return [], ids
    prev_rec = max(records, key=lambda r: r["round"])
    prev_snap, cur_snap = snaps.get(prev_rec["round"]), snaps.get(rnd)
    prev_fp = prev_rec.get("fingerprints")
    now_fp = fingerprints(data)
    if not prev_snap or not cur_snap or not prev_fp or prev_fp.get("sources") != now_fp["sources"]:
        return [], ids  # 원문이 바뀌었거나 직전 기록에 지문이 없다
    prev_lines = (root / prev_snap["path"]).read_text(encoding="utf-8").splitlines()
    cur_text = (root / cur_snap["path"]).read_text(encoding="utf-8")
    cur_lines = cur_text.splitlines()
    prev_text = "\n".join(prev_lines)
    target_path = meta["active_target"]["path"]
    rows = {r["id"]: r for r in data["requirements"] + data.get("exclusions", [])}

    # 바뀐 줄이 모두 이번에 판정한 행의 대상 절 안에 있어야 한다.
    judged_spans: list[tuple[int, int]] = []
    for iid in judged:
        for loc in rows.get(iid, {}).get("target_locations", []) or []:
            path, section = loc.rsplit("#", 1)
            if path == target_path:
                judged_spans.extend(section_span(cur_lines, section))
    changed: list[int] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=prev_lines, b=cur_lines, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        changed.extend(range(j1 + 1, j2 + 1) if j2 > j1 else [max(j1, 1)])
    if any(not any(a <= n <= b for a, b in judged_spans) for n in changed):
        return [], ids

    prev_record = load(root / prev_rec["path"])
    prev_pass = {
        item["id"]
        for review in prev_record.get("reviews", [])
        for item in review.get("requirements", []) + review.get("exclusions", [])
        if item.get("verdict") == "PASS"
    } | set(prev_record.get("summary", {}).get("carried_over", []))
    carried, refused = [], []
    for iid in ids:
        row = rows.get(iid)
        ok = row is not None and iid in prev_pass and prev_fp["rows"].get(iid) == now_fp["rows"].get(iid)
        targets = (row or {}).get("target_locations")
        if ok and targets:
            for loc in targets:
                path, section = loc.rsplit("#", 1)
                before, after = section_text(prev_text, section), section_text(cur_text, section)
                if path != target_path or before is None or before != after:
                    ok = False
                    break
        elif ok and "target_locations" in (row or {}):
            ok = False  # 대상 위치가 빈 요구사항 행은 매번 검토자가 본다
        if ok:
            carried.append((iid, {"id": iid, "verdict": "PASS", "reason": f"차수 {prev_rec['round']} 판정 이어받음", "from_round": prev_rec["round"]}))
        else:
            refused.append(iid)
    return carried, refused


def refuse(messages: list[str]) -> int:
    print("기록 거부:", file=sys.stderr)
    for message in messages:
        print(f"- {message}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--reviews", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True, help="--root 기준 상대 경로")
    parser.add_argument("--purpose", default="")
    parser.add_argument("--carry-over", action="store_true", help="고친 범위만 재검토할 때, 바뀌지 않은 행의 직전 PASS를 이어받는다")
    args = parser.parse_args()

    root = args.root.resolve()
    trace = args.trace.resolve()
    problems = validate(trace, root)
    if problems:
        return refuse(["추적표가 기계 검사를 통과하지 못한다. check_trace.py로 먼저 고친다."] + problems[:10])

    out = (root / args.out).resolve()
    try:
        out_rel = str(out.relative_to(root))
    except ValueError:
        return refuse([f"--out이 --root 밖을 가리킨다: {args.out}"])
    if out.exists():
        return refuse([f"기록 파일이 이미 있다: {out_rel}. 판정 기록은 덮어쓰지 않는다"])

    data = load(trace)
    meta = data["metadata"]
    snaps = meta.get("snapshots", [])
    if args.round <= 0:
        return refuse(["차수 0은 개정 전 기준본이다. 검토 대상 차수는 1 이상이다"])
    if not any(s.get("round", 0) >= 1 for s in snaps):
        return refuse(["검토 대상의 불변 사본이 없다. freeze_snapshot.py로 먼저 얼린다"])
    latest = max((s.get("round", 0) for s in snaps), default=0)
    if args.round != latest:
        return refuse([f"차수 {args.round}는 가장 최근에 얼린 차수({latest})가 아니다. 낡은 사본으로 판정을 기록하지 않는다"])
    snap = next(s for s in snaps if s.get("round") == args.round)
    if snap.get("sha256") != meta["active_target"].get("sha256"):
        return refuse(["차수 사본의 지문이 현재 대상 지문과 다르다. 대상을 다시 얼린 뒤 검토한다"])
    if any(r.get("round") == args.round for r in meta.get("review_records", [])):
        return refuse([f"차수 {args.round}는 이미 기록됐다. 다시 검토하려면 새로 얼려 다음 차수로 돈다"])

    reviews = [load(p) for p in args.reviews]
    row_ids = [r["id"] for r in data["requirements"]]
    ex_ids = [e["id"] for e in data.get("exclusions", [])]
    owner: dict[str, str] = {}
    verdicts: dict[str, dict] = {}
    for review in reviews:
        name = review.get("reviewer", "?")
        for key, valid in (("requirements", set(row_ids)), ("exclusions", set(ex_ids))):
            for item in review.get(key, []):
                iid = item.get("id")
                if iid not in valid:
                    problems.append(f"검토자 {name}의 {key}에 추적표에 없는 id가 있다: {iid}")
                    continue
                if item.get("verdict") not in VERDICTS:
                    problems.append(f"검토자 {name}의 {iid} 판정값 오류: {item.get('verdict')}")
                    continue
                if item["verdict"] == "OUT_OF_SCOPE":
                    continue
                if iid in owner:
                    problems.append(f"{iid}를 검토자 {owner[iid]}와 {name}가 둘 다 판정했다")
                    continue
                owner[iid] = name
                verdicts[iid] = item
    carried: list[str] = []
    if args.carry_over:
        if not owner:
            return refuse(["--carry-over를 줬지만 이번 회차 검토자가 판정한 행이 하나도 없다. 고친 범위를 맡은 검토자의 판정이 필요하다"])
        carried, not_carryable = carry_over(root, data, [i for i in row_ids + ex_ids if i not in owner], args.round, set(owner))
        for iid, prev in carried:
            owner[iid] = f"차수 {prev['from_round']} 이어받음"
            verdicts[iid] = prev
        carried = [iid for iid, _ in carried]
        if not_carryable:
            problems.append("직전 판정을 이어받을 수 없는 행(직전 PASS가 아니거나 대상 절이 바뀜): " + ", ".join(not_carryable[:20]))
    missing = [i for i in row_ids + ex_ids if i not in owner]
    if missing:
        problems.append("아무도 판정하지 않은 행: " + ", ".join(missing[:20]) + (" …" if len(missing) > 20 else ""))
    if problems:
        return refuse(problems)

    req_fail = [i for i in row_ids if verdicts[i]["verdict"] == "FAIL"]
    ex_fail = [i for i in ex_ids if verdicts[i]["verdict"] == "FAIL"]
    outside = [f for r in reviews for f in r.get("outside_trace_findings", [])]
    contradictions = [c for r in reviews for c in r.get("contradictions", []) + r.get("internal_contradictions", [])]
    proven_c = [c for c in contradictions if proven(c)]
    unproven_c = [c for c in contradictions if not proven(c)]
    violations = [v for r in reviews for v in r.get("rule_violations", [])]
    objections = [o for r in reviews for o in r.get("criteria_objections", [])]
    awaiting = [r["id"] for r in data["requirements"] if r.get("verification_status") == "source_conflict_pending"]
    disputed_removals = [
        r["id"] for r in data["requirements"]
        if r.get("verification_status") == "approved_removal" and verdicts[r["id"]]["verdict"] == "FAIL"
    ]
    destination_unconfirmed = [
        r["id"] for r in data["requirements"]
        if r.get("verification_status") == "destination_pending" and verdicts[r["id"]]["verdict"] == "FAIL"
    ]
    blocking_req_fail = [i for i in req_fail if i not in disputed_removals and i not in awaiting]
    result = "PASS" if not (blocking_req_fail or ex_fail or outside or proven_c or violations or awaiting) else "FAIL"

    for row in data["requirements"]:
        v = verdicts[row["id"]]
        status = row.get("verification_status")
        if status in HUMAN_DECIDED:
            continue
        if v["verdict"] == "PASS" and status == "destination_pending" and not row.get("destination"):
            # 목적지가 정해지지 않았다. 옮겨진 곳이 없으므로 확인 상태로 올리지 않고 임시 경계 확인만 남긴다.
            row["pending_reason"] = f"차수 {args.round}: 목적지 미정, 이 사양의 임시 경계로 보존됨을 확인"
        elif v["verdict"] == "PASS":
            row["verification_status"] = "destination_verified" if status == "destination_pending" else "verified_equivalent"
            row.pop("pending_reason", None)
        elif status == "destination_pending":
            row["pending_reason"] = f"차수 {args.round} 검토자 {owner[row['id']]}: 목적지 확인 실패 — {v.get('reason', '')}"
        else:
            row["verification_status"] = "restore_required"
            row["pending_reason"] = f"차수 {args.round} 검토자 {owner[row['id']]}: {v.get('reason', '')}"
    for item in data.get("exclusions", []):
        v = verdicts[item["id"]]
        item["review_verdict"] = v["verdict"]
        item["review_reason"] = f"차수 {args.round} 검토자 {owner[item['id']]}: {v.get('reason', '')}"

    record = {
        "schema_version": 1,
        "round": args.round,
        "reviewed_at": date.today().isoformat(),
        "result": result,
        "purpose": args.purpose,
        "subject": {k: snap[k] for k in ("path", "sha256", "line_count", "state") if k in snap},
        "summary": {
            "requirements": len(row_ids),
            "requirement_fail": blocking_req_fail,
            "exclusion_fail": ex_fail,
            "outside_trace_findings": len(outside),
            "proven_contradictions": len(proven_c),
            "unproven_contradictions_discarded": len(unproven_c),
            "rule_violations": len(violations),
            "awaiting_human_decision": awaiting,
            "disputed_approved_removals": disputed_removals,
            "destination_unconfirmed": destination_unconfirmed,
            "carried_over": carried,
            "criteria_objections": len(objections),
            "by_reviewer": {r.get("reviewer", "?"): r.get("result") for r in reviews},
        },
        "reviews": reviews,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    save(out, record)
    os.chmod(out, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 판정 기록도 고치지 않는다
    meta.setdefault("review_records", []).append({
        "round": args.round,
        "path": out_rel,
        "result": result,
        "subject_sha256": snap["sha256"],
        "fingerprints": fingerprints(data),
        "requirement_fail": len(blocking_req_fail),
        "exclusion_fail": len(ex_fail),
    })
    recount(data)
    save(trace, data)
    print(
        f"차수 {args.round} {result}: 요구사항 실패 {len(blocking_req_fail)}, 제외 실패 {len(ex_fail)}, "
        f"추적표 밖 {len(outside)}, 증명된 모순 {len(proven_c)}(증명 없어 버린 것 {len(unproven_c)}), "
        f"규칙 위반 {len(violations)}, 사람 결정 대기 {len(awaiting)}, 승인된 삭제에 대한 이견 {len(disputed_removals)}, "
        f"목적지 미확인 {len(destination_unconfirmed)}, 이어받음 {len(carried)}, "
        f"기준 이의 {len(objections)}"
    )
    return 0 if result == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
