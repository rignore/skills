#!/usr/bin/env python3
"""추적표의 파생값을 다시 채운다: 대상 지문·줄 수, 행 합계.

추적표를 처음 만든 뒤와, 행을 더하거나 상태를 바꾼 뒤에 쓴다. 손으로 합계를 쓰지 않기 위한 것이다.
대상 지문을 여기서 갱신해도 통과 판정이 생기지는 않는다. 마감 검사(check_trace.py --require-pass)는
마지막 회차가 본 판본의 지문과 현재 대상 지문을 대조한다.

  refresh_trace.py TRACE --root DIR
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load, recount, save, sha256  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    data = load(args.trace)
    target = data["metadata"]["active_target"]
    path = root / target["path"]
    if not path.is_file():
        print(f"대상 파일이 없다: {target['path']}", file=sys.stderr)
        return 1
    target["sha256"] = sha256(path)
    target["line_count"] = len(path.read_text(encoding="utf-8").splitlines())
    recount(data)
    save(args.trace, data)
    meta = data["metadata"]
    print(f"갱신: 대상 {target['line_count']}줄 지문 {target['sha256'][:8]}, 요구사항 {meta['requirement_count']}개, 제외 {meta['exclusion_count']}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
