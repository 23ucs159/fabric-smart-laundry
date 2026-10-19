# Limitations

## Machine learning

- The shipped model is a **classical baseline** (hand-crafted colour/texture features + random forest), not a deep CNN or transfer-learning model. This was chosen so it trains in seconds on a CPU with no GPU or large download.
- The shipped model was trained on **procedurally generated synthetic textures**, not photographs of real fabric, because no real labelled fabric dataset was available offline. Its measured test metrics (see `ml/artifacts/metrics.json` and the ML insights page) only show that the pipeline works. **They must not be quoted as real-world accuracy.**
- Real garment photos (folds, shadows, backgrounds, stitching, lighting) will usually be classified much worse. Expect to retrain on a real dataset (`python -m ml.train --data-dir ...`) for any meaningful accuracy.
- Visually similar fabrics (cotton/linen, silk/rayon/nylon) are inherently hard to separate from an image alone. The care label is the authority.
- The class list is fixed at ten. Adding a class requires new training data, a rules entry in `care_rules.json`, and retraining.

## Recommendations and assistant

- Care rules are general guidance written for this project, not verified against any textile standard. They do not cover garment construction, finishes, dyes or blends in detail.
- The assistant uses keyword/intent rules and TF-IDF retrieval; it does not "understand" free-form questions. Questions outside the knowledge base get a fallback message.
- The optional LLM path is implemented but was **not tested against a live API** in this environment.
- The prompt-injection filter is heuristic (see `SECURITY.md`).

## Platform

- Sessions are stateless signed cookies (no server-side revocation); the rate limiter is in-memory and per process.
- SQLite is used in development; PostgreSQL is supported by configuration but **was not tested** here. There are no migrations (tables are created with `create_all`).
- No AWS service is deployed; see `CLOUD_ARCHITECTURE.md`.
- Email/push notifications, data export, MFA, password reset and email verification are not implemented (the Settings page labels what is future work).
- Frontend JavaScript is verified by syntax check and server-side smoke tests; the Playwright browser test is written but was not executed in the build environment.
- Accessibility was designed for (labels, skip link, focus outlines, aria-live regions, keyboard-operable drop zone) but was not audited with assistive technology.

## Data

- Demo records are **Synthetic Demo Data** produced by a seeded generator (`app/services/seed.py`, seed 42). They are not real users or real laundry history.
- The sample images in `data/raw/fabric_images/` are synthetic textures; one intentionally corrupt file is included to exercise the ETL image check.
