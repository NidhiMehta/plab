# PLAB — Privacy attack LLM Benchmark

*Silent Judge: Weak LLMs as Evaluators Inflate Privacy Failure Rates by 3.5× in PLAB*

3,600-case privacy benchmark across 6 domains × 8 attack families × 3 difficulty levels.
v0.4 adds 45 hand-crafted cases across 4 tiers with deterministic evaluation.

---

## Key finding

A weak judge (qwen3.5:3b) flagged **1,441** cases as failures. Only **412** were real — a **3.5× inflation**. 683 of the flags (47.4%) are confirmed hallucinations.

![Judge false-positive rates](paper/figures/fig1_judge_fp.svg)

![v0.4 pass rates by tier and model](paper/figures/fig3_v04_results.svg)

---

## Results

| Metric | Value |
|--------|-------|
| v0.3 judge-flagged | 1,441 / 3,600 (40.0%) |
| v0.3 true failures | 412 / 3,600 (11.4%) |
| Inflation factor | **3.5×** |
| Confirmed hallucinations | 683 / 1,441 (47.4%) |
| Partial-leak anti-pattern | 13 / 15 failures (87%) |
| v0.4 best | DeepSeek R1 — 44/45 (97.8%) |
| v0.4 weakest | Gemini 2.5 Pro — 40/45 (88.9%) |

---

## Reports

| | |
|--|--|
| [v0.4 model comparison (PDF)](results/v0.4/full_run/comparison_report.pdf) | All 5 models × 4 tiers |
| [v0.3 full run (PDF)](results/v0.3/full_report.pdf) | 3,600-case summary |
| [v0.3 failure detail (PDF)](results/v0.3/failures_detail_report.pdf) | All 412 true failures |
| [v0.3 domain analysis (PDF)](results/v0.3/domain_analysis_report.pdf) | Breakdown by domain and attack family |

---

## Repo layout

```
data/          benchmark cases (v0.1 – v0.3)
schema/        JSON schemas + v0.4 case definitions
src/           evaluator, judge, scorer, leakage detector
scripts/       report generators, pilot sampler
results/       raw JSONL outputs + HTML/PDF reports
paper/         LaTeX source, figures, compiled PDF
release/       clean artifact bundle (figures, results, paper)
iclr_submission/  anonymous ICLR 2027 package
```

→ [Full reproduction steps](REPRODUCING.md)
