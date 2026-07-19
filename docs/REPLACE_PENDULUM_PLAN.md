# Migration Plan: Replace Pendulum with Standard Library

## 1. Technical Debt Overview
**Status:** Medium Complexity
**Risk:** Moderate (Mainly related to timezone behavior and leap year/DST edge cases)
**Goal:** Remove external dependency `pendulum` and replace with Python's built-in `datetime`, `timedelta`, and `zoneinfo`.

## 2. Key Replacement Logic Reference

| Feature | Pendulum | Standard Library |
| :--- | :--- | :--- |
| **Import** | `import pendulum` | `from datetime import datetime, timedelta, timezone; from zoneinfo import ZoneInfo` |
| **Now (UTC)** | `pendulum.now(tz='UTC')` | `datetime.now(tz=timezone.utc)` |
| **Addition** | `dt.add(minutes=30)` | `dt + timedelta(minutes=30)` |
| **Parse** | `pendulum.parse(str)` | `datetime.fromisoformat(str.replace('Z', '+00:00'))` |

---

## 3. Detailed Refactoring Map

Below are the specific files requiring modification and the corresponding refactor proposals.

### Core Application & Services
**File:** `app/__init__.py`
- **Original:** `import pendulum`
- **Proposal:** Replace with standard library imports to clean up the global namespace.
- **Note:** Standardize on `datetime` for any global utility functions defined here.

**File:** `app/services/auth_service.py`
- **Original:** `import pendulum` (and usages of `.now()`, `.add()`)
- **Proposal:** 
  - Use `datetime.now(tz=timezone.utc)` for time checks.
  - Use `timedelta(...)` for expiration calculations.
- **Note:** Critical file; ensure interval logic remains consistent.

**File:** `app/services/token_service.py`
- **Original:** `import pendulum`
- **Proposal:** Replace with standard library imports. 
- **Note:** Ensure token validation windows are calculated using `timedelta`.

### Repositories & Data Access
**File:** `app/repositories/authorization_code_repository.py`
- **Original:** `import pendulum` (often used for parsing DB timestamps)
- **Proposal:** Replace with `datetime.fromisoformat()`.
- **Note:** Ensure the string cleaning logic handles the 'Z' suffix if coming from a database or external source.

### Test Suite
The following files utilize `pendulum` primarily for mocking time, generating dates in tests, or assertion matching.

**Files:**
- `tests/conftest.py`
- `tests/integration/conftest.py`
- `tests/integration/test_auth_api.py`
- `tests/unit/conftest.py`
- `tests/unit/repository/test_authorization_code_repository.py`
- `tests/unit/repository/test_service_repository.py`
- `tests/unit/repository/test_token_repository.py`
- `tests/unit/service/test_auth_service.py`
- `tests/unit/service/test_token_service.py`

**Refactor Proposal for all Test files:**
1. Replace `import pendulum` with standard library equivalents.
2. For "frozen" time tests, if currently using a third-party tool (like `freezegun`) that integrates with Pendulum, ensure it is updated to handle `datetime`.
3. Ensure consistency in sample data construction (e.g., creating dummy expiration dates).

---

## 4. Execution Checklist
- [ ] Replace all `import pendulum` statements.
- [ ] Update duration/math logic using `timedelta`.
- [ ] Replace date parsing with `datetime.fromisoformat`.
- [ ] Run specialized tests to verify auth and token expiry windows.
- [ ] Remove `pendulum` from `requirements.txt`/`pyproject.toml`.
