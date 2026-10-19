# Deployment

## Local (no Docker)

```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m ml.train --synthetic 150                        # only if ml/artifacts/ is missing or sklearn version differs
python -m app.services.seed                               # optional Synthetic Demo Data
uvicorn app.main:app --reload --port 8000
```

## Docker (implemented, single host)

```bash
cp .env.example .env            # set SECRET_KEY and FERNET_KEY for anything beyond a demo
docker compose up --build       # http://localhost:8000
docker compose --profile postgres up --build   # with PostgreSQL (set POSTGRES_PASSWORD and DATABASE_URL in .env)
```

The image trains the baseline model during the build so the model file matches the installed scikit-learn version.
To use real photos, replace that line in the `Dockerfile` with `python -m ml.train --data-dir <path>` and copy the dataset in.

## Production checklist

- `ENVIRONMENT=production`, `COOKIE_SECURE=true`, real `SECRET_KEY` and `FERNET_KEY` (keep the Fernet key: losing it makes stored notes unreadable)
- PostgreSQL via `DATABASE_URL`; add Alembic migrations before changing the schema
- HTTPS termination (ALB/CloudFront/nginx) and a reverse proxy that forwards the client IP
- One worker per container unless the rate limiter is moved to a shared store
- Backups for the database and `data/uploads` (or S3)
- Never expose `/api/docs` publicly if you do not want the API surface advertised

## CI/CD

`.github/workflows/ci.yml` installs dependencies, retrains a quick model, runs `pytest` with coverage on Python 3.11 and 3.12,
and builds the Docker image. It has **not** been run on GitHub from this environment; it is a ready-to-use definition.
Continuous *deployment* (push to ECR, update an ECS service) is described in `CLOUD_ARCHITECTURE.md` but not implemented.
