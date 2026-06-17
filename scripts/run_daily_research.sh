#!/usr/bin/env sh
set -eu

CONFIG_PATH="${AIQRA_CONFIG:-configs/base.yaml}"

python -m quant_research_agent.main --config "$CONFIG_PATH" --json
