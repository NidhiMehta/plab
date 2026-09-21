#!/usr/bin/env bash
# Run PLAB v0.5 evaluator against all 90 cases using gemini-2.5-pro
# via H2OGPTE's OpenAI-compatible /openai_api/v1 endpoint (native tool calling).
#
# Usage:
#   export H2OGPTE_API_KEY=sk-...
#   export H2OGPTE_ADDRESS=https://h2ogpte.genai.h2o.ai   # or your instance URL
#   bash scripts/run_gemini25pro_h2o.sh
#
# Output:
#   results/v0.5_gemini25pro_h2o.jsonl   — one result per case
#   results/v0.5_gemini25pro_h2o.log     — full run log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

PYTHON="${PYTHON:-python3}"
H2OGPTE_ADDRESS="${H2OGPTE_ADDRESS:-https://h2ogpte.genai.h2o.ai}"

if [[ -z "${H2OGPTE_API_KEY:-}" ]]; then
  echo "ERROR: H2OGPTE_API_KEY not set" >&2
  exit 1
fi

LOG_FILE="results/v0.5_gemini25pro_h2o.log"

"$PYTHON" evaluator_v05_1.py \
  --provider        h2ogpte-openai \
  --model           gemini-2.5-pro \
  --judge-model     gemini-2.5-pro \
  --api-key         "$H2OGPTE_API_KEY" \
  --h2ogpte-address "$H2OGPTE_ADDRESS" \
  --output          results/v0.5_gemini25pro_h2o.jsonl \
  --concurrency     3 \
  --rpm             20 \
  2>&1 | tee "$LOG_FILE"
