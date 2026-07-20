# auth-service — Fix Priority Plan

Synthesized from `code_review_report.md`, `code_review_rfc_compliance.md`,
`audit_report.md`, `architectural_review.md`, and `analysis_report.md`,
cross-checked against the actual code on `develop`. Items marked **not
actually a gap** were claimed as issues in one of the docs but disproven on
inspection — don't spend time on them.

---

## 🔴 Fix right now — live bugs, currently broken or actively insecure

### 1. JWT `aud` claim breaks validation on every protected endpoint
**Files:** `app/jwt_bearer.py` (`_validate_token`), `app/services/auth_service.py` (`_generate_token`)

**Status:** ✅ **Fixed** in `b7dc314` — added `audience=settings.jwt_audience or settings.app_name` and `issuer=settings.jwt_issuer or settings.app_name` to the `jwt.decode()` call in `_validate_token()`. `app/jwt_bearer.py`.

---

### 2. `delete_by_id` still can't detect a missing token
**Files:** `app/repositories/token_repository.py`, `app/services/token_service.py`

**Status:** ✅ **Already fixed** (before this session) — `TokenRepository.delete_by_id()` returns `"Attributes" in response` (checks DynamoDB's `ALL_OLD` return, not HTTP status code). `TokenService.delete_by_id()` checks the boolean result correctly. Tests use moto with real DynamoDB response shapes.

---

### 3. Bearer token accepted via query parameter
**File:** `app/jwt_bearer.py` (lines ~40-42)

**Status:** ✅ **Fixed** in `55ed4e3` — removed the `request.query_params.get("token")` fallback from `HTTPBearer.__call__()` and the now-dead `_get_authorization_credentials_from_token()` method. Requests without an `Authorization` header now fail immediately with 403.

---

### 4. Correlation ID set on a shared Logger singleton, not per-request
**File:** `app/middlewares.py`

**Status:** ✅ **Already fixed** (before this session) — the middleware uses `logger.append_keys(correlation_id=...)` (per-record key injection) rather than `logger.set_correlation_id(...)` (shared state mutation). No per-request correlation ID corruption on concurrent ASGI servers.

---

### 5. Authorization decorator silently no-ops on async route handlers
**File:** `app/security/authorization.py` (lines ~19-37)

**Status:** ➡️ **Not applicable** — the `require_scope` decorator is defined but **never imported or applied** to any route handler. Dead code. Per the original note: "if it's dead code, this drops to the 'later' bucket."

---

## 🟠 Fix soon — real bugs/risks, not on fire but next in line

| Item | Where | Why it matters |
|---|---|---|
| TOCTOU race in auth code consumption | `authorization_code_repository.py` | Two concurrent requests can both fetch and use the same code before either deletes it. Already partially mitigated by a conditional update — confirm it actually closes the window, don't assume. |
| Refresh token reuse race | `auth_service.py` (refresh flow) | Same shape as above; partially mitigated by atomic `consume_by_id`. |
| `_validate_redirect_uri` fails open | `auth_service.py:475` | If the client-repository lookup throws, validation is silently skipped (`except Exception: return`) instead of rejecting the request. The validation logic itself is fine — this is just the error path. |
| Timing side-channel in `login()` | `auth_service.py` | `get_user_by_email()` returning "not found" short-circuits before the password check runs, so response time leaks whether an email is registered. Fix by running the (dummy) password check regardless of whether the user was found. |
| IAM policy uses `Resource: "*"` | `infrastructure/iam.tf` | DynamoDB/SSM actions aren't scoped to specific ARNs. Not exploitable on its own, but widens blast radius if a Lambda execution is ever compromised. |
| SSM values re-fetched on every access | `app/settings.py` | `@cached_property` was removed to fix a staleness bug, but the replacement (`@computed_field` property) now hits SSM Parameter Store on every single property access — every request, potentially several times. Check Parameter Store latency/throttle limits under real load; consider a short explicit-TTL cache as a middle ground. |
| Test false positive: refresh token type mismatch | `tests/unit/service/test_auth_service.py` | Tests pass a `RefreshToken` object where the service expects a `str`; the mock doesn't care, so the test proves nothing about real behavior. Pass `refresh_token.token` instead. |
| Nested moto mock contexts | `tests/conftest.py` | `mock_aws()` nested inside another `mock_aws()` isn't guaranteed to share state consistently across moto versions — flaky tests waiting to happen. |
| `redirect_uri` unvalidated as a URL format in the request model | `app/models/request/oauth_authorize.py` (per code_review_report 2.19) | Separate from the registration-matching check in `authorize()` — this is about rejecting malformed/non-URL input at the model layer before it ever reaches business logic. |

---

## 🟡 Fix later — real, but lower severity or genuinely post-MVP

- **No timezone validation** at import time (`app/__init__.py`) — invalid `default_timezone` crashes at import rather than failing a health check with a clear message.
- **Ambiguous `_derive_scope()` return of `None`** for zero-scope users — define explicit behavior so downstream permission checks don't fail open by accident.
- **Rate limiting** on `/oauth/token` and `/oauth/authorize` — genuinely useful, genuinely not urgent for a service without production traffic yet.
- **Secrets masking in logs** (`client_secret`, `password`, `refresh_token`) — use `SecretStr` or a masked type; low likelihood of accidental logging today, but cheap insurance.
- **Cross-field `grant_type` validation**, empty-string grant/field acceptance, `create_service` missing `ConditionExpression`, eventually-consistent reads after writes, missing DynamoDB exception handling in a few repositories — a cluster of small correctness/robustness items from `code_review_report.md`'s Medium section. None of these are exploitable on their own; batch them into one cleanup pass.
- **Password grant removal or feature-flagging** — reasonable to do, but frame it correctly: this is an **OAuth 2.1 best practice**, not an RFC 6749 requirement (6749 permits the password grant). It's already deprecated with a warning + response header, which is a reasonable interim state.
- **Token binding for refresh/access tokens (RFC 6750 §2.2, `cnf` claim, RFC 7800)** — legitimate defense-in-depth, meaningfully more work (client cert / mTLS or proof-of-possession), correctly scoped as post-MVP.
- **JWT hardening nice-to-haves:** `nbf` claim, `kid` header + key rotation, migrating `HS256` → `ES256`, enforcing `jti` uniqueness at the storage layer, expiry grace period for clock skew. All reasonable, none urgent.
- **Test coverage gaps:** no DynamoDB error-path tests, no edge-case JWT fixtures (expired/malformed), no Lambda-context correlation test. Worth doing before a real production launch, not before the critical fixes above.

---

## ⚪ Not actually gaps — don't put these on any list

These were flagged as issues in one of the review docs but don't hold up
against the actual RFC text or the actual code:

- **`scope` omitted from the token response when `None`** — RFC 6749 §5.1 makes this OPTIONAL. Compliant as-is; only change it for stylistic consistency if you want to, not for compliance.
- **`state` parameter "not validated"** — RFC 6749 §10.12 makes verifying `state` on the callback the **client's** job, not the authorization server's. The server's only obligation is to echo it back unmodified, which it already does correctly. A server-side `StateRepository` would be solving a problem that isn't the server's to solve.
- **`redirect_uri` "validation happens in `exchange_code` but is partial"** — false; `_validate_redirect_uri()` already runs at the top of `authorize()` against the full registered `redirect_uris` list. The only real gap here is the fail-open error path (see the 🟠 list above).
- **`consume_by_id()` needs a `ConditionExpression` to prevent double-consumption** — false; DynamoDB serializes writes to a single item, so of two concurrent `delete_item` calls on the same key, only one gets `Attributes` back. The existing `"Attributes" in response` check already gives correct exactly-once semantics. Don't add a redundant `ConditionExpression` here — fix `delete_by_id` instead (🔴 #2 above), which is the method with the actual bug.
- **Token introspection (RFC 7662) as an "RFC 6749 gap"** — it's a real missing feature if you need it, but it's a separate, optional extension spec. Track it on its own if there's a real use case; don't count it toward RFC 6749 compliance.
