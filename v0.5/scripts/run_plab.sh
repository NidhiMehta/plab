#!/usr/bin/env bash
# PLAB v0.5 runner — portable, works for any model on H2OGPTE's OpenAI-compatible endpoint.
#
# Prerequisites:
#   pip install openai aiohttp tqdm   (or: uv pip install ...)
#
# Required env vars:
#   H2OGPTE_API_KEY   — your H2OGPTE API key (sk-...)
#
# Optional env vars:
#   H2OGPTE_ADDRESS   — H2OGPTE instance URL (default: https://h2ogpte.genai.h2o.ai)
#   PYTHON            — Python interpreter to use (default: python3)
#
# Usage:
#   export H2OGPTE_API_KEY=sk-...
#   bash scripts/run_plab.sh --model deepseek-ai/DeepSeek-V3.2
#   bash scripts/run_plab.sh --model gemini-2.5-pro
#   bash scripts/run_plab.sh --model claude-opus-4-7 --output results/my_run.jsonl
#
# All extra args are forwarded to evaluator_v05_1.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

PYTHON="${PYTHON:-python3}"
H2OGPTE_ADDRESS="${H2OGPTE_ADDRESS:-https://h2ogpte.genai.h2o.ai}"

if [[ -z "${H2OGPTE_API_KEY:-}" ]]; then
  echo "ERROR: H2OGPTE_API_KEY is not set." >&2
  echo "  export H2OGPTE_API_KEY=sk-..." >&2
  exit 1
fi

# Parse --model and --output from args so we can set a default output path
MODEL=""
OUTPUT=""
REMAINING=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)    MODEL="$2";  shift 2 ;;
    --output)   OUTPUT="$2"; shift 2 ;;
    *)          REMAINING+=("$1"); shift ;;
  esac
done

if [[ -z "$MODEL" ]]; then
  echo "ERROR: --model <name> is required." >&2
  echo "  Example: bash scripts/run_plab.sh --model deepseek-ai/DeepSeek-V3.2" >&2
  exit 1
fi

# Default output: results/v0.5_<slug>.jsonl
if [[ -z "$OUTPUT" ]]; then
  SLUG="${MODEL//\//_}"
  SLUG="${SLUG//[^a-zA-Z0-9_-]/_}"
  OUTPUT="results/v0.5_${SLUG}.jsonl"
fi

LOG="${OUTPUT%.jsonl}.log"

mkdir -p results

echo "Model   : $MODEL"
echo "Output  : $OUTPUT"
echo "Log     : $LOG"
echo "Address : $H2OGPTE_ADDRESS"
echo ""

"$PYTHON" evaluator_v05_1.py \
  --provider        h2ogpte-openai \
  --model           "$MODEL" \
  --judge-model     "$MODEL" \
  --api-key         "$H2OGPTE_API_KEY" \
  --h2ogpte-address "$H2OGPTE_ADDRESS" \
  --output          "$OUTPUT" \
  --concurrency     3 \
  --rpm             20 \
  "${REMAINING[@]}" \
  2>&1 | tee "$LOG"
