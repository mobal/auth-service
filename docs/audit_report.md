# 🛡️ Comprehensive Architectural & Security Audit Report

## 📑 Overview
This report details a deep architectural review of the `auth-service`. The audit covers security, scalability, reliability, and maintainability across the service's logic layer, infrastructure configuration, and data access patterns.

---

## 🚨 Critical Findings (Immediate Action Required)

### 0. ✅ Verified addition (2026-07-19) — JWT `aud` claim breaks token validation in production
*   **Location:** `app/jwt_bearer.py` -> `JWTBearer._validate_token()`, in combination with `app/services/auth_service.py` -> `_generate_token()`
*   **Issue:** `_generate_token()` now unconditionally sets an `aud` claim on every issued token, but `_validate_token()` still calls `jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])` without passing `audience=`. Reproduced directly against PyJWT 2.7: decoding a token that has an `aud` claim, with no `audience` argument supplied, raises `InvalidAudienceError`. That exception is caught by the trailing `except PyJWTError` in `_validate_token`, so it fails silently into a 403 instead of crashing — which is why this hasn't been noticed from logs alone.
*   **Risk:** Critical — not theoretical. Every token issued via `login()`, `authorize()`, or the client-credentials flow currently fails to validate on `/oauth/revoke` and `/oauth/authorize`, the only two endpoints in this service that require authentication.
*   **Why the test suite didn't catch it:** the `jwt_token` fixture in `tests/conftest.py` sets `iss=None` and never sets `aud`, so the fixture-encoded token used in `JWTBearer` tests has no `aud` claim at all — the test and production code paths have diverged.
*   **Recommendation:** Add `audience=settings.jwt_audience or settings.app_name` (and, while touching this line, `issuer=settings.jwt_issuer or settings.app_name`) to the `jwt.decode()` call in `_validate_token()`. Add a regression test that builds the token the way `_generate_token()` actually does — i.e. with `aud` set — rather than relying on a fixture that omits it.

### 1. Timing Attack Exposure in Authentication Flow
*   **Location:** `app/services/auth_service.py` -> `login()` & `validate_user_password()`
*   **Issue:** The sequence of execution currently allows for timing side-channel attacks to identify valid user accounts. When the system calls `self._user_service_client.get_user_by_email`, if it returns a "User Not Found" response immediately, an attacker can measure the delta in response time to enumerate registered emails before the password check even occurs.
*   **Risk:** High - Potential for automated account enumeration and targeted phishing/brute-force attacks.
*   **Recommendation:** The `user_service_client` should return a uniform "invalid credentials" or result structure even if the user is not found, ensuring the external time signature remains constant regardless of whether the username was valid.

### 2. ⚠️ Corrected — "Atomic Transaction Failures" claim doesn't hold up
*   **Location:** `app/repositories/token_repository.py` -> `consume_by_id()`
*   **Original claim:** consumption is done via a plain `delete_item` without a Condition Expression, allegedly allowing two concurrent requests to both "successfully" consume the same JTI.
*   **Why this is wrong:** DynamoDB serializes writes to a single item — of two concurrent `delete_item` calls against the same key, only the one that actually finds the item gets `Attributes` back in the response; the other sees it already gone. `consume_by_id()` already checks `"Attributes" in response`, which correctly gives exactly-once semantics without needing a `ConditionExpression`. A `ConditionExpression=attribute_exists(jti)` would be redundant here, not a fix for a real race.
*   **What's actually broken nearby, and isn't mentioned in this report:** `TokenRepository.delete_by_id()` (a *different* method, used by `TokenService.delete_by_id()` for logout/manual revocation — not `consume_by_id`) was recently changed to pass `ReturnValues="ALL_OLD"`, but the caller in `token_service.py` still checks `response["ResponseMetadata"]["HTTPStatusCode"] != 200` instead of checking for `"Attributes"` in the response. DynamoDB returns HTTP 200 for a delete on a nonexistent key, so this can never detect a missing token — the existing unit test only passes because it mocks a fabricated `404` status DynamoDB would never actually return. This is the real bug in this area; the `consume_by_id` one is not.
*   **Recommendation:** Leave `consume_by_id()` as-is. Fix `TokenService.delete_by_id()` to check `"Attributes" in response` instead of the HTTP status code, and add a test that exercises the real moto/DynamoDB response shape rather than a hand-constructed mock.

### 3. IAM Privilege Escalation Risk
*   **Location:** `infrastructure/iam.tf`
*   **Issue:** Several actions in the Lambda policy use `"Resource": "*"` for DynamoDB local indices or SSM parameters. While common, it bypasses the principle of least privilege among resources not specifically required by the application.
*   **Risk:** Medium - Potential lateral movement if a lambda execution is compromised.
*   **Recommendation:** Constrain `ssm:GetParameter` and other actions to specific ARNs (e.g., `${aws_ssm_parameter.specific_param.arn}`).

---

## ⚠️ High Risk Findings (Architectural & Security)

### 1. Ambiguous Scope Resolution Logic
*   **Location:** `app/services/auth_service.py` -> `_derive_scope()`
*   **Issue:** When a user has no roles or role-mapped scopes, the method returns `None`. The downstream interpretation of `None` (Is it "No Permission" or "Default Public Scope"?) is not defined at the type level or in the documentation. 
*   **Refactor Recommendation:** Define an explicit behavior for zero-scope users to avoid "Fail-Open" scenarios in permission middleware.

### 2. Lack of Rate Limiting on Exposure Points
*   **Location:** `app/routers/oauth/auth_router.py`
*   **Issue:** The `/oauth/token` and `/oauth/authorize` endpoints are the most sensitive attack vectors. While defined in settings, no global or circuit-breaker logic is implemented in the application layer to throttle repeated failed attempts from a single IP or user agent.
*   **Recommendation:** Implement an Nginx or API Gateway level rate limit; add a custom "Slow down" middleware for consecutive 401/403 errors.

### 3. Overly Broad Redirect Validation
*   **Location:** `app/services/auth_service.py` -> `_validate_redirect_uri()`
*   **Issue:** The validation happens only after the token has been partly processed in some flows. It should be performed at the very beginning of the request lifecycle to prevent "Redirect Injection" where a user is redirected to a malicious site with a valid but hijacked redirect URI code.

---

## ⚖️ Medium Findings (Technical Debt & Performance)

### 1. Redundant Inter-Service Communication
*   **Observation:** In `login` and `exchange_code`, the application performs multiple network calls to the `user_service` to fetch data that is verified only minutes prior or can be partially constructed from the JWT payload itself.
*   **Impact:** Increased latency (higher p99) and higher AWS Lambda execution costs due to unnecessary compute seconds.
*   **Recommendation:** Fetch a "Profile/Status Bundle" in one go.

### 2. Inconsistent Time Type Management
*   **Observation:** The code mixes `pendulum` objects, standard Python integers, and string parsing for timestamps across various modules.
*   **Impact:** Risk of subtle rounding errors or timezone offsets when calculating the "safety_buffer" (e.g., `service_token_lifetime_seconds // 5`).
*   **Recommendation:** Create a consistent utility class to handle all time mutations.

### 3. Logging Information Leakage Potential
*   **Observation:** Several logs in `auth_router.py` print raw values from logic steps. Specifically, ensure that `client_secret` or other PII never hit the `log.info()` path during production outages.
*   **Refactor:** Implementation of a "MaskedString" type for sensitive variables used in logging outputs.

---

## 🚀 Optimization Roadmap

| Phase | Task | Priority | Target Modules |
| :--- | :--- | :--- | :--- |
| **Phase I** | Enforce DynamoDB Condition Expressions for Tokens | Critical | `token_repository.py` |
| **Phase II** | Standardize "Service Exchange" logic to minimize API hops | High | `auth_service.py`, `user_service_client.py` |
| **Phase III** | Refactor and Unified Type-Safe Scope handling | Medium | `auth_service.py`, `models/request/*.py` |
| **Phase IV** | Implementation of standard "Audit Logging" middle-ware | Low | `middleware.py` (if exists) / Router |

---
*Report Generated by Nanocoder Architecture Audit Agent.*
