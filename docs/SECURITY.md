# Security

Every control below is implemented in code and covered by tests in `tests/test_security.py`, `tests/test_auth.py` and `tests/test_rag.py`.

| Control | Implementation | Where |
|---|---|---|
| Password hashing | Argon2id (`argon2-cffi`), per-password salt, no plain text stored; constant-time dummy verify for unknown emails | `app/core/security.py` |
| Password policy | 8-128 characters, at least one letter and one digit | `password_policy_error` |
| Sessions | `itsdangerous` signed, time-limited cookie; `HttpOnly`, `SameSite=Lax`, `Secure` when `COOKIE_SECURE=true`; session and CSRF token rotate at login | `app/core/security.py`, `app/api/auth.py` |
| CSRF | Per-session token; every POST/PUT/DELETE must send `X-CSRF-Token` (compared in constant time), including login and register | `app/core/deps.py` |
| Rate limiting | Sliding window per client IP: login 10, register 5, upload 20, assistant 30 per 60 s (configurable) -> HTTP 429 + `Retry-After` | `app/core/ratelimit.py` |
| Authorization | Every query filters by `user_id`; another user's record answers 404 (no existence leak); images are served only through an authenticated route with path checks | `app/api/fabric.py` |
| Encryption | Fernet encryption of the analysis note; key from `FERNET_KEY` (never hard-coded; dev key auto-generated to a git-ignored file; production refuses to start without env keys) | `app/core/security.py` |
| Audit logging | register, login, failed login, logout, upload, prediction, data deletion, settings/password changes, blocked assistant prompts; no secrets logged | `app/core/audit.py` |
| Security headers | `Content-Security-Policy` (`default-src 'self'`, no inline scripts/styles), `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, HSTS when secure cookies are on | `app/main.py` |
| Upload validation | Size limit, extension allow-list, real format check by decoding (JPEG/PNG/WEBP), min/max dimensions, decompression-bomb guard, image re-encoded and stored under a random UUID name (client filename never used) | `app/services/ml/validation.py` |
| XSS | Jinja2 auto-escaping; the JavaScript inserts all dynamic text with `textContent` (a test fails if `innerHTML` appears) | `app/static/js/app.js` |
| SQL injection | SQLAlchemy parameterised queries only; the assistant has no database access | all services |
| Assistant safety | Pattern-based prompt-injection filter; the assistant receives only the question text (no DB session, no user object, no tools); an optional LLM sees only retrieved knowledge and may only rephrase it | `app/services/rag/assistant.py` |

## Threat notes and known gaps (see also `LIMITATIONS.md`)

- Logout clears the cookie; there is no server-side session revocation list, so a stolen cookie stays valid until it expires (8 h).
- The in-memory rate limiter is per process and keyed by IP (behind a proxy, configure trusted forwarded headers or rate-limit at the gateway).
- The prompt-injection filter is a heuristic. It reduces risk but is not proof against every attack; the real protection is the architecture (no data or tool access).
- No multi-factor authentication, no email verification or password reset flow.
- The ETL pages are visible to every signed-in user (the sample data is not personal).
- Run behind HTTPS in production and set `COOKIE_SECURE=true`.
