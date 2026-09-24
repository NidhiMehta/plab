"""
Compare v0.6 tool_gated results WITH vs WITHOUT the pre-call reasoning instruction.

Produces a 2×4 table (models × condition) and per-case breakdown showing which
cases flipped and in which direction.

Usage (from the v0.5 directory):
    uv run python scripts/compare_ablation.py

Reads:
    results/v0.6_opus47.jsonl          — with pre-call check (baseline run)
    results/v0.6_gemini.jsonl
    results/v0.6_gpt52.jsonl
    results/v0.6_deepseek.jsonl
    results/v0.6_ablation_opus47.jsonl  — without pre-call check (ablation run)
    results/v0.6_ablation_gemini.jsonl
    results/v0.6_ablation_gpt52.jsonl
    results/v0.6_ablation_deepseek.jsonl
    schema/case.v0.6.ablation_no_precheck.jsonl  — to get case IDs and metadata

Writes:
    results/v0.6_ablation_comparison.txt  — plain-text table (also printed)
"""

import json
from pathlib import Path

HERE = Path(__file__).parent.parent

MODELS = [
    ("Opus 4.7",    "opus47"),
    ("Gemini 2.5",  "gemini"),
    ("GPT-5.2",     "gpt52"),
    ("DeepSeek V3", "deepseek"),
]


def load_results(path: Path) -> dict[str, str]:
    """Return {case_id: status} from a JSONL result file."""
    results = {}
    if not path.exists():
        return results
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            cid = obj.get("case_id") or obj.get("id", "")
            results[cid] = obj.get("status", "inconclusive")
    return results


def load_case_meta(path: Path) -> list[dict]:
    cases = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            cases.append({
                "id":     c["id"],
                "domain": c.get("domain", ""),
                "family": c.get("metadata", {}).get("attack_family",
                          c.get("attack_family", "")),
            })
    return cases


def pass_rate(results: dict[str, str]) -> tuple[int, int, str]:
    """Return (passed, conclusive, pct_str)."""
    p = sum(1 for s in results.values() if s == "passed")
    f = sum(1 for s in results.values() if s == "failed")
    if p + f == 0:
        return p, p + f, "—"
    return p, p + f, f"{round(100 * p / (p + f))}%"


def main():
    cases = load_case_meta(HERE / "schema" / "case.v0.6.ablation_no_precheck.jsonl")
    case_ids = [c["id"] for c in cases]

    with_check  = {}
    no_check    = {}

    for label, key in MODELS:
        with_check[key]  = load_results(HERE / f"results/v0.6_{key}.jsonl")
        no_check[key]    = load_results(HERE / f"results/v0.6_ablation_{key}.jsonl")

        # Restrict 'with_check' to the same 23 tool_gated cases
        with_check[key] = {k: v for k, v in with_check[key].items() if k in case_ids}

    lines = []
    lines.append("=" * 72)
    lines.append("PLAB v0.6 — Tool-gated pre-call reasoning ablation (23 cases)")
    lines.append("=" * 72)
    lines.append("")
    lines.append("Condition: WITH = pre-call check instruction present (v0.6 baseline)")
    lines.append("           WITHOUT = instruction removed from role_prompt")
    lines.append("")

    # ── Summary table ──
    header = f"{'Model':<14}  {'WITH':>10}  {'WITHOUT':>10}  {'Delta':>8}"
    lines.append(header)
    lines.append("-" * len(header))
    for label, key in MODELS:
        wp, wc, wpct  = pass_rate(with_check[key])
        np, nc, npct  = pass_rate(no_check[key])
        if wc and nc:
            delta = round(100 * np / nc) - round(100 * wp / wc)
            delta_str = f"{delta:+d}pp"
        else:
            delta_str = "—"
        lines.append(
            f"{label:<14}  {wpct:>7} ({wp}/{wc})  {npct:>7} ({np}/{nc})  {delta_str:>8}"
        )
    lines.append("")

    # ── Per-case flip table ──
    lines.append("Per-case status changes (WITH → WITHOUT):")
    lines.append("-" * 72)
    header2 = f"{'Case ID':<38}  " + "  ".join(f"{l:<6}" for l, _ in MODELS)
    lines.append(header2)
    lines.append("-" * len(header2))
    for c in cases:
        cid = c["id"]
        cells = []
        changed = False
        for label, key in MODELS:
            w = with_check[key].get(cid, "—")[:3].upper()
            n = no_check[key].get(cid, "—")[:3].upper()
            if w != n:
                cell = f"{w}→{n}"
                changed = True
            else:
                cell = f"{w}   "
            cells.append(f"{cell:<6}")
        marker = " *" if changed else ""
        lines.append(f"{cid:<38}  " + "  ".join(cells) + marker)
    lines.append("")
    lines.append("* = at least one model changed status")
    lines.append("Status abbreviations: PAS=passed  FAI=failed  INC=inconclusive")
    lines.append("")
    lines.append("=" * 72)

    output = "\n".join(lines)
    print(output)

    out_path = HERE / "results" / "v0.6_ablation_comparison.txt"
    out_path.write_text(output + "\n", encoding="utf-8")
    print(f"\nWritten → {out_path}")


if __name__ == "__main__":
    main()
