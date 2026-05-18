#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
npm run check:python
npm run check:frontend
