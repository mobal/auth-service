# 🛡️ Comprehensive Architectural & Security Audit Report

## 📑 Overview
This report details a deep architectural review of the `auth-service`. The audit covers security, scalability, reliability, and maintainability across the service's logic layer, infrastructure configuration, and data access patterns.

> **Actualized:** 2026-07-19 — findings verified against current codebase. See status updates inline.

---

## 🚨 Critical Findings (Immediate Action Required)

### 1. Timing Attack Exposure in Authentication Flow
*   **Location:** `app/services/auth_service.py` -> `login()` & `validate_user_password()`
*   **Issue:** The sequence of execution currently allows for timing side-channel attacks to identify valid user accounts. When the system calls `self._user_service_client.get_user_by_email`, if it returns a "User Not Found" response immediately, an attacker can measure the delta in response time to enumerate registered emails before the password check even occurs.
*   **Risk:** High - Potential for automated account enumeration and targeted phishing/brute-force attacks.
*   **Recommendation:** The `user_service_client` should return a uniform "invalid credentials" or result structure even if the user is not found, ensuring the external time signature remains constant regardless of whether the username was valid.

### 2. Atomic Transaction Failures in Token Management
*   **Location:** `app/repositories/authorization_code_repository.py` -> `consume_by_id()` (✅ **Fixed**) and `app/repositories/token_repository.py` -> `delete_by_id()` (⚠️ **Still Open**)
*   **Issue:** ~~The consumption of one-time use credentials (e.g., Authorization Codes or Refresh Tokens) is performed using a standard `delete_item` call without **Condition Expressions**.~~ The authorization code repository is now hardened with `ConditionExpression=Attr("id").exists() & Attr("consumed").not_exists()`. However, the token repository's `delete_by_id()` still uses a plain `delete_item` without conditions — in high-concurrency refresh scenarios, two executions could both delete and regenerate tokens from the same JTI.
*   **Risk:** High (token repo) — two concurrent refresh requests could both succeed from the same refresh token.
*   **Recommendation:** Implement DynamoDB Condition Expressions in `token_repository.py:delete_by_id()` similar to the auth code repository, e.g., add a `consumed` flag or use `ConditionExpression="attribute_exists(jti)"`.

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

### 3. ~~Overly Broad Redirect Validation~~ ✅ Fixed
*   **Location:** `app/services/auth_service.py` -> `_validate_redirect_uri()`
*   **Status:** ✅ **Fixed.** The redirect URI is now validated at the start of the `authorize()` method (before code generation) using `_validate_redirect_uri()` which normalizes URIs and checks against the client's registered `redirect_uris` list. The same validation also runs at exchange time in `exchange_code()`.

---

## ⚖️ Medium Findings (Technical Debt & Performance)

### 1. Redundant Inter-Service Communication
*   **Observation:** In `login` and `exchange_code`, the application performs multiple network calls to the `user_service` to fetch data that is verified only minutes prior or can be partially constructed from the JWT payload itself.
*   **Impact:** Increased latency (higher p99) and higher AWS Lambda execution costs due to unnecessary compute seconds.
*   **Recommendation:** Fetch a "Profile/Status Bundle" in one go.

### 2. Inconsistent Time Type Management
*   **Observation:** The code depends on `pendulum` across 13 files for date/time operations. All timezone-aware operations now consistently use `pendulum.now('UTC')`.
*   **Impact:** Risk of subtle rounding errors or timezone offsets when calculating the "safety_buffer" (e.g., `service_token_lifetime_seconds // 5`). The pendulum dependency also adds maintenance burden.
*   **Recommendation:** Execute the existing migration plan in [`REPLACE_PENDULUM_PLAN.md`](REPLACE_PENDULUM_PLAN.md) to replace pendulum with standard library `datetime`/`zoneinfo`.

### 3. Logging Information Leakage Potential
*   **Observation:** Several logs in `auth_router.py` print raw values from logic steps. Specifically, ensure that `client_secret` or other PII never hit the `log.info()` path during production outages.
*   **Refactor:** Implementation of a "MaskedString" type for sensitive variables used in logging outputs.

---

## 🚀 Optimization Roadmap

| Phase | Task | Priority | Target Modules |
| :--- | :--- | :--- | :--- |
| **Phase I** | Enforce DynamoDB Condition Expressions for Tokens | Critical | `token_repository.py` |
| **Phase I** ✅ | Enforce DynamoDB Condition Expressions for Auth Codes | Done | `authorization_code_repository.py` |
| **Phase II** | Standardize "Service Exchange" logic to minimize API hops | High | `auth_service.py`, `user_service_client.py` |
| **Phase III** | Replace pendulum with stdlib (time management) | Medium | 13 files (see [`REPLACE_PENDULUM_PLAN.md`](REPLACE_PENDULUM_PLAN.md)) |
| **Phase IV** | Refactor and Unified Type-Safe Scope handling | Medium | `auth_service.py`, `models/request/*.py` |
| **Phase V** | Implementation of standard "Audit Logging" middleware | Low | `middlewares.py` / Router |

---
*Report Generated by Nanocoder Architecture Audit Agent. Actualized 2026-07-19.*
