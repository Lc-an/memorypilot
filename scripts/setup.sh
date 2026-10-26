#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
mkdir -p .tools
if [ ! -x .tools/bin/uv ]; then
  curl --fail --location --retry 2 https://astral.sh/uv/0.13.5/install.sh -o .tools/install-uv.sh
  UV_UNMANAGED_INSTALL="$root/.tools/bin" UV_NO_MODIFY_PATH=1 sh .tools/install-uv.sh
fi
export UV_PYTHON_INSTALL_DIR="$root/.tools/python"
export UV_CACHE_DIR="$root/.tools/cache"
.tools/bin/uv python install --no-bin 3.12
.tools/bin/uv sync --frozen
if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
fi
./run.sh doctor
