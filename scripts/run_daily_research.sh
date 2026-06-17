#!/usr/bin/env sh
set -eu

CONFIGS="${AIQRA_CONFIGS:-${AIQRA_CONFIG:-configs/base.yaml}}"
BATCH_OUTPUT_DIR="${AIQRA_BATCH_OUTPUT_DIR:-results/daily}"
COMPARISON_METRIC="${AIQRA_COMPARISON_METRIC:-sharpe}"

# shellcheck disable=SC2086
python -m quant_research_agent.main \
  --run-batch $CONFIGS \
  --batch-output-dir "$BATCH_OUTPUT_DIR" \
  --comparison-metric "$COMPARISON_METRIC"
