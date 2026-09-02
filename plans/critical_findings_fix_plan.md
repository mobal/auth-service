# Critical Findings Fix Plan

This document outlines the critical findings that need to be addressed as a priority in the auth-service codebase, along with detailed recommendations for fixing each issue.

## 1. TOCTOU Race Condition in Authorization Code Consumption (1.5)

**File:** `app/repositories/authorization_code_repository.py` | **Lines:** 56-82

### Problem
Two concurrent requests can both call `get_by_code()` with the same code, both receive the `AuthorizationCode`, and both proceed to use it before either calls `delete_by_id()`. The DynamoDB delete is unconditional and not conditional on the code still existing.

### Solution
Use a conditional delete or a DynamoDB transaction. Alternatively, store a `consumed` flag and use a conditional update to atomically claim the code.

### Implementation Plan
1. Add a `consumed: bool = False` field to the `AuthorizationCode` model
2. Add a `consumed_at: Optional[datetime]` field to track when it was consumed
3. Modify the consumption logic to use a conditional update that sets `consumed=True` only if it's currently `False`
4. Update the repository's `consume_by_code` method to use this atomic operation

### Code Changes Required
- `app/models/authorization_code.py` - Add fields
- `app/repositories/authorization_code_repository.py` - Update consumption method
- Possibly `app/services/auth_service.py` - Update service layer to handle new consumption pattern

## 2. Refresh Token Reuse Race Condition (1.6)

**File:** `app/services/auth_service.py` | **Lines:** 269-291

### Problem
The `refresh` method has no atomicity for the read-delete-create cycle. Two concurrent requests with the same refresh token can both pass the TTL check before either reaches the delete, producing two independent valid token pairs from the same original refresh token.

### Solution
Use a conditional delete (DynamoDB ConditionExpression) that atomically deletes the old record and only proceeds if it still exists. The second concurrent request's delete should fail, preventing duplicate token generation.

### Implementation Plan
1. Modify the token repository's `delete_by_refresh_token` method to accept a condition
2. Update the auth service's `refresh` method to use conditional deletion
3. Handle the case where deletion fails due to concurrent access

### Code Changes Required
- `app/repositories/token_repository.py` - Add conditional delete support
- `app/services/auth_service.py` - Update refresh method to use conditional deletion

## 3. SSM Caching Reliability (1.15)

**File:** `app/settings.py` | **Lines:** 26-48

### Problem
`@computed_field @property` in Pydantic v2 is evaluated on every attribute access. Every access to `.client_secret`, `.jwt_secret`, or `.user_service_base_url` makes a live SSM API call. Under load this causes excessive latency (~100-500ms each), SSM throttling, and AWS cost.

### Solution
Use `@cached_property` from `functools` or use the `max_age` parameter of `parameters.get_parameter(..., max_age=300)`.

### Implementation Plan
1. Replace `@computed_field @property` with `@cached_property` from functools
2. Add appropriate cache invalidation mechanisms if needed
3. Consider adding cache timeout configuration

### Code Changes Required
- `app/settings.py` - Update property decorators and caching mechanism

## 4. Decorator Not Async-Safe (1.18)

**File:** `app/security/authorization.py` | **Lines:** 19-37

### Problem
The wrapper is synchronous. If the decorated function is an async coroutine (normal for FastAPI), `func(...)` returns a coroutine object without executing it.

### Solution
Make the wrapper detect whether `func` is async: use `inspect.iscoroutinefunction(func)` and define an async wrapper accordingly.

### Implementation Plan
1. Import `inspect` module
2. Check if the decorated function is a coroutine function
3. Create separate wrapper logic for async and sync functions
4. Return an async wrapper when the decorated function is async

### Code Changes Required
- `app/security/authorization.py` - Update the `require_scope` decorator to handle both sync and async functions

## 5. No Timezone Validation (1.24)

**File:** `app/__init__.py` | **Line:** 27

### Problem
`settings.default_timezone` could be None, empty, or an invalid IANA timezone string. `pendulum.timezone()` would raise an unknown timezone exception crashing at import time.

### Solution
Validate the timezone string, catching `pendulum.UnknownTimeZoneError`.

### Implementation Plan
1. Wrap the timezone initialization in a try/except block
2. Catch `pendulum.UnknownTimeZoneError` specifically
3. Provide a fallback timezone (UTC) or raise a more descriptive error

### Code Changes Required
- `app/__init__.py` - Add timezone validation with proper error handling

## 6. Test False Positives: Refresh Token Type (1.25)

**File:** `tests/unit/service/test_auth_service.py` | **Lines:** 155-189, 191-206, 239-272

### Problem
Three refresh tests pass a `RefreshToken` object to `auth_service.refresh()` which expects a `str`. The mock on `get_by_refresh_token` ignores the type mismatch, so tests pass but prove nothing about real behavior.

### Solution
Pass `refresh_token.token` (a string) instead of the `RefreshToken` object.

### Implementation Plan
1. Update test cases to pass the token string value instead of the object
2. Ensure mocks are properly configured to handle the correct parameter types

### Code Changes Required
- `tests/unit/service/test_auth_service.py` - Update test cases to pass string values

## 7. Nested Moto Mock Contexts (1.29)

**File:** `tests/conftest.py` | **Lines:** 17-52, 67-74

### Problem
The `setup` fixture wraps in `mock_aws()` and the `dynamodb_resource` fixture opens a second nested `mock_aws()` context. Moto state is not reliably shared across nested contexts in all moto versions.

### Solution
Use a single `mock_aws()` context or use separate `@mock_ssm` / `@mock_dynamodb` decorators without nesting.

### Implementation Plan
1. Restructure test fixtures to avoid nested mock contexts
2. Use specific mock decorators for each AWS service instead of broad `mock_aws()`
3. Ensure all tests properly share mock state

### Code Changes Required
- `tests/conftest.py` - Restructure fixtures to avoid nested mock contexts

## 8. Token Accepted via Query Parameter (1.30)

**File:** `app/jwt_bearer.py` | **Lines:** 40-42

### Problem
Falls back to `request.query_params.get('token')` when the Authorization header is missing. URLs containing bearer tokens are logged by web servers, load balancers, proxies, and CDNs; they appear in browser history and leak via the `Referer` header.

### Solution
Remove the query-parameter fallback or gate it behind an explicit configuration toggle that defaults to off.

### Implementation Plan
1. Add a configuration option to enable/disable query parameter token acceptance
2. Default this option to disabled
3. Update the JWT bearer logic to respect this configuration

### Code Changes Required
- `app/settings.py` - Add configuration option
- `app/jwt_bearer.py` - Update token extraction logic to respect configuration

## 9. Correlation ID Pollution (1.31)

**File:** `app/middlewares.py` | **Lines:** 15, 39

### Problem
`logger.set_correlation_id(correlation_id.get())` sets a mutable value on a singleton Logger shared across all requests. In a concurrent ASGI server, two requests can overwrite each other's correlation ID.

### Solution
Use `logger.append_keys(correlation_id=correlation_id.get())` with keys that force per-record lookup, or configure the Logger to read from the ContextVar at emission time.

### Implementation Plan
1. Update correlation ID middleware to use `append_keys` instead of `set_correlation_id`
2. Ensure each log record reads the current correlation ID value
3. Verify this works correctly in concurrent request scenarios

### Code Changes Required
- `app/middlewares.py` - Update correlation ID middleware implementation

## Priority Ranking for Implementation

1. **Security Issues** (Highest Priority)
   - Token accepted via query parameter (1.30)
   - Correlation ID pollution (1.31)

2. **Race Conditions** (High Priority)
   - TOCTOU race condition in auth code consumption (1.5)
   - Refresh token reuse race condition (1.6)

3. **Functionality Issues** (Medium Priority)
   - Decorator not async-safe (1.18)
   - No timezone validation (1.24)

4. **Infrastructure/Testing Issues** (Medium Priority)
   - SSM caching reliability (1.15)
   - Test false positives: refresh token type (1.25)
   - Nested moto mock contexts (1.29)

## Implementation Approach

1. Start with security fixes (query parameter token acceptance and correlation ID pollution)
2. Address race conditions with atomic operations in DynamoDB
3. Fix the async decorator issue to ensure proper async support
4. Add timezone validation to prevent startup crashes
5. Improve SSM caching to reduce AWS costs and latency
6. Fix test false positives to ensure test reliability
7. Restructure test fixtures to avoid nested mock contexts

Each fix should be implemented and tested independently to ensure no regressions are introduced.