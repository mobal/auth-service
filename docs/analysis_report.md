# Test Analysis Report - Auth Service

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

| Category | Location | Issue Description | Priority |
| :--- | :--- | :--- | :--- |
| Missing Edge Case | `auth_service.py:149` | Service token buffer boundary testing is missing. | Medium |
| Missing Edge Case | `auth_service.py:68` | Weak validation for malformed scope strings. | Low |
| Bad Implementation | `test_auth_service.py` | Use of hardcoded integers instead of config values. | Medium |
| Robustness | `auth_service.py:90` | Limited variation in PKCE method testing. | Low |
