# PLAB Paper

**Title:** Silent Judge: Weak LLMs as Evaluators Inflate Privacy Failure Rates by 4× in PLAB

## Directory structure

```
paper/
├── main.tex              ← Full paper (NeurIPS 2024 format)
├── refs.bib              ← Bibliography
├── figures/
│   ├── gen_figures.py    ← Generates all SVG figures from raw data
│   ├── fig1_judge_fp.svg ← Figure 1: judge FP rate bar chart
│   ├── fig2_v03_decomposition.svg ← Figure 2: v0.3 failure breakdown
│   ├── fig3_v04_results.svg       ← Figure 3: v0.4 per-tier results
│   └── fig4_experiment.svg        ← Figure 4: controlled experiment
├── data/
│   └── key_numbers.json  ← All headline numbers in one place
└── sections/             ← (optional) split sections for long revision
```

## Building

```bash
# Regenerate figures
python figures/gen_figures.py

# Compile (requires LaTeX + svg package)
pdflatex -shell-escape main.tex
bibtex main
pdflatex -shell-escape main.tex
pdflatex -shell-escape main.tex
```

The `svg` package requires `--shell-escape` and Inkscape or `rsvg-convert` installed.
Alternatively convert SVGs to PDFs first:

```bash
for f in figures/*.svg; do inkscape "$f" --export-pdf="${f%.svg}.pdf"; done
# then change \includesvg to \includegraphics in main.tex
```

## Key numbers (quick reference)

| Metric | Value |
|--------|-------|
| v0.3 judge-flagged failures | 1,441 / 3,600 (40.0%) |
| v0.3 true failures (deterministic) | 412 / 3,600 (11.4%) |
| v0.3 confirmed hallucinations | 683 / 1,441 (47.4%) |
| Experiment: qwen3.5:3b FP rate | 100 / 100 (100%) |
| Experiment: Claude Opus 4.7 FP rate (contaminated) | 0 / 100 (0%) |
| Experiment: Claude Opus 4.7 FP rate (clean) | 2 / 100 (2%) |
| v0.4 best model | DeepSeek R1 — 44/45 (97.8%) |
| v0.4 weakest model | Gemini 2.5 Pro — 40/45 (88.9%) |
| Disagreement cases | 12 / 45 |

## Data sources

- `results/v0.3/full_20260911_025506.jsonl` — full v0.3 run (3,600 cases)
- `results/v0.4/full_run/*.jsonl` — v0.4 per-model results
- `/tmp/hallucination_experiment_results.json` — experiment raw output
- `/tmp/report_data.json` — pre-processed v0.4 comparison data
