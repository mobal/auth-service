# Plan to Replace Pendulum with Python's Built-in datetime Library

## Overview
This plan outlines the steps needed to replace Pendulum with Python's built-in datetime library in the auth-service project. Based on the analysis, there are 57 instances of Pendulum usage across 19 files that need to be refactored.

## Files to Modify

### Production Code Files
1. `app/__init__.py` - Contains `pendulum.set_local_timezone()`
2. `app/repositories/authorization_code_repository.py` - Uses `pendulum.now()` and `.add()`
3. `app/services/auth_service.py` - Uses `pendulum.now()`, `.add()`, `.int_timestamp`, `.subtract()`
4. `app/services/token_service.py` - Uses `pendulum.from_timestamp()` and `.to_iso8601_string()`

### Test Files
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

## Dependency Changes
1. `pyproject.toml` - Remove `pendulum>=3.2.0` from dependencies

## Replacement Patterns

### Import Changes
- Replace `import pendulum` with `from datetime import datetime, timezone, timedelta`
- Replace `import pendulum` with `from datetime import datetime, timezone, timedelta` in all test files

### Method Replacements

| Pendulum Method | datetime Equivalent | Notes |
|----------------|---------------------|-------|
| `pendulum.now()` | `datetime.now(timezone.utc)` | For UTC times |
| `pendulum.now("UTC")` | `datetime.now(timezone.utc)` | Explicit UTC timezone |
| `pendulum.from_timestamp(timestamp)` | `datetime.fromtimestamp(timestamp, timezone.utc)` | Add timezone for consistency |
| `dt.add(hours=1)` | `dt + timedelta(hours=1)` | Use timedelta for addition |
| `dt.subtract(days=2)` | `dt - timedelta(days=2)` | Use timedelta for subtraction |
| `dt.int_timestamp` | `int(dt.timestamp())` | Convert to integer timestamp |
| `dt.to_iso8601_string()` | `dt.isoformat().replace("+00:00", "Z")` | For UTC times, replace timezone format |
| `pendulum.timezone("UTC")` | `timezone.utc` | Standard UTC timezone |
| `pendulum.set_local_timezone()` | Handle timezone conversion explicitly | Not directly equivalent |

## Detailed Implementation Steps

### 1. Update Dependencies
- Remove pendulum from `pyproject.toml`

### 2. Update Production Code
- Update `app/__init__.py` to handle timezone differently
- Update `app/repositories/authorization_code_repository.py` 
- Update `app/services/auth_service.py`
- Update `app/services/token_service.py`

### 3. Update Test Files
- Update all test files to use datetime instead of pendulum
- Ensure test assertions still work correctly

### 4. Testing
- Run all unit tests
- Run all integration tests
- Verify that all datetime-related functionality works as expected

## Risk Assessment
1. **Timezone Handling**: The biggest risk is ensuring all datetime objects are timezone-aware and consistent
2. **Timestamp Conversions**: Converting between different timestamp formats needs careful handling
3. **Test Failures**: Tests may fail due to slight differences in datetime formatting or calculations
4. **Performance**: datetime operations might have different performance characteristics

## Estimated Impact
- **Scope**: 19 files need modification
- **Complexity**: Medium - requires careful attention to timezone handling
- **Risk**: Medium - potential for datetime-related bugs if not careful
- **Testing**: All existing tests need to pass after the refactor

## Validation Plan
1. Run unit tests
2. Run integration tests
3. Manual testing of datetime-related functionality
4. Code review of changes