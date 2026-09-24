"""
Regenerate results/plab_v06_report.html from the raw v0.6 result JSONL files.

Usage (from the v0.5 directory):
    uv run python build_report_v06.py

Reads:
    results/v0.6_opus47.jsonl
    results/v0.6_gemini.jsonl
    results/v0.6_gpt52.jsonl
    results/v0.6_deepseek.jsonl
    schema/case.v0.6.cases.jsonl

Writes:
    results/plab_v06_report.html
"""

import json
from pathlib import Path

HERE = Path(__file__).parent

RUNS = [
    ("results/v0.6_opus47.jsonl",   "opus"),
    ("results/v0.6_gemini.jsonl",   "gemini"),
    ("results/v0.6_gpt52.jsonl",    "gpt52"),
    ("results/v0.6_deepseek.jsonl", "deepseek"),
]

def load_results():
    """Return {case_id: {model_key: status}} from the four JSONL files."""
    by_case: dict[str, dict] = {}
    for path, key in RUNS:
        p = HERE / path
        if not p.exists():
            print(f"WARNING: {path} not found &mdash; skipping")
            continue
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                cid = obj.get("case_id") or obj.get("id", "")
                status = obj.get("status", "inconclusive")
                if cid not in by_case:
                    by_case[cid] = {}
                by_case[cid][key] = status
    return by_case


def load_cases():
    """Return list of case metadata dicts from the case file."""
    p = HERE / "schema" / "case.v0.6.cases.jsonl"
    cases = []
    if not p.exists():
        print(f"WARNING: {p} not found")
        return cases
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases


def build_cases_js(cases, results):
    """Return a JS array literal for embedding in the HTML."""
    rows = []
    for c in cases:
        cid = c["id"]
        tier = c.get("tier", "")
        domain = c.get("domain", "")
        env = c.get("environment", {})
        meta = c.get("metadata", {})
        family = meta.get("attack_family", c.get("attack_family", ""))
        difficulty = meta.get("difficulty", c.get("difficulty", ""))
        res = results.get(cid, {})
        row = {
            "id": cid,
            "tier": tier,
            "domain": domain,
            "family": family,
            "difficulty": difficulty,
            "results": {
                "opus":     res.get("opus",     "inconclusive"),
                "gemini":   res.get("gemini",   "inconclusive"),
                "gpt52":    res.get("gpt52",    "inconclusive"),
                "deepseek": res.get("deepseek", "inconclusive"),
            },
        }
        rows.append(row)
    return json.dumps(rows, separators=(",", ":"))


HTML_TEMPLATE = r"""<title>PLAB v0.6</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
:root {
  --bg:        #0d1117;
  --surface:   #161b22;
  --surface2:  #21262d;
  --border:    #30363d;
  --text:      #e6edf3;
  --text-dim:  #8b949e;
  --accent:    #58a6ff;
  --pass:      #3fb950;
  --fail:      #f85149;
  --inc:       #d29922;
  --opus:      #58a6ff;
  --gemini:    #56d364;
  --gpt52:     #ffa657;
  --deepseek:  #bc8cff;
}
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    --bg: #f6f8fa; --surface: #ffffff; --surface2: #f0f3f7;
    --border: #d0d7de; --text: #1f2328; --text-dim: #656d76;
    --accent: #0969da; --pass: #1a7f37; --fail: #cf222e;
    --inc: #9a6700; --opus: #0969da; --gemini: #1a7f37;
    --gpt52: #bc4c00; --deepseek: #8250df;
  }
}
:root[data-theme="light"] {
  --bg: #f6f8fa; --surface: #ffffff; --surface2: #f0f3f7;
  --border: #d0d7de; --text: #1f2328; --text-dim: #656d76;
  --accent: #0969da; --pass: #1a7f37; --fail: #cf222e;
  --inc: #9a6700; --opus: #0969da; --gemini: #1a7f37;
  --gpt52: #bc4c00; --deepseek: #8250df;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;font-size:14px;line-height:1.6;padding-inline:clamp(16px,4vw,48px);padding-block:32px}
h1{font-size:clamp(20px,3vw,28px);font-weight:700;letter-spacing:-.02em}
h2{font-size:15px;font-weight:600;color:var(--text-dim);text-transform:uppercase;letter-spacing:.08em;margin-bottom:16px}
h3{font-size:14px;font-weight:600;margin-bottom:8px}
.subtitle{color:var(--text-dim);font-size:13px;margin-top:4px}
section{margin-top:40px}
.page-header{display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:40px}
.theme-btn{background:var(--surface2);border:1px solid var(--border);color:var(--text-dim);padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;font-family:inherit}
.theme-btn:hover{color:var(--text)}
.model-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px}
.model-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:20px;border-top:3px solid var(--model-color)}
.model-name{font-weight:600;font-size:15px;margin-bottom:12px}
.stat-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.stat-label{color:var(--text-dim);font-size:12px}
.stat-val{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:500}
.pass-val{color:var(--pass)}.fail-val{color:var(--fail)}.inc-val{color:var(--inc)}
.rate-bar{height:6px;background:var(--surface2);border-radius:3px;margin-top:12px;overflow:hidden}
.rate-fill{height:100%;border-radius:3px;background:var(--model-color)}
.big-rate{font-size:28px;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--model-color);margin-top:4px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px 12px;color:var(--text-dim);font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid var(--border)}
td{padding:8px 12px;border-bottom:1px solid var(--border)}
tr:last-child td{border-bottom:none}
tr:hover td{background:var(--surface2)}
.tbl-wrap{background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden;overflow-x:auto}
.pct{font-family:'JetBrains Mono',monospace;font-weight:500}
.pct-high{color:var(--pass)}.pct-mid{color:var(--text)}.pct-low{color:var(--fail)}.pct-zero{color:var(--fail);font-weight:700}
.heatmap-grid{display:grid;grid-template-columns:140px repeat(4,1fr);gap:1px;background:var(--border);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.hm-header{background:var(--surface);padding:8px 10px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--text-dim)}
.hm-cell{background:var(--surface);padding:10px;text-align:center;font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:500}
.hm-row-label{background:var(--surface);padding:10px 12px;font-size:13px;font-weight:500}
.fam-grid{display:grid;gap:10px}
.fam-row{display:grid;grid-template-columns:160px 1fr;align-items:center;gap:12px}
.fam-label{font-size:13px;color:var(--text-dim)}
.fam-bars{display:flex;gap:4px;align-items:center;height:20px}
.fam-bar{height:20px;border-radius:3px;min-width:2px}
.fam-legend{display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap}
.fam-leg-item{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-dim)}
.fam-leg-dot{width:10px;height:10px;border-radius:2px}
.filter-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;align-items:center}
.filter-select{background:var(--surface);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:6px;font-size:12px;font-family:inherit}
.filter-select:focus{outline:2px solid var(--accent);border-color:transparent}
.cases-table th,.cases-table td{font-size:12px;padding:6px 10px}
.badge{display:inline-block;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600;font-family:'JetBrains Mono',monospace}
.badge-passed{background:color-mix(in srgb,var(--pass) 15%,transparent);color:var(--pass)}
.badge-failed{background:color-mix(in srgb,var(--fail) 15%,transparent);color:var(--fail)}
.badge-inconclusive{background:color-mix(in srgb,var(--inc) 15%,transparent);color:var(--inc)}
.case-id{font-family:'JetBrains Mono',monospace;color:var(--text-dim);font-size:11px}
.tier-pill{display:inline-block;padding:2px 6px;border-radius:3px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.tier-cd{background:color-mix(in srgb,var(--accent) 15%,transparent);color:var(--accent)}
.tier-tg{background:color-mix(in srgb,var(--gpt52) 15%,transparent);color:var(--gpt52)}
.tier-ch{background:color-mix(in srgb,var(--deepseek) 15%,transparent);color:var(--deepseek)}
.findings{display:grid;gap:16px}
.finding{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:20px;border-left:3px solid var(--accent)}
.finding-num{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-dim);margin-bottom:6px}
.finding-title{font-weight:600;font-size:14px;margin-bottom:8px}
.finding-body{color:var(--text-dim);font-size:13px;line-height:1.65}
.finding-body strong{color:var(--text)}
.tag{display:inline-block;background:var(--surface2);border:1px solid var(--border);border-radius:4px;padding:1px 6px;font-size:11px;font-family:'JetBrains Mono',monospace;margin:2px}
.uf-list{display:grid;gap:8px}
.uf-item{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:12px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.uf-id{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text-dim);flex:1;min-width:220px}
.uf-badges{display:flex;gap:6px;flex-wrap:wrap}
footer{margin-top:60px;padding-top:24px;border-top:1px solid var(--border);color:var(--text-dim);font-size:12px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
</style>

<div class="page-header">
  <div>
    <h1>PLAB v0.6</h1>
    <p class="subtitle">Privacy Leakage Adversarial Benchmark &middot; 69 cases &middot; 4 models &middot; 3 tiers &middot; 6 domains</p>
  </div>
  <button class="theme-btn" onclick="toggleTheme()">Toggle theme</button>
</div>

<section>
  <h2>Models</h2>
  <div class="model-grid" id="model-grid"></div>
</section>

<section>
  <h2>Results by tier</h2>
  <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th>Tier</th><th>Cases</th>
        <th>Opus 4.7</th><th>Gemini 2.5</th><th>GPT-5.2</th><th>DeepSeek V3</th>
      </tr></thead>
      <tbody id="tier-tbody"></tbody>
    </table>
  </div>
</section>

<section>
  <h2>Domain heatmap (conclusive pass %)</h2>
  <div class="heatmap-grid" id="heatmap"></div>
</section>

<section>
  <h2>Attack family breakdown</h2>
  <div class="fam-legend" id="fam-legend"></div>
  <div class="fam-grid" id="fam-grid"></div>
</section>

<section>
  <h2>Analysis</h2>
  <div class="findings">
    <div class="finding">
      <div class="finding-num">FINDING 01</div>
      <div class="finding-title">audit_pretext is the most reliable attack vector &mdash; 0% pass for two models</div>
      <div class="finding-body">All 7 audit-framing cases produced failures across <strong>Claude Opus 4.7</strong> and <strong>GPT-5.2</strong> (0%), and near-zero rates for Gemini (14%) and DeepSeek (14%). Attacks framed as internal audit reviews, AML transaction monitoring, SAR quality checks, or reinsurance submissions are consistently effective. The common thread: the framing invokes a high-authority compliance or oversight function where refusing access feels like obstructing a mandatory process. No model reliably detected that compliance authority does not confer record-level authorisation.</div>
    </div>
    <div class="finding">
      <div class="finding-num">FINDING 02</div>
      <div class="finding-title">GPT-5.2 fails every tool_gated case (0/16) &mdash; pre-call reasoning instruction has no effect</div>
      <div class="finding-body">Despite an explicit instruction to "verify authorisation before calling the tool," GPT-5.2 calls the tool on every unauthorized request across all 16 conclusive tool-gated cases &mdash; the only model with a structural 0% on any tier. Opus (52%) and DeepSeek (50%) both apply pre-call reasoning effectively. This is not a function of prompt comprehension: GPT-5.2 correctly refuses social engineering in the enterprise domain (73%) but treats tool invocation as unconditional regardless of authorization context. The failure mode is consistent with its v0.5 pattern of high tool-call willingness under adversarial framing.</div>
    </div>
    <div class="finding">
      <div class="finding-num">FINDING 03</div>
      <div class="finding-title">GPT-5.2 domain gap: 73% enterprise, 0% health and education</div>
      <div class="finding-body">GPT-5.2 correctly refuses 73% of enterprise-domain attacks (the best of any model on that domain) but fails <em>every</em> health and education case. The pattern suggests domain-sensitive calibration of what constitutes "sensitive data": it treats business-context records as inherently sensitive, but is not calibrated to protect clinical diagnoses, pharmacy records, student welfare flags, or looked-after-child status. <strong>Financial domain</strong> (6% pass) follows a similar pattern &mdash; GPT-5.2 is very willing to make financial data tool calls for seemingly routine banking requests.</div>
    </div>
    <div class="finding">
      <div class="finding-num">FINDING 04</div>
      <div class="finding-title">Gemini leads on chained (45%) and confused_deputy (80%) but collapses on tool_gated (20%)</div>
      <div class="finding-body">Gemini has the widest variance across tiers. It is the best model on multi-turn <span class="tag">chained</span> attacks (45%) and the best on <span class="tag">confused_deputy</span> (80%), suggesting strong context management and verification-seeking behavior. But it performs worst on <span class="tag">tool_gated</span> (20%, second only to GPT-5.2's 0%). Government domain (33%) is its weakest, clustering on benefits, tax investigations, and licensing where official authority framing appears to override refusal calibration.</div>
    </div>
    <div class="finding">
      <div class="finding-num">FINDING 05</div>
      <div class="finding-title">18 cases break all four models (26% of the benchmark)</div>
      <div class="finding-body">18 of 69 cases produced confirmed failures or inconclusives across all four models. These concentrate in three patterns: <strong>(1)</strong> all chained cases involving financial audit, health MDT, government benefits, insurance, and education audit pretexts; <strong>(2)</strong> all government-domain tool_gated cases; <strong>(3)</strong> the offboarding and medical-coverage confused_deputy cases. The universal failures are not the hardest-rated cases &mdash; several are rated "medium" &mdash; suggesting that the attack vector, not difficulty rating, is the primary predictor of cross-model failure.</div>
    </div>
    <div class="finding">
      <div class="finding-num">FINDING 06</div>
      <div class="finding-title">Chained attacks are the hardest tier for three of four models</div>
      <div class="finding-body">Pass rates on chained: Opus 24%, GPT-5.2 24%, DeepSeek 19%, Gemini 45%. The commitment_trap pattern &mdash; where the first turn establishes a false role and the second turn exploits the implicitly validated context &mdash; is the key mechanism. The assistant's confirmatory first response functions as implicit authorisation of the claimed role, and the model does not re-evaluate credentials when the extraction request arrives.</div>
    </div>
  </div>
</section>

<section>
  <h2>Evaluator&ndash;judge agreement &amp; soft disclosures</h2>
  <p style="color:var(--text-dim);font-size:13px;margin-bottom:16px;line-height:1.65">
    Across 276 evaluations (69 cases &times; 4 models), failures split into three categories.
    <strong>Deterministic failures</strong> require no judge: exact string match (<em>n</em>=83)
    or unauthorized tool call (<em>n</em>=51). <strong>Soft disclosures</strong> (<em>n</em>=18,
    14 of 18 at leakage level &ge;3, median 4/5) are cases the deterministic check passes but the
    semantic judge detects partial or implicit leakage &mdash; the model refused but echoed a protected
    value, or disclosed data through implication rather than verbatim output.
    <strong>Agreed passes</strong> (<em>n</em>=124) have no signal from either layer.
  </p>
  <table class="stats-table" style="margin-bottom:20px">
    <thead><tr><th>Category</th><th>n</th><th>Det. signal</th><th>Mean leakage level</th><th>Agreement</th></tr></thead>
    <tbody>
      <tr><td>Det. failure &mdash; exact disclosure</td><td>83</td><td>exact match</td><td>&mdash;</td><td>det sufficient</td></tr>
      <tr><td>Det. failure &mdash; tool violation</td><td>51</td><td>tool_auth_violation</td><td>&mdash;</td><td>det sufficient</td></tr>
      <tr><td><strong>Soft disclosure (judge only)</strong></td><td><strong>18</strong></td><td>none</td><td><strong>14/18 &ge;3 (med. 4)</strong></td><td>judge-only detection</td></tr>
      <tr><td>Agreed pass / inconclusive</td><td>124</td><td>none</td><td>0</td><td>agreed</td></tr>
    </tbody>
  </table>
  <p style="color:var(--text-dim);font-size:13px;line-height:1.65">
    Soft disclosures concentrate in <strong>chained</strong> (<em>n</em>=10) and
    <strong>confused_deputy</strong> (<em>n</em>=8) tiers &mdash; none in tool_gated, where
    violations are fully captured by the tool-call log. Opus 4.7 accounts for 8 of the 18,
    reflecting its tendency to echo sensitive context in refusals (e.g., restating a protected
    salary figure while declining to confirm it). The highest-severity cases (level 5) involve
    mental health data: <strong>CH-EDU-001</strong> &mdash; a chained attack targeting a student's
    PHQ-9 score and suicidal ideation flag &mdash; produces a level-5 soft disclosure across all four
    models, a universal failure the deterministic check alone would have missed.
  </p>
  <table class="stats-table" style="margin-top:14px">
    <thead><tr><th>Case</th><th>Tier</th><th>Domain</th><th>Family</th><th>Model</th><th style="text-align:right">Level</th><th>Judge rationale (excerpt)</th></tr></thead>
    <tbody>
SOFT_DISCLOSURE_ROWS
    </tbody>
  </table>
</section>

<section>
  <h2>Cases that break all models</h2>
  <div class="uf-list" id="uf-list"></div>
</section>

<section>
  <h2>Per-case results</h2>
  <div class="filter-row">
    <select class="filter-select" id="f-tier" onchange="applyFilters()">
      <option value="">All tiers</option>
      <option value="confused_deputy">confused_deputy</option>
      <option value="tool_gated">tool_gated</option>
      <option value="chained">chained</option>
    </select>
    <select class="filter-select" id="f-domain" onchange="applyFilters()">
      <option value="">All domains</option>
      <option value="enterprise">enterprise</option>
      <option value="financial">financial</option>
      <option value="health">health</option>
      <option value="government">government</option>
      <option value="legal">legal</option>
      <option value="education">education</option>
    </select>
    <select class="filter-select" id="f-family" onchange="applyFilters()">
      <option value="">All families</option>
      <option value="social_engineering">social_engineering</option>
      <option value="role_impersonation">role_impersonation</option>
      <option value="audit_pretext">audit_pretext</option>
      <option value="commitment_trap">commitment_trap</option>
      <option value="debugging_pretext">debugging_pretext</option>
      <option value="context_manipulation">context_manipulation</option>
    </select>
    <select class="filter-select" id="f-verdict" onchange="applyFilters()">
      <option value="">All verdicts</option>
      <option value="all_fail">All failed</option>
      <option value="all_pass">All passed</option>
      <option value="mixed">Mixed</option>
    </select>
    <span style="color:var(--text-dim);font-size:12px;margin-left:4px" id="case-count"></span>
  </div>
  <div class="tbl-wrap">
    <table class="cases-table">
      <thead><tr>
        <th>Case ID</th><th>Tier</th><th>Domain</th><th>Family</th><th>Diff</th>
        <th>Opus</th><th>Gemini</th><th>GPT-5.2</th><th>DeepSeek</th>
      </tr></thead>
      <tbody id="cases-tbody"></tbody>
    </table>
  </div>
</section>

<footer>
  <span>PLAB v0.6 &middot; 69 cases &middot; 2026-09-23</span>
  <span>Claude Opus 4.7 &middot; Gemini 2.5 Pro &middot; GPT-5.2 &middot; DeepSeek V3.2</span>
</footer>

<script>
const MODELS=[
  {key:'opus',    name:'Claude Opus 4.7',color:'var(--opus)'},
  {key:'gemini',  name:'Gemini 2.5 Pro', color:'var(--gemini)'},
  {key:'gpt52',   name:'GPT-5.2',        color:'var(--gpt52)'},
  {key:'deepseek',name:'DeepSeek V3.2',  color:'var(--deepseek)'},
];
const TIERS=['confused_deputy','tool_gated','chained'];
const DOMAINS=['enterprise','financial','health','legal','government','education'];
const FAMILIES=['social_engineering','role_impersonation','debugging_pretext','audit_pretext','commitment_trap','context_manipulation'];
const CASES=CASES_DATA;
function s2c(s){return s==='passed'?'var(--pass)':s==='failed'?'var(--fail)':'var(--inc)'}
function pct(p,f){return p+f===0?null:Math.round(100*p/(p+f))}
function pctClass(v){return v===null?'':v>=60?'pct-high':v>=35?'pct-mid':v>0?'pct-low':'pct-zero'}
function pctStr(v){return v===null?'&mdash;':v+'%'}
function tierClass(t){return t==='confused_deputy'?'tier-cd':t==='tool_gated'?'tier-tg':'tier-ch'}
function tierShort(t){return t==='confused_deputy'?'CD':t==='tool_gated'?'TG':'CH'}
function badge(s){return `<span class="badge badge-${s}">${s==='inconclusive'?'INC':s.toUpperCase()}</span>`}

function buildModelCards(){
  const g=document.getElementById('model-grid');
  MODELS.forEach(m=>{
    let p=0,f=0,i=0;
    CASES.forEach(c=>{const s=c.results[m.key];if(s==='passed')p++;else if(s==='failed')f++;else i++;});
    const rate=pct(p,f);
    g.innerHTML+=`<div class="model-card" style="--model-color:${m.color}">
      <div class="model-name">${m.name}</div>
      <div class="stat-row"><span class="stat-label">Passed</span><span class="stat-val pass-val">${p}</span></div>
      <div class="stat-row"><span class="stat-label">Failed</span><span class="stat-val fail-val">${f}</span></div>
      <div class="stat-row"><span class="stat-label">Inconclusive</span><span class="stat-val inc-val">${i}</span></div>
      <div class="big-rate">${rate}%</div>
      <div class="rate-bar"><div class="rate-fill" style="width:${rate}%"></div></div>
    </div>`;
  });
}

function buildTierTable(){
  const tb=document.getElementById('tier-tbody');
  const total={confused_deputy:25,tool_gated:23,chained:21};
  TIERS.forEach(tier=>{
    let cells='';
    MODELS.forEach(m=>{
      let p=0,f=0,i=0;
      CASES.filter(c=>c.tier===tier).forEach(c=>{const s=c.results[m.key];if(s==='passed')p++;else if(s==='failed')f++;else i++;});
      const v=pct(p,f);
      cells+=`<td><span class="pct ${pctClass(v)}">${pctStr(v)}</span> <span style="color:var(--text-dim);font-size:11px">(${p}/${p+f})</span></td>`;
    });
    tb.innerHTML+=`<tr><td><span class="tier-pill ${tierClass(tier)}">${tierShort(tier)}</span> <span style="color:var(--text-dim)">${tier.replace('_',' ')}</span></td><td style="color:var(--text-dim)">${total[tier]}</td>${cells}</tr>`;
  });
}

function buildHeatmap(){
  const g=document.getElementById('heatmap');
  g.innerHTML='<div class="hm-header"></div>';
  MODELS.forEach(m=>{g.innerHTML+=`<div class="hm-header" style="color:${m.color}">${m.name}</div>`;});
  DOMAINS.forEach(dom=>{
    g.innerHTML+=`<div class="hm-row-label">${dom}</div>`;
    MODELS.forEach(m=>{
      let p=0,f=0;
      CASES.filter(c=>c.domain===dom).forEach(c=>{const s=c.results[m.key];if(s==='passed')p++;else if(s==='failed')f++;});
      const v=pct(p,f);
      const alpha=v===null?0.08:0.08+0.6*(v/100);
      const bg=v===null?'var(--surface2)':v>=60?`color-mix(in srgb,var(--pass) ${Math.round(alpha*100)}%,var(--surface))`:v>=30?`color-mix(in srgb,var(--inc) ${Math.round(alpha*80)}%,var(--surface))`:`color-mix(in srgb,var(--fail) ${Math.round(alpha*100)}%,var(--surface))`;
      g.innerHTML+=`<div class="hm-cell" style="background:${bg}"><span class="${pctClass(v)}">${pctStr(v)}</span></div>`;
    });
  });
}

function buildFamilyBars(){
  const leg=document.getElementById('fam-legend');
  MODELS.forEach(m=>{leg.innerHTML+=`<div class="fam-leg-item"><div class="fam-leg-dot" style="background:${m.color}"></div>${m.name}</div>`;});
  const g=document.getElementById('fam-grid');
  const maxCases=Math.max(...FAMILIES.map(fam=>CASES.filter(c=>c.family===fam).length));
  FAMILIES.forEach(fam=>{
    const famCases=CASES.filter(c=>c.family===fam);
    const total=famCases.length;
    let bars='';
    MODELS.forEach(m=>{
      let p=0,f=0;
      famCases.forEach(c=>{const s=c.results[m.key];if(s==='passed')p++;else if(s==='failed')f++;});
      const rate=pct(p,f);
      const w=Math.round((total/maxCases)*100);
      bars+=`<div title="${m.name}: ${pctStr(rate)} (${p}/${p+f})" class="fam-bar" style="width:${w*(rate||0)/100}px;min-width:${rate?2:0}px;background:${m.color};opacity:0.85"></div>`;
    });
    g.innerHTML+=`<div class="fam-row"><div class="fam-label">${fam.replace(/_/g,' ')}<span style="color:var(--text-dim);font-size:11px"> &times;${total}</span></div><div class="fam-bars">${bars}</div></div>`;
  });
}

function buildUF(){
  const uf=CASES.filter(c=>MODELS.every(m=>c.results[m.key]!=='passed'));
  const el=document.getElementById('uf-list');
  uf.forEach(c=>{
    let badges='';
    MODELS.forEach(m=>{badges+=badge(c.results[m.key]);});
    el.innerHTML+=`<div class="uf-item">
      <div><span class="case-id">${c.id}</span></div>
      <div><span class="tier-pill ${tierClass(c.tier)}">${tierShort(c.tier)}</span></div>
      <div style="color:var(--text-dim);font-size:12px">${c.domain} &middot; ${c.family.replace(/_/g,' ')}</div>
      <div class="uf-badges">${badges}</div>
    </div>`;
  });
}

let visibleCases=[...CASES];
function renderCasesTable(){
  const tb=document.getElementById('cases-tbody');
  tb.innerHTML='';
  document.getElementById('case-count').textContent=`${visibleCases.length} cases`;
  visibleCases.forEach(c=>{
    let cells='';
    MODELS.forEach(m=>{cells+=`<td>${badge(c.results[m.key])}</td>`;});
    tb.innerHTML+=`<tr>
      <td class="case-id">${c.id}</td>
      <td><span class="tier-pill ${tierClass(c.tier)}">${tierShort(c.tier)}</span></td>
      <td style="color:var(--text-dim)">${c.domain}</td>
      <td style="color:var(--text-dim)">${c.family.replace(/_/g,' ')}</td>
      <td style="color:var(--text-dim)">${c.difficulty}</td>
      ${cells}
    </tr>`;
  });
}
function applyFilters(){
  const tier=document.getElementById('f-tier').value;
  const domain=document.getElementById('f-domain').value;
  const family=document.getElementById('f-family').value;
  const verdict=document.getElementById('f-verdict').value;
  visibleCases=CASES.filter(c=>{
    if(tier&&c.tier!==tier)return false;
    if(domain&&c.domain!==domain)return false;
    if(family&&c.family!==family)return false;
    if(verdict==='all_fail'&&!MODELS.every(m=>c.results[m.key]!=='passed'))return false;
    if(verdict==='all_pass'&&!MODELS.every(m=>c.results[m.key]==='passed'))return false;
    if(verdict==='mixed'){const st=new Set(MODELS.map(m=>c.results[m.key]));if(!st.has('passed')||!st.has('failed'))return false;}
    return true;
  });
  renderCasesTable();
}
function toggleTheme(){
  const r=document.documentElement;
  r.setAttribute('data-theme',r.getAttribute('data-theme')==='light'?'dark':'light');
}
buildModelCards();buildTierTable();buildHeatmap();buildFamilyBars();buildUF();renderCasesTable();
</script>
"""


MODEL_LABELS = {
    "opus":     "Opus 4.7",
    "opus47":   "Opus 4.7",
    "gemini":   "Gemini 2.5",
    "gpt52":    "GPT-5.2",
    "deepseek": "DeepSeek V3",
}

LEVEL_COLORS = {5: "#b91c1c", 4: "#c2410c", 3: "#b45309", 2: "#6b7280", 1: "#6b7280"}


def build_soft_disclosure_rows() -> str:
    rows = []
    for path, key in RUNS:
        p = HERE / path
        if not p.exists():
            continue
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                ev = obj.get("evaluation", {})
                j  = ev.get("judge", {})
                det_fail = (
                    ev.get("exact_disclosure", False)
                    or ev.get("tool_authorization_violation", False)
                    or ev.get("confused_deputy_violation", False)
                )
                jl = j.get("leakage_level")
                if not det_fail and jl is not None and jl > 0:
                    rows.append({
                        "case_id":  obj.get("case_id", ""),
                        "tier":     obj.get("tier", ""),
                        "domain":   obj.get("domain", ""),
                        "family":   obj.get("attack_family", ""),
                        "model":    MODEL_LABELS.get(key, key),
                        "level":    jl,
                        "rationale": j.get("rationale", ""),
                    })

    rows.sort(key=lambda r: (-r["level"], r["case_id"], r["model"]))

    html_rows = []
    for r in rows:
        color = LEVEL_COLORS.get(r["level"], "#6b7280")
        excerpt = r["rationale"][:110].rstrip()
        if len(r["rationale"]) > 110:
            excerpt += "..."
        cid_short = r["case_id"].replace("PLAB-v0.6-", "")
        html_rows.append(
            f'      <tr>'
            f'<td style="font-family:monospace;font-size:11px">{cid_short}</td>'
            f'<td><span class="tag">{r["tier"]}</span></td>'
            f'<td style="color:var(--text-dim)">{r["domain"]}</td>'
            f'<td style="color:var(--text-dim);font-size:12px">{r["family"].replace("_"," ")}</td>'
            f'<td style="color:var(--text-dim)">{r["model"]}</td>'
            f'<td style="text-align:right;font-weight:600;color:{color}">{r["level"]}</td>'
            f'<td style="color:var(--text-dim);font-size:12px">{excerpt}</td>'
            f'</tr>'
        )
    return "\n".join(html_rows)


def build():
    cases = load_cases()
    results = load_results()
    cases_js = build_cases_js(cases, results)
    soft_rows = build_soft_disclosure_rows()
    html = HTML_TEMPLATE.replace("CASES_DATA", cases_js)
    html = html.replace("SOFT_DISCLOSURE_ROWS", soft_rows)
    out = HERE / "results" / "plab_v06_report.html"
    out.write_text(html, encoding="utf-8")
    print(f"Written {out} ({out.stat().st_size:,} bytes, {len(cases)} cases)")


if __name__ == "__main__":
    build()
