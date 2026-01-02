#!/usr/bin/env bash
# Wrapper script for security feed aggregator
# This script is designed to be run from cron

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the script
python3 -m sec_alerts.main --config config.yaml >> logs/sec-alerts.log 2>&1

