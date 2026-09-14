# PLAB — Privacy attack LLM Benchmark

*Silent Judge: Weak LLMs as Evaluators Inflate Privacy Failure Rates by 3.5× in PLAB*

3,600-case privacy benchmark across 6 domains × 8 attack families × 3 difficulty levels.
v0.4 adds 45 hand-crafted cases across 4 tiers with deterministic evaluation.

→ **[One-page summary (PDF)](paper/summary.pdf)**

---

## Key finding

A weak judge (qwen3.5:3b) flagged **1,441 / 3,600** cases as failures. A stronger judge confirmed only **412** — a **3.5× inflation**. Of the 1,029 disagreements, 683 (47.4%) are confirmed judge hallucinations: the model clearly refused, but the weak judge invented a violation anyway. The remaining 346 are borderline partial leaks where judges genuinely differ.

In a controlled experiment on 100 unambiguous-refusal cases (ground-truth FP rate = 0%), qwen3.5:3b flagged **100%** as failures. Claude Opus 4.7 on the same cases: **0%**.

The dominant failure pattern across all five models in v0.4 is **partial-leak** (87% of failures): the model refuses the targeted asset but leaks an adjacent field — e.g. refuses to give an account number but states the account holder's address.

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
results/       raw JSONL outputs + PDF reports
paper/         LaTeX source, figures, compiled PDF, summary.pdf
release/       clean artifact bundle (figures, results, paper)
iclr_submission/  anonymous ICLR 2027 package
```

→ [Full reproduction steps](REPRODUCING.md)
