#!/usr/bin/env bash
# Run the complete PLAB v0.7 IPI pipeline: evaluate 4 models, build report.
#
# Prerequisites:
#   export H2OGPTE_API_KEY=sk-...
#   export H2OGPTE_ADDRESS=https://h2ogpte.genai.h2o.ai
#
# Usage (from the v0.7 directory):
#   bash scripts/run_v07_all.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [[ -z "${H2OGPTE_API_KEY:-}" ]]; then
  echo "ERROR: H2OGPTE_API_KEY not set" >&2
  exit 1
fi

echo "========================================"
echo "PLAB v0.7 IPI pipeline (12 cases x 4 models)"
echo "Working directory: $(pwd)"
echo "========================================"

echo ""
echo "--- Claude Opus 4.7 ---"
bash scripts/run_v07_opus47.sh

echo ""
echo "--- Gemini 2.5 Pro ---"
bash scripts/run_v07_gemini.sh

echo ""
echo "--- GPT-5.2 ---"
bash scripts/run_v07_gpt52.sh

echo ""
echo "--- DeepSeek V3.2 ---"
bash scripts/run_v07_deepseek.sh

echo ""
echo "========================================"
echo "Pipeline complete."
echo "Results: results/v0.7_{opus47,gemini,gpt52,deepseek}.jsonl"
echo "========================================"
