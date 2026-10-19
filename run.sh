#!/usr/bin/env bash
# One-command local start (Linux/macOS):  ./run.sh
set -e
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements-dev.txt
[ -f ml/artifacts/fabric_model.joblib ] || python -m ml.train --synthetic 150
python -m app.services.seed
uvicorn app.main:app --reload --port 8000
