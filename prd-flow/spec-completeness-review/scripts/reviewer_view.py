#!/usr/bin/env python3
"""검토자에게 줄 추적표 사본을 만든다.

작성자가 적은 판정 근거(evidence), 대기 사유(pending_reason), 이전 검토자의 판정 사유(review_reason, review_verdict),
작성자가 매긴 개정 전 대비 분류(disposition)를 뺀다. 상태(verification_status)는 사람이 정한 값
(승인된 삭제, 원문 충돌 대기, 목적지 확인 대기)만 남기고 나머지는 뺀다. 이것들은 작성자의 주장이거나
이전 판정이라, 그대로 주면 검토자가 그 주장대로 읽는다. 행의 원문 위치, 요약, 대상 위치와 판정 기준 기록은 남긴다.

  reviewer_view.py TRACE --out records/round-N-trace-for-reviewer.json --root DIR
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load, save  # noqa: E402

HIDDEN = ("evidence", "pending_reason", "review_reason", "review_verdict", "disposition")
# 사람이 정한 상태만 남긴다. 검토자는 이 값으로 승인된 삭제와 목적지 확인 대상 행을 구별한다.
SHOWN_STATUSES = {"approved_removal", "source_conflict_pending", "destination_pending"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, required=True, help="--root 기준 상대 경로")
    args = parser.parse_args()
    data = load(args.trace)
    for key in ("requirements", "exclusions"):
        for row in data.get(key, []):
            for field in HIDDEN:
                row.pop(field, None)
            if row.get("verification_status") not in SHOWN_STATUSES:
                row.pop("verification_status", None)
    meta = data["metadata"]
    view = {
        "schema_version": data.get("schema_version"),
        "note": "검토자용 사본이다. 작성자의 근거와 이전 판정을 뺐다. 원본 추적표는 기계 검사에만 쓴다.",
        "metadata": {k: meta.get(k) for k in ("mode", "purpose", "extraction_rule", "sources", "id_families", "active_target", "criteria_rulings")},
        "requirements": data.get("requirements", []),
        "exclusions": data.get("exclusions", []),
    }
    out = args.root.resolve() / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    save(out, view)
    print(f"검토자용 추적표: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
