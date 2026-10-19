"""Generate docs/API.md from the live OpenAPI schema (so the documentation cannot drift)."""
from pathlib import Path

from app.main import app

def main():
    spec = app.openapi()
    lines = ["# API reference", "",
             "Generated from the FastAPI OpenAPI schema by `python -m scripts.gen_api_doc`. "
             "Interactive docs: `/api/docs` (Swagger UI) and `/api/redoc`.", "",
             "All state-changing requests (POST/PUT/DELETE) need the header `X-CSRF-Token` (get it from `GET /api/auth/csrf`) "
             "and the session cookie. Everything except `/api/auth/*` and `/api/health` requires login.", "",
             "| Method | Path | Summary |", "|---|---|---|"]
    for path, ops in sorted(spec["paths"].items()):
        for method, op in ops.items():
            lines.append(f"| {method.upper()} | `{path}` | {op.get('summary', '')} |")
    Path(__file__).resolve().parents[1].joinpath("docs", "API.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("docs/API.md written")

if __name__ == "__main__":
    main()
