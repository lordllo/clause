#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../backend"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m pip install --no-deps -e '.[dev]'
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill "$API_PID"' EXIT INT TERM
cd ../frontend
npm ci
npm run dev
