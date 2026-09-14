"""
Sample a pilot subset from the PLAB corpus.

Picks --per-cell cases for each (attack_family × domain × difficulty) cell,
optionally filtered to a single domain or difficulty.

Usage:
  # 144-case pilot (1 per cell, all axes)
  python scripts/sample_pilot.py \\
    --input data/v0.3/cases.jsonl \\
    --output /tmp/plab_pilot_144.jsonl

  # 8-case family check (1 per attack family, personal + easy only)
  python scripts/sample_pilot.py \\
    --input data/v0.3/cases.jsonl \\
    --output /tmp/plab_pilot_8.jsonl \\
    --domain personal --difficulty easy
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sample a PLAB pilot subset.")
    p.add_argument("--input", default="data/v0.3/cases.jsonl")
    p.add_argument("--output", required=True)
    p.add_argument(
        "--per-cell",
        type=int,
        default=1,
        help="Cases to pick per (attack_family × domain × difficulty) cell.",
    )
    p.add_argument("--domain", default=None, help="Restrict to one domain.")
    p.add_argument("--difficulty", default=None, help="Restrict to one difficulty.")
    p.add_argument("--attack-family", default=None, help="Restrict to one attack family.")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    all_cases = []
    with Path(args.input).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                all_cases.append(json.loads(line))

    # Apply filters
    if args.domain:
        all_cases = [c for c in all_cases if c["domain"] == args.domain]
    if args.difficulty:
        all_cases = [c for c in all_cases if c["difficulty"] == args.difficulty]
    if args.attack_family:
        all_cases = [c for c in all_cases if c["attack_family"] == args.attack_family]

    # Sample --per-cell from each cell
    cell_counts: dict[tuple, int] = defaultdict(int)
    selected = []

    for case in all_cases:
        key = (case["attack_family"], case["domain"], case["difficulty"])
        if cell_counts[key] < args.per_cell:
            selected.append(case)
            cell_counts[key] += 1

    selected.sort(key=lambda c: (c["domain"], c["attack_family"], c["difficulty"]))

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.output).open("w", encoding="utf-8") as f:
        for case in selected:
            f.write(json.dumps(case, separators=(",", ":")) + "\n")

    # Summary
    from collections import Counter
    by_fam = Counter(c["attack_family"] for c in selected)
    by_dom = Counter(c["domain"] for c in selected)
    by_dif = Counter(c["difficulty"] for c in selected)

    print(f"Sampled {len(selected)} cases → {args.output}")
    print(f"  Families  : {dict(sorted(by_fam.items()))}")
    print(f"  Domains   : {dict(sorted(by_dom.items()))}")
    print(f"  Difficulty: {dict(sorted(by_dif.items()))}")


if __name__ == "__main__":
    main()
