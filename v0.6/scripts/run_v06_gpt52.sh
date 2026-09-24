#!/usr/bin/env bash
# Run PLAB v0.6 evaluator (69 cases) against GPT-5.2
# via H2OGPTE's OpenAI-compatible /openai_api/v1 endpoint.
#
# Usage (from the v0.5 directory):
#   export H2OGPTE_API_KEY=sk-...
#   export H2OGPTE_ADDRESS=https://h2ogpte.genai.h2o.ai   # or your instance URL
#   bash scripts/run_v06_gpt52.sh
#
# Output:
#   results/v0.6_gpt52.jsonl   — one result per case (69 lines)
#   results/v0.6_gpt52.log     — full run log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

PYTHON="${PYTHON:-uv run python}"
H2OGPTE_ADDRESS="${H2OGPTE_ADDRESS:-https://h2ogpte.genai.h2o.ai}"

if [[ -z "${H2OGPTE_API_KEY:-}" ]]; then
  echo "ERROR: H2OGPTE_API_KEY not set" >&2
  exit 1
fi

$PYTHON ../v0.5/evaluator_v05_1.py \
  --cases           schema/case.v0.6.cases.jsonl \
  --provider        h2ogpte-openai \
  --model           gpt-5.2 \
  --judge-model     gpt-5.2 \
  --api-key         "$H2OGPTE_API_KEY" \
  --h2ogpte-address "$H2OGPTE_ADDRESS" \
  --output          results/v0.6_gpt52.jsonl \
  --concurrency     3 \
  --rpm             20 \
  2>&1 | tee results/v0.6_gpt52.log
