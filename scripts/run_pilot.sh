#!/usr/bin/env bash
# run_pilot.sh — full PLAB pipeline in one command
#
# Usage:
#   ./scripts/run_pilot.sh                    # 144-case pilot (default)
#   ./scripts/run_pilot.sh --cells 2          # 2 cases per cell (288 cases)
#   ./scripts/run_pilot.sh --limit 20         # cap evaluator at 20 cases
#   ./scripts/run_pilot.sh --concurrency 8    # more parallel workers
#   ./scripts/run_pilot.sh --skip-generate    # skip corpus regen (already have cases.jsonl)
#   ./scripts/run_pilot.sh --full             # run all 3600 cases (no sampling)
#
# All output lands in results/v0.3/
# Corpus cached at data/v0.3/cases.jsonl (only regenerated if missing or --regen)

set -euo pipefail

PYTHON="/Users/nidhi/git_repos/agentscope/.venv/bin/python"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ── defaults ──────────────────────────────────────────────────────────────
CELLS=1
CONCURRENCY=4
MODEL="qwen3.5:9b"
JUDGE_MODEL="qwen3.5:9b"
LIMIT=""
SKIP_GENERATE=false
FULL=false
REGEN=false

# ── arg parse ─────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --cells)         CELLS="$2";       shift 2 ;;
    --concurrency)   CONCURRENCY="$2"; shift 2 ;;
    --model)         MODEL="$2";       shift 2 ;;
    --judge-model)   JUDGE_MODEL="$2"; shift 2 ;;
    --limit)         LIMIT="$2";       shift 2 ;;
    --skip-generate) SKIP_GENERATE=true; shift ;;
    --regen)         REGEN=true;        shift ;;
    --full)          FULL=true;         shift ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

# ── derived paths ─────────────────────────────────────────────────────────
CASES="data/v0.3/cases.jsonl"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

if $FULL; then
  PILOT_CASES="$CASES"
  TAG="full_${TIMESTAMP}"
else
  PILOT_CASES="/tmp/plab_pilot_${CELLS}cell_${TIMESTAMP}.jsonl"
  TAG="pilot_${CELLS}cell_${TIMESTAMP}"
fi

RESULTS_DIR="results/v0.3"
RESULTS_FILE="${RESULTS_DIR}/${TAG}.jsonl"
SUMMARY_FILE="${RESULTS_DIR}/${TAG}_summary.json"

mkdir -p "$RESULTS_DIR"

# ── step 1: generate corpus ───────────────────────────────────────────────
if $REGEN || ( ! $SKIP_GENERATE && [ ! -f "$CASES" ] ); then
  echo ""
  echo "━━━ [1/4] Generating corpus ━━━"
  $PYTHON -m src.generator --output "$CASES"
else
  echo ""
  echo "━━━ [1/4] Corpus exists — skipping generate ━━━"
  echo "    $CASES"
  if $REGEN; then : ; else echo "    (use --regen to force regeneration)"; fi
fi

# ── step 2: sample pilot ──────────────────────────────────────────────────
if $FULL; then
  echo ""
  echo "━━━ [2/4] Full run — skipping sampling ━━━"
  echo "    Using all cases: $CASES"
else
  echo ""
  echo "━━━ [2/4] Sampling pilot (${CELLS} per cell) ━━━"
  $PYTHON scripts/sample_pilot.py \
    --input "$CASES" \
    --output "$PILOT_CASES" \
    --per-cell "$CELLS"
fi

# ── step 3: evaluate ──────────────────────────────────────────────────────
echo ""
echo "━━━ [3/4] Running evaluator ━━━"

TOTAL_CASES=$(wc -l < "$PILOT_CASES" | tr -d ' ')
BATCH_SIZE=400  # keep memory footprint small on 16GB

EVAL_BASE=(
  --cases "$PILOT_CASES"
  --output "$RESULTS_FILE"
  --model "$MODEL"
  --judge-model "$JUDGE_MODEL"
  --concurrency "$CONCURRENCY"
)

if [[ -n "$LIMIT" ]]; then
  # Single bounded run (pilot / smoke test)
  $PYTHON -m src.evaluator "${EVAL_BASE[@]}" --limit "$LIMIT"
elif $FULL && [[ "$TOTAL_CASES" -gt "$BATCH_SIZE" ]]; then
  # Full run: loop in batches so we never hold all cases in RAM at once
  DONE=0
  BATCH=1
  while [[ "$DONE" -lt "$TOTAL_CASES" ]]; do
    DONE=$(wc -l < "$RESULTS_FILE" 2>/dev/null | tr -d ' ' || echo 0)
    REMAINING=$(( TOTAL_CASES - DONE ))
    [[ "$REMAINING" -le 0 ]] && break
    echo "  batch $BATCH — done=$DONE remaining=$REMAINING (batch_size=$BATCH_SIZE)"
    $PYTHON -m src.evaluator "${EVAL_BASE[@]}" --limit "$BATCH_SIZE"
    BATCH=$(( BATCH + 1 ))
    # Brief pause between batches so Ollama can release memory
    sleep 5
  done
else
  $PYTHON -m src.evaluator "${EVAL_BASE[@]}"
fi

# ── step 4: score ─────────────────────────────────────────────────────────
echo ""
echo "━━━ [4/4] Scoring results ━━━"
$PYTHON -m src.scorer \
  --input "$RESULTS_FILE" \
  --output "$SUMMARY_FILE"

# ── done ──────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Done."
echo "  Results : $RESULTS_FILE"
echo "  Summary : $SUMMARY_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
