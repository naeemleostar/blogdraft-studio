#!/usr/bin/env bash
# BlogDraft Studio launcher for macOS / Linux
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null; then
  echo "Python 3 is not installed. Get it from https://www.python.org/downloads/"; exit 1
fi
if [ ! -x .venv/bin/python ]; then
  echo "First start: setting things up..."
  python3 -m venv .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -r requirements.txt || exit 1
fi
exec .venv/bin/python server.py
