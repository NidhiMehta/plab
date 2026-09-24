#!/usr/bin/env bash
# Run the full pre-call reasoning ablation: all 4 models × 23 tool_gated cases
# (role_prompt with pre-call check instruction removed).
#
# Runs models sequentially. To run a single model, call its individual script.
#
# Prerequisites:
#   1. Generate the ablation case file first (only needed once):
#        uv run python scripts/gen_ablation_cases.py
#
#   2. Set environment variables:
#        export H2OGPTE_API_KEY=sk-...
#        export H2OGPTE_ADDRESS=https://h2ogpte.genai.h2o.ai
#
# Usage (from the v0.5 directory):
#   bash scripts/run_ablation_all.sh
#
# Outputs (in results/):
#   v0.6_ablation_opus47.jsonl / .log
#   v0.6_ablation_gemini.jsonl / .log
#   v0.6_ablation_gpt52.jsonl  / .log
#   v0.6_ablation_deepseek.jsonl / .log
#
# After all runs complete, analyse results with:
#   uv run python scripts/compare_ablation.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [[ -z "${H2OGPTE_API_KEY:-}" ]]; then
  echo "ERROR: H2OGPTE_API_KEY not set" >&2
  exit 1
fi

if [[ ! -f "schema/case.v0.6.ablation_no_precheck.jsonl" ]]; then
  echo "Ablation case file not found — generating it now..."
  uv run python scripts/gen_ablation_cases.py
fi

echo "=== Running ablation: Claude Opus 4.7 ==="
bash scripts/run_ablation_opus47.sh

echo "=== Running ablation: Gemini 2.5 Pro ==="
bash scripts/run_ablation_gemini.sh

echo "=== Running ablation: GPT-5.2 ==="
bash scripts/run_ablation_gpt52.sh

echo "=== Running ablation: DeepSeek V3.2 ==="
bash scripts/run_ablation_deepseek.sh

echo ""
echo "All ablation runs complete. Generating comparison..."
uv run python scripts/compare_ablation.py
