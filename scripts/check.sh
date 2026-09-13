#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
npm run check:lint
npm run check:python
npm run check:frontend
