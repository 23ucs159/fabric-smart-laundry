# CPPE / engineering mapping

Maps project features to the four engineering modules. "Implemented" means working code in this repository with tests; "Documented" means described only.

## Data Engineering

| Topic | Feature | Status | Where |
|---|---|---|---|
| Collection | Raw fabric records CSV, labelled image folders, user analysis records, prediction results | Implemented | `data/raw/`, `app/api/fabric.py` |
| Validation | Schema, file type, corruption, dimensions, missing labels, duplicates, invalid values | Implemented | `app/services/etl/validate.py`, `app/services/ml/validation.py` |
| Preprocessing | Resize, normalise, centre-crop, optional denoise, stratified train/validation/test split; tabular cleaning, encoding, normalisation | Implemented | `app/services/ml/preprocessing.py`, `etl/transform.py` |
| ETL | Extract -> Validate -> Transform -> Load, data-quality report, messy test data | Implemented | `app/services/etl/`, `data/raw/messy_fabric_records.csv` |
| Storage | Relational schema with foreign keys; processed CSV and JSON reports | Implemented | `app/models/`, `data/processed/` |
| Large-scale ETL | AWS Glue | Documented | `CLOUD_ARCHITECTURE.md` |

## Cloud Engineering

| Topic | Feature | Status |
|---|---|---|
| Scalable architecture | Stateless API, container image, PostgreSQL-ready configuration | Container + config implemented; scaling documented |
| AWS mapping | S3, Lambda, RDS, ECS/EC2, CloudWatch, CloudTrail, Glue, Kinesis | Documented only (nothing deployed) |
| Storage / monitoring | Local upload folder, audit table, `/api/health` | Local equivalents implemented |
| Deployment | Dockerfile, docker-compose (with PostgreSQL profile), CI workflow | Implemented as files; CI not run on GitHub here |

## AI Engineering

| Topic | Feature | Status | Where |
|---|---|---|---|
| Image classification | Colour/texture features + RandomForest, probabilities, 10 classes | Implemented | `app/services/ml/` |
| Training and evaluation | Train/validate/test split, accuracy, precision, recall, F1, confusion matrix | Implemented (measured on synthetic data) | `ml/train.py`, `ml/evaluate.py` |
| Recommendation engine | Rule engine from editable JSON, confidence handling, preferences | Implemented | `app/services/recommendation.py` |
| Explainability | Plain-language explanation and probability list | Implemented | result UI |
| RAG assistant | TF-IDF retrieval over 15 documents, deterministic rules first, source display, optional LLM rephrase | Implemented (LLM path untested live) | `app/services/rag/` |

## Security Engineering

| Topic | Feature | Status |
|---|---|---|
| Authentication | Registration, login, logout, Argon2 hashing | Implemented |
| Authorization | Per-user scoping, cross-user tests | Implemented |
| Encryption | Fernet field encryption, keys from environment | Implemented |
| Session / CSRF / rate limits | Signed HttpOnly cookie, CSRF token, sliding-window limiter | Implemented |
| Auditing | `audit_logs` table and viewer | Implemented |
| Hardening | CSP and other headers, upload validation, XSS-safe rendering, prompt-injection guard | Implemented |
| MFA, session revocation | - | Not implemented (listed as future) |
