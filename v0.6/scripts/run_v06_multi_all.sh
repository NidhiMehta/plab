#!/usr/bin/env bash
# PLAB v0.6 — full 5-run pipeline: 69 cases x 5 runs x 4 models = 1380 evaluations
#
# Prerequisites:
#   export H2OGPTE_API_KEY=sk-...
#   export H2OGPTE_ADDRESS=https://h2ogpte.genai.h2o.ai
#
# Usage (from the v0.6 directory):
#   bash scripts/run_v06_multi_all.sh
#
# Outputs:
#   results_multirun/v0.6_{opus47,gemini,gpt52,deepseek}_5run.jsonl

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

[[ -z "${H2OGPTE_API_KEY:-}" ]] && { echo "ERROR: H2OGPTE_API_KEY not set" >&2; exit 1; }

echo "========================================"
echo "PLAB v0.6 multi-run pipeline"
echo "69 cases x 5 runs x 4 models = 1380 evaluations"
echo "Working directory: $(pwd)"
echo "========================================"

echo ""
echo "--- Claude Opus 4.7 ---"
bash scripts/run_v06_multi_opus47.sh

echo ""
echo "--- Gemini 2.5 Pro ---"
bash scripts/run_v06_multi_gemini.sh

echo ""
echo "--- GPT-5.2 ---"
bash scripts/run_v06_multi_gpt52.sh

echo ""
echo "--- DeepSeek V3.2 ---"
bash scripts/run_v06_multi_deepseek.sh

echo ""
echo "========================================"
echo "Pipeline complete. Results in results_multirun/"
echo "Run scripts/analyze_multirun.py to compute pass rates and CIs."
echo "========================================"
