#!/usr/bin/env bash
set -euo pipefail
python3 src/audit.py --dir memory --out report.md --json report.json
cat report.md
