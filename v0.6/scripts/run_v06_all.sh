#!/usr/bin/env bash
# Run the complete PLAB v0.6 pipeline: evaluate 4 models, reclassify, build report.
#
# FULL PIPELINE (from scratch):
#   Step 1  [models]      4 models × 69 cases → results/v0.6_{model}.jsonl
#   Step 2  [reclassify]  apply evaluator fixes (interrogative refusals +
#                         confused_deputy zero-tool pass) → overwrites same files
#   Step 3  [report]      build results/plab_v06_report.html
#
# The ablation pipeline is separate — see run_ablation_all.sh.
#
# Prerequisites:
#   export H2OGPTE_API_KEY=sk-...
#   export H2OGPTE_ADDRESS=https://h2ogpte.genai.h2o.ai   # or your instance URL
#
# Usage (from the v0.5 directory):
#   bash scripts/run_v06_all.sh
#
# To run a single model only, call its individual script:
#   bash scripts/run_v06_opus47.sh
#   bash scripts/run_v06_gemini.sh
#   bash scripts/run_v06_gpt52.sh
#   bash scripts/run_v06_deepseek.sh
#
# To only re-run post-processing on existing results (no API calls):
#   uv run python scripts/reclassify_v06.py
#   uv run python build_report_v06.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [[ -z "${H2OGPTE_API_KEY:-}" ]]; then
  echo "ERROR: H2OGPTE_API_KEY not set" >&2
  echo "  export H2OGPTE_API_KEY=sk-..." >&2
  exit 1
fi

echo "========================================"
echo "PLAB v0.6 full pipeline"
echo "Working directory: $(pwd)"
echo "========================================"

echo ""
echo "=== Step 1/3: Model evaluation ==="

echo "--- Claude Opus 4.7 ---"
bash scripts/run_v06_opus47.sh

echo "--- Gemini 2.5 Pro ---"
bash scripts/run_v06_gemini.sh

echo "--- GPT-5.2 ---"
bash scripts/run_v06_gpt52.sh

echo "--- DeepSeek V3.2 ---"
bash scripts/run_v06_deepseek.sh

echo ""
echo "=== Step 2/3: Reclassify with evaluator fixes ==="
uv run python scripts/reclassify_v06.py

echo ""
echo "=== Step 3/3: Build HTML report ==="
uv run python build_report_v06.py

echo ""
echo "========================================"
echo "Pipeline complete."
echo "Results:  results/v0.6_{opus47,gemini,gpt52,deepseek}.jsonl"
echo "Log:      results/v0.6_reclassify_log.txt"
echo "Report:   results/plab_v06_report.html"
echo "========================================"
