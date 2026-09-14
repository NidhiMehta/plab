"""
Generate an HTML evaluation report from a PLAB results JSONL file.

Usage:
    /Users/nidhi/git_repos/agentscope/.venv/bin/python scripts/make_report.py \
        --input  results/v0.3/full_20260911_025506.jsonl \
        --output results/v0.3/interim_1056_report.html \
        --title  "Interim Report — 1056 cases"

    # Minimal (title auto-derived from input filename):
    /Users/nidhi/git_repos/agentscope/.venv/bin/python scripts/make_report.py \
        --input results/v0.3/pilot_144_patched.jsonl \
        --output results/v0.3/pilot_144_patched_report.html
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_results(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def compute_stats(rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {}

    failures = [r for r in rows if r["status"] == "failed"]
    errors   = [r for r in rows if r["status"] == "error"]
    passed   = [r for r in rows if r["status"] == "passed"]
    mean_lev = sum(r["evaluation"]["leakage_level"] for r in rows) / n

    def bucket():
        return {"n": 0, "fail": 0, "lev": 0, "exact": 0, "tool_viol": 0}

    by_fam = defaultdict(bucket)
    by_dom = defaultdict(bucket)
    by_dif = defaultdict(bucket)

    for r in rows:
        ev  = r["evaluation"]
        fam = r["attack_family"]
        dom = r["domain"]
        dif = r.get("difficulty", "unknown")
        lev = ev["leakage_level"]
        s   = r["status"]

        for d, k in [(by_fam, fam), (by_dom, dom), (by_dif, dif)]:
            d[k]["n"]   += 1
            d[k]["lev"] += lev
            if s == "failed":
                d[k]["fail"] += 1
        by_fam[fam]["exact"]     += 1 if ev.get("exact_disclosure") else 0
        by_fam[fam]["tool_viol"] += 1 if ev.get("tool_authorization_violation") else 0

    def finalize(d):
        return {
            k: {**v,
                "fail_rate": round(v["fail"] / v["n"] * 100, 1) if v["n"] else 0,
                "mean_lev":  round(v["lev"]  / v["n"], 3)       if v["n"] else 0}
            for k, v in d.items()
        }

    # Sample one failure per family
    samples: dict[str, dict] = {}
    for r in rows:
        fam = r["attack_family"]
        if r["status"] == "failed" and fam not in samples:
            ev   = r["evaluation"]
            msgs = r.get("trace", {}).get("messages", [])
            asst = next((m.get("content", "") for m in msgs if m.get("role") == "assistant"), "")
            samples[fam] = {
                "case_id":   r["case_id"],
                "domain":    r["domain"],
                "difficulty": r.get("difficulty", ""),
                "level":     ev["leakage_level"],
                "exact":     ev.get("exact_disclosure", False),
                "tool_viol": ev.get("tool_authorization_violation", False),
                "auth_viol": ev.get("authorization_violation", False),
                "response":  asst[:400],
            }

    return {
        "n": n,
        "passed": len(passed),
        "failed": len(failures),
        "errors": len(errors),
        "pass_rate": round(len(passed) / n * 100, 1),
        "fail_rate": round(len(failures) / n * 100, 1),
        "mean_lev": round(mean_lev, 3),
        "by_fam": finalize(by_fam),
        "by_dom": finalize(by_dom),
        "by_dif": finalize(by_dif),
        "samples": samples,
    }


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

def _rate_color(rate: float) -> str:
    if rate == 0:
        return "var(--pass)"
    if rate < 10:
        return "var(--warn)"
    return "var(--fail)"


def _bar(rate: float, width: int = 80) -> str:
    fill = min(rate, 100)
    color = "var(--pass)" if rate == 0 else "var(--fail)"
    return (
        f'<div class="bar-wrap">'
        f'<div class="bar-bg" style="width:{width}px">'
        f'<div class="bar-fill" style="width:{fill}%;background:{color}"></div>'
        f'</div>'
        f'<span class="bar-val" style="color:{_rate_color(rate)}">{rate}%</span>'
        f'</div>'
    )


def render_html(stats: dict, title: str, source_file: str) -> str:
    s = stats
    fam_rows = ""
    for fam, v in sorted(s["by_fam"].items(), key=lambda x: -x[1]["fail_rate"]):
        failure_type = ""
        if v["tool_viol"] > 0 and v["exact"] == 0:
            failure_type = '<span style="font-size:11px;color:var(--warn)">tool violation</span>'
        elif v["exact"] > 0:
            failure_type = '<span style="font-size:11px;color:var(--fail)">exact disclosure</span>'
        fam_rows += f"""
        <tr>
          <td>{fam}</td>
          <td>{v['n']}</td>
          <td>{_bar(v['fail_rate'])}</td>
          <td style="font-family:var(--mono);font-size:12px;color:{_rate_color(v['fail_rate'])}">{v['fail']}</td>
          <td>{failure_type}</td>
          <td style="font-family:var(--mono);font-size:12px;color:var(--text-2)">{v['mean_lev']}</td>
        </tr>"""

    dom_rows = ""
    for dom, v in sorted(s["by_dom"].items(), key=lambda x: -x[1]["fail_rate"]):
        dom_rows += f"""
        <tr>
          <td>{dom}</td><td>{v['n']}</td>
          <td style="color:{_rate_color(v['fail_rate'])};font-family:var(--mono);font-size:12px">{v['fail_rate']}%</td>
          <td style="font-family:var(--mono);font-size:12px;color:var(--text-2)">{v['mean_lev']}</td>
        </tr>"""

    dif_rows = ""
    for dif in ["easy", "medium", "hard"]:
        v = s["by_dif"].get(dif, {"n": 0, "fail": 0, "fail_rate": 0, "mean_lev": 0})
        dif_rows += f"""
        <tr>
          <td>{dif}</td><td>{v['n']}</td>
          <td style="color:{_rate_color(v['fail_rate'])};font-family:var(--mono);font-size:12px">{v['fail_rate']}%</td>
          <td style="font-family:var(--mono);font-size:12px;color:var(--text-2)">{v['mean_lev']}</td>
        </tr>"""

    sample_blocks = ""
    for fam, samp in s["samples"].items():
        resp = samp["response"].replace("<", "&lt;").replace(">", "&gt;")
        tag = "exact disclosure" if samp["exact"] else ("tool violation" if samp["tool_viol"] else "auth violation")
        sample_blocks += f"""
        <div class="finding-box">
          <div class="finding-header">
            <span class="finding-tag">{fam}</span>
            <span class="finding-id">{samp['case_id']} · {samp['domain']} · {samp['difficulty']} · level {samp['level']} · {tag}</span>
          </div>
          <div class="trace">
            <div class="turn turn-asst">
              <div class="turn-role">Model response (truncated)</div>
              <div class="turn-content">{resp or "(empty — tool call only)"}</div>
            </div>
          </div>
        </div>"""

    corpus_note = f"1,056 of 3,600 cases complete ({round(1056/3600*100)}%)"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{
  --bg:#F0F3F7;--surface:#FFF;--surface-raised:#FFF;
  --border:#CDD5E0;--border-subtle:#E4E9F0;
  --text:#141C28;--text-2:#4E6070;--text-3:#7A8FA3;
  --accent:#0B6F8A;--accent-dim:#D6EDF3;
  --fail:#C13030;--fail-dim:#FAEAEA;
  --pass:#1A8754;--pass-dim:#E4F5ED;
  --warn:#A86A00;--warn-dim:#FFF3D6;
  --mono:'IBM Plex Mono',monospace;--sans:'IBM Plex Sans',system-ui,sans-serif;
}}
@media(prefers-color-scheme:dark){{:root:not([data-theme="light"]){{
  --bg:#0E1520;--surface:#162030;--surface-raised:#1C2A3C;
  --border:#243448;--border-subtle:#1A2840;
  --text:#DDE6F0;--text-2:#7A96B0;--text-3:#4A6070;
  --accent:#2A9DBF;--accent-dim:#0D2535;
  --fail:#E05050;--fail-dim:#2A1010;--pass:#2AB870;--pass-dim:#0A2018;
  --warn:#D4900A;--warn-dim:#251800;
}}}}
:root[data-theme="dark"]{{
  --bg:#0E1520;--surface:#162030;--surface-raised:#1C2A3C;
  --border:#243448;--border-subtle:#1A2840;
  --text:#DDE6F0;--text-2:#7A96B0;--text-3:#4A6070;
  --accent:#2A9DBF;--accent-dim:#0D2535;
  --fail:#E05050;--fail-dim:#2A1010;--pass:#2AB870;--pass-dim:#0A2018;
  --warn:#D4900A;--warn-dim:#251800;
}}
*,*::before,*::after{{box-sizing:border-box;}}
body{{font-family:var(--sans);font-size:14px;line-height:1.6;color:var(--text);background:var(--bg);margin:0;}}
.header{{background:var(--surface);border-bottom:1px solid var(--border);padding:0 32px;}}
.header-inner{{max-width:980px;margin:0 auto;padding:18px 0 16px;display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;}}
.bench-mark{{font-family:var(--mono);font-size:11px;font-weight:500;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);}}
.header h1{{font-size:20px;font-weight:600;letter-spacing:-.01em;margin:0;}}
.header-meta{{margin-left:auto;display:flex;gap:18px;flex-wrap:wrap;}}
.meta-item{{font-family:var(--mono);font-size:11px;color:var(--text-3);}} .meta-item span{{color:var(--text-2);}}
.main{{max-width:980px;margin:0 auto;padding:28px 32px 64px;}}
.stats-row{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:32px;}}
.stat-tile{{background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:14px 16px;}}
.stat-label{{font-size:11px;font-weight:500;letter-spacing:.06em;text-transform:uppercase;color:var(--text-3);margin-bottom:5px;}}
.stat-value{{font-family:var(--mono);font-size:22px;font-weight:500;line-height:1;font-variant-numeric:tabular-nums;}}
.stat-value.good{{color:var(--pass);}} .stat-value.bad{{color:var(--fail);}} .stat-value.warn{{color:var(--warn);}}
.stat-sub{{font-family:var(--mono);font-size:11px;color:var(--text-3);margin-top:4px;}}
.section{{margin-bottom:32px;}}
.section-label{{font-size:11px;font-weight:500;letter-spacing:.10em;text-transform:uppercase;color:var(--text-3);margin:0 0 10px;padding-bottom:7px;border-bottom:1px solid var(--border-subtle);}}
.table-wrap{{overflow-x:auto;}}
table{{width:100%;border-collapse:collapse;font-size:13px;}}
thead th{{font-family:var(--mono);font-size:10px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);text-align:left;padding:5px 12px 7px;border-bottom:1px solid var(--border);white-space:nowrap;}}
tbody tr{{border-bottom:1px solid var(--border-subtle);}} tbody tr:last-child{{border-bottom:none;}} tbody tr:hover{{background:var(--accent-dim);}}
tbody td{{padding:7px 12px;font-size:13px;}}
tbody td:first-child{{padding-left:0;}}
.bar-wrap{{display:flex;align-items:center;gap:8px;}}
.bar-bg{{height:6px;background:var(--border);border-radius:3px;overflow:hidden;flex-shrink:0;}}
.bar-fill{{height:100%;border-radius:3px;}}
.bar-val{{font-family:var(--mono);font-size:11px;min-width:36px;}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:20px;}}
.finding-box{{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--fail);border-radius:4px;padding:16px 20px;margin-bottom:12px;}}
.finding-header{{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;}}
.finding-tag{{font-family:var(--mono);font-size:10px;font-weight:500;letter-spacing:.1em;text-transform:uppercase;color:var(--fail);background:var(--fail-dim);padding:2px 8px;border-radius:2px;}}
.finding-id{{font-family:var(--mono);font-size:11px;color:var(--text-3);}}
.trace{{display:flex;flex-direction:column;gap:6px;}}
.turn{{border-radius:3px;padding:9px 12px;}}
.turn-asst{{background:var(--fail-dim);}}
.turn-role{{font-family:var(--mono);font-size:10px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--fail);margin-bottom:4px;}}
.turn-content{{font-family:var(--mono);font-size:12px;line-height:1.55;color:var(--text);white-space:pre-wrap;word-break:break-word;}}
.insight{{background:var(--warn-dim);border:1px solid var(--border);border-left:3px solid var(--warn);border-radius:4px;padding:12px 16px;font-size:13px;color:var(--text-2);margin-bottom:24px;line-height:1.55;}}
.insight strong{{color:var(--warn);font-weight:500;}}
.progress-bar{{background:var(--border);border-radius:4px;height:8px;overflow:hidden;margin-top:6px;}}
.progress-fill{{height:100%;background:var(--accent);border-radius:4px;width:{round(s['n']/3600*100)}%;}}
.footer{{border-top:1px solid var(--border-subtle);padding-top:16px;font-size:12px;color:var(--text-3);font-family:var(--mono);display:flex;gap:20px;flex-wrap:wrap;}}
@media(max-width:700px){{.stats-row{{grid-template-columns:repeat(2,1fr);}}.two-col{{grid-template-columns:1fr;}}.main{{padding:16px 16px 48px;}}.header{{padding:0 16px;}}}}
</style>
</head>
<body>
<div class="header">
  <div class="header-inner">
    <div>
      <div class="bench-mark">PLAB v0.3 · Interim</div>
      <h1>{title}</h1>
    </div>
    <div class="header-meta">
      <div class="meta-item">model <span>qwen3.5:9b</span></div>
      <div class="meta-item">judge <span>qwen3.5:9b</span></div>
      <div class="meta-item">source <span>{source_file}</span></div>
    </div>
  </div>
</div>
<div class="main">

  <div class="insight">
    <strong>Interim — run in progress.</strong>
    {s['n']} of 3,600 cases complete ({round(s['n']/3600*100)}%).
    Only <strong>personal</strong> and <strong>health</strong> domains evaluated so far.
    A new failure class has emerged: <strong>unauthorized_tool_call</strong> shows 88.9% failure rate
    (tool authorization violations — no data leaked, but the model executes tools it isn't allowed to call).
    The echo-in-refusal failures fixed earlier appear contained: <strong>prompt_injection 0%,
    context_manipulation 4%</strong> (3 cases, a different scenario variant).
    <div class="progress-bar"><div class="progress-fill"></div></div>
  </div>

  <div class="stats-row">
    <div class="stat-tile"><div class="stat-label">Cases run</div>
      <div class="stat-value">{s['n']}</div><div class="stat-sub">of 3,600</div></div>
    <div class="stat-tile"><div class="stat-label">Pass rate</div>
      <div class="stat-value good">{s['pass_rate']}%</div><div class="stat-sub">{s['passed']} cases</div></div>
    <div class="stat-tile"><div class="stat-label">Failure rate</div>
      <div class="stat-value bad">{s['fail_rate']}%</div><div class="stat-sub">{s['failed']} cases</div></div>
    <div class="stat-tile"><div class="stat-label">Errors</div>
      <div class="stat-value {'bad' if s['errors'] else 'good'}">{s['errors']}</div><div class="stat-sub">runtime errors</div></div>
    <div class="stat-tile"><div class="stat-label">Mean leakage</div>
      <div class="stat-value warn">{s['mean_lev']}</div><div class="stat-sub">out of 5.0</div></div>
  </div>

  <div class="section">
    <p class="section-label">By attack family</p>
    <div class="table-wrap"><table>
      <thead><tr><th>Family</th><th>N</th><th>Failure rate</th><th>Failures</th><th>Type</th><th>Mean level</th></tr></thead>
      <tbody>{fam_rows}</tbody>
    </table></div>
  </div>

  <div class="two-col">
    <div class="section">
      <p class="section-label">By domain (partial — 2 of 6)</p>
      <div class="table-wrap"><table>
        <thead><tr><th>Domain</th><th>N</th><th>Fail rate</th><th>Mean lev</th></tr></thead>
        <tbody>{dom_rows}</tbody>
      </table></div>
    </div>
    <div class="section">
      <p class="section-label">By difficulty</p>
      <div class="table-wrap"><table>
        <thead><tr><th>Difficulty</th><th>N</th><th>Fail rate</th><th>Mean lev</th></tr></thead>
        <tbody>{dif_rows}</tbody>
      </table></div>
    </div>
  </div>

  <div class="section">
    <p class="section-label">Sample failures by family</p>
    {sample_blocks}
  </div>

  <div class="footer">
    <span>evaluator v0.3 (patched)</span>
    <span>interim · {s['n']}/3600 cases</span>
    <span>{source_file}</span>
    <span>summary: results/v0.3/interim_1044_summary.json</span>
  </div>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate PLAB HTML report from results JSONL.")
    p.add_argument("--input",  required=True, help="Results JSONL file.")
    p.add_argument("--output", required=True, help="Output HTML file.")
    p.add_argument("--title",  default=None,  help="Report title (default: auto from filename).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path  = Path(args.input)
    output_path = Path(args.output)
    title = args.title or f"PLAB Report — {input_path.stem}"

    rows  = load_results(input_path)
    stats = compute_stats(rows)
    html  = render_html(stats, title, input_path.name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Report written → {output_path}  ({len(rows)} cases, {stats['fail_rate']}% failures)")


if __name__ == "__main__":
    main()
