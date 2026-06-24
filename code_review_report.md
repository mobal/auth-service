# Auth-Service Code Review Report

## Executive Summary — Still-Actionable Findings

| # | Finding | Severity | Difficulty | Recommendation |
|---|---------|----------|------------|----------------|
| | **Critical / High** | | | |
| ~~1.3~~ | ~~Incomplete PyJWT exception coverage~~ | 🔴 High | 🟢 Easy | ✅ **Fixed** |
| 1.5 | TOCTOU race in auth code consumption | 🔴 High | 🟡 Medium | ⏳ **Fix Later** — already partially mitigated by conditional update |
| 1.6 | Refresh token reuse race condition | 🔴 High | 🟡 Medium | ⏳ **Fix Later** — already partially mitigated by atomic `consume_by_id` |
| ~~1.8~~ | ~~Wrong OAuth error message for response_type~~ | 🔴 High | 🟢 Easy | ✅ **Fixed** |
| ~~1.12~~ | ~~CORS allows all origins~~ | 🔴 High | 🟢 Easy | ✅ **Fixed** |
| 1.15 | SSM caching reliability with `@computed_field @cached_property` | 🔴 High | 🟡 Medium | ⏳ **Fix Later** — verify interaction manually first |
| 1.18 | Decorator not async-safe | 🔴 High | 🟡 Medium | ✅ **Fix** — add async wrapper detection |
| ~~1.21~~ | ~~Env file loading order wrong~~ | 🔴 High | 🟢 Easy | ✅ **Fixed** |
| ~~1.22~~ | ~~Logger initialized before env files~~ | 🔴 High | 🟢 Easy | ✅ **Fixed** |
| ~~1.23~~ | ~~ErrorResponse timestamp at class time~~ | 🔴 High | 🟢 Easy | ✅ **Fixed** |
| 1.24 | No timezone validation | 🔴 High | 🟡 Medium | ✅ **Fix** — add try/except for `UnknownTimeZoneError` |
| 1.25 | Test false positives: refresh token type | 🔴 High | 🟡 Medium | ✅ **Fix** — ensure string not object passed |
| ~~1.26~~ | ~~Test false positives: no return assertions~~ | 🔴 High | 🟢 Easy | ✅ **Fixed** |
| ~~1.27~~ | ~~Test false positive: no body assertions~~ | 🔴 High | 🟢 Easy | ✅ **Fixed** |
| 1.29 | Nested moto mock contexts | 🔴 High | 🟡 Medium | ⏳ **Fix Later** — low risk in current moto versions |
| 1.30 | Token accepted via query param | 🔴 High | 🟡 Medium | ⚠️ **Consider** — breaking change; gate behind config toggle |
| 1.31 | Correlation ID pollution | 🔴 High | 🔴 Hard | ⚠️ **Consider** — only affects non-Lambda ASGI deployments |
| | **Medium** | | | |
| 2.3 | All 4xx treated as password failure | 🟡 Medium | 🟢 Easy | ✅ **Fix** — check for 400/422 specifically |
| 2.5 | Inconsistent error logging in client | 🟡 Medium | 🟢 Easy | ✅ **Fix** — standardize log level |
| 2.9 | Cached service token can become stale | 🟡 Medium | 🟢 Easy | ✅ **Fix** — shorter cache TTL |
| 2.10 | Logging entire JWTToken object | 🟡 Medium | 🟢 Easy | ✅ **Fix** — remove from `extra` dict |
| 2.11 | SSM param names not validated at startup | 🟡 Medium | 🟡 Medium | ✅ **Fix** — add `@model_validator` |
| 2.12 | No error handling around SSM calls | 🟡 Medium | 🟡 Medium | ✅ **Fix** — wrap in try/except |
| 2.13 | Type mismatch `os.environ.get()` → `get_parameter()` | 🟡 Medium | 🟢 Easy | ✅ **Fix** — add type narrowing |
| 2.14 | Duplicate ExceptionMiddleware | 🟡 Medium | 🟢 Easy | ✅ **Fix** — remove explicit middleware |
| 2.15 | Catch-all double-logs exceptions | 🟡 Medium | 🟢 Easy | ✅ **Fix** — remove `logger.error` |
| 2.16 | HTTPException logged at exception level | 🟡 Medium | 🟢 Easy | ✅ **Fix** — use `logger.warning` |
| 2.17 | RequestValidationError logged at exception level | 🟡 Medium | 🟢 Easy | ✅ **Fix** — use `logger.warning` |
| 2.18 | Missing cross-field grant_type validation | 🟡 Medium | 🟡 Medium | ⏳ **Fix Later** — partially handled by model dispatch |
| 2.19 | `redirect_uri` unvalidated in model | 🟡 Medium | 🟡 Medium | ✅ **Fix** — add URL validator |
| 2.20 | Grant type accepts empty strings | 🟡 Medium | 🟢 Easy | ✅ **Fix** — add `Literal` or `min_length` |
| 2.21 | Password/refresh_token plain strings | 🟡 Medium | 🟡 Medium | ⚠️ **Consider** — `SecretStr` breaks serialization |
| 2.22 | Secret stored as plain str | 🟡 Medium | 🟡 Medium | ✅ **Fix** — use `pydantic.SecretStr` |
| 2.23 | No DynamoDB exception handling (auth_codes) | 🟡 Medium | 🟡 Medium | ✅ **Fix** — add try/except |
| 2.24 | `create_service` without ConditionExpression | 🟡 Medium | 🟢 Easy | ✅ **Fix** — add `ConditionExpression` |
| 2.25 | Eventually consistent reads stale data | 🟡 Medium | 🟢 Easy | ✅ **Fix** — add `ConsistentRead=True` |
| 2.26 | No DynamoDB exception handling (services) | 🟡 Medium | 🟡 Medium | ✅ **Fix** — add try/except |
| 2.28 | ContextVar without default | 🟡 Medium | 🟢 Easy | ✅ **Fix** — add `default=""` |
| 2.29 | No exception handling in dispatch | 🟡 Medium | 🟡 Medium | ✅ **Fix** — add try/except/finally |
| 2.30 | Overly broad `except Exception` | 🟡 Medium | 🟢 Easy | ✅ **Fix** — narrow to specific exceptions |
| 2.32 | No default for STAGE env var | 🟡 Medium | 🟢 Easy | ✅ **Fix** — add `default='test'` |
| 2.33 | Monkeypatch passes None values | 🟡 Medium | 🟢 Easy | ✅ **Fix** — add defaults |
| 2.34 | No edge-case repository tests | 🟡 Medium | 🔴 Hard | ⚠️ **Consider** — time-consuming |
| 2.36 | jwt_bearer fixture wired to real infra | 🟡 Medium | 🟡 Medium | ⏳ **Fix Later** — refactor for DI |
| 2.37 | Mock return type mismatch | 🟡 Medium | 🟢 Easy | ✅ **Fix** — match real contract |
| 2.38 | No expired JWT test | 🟡 Medium | 🟢 Easy | ✅ **Fix** — add test |
| 2.39 | No ValidationError test | 🟡 Medium | 🟢 Easy | ✅ **Fix** — add test |
| 2.42 | No AWS Lambda context test | 🟡 Medium | 🟡 Medium | ⏳ **Fix Later** — niche path |
| | **Low / Info** | | | |
| 3.1 | Inconsistent return types | 🟢 Low | 🟡 Medium | ⏳ **Fix Later** — refactor both to same type |
| 3.2 | Misleading param name `code_id` | 🟢 Low | 🟢 Easy | ✅ **Fix** — rename |
| 3.3 | Unnecessary round-trip conversion | 🟢 Low | 🟢 Easy | ✅ **Fix** — simplify |
| 3.4 | Timezone inconsistency | 🟢 Low | 🟢 Easy | ✅ **Fix** — use `pendulum.now('UTC')` |
| 3.5 | F-strings in logger calls | 🟢 Low | 🟢 Easy | ✅ **Fix** — use `%s` formatting |
| 3.6 | Missing return type annotations | 🟢 Low | 🟢 Easy | ✅ **Fix** — add type hints |
| 3.7 | Unused module-level dict | 🟢 Low | 🟢 Easy | ✅ **Fix** — remove dead code |
| 3.8 | Dead default in `request.scope.get()` | 🟢 Low | 🟢 Easy | ✅ **Fix** — simplify |
| 3.9 | No docstrings on models | 🟢 Low | 🔴 Hard | ⚠️ **Consider** — time-consuming |
| 3.14 | Unused fixture `jwt_auth` | 🟢 Low | 🟢 Easy | ✅ **Fix** — remove |
| 3.15 | Redundant `import pytest as pytest` | 🟢 Low | 🟢 Easy | ✅ **Fix** — simplify |
| 3.17 | Exception type assertion uses `__name__` | 🟢 Low | 🟢 Easy | ✅ **Fix** — use direct type comparison |
| 3.18 | No DynamoDB error tests | 🟢 Low | 🔴 Hard | ⚠️ **Consider** — time-consuming |
| 3.19 | No edge-case JWT token fixtures | 🟢 Low | 🟡 Medium | ⏳ **Fix Later** — add fixtures |

**Legend:**
- **Difficulty:** 🟢 Easy = single-file change, <10 LOC; 🟡 Medium = cross-file change, 10-50 LOC; 🔴 Hard = significant refactor or new tests
- **Recommendation:** ✅ **Fix** = should be fixed; ⏳ **Fix Later** = lower priority or partially mitigated; ⚠️ **Consider** = evaluate trade-offs before fixing

---

## Overview

This review analyzed 14 source files and 16 test/configuration files, finding approximately 230+ issues across the codebase. The most critical problems fall into three categories: **concurrency bugs** (shared mutable state in a JWT bearer that can leak tokens between requests), **security gaps** (missing RFC-mandated headers, open redirect vulnerabilities, token replay), and **test false positives** (tests that pass without actually verifying the behavior they claim to test).

> **Validation Note:** ~60% of findings below have been **already fixed** in the current codebase (struck through and grouped at the end of each section). The original report appears to have been generated against an older version. Key resolved items include the JWTBearer race condition, missing WWW-Authenticate headers, ValidationError handling, authorization code replay, and multiple test false positives. See [`plans/validated_code_review_plan.md`](plans/validated_code_review_plan.md) for the full validation.

---

## 1. Critical / High

### 🔴 Still Actionable Findings

---

### ~~1.3 Incomplete PyJWT exception coverage~~ ✅ Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/jwt_bearer.py` | **Lines:** 129-133~~

~~Only `DecodeError` and `ExpiredSignatureError` are caught. Other `PyJWTError` subclasses (`InvalidAlgorithmError`, `InvalidTokenError`, `InvalidKeyError`, `MissingRequiredClaimError`, `ImmatureSignatureError`, `InvalidAudienceError`, `InvalidIssuerError`, `InvalidIssuedAtError`) will propagate as unhandled 500 errors.~~

~~**Fix:** Catch `PyJWTError` (the base class of all PyJWT exceptions) instead of or in addition to the narrower types.~~

---

### 1.5 TOCTOU race condition in authorization code consumption

**File:** `/Users/mobal/src/p4493/auth-service/app/repositories/authorization_code_repository.py` | **Lines:** 56-82

Two concurrent requests can both call `get_by_code()` with the same code, both receive the `AuthorizationCode`, and both proceed to use it before either calls `delete_by_id()`. The DynamoDB delete is unconditional and not conditional on the code still existing.

**Fix:** Use a conditional delete or a DynamoDB transaction. Alternatively, store a `consumed` flag and use a conditional update to atomically claim the code.

---

### 1.6 Refresh token reuse race condition

**File:** `/Users/mobal/src/p4493/auth-service/app/services/auth_service.py` | **Lines:** 269-291

The `refresh` method has no atomicity for the read-delete-create cycle. Two concurrent requests with the same refresh token can both pass the TTL check before either reaches the delete, producing two independent valid token pairs from the same original refresh token.

**Fix:** Use a conditional delete (DynamoDB ConditionExpression) that atomically deletes the old record and only proceeds if it still exists. The second concurrent request's delete should fail, preventing duplicate token generation.

---

### ~~1.8 Response type error uses wrong OAuth error message~~ ✅ Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/routers/oauth/auth_router.py` | **Lines:** 188, 193~~

~~When `response_type != 'code'`, the code raises `OAuthException` with `ERROR_MESSAGE_UNSUPPORTED_GRANT_TYPE` ("Unsupported grant type") instead of "Unsupported response type".~~

~~**Fix:** Create a dedicated constant `ERROR_MESSAGE_UNSUPPORTED_RESPONSE_TYPE` and use that instead.~~

---

### ~~1.12 CORS middleware allows all origins in an authentication service~~ ✅ Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/api_handler.py` | **Lines:** 25-27~~

~~`CORSMiddleware` is configured with `allow_origins=["*"]`, permitting any website to make cross-origin requests to this auth service.~~

~~**Fix:** Restrict `allow_origins` to a whitelist of known frontend domains, loaded from `settings.allowed_origins`.~~

---

### 1.15 SSM API call on every property access with no caching

**File:** `/Users/mobal/src/p4493/auth-service/app/settings.py` | **Lines:** 26-48

`@computed_field @property` in Pydantic v2 is evaluated on every attribute access. Every access to `.client_secret`, `.jwt_secret`, or `.user_service_base_url` makes a live SSM API call. Under load this causes excessive latency (~100-500ms each), SSM throttling, and AWS cost.

**Fix:** Use `@cached_property` from `functools` or use the `max_age` parameter of `parameters.get_parameter(..., max_age=300)`.

---

### 1.18 Decorator is not async-safe; silently breaks async route handlers

**File:** `/Users/mobal/src/p4493/auth-service/app/security/authorization.py` | **Lines:** 19-37

The wrapper is synchronous. If the decorated function is an async coroutine (normal for FastAPI), `func(...)` returns a coroutine object without executing it.

**Fix:** Make the wrapper detect whether `func` is async: use `inspect.iscoroutinefunction(func)` and define an async wrapper accordingly.

---

### ~~1.21 Env file loading order gives .env highest priority, silently overriding production values~~ ✅ Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/__init__.py` | **Lines:** 9, 16-20~~

~~The list `['.env', '.env.dev', '.env.local', '.env.prod']` with `override=False` means `.env` (loaded first) wins for each variable. A developer's local `.env` silently overrides `.env.prod` values.~~

~~**Fix:** Reverse the list order so `.env.prod` is loaded last, or use `override=True` for more specific files.~~

---

### ~~1.22 Logger initialized before env files are loaded~~ ✅ Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/__init__.py` | **Lines:** 10, 23~~

~~The Logger is created on line 10, but `load_env_files()` is called on line 23. Logger configuration from `.env` files (LOG_LEVEL, POWERTOOLS_LOG_LEVEL) is silently ignored.~~

~~**Fix:** Move Logger instantiation after `load_env_files()`.~~

---

### ~~1.23 ErrorResponse timestamp evaluated once at class definition time, not per-instance~~ ✅ Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/models/response/error.py` | **Line:** 10~~

~~`timestamp: int = int(time.time())` evaluates at class definition time, so every ErrorResponse instance gets the same timestamp for the lifetime of the module.~~

~~**Fix:** Use `Field(default_factory=lambda: int(time.time()))`.~~

---

### 1.24 No validation of the timezone string before passing to pendulum

**File:** `/Users/mobal/src/p4493/auth-service/app/__init__.py` | **Line:** 27

`settings.default_timezone` could be None, empty, or an invalid IANA timezone string. `pendulum.timezone()` would raise an unknown timezone exception crashing at import time.

**Fix:** Validate the timezone string, catching `pendulum.UnknownTimeZoneError`.

---

### 1.25 Test false positives: Refresh token type mismatch in auth_service tests

**File:** `/Users/mobal/src/p4493/auth-service/tests/unit/service/test_auth_service.py` | **Lines:** 155-189, 191-206, 239-272

Three refresh tests pass a `RefreshToken` object to `auth_service.refresh()` which expects a `str`. The mock on `get_by_refresh_token` ignores the type mismatch, so tests pass but prove nothing about real behavior.

**Fix:** Pass `refresh_token.token` (a string) instead of the `RefreshToken` object.

---

### ~~1.26 Critical test false positives: get_by_id and get_by_refresh_token tests never assert return values~~ ✅ Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/tests/unit/service/test_token_service.py` | **Lines:** 89-102, 104-122~~

~~Both tests patch the repository but never capture or assert on the service method's return value. If the service stopped returning data, these tests would still pass.~~

~~**Fix:** Capture return values and assert they match expected output.~~

---

### ~~1.27 Test false positive: Token refresh success test does not assert token issuance~~ ✅ Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/tests/integration/test_auth_api.py` | **Lines:** 195-207~~

~~Only checks `status_code == 200` and cache headers. Never asserts the response body contains a new `access_token` or `refresh_token`.~~

~~**Fix:** Add JSON body assertions for `access_token` and `refresh_token`.~~

---

### 1.29 Nested moto mock contexts can cause inconsistent test state

**File:** `/Users/mobal/src/p4493/auth-service/tests/conftest.py` | **Lines:** 17-52, 67-74

The `setup` fixture wraps in `mock_aws()` and the `dynamodb_resource` fixture opens a second nested `mock_aws()` context. Moto state is not reliably shared across nested contexts in all moto versions.

**Fix:** Use a single `mock_aws()` context or use separate `@mock_ssm` / `@mock_dynamodb` decorators without nesting.

---

### 1.30 Token accepted via query parameter leaks credentials through URLs

**File:** `/Users/mobal/src/p4493/auth-service/app/jwt_bearer.py` | **Lines:** 40-42

Falls back to `request.query_params.get('token')` when the Authorization header is missing. URLs containing bearer tokens are logged by web servers, load balancers, proxies, and CDNs; they appear in browser history and leak via the `Referer` header.

**Fix:** Remove the query-parameter fallback or gate it behind an explicit configuration toggle that defaults to off.

---

### 1.31 Correlation ID pollution across requests in concurrent environments

**File:** `/Users/mobal/src/p4493/auth-service/app/middlewares.py` | **Lines:** 15, 39

`logger.set_correlation_id(correlation_id.get())` sets a mutable value on a singleton Logger shared across all requests. In a concurrent ASGI server, two requests can overwrite each other's correlation ID.

**Fix:** Use `logger.append_keys(correlation_id=correlation_id.get())` with keys that force per-record lookup, or configure the Logger to read from the ContextVar at emission time.

---

### ✅ Already Fixed Findings

---

### ~~1.1 Shared mutable state on JWTBearer instance creates a race condition enabling cross-user token leakage~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/jwt_bearer.py` | **Lines:** 110, 125~~

~~The `self.decoded_token` attribute is set in `_validate_token` (line 125) and read back in `__call__` (line 110). FastAPI reuses the same `JWTBearer` instance across all requests. Under concurrent async handling (Uvicorn, Daphne, or any multi-worker ASGI server), two requests can interleave: Request A sets `self.decoded_token`, Request B overwrites it, then Request A returns Request B's decoded token. This means User A could be authenticated with User B's token claims.~~

~~**Fix:** Replace the instance attribute with a local variable. In `_validate_token`, return the `JWTToken` instance directly. In `__call__`, capture the return value in a local variable.~~

---

### ~~1.2 Unhandled Pydantic ValidationError when JWT payload is missing required claims~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/jwt_bearer.py` | **Lines:** 116-117~~

~~`JWTToken(**jwt.decode(...))` raises `pydantic.ValidationError` if the decoded payload is missing required fields (`jti`, `exp`, `iat`, `sub`). This is **not** a subclass of `DecodeError` or `ExpiredSignatureError`, so it propagates as an unhandled 500, leaking the fact that a token validation failure occurred.~~

~~**Fix:** Add `except (ValidationError, ...)` alongside the existing handlers.~~

---

### ~~1.4 Authorization code replay vulnerability (no single-use enforcement)~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/models/authorization_code.py` | **Lines:** 5-8~~

~~The model has no `used: bool` or `consumed_at` field. RFC 6749 Section 4.1.2 requires authorization codes to be single-use. Without this, a compromised code can be replayed indefinitely.~~

~~**Fix:** Add a `used: bool = False` field and a `mark_used()` method. The service layer must check this flag before authorizing a token exchange.~~

---

### ~~1.7 Authorization code not deleted on PKCE validation failure, enabling brute-force attacks~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/services/auth_service.py` | **Lines:** 449-451~~

~~The authorization code is deleted only after successful PKCE validation. If `_validate_pkce` raises an exception, the code remains valid in the database, allowing an attacker to retry the code exchange repeatedly.~~

~~**Fix:** Delete the authorization code immediately after the initial validity check, before running PKCE validation. Make it single-use regardless of the reason for failure.~~

---

### ~~1.9 OAuthException never includes error_description in HTTP response~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/exceptions.py` | **Lines:** 21-31~~

~~The constructor accepts `error_description` and stores it in `self.oauth_error_description`, but only the error code string is passed via `detail=error` to the parent constructor. Per RFC 6749 Section 5.2, OAuth error responses MUST include both `error` and `error_description`.~~

~~**Fix:** Pass `detail={"error": error, "error_description": error_description}` to `super().__init__()`.~~

---

### ~~1.10 Missing WWW-Authenticate headers on 401 responses~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/exceptions.py` | **Lines:** 11-13, 34-36, 39-41~~

~~`InvalidCredentialsException`, `TokenExpiredException`, and `TokenMismatchException` return 401 without the required `WWW-Authenticate` header. RFC 7235 Section 3.1 and RFC 6750 require this header for clients to determine the authentication scheme.~~

~~**Fix:** Add the appropriate `WWW-Authenticate` header parameter to each exception's `super().__init__()` call.~~

---

### ~~1.11 Debug mode configurable via settings may expose stack traces in production~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/api_handler.py` | **Line:** 21~~

~~FastAPI is initialized with `debug=settings.debug`. If set to `True` in production (through env vars or SSM), FastAPI returns detailed stack traces to clients on every unhandled exception, leaking internal implementation details, file paths, and source code excerpts.~~

~~**Fix:** Remove the `debug` parameter or hard-code it to `False` in production: `debug=settings.debug if settings.stage != 'prod' else False`.~~

---

### ~~1.13 Logging full Lambda event may expose sensitive request data~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/api_handler.py` | **Line:** 31~~

~~`logger.inject_lambda_context` is called with `log_event=True`, causing the entire Lambda event payload (including `Authorization` headers, bearer tokens, cookies) to be written to CloudWatch logs.~~

~~**Fix:** Set `log_event=False` or sanitize the event before logging.~~

---

### ~~1.14 Redirect URI accepted from user input without validation at the router layer~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/routers/oauth/auth_router.py` | **Lines:** 196-201, 215~~

~~The authorize endpoint accepts `redirect_uri` as a free-form query string and passes it directly to `auth_service.authorize()` and into the `Location` header. If not validated against registered URIs, this enables an OAuth open-redirect vulnerability.~~

~~**Fix:** Validate the redirect URI against the client's registered allowed URIs at the router layer.~~

---

### ~~1.16 Scope check uses OR instead of AND logic~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/security/authorization.py` | **Line:** 23~~

~~The authorization check uses `any(scope in token_scopes for scope in required_scopes)`, meaning the request is authorized if the token has ANY ONE of the required scopes. Standard OAuth2 uses AND logic (ALL required scopes must be present), making this a potential privilege escalation.~~

~~**Fix:** Replace `any(...)` with `all(...)`. If OR is truly intended, document it clearly.~~

---

### ~~1.17 Token can be None, causing AttributeError crash~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/security/authorization.py` | **Lines:** 20-21~~

~~If `token_param` is not present in kwargs or its value is `None`, `kwargs.get(token_param)` returns `None`, and `token.scope` crashes with `AttributeError` resulting in a 500 instead of 401/403.~~

~~**Fix:** Add a guard: `if token is None: raise HTTPException(401, ...)` before accessing `token.scope`.~~

---

### ~~1.19 Token deleted before new tokens are generated, risking data loss on failure~~ ✅ Already Fixed (by-design)

~~**File:** `/Users/mobal/src/p4493/auth-service/app/services/auth_service.py` | **Lines:** 276-280~~

~~In `refresh()`, the old token is deleted before `_generate_tokens` is called. If token generation fails, the old token record is permanently deleted and the user must re-authenticate entirely.~~

~~**Fix:** Generate new tokens first, then delete the old record. If generation fails, the old token remains valid.~~

---

### ~~1.20 Crash if `service.scopes` is None~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/services/auth_service.py` | **Line:** 322~~

~~`set(service.scopes)` raises `TypeError: 'NoneType' object is not iterable` if service has no scopes.~~

~~**Fix:** Use `allowed = set(service.scopes) if service.scopes else set()`.~~

---

### ~~1.28 Monkeypatch-based 404 tests can produce false positives~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/tests/unit/client/test_user_service_client.py` | **Lines:** 39-58, 96-115~~

~~The `raise_404` function ignores all arguments. If the implementation changes from `httpx.get()` to `httpx.Client().get()`, the monkeypatch silently stops working and tests pass without exercising any real code path.~~

~~**Fix:** Use `httpx_mock.add_response(status_code=404)` for consistency with the rest of the test class.~~

---

### ~~1.32 Extra fields silently ignored in request models~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/models/models.py` | **Line:** 6~~

~~The base model does not set `extra = "forbid"`. Pydantic v2 defaults to `extra = "ignore"`, silently dropping unexpected fields in request payloads. For an auth service, this means typos, API contract drift, or attacker-injected extra fields all pass without detection.~~

~~**Fix:** Add `extra = "forbid"` to `model_config`.~~

---

## 2. Medium

### 🔴 Still Actionable Findings

---

### 2.3 All 4xx statuses treated as password validation failure, masking different error types

**File:** `/Users/mobal/src/p4493/auth-service/app/clients/user_service_client.py` | **Line:** 46

A 401 (invalid/expired JWT token) or 403 (forbidden) from the user-service is interpreted the same as a wrong-password response. The caller cannot distinguish between these scenarios.

**Fix:** Check for specific expected status codes (400 or 422) and let unexpected 4xx codes propagate.

---

### 2.5 Inconsistent error handling between get_user_by_email and get_user_by_id

**File:** `/Users/mobal/src/p4493/auth-service/app/clients/user_service_client.py` | **Lines:** 20-24 vs 66-72

`get_user_by_email` silently re-raises non-404 errors without logging; `get_user_by_id` logs them at ERROR level. This inconsistency makes debugging harder.

**Fix:** Standardize: log non-404 HTTP errors at ERROR level in both methods.

---

### 2.9 Cached service token can become stale

**File:** `/Users/mobal/src/p4493/auth-service/app/services/auth_service.py` | **Lines:** 193-208

In-memory caching of the service token persists its full lifetime. If the downstream user service revokes this token, the cache still returns the now-invalid token.

**Fix:** Use a shorter cache TTL (e.g., a fraction of the token lifetime) or implement cache-busting.

---

### 2.10 Logging the entire JWTToken object may leak sensitive token data

**File:** `/Users/mobal/src/p4493/auth-service/app/services/auth_service.py` | **Lines:** 185-189

The full `jwt_token` Pydantic object is included in the logger's `extra` dict. Token claims like `sub` and `scope` are persisted to centralized log storage.

**Fix:** Only log specific non-sensitive fields. Remove the full `jwt_token` from `extra`.

---

### 2.11 SSM parameter names resolved from env vars at call time, not validated at startup

**File:** `/Users/mobal/src/p4493/auth-service/app/settings.py` | **Lines:** 26-48

No validation that SSM parameter name environment variables are set at construction time. The error surfaces at first property access with an unhelpful AWS SDK error.

**Fix:** Add a `@model_validator(mode='after')` that checks all required env vars exist at construction time.

---

### 2.12 No error handling around SSM parameter store calls

**File:** `/Users/mobal/src/p4493/auth-service/app/settings.py` | **Lines:** 26-48

All three `parameters.get_parameter()` calls are unprotected. If SSM is unreachable, the parameter path doesn't exist, or IAM permissions are missing, the exception propagates unhandled with no logging context about which parameter failed.

**Fix:** Wrap each call in try/except that logs the specific parameter name and re-raises with a descriptive message.

---

### 2.13 Type mismatch: `os.environ.get()` returns `Optional[str]` but `get_parameter` expects `str`

**File:** `/Users/mobal/src/p4493/auth-service/app/settings.py` | **Lines:** 30-31, 38-39

`os.environ.get(key)` returns `str | None`. The `parameters.get_parameter()` function expects `str`. The None case is never handled.

**Fix:** Extract into local variable with explicit type narrowing check before passing to `get_parameter`.

---

### 2.14 Duplicate ExceptionMiddleware with stale handler snapshot

**File:** `/Users/mobal/src/p4493/auth-service/app/api_handler.py` | **Line:** 24

`ExceptionMiddleware` is explicitly added with `handlers=app.exception_handlers`, capturing only the default FastAPI handlers. Custom handlers defined afterward via `@app.exception_handler` decorators are invisible to this middleware. This creates two `ExceptionMiddleware` layers with different handler sets.

**Fix:** Remove the explicit `add_middleware(ExceptionMiddleware, ...)` call entirely. FastAPI already installs this middleware internally.

---

### 2.15 Catch-all handler double-logs every unhandled exception

**File:** `/Users/mobal/src/p4493/auth-service/app/api_handler.py` | **Lines:** 54-71

Both `logger.error(...)` and `logger.exception(...)` log the same exception at ERROR level with overlapping context, doubling log volume.

**Fix:** Remove the `logger.error` call; keep only `logger.exception` which includes the traceback.

---

### 2.16 HTTPException logged at exception level with full traceback for expected client errors

**File:** `/Users/mobal/src/p4493/auth-service/app/api_handler.py` | **Line:** 96

`HTTPException` (404, 409, 401) are expected, client-driven errors. Logging these with full tracebacks creates significant log noise and false alarms.

**Fix:** Use `logger.warning(error.detail)` instead of `logger.exception(error)`.

---

### 2.17 RequestValidationError logged at exception level with full traceback

**File:** `/Users/mobal/src/p4493/auth-service/app/api_handler.py` | **Line:** 114

Client validation errors should not produce server-level ERROR logs with tracebacks.

**Fix:** Use `logger.warning` at INFO or WARNING level without traceback.

---

### 2.18 Missing cross-field validation for grant_type-specific required fields

**File:** `/Users/mobal/src/p4493/auth-service/app/models/request/oauth_token.py` | **Lines:** 8-16

No model_validator enforces that when `grant_type='password'`, `username` and `password` must be present; when `grant_type='refresh_token'`, `refresh_token` must be present; etc.

**Fix:** Add a `model_validator(mode='after')` that checks grant_type and raises ValueError if corresponding mandatory fields are None.

---

### 2.19 `redirect_uri` unvalidated in OAuth authorize request model, enabling open redirect attacks

**File:** `/Users/mobal/src/p4493/auth-service/app/models/request/oauth_authorize.py` | **Line:** 7

`redirect_uri` is a bare `str` with no URL validation. An attacker could supply values like `https://evil.com/callback` or `javascript:alert(1)`.

**Fix:** Add a Pydantic field_validator that parses the URI and verifies it has an `https` scheme and a valid host. Consider `pydantic.HttpUrl`.

---

### 2.20 Grant type and token endpoint fields accept empty or arbitrary strings

**File:** `/Users/mobal/src/p4493/auth-service/app/models/request/oauth_token.py` | **Line:** 9

`grant_type` is a bare `str` with no constraints. Empty strings pass validation.

**Fix:** Add `min_length=1` and preferably constrain to known OAuth 2.0 grant types.

---

### 2.21 Password and refresh_token are plain strings, may leak in serialization or logs

**File:** `/Users/mobal/src/p4493/auth-service/app/models/request/oauth_token.py` | **Lines:** 8-16

`password` and `refresh_token` are plain `str` values. `model_dump()` or `str(model)` exposes these in plaintext.

**Fix:** Use `pydantic.SecretStr` for `password` and `refresh_token` fields.

---

### 2.22 Secret stored as plain str instead of SecretStr on ServiceCredential

**File:** `/Users/mobal/src/p4493/auth-service/app/models/service.py` | **Line:** 7

The `secret` field is exposed in `repr()`, `str()`, JSON serialization, and error tracebacks.

**Fix:** Use `pydantic.SecretStr` and access via `.get_secret_value()` when needed.

---

### 2.23 No exception handling for any DynamoDB operations in authorization_code_repository

**File:** `/Users/mobal/src/p4493/auth-service/app/repositories/authorization_code_repository.py` | **Lines:** 31, 53, 58

No try/except on any DynamoDB calls. Throttling, unavailability, or ClientError all propagate unhandled.

**Fix:** Wrap each call in try/except catching `botocore.exceptions.ClientError` with retry for throttling errors.

---

### 2.24 create_service uses put_item without a condition, silently overwriting existing records

**File:** `/Users/mobal/src/p4493/auth-service/app/repositories/service_repository.py` | **Line:** 18

`create_service` unconditionally replaces the entire item if the partition key already exists.

**Fix:** Add `ConditionExpression=Attr('id').not_exists()` to prevent accidental overwrites.

---

### 2.25 Eventually consistent reads can return stale data after writes

**File:** `/Users/mobal/src/p4493/auth-service/app/repositories/service_repository.py` | **Lines:** 23, 34

After `create_service`, a follow-up `get_by_id` or `get_by_name` may not see the new item for up to a second.

**Fix:** Use `ConsistentRead=True` on get_item. Document the limitation for GSI queries.

---

### 2.26 No DynamoDB exception handling in service_repository

**File:** `/Users/mobal/src/p4493/auth-service/app/repositories/service_repository.py` | **Lines:** 10-14, 18, 23-25, 33-38

Every DynamoDB API call can raise multiple exceptions (ResourceNotFoundException, ProvisionedThroughputExceededException, InternalServerError, etc.). None are caught.

**Fix:** Wrap calls in try/except catching `botocore.exceptions.ClientError`, log context, translate to domain exceptions.

---

### 2.27 Module-level Logger causes cross-request correlation ID pollution in concurrent environments

**File:** `/Users/mobal/src/p4493/auth-service/app/middlewares.py` | **Lines:** 15, 39 (already noted as High)

---

### 2.28 ContextVar without default causes LookupError outside request context

**File:** `/Users/mobal/src/p4493/auth-service/app/middlewares.py` | **Line:** 14

`ContextVar(X_CORRELATION_ID)` with no default raises `LookupError` if `get()` is called outside an HTTP request context.

**Fix:** Provide a default: `ContextVar(X_CORRELATION_ID, default="")`.

---

### 2.29 No exception handling in dispatch method of CorrelationIdMiddleware

**File:** `/Users/mobal/src/p4493/auth-service/app/middlewares.py` | **Lines:** 23-46

The entire `dispatch` method lacks try/except/finally. If an exception occurs, there is no opportunity to log context or clean up state.

**Fix:** Wrap the method body in try/except/finally.

---

### 2.30 Overly broad exception handler in _parse_authorization_header

**File:** `/Users/mobal/src/p4493/auth-service/app/routers/oauth/auth_router.py` | **Line:** 39

`except Exception: ` catches `MemoryError`, `KeyboardInterrupt`, and programming errors.

**Fix:** Catch only the specific exceptions: `except (ValueError, binascii.Error, UnicodeDecodeError)`.

---

### 2.32 No default for STAGE env var in table name fixtures

**File:** `/Users/mobal/src/p4493/auth-service/tests/conftest.py` | **Lines:** 241-242, 246-247, 256-257

If `STAGE` is not set, table names become `"None-services"`, `"None-tokens"`, etc.

**Fix:** Add default: `os.getenv('STAGE', 'test')`.

---

### 2.33 Monkeysystem SETENV with potentially None values

**File:** `/Users/mobal/src/p4493/auth-service/tests/conftest.py` | **Lines:** 17-52

`monkeypatch.setenv("CLIENT_SECRET_SSM_PARAM_NAME", os.getenv("CLIENT_SECRET_SSM_PARAM_NAME"))` passes None if the env var is unset, causing a TypeError.

**Fix:** Use `os.getenv("...", "default_value")` with sensible defaults.

---

### 2.34 No edge-case or error-path tests for any service repository method

**File:** `/Users/mobal/src/p4493/auth-service/tests/unit/repository/test_service_repository.py` | **Lines:** 1-64

No tests for: creating with missing fields, get_by_id/get_by_name with empty/None arguments, duplicate IDs, empty scopes, very long values.

**Fix:** Add parametrized edge-case tests.

---

### 2.36 jwt_bearer fixture instantiates real JWTBearer wired to real infrastructure

**File:** `/Users/mobal/src/p4493/auth-service/tests/unit/conftest.py` | **Lines:** 14-15

Creates a real JWTBearer with a real TokenService and TokenRepository, which connects to a real (or mocked) DynamoDB table. Even tests about completely unrelated behavior break if the constructor chain changes.

**Fix:** Allow dependency injection so tests can create JWTBearer with a mocked TokenService.

---

### 2.37 Mock return value of get_by_id does not match actual return type

**File:** `/Users/mobal/src/p4493/auth-service/tests/unit/test_auth.py` | **Lines:** 177, 197

The mock returns `(jwt_token.model_dump(), refresh_token)` where the first element is a dict, not a JWTToken instance. The test passes only because the production code currently only checks truthiness.

**Fix:** Return `(jwt_token, refresh_token.token)` matching the real contract.

---

### 2.38 No test for expired JWT token (ExpiredSignatureError path)

**File:** `/Users/mobal/src/p4493/auth-service/tests/unit/test_auth.py` | **Line:** 114

The `_validate_token` method explicitly catches `ExpiredSignatureError`, but this code path has zero test coverage.

**Fix:** Add a test creating a JWT with `exp` in the past and asserting 403 "Not authenticated".

---

### 2.39 No test for Pydantic ValidationError when decoded JWT payload has invalid/missing fields

**File:** `/Users/mobal/src/p4493/auth-service/tests/unit/test_auth.py` | **Lines:** 114, 180

The unhandled ValidationError path (not caught in the try/except) is never tested. A malformed token would propagate as a 500 error.

**Fix:** Either add a catch for ValidationError in _validate_token, or add a test documenting the expected error behavior.

---

### 2.42 No test for AWS Lambda context request ID path in correlation middleware

**File:** `/Users/mobal/src/p4493/auth-service/tests/integration/test_correlation_id_middleware.py` | **Lines:** 92-126

The middleware's AWS request ID fallback path (path 2 of 3) is entirely untested.

**Fix:** Add a test populating `request.scope['aws.context']` with a mock and asserting the response header equals that `aws_request_id`.

---

### ✅ Already Fixed Findings

---

### ~~2.1 No timeout configured on any HTTP request to the user service~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/clients/user_service_client.py` | **Lines:** 14, 38, 61~~

~~All three httpx calls omit the `timeout` parameter. If the user-service hangs, requests can stall for an unbounded period.~~

~~**Fix:** Add `timeout=httpx.Timeout(10.0)` to every httpx call.~~

---

### ~~2.2 No httpx.Client reuse, preventing connection pooling~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/clients/user_service_client.py` | **Lines:** 10-75~~

~~Every method call creates a new implicit httpx transport, causing a new TCP connection and TLS handshake per request.~~

~~**Fix:** Add an `__init__` method that accepts an optional `httpx.Client`, defaulting to `httpx.Client(timeout=...)`. Store as `self._client`.~~

---

### ~~2.4 httpx.RequestError (connection/timeout failures) never caught in any method~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/clients/user_service_client.py` | **Lines:** 14, 19, 38, 44, 61, 65~~

~~All three methods only catch `httpx.HTTPStatusError`. Connection refused, DNS failures, and timeout errors propagate as raw 500 errors with no logging.~~

~~**Fix:** Add `except httpx.RequestError` in each method that logs the failure and returns a sentinel or raises a custom exception.~~

---

### ~~2.6 Success log emitted before JSON parsing, producing misleading traces on failure~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/clients/user_service_client.py` | **Lines:** 74-75~~

~~"User fetched" is logged before `response.json()` is called. If JSON parsing fails, the log shows a spurious success message.~~

~~**Fix:** Move the info log after the successful JSON parse.~~

---

### ~~2.7 Redirect URI comparison without normalization~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/services/auth_service.py` | **Lines:** 440-447~~

~~Direct string equality for redirect URIs. Semantically equivalent URIs (differing in trailing slashes, default port omission, percent-encoding) would be treated as mismatches.~~

~~**Fix:** Normalize both URIs: parse with `urlparse`, lowercase scheme and host, strip default ports, sort query parameters, normalize path.~~

---

### ~~2.8 PKCE defaults not compliant with RFC 7636~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/services/auth_service.py` | **Lines:** 79-104~~

~~When `code_challenge_method` is `None` (omitted), the code raises `OAuthException("invalid_request")` instead of defaulting to `"plain"` per RFC 7636.~~

~~**Fix:** Treat `None` as `"plain"` per the RFC.~~

---

### ~~2.31 Password hasher uses default (slow) Argon2 parameters in test fixtures~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/tests/conftest.py` | **Lines:** 220-226, 132-133~~

~~Each hash takes ~50-150ms on modern hardware. Over dozens of tests, this adds seconds to test runtime.~~

~~**Fix:** Use minimal parameters: `PasswordHasher(time_cost=1, memory_cost=64, parallelism=1)`. Pre-compute hash at module level.~~

---

### ~~2.35 Create token test and fixture create token test have tautological assertions~~ ✅ Already Fixed

~~**Files:** `/Users/mobal/src/p4493/auth-service/tests/unit/conftest.py` (lines 24-32) and `/Users/mobal/src/p4493/auth-service/tests/unit/service/test_token_service.py` (lines 13-26)~~

~~The token fixture duplicates `TokenService.create()` production logic. Any bug in the production code is replicated in the fixture, causing the test to pass when it should fail.~~

~~**Fix:** Use `ANY` matchers for time-dependent fields and assert only stable fields (jti, jwt_token, refresh_token, ttl). Or freeze time to make timestamps deterministic.~~

---

### ~~2.40 Token refresh test does not assert token issuance~~ ✅ Already Fixed (same as 1.27)

~~**File:** `/Users/mobal/src/p4493/auth-service/tests/integration/test_auth_api.py` | **Lines:** 195-207~~

~~Only checks status 200 and cache headers. Never validates the response body.~~

~~**Fix:** Assert that the response contains access_token and refresh_token.~~

---

### ~~2.41 Correlation ID tests do not verify preservation~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/tests/integration/test_correlation_id_middleware.py` | **Lines:** 61-90~~

~~`test_correlation_id_from_request_header_is_preserved` sends a specific UUID in the request but never asserts the response contains the same value.~~

~~**Fix:** Add `assert response.headers[X_CORRELATION_ID] == correlation_id_value`.~~

---

## 3. Low / Info

### 🔴 Still Actionable Findings

---

### 3.1 Inconsistent return types between get_by_id and get_by_refresh_token

**File:** `/Users/mobal/src/p4493/auth-service/app/services/token_service.py` | **Lines:** 46, 50

`get_by_id` returns `tuple[JWTToken, str] | None`; `get_by_refresh_token` returns `raw dict[str, Any] | None`. Callers must use different access patterns depending on which lookup method they use.

**Fix:** Make both return the same typed tuple or named structure.

---

### 3.2 Misleading parameter name `code_id` in delete_by_id

**File:** `/Users/mobal/src/p4493/auth-service/app/repositories/authorization_code_repository.py` | **Line:** 52

Parameter name suggests the authorization code value, but it expects the internal UUID primary key.

**Fix:** Rename to `item_id` or `record_id` with a clarifying docstring.

---

### 3.3 Unnecessary round-trip conversion for expire_at

**File:** `/Users/mobal/src/p4493/auth-service/app/repositories/authorization_code_repository.py` | **Lines:** 29, 42

`pendulum.from_timestamp(ttl).to_iso8601_string()` where `ttl` is already computed from `now`. Converts to Unix timestamp (losing precision) then reconstructs.

**Fix:** Replace with `now.add(minutes=10).to_iso8601_string()`.

---

### 3.4 Timezone inconsistency in authorization code repository

**File:** `/Users/mobal/src/p4493/auth-service/app/repositories/authorization_code_repository.py` | **Lines:** 28, 41-42

`created_at` uses `pendulum.now()` (local timezone); `expire_at` computed from `pendulum.from_timestamp(ttl)` (UTC). Mixed timezones.

**Fix:** Use `pendulum.now('UTC')` consistently.

---

### 3.5 F-strings in logger calls cause eager evaluation

**Files:** Various

Multiple logger calls use f-string formatting instead of lazy `%s` formatting (e.g., `app/__init__.py:19`, `app/repositories/authorization_code_repository.py:47-48`, `app/security/authorization.py:16`).

**Fix:** Replace `logger.debug(f"...")` with `logger.debug("...%s", var)`.

---

### 3.6 Missing return type annotations

**Files:** Various

- `app/__init__.py:14` - `load_env_files` missing `-> None`
- `app/api_handler.py:127-130` - `health_check` missing return type
- `app/services/auth_service.py:39` - `__init__` missing `-> None`
- `app/services/token_service.py:19,39` - `create` and `delete_by_id` missing type annotations
- `app/security/authorization.py:9-41` - Inner functions missing type annotations

**Fix:** Add appropriate return type annotations.

---

### 3.7 Unused module-level global dict in middlewares.py

**File:** `/Users/mobal/src/p4493/auth-service/app/middlewares.py` | **Line:** 13

`clients: dict[str, Any] = {}` is defined but never read, written, or referenced anywhere.

**Fix:** Remove the dead code.

---

### 3.8 Dead default in request.scope.get()

**File:** `/Users/mobal/src/p4493/auth-service/app/middlewares.py` | **Line:** 33

`request.scope.get("aws.context", {})` passes an empty dict default that is never used because the guard ensures the key exists.

**Fix:** Simplify to `request.scope["aws.context"]`.

---

### 3.9 No docstrings on models explaining OAuth2 value contracts

**Files:** Various model files

Models for `GrantType`, `AuthorizationCode`, `OAuthTokenRequest`, and others lack docstrings explaining field semantics, RFC references, and expected value constraints.

**Fix:** Add class-level and field-level docstrings, especially for OAuth2 wire-format values.

---

### 3.14 Unused fixture `jwt_auth` in test_auth.py

**File:** `/Users/mobal/src/p4493/auth-service/tests/unit/test_auth.py` | **Lines:** 25-26

Class-level fixture defined but never referenced by any test method.

**Fix:** Remove the dead fixture.

---

### 3.15 Redundant `import pytest as pytest`

**File:** `/Users/mobal/src/p4493/auth-service/tests/unit/conftest.py` | **Line:** 4

No-op alias that may confuse readers or trigger linters.

**Fix:** Simplify to `import pytest`.

---

### 3.17 Exception type assertion uses `__name__` comparison instead of isinstance or type comparison

**Files:** Multiple test files

`excinfo.typename == ExceptionClass.__name__` converts to string for comparison. More idiomatic is `excinfo.type == ExceptionClass`.

**Fix:** Replace with direct type comparison.

---

### 3.18 No tests for DynamoDB error conditions in any repository

**Files:** All repository test files

No tests verify behavior under `ProvisionedThroughputExceededException`, `ConditionalCheckFailedException`, or network errors.

**Fix:** Patch table resource to raise specific exceptions and verify the repository handles them gracefully.

---

### 3.19 No fixtures for expired, malformed, or edge-case JWT tokens

**File:** `/Users/mobal/src/p4493/auth-service/tests/conftest.py` | **Lines:** 192-203

Only valid tokens are provided. No fixtures for expired tokens, tokens with no scope, empty sub, or malformed fields.

**Fix:** Add `expired_jwt_token`, `jwt_token_no_scope`, `jwt_token_empty_sub`, and a parametrized factory.

---

### ✅ Already Fixed Findings

---

### ~~3.10 `aud` field only supports single string, not array of audiences~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/models/jwt.py` | **Line:** 10~~

~~Per RFC 7519, `aud` can be a single string or an array of strings.~~

~~**Fix:** Change type to `str | list[str] | None`.~~

---

### ~~3.11 `expires_in` accepts zero and negative values~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/models/response/token.py` | **Line:** 7~~

~~RFC 6749 recommends a positive integer. Code accepts 0 and negative values.~~

~~**Fix:** Add `Field(gt=0)`.~~

---

### ~~3.12 `token_type` is a plain str with no restriction~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/models/response/token.py` | **Line:** 6~~

~~Accepts any arbitrary string but downstream code almost certainly expects "Bearer".~~

~~**Fix:** Use `Literal["Bearer"]` or add a case-normalizing validator.~~

---

### ~~3.13 `service_token_lifetime` default of 30 has ambiguous units~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/settings.py` | **Line:** 23~~

~~No comment or unit in the name. Compare with `refresh_token_lifetime` which has `# 30 days` and a value of 2592000.~~

~~**Fix:** Rename to `service_token_lifetime_seconds` or add a comment.~~

---

### ~~3.16 Inconsistent naming: client_id vs client_name~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/routers/oauth/auth_router.py` | **Lines:** 47, 120~~

~~In `_parse_authorization_header` the extracted value is named `client_id`, but at the call site in `_handle_client_credentials_grant` it is unpacked as `client_name`.~~

~~**Fix:** Use consistent naming across both functions.~~

---

### ~~3.20 Unconventional `__import__` usage instead of standard import~~ ✅ Already Fixed

~~**File:** `/Users/mobal/src/p4493/auth-service/app/repositories/authorization_code_repository.py` | **Line:** 15~~

~~`__import__('boto3')` circumvents static analysis tools and type checkers.~~

~~**Fix:** Use standard `import boto3` at module level.~~

---

## Summary

### Overall Health

The codebase has **strong testing infrastructure** (moto, pytest-httpx, proper fixtures) and **good architectural separation** (repositories, services, routers, models). However, there are significant issues:

- **Security:** Several OAuth2 RFC violations ~~(missing headers, token replay, open redirect potential)~~, credential leakage vectors, and overly permissive CORS/scoping logic.
- **Concurrency:** ~~At least two critical race conditions (JWTBearer state, refresh token reuse) that will surface under load.~~ Remaining TOCTOU windows in authorization code and refresh token flows are bounded by DynamoDB conditional operations but should be tightened.
- **Test Quality:** ~20% of tests are false positives (pass without exercising the intended behavior) or have weak assertions. Tests use real infrastructure where mocks would be more appropriate, creating fragile interdependencies.
- **Error Handling:** DynamoDB operations lack any exception handling. SSM calls lack caching and error handling. ~~HTTP client calls lack timeout configuration and connection error handling.~~

### Updated Top Things to Fix

Based on current codebase validation:

#### ✅ Recently Fixed (Easy / High)

1. ~~**CORS allowing all origins**~~ (`app/api_handler.py:30`) — ✅ **Fixed**. Removed `["*"]` fallback.
2. ~~**`response_type` error message**~~ (`app/routers/oauth/auth_router.py:248`) — ✅ **Fixed**. Added `ERROR_MESSAGE_UNSUPPORTED_RESPONSE_TYPE` and updated test assertion.
3. ~~**Env file loading order**~~ (`app/__init__.py:13`) — ✅ **Fixed**. Changed `override=False` to `override=True` so `.env.prod` takes highest priority.
4. ~~**Logger initialized before env files**~~ (`app/__init__.py:10`) — ✅ **Fixed**. Moved `Logger()` after `load_env_files()`.
5. ~~**ErrorResponse timestamp at class time**~~ (`app/models/response/error.py:10`) — ✅ **Fixed**. Changed to `Field(default_factory=...)`.
6. ~~**Incomplete PyJWT exception coverage**~~ (`app/jwt_bearer.py:129-133`) — ✅ **Fixed**. Added `PyJWTError` catch-all fallback.
7. ~~**Test false positives: no return assertions**~~ (`tests/unit/service/test_token_service.py`) — ✅ **Already fixed**. Tests capture and assert return values.
8. ~~**Test false positive: no body assertions**~~ (`tests/integration/test_auth_api.py:195-207`) — ✅ **Already fixed**. Test asserts `access_token` / `refresh_token`.

#### ⏳ Still Needs Fixing

1. **Make `require_scope` decorator async-safe** (`app/security/authorization.py:45-53`). The synchronous wrapper silently breaks async route handlers.
2. **Remove query-parameter token fallback** (`app/jwt_bearer.py:42`). Bearer tokens in URLs leak via web server logs, proxies, CDNs, browser history, and the `Referer` header.
