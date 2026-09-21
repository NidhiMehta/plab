"""
Print every failed case in v0.5 with the full attack conversation and model response.

Usage (from the v0.5 directory):
    python show_failures.py                   # all failures
    python show_failures.py --tier chained    # filter by tier
    python show_failures.py --model GPT-5     # filter by model label
    python show_failures.py --domain financial
    python show_failures.py --html            # write failures_report.html instead of printing
"""

import argparse
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


def load_data():
    model_results = {}
    for fname, label in RUNS:
        model_results[label] = {}
        p = HERE / fname
        if not p.exists():
            print(f"  warning: {fname} not found, skipping")
            continue
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            model_results[label][r["case_id"]] = r

    cases = {}
    for line in (HERE / "schema/case.v0.5.cases.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        c = json.loads(line)
        cases[c["id"]] = c

    return model_results, cases


def collect_failures(model_results, cases, tier_filter=None, model_filter=None, domain_filter=None):
    failures = []
    for cid, case in cases.items():
        for _, label in RUNS:
            if model_filter and label != model_filter:
                continue
            r = model_results[label].get(cid, {})
            if r.get("status") != "failed":
                continue
            if tier_filter and case["tier"] != tier_filter:
                continue
            if domain_filter and case["domain"] != domain_filter:
                continue
            failures.append({
                "case_id": cid,
                "model": label,
                "tier": case["tier"],
                "domain": case["domain"],
                "attack_family": case["attack_family"],
                "difficulty": case.get("difficulty", ""),
                "protected": case["expected"]["protected_values"],
                "leak": r.get("evaluation", {}).get("leakage_level", 0),
                "rationale": r.get("evaluation", {}).get("judge", {}).get("rationale", ""),
                "messages": r.get("trace", {}).get("messages", []),
                "attack_conv": case.get("attack", {}).get("conversation", []),
            })
    failures.sort(key=lambda x: (TIER_ORDER.get(x["tier"], 9), x["case_id"], x["model"]))
    return failures


# ── Terminal output ────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD  = "\033[1m"
RED   = "\033[91m"
CYAN  = "\033[96m"
YELLOW= "\033[93m"
GRAY  = "\033[90m"
GREEN = "\033[92m"


def print_failures(failures):
    print(f"\n{BOLD}PLAB v0.5 — {len(failures)} failure(s){RESET}\n")
    for i, f in enumerate(failures, 1):
        print(f"{BOLD}{RED}{'─'*72}{RESET}")
        print(f"{BOLD}[{i}/{len(failures)}] {f['case_id']}{RESET}  {YELLOW}{f['model']}{RESET}")
        print(f"  tier={f['tier']}  domain={f['domain']}  attack={f['attack_family']}  diff={f['difficulty']}  leak={f['leak']}")
        print(f"  {RED}protected: {f['protected']}{RESET}")
        print()

        # Conversation
        msgs = f["messages"] if f["messages"] else f["attack_conv"]
        if msgs:
            print(f"  {BOLD}Conversation:{RESET}")
            for m in msgs:
                role = m.get("role", "?")
                content = str(m.get("content", "")).strip()
                pre = "  [pre-supplied]" if m.get("pre_supplied") else ""
                if role == "user":
                    print(f"    {CYAN}User:{RESET} {content}{GRAY}{pre}{RESET}")
                elif role == "assistant":
                    print(f"    {GREEN}Model:{RESET} {content}{GRAY}{pre}{RESET}")
                else:
                    print(f"    {GRAY}{role}: {content}{RESET}")
            print()

        if f["rationale"]:
            print(f"  {BOLD}Judge:{RESET} {f['rationale']}")
        print()

    print(f"{BOLD}{RED}{'─'*72}{RESET}")
    print(f"{BOLD}Total: {len(failures)} failure(s){RESET}\n")


# ── HTML output ────────────────────────────────────────────────────────────

def build_html(failures):
    import html as html_mod

    def e(s):
        return html_mod.escape(str(s))

    rows_html = ""
    for i, f in enumerate(failures, 1):
        msgs = f["messages"] if f["messages"] else f["attack_conv"]
        conv_html = ""
        for m in msgs:
            role = m.get("role", "?")
            content = e(str(m.get("content", "")).strip())
            pre = " <span class='pre'>[pre-supplied]</span>" if m.get("pre_supplied") else ""
            cls = "msg-user" if role == "user" else "msg-model"
            lbl = "User" if role == "user" else "Model"
            conv_html += f'<div class="msg {cls}"><span class="msg-role">{lbl}</span> {content}{pre}</div>\n'

        protected_html = " ".join(f'<span class="pv">{e(v)}</span>' for v in f["protected"])
        rationale_html = f'<div class="rationale"><strong>Judge:</strong> {e(f["rationale"])}</div>' if f["rationale"] else ""

        rows_html += f"""
<div class="failure" id="f{i}">
  <div class="failure-header">
    <span class="fnum">[{i}/{len(failures)}]</span>
    <span class="case-id">{e(f['case_id'])}</span>
    <span class="model-badge">{e(f['model'])}</span>
    <span class="meta">tier={e(f['tier'])} · domain={e(f['domain'])} · attack={e(f['attack_family'])} · diff={e(f['difficulty'])} · leak={f['leak']}</span>
  </div>
  <div class="protected-row"><strong>Protected:</strong> {protected_html}</div>
  <div class="conversation">{conv_html}</div>
  {rationale_html}
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PLAB v0.5 Failures</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Source+Sans+3:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
:root {{
  --bg:#0d0f14; --surface:#161925; --surface2:#1e2436;
  --border:#252c40; --border2:#2e3752;
  --text:#dde3f0; --muted:#7b87a6; --accent:#4f8eff;
  --c-fail:#ef4444; --c-fail-bg:rgba(239,68,68,.1);
  --c-user:#4f8eff; --c-user-bg:rgba(79,142,255,.08);
  --c-model:#22c55e; --c-model-bg:rgba(34,197,94,.07);
  --f-head:'Syne',sans-serif; --f-body:'Source Sans 3',sans-serif; --f-mono:'JetBrains Mono',monospace;
}}
@media(prefers-color-scheme:light) {{ :root:not([data-theme="dark"]) {{
  --bg:#f4f6fb; --surface:#fff; --surface2:#eef1f8;
  --border:#d8dded; --border2:#c4cde0; --text:#1a2038; --muted:#5a6585; --accent:#3a6fd6;
  --c-user-bg:rgba(58,111,214,.07); --c-model-bg:rgba(22,163,74,.06);
}} }}
:root[data-theme="light"] {{
  --bg:#f4f6fb; --surface:#fff; --surface2:#eef1f8;
  --border:#d8dded; --border2:#c4cde0; --text:#1a2038; --muted:#5a6585; --accent:#3a6fd6;
}}
*,*::before,*::after {{ box-sizing:border-box; }}
body {{ background:var(--bg); color:var(--text); font-family:var(--f-body); font-size:14px; line-height:1.6; margin:0; padding:0; }}
.page {{ max-width:860px; margin:0 auto; padding:32px 20px 64px; }}
h1 {{ font-family:var(--f-head); font-size:28px; font-weight:800; margin:0 0 4px; letter-spacing:-.02em; text-wrap:balance; }}
.eyebrow {{ font-family:var(--f-mono); font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--accent); margin-bottom:8px; }}
.subtitle {{ color:var(--muted); font-size:13px; margin-bottom:32px; }}
.failure {{
  background:var(--surface); border:1px solid var(--border);
  border-left:3px solid var(--c-fail); border-radius:6px;
  padding:20px 22px; margin-bottom:20px;
}}
.failure-header {{ display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; margin-bottom:10px; }}
.fnum {{ font-family:var(--f-mono); font-size:11px; color:var(--muted); }}
.case-id {{ font-family:var(--f-mono); font-size:13px; font-weight:500; color:var(--accent); }}
.model-badge {{
  font-family:var(--f-mono); font-size:11px; padding:2px 7px; border-radius:3px;
  background:var(--c-fail-bg); color:var(--c-fail); white-space:nowrap;
}}
.meta {{ font-family:var(--f-mono); font-size:10px; color:var(--muted); }}
.protected-row {{ font-size:12px; color:var(--muted); margin-bottom:14px; }}
.pv {{
  font-family:var(--f-mono); font-size:11px; padding:1px 6px; border-radius:3px;
  background:rgba(239,68,68,.15); color:var(--c-fail); margin-right:4px;
}}
.conversation {{ display:flex; flex-direction:column; gap:8px; margin-bottom:14px; }}
.msg {{ padding:9px 12px; border-radius:5px; font-size:13px; line-height:1.55; }}
.msg-user  {{ background:var(--c-user-bg);  border-left:2px solid var(--c-user);  }}
.msg-model {{ background:var(--c-model-bg); border-left:2px solid var(--c-model); }}
.msg-role {{ font-family:var(--f-mono); font-size:10px; font-weight:500; text-transform:uppercase; letter-spacing:.06em; margin-right:8px; opacity:.7; }}
.msg-user  .msg-role {{ color:var(--c-user);  }}
.msg-model .msg-role {{ color:var(--c-model); }}
.pre {{ font-family:var(--f-mono); font-size:10px; color:var(--muted); margin-left:6px; }}
.rationale {{ font-size:12px; color:var(--muted); border-top:1px solid var(--border2); padding-top:10px; line-height:1.5; }}
.rationale strong {{ color:var(--text); }}
</style>
</head>
<body>
<div class="page">
<div class="eyebrow">PLAB · v0.5 · failures</div>
<h1>Failed Cases</h1>
<p class="subtitle">{len(failures)} failure(s) — cases where a model disclosed protected information</p>
{rows_html}
</div>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Show PLAB v0.5 failed cases")
    parser.add_argument("--tier",   help="Filter by tier (tool_gated, implicit_authz, confused_deputy, chained)")
    parser.add_argument("--model",  help="Filter by model label (e.g. 'GPT-5', 'Gemini 2.5 Pro')")
    parser.add_argument("--domain", help="Filter by domain (financial, health, enterprise, …)")
    parser.add_argument("--html",   action="store_true", help="Write HTML report to results/failures_report.html")
    args = parser.parse_args()

    model_results, cases = load_data()
    failures = collect_failures(model_results, cases,
                                tier_filter=args.tier,
                                model_filter=args.model,
                                domain_filter=args.domain)

    if not failures:
        print("No failures found matching filters.")
        return

    if args.html:
        out = HERE / "results/failures_report.html"
        out.write_text(build_html(failures))
        print(f"Written: {out}  ({len(failures)} failures)")
    else:
        print_failures(failures)


if __name__ == "__main__":
    main()
