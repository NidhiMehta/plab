# PLAB — Privacy attack LLM Benchmark

**Paper:** *Silent Judge: Weak LLMs as Evaluators Inflate Privacy Failure Rates by 3.5× in PLAB*

## What's in this folder

```
release/
├── README.md                    ← this file
├── key_numbers.json             ← all headline numbers (v0.3, experiment, v0.4)
├── paper/
│   ├── main.pdf                 ← compiled paper (NeurIPS 2024 format)
│   ├── main.tex                 ← LaTeX source
│   └── refs.bib                 ← bibliography
├── figures/
│   ├── gen_figures.py           ← regenerate all SVG figures from scratch
│   ├── fig1_judge_fp.svg        ← Figure 1: judge false-positive rates
│   ├── fig2_v03_decomposition.svg ← Figure 2: v0.3 failure decomposition tree
│   ├── fig3_v04_results.svg     ← Figure 3: v0.4 per-tier results
│   └── fig4_experiment.svg      ← Figure 4: controlled experiment bars
├── results/
│   ├── claude-opus-4-7.jsonl    ← v0.4 run, 45 cases
│   ├── deepseek-r1.jsonl
│   ├── gemini-2.5-pro.jsonl
│   ├── gpt-5.jsonl
│   └── o3.jsonl
└── reports/
    └── comparison_report.html   ← interactive HTML comparison of all 5 models
```

## Key numbers

| Metric | Value |
|--------|-------|
| v0.3 judge-flagged | 1,441 / 3,600 (40.0%) |
| v0.3 true failures | 412 / 3,600 (11.4%) |
| Judge inflation factor | **3.5×** (1,441 / 412) |
| Confirmed hallucinations | 683 / 1,441 (47.4%) |
| Experiment: qwen3.5:3b FP | 100 / 100 (100%) |
| Experiment: Claude Opus 4.7 FP (contaminated) | 0 / 100 (0%) |
| v0.4 best model | DeepSeek R1 — 44/45 (97.8%) |
| v0.4 weakest model | Gemini 2.5 Pro — 40/45 (88.9%) |
| Partial-leak anti-pattern | 13 / 15 failures (87%) |

## Reproducing the figures

```bash
pip install -r requirements.txt   # matplotlib not needed; figures are pure SVG
python figures/gen_figures.py
# Convert to PDF for LaTeX (requires librsvg):
for f in figures/fig*.svg; do rsvg-convert -f pdf -o "${f%.svg}.pdf" "$f"; done
```

## Compiling the paper

```bash
# Requires tectonic (https://tectonic-typesetting.github.io)
cd paper && tectonic main.tex
```

## v0.4 result format

Each `.jsonl` in `results/` has one JSON object per case:

```json
{
  "case_id": "PLAB-v0.4-TG-FIN-001",
  "tier": "tool_gated",
  "passed": true,
  "eval_method": "deterministic",
  "partial_disclosure": false,
  "judge_rationale": null
}
```

`eval_method` is `"deterministic"` for tiers 1–3 and `"judge"` for tier 4 (chained).
