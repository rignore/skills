#!/usr/bin/env python3
"""완전성 검토 추적표를 기계 검사한다.

확인하는 것: 원문·대상·불변 사본 파일의 실재와 지문(sha256), 원문 위치의 줄이 그 절(또는 그 하위 절)
안에 있는지, 대상 위치의 절이 있는지, 행 번호의 연속성, 허용값, 합계, 제외 항목, 판정 기준 기록 형식.
--require-pass를 주면 마지막 회차가 PASS이고 그 회차가 현재 대상 판본을 봤는지도 확인한다(마감 때 쓴다).
확인하지 못하는 것: 문장의 뜻이 같은지. 그것은 격리 검토자가 판정한다.

경로는 모두 --root(기본: 현재 폴더) 기준 상대 경로다. 절 표기 '머리말'은 첫 제목보다 앞의 줄을 뜻한다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

MODES = {"initial", "revision"}
DISPOSITIONS = {"preserved", "condensed_equivalent", "weakened", "missing", "move_candidate", "source_revised"}
STATUSES = {
    "unverified",
    "verified_equivalent",
    "restore_required",
    "restored_pending_review",
    "destination_pending",
    "destination_verified",
    "approved_removal",
    "source_conflict_pending",
}
HUMAN_DECIDED = {"approved_removal", "destination_pending"}
# 사람의 결정을 증명하지 못하는 값. approved_by에는 결정한 사람이나 직책을 적는다.
NOT_A_DECIDER = {"", "작성자", "자동", "에이전트", "검토자", "author", "auto", "agent", "claude", "codex"}
PENDING = {"unverified", "restore_required", "restored_pending_review", "destination_pending", "source_conflict_pending"}
LOCATION_RE = re.compile(r"^(?P<section>[^:]+):L(?P<start>[1-9][0-9]*)-L(?P<end>[1-9][0-9]*)$")
EXCLUSION_RE = re.compile(r"^EX-[0-9]{2,3}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


HEADING_RE = re.compile(r"^(#{1,6}) (.*)$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
FRONT_MATTER = {"머리말", "문서 머리"}


def heading_lines(lines: list[str]) -> list[tuple[int, int, str]]:
    """(줄 번호 0부터, 수준, 제목) 목록. 코드 블록(``` 또는 ~~~ 사이) 안의 # 줄은 제목이 아니다."""
    out: list[tuple[int, int, str]] = []
    fence: str | None = None  # 연 울타리 문자열(예: ``` 또는 ~~~~)
    for index, line in enumerate(lines):
        m_fence = FENCE_RE.match(line)
        if m_fence:
            mark = m_fence.group(1)
            if fence is None:
                fence = mark
                continue
            if mark[0] == fence[0] and len(mark) >= len(fence) and not line.strip()[len(mark):].strip():
                fence = None
                continue
        if fence is None and (m := HEADING_RE.match(line)):
            out.append((index, len(m.group(1)), m.group(2).strip()))
    return out


def headings(text: str) -> list[str]:
    return [h for _, _, h in heading_lines(text.splitlines())]


def heading_matches(heading: str, section: str) -> bool:
    """절 표기(예: §3.1, 3.1, 4.5 인수 조건, 요구 3)가 제목의 앞부분과 맞는지 본다."""
    token = section.strip().lstrip("§").strip()
    h = heading.lstrip("§").strip()
    if not token:
        return False
    return h == token or h.startswith(token + ".") or h.startswith(token + " ") or h.startswith(token + "—")


def section_exists(text: str, section: str) -> bool:
    return any(heading_matches(h, section) for h in headings(text))


def section_span(lines: list[str], section: str) -> list[tuple[int, int]]:
    """그 절 제목 줄부터 같은 수준 이상의 다음 제목 앞까지의 줄 범위(1부터, 끝 포함) 목록."""
    token = section.strip().lstrip("§").strip()
    heads = heading_lines(lines)
    if token in FRONT_MATTER:
        first = next((i for i, level, _ in heads if level > 1), len(lines))
        return [(1, first)]
    spans = []
    for k, (index, level, title) in enumerate(heads):
        if not heading_matches(title, section):
            continue
        end = next((i for i, lv, _ in heads[k + 1:] if lv <= level), len(lines))
        spans.append((index + 1, end))
    return spans


def line_in_section(lines: list[str], start: int, section: str, end: int | None = None) -> bool:
    """start~end 줄(1부터)이 모두 그 절 제목 줄부터 같은 수준 이상의 다음 제목 앞까지 안에 있는지 본다.

    하위 절(예: 2 아래의 2.1)이나 번호 없는 하위 제목 안의 줄도 그 절 안으로 본다.
    """
    end = start if end is None else end
    return any(a <= start and end <= b for a, b in section_span(lines, section))


def section_text(text: str, section: str) -> str | None:
    lines = text.splitlines()
    spans = section_span(lines, section)
    if not spans:
        return None
    return "\n".join("\n".join(lines[a - 1:b]) for a, b in spans)


def check_location(lines: list[str], raw: Any, label: str, errors: list[str]) -> None:
    match = LOCATION_RE.fullmatch(raw or "") if isinstance(raw, str) else None
    if match is None:
        errors.append(f"{label} 형식은 '절:L시작-L끝'이어야 한다: {raw}")
        return
    if not lines:
        return
    start, end = int(match["start"]), int(match["end"])
    if start > end or end > len(lines):
        errors.append(f"{label} 줄 범위가 원문에 없다: {raw}")
    elif not line_in_section(lines, start, match["section"], end):
        errors.append(f"{label}: L{start}-L{end}이 절 {match['section']} 안에 있지 않다")


def resolve(root: Path, raw: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        errors.append(f"{label} 경로가 비었다")
        return None
    path = Path(raw)
    if path.is_absolute():
        errors.append(f"{label}는 --root 기준 상대 경로여야 한다: {raw}")
        return None
    full = (root / path).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label}가 --root 밖을 가리킨다: {raw}")
        return None
    if not full.is_file():
        errors.append(f"{label} 파일이 없다: {raw}")
        return None
    return full


def validate(trace_path: Path, root: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(trace_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"추적표를 읽을 수 없다: {error}"]
    if data.get("schema_version") != 1:
        errors.append("schema_version은 1이어야 한다")
    meta = data.get("metadata")
    if not isinstance(meta, dict):
        return errors + ["metadata는 객체여야 한다"]
    mode = meta.get("mode")
    if mode not in MODES:
        errors.append(f"metadata.mode는 initial 또는 revision이어야 한다: {mode}")

    limit = meta.get("machine_validation_limit")
    if not isinstance(limit, str) or "의미" not in limit:
        errors.append("machine_validation_limit에 기계 검사가 뜻의 동등성을 판정하지 못한다는 한계를 적어야 한다")

    # 원문: 요구사항을 뽑은 문서. 지문이 바뀌면 그 원문을 가리키는 행을 다시 추적해야 한다.
    source_lines: dict[str, list[str]] = {}
    sources = meta.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("metadata.sources에 원문이 하나 이상 있어야 한다")
        sources = []
    for item in sources:
        sid = item.get("id") if isinstance(item, dict) else None
        if not isinstance(sid, str) or not sid:
            errors.append("source 항목에는 id가 있어야 한다")
            continue
        if sid in source_lines:
            errors.append(f"source id 중복: {sid}")
            continue
        path = resolve(root, item.get("path"), f"source {sid}", errors)
        if path is None:
            continue
        if sha256(path) != item.get("sha256"):
            errors.append(f"source 지문 불일치: {sid} ({item.get('path')}) — 원문이 바뀌었으면 이 원문을 가리키는 행의 위치를 다시 지정하고 지문을 갱신한다")
        source_lines[sid] = path.read_text(encoding="utf-8").splitlines()
    families = meta.get("id_families")
    if not isinstance(families, dict) or not families:
        errors.append("metadata.id_families에 행 번호 접두어와 그 원문 id의 대응을 적어야 한다")
        families = {}
    for prefix, sid in families.items():
        if sid not in source_lines and sid not in {s.get("id") for s in sources if isinstance(s, dict)}:
            errors.append(f"id_families.{prefix}가 없는 source를 가리킨다: {sid}")

    # 대상: 지금 검토하는 사양.
    target = meta.get("active_target")
    target_path = None
    if not isinstance(target, dict):
        errors.append("metadata.active_target은 객체여야 한다")
    else:
        target_path = resolve(root, target.get("path"), "active_target", errors)
        if target_path is not None:
            if target.get("sha256") != sha256(target_path):
                errors.append("active_target.sha256이 대상 파일과 다르다 — 고친 뒤에는 freeze_snapshot.py로 얼리고 지문을 갱신한다")
            if target.get("line_count") != len(target_path.read_text(encoding="utf-8").splitlines()):
                errors.append("active_target.line_count가 대상 파일과 다르다")

    # 불변 사본: 검토자가 본 판본을 차수별로 고정한다.
    snapshots = meta.get("snapshots", [])
    if not isinstance(snapshots, list):
        errors.append("metadata.snapshots는 배열이어야 한다")
        snapshots = []
    rounds_seen: list[int] = []
    for index, snap in enumerate(snapshots, start=1):
        if not isinstance(snap, dict):
            errors.append(f"snapshots[{index}]는 객체여야 한다")
            continue
        rnd = snap.get("round")
        if not isinstance(rnd, int) or rnd < 0:
            errors.append(f"snapshots[{index}].round는 0 이상 정수여야 한다(0은 개정 전 기준본)")
        else:
            rounds_seen.append(rnd)
        path = resolve(root, snap.get("path"), f"snapshot 차수 {rnd}", errors)
        if path is not None and sha256(path) != snap.get("sha256"):
            errors.append(f"불변 사본 지문 불일치: 차수 {rnd} ({snap.get('path')}) — 얼린 사본은 고치지 않는다")
    if rounds_seen != sorted(set(rounds_seen)):
        errors.append("snapshots.round는 중복 없이 오름차순이어야 한다")
    if mode == "revision" and 0 not in rounds_seen:
        errors.append("개정 모드는 개정 전 기준본을 차수 0 사본으로 얼려 두어야 한다")

    # 검토 회차 기록: 각 회차가 어느 사본을 봤는지.
    reviews = meta.get("review_records", [])
    if not isinstance(reviews, list):
        errors.append("metadata.review_records는 배열이어야 한다")
        reviews = []
    snap_rounds = set(rounds_seen)
    for index, rec in enumerate(reviews, start=1):
        if not isinstance(rec, dict):
            errors.append(f"review_records[{index}]는 객체여야 한다")
            continue
        if rec.get("result") not in {"PASS", "FAIL"}:
            errors.append(f"review_records[{index}].result는 PASS 또는 FAIL이어야 한다")
        if rec.get("round") not in snap_rounds:
            errors.append(f"review_records[{index}]의 차수 {rec.get('round')}에 해당하는 불변 사본이 없다 — 검토 전에 얼려야 한다")
        resolve(root, rec.get("path"), f"review_records[{index}]", errors)

    rulings = meta.get("criteria_rulings", [])
    if not isinstance(rulings, list):
        errors.append("metadata.criteria_rulings는 배열이어야 한다")
        rulings = []
    for index, ruling in enumerate(rulings, start=1):
        if not isinstance(ruling, dict) or not all(
            isinstance(ruling.get(k), str) and ruling.get(k).strip() for k in ("decided_at", "decided_by", "ruling", "basis")
        ):
            errors.append(f"criteria_rulings[{index}]에는 decided_at·decided_by·ruling·basis가 있어야 한다")

    # 요구사항 행.
    rows = data.get("requirements")
    if not isinstance(rows, list) or not rows:
        return errors + ["requirements는 비어 있지 않은 배열이어야 한다"]
    if meta.get("requirement_count") != len(rows):
        errors.append("requirement_count와 requirements 행 수가 다르다")
    if meta.get("status_counts") != dict(Counter(r.get("verification_status") for r in rows if isinstance(r, dict))):
        errors.append("status_counts와 실제 상태 합계가 다르다")
    if mode == "revision" and meta.get("disposition_counts") != dict(
        Counter(r.get("disposition") for r in rows if isinstance(r, dict))
    ):
        errors.append("disposition_counts와 실제 분류 합계가 다르다")
    seen: set[str] = set()
    counters: Counter[str] = Counter()
    target_text = target_path.read_text(encoding="utf-8") if target_path else ""
    for index, row in enumerate(rows, start=1):
        label = f"requirements[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label}는 객체여야 한다")
            continue
        rid = row.get("id")
        prefix = rid.rsplit("-", 1)[0] if isinstance(rid, str) and "-" in rid else None
        if prefix not in families:
            errors.append(f"{label}.id 접두어가 id_families에 없다: {rid}")
        else:
            counters[prefix] += 1
            expected = f"{prefix}-{counters[prefix]:03d}"
            if rid != expected:
                errors.append(f"{label}.id는 연속 번호 {expected}여야 한다: {rid}")
        if rid in seen:
            errors.append(f"요구사항 id 중복: {rid}")
        seen.add(rid)
        row_source = row.get("source_id") or families.get(prefix, "")
        if row.get("source_id") and row_source not in source_lines:
            errors.append(f"{label}.source_id가 없는 원문을 가리킨다: {row_source}")
        lines = source_lines.get(row_source, [])
        check_location(lines, row.get("source_location"), f"{label}.source_location", errors)
        for key in ("summary", "evidence"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                errors.append(f"{label}.{key}가 비었다")
        if mode == "revision" and row.get("disposition") not in DISPOSITIONS:
            errors.append(f"{label}.disposition 허용값 오류: {row.get('disposition')}")
        status = row.get("verification_status")
        if status not in STATUSES:
            errors.append(f"{label}.verification_status 허용값 오류: {status}")
        if status in PENDING and not str(row.get("pending_reason", "")).strip() and status != "unverified":
            errors.append(f"{label}.pending_reason이 필요한 상태다")
        if status in HUMAN_DECIDED and not any(
            isinstance(r, dict) and rid in (r.get("affects") or [])
            and str(r.get("approved_by", "")).strip() not in NOT_A_DECIDER
            and str(r.get("basis", "")).strip()
            for r in rulings
        ):
            errors.append(
                f"{label}: 상태 {status}는 사람의 결정이다. criteria_rulings에 이 행을 affects로 가리키고 "
                "approved_by(결정한 사람 또는 직책)를 적은 항목이 있어야 한다"
            )
        # destination: 옮겨 갈 다른 문서의 '경로#절'. target_locations는 옮기기 전까지 이 사양 안에 임시로 둔 곳이다.
        destination = row.get("destination")
        if destination is not None:
            if status not in {"destination_pending", "destination_verified"}:
                errors.append(f"{label}: destination은 목적지 확인 대기·확인 행에만 둔다")
            elif not isinstance(destination, str) or "#" not in destination:
                errors.append(f"{label}.destination 형식은 '경로#절'이어야 한다: {destination}")
            else:
                raw_path, dsection = destination.rsplit("#", 1)
                if raw_path in {s_.get("path") for s_ in sources if isinstance(s_, dict)} or (target and raw_path == target.get("path")):
                    errors.append(f"{label}: 목적지는 원문이나 이 사양이 아닌 다른 문서여야 한다: {destination}")
                else:
                    dpath = resolve(root, raw_path, f"{label} 목적지", errors)
                    if dpath and not section_exists(dpath.read_text(encoding="utf-8"), dsection):
                        errors.append(f"{label} 목적지 절이 없다: {destination}")
        targets = row.get("target_locations")
        if not isinstance(targets, list):
            errors.append(f"{label}.target_locations는 배열이어야 한다")
            continue
        if not targets and status not in {"approved_removal", "restore_required", "unverified"}:
            errors.append(f"{label}: 대상 위치가 없는데 상태가 {status}다")
        for loc in targets:
            if not isinstance(loc, str) or "#" not in loc:
                errors.append(f"{label} 대상 위치 형식은 '경로#절'이어야 한다: {loc}")
                continue
            raw, section = loc.rsplit("#", 1)
            if target and raw == target.get("path"):
                text = target_text
            else:
                path = resolve(root, raw, f"{label} 대상", errors)
                text = path.read_text(encoding="utf-8") if path else ""
            if text and not section_exists(text, section):
                errors.append(f"{label} 대상 절이 없다: {loc}")

    exclusions = data.get("exclusions", [])
    if not isinstance(exclusions, list):
        errors.append("exclusions는 배열이어야 한다")
        exclusions = []
    if meta.get("exclusion_count") != len(exclusions):
        errors.append("exclusion_count와 exclusions 행 수가 다르다")
    ex_ids: set[str] = set()
    for index, item in enumerate(exclusions, start=1):
        eid = item.get("id") if isinstance(item, dict) else None
        if not isinstance(eid, str) or not EXCLUSION_RE.fullmatch(eid):
            errors.append(f"exclusions[{index}].id 형식 오류(EX-01): {eid}")
        elif eid in ex_ids:
            errors.append(f"제외 id 중복: {eid}")
        else:
            ex_ids.add(eid)
        if isinstance(item, dict):
            sid = item.get("source_id")
            if sid is None and len(source_lines) > 1:
                errors.append(f"exclusions[{index}].source_id가 필요하다(원문이 둘 이상이다)")
            elif sid is not None and sid not in source_lines:
                errors.append(f"exclusions[{index}].source_id가 없는 원문을 가리킨다: {sid}")
            ex_lines = source_lines.get(sid) if sid else (next(iter(source_lines.values())) if len(source_lines) == 1 else [])
            check_location(ex_lines or [], item.get("source_location"), f"exclusions[{index}].source_location", errors)
            for key in ("source_location", "category", "summary", "evidence"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    errors.append(f"exclusions[{index}].{key}가 비었다")
    return errors


def overlap_warnings(trace_path: Path, root: Path) -> list[str]:
    """제외 행이 요구사항 행과 같은 원문 줄을 덮는 곳을 경고로 돌려준다(종료 코드에 영향 없음).

    같은 원문 줄을 요구사항과 제외에 동시에 두면, 뜻이 빠져도 제외를 근거로 통과할 수 있다.
    절 전체를 작성 경위로 제외하면서 그 안의 요구 문장을 행으로 뽑은 경우처럼 정당한 겹침도 있으므로
    막지 않고 보여 준다. 정당하면 제외 행의 overlap_reason에 무엇을 뺐는지 적어 경고를 끈다.
    """
    warnings: list[str] = []
    try:
        data = json.loads(trace_path.read_text(encoding="utf-8"))
        meta = data["metadata"]
        sources = meta.get("sources", [])
        families = meta.get("id_families", {})
        rows = data.get("requirements", [])
        exclusions = data.get("exclusions", [])
    except (OSError, ValueError, KeyError, TypeError):
        return warnings
    # 같은 원문 줄을 요구사항 행과 제외 행에 동시에 두면, 뜻이 빠져도 제외를 근거로 통과할 수 있다.
    source_ids = [s.get("id") for s in sources if isinstance(s, dict)]
    req_ranges: dict[str, list[tuple[int, int, str]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        prefix = row.get("id", "").rsplit("-", 1)[0] if isinstance(row.get("id"), str) else ""
        m = LOCATION_RE.fullmatch(row.get("source_location") or "")
        if m and prefix in families:
            req_ranges.setdefault(row.get("source_id") or families[prefix], []).append((int(m["start"]), int(m["end"]), row["id"]))
    for index, item in enumerate(exclusions, start=1):
        if not isinstance(item, dict):
            continue
        sid = item.get("source_id") or (source_ids[0] if len(source_ids) == 1 else None)
        m = LOCATION_RE.fullmatch(item.get("source_location") or "")
        if sid not in source_ids or m is None:
            continue
        start, end = int(m["start"]), int(m["end"])
        for rs, re_, rid in req_ranges.get(sid, []):
            if start <= re_ and rs <= end and not item.get("overlap_reason"):
                warnings.append(
                    f"exclusions[{index}]({item.get('id')})가 요구사항 {rid}와 같은 원문 줄을 덮는다 — "
                    "요구 문장이면 제외에서 빼고, 한 줄에 요구와 비요구가 섞였으면 overlap_reason에 무엇을 뺐는지 적는다"
                )
    return warnings


def pass_errors(trace_path: Path) -> list[str]:
    """마감 조건: 마지막 회차가 PASS이고 그 회차가 본 판본이 지금 대상과 같아야 한다."""
    data = json.loads(trace_path.read_text(encoding="utf-8"))
    meta = data["metadata"]
    records = meta.get("review_records", [])
    if not records:
        return ["아직 기록된 검토 회차가 없다"]
    last = max(records, key=lambda r: r.get("round", 0))
    errors = []
    if last.get("result") != "PASS":
        errors.append(f"마지막 회차(차수 {last.get('round')})가 PASS가 아니다")
    if last.get("subject_sha256") != meta.get("active_target", {}).get("sha256"):
        errors.append(
            f"마지막 회차(차수 {last.get('round')})가 본 판본과 현재 대상이 다르다 — 통과 뒤 사양이 바뀌었다. 다시 얼리고 재검토한다"
        )
    blocking = PENDING - {"destination_pending"}  # 다른 문서로 옮겨 가기를 기다리는 행은 이 사양의 통과를 막지 않는다
    pending = [r["id"] for r in data.get("requirements", []) if r.get("verification_status") in blocking]
    if pending:
        errors.append("검토 대기·복원 필요·사람 결정 대기 행이 남아 있다: " + ", ".join(pending[:20]))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--require-pass", action="store_true", help="마감 조건까지 확인한다")
    args = parser.parse_args()
    errors = validate(args.trace.resolve(), args.root.resolve())
    if not errors and args.require_pass:
        errors = pass_errors(args.trace.resolve())
    if errors:
        for warning in overlap_warnings(args.trace.resolve(), args.root.resolve()):
            errors.append(f"(경고) {warning}")
        print(f"FAIL — 추적표 {args.trace}")
        for error in errors:
            print(f"- {error}")
        return 1
    for warning in overlap_warnings(args.trace.resolve(), args.root.resolve()):
        print(f"경고 — {warning}")
    data = json.loads(args.trace.read_text(encoding="utf-8"))
    print(f"PASS — 추적표 {args.trace}: 요구사항 {len(data['requirements'])}개, 제외 {len(data.get('exclusions', []))}개")
    print("주의 — 이 검사는 뜻의 동등성을 판정하지 않는다. 격리 검토가 따로 필요하다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
