#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
uv sync
npm --prefix apps/frontend install
