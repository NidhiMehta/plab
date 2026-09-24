#!/usr/bin/env bash
# Run PLAB v0.7 IPI evaluator (12 cases) against Claude Opus 4.7
#
# Usage (from the v0.7 directory):
#   export H2OGPTE_API_KEY=sk-...
#   export H2OGPTE_ADDRESS=https://h2ogpte.genai.h2o.ai
#   bash scripts/run_v07_opus47.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

PYTHON="${PYTHON:-uv run python}"
H2OGPTE_ADDRESS="${H2OGPTE_ADDRESS:-https://h2ogpte.genai.h2o.ai}"

if [[ -z "${H2OGPTE_API_KEY:-}" ]]; then
  echo "ERROR: H2OGPTE_API_KEY not set" >&2
  exit 1
fi

$PYTHON evaluator_v07.py \
  --cases           schema/case.v0.7.ipi.jsonl \
  --provider        h2ogpte-openai \
  --model           claude-opus-4-7 \
  --judge-model     claude-opus-4-7 \
  --api-key         "$H2OGPTE_API_KEY" \
  --h2ogpte-address "$H2OGPTE_ADDRESS" \
  --output          results/v0.7_opus47.jsonl \
  --concurrency     3 \
  --rpm             20 \
  2>&1 | tee results/v0.7_opus47.log
