"""
Generate a detailed HTML report of all failed cases, including full prompt,
system context, attack conversation, model response, and evaluation verdict.

Usage:
    /Users/nidhi/git_repos/agentscope/.venv/bin/python scripts/make_failures_report.py \
        --results results/v0.3/full_20260911_025506.jsonl \
        --cases   data/v0.3/cases.jsonl \
        --output  results/v0.3/failures_detail_report.html

    # Filter to one family:
    /Users/nidhi/git_repos/agentscope/.venv/bin/python scripts/make_failures_report.py \
        --results results/v0.3/full_20260911_025506.jsonl \
        --cases   data/v0.3/cases.jsonl \
        --output  results/v0.3/failures_tool_call.html \
        --family  unauthorized_tool_call
"""

from __future__ import annotations

import argparse
import html as html_mod
import json
from collections import Counter
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def esc(s: str) -> str:
    return html_mod.escape(str(s))


def verdict_pill(ev: dict) -> str:
    parts = []
    if ev.get("exact_disclosure"):
        parts.append('<span class="pill pill-fail">exact disclosure</span>')
    if ev.get("tool_authorization_violation"):
        parts.append('<span class="pill pill-warn">tool violation</span>')
    if ev.get("authorization_violation") and not ev.get("exact_disclosure"):
        parts.append('<span class="pill pill-warn">auth violation</span>')
    if ev.get("partial_disclosure"):
        parts.append('<span class="pill pill-warn">partial</span>')
    if ev.get("inference_leakage"):
        parts.append('<span class="pill pill-info">inference</span>')
    return " ".join(parts) or '<span class="pill pill-pass">no data leaked</span>'


def render_case(result: dict, case: dict | None) -> str:
    ev   = result["evaluation"]
    msgs = result.get("trace", {}).get("messages", [])
    tool_calls = result.get("trace", {}).get("tool_calls", [])
    case_id = result["case_id"]
    lev = ev["leakage_level"]

    # ── system context from corpus ──
    ctx_html = ""
    if case:
        sc = case.get("scenario", {})
        priv = sc.get("private_context", [])
        vis  = sc.get("visible_context", [])
        pol  = sc.get("authorization_policy", [])
        tools = case.get("tools", [])
        atk   = case.get("attack", {})

        priv_lines = "\n".join(f"  {esc(p)}" for p in priv)
        vis_lines  = "\n".join(f"  {esc(v)}" for v in vis)
        pol_lines  = "\n".join(
            f"  {esc(p['principal'])} → {esc(p['asset'])}: {'ALLOWED' if p['allowed'] else 'NOT ALLOWED'}"
            for p in pol
        )
        tool_lines = "\n".join(f"  {esc(t['name'])} ({esc(t.get('description',''))})" for t in tools) or "  (none)"
        goal = esc(atk.get("goal", ""))

        ctx_html = f"""
        <div class="ctx-block">
          <div class="ctx-label">Private context</div>
          <pre class="ctx-pre">{priv_lines or "  (empty)"}</pre>
        </div>
        <div class="ctx-block">
          <div class="ctx-label">Visible context</div>
          <pre class="ctx-pre">{vis_lines or "  (empty)"}</pre>
        </div>
        <div class="ctx-block">
          <div class="ctx-label">Authorization policy</div>
          <pre class="ctx-pre">{pol_lines or "  (empty)"}</pre>
        </div>
        <div class="ctx-block">
          <div class="ctx-label">Available tools</div>
          <pre class="ctx-pre">{tool_lines}</pre>
        </div>
        <div class="ctx-block">
          <div class="ctx-label">Attacker goal</div>
          <pre class="ctx-pre">  {goal}</pre>
        </div>"""

    # ── conversation trace ──
    turn_html = ""
    tc_by_turn: dict[int, list] = {}
    for tc in tool_calls:
        tc_by_turn.setdefault(tc["turn"], []).append(tc)

    for m in msgs:
        role    = m.get("role", "")
        content = esc(m.get("content", "") or "")
        turn    = m.get("turn", "")
        css     = {"user": "turn-user", "assistant": "turn-asst", "system": "turn-sys"}.get(role, "turn-user")
        label   = {"user": "Attacker", "assistant": "Model", "system": "System"}.get(role, role)

        # inject tool calls after assistant turn
        tc_block = ""
        if role == "assistant" and turn in tc_by_turn:
            for tc in tc_by_turn[turn]:
                auth_label = "AUTHORIZED" if tc.get("authorized") else "BLOCKED"
                auth_color = "var(--pass)" if tc.get("authorized") else "var(--fail)"
                tc_block += f"""
                <div class="tool-call">
                  <span class="tool-name">{esc(tc['name'])}</span>
                  <span class="tool-auth" style="color:{auth_color}">{auth_label}</span>
                  <span class="tool-reason">{esc(tc.get('blocked_reason') or '')}</span>
                </div>"""

        turn_html += f"""
        <div class="turn {css}">
          <div class="turn-role">{label}{' · turn ' + str(turn) if turn != '' else ''}</div>
          <div class="turn-content">{content or '<em style="opacity:.5">(empty — tool call only)</em>'}</div>
          {tc_block}
        </div>"""

    # ── evaluation verdict ──
    judge = ev.get("judge", {})
    judge_html = f"""
    <div class="verdict-row">
      <span class="verdict-label">Final level</span>
      <span class="lev lev-{min(lev,5)}">{lev}</span>
      {verdict_pill(ev)}
    </div>
    <div class="verdict-row" style="margin-top:6px;font-size:12px;color:var(--text-3);font-family:var(--mono);">
      judge level={judge.get('leakage_level','—')}
      · confidence={judge.get('confidence','—')}
      · {esc(judge.get('rationale','') or '')}
    </div>"""

    return f"""
    <div class="case-card" id="{esc(case_id)}">
      <div class="case-header">
        <div class="case-id">{esc(case_id)}</div>
        <div class="case-tags">
          <span class="tag">{esc(result['attack_family'])}</span>
          <span class="tag">{esc(result['domain'])}</span>
          <span class="tag">{esc(result.get('difficulty',''))}</span>
        </div>
      </div>

      <details>
        <summary class="section-summary">System context &amp; attack goal</summary>
        <div class="details-body">{ctx_html or '<p style="color:var(--text-3);font-size:13px">Case not found in corpus.</p>'}</div>
      </details>

      <div class="conv-label">Conversation</div>
      <div class="trace">{turn_html}</div>

      <div class="verdict">{judge_html}</div>
    </div>"""


def render_html(failures: list[dict], cases_map: dict, title: str, source: str) -> str:
    n_fail = len(failures)
    by_fam = Counter(r["attack_family"] for r in failures)
    by_dom = Counter(r["domain"] for r in failures)

    nav_fam = "".join(
        f'<button class="nav-btn" onclick="filterFamily(\'{fam}\')">'
        f'{fam} <span class="nav-count">{cnt}</span></button>'
        for fam, cnt in sorted(by_fam.items(), key=lambda x: -x[1])
    )
    nav_dom = "".join(
        f'<button class="nav-btn" onclick="filterDomain(\'{dom}\')">'
        f'{dom} <span class="nav-count">{cnt}</span></button>'
        for dom, cnt in sorted(by_dom.items(), key=lambda x: -x[1])
    )

    cases_html = "".join(
        render_case(r, cases_map.get(r["case_id"]))
        for r in sorted(failures, key=lambda x: (x["attack_family"], x["domain"], x.get("difficulty",""), x["case_id"]))
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{
  --bg:#F0F3F7;--surface:#FFF;--surface-raised:#F7F9FC;
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

/* header */
.header{{background:var(--surface);border-bottom:1px solid var(--border);padding:0 24px;position:sticky;top:0;z-index:100;}}
.header-inner{{max-width:900px;margin:0 auto;padding:14px 0 12px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;}}
.bench-mark{{font-family:var(--mono);font-size:10px;font-weight:500;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);}}
.header h1{{font-size:17px;font-weight:600;margin:0;}}
.header-count{{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--fail);font-weight:500;}}

/* sidebar + main layout */
.layout{{max-width:900px;margin:0 auto;padding:24px 24px 64px;display:grid;grid-template-columns:200px 1fr;gap:24px;}}
.sidebar{{position:sticky;top:64px;height:fit-content;}}
.sidebar-section{{margin-bottom:20px;}}
.sidebar-label{{font-size:10px;font-weight:500;letter-spacing:.1em;text-transform:uppercase;color:var(--text-3);margin-bottom:8px;}}
.nav-btn{{display:block;width:100%;text-align:left;background:none;border:none;border-radius:3px;padding:5px 8px;font-family:var(--sans);font-size:12px;color:var(--text-2);cursor:pointer;margin-bottom:2px;}}
.nav-btn:hover,.nav-btn.active{{background:var(--accent-dim);color:var(--accent);}}
.nav-btn.active{{font-weight:500;}}
.nav-count{{float:right;font-family:var(--mono);font-size:11px;color:var(--text-3);}}
.search-box{{width:100%;padding:6px 8px;border:1px solid var(--border);border-radius:3px;background:var(--surface);color:var(--text);font-size:12px;font-family:var(--mono);margin-bottom:12px;}}
.search-box:focus{{outline:none;border-color:var(--accent);}}
.clear-btn{{display:block;width:100%;text-align:center;font-size:11px;color:var(--text-3);background:none;border:none;cursor:pointer;padding:4px;}}
.clear-btn:hover{{color:var(--accent);}}

/* case cards */
.case-card{{background:var(--surface);border:1px solid var(--border);border-radius:4px;margin-bottom:16px;overflow:hidden;}}
.case-header{{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid var(--border-subtle);background:var(--fail-dim);flex-wrap:wrap;}}
.case-id{{font-family:var(--mono);font-size:11px;font-weight:500;color:var(--fail);}}
.case-tags{{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto;}}
.tag{{font-family:var(--mono);font-size:10px;padding:2px 7px;border-radius:2px;background:var(--surface);border:1px solid var(--border);color:var(--text-2);}}

/* collapsible context */
details{{border-bottom:1px solid var(--border-subtle);}}
summary.section-summary{{padding:8px 16px;font-size:12px;font-weight:500;color:var(--text-2);cursor:pointer;list-style:none;user-select:none;}}
summary.section-summary::-webkit-details-marker{{display:none;}}
summary.section-summary::before{{content:"▶ ";font-size:9px;color:var(--text-3);}}
details[open] summary.section-summary::before{{content:"▼ ";}}
.details-body{{padding:0 16px 12px;}}
.ctx-block{{margin-bottom:10px;}}
.ctx-label{{font-size:10px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);margin-bottom:3px;}}
.ctx-pre{{font-family:var(--mono);font-size:12px;color:var(--text-2);margin:0;white-space:pre-wrap;word-break:break-word;background:var(--surface-raised);border:1px solid var(--border-subtle);border-radius:3px;padding:8px 10px;line-height:1.55;}}

/* conversation */
.conv-label{{font-size:10px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);padding:10px 16px 6px;}}
.trace{{display:flex;flex-direction:column;gap:6px;padding:0 16px 12px;}}
.turn{{border-radius:3px;padding:9px 12px;}}
.turn-user{{background:var(--accent-dim);}}
.turn-asst{{background:var(--fail-dim);}}
.turn-sys{{background:var(--surface-raised);border:1px solid var(--border-subtle);}}
.turn-role{{font-family:var(--mono);font-size:10px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;margin-bottom:4px;}}
.turn-user .turn-role{{color:var(--accent);}}
.turn-asst .turn-role{{color:var(--fail);}}
.turn-sys  .turn-role{{color:var(--text-3);}}
.turn-content{{font-family:var(--mono);font-size:12px;line-height:1.55;color:var(--text);white-space:pre-wrap;word-break:break-word;}}
.tool-call{{margin-top:8px;display:flex;align-items:center;gap:8px;font-family:var(--mono);font-size:11px;background:var(--surface);border:1px solid var(--border);border-radius:2px;padding:4px 8px;}}
.tool-name{{font-weight:500;color:var(--text);}}
.tool-auth{{font-weight:500;}}
.tool-reason{{color:var(--text-3);}}

/* verdict */
.verdict{{padding:10px 16px 12px;border-top:1px solid var(--border-subtle);background:var(--surface-raised);}}
.verdict-row{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}}
.verdict-label{{font-size:11px;font-weight:500;color:var(--text-3);font-family:var(--mono);}}
.lev{{display:inline-block;font-family:var(--mono);font-size:12px;font-weight:500;padding:1px 7px;border-radius:2px;}}
.lev-0{{background:var(--pass-dim);color:var(--pass);}}
.lev-1,.lev-2,.lev-3{{background:var(--warn-dim);color:var(--warn);}}
.lev-4,.lev-5{{background:var(--fail-dim);color:var(--fail);}}
.pill{{font-family:var(--mono);font-size:11px;font-weight:500;padding:2px 8px;border-radius:3px;}}
.pill-fail{{background:var(--fail-dim);color:var(--fail);}}
.pill-warn{{background:var(--warn-dim);color:var(--warn);}}
.pill-pass{{background:var(--pass-dim);color:var(--pass);}}
.pill-info{{background:var(--accent-dim);color:var(--accent);}}

.hidden{{display:none!important;}}
.footer{{grid-column:1/-1;border-top:1px solid var(--border-subtle);padding-top:16px;font-size:12px;color:var(--text-3);font-family:var(--mono);}}

@media(max-width:700px){{.layout{{grid-template-columns:1fr;}}.sidebar{{position:static;}}}}
</style>
</head>
<body>
<div class="header">
  <div class="header-inner">
    <div>
      <div class="bench-mark">PLAB v0.3 · Failure Detail</div>
      <h1>{esc(title)}</h1>
    </div>
    <div class="header-count">{n_fail} failures</div>
  </div>
</div>

<div class="layout">
  <aside class="sidebar">
    <input class="search-box" type="text" placeholder="Search case ID…" oninput="filterSearch(this.value)">
    <div class="sidebar-section">
      <div class="sidebar-label">Attack family</div>
      <button class="nav-btn active" onclick="clearFilters()">All families <span class="nav-count">{n_fail}</span></button>
      {nav_fam}
    </div>
    <div class="sidebar-section">
      <div class="sidebar-label">Domain</div>
      {nav_dom}
    </div>
    <button class="clear-btn" onclick="clearFilters()">Clear filters</button>
  </aside>

  <main>
    <div id="cases">
      {cases_html}
    </div>
    <div class="footer">
      source: {esc(source)} &nbsp;·&nbsp; generated by scripts/make_failures_report.py
    </div>
  </main>
</div>

<script>
let activeFamily = null;
let activeDomain = null;
let searchQuery  = "";

function applyFilters() {{
  document.querySelectorAll(".case-card").forEach(card => {{
    const id  = card.id;
    const fam = card.querySelector(".case-tags .tag:nth-child(1)")?.textContent.trim();
    const dom = card.querySelector(".case-tags .tag:nth-child(2)")?.textContent.trim();
    const hide =
      (activeFamily && fam !== activeFamily) ||
      (activeDomain && dom !== activeDomain) ||
      (searchQuery && !id.toLowerCase().includes(searchQuery));
    card.classList.toggle("hidden", !!hide);
  }});
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
}}
function filterFamily(f) {{ activeFamily = activeFamily === f ? null : f; applyFilters(); }}
function filterDomain(d) {{ activeDomain = activeDomain === d ? null : d; applyFilters(); }}
function filterSearch(v) {{ searchQuery = v.toLowerCase(); applyFilters(); }}
function clearFilters() {{ activeFamily = null; activeDomain = null; searchQuery = ""; document.querySelector(".search-box").value = ""; applyFilters(); }}
</script>
</body>
</html>"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate PLAB detailed failures report.")
    p.add_argument("--results", required=True, help="Results JSONL file.")
    p.add_argument("--cases",   required=True, help="Corpus cases JSONL file.")
    p.add_argument("--output",  required=True, help="Output HTML file.")
    p.add_argument("--title",   default=None,  help="Report title.")
    p.add_argument("--family",  default=None,  help="Filter to one attack family.")
    p.add_argument("--domain",  default=None,  help="Filter to one domain.")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    results = load_jsonl(Path(args.results))
    failures = [r for r in results if r["status"] == "failed"]
    if args.family:
        failures = [r for r in failures if r["attack_family"] == args.family]
    if args.domain:
        failures = [r for r in failures if r["domain"] == args.domain]

    cases_map = {c["id"]: c for c in load_jsonl(Path(args.cases))}

    title = args.title or f"PLAB Failures — {Path(args.results).stem}"
    html  = render_html(failures, cases_map, title, Path(args.results).name)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Report written → {out}  ({len(failures)} failures)")


if __name__ == "__main__":
    main()
