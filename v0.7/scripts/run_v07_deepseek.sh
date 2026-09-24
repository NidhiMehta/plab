#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
PYTHON="${PYTHON:-uv run python}"
H2OGPTE_ADDRESS="${H2OGPTE_ADDRESS:-https://h2ogpte.genai.h2o.ai}"
[[ -z "${H2OGPTE_API_KEY:-}" ]] && { echo "ERROR: H2OGPTE_API_KEY not set" >&2; exit 1; }
$PYTHON evaluator_v07.py \
  --cases schema/case.v0.7.ipi.jsonl --provider h2ogpte-openai \
  --model deepseek-v3-2 --judge-model claude-opus-4-7 \
  --api-key "$H2OGPTE_API_KEY" --h2ogpte-address "$H2OGPTE_ADDRESS" \
  --output results/v0.7_deepseek.jsonl --concurrency 3 --rpm 20 \
  2>&1 | tee results/v0.7_deepseek.log
