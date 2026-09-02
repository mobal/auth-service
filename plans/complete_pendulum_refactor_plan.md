# Complete Plan to Replace Pendulum with Python's Built-in datetime Library

## Executive Summary

This document outlines a comprehensive plan to refactor the auth-service project to replace the Pendulum library with Python's built-in datetime library. The refactor affects 19 files with approximately 57 instances of Pendulum usage. The estimated effort is 8-12 hours including implementation, testing, and validation.

## Refactor Scope

### Files to Modify

#### Production Code Files (4 files)
1. `app/__init__.py` - Contains `pendulum.set_local_timezone()`
2. `app/repositories/authorization_code_repository.py` - Uses `pendulum.now()` and `.add()`
3. `app/services/auth_service.py` - Uses `pendulum.now()`, `.add()`, `.int_timestamp`, `.subtract()`
4. `app/services/token_service.py` - Uses `pendulum.from_timestamp()` and `.to_iso8601_string()`

#### Test Files (10 files)
1. `tests/conftest.py` - Uses various Pendulum methods
2. `tests/integration/conftest.py` - Uses `pendulum.now().int_timestamp`
3. `tests/integration/test_auth_api.py` - Uses various Pendulum methods
4. `tests/unit/conftest.py` - Uses `pendulum.from_timestamp()`
5. `tests/unit/repository/test_authorization_code_repository.py` - Uses `pendulum.now().int_timestamp`
6. `tests/unit/repository/test_service_repository.py` - Uses `pendulum.now().to_iso8601_string()`
7. `tests/unit/repository/test_token_repository.py` - Uses various Pendulum methods
8. `tests/unit/service/test_auth_service.py` - Uses various Pendulum methods
9. `tests/unit/service/test_token_service.py` - Uses `pendulum.from_timestamp()` and `.to_iso8601_string()`
10. `tests/unit/client/test_user_service_client.py` - May need updates if it uses datetime

#### Configuration Files (1 file)
1. `pyproject.toml` - Remove `pendulum>=3.2.0` from dependencies

## Detailed Implementation Plan

### Phase 1: Dependency Management
**File**: `pyproject.toml`
- Remove `pendulum>=3.2.0` from the dependencies list

### Phase 2: Production Code Refactoring

#### File: `app/__init__.py`
**Current Code**:
```python
import pendulum
# ...
pendulum.set_local_timezone(pendulum.timezone(settings.default_timezone))
```

**Refactored Code**:
```python
from datetime import datetime, timezone
import zoneinfo  # Python 3.9+

# Replace the pendulum timezone setting with standard timezone handling
# Use zoneinfo for timezone conversions if needed
```

#### File: `app/repositories/authorization_code_repository.py`
**Current Code**:
```python
import pendulum
# ...
now = pendulum.now("UTC")
expire_at = now.add(minutes=10)
ttl = expire_at.int_timestamp
```

**Refactored Code**:
```python
from datetime import datetime, timedelta, timezone
# ...
now = datetime.now(timezone.utc)
expire_at = now + timedelta(minutes=10)
ttl = int(expire_at.timestamp())
```

#### File: `app/services/auth_service.py`
**Current Code**:
```python
import pendulum
# ...
iat = pendulum.now("UTC")
exp = (
    iat.add(seconds=settings.jwt_token_lifetime)
    if exp is None
    else iat.add(seconds=exp)
)
# ...
remaining = self._user_service_token.exp - pendulum.now("UTC").int_timestamp
# ...
now = pendulum.now("UTC").int_timestamp
```

**Refactored Code**:
```python
from datetime import datetime, timedelta, timezone
# ...
iat = datetime.now(timezone.utc)
exp = (
    iat + timedelta(seconds=settings.jwt_token_lifetime)
    if exp is None
    else iat + timedelta(seconds=exp)
)
# ...
remaining = self._user_service_token.exp - int(datetime.now(timezone.utc).timestamp())
# ...
now = int(datetime.now(timezone.utc).timestamp())
```

#### File: `app/services/token_service.py`
**Current Code**:
```python
import pendulum
# ...
"created_at": pendulum.from_timestamp(jwt_token.iat).to_iso8601_string(),
"expire_at": pendulum.from_timestamp(
    refresh_token.ttl if refresh_token else jwt_token.exp
).to_iso8601_string(),
```

**Refactored Code**:
```python
from datetime import datetime, timezone
# ...
"created_at": datetime.fromtimestamp(jwt_token.iat, timezone.utc).isoformat().replace("+00:00", "Z"),
"expire_at": datetime.fromtimestamp(
    refresh_token.ttl if refresh_token else jwt_token.exp, 
    timezone.utc
).isoformat().replace("+00:00", "Z"),
```

### Phase 3: Test Files Refactoring

All test files need similar updates to replace Pendulum with datetime. The patterns are consistent across files:

#### Common Replacements:
- `pendulum.now()` → `datetime.now(timezone.utc)`
- `pendulum.now().int_timestamp` → `int(datetime.now(timezone.utc).timestamp())`
- `pendulum.from_timestamp(ts)` → `datetime.fromtimestamp(ts, timezone.utc)`
- `dt.add(hours=1)` → `dt + timedelta(hours=1)`
- `dt.subtract(days=2)` → `dt - timedelta(days=2)`
- `dt.to_iso8601_string()` → `dt.isoformat().replace("+00:00", "Z")`

### Phase 4: Validation and Testing

#### Test Plan:
1. Run all unit tests:
   ```bash
   pytest tests/unit/
   ```

2. Run all integration tests:
   ```bash
   pytest tests/integration/
   ```

3. Manual testing of datetime-related functionality:
   - Token generation and expiration
   - Authorization code creation and validation
   - Service token handling

## Replacement Patterns Reference

| Pendulum Method | datetime Equivalent | Notes |
|----------------|---------------------|-------|
| `import pendulum` | `from datetime import datetime, timezone, timedelta` | Import changes |
| `pendulum.now()` | `datetime.now(timezone.utc)` | For UTC times |
| `pendulum.now("UTC")` | `datetime.now(timezone.utc)` | Explicit UTC timezone |
| `pendulum.from_timestamp(timestamp)` | `datetime.fromtimestamp(timestamp, timezone.utc)` | Add timezone for consistency |
| `dt.int_timestamp` | `int(dt.timestamp())` | Convert to integer timestamp |
| `dt.to_iso8601_string()` | `dt.isoformat().replace("+00:00", "Z")` | For UTC times, replace timezone format |
| `dt.add(duration)` | `dt + timedelta(**duration_params)` | Use timedelta for addition |
| `dt.subtract(duration)` | `dt - timedelta(**duration_params)` | Use timedelta for subtraction |
| `pendulum.timezone("UTC")` | `timezone.utc` | Standard UTC timezone |
| `pendulum.set_local_timezone()` | Handle timezone conversion explicitly | Not directly equivalent |

## Risk Assessment and Mitigation

### Risks:
1. **Timezone Inconsistencies**: Ensuring all datetime objects use the same timezone
2. **Timestamp Precision**: Converting between float and integer timestamps
3. **Test Failures**: Tests may fail due to slight differences in datetime formatting
4. **Performance Changes**: datetime operations might have different performance characteristics

### Mitigation Strategies:
1. Use `timezone.utc` consistently throughout the application
2. Convert timestamps with `int(dt.timestamp())` to match existing integer expectations
3. Run all tests before and after changes to identify regressions
4. Use `isoformat().replace("+00:00", "Z")` to maintain ISO 8601 formatting consistency

## Implementation Approach

### Recommended Order:
1. Update dependencies in `pyproject.toml`
2. Refactor production code files
3. Refactor test files
4. Run tests and fix any issues
5. Code review and validation

### Tools and Commands:
```bash
# Run unit tests
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run all tests
pytest tests/ -v
```

## Conclusion

This refactor will reduce external dependencies while maintaining all existing functionality. The changes are straightforward method replacements with well-established patterns. The main considerations are ensuring timezone consistency and maintaining compatibility with existing timestamp expectations.

The refactor should improve long-term maintainability by using Python's standard library instead of a third-party dependency for datetime operations.