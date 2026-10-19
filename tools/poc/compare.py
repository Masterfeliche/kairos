"""Phase 1 PoC: compare the naive table extractor with the geometry parser.

Reports, per strategy, the number of sessions and codes recovered, plus agreement
on (page, day, start_time, code) triples. Two parsers agreeing on a triple is weak
evidence of correctness; disagreement flags cells for the human gold set.

Usage:
    python tools/poc/compare.py <naive.json> <geometry.json>
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict


def load(path: str):
    data = json.load(open(path, encoding="utf-8"))
    sessions = data["sessions"]
    for s in sessions:
        if "course_code" not in s and "code" in s:
            s["course_code"] = s["code"]
        if "start_time" not in s and s.get("slot"):
            s["start_time"] = str(s["slot"]).split("-")[0]
    return sessions


def norm(s: str | None) -> str:
    return (s or "").upper().replace(" ", "")


def key(s: dict) -> tuple:
    return (s["page"], s.get("day"), s.get("start_time"), norm(s.get("course_code")))


def main() -> None:
    naive = load(sys.argv[1])
    geo = load(sys.argv[2])

    print(f"naive sessions   : {len(naive)}")
    print(f"geometry sessions: {len(geo)}")
    print(f"naive with code  : {sum(1 for s in naive if s.get('course_code'))}")
    print(f"geometry code    : {sum(1 for s in geo if s.get('course_code'))}")

    n_keys = Counter(key(s) for s in naive if s.get("course_code"))
    g_keys = Counter(key(s) for s in geo if s.get("course_code"))
    agree = sum((n_keys & g_keys).values())
    print(f"\ncode triples     : naive={sum(n_keys.values())} geom={sum(g_keys.values())} agree={agree}")

    geo_only = set(g_keys) - set(n_keys)
    naive_only = set(n_keys) - set(g_keys)
    print(f"geometry-only    : {len(geo_only)}")
    print(f"naive-only       : {len(naive_only)}")

    print("\nsample geometry-only recoveries (page, day, start, code):")
    for k in sorted(geo_only)[:20]:
        print("  ", k)
    print("\nsample naive-only (geometry lost):")
    for k in sorted(naive_only)[:20]:
        print("  ", k)

    # sessions per page delta
    npp = Counter(s["page"] for s in naive)
    gpp = Counter(s["page"] for s in geo)
    print("\nlargest geometry excess per page:")
    for pg, _ in sorted(((pg, gpp[pg] - npp.get(pg, 0)) for pg in gpp),
                        key=lambda x: -x[1])[:10]:
        print(f"  page {pg}: naive={npp.get(pg,0)} geom={gpp[pg]}")


if __name__ == "__main__":
    main()
