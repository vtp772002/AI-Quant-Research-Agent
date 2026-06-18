#!/usr/bin/env sh
set -eu

CONFIGS="${AIQRA_CONFIGS:-${AIQRA_CONFIG:-configs/base.yaml}}"
PYTHON_BIN="${AIQRA_PYTHON:-python}"
BATCH_OUTPUT_DIR="${AIQRA_BATCH_OUTPUT_DIR:-results/daily}"
COMPARISON_METRIC="${AIQRA_COMPARISON_METRIC:-sharpe}"
DAILY_MODE="${AIQRA_DAILY_MODE:-run-batch}"
JOB_QUEUE_PATH="${AIQRA_JOB_QUEUE_PATH:-results/research_jobs.sqlite}"
JOB_IDEMPOTENCY_KEY="${AIQRA_JOB_IDEMPOTENCY_KEY:-daily-$(date -u +%Y-%m-%d)}"
WORKER_ID="${AIQRA_WORKER_ID:-daily-worker}"
WORKER_POLL_SECONDS="${AIQRA_WORKER_POLL_SECONDS:-5}"
WORKER_MAX_JOBS="${AIQRA_WORKER_MAX_JOBS:-}"
WORKER_MAX_RUNTIME_SECONDS="${AIQRA_WORKER_MAX_RUNTIME_SECONDS:-}"

case "$DAILY_MODE" in
  run-batch)
    # shellcheck disable=SC2086
    "$PYTHON_BIN" -m quant_research_agent.main \
      --run-batch $CONFIGS \
      --batch-output-dir "$BATCH_OUTPUT_DIR" \
      --comparison-metric "$COMPARISON_METRIC"
    ;;
  enqueue)
    # shellcheck disable=SC2086
    "$PYTHON_BIN" -m quant_research_agent.main \
      --enqueue-research-job $CONFIGS \
      --job-queue-path "$JOB_QUEUE_PATH" \
      --job-idempotency-key "$JOB_IDEMPOTENCY_KEY" \
      --job-output-dir "$BATCH_OUTPUT_DIR" \
      --comparison-metric "$COMPARISON_METRIC"
    ;;
  worker)
    set -- \
      --research-worker-loop \
      --job-queue-path "$JOB_QUEUE_PATH" \
      --worker-id "$WORKER_ID" \
      --worker-poll-seconds "$WORKER_POLL_SECONDS" \
      --worker-stop-when-idle
    if [ -n "$WORKER_MAX_JOBS" ]; then
      set -- "$@" --worker-max-jobs "$WORKER_MAX_JOBS"
    fi
    if [ -n "$WORKER_MAX_RUNTIME_SECONDS" ]; then
      set -- "$@" --worker-max-runtime-seconds "$WORKER_MAX_RUNTIME_SECONDS"
    fi
    "$PYTHON_BIN" -m quant_research_agent.main "$@"
    ;;
  *)
    echo "Unsupported AIQRA_DAILY_MODE: $DAILY_MODE" >&2
    exit 2
    ;;
esac
