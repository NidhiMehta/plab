# PLAB v0.6 Reproducible Evaluation Pipeline

End-to-end steps to reproduce all results in the paper (1,380 trials + ablation).

## Reproducibility note

Experiments were conducted using the H2O GPT Enterprise OpenAI-compatible endpoint.
Reproducing model evaluations requires independent access to the corresponding model
APIs and may produce different outputs as models and provider infrastructure change.
The benchmark cases, prompts, evaluation code, scoring logic, and configuration
required to reproduce the experimental procedure are released in full.

Exact model identifiers and evaluation configuration are in `experiments/model_config.yaml`.

---

## Prerequisites

```bash
# Python env (uv required)
uv sync
```

**Option A — Direct provider APIs (recommended for reproducibility):**
```bash
export OPENAI_API_KEY=<your-openai-key>       # for GPT-5.2
export ANTHROPIC_API_KEY=<your-anthropic-key> # for Claude Opus 4.7
export GOOGLE_API_KEY=<your-google-key>       # for Gemini 2.5 Pro
export DEEPSEEK_API_KEY=<your-deepseek-key>   # for DeepSeek V3.2
```

**Option B — H2O GPT Enterprise (used for paper results):**
```bash
export H2OGPTE_API_KEY=<your-key>
export H2OGPTE_ADDRESS=<endpoint-url>   # e.g. https://h2ogpte.example.com
```

**Option C — Any OpenAI-compatible endpoint:**
```bash
export PLAB_API_BASE_URL=<base-url>
export PLAB_API_KEY=<your-key>
# Then use --provider custom in all commands below
```

All commands are run from the `v0.6/` directory.

---

## Smoke test (one case, verify the pipeline)

Before running the full benchmark, verify the pipeline with a single case:

```bash
uv run python scripts/run_multiround_eval.py \
  --model claude-opus-4-7 \
  --cases cases/ \
  --case-id PLAB-v0.6-TG-FIN-001 \
  --runs 1 \
  --out /tmp/smoke_test.jsonl

# Should produce 1 line with status=passed or status=failed
# (Opus 4.7 passes this case with the pre-call instruction)
grep '"status"' /tmp/smoke_test.jsonl
```

This verifies the full pipeline (prompt assembly → model call → tool execution →
deterministic evaluation) with a single API call before committing to 1,380 trials.

---

## Step 1 — Run multi-round evaluation (1,380 trials)

Runs each of the 69 cases 5× per model at temperature 1.0.
Results land in `results_multirun/v0.6_<model>_5run.jsonl`.

```bash
# Opus 4.7
uv run python scripts/run_multiround_eval.py \
  --model claude-opus-4-7 \
  --cases cases/ \
  --runs 5 \
  --out results_multirun/v0.6_opus_5run.jsonl

# GPT-5.2
uv run python scripts/run_multiround_eval.py \
  --model gpt-5.2 \
  --cases cases/ \
  --runs 5 \
  --out results_multirun/v0.6_gpt_5run.jsonl

# Gemini 2.5 Pro
uv run python scripts/run_multiround_eval.py \
  --model gemini-2.5-pro \
  --cases cases/ \
  --runs 5 \
  --out results_multirun/v0.6_gemini_5run.jsonl

# DeepSeek V3.2
uv run python scripts/run_multiround_eval.py \
  --model deepseek-ai/DeepSeek-V3.2 \
  --cases cases/ \
  --runs 5 \
  --out results_multirun/v0.6_deepseek_5run.jsonl
```

Expected output files (already committed):
- `results_multirun/v0.6_opus_5run.jsonl` (345 lines)
- `results_multirun/v0.6_gpt_5run.jsonl` (345 lines)
- `results_multirun/v0.6_gemini_5run.jsonl` (345 lines)
- `results_multirun/v0.6_deepseek_5run.jsonl` (345 lines)

---

## Step 2 — Run ablation (tool-gated, instruction removed)

23 cases × 4 models × 1 run = 92 ablation trials.
Ablation cases are in `cases_ablation/` (pre-call instruction stripped from role prompts).

```bash
for MODEL in claude-opus-4-7 gpt-5.2 gemini-2.5-pro deepseek-ai/DeepSeek-V3.2; do
  uv run python scripts/run_multiround_eval.py \
    --model "$MODEL" \
    --cases cases_ablation/ \
    --runs 1 \
    --out "results/v0.6_ablation_${MODEL//\//_}.jsonl"
done
```

Expected output: `results/v0.6_ablation_*.jsonl` — all cases should show status=failed.

---

## Step 3 — Deep analysis

Produces the full statistical analysis (pass rates, robustness, tier/domain breakdown,
stochasticity, case hardness) and a per-case CSV.

```bash
uv run python scripts/analyze_multirun_deep.py \
  --dir results_multirun \
  --csv results_multirun/deep_summary.csv
```

Key outputs printed to stdout:
1. Trial-level pass rates + Wilson 95% CI per model
2. Case-level robustness distribution (0/5 – 5/5)
3. Failure-type breakdown
4. Tier breakdown with CIs
5. Domain breakdown
6. Case hardness (hardest/easiest 10 cases)
7. Stochasticity profile

CSV written to `results_multirun/deep_summary.csv` (per-case: model, tier, domain,
passes, n, pass_rate).

---

## Step 4 — Generate HTML report

Builds the self-contained research report at `results_multirun/report.html`
from the deep summary CSV and embedded JSON data.

```bash
uv run python scripts/build_report.py \
  --csv results_multirun/deep_summary.csv \
  --ablation-dir results \
  --out results_multirun/report.html
```

The report includes all 9 sections: Evaluation Protocol, Key Findings, Overall
Performance, Case-Level Robustness, Tier Results, Case Matrix (69×4), Universal
Failures, Stochasticity, Domain Analysis, and the Instruction Ablation figure.

---

## Step 5 — Verify checksums (optional)

Compare your result files against the committed ones to verify reproducibility.

```bash
# Count passing trials per model — should match paper Table 1
for f in results_multirun/v0.6_*_5run.jsonl; do
  echo "$f: $(grep -c '"status":"passed"' "$f") passes"
done
# Expected: opus=171, gemini=170, deepseek=142, gpt=69
```

---

## File layout

```
v0.6/
├── cases/                     # 69 case JSON files
├── cases_ablation/            # 23 tool_gated cases, instruction stripped
├── results_multirun/
│   ├── v0.6_opus_5run.jsonl
│   ├── v0.6_gpt_5run.jsonl
│   ├── v0.6_gemini_5run.jsonl
│   ├── v0.6_deepseek_5run.jsonl
│   ├── deep_summary.csv       # per-case aggregates
│   ├── report_data.json       # embedded data for HTML report
│   └── report.html            # self-contained report
├── results/
│   ├── v0.6_ablation_*.jsonl  # ablation results
│   └── v0.6_ablation_comparison.txt
└── scripts/
    ├── run_multiround_eval.py  # Step 1 & 2
    ├── analyze_multirun_deep.py # Step 3
    └── build_report.py         # Step 4
```

---

## Reproducing paper tables

All numbers in the paper derive from Steps 3–4 above.

| Paper table | Source |
|---|---|
| Table 1 (overall pass rates) | Step 3, section 1 output |
| Table 2 (robustness 0/5–5/5) | Step 3, section 2 output |
| Table 3 (tier breakdown) | Step 3, section 4 output |
| Table 4 (domain breakdown) | Step 3, section 5 output |
| Table 5 (ablation) | Step 2 results + Step 3 tier output |

Wilson 95% confidence intervals are computed by `analyze_multirun_deep.py`
using the `wilson(k, n)` function (see `scripts/analyze_multirun_deep.py:32`).
