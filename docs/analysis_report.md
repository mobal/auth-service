# Test Analysis Report - Auth Service

> **Actualized:** 2026-07-19 — test gaps verified against current codebase.

This document outlines the analysis of the test suite for the `auth-service` component, specifically focusing on missing edge cases and potential improvements in implementation quality within the testing layer.

## 1. Missing Edge Cases

### A. Service Token Buffer Logic (`_issue_service_token`)
The internal service token management currently uses a safety buffer to decide when to refresh:
> `safety_buffer = max(settings.service_token_lifetime_seconds // 5, 60)`

**Gaps:** 
- No test explores the "edge" of this calculation (e.g., exactly at the threshold).
- There are no tests for scenarios where a token is technically valid but falls within the `safety_buffer` range, ensuring it's correctly refreshed before expiring.

### B. Scopes Parsing Robustness (`_derive_scope`)
The `_derive_scope` method handles space-separated strings: 
`requested = set(requested_score.split())`

**Gaps:**
- No tests for "malformed" scope strings (e.g., multiple spaces between keywords, trailing/leading whitespaces, or empty strings).
- Testing of edge cases where the scope string is valid grammatically but logically unsupported by the `ROLE_SCOPE_MAP`.

### C. PKCE Method Variety (`_get_pkce_challenge`)
The method explicitly handles "S256" and "plain".

**Gaps:** 
- While it handles an unknown type, there are no tests for common but unintended types (e.g., "RS256") to ensure the custom `OAuthException` is returned correctly with the expected status codes.

### D. Client Data Validation
The `client_credentials` flow relies on a pre-registered client in `service_repository`.

**Gaps:**
- No test cases for missing fields (e.g., an empty name or special characters in the secret) at the entry point to ensure inputs are validated before reaching the internal logic.

## 2. Test Implementation Issues

### A. Hardcoded Values vs. Configuration
In `tests/unit/service/test_auth_service.py`:
- **Issue**: The test for successfully refreshing tokens uses a hardcoded integer (`3600`) to check token duration.
- **Impact**: This makes the test fragile. If `settings.jwt_token_lifetime` is updated in the configuration, the test will fail even if the logic remains correct. 
- **Fix**: Assert against the configuration variable directly.

### B. Non-Specific Error Validation
Several tests for "failed" states (e.g., `test_fail_to_login_due_to_invalid_credentials`) only assert that an exception was raised and check a single generic field like `.detail`.
- **Issue**: This doesn't verify if the *correct* internal error code or missing fields are correctly handled by the underlying service.

### C. Mock Over-Broadness (Potential)
In some unit tests, `mock.patch` is used on high-level objects where a more specific mock of the contract would be safer. 
- **Recommendation**: Ensure that all mocked return values reflect the data structures exactly as they are produced by the underlying models to catch schema regressions early.

## Summary Table of Findings

| Category | Location | Issue Description | Priority | Status (2026-07-19) |
| :--- | :--- | :--- | :--- | :--- |
| Missing Edge Case | `auth_service.py:149` | Service token buffer boundary testing is missing. | Medium | Still open |
| Missing Edge Case | `auth_service.py:68` | Weak validation for malformed scope strings. | Low | Still open |
| Bad Implementation | `test_auth_service.py` | Use of hardcoded integers instead of config values. | Medium | ⚠️ Verify — test may hardcode `3600` vs `settings.jwt_token_lifetime` |
| Robustness | `auth_service.py:90` | Limited variation in PKCE method testing. | Low | Still open |
| Dependency | 9 test files | All test files still import `pendulum`. Tests need updating alongside the pendulum→stdlib migration. | Medium | Tracked in [`REPLACE_PENDULUM_PLAN.md`](REPLACE_PENDULUM_PLAN.md) |
| Coverage | `auth_service.py:login()` | No test for the timing side-channel (user-not-found early return). A test simulating the response-time delta between known vs unknown users would validate the timing-attack resistance. | Medium | New — related to [`audit_report.md`](audit_report.md) critical finding #1 |
| Coverage | `token_repository.py:delete_by_id()` | No test for concurrent token consumption (two requests racing on the same JTI). The plain `delete_item` has no ConditionExpression. | High | New — related to [`audit_report.md`](audit_report.md) critical finding #2 |

## Updates Since Original Report

1. **Service token buffer** — `_issue_service_token` still uses in-memory caching, and the safety buffer boundary (`max(lifetime // 5, 60)`) remains untested at the edge thresholds.
2. **Scope parsing** — `_derive_scope` still uses bare `requested_scope.split()` without stripping or filtering empty tokens from multiple consecutive spaces.
3. **Hardcoded values** — The original finding about hardcoded `3600` in `test_auth_service.py` needs re-verification against the current test file.
4. **PKCE testing** — Only `S256` and `plain` methods are covered; no test for an unsupported method (e.g., `RS256`) verifying the `OAuthException` is raised with the correct status code.
5. **Pendulum** — All 9 test files still import pendulum. These will need updating alongside the app code during the migration.
