# Test results

These numbers are produced by `python -m scripts.run_tests_report`, which runs pytest and writes this file. Nothing here is typed by hand.

- Run at: 2026-10-18 04:18 UTC
- Python 3.12.3 on Linux
- pytest summary line: `148 passed, 1 skipped, 1 warning in 45.24s`
- Line coverage of `app/` and `ml/`: 92%

| Area | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Authentication | 12 | 0 | 0 |
| Security (CSRF, authorization, XSS, file validation, encryption) | 24 | 0 | 0 |
| Database | 6 | 0 | 0 |
| ETL | 9 | 0 | 0 |
| ML | 14 | 0 | 0 |
| Recommendation | 17 | 0 | 0 |
| RAG / assistant (incl. prompt injection) | 32 | 0 | 0 |
| API flow / analytics / settings / seed | 13 | 0 | 0 |
| Frontend smoke | 21 | 0 | 0 |
| Browser end-to-end (Playwright) | 0 | 0 | 1 |
| **Total** | **148** | **0** | **1** |

## Skipped tests and limitations

- tests/e2e/test_e2e_playwright.py:29: E2E_BASE_URL not set

The Playwright browser test (`tests/e2e/`) was **not executed** in the development environment used to produce this report: browser binaries could not be downloaded there. It is included and documented; run it locally as described in `tests/e2e/test_e2e_playwright.py`. Frontend behaviour is covered here only by the server-rendered smoke tests (page rendering, asset serving, element-id consistency between JavaScript and templates, no inline scripts/`innerHTML`). JavaScript was checked with `node --check` and, ad hoc during development, by rendering every page against real API data in a simulated browser (jsdom); that check is not part of this automated suite.

