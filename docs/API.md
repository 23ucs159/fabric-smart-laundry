# API reference

Generated from the FastAPI OpenAPI schema by `python -m scripts.gen_api_doc`. Interactive docs: `/api/docs` (Swagger UI) and `/api/redoc`.

All state-changing requests (POST/PUT/DELETE) need the header `X-CSRF-Token` (get it from `GET /api/auth/csrf`) and the session cookie. Everything except `/api/auth/*` and `/api/health` requires login.

| Method | Path | Summary |
|---|---|---|
| GET | `/api/analytics/charts` | Charts |
| GET | `/api/analytics/summary` | Summary |
| POST | `/api/assistant/ask` | Ask |
| GET | `/api/assistant/suggestions` | Suggestions |
| GET | `/api/auth/csrf` | Csrf |
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Me |
| POST | `/api/auth/register` | Register |
| GET | `/api/etl/report` | Report |
| POST | `/api/etl/run` | Run |
| POST | `/api/fabric/analyze` | Analyze |
| GET | `/api/fabric/{analysis_id}` | Get Analysis |
| DELETE | `/api/fabric/{analysis_id}` | Delete Analysis |
| GET | `/api/fabric/{analysis_id}/image` | Get Image |
| GET | `/api/health` | Health |
| GET | `/api/history` | History |
| GET | `/api/ml/info` | Info |
| GET | `/api/ml/predictions` | Predictions |
| GET | `/api/recommendations/analysis/{analysis_id}` | For Analysis |
| GET | `/api/recommendations/fabrics` | Fabrics |
| GET | `/api/recommendations/lookup` | Lookup |
| POST | `/api/recommendations/select` | Select Mode |
| GET | `/api/recommendations/selections` | Selections |
| GET | `/api/security/audit` | Audit |
| GET | `/api/security/controls` | Controls |
| GET | `/api/settings` | Get Settings |
| DELETE | `/api/settings/data` | Delete My Data |
| POST | `/api/settings/password` | Change Password |
| PUT | `/api/settings/preferences` | Update Preferences |
| PUT | `/api/settings/profile` | Update Profile |
