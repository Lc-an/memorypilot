#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
cd "$root"
if [ ! -x .venv/bin/python ]; then
  echo '请先执行 bash scripts/setup.sh' >&2
  exit 2
fi
export LANGSMITH_TRACING=false
exec .venv/bin/python -m memorypilot.cli "$@"
