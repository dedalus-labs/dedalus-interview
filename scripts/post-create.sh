#!/usr/bin/env bash
# Codespaces / devcontainer: install uv and project deps (workspace cwd = repo root).
set -euo pipefail
export PATH="${HOME}/.local/bin:${PATH}"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
uv sync
