"""
Aggregate PLAB v0.6 multi-run results and print a summary table.

Reads all JSONL files in results_multirun/ that match v0.6_*_5run.jsonl.
For each (model, tier, case_id) computes:
  - pass_rate  = passes / (passes + fails)   [inconclusive excluded from denominator]
  - ci_lo/hi   = 95% Wilson score confidence interval

Usage (from the v0.6 directory):
  uv run python scripts/analyze_multirun.py
  uv run python scripts/analyze_multirun.py --dir results_multirun --out results_multirun/summary.json
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Wilson score interval (two-sided 95%)
# ---------------------------------------------------------------------------

def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials."""
    if n == 0:
        return (0.0, 1.0)
    p    = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


# ---------------------------------------------------------------------------
# Load results
# ---------------------------------------------------------------------------

def load_results(results_dir: Path) -> list[dict]:
    records = []
    for path in sorted(results_dir.glob("v0.6_*_5run.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------

def aggregate(records: list[dict]) -> dict:
    # key: (model_name, tier, case_id) → {passes, fails, inconclusives, total}
    counts: dict[tuple, dict] = defaultdict(lambda: {"passes": 0, "fails": 0, "inconclusives": 0})

    for r in records:
        model = r.get("model", {}).get("name", "unknown")
        tier  = r.get("tier", "unknown")
        cid   = r.get("case_id", "unknown")
        key   = (model, tier, cid)
        s     = r.get("status", "error")
        if s == "passed":
            counts[key]["passes"] += 1
        elif s == "inconclusive":
            counts[key]["inconclusives"] += 1
        else:
            counts[key]["fails"] += 1

    results = {}
    for (model, tier, cid), c in counts.items():
        n  = c["passes"] + c["fails"]  # exclude inconclusive from denominator
        pr = c["passes"] / n if n > 0 else None
        lo, hi = wilson_ci(c["passes"], n) if n > 0 else (None, None)
        results[(model, tier, cid)] = {
            "model": model, "tier": tier, "case_id": cid,
            "passes": c["passes"], "fails": c["fails"],
            "inconclusives": c["inconclusives"], "n": n,
            "pass_rate": round(pr, 3) if pr is not None else None,
            "ci_lo": round(lo, 3) if lo is not None else None,
            "ci_hi": round(hi, 3) if hi is not None else None,
        }
    return results


# ---------------------------------------------------------------------------
# Summary tables
# ---------------------------------------------------------------------------

MODEL_DISPLAY = {
    "claude-opus-4-7": "Opus 4.7",
    "gemini-2-5-pro":  "Gemini 2.5 Pro",
    "gpt-5-2":         "GPT-5.2",
    "deepseek-v3-2":   "DeepSeek V3.2",
}

TIER_ORDER = ["confused_deputy", "tool_gated", "chained"]


def print_summary(results: dict) -> None:
    # Per-model, per-tier aggregate pass rate
    model_tier: dict[tuple, list] = defaultdict(list)
    for v in results.values():
        if v["n"] > 0 and v["pass_rate"] is not None:
            model_tier[(v["model"], v["tier"])].append(v["pass_rate"])

    models = sorted({v["model"] for v in results.values()},
                    key=lambda m: list(MODEL_DISPLAY.keys()).index(m) if m in MODEL_DISPLAY else 99)
    tiers  = [t for t in TIER_ORDER if any(v["tier"] == t for v in results.values())]

    header = f"{'Model':<22}" + "".join(f"  {t:<18}" for t in tiers) + "  Overall"
    print("\n=== PLAB v0.6 multi-run pass rates (mean ± 95% CI, per tier) ===\n")
    print(header)
    print("-" * len(header))

    for model in models:
        label = MODEL_DISPLAY.get(model, model)
        row   = f"{label:<22}"
        all_rates = []
        for tier in tiers:
            rates = model_tier.get((model, tier), [])
            if rates:
                mean = sum(rates) / len(rates)
                # Pool counts for aggregate CI
                pool = [(v["passes"], v["n"]) for v in results.values()
                        if v["model"] == model and v["tier"] == tier and v["n"] > 0]
                k_tot = sum(p for p, _ in pool)
                n_tot = sum(n for _, n in pool)
                lo, hi = wilson_ci(k_tot, n_tot)
                row += f"  {mean*100:5.1f}% [{lo*100:.0f}–{hi*100:.0f}%]  "
                all_rates.extend(rates)
            else:
                row += f"  {'n/a':<18}  "
        if all_rates:
            overall_pool = [(v["passes"], v["n"]) for v in results.values()
                            if v["model"] == model and v["n"] > 0]
            k_tot = sum(p for p, _ in overall_pool)
            n_tot = sum(n for _, n in overall_pool)
            lo, hi = wilson_ci(k_tot, n_tot)
            mean   = sum(all_rates) / len(all_rates)
            row += f"  {mean*100:.1f}% [{lo*100:.0f}–{hi*100:.0f}%]"
        print(row)

    print()

    # Per-case variance: flag cases with high variance across runs
    print("=== High-variance cases (pass_rate in (0.2, 0.8)) ===\n")
    volatile = sorted(
        [v for v in results.values() if v["pass_rate"] is not None
         and 0.2 < v["pass_rate"] < 0.8],
        key=lambda v: abs(v["pass_rate"] - 0.5)
    )
    if volatile:
        print(f"  {'Case ID':<40} {'Model':<22} {'Tier':<18} passes/n  rate")
        for v in volatile[:20]:
            label = MODEL_DISPLAY.get(v["model"], v["model"])
            print(f"  {v['case_id']:<40} {label:<22} {v['tier']:<18} "
                  f"{v['passes']}/{v['n']}      {v['pass_rate']:.2f}")
    else:
        print("  None — all cases are decisive (always pass or always fail).")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Aggregate PLAB v0.6 multi-run results")
    ap.add_argument("--dir", default="results_multirun",
                    help="Directory containing v0.6_*_5run.jsonl files")
    ap.add_argument("--out", default=None,
                    help="If set, write per-case JSON summary to this path")
    args = ap.parse_args()

    results_dir = Path(args.dir)
    records     = load_results(results_dir)
    if not records:
        print(f"No records found in {results_dir}. Run the multi pipeline first.")
        return

    print(f"Loaded {len(records)} records from {results_dir}")
    results = aggregate(records)
    print_summary(results)

    if args.out:
        out_path = Path(args.out)
        rows = sorted(results.values(), key=lambda v: (v["model"], v["tier"], v["case_id"]))
        out_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Per-case summary written to {out_path}")


if __name__ == "__main__":
    main()
