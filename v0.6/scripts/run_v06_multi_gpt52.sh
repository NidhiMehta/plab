#!/usr/bin/env bash
# PLAB v0.6 — 5-run stochastic evaluation: GPT-5.2
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
PYTHON="${PYTHON:-uv run python}"
H2OGPTE_ADDRESS="${H2OGPTE_ADDRESS:-https://h2ogpte.genai.h2o.ai}"
[[ -z "${H2OGPTE_API_KEY:-}" ]] && { echo "ERROR: H2OGPTE_API_KEY not set" >&2; exit 1; }
$PYTHON evaluator_v06_multirun.py \
  --cases schema/case.v0.6.cases.jsonl --provider h2ogpte-openai \
  --model gpt-5.2 --judge-model gpt-5.2 \
  --api-key "$H2OGPTE_API_KEY" --h2ogpte-address "$H2OGPTE_ADDRESS" \
  --output results_multirun/v0.6_gpt52_5run.jsonl \
  --runs 5 --temperature 1.0 --concurrency 3 --rpm 20 \
  2>&1 | tee results_multirun/v0.6_gpt52_5run.log
