"""
Regenerate results/v0.5_report.html from the raw result JSONL files.

Usage (from the v0.5 directory):
    python build_report.py

Reads:
    results/v0.5_gpt5.jsonl
    results/v0.5_gemini25pro.jsonl
    results/v0.5_full_run.jsonl        (Claude Opus 4-7)
    results/v0.5_deepseek_v32.jsonl
    schema/case.v0.5.cases.jsonl

Writes:
    results/v0.5_report.html
"""

import json
from pathlib import Path

HERE = Path(__file__).parent

RUNS = [
    ("results/v0.5_gpt5.jsonl",        "GPT-5"),
    ("results/v0.5_gemini25pro.jsonl",  "Gemini 2.5 Pro"),
    ("results/v0.5_full_run.jsonl",     "Claude Opus 4-7"),
    ("results/v0.5_deepseek_v32.jsonl", "DeepSeek V3.2"),
]

TIER_ORDER = {"tool_gated": 0, "implicit_authz": 1, "confused_deputy": 2, "chained": 3}


def load_results():
    model_results = {}
    for fname, label in RUNS:
        model_results[label] = {}
        path = HERE / fname
        if not path.exists():
            print(f"  warning: {fname} not found, skipping {label}")
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            model_results[label][r["case_id"]] = r
    return model_results


def build_data(model_results):
    cases = {}
    for line in (HERE / "schema/case.v0.5.cases.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        c = json.loads(line)
        cases[c["id"]] = c

    rows = []
    for cid, case in cases.items():
        row = {
            "id": cid,
            "tier": case["tier"],
            "domain": case["domain"],
            "attack_family": case["attack_family"],
            "difficulty": case.get("difficulty", ""),
            "protected": case["expected"]["protected_values"][:2],
            "models": {},
        }
        for _, label in RUNS:
            r = model_results[label].get(cid, {})
            row["models"][label] = {
                "status": r.get("status", "missing"),
                "leak": r.get("evaluation", {}).get("leakage_level") or 0,
                "tool_calls": len(r.get("trace", {}).get("tool_calls", [])),
            }
        rows.append(row)

    rows.sort(key=lambda r: (TIER_ORDER.get(r["tier"], 9), r["domain"], r["id"]))
    return {"cases": rows, "models": [label for _, label in RUNS]}


def build_html(data: dict) -> str:
    data_json = json.dumps(data)
    template = (HERE / "results/v0.5_report.html").read_text()
    # Replace the DATA constant with fresh data
    import re
    new_html = re.sub(
        r'const DATA = \{.*?\};',
        f'const DATA = {data_json};',
        template,
        flags=re.DOTALL,
    )
    return new_html


def main():
    print("Loading results...")
    model_results = load_results()
    data = build_data(model_results)
    total = len(data["cases"])
    print(f"  {total} cases, {len(data['models'])} models")

    out_path = HERE / "results/v0.5_report.html"
    html = build_html(data)
    out_path.write_text(html)
    print(f"  Written: {out_path}")

    # Print summary
    for m in data["models"]:
        statuses = [c["models"][m]["status"] for c in data["cases"]]
        counts = {s: statuses.count(s) for s in ("passed", "failed", "inconclusive", "error", "missing")}
        print(f"  {m}: passed={counts['passed']} failed={counts['failed']} inc={counts['inconclusive']} err={counts['error']}")


if __name__ == "__main__":
    main()
