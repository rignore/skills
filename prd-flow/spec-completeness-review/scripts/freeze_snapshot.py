#!/usr/bin/env python3
"""검토 직전의 대상 사양을 읽기 전용 사본으로 얼리고 추적표에 차수와 지문을 적는다.

검토자에게는 언제나 얼린 사본을 준다. 활성 파일을 주면 검토 중에 누가 고쳐도 알 수 없고,
나중에 "검토자가 본 판본이 무엇이었나"를 증명할 수 없다.

  freeze_snapshot.py TRACE --history-dir DIR --state "무엇을 반영한 직후인가"
  freeze_snapshot.py TRACE --history-dir DIR --baseline 원본경로 --state "개정 전 기준본"   # 개정 모드 차수 0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load, recount, save, sha256  # noqa: E402


def trace_state(data: dict) -> str:
    """판정 기준 기록과 행 상태의 지문. 같은 사양을 다시 얼릴 수 있는지 가릴 때 쓴다."""
    meta = data["metadata"]
    payload = json.dumps(
        [
            meta.get("criteria_rulings", []),
            # 검토 판정이 바꾸는 상태는 빼고 사람이 정한 상태만 본다. 그래야 회차를 기록한 것만으로 다시 얼릴 수 없다.
            sorted((r.get("id"), r.get("verification_status")) for r in data.get("requirements", [])
                   if r.get("verification_status") in {"approved_removal", "source_conflict_pending", "destination_pending"}),
        ],
        ensure_ascii=False, sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--history-dir", type=Path, required=True, help="--root 기준 상대 경로")
    parser.add_argument("--state", required=True, help="이 사본이 어떤 변경 직후인지 한 문장")
    parser.add_argument("--baseline", type=Path, help="개정 전 기준본을 차수 0으로 얼릴 때 그 파일(--root 기준)")
    parser.add_argument("--criteria-changed", action="store_true",
                        help="사양은 그대로이고 판정 기준 기록이나 행 상태만 바뀌었을 때 같은 내용을 새 차수로 얼린다")
    args = parser.parse_args()

    root = args.root.resolve()
    data = load(args.trace)
    meta = data["metadata"]
    snaps = meta.setdefault("snapshots", [])
    target = meta["active_target"]

    if args.baseline:
        if any(s.get("round") == 0 for s in snaps):
            print("차수 0 사본이 이미 있다. 기준본은 한 번만 얼린다.", file=sys.stderr)
            return 1
        source, rnd = root / args.baseline, 0
    else:
        source = root / target["path"]
        rnd = max((s.get("round", 0) for s in snaps), default=0) + 1
        if snaps and snaps[-1]["sha256"] == sha256(source):
            if not args.criteria_changed:
                print(f"대상이 직전 사본(차수 {snaps[-1]['round']})과 같다. 바뀐 것이 없으면 새로 얼리지 않는다. "
                      "판정 기준이나 사람이 정한 상태만 바뀌었으면 --criteria-changed를 준다.", file=sys.stderr)
                return 1
            if snaps[-1].get("trace_state") == trace_state(data):
                print("사양도 판정 기준도 행 상태도 직전 사본 때와 같다. 새로 얼릴 이유가 없다.", file=sys.stderr)
                return 1

    digest = sha256(source)
    history = root / args.history_dir
    history.mkdir(parents=True, exist_ok=True)
    dest = history / f"{source.stem}-차수{rnd:02d}-{digest[:8]}{source.suffix}"
    if dest.exists():
        print(f"같은 이름의 사본이 이미 있다: {dest}", file=sys.stderr)
        return 1
    shutil.copyfile(source, dest)
    os.chmod(dest, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 444: 얼린 사본은 고치지 않는다

    line_count = len(source.read_text(encoding="utf-8").splitlines())
    snaps.append({
        "trace_state": trace_state(data),
        "round": rnd,
        "path": str(dest.relative_to(root)),
        "sha256": digest,
        "line_count": line_count,
        "state": args.state,
        "frozen_at": date.today().isoformat(),
    })
    if not args.baseline:
        target["sha256"] = digest
        target["line_count"] = line_count
    recount(data)
    save(args.trace, data)
    print(f"차수 {rnd} 사본을 얼렸다: {dest.relative_to(root)} ({line_count}줄, 지문 {digest[:8]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
