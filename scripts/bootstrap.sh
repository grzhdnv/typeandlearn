#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
uv sync --locked
npm --prefix apps/frontend ci
