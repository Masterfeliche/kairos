"""Phase 1 PoC: score a parser output against the candidate gold set.

Metrics:
  - session match   : a parser session exists at the same (page, day, start_time)
  - code accuracy   : matched session has the expected course code
  - extra sessions  : parser sessions on gold pages with no gold counterpart
  - flagged rate    : parser sessions marked low confidence (reported separately)

Uncertain parser records are never counted as correct on code mismatch.

Usage:
    python tools/poc/score.py <parser.json> [gold.json]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DEFAULT_GOLD = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "gold" / "gold_pages.json"


def norm_code(s: str | None) -> str:
    return re.sub(r"\s+", "", (s or "")).upper()


def load_parser(path: str) -> dict:
    data = json.load(open(path, encoding="utf-8"))
    sessions = data["sessions"]
    for s in sessions:
        if "course_code" not in s and "code" in s:
            s["course_code"] = s["code"]
        if "start_time" not in s and s.get("slot"):
            s["start_time"] = str(s["slot"]).split("-")[0]
    return {"sessions": sessions, "report": data.get("report", {})}


def main() -> None:
    parser = load_parser(sys.argv[1])
    gold = json.load(open(sys.argv[2] if len(sys.argv) > 2 else DEFAULT_GOLD, encoding="utf-8"))

    total_gold = 0
    matched = 0
    code_ok = 0
    missing = []
    wrong = []

    for page in gold["pages"]:
        pno = page["page"]
        p_sessions = [s for s in parser["sessions"] if s["page"] == pno]
        for g in page["sessions"]:
            total_gold += 1
            cand = next((s for s in p_sessions
                         if s.get("day") == g["day"] and s.get("start_time") == g["start_time"]), None)
            if not cand:
                missing.append((pno, g["day"], g["start_time"], g["course_code"]))
                continue
            matched += 1
            if norm_code(cand.get("course_code")) == norm_code(g["course_code"]):
                code_ok += 1
            else:
                wrong.append((pno, g["day"], g["start_time"],
                              g["course_code"], cand.get("course_code"), cand.get("confidence")))

    gold_codes = {(p["page"], g["start_time"], norm_code(g["course_code"]))
                  for p in gold["pages"] for g in p["sessions"]}
    gold_pages = {p["page"] for p in gold["pages"]}
    extra = []
    for s in parser["sessions"]:
        if s["page"] in gold_pages:
            k = (s["page"], s.get("start_time"), norm_code(s.get("course_code")))
            if s.get("course_code") and k not in gold_codes:
                extra.append((s["page"], s.get("day"), s.get("start_time"),
                              s.get("course_code"), s.get("confidence")))

    print(f"gold sessions        : {total_gold}")
    print(f"matched (page/day/time): {matched}")
    print(f"code correct         : {code_ok}")
    if matched:
        print(f"field(code) accuracy : {code_ok / matched:.1%}")
    if total_gold:
        print(f"recall vs gold       : {matched / total_gold:.1%}")
    print(f"extra on gold pages  : {len(extra)}")

    if missing:
        print("\nMISSING (gold session not found by parser):")
        for m in missing:
            print("  ", m)
    if wrong:
        print("\nWRONG CODE (parser code != gold):")
        for w in wrong:
            print("  ", w)
    if extra:
        print("\nEXTRA (parser session not in gold):")
        for e in extra[:30]:
            print("  ", e)


if __name__ == "__main__":
    main()
