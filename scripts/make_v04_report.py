"""
Generate a PLAB v0.4 case detail report — shows system prompt, full conversation,
tool calls with results, and evaluation verdict for every case.

Run:
  python scripts/make_v04_report.py \
    --results results/v0.4/smoke_test.jsonl \
    --cases   schema/case.v0.4.examples.jsonl \
    --output  results/v0.4/smoke_test_report.html
"""

import argparse
import json
import html as html_module
from pathlib import Path


TIER_COLOR = {
    "tool_gated":     "#3b82f6",
    "implicit_authz": "#8b5cf6",
    "confused_deputy":"#f59e0b",
    "chained":        "#ef4444",
}

LEVEL_COLOR = {
    0: ("#d1fae5", "#065f46"),
    1: ("#fef3c7", "#92400e"),
    2: ("#fed7aa", "#9a3412"),
    3: ("#fecaca", "#991b1b"),
    4: ("#fca5a5", "#7f1d1d"),
    5: ("#f87171", "#450a0a"),
}


def h(s: str) -> str:
    return html_module.escape(str(s) if s is not None else "")


def load_data(results_path: Path, cases_path: Path):
    cases = {}
    with cases_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                c = json.loads(line)
                cases[c["id"]] = c

    results = []
    with results_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results, cases


def resolve_prompt(case: dict) -> str:
    session = case["environment"]["session"]
    prompt = case["environment"]["role_prompt"]
    for k, v in session.items():
        prompt = prompt.replace(f"{{session.{k}}}", str(v) if v is not None else "")
    return prompt


def render_case(result: dict, case: dict) -> str:
    cid = result["case_id"]
    tier = result.get("tier", "")
    tier_col = TIER_COLOR.get(tier, "#6b7280")
    family = result["attack_family"]
    difficulty = result.get("difficulty", "")
    status = result["status"]
    ev = result["evaluation"]
    level = ev.get("leakage_level", 0) or 0
    lbg, lfg = LEVEL_COLOR.get(level, ("#f3f4f6", "#111827"))
    violations = ev.get("violations", [])
    tool_calls = result["trace"].get("tool_calls", [])

    status_pill = (
        f'<span class="pill pill-pass">PASS</span>' if status == "passed"
        else f'<span class="pill pill-fail">FAIL</span>'
    )

    # System prompt
    sys_prompt = resolve_prompt(case)

    # Data store summary
    ds = case["environment"].get("data_store", {})
    ds_rows = ""
    for store_name, records in ds.items():
        for rec_id, rec_data in records.items():
            preview = json.dumps(rec_data, ensure_ascii=False)[:120] + ("…" if len(json.dumps(rec_data)) > 120 else "")
            ds_rows += f'<tr><td class="mono">{h(store_name)}</td><td class="mono">{h(rec_id)}</td><td class="mono small">{h(preview)}</td></tr>'

    # Tools
    tools_html = ""
    for t in case.get("tools", []):
        acl = t.get("access_control", {})
        mode = t.get("mock_behavior", {}).get("mode", "")
        mode_badge = (
            '<span class="badge badge-red">permissive</span>' if mode == "permissive"
            else '<span class="badge badge-blue">enforce_acl</span>'
        )
        protected = ", ".join(f'<code>{h(v)}</code>' for v in acl.get("protected_values", []))
        tools_html += f"""
        <div class="tool-def">
          <div class="tool-header">
            <code class="tool-name">{h(t['name'])}</code>
            {mode_badge}
          </div>
          <div class="tool-desc">{h(t['description'])}</div>
          <div class="tool-meta">
            <span class="label">allowed pattern:</span> <code>{h(acl.get('allowed_resource_pattern','*'))}</code>
            &nbsp;·&nbsp;
            <span class="label">violation:</span> {h(acl.get('violation_condition',''))}
          </div>
          {'<div class="tool-meta"><span class="label">protected values:</span> ' + protected + '</div>' if protected else ''}
        </div>"""

    # Conversation trace
    conv_html = ""
    for msg in result["trace"]["messages"]:
        role = msg.get("role", "")
        content = msg.get("content") or ""
        pre = msg.get("pre_supplied", False)
        if role == "user":
            pre_label = '<span class="pre-label">[history]</span>' if pre else '<span class="pre-label attacker">[attacker]</span>'
            conv_html += f'<div class="msg msg-user">{pre_label}<div class="msg-content">{h(content)}</div></div>'
        elif role == "assistant":
            pre_label = '<span class="pre-label">[scripted]</span>' if pre else ''
            conv_html += f'<div class="msg msg-assistant">{pre_label}<div class="msg-content">{h(content)}</div></div>'

    # Tool call trace
    tc_html = ""
    if tool_calls:
        for tc in tool_calls:
            auth_badge = (
                '<span class="badge badge-red">UNAUTHORIZED</span>'
                if not tc.get("authorized")
                else '<span class="badge badge-blue">authorized</span>'
            )
            args_str = json.dumps(tc.get("arguments", {}), ensure_ascii=False)
            result_str = json.dumps(tc.get("result", {}), ensure_ascii=False)[:300]
            tc_html += f"""
            <div class="tool-call {'tool-call-bad' if not tc.get('authorized') else ''}">
              <div class="tc-header">
                <code>{h(tc['name'])}({h(args_str)})</code>
                {auth_badge}
              </div>
              <div class="tc-result"><span class="label">Response:</span> <code class="small">{h(result_str)}</code></div>
            </div>"""
    else:
        tc_html = '<div class="no-tools">No tool calls made</div>'

    # Violations
    viol_html = ""
    if violations:
        for v in violations:
            viol_html += f"""
            <div class="violation">
              <code>{h(v['tool'])}({h(json.dumps(v['args']))})</code><br>
              <span class="label">Resource:</span> <code>{h(v['resource_id'])}</code>
              &nbsp;·&nbsp;
              <span class="label">Allowed:</span> <code>{h(v['allowed_pattern'])}</code>
              &nbsp;·&nbsp;
              <span class="label">Mode:</span> <code>{h(v['mode'])}</code><br>
              {h(v['condition'])}
            </div>"""
    else:
        viol_html = '<div class="no-viol">No ACL violations</div>'

    # Judge
    judge = ev.get("judge", {})
    judge_html = f"""
    <div class="judge-box">
      <span class="label">Judge model:</span> {h(judge.get('judge_model') or 'skipped')}
      &nbsp;·&nbsp;
      <span class="label">Score:</span> {h(judge.get('leakage_level', '—'))}
      &nbsp;·&nbsp;
      <span class="label">Confidence:</span> {h(judge.get('confidence', '—'))}<br>
      <span class="label">Rationale:</span> {h(judge.get('rationale', ''))}
    </div>"""

    # Flags
    flags = []
    if ev.get("exact_disclosure"):       flags.append('<span class="badge badge-red">exact_disclosure</span>')
    if ev.get("tool_authorization_violation"): flags.append('<span class="badge badge-red">tool_auth_violation</span>')
    if ev.get("authorization_violation"): flags.append('<span class="badge badge-red">auth_violation</span>')
    if ev.get("confused_deputy_violation"): flags.append('<span class="badge badge-red">confused_deputy</span>')
    if ev.get("cross_user_violation"):    flags.append('<span class="badge badge-red">cross_user</span>')
    if ev.get("partial_disclosure"):      flags.append('<span class="badge badge-amber">partial_disclosure</span>')
    if ev.get("inference_leakage"):       flags.append('<span class="badge badge-amber">inference_leakage</span>')
    if not flags: flags.append('<span class="badge badge-green">clean</span>')
    flags_html = " ".join(flags)

    return f"""
    <div class="case-card" id="{h(cid)}">
      <div class="case-header">
        <div class="case-id-row">
          <span class="case-id">{h(cid)}</span>
          {status_pill}
          <span class="tier-pill" style="background:{tier_col}">{h(tier)}</span>
          <span class="meta-pill">{h(family)}</span>
          <span class="meta-pill">{h(difficulty)}</span>
        </div>
        <div class="level-badge" style="background:{lbg};color:{lfg}">
          Leakage Level {level}
        </div>
      </div>

      <div class="flags">{flags_html}</div>

      <div class="section-label">System prompt (model's view)</div>
      <pre class="code-block">{h(sys_prompt)}</pre>

      <div class="two-col">
        <div>
          <div class="section-label">Available tools</div>
          {tools_html}
        </div>
        <div>
          <div class="section-label">Data store (evaluator-only)</div>
          <table class="ds-table">
            <thead><tr><th>Store</th><th>Key</th><th>Data</th></tr></thead>
            <tbody>{ds_rows}</tbody>
          </table>
        </div>
      </div>

      <div class="section-label">Conversation</div>
      <div class="conv">{conv_html}</div>

      <div class="section-label">Tool calls</div>
      {tc_html}

      <div class="section-label">ACL violations detected</div>
      {viol_html}

      <div class="section-label">Judge</div>
      {judge_html}

      <div class="section-label">Scenario context</div>
      <div class="meta-box">
        <div><span class="label">Real-world analogue:</span> {h(case.get('metadata',{}).get('real_world_analogue',''))}</div>
        <div><span class="label">Why realistic:</span> {h(case.get('metadata',{}).get('why_realistic',''))}</div>
        <div><span class="label">Attack goal:</span> {h(case['attack']['goal'])}</div>
        <div><span class="label">Target resource:</span> <code>{h(case['attack'].get('target_resource',''))}</code></div>
      </div>
    </div>"""


def render_html(results: list, cases: dict, title: str) -> str:
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    errors = sum(1 for r in results if r["status"] == "error")

    by_tier = {}
    for r in results:
        t = r.get("tier", "unknown")
        by_tier.setdefault(t, {"pass": 0, "fail": 0})
        if r["status"] == "passed": by_tier[t]["pass"] += 1
        else: by_tier[t]["fail"] += 1

    tier_rows = "".join(
        '<tr><td><span class="tier-pill" style="background:{col}">{tier}</span></td>'
        '<td>{total}</td>'
        '<td style="color:#16a34a">{p}</td>'
        '<td style="color:#dc2626">{f}</td></tr>'.format(
            col=TIER_COLOR.get(t, "#6b7280"), tier=h(t),
            total=v["pass"]+v["fail"], p=v["pass"], f=v["fail"]
        )
        for t, v in sorted(by_tier.items())
    )

    cases_html = "".join(render_case(r, cases[r["case_id"]]) for r in results)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{h(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
  :root {{
    --bg: #f8fafc;
    --surface: #ffffff;
    --surface2: #f1f5f9;
    --border: #e2e8f0;
    --text: #0f172a;
    --muted: #64748b;
    --user-bg: #eff6ff;
    --user-border: #bfdbfe;
    --asst-bg: #f0fdf4;
    --asst-border: #bbf7d0;
    --font: 'Inter', system-ui, sans-serif;
    --mono: 'JetBrains Mono', 'Fira Code', monospace;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #0f172a; --surface: #1e293b; --surface2: #334155;
      --border: #334155; --text: #f1f5f9; --muted: #94a3b8;
      --user-bg: #1e3a5f; --user-border: #3b82f6;
      --asst-bg: #14532d; --asst-border: #22c55e;
    }}
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; }}
  body {{ font-family: var(--font); background: var(--bg); color: var(--text);
          font-size: 14px; line-height: 1.6; padding: 32px 24px; }}
  .page-header {{ max-width: 1100px; margin: 0 auto 32px; }}
  h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
  .subtitle {{ color: var(--muted); font-size: 13px; margin-bottom: 20px; }}
  .summary-grid {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
  .stat {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
           padding: 12px 20px; min-width: 90px; text-align: center; }}
  .stat-num {{ font-size: 28px; font-weight: 700; line-height: 1; }}
  .stat-label {{ font-size: 11px; color: var(--muted); text-transform: uppercase;
                  letter-spacing: .05em; margin-top: 2px; }}
  .tier-table {{ background: var(--surface); border: 1px solid var(--border);
                  border-radius: 8px; border-collapse: collapse; overflow: hidden; }}
  .tier-table th, .tier-table td {{ padding: 8px 14px; text-align: left; border-bottom: 1px solid var(--border); }}
  .tier-table th {{ font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }}
  .case-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
                max-width: 1100px; margin: 0 auto 28px; overflow: hidden; }}
  .case-header {{ display: flex; justify-content: space-between; align-items: flex-start;
                   padding: 16px 20px; border-bottom: 1px solid var(--border); background: var(--surface2); }}
  .case-id-row {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
  .case-id {{ font-family: var(--mono); font-weight: 500; font-size: 13px; }}
  .level-badge {{ padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; white-space: nowrap; }}
  .flags {{ padding: 10px 20px; border-bottom: 1px solid var(--border); display: flex; gap: 6px; flex-wrap: wrap; }}
  .section-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase;
                     letter-spacing: .07em; color: var(--muted); padding: 12px 20px 4px; }}
  pre.code-block {{ font-family: var(--mono); font-size: 12px; background: var(--surface2);
                     border: 1px solid var(--border); border-radius: 6px; padding: 12px 14px;
                     margin: 0 20px 8px; white-space: pre-wrap; word-break: break-word;
                     overflow-x: auto; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0; }}
  .two-col > div {{ padding: 0 20px 12px; }}
  .tool-def {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 6px;
               padding: 10px 12px; margin-bottom: 8px; }}
  .tool-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }}
  .tool-name {{ font-size: 12px; font-weight: 500; }}
  .tool-desc {{ font-size: 12px; color: var(--muted); margin-bottom: 4px; }}
  .tool-meta {{ font-size: 11px; color: var(--muted); }}
  .ds-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  .ds-table th, .ds-table td {{ padding: 4px 6px; border: 1px solid var(--border); vertical-align: top; }}
  .ds-table th {{ background: var(--surface2); font-weight: 600; }}
  .conv {{ padding: 0 20px 12px; display: flex; flex-direction: column; gap: 8px; }}
  .msg {{ border-radius: 8px; padding: 10px 14px; font-size: 13px; }}
  .msg-user {{ background: var(--user-bg); border: 1px solid var(--user-border); }}
  .msg-assistant {{ background: var(--asst-bg); border: 1px solid var(--asst-border); }}
  .msg-content {{ white-space: pre-wrap; word-break: break-word; }}
  .pre-label {{ font-size: 10px; font-weight: 600; text-transform: uppercase;
                 letter-spacing: .05em; color: var(--muted); margin-bottom: 4px;
                 display: inline-block; }}
  .pre-label.attacker {{ color: #dc2626; }}
  .tool-call {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 6px;
                padding: 8px 12px; margin: 0 20px 8px; font-size: 12px; }}
  .tool-call-bad {{ border-color: #fca5a5; background: #fff1f2; }}
  .tc-header {{ display: flex; align-items: flex-start; gap: 8px; margin-bottom: 4px; word-break: break-all; }}
  .tc-result {{ color: var(--muted); }}
  .violation {{ background: #fff1f2; border: 1px solid #fca5a5; border-radius: 6px;
                padding: 8px 12px; margin: 0 20px 8px; font-size: 12px; }}
  .no-tools, .no-viol {{ padding: 4px 20px 10px; color: var(--muted); font-size: 12px; }}
  .judge-box {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 6px;
                padding: 8px 12px; margin: 0 20px 8px; font-size: 12px; }}
  .meta-box {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 6px;
               padding: 10px 14px; margin: 0 20px 16px; font-size: 12px;
               display: flex; flex-direction: column; gap: 4px; }}
  .pill {{ padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
  .pill-pass {{ background: #d1fae5; color: #065f46; }}
  .pill-fail {{ background: #fee2e2; color: #991b1b; }}
  .tier-pill {{ padding: 2px 8px; border-radius: 12px; font-size: 11px;
                font-weight: 600; color: #fff; }}
  .meta-pill {{ padding: 2px 8px; border-radius: 12px; font-size: 11px;
                background: var(--surface2); border: 1px solid var(--border); color: var(--muted); }}
  .badge {{ padding: 1px 7px; border-radius: 10px; font-size: 10px; font-weight: 600; }}
  .badge-red {{ background: #fee2e2; color: #991b1b; }}
  .badge-blue {{ background: #dbeafe; color: #1e40af; }}
  .badge-amber {{ background: #fef3c7; color: #92400e; }}
  .badge-green {{ background: #d1fae5; color: #065f46; }}
  .label {{ font-weight: 600; }}
  .mono {{ font-family: var(--mono); }}
  .small {{ font-size: 11px; }}
  code {{ font-family: var(--mono); font-size: 11px; background: var(--surface2);
           padding: 1px 4px; border-radius: 3px; }}
  @media (max-width: 700px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="page-header">
  <h1>{h(title)}</h1>
  <div class="subtitle">PLAB v0.4 · tool-gated data, implicit authorization, confused deputy, chained attacks</div>
  <div class="summary-grid">
    <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">Total</div></div>
    <div class="stat"><div class="stat-num" style="color:#16a34a">{passed}</div><div class="stat-label">Passed</div></div>
    <div class="stat"><div class="stat-num" style="color:#dc2626">{failed}</div><div class="stat-label">Failed</div></div>
    <div class="stat"><div class="stat-num" style="color:#9ca3af">{errors}</div><div class="stat-label">Errors</div></div>
  </div>
  <table class="tier-table">
    <thead><tr><th>Tier</th><th>Cases</th><th>Pass</th><th>Fail</th></tr></thead>
    <tbody>{tier_rows}</tbody>
  </table>
</div>
{cases_html}
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="results/v0.4/smoke_test.jsonl")
    parser.add_argument("--cases",   default="schema/case.v0.4.examples.jsonl")
    parser.add_argument("--output",  default="results/v0.4/smoke_test_report.html")
    parser.add_argument("--title",   default="PLAB v0.4 — Smoke Test Report")
    args = parser.parse_args()

    results, cases = load_data(Path(args.results), Path(args.cases))
    html = render_html(results, cases, args.title)
    Path(args.output).write_text(html, encoding="utf-8")
    print(f"Written {len(results)} cases → {args.output}")


if __name__ == "__main__":
    main()
