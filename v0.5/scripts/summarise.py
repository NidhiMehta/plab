#!/usr/bin/env python3
"""
Summarise any PLAB result JSONL file.

Usage:
    python scripts/summarise.py results/v0.5_opus47_fixed.jsonl
    python scripts/summarise.py results/v0.5_nemotron_fixed.jsonl --verbose
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

TIERS = ["tool_gated", "implicit_authz", "confused_deputy", "chained"]


def load(path: Path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("results", type=Path, help="JSONL result file")
    p.add_argument("--verbose", "-v", action="store_true", help="Show failed/inconclusive case IDs")
    args = p.parse_args()

    if not args.results.exists():
        print(f"ERROR: {args.results} not found", file=sys.stderr)
        sys.exit(1)

    results = load(args.results)
    if not results:
        print("Empty file.")
        sys.exit(0)

    overall = Counter(r["status"] for r in results)
    by_tier = {}
    for r in results:
        t = r.get("tier", "unknown")
        by_tier.setdefault(t, Counter())[r["status"]] += 1

    model = results[0].get("model", {})
    print(f"\n{'─'*60}")
    print(f"  {args.results.name}")
    print(f"  model : {model.get('name','?')}  provider: {model.get('provider','?')}")
    print(f"  total : {len(results)} cases")
    print(f"{'─'*60}")
    print(f"  {'TIER':<22} {'PASS':>5} {'FAIL':>5} {'INC':>5} {'ERR':>5} {'TOTAL':>6}")
    print(f"  {'─'*22} {'─'*5} {'─'*5} {'─'*5} {'─'*5} {'─'*6}")

    for tier in TIERS + [t for t in by_tier if t not in TIERS]:
        c = by_tier.get(tier, Counter())
        total = sum(c.values())
        if total == 0:
            continue
        print(f"  {tier:<22} {c['passed']:>5} {c['failed']:>5} {c['inconclusive']:>5} {c['error']:>5} {total:>6}")

    print(f"  {'─'*22} {'─'*5} {'─'*5} {'─'*5} {'─'*5} {'─'*6}")
    total = len(results)
    print(f"  {'ALL':<22} {overall['passed']:>5} {overall['failed']:>5} {overall['inconclusive']:>5} {overall['error']:>5} {total:>6}")
    print(f"{'─'*60}\n")

    if args.verbose:
        for status in ("failed", "inconclusive"):
            cases = [r for r in results if r["status"] == status]
            if not cases:
                continue
            print(f"  {status.upper()} ({len(cases)}):")
            for r in cases:
                tc = len(r.get("trace", {}).get("tool_calls", []))
                leak = r.get("evaluation", {}).get("leakage_level", 0)
                print(f"    {r['case_id']:<35} tool_calls={tc}  leak={leak}")
            print()


if __name__ == "__main__":
    main()
