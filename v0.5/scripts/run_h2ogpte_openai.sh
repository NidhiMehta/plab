#!/usr/bin/env bash
# Run PLAB v0.5 evaluator against all 90 cases using H2OGPTE's OpenAI-compatible
# /v1 endpoint — native tool calling, no prompt-injection workaround.
#
# Usage:
#   export H2OGPTE_API_KEY=sk-...
#   bash scripts/run_h2ogpte_openai.sh
#
# With uv (from repo root):
#   export H2OGPTE_API_KEY=sk-...
#   uv run examples/agent/my_evaluator/plab/v0.5/evaluator_v05_1.py \
#     --provider h2ogpte-openai --model claude-opus-4-7 --judge-model claude-opus-4-7 \
#     --api-key "$H2OGPTE_API_KEY" --h2ogpte-address https://h2ogpte.genai.h2o.ai \
#     --output examples/agent/my_evaluator/plab/v0.5/results/v0.5_opus47_fixed.jsonl \
#     --concurrency 3 --rpm 20
#
# Output:
#   results/v0.5_opus47_fixed.jsonl   — one result per case
#   results/v0.5_opus47_fixed.log     — full run log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

PYTHON="${PYTHON:-python3}"

if [[ -z "${H2OGPTE_API_KEY:-}" ]]; then
  echo "ERROR: H2OGPTE_API_KEY not set" >&2
  exit 1
fi

"$PYTHON" evaluator_v05_1.py \
  --provider       h2ogpte-openai \
  --model          claude-opus-4-7 \
  --judge-model    claude-opus-4-7 \
  --api-key        "$H2OGPTE_API_KEY" \
  --h2ogpte-address https://h2ogpte.genai.h2o.ai \
  --output         results/v0.5_opus47_fixed.jsonl \
  --concurrency    3 \
  --rpm            20
