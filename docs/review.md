# auth-service — Consolidated Review & Action Plan

> **Consolidated 2026-09-02** from `analysis_report.md`, `architectural_review.md`,
> `audit_report.md`, `code_review_report.md`, `code_review_rfc_compliance.md`,
> `fix_priority.md`, and `REPLACE_PENDULUM_PLAN.md` (all deleted; this file replaces them).
> All claims re-verified against the code on `develop`. Fixed/obsolete items were removed;
> only still-actionable work is listed. Items marked **not a gap** were disproven on
> inspection — don't spend time on them.

---

## 1. Architecture Snapshot

N-tiered layered architecture for AWS Lambda: Router (`app/routers/oauth/auth_router.py`)
→ Services (`app/services/`) → Repositories (`app/repositories/`) → DynamoDB, with
`pydantic-settings` + SSM config (`app/settings.py`) and Powertools logging.

**Strengths:** Argon2 hashing, PKCE (S256/plain, constant-time compare), refresh token
rotation, atomic auth-code consumption, `extra="forbid"` models, proper `WWW-Authenticate`
headers, httpx client reuse with timeouts, `aud`/`iss` claims always populated and
validated on decode (fixed in `b7dc314`/`22d9cb2`), password grant deprecated with
warnings, query-param bearer token fallback removed (`55ed4e3`).

**RFC compliance (approx.):** RFC 6749 ~92%, RFC 6750 ~90% (token binding outstanding),
JWT best practices ~90%. Service is production-suitable; remaining items below are
hardening, not blockers.

---

## 2. 🔴 Fix now — real bugs / risks

| Item | Where | Notes |
|---|---|---|
| Timing side-channel in `login()` | `app/services/auth_service.py` | User-not-found short-circuits before the password check → response time leaks registered emails. Run a dummy Argon2 check regardless. |
| `_validate_redirect_uri` fails open | `app/services/auth_service.py` (~:475) | `except Exception: return` silently skips validation on client-repo errors. Narrow the except and reject with `invalid_request`. |
| TOCTOU race in auth code consumption | `app/repositories/authorization_code_repository.py` | Partially mitigated by conditional update — verify the window is actually closed. |
| Refresh token reuse race | `app/services/auth_service.py` (refresh flow) | Same shape; partially mitigated by atomic `consume_by_id`. |
| Test false positive: refresh token type | `tests/unit/service/test_auth_service.py` | Tests pass a `RefreshToken` object where the service expects `str`; pass `refresh_token.token`. |
| Nested moto `mock_aws()` contexts | `tests/conftest.py` | State not reliably shared across nested contexts — flaky-test risk. |

## 3. 🟠 Fix soon

| Item | Where | Notes |
|---|---|---|
| SSM values re-fetched on every access | `app/settings.py` | `@computed_field` properties hit Parameter Store per access. Consider a short explicit-TTL cache. |
| IAM `Resource: "*"` | `infrastructure/iam.tf` | Scope DynamoDB/SSM actions to specific ARNs. |
| `redirect_uri` not URL-validated at model layer | `app/models/request/oauth_authorize.py` | Reject malformed/non-URL input before business logic (separate from registration matching). |
| No DynamoDB exception handling in repositories | `app/repositories/*` | Wrap calls in `ClientError` handling; add error-path tests. |
| Small robustness cluster | various | Cross-field `grant_type` validation, empty-string grant acceptance, `create_service` missing `ConditionExpression`, `ConsistentRead=True` on reads, `SecretStr` for secrets, scope parsing hardening (`strip().split()`), CORS `allow_methods` narrowing. Batch into one cleanup pass. |
| Test gaps | tests/ | No DynamoDB error-path tests, no expired/malformed JWT fixtures, no Lambda-context correlation test, no PKCE unsupported-method test, no concurrent-consumption test. The `in_words` hardcoded-duration assertion was fixed in the pendulum-migration commit (now compares against `settings.jwt_token_lifetime`); remaining `assert exp == 3600` literals in exchange-code tests should also use the setting. |

## 4. 🟡 Fix later / post-MVP

- ~~**Pendulum → stdlib migration**~~ — ✅ **Done 2026-09-02** (see §6).
- ~~**No timezone validation** at import~~ — ✅ **Done 2026-09-02** — `app/__init__.py` now validates `DEFAULT_TIMEZONE` with `ZoneInfo` and raises a descriptive `ValueError` at startup.
- **`require_scope` decorator not async-safe** (`app/security/authorization.py`) — currently **dead code** (defined, never applied). Either delete it or make the wrapper async-safe via `inspect.iscoroutinefunction` before ever using it.
- **Rate limiting** on `/oauth/token` and `/oauth/authorize` — `settings.rate_limiting` defaults to `False`; implement at middleware or API Gateway/WAF level.
- **Token binding** (RFC 6750 §2.2, `cnf` claim / RFC 7800) — bind refresh tokens to `client_id`; post-MVP.
- **JWT hardening:** `nbf` claim, `kid` header + key rotation, HS256 → ES256, `jti` uniqueness conditional write, expiry grace period (leeway).
- **Ambiguous `_derive_scope()` `None` return** for zero-scope users — define explicit behavior to avoid fail-open.
- **Secrets masking in logs** (`client_secret`, `password`, `refresh_token`) — `SecretStr` or masked type.
- **Token introspection (RFC 7662)** — optional extension; track separately if needed.
- **Password grant removal** — OAuth 2.1 best practice, *not* an RFC 6749 requirement; current deprecation state is a reasonable interim.
- **Misc:** docstrings on OAuth models, inconsistent `get_by_id`/`get_by_refresh_token` return types, edge-case repository tests.

## 5. ⚪ Not actually gaps — don't fix

- **`scope` omitted from token response when `None`** — RFC 6749 §5.1 makes it OPTIONAL. Compliant.
- **`state` parameter "not validated"** — RFC 6749 §10.12 assigns callback verification to the **client**; the server only echoes it back, which it does. No `StateRepository` needed.
- **`redirect_uri` "validation is partial"** — false; `_validate_redirect_uri()` runs at the top of `authorize()` against the full registered list. Only the fail-open error path is real (§2).
- **`consume_by_id()` needs a `ConditionExpression`** — false; DynamoDB serializes single-item writes, and the `"Attributes" in response` check already gives exactly-once semantics. Don't add a redundant condition.
- **Token introspection as an "RFC 6749 gap"** — it's RFC 7662, a separate optional spec.

---

## 6. Pendulum → Standard Library Migration — ✅ Completed 2026-09-02

All 13 files migrated; `pendulum` removed from `pyproject.toml` and `uv.lock`
(see "refactor: replace pendulum with stdlib datetime" and
"chore: update uv lock file").

**Mapping used:**

| Feature | Pendulum | Standard Library |
| :--- | :--- | :--- |
| Now (UTC) | `pendulum.now(tz='UTC')` | `datetime.now(tz=timezone.utc)` / `int(time.time())` |
| Addition | `dt.add(minutes=30)` | `dt + timedelta(minutes=30)` |
| From timestamp | `pendulum.from_timestamp(x)` | `datetime.fromtimestamp(x, tz=timezone.utc)` |
| ISO string | `.to_iso8601_string()` | `.isoformat()` |
| Unix timestamp | `.int_timestamp` | `int(dt.timestamp())` / `int(time.time())` |

**Notes:**
- `pendulum.set_local_timezone()` was removed entirely — all timestamps are UTC; `app/__init__.py` now validates `DEFAULT_TIMEZONE` via `ZoneInfo` at startup instead.
- Tests use plain `int(time.time())` arithmetic instead of pendulum date math; `time-machine` remains available in dev deps for frozen-time tests if needed.
- Verified: 137/137 tests pass, `ruff check`/`format` clean, `bandit` clean, `ty` diagnostics unchanged from baseline (85, all pre-existing test-typing noise).
