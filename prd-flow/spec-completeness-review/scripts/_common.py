"""스크립트끼리 쓰는 작은 도구."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from check_trace import sha256  # noqa: F401  (다른 스크립트가 여기서 가져간다)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def recount(data: dict[str, Any]) -> None:
    """합계는 손으로 쓰지 않고 행에서 다시 센다."""
    meta = data["metadata"]
    rows = data.get("requirements", [])
    meta["requirement_count"] = len(rows)
    meta["status_counts"] = dict(Counter(r.get("verification_status") for r in rows))
    if meta.get("mode") == "revision":
        meta["disposition_counts"] = dict(Counter(r.get("disposition") for r in rows))
    meta["exclusion_count"] = len(data.get("exclusions", []))
