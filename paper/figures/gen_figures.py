"""Generate all figures for the PLAB paper."""
import json, math, sys
from pathlib import Path

# We generate SVG so the paper can embed them without matplotlib dependency.
# All figures saved to paper/figures/.

OUT = Path(__file__).parent

# ─────────────────────────────────────────────────────────────────────────────
# Figure 1 — Judge false-positive rate comparison (bar chart)
# ─────────────────────────────────────────────────────────────────────────────
def fig1_judge_fp():
    bars = [
        ("qwen3.5:3b\n(v0.3 judge)", 100, "#dc2626"),
        ("claude-opus-4-7\n(contaminated)", 0, "#7c3aed"),
        ("claude-opus-4-7\n(clean)", 2, "#7c3aed"),
    ]
    W, H = 420, 260
    margin = dict(l=60, r=20, t=40, b=70)
    bw = 80
    gap = 40
    total_bar_w = len(bars) * (bw + gap) - gap
    x0 = margin["l"] + (W - margin["l"] - margin["r"] - total_bar_w) / 2
    chart_h = H - margin["t"] - margin["b"]

    def bx(i): return x0 + i * (bw + gap)
    def by(v): return margin["t"] + chart_h * (1 - v / 100)

    rects = ""
    labels = ""
    for i, (name, val, col) in enumerate(bars):
        x = bx(i); y = by(val); bh = chart_h - (y - margin["t"])
        rects += f'<rect x="{x}" y="{y:.1f}" width="{bw}" height="{bh:.1f}" fill="{col}" rx="3"/>'
        rects += f'<text x="{x+bw/2:.1f}" y="{y-6:.1f}" text-anchor="middle" font-size="13" font-weight="700" fill="{col}">{val}%</text>'
        # multi-line label
        lines = name.split("\n")
        for j, line in enumerate(lines):
            ly = H - margin["b"] + 16 + j * 14
            labels += f'<text x="{x+bw/2:.1f}" y="{ly}" text-anchor="middle" font-size="10" fill="#64748b">{line}</text>'

    # y-axis
    axis = f'<line x1="{margin["l"]}" y1="{margin["t"]}" x2="{margin["l"]}" y2="{margin["t"]+chart_h}" stroke="#e2e8f0" stroke-width="1"/>'
    for tick in [0, 25, 50, 75, 100]:
        ty = by(tick)
        axis += f'<line x1="{margin["l"]-4}" y1="{ty:.1f}" x2="{W-margin["r"]}" y2="{ty:.1f}" stroke="#f1f5f9" stroke-width="1"/>'
        axis += f'<text x="{margin["l"]-8}" y="{ty+4:.1f}" text-anchor="end" font-size="10" fill="#94a3b8">{tick}%</text>'

    title = f'<text x="{W/2}" y="22" text-anchor="middle" font-size="13" font-weight="600" fill="#1e293b">False Positive Rate — Cases Where Model Clearly Refused (n=100)</text>'

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'style="font-family:\'IBM Plex Sans\',system-ui,sans-serif;background:#fff">'
           f'{title}{axis}{rects}{labels}</svg>')
    (OUT / "fig1_judge_fp.svg").write_text(svg)
    print("fig1 done")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 2 — v0.3 failure decomposition (stacked bar / sankey-style)
# ─────────────────────────────────────────────────────────────────────────────
def fig2_v03_decomposition():
    # Top-down tree layout — no overlapping labels, each level clearly separated:
    #              [3,600]
    #             /       \
    #       [1,441]      [2,159]
    #       /     \
    #   [412]   [1,029]
    #            /    \
    #          [683]  [346]   + callout box
    W, H = 560, 320
    NW = 110   # node width
    NH = 38    # node height

    # Vertical positions of each level (top of node) — 76px between levels
    LY = [26, 102, 178, 248]

    # Horizontal centers — all verified to stay within [10, 550]
    # L0: single node
    CX = dict(
        root  = 280.0,
        flag  = 175.0,   # L1 left
        pass_ = 385.0,   # L1 right   (175+130+130+... symmetric around 280)
        true  = 110.0,   # L2 left:  175 - (110+20+110)/2 + 55 = 110
        jonly = 240.0,   # L2 right: 110 + 110 + 20 = 240
        hall  = 175.0,   # L3 left:  240 - (110+20+110)/2 + 55 = 175
        ambig = 305.0,   # L3 right: 175 + 110 + 20 = 305
    )
    # Verify no overflow
    for k, cx in CX.items():
        assert cx - NW/2 >= 8, f"{k} left overflow"
        assert cx + NW/2 <= W - 8, f"{k} right overflow"

    COLORS = dict(
        root="#475569", flag="#dc2626", pass_="#16a34a",
        true="#16a34a", jonly="#f59e0b", hall="#dc2626", ambig="#64748b",
    )
    LABELS = dict(
        root =("3,600",  "all cases"),
        flag =("1,441",  "judge-flagged (40%)"),
        pass_=("2,159",  "passed (60%)"),
        true =("412",    "true failures (11.4%)"),
        jonly=("1,029",  "judge-only (28.6%)"),
        hall =("683",    "confirmed hall. (19%)"),
        ambig=("346",    "ambiguous (9.6%)"),
    )
    LEVELS = dict(root=0, flag=1, pass_=1, true=2, jonly=2, hall=3, ambig=3)
    EDGES  = [("root","flag","#dc2626"), ("root","pass_","#16a34a"),
              ("flag","true","#16a34a"), ("flag","jonly","#f59e0b"),
              ("jonly","hall","#dc2626"), ("jonly","ambig","#64748b")]

    def nrect(key):
        cx = CX[key]; y = LY[LEVELS[key]]; col = COLORS[key]
        x = cx - NW / 2
        val, sub = LABELS[key]
        s  = f'<rect x="{x:.1f}" y="{y}" width="{NW}" height="{NH}" fill="{col}" rx="4" fill-opacity="0.13" stroke="{col}" stroke-width="1.5"/>'
        s += f'<text x="{cx:.1f}" y="{y+NH/2-3:.1f}" text-anchor="middle" font-size="11" font-weight="700" fill="{col}">{val}</text>'
        s += f'<text x="{cx:.1f}" y="{y+NH/2+11:.1f}" text-anchor="middle" font-size="8" fill="{col}">{sub}</text>'
        return s

    def nedge(src, dst, col):
        x1 = CX[src]; y1 = LY[LEVELS[src]] + NH
        x2 = CX[dst]; y2 = LY[LEVELS[dst]]
        return f'<line x1="{x1:.1f}" y1="{y1}" x2="{x2:.1f}" y2="{y2}" stroke="{col}" stroke-width="1.5" stroke-opacity="0.45"/>'

    body = ""
    for src, dst, col in EDGES:
        body += nedge(src, dst, col)
    for key in ("root","flag","pass_","true","jonly","hall","ambig"):
        body += nrect(key)

    # Callout box: key finding — placed to the right of jonly node (level 2), connected with short horizontal line
    jonly_right = CX["jonly"] + NW / 2   # 295
    kx, ky, kw, kh = int(jonly_right) + 14, LY[2] + 2, 145, 46
    body += f'<rect x="{kx}" y="{ky}" width="{kw}" height="{kh}" fill="#fef2f2" stroke="#dc2626" stroke-width="1.2" rx="4"/>'
    body += f'<text x="{kx+kw//2}" y="{ky+15}" text-anchor="middle" font-size="9.5" font-weight="700" fill="#dc2626">47.4% of all flags</text>'
    body += f'<text x="{kx+kw//2}" y="{ky+28}" text-anchor="middle" font-size="8.5" fill="#dc2626">are hallucinations</text>'
    body += f'<text x="{kx+kw//2}" y="{ky+41}" text-anchor="middle" font-size="8" fill="#94a3b8">(683 / 1,441)</text>'
    # Short horizontal connector from jonly right edge to callout left edge — no nodes in between
    body += f'<line x1="{jonly_right:.1f}" y1="{LY[2]+NH//2}" x2="{kx}" y2="{ky+kh//2}" stroke="#dc2626" stroke-width="1" stroke-dasharray="4,3" stroke-opacity="0.55"/>'

    title = f'<text x="{W//2}" y="16" text-anchor="middle" font-size="12" font-weight="600" fill="#1e293b">PLAB v0.3: 1,441 Judge Flags — Only 412 Are True Failures</text>'

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'style="font-family:\'IBM Plex Sans\',system-ui,sans-serif;background:#fff">'
           f'{title}{body}</svg>')
    (OUT / "fig2_v03_decomposition.svg").write_text(svg)
    print("fig2 done")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 3 — v0.4 model pass rates by tier (grouped bar)
# ─────────────────────────────────────────────────────────────────────────────
def fig3_v04_results():
    data = json.load(open("/tmp/report_data.json"))
    MODELS = data["models"]
    TIERS  = data["tiers"]
    COLORS = {"claude-opus-4-7":"#7c3aed","gpt-5":"#16a34a",
              "gemini-2.5-pro":"#0284c7","o3":"#b45309","deepseek-r1":"#dc2626"}
    LABELS = {"claude-opus-4-7":"Claude\nOpus 4.7","gpt-5":"GPT-5",
              "gemini-2.5-pro":"Gemini\n2.5 Pro","o3":"o3","deepseek-r1":"DeepSeek\nR1"}
    TIER_SHORT = {"tool_gated":"Tool\nGated","implicit_authz":"Implicit\nAuthz",
                  "confused_deputy":"Confused\nDeputy","chained":"Chained"}

    W, H = 520, 280
    margin = dict(l=50, r=10, t=40, b=80)
    n_tiers = len(TIERS); n_models = len(MODELS)
    chart_w = W - margin["l"] - margin["r"]
    chart_h = H - margin["t"] - margin["b"]
    group_w = chart_w / n_tiers
    bw = min(18, (group_w - 10) / n_models)
    gap = 2

    rects = ""
    for ti, tier in enumerate(TIERS):
        gx = margin["l"] + ti * group_w + (group_w - n_models * (bw + gap)) / 2
        for mi, m in enumerate(MODELS):
            bt = data["by_tier"][tier][m]
            pct = bt["passed"] / bt["total"]
            bh = chart_h * pct
            x = gx + mi * (bw + gap)
            y = margin["t"] + chart_h - bh
            col = COLORS[m]
            rects += f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw}" height="{bh:.1f}" fill="{col}" rx="2"/>'

        # tier label
        cx = margin["l"] + ti * group_w + group_w / 2
        for j, line in enumerate(TIER_SHORT[tier].split("\n")):
            rects += f'<text x="{cx:.1f}" y="{H - margin["b"] + 14 + j*12}" text-anchor="middle" font-size="10" fill="#64748b">{line}</text>'

    # y axis
    axis = ""
    for tick in [0, 25, 50, 75, 100]:
        ty = margin["t"] + chart_h * (1 - tick / 100)
        axis += f'<line x1="{margin["l"]}" y1="{ty:.1f}" x2="{W-margin["r"]}" y2="{ty:.1f}" stroke="#f1f5f9" stroke-width="1"/>'
        axis += f'<text x="{margin["l"]-6}" y="{ty+4:.1f}" text-anchor="end" font-size="9" fill="#94a3b8">{tick}%</text>'

    # legend
    legend = ""
    lx = margin["l"]; ly = H - 14
    for m in MODELS:
        legend += f'<rect x="{lx}" y="{ly-8}" width="10" height="10" fill="{COLORS[m]}" rx="2"/>'
        legend += f'<text x="{lx+13}" y="{ly}" font-size="9" fill="#64748b">{LABELS[m].replace(chr(10)," ")}</text>'
        lx += 88

    title = f'<text x="{W/2}" y="22" text-anchor="middle" font-size="13" font-weight="600" fill="#1e293b">PLAB v0.4 Pass Rate by Tier and Model</text>'
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'style="font-family:\'IBM Plex Sans\',system-ui,sans-serif;background:#fff">'
           f'{title}{axis}{rects}{legend}</svg>')
    (OUT / "fig3_v04_results.svg").write_text(svg)
    print("fig3 done")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 4 — Experiment: judge false positive rates (simple comparison table-chart)
# ─────────────────────────────────────────────────────────────────────────────
def fig4_experiment():
    W, H = 400, 220
    rows = [
        ("qwen3.5:3b",       "Contaminated", 100, "#dc2626"),
        ("claude-opus-4-7",  "Contaminated",   0, "#7c3aed"),
        ("claude-opus-4-7",  "Clean",           2, "#7c3aed"),
    ]
    bx = 190; bw_max = 170; by_start = 50; row_h = 44; bh = 22

    bars = ""
    for i, (judge, cond, val, col) in enumerate(rows):
        y = by_start + i * row_h
        w = bw_max * val / 100
        bars += f'<text x="{bx-8}" y="{y+bh/2+4:.1f}" text-anchor="end" font-size="10" fill="#1e293b" font-weight="600">{judge}</text>'
        bars += f'<text x="{bx-8}" y="{y+bh/2+15:.1f}" text-anchor="end" font-size="9" fill="#94a3b8">({cond})</text>'
        # background track
        bars += f'<rect x="{bx}" y="{y}" width="{bw_max}" height="{bh}" fill="#f8fafc" rx="3" stroke="#e2e8f0" stroke-width="1"/>'
        if w > 0:
            bars += f'<rect x="{bx}" y="{y}" width="{w:.1f}" height="{bh}" fill="{col}" rx="3"/>'
        pct_x = bx + max(w + 6, 6)
        bars += f'<text x="{pct_x:.1f}" y="{y+bh/2+4:.1f}" font-size="12" font-weight="700" fill="{col}">{val}%</text>'

    title = f'<text x="{W/2}" y="28" text-anchor="middle" font-size="13" font-weight="600" fill="#1e293b">False Positive Rate on Clear-Refusal Cases (n=100)</text>'
    note  = f'<text x="{W/2}" y="{H-10}" text-anchor="middle" font-size="9" fill="#94a3b8">All cases: model response is an unambiguous refusal; ground truth FP rate = 0%</text>'
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'style="font-family:\'IBM Plex Sans\',system-ui,sans-serif;background:#fff">'
           f'{title}{bars}{note}</svg>')
    (OUT / "fig4_experiment.svg").write_text(svg)
    print("fig4 done")

fig1_judge_fp()
fig2_v03_decomposition()
fig3_v04_results()
fig4_experiment()
print("All figures written to", OUT)
