#!/usr/bin/env bash
set -euo pipefail
python3 src/audit.py --dir memory --config audit.config.json --out report.md --json report.json
echo "--- report.md ---"
cat report.md
