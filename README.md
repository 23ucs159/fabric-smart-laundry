deployed link: 
             https://fabric-smart-laundry.onrender.com/api/health
# AI-Based Fabric Recognition and Smart Laundry System

Upload a photo of a fabric. The app names the fabric, says how sure it is, and gives simple care advice
(wash, temperature, dry, iron), with a short reason. Results are saved so you can browse history and charts.

> **Good to know:** the bundled model is trained on *synthetic textures*, not real fabric photos, so its scores show that the
> pipeline works, not real-world accuracy. AWS is documented only, not deployed. Demo data is labelled *Synthetic Demo Data*.
> Details: `docs/LIMITATIONS.md`.

## Run it

**Windows:** open a terminal in this folder and run `run.bat`
**Linux / macOS:** `./run.sh`

Then open **http://localhost:8000**. Demo login: `demo@fabric-demo.local` / `DemoPass2026`, or create your own account.

Manual steps (if the script fails):
```
python -m venv .venv
.venv\Scripts\activate            (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
python -m ml.train --synthetic 150
python -m app.services.seed
uvicorn app.main:app --port 8000
```

## What's inside

| Part | Where |
|---|---|
| Web pages (14) and styling | `app/templates`, `app/static` |
| API (docs at `/api/docs`) | `app/api` |
| Fabric model and training | `app/services/ml`, `ml/` |
| Care rules and recommendations | `data/knowledge/care_rules.json`, `app/services/recommendation.py` |
| ETL and data quality | `app/services/etl`, `data/raw`, `data/processed` |
| Laundry assistant (local search) | `app/services/rag`, `data/knowledge/*.md` |
| Security (login, CSRF, limits, encryption) | `app/core` |
| Tests | `tests/` (run `pytest -q`) |

## Common tasks

- **Train on real photos:** put them in `dataset/<fabric>/*.jpg`, then `python -m ml.train --data-dir dataset`
- **Run tests:** `pytest -q` (refresh the report with `python -m scripts.run_tests_report`)
- **Docker:** `copy .env.example .env`, then `docker compose up --build`
- **Settings and secrets:** see `.env.example` (nothing secret is hard-coded)

## Documentation (`docs/`)

Start with `DEMO_CHECKLIST.md` for a demo walkthrough. Others: `ARCHITECTURE`, `DATA_FLOW`, `ERD`, `CLOUD_ARCHITECTURE`,
`SECURITY`, `API`, `TEST_RESULTS`, `DEPLOYMENT`, `LIMITATIONS`, `CPPE_MAPPING`.
