# Fix Easy Difficulty High Findings — Plan

## Overview

Fix 8 "easy difficulty high" findings (1.3, 1.8, 1.12, 1.21, 1.22, 1.23, 1.26, 1.27) from the code review report. Each fix gets its own commit with a lowercase conventional commit message using the finding title.

---

## Current State Analysis

After examining the current codebase against the report:

| Finding | Status | Needs Fix? |
|---------|--------|------------|
| 1.3 — Incomplete PyJWT exception coverage | Not fixed | ✅ Yes |
| 1.8 — Wrong OAuth error message for response_type | Not fixed | ✅ Yes |
| 1.12 — CORS allows all origins | Not fixed | ✅ Yes |
| 1.21 — Env file loading order wrong | Not fixed | ✅ Yes |
| 1.22 — Logger initialized before env files | Not fixed | ✅ Yes |
| 1.23 — ErrorResponse timestamp at class time | Not fixed | ✅ Yes |
| 1.26 — No return assertions in get_by_id/get_by_refresh_token tests | **Already fixed** | ❌ No |
| 1.27 — No body assertions in refresh success test | **Already fixed** | ❌ No |

**1.26** and **1.27** already have proper assertions in the current code — the report's line numbers are outdated. These are listed as verification items rather than actual fixes.

---

## Detailed Fix Specifications

### Fix 1.3 — Incomplete PyJWT exception coverage

**File:** [`app/jwt_bearer.py`](app/jwt_bearer.py:118)

**Current code (lines 132-137):**
```python
        except DecodeError as err:
            logger.exception("Error occurred during token decoding: %s", err)
        except ExpiredSignatureError as err:
            logger.exception("Expired signature: %s", err)
        except ValidationError as err:
            logger.exception("Invalid JWT payload structure: %s", err)
```

**Fix:** Add `except PyJWTError` as a fallback after the existing handlers. Import `PyJWTError` from `jwt`.

**Changed import:**
```python
from jwt import DecodeError, ExpiredSignatureError, PyJWTError
```

**New except block (after `except ValidationError`):**
```python
        except PyJWTError as err:
            logger.exception("Unexpected JWT error: %s", err)
```

**Commit:** `fix: incomplete PyJWT exception coverage`

---

### Fix 1.8 — Wrong OAuth error message for response_type

**File:** [`app/routers/oauth/auth_router.py`](app/routers/oauth/auth_router.py:29)

**Current code (line 29):**
```python
ERROR_MESSAGE_UNSUPPORTED_GRANT_TYPE = "Unsupported grant type"
```

**Fix:** Add a new constant and use it on the authorize endpoint.

**Add after line 29:**
```python
ERROR_MESSAGE_UNSUPPORTED_RESPONSE_TYPE = "Unsupported response type"
```

**Change line 248** — the `raise OAuthException(...)` to use the new constant:
```python
        raise OAuthException(ERROR_MESSAGE_UNSUPPORTED_RESPONSE_TYPE)
```

**Also update test assertion in** [`tests/integration/test_auth_api.py`](tests/integration/test_auth_api.py:462):
```python
        assert response.json()["error"] == "Unsupported response type"
```

**Commit:** `fix: wrong OAuth error message for response type`

---

### Fix 1.12 — CORS allows all origins

**File:** [`app/api_handler.py`](app/api_handler.py:30)

**Current code:**
```python
    allow_origins=settings.allowed_origins or ["*"],
```

**Fix:** Remove the `["*"]` fallback so if `allowed_origins` is empty, CORS is restrictive.
```python
    allow_origins=settings.allowed_origins,
```

**Commit:** `fix: CORS allows all origins`

---

### Fix 1.21 — Env file loading order wrong

**File:** [`app/__init__.py`](app/__init__.py:13)

**Current code:**
```python
env_files = [".env", ".env.dev", ".env.local", ".env.prod"]
```

**Fix:** Reverse the list so `.env.prod` (most specific) is loaded last, overriding less specific files:
```python
env_files = [".env.prod", ".env.local", ".env.dev", ".env"]
```
With `override=False`, the first loaded file wins. By listing most-specific first, the env files take lowest-priority-first. Actually — the correct fix per the report is to reverse the order so the most specific `.env.prod` is loaded LAST. But `override=False` means first-loaded wins. So we need to reverse AND use `override=True` for later files, OR simply reorder so `.env` is last.

Let's reconsider: The issue is `.env` is loaded first with `override=False`, so its values win over `.env.prod`. 

The cleanest fix is: **reverse the list order** and change to **`override=True`**.

```python
env_files = [".env", ".env.dev", ".env.local", ".env.prod"]
# Change to:
env_files = [".env", ".env.dev", ".env.local", ".env.prod"]
# And change override=False to override=True on line 25
```

Wait, that's not right either. Let me think again.

Current behavior: `override=False` means the first value loaded is kept. So `.env` is loaded first, its values stick, and `.env.prod` values are ignored. This is WRONG — production should win.

Fix: Load `.env.prod` first (but since `override=False`, `.env` still wins if loaded later). OR: change `override=False` to `override=True` so later files override earlier ones, AND reverse the order so `.env` is first (lowest priority) and `.env.prod` is last (highest priority).

Actually, re-reading the report: "The list `['.env', '.env.dev', '.env.local', '.env.prod']` with `override=False` means `.env` (loaded first) wins for each variable."

Report says: "**Fix:** Reverse the list order so `.env.prod` is loaded last, or use `override=True` for more specific files."

The simplest fix that matches the report: **Reverse the list order:**

```python
env_files = [".env.prod", ".env.local", ".env.dev", ".env"]
```

With `override=False`, the FIRST file loaded wins. So if we put `.env.prod` first, it wins. But then `.env.local` and `.env.dev` can't override it... Hmm, that's also not great.

Actually, the most sensible approach is:
- `.env` should be lowest priority
- `.env.prod` should be highest priority

So reverse the list AND use `override=True`:
```python
env_files = [".env", ".env.dev", ".env.local", ".env.prod"]
# with override=True
```

This way: `.env` is loaded first, then `.env.dev` overrides, then `.env.local` overrides, then `.env.prod` overrides (highest priority).

Let me go with this approach.

**Commit:** `fix: env file loading order wrong`

---

### Fix 1.22 — Logger initialized before env files

**File:** [`app/__init__.py`](app/__init__.py:14)

**Current code:**
```python
env_files = [".env", ".env.dev", ".env.local", ".env.prod"]
logger = Logger()                           # <-- Created too early

def load_env_files() -> None:
    logger.debug("Loading environment files")   # <-- Uses logger
    ...

load_env_files()                            # <-- Called too late

settings = Settings()
```

**Fix:**
1. Remove `logger.debug()` calls from inside `load_env_files()` (they reference an undefined variable)
2. Move `logger = Logger()` to after `load_env_files()` and before `settings = Settings()`

**Result:**
```python
env_files = [".env", ".env.dev", ".env.local", ".env.prod"]

def load_env_files() -> None:
    root_dir = Path(__file__).parent.parent
    for env in env_files:
        f = root_dir / env
        if f.exists():
            if load_dotenv is not None:
                load_dotenv(dotenv_path=f, override=False)

load_env_files()

logger = Logger()      # <-- Moved after env files are loaded
settings = Settings()
```

**Commit:** `fix: logger initialized before env files`

---

### Fix 1.23 — ErrorResponse timestamp at class time

**File:** [`app/models/response/error.py`](app/models/response/error.py:19)

**Current code:**
```python
timestamp: int = int(time.time())
```

**Fix:** Use `Field(default_factory=...)` so each instance gets a fresh timestamp:
```python
from pydantic import Field
...
timestamp: int = Field(default_factory=lambda: int(time.time()))
```

**Commit:** `fix: ErrorResponse timestamp evaluated at class time`

---

### Fix 1.26 — No return assertions in token service tests (VERIFY ONLY)

**File:** [`tests/unit/service/test_token_service.py`](tests/unit/service/test_token_service.py)

**Current state:** Already fixed. The tests `test_successfully_get_token_by_id` (line 125) and `test_successfully_get_token_by_refresh_token` (line 145) both capture return values and assert on them.

No action needed.

---

### Fix 1.27 — No body assertions in refresh success test (VERIFY ONLY)

**File:** [`tests/integration/test_auth_api.py`](tests/integration/test_auth_api.py)

**Current state:** Already fixed. `test_successfully_refresh` (line 226) already asserts:
```python
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "Bearer"
        assert "expires_in" in body
```

No action needed.

---

## Execution Order

| Step | File | Change Summary |
|------|------|----------------|
| 1 | [`app/jwt_bearer.py`](app/jwt_bearer.py) | Add `PyJWTError` import + except block |
| 2 | [`app/routers/oauth/auth_router.py`](app/routers/oauth/auth_router.py) | Add constant + use it |
| 3 | [`tests/integration/test_auth_api.py`](tests/integration/test_auth_api.py) | Update assertion for new error message |
| 4 | [`app/api_handler.py`](app/api_handler.py) | Remove `["*"]` fallback |
| 5 | [`app/__init__.py`](app/__init__.py) | Fix env order and logger position |
| 6 | [`app/models/response/error.py`](app/models/response/error.py) | Use `Field(default_factory=...)` |
| 7 | Run tests | Verify all tests pass |
| 8 | Create 5 commits | One per actual fix (1.26 and 1.27 are already fixed) |

**Note:** Steps 2 and 3 (1.8 router fix + test update) should be in the same commit since the test must match the new error message.

## Final Commits

1. `fix: incomplete PyJWT exception coverage` — [`app/jwt_bearer.py`](app/jwt_bearer.py)
2. `fix: wrong OAuth error message for response type` — [`app/routers/oauth/auth_router.py`](app/routers/oauth/auth_router.py), [`tests/integration/test_auth_api.py`](tests/integration/test_auth_api.py)
3. `fix: CORS allows all origins` — [`app/api_handler.py`](app/api_handler.py)
4. `fix: env file loading order wrong` — [`app/__init__.py`](app/__init__.py)
5. `fix: logger initialized before env files` — [`app/__init__.py`](app/__init__.py)
6. `fix: ErrorResponse timestamp evaluated at class time` — [`app/models/response/error.py`](app/models/response/error.py)
