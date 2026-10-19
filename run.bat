@echo off
REM One-command local start (Windows):  run.bat
if not exist .venv ( py -3 -m venv .venv )
call .venv\Scripts\activate
pip install -q -r requirements-dev.txt
if not exist ml\artifacts\fabric_model.joblib ( python -m ml.train --synthetic 150 )
python -m app.services.seed
uvicorn app.main:app --reload --port 8000
